"""Rule-compliant v1: nothing is fitted on the game it is applied to, nor on the provided match.

    python -m possession.harness.logo_v1 fit            # precompute + cache every fit (resumable), export frozen_params.json
    python -m possession.harness.run --plugin possession.harness.baseline_windows --plugin possession.harness.logo_v1 \
        --methods raw,smooth25,smooth50,smooth125,v1_refit,v1_logo --out analysis/logo_v1

Methods registered here
  v1_logo          for held-out game G: every quantity v1 fits (analysis/logo_v1/PROVENANCE.md section A: control radius,
                   carry speed, bin edges, EM emissions + transitions) is fitted on the OTHER two sample games' tracking
                   only, unsupervised, under the same ball condition, then frozen; Viterbi on G.
  v1_external_all  the same fit on all three sample games pooled, frozen in analysis/logo_v1/frozen_params.json. Meant for a
                   match outside the sample games (the provided match); refuses to run on a sample game (in-sample).

The inference path is `adapters.run_v1(mode="transfer")`, i.e. the shipped v1 code (features.frame_signals, rederive,
build_with_edges, hmm.decode, upsample); the fit is the shipped v1 recipe (features.build's percentile edges, hmm.fit with the
shipped settings) generalised from one game to a pool of games. For one game it reproduces the shipped v1 byte for byte
(test_logo_v1.py). No label, event, Smart Tagging row or provided-match value is read by any fit: the fit function takes
tracking arrays and interval boundaries only.
"""

import contextlib
import json
import os
import pickle
import sys
import warnings

import numpy as np

from .. import data, features, hmm, run
from ..pilot import adapters
from . import conditions, games
from .api import register

OUT = os.path.join(data.ROOT, "analysis", "logo_v1")
FITS = os.path.join(OUT, "fits")
FROZEN = os.path.join(OUT, "frozen_params.json")
CONDS = ("asis", "degraded_seed0", "degraded_seed1")
FEATURES = ("gap", "dwell", "ball_speed", "heading", "outside", "setpiece", "player_speed")

_GAMES = {}
_PROVIDED = {}
N_PSPEED_DEFAULT = 12                      # v1's value; the follow-up (analysis/logo_v1_followup) evaluates others


@contextlib.contextmanager
def use_npspeed(n):
    """Temporarily set the number of player-speed bins (features.N_PSPEED is read at call time by the fit and by
    adapters.build_with_edges). Restored on exit."""
    old = features.N_PSPEED
    features.N_PSPEED = int(n)
    try:
        yield
    finally:
        features.N_PSPEED = old


# ---------------------------------------------------------------------------------------------- the fit
def fit_frozen(train, setpiece_missing=True, verbose=False):
    """Fit every quantity of PROVENANCE.md section A on a list of training games, unsupervised.

    train: list of dict(atd=dict(ball, players, pspeed, team), blocks=[(half, first, last)], pitch, set_pieces=[]).
           Nothing else: no labels, no events. `blocks` are intervals to treat as play (tracking periods in LOGO).
    Returns the frozen pack dict(radius, carry, edges, params) that adapters.run_v1(mode="transfer") consumes, plus meta.
    """
    stay = [s * data.FPS / features.BLOCK for s in run.PRIOR_DWELL_S]
    # 1. frame signals per game (own provisional constants), then pooled radius and carry speed
    sigs, dmin_all, pspeed_all = [], [], []
    for g in train:
        with adapters.use_game(g["atd"], g["blocks"], g.get("set_pieces", []), g["pitch"]):
            sig = features.frame_signals(g["atd"])
        sigs.append(sig)
        gm = sig["graded"]
        dmin_all.append(sig["dmin"][gm & sig["vis"]])
        pspeed_all.append(g["atd"]["pspeed"][gm].ravel())
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        radius = float(np.nanmedian(np.concatenate(dmin_all)))
        carry = float(np.nanpercentile(np.concatenate(pspeed_all), 99))
    # 2. per-block values with the pooled constants; pooled percentile edges (the recipe of features.build)
    pooled = {k: [] for k in ("gap", "dwell", "bspeed", "heading", "pspeed")}
    resigs = []
    for g, sig in zip(train, sigs):
        with adapters.use_game(g["atd"], g["blocks"], g.get("set_pieces", []), g["pitch"]):
            s = adapters.rederive(sig, radius, carry)
            for h in features.block_values(s):
                for k in pooled:
                    pooled[k].append(h[k])
        resigs.append(s)
    pool = {k: np.concatenate(v) for k, v in pooled.items()}

    def q(x, n):
        return np.nanpercentile(x, np.linspace(0, 100, n + 1)[1:-1])

    absd = np.abs(pool["dwell"])
    edges = dict(gap=q(np.abs(pool["gap"]), features.N_G_BINS), dwell=q(absd[absd > 0], features.N_DWELL_BINS),
                 ball_speed=q(pool["bspeed"], features.N_BSPEED), heading=q(pool["heading"], features.N_HEAD),
                 player_speed=q(pool["pspeed"], features.N_PSPEED))
    # 3. sequences with those edges; set-piece feature missing (no Smart Tagging in the sample games)
    seqs, specs = [], None
    for g, s in zip(train, resigs):
        with adapters.use_game(g["atd"], g["blocks"], g.get("set_pieces", []), g["pitch"]):
            sq, specs, _ = adapters.build_with_edges(s, edges)
        if setpiece_missing:
            col = [sp.name for sp in specs].index("setpiece")
            for a in sq:
                a[:, col] = -1
        seqs += sq
    # 4. Baum-Welch, shared parameters, all halves of all training games as independent sequences
    params = hmm.fit(seqs, specs, stay, verbose=verbose)
    return dict(radius=radius, carry=carry, edges=edges, params=params,
                meta=dict(n_sequences=len(seqs), n_blocks=int(sum(len(a) for a in seqs)),
                          n_iter=len(params["history"]), converged=bool(params["converged"]),
                          loglik_per_step=float(params["history"][-1] / sum(len(a) for a in seqs)),
                          setpiece_missing=bool(setpiece_missing)))


