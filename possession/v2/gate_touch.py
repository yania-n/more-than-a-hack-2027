"""Flight-gate and touch analysis for v2b. Unlabeled statistics only (PREREGISTRATION.md section 5).

    python -m possession.v2.gate_touch   ->  analysis/hmm_v2/gate_touch.json, gate_touch.png
"""

import json
import os
import warnings

import numpy as np

from .. import data, features

W = features.FLIGHT_W
DT = W / data.FPS                       # seconds spanned by one half-window
GLITCH_SPEED = 35.0                     # m/s: about the fastest professional strike; above = tracking glitch
FREE_BALL_DIST = 5.0                    # m: nobody this close => the ball cannot have been touched
TOUCH_PCT = 99.0                        # registered reference percentile (sensitivity: 95 / 99.9)
SPEED_THRESHOLDS = (6.44, 10.0, 15.0, 25.0, 35.0)


def kinematics(ball):
    """Per-frame ball speed (+-W), velocity change |dv| across t, and the second-difference residual."""
    n = len(ball)
    speed = np.full(n, np.nan)
    dv = np.full(n, np.nan)
    accel = np.full((n, 2), np.nan)
    before = (ball[W:-W] - ball[:-2 * W]) / DT
    after = (ball[2 * W:] - ball[W:-W]) / DT
    speed[W:-W] = np.hypot(*(ball[2 * W:] - ball[:-2 * W]).T) / (2 * DT)
    dv[W:-W] = np.hypot(*(after - before).T)
    accel[W:-W] = ball[2 * W:] - 2 * ball[W:-W] + ball[:-2 * W]
    return speed, dv, accel


def noise_floor(accel, graded):
    """Position-noise sigma (m) from the second difference (robust, an upper bound: real
    accelerations are included) and the speed noise it implies for the +-W speed estimate."""
    a = accel[graded]
    a = a[np.isfinite(a).all(1)]
    mad = np.median(np.abs(a - np.median(a, axis=0)), axis=0) / 0.6745   # per axis
    sigma = float(np.mean(mad) / np.sqrt(6.0))
    return sigma, sigma * np.sqrt(2.0) / (2 * DT)


def find_antimode(speed_vis, lo=3.0, hi=15.0, nb=60):
    """Valley of the smoothed log10 ball-speed histogram inside [lo, hi] m/s, or None.

    A valley counts only if its density is below 80% of the smaller flanking peak (peaks searched
    in [0.3, 35] m/s). Decided by the histogram alone.
    """
    x = np.log10(speed_vis[(speed_vis > 0.3) & (speed_vis < GLITCH_SPEED)])
    h, e = np.histogram(x, bins=nb, range=(np.log10(0.3), np.log10(GLITCH_SPEED)))
    hs = np.convolve(h, np.ones(5) / 5.0, mode="same")
    c = 0.5 * (e[1:] + e[:-1])
    inside = np.flatnonzero((10 ** c >= lo) & (10 ** c <= hi))
    # local minima of the smoothed histogram inside the window
    cand = [i for i in inside if 0 < i < nb - 1 and hs[i] < hs[i - 1] and hs[i] <= hs[i + 1]]
    best = None
    for i in cand:
        left, right = hs[:i].max(), hs[i + 1:].max()
        depth = hs[i] / min(left, right)
        if depth < 0.8 and (best is None or depth < best[1]):
            best = (float(10 ** c[i]), float(depth))
    return best, (c, h, hs)


def touch_events(sig, dv, pct=TOUCH_PCT, thr=None):
    """Frames where the ball's velocity changes sharply with a player within the control radius.

    Threshold = pct-th percentile of |dv| over graded frames where nobody is within FREE_BALL_DIST.
    Candidates are thinned by non-maximum suppression within +-W frames so a single touch gives one
    event. Returns (event_frames, thr, sign array +1 home / -1 away at event frames).
    """
    g = sig["graded"]
    ok = g & np.isfinite(dv) & sig["vis"]
    free = ok & (sig["dmin"] > FREE_BALL_DIST)
    if thr is None:
        thr = float(np.percentile(dv[free], pct))
    cand = ok & (dv > thr) & (sig["dmin"] <= sig["radius"])
    idx = np.flatnonzero(cand)
    keep = []
    for t in idx:
        lo, hi = max(0, t - W), min(len(dv), t + W + 1)
        window = np.where(cand[lo:hi], dv[lo:hi], -np.inf)
        if dv[t] >= window.max() and (not keep or t - keep[-1] > W):
            keep.append(int(t))
    keep = np.array(keep, dtype=int)
    sign = np.zeros(len(dv))
    if keep.size:
        home_closer = np.nan_to_num(sig["gap_all"][keep], nan=0.0) > 0
        sign[keep] = np.where(home_closer, 1.0, -1.0)
    return keep, thr, sign


