"""Scoring helpers for the pilot: organizers' metric code + a paired bootstrap of the spellF1 difference."""

import os
import sys

import numpy as np

from .. import data

sys.path.insert(0, os.path.join(data.ROOT, "evaluation"))
import possession_metrics as pm  # noqa: E402

KEYS = ("spell_f1_mean", "spell_f1_at_headline", "macro_f1", "alive_dead_f1", "team_acc_gt_alive",
        "team_acc_both_alive", "spell_bootstrap_low", "spell_bootstrap_high", "n_gt_spells", "n_pred_spells")


def half_gt(gt, block):
    """Copy of gt with everything outside one block (a, b inclusive) set to X."""
    out = np.full_like(gt, pm.X)
    a, b = block
    out[a:b + 1] = gt[a:b + 1]
    return out


def evaluate(gt, pred, bootstrap_n):
    r = pm.evaluate(gt, pred, bootstrap_n=bootstrap_n)
    return {k: r[k] for k in KEYS}


def _flags(gt, pred):
    runs = pm.valid_runs(gt)
    filled = pm.fill_abstentions(pred, runs)
    gt_sp, pr_sp = pm.possession_spells(gt, runs), pm.possession_spells(filled, runs)
    ov = pm.spell_overlaps(gt_sp, pr_sp)
    flags = np.vstack([pm.matched_gt_flags(ov, len(gt_sp), t) for t in pm.SPELL_IOUS])
    return flags, len(gt_sp), len(pr_sp)


def _f1(flags, picks, n_gt, n_pred):
    out = []
    for row in flags:
        tp = int(row[picks].sum())
        fn, fp = n_gt - tp, max(0, n_pred - tp)
        out.append(2.0 * tp / (2 * tp + fp + fn) if tp else 0.0)
    return float(np.mean(out))


def paired_bootstrap(gt, pred_a, pred_b, n_draws=1000, seed=0):
    """Resample the ground-truth possessions once per draw and score both predictions on the same
    resample (same matching flags as pm.bootstrap_spell_f1). Returns the difference a - b."""
    fa, n_gt, na = _flags(gt, pred_a)
    fb, _, nb = _flags(gt, pred_b)
    rng = np.random.RandomState(seed)
    diffs = np.empty(n_draws)
    for i in range(n_draws):
        picks = rng.randint(0, n_gt, n_gt)
        diffs[i] = _f1(fa, picks, n_gt, na) - _f1(fb, picks, n_gt, nb)
    lo, hi = np.percentile(diffs, [5, 95])
    return dict(mean_diff=float(diffs.mean()), low90=float(lo), high90=float(hi),
                p_a_better=float(np.mean(diffs > 0)))


def proxies(pred, gt):
    """Label-free possession statistics of a prediction over the ground truth's graded runs."""
    runs = pm.valid_runs(gt)
    filled = pm.fill_abstentions(pred, runs)
    spells = pm.possession_spells(filled, runs)
    minutes = sum(b - a for a, b in runs) / pm.FPS / 60.0
    dur = np.array([(b - a) / pm.FPS for a, b, _ in spells])
    allt = pm.transitions(filled, runs)
    direct = [(i, t) for i, t in enumerate(allt) if t[1] in (0, 1) and t[2] in (0, 1)]
    rev = sum(1 for i, t in direct if i + 1 < len(allt) and allt[i + 1][1] == t[2]
              and allt[i + 1][2] == t[1] and allt[i + 1][0] - t[0] <= 75)
    graded = sum(b - a for a, b in runs)
    ds = sum(1 for a, b in runs for x in filled[a:b] if x == pm.D)
    return dict(possessions_per_min=len(spells) / minutes, median_possession_s=float(np.median(dur)),
                pct_lt_2s=100 * float(np.mean(dur < 2)), reversal_rate_3s_pct=100 * rev / max(len(direct), 1),
                D_share_pct=100 * ds / graded)
