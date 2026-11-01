"""Entry point:  python -m possession.run   ->  submissions/hmm_v1.csv

Fits the 3-state HMM without labels on both halves (shared parameters, separate sequences),
Viterbi-decodes each half independently, and writes the submission. Deterministic: no random
numbers anywhere, so the same input gives the same bytes.
"""

import json
import os
import sys

import numpy as np

from . import data, features, hmm

SUBMISSION = os.path.join(data.ROOT, "submissions", "hmm_v1.csv")
# Prior expected sojourn time of every state before EM, in seconds. Football reasoning only:
# possessions and stoppages both last "several to a few tens of seconds"; 10 s says "sticky,
# not frame-to-frame". EM replaces it with the learned matrix.
PRIOR_DWELL_S = (10.0, 10.0, 10.0)


def fit_model(verbose=True):
    atd = data.load_atd()
    sig = features.frame_signals(atd)
    seqs, specs, halves, edges = features.build(sig)
    stay = [s * data.FPS / features.BLOCK for s in PRIOR_DWELL_S]
    params = hmm.fit(seqs, specs, stay, verbose=verbose)
    paths = hmm.decode(seqs, params)
    return dict(atd=atd, sig=sig, seqs=seqs, specs=specs, halves=halves, edges=edges,
                params=params, paths=paths)


def labels_from(model):
    codes = features.upsample(model["paths"], model["halves"])
    return np.array(["H", "A", "D", "X"])[codes]


def write_submission(labels, path=SUBMISSION):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="\n") as handle:
        handle.write("frame,label\n")
        handle.writelines("{},{}\n".format(i, lab) for i, lab in enumerate(labels))
    return path


def main():
    model = fit_model()
    labels = labels_from(model)
    path = write_submission(labels)
    p = model["params"]
    print("converged: {}  iterations: {}".format(p["converged"], len(p["history"])))
    print("wrote {}  ({} rows)".format(os.path.relpath(path, data.ROOT), len(labels)))
    for s in "HADX":
        print("  {}: {}".format(s, int(np.sum(labels == s))))
    os.makedirs(data.OUT_DIR, exist_ok=True)
    with open(os.path.join(data.OUT_DIR, "model.json"), "w") as handle:
        json.dump(dict(A=p["A"].tolist(), history=p["history"],
                       emis={s.name: e.tolist() for s, e in zip(model["specs"], p["emis"])},
                       radius=model["sig"]["radius"], carry=model["sig"]["carry"],
                       edges={k: v.tolist() for k, v in model["edges"].items()}), handle, indent=1)


if __name__ == "__main__":
    main()
