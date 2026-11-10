import sys
sys.path.insert(0, ".")
import numpy as np
from possession import features, run
np.set_printoptions(precision=3, suppress=True)
for nb in (6, 12, 24):
    features.N_PSPEED = nb
    m = run.fit_model(verbose=False)
    e = m["params"]["emis"][6]
    print(nb, "bins; D emission:", e[2], "\n   alive:", e[0], "\n   D share (viterbi):",
          np.mean(np.concatenate(m["paths"]) == 2).round(3), "iters", len(m["params"]["history"]))
