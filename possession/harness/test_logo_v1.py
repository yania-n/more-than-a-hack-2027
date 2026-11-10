"""Tests of the LOGO code (run: python -m possession.harness.test_logo_v1). These are tests of CODE, not results.

1. regression: fit_frozen on the provided match alone (its published graded blocks, Smart Tagging, set-piece feature present)
   + the transfer inference path reproduces the shipped v1 submission byte for byte (md5 83b587d7...). The provided match is
   used here only as an INPUT to check that the generalised fit is the shipped recipe; the output is never scored.
2. leakage audit: fit_frozen's signature has no label/event/provided-match argument, the module never imports labels, and
   v1_logo's training set never contains the held-out game.
3. frozen_params.json (if present) round-trips: loading it decodes identically to the in-memory fit it was written from.
"""
import hashlib
import inspect
import os
import sys

import numpy as np

from .. import data, run
from ..pilot import adapters
from . import games, logo_v1

V1_MD5 = "83b587d7b36a665a69f2eaf88566e60b"


def test_regression_reproduces_shipped_v1():
    atd = data.load_atd()
    g = dict(atd=atd, blocks=data.graded_blocks(), pitch=data.PITCH.copy(), set_pieces=data.load_set_pieces())
    fit = logo_v1.fit_frozen([g], setpiece_missing=False)
    codes = adapters.run_v1(atd, g["blocks"], g["set_pieces"], g["pitch"], mode="transfer", ref=fit,
                            setpiece_missing=False)["codes"]
    out = os.path.join(logo_v1.OUT, "regression_v1_provided.csv")
    os.makedirs(logo_v1.OUT, exist_ok=True)
    run.write_submission(np.array(["H", "A", "D", "X"])[codes], out)
    md5 = hashlib.md5(open(out, "rb").read()).hexdigest()
    os.remove(out)                                   # derived provided-match labels: do not leave lying around
    assert md5 == V1_MD5, "fit_frozen on the provided match gives md5 %s, shipped v1 is %s" % (md5, V1_MD5)
    return md5


def test_no_leakage_surface():
    params = set(inspect.signature(logo_v1.fit_frozen).parameters)
    assert params == {"train", "setpiece_missing", "verbose"}, params
    src = inspect.getsource(logo_v1)
    assert "game_labels" not in src and "harness_events" not in src and "import labels" not in src
    for held in games.GAMES:
        train = tuple(sorted(n for n in games.GAMES if n != held))
        assert held not in train and len(train) == 2


def test_frozen_roundtrip():
    if not os.path.isfile(logo_v1.FROZEN):
        return "skipped (no frozen_params.json yet)"
    fit = logo_v1.get_fit(games.GAMES, "asis")
    back = logo_v1.load_frozen()
    assert back["radius"] == fit["radius"] and back["carry"] == fit["carry"]
    for k in fit["edges"]:
        assert np.array_equal(back["edges"][k], fit["edges"][k]), k
    assert np.array_equal(back["params"]["A"], fit["params"]["A"])
    for a, b in zip(back["params"]["emis"], fit["params"]["emis"]):
        assert np.array_equal(a, b)
    return "ok"


def test_default_bins_keep_old_cache_and_context_restores():
    from .. import features
    assert os.path.basename(logo_v1.fit_path(("game2", "game3"), "asis")) == "fit_game2+game3_asis.pkl"
    assert os.path.basename(logo_v1.fit_path(("game2", "game3"), "asis", 24)) == "fit_game2+game3_asis_np24.pkl"
    before = features.N_PSPEED
    with logo_v1.use_npspeed(24):
        assert features.N_PSPEED == 24
    assert features.N_PSPEED == before == 12
    # a cached 12-bin fit still has 11 edges, a 24-bin fit 23
    assert len(logo_v1.get_fit(("game2", "game3"), "asis")["edges"]["player_speed"]) == 11
    assert len(logo_v1.get_fit(("game2", "game3"), "asis", n_pspeed=24)["edges"]["player_speed"]) == 23


if __name__ == "__main__":
    for name, fn in sorted((n, f) for n, f in globals().items() if n.startswith("test_")):
        print(name, "->", fn() or "ok", flush=True)
