"""Load Metrica Sample Game 3 (EPTS tracking + JSON events) into numpy arrays.

Source: https://github.com/metrica-sports/sample-data (Metrica Sports). Its README, quoted: "Please be
responsible with the use of this data. If you use it for anything public, please aknowledge the
source." The data lives under data/other_games/metrica_sample/ (gitignored) and is never committed.

Conventions: frame_id counts from 1 in the file; arrays here are indexed by frame_id - 1 (0-based),
the same convention as the provided match. Coordinates are 0-1 in the file, converted to metres with
the 105 x 68 m pitch stated in the sample README. Team A (first Team in the metadata, idLocal) = home = H.
"""

import json
import os
import xml.etree.ElementTree as ET

import numpy as np

from .. import data

ROOT = data.ROOT
GAME_DIR = os.path.join(ROOT, "data", "other_games", "metrica_sample", "data", "Sample_Game_3")
META = os.path.join(GAME_DIR, "Sample_Game_3_metadata.xml")
TRACK = os.path.join(GAME_DIR, "Sample_Game_3_tracking.txt")
EVENTS = os.path.join(GAME_DIR, "Sample_Game_3_events.json")
PITCH = np.array([105.0, 68.0])
FPS = 25
CACHE = os.path.join(ROOT, "analysis", "pilot_game3", "cache")


def _tags(root, suffix):
    return [e for e in root.iter() if e.tag.endswith(suffix)]


def metadata():
    root = ET.parse(META).getroot()
    teams = [e.get("id") for e in _tags(root, "Team")]
    player_team = {e.get("id"): e.get("teamId") for e in _tags(root, "Player") if e.get("teamId")}
    chan = {e.get("id"): e.get("playerId") for e in _tags(root, "PlayerChannel")}
    specs = []
    for spec in _tags(root, "DataFormatSpecification"):
        refs = [r.get("playerChannelId") for r in _tags(spec, "PlayerChannelRef")]
        cols = [chan[r] for r in refs if r.endswith("_x")]
        specs.append((int(spec.get("startFrame")), int(spec.get("endFrame")), cols))
    glob = {p.findtext("Name"): p.findtext("Value") for p in _tags(root, "ProviderParameter")}
    return dict(home_id=teams[0], away_id=teams[1], player_team=player_team, specs=specs,
                first_half=(int(glob["first_half_start"]), int(glob["first_half_end"])),
                second_half=(int(glob["second_half_start"]), int(glob["second_half_end"])))


def load_tracking():
    """dict: ball (N,2) m, players (N,22,2) m, team (22,) 0 home / 1 away, col_player (N,22) player ids."""
    os.makedirs(CACHE, exist_ok=True)
    cache = os.path.join(CACHE, "game3_tracking.npz")
    size = os.path.getsize(TRACK)
    if os.path.isfile(cache):
        z = np.load(cache, allow_pickle=False)
        if int(z["size"]) == size:
            return {k: z[k] for k in z.files if k != "size"}
    md = metadata()
    n = md["second_half"][1]
    ball = np.full((n, 2), np.nan)
    players = np.full((n, 22, 2), np.nan)
    with open(TRACK) as handle:
        for line in handle:
            row = np.fromstring(line.replace(":", ",").replace(";", ","), sep=",")
            if row.size != 1 + 44 + 2:
                raise ValueError("unexpected Game 3 line width {}".format(row.size))
            f = int(row[0]) - 1
            players[f] = row[1:45].reshape(22, 2) * PITCH
            ball[f] = row[45:47] * PITCH
    team = np.array([0] * 11 + [1] * 11, dtype=np.int8)
    for _, _, cols in md["specs"]:   # the column->team split is fixed across the whole match
        t = [0 if md["player_team"][p] == md["home_id"] else 1 for p in cols]
        assert t == team.tolist()
    col_player = np.empty((n, 22), dtype="<U8")
    for a, b, cols in md["specs"]:
        col_player[a - 1:b] = np.array(cols)
    out = dict(ball=ball, players=players, team=team, col_player=col_player)
    np.savez_compressed(cache, size=np.array(size), **out)
    return out


def load_events():
    """List of dicts: team (0 home/1 away), type, subs (set of lower-case subtype names), start, end
    (0-based frames, same index as the arrays), period, player (id)."""
    md = metadata()
    raw = json.load(open(EVENTS))["data"]
    out = []
    for e in raw:
        s = e.get("subtypes")
        if s is None:
            subs = set()
        elif isinstance(s, dict):
            subs = {s["name"].lower()}
        else:
            subs = {x["name"].lower() for x in s}
        out.append(dict(index=e["index"], team=0 if e["team"]["id"] == md["home_id"] else 1,
                        type=e["type"]["name"], subs=subs,
                        start=int(e["start"]["frame"]) - 1, end=int(e["end"]["frame"]) - 1,
                        period=int(e["period"]), player=(e.get("from") or {}).get("id")))
    return out


def half_blocks():
    md = metadata()
    return [(1, md["first_half"][0] - 1, md["first_half"][1] - 1),
            (2, md["second_half"][0] - 1, md["second_half"][1] - 1)]
