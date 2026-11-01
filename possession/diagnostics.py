"""Label-free quality numbers for a label array, computed identically for every submission.

Uses the organisers' own segment/transition code (evaluation/possession_metrics.py) so that a
"possession" means exactly what the scorer means. No ground truth is read.

Codes: 0 H, 1 A, 2 D, 3 X (as in possession_metrics).
"""

import os
import sys

import numpy as np

from . import data, features

sys.path.insert(0, os.path.join(data.ROOT, "evaluation"))
import possession_metrics as pm  # noqa: E402

FPS = data.FPS
SHORT_S = 2.0          # "short possession" threshold used in the comparison table
REVERSAL_S = 3.0       # a team regains the ball within this long => reversal
RESTART_TOL_S = 2.0    # restart agreement tolerance
PLAUSIBLE_WINDOW_S = (1.0, 2.0)


def read_codes(path):
    return pm.label_codes(pm.read_label_csv(path))


def graded_runs():
    fake = np.where(data.graded_mask(), 0, 3).astype(np.int8)
    return pm.valid_runs(fake)


def _direct_handovers(codes, runs):
    """[(frame, from_team, to_team)] H<->A changes with no D in between, plus all transitions."""
    allt = pm.transitions(codes, runs)
    return allt, [t for t in allt if t[1] in (0, 1) and t[2] in (0, 1)]


def reversal_rate(allt, runs_frames=REVERSAL_S * FPS):
    """Share of direct hand-overs followed by a direct hand-back within REVERSAL_S."""
    direct = [(i, t) for i, t in enumerate(allt) if t[1] in (0, 1) and t[2] in (0, 1)]
    if not direct:
        return float("nan")
    rev = 0
    for i, (f, a, b) in direct:
        if i + 1 < len(allt):
            f2, a2, b2 = allt[i + 1]
            if a2 == b and b2 == a and f2 - f <= runs_frames:
                rev += 1
    return rev / len(direct)


def handover_plausibility(codes, sig, allt):
    """Share of direct hand-overs whose new team still has the nearest player within the control
    radius for at least half of the visible-ball frames 1-2 s later (needs >= 1 visible frame)."""
    lo, hi = [int(s * FPS) for s in PLAUSIBLE_WINDOW_S]
    R = sig["radius"]
    ok, judged = 0, 0
    for f, a, b in allt:
        if not (a in (0, 1) and b in (0, 1)):
            continue
        win = np.arange(f + lo, min(f + hi + 1, len(codes)))
        win = win[sig["vis"][win] & np.isfinite(sig["gap_all"][win])]
        if len(win) == 0:
            continue
        mine = sig["dH"] if b == 0 else sig["dA"]
        other = sig["dA"] if b == 0 else sig["dH"]
        good = (mine[win] <= other[win]) & (mine[win] <= R)
        judged += 1
        ok += int(good.mean() >= 0.5)
    return (ok / judged if judged else float("nan")), judged


def summarise(codes, sig, set_pieces):
    runs = graded_runs()
    n_graded = int(data.graded_mask().sum())
    minutes = n_graded / FPS / 60.0
    spells = pm.possession_spells(codes, runs)
    dur = np.array([(b - a) / FPS for a, b, _ in spells])
    allt, direct = _direct_handovers(codes, runs)
    segs = pm.segments(codes, runs)
    dead = np.array([(b - a) / FPS for a, b, k in segs if k == 2])
    graded = data.graded_mask()
    alive = int(np.sum(graded & ((codes == 0) | (codes == 1))))
    plaus, judged = handover_plausibility(codes, sig, allt)

    ends = np.array([b for a, b, k in segs if k == 2])
    tol = RESTART_TOL_S * FPS
    starts = [e["start_frame"] for e in set_pieces
              if e["type"] in features.RESTART_TYPES and graded[min(e["start_frame"], len(graded) - 1)]]
    hit = sum(int(len(ends) > 0 and np.min(np.abs(ends - s)) <= tol) for s in starts)
    near_d = sum(int(np.any(codes[max(0, s - int(tol)):s + int(tol) + 1] == 2)) for s in starts)

    out_frames = graded & sig["vis"] & (sig["beyond"] > features.OUTSIDE_MARGIN)
    return {
        "possessions": len(spells),
        "possessions_per_min": len(spells) / minutes,
        "median_possession_s": float(np.median(dur)) if len(dur) else float("nan"),
        "pct_possessions_lt_2s": 100.0 * float(np.mean(dur < SHORT_S)) if len(dur) else float("nan"),
        "transitions_per_min": len(allt) / minutes,
        "reversal_rate_3s_pct": 100.0 * reversal_rate(allt),
        "D_share_pct": 100.0 * float(np.sum(graded & (codes == 2))) / n_graded,
        "median_D_stretch_s": float(np.median(dead)) if len(dead) else float("nan"),
        "restart_D_end_within_2s_pct": 100.0 * hit / max(len(starts), 1),
        "restart_any_D_within_2s_pct": 100.0 * near_d / max(len(starts), 1),
        "n_restarts_graded": len(starts),
        "ball_outside_labelled_D_pct": 100.0 * float(np.mean(codes[out_frames] == 2)),
        "n_ball_outside_frames": int(out_frames.sum()),
        "handover_plausible_pct": 100.0 * plaus,
        "n_handovers_judged": judged,
        "n_direct_handovers": len(direct),
        "home_share_of_alive_pct": 100.0 * float(np.sum(graded & (codes == 0))) / max(alive, 1),
    }
