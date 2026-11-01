"""Mirror test: does the home lean follow the data (Barcelona) or the label ("H")?

Re-runs the v1 features + EM + Viterbi with the home/away team assignment of the tracks swapped.
The model ties H and A symmetrically, so the *team* (not the label) should keep its share.

    python -m possession.v2.mirror      -> analysis/hmm_v2/mirror.json
"""

import json
import os

import numpy as np

from .. import data, features, hmm, run


def fit_variant(swap):
    atd = dict(data.load_atd())
    if swap:
        atd["team"] = (1 - atd["team"]).astype(atd["team"].dtype)
    sig = features.frame_signals(atd)
    seqs, specs, halves, edges = features.build(sig)
    stay = [s * data.FPS / features.BLOCK for s in run.PRIOR_DWELL_S]
    params = hmm.fit(seqs, specs, stay, verbose=False)
    paths = hmm.decode(seqs, params)
    return dict(sig=sig, seqs=seqs, halves=halves, params=params, paths=paths)


def main():
    out = {}
    res = {}
    for name, swap in (("original", False), ("swapped", True)):
        r = fit_variant(swap)
        res[name] = r
        p = np.concatenate(r["paths"])
        n_h, n_a = int(np.sum(p == 0)), int(np.sum(p == 1))
        out[name] = dict(share_label_H=n_h / (n_h + n_a), share_label_A=n_a / (n_h + n_a),
                         share_D=float(np.mean(p == 2)), iters=len(r["params"]["history"]),
                         logL=r["params"]["history"][-1],
                         A=r["params"]["A"].tolist())
    # Barcelona = label H in the original run, label A in the swapped run.
    po = np.concatenate(res["original"]["paths"])
    ps = np.concatenate(res["swapped"]["paths"])
    ps_as_orig = np.where(ps == 0, 1, np.where(ps == 1, 0, ps))   # relabel back to Barcelona = H
    alive = (po < 2) & (ps_as_orig < 2)
    out["barcelona_share_original"] = out["original"]["share_label_H"]
    out["barcelona_share_swapped"] = out["swapped"]["share_label_A"]
    out["barcelona_share_diff_points"] = 100 * abs(out["barcelona_share_original"]
                                                   - out["barcelona_share_swapped"])
    out["blocks_decoded_differently_pct"] = 100 * float(np.mean(po != ps_as_orig))
    out["alive_blocks_team_differs_pct"] = 100 * float(np.mean(po[alive] != ps_as_orig[alive]))
    out["follows_data"] = bool(out["barcelona_share_diff_points"] < 2.0)
    path = os.path.join(data.ROOT, "analysis", "hmm_v2", "mirror.json")
    with open(path, "w") as handle:
        json.dump(out, handle, indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