# ---------------------------------------------------------------------------------------------- training data
def provided_ball_stats():
    """Unlabelled aggregates of the provided match's ball channel (gap lengths, visible share) that define the harness'
    degraded-ball condition (PROVENANCE C3). No fitting of v1; the same numbers the harness computes."""
    if not _PROVIDED:
        atd = data.load_atd()
        blocks = data.graded_blocks()
        vis = np.isfinite(atd["ball"][:, 0])
        _, gap_runs = adapters.graded_runs(vis, blocks)
        _PROVIDED.update(gap_runs=gap_runs, share=float(vis[data.graded_mask()].mean()))
    return _PROVIDED["gap_runs"], _PROVIDED["share"]


def training_game(name, cond):
    """A sample game as fit_frozen's input: tracking only, ball under `cond`, intervals = tracking periods."""
    if name not in _GAMES:
        g = games.load_game(name)
        _GAMES[name] = dict(players=g["players"], ball=g["ball"], team=g["team"], pitch=g["pitch"],
                            pspeed=adapters.derive_pspeed(g["players"]), blocks=[tuple(p) for p in g["periods"]])
    s = _GAMES[name]
    ball = s["ball"]
    if cond != "asis":
        if not cond.startswith("degraded_seed"):
            raise ValueError("v1_logo supports asis / degraded_seed*; got %r" % cond)
        gap_runs, share = provided_ball_stats()
        ball, _ = adapters.degrade_ball(ball, s["blocks"], gap_runs, share, conditions.SIGMA_BALL, int(cond[-1]))
    atd = dict(ball=ball, players=s["players"], pspeed=s["pspeed"], team=s["team"])
    return dict(atd=atd, blocks=s["blocks"], pitch=s["pitch"], set_pieces=[], name=name)


def fit_path(train_names, cond, n_pspeed=N_PSPEED_DEFAULT):
    """Cache path; the 12-bin fits keep the names used by analysis/logo_v1."""
    tag = "" if n_pspeed == N_PSPEED_DEFAULT else "_np%d" % n_pspeed
    return os.path.join(FITS, "fit_%s_%s%s.pkl" % ("+".join(sorted(train_names)), cond, tag))


def get_fit(train_names, cond, verbose=False, n_pspeed=N_PSPEED_DEFAULT):
    """Cached frozen fit for (training games, ball condition, player-speed bins). Stores fitted parameters only."""
    train_names = tuple(sorted(train_names))
    path = fit_path(train_names, cond, n_pspeed)
    if os.path.isfile(path):
        return pickle.load(open(path, "rb"))
    with use_npspeed(n_pspeed):
        fit = fit_frozen([training_game(n, cond) for n in train_names], verbose=verbose)
    fit["meta"].update(train=list(train_names), condition=cond, n_pspeed=n_pspeed)
    os.makedirs(FITS, exist_ok=True)
    with open(path, "wb") as handle:
        pickle.dump(fit, handle)
    return fit


