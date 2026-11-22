import math

METRICS = ("Wq", "W", "Lq", "L", "U", "X", "Pblock", "lambda_eff")

class StatisticsCollector:
    def __init__(self, servers, warmup=0.0):
        self.servers = servers
        self.warmup = warmup
        self.last_time = 0.0
        self.area_system = 0.0
        self.area_queue = 0.0
        self.area_busy = 0.0
        self.arrivals = 0
        self.rejections = 0
        self.completions = 0
        self.total_wait = 0.0
        self.total_response = 0.0

    def advance(self, now, in_system, in_queue, busy):
        start = max(self.last_time, self.warmup)
        if now > start:
            span = now - start
            self.area_system += in_system * span
            self.area_queue += in_queue * span
            self.area_busy += busy * span
        self.last_time = now

    def record_arrival(self, now):
        if now >= self.warmup:
            self.arrivals += 1

    def record_rejection(self, now):
        if now >= self.warmup:
            self.rejections += 1

    def record_completion(self, arrival_time, start_time, now):
        if now < self.warmup:
            return
        self.completions += 1
        self.total_wait += start_time - arrival_time
        self.total_response += now - arrival_time

    def summarize(self, end_time):
        window = end_time - self.warmup
        done = max(self.completions, 1)
        offered = max(self.arrivals, 1)
        utilization = math.nan if math.isinf(self.servers) else self.area_busy / window / self.servers
        return {
            "Wq": self.total_wait / done,
            "W": self.total_response / done,
            "Lq": self.area_queue / window,
            "L": self.area_system / window,
            "U": utilization,
            "X": self.completions / window,
            "Pblock": self.rejections / offered,
            "lambda_eff": (self.arrivals - self.rejections) / window,
        }
