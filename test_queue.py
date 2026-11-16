import math
from queue_simu import run, INF

NAMES= ['L', 'Lq', 'U', 'X', 'P_block', 'Wq', 'W']
 
def theory(lam, mu, c, K): #calcul of the parameters for every formulas
    kmax = int(K) if K != INF else 3000
    p = [1.0]
    for j in range(1, kmax + 1):
        p.append(p[-1] * lam / (min(j, c) * mu))
    total = sum(p)
    p = [x / total for x in p]
    L = sum(j * pj for j, pj in enumerate(p))
    busy = sum(min(j, c) * pj for j, pj in enumerate(p))
    p_block = p[kmax] if K != INF else 0.0
    lam_eff = lam * (1 - p_block)
    return {"L": L, "Lq": L - busy, "U": busy / c, "X": lam_eff,
            "P_block": p_block, "Wq": (L - busy) / lam_eff, "W": L / lam_eff}
 
 
CASES = [  # (systeme, lam, mu, c, K, T, tolerance) 
    ("M/M/1",     8, 10, 1,   INF, 40000, 0.07),
    ("M/M/1/5",  12, 10, 1,   5,   20000, 0.05),
    ("M/M/2/2",  20, 12, 2,   2,   20000, 0.05),
    ("M/M/3",    20, 12, 3,   INF, 20000, 0.05),
    ("M/M/3/5",  20, 12, 3,   5,   20000, 0.05),
    ("M/M/inf",  20, 12, INF, INF, 20000, 0.05),
]
 
for name, lam, mu, c, K, T, tol in CASES:
    th, sim = theory(lam, mu, c, K), dict(zip(NAMES, run(lam, mu, c, K, T)))
    print(f"\n{name}  (λ={lam}, µ={mu}, c={c}, K={K})")
    for key in NAMES:
        a, b = th[key], sim[key]
        err = abs(b - a) / abs(a) if abs(a) > 1e-2 else abs(b - a)
        print(f"  {'' if err <= tol else 'KO'} {key:8s} théorie={a:.5f} simu={b:.5f} err={err*100:.2f}%")
        assert err <= tol, f"{name} / {key}"
 
print("\n the test work.")