"""Part A of the follow-up: choose N_PSPEED on external data, label-free (analysis/logo_v1_followup/PREREGISTRATION_A.md).

    python -m possession.harness.npspeed run        # fits (cached, resumable) + held-out likelihoods -> partA_ll.json
    python -m possession.harness.npspeed select     # the pre-registered selection rule -> partA_table.md, partA_choice.json

For every candidate N_PSPEED and held-out game G: the LOGO fit (two other games, as-is ball, tracking-period intervals) is scored
by the forward-algorithm log-likelihood of G's blocks (G's tracking periods, as-is ball) under that fixed fit. No label of any
kind is read; the provided match is not read. Selection uses the density-corrected per-block log-likelihood (see the
pre-registration for why the raw discrete one cannot rank bin counts); the raw value is reported too.
"""
import json
import os
import sys

import numpy as np

from .. import data, features, hmm
from ..pilot import adapters
from . import games, logo_v1

OUT = os.path.join(data.ROOT, "analysis", "logo_v1_followup")
CANDIDATES = (6, 8, 12, 16, 24)
FOLDS = tuple(games.GAMES)
PS_COL = 6                                   # player_speed column of the sequences

_SIG = {}


def game_signals(name):
    """Frame signals of a sample game (as-is ball, tracking periods), cached; independent of N_PSPEED, radius, carry."""
    if name not in _SIG:
        g = logo_v1.training_game(name, "asis")
        with adapters.use_game(g["atd"], g["blocks"], [], g["pitch"]):
            _SIG[name] = (g, features.frame_signals(g["atd"]))
    return _SIG[name]


def block_pspeed(name):
    g, sig = game_signals(name)
    with adapters.use_game(g["atd"], g["blocks"], [], g["pitch"]):
        return np.concatenate([h["pspeed"] for h in features.block_values(sig)])


def forward_logz(X, params):
    """log P(sequence) by the forward algorithm (log space, fixed uniform pi)."""
    logB = [np.log(e) for e in params["emis"]]
    logA = np.log(params["A"])
    ll = hmm.emission_loglik(X, logB)
    alpha = params["logpi"] + ll[0]
    for t in range(1, len(X)):
        alpha = hmm._lse(alpha[:, None] + logA, 0) + ll[t]
    return float(hmm._lse(alpha, 0))


def heldout(n, held):
    train = tuple(g for g in FOLDS if g != held)
    fit = logo_v1.get_fit(train, "asis", n_pspeed=n)
    g, sig = game_signals(held)
    with logo_v1.use_npspeed(n), adapters.use_game(g["atd"], g["blocks"], [], g["pitch"]):
        s = adapters.rederive(sig, fit["radius"], fit["carry"])
        seqs, specs, halves = adapters.build_with_edges(s, fit["edges"])
    col = [sp.name for sp in specs].index("setpiece")
    for a in seqs:
        a[:, col] = -1                                           # no Smart Tagging in the sample games
    n_blocks = sum(len(a) for a in seqs)
    raw = sum(forward_logz(a, fit["params"]) for a in seqs) / n_blocks
    # density correction: log of the player-speed bin width, outer bins closed at the training games' pooled min / max
    tr = np.concatenate([block_pspeed(t) for t in train])
    lo, hi = float(np.nanmin(tr)), float(np.nanmax(tr))
    e = np.asarray(fit["edges"]["player_speed"], dtype=float)
    bounds = np.concatenate(([lo], e, [hi]))
    width = np.maximum(np.diff(bounds), 1e-9)
    cat = np.concatenate([a[:, PS_COL] for a in seqs])
    corr = float(np.sum(np.log(width[cat[cat >= 0]]))) / n_blocks
    return dict(raw=raw, corrected=raw - corr, n_blocks=int(n_blocks), converged=bool(fit["meta"]["converged"]),
                n_iter=int(fit["meta"]["n_iter"]), observed_share=float(np.mean(cat >= 0)), cutoff=cutoff(fit, bounds))


