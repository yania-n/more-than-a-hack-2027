"""Adapters that feed another game to the *unchanged* smooth50 and v1 code.  (PREREGISTRATION.md s.4-5)

Nothing in starter/ or possession/{data,features,hmm,run}.py is edited. v1 is called under a runtime
context that points `possession.data` at the other game (module attributes are swapped for the duration
of the call and restored afterwards).
"""

import contextlib
import warnings

import numpy as np

from .. import data, features, hmm, run
from ..hmm import FeatureSpec

baseline = data._baseline                     # starter/baseline.py, called as is
SPEED_K = 8                                   # +-8 frames: closest to the provided ATD speed column (PREREG s.4)
SPEED_FIELDS = ("N_FRAMES", "PITCH", "load_atd", "graded_mask", "graded_blocks", "load_set_pieces")


# ------------------------------------------------------------------ smooth50 (organizers' code)
def write_raw_atd_like(path, players_m, ball_m, pitch):
    """Write 'frame:x,y,NaN;...:x,y,NaN' (the layout starter/baseline.py parses). Coordinates 0-1."""
    pitch = np.asarray(pitch, dtype=float)

    def fmt(p):
        return "NaN,NaN,NaN" if not np.isfinite(p[0]) else "{:.5f},{:.5f},NaN".format(p[0], p[1])

    with open(path, "w", newline="\n") as handle:
        for f in range(len(ball_m)):
            groups = ";".join(fmt(players_m[f, j] / pitch) for j in range(players_m.shape[1]))
            handle.write("{}:{}:{}\n".format(f + 1, groups, fmt(ball_m[f] / pitch)))


def smooth50_codes(raw_path, team_of_track, n_frames, pitch, window=50):
    codes = baseline.nearest_player_labels(raw_path, np.asarray(team_of_track), n_frames, tuple(pitch))
    lab = baseline.smooth(codes, window)
    return np.array([{"H": 0, "A": 1, "D": 2}[x] for x in lab], dtype=np.int8)


# ------------------------------------------------------------------ v1 (possession/ code)
def derive_pspeed(players, k=SPEED_K):
    """Player speed (m/s) from positions, central difference over +-k frames."""
    v = np.full(players.shape[:2], np.nan)
    v[k:-k] = np.hypot(*(players[2 * k:] - players[:-2 * k]).transpose(2, 0, 1)) / (2.0 * k / data.FPS)
    return v


@contextlib.contextmanager
def use_game(atd, blocks, set_pieces, pitch):
    """Point possession.data at another game for the duration of the block."""
    n = len(atd["ball"])
    mask = np.zeros(n, dtype=bool)
    for _, a, b in blocks:
        mask[a:b + 1] = True
    saved = {k: getattr(data, k) for k in SPEED_FIELDS}
    data.N_FRAMES, data.PITCH = n, np.asarray(pitch, dtype=np.float64)
    data.load_atd = lambda: atd
    data.graded_mask = lambda: mask
    data.graded_blocks = lambda: blocks
    data.load_set_pieces = lambda: list(set_pieces)
    try:
        yield
    finally:
        for k, v in saved.items():
            setattr(data, k, v)


def rederive(sig, radius, carry):
    """Recompute everything in the frame signals that depends on the control radius / carry speed
    (a copy of the corresponding lines of features.frame_signals, validated against it)."""
    s = dict(sig)
    vis, gap, dmin = sig["vis"], sig["gap_all"], sig["dmin"]
    flight = vis & (sig["bspeed"] > carry)
    eligible = vis & ~flight & np.isfinite(gap) & (gap != 0)
    side = np.where(dmin <= radius, np.sign(gap), 0.0)
    dwell = np.zeros(len(vis))
    run_len, prev = 0, 0
    for t in np.flatnonzero(vis & np.isfinite(gap)):
        sd = int(side[t])
        run_len = (run_len + 1 if sd == prev else 1) if sd != 0 else 0
        prev = sd
        dwell[t] = sd * run_len
    dwell[~eligible] = np.nan
    s.update(flight=flight, gap=np.where(eligible, gap, np.nan), dwell=dwell, radius=radius, carry=carry)
    return s


