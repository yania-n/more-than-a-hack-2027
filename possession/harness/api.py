"""The harness' method interface. Adding a method never requires editing the harness.

A method is a function

    def my_method(ctx: GameContext) -> numpy.ndarray   # shape (ctx.n_frames,), values 0 H, 1 A, 2 D, 3 X

registered by name from any module:

    from possession.harness.api import register

    @register("always_home")
    def always_home(ctx):
        import numpy as np
        return np.zeros(ctx.n_frames, dtype=np.int8)        # 0 = H

and loaded with  python -m possession.harness.run --plugin my_package.my_module --methods always_home

Rules of the road for a method
  * It sees only tracking (ctx.players, ctx.ball, ctx.pspeed, ctx.team) and the graded half blocks
    (ctx.blocks: [(half, first_frame, last_frame)] inclusive, the analogue of the provided match's published
    graded blocks). It never sees labels. Ball masking / noise for the ball condition is already applied
    to ctx.ball.
  * Frames outside the blocks are not scored; return anything (3 = X is conventional).
  * Run each half independently (no state across the break) like the provided-match pipeline does.
  * ctx.reference() lazily returns the provided-match v1 reference pack (radius, carry speed, bin edges,
    EM parameters) for methods that transfer; ctx.tmp_dir is a scratch folder.
  * Be deterministic (fixed seeds).
"""

from dataclasses import dataclass, field

import numpy as np

METHODS = {}


def register(name):
    def decorator(fn):
        METHODS[name] = fn
        return fn
    return decorator


@dataclass
class GameContext:
    name: str
    fps: float
    pitch: np.ndarray                      # (length, width) m
    players: np.ndarray                    # (N, S, 2) m, NaN = not tracked
    ball: np.ndarray                       # (N, 2) m, NaN = not visible (condition already applied)
    pspeed: np.ndarray                     # (N, S) m/s derived from positions (central difference +-8 frames)
    team: np.ndarray                       # (S,) 0 home / 1 away
    blocks: list                           # [(half, first, last)] graded play intervals, inclusive
    n_frames: int
    condition: str                         # asis / degraded_seed0 / degraded_seed1 / ...
    tmp_dir: str
    reference: object = None               # callable -> v1 reference pack
    set_pieces: list = field(default_factory=list)   # always empty: no Smart Tagging for these games


def run_method(name, ctx):
    if name not in METHODS:
        raise KeyError("unknown method {!r}; registered: {}".format(name, sorted(METHODS)))
    codes = np.asarray(METHODS[name](ctx))
    if codes.shape != (ctx.n_frames,):
        raise ValueError("method {!r} returned shape {}, expected ({},)".format(name, codes.shape, ctx.n_frames))
    if not np.isin(codes, (0, 1, 2, 3)).all():
        raise ValueError("method {!r} returned codes outside 0..3".format(name))
    return codes.astype(np.int8)
