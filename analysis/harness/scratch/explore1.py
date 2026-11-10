import sys
sys.path.insert(0, ".")
import numpy as np
from possession.harness import games
from possession.pilot import labels as L

for name in games.GAMES:
    g = games.load_game(name)
    n = len(g["ball"]); pl = g["players"]; ball = g["ball"]
    present = np.isfinite(pl[:, :, 0]).sum(1)
    print("=====", name, "fps", g["fps"], "frames", n, "slots", pl.shape[1], "periods", g["periods"])
    print(" players per frame: mean %.2f min %d max %d" % (present.mean(), present.min(), present.max()),
          "distribution", dict(zip(*np.unique(present, return_counts=True))))
    print(" ball visible %.3f" % np.isfinite(ball[:, 0]).mean(), " consistent home/away ball:", g.get("ball_h_a_consistent"),
          " raw events end<start:", g.get("raw_event_end_before_start"))
    print(" ball range", np.nanmin(ball, 0).round(1), np.nanmax(ball, 0).round(1))
    ev = g["events"]
    print(" events", len(ev), "sorted by start:", all(ev[i]["start"] <= ev[i + 1]["start"] for i in range(len(ev) - 1)))
    sp = g["slot_player"]
    for etype in ("PASS", "SHOT"):
        for off in (-2, -1, 0, 1, 2):
            d = []
            for e in ev:
                if e["type"] != etype or e["player"] is None: continue
                f = e["start"] + off
                if not (0 <= f < n): continue
                cols = sp[f] if sp.ndim == 2 else sp
                j = np.flatnonzero(cols == e["player"])
                if j.size and np.isfinite(ball[f, 0]) and np.isfinite(pl[f, j[0], 0]):
                    d.append(np.hypot(*(pl[f, j[0]] - ball[f])))
            if d: print("  sync %s offset %+d n=%d median %.2f p75 %.2f p90 %.2f" % (etype, off, len(d), np.median(d), np.percentile(d, 75), np.percentile(d, 90)))
    for p, a, b in g["periods"]:
        es = [e for e in ev if e["period"] == p]
        print(" period", p, "frames", a, b, "first event", min(e["start"] for e in es), "last end", max(e["end"] for e in es))
        for e in es[-3:]:
            print("    last:", e["team"], e["type"], sorted(e["subs"]), e["start"], e["end"])
    lab = L.build_labels(ev, n, "primary")
    vis = np.isfinite(ball[:, 0])
    for code, nm in ((0, "H"), (1, "A"), (2, "D")):
        m = lab == code
        print(" primary label %s: frames %d  ball visible %.3f" % (nm, m.sum(), vis[m].mean()))
    print(" graded frames", int((lab != 3).sum()), "= %.1f min" % ((lab != 3).sum() / g["fps"] / 60))
    bo = [(e["start"], e["end"]) for e in ev if e["type"] == "BALL OUT"]
    print(" BALL OUT end-start frames: median %.0f p90 %.0f" % (np.median([b - a for a, b in bo]), np.percentile([b - a for a, b in bo], 90)))