def build_with_edges(sig, edges):
    """features.build with the percentile bin edges given instead of computed (a copy, validated)."""
    halves = features.block_values(sig)
    N_G, N_D = features.N_G_BINS, features.N_DWELL_BINS
    specs = [
        FeatureSpec("gap", 2 * N_G, "team"), FeatureSpec("dwell", 2 * N_D + 1, "team"),
        FeatureSpec("ball_speed", features.N_BSPEED, "sym", dead_tilt=-1),
        FeatureSpec("heading", features.N_HEAD, "sym"), FeatureSpec("outside", 2, "sym", dead_tilt=+1),
        FeatureSpec("setpiece", 2, "sym", dead_tilt=+1),
        FeatureSpec("player_speed", features.N_PSPEED, "sym", dead_tilt=-1)]
    seqs = []
    for h in halves:
        cg = np.full(len(h["gap"]), -1, dtype=np.int64)
        ok = np.isfinite(h["gap"])
        mag = np.searchsorted(edges["gap"], np.abs(h["gap"][ok]), side="right")
        cg[ok] = np.where(h["gap"][ok] < 0, N_G - 1 - mag, N_G + mag)
        cd = np.full(len(h["dwell"]), -1, dtype=np.int64)
        ok = np.isfinite(h["dwell"])
        mag = np.searchsorted(edges["dwell"], np.abs(h["dwell"][ok]), side="right")
        cd[ok] = N_D + np.sign(h["dwell"][ok]).astype(int) * (1 + mag)
        cd[ok & (h["dwell"] == 0)] = N_D
        cols = [cg, cd, features._digitize(h["bspeed"], edges["ball_speed"]),
                features._digitize(h["heading"], edges["heading"]),
                np.where(np.isfinite(h["outside"]), h["outside"], -1).astype(np.int64),
                h["setpiece"].astype(np.int64), features._digitize(h["pspeed"], edges["player_speed"])]
        seqs.append(np.stack(cols, 1))
    return seqs, specs, halves


def run_v1(atd, blocks, set_pieces, pitch, mode="refit", ref=None, setpiece_missing=False):
    """v1 on any game. mode 'refit': EM on this game, constants and bin edges from this game.
    mode 'transfer': ref (radius, carry, edges, params) from another game, decoding only.
    Returns dict(codes, params, radius, carry, edges, sig, seqs, halves)."""
    stay = [s * data.FPS / features.BLOCK for s in run.PRIOR_DWELL_S]
    n = len(atd["ball"])
    with use_game(atd, blocks, set_pieces, pitch):
        sig = features.frame_signals(atd)
        if mode == "refit":
            seqs, specs, halves, edges = features.build(sig)
        else:
            sig = rederive(sig, ref["radius"], ref["carry"])
            seqs, specs, halves = build_with_edges(sig, ref["edges"])
            edges = ref["edges"]
        if setpiece_missing:
            col = [s.name for s in specs].index("setpiece")
            for s in seqs:
                s[:, col] = -1                        # marginalised: contributes nothing to any state
        params = hmm.fit(seqs, specs, stay, verbose=False) if mode == "refit" else ref["params"]
        paths = hmm.decode(seqs, params)
        codes = features.upsample(paths, halves, n_frames=n)
    return dict(codes=codes, params=params, radius=sig["radius"], carry=sig["carry"], edges=edges,
                sig=sig, seqs=seqs, halves=halves)


# ------------------------------------------------------------------ ball degradation
def graded_runs(mask_vis, blocks):
    """Lengths of visible runs and of missing runs of a boolean 'ball visible' array inside blocks."""
    vis_runs, gap_runs = [], []
    for _, a, b in blocks:
        x = mask_vis[a:b + 1].astype(np.int8)
        edges = np.flatnonzero(np.diff(np.concatenate(([2], x, [2]))) != 0)
        for s, e in zip(edges[:-1], edges[1:]):
            (vis_runs if x[s] else gap_runs).append(int(e - s))
    return np.array(vis_runs), np.array(gap_runs)


def _drop_mask(n, blocks, rate, gap_lengths, seed):
    rng = np.random.default_rng(seed)
    drop = np.zeros(n, dtype=bool)
    for _, a, b in blocks:
        t = a
        while t <= b:
            t += int(rng.geometric(rate))
            length = int(rng.choice(gap_lengths))
            drop[t:min(t + length, b + 1)] = True
            t += length
    return drop


def degrade_ball(ball, blocks, gap_lengths, target_share, sigma, seed):
    """Extra ball gaps (lengths from the provided match's empirical gap distribution, onsets a Poisson
    process whose rate is found by bisection so the graded visible share equals target_share), then
    Gaussian position noise sigma (m) on visible frames. Deterministic given the seed."""
    n = len(ball)
    g = np.zeros(n, dtype=bool)
    for _, a, b in blocks:
        g[a:b + 1] = True
    vis = np.isfinite(ball[:, 0])
    lo, hi = 1e-6, 0.5                                   # per-frame onset probability, bisected in log space
    for _ in range(40):
        mid = np.sqrt(lo * hi)
        share = np.mean((vis & ~_drop_mask(n, blocks, mid, gap_lengths, seed))[g])
        if share > target_share:
            lo = mid
        else:
            hi = mid
    rate = np.sqrt(lo * hi)
    drop = _drop_mask(n, blocks, rate, gap_lengths, seed)
    out = ball.copy()
    out[drop] = np.nan
    rng = np.random.default_rng(seed + 1000)
    seen = np.isfinite(out[:, 0])
    out[seen] += rng.normal(0.0, sigma, size=(int(seen.sum()), 2))
    return out, dict(rate=float(rate), visible_share=float(np.mean(np.isfinite(out[g, 0]))),
                     extra_gap_share=float(np.mean((vis & drop)[g]) / max(np.mean(vis[g]), 1e-9)))
