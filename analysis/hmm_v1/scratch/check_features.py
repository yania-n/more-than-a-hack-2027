import sys, time
sys.path.insert(0, ".")
import numpy as np
from possession import data, features as F

t = time.time()
sig = F.frame_signals(data.load_atd())
g, v = sig["graded"], sig["vis"]
print("signals %.1fs  radius %.2f m  carry %.2f m/s  flight share of visible graded %.3f"
      % (time.time() - t, sig["radius"], sig["carry"], sig["flight"][g & v].mean()), flush=True)
seqs, specs, halves, edges = F.build(sig)
X = np.concatenate(seqs)
print("blocks", X.shape)
for f, sp in enumerate(specs):
    print(sp.name, "missing %.3f" % (X[:, f] < 0).mean(),
          np.bincount(X[X[:, f] >= 0, f], minlength=sp.n_cat).tolist())
print({k: np.round(e, 2).tolist() for k, e in edges.items()})
