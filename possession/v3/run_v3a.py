"""v3a: v1 + relative-motion control feature.   python -m possession.v3.run_v3a

Output: submissions/hmm_v3a.csv, analysis/hmm_v3/v3a.json, analysis/hmm_v3/null.png
Same blocks, priors, symmetry tying and EM as v1; the new feature is mirror-tied and untempered.
"""

import json
import os

import numpy as np

from .. import data, features, hmm, run
from ..hmm import FeatureSpec
from . import motion

OUT = os.path.join(data.ROOT, "analysis", "hmm_v3")
SUBMISSION = os.path.join(data.ROOT, "submissions", "hmm_v3a.csv")


def plot_null(extra, info):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(12, 4))
    for a, idx, name, thr in ((ax[0], 0, "window-mean cosine C", info["theta_C"]),
                              (ax[1], 1, "window-mean |ln speed ratio| L", info["theta_L"])):
        real = extra["cbar_real"] if idx == 0 else extra["lbar_real"]
        lo, hi = (-1, 1) if idx == 0 else (0, 3)
        bins = np.linspace(lo, hi, 80)
        a.hist(real[np.isfinite(real)], bins=bins, density=True, alpha=.5, label="real (candidate windows)")
        for kind, col in (("shift", "r"), ("team", "g")):
            a.hist(extra["pools"][kind][idx], bins=bins, density=True, histtype="step", color=col,
                   label="null: " + ("time-shifted player" if kind == "shift" else "random teammate"))
        a.axvline(thr, color="k", ls="--", label="threshold (p%.0f of null)" % info["pct"])
        a.set_title(name)
        a.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "null.png"), dpi=110)
    plt.close(fig)


def main():
    os.makedirs(OUT, exist_ok=True)
    atd = data.load_atd()
    v1 = run.fit_model(verbose=False)
    cols, info, extra = motion.compute(atd, v1["sig"], v1["halves"], make_plot_data=True)
    plot_null(extra, info)
    seqs = [np.concatenate([s, c[:, None]], axis=1) for s, c in zip(v1["seqs"], cols)]
    specs = v1["specs"] + [FeatureSpec("carry", 3, "team")]
    stay = [s * data.FPS / features.BLOCK for s in run.PRIOR_DWELL_S]
    params = hmm.fit(seqs, specs, stay, verbose=False)
    paths = hmm.decode(seqs, params)
    labels = np.array(["H", "A", "D", "X"])[features.upsample(paths, v1["halves"])]
    run.write_submission(labels, SUBMISSION)
    e = params["emis"][-1]            # rows H, A, D ; columns away-carried, none, home-carried
    step_s = features.BLOCK / data.FPS
    res = dict(info=info,
               emission_carry={"H": e[0].tolist(), "A": e[1].tolist(), "D": e[2].tolist()},
               LR_home_carried_H_over_A=float(e[0, 2] / e[1, 2]),
               carried_share_of_observed=info["carried_share_of_observed"],
               A=params["A"].tolist(), sojourn_s=(step_s / (1 - np.diag(params["A"]))).tolist(),
               iters=len(params["history"]), converged=bool(params["converged"]),
               counts={s: int(np.sum(labels == s)) for s in "HADX"})
    with open(os.path.join(OUT, "v3a.json"), "w") as handle:
        json.dump(res, handle, indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
