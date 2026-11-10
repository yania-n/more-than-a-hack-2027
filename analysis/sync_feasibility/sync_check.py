"""Feasibility check: would a synced broadcast feed fill the gaps in the tactical ball track?

    .venv/Scripts/python.exe analysis/sync_feasibility/sync_check.py

Runs end to end and deterministically (no randomness except a seeded RNG for picking overlay
frames). Everything it writes stays under analysis/sync_feasibility/ (gitignored): a cache/ of
numpy arrays parsed from the ATD, PNG plots, and results.json with every number in REPORT.md.

Rules respected (RULES.md):
  * the alignment is found by code only -- no frame numbers or offsets of this game appear here,
    apart from the published graded blocks, which come from games.half_video_blocks();
  * no ground truth of any kind is read;
  * nothing derived from the data is written outside this gitignored folder.
"""

import json
import os
import sys
import time
import warnings

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "starter"))

from games import GAME, GAMES, half_video_blocks  # noqa: E402
import load_atd  # noqa: E402
import load_homography  # noqa: E402

CACHE = os.path.join(HERE, "cache")
PITCH = np.array(GAMES[GAME]["pitch"], dtype=np.float64)  # metres, (length, width)
FPS = GAMES[GAME]["fps"]


# ---------------------------------------------------------------------------------------------
# Step 1: load
# ---------------------------------------------------------------------------------------------

def load_source(source):
    """ATD of one source as arrays, indexed by video frame (= frame_id - 1).

    Returns dict: ball (n, 2), players (n, slots, 2), team (slots,) 0 = home / 1 = away.
    Parsed once through kloppy, then cached as .npz under the gitignored cache/ folder.
    """
    path = os.path.join(CACHE, source + ".npz")
    if os.path.isfile(path):
        z = np.load(path)
        return {k: z[k] for k in z.files}

    t0 = time.time()
    dataset = load_atd.load(source=source)
    df = dataset.to_df()
    home = dataset.metadata.teams[0]
    slot_team = {}
    for team_index, team in enumerate(dataset.metadata.teams):
        for player in team.players:
            slot_team[str(player.player_id)] = team_index
    slots = sorted(slot_team, key=int)

    video_frame = df["frame_id"].values.astype(np.int64) - 1
    n = int(video_frame.max()) + 1
    ball = np.full((n, 2), np.nan, dtype=np.float32)
    ball[video_frame, 0] = df["ball_x"].values
    ball[video_frame, 1] = df["ball_y"].values
    players = np.full((n, len(slots), 2), np.nan, dtype=np.float32)
    for i, slot in enumerate(slots):
        players[video_frame, i, 0] = df[slot + "_x"].values
        players[video_frame, i, 1] = df[slot + "_y"].values
    out = {"ball": ball, "players": players,
           "team": np.array([slot_team[s] for s in slots], dtype=np.int8),
           "home_name": np.array(str(home))}
    os.makedirs(CACHE, exist_ok=True)
    np.savez_compressed(path, **out)
    print("  parsed {} via kloppy in {:.0f}s".format(source, time.time() - t0))
    return out


def team_centroid_gap(players, team):
    """Per-frame mean x of home minus mean x of away (normalised units)."""
    with np.errstate(all="ignore"):
        hx = np.nanmean(np.where(team[None, :] == 0, players[:, :, 0], np.nan), axis=1)
        ax = np.nanmean(np.where(team[None, :] == 1, players[:, :, 0], np.nan), axis=1)
    return hx - ax


def summarise(name, d):
    ball = ~np.isnan(d["ball"][:, 0])
    n_players = (~np.isnan(d["players"][:, :, 0])).sum(1)
    out = {"frames": int(len(ball)), "ball_pct": 100.0 * ball.mean(),
           "players_per_frame": float(n_players.mean()),
           "players_per_frame_nonempty": float(n_players[n_players > 0].mean()),
           "slots": int(len(d["team"])), "slots_per_team": np.bincount(d["team"]).tolist()}
    print("  {:<9} frames {:>6}  ball {:5.1f}%  players/frame {:5.2f} ({:5.2f} where any)  "
          "slots {} {}".format(name, out["frames"], out["ball_pct"], out["players_per_frame"],
                               out["players_per_frame_nonempty"], out["slots"],
                               out["slots_per_team"]))
    return out


