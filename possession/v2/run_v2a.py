"""v2a: v1 features, team evidence tempered by 1/tau.   python -m possession.v2.run_v2a

tau comes from the autocorrelation of the state-conditional residual of the team evidence under the
v1 decoding (PREREGISTRATION.md rule 1), computed once; nothing is tuned afterwards.
Output: submissions/hmm_v2a.csv, analysis/hmm_v2/v2a.json, analysis/hmm_v2/acf.png
"""

import json
import os

import numpy as np

from .. import data, features, hmm, run
from . import tempered

OUT = os.path.join(data.ROOT, "analysis", "hmm_v2")
SUBMISSION = os.path.join(data.ROOT, "submissions", "hmm_v2a.csv")
TEAM_FEATURES = ("gap", "dwell")


def team_scores(halves):
    """Numeric per-block score of each team feature, per half (NaN = unobserved)."""
    pool = np.concatenate([h["dwell"] for h in halves])
    cap = float(np.nanpercentile(np.abs(pool), 99))
    return {"gap": [h["gap"] for h in halves],
            "dwell": [np.clip(h["dwell"], -cap, cap) for h in halves]}


def compute_taus(halves, v1_paths):
    scores = team_scores(halves)
    out = {}
    for name in TEAM_FEATURES:
        rho = tempered.residual_acf(scores[name], v1_paths)
        rho_raw = tempered.residual_acf(scores[name], v1_paths, remove_state=False)
        out[name] = dict(rho=rho, rho_raw=rho_raw, tau=tempered.integrated_tau(rho),
                         tau_raw=tempered.integrated_tau(rho_raw))
        out[name]["weight"] = tempered.tempering_weight(out[name]["tau"])
    return out


def plot_acf(taus, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    lag_s = features.BLOCK / data.FPS
    for a, name in zip(ax, TEAM_FEATURES):
        k = np.arange(1, len(taus[name]["rho"]) + 1)
        a.plot(k * lag_s, taus[name]["rho_raw"], label="raw (tau %.1f blocks)" % taus[name]["tau_raw"])
        a.plot(k * lag_s, taus[name]["rho"], label="state-residual (tau %.1f blocks)" % taus[name]["tau"])
        a.axhline(0, color="k", lw=.5)
        a.set_title("%s: autocorrelation of team evidence" % name)
        a.set_xlabel("lag (s)")
        a.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def weights_for(specs, taus):
    return [taus[s.name]["weight"] if s.name in taus else 1.0 for s in specs]


def main():
    os.makedirs(OUT, exist_ok=True)
    v1 = run.fit_model(verbose=False)
    taus = compute_taus(v1["halves"], v1["paths"])
    plot_acf(taus, os.path.join(OUT, "acf.png"))
    w = weights_for(v1["specs"], taus)
    stay = [s * data.FPS / features.BLOCK for s in run.PRIOR_DWELL_S]
    params = tempered.fit(v1["seqs"], v1["specs"], stay, w, verbose=True)
    paths = tempered.decode(v1["seqs"], params)
    labels = np.array(["H", "A", "D", "X"])[features.upsample(paths, v1["halves"])]
    run.write_submission(labels, SUBMISSION)
    step_s = features.BLOCK / data.FPS
    res = dict(taus={k: dict(tau=v["tau"], tau_raw=v["tau_raw"], weight=v["weight"]) for k, v in taus.items()},
               weights=dict(zip([s.name for s in v1["specs"]], w)),
               A=params["A"].tolist(), sojourn_s=(step_s / (1 - np.diag(params["A"]))).tolist(),
               iters=len(params["history"]), converged=bool(params["converged"]),
               monotone=bool(np.all(np.diff(params["history"]) > -1e-9 * abs(params["history"][0]))),
               counts={s: int(np.sum(labels == s)) for s in "HADX"})
    with open(os.path.join(OUT, "v2a.json"), "w") as handle:
        json.dump(res, handle, indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
