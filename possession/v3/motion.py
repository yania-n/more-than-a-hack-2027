"""Relative-motion control signal (v3): does the ball move with its nearest player?

Everything here follows analysis/hmm_v3/PREREGISTRATION.md (sections 2 and 3). No ground truth.
"""

import warnings

import numpy as np

from .. import data, features

W = features.FLIGHT_W                 # 5 frames: velocity = central difference over +-0.2 s
DT = W / data.FPS
WIN_BEFORE, WIN_AFTER = 15, 25        # window [s-15, s+25) = 1.6 s centred on a 10-frame block
MIN_FRAMES = 12                       # 0.48 s of evidence
FLOOR_K = 4.0                         # a velocity must exceed 4x its noise speed to have a direction
SHIFTS = (-250, -175, 175, 250)       # +-7 s, +-10 s
PCT = 99.0                            # registered null percentile
SEED = 0


def velocity(x):
    """Central-difference velocity (m/s) of an (N,...,2) track; NaN where an end is missing."""
    v = np.full(x.shape, np.nan)
    v[W:-W] = (x[2 * W:] - x[:-2 * W]) / (2 * DT)
    return v


def noise_speed(x, graded):
    """Speed-noise scale: sigma_pos (robust upper bound from the second difference) -> m/s."""
    a = np.full(x.shape, np.nan)
    a[W:-W] = x[2 * W:] - 2 * x[W:-W] + x[:-2 * W]
    a = a[graded]
    a = a[np.isfinite(a).all(-1)].reshape(-1, 2)
    mad = np.median(np.abs(a - np.median(a, axis=0)), axis=0) / 0.6745
    sigma = float(np.mean(mad) / np.sqrt(6.0))
    return sigma, sigma * np.sqrt(2.0) / (2 * DT)


def agreement(vb, vp, fb, fp):
    """Per-frame cosine C, |ln speed ratio| L and validity of ball velocity vs player velocity."""
    nb, npl = np.hypot(*vb.T), np.hypot(*vp.T)
    valid = np.isfinite(nb) & np.isfinite(npl) & (nb >= fb) & (npl >= fp)
    with np.errstate(all="ignore"):
        c = (vb * vp).sum(1) / (nb * npl)
        l = np.abs(np.log(nb / npl))
    c = np.where(valid, c, np.nan)
    l = np.where(valid, l, np.nan)
    return c, l, valid


def _csum(x):
    return np.concatenate(([0.0], np.cumsum(x)))


def _wsum(cs, lo, hi):
    return cs[hi] - cs[lo]


