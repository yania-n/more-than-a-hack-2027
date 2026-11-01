"""Per-frame signals and per-block categorical features. No ground truth anywhere.

Fixed constants (each justified; none was chosen by looking at a score):

  BLOCK = 10 frames (0.4 s)   The HMM runs on 2.5 Hz blocks, not 25 Hz frames. Emissions are
      treated as conditionally independent given the state, which is badly false for consecutive
      frames (the ball sits 1 m from the same player for dozens of frames); at 25 Hz the product
      would overcount evidence ~25x and swamp the transition prior. 0.4 s is about one touch /
      pass-cycle of football and well above tracker jitter. Cost: boundary placement +-0.2 s.
  CONTROL_RADIUS = median nearest-player distance over visible-ball graded frames (computed, ~2 m).
      A player "in control" has the ball within playing distance: about one stride plus the
      tracker's metre-scale position noise. Taken as the median so that by construction the
      ball is "inside someone's radius" on half the visible frames, with no tuned number.
  CARRY_SPEED = 99th percentile of player speeds over graded frames (computed, ~6.4 m/s). A ball
      moving faster than almost any player ever runs cannot be being carried: it is in flight, so
      "who is closest" says nothing about control and the control features are set missing.
  OUTSIDE_MARGIN = 0.5 m. Ball must be this far beyond a touchline/goal line to count as out,
      because tracked ball positions have sub-metre noise and an in-play ball often sits on a line.
  SPEED_SMOOTH = 25 frames (1 s) for mean player speed: removes step-frequency oscillation.
  FLIGHT_W = 5 frames (0.2 s) half-window for ball speed / heading change.
  HEADING_MIN_MOVE = 0.5 m. Heading is only defined if the ball moved at least this far in each
      half-window (2.5 m/s, above walking pace and far above tracker noise); otherwise missing.
  SETPIECE_LEAD = 10 s. Smart Tagging marks the start of a set piece phase; players visibly slow
      for the stoppage before it. The indicator is on for the 10 s before an instance start.
      (Chosen from the unlabeled event-triggered mean-speed profile around tagged starts:
      speed is depressed from ~10 s before to ~5 s after.)
  Quantile bin counts (4 |g| bins, 3 dwell bins, 5 ball-speed, 4 heading, 12 player-speed):
      edges are percentiles of the pooled full-match distribution, so each bin holds equal mass.
      Player speed gets 12 because it carries the dead-ball threshold: with 6 bins the learned
      cutoff was pinned to a bin edge (1.19 m/s); 12 bins (>1,300 blocks each) lets EM place the
      boundary to ~0.1 m/s. Chosen from the shape of the learned emission, before any scoring.
      Sensitivity (6/12/24 bins -> cutoff ~1.2/1.4/1.5 m/s) is reported as a weakness.
"""

import warnings

import numpy as np

from . import data
from .hmm import FeatureSpec

BLOCK = 10
SPEED_SMOOTH = 25
FLIGHT_W = 5
HEADING_MIN_MOVE = 0.5
OUTSIDE_MARGIN = 0.5
SETPIECE_LEAD = 10 * data.FPS
N_G_BINS, N_DWELL_BINS, N_BSPEED, N_HEAD, N_PSPEED = 4, 3, 5, 4, 12
RESTART_TYPES = ("free kick", "goal kick", "corner kick", "throw-in",
                 "kick off (after goal)", "kick off (start)")