# ---------------------------------------------------------------------------------------------
# Step 2: segment the broadcast into shots
# ---------------------------------------------------------------------------------------------

# Params
IMAGE_CENTRE = (960.0, 540.0)   # 1920x1080 video
MAX_LOOKAT_JUMP_M = 3.0         # camera look-at point moves < 0.6 m/frame at p99 inside a shot
MAX_ERR_JUMP = 3.0              # reprojection-error step that signals a re-fit / cut
MAX_ERR = 10.0                  # homographies worse than this are treated as invalid
MIN_SEGMENT = 2 * FPS           # drop shots shorter than 2 s


def lookat_point(H, valid):
    """Pitch point (metres) under the image centre, per frame; NaN where invalid."""
    out = np.full((len(H), 2), np.nan)
    Hinv = np.linalg.inv(H[valid])
    u, v = IMAGE_CENTRE
    den = Hinv[:, 2, 0] * u + Hinv[:, 2, 1] * v + Hinv[:, 2, 2]
    out[valid, 0] = (Hinv[:, 0, 0] * u + Hinv[:, 0, 1] * v + Hinv[:, 0, 2]) / den * PITCH[0]
    out[valid, 1] = (Hinv[:, 1, 0] * u + Hinv[:, 1, 1] * v + Hinv[:, 1, 2]) / den * PITCH[1]
    return out


def segment_broadcast():
    H, err, valid = load_homography.load(source="broadcast")
    usable = valid & (err < MAX_ERR)
    look = lookat_point(H, valid)
    jump = np.r_[np.inf, np.hypot(*np.diff(look, axis=0).T)]
    err_jump = np.r_[np.inf, np.abs(np.diff(err))]
    # a new segment starts wherever a usable frame follows an unusable one or a big jump
    starts_new = usable & (~np.r_[False, usable[:-1]] | ~(jump <= MAX_LOOKAT_JUMP_M)
                           | ~(err_jump <= MAX_ERR_JUMP))
    starts = np.flatnonzero(starts_new)
    ends = np.flatnonzero(usable & ~np.r_[usable[1:], False])      # last usable frame of a run
    # each segment ends at the frame before the next start, or at the end of its usable run
    bounds = []
    for k, a in enumerate(starts):
        run_end = ends[np.searchsorted(ends, a)]
        nxt = starts[k + 1] - 1 if k + 1 < len(starts) else len(usable) - 1
        bounds.append((int(a), int(min(run_end, nxt))))
    segments = [(a, b) for a, b in bounds if b - a + 1 >= MIN_SEGMENT]
    stats = {"valid_pct": 100.0 * valid.mean(), "usable_pct": 100.0 * usable.mean(),
             "raw_segments": len(bounds), "kept_segments": len(segments)}
    return segments, stats


# ---------------------------------------------------------------------------------------------
# Step 3: align each broadcast segment to the tactical timeline
# ---------------------------------------------------------------------------------------------
#
# Cost of (broadcast frame b, tactical frame t), in metres: a one-sided, truncated chamfer.
# The broadcast only tracks the ~12 players in shot, the tactical camera sees ~19-22, so every
# broadcast player is matched to the nearest tactical player OF THE SAME TEAM (track slots are
# not identities, so the match is by position only). The ball is one more point when the
# broadcast has it: its distance to the tactical ball, or a fixed penalty if tactical has none.
# Each point's distance is capped at CAP_M so a duplicate or stray detection cannot dominate.

# Params
CAP_M = 10.0
BALL_MISSING_PENALTY_M = 5.0
MIN_PLAYERS = 4                 # broadcast frames with fewer tracked players are not scored
COARSE_STEP = 5                 # tactical frames are sampled every 5 for the global search
COARSE_MAX_SAMPLES = 40         # broadcast frames per segment in the coarse search (>= 1 s apart)
N_CANDIDATES = 5                # coarse minima refined at frame resolution
CANDIDATE_SEPARATION = 2 * FPS  # runner-up must be at least 2 s away from the best offset
FINE_MAX_SAMPLES = 200
FAR = 1.0e4                     # stands in for a missing tactical point


