"""Event-based proxy possession labels for Sample Game 3. Rules registered in
analysis/pilot_game3/PREREGISTRATION.md section 3. Everything is by code from the events.

Label codes as in evaluation/possession_metrics.py: 0 H, 1 A, 2 D, 3 X.
"""

import numpy as np

H, A, D, X = 0, 1, 2, 3
CONTROL_TYPES = ("PASS", "CARRY", "SHOT", "RECOVERY", "SET PIECE")
STOP_BALL_LOST_SUBS = ("forced", "offside", "hand ball", "referee hit")


def classify(e, rule):
    """-> (kind, effective_frame). kind in ctrl / stop / endhalf / none."""
    t, subs = e["type"], e["subs"]
    if t == "BALL LOST" and "end half" in subs:
        return "endhalf", e["end"]
    if t in ("BALL OUT", "FAULT RECEIVED"):
        return "stop", e["end"]
    if t == "SHOT" and "goal" in subs:
        return "ctrl_then_stop", e["end"]       # the shot is controlling at its start, stop at its end
    if t == "BALL LOST" and any(s in subs for s in STOP_BALL_LOST_SUBS):
        return "stop", e["end"]
    if t in CONTROL_TYPES:
        return "ctrl", e["start"]
    if t == "CHALLENGE":
        if rule == "S2" and "fault" not in subs:     # a foul is not an on-ball action (PREREG note 1)
            return "ctrl", e["start"]
        if rule == "primary" and "won" in subs:
            return "ctrl", e["start"]
    return "none", e["start"]


def build_labels(events, n_frames, rule="primary"):
    """Per-frame codes (int8) for the whole video; X outside play."""
    assert rule in ("primary", "S1", "S2")
    out = np.full(n_frames, X, dtype=np.int8)
    for period in sorted({e["period"] for e in events}):
        items = []   # (frame, order, kind, team)
        for k, e in enumerate(e for e in events if e["period"] == period):
            kind, t = classify(e, rule)
            if kind == "ctrl_then_stop":
                items.append((e["start"], k, "ctrl", e["team"]))
                items.append((e["end"], k, "stop", e["team"]))
            elif kind != "none":
                items.append((t, k, kind, e["team"]))
        items.sort(key=lambda it: (it[0], it[1]))
        state, breaks = X, []            # breaks: (frame, state)
        end_frame = None
        for i, (t, _, kind, team) in enumerate(items):
            if kind == "endhalf":
                breaks.append((t, X))
                end_frame = t
                break
            if kind == "stop":
                if state in (H, A):
                    state = D
                    breaks.append((t, D))
                continue
            # controlling event
            if rule == "S1" and state in (H, A) and team != state:
                nxt = next((it for it in items[i + 1:] if it[2] in ("ctrl", "stop", "endhalf")), None)
                if nxt is not None and nxt[2] == "ctrl" and nxt[3] == state:
                    continue                        # lone touch followed by the original team: ignore
            if team != state or state == D:
                state = team
                breaks.append((t, team))
        # paint
        for (t, s), nxt in zip(breaks, breaks[1:] + [(end_frame if end_frame is not None else t, X)]):
            out[t:nxt[0]] = s
        if breaks and breaks[-1][1] != X and end_frame is None:
            last = max(e["end"] for e in events if e["period"] == period)
            out[breaks[-1][0]:last + 1] = breaks[-1][1]
    return out
