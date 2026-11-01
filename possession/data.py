"""Read the tactical ATD and the Smart Tagging into plain numpy arrays (no ground truth).

All coordinates are converted to metres. Frame index = submission row = ATD frame_id - 1.
The parsed ATD is cached under analysis/hmm_v1/cache/ (gitignored), keyed on the raw file.
"""

import os
import sys
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (ROOT, os.path.join(ROOT, "starter")):
    if p not in sys.path:
        sys.path.insert(0, p)

from games import GAME, GAMES, half_video_blocks, require, source_frames  # noqa: E402
import baseline as _baseline  # noqa: E402  (starter/baseline.py; only called, never edited)
import load_smart_tagging as _tags  # noqa: E402

OUT_DIR = os.path.join(ROOT, "analysis", "hmm_v1")
CACHE_DIR = os.path.join(OUT_DIR, "cache")
FPS = GAMES[GAME]["fps"]
PITCH = np.array(GAMES[GAME]["pitch"], dtype=np.float64)  # (length, width) in metres
N_FRAMES = source_frames("tactical", GAME)

HOME, AWAY = 0, 1


def graded_blocks():
    """[(half, first_frame, last_frame)] inclusive, video frames."""
    return half_video_blocks(GAME)


def graded_mask():
    mask = np.zeros(N_FRAMES, dtype=bool)
    for _, a, b in graded_blocks():
        mask[a:b + 1] = True
    return mask


def _cache_key(raw_path):
    with open(raw_path, "rb") as handle:
        head = handle.read(1 << 16)
    return "{}-{}".format(os.path.getsize(raw_path), zlib.crc32(head))


def load_atd():
    """dict: ball (N,2) m, players (N,46,2) m, pspeed (N,46) m/s, bspeed_file (N,), team (46,).

    NaN marks a missing observation. `team` is 0 (home) / 1 (away) per track slot.
    """
    meta_path, raw_path = require(["atd_meta", "atd_raw"], GAME)
    key = _cache_key(raw_path)
    cache = os.path.join(CACHE_DIR, "atd_tactical.npz")
    if os.path.isfile(cache):
        z = np.load(cache, allow_pickle=False)
        if str(z["key"]) == key:
            return {k: z[k] for k in z.files if k != "key"}

    team = _baseline.team_of_each_track(meta_path)
    n_slots = len(team)
    ball = np.full((N_FRAMES, 2), np.nan)
    players = np.full((N_FRAMES, n_slots, 2), np.nan)
    pspeed = np.full((N_FRAMES, n_slots), np.nan)
    bspeed = np.full(N_FRAMES, np.nan)
    seen = np.zeros(N_FRAMES, dtype=bool)
    width = 1 + 3 * n_slots + 3  # frame_id, n_slots x (x,y,s), ball (x,y,s)
    with open(raw_path) as handle:
        for line in handle:
            row = np.fromstring(line.replace(":", ",").replace(";", ","), sep=",")
            if row.size != width:
                raise ValueError("unexpected ATD line width {} (expected {})".format(row.size, width))
            f = int(row[0]) - 1  # frame_id counts from 1
            seen[f] = True
            body = row[1:1 + 3 * n_slots].reshape(n_slots, 3)
            players[f] = body[:, :2] * PITCH
            pspeed[f] = body[:, 2]
            ball[f] = row[-3:-1] * PITCH
            bspeed[f] = row[-1]
    if not seen.all():
        raise ValueError("ATD does not cover every video frame")
    out = dict(ball=ball, players=players, pspeed=pspeed, bspeed_file=bspeed, team=team)
    os.makedirs(CACHE_DIR, exist_ok=True)
    np.savez_compressed(cache, key=np.array(key), **out)
    return out


def load_set_pieces():
    """Smart Tagging restart instances: list of dicts(start_frame, end_frame, type, team, half).

    `team` is 'H', 'A' or None (the tag says N/A -- every throw-in and the kick-offs). Team is
    returned for completeness; v1 does not use it (the indicator is team-blind).
    """
    meta_path = require(["atd_meta"], GAME)[0]
    home, away = _baseline.team_names(meta_path)
    out = []
    for e in _tags.load(GAME):
        if (e["code"] or "").strip().lower() != "set pieces":
            continue
        t = (e["tags"].get("Type") or "").strip().lower()
        team = (e["tags"].get("Team") or "").strip()
        side = "H" if team and team == home else "A" if team and team != "N/A" else None
        out.append(dict(start_frame=e["start_frame"], end_frame=e["end_frame"], type=t,
                        team=side, half=e["tags"].get("Half")))
    return out
