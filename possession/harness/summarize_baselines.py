"""Summarise a harness results.json: spellF1 per method, per game, pooled, and where each method wins.

    python -m possession.harness.summarize_baselines analysis/harness_baselines

Writes <dir>/summary.md and prints it. Descriptive only: the harness' pre-registered decision rule is in
results.json["decisions"]. Picking the best baseline window on three games is itself a selection on those
games, so read the margins, not just the winner.
"""

import json
import os
import sys
from collections import Counter

import numpy as np

ORDER = ["raw", "smooth25", "smooth50", "smooth125", "v1_refit", "v1_transfer"]
RULES = ["primary", "S1", "S2"]
COND_ORDER = ["asis", "degraded_seed0", "degraded_seed1", "leakfree_seed0", "leakfree_seed1"]


def load(folder):
    with open(os.path.join(folder, "results.json")) as handle:
        return json.load(handle)


def parse(table):
    games, rules, conds, methods = set(), set(), set(), set()
    for key in table:
        g, r, c, m = key.split("|")
        games.add(g), rules.add(r), conds.add(c), methods.add(m)
    methods = [m for m in ORDER if m in methods] + sorted(m for m in methods if m not in ORDER)
    conds = [c for c in COND_ORDER if c in conds] + sorted(c for c in conds if c not in COND_ORDER)
    rules = [r for r in RULES if r in rules] + sorted(r for r in rules if r not in RULES)
    return sorted(games), rules, conds, methods


def val(table, g, r, c, m, key="spell_f1_mean"):
    return table["%s|%s|%s|%s" % (g, r, c, m)]["whole"][key]


def md_table(header, rows, bold_best=None):
    """rows: list of (label, [floats]); bold the max of each column when bold_best is set."""
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] + ["---:"] * (len(header) - 1)) + "|"]
    ncol = len(header) - 1
    nbold = ncol if bold_best is True else int(bold_best or 0)      # bold only the first nbold columns
    best = [max(r[1][j] for r in rows) if j < nbold else None for j in range(ncol)]
    for label, vals in rows:
        cells = []
        for j, v in enumerate(vals):
            s = "%.3f" % v
            cells.append("**%s**" % s if best[j] is not None and abs(v - best[j]) < 1e-12 else s)
        out.append("| " + " | ".join([label] + cells) + " |")
    return out


def main(argv=None):
    folder = (argv or sys.argv[1:] or ["analysis/harness_baselines"])[0]
    res = load(folder)
    t = res["table"]
    games, rules, conds, methods = parse(t)
    base_conds = [c for c in conds if c in ("asis", "degraded_seed0", "degraded_seed1")]
    lines = ["# Baselines vs v1 on the three Metrica sample games", "",
             "Methods: %s. Games: %s. spellF1 = mean over IoU 0.3-0.7 (the ranking metric), whole game." %
             (", ".join(methods), ", ".join(games)), ""]

    # 1. pooled spellF1 for every (rule, condition): equal-weight mean of the games' whole-game spellF1
    cols = [(r, c) for r in rules for c in base_conds]
    pooled = {m: [float(np.mean([val(t, g, r, c, m) for g in games])) for r, c in cols] for m in methods}
    lines += ["## 1. Pooled spellF1 (equal-weight mean of the games), by label rule and ball condition", ""]
    lines += md_table(["method"] + ["%s / %s" % (r, c) for r, c in cols], [(m, pooled[m]) for m in methods], True)
    overall = {m: float(np.mean(pooled[m])) for m in methods}
    ranked = sorted(methods, key=lambda m: -overall[m])
    lines += ["", "Mean over all %d columns: %s." % (
        len(cols), ", ".join("%s %.3f" % (m, overall[m]) for m in ranked)),
        "**Highest pooled spellF1: %s (%.3f), ahead of %s (%.3f) by %.3f.**" % (
            ranked[0], overall[ranked[0]], ranked[1], overall[ranked[1]], overall[ranked[0]] - overall[ranked[1]]), ""]

    # 2. per game, primary rule, as-is, with each method's own bootstrap interval
    lines += ["## 2. Per game, primary rule, ball as-is (5-95% bootstrap over the game's possessions)", ""]
    header = ["method"] + games
    rows = [["| " + " | ".join(header) + " |", "|---|" + "---:|" * len(games)]][0]
    best_g = {g: max(val(t, g, "primary", "asis", m) for m in methods) for g in games}
    for m in methods:
        cells = []
        for g in games:
            w = t["%s|primary|asis|%s" % (g, m)]["whole"]
            s = "%.3f [%.3f, %.3f]" % (w["spell_f1_mean"], w["spell_bootstrap_low"], w["spell_bootstrap_high"])
            cells.append("**%s**" % s if abs(w["spell_f1_mean"] - best_g[g]) < 1e-12 else s)
        rows.append("| " + " | ".join([m] + cells) + " |")
    lines += rows + ["", "Per-method intervals overlap whenever two methods are close; the harness' paired intervals "
                         "(results.json, `paired` and `pooled`) are the sharper test.", ""]

    # 3. where each method wins (27 cells)
    wins, cells_all = Counter(), []
    for g in games:
        for r in rules:
            for c in base_conds:
                scores = {m: val(t, g, r, c, m) for m in methods}
                w = max(scores, key=scores.get)
                wins[w] += 1
                cells_all.append((g, r, c, w))
    lines += ["## 3. Which method has the highest spellF1 in each game x rule x condition cell (%d cells)" %
              len(cells_all), ""]
    lines += md_table(["method", "cells won"], [(m, [float(wins.get(m, 0))]) for m in methods])
    lines[-len(methods):] = [l.replace(".000 |", " |") for l in lines[-len(methods):]]
    lines += ["", "Winner by game (primary rule, as-is): " +
              ", ".join("%s: %s" % (g, max(methods, key=lambda m: val(t, g, "primary", "asis", m))) for g in games), ""]

    # 4. components, primary rule, as-is, pooled
    lines += ["## 4. Where each method wins: component metrics (primary rule, ball as-is, mean of the games)", ""]
    comp_keys = [("spell_f1_mean", "spellF1"), ("macro_f1", "macroF1"), ("alive_dead_f1", "alive/dead F1"),
                 ("team_acc_both_alive", "team acc (both alive)")]
    crow = []
    for m in methods:
        vals = [float(np.mean([val(t, g, "primary", "asis", m, k) for g in games])) for k, _ in comp_keys]
        ratio = float(np.mean([t["%s|primary|asis|%s" % (g, m)]["whole"]["n_pred_spells"] /
                               t["%s|primary|asis|%s" % (g, m)]["whole"]["n_gt_spells"] for g in games]))
        crow.append((m, vals + [ratio]))
    lines += md_table(["method"] + [n for _, n in comp_keys] + ["predicted / real possessions"], crow, len(comp_keys))
    lines += ["", "(The last column should be near 1.00; the best value there is the closest to 1, not the highest.)", ""]

    lines += ["## Caveats", "",
              "- Labels are proxies built from event data, not the competition's ground truth.",
              "- The ball is blank during stoppages in all three games, which flatters rules that read a missing "
              "ball as dead ball (the baselines); the provided match is not like that.",
              "- Choosing the best window on three games selects on those games; the organizers' own full-match "
              "numbers rank the windows differently from their public window.", ""]
    text = "\n".join(lines)
    with open(os.path.join(folder, "summary.md"), "w") as handle:
        handle.write(text)
    print(text)


if __name__ == "__main__":
    main()
