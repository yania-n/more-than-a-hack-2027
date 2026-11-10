"""Diagnose where baseline_smooth50 loses points on the public 5-minute window.

    .venv/Scripts/python.exe analysis/diagnose_smooth50/diagnose.py

Diagnosis only. The public ground truth is read to UNDERSTAND errors, never to choose a parameter:
no constant in this file was picked by looking at a score. The few fixed numbers below are either
taken from the baseline itself (its +-50-frame window) or are reporting conventions (1 s = 25
frames for "long" stretches and "meaningful" overlaps), stated where they are defined.

Every metric goes through evaluation/possession_metrics.py so the numbers agree with the scorer;
the script asserts that it reproduces the published report before going further.

Writes only under analysis/diagnose_smooth50/ (gitignored): cache/, timeline.png, results.json,
tables/*.csv. REPORT.md is written by hand from results.json.
"""

import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for p in (ROOT, os.path.join(ROOT, "evaluation"), os.path.join(ROOT, "starter")):
    sys.path.insert(0, p)

import possession_metrics as pm  # noqa: E402
from games import GAME, GAMES  # noqa: E402
import load_atd  # noqa: E402
import load_smart_tagging  # noqa: E402

# Params
SUBMISSION = "baseline_smooth50"
PRED_PATH = os.path.join(ROOT, "evaluation", "results", SUBMISSION + ".csv")
GT_PATH = os.path.join(ROOT, "evaluation", "gt", "BAR-ATH_possession_gt_public.csv")
REPORT_JSON = os.path.join(ROOT, "evaluation", "reports", SUBMISSION + ".json")
CACHE = os.path.join(HERE, "cache")
TABLES = os.path.join(HERE, "tables")
FPS = GAMES[GAME]["fps"]
PITCH = np.array(GAMES[GAME]["pitch"])
WINDOW = 50               # the baseline's own half-window (starter/baseline.py VARIANTS)
LONG = FPS                # error stretches longer than 1 s get the full "why" treatment
MIN_OVERLAP = FPS         # an overlap shorter than 1 s does not count as a split/merge piece
NEAR = WINDOW             # "near a transition" = within the smoothing half-window of one
TRACK_MARGIN = 2 * WINDOW # tracking loaded this far either side of the graded window
IOU = pm.SPELL_IOU_HEADLINE
CODE = {0: "H", 1: "A", 2: "D", 3: "X"}
ST_TEAM = {"Barcelona": "H", "Atletic Club": "A"}
# Smart Tagging writes every phase twice: once for the attacking side and once as a mirrored
# DEFENDING... / DEFENSIVE TRANSITION instance for the other team. Only the first says who has
# the ball, so the mirrors are left out of team attribution.
ST_MIRROR_PREFIX = ("DEFENDING", "DEFENSIVE")


# ---------------------------------------------------------------------------------------------
# inputs
# ---------------------------------------------------------------------------------------------

def load_labels():
    gt = pm.label_codes(pm.read_label_csv(GT_PATH))
    pred = pm.label_codes(pm.read_label_csv(PRED_PATH))
    runs = pm.valid_runs(gt)
    filled = pm.fill_abstentions(pred, runs)
    return gt, pred, filled, runs


def load_tracking(lo, hi):
    """Ball, players and speeds for video frames [lo, hi), cached as .npz under cache/."""
    path = os.path.join(CACHE, "tactical_{}_{}.npz".format(lo, hi))
    if os.path.isfile(path):
        z = np.load(path)
        return {k: z[k] for k in z.files}
    dataset = load_atd.load(source="tactical")
    df = dataset.to_df()
    team_of = {}
    for k, team in enumerate(dataset.metadata.teams):
        for player in team.players:
            team_of[str(player.player_id)] = k
    slots = sorted(team_of, key=int)
    df = df.assign(video_frame=df["frame_id"].astype(int) - 1)
    df = df[(df["video_frame"] >= lo) & (df["video_frame"] < hi)].sort_values("video_frame")
    assert np.array_equal(df["video_frame"].values, np.arange(lo, hi))
    out = {
        "ball": df[["ball_x", "ball_y"]].values.astype(np.float64) * PITCH,
        "players": np.stack([df[[s + "_x", s + "_y"]].values for s in slots], 1) * PITCH,
        "speed": np.stack([df[s + "_s"].values for s in slots], 1).astype(np.float64),
        "team": np.array([team_of[s] for s in slots], dtype=np.int8),
    }
    os.makedirs(CACHE, exist_ok=True)
    np.savez_compressed(path, **out)
    return out


