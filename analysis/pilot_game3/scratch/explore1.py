import sys
sys.path.insert(0, ".")
import collections
import numpy as np
from possession.pilot import game3

t = game3.load_tracking()
ev = game3.load_events()
ball, pl = t["ball"], t["players"]
n = len(ball)
print("frames", n, "half blocks (0-based)", game3.half_blocks())
print("ball visible %.4f" % np.isfinite(ball[:, 0]).mean(), " players present per frame mean %.2f" %
      np.isfinite(pl[:, :, 0]).sum(1).mean(), " min", np.isfinite(pl[:, :, 0]).sum(1).min())
print("ball min/max x,y", np.nanmin(ball, 0), np.nanmax(ball, 0))
# sync check: distance ball -> event player at event start (+offset)
cols = t["col_player"]
for etype in ("PASS", "SHOT", "CARRY", "SET PIECE"):
    res = {}
    for off in (-3, -2, -1, 0, 1, 2, 3):
        d = []
        for e in ev:
            if e["type"] != etype or e["player"] is None:
                continue
            f = e["start"] + off
            if not (0 <= f < n):
                continue
            j = np.flatnonzero(cols[f] == e["player"])
            if j.size and np.isfinite(ball[f, 0]):
                d.append(np.hypot(*(pl[f, j[0]] - ball[f])))
        res[off] = (len(d), np.percentile(d, [25, 50, 75, 90]).round(2).tolist())
    print(etype, "(n, [p25,p50,p75,p90] of ball-to-event-player distance, m)")
    for off, v in res.items():
        print("  offset %+d" % off, v)
print("event frame ranges by period:")
for p in (1, 2):
    es = [e for e in ev if e["period"] == p]
    print(" period", p, "first", min(e["start"] for e in es), "last end", max(e["end"] for e in es), "n", len(es))
# start==end?
print("share of events with end > start:", np.mean([e["end"] > e["start"] for e in ev]))
print("events sorted by start?", all(ev[i]["start"] <= ev[i + 1]["start"] for i in range(len(ev) - 1)))
# sequences around stoppages
seq = [(e["start"], e["end"], "AH"[e["team"]] if False else ("H" if e["team"] == 0 else "A"), e["type"], sorted(e["subs"])) for e in ev]
for k in range(0, 40):
    print(seq[k])
