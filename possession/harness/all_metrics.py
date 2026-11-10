"""Every metric of evaluation/possession_metrics.py for each method on the sample games.

Reads the labels and predictions a harness run saved (<dir>/labels, <dir>/predictions) and calls
possession_metrics.evaluate() on each game x rule x ball-condition cell. Writes <dir>/all_metrics.md
and <dir>/all_metrics.json. Equal-weight mean over games (counts are summed). Own work; the
organisers' scorer is imported, not modified.

    python -m possession.harness.all_metrics analysis/harness_baselines
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "evaluation"))
import possession_metrics as pm  # noqa: E402

METHODS = ["raw", "smooth25", "smooth50", "smooth125", "v1_refit", "v1_transfer"]
GAMES = ["game1", "game2", "game3"]
RULES = ["primary", "S1", "S2"]
CONDS = ["asis", "degraded_seed0", "degraded_seed1"]


def codes(path):
    return pm.label_codes(pm.read_label_csv(path))


def flat(res):
    d = {k: res[k] for k in ("macro_f1", "spell_f1_mean", "spell_f1_at_headline", "accuracy", "kappa",
                             "alive_dead_f1", "team_acc_gt_alive", "team_acc_both_alive", "share_err",
                             "n_gt_spells", "n_pred_spells", "spell_count_error", "mean_spell_duration_s",
                             "gt_mean_spell_duration_s", "n_gt_segments", "n_pred_segments", "fragmentation",
                             "n_abstain_on_graded", "n_graded")}
    for iou, v in res["spell_f1"].items():
        d["spellF1@%s" % iou] = v["f1"]
    for name, v in res["per_class"].items():
        d["F1_" + name] = v["f1"]
        d["P_" + name] = v["precision"]
        d["R_" + name] = v["recall"]
    for tol, v in res["transitions"].items():
        for k in ("precision", "recall", "f1", "mean_abs_latency", "n_spurious", "n_missed"):
            d["trans%s_%s" % (tol, k)] = v[k]
    return d


def mean(vals):
    vals = [v for v in vals if v is not None and not (isinstance(v, float) and np.isnan(v))]
    return float(np.mean(vals)) if vals else None


def main(out):
    cells = {}
    for g in GAMES:
        for r in RULES:
            gt = codes(os.path.join(out, "labels", "%s_%s.csv" % (g, r)))
            for c in CONDS:
                for m in METHODS:
                    p = os.path.join(out, "predictions", "%s_%s_%s.csv" % (g, c, m))
                    cells[(g, r, c, m)] = flat(pm.evaluate(gt, codes(p), bootstrap_n=0))
        print("done", g, flush=True)
    keys = list(next(iter(cells.values())))

    def agg(sel):
        res = {}
        for m in METHODS:
            rows = [v for (g, r, c, mm), v in cells.items() if mm == m and sel(g, r, c)]
            res[m] = {k: mean([x[k] for x in rows]) for k in keys}
        return res

    views = {
        "primary rule, ball as-is": agg(lambda g, r, c: r == "primary" and c == "asis"),
        "primary rule, mean of 3 ball conditions": agg(lambda g, r, c: r == "primary"),
        "mean of all 9 columns (3 rules x 3 conditions)": agg(lambda g, r, c: True),
        "S1 (strict) rule, ball as-is": agg(lambda g, r, c: r == "S1" and c == "asis"),
        "S2 (loose) rule, ball as-is": agg(lambda g, r, c: r == "S2" and c == "asis"),
    }
    json.dump({"views": views}, open(os.path.join(out, "all_metrics.json"), "w"), indent=1)

    groups = [
        ("Ranking metrics", ["spell_f1_mean", "macro_f1"]),
        ("Spell F1 per IoU threshold", ["spellF1@%s" % i for i in pm.SPELL_IOUS]),
        ("Frame level", ["accuracy", "kappa", "alive_dead_f1", "team_acc_gt_alive", "team_acc_both_alive",
                         "F1_H", "F1_A", "F1_D", "share_err"]),
        ("Possession structure (real count is the target)", ["n_gt_spells", "n_pred_spells", "spell_count_error",
                                                              "mean_spell_duration_s", "gt_mean_spell_duration_s",
                                                              "fragmentation"]),
        ("Transitions, tau = %s frames" % (pm.TAUS[0],), ["trans%s_%s" % (pm.TAUS[0], k) for k in
                                                         ("precision", "recall", "f1", "mean_abs_latency")]),
        ("Transitions, tau = %s frames" % (pm.TAUS[1],), ["trans%s_%s" % (pm.TAUS[1], k) for k in
                                                         ("precision", "recall", "f1", "mean_abs_latency")]),
    ]
    lower_better = {"share_err", "spell_count_error", "fragmentation", "mean_abs_latency"}
    lines = ["# All organiser metrics: baselines vs v1 on the three Metrica sample games", "",
             "Each number is the equal-weight mean over games 1-3 (and over the columns named in the heading). "
             "Best value per row in bold; for count/error rows the best is the one closest to the target. "
             "Labels are event-derived proxies, not the competition ground truth.", ""]
    for vname, res in views.items():
        lines += ["## " + vname, ""]
        for gname, ks in groups:
            lines += ["**%s**" % gname, "", "| metric | " + " | ".join(METHODS) + " |",
                      "|---|" + "---:|" * len(METHODS)]
            for k in ks:
                vals = [res[m][k] for m in METHODS]
                if any(v is None for v in vals):
                    cells_txt = ["n/a" if v is None else "%.3f" % v for v in vals]
                    lines.append("| %s | %s |" % (k, " | ".join(cells_txt)))
                    continue
                if k == "spell_count_error" or k == "share_err":
                    best = int(np.argmin([abs(v) for v in vals]))
                elif k == "n_pred_spells":
                    best = int(np.argmin([abs(v - res["raw"]["n_gt_spells"]) for v in vals]))
                elif k == "mean_spell_duration_s":
                    best = int(np.argmin([abs(v - res["raw"]["gt_mean_spell_duration_s"]) for v in vals]))
                elif k in ("n_gt_spells", "gt_mean_spell_duration_s"):
                    best = None
                elif k == "fragmentation" or k.endswith("mean_abs_latency"):
                    best = int(np.argmin(vals))
                else:
                    best = int(np.argmax(vals))
                txt = []
                for i, v in enumerate(vals):
                    s = "%.3f" % v if abs(v) < 100 else "%.0f" % v
                    txt.append("**%s**" % s if best == i else s)
                lines.append("| %s | %s |" % (k, " | ".join(txt)))
            lines.append("")
    # win count over all single cells for the two ranking metrics
    for k in ("spell_f1_mean", "macro_f1"):
        wins = {m: 0 for m in METHODS}
        for g in GAMES:
            for r in RULES:
                for c in CONDS:
                    wins[max(METHODS, key=lambda m: cells[(g, r, c, m)][k])] += 1
        lines.append("Cells won on %s (of 27): %s" % (k, ", ".join("%s %d" % (m, w) for m, w in wins.items())))
        lines.append("")
    open(os.path.join(out, "all_metrics.md"), "w").write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "analysis/harness_baselines")
