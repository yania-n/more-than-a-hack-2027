"""Validate the adapters on the PROVIDED match before trusting them on another game.
    python -m possession.pilot.validate_adapters   ->  analysis/pilot_game3/validate/validation.json
"""

import hashlib
import json
import os

import numpy as np

from .. import data, features, run
from . import adapters

OUT = os.path.join(data.ROOT, "analysis", "pilot_game3", "validate")
V1_MD5 = "83b587d7b36a665a69f2eaf88566e60b"


def md5_text(path):
    """md5 of the file with Windows line endings normalised (the repo CSVs may be LF or CRLF)."""
    raw = open(path, "rb").read()
    return hashlib.md5(raw).hexdigest(), hashlib.md5(raw.replace(b"\r\n", b"\n")).hexdigest()


def same(a, b):
    return bool(np.array_equal(a, b, equal_nan=True))


def main():
    os.makedirs(OUT, exist_ok=True)
    res = {}
    meta_path, raw_path = data.require(["atd_meta", "atd_raw"], data.GAME)
    # 1. smooth50 through the adapter on the provided match
    team = adapters.baseline.team_of_each_track(meta_path)
    codes = adapters.smooth50_codes(raw_path, team, data.N_FRAMES, data.GAMES[data.GAME]["pitch"])
    mine = os.path.join(OUT, "smooth50_provided.csv")
    run.write_submission(np.array(["H", "A", "D", "X"])[codes], mine)
    ref = os.path.join(data.ROOT, "evaluation", "results", "baseline_smooth50.csv")
    ref_codes = np.array([{"H": 0, "A": 1, "D": 2}[l.strip().split(",")[1]]
                          for l in open(ref).read().split("\n")[1:] if l.strip()], dtype=np.int8)
    res["smooth50_provided"] = dict(labels_identical=same(codes, ref_codes), mine_md5=md5_text(mine),
                                    repo_md5=md5_text(ref), n_differing=int((codes != ref_codes).sum()))
    # 2. v1 through the adapter on the provided match (set pieces present, EM refit)
    atd = data.load_atd()
    blocks, sps = data.graded_blocks(), data.load_set_pieces()
    pitch = data.PITCH.copy()
    r = adapters.run_v1(atd, blocks, sps, pitch, mode="refit")
    path = os.path.join(OUT, "v1_provided.csv")
    run.write_submission(np.array(["H", "A", "D", "X"])[r["codes"]], path)
    res["v1_provided"] = dict(md5=md5_text(path)[0], expected=V1_MD5, matches=md5_text(path)[0] == V1_MD5)
    # 3. rederive == frame_signals when given its own constants
    with adapters.use_game(atd, blocks, sps, pitch):
        sig = features.frame_signals(atd)
        sig2 = adapters.rederive(sig, sig["radius"], sig["carry"])
        res["rederive_identical"] = {k: same(sig[k], sig2[k]) for k in ("flight", "gap", "dwell")}
        # 4. build_with_edges == build when given its own edges
        seqs, specs, halves, edges = features.build(sig)
        seqs2, _, _ = adapters.build_with_edges(sig, edges)
        res["build_with_edges_identical"] = all(same(a, b) for a, b in zip(seqs, seqs2))
    # 5. transfer decode path: v1's own parameters, constants and edges reproduce v1
    ref_pack = dict(radius=r["radius"], carry=r["carry"], edges=r["edges"], params=r["params"])
    t = adapters.run_v1(atd, blocks, sps, pitch, mode="transfer", ref=ref_pack)
    res["transfer_path_reproduces_v1"] = same(t["codes"], r["codes"])
    res["v1_constants_provided"] = dict(radius=float(r["radius"]), carry=float(r["carry"]))
    with open(os.path.join(OUT, "validation.json"), "w") as handle:
        json.dump(res, handle, indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