def cutoff(fit, bounds):
    """Dead-ball cutoff of the player-speed emission: where P(k|D) / P(k|alive) first drops below 1 (slowest to fastest)."""
    em = fit["params"]["emis"][PS_COL]
    ratio = em[2] / em[0]
    below = ratio < 1.0
    first = int(np.argmax(below)) if below.any() else len(ratio)
    crossings = int(np.sum(below[1:] != below[:-1]))
    edge = float(bounds[first]) if first < len(ratio) else float("nan")      # upper edge of category first-1
    lr = np.log(ratio)
    centres = 0.5 * (bounds[:-1] + bounds[1:])
    interp = float("nan")
    if 0 < first < len(ratio):
        a, b = lr[first - 1], lr[first]
        interp = float(centres[first - 1] + (0 - a) / (b - a) * (centres[first] - centres[first - 1]))
    widths = np.diff(bounds)
    return dict(edge=edge, interpolated=interp, crossings=crossings, first_category_below_1=first,
                width_below=float(widths[first - 1]) if first > 0 else None,
                width_above=float(widths[first]) if first < len(widths) else None,
                ratio=[float(x) for x in ratio])


def run():
    path = os.path.join(OUT, "partA_ll.json")
    res = json.load(open(path)) if os.path.isfile(path) else {}
    for n in CANDIDATES:
        for held in FOLDS:
            key = "%d|%s" % (n, held)
            if key in res:
                continue
            res[key] = heldout(n, held)
            json.dump(res, open(path, "w"), indent=1)
            r = res[key]
            print("N_PSPEED %2d held-out %s: raw %.4f corrected %.4f cutoff %.3f (iters %d)" % (
                n, held, r["raw"], r["corrected"], r["cutoff"]["edge"], r["n_iter"]), flush=True)


