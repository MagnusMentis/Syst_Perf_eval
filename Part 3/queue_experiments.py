import csv
import math
import sys
from pathlib import Path

from queue_system_lp import INF, simulate_once
from statistics_collector import METRICS
from theory_models import compute_theory

REPLICATIONS = 4
NORMAL_DURATION = 6000.0
HEAVY_DURATION = 20000.0
WARMUP = 200.0
BASE_SEED = 20261120
MIN_THEORY = 0.01
TOLERANCE = 5.0

def build_experiments():
    rows = []
    for lam in (4, 6, 8, 9, 9.5):
        rows.append(("M/M/1", "Main", lam, 10, 1, INF))
    for lam, K in ((8, 5), (10, 5), (12, 5), (12, 10), (12, 20)):
        rows.append(("M/M/1/K", "Main", lam, 10, 1, K))
    for lam, mu in ((10, 12), (20, 12), (30, 12), (20, 10), (20, 20)):
        rows.append(("M/M/inf", "Main", lam, mu, INF, INF))
    for n in range(1, 6):
        rows.append(("M/M/n/n", "Set 1", 20, 12, n, n))
    for lam in (10, 20, 30, 40, 50):
        rows.append(("M/M/n/n", "Set 2", lam, 12, 3, 3))
    for c in range(2, 7):
        rows.append(("M/M/c", "Set 1", 20, 12, c, INF))
    for lam in (10, 20, 30, 35):
        rows.append(("M/M/c", "Set 2", lam, 12, 3, INF))
    for c in range(2, 6):
        rows.append(("M/M/c/K", "Set 1", 20, 12, c, 10))
    for K in (3, 5, 10, 15, 20):
        rows.append(("M/M/c/K", "Set 2", 20, 12, 3, K))
    return rows

def label_of(rows, index):
    model, group = rows[index][0], rows[index][1]
    count = sum(1 for r in rows[:index + 1] if r[0] == model and r[1] == group)
    return f"E{count}"

def duration_for(lam, mu, c, K):
    heavy = K == INF and c != INF and lam / (c * mu) >= 0.9
    return HEAVY_DURATION if heavy else NORMAL_DURATION

def simulate(index, lam, mu, c, K):
    T = duration_for(lam, mu, c, K)
    runs = [simulate_once(lam, mu, c, K, T, WARMUP, BASE_SEED + 1000 * index + r) for r in range(REPLICATIONS)]
    return {name: sum(run[name] for run in runs) / len(runs) for name in METRICS}

def relative_error(simulated, theoretical):
    if math.isnan(simulated) or math.isnan(theoretical):
        return math.nan
    if abs(theoretical) < 1e-12:
        return 0.0 if simulated == 0 else math.nan
    return abs(simulated - theoretical) / abs(theoretical) * 100

def fmt(value):
    return "n/a" if math.isnan(value) else f"{value:.5f}"

def limit_text(value):
    return "inf" if value == INF else str(value)

def worst_error(theory, simulated):
    errors = [relative_error(simulated[m], theory[m]) for m in METRICS if abs(theory[m]) >= MIN_THEORY]
    errors = [e for e in errors if not math.isnan(e)]
    return max(errors, default=0.0)

def main(out_dir="."):
    rows = build_experiments()
    out = Path(out_dir)
    summary = []
    with open(out / "results.csv", "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["model", "set", "experiment", "lambda", "mu", "c", "K", "metric", "theory", "simulation", "relative_error_percent"])
        for index, (model, group, lam, mu, c, K) in enumerate(rows):
            label = label_of(rows, index)
            theory = compute_theory(model, lam, mu, c, K)
            simulated = simulate(index, lam, mu, c, K)
            print(f"[{model}] {group} {label}  lambda={lam} mu={mu} c={limit_text(c)} K={limit_text(K)}")
            print(f"{'Metric':<12}{'Theory':<14}{'Simulation':<14}RelError(%)")
            for name in METRICS:
                error = relative_error(simulated[name], theory[name])
                print(f"{name:<12}{fmt(theory[name]):<14}{fmt(simulated[name]):<14}{fmt(error)}")
                writer.writerow([model, group, label, lam, mu, limit_text(c), limit_text(K), name, fmt(theory[name]), fmt(simulated[name]), fmt(error)])
            print()
            worst = worst_error(theory, simulated)
            verdict = "PASS" if worst <= TOLERANCE else "CHECK"
            summary.append(f"{model:<10}{group:<8}{label:<5}{worst:<12.5f}{verdict}")
            sys.stdout.flush()
    print(f"SUMMARY (max relative error over metrics with theory >= {MIN_THEORY}, tolerance {TOLERANCE}%)")
    print("\n".join(summary))

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
