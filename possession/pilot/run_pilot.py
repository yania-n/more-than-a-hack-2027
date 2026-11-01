"""Run the pilot: smooth50 vs v1 on Game 3 under 3 label rules x 3 ball conditions.
    python -m possession.pilot.run_pilot        (stage 1: predictions, stage 2: scoring)

Everything is registered in analysis/pilot_game3/PREREGISTRATION.md. Outputs under analysis/pilot_game3/.
"""

import hashlib
import json
import os
import pickle

import numpy as np

from .. import data
from . import adapters, game3, labels, score
from .make_labels import LETTERS, RULES, write_csv

OUT = os.path.join(data.ROOT, "analysis", "pilot_game3")
PRED = os.path.join(OUT, "predictions")
RAW = os.path.join(OUT, "raw")
CONDITIONS = ("asis", "degraded_seed0", "degraded_seed1")
METHODS = ("smooth50", "v1_refit", "v1_transfer")
SIGMA_BALL = 0.07          # m: v3's measured upper bound for the provided ATD (brief, step 4)
BOOT = 1000


def md5(path):
    return hashlib.md5(open(path, "rb").read()).hexdigest()


def reference_from_provided():
    """v1 constants, bin edges and EM parameters fitted on the provided match, + the ball statistics
    used to degrade Game 3 (unlabeled aggregates of the provided tracking)."""
    atd = data.load_atd()
    blocks, sps, pitch = data.graded_blocks(), data.load_set_pieces(), data.PITCH.copy()
    r = adapters.run_v1(atd, blocks, sps, pitch, mode="refit")
    vis = np.isfinite(atd["ball"][:, 0])
    vis_runs, gap_runs = adapters.graded_runs(vis, blocks)
    g = data.graded_mask()
    pack = dict(radius=r["radius"], carry=r["carry"], edges=r["edges"], params=r["params"])
    stats = dict(visible_share=float(vis[g].mean()), n_gaps=int(len(gap_runs)),
                 gap_len_pct=np.percentile(gap_runs, [10, 25, 50, 75, 90, 99]).tolist(),
                 gap_len_mean=float(gap_runs.mean()), vis_run_mean=float(vis_runs.mean()))
    return pack, gap_runs, stats


def stage1():
    os.makedirs(PRED, exist_ok=True)
    os.makedirs(RAW, exist_ok=True)
    pack, gap_runs, pstats = reference_from_provided()
    t = game3.load_tracking()
    players, ball0 = t["players"], t["ball"]
    team = t["team"]
    pspeed = adapters.derive_pspeed(players)
    n = len(ball0)
    ev = game3.load_events()
    gt = {rule: labels.build_labels(ev, n, rule) for rule in RULES}
    from .. import data as _d
    import sys
    sys.path.insert(0, os.path.join(_d.ROOT, "evaluation"))
    import possession_metrics as pm
    runs = pm.valid_runs(gt["primary"])
    assert all(pm.valid_runs(gt[r]) == runs for r in RULES), "graded intervals differ between rules"
    blocks = [(i + 1, a, b - 1) for i, (a, b) in enumerate(runs)]
    info = dict(provided_ball=pstats, play_blocks=blocks, degraded={})
    preds = {}
    for cond in CONDITIONS:
        if cond == "asis":
            ball = ball0
        else:
            seed = int(cond[-1])
            ball, dinfo = adapters.degrade_ball(ball0, blocks, gap_runs, pstats["visible_share"], SIGMA_BALL, seed)
            info["degraded"][cond] = dinfo
        g = np.zeros(n, dtype=bool)
        for _, a, b in blocks:
            g[a:b + 1] = True
        info.setdefault("ball_visible_share", {})[cond] = float(np.isfinite(ball[g, 0]).mean())
        atd = dict(ball=ball, players=players, pspeed=pspeed, team=team)
        raw_path = os.path.join(RAW, "game3_{}.txt".format(cond))
        adapters.write_raw_atd_like(raw_path, players, ball, game3.PITCH)
        preds[(cond, "smooth50")] = adapters.smooth50_codes(raw_path, team, n, tuple(game3.PITCH))
        r = adapters.run_v1(atd, blocks, [], game3.PITCH, mode="refit", setpiece_missing=True)
        preds[(cond, "v1_refit")] = r["codes"]
        info.setdefault("game3_v1_constants", {})[cond] = dict(radius=float(r["radius"]), carry=float(r["carry"]))
        preds[(cond, "v1_transfer")] = adapters.run_v1(atd, blocks, [], game3.PITCH, mode="transfer", ref=pack,
                                                       setpiece_missing=True)["codes"]
        os.remove(raw_path)          # derived tracking export: do not leave it lying around
        print("stage 1 done for", cond, flush=True)
    md5s = {}
    for (cond, m), c in preds.items():
        path = os.path.join(PRED, "{}_{}.csv".format(m, cond))
        write_csv(c, path)
        md5s["{}_{}".format(m, cond)] = md5(path)
    for rule in RULES:
        md5s["labels_" + rule] = md5(os.path.join(OUT, "labels_{}.csv".format(rule)))
    info["md5"] = md5s
    with open(os.path.join(OUT, "stage1.json"), "w") as handle:
        json.dump(info, handle, indent=1)
    with open(os.path.join(PRED, "preds.pkl"), "wb") as handle:
        pickle.dump(dict(preds=preds, gt=gt, blocks=blocks), handle)
    return preds, gt, blocks, info


