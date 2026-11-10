import json, sys
sys.path.insert(0, ".")
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from possession import data, features, run
import hmm_sub

seqs, specs, halves, edges = features.build(features.frame_signals(data.load_atd()))
stay = [s * data.FPS / features.BLOCK for s in run.PRIOR_DWELL_S]
p = hmm_sub.fit(seqs, specs, stay, 1)
v1 = json.load(open("analysis/hmm_v1/model.json"))
n = sum(len(s) for s in seqs)
print("m=1 final logL/step %.5f   v1 %.5f" % (p["history"][-1] / n, v1["history"][-1] / n))
print("max |A diff| vs v1:", np.abs(p["A"] - np.array(v1["A"])).max())
paths = hmm_sub.decode(seqs, p)
codes = features.upsample(paths, halves)
lab = np.array(["H", "A", "D", "X"])[codes]
old = np.array([l.strip().split(",")[1] for l in open("submissions/hmm_v1.csv").read().split("\n")[1:] if l])
print("identical labels to v1 submission:", bool((lab == old).all()), "differing frames:", int((lab != old).sum()))
