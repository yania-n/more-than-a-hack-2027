"""Stability of the fitted v1 parameters across the LOGO fits (PREREGISTRATION.md s.7). Descriptive.

    python -m possession.harness.logo_stability analysis/logo_v1
Reads analysis/logo_v1/fits/*.pkl (fitted numbers only) and analysis/hmm_v1/model.json (the shipped fit). Writes
<dir>/stability.md and stability.json.
"""
import itertools
import json
import os
import pickle
import sys

import numpy as np

from .. import data
from .logo_v1 import FEATURES

GAMES = ("game1", "game2", "game3")


def pack_logo(fit):
    p = fit["params"]
    return dict(radius=fit["radius"], carry=fit["carry"], edges={k: np.asarray(v) for k, v in fit["edges"].items()},
                diagA=np.diag(p["A"]), emis=dict(zip(FEATURES, p["emis"])), iters=fit["meta"]["n_iter"])


def pack_shipped():
    d = json.load(open(os.path.join(data.ROOT, "analysis", "hmm_v1", "model.json")))
    return dict(radius=d["radius"], carry=d["carry"], edges={k: np.asarray(v) for k, v in d["edges"].items()},
                diagA=np.diag(np.array(d["A"])), emis={k: np.array(v) for k, v in d["emis"].items()},
                iters=len(d["history"]))


def tv(a, b):
    return float(np.mean(0.5 * np.abs(a - b).sum(axis=1)))     # mean over the 3 states


def rel_range(vals):
    vals = np.asarray(vals, dtype=float)
    return float((vals.max() - vals.min()) / abs(vals.mean())) if vals.mean() else float("nan")


def main(folder):
    fits = {}
    for g in GAMES:
        fits["logo_hold_%s" % g] = pack_logo(pickle.load(open(os.path.join(
            folder, "fits", "fit_%s_asis.pkl" % "+".join(h for h in GAMES if h != g)), "rb")))
        fits["only_%s" % g] = pack_logo(pickle.load(open(os.path.join(folder, "fits", "fit_%s_asis.pkl" % g), "rb")))
    fits["all3"] = pack_logo(pickle.load(open(os.path.join(folder, "fits", "fit_%s_asis.pkl" % "+".join(GAMES)), "rb")))
    fits["shipped_provided"] = pack_shipped()
    groups = {"LOGO folds (3)": [k for k in fits if k.startswith("logo_")],
              "single-game fits (3)": [k for k in fits if k.startswith("only_")],
              "all 7 sample-game fits": [k for k in fits if k != "shipped_provided"]}

    scal = {"radius (m)": lambda f: f["radius"], "carry speed (m/s)": lambda f: f["carry"]}
    for feat, e in fits["shipped_provided"]["edges"].items():
        for i in range(len(e)):
            scal["edge %s[%d]" % (feat, i)] = (lambda feat, i: lambda f: float(f["edges"][feat][i]))(feat, i)
    for s, n in enumerate("HAD"):
        scal["stay prob %s" % n] = (lambda s: lambda f: float(f["diagA"][s]))(s)
    rows, js = [], {}
    for name, fn in scal.items():
        v = {k: fn(f) for k, f in fits.items()}
        rr = {g: rel_range([v[k] for k in ks]) for g, ks in groups.items()}
        js[name] = dict(values=v, rel_range=rr)
        rows.append((name, v, rr))
    lines = ["# Stability of fitted v1 parameters across fits", "",
             "All fits unsupervised, ball as-is. `logo_hold_gK` = trained on the two games other than K (the fits `v1_logo` uses "
             "for game K); `only_gK` = trained on game K alone (stability only, never scored); `all3` = frozen_params.json; "
             "`shipped_provided` = the shipped v1 (fitted on the provided match). Relative range = (max-min)/mean.", "",
             "## Scalars", "", "| parameter | " + " | ".join(fits) + " | rel.range LOGO | rel.range 7 sample fits |",
             "|---|" + "---:|" * (len(fits) + 2)]
    for name, v, rr in rows:
        lines.append("| %s | %s | %.2f | %.2f |" % (name, " | ".join("%.3f" % v[k] for k in fits),
                                                   rr["LOGO folds (3)"], rr["all 7 sample-game fits"]))
    ranked = sorted(rows, key=lambda r: -r[2]["LOGO folds (3)"])[:8]
    lines += ["", "Scalars that moved most between the three LOGO folds (relative range): " +
              ", ".join("%s %.2f" % (n, rr["LOGO folds (3)"]) for n, _, rr in ranked), "",
              "## Emission tables: mean total-variation distance (0 identical, 1 disjoint), mean over the 3 states", ""]
    keys = list(fits)
    emjs = {}
    for feat in FEATURES:
        if feat == "setpiece":
            continue
        d = {}
        for a, b in itertools.combinations(keys, 2):
            ea, eb = fits[a]["emis"][feat], fits[b]["emis"][feat]
            d[(a, b)] = tv(np.asarray(ea), np.asarray(eb))
        logo = [d[(a, b)] if (a, b) in d else d[(b, a)] for a, b in itertools.combinations(groups["LOGO folds (3)"], 2)]
        sample = [v for (a, b), v in d.items() if "shipped_provided" not in (a, b)]
        ship = [v for (a, b), v in d.items() if "shipped_provided" in (a, b)]
        emjs[feat] = dict(logo_mean=float(np.mean(logo)), sample_fits_mean=float(np.mean(sample)),
                          vs_shipped_mean=float(np.mean(ship)))
    lines += ["| feature | LOGO folds, mean pairwise TV | all 7 sample fits | sample fits vs shipped |", "|---|---:|---:|---:|"]
    for feat, v in sorted(emjs.items(), key=lambda kv: -kv[1]["logo_mean"]):
        lines.append("| %s | %.3f | %.3f | %.3f |" % (feat, v["logo_mean"], v["sample_fits_mean"], v["vs_shipped_mean"]))
    lines += ["", "(The set-piece feature is missing in every sample-game fit, so its emission is the uninformative prior; omitted.)",
              "", "EM iterations to converge: " + ", ".join("%s %d" % (k, f["iters"]) for k, f in fits.items()), ""]
    json.dump(dict(scalars=js, emission_tv=emjs), open(os.path.join(folder, "stability.json"), "w"), indent=1)
    open(os.path.join(folder, "stability.md"), "w").write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "analysis/logo_v1")
