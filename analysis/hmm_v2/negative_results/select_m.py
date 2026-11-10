"""Choose the number of substates m by held-out likelihood (2-fold over the two halves).

Label-free: fit on one half, score the log-likelihood of the other half under the fitted model.
Rule fixed before looking at any v2 output: pick the m with the highest total held-out log-lik;
if m=2..4 do not beat m=1 by a clear margin, v2's duration structure is not supported by the data.
"""
import json
import sys
import time

sys.path.insert(0, ".")
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from possession import data, features, run
import hmm_sub

atd = data.load_atd()
sig = features.frame_signals(atd)
seqs, specs, halves, edges = features.build(sig)
stay = [s * data.FPS / features.BLOCK for s in run.PRIOR_DWELL_S]
res = {}
for m in (1, 2, 3, 4):
    t = time.time()
    tot = 0.0
    for tr, te in ((0, 1), (1, 0)):
        p = hmm_sub.fit([seqs[tr]], specs, stay, m)
        tot += hmm_sub.loglik([seqs[te]], p)
    n = sum(len(s) for s in seqs)
    res[m] = tot / n
    print("m=%d  held-out logL/step %.5f  (%.0fs)" % (m, tot / n, time.time() - t), flush=True)
json.dump(res, open("analysis/hmm_v2/negative_results/select_m.json", "w"))
print("best m:", max(res, key=res.get))
