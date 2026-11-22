import random
from collections import deque

from bkitevsim.core import Event, BkSysLogicalProcess, Simulation, SimulationOptions
from statistics_collector import StatisticsCollector

INF = float("inf")

class QueueSystemLP(BkSysLogicalProcess):
    def __init__(self, lp_id, lam, mu, c, K, T, warmup, seed):
        super().__init__(lp_id)
        self.lam = lam
        self.mu = mu
        self.c = c
        self.K = K
        self.T = T
        self.arrival_rng = random.Random(f"{seed}-arrival")
        self.service_rng = random.Random(f"{seed}-service")
        self.waiting = deque()
        self.busy = 0
        self.stats = StatisticsCollector(c, warmup)

    def _send(self, time, kind, payload=None):
        self.send_event(Event(time, self.lp_id, self.lp_id, kind, payload))

    def _in_system(self):
        return self.busy + len(self.waiting)

    def _observe(self, now):
        self.stats.advance(now, self._in_system(), len(self.waiting), self.busy)

    def _start_service(self, arrival_time, now):
        self.busy += 1
        service = self.service_rng.expovariate(self.mu)
        self._send(now + service, "END_SERVICE", (arrival_time, now))

    def initialize(self):
        self._send(self.arrival_rng.expovariate(self.lam), "ARRIVAL")

    def handle_event(self, event):
        now = event.timestamp
        self._observe(now)
        if event.event_type == "ARRIVAL":
            self._on_arrival(now)
        else:
            self._on_departure(event)

    def _on_arrival(self, now):
        self._send(now + self.arrival_rng.expovariate(self.lam), "ARRIVAL")
        self.stats.record_arrival(now)
        if self._in_system() >= self.K:
            self.stats.record_rejection(now)
            return
        if self.busy < self.c:
            self._start_service(now, now)
        else:
            self.waiting.append(now)

    def _on_departure(self, event):
        arrival_time, start_time = event.payload
        self.busy -= 1
        self.stats.record_completion(arrival_time, start_time, event.timestamp)
        if self.waiting:
            self._start_service(self.waiting.popleft(), event.timestamp)

    def finalize(self):
        self._observe(self.T)

def simulate_once(lam, mu, c, K, T, warmup, seed):
    options = SimulationOptions(end_time=T, dispatcher="sequential", bucket_width=T / 500)
    sim = Simulation(options, models={"QueueSystemLP": QueueSystemLP})
    lp = sim.create_lp(0, "QueueSystemLP", lam=lam, mu=mu, c=c, K=K, T=T, warmup=warmup, seed=seed)
    sim.run()
    return lp.stats.summarize(T)
