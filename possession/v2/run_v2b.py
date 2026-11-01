"""v2b: v1 + glitch exclusion (>35 m/s) + touch evidence.   python -m possession.v2.run_v2b [pct tag]

Built on v1 (v2a did not help, PREREGISTRATION.md section 3). The flight gate stays at 6.44 m/s
because the ball-speed histogram has no valley to justify another one (gate_touch.json); the only
change to the gate is that speeds above 35 m/s are treated as tracking glitches. Touch evidence is a
mirror-tied team feature {away, none, home}, untempered (see the 2026-11-01 note).
Default registered run: pct = 99 -> submissions/hmm_v2b.csv. A sensitivity run is labelled as such.
"""

import json
import os
import sys

import numpy as np

from .. import data, features, hmm, run
from ..hmm import FeatureSpec
from . import gate_touch, run_v2a, tempered

OUT = os.path.join(data.ROOT, "analysis", "hmm_v2")


def regate(sig, speed):
    """Recompute the gap/dwell evidence with the extra glitch exclusion (all else as in v1)."""
    s = dict(sig)
    glitch = sig["vis"] & (speed > gate_touch.GLITCH_SPEED)
    eligible = sig["vis"] & ~sig["flight"] & ~glitch & np.isfinite(sig["gap_all"]) & (sig["gap_all"] != 0)
    side = np.where(sig["dmin"] <= sig["radius"], np.sign(sig["gap_all"]), 0.0)
    dwell = np.zeros(len(side))
    run_len, prev = 0, 0
    for t in np.flatnonzero(sig["vis"] & np.isfinite(sig["gap_all"])):
        sd = int(side[t])
        run_len = (run_len + 1 if sd == prev else 1) if sd != 0 else 0
        prev = sd
        dwell[t] = sd * run_len
    dwell[~eligible] = np.nan
    s["gap"] = np.where(eligible, sig["gap_all"], np.nan)
    s["dwell"] = dwell
    return s, int(np.sum(glitch & sig["graded"]))


def touch_column(halves, sig, dv, sign):
    obs = (sig["vis"] & np.isfinite(dv)).astype(float)
    cols, scores = [], []
    for h in halves:
        a, b = h["start"], h["end"]
        o = features._blocks(np.where(obs > 0, 1.0, np.nan), a, b)
        has = np.isfinite(o).any(axis=1)
        net = np.nansum(features._blocks(sign, a, b), axis=1)
        cat = np.where(has, 1 + np.sign(net).astype(int), -1)
        cols.append(cat)
        scores.append(np.where(has, net, np.nan))
    return cols, scores


def build(atd, sig, pct):
    speed, dv, _ = gate_touch.kinematics(atd["ball"])
    sig2, n_glitch = regate(sig, speed)
    seqs, specs, halves, edges = features.build(sig2)
    ev, thr, sign = gate_touch.touch_events(sig, dv, pct)
    cols, scores = touch_column(halves, sig, dv, sign)
    seqs = [np.concatenate([s, c[:, None]], axis=1) for s, c in zip(seqs, cols)]
    specs = specs + [FeatureSpec("touch", 3, "team")]
    return seqs, specs, halves, edges, scores, dict(n_glitch_frames=n_glitch, n_touches=int(len(ev)), touch_thr=thr)


def main(pct=99.0, tag="hmm_v2b"):
    os.makedirs(OUT, exist_ok=True)
    atd = data.load_atd()
    v1 = run.fit_model(verbose=False)
    seqs, specs, halves, edges, touch_scores, info = build(atd, v1["sig"], pct)
    rho = tempered.residual_acf(touch_scores, v1["paths"])
    info["touch_tau_for_information"] = tempered.integrated_tau(rho)
    stay = [s * data.FPS / features.BLOCK for s in run.PRIOR_DWELL_S]
    params = hmm.fit(seqs, specs, stay, verbose=False)
    paths = hmm.decode(seqs, params)
    labels = np.array(["H", "A", "D", "X"])[features.upsample(paths, halves)]
    run.write_submission(labels, os.path.join(data.ROOT, "submissions", tag + ".csv"))
    step_s = features.BLOCK / data.FPS
    res = dict(info=info, pct=pct, A=params["A"].tolist(), sojourn_s=(step_s / (1 - np.diag(params["A"]))).tolist(),
               iters=len(params["history"]), converged=bool(params["converged"]),
               touch_emission=params["emis"][-1].tolist(),
               counts={s: int(np.sum(labels == s)) for s in "HADX"})
    with open(os.path.join(OUT, tag + ".json"), "w") as handle:
        json.dump(res, handle, indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    if len(sys.argv) > 2:
        main(float(sys.argv[1]), sys.argv[2])
    else:
        main()