def nearest_player(tr):
    """Raw step 1 of the baseline: team of the nearest tracked player, -1 if no ball/players.
    Also the distance from the ball to the nearest home and nearest away player (NaN if none)."""
    d = np.hypot(*(tr["players"] - tr["ball"][:, None, :]).transpose(2, 0, 1))
    d_home = np.nanmin(np.where(tr["team"] == 0, d, np.inf), 1)
    d_away = np.nanmin(np.where(tr["team"] == 1, d, np.inf), 1)
    d_home[~np.isfinite(d_home)] = np.nan
    d_away[~np.isfinite(d_away)] = np.nan
    raw = np.full(len(d), -1, dtype=np.int8)
    ok = np.isfinite(d_home) | np.isfinite(d_away)
    raw[ok] = np.where(np.nan_to_num(d_home[ok], nan=np.inf)
                       <= np.nan_to_num(d_away[ok], nan=np.inf), 0, 1)
    return raw, d_home, d_away


def resmooth(raw, window):
    """starter/baseline.py smooth(), on codes 0/1/-1, returning pm codes. Used only to check
    that the tracking loaded here reproduces the submission exactly."""
    home = np.r_[0, np.cumsum(raw == 0)]
    away = np.r_[0, np.cumsum(raw == 1)]
    i = np.arange(len(raw))
    lo, hi = np.maximum(0, i - window), np.minimum(len(raw), i + window + 1)
    h, a = home[hi] - home[lo], away[hi] - away[lo]
    return np.where(h + a == 0, pm.D, np.where(h >= a, pm.H, pm.A)).astype(np.int8)


# ---------------------------------------------------------------------------------------------
# possession level
# ---------------------------------------------------------------------------------------------

def greedy_pairs(overlaps, threshold):
    """The scorer's one-to-one greedy match (pm.matched_gt_flags), returning the pairs."""
    pairs, used_g, used_p = {}, set(), set()
    for iou, g, p in overlaps:
        if iou < threshold:
            break
        if g in used_g or p in used_p:
            continue
        used_g.add(g)
        used_p.add(p)
        pairs[g] = p
    return pairs


def overlap(a0, a1, b0, b1):
    return max(0, min(a1, b1) - max(a0, b0))


def composition(codes, a, b):
    """% of frames [a, b) carrying each label."""
    c = np.bincount(codes[a:b], minlength=4)
    return "H {:.0f} / A {:.0f} / D {:.0f}".format(*(100.0 * c[:3] / (b - a)))


def classify_spell(spell, side, other_codes, other_spells, own_spells):
    """Class of a spell left unmatched at IoU 0.5. side is "gt" or "pred".

    Counterparts are same-team spells on the other side that overlap it; a "meaningful" one
    overlaps by at least MIN_OVERLAP (1 s).

    no counterpart at all  -> "wrong team" if the other side has those frames mostly as the
                              other team, else "missed" (GT side) / "spurious" (pred side) --
                              the other side calls it dead ball
    >= 2 meaningful        -> GT side: "split" (one GT possession broken into several preds)
                              pred side: "merged" (one pred covers several GT possessions)
    best counterpart itself has >= 2 meaningful counterparts on this side
                           -> GT side: "merged" (that pred also covers other GT possessions)
                              pred side: "split" (this pred is one fragment of a GT possession)
    otherwise              -> "boundary": right team, overlaps, start/end off
    """
    a, b, team = spell
    same = [j for j, (c, d, k) in enumerate(other_spells)
            if k == team and overlap(a, b, c, d) > 0]
    if not same:
        comp = np.bincount(other_codes[a:b], minlength=4)
        other_team = pm.A if team == pm.H else pm.H
        if comp[other_team] >= comp[pm.D]:
            return "wrong team"
        return "missed" if side == "gt" else "spurious"
    meaningful = [j for j in same if overlap(a, b, *other_spells[j][:2]) >= MIN_OVERLAP]
    if len(meaningful) >= 2:
        return "split" if side == "gt" else "merged"
    best = max(same, key=lambda j: overlap(a, b, *other_spells[j][:2]))
    c, d, _ = other_spells[best]
    covered = [k for k, (e, f, t) in enumerate(own_spells)
               if t == team and overlap(c, d, e, f) >= MIN_OVERLAP]
    if len(covered) >= 2:
        return "merged" if side == "gt" else "split"
    return "boundary"