def analyse(atd, sig, make_plot=True):
    g, vis = sig["graded"], sig["vis"]
    speed, dv, accel = kinematics(atd["ball"])
    sv = speed[g & vis & np.isfinite(speed)]
    sigma, speed_noise = noise_floor(accel, g & vis)
    anti, (c, h, hs) = find_antimode(sv)
    shares = {str(t): float(np.mean(sv > t)) for t in SPEED_THRESHOLDS}
    out = dict(speed_pct=np.percentile(sv, [5, 25, 50, 75, 95, 99]).tolist(),
               shares_above_mps=shares, sigma_pos_upper_bound_m=sigma,
               implied_speed_noise_mps=float(speed_noise),
               antimode=None if anti is None else dict(speed_mps=anti[0], depth=anti[1]),
               glitch_share=float(np.mean(sv > GLITCH_SPEED)))
    ok = g & vis & np.isfinite(dv)
    free = ok & (sig["dmin"] > FREE_BALL_DIST)
    near = ok & (sig["dmin"] <= sig["radius"])
    out["dv_free_pct"] = np.percentile(dv[free], [50, 90, 95, 99, 99.9]).tolist()
    out["dv_near_pct"] = np.percentile(dv[near], [50, 90, 95, 99, 99.9]).tolist()
    minutes = g.sum() / data.FPS / 60.0
    out["touches"] = {}
    for pct in (95.0, 99.0, 99.9):
        ev, thr, sign = touch_events(sig, dv, pct)
        out["touches"][str(pct)] = dict(threshold_mps=thr, n=int(len(ev)), per_min=float(len(ev) / minutes),
                                        home_share=float(np.mean(sign[ev] > 0)) if len(ev) else None)
    if make_plot:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 3, figsize=(16, 4))
        ax[0].bar(10 ** c, h, width=0.12 * 10 ** c, color="#9ab")
        ax[0].plot(10 ** c, hs, "k")
        ax[0].set_xscale("log")
        ax[0].axvline(sig["carry"], color="r", ls="--", label="v1 gate %.2f" % sig["carry"])
        if anti:
            ax[0].axvline(anti[0], color="g", ls="--", label="antimode %.1f" % anti[0])
        ax[0].set_title("Ball speed (visible, graded), log x")
        ax[0].legend(fontsize=8)
        bins = np.linspace(0, 20, 80)
        ax[1].hist(dv[free], bins=bins, alpha=.6, density=True, label="no player within 5 m", log=True)
        ax[1].hist(dv[near], bins=bins, alpha=.6, density=True, label="player within control radius", log=True)
        ax[1].axvline(out["touches"]["99.0"]["threshold_mps"], color="k", ls="--", label="touch thr (p99 free)")
        ax[1].set_title("|velocity change| across t (+-0.2 s)")
        ax[1].legend(fontsize=8)
        ax[2].axis("off")
        ax[2].text(0, .5, "sigma_pos <= %.3f m\nspeed noise ~ %.2f m/s\nshare > 6.44/10/15/25/35 m/s:\n%s\ntouches p95/p99/p99.9: %s"
                   % (sigma, speed_noise, ", ".join("%.1f%%" % (100 * v) for v in shares.values()),
                      [out["touches"][k]["n"] for k in out["touches"]]), fontsize=11, va="center")
        fig.tight_layout()
        fig.savefig(os.path.join(data.ROOT, "analysis", "hmm_v2", "gate_touch.png"), dpi=110)
        plt.close(fig)
    return out, dv


def main():
    atd = data.load_atd()
    sig = features.frame_signals(atd)
    out, _ = analyse(atd, sig)
    with open(os.path.join(data.ROOT, "analysis", "hmm_v2", "gate_touch.json"), "w") as handle:
        json.dump(out, handle, indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
