import sys
sys.path.insert(0, ".")
import collections
import numpy as np
from possession.pilot import game3
ev = game3.load_events()
for p in (1, 2):
    es = [e for e in ev if e["period"] == p]
    print("period", p, "first start", min(e["start"] for e in es), "last end", max(e["end"] for e in es), "n", len(es))
print("share end>start %.2f" % np.mean([e["end"] > e["start"] for e in ev]))
print("sorted by start:", all(ev[i]["start"] <= ev[i + 1]["start"] for i in range(len(ev) - 1)))
S = lambda e: "%s %-14s %-24s %6d-%6d" % ("H" if e["team"] == 0 else "A", e["type"], ",".join(sorted(e["subs"])), e["start"], e["end"])
for k in range(0, 45):
    print(k, S(ev[k]))
print("--- around some BALL OUT / FAULT / SHOT GOAL")
shown = 0
for k, e in enumerate(ev):
    if (e["type"] in ("BALL OUT", "FAULT RECEIVED") or (e["type"] == "SHOT" and "goal" in e["subs"])) and shown < 6 and k > 60:
        for j in range(max(0, k - 2), min(len(ev), k + 4)):
            print("  ", j, S(ev[j]))
        print(); shown += 1
print("last events of period 1 / 2:")
for p in (1, 2):
    es = [e for e in ev if e["period"] == p][-4:]
    for e in es: print("  p%d" % p, S(e))