def spell_tables(gt, filled, runs):
    gs = pm.possession_spells(gt, runs)
    ps = pm.possession_spells(filled, runs)
    ov = pm.spell_overlaps(gs, ps)
    # sanity: our greedy == the scorer's
    pairs = greedy_pairs(ov, IOU)
    assert np.array_equal(pm.matched_gt_flags(ov, len(gs), IOU),
                          np.array([g in pairs for g in range(len(gs))]))
    inv = {p: g for g, p in pairs.items()}
    n_thr_g = {g: sum(g in greedy_pairs(ov, t) for t in pm.SPELL_IOUS) for g in range(len(gs))}
    pairs_by_t = {t: greedy_pairs(ov, t) for t in pm.SPELL_IOUS}
    n_thr_p = {p: sum(p in set(pairs_by_t[t].values()) for t in pm.SPELL_IOUS)
               for p in range(len(ps))}

    def best(i, side):
        cands = [(iou, (p if side == "gt" else g)) for iou, g, p in ov
                 if (g if side == "gt" else p) == i]
        return max(cands) if cands else (0.0, None)

    rows_g, rows_p = [], []
    for i, (a, b, k) in enumerate(gs):
        iou, j = best(i, "gt")
        matched = i in pairs
        cls = "" if matched else classify_spell((a, b, k), "gt", filled, ps, gs)
        rows_g.append({"gt": "G{}".format(i + 1), "start": a, "end": b - 1,
                       "dur_s": round((b - a) / FPS, 1), "team": CODE[k],
                       "best_pred": "P{}".format(j + 1) if j is not None else "-",
                       "iou": round(iou, 3), "matched@0.5": matched,
                       "thresholds_matched": n_thr_g[i], "class": cls,
                       "pred_frames_%HAD": composition(filled, a, b)})
    for j, (a, b, k) in enumerate(ps):
        iou, i = best(j, "pred")
        matched = j in inv
        cls = "" if matched else classify_spell((a, b, k), "pred", gt, gs, ps)
        rows_p.append({"pred": "P{}".format(j + 1), "start": a, "end": b - 1,
                       "dur_s": round((b - a) / FPS, 1), "team": CODE[k],
                       "best_gt": "G{}".format(i + 1) if i is not None else "-",
                       "iou": round(iou, 3), "matched@0.5": matched,
                       "thresholds_matched": n_thr_p[j], "class": cls,
                       "gt_frames_%HAD": composition(gt, a, b)})
    return gs, ps, rows_g, rows_p


# ---------------------------------------------------------------------------------------------
# frame level
# ---------------------------------------------------------------------------------------------

def error_type(g, p):
    if g == p:
        return None
    if g in (pm.H, pm.A) and p == pm.D:
        return "alive->dead"
    if g == pm.D and p in (pm.H, pm.A):
        return "dead->alive"
    if g in (pm.H, pm.A) and p in (pm.H, pm.A):
        return "wrong team"
    return "abstain"  # pred X on a graded frame; baseline writes none


def frame_causes(etype, ball, raw, gt_win):
    """Per-frame mechanism, from the baseline's own two steps (nearest player, then vote)."""
    cause = np.full(len(etype), "", dtype=object)
    for i, t in enumerate(etype):
        if t is None:
            continue
        if t == "dead->alive":
            cause[i] = "ball seen during stoppage" if ball[i] else \
                "ball missing; vote bleeds alive label in"
        elif t == "alive->dead":
            cause[i] = "ball missing for whole +-50 window"
        elif t == "wrong team":
            if not ball[i]:
                cause[i] = "ball missing; vote inherits neighbour label"
            elif raw[i] == gt_win[i]:
                cause[i] = "nearest player right; vote overrides"
            elif raw[i] < 0:
                cause[i] = "ball seen, no players"
            else:
                cause[i] = "nearest player is the other team"
    return cause