def select():
    res = json.load(open(os.path.join(OUT, "partA_ll.json")))
    mean = {n: float(np.mean([res["%d|%s" % (n, g)]["corrected"] for g in FOLDS])) for n in CANDIDATES}
    best = max(mean, key=mean.get)
    within, within_alt = {}, {}
    rows = {}
    for n in CANDIDATES:
        d = np.array([res["%d|%s" % (best, g)]["corrected"] - res["%d|%s" % (n, g)]["corrected"] for g in FOLDS])
        se = float(np.std(d, ddof=1) / np.sqrt(len(d))) if n != best else 0.0
        within[n] = bool(n == best or d.mean() <= se)
        within_alt[n] = bool(d.mean() <= 0.005 * abs(mean[best]))
        rows[n] = dict(mean_diff=float(d.mean()), se=se, folds_diff=d.tolist())
    chosen = min(n for n in CANDIDATES if within[n])
    chosen_alt = min(n for n in CANDIDATES if within_alt[n])
    L = ["# Part A: held-out log-likelihood per block, by N_PSPEED (label-free)", "",
         "Leave-one-game-out, as-is ball, tracking-period intervals; each cell is the held-out game's forward log-likelihood per block "
         "under the fit on the other two games. Source data: Metrica Sports sample data (github.com/metrica-sports/sample-data).", "",
         "## Density-corrected (selection criterion)", "",
         "| N_PSPEED | " + " | ".join("held-out " + g for g in FOLDS) + " | mean | best - this (mean) | SE of paired diff | within 1 SE |",
         "|---|" + "---:|" * (len(FOLDS) + 4)]
    for n in CANDIDATES:
        vals = [res["%d|%s" % (n, g)]["corrected"] for g in FOLDS]
        L.append("| %d | %s | %.4f | %.4f | %.4f | %s |" % (n, " | ".join("%.4f" % v for v in vals), mean[n],
                                                         rows[n]["mean_diff"], rows[n]["se"], "yes" if within[n] else "no"))
    L += ["", "Best by mean: **%d**. Smallest candidate within one SE of the paired difference: **%d** (registered rule). "
          "Alternative tolerance (0.5%% of |best|), diagnostic only: %d." % (best, chosen, chosen_alt), "",
          "## Raw discrete log-likelihood per block (not comparable across bin counts; shown as the task states it)", "",
          "| N_PSPEED | " + " | ".join("held-out " + g for g in FOLDS) + " | mean |", "|---|" + "---:|" * (len(FOLDS) + 1)]
    for n in CANDIDATES:
        vals = [res["%d|%s" % (n, g)]["raw"] for g in FOLDS]
        L.append("| %d | %s | %.4f |" % (n, " | ".join("%.4f" % v for v in vals), np.mean(vals)))
    L += ["", "## Diagnostic: learned dead-ball cutoff in player speed (D:alive likelihood ratio first below 1), m/s", "",
          "| N_PSPEED | " + " | ".join("fold " + g for g in FOLDS) + " | range across folds | interpolated (3 folds) | crossings (3 folds) | bin width at cutoff (3 folds) |",
          "|---|" + "---:|" * (len(FOLDS) + 4)]
    for n in CANDIDATES:
        c = [res["%d|%s" % (n, g)]["cutoff"] for g in FOLDS]
        edges = [x["edge"] for x in c]
        L.append("| %d | %s | %.3f | %s | %s | %s |" % (
            n, " | ".join("%.3f" % v for v in edges), max(edges) - min(edges),
            " / ".join("%.3f" % x["interpolated"] for x in c), " / ".join(str(x["crossings"]) for x in c),
            " / ".join("%.2f+%.2f" % (x["width_below"] or 0, x["width_above"] or 0) for x in c)))
    L += ["", "In a categorical model the cutoff is always a bin edge; the last column is the width of the bins either side "
          "(resolution), and 'interpolated' is a continuous estimate from the log-ratio between bin centres.", "",
          "EM iterations: " + ", ".join("%d:%s" % (n, "/".join(str(res["%d|%s" % (n, g)]["n_iter"]) for g in FOLDS))
                                        for n in CANDIDATES), ""]
    open(os.path.join(OUT, "partA_table.md"), "w").write("\n".join(L))
    json.dump(dict(chosen=chosen, chosen_alt_tolerance=chosen_alt, best_by_mean=best, mean_corrected=mean, rows=rows,
                   within=within), open(os.path.join(OUT, "partA_choice.json"), "w"), indent=1)
    print("\n".join(L))
    print("CHOSEN", chosen)


def export(n):
    """All-games as-is fit with n player-speed bins -> analysis/logo_v1_followup/frozen_params_np<n>.json (new file)."""
    fit = logo_v1.get_fit(FOLDS, "asis", n_pspeed=n)
    path = os.path.join(OUT, "frozen_params_np%d.json" % n)
    with logo_v1.use_npspeed(n):
        json.dump(logo_v1.to_jsonable(fit), open(path, "w"), indent=1)
    print("wrote", os.path.relpath(path, data.ROOT), "radius %.3f carry %.3f iters %d" % (
        fit["radius"], fit["carry"], fit["meta"]["n_iter"]), flush=True)


def fit_followup(n):
    """The remaining fits the follow-up re-run needs: all-games as-is (exported first), then the degraded folds."""
    export(n)
    for cond in logo_v1.CONDS:
        for held in FOLDS:
            fit = logo_v1.get_fit(tuple(g for g in FOLDS if g != held), cond, n_pspeed=n)
            print("np%d %s hold %s: radius %.3f carry %.3f iters %d" % (n, cond, held, fit["radius"], fit["carry"],
                                                                      fit["meta"]["n_iter"]), flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] in ("export", "fit-followup"):
        {"export": export, "fit-followup": fit_followup}[sys.argv[1]](int(sys.argv[2]))
        sys.exit()
    {"run": run, "select": select}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: print(__doc__))()
