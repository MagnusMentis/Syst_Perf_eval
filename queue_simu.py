import random 
from collections import deque
from bkitevsim.core import Event,BkSysLogicalProcess, Simulation, SimulationOptions

INF= float("inf")

class QueueSystemLP(BkSysLogicalProcess):
    def __init__(self, lp_id, lam, mu, c=1, K=INF, T= 1000.0, seed=42):
        super().__init__(lp_id)
        self.lam, self.mu, self.c, self.K, self.T= lam, mu, c, K, T
        self.rng_arrival = random.Random(f"{seed}-arrival")
        self.rng_service = random.Random(f"{seed}-service")

        self.waiting = deque() 
        self.busy = 0 #busy workers
        self.last_t = 0.0 #last update time
        self.area_n = self.area_q = self.area_busy = 0.0
        self.arrived = self.rejected = self.completed = self.started = 0
        self.wait_sum = self.resp_sum = 0.0 #waiting time

    def _send(self, time, kind, payload=None):
        self.send_event(Event(time, self.lp_id, self.lp_id, kind, payload))

    def _update_areas(self, now):
        dt = now - self.last_t
        self.area_n += (len(self.waiting) + self.busy) * dt
        self.area_q += len(self.waiting) * dt
        self.area_busy += self.busy * dt
        self.last_t = now

    def _start_service(self, now, arrival_time):
        self.busy += 1
        self.started += 1
        self.wait_sum += now - arrival_time
        service = self.rng_service.expovariate(self.mu)
        self._send(now + service, "END_SERVICE", arrival_time)

    def initialize(self):
        self._send(self.rng_arrival.expovariate(self.lam), "ARRIVAL")

    def handle_event(self, event):
        now = event.timestamp
        self.local_virt_time = now
        self._update_areas(now)

        if event.event_type == "ARRIVAL":
            self.arrived += 1
            self._send(now + self.rng_arrival.expovariate(self.lam), "ARRIVAL")
            if len(self.waiting) + self.busy >= self.K:      # system is full
                self.rejected += 1
            elif self.busy < self.c:                         # a worker is free
                self._start_service(now, now)
            else:                                            
                self.waiting.append(now)

        elif event.event_type == "END_SERVICE":
            self.busy -= 1
            self.completed += 1
            self.resp_sum += now - event.payload             # payload = arrival time
            if len(self.waiting)>0:                                 # FIFO
                self._start_service(now, self.waiting.popleft())

    def finalize(self):
        self._update_areas(self.T)


def run(lam, mu, c, K, T, seed=42):
    random.seed(seed)
    options = SimulationOptions(end_time=T, dispatcher="sequential", bucket_width=T / 500)
    sim = Simulation(options, models={"QueueSystemLP": QueueSystemLP})
    lp = sim.create_lp(0, "QueueSystemLP", lam=lam, mu=mu, c=c, K=K, T=T, seed=seed)
    sim.run()

    L = lp.area_n / T
    Lq = lp.area_q / T
    U = lp.area_busy / T / c
    X = lp.completed / T
    P_block = lp.rejected / lp.arrived
    Wq = lp.wait_sum / lp.started
    W = lp.resp_sum / lp.completed
    return L, Lq, U, X, P_block, Wq, W



if __name__ == "__main__":
    L, Lq, U, X, P_block, Wq, W = run(lam=12, mu=10, c=1, K=5, T=5000) #exemple:M/M/1/5
    print("L =", L)
    print("Lq =", Lq)
    print("U =", U)
    print("X =", X)
    print("P_block =", P_block)
    print("Wq =", Wq)
    print("W =", W)