def stretches(gt_w, pred_w):
    """Maximal runs of one (gt, pred) error pair. Indices relative to the window."""
    out = []
    i, n = 0, len(gt_w)
    while i < n:
        if gt_w[i] == pred_w[i]:
            i += 1
            continue
        j = i
        while j < n and gt_w[j] == gt_w[i] and pred_w[j] == pred_w[i]:
            j += 1
        out.append((i, j))
        i = j
    return out


def st_overlaps(events, a, b):
    """Smart Tagging instances overlapping video frames [a, b), mirrors excluded."""
    out = []
    for e in events:
        if e["code"].upper().startswith(ST_MIRROR_PREFIX):
            continue
        if overlap(a, b, e["start_frame"], e["end_frame"]) > 0:
            team = e["tags"].get("Team", "")
            typ = e["tags"].get("Type")
            out.append("{}{} [{}]".format(e["code"], " / " + typ if typ else "",
                                          ST_TEAM.get(team, team)))
    return out


def oracle(gt, filled, runs, mask):
    """spellF1 / macroF1 / #spells if the frames in mask were given the GT label."""
    fixed = filled.copy()
    fixed[mask] = gt[mask]
    s = pm.spell_scores(gt, fixed, runs)
    return {"spell_f1_mean": round(s["mean_f1"], 4),
            "macro_f1": round(pm.macro_f1(pm.scored_confusion(pm.confusion(gt, fixed))), 4),
            "n_pred_spells": s["n_pred"], "frames_fixed": int(mask.sum())}


# ---------------------------------------------------------------------------------------------
# plot
# ---------------------------------------------------------------------------------------------

COL = {"H": "#2a78d6", "A": "#eb6834", "D": "#a3a29c", "X": "#ffffff"}
ERR_COL = {"dead->alive": "#1baf7a", "alive->dead": "#eda100", "wrong team": "#e87ba4"}
INK, INK2 = "#0b0b0b", "#52514e"


def bands(ax, y, codes, x0, h=0.8):
    """Draw constant-label runs of codes (pm codes) as a horizontal band at row y."""
    edges = np.flatnonzero(np.diff(codes)) + 1
    starts = np.r_[0, edges]
    ends = np.r_[edges, len(codes)]
    for s, e in zip(starts, ends):
        ax.broken_barh([((x0 + s) / FPS, (e - s) / FPS)], (y - h / 2, h),
                       facecolors=COL[CODE[int(codes[s])]], edgecolor="none")


