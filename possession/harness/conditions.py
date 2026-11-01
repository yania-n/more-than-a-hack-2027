"""Ball conditions for the harness. as-is and degraded come from the pilot (adapters.degrade_ball);
the leak-free condition below is built here and is only run for a game that meets the registered
trigger (>= 25% of its dead-ball frames have a visible ball; PREREGISTRATION.md s.6)."""

import numpy as np

from ..pilot import adapters

LEAKFREE_TRIGGER = 0.25
SIGMA_BALL = 0.07


def degrade_alive_only(ball, blocks, gap_lengths, target_share, sigma, seed, alive_mask):
    """Like adapters.degrade_ball, but the extra gaps are applied only on alive-play frames, so the
    stoppage frames keep whatever ball the game itself has. The rate is bisected so that the graded
    visible share equals target_share (or as close as possible if the game's own share is lower)."""
    n = len(ball)
    g = np.zeros(n, dtype=bool)
    for _, a, b in blocks:
        g[a:b + 1] = True
    vis = np.isfinite(ball[:, 0])
    lo, hi = 1e-6, 0.5
    for _ in range(40):
        mid = np.sqrt(lo * hi)
        drop = adapters._drop_mask(n, blocks, mid, gap_lengths, seed) & alive_mask
        if np.mean((vis & ~drop)[g]) > target_share:
            lo = mid
        else:
            hi = mid
    rate = np.sqrt(lo * hi)
    drop = adapters._drop_mask(n, blocks, rate, gap_lengths, seed) & alive_mask
    out = ball.copy()
    out[drop] = np.nan
    rng = np.random.default_rng(seed + 1000)
    seen = np.isfinite(out[:, 0])
    out[seen] += rng.normal(0.0, sigma, size=(int(seen.sum()), 2))
    return out, dict(rate=float(rate), visible_share=float(np.mean(np.isfinite(out[g, 0]))),
                     extra_gap_share=float(np.mean((vis & drop)[g]) / max(np.mean(vis[g]), 1e-9)))
