# Part 2: Non-Blocking Async Dispatcher & Workers (using asyncio & bkitevsim)


from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from bkitevsim.core import (
    BkSysCoLogicalProcess,
    BkSysLogicalProcessState,
    BkSysFuture,
    TIMEOUT_ERROR,
)
from bkitevsim.core.event import create_event
from bkitevsim.core.logical_coProcess import CANCELLED_ERROR


class EventType(Enum):
    TASK_ARRIVAL = "TASK_ARRIVAL"
    ASSIGN_TASK = "ASSIGN_TASK"
    WORKER_DONE = "WORKER_DONE"


@dataclass
class Task:
    task_id: int
    arrival_time: float
    service_duration: float
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    worker_id: Optional[int] = None
    future: Optional[BkSysFuture] = None


@dataclass
class WorkerState(BkSysLogicalProcessState):
    is_busy: bool = False
    processed: int = 0
    busy_time: float = 0.0


@dataclass
class DispatcherState(BkSysLogicalProcessState):
    arrived: int = 0
    dispatched: int = 0
    rejected: int = 0


class AsyncWorkerLP(BkSysCoLogicalProcess):
    def __init__(self, lp_id: int, dispatcher_id: int, **kwargs):
        super().__init__(lp_id, initial_state=WorkerState(), **kwargs)
        self.dispatcher_id = dispatcher_id

    async def coroutine_run(self):
        while True:
            try:
                ev = await self.wait_for_multiple([EventType.ASSIGN_TASK.value])
                self._pending_events = [e for e in self._pending_events if e is not ev]
            except (TIMEOUT_ERROR, CANCELLED_ERROR):
                break

            task: Task = ev.payload
            start = ev.timestamp
            self.state.is_busy = True
            task.worker_id = self.lp_id
            task.start_time = start

            end = await self.advance_time(task.service_duration)
            self.set_local_virt_time(end)

            task.end_time = end
            self.state.is_busy = False
            self.state.processed += 1
            self.state.busy_time += end - start

            if task.future and not task.future.done():
                task.future.set_result(task)

            self.send_event(create_event(
                timestamp=end,
                sender_id=self.lp_id,
                receiver_id=self.dispatcher_id,
                event_type=EventType.WORKER_DONE.value,
                payload={"worker_id": self.lp_id, "task": task},
            ))

    def get_statistics(self):
        return {
            "lp_id": self.lp_id,
            "role": "worker",
            "processed": self.state.processed,
            "busy_time": self.state.busy_time,
        }


class AsyncDispatcherLP(BkSysCoLogicalProcess):
    def __init__(self, lp_id: int, worker_ids: list[int], capacity: Optional[int] = None, **kwargs):
        super().__init__(lp_id, initial_state=DispatcherState(), **kwargs)
        self.idle_workers = deque(worker_ids)
        self.busy_workers = set()
        self.queue = deque()
        self.capacity = capacity

    def _assign(self, task: Task, worker_id: int, now: float):
        self.busy_workers.add(worker_id)
        self.state.dispatched += 1
        self.send_event(create_event(
            timestamp=now,
            sender_id=self.lp_id,
            receiver_id=worker_id,
            event_type=EventType.ASSIGN_TASK.value,
            payload=task,
        ))

    def _flush_queue(self, now: float):
        while self.queue and self.idle_workers:
            self._assign(self.queue.popleft(), self.idle_workers.popleft(), now)

    async def coroutine_run(self):
        while True:
            try:
                ev = await self.wait_for_multiple([
                    EventType.TASK_ARRIVAL.value,
                    EventType.WORKER_DONE.value,
                ])
                self._pending_events = [e for e in self._pending_events if e is not ev]
            except (TIMEOUT_ERROR, CANCELLED_ERROR):
                break

            now = ev.timestamp
            if ev.event_type == EventType.TASK_ARRIVAL.value:
                task: Task = ev.payload
                self.state.arrived += 1
                if task.future is None and self._event_loop:
                    task.future = self._create_future()

                in_system = len(self.queue) + len(self.busy_workers)
                if self.capacity is not None and in_system >= self.capacity:
                    self.state.rejected += 1
                    if task.future and not task.future.done():
                        task.future.cancel()
                    continue

                if not self.queue and self.idle_workers:
                    self._assign(task, self.idle_workers.popleft(), now)
                else:
                    self.queue.append(task)
                    self._flush_queue(now)

            elif ev.event_type == EventType.WORKER_DONE.value:
                w_id = ev.payload["worker_id"]
                self.busy_workers.discard(w_id)
                self.idle_workers.append(w_id)
                self._flush_queue(now)

    def get_statistics(self):
        return {
            "lp_id": self.lp_id,
            "role": "dispatcher",
            "arrived": self.state.arrived,
            "dispatched": self.state.dispatched,
            "rejected": self.state.rejected,
            "in_queue": len(self.queue),
        }
