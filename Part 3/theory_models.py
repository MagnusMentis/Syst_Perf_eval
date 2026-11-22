import math

from statistics_collector import METRICS

def pack(Wq, W, Lq, L, U, X, Pblock, lambda_eff):
    return dict(zip(METRICS, (Wq, W, Lq, L, U, X, Pblock, lambda_eff)))

def unstable():
    return pack(*([math.nan] * 8))

def mm1(lam, mu, c, K):
    rho = lam / mu
    if rho >= 1:
        return unstable()
    return pack(lam / (mu * (mu - lam)), 1 / (mu - lam), rho ** 2 / (1 - rho), rho / (1 - rho), rho, lam, 0.0, lam)

def mm1k(lam, mu, c, K):
    rho = lam / mu
    if abs(rho - 1) < 1e-12:
        p = [1 / (K + 1)] * (K + 1)
    else:
        p = [(1 - rho) * rho ** n / (1 - rho ** (K + 1)) for n in range(K + 1)]
    L = sum(n * pn for n, pn in enumerate(p))
    lam_eff = lam * (1 - p[K])
    Lq = L - (1 - p[0])
    return pack(Lq / lam_eff, L / lam_eff, Lq, L, 1 - p[0], lam_eff, p[K], lam_eff)

def mminf(lam, mu, c, K):
    return pack(0.0, 1 / mu, 0.0, lam / mu, math.nan, lam, 0.0, lam)

def mmnn(lam, mu, c, K):
    a = lam / mu
    term = 1.0
    total = 1.0
    for j in range(1, c + 1):
        term *= a / j
        total += term
    pblock = term / total
    lam_eff = lam * (1 - pblock)
    return pack(0.0, 1 / mu, 0.0, lam_eff / mu, lam_eff / (c * mu), lam_eff, pblock, lam_eff)

def mmc(lam, mu, c, K):
    a = lam / mu
    rho = a / c
    if rho >= 1:
        return unstable()
    term = 1.0
    total = 0.0
    for n in range(c):
        total += term
        term *= a / (n + 1)
    last = term / (1 - rho)
    p0 = 1 / (total + last)
    p_wait = last * p0
    Lq = p_wait * rho / (1 - rho)
    Wq = Lq / lam
    return pack(Wq, Wq + 1 / mu, Lq, Lq + a, rho, lam, 0.0, lam)

def mmck(lam, mu, c, K):
    a = lam / mu
    weights = [1.0]
    for j in range(1, K + 1):
        weights.append(weights[-1] * a / min(j, c))
    total = sum(weights)
    p = [w / total for w in weights]
    L = sum(j * pj for j, pj in enumerate(p))
    B = sum(min(j, c) * pj for j, pj in enumerate(p))
    lam_eff = lam * (1 - p[K])
    Lq = L - B
    return pack(Lq / lam_eff, L / lam_eff, Lq, L, B / c, lam_eff, p[K], lam_eff)

THEORY = {"M/M/1": mm1, "M/M/1/K": mm1k, "M/M/inf": mminf, "M/M/n/n": mmnn, "M/M/c": mmc, "M/M/c/K": mmck}

def compute_theory(model, lam, mu, c, K):
    return THEORY[model](lam, mu, c, K)
