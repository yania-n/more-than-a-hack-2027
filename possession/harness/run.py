"""Multi-game validation harness.

    python -m possession.harness.run --methods smooth50,v1_refit,v1_transfer
    python -m possession.harness.run --methods smooth50,my_method --plugin my_package.my_module

Runs every registered method over every game x label rule (primary, S1, S2) x ball condition (as-is,
degraded seed 0 / 1, and a leak-free condition for any game meeting the registered trigger), scores with
the organizers' possession_metrics functions, writes analysis/harness/results.json and results.csv.
Registered in analysis/harness/PREREGISTRATION.md. See possession/harness/api.py for the method interface.
"""

import argparse
import csv
import hashlib
import importlib
import json
import os
import pickle
import sys

import numpy as np

from .. import data
from ..pilot import adapters, run_pilot, score
from ..pilot.make_labels import write_csv
from . import api, conditions, games, labels, methods, pooled  # noqa: F401  (methods registers built-ins)

OUT = os.path.join(data.ROOT, "analysis", "harness")
RULES = labels.RULES
BASE_CONDITIONS = ("asis", "degraded_seed0", "degraded_seed1")


def md5(path):
    return hashlib.md5(open(path, "rb").read()).hexdigest()


def validate_adapters():
    """Re-run the pilot's adapter validation on the provided match; fail loudly if anything stops matching."""
    from ..pilot import validate_adapters as va
    va.main()
    res = json.load(open(os.path.join(va.OUT, "validation.json")))
    checks = {
        "smooth50 reproduces its repo file": res["smooth50_provided"]["labels_identical"],
        "v1 reproduces md5 83b587d7...": res["v1_provided"]["matches"],
        "rederive identical": all(res["rederive_identical"].values()),
        "build_with_edges identical": res["build_with_edges_identical"],
        "transfer path reproduces v1": res["transfer_path_reproduces_v1"],
    }
    with open(os.path.join(OUT, "validation.json"), "w") as handle:
        json.dump(dict(raw=res, checks=checks), handle, indent=1)
    bad = [k for k, v in checks.items() if not v]
    if bad:
        raise RuntimeError("ADAPTER VALIDATION FAILED on the provided match: " + "; ".join(bad))
    print("adapter validation passed:", ", ".join(checks), flush=True)
    return checks


def build_games(names):
    out = {}
    for name in names:
        g = games.load_game(name)
        g["pspeed"] = adapters.derive_pspeed(g["players"])
        g["labels"] = {r: labels.game_labels(g, r) for r in RULES}
        g["blocks"] = labels.play_blocks(g["labels"])
        out[name] = g
    return out