def stage2(preds, gt, blocks):
    table, boot, prox = {}, {}, {}
    for rule in RULES:
        for cond in CONDITIONS:
            for m in METHODS:
                p = preds[(cond, m)]
                cell = {"whole": score.evaluate(gt[rule], p, BOOT)}
                for h, (_, a, b) in enumerate(blocks, start=1):
                    cell["half%d" % h] = score.evaluate(score.half_gt(gt[rule], (a, b)), p, 0)
                table["{}|{}|{}".format(rule, cond, m)] = cell
            for other in ("v1_refit", "v1_transfer"):
                boot["{}|{}|{}-smooth50".format(rule, cond, other)] = score.paired_bootstrap(
                    gt[rule], preds[(cond, other)], preds[(cond, "smooth50")], BOOT, 0)
        print("stage 2 done for rule", rule, flush=True)
    for cond in CONDITIONS:
        for m in METHODS:
            prox["{}|{}".format(cond, m)] = score.proxies(preds[(cond, m)], gt["primary"])
    return table, boot, prox


def verdict(table, boot):
    cells, diffs = [], {}
    for rule in RULES:
        for cond in CONDITIONS:
            d = {s: table["%s|%s|v1_refit" % (rule, cond)][s]["spell_f1_mean"]
                 - table["%s|%s|smooth50" % (rule, cond)][s]["spell_f1_mean"] for s in ("whole", "half1", "half2")}
            diffs["%s|%s" % (rule, cond)] = d
            cells.append(d)
    all_pos = all(v > 0 for d in cells for v in d.values())
    all_neg = all(v < 0 for d in cells for v in d.values())
    b = boot["primary|asis|v1_refit-smooth50"]
    excl = b["low90"] > 0 or b["high90"] < 0
    leaning = "v1" if sum(d["whole"] for d in cells) > 0 else "smooth50"
    if all_pos and excl:
        v = "v1 wins"
    elif all_neg and excl:
        v = "smooth50 wins"
    else:
        v = "no clear winner (leaning %s%s)" % (leaning, ", signs agree in every cell but interval includes 0"
                                                  if (all_pos or all_neg) else "; signs disagree in some cells")
    return dict(verdict=v, all_positive=all_pos, all_negative=all_neg, primary_asis_interval_excludes_0=excl,
                diffs=diffs)


def main():
    cache = os.path.join(PRED, "preds.pkl")
    if os.environ.get("PILOT_REUSE") and os.path.isfile(cache):
        d = pickle.load(open(cache, "rb"))
        preds, gt, blocks = d["preds"], d["gt"], d["blocks"]
        info = json.load(open(os.path.join(OUT, "stage1.json")))
    else:
        preds, gt, blocks, info = stage1()
    table, boot, prox = stage2(preds, gt, blocks)
    v = verdict(table, boot)
    with open(os.path.join(OUT, "results.json"), "w") as handle:
        json.dump(dict(table=table, paired_bootstrap=boot, proxies=prox, verdict=v, stage1=info), handle, indent=1)
    print(json.dumps(v, indent=1))


if __name__ == "__main__":
    main()