# ---------------------------------------------------------------------------------------------- inference
def decode_game(frozen, ctx_like):
    """Frozen pack -> per-frame codes (0 H, 1 A, 2 D, 3 X). The shipped v1 transfer/inference path."""
    atd = dict(ball=ctx_like.ball, players=ctx_like.players, pspeed=ctx_like.pspeed, team=ctx_like.team)
    with use_npspeed(len(frozen["edges"]["player_speed"]) + 1):
        return adapters.run_v1(atd, ctx_like.blocks, [], ctx_like.pitch, mode="transfer", ref=frozen,
                               setpiece_missing=True)["codes"]


def _logo_method(n_pspeed):
    def method(ctx):
        if ctx.name not in games.GAMES:
            raise ValueError("v1_logo is defined for the sample games only (got %r)" % ctx.name)
        train = tuple(sorted(n for n in games.GAMES if n != ctx.name))
        assert ctx.name not in train and len(train) == 2
        return decode_game(get_fit(train, ctx.condition, n_pspeed=n_pspeed), ctx)
    return method


register("v1_logo")(_logo_method(N_PSPEED_DEFAULT))                 # the registered run
for _n in (6, 8, 16, 24):                                            # follow-up variants (Part A), same code path
    register("v1_logo_p%d" % _n)(_logo_method(_n))


# ---------------------------------------------------------------------------------------------- frozen file
def to_jsonable(fit):
    p = fit["params"]
    return dict(
        description="v1 parameters fitted on Metrica Sample Games 1-3 pooled (tracking only, unsupervised, no labels), "
                    "ball as-is. Frozen. Source: github.com/metrica-sports/sample-data (acknowledged). No tracking or "
                    "event rows are stored here, only fitted numbers.",
        train=fit["meta"].get("train"), condition=fit["meta"].get("condition"), meta=fit["meta"],
        radius=fit["radius"], carry=fit["carry"], edges={k: list(map(float, v)) for k, v in fit["edges"].items()},
        features=list(FEATURES), emis={n: e.tolist() for n, e in zip(FEATURES, p["emis"])},
        A=p["A"].tolist(), logpi=p["logpi"].tolist(), history=list(map(float, p["history"])),
        constants=dict(BLOCK=features.BLOCK, N_G_BINS=features.N_G_BINS, N_DWELL_BINS=features.N_DWELL_BINS,
                       N_BSPEED=features.N_BSPEED, N_HEAD=features.N_HEAD, N_PSPEED=len(fit["edges"]["player_speed"]) + 1,
                       PRIOR_DWELL_S=list(run.PRIOR_DWELL_S), set_piece_feature="missing (-1) in every sample game"))


def load_frozen(path=FROZEN):
    """frozen_params.json -> the pack adapters.run_v1(mode='transfer') consumes."""
    d = json.load(open(path))
    params = dict(emis=[np.array(d["emis"][n]) for n in d["features"]], A=np.array(d["A"]),
                  logpi=np.array(d["logpi"]), history=d["history"], converged=d["meta"]["converged"])
    return dict(radius=d["radius"], carry=d["carry"], edges={k: np.array(v) for k, v in d["edges"].items()},
                params=params)


@register("v1_external_all")
def v1_external_all(ctx):
    """Frozen all-sample-games parameters applied to a match outside them. Not a held-out result on a sample game."""
    if ctx.name in games.GAMES:
        raise ValueError("v1_external_all is fitted on %s: running it there is in-sample, not a result" % (games.GAMES,))
    return decode_game(load_frozen(), ctx)


# ---------------------------------------------------------------------------------------------- CLI
def main(argv=None):
    args = argv or sys.argv[1:]
    if not args or args[0] != "fit":
        print(__doc__)
        return
    names = list(games.GAMES)
    jobs = []
    for cond in CONDS:                                   # LOGO fits: train on the other two
        for g in names:
            jobs.append(tuple(n for n in names if n != g) + (cond,))
    jobs += [(g, "asis") for g in names]                 # single-game fits, stability only, never scored
    jobs += [tuple(names) + ("asis",)]                   # all three, as-is -> frozen_params.json
    for job in jobs:
        *train, cond = job
        path = os.path.join(FITS, "fit_%s_%s.pkl" % ("+".join(sorted(train)), cond))
        done = os.path.isfile(path)
        fit = get_fit(train, cond)
        m = fit["meta"]
        print("%s train=%s cond=%s radius %.3f carry %.3f iters %d converged %s logL/step %.5f" % (
            "cached" if done else "fitted", "+".join(sorted(train)), cond, fit["radius"], fit["carry"], m["n_iter"],
            m["converged"], m["loglik_per_step"]), flush=True)
    allfit = get_fit(names, "asis")
    with open(FROZEN, "w") as handle:
        json.dump(to_jsonable(allfit), handle, indent=1)
    print("wrote", os.path.relpath(FROZEN, data.ROOT), flush=True)


if __name__ == "__main__":
    main()