def plot_timeline(lo, hi, gt, pred, ball_w, etype_w, long_stretches, events, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    fig, ax = plt.subplots(figsize=(15, 6))
    x0 = lo
    # rows (top to bottom): GT, errors, prediction, ball, Smart Tagging lanes
    bands(ax, 6, gt[lo:hi], x0)
    bands(ax, 4, pred[lo:hi], x0)
    # error band
    for t, col in ERR_COL.items():
        m = np.array([e == t for e in etype_w]).astype(np.int8)
        edges = np.flatnonzero(np.diff(np.r_[0, m, 0]))
        ax.broken_barh([((x0 + s) / FPS, (e - s) / FPS) for s, e in zip(edges[::2], edges[1::2])],
                       (4.75, 0.5), facecolors=col, edgecolor="none")
    # ball band
    m = ball_w.astype(np.int8)
    edges = np.flatnonzero(np.diff(np.r_[0, m, 0]))
    ax.broken_barh([(0 + (x0) / FPS, (hi - lo) / FPS)], (2.6, 0.8), facecolors="#ecebe6")
    ax.broken_barh([((x0 + s) / FPS, (e - s) / FPS) for s, e in zip(edges[::2], edges[1::2])],
                   (2.6, 0.8), facecolors=INK2, edgecolor="none")
    # Smart Tagging, greedy lanes, attacking-side instances only
    evs = sorted([e for e in events if not e["code"].upper().startswith(ST_MIRROR_PREFIX)
                  and e["end_frame"] > lo and e["start_frame"] < hi],
                 key=lambda e: e["start_frame"])
    lane_end = []
    for e in evs:
        s, f = max(e["start_frame"], lo), min(e["end_frame"], hi)
        for k, end in enumerate(lane_end):
            if end <= s:
                lane_end[k] = f
                break
        else:
            k = len(lane_end)
            lane_end.append(f)
        y = 1.6 - 0.42 * k
        team = ST_TEAM.get(e["tags"].get("Team", ""), "D")
        ax.broken_barh([(s / FPS, (f - s) / FPS)], (y - 0.17, 0.34), facecolors=COL[team],
                       edgecolor="white", linewidth=1, alpha=0.75)
        label = e["code"].title().replace("Ball In ", "").replace("Players In The Box", "PitB")
        ax.text(s / FPS + 0.5, y, label, fontsize=6, va="center", color=INK, clip_on=True)
    # long error stretches: thin outline over GT+pred rows
    for a, b in long_stretches:
        ax.axvspan((x0 + a) / FPS, (x0 + b) / FPS, ymin=0.48, ymax=0.99, facecolor="none",
                   edgecolor=INK, linewidth=0.6, linestyle=":")
    y_min = 1.6 - 0.42 * max(len(lane_end), 1) - 0.2
    ax.set_ylim(y_min, 6.6)
    ax.set_xlim(lo / FPS, hi / FPS)
    ax.set_yticks([6, 5, 4, 3, 1.6 - 0.42 * (len(lane_end) - 1) / 2])
    ax.set_yticklabels(["ground truth", "error", SUBMISSION, "ball in ATD", "Smart Tagging"],
                       color=INK2, fontsize=9)
    ticks = np.arange(np.ceil(lo / FPS / 15) * 15, hi / FPS, 15)
    ax.set_xticks(ticks)
    ax.set_xticklabels(["{:d}:{:02d}\n{}".format(int(t // 60), int(t % 60), int(t * FPS))
                        for t in ticks], fontsize=7, color=INK2)
    ax.set_xlabel("video time (m:ss) / video frame", color=INK2, fontsize=9)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.tick_params(axis="y", length=0)
    handles = [Patch(color=COL["H"], label="H (home)"), Patch(color=COL["A"], label="A (away)"),
               Patch(color=COL["D"], label="D (dead)"),
               Patch(color=INK2, label="ball present")] + \
              [Patch(color=c, label="error: " + t) for t, c in ERR_COL.items()] + \
              [Patch(facecolor="none", edgecolor=INK, linestyle=":", label="error stretch > 1 s")]
    ax.legend(handles=handles, ncol=8, fontsize=7, frameon=False, loc="upper center",
              bbox_to_anchor=(0.5, -0.17))
    ax.set_title("baseline_smooth50 vs public ground truth (Smart Tagging bars coloured by the "
                 "Team tag; grey = N/A)", fontsize=10, color=INK, loc="left", pad=8)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


# ---------------------------------------------------------------------------------------------
# full-match, label-free sanity numbers (no ground truth involved)
# ---------------------------------------------------------------------------------------------

def unlabeled_stats(pred):
    from games import half_video_blocks
    runs = [(a, b + 1) for _, a, b in half_video_blocks(GAME)]
    spells = pm.possession_spells(pred, runs)
    L = np.array([b - a for a, b, _ in spells]) / float(FPS)
    trans = pm.transitions(pred, runs)
    minutes = sum(b - a for a, b in runs) / float(FPS) / 60
    graded = np.concatenate([pred[a:b] for a, b in runs])
    return {"n_spells": len(spells), "spells_per_min": round(len(spells) / minutes, 2),
            "mean_spell_s": round(float(L.mean()), 1),
            "median_spell_s": round(float(np.median(L)), 1),
            "spells_under_2s_pct": round(100.0 * (L < 2).mean(), 1),
            "transitions_per_min": round(len(trans) / minutes, 2),
            "pred_D_pct": round(100.0 * (graded == pm.D).mean(), 1)}


# ---------------------------------------------------------------------------------------------

def main():
    os.makedirs(TABLES, exist_ok=True)
    res = {}
    gt, pred, filled, runs = load_labels()
    assert len(runs) == 1, "public GT is one graded window"
    lo, hi = runs[0]
    res["window"] = {"first": lo, "last": hi - 1, "frames": hi - lo}

    # agree with the published report before anything else
    ev = pm.evaluate(gt, pred)
    with open(REPORT_JSON) as fh:
        published = json.load(fh)
    for k in ("macro_f1", "spell_f1_mean", "n_pred_spells", "n_gt_spells"):
        assert abs(ev[k] - published[k]) < 1e-9, k
    res["scores"] = {k: ev[k] for k in ("macro_f1", "spell_f1_mean", "n_gt_spells",
                                        "n_pred_spells", "mean_spell_duration_s",
                                        "gt_mean_spell_duration_s", "alive_dead_f1",
                                        "team_acc_both_alive")}
    res["scores"]["spell_f1_per_iou"] = {str(t): round(v["f1"], 4)
                                         for t, v in ev["spell_f1"].items()}

    # ---- 1. confusion and error groups
    cm3 = pm.scored_confusion(pm.confusion(gt, pred))
    res["confusion"] = {"rows_gt": ["H", "A", "D"], "cols_pred": ["H", "A", "D", "X"],
                        "matrix": cm3.tolist()}
    gt_w, pred_w = gt[lo:hi], filled[lo:hi]
    etype = [error_type(g, p) for g, p in zip(gt_w, pred_w)]
    n_err = sum(e is not None for e in etype)
    groups = {}
    for t in ("alive->dead", "dead->alive", "wrong team", "abstain"):
        c = sum(e == t for e in etype)
        groups[t] = {"frames": c, "pct_of_errors": round(100.0 * c / n_err, 1)}
    res["errors"] = {"total": n_err, "pct_of_graded": round(100.0 * n_err / (hi - lo), 1),
                     "groups": groups}

    # ---- tracking context
    t_lo, t_hi = lo - TRACK_MARGIN, hi + TRACK_MARGIN
    tr = load_tracking(t_lo, t_hi)
    raw_all, dh_all, da_all = nearest_player(tr)
    ball_all = ~np.isnan(tr["ball"][:, 0])
    # the tracking loaded here must reproduce the submission on every graded frame
    assert np.array_equal(resmooth(raw_all, WINDOW)[lo - t_lo:hi - t_lo], pred_w), \
        "re-smoothed nearest-player codes do not reproduce the submission"
    sl = slice(lo - t_lo, hi - t_lo)
    raw, ball, dh, da = raw_all[sl], ball_all[sl], dh_all[sl], da_all[sl]
    speed = np.nanmean(tr["speed"][sl], 1)
    gt_team = np.where(gt_w == pm.H, 0, np.where(gt_w == pm.A, 1, -9))

    cause = frame_causes(etype, ball, raw, gt_team)
    causes = {}
    for t in ("dead->alive", "alive->dead", "wrong team"):
        sub = [c for e, c in zip(etype, cause) if e == t]
        causes[t] = {c: sub.count(c) for c in sorted(set(sub))}
    res["error_causes"] = causes

    # raw nearest-player accuracy, ball visible & GT alive -- the geometry on its own
    vis_alive = ball & (gt_team >= 0) & (raw >= 0)
    res["raw_nearest_player"] = {
        "frames_ball_visible_gt_alive": int(vis_alive.sum()),
        "team_correct_pct": round(100.0 * (raw[vis_alive] == gt_team[vis_alive]).mean(), 1),
        "ball_present_pct_gt_alive": round(100.0 * ball[gt_team >= 0].mean(), 1),
        "ball_present_pct_gt_dead": round(100.0 * ball[gt_w == pm.D].mean(), 1)}

    # frame-level summary of circumstances
    gt_trans = np.array([f for f, _, _ in pm.transitions(gt, runs)])
    dist_tr = np.min(np.abs(np.arange(lo, hi)[:, None] - gt_trans[None, :]), 1)
    is_err = np.array([e is not None for e in etype])
    res["error_circumstances"] = {
        "error_frames_ball_missing_pct": round(100.0 * (~ball[is_err]).mean(), 1),
        "all_frames_ball_missing_pct": round(100.0 * (~ball).mean(), 1),
        "error_frames_within_2s_of_gt_transition_pct":
            round(100.0 * (dist_tr[is_err] <= NEAR).mean(), 1),
        "all_frames_within_2s_of_gt_transition_pct": round(100.0 * (dist_tr <= NEAR).mean(), 1),
        "error_frames_during_gt_dead_pct": round(100.0 * (gt_w[is_err] == pm.D).mean(), 1),
        "all_frames_gt_dead_pct": round(100.0 * (gt_w == pm.D).mean(), 1)}

    # ---- 2. possession level
    gs, ps, rows_g, rows_p = spell_tables(gt, filled, runs)
    pd.DataFrame(rows_g).to_csv(os.path.join(TABLES, "gt_possessions.csv"), index=False)
    pd.DataFrame(rows_p).to_csv(os.path.join(TABLES, "pred_possessions.csv"), index=False)
    res["gt_possessions"], res["pred_possessions"] = rows_g, rows_p
    res["class_counts"] = {
        "gt_unmatched": pd.Series([r["class"] for r in rows_g if not r["matched@0.5"]])
        .value_counts().to_dict(),
        "pred_unmatched": pd.Series([r["class"] for r in rows_p if not r["matched@0.5"]])
        .value_counts().to_dict()}

    # ---- 3. error stretches
    events = load_smart_tagging.load()
    rows = []
    long_st = []
    for a, b in stretches(gt_w, pred_w):
        if b - a <= LONG:
            continue
        long_st.append((a, b))
        sel = slice(a, b)
        bv = ball[sel]
        cs = pd.Series(cause[sel]).value_counts()
        dt = int(dist_tr[a:b].min())
        rows.append({
            "start": lo + a, "end": lo + b - 1, "dur_s": round((b - a) / FPS, 1),
            "type": "{}->{} ({})".format(CODE[gt_w[a]], CODE[pred_w[a]], etype[a]),
            "ball_present_%": round(100.0 * bv.mean(), 0),
            "ball_to_home_m": round(float(np.nanmean(dh[sel][bv])), 1) if bv.any() else None,
            "ball_to_away_m": round(float(np.nanmean(da[sel][bv])), 1) if bv.any() else None,
            "mean_speed_mps": round(float(np.nanmean(speed[sel])), 2),
            "frames_to_gt_transition": dt,
            "main_cause": "{} ({:.0f}%)".format(cs.index[0], 100.0 * cs.iloc[0] / (b - a)),
            "smart_tagging": "; ".join(st_overlaps(events, lo + a, lo + b)) or "-"})
    res["long_stretches"] = rows
    pd.DataFrame(rows).to_csv(os.path.join(TABLES, "error_stretches.csv"), index=False)
    long_mask = np.zeros(hi - lo, dtype=bool)
    for a, b in long_st:
        long_mask[a:b] = True
    res["long_stretch_share_of_error_frames_pct"] = round(100.0 * long_mask[is_err].mean(), 1)
    res["speed_context"] = {
        "mean_speed_gt_alive": round(float(np.nanmean(speed[gt_w != pm.D])), 2),
        "mean_speed_gt_dead": round(float(np.nanmean(speed[gt_w == pm.D])), 2)}

    # ---- oracle ablations: which error type costs the most spellF1?
    def mask_of(pred_fn):
        m = np.zeros(len(gt), dtype=bool)
        m[lo:hi] = pred_fn
        return m
    et = np.array([e or "" for e in etype], dtype=object)
    cz = cause.astype(str)
    near = dist_tr <= NEAR
    # Whole wrong-team stretches (not single frames, so the oracle cannot fragment a run) split
    # by whether the stretch starts or ends on a GT transition (+-1 frame) -- a late/early
    # hand-over -- or sits strictly inside one GT possession -- a flip that splits it.
    gt_tr_rel = set((gt_trans - lo).tolist())
    wt_at_handover = np.zeros(hi - lo, dtype=bool)
    n_wt = {"at_handover": 0, "inside_possession": 0}
    for a, b in stretches(gt_w, pred_w):
        if etype[a] != "wrong team":
            continue
        touches = any(abs(a - t) <= 1 or abs(b - t) <= 1 for t in gt_tr_rel)
        wt_at_handover[a:b] = touches
        n_wt["at_handover" if touches else "inside_possession"] += b - a
    res["wrong_team_frames_by_position"] = n_wt
    # Possessions a centred +-WINDOW majority vote can barely represent: shorter than its width.
    vote_width = 2 * WINDOW + 1
    res["gt_spells_shorter_than_vote_window"] = {
        "vote_width_frames": vote_width,
        "n": sum(1 for a, b, _ in gs if b - a < vote_width),
        "of": len(gs),
        "matched_at_0.5": sum(1 for (a, b, _), r in zip(gs, rows_g)
                              if b - a < vote_width and r["matched@0.5"])}
    res["oracle"] = {
        "none": oracle(gt, filled, runs, mask_of(np.zeros(hi - lo, bool))),
        "dead->alive": oracle(gt, filled, runs, mask_of(et == "dead->alive")),
        "alive->dead": oracle(gt, filled, runs, mask_of(et == "alive->dead")),
        "all dead-ball errors": oracle(gt, filled, runs,
                                       mask_of((et == "dead->alive") | (et == "alive->dead"))),
        "wrong team: nearest player is the other team":
            oracle(gt, filled, runs, mask_of(cz == "nearest player is the other team")),
        "wrong team: nearest player right, vote overrides":
            oracle(gt, filled, runs, mask_of(cz == "nearest player right; vote overrides")),
        "wrong team: ball missing":
            oracle(gt, filled, runs,
                   mask_of(cz == "ball missing; vote inherits neighbour label")),
        "all wrong team": oracle(gt, filled, runs, mask_of(et == "wrong team")),
        "wrong team stretches touching a GT transition (hand-over timing)":
            oracle(gt, filled, runs, mask_of(wt_at_handover)),
        "wrong team stretches inside a GT possession (mid-spell flips)":
            oracle(gt, filled, runs, mask_of((et == "wrong team") & ~wt_at_handover)),
        # leave-one-out: everything fixed EXCEPT this group -> what this group alone still costs
        "everything except dead->alive": oracle(gt, filled, runs,
                                                mask_of(is_err & (et != "dead->alive"))),
        "everything except alive->dead": oracle(gt, filled, runs,
                                                mask_of(is_err & (et != "alive->dead"))),
        "everything except wrong team": oracle(gt, filled, runs,
                                               mask_of(is_err & (et != "wrong team"))),
        "everything except all dead-ball errors": oracle(gt, filled, runs,
                                                         mask_of(et == "wrong team")),
        "everything except wrong-team hand-over stretches":
            oracle(gt, filled, runs, mask_of(is_err & ~wt_at_handover)),
        "everything except wrong-team mid-spell flips":
            oracle(gt, filled, runs, mask_of(is_err & ~((et == "wrong team") & ~wt_at_handover))),
        "all errors within 2 s of a GT transition": oracle(gt, filled, runs,
                                                           mask_of(is_err & near)),
        "all errors further than 2 s from a GT transition": oracle(gt, filled, runs,
                                                                   mask_of(is_err & ~near)),
    }

    # ---- transition timing: the scorer's matcher at a wide (5 s) reporting tolerance, so the
    # late/early structure is visible instead of everything being "missed" at 0.5-1 s
    pairs, missed, spurious = pm.match_transitions(pm.transitions(gt, runs),
                                                   pm.transitions(filled, runs), 5 * FPS)
    lat = np.array([p[0] - g[0] for g, p in pairs])
    res["transition_timing_5s"] = {
        "gt_transitions": len(pm.transitions(gt, runs)), "matched": len(pairs),
        "missed": len(missed), "spurious": len(spurious),
        "latency_frames": lat.tolist(),
        "median_latency_s": round(float(np.median(lat)) / FPS, 2) if len(lat) else None,
        "late_by_over_1s": int((lat > FPS).sum()), "early_by_over_1s": int((lat < -FPS).sum())}

    # ---- full match, no labels
    res["unlabeled_full_match"] = unlabeled_stats(filled)

    plot_timeline(lo, hi, gt, filled, ball, etype, long_st, events,
                  os.path.join(HERE, "timeline.png"))
    with open(os.path.join(HERE, "results.json"), "w") as fh:
        json.dump(res, fh, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(json.dumps({k: v for k, v in res.items()
                      if k not in ("gt_possessions", "pred_possessions", "long_stretches")},
                     indent=1))


if __name__ == "__main__":
    main()