class Tracks(object):
    """One source's tracking in metres, split by team, NaN replaced by FAR for min()."""

    def __init__(self, d, mirror=False):
        pitch = PITCH.astype(np.float32)
        players = d["players"].astype(np.float32) * pitch
        ball = d["ball"].astype(np.float32) * pitch
        if mirror:
            players = pitch - players
            ball = pitch - ball
        self.by_team = [players[:, d["team"] == k, :] for k in (0, 1)]
        self.filled = [np.where(np.isnan(p), FAR, p) for p in self.by_team]
        self.ball = ball
        self.n = len(ball)


def coarse_costs(bt, b, tt, t_index):
    """Cost of broadcast frame b against every tactical frame in t_index. None if b unusable."""
    pts = [p[b][~np.isnan(p[b][:, 0])] for p in bt.by_team]
    n_pts = sum(len(p) for p in pts)
    if n_pts < MIN_PLAYERS:
        return None
    total = np.zeros(len(t_index), dtype=np.float32)
    for k in (0, 1):
        if len(pts[k]) == 0:
            continue
        tp = tt.filled[k][t_index]                                   # (m, slots, 2)
        diff = tp[:, :, None, :] - pts[k][None, None, :, :]          # (m, slots, pb, 2)
        dist = np.sqrt((diff ** 2).sum(-1)).min(1)                   # (m, pb)
        total += np.minimum(dist, CAP_M).sum(1)
    count = n_pts
    bball = bt.ball[b]
    if not np.isnan(bball[0]):
        bd = np.sqrt(((tt.ball[t_index] - bball) ** 2).sum(-1))
        total += np.where(np.isnan(bd), BALL_MISSING_PENALTY_M, np.minimum(bd, CAP_M))
        count += 1
    return total / count


def pair_costs(bt, tt, bframes, tframes):
    """Cost of each (bframes[i], tframes[i]) pair. NaN where the broadcast frame is unusable."""
    bframes, tframes = np.asarray(bframes), np.asarray(tframes)
    total = np.zeros(len(bframes))
    count = np.zeros(len(bframes))
    for k in (0, 1):
        bp = bt.by_team[k][bframes]                                  # (m, sb, 2) with NaN
        tp = tt.filled[k][tframes]                                   # (m, st, 2)
        diff = bp[:, :, None, :] - tp[:, None, :, :]
        dist = np.minimum(np.sqrt((diff ** 2).sum(-1)).min(2), CAP_M)  # (m, sb)
        present = ~np.isnan(bp[:, :, 0])
        total += np.where(present, dist, 0.0).sum(1)
        count += present.sum(1)
    enough = count >= MIN_PLAYERS
    bb, tb = bt.ball[bframes], tt.ball[tframes]
    has_bb = ~np.isnan(bb[:, 0])
    bd = np.sqrt(((bb - tb) ** 2).sum(-1))
    total += np.where(has_bb, np.where(np.isnan(bd), BALL_MISSING_PENALTY_M,
                                       np.minimum(bd, CAP_M)), 0.0)
    count += has_bb
    out = total / np.maximum(count, 1)
    out[~enough] = np.nan
    return out


def segment_cost(bt, tt, frames, offset):
    t = frames + offset
    if t[0] < 0 or t[-1] >= tt.n:
        return np.inf
    c = pair_costs(bt, tt, frames, t)
    return float(np.nanmean(c)) if np.isfinite(c).any() else np.inf


def evenly(a, b, max_n, min_step):
    step = max(min_step, int(np.ceil((b - a + 1) / float(max_n))))
    return np.arange(a, b + 1, step)


def best_offset(bt, tt, frames, lo, hi):
    return min((segment_cost(bt, tt, frames, d), d) for d in range(lo, hi + 1))


