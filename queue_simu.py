import random #we need random arrival and service time
from collections import deque #waiting list
from bkitevsim.core import Event,BkSysLogicalProcess, Simulation, SimulationOptions

INF= float("inf") #for the infinite workers or capacity options

class QueueSystemLP(BkSysLogicalProcess): #our own model 
    def __init__(self, lp_id, lam, mu, c, K, T):
        super().__init__(lp_id)
        self.lam = lam #arrival rate
        self.mu = mu #service rate
        self.c= c #workers numbers
        self.K = K # system capacity
        self.T= T #simulation time
    

        self.waiting = deque()  # empty waiting list at first
        self.busy = 0 #busy workers (0 at first too)
        self.last_t = 0.0 #last time update (0 at first too)
        
        self.area_n = self.area_q = self.area_busy = 0.0 #sums of persons in the area,sum of persons in the queue and sum of busy workers
        self.arrived = self.rejected = self.completed = self.started = 0 #number of arrived clients,number of rejected clients, number request completed and number of client getting served 
        self.wait_q = self.wait_tot = 0.0 #sum of waiting time in the queue, and total waiting time queue+service

    def send(self, time, kind, payload=None): #function to add an event to the simulator's list of events
        self.send_event(Event(time, self.lp_id, self.lp_id, kind, payload)) #sender and receiver are the same in our model

    def update_areas(self, now):
        dt = now - self.last_t #calculate time since previous event
        self.area_n += (len(self.waiting) + self.busy) * dt
        self.area_q += len(self.waiting) * dt
        self.area_busy += self.busy * dt
        self.last_t = now

    def start_service(self, now, arrival_time): #one more worker is busy, one more client is start service
        self.busy += 1
        self.started += 1
        self.wait_q += now - arrival_time
        service_time = random.expovariate(self.mu) # the service time is random
        self.send(now + service_time, "END_SERVICE", arrival_time)

    def initialize(self): #schedule the first arrival
        self.send(random.expovariate(self.lam), "ARRIVAL")

    def handle_event(self, event): #function to handle an event 
        now = event.timestamp
        self.local_virt_time = now
        self.update_areas(now)

        if event.event_type == "ARRIVAL":
            self.arrived += 1
            self.send(now + random.expovariate(self.lam), "ARRIVAL") #program next arrival
            if len(self.waiting) + self.busy >= self.K: # system is full
                self.rejected += 1  #client get rejected
            elif self.busy < self.c:     # a worker is free
                self.start_service(now, now) #service start
            else:                                            
                self.waiting.append(now) #client stays in the waiting list

        elif event.event_type == "END_SERVICE":
            self.busy -= 1 #one worker is free
            self.completed += 1 
            self.wait_tot += now - event.payload # payload = arrival time
            if len(self.waiting)>0: # FIFO
                self.start_service(now, self.waiting.popleft())

    def finalize(self):
        self.update_areas(self.T)


def run(lam, mu, c, K, T, seed=42):
    random.seed(seed)
    options = SimulationOptions(end_time=T, dispatcher="sequential", bucket_width=T / 500)
    sim = Simulation(options, models={"QueueSystemLP": QueueSystemLP})
    lp = sim.create_lp(0, "QueueSystemLP", lam=lam, mu=mu, c=c, K=K, T=T)
    sim.run()

    L = lp.area_n / T
    Lq = lp.area_q / T
    U = lp.area_busy / T / c
    X = lp.completed / T
    P_block = lp.rejected / lp.arrived
    Wq = lp.wait_q / lp.started
    W = lp.wait_tot / lp.completed
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