def block_windows(halves):
    """(lo, hi) frame arrays (clipped to the half) for every block of every half, + block counts."""
    lo, hi, counts = [], [], []
    for h in halves:
        a, b = h["start"], h["end"]
        n = -(-(b - a + 1) // features.BLOCK)
        s = a + features.BLOCK * np.arange(n)
        lo.append(np.maximum(s - WIN_BEFORE, a))
        hi.append(np.minimum(s + WIN_AFTER, b + 1))
        counts.append(n)
    return np.concatenate(lo), np.concatenate(hi), counts


def compute(atd, sig, halves, pct=PCT, make_plot_data=False):
    ball, pl, team = atd["ball"], atd["players"], atd["team"]
    n = len(ball)
    g = sig["graded"]
    vb = velocity(ball)
    vp = velocity(pl)
    sb, fb_noise = noise_speed(ball, g & sig["vis"])
    # pooled player-track noise: average sigma over slots with enough data
    sigs = []
    for j in range(pl.shape[1]):
        a = np.full((n, 2), np.nan)
        a[W:-W] = pl[2 * W:, j] - 2 * pl[W:-W, j] + pl[:-2 * W, j]
        a = a[g]
        a = a[np.isfinite(a).all(1)]
        if len(a) > 2000:
            sigs.append(a)
    A = np.concatenate(sigs)
    mad = np.median(np.abs(A - np.median(A, axis=0)), axis=0) / 0.6745
    sigma_p = float(np.mean(mad) / np.sqrt(6.0))
    fp_noise = sigma_p * np.sqrt(2.0) / (2 * DT)
    f_b, f_p = FLOOR_K * fb_noise, FLOOR_K * fp_noise

    dist = np.sqrt(((pl - ball[:, None, :]) ** 2).sum(-1))
    dist[~np.isfinite(dist)] = np.inf
    jstar = np.argmin(dist, axis=1)
    dmin = dist[np.arange(n), jstar]
    dmin[~np.isfinite(dmin)] = np.nan
    tstar = team[jstar]
    vp_star = vp[np.arange(n), jstar]

    # real agreement
    c_real, l_real, valid_real = agreement(vb, vp_star, f_b, f_p)
    # time-shift nulls (same slot, player velocity from Delta frames away)
    null_shift = []
    for d in SHIFTS:
        idx = np.arange(n) + d
        ok = (idx >= 0) & (idx < n)
        v = np.full((n, 2), np.nan)
        v[ok] = vp[idx[ok], jstar[ok]]
        null_shift.append(agreement(vb, v, f_b, f_p))
    # same-team random-player null
    rng = np.random.default_rng(SEED)
    cand = (team[None, :] == tstar[:, None]) & np.isfinite(vp[:, :, 0])
    cand[np.arange(n), jstar] = False
    cnt = cand.sum(1)
    k = np.floor(rng.random(n) * np.maximum(cnt, 1)).astype(int)
    pick = np.argmax(np.cumsum(cand, axis=1) > k[:, None], axis=1)
    v_rand = np.where((cnt > 0)[:, None], vp[np.arange(n), pick], np.nan)
    null_team = agreement(vb, v_rand, f_b, f_p)

    visf = sig["vis"] & np.isfinite(vb[:, 0])
    nearf = visf & (dmin <= sig["radius"])
    home_near = nearf & (tstar == 0)
    away_near = nearf & (tstar == 1)
    lo, hi, counts = block_windows(halves)
    vis_n = _wsum(_csum(visf), lo, hi)
    near_n = _wsum(_csum(nearf), lo, hi)
    home_n = _wsum(_csum(home_near), lo, hi)
    away_n = _wsum(_csum(away_near), lo, hi)

    def stats(c, l, valid):
        vn = _wsum(_csum(valid & nearf), lo, hi)
        sc = _wsum(_csum(np.where(valid & nearf, c, 0.0)), lo, hi)
        sl = _wsum(_csum(np.where(valid & nearf, l, 0.0)), lo, hi)
        with np.errstate(all="ignore"):
            return vn, sc / vn, sl / vn

    vn_r, cbar_r, lbar_r = stats(c_real, l_real, valid_real)
    candidate = (vis_n >= MIN_FRAMES) & (near_n == vis_n) & ((home_n == vis_n) | (away_n == vis_n)) \
        & (vn_r >= MIN_FRAMES)
    nulls = {"shift": [stats(*nz) for nz in null_shift], "team": [stats(*null_team)]}

    def null_pool(kind):
        cs, ls = [], []
        for vn, cb, lb in nulls[kind]:
            ok = candidate & (vn >= MIN_FRAMES)
            cs.append(cb[ok])
            ls.append(lb[ok])
        return np.concatenate(cs), np.concatenate(ls)

    pools = {kind: null_pool(kind) for kind in nulls}

    def thresholds(p):
        tc = max(np.percentile(pools[k][0], p) for k in pools)
        tl = min(np.percentile(pools[k][1], 100 - p) for k in pools)
        return float(tc), float(tl)

    def carried_mask(tc, tl):
        return candidate & (cbar_r > tc) & (lbar_r < tl)

    tc, tl = thresholds(pct)
    carried = carried_mask(tc, tl)
    cat = np.where(vis_n < MIN_FRAMES, -1, 1)
    cat = np.where(carried & (home_n == vis_n), 2, cat)
    cat = np.where(carried & (away_n == vis_n), 0, cat)

    # per-half split
    cols, start = [], 0
    for c in counts:
        cols.append(cat[start:start + c].astype(np.int64))
        start += c

    observed = int(np.sum(cat >= 0))
    info = dict(
        sigma_pos_ball=sb, sigma_pos_players=sigma_p, speed_floor_ball=f_b, speed_floor_players=f_p,
        radius=sig["radius"], blocks=int(len(cat)), observed=observed,
        candidates=int(candidate.sum()), carried_home=int(np.sum(cat == 2)), carried_away=int(np.sum(cat == 0)),
        carried_share_of_observed=float(np.sum((cat == 0) | (cat == 2)) / max(observed, 1)),
        carried_share_of_candidates=float(carried.sum() / max(candidate.sum(), 1)),
        theta_C=tc, theta_L=tl, pct=pct,
        null_fp_joint={k: float(np.mean((pools[k][0] > tc) & (pools[k][1] < tl))) for k in pools},
        null_quantiles={k: dict(C=np.percentile(pools[k][0], [1, 50, 95, 99]).tolist(),
                                L=np.percentile(pools[k][1], [1, 5, 50, 99]).tolist()) for k in pools},
        real_quantiles=dict(C=np.nanpercentile(cbar_r[candidate], [1, 50, 95, 99]).tolist(),
                            L=np.nanpercentile(lbar_r[candidate], [1, 5, 50, 99]).tolist()),
        sensitivity={str(p): dict(zip(("theta_C", "theta_L"), thresholds(p)),
                                  carried_share_of_observed=float(carried_mask(*thresholds(p)).sum() / max(observed, 1)))
                     for p in (95.0, 99.0, 99.9)},
    )
    # frame-level autocorrelation time of C near the ball (information only)
    x = np.where(valid_real & nearf, c_real, np.nan)
    ok = np.isfinite(x)
    mu = np.nanmean(x)
    rho = []
    for lag in range(1, 101):
        a_, b_ = x[:-lag] - mu, x[lag:] - mu
        m = np.isfinite(a_) & np.isfinite(b_)
        rho.append(float(np.sum(a_[m] * b_[m]) / np.sqrt(np.sum(a_[m] ** 2) * np.sum(b_[m] ** 2))) if m.sum() > 100 else 0.0)
    below = [i + 1 for i, r in enumerate(rho) if r < 1 / np.e]
    info["frame_acf_efold_frames"] = below[0] if below else None
    extra = dict(cbar_real=cbar_r[candidate], lbar_real=lbar_r[candidate], pools=pools) if make_plot_data else None
    return cols, info, extra