def moving_mean_nan(x, k):
    ok = np.isfinite(x)
    c = np.concatenate(([0.0], np.cumsum(np.where(ok, x, 0.0))))
    n = np.concatenate(([0], np.cumsum(ok)))
    i = np.arange(len(x))
    lo, hi = np.maximum(0, i - k // 2), np.minimum(len(x), i + k // 2 + 1)
    with np.errstate(all="ignore"):
        return (c[hi] - c[lo]) / (n[hi] - n[lo])


def nearest_team_distance(atd):
    """(N,2) metres from the ball to the nearest home / away player; NaN if none or no ball."""
    ball, pl, team = atd["ball"], atd["players"], atd["team"]
    out = np.full((len(ball), 2), np.nan)
    for t in (0, 1):
        dd = np.sqrt(((pl[:, team == t, :] - ball[:, None, :]) ** 2).sum(-1))
        dd[~np.isfinite(dd)] = np.inf
        mn = dd.min(1)
        mn[~np.isfinite(mn)] = np.nan
        out[:, t] = mn
    return out


def frame_signals(atd):
    """Everything that is computed per video frame (graded or not), as a dict of arrays."""
    ball, P = atd["ball"], data.PITCH
    g_mask = data.graded_mask()
    vis = np.isfinite(ball[:, 0])
    dist = nearest_team_distance(atd)
    dH, dA = dist[:, 0], dist[:, 1]
    gap = dA - dH  # >0: home closer
    dmin = np.fmin(dH, dA)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pmean = np.nanmean(atd["pspeed"], axis=1)
        radius = float(np.nanmedian(dmin[g_mask & vis]))
        carry = float(np.nanpercentile(atd["pspeed"][g_mask], 99))
    pspeed = moving_mean_nan(pmean, SPEED_SMOOTH)

    w, n = FLIGHT_W, len(ball)
    bspeed = np.full(n, np.nan)
    heading = np.full(n, np.nan)
    d_back = ball[w:-w] - ball[:-2 * w]       # ball[t] - ball[t-w], stored at index t
    d_fwd = ball[2 * w:] - ball[w:-w]          # ball[t+w] - ball[t]
    bspeed[w:-w] = np.hypot(*(ball[2 * w:] - ball[:-2 * w]).T) / (2.0 * w / data.FPS)
    nb, nf = np.hypot(*d_back.T), np.hypot(*d_fwd.T)
    with np.errstate(all="ignore"):
        cosang = (d_back * d_fwd).sum(1) / (nb * nf)
    ang = np.degrees(np.arccos(np.clip(cosang, -1, 1)))
    ang[~((nb >= HEADING_MIN_MOVE) & (nf >= HEADING_MIN_MOVE))] = np.nan
    heading[w:-w] = ang

    bx, by = ball[:, 0], ball[:, 1]
    beyond = np.maximum.reduce([-bx, bx - P[0], -by, by - P[1], np.zeros(n)])
    beyond[~vis] = np.nan

    flight = vis & (bspeed > carry)
    eligible = vis & ~flight & np.isfinite(gap) & (gap != 0)

    # Signed dwell: consecutive visible frames the same team has been the closer one while within
    # the control radius (+ home, - away, 0 = nobody within radius). Missing-ball frames are
    # skipped (neither extend nor reset the run): they carry no evidence either way.
    side = np.where(dmin <= radius, np.sign(gap), 0.0)
    dwell = np.zeros(n)
    run, prev = 0, 0
    for t in np.flatnonzero(vis & np.isfinite(gap)):
        s = int(side[t])
        run = (run + 1 if s == prev else 1) if s != 0 else 0
        prev = s
        dwell[t] = s * run
    dwell[~eligible] = np.nan

    sp = np.zeros(n, dtype=bool)
    for ev in data.load_set_pieces():
        if ev["type"] in RESTART_TYPES:
            sp[max(0, ev["start_frame"] - SETPIECE_LEAD):ev["start_frame"] + 1] = True

    return dict(vis=vis, dH=dH, dA=dA, dmin=dmin, gap=np.where(eligible, gap, np.nan),
                gap_all=gap, dwell=dwell, bspeed=bspeed, heading=heading, beyond=beyond,
                pspeed=pspeed, pmean=pmean, setpiece=sp, flight=flight, radius=radius,
                carry=carry, graded=g_mask)


def _blocks(x, a, b):
    n = b - a + 1
    nb = -(-n // BLOCK)
    out = np.full(nb * BLOCK, np.nan, dtype=float)
    out[:n] = x[a:b + 1]
    return out.reshape(nb, BLOCK)


def _nanagg(fn, m):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return fn(m, axis=1)


def _digitize(x, edges):
    out = np.full(len(x), -1, dtype=np.int64)
    ok = np.isfinite(x)
    out[ok] = np.searchsorted(edges, x[ok], side="right")
    return out


def block_values(sig):
    """Raw per-block values, one dict per half."""
    halves = []
    for half, a, b in data.graded_blocks():
        v = {}
        v["gap"] = _nanagg(np.nanmedian, _blocks(sig["gap"], a, b))
        dw = _blocks(sig["dwell"], a, b)
        last = np.full(dw.shape[0], np.nan)
        for i in range(dw.shape[0]):               # dwell at the last eligible frame of the block
            idx = np.flatnonzero(np.isfinite(dw[i]))
            if idx.size:
                last[i] = dw[i, idx[-1]]
        v["dwell"] = last
        v["bspeed"] = _nanagg(np.nanmedian, _blocks(np.where(sig["vis"], sig["bspeed"], np.nan), a, b))
        v["heading"] = _nanagg(np.nanmedian, _blocks(sig["heading"], a, b))
        out_frac = _nanagg(np.nanmean, _blocks(np.where(np.isfinite(sig["beyond"]),
                                                        (sig["beyond"] > OUTSIDE_MARGIN) * 1.0,
                                                        np.nan), a, b))
        v["outside"] = np.where(np.isfinite(out_frac), (out_frac > 0.5) * 1.0, np.nan)
        v["pspeed"] = _nanagg(np.nanmean, _blocks(sig["pspeed"], a, b))
        v["setpiece"] = (_nanagg(np.nanmean, _blocks(sig["setpiece"].astype(float), a, b)) > 0.5) * 1.0
        v["start"], v["end"] = a, b
        halves.append(v)
    return halves


def build(sig):
    """-> (seqs, specs, halves_values, edges). seqs: per-half (T, F) int category arrays, -1 = missing."""
    halves = block_values(sig)
    pool = {k: np.concatenate([h[k] for h in halves]) for k in
            ("gap", "dwell", "bspeed", "heading", "pspeed")}

    def q(x, n):
        return np.nanpercentile(x, np.linspace(0, 100, n + 1)[1:-1])

    e_g = q(np.abs(pool["gap"]), N_G_BINS)
    absd = np.abs(pool["dwell"])
    e_d = q(absd[absd > 0], N_DWELL_BINS)
    e_b, e_h, e_p = q(pool["bspeed"], N_BSPEED), q(pool["heading"], N_HEAD), q(pool["pspeed"], N_PSPEED)

    specs = [
        FeatureSpec("gap", 2 * N_G_BINS, "team"),
        FeatureSpec("dwell", 2 * N_DWELL_BINS + 1, "team"),
        FeatureSpec("ball_speed", N_BSPEED, "sym", dead_tilt=-1),
        FeatureSpec("heading", N_HEAD, "sym"),
        FeatureSpec("outside", 2, "sym", dead_tilt=+1),
        FeatureSpec("setpiece", 2, "sym", dead_tilt=+1),
        FeatureSpec("player_speed", N_PSPEED, "sym", dead_tilt=-1),
    ]
    seqs = []
    for h in halves:
        cg = np.full(len(h["gap"]), -1, dtype=np.int64)
        ok = np.isfinite(h["gap"])
        mag = np.searchsorted(e_g, np.abs(h["gap"][ok]), side="right")
        cg[ok] = np.where(h["gap"][ok] < 0, N_G_BINS - 1 - mag, N_G_BINS + mag)
        cd = np.full(len(h["dwell"]), -1, dtype=np.int64)
        ok = np.isfinite(h["dwell"])
        mag = np.searchsorted(e_d, np.abs(h["dwell"][ok]), side="right")
        cd[ok] = N_DWELL_BINS + np.sign(h["dwell"][ok]).astype(int) * (1 + mag)
        cd[ok & (h["dwell"] == 0)] = N_DWELL_BINS
        cols = [cg, cd, _digitize(h["bspeed"], e_b), _digitize(h["heading"], e_h),
                np.where(np.isfinite(h["outside"]), h["outside"], -1).astype(np.int64),
                h["setpiece"].astype(np.int64), _digitize(h["pspeed"], e_p)]
        seqs.append(np.stack(cols, 1))
    edges = dict(gap=e_g, dwell=e_d, ball_speed=e_b, heading=e_h, player_speed=e_p)
    return seqs, specs, halves, edges


def upsample(paths, halves, n_frames=data.N_FRAMES):
    """Block-level state paths -> frame codes (int8: 0 H, 1 A, 2 D, 3 X on ungraded frames)."""
    out = np.full(n_frames, 3, dtype=np.int8)
    for p, h in zip(paths, halves):
        n = h["end"] - h["start"] + 1
        out[h["start"]:h["end"] + 1] = np.repeat(p, BLOCK)[:n]
    return out
