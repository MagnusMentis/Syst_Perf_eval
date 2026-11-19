import logging
import random

from bkitevsim.core import BkSysCoLogicalProcess, Simulation, SimulationOptions
from bkitevsim.core.event import create_event

from async_dispatcher_workers import (
    AsyncDispatcherLP,
    AsyncWorkerLP,
    EventType,
    Task,
)


class TaskGeneratorLP(BkSysCoLogicalProcess):
    def __init__(self, lp_id: int, dispatcher_id: int, lam: float, mu: float, sim_end: float, seed: int = 42, **kwargs):
        super().__init__(lp_id, **kwargs)
        self.dispatcher_id = dispatcher_id
        self.lam = lam
        self.mu = mu
        self.sim_end = sim_end
        self.rng = random.Random(seed)

    async def coroutine_run(self):
        seq = 0
        while True:
            now = await self.advance_time(self.rng.expovariate(self.lam))
            if now >= self.sim_end:
                break
            seq += 1
            task = Task(seq, now, self.rng.expovariate(self.mu))
            self.send_event(create_event(
                timestamp=now,
                sender_id=self.lp_id,
                receiver_id=self.dispatcher_id,
                event_type=EventType.TASK_ARRIVAL.value,
                payload=task,
            ))


def run_test(end_time: float = 500.0, num_workers: int = 3, capacity: int = 8, lam: float = 5.0, mu: float = 2.0):
    # Keep bucket_width large enough so LadderQueue (1024 buckets) does not wrap around
    options = SimulationOptions(
        end_time=end_time,
        dispatcher="auto",
        bucket_width=max(1.0, end_time / 512.0),
    )
    sim = Simulation(options, models={
        "Dispatcher": AsyncDispatcherLP,
        "Worker": AsyncWorkerLP,
        "Generator": TaskGeneratorLP,
    })

    disp_id = 0
    worker_ids = [10 + i for i in range(num_workers)]

    sim.create_lp(disp_id, "Dispatcher", worker_ids=worker_ids, capacity=capacity)
    sim.create_lp(1, "Generator", dispatcher_id=disp_id, lam=lam, mu=mu, sim_end=end_time)
    for w_id in worker_ids:
        sim.create_lp(w_id, "Worker", dispatcher_id=disp_id)

    stats = sim.run()
    lp_stats = sim.get_statistics().get("lp_statistics", {})

    print(f"Events: {stats['events_processed']} | Wall time: {stats['wall_time']:.4f}s")
    print("Dispatcher:", lp_stats.get(disp_id))
    for w_id in worker_ids:
        st = lp_stats.get(w_id, {})
        util = st.get("busy_time", 0.0) / end_time
        print(f"Worker {w_id}: processed={st.get('processed')}, util={util:.2%}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    run_test()