def flat_row(key, cell, prox):
    game, rule, cond, method = key.split("|")
    row = dict(game=game, rule=rule, condition=cond, method=method)
    for scope in ("whole", "half1", "half2"):
        for k, v in cell[scope].items():
            if scope != "whole" and k in ("spell_bootstrap_low", "spell_bootstrap_high"):
                continue
            row["%s_%s" % (scope, k)] = v
    row.update({"proxy_" + k: v for k, v in prox.items()})
    return row


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--methods", default="smooth50,v1_refit,v1_transfer")
    ap.add_argument("--games", default=",".join(games.GAMES))
    ap.add_argument("--reference", default="smooth50")
    ap.add_argument("--plugin", action="append", default=[], help="module to import (registers methods)")
    ap.add_argument("--boot", type=int, default=1000)
    ap.add_argument("--reuse", action="store_true", help="reuse cached predictions (scoring only)")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--skip-validation", action="store_true", help="NOT for official runs")
    args = ap.parse_args(argv)
    for mod in args.plugin:
        importlib.import_module(mod)
    method_names = [m for m in args.methods.split(",") if m]
    if args.reference not in method_names:
        method_names.insert(0, args.reference)
    out = args.out
    os.makedirs(os.path.join(out, "predictions"), exist_ok=True)
    os.makedirs(os.path.join(out, "labels"), exist_ok=True)
    os.makedirs(os.path.join(out, "tmp"), exist_ok=True)

    validation = None if args.skip_validation else validate_adapters()
    pack, gap_runs, pstats = run_pilot.reference_from_provided()
    gs = build_games(args.games.split(","))

    # ---- labels, ball-visibility facts, conditions per game
    info = dict(provided_ball=pstats, validation=validation, games={})
    md5s = {}
    for name, g in gs.items():
        n = len(g["ball"])
        gmask = np.zeros(n, dtype=bool)
        for _, a, b in g["blocks"]:
            gmask[a:b + 1] = True
        vis = np.isfinite(g["ball"][:, 0])
        dead = g["labels"]["primary"] == 2
        alive = (g["labels"]["primary"] == 0) | (g["labels"]["primary"] == 1)
        share_dead = float(vis[dead].mean())
        conds = list(BASE_CONDITIONS)
        if share_dead >= conditions.LEAKFREE_TRIGGER:
            conds += ["leakfree_seed0", "leakfree_seed1"]
        slot_counts = np.isfinite(g["players"][:, :, 0]).sum(1)
        info["games"][name] = dict(
            fps=g["fps"], frames=n, slots=int(g["players"].shape[1]), blocks=g["blocks"],
            players_per_frame=dict(mean=float(slot_counts.mean()), min=int(slot_counts.min()),
                                   max=int(slot_counts.max())),
            ball_visible_all=float(vis.mean()), ball_visible_graded=float(vis[gmask].mean()),
            ball_visible_when_D=share_dead, ball_visible_when_alive=float(vis[alive].mean()),
            leakfree_triggered=share_dead >= conditions.LEAKFREE_TRIGGER, conditions=conds,
            label_stats={r: labels.label_stats(g["labels"][r], g["fps"]) for r in RULES}, degraded={})
        for r in RULES:
            p = os.path.join(out, "labels", "%s_%s.csv" % (name, r))
            write_csv(g["labels"][r], p)
            md5s["labels|%s|%s" % (name, r)] = md5(p)

    # ---- predictions
    cache = os.path.join(out, "predictions", "preds.pkl")
    if args.reuse and os.path.isfile(cache):
        preds = pickle.load(open(cache, "rb"))
    else:
        preds = {}
        for name, g in gs.items():
            n = len(g["ball"])
            for cond in info["games"][name]["conditions"]:
                if cond == "asis":
                    ball = g["ball"]
                else:
                    seed = int(cond[-1])
                    if cond.startswith("degraded"):
                        ball, dinfo = adapters.degrade_ball(g["ball"], g["blocks"], gap_runs,
                                                            pstats["visible_share"], conditions.SIGMA_BALL, seed)
                    else:
                        alive = (g["labels"]["primary"] == 0) | (g["labels"]["primary"] == 1)
                        ball, dinfo = conditions.degrade_alive_only(g["ball"], g["blocks"], gap_runs,
                                                                    pstats["visible_share"], conditions.SIGMA_BALL,
                                                                    seed, alive)
                    info["games"][name]["degraded"][cond] = dinfo
                ctx = api.GameContext(name=name, fps=g["fps"], pitch=g["pitch"], players=g["players"], ball=ball,
                                      pspeed=g["pspeed"], team=g["team"], blocks=g["blocks"], n_frames=n,
                                      condition=cond, tmp_dir=os.path.join(out, "tmp"), reference=lambda: pack)
                for m in method_names:
                    preds[(name, cond, m)] = api.run_method(m, ctx)
                print("predictions done:", name, cond, flush=True)
        with open(cache, "wb") as handle:
            pickle.dump(preds, handle)
    for (name, cond, m), c in preds.items():
        p = os.path.join(out, "predictions", "%s_%s_%s.csv" % (name, cond, m))
        write_csv(c, p)
        md5s["pred|%s|%s|%s" % (name, cond, m)] = md5(p)
    info["md5"] = md5s

    # ---- scoring
    table, paired, prox = {}, {}, {}
    for name, g in gs.items():
        for cond in info["games"][name]["conditions"]:
            for m in method_names:
                prox["%s|%s|%s" % (name, cond, m)] = score.proxies(preds[(name, cond, m)], g["labels"]["primary"])
            for rule in RULES:
                gt = g["labels"][rule]
                for m in method_names:
                    cell = {"whole": score.evaluate(gt, preds[(name, cond, m)], args.boot)}
                    for h, (_, a, b) in enumerate(g["blocks"], start=1):
                        cell["half%d" % h] = score.evaluate(score.half_gt(gt, (a, b)), preds[(name, cond, m)], 0)
                    table["%s|%s|%s|%s" % (name, rule, cond, m)] = cell
                for m in method_names:
                    if m != args.reference:
                        paired["%s|%s|%s|%s-%s" % (name, rule, cond, m, args.reference)] = score.paired_bootstrap(
                            gt, preds[(name, cond, m)], preds[(name, cond, args.reference)], args.boot, 0)
        print("scored", name, flush=True)
    pooled_res, decisions = {}, {}
    names = sorted(gs)
    for m in method_names:
        if m == args.reference:
            continue
        pm_ = {}
        for rule in RULES:
            for cond in BASE_CONDITIONS:
                pm_[(rule, cond)] = pooled.pooled_paired(
                    {n_: gs[n_]["labels"][rule] for n_ in names},
                    {n_: preds[(n_, cond, m)] for n_ in names},
                    {n_: preds[(n_, cond, args.reference)] for n_ in names}, args.boot, 0)
        pooled_res[m] = {"%s|%s" % k: v for k, v in pm_.items()}
        decisions[m] = pooled.decide(m, args.reference, names, table, pm_)

    # ---- regression against the pilot (Game 3 under the primary rule must be reproduced exactly)
    regression = None
    pilot_stage1 = os.path.join(data.ROOT, "analysis", "pilot_game3", "stage1.json")
    if "game3" in gs and os.path.isfile(pilot_stage1):
        pm1 = json.load(open(pilot_stage1))["md5"]
        regression = {"labels_primary_equal": pm1["labels_primary"] == md5s["labels|game3|primary"]}
        for m in method_names:
            for cond in BASE_CONDITIONS:
                k = "%s_%s" % (m, cond)
                if k in pm1:
                    regression["pred_%s_equal" % k] = pm1[k] == md5s["pred|game3|%s|%s" % (cond, m)]

    res = dict(methods=method_names, reference=args.reference, games=info["games"], provided_ball=pstats,
               validation=validation, md5=md5s, table=table, paired=paired, pooled=pooled_res, decisions=decisions,
               proxies=prox, regression_vs_pilot=regression)
    with open(os.path.join(out, "results.json"), "w") as handle:
        json.dump(res, handle, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    rows = [flat_row(k, v, prox["|".join([k.split("|")[0], k.split("|")[2], k.split("|")[3]])])
            for k, v in table.items()]
    with open(os.path.join(out, "results.csv"), "w", newline="") as handle:
        head = ["game", "rule", "condition", "method"]
        w = csv.DictWriter(handle, fieldnames=head + sorted({k for r in rows for k in r} - set(head)))
        w.writeheader()
        w.writerows(rows)
    for m, d in decisions.items():
        print("%s vs %s: %s  clauses %s  halves %.0f%%" % (m, args.reference, d["verdict"], d["clauses"],
                                                          100 * d["halves_fraction"]))
    print("regression vs pilot:", regression)


if __name__ == "__main__":
    main()
