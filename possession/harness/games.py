"""Game loaders for the validation harness: Metrica Sample Games 1, 2 (CSV) and 3 (EPTS + JSON).

Source of all three: Metrica Sports' public sample data, https://github.com/metrica-sports/sample-data
Its README (quoted): "Please be responsible with the use of this data. If you use it for anything
public, please aknowledge the source." The data lives in data/other_games/metrica_sample/ (gitignored)
and is never committed.

A game is a dict:
  name, fps, pitch (length, width m), players (N,S,2) m, ball (N,2) m, team (S,) 0 home / 1 away,
  slot_player ((S,) or (N,S) player ids, for the sync check), periods [(period, first, last)] 0-based
  inclusive frames of the tracking, events: list of dicts (index, team 0/1, type, subs (set of lower-case
  subtype tokens), start, end (0-based frames, end >= start), period, player).
Frame index = Frame (1-based in the files) - 1.
"""

import os

import numpy as np
import pandas as pd

from .. import data

ROOT = data.ROOT
SAMPLE = os.path.join(ROOT, "data", "other_games", "metrica_sample", "data")
CACHE = os.path.join(ROOT, "analysis", "harness", "cache")
PITCH = np.array([105.0, 68.0])
GAMES = ("game1", "game2", "game3")


def _csv_tracking(game_no):
    d = os.path.join(SAMPLE, "Sample_Game_%d" % game_no)
    out = {}
    for side in ("Home", "Away"):
        path = os.path.join(d, "Sample_Game_%d_RawTrackingData_%s_Team.csv" % (game_no, side))
        names = pd.read_csv(path, header=None, skiprows=2, nrows=1).iloc[0].tolist()
        df = pd.read_csv(path, header=None, skiprows=3)
        out[side] = (names, df)
    return out


def load_csv_game(game_no):
    cache = os.path.join(CACHE, "game%d.npz" % game_no)
    os.makedirs(CACHE, exist_ok=True)
    tr = _csv_tracking(game_no)
    (names_h, dfh), (names_a, dfa) = tr["Home"], tr["Away"]
    assert (dfh[0].values == dfa[0].values).all() and (dfh[1].values == dfa[1].values).all()
    frames = dfh[1].values.astype(int)
    assert frames[0] == 1 and (np.diff(frames) == 1).all(), "frames not contiguous from 1"
    n = len(frames)
    ph, pa = (len(names_h) - 5) // 2, (len(names_a) - 5) // 2        # Period, Frame, Time + players + Ball
    def block(df, k):
        x = df.iloc[:, 3:3 + 2 * k].values.astype(float).reshape(n, k, 2)
        return x
    players = np.concatenate([block(dfh, ph), block(dfa, pa)], axis=1) * PITCH
    ball_h = dfh.iloc[:, 3 + 2 * ph:5 + 2 * ph].values.astype(float) * PITCH
    ball_a = dfa.iloc[:, 3 + 2 * pa:5 + 2 * pa].values.astype(float) * PITCH
    both = np.isfinite(ball_h[:, 0]) & np.isfinite(ball_a[:, 0])
    ball_consistent = bool(np.allclose(ball_h[both], ball_a[both]) and
                           (np.isfinite(ball_h[:, 0]) == np.isfinite(ball_a[:, 0])).all())
    slot_player = np.array([names_h[3 + 2 * i] for i in range(ph)] + [names_a[3 + 2 * i] for i in range(pa)])
    team = np.array([0] * ph + [1] * pa, dtype=np.int8)
    period = dfh[0].values.astype(int)
    periods = []
    for p in sorted(set(period)):
        idx = np.flatnonzero(period == p)
        periods.append((int(p), int(idx[0]), int(idx[-1])))
    ev = pd.read_csv(os.path.join(SAMPLE, "Sample_Game_%d" % game_no,
                                  "Sample_Game_%d_RawEventsData.csv" % game_no))
    events = []
    for k, r in ev.iterrows():
        sub = r["Subtype"]
        subs = set(s.strip().lower() for s in str(sub).split("-")) if isinstance(sub, str) else set()
        start = int(r["Start Frame"]) - 1
        end = int(r["End Frame"]) - 1
        events.append(dict(index=k, team=0 if r["Team"] == "Home" else 1, type=r["Type"], subs=subs,
                           start=start, end=max(end, start), period=int(r["Period"]),
                           player=r["From"] if isinstance(r["From"], str) else None))
    fps = float(np.round(1.0 / np.median(np.diff(dfh[2].values.astype(float))), 3))
    return dict(name="game%d" % game_no, fps=fps, pitch=PITCH, players=players, ball=ball_h, team=team,
                slot_player=slot_player, periods=periods, events=events, ball_h_a_consistent=ball_consistent,
                raw_event_end_before_start=int((ev["End Frame"] < ev["Start Frame"]).sum()))


def load_game3():
    from ..pilot import game3
    t = game3.load_tracking()
    return dict(name="game3", fps=25, pitch=PITCH, players=t["players"], ball=t["ball"], team=t["team"],
                slot_player=t["col_player"], periods=[(p, a, b) for p, a, b in game3.half_blocks()],
                events=game3.load_events())


def load_game(name):
    if name == "game3":
        return load_game3()
    return load_csv_game(int(name[-1]))