def align_segment(bt, tt, a, b, t_sampled):
    """Global coarse-to-fine search of the constant offset (tactical = broadcast + offset)."""
    step = COARSE_STEP * max(FPS // COARSE_STEP,
                             int(np.ceil((b - a + 1) / float(COARSE_MAX_SAMPLES * COARSE_STEP))))
    rows, shifts = [], []
    for bf in range(a, b + 1, step):
        c = coarse_costs(bt, bf, tt, t_sampled)
        if c is not None:
            rows.append(c)
            shifts.append((bf - a) // COARSE_STEP)
    if len(rows) < 3:
        return None
    n_j = len(t_sampled) - max(shifts)
    score = np.zeros(n_j)
    for c, s in zip(rows, shifts):
        score += c[s:s + n_j]
    score /= len(rows)

    # coarse candidates: the N best minima, each at least CANDIDATE_SEPARATION apart
    masked = score.copy()
    sep = CANDIDATE_SEPARATION // COARSE_STEP
    cands = []
    for _ in range(N_CANDIDATES):
        j = int(np.argmin(masked))
        cands.append(int(t_sampled[j]) - a)
        masked[max(0, j - sep):j + sep + 1] = np.inf

    # fine: every offset within +-COARSE_STEP of each candidate, on up to 200 frames
    fine_frames = evenly(a, b, FINE_MAX_SAMPLES, 1)
    refined = sorted(best_offset(bt, tt, fine_frames, d0 - COARSE_STEP, d0 + COARSE_STEP)
                     for d0 in cands)
    best_cost, best_off = refined[0]
    runner = [c for c, d in refined[1:] if abs(d - best_off) >= CANDIDATE_SEPARATION]
    runner_cost = runner[0] if runner else np.inf

    # constant-offset check: refine each half of the segment on its own (segments >= 8 s)
    drift = None
    if b - a + 1 >= 8 * FPS:
        mid = (a + b) // 2
        offs = [best_offset(bt, tt, evenly(lo, hi, FINE_MAX_SAMPLES // 2, 1),
                            best_off - FPS, best_off + FPS)[1]
                for lo, hi in ((a, mid), (mid + 1, b))]
        drift = offs[1] - offs[0]

    # per-second cost over the whole segment at the chosen offset
    frames = np.arange(a, b + 1)
    per_frame = pair_costs(bt, tt, frames, frames + best_off)
    with np.errstate(all="ignore"):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            blocks = np.array([np.nanmedian(per_frame[i:i + FPS])
                               for i in range(0, len(frames), FPS)])
    return {"a": int(a), "b": int(b), "offset": int(best_off), "cost": float(best_cost),
            "runner_cost": float(runner_cost), "coarse_samples": len(rows), "drift": drift,
            "worst_second_cost": float(np.nanmax(blocks)) if np.isfinite(blocks).any() else None}


def detect_orientation(bt_plain, bt_mirror, tt, segments, t_sampled, n=8):
    """Align the n longest segments both ways; the orientation with the lower costs wins."""
    longest = sorted(segments, key=lambda s: s[0] - s[1])[:n]
    plain, mirror = [], []
    for a, b in longest:
        r0 = align_segment(bt_plain, tt, a, b, t_sampled)
        r1 = align_segment(bt_mirror, tt, a, b, t_sampled)
        if r0 and r1:
            plain.append(r0["cost"])
            mirror.append(r1["cost"])
    return {"plain_median_cost": float(np.median(plain)),
            "mirrored_median_cost": float(np.median(mirror)),
            "mirrored": bool(np.median(mirror) < np.median(plain)), "n": len(plain)}


# Params -- acceptance (chosen from the cost distribution, see REPORT.md)
MAX_COST_M = 2.0           # mean chamfer cost of an accepted segment
MIN_MARGIN_RATIO = 1.5     # runner-up cost / best cost
MAX_DRIFT = 3              # frames between the two halves' own best offsets
REPLAY_TOL = 2 * FPS       # behind both neighbourhoods by more than this -> replay
NEIGHBOURS = 5


def classify(results):
    """status per segment: accepted | replay | ahead | inconsistent | ambiguous | high_cost |
    drift | no_data. Replay = offset behind the live offset on both sides of it."""
    for r in results:
        if r.get("cost") is None:
            r["status"] = "no_data"
        elif r["cost"] > MAX_COST_M:
            r["status"] = "high_cost"
        elif r["runner_cost"] / r["cost"] < MIN_MARGIN_RATIO:
            r["status"] = "ambiguous"
        elif r["drift"] is not None and abs(r["drift"]) > MAX_DRIFT:
            r["status"] = "drift"
        else:
            r["status"] = "candidate"
    cands = [r for r in results if r["status"] == "candidate"]
    offs = np.array([r["offset"] for r in cands])
    for i, r in enumerate(cands):
        prev = offs[max(0, i - NEIGHBOURS):i]
        nxt = offs[i + 1:i + 1 + NEIGHBOURS]
        refs = [float(np.median(x)) for x in (prev, nxt) if len(x)]
        r["live_ref"] = refs
        if all(r["offset"] < ref - REPLAY_TOL for ref in refs):
            r["status"] = "replay"
        elif all(r["offset"] > ref + REPLAY_TOL for ref in refs):
            r["status"] = "ahead"
        elif not any(abs(r["offset"] - ref) <= REPLAY_TOL for ref in refs):
            r["status"] = "inconsistent"
        else:
            r["status"] = "accepted"
    return results


def build_mapping(results, n_tactical):
    """Broadcast frame for every tactical frame covered by an accepted segment, else -1."""
    b_of_t = np.full(n_tactical, -1, dtype=np.int64)
    for r in results:
        if r["status"] != "accepted":
            continue
        b = np.arange(r["a"], r["b"] + 1)
        t = b + r["offset"]
        ok = (t >= 0) & (t < n_tactical)
        b_of_t[t[ok]] = b[ok]
    return b_of_t


# ---------------------------------------------------------------------------------------------
# Steps 4 and 5: validate and answer
# ---------------------------------------------------------------------------------------------

GAP_BUCKETS = [(1, 5, "1-5"), (6, 25, "6-25"), (26, 125, "26-125"), (126, 10 ** 9, ">125")]


def graded_half(n):
    half = np.zeros(n, dtype=np.int8)
    for h, first, last in half_video_blocks(GAME):
        half[first:last + 1] = h
    return half


def gap_lengths(missing, half):
    """Length of the graded tactical-ball gap each frame belongs to (0 elsewhere).
    Gaps are cut at the graded-block boundaries."""
    out = np.zeros(len(missing), dtype=np.int64)
    m = (missing & (half > 0)).astype(np.int8)
    edges = np.flatnonzero(np.diff(np.r_[0, m, 0]))
    for s, e in zip(edges[::2], edges[1::2]):
        out[s:e] = e - s
    return out


def pct(num, den):
    return 100.0 * float(num) / float(den) if den else float("nan")


def answer(tac, bro, b_of_t):
    n = len(tac["ball"])
    half = graded_half(n)
    t_ball = ~np.isnan(tac["ball"][:, 0])
    covered = b_of_t >= 0
    b_ball = np.zeros(n, dtype=bool)
    b_ball[covered] = ~np.isnan(bro["ball"][b_of_t[covered], 0])
    missing = ~t_ball
    glen = gap_lengths(missing, half)

    def block(sel):
        g = sel & (half > 0)
        gm = g & missing
        return {"graded_frames": int(g.sum()),
                "tactical_ball_pct": pct((g & t_ball).sum(), g.sum()),
                "covered_pct": pct((g & covered).sum(), g.sum()),
                "missing_frames": int(gm.sum()),
                "missing_covered_pct": pct((gm & covered).sum(), gm.sum()),
                "missing_filled_pct": pct((gm & b_ball).sum(), gm.sum()),
                # are the two trackers' failures correlated? broadcast ball rate on covered
                # frames, split by whether tactical has the ball
                "bro_ball_given_covered_tac_present_pct":
                    pct((g & covered & t_ball & b_ball).sum(), (g & covered & t_ball).sum()),
                "bro_ball_given_covered_tac_missing_pct":
                    pct((gm & covered & b_ball).sum(), (gm & covered).sum()),
                "combined_ball_pct": pct((g & (t_ball | b_ball)).sum(), g.sum())}

    out = {"all": block(np.ones(n, dtype=bool)),
           "half1": block(half == 1), "half2": block(half == 2), "gaps": []}
    for lo, hi, name in GAP_BUCKETS:
        sel = (glen >= lo) & (glen <= hi)
        edges = np.flatnonzero(np.diff(np.r_[0, sel.astype(np.int8), 0]))
        gaps = list(zip(edges[::2], edges[1::2]))
        touched = sum(bool(b_ball[s:e].any()) for s, e in gaps)
        out["gaps"].append({"bucket": name, "gaps": len(gaps), "frames": int(sel.sum()),
                            "covered_pct": pct((sel & covered).sum(), sel.sum()),
                            "filled_pct": pct((sel & b_ball).sum(), sel.sum()),
                            "gaps_touched_pct": pct(touched, len(gaps))})
    return out


def ball_disagreement(tac, bro, b_of_t):
    """Metres between the two balls on aligned frames where both sources have one."""
    t = np.flatnonzero(b_of_t >= 0)
    tb = tac["ball"][t].astype(np.float64) * PITCH
    bb = bro["ball"][b_of_t[t]].astype(np.float64) * PITCH
    d = np.hypot(*(tb - bb).T)
    return d[np.isfinite(d)]


# ---------------------------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------------------------

BLUE, ORANGE, GREY, INK, INK2 = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#52514e"


def _style(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GREY)
    ax.tick_params(colors=INK2, labelsize=8)
    ax.grid(axis="y", color="#e6e5e0", linewidth=0.6)
    ax.set_axisbelow(True)


def plot_all(results, segments, dist, tac, bro, b_of_t, out_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from utils import draw_pitch

    # segment lengths
    fig, ax = plt.subplots(figsize=(6, 3.2))
    L = np.array([b - a + 1 for a, b in segments]) / float(FPS)
    ax.hist(L, bins=np.arange(0, L.max() + 10, 5), color=BLUE, edgecolor="white", linewidth=1)
    ax.set_xlabel("segment length (s)", color=INK2)
    ax.set_ylabel("segments", color=INK2)
    ax.set_title("Broadcast shots with a usable homography (>= 2 s)", color=INK, fontsize=10,
                 loc="left")
    _style(ax)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "segment_lengths.png"), dpi=130)
    plt.close(fig)

    # offset vs broadcast frame
    fig, ax = plt.subplots(figsize=(8, 3.8))
    groups = (("accepted", BLUE, "o", "accepted (live)"),
              ("replay", ORANGE, "v", "replay (behind both neighbourhoods)"),
              ("other", GREY, "x", "rejected (cost / margin / drift / inconsistent)"))
    for key, col, mk, lab in groups:
        rs = [r for r in results if r.get("cost") is not None and
              (r["status"] == key or
               (key == "other" and r["status"] not in ("accepted", "replay")))]
        if rs:
            ax.scatter([(r["a"] + r["b"]) / 2.0 / FPS / 60 for r in rs],
                       [r["offset"] / float(FPS) / 60 for r in rs], s=22, c=col, marker=mk,
                       label=lab, linewidths=1.2)
    ax.set_xlabel("broadcast time (min)", color=INK2)
    ax.set_ylabel("offset: tactical - broadcast (min)", color=INK2)
    ax.set_title("Best offset per broadcast segment", color=INK, fontsize=10, loc="left")
    ax.legend(frameon=False, fontsize=8)
    _style(ax)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "offsets.png"), dpi=130)
    plt.close(fig)

    # ball disagreement
    fig, ax = plt.subplots(figsize=(6, 3.2))
    ax.hist(np.minimum(dist, 10), bins=np.arange(0, 10.25, 0.25), color=BLUE,
            edgecolor="white", linewidth=0.8)
    med = float(np.median(dist))
    ax.axvline(med, color=INK, linewidth=1, linestyle="--")
    ax.text(med + 0.15, ax.get_ylim()[1] * 0.9, "median {:.2f} m".format(med), color=INK,
            fontsize=8)
    ax.set_xlabel("tactical vs broadcast ball position (m, clipped at 10)", color=INK2)
    ax.set_ylabel("frames", color=INK2)
    ax.set_title("Ball disagreement on aligned frames where both see it", color=INK,
                 fontsize=10, loc="left")
    _style(ax)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "ball_disagreement.png"), dpi=130)
    plt.close(fig)

    # overlays: 4 random aligned frames where both sources have the ball (seeded)
    rng = np.random.RandomState(0)
    t_both = np.flatnonzero((b_of_t >= 0) & ~np.isnan(tac["ball"][:, 0]))
    t_both = t_both[~np.isnan(bro["ball"][b_of_t[t_both], 0])]
    picks = np.sort(rng.choice(t_both, 4, replace=False))
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.6))
    for ax, t in zip(axes.ravel(), picks):
        draw_pitch(ax, PITCH[0], PITCH[1])
        b = b_of_t[t]
        for src, f, is_tac in ((tac, t, True), (bro, b, False)):
            P = src["players"][f].astype(np.float64) * PITCH
            for k, col in ((0, BLUE), (1, ORANGE)):
                sel = src["team"] == k
                if is_tac:
                    ax.scatter(P[sel, 0], P[sel, 1], s=70, facecolors="none", edgecolors=col,
                               linewidths=1.4, zorder=3)
                else:
                    ax.scatter(P[sel, 0], P[sel, 1], s=45, c=col, marker="x", linewidths=1.6,
                               zorder=4)
        tb, bb = tac["ball"][t] * PITCH, bro["ball"][b] * PITCH
        ax.scatter([tb[0]], [tb[1]], s=90, facecolors="none", edgecolors=INK, linewidths=1.6,
                   zorder=5)
        ax.scatter([bb[0]], [bb[1]], s=40, c=INK, marker="x", linewidths=1.8, zorder=6)
        ax.set_title("tactical frame {}  <->  broadcast frame {}   ball gap {:.2f} m".format(
            t, b, float(np.hypot(*(tb - bb)))), fontsize=8, color=INK)
    fig.text(0.5, 0.01, "circles = tactical ATD, crosses = broadcast ATD;  blue = home, "
             "orange = away, black = ball", ha="center", fontsize=9, color=INK2)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(os.path.join(out_dir, "overlays.png"), dpi=120)
    plt.close(fig)


