import sys
sys.path.insert(0, ".")
import numpy as np
from possession import data, features, run, hmm

m = run.fit_model(verbose=False)
p = m["params"]
np.set_printoptions(precision=3, suppress=True)
print("A (rows from H,A,D):\n", p["A"])
step_s = features.BLOCK / data.FPS
print("expected sojourn s:", (step_s / (1 - np.diag(p["A"]))).round(1))
for sp, e in zip(m["specs"], p["emis"]):
    print(sp.name); print(e)
G = np.concatenate(hmm.posteriors(m["seqs"], p))
print("mean posterior H,A,D:", G.mean(0))
for half, path in zip(m["halves"], m["paths"]):
    print("viterbi share H,A,D", [(path == s).mean().round(3) for s in range(3)])
# posterior-weighted raw means
vals = {k: np.concatenate([h[k] for h in m["halves"]]) for k in ("pspeed", "bspeed", "gap")}
for k, v in vals.items():
    ok = np.isfinite(v)
    print(k, "mean by state H,A,D:", [(np.sum(G[ok, s] * v[ok]) / G[ok, s].sum()).round(2) for s in range(3)])
