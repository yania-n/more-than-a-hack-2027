"""Labels for the harness: the pilot's rules on a COMMON event vocabulary (CARRY excluded for every game).

Games 1 and 2 have no CARRY events, so the three rules are built from the same classes in all games by
dropping Game 3's CARRY events (PREREGISTRATION.md s.2: primary labels stay identical, S1/S2 change).
"""

import os
import sys

import numpy as np

from .. import data
from ..pilot import labels as pilot_labels

sys.path.insert(0, os.path.join(data.ROOT, "evaluation"))
import possession_metrics as pm  # noqa: E402

RULES = ("primary", "S1", "S2")


def harness_events(game):
    return [e for e in game["events"] if e["type"] != "CARRY"]


def game_labels(game, rule):
    return pilot_labels.build_labels(harness_events(game), len(game["ball"]), rule)


def play_blocks(label_sets):
    """[(half, first, last)] from the graded runs of the labels; identical across rules (asserted)."""
    runs = pm.valid_runs(label_sets["primary"])
    for r, c in label_sets.items():
        assert pm.valid_runs(c) == runs, "graded intervals differ between rules ({})".format(r)
    return [(i + 1, a, b - 1) for i, (a, b) in enumerate(runs)]


def label_stats(codes, fps):
    runs = pm.valid_runs(codes)
    spells = pm.possession_spells(codes, runs)
    dur = np.array([(b - a) / fps for a, b, _ in spells])
    graded = int(np.sum(codes != pm.X))
    alive = int(np.sum((codes == 0) | (codes == 1)))
    minutes = graded / fps / 60.0
    dead = [(b - a) / fps for a, b, k in pm.segments(codes, runs) if k == pm.D]
    allt = pm.transitions(codes, runs)
    direct = [(i, t) for i, t in enumerate(allt) if t[1] in (0, 1) and t[2] in (0, 1)]
    rev = sum(1 for i, t in direct if i + 1 < len(allt) and allt[i + 1][1] == t[2]
              and allt[i + 1][2] == t[1] and allt[i + 1][0] - t[0] <= 3 * fps)
    return dict(graded_minutes=minutes, possessions=len(spells), possessions_per_min=len(spells) / minutes,
                mean_duration_s=float(dur.mean()), median_duration_s=float(np.median(dur)),
                pct_lt_2s=100 * float(np.mean(dur < 2)), D_share_pct=100 * float(np.sum(codes == pm.D)) / graded,
                median_D_stretch_s=float(np.median(dead)) if dead else None,
                home_share_of_alive_pct=100 * float(np.sum(codes == 0)) / max(alive, 1),
                reversal_rate_3s_pct=100 * rev / max(len(direct), 1))