# ---------------------------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------------------------

def main():
    t_start = time.time()
    res = {}
    print("Step 1: load")
    tac, bro = load_source("tactical"), load_source("broadcast")
    res["tactical"], res["broadcast"] = summarise("tactical", tac), summarise("broadcast", bro)

    print("Step 2: segment the broadcast")
    segments, res["segmentation"] = segment_broadcast()
    L = np.array([b - a + 1 for a, b in segments]) / float(FPS)
    res["segmentation"].update({
        "length_s_pctiles": dict(zip(["min", "p10", "p25", "median", "p75", "p90", "max"],
                                     np.percentile(L, [0, 10, 25, 50, 75, 90, 100]).round(1)
                                     .tolist())),
        "total_min": float(L.sum() / 60)})
    print("  ", res["segmentation"])

    print("Step 3: align")
    tt = Tracks(tac)
    t_sampled = np.arange(0, tt.n, COARSE_STEP)
    res["orientation"] = detect_orientation(Tracks(bro), Tracks(bro, mirror=True), tt,
                                            segments, t_sampled)
    print("  orientation:", res["orientation"])
    bt = Tracks(bro, mirror=res["orientation"]["mirrored"])
    results = []
    for i, (a, b) in enumerate(segments):
        r = align_segment(bt, tt, a, b, t_sampled) or {"a": int(a), "b": int(b), "cost": None}
        results.append(r)
        if i % 20 == 0:
            print("   segment {}/{}  ({:.0f}s)".format(i, len(segments), time.time() - t_start))
    classify(results)
    status = {}
    for r in results:
        status[r["status"]] = status.get(r["status"], 0) + 1
    acc = [r for r in results if r["status"] == "accepted"]
    res["alignment"] = {
        "status_counts": status,
        "accepted_minutes": sum(r["b"] - r["a"] + 1 for r in acc) / float(FPS) / 60.0,
        "accepted_cost_median": float(np.median([r["cost"] for r in acc])),
        "accepted_margin_median": float(np.median([r["runner_cost"] / r["cost"] for r in acc])),
        "accepted_drift_abs_max": max([abs(r["drift"]) for r in acc if r["drift"] is not None]
                                      or [0]),
        "distinct_live_offsets": sorted(set(r["offset"] for r in acc)),
        "segments": results}
    print("  status:", status)
    b_of_t = build_mapping(results, tt.n)

    print("Step 4: validate")
    dist = ball_disagreement(tac, bro, b_of_t)
    res["validation"] = {"frames_both_ball": int(len(dist)),
                         "median_m": float(np.median(dist)),
                         "p75_m": float(np.percentile(dist, 75)),
                         "p90_m": float(np.percentile(dist, 90)),
                         "within_1m_pct": pct((dist < 1).sum(), len(dist)),
                         "within_2m_pct": pct((dist < 2).sum(), len(dist)),
                         "over_5m_pct": pct((dist > 5).sum(), len(dist))}
    print("  ", res["validation"])

    print("Step 5: answer")
    res["answer"] = answer(tac, bro, b_of_t)
    print(json.dumps(res["answer"], indent=1))

    plot_all(results, segments, dist, tac, bro, b_of_t, HERE)
    with open(os.path.join(HERE, "results.json"), "w") as fh:
        json.dump(res, fh, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print("done in {:.0f}s".format(time.time() - t_start))


if __name__ == "__main__":
    main()
