"""Write the three proxy label files and their sanity report.   python -m possession.pilot.make_labels

Outputs (all under analysis/pilot_game3/): labels_primary.csv, labels_S1.csv, labels_S2.csv,
label_stats.json, label_timeline.png, ending_events.json
"""

import json
import os
import sys

import numpy as np

from .. import data
from . import game3, labels

sys.path.insert(0, os.path.join(data.ROOT, "evaluation"))
import possession_metrics as pm  # noqa: E402

OUT = os.path.join(data.ROOT, "analysis", "pilot_game3")
RULES = ("primary", "S1", "S2")
LETTERS = np.array(["H", "A", "D", "X"])


def write_csv(codes, path):
    with open(path, "w", newline="\n") as handle:
        handle.write("frame,label\n")
        handle.writelines("{},{}\n".format(i, LETTERS[c]) for i, c in enumerate(codes))


def stats(codes):
    runs = pm.valid_runs(codes)
    spells = pm.possession_spells(codes, runs)
    dur = np.array([(b - a) / game3.FPS for a, b, _ in spells])
    graded = int(np.sum(codes != labels.X))
    alive = int(np.sum((codes == 0) | (codes == 1)))
    dead_runs = [(b - a) / game3.FPS for a, b, k in pm.segments(codes, runs) if k == labels.D]
    allt = pm.transitions(codes, runs)
    direct = [t for t in allt if t[1] in (0, 1) and t[2] in (0, 1)]
    rev = sum(1 for i, t in enumerate(allt[:-1]) if t[1] in (0, 1) and t[2] in (0, 1)
              and allt[i + 1][1] == t[2] and allt[i + 1][2] == t[1] and allt[i + 1][0] - t[0] <= 75)
    return dict(valid_runs=[list(map(int, r)) for r in runs], graded_frames=graded,
                graded_minutes=graded / game3.FPS / 60, possessions=len(spells),
                possessions_per_min=len(spells) / (graded / game3.FPS / 60),
                mean_duration_s=float(dur.mean()), median_duration_s=float(np.median(dur)),
                pct_lt_2s=100 * float(np.mean(dur < 2)), D_share_pct=100 * float(np.sum(codes == labels.D)) / graded,
                median_D_stretch_s=float(np.median(dead_runs)) if dead_runs else None,
                home_share_of_alive_pct=100 * float(np.sum(codes == 0)) / alive,
                transitions_per_min=len(allt) / (graded / game3.FPS / 60),
                reversal_rate_3s_pct=100 * rev / max(len(direct), 1), direct_handovers=len(direct))


def main():
    os.makedirs(OUT, exist_ok=True)
    ev = game3.load_events()
    n = game3.half_blocks()[-1][2] + 1
    res = {}
    codes = {}
    for rule in RULES:
        c = labels.build_labels(ev, n, rule)
        codes[rule] = c
        write_csv(c, os.path.join(OUT, "labels_{}.csv".format(rule)))
        res[rule] = stats(c)
    # What ends the dead-ball stretches (primary): type of the first controlling event after each D
    ends = {}
    c = codes["primary"]
    runs = pm.valid_runs(c)
    starts = {}
    for e in ev:
        starts.setdefault(e["start"], []).append(e)
    for a, b, k in pm.segments(c, runs):
        if k == labels.D and b < len(c):
            names = sorted({"{} {}".format(e["type"], ",".join(sorted(e["subs"]))).strip() for e in starts.get(b, [])
                            if labels.classify(e, "primary")[0] in ("ctrl", "ctrl_then_stop")})
            key = " | ".join(names) if names else "(none at that frame)"
            ends[key] = ends.get(key, 0) + 1
    res["dead_stretch_end_events_primary"] = dict(sorted(ends.items(), key=lambda kv: -kv[1]))
    with open(os.path.join(OUT, "label_stats.json"), "w") as handle:
        json.dump(res, handle, indent=1)
    plot(ev, codes)
    for rule in RULES:
        s = res[rule]
        print("%-8s poss %4d (%.2f/min)  mean %.1fs median %.1fs  <2s %.1f%%  D %.1f%%  home %.1f%%  rev %.1f%%" % (
            rule, s["possessions"], s["possessions_per_min"], s["mean_duration_s"], s["median_duration_s"],
            s["pct_lt_2s"], s["D_share_pct"], s["home_share_of_alive_pct"], s["reversal_rate_3s_pct"]))
    print(json.dumps(res["dead_stretch_end_events_primary"], indent=1))


def plot(ev, codes, start=3000, length=7500):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    colors = {0: "#d62728", 1: "#1f77b4", 2: "#999999", 3: "#ffffff"}
    fig, ax = plt.subplots(4, 1, figsize=(16, 7), sharex=True, gridspec_kw={"height_ratios": [1, 1, 1, 2]})
    xs = np.arange(start, start + length)
    for a, rule in zip(ax[:3], RULES):
        c = codes[rule][start:start + length]
        a.imshow(np.array([[matplotlib.colors.to_rgb(colors[v]) for v in c[::5]]]), aspect="auto",
                 extent=[start, start + length, 0, 1])
        a.set_yticks([])
        a.set_ylabel(rule)
    a = ax[3]
    ypos = {"PASS": 0, "CARRY": 1, "SHOT": 2, "RECOVERY": 3, "CHALLENGE": 4, "BALL LOST": 5, "BALL OUT": 6,
            "SET PIECE": 7, "FAULT RECEIVED": 8, "CARD": 9}
    for e in ev:
        if start <= e["start"] < start + length:
            a.plot([e["start"], max(e["end"], e["start"] + 2)], [ypos[e["type"]]] * 2, lw=4,
                   color=colors[e["team"]])
    a.set_yticks(list(ypos.values()))
    a.set_yticklabels(list(ypos.keys()))
    a.set_xlabel("frame (25 Hz); red = home events, blue = away; top: H red, A blue, D grey")
    a.set_xlim(start, start + length)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "label_timeline.png"), dpi=100)
    plt.close(fig)


if __name__ == "__main__":
    main()
