"""Part B of the follow-up: does the frozen v1_external_all behave sensibly on the provided match's tracking? (label-free)

    python -m possession.harness.domain_shift b1  --frozen <frozen_params.json>     # feature shift (no model output)
    python -m possession.harness.domain_shift b23 --frozen <frozen_params.json>     # decode + proxies + agreement
    python -m possession.harness.domain_shift b4  --frozen <frozen_params.json>     # one-change-at-a-time diagnosis

analysis/logo_v1_followup/PREREGISTRATION_B.md fixes everything. The provided match is INPUT to a frozen model only: its tracking
(data.load_atd, like the shipped v1) and the published graded blocks are read; no ground-truth CSV, public window, video or label
is read. The per-frame output is written to analysis/logo_v1_followup/private/ (nested .gitignore) and nowhere else.
Source of the fitted numbers: Metrica Sports public sample data (github.com/metrica-sports/sample-data).
"""
import copy
import hashlib
import json
import os
import sys

import numpy as np

from .. import data, features, run
from ..pilot import adapters
from . import games, logo_v1, npspeed

sys.path.insert(0, os.path.join(data.ROOT, "evaluation"))
import possession_metrics as pm  # noqa: E402

OUT = os.path.join(data.ROOT, "analysis", "logo_v1_followup")
PRIVATE = os.path.join(OUT, "private")
FEATS = logo_v1.FEATURES
FPS = 25
LOGO = os.path.join(data.ROOT, "analysis", "logo_v1")
PROXIES = ("poss_per_alive_min", "mean_poss_len_s", "pct_lt_2s", "reversal_3s", "dead_share", "mean_dead_spell_s",
           "home_share_alive")
LETTERS = np.array(["H", "A", "D", "X"])


# ------------------------------------------------------------------------------------------------ provided match
def provided_inputs():
    atd = data.load_atd()
    return atd, data.graded_blocks(), data.PITCH.copy(), data.graded_mask()


def n_bins(pack):
    return len(pack["edges"]["player_speed"]) + 1


def features_for(atd, blocks, pitch, pack):
    """Per-half category sequences of one game under a frozen pack (setpiece column missing)."""
    with logo_v1.use_npspeed(n_bins(pack)), adapters.use_game(atd, blocks, [], pitch):
        sig = features.frame_signals(atd)
        s = adapters.rederive(sig, pack["radius"], pack["carry"])
        seqs, specs, _ = adapters.build_with_edges(s, pack["edges"])
    col = [sp.name for sp in specs].index("setpiece")
    for a in seqs:
        a[:, col] = -1
    return np.concatenate(seqs), specs


def sample_features(name, pack):
    g = logo_v1.training_game(name, "asis")
    return features_for(g["atd"], g["blocks"], g["pitch"], pack)


def dist(X, f, n_cat):
    x = X[:, f]
    ok = x >= 0
    c = np.bincount(x[ok], minlength=n_cat).astype(float)
    return c / c.sum() if c.sum() else c, float(1.0 - ok.mean())


# ------------------------------------------------------------------------------------------------ B1
def b1(pack):
    atd, blocks, pitch, _ = provided_inputs()
    Xp, specs = features_for(atd, blocks, pitch, pack)
    Xs = {g: sample_features(g, pack)[0] for g in games.GAMES}
    rows, js = [], {}
    for f, sp in enumerate(specs):
        name = sp.name
        if name == "setpiece":
            js[name] = dict(note="missing in the provided match and in every sample game (frozen emission uninformative)")
            continue
        pp, mp = dist(Xp, f, sp.n_cat)
        pooled = np.concatenate(list(Xs.values()))
        pt, mt = dist(pooled, f, sp.n_cat)
        miss_g = {g: dist(Xs[g], f, sp.n_cat)[1] for g in games.GAMES}
        loo = {}
        for g in games.GAMES:
            rest = np.concatenate([Xs[h] for h in games.GAMES if h != g])
            loo[g] = 0.5 * float(np.abs(dist(Xs[g], f, sp.n_cat)[0] - dist(rest, f, sp.n_cat)[0]).sum())
        tv = 0.5 * float(np.abs(pp - pt).sum())
        delta = pp - pt
        order = np.argsort(delta)
        gain = [(int(k), float(delta[k])) for k in order[::-1][:3] if delta[k] > 0]
        lose = [(int(k), float(delta[k])) for k in order[:3] if delta[k] < 0]
        rare = pt < 0.02
        rare_mass = float(pp[rare].sum())
        flags = []
        if tv > 2 * max(loo.values()):
            flags.append("TV > 2 x largest sample-game TV")
        if rare_mass > 0.10:
            flags.append("%.0f%% of mass in bins with training share < 2%%" % (100 * rare_mass))
        lo, hi = min(miss_g.values()), max(miss_g.values())
        if not (0.5 * lo <= mp <= 2 * hi):
            flags.append("missing share outside [0.5 x min, 2 x max] of sample games")
        js[name] = dict(tv=tv, tv_loo_sample_games=loo, gain=gain, lose=lose, rare_mass=rare_mass, flags=flags,
                        missing_provided=mp, missing_games=miss_g, missing_pooled=mt, n_cat=sp.n_cat,
                        p_provided=pp.tolist(), p_train=pt.tolist())
        rows.append((name, tv, max(loo.values()), rare_mass, mp, lo, hi, gain, lose, flags))
    L = ["# B1: feature shift of the provided match against the sample games, over the FROZEN bins", "",
         "Bins = frozen radius / carry / edges of `%s` (%d player-speed bins). Training = Sample Games 1-3 as-is (Metrica Sports sample "
         "data), provided match = its tracking as the shipped v1 reads it. TV = total variation between observed-category "
         "distributions; the scale is each sample game vs the pooled other two. Missing share = blocks whose feature is absent "
         "(ball absent, ball in flight, heading undefined...)." % (pack.get("_name", "frozen"), n_bins(pack)), "",
         "| feature | TV provided vs sample | largest sample-game TV (LOO) | mass in rare bins | missing share provided | missing share sample games (min-max) | flags |",
         "|---|---:|---:|---:|---:|---:|---|"]
    for name, tv, ltv, rm, mp, lo, hi, gain, lose, flags in rows:
        L.append("| %s | %.3f | %.3f | %.1f%% | %.1f%% | %.1f%% - %.1f%% | %s |" % (
            name, tv, ltv, 100 * rm, 100 * mp, 100 * lo, 100 * hi, "; ".join(flags) or "-"))
    L += ["", "Bins that gain / lose most mass (category index: delta share provided - training; categories ordered low to high; "
          "for gap and dwell, below the middle = away side):", ""]
    for name, tv, ltv, rm, mp, lo, hi, gain, lose, flags in rows:
        L.append("* **%s** gain %s; lose %s" % (name, ", ".join("%d (%+.1f pp)" % (k, 100 * d) for k, d in gain),
                                                ", ".join("%d (%+.1f pp)" % (k, 100 * d) for k, d in lose)))
    L += ["", "Set-piece feature: missing everywhere (the frozen model has no informative set-piece emission).", ""]
    open(os.path.join(OUT, "partB_features.md"), "w").write("\n".join(L))
    json.dump(js, open(os.path.join(OUT, "partB_features.json"), "w"), indent=1)
    print("\n".join(L))


# ------------------------------------------------------------------------------------------------ proxies
def proxies(codes):
    runs = pm.valid_runs(codes)
    spells = pm.possession_spells(codes, runs)
    dur = np.array([(b - a) / FPS for a, b, _ in spells])
    alive = int(np.sum((codes == 0) | (codes == 1)))
    graded = int(np.sum(codes != 3))
    dead = np.array([(b - a) / FPS for a, b, k in pm.segments(codes, runs) if k == pm.D])
    allt = pm.transitions(codes, runs)
    direct = [(i, t) for i, t in enumerate(allt) if t[1] in (0, 1) and t[2] in (0, 1)]
    rev = sum(1 for i, t in direct if i + 1 < len(allt) and allt[i + 1][1] == t[2] and allt[i + 1][2] == t[1]
              and allt[i + 1][0] - t[0] <= 3 * FPS)
    return dict(poss_per_alive_min=len(spells) / (alive / FPS / 60.0), mean_poss_len_s=float(dur.mean()),
                pct_lt_2s=float(np.mean(dur < 2)), reversal_3s=rev / max(len(direct), 1), n_direct=len(direct),
                dead_share=float(np.sum(codes == 2)) / graded, mean_dead_spell_s=float(dead.mean()),
                median_dead_spell_s=float(np.median(dead)), home_share_alive=float(np.sum(codes == 0)) / alive,
                n_spells=len(spells), graded_min=graded / FPS / 60.0)


def agreement(ref, pred):
    ok = ref != 3
    return dict(frame_agreement=float(np.mean(ref[ok] == pred[ok])),
                spell_f1=float(pm.evaluate(ref, pred, bootstrap_n=0)["spell_f1_mean"]))


def read_codes(path):
    return pm.label_codes(pm.read_label_csv(path))


def write_private(codes, name):
    os.makedirs(PRIVATE, exist_ok=True)
    path = os.path.join(PRIVATE, name)
    run.write_submission(LETTERS[codes], path)
    return path


def decode_provided(pack, atd=None):
    a, blocks, pitch, _ = provided_inputs()
    atd = atd or a
    with logo_v1.use_npspeed(n_bins(pack)):
        return adapters.run_v1(atd, blocks, [], pitch, mode="transfer", ref=pack, setpiece_missing=True)["codes"]


def flag_row(name, p, rng, old):
    out = {}
    for k in PROXIES:
        lo, hi = 0.5 * rng[k][0], 2 * rng[k][1]
        a = not (lo <= p[k] <= hi)
        if k == "home_share_alive":
            b = abs(p[k] - old[k]) > 0.10
        else:
            r = p[k] / old[k] if old[k] else float("inf")
            b = not (1 / 1.5 <= r <= 1.5)
        out[k] = dict(range_flag=bool(a), old_flag=bool(b), allowed=[lo, hi])
    return out


def b23(pack):
    _, _, _, mask = provided_inputs()
    codes1 = decode_provided(pack)
    codes2 = decode_provided(pack)
    path = write_private(codes1, "v1_external_all_provided.csv")
    md5a = hashlib.md5(open(path, "rb").read()).hexdigest()
    path2 = write_private(codes2, "_second_run.csv")
    md5b = hashlib.md5(open(path2, "rb").read()).hexdigest()
    os.remove(path2)
    assert md5a == md5b, "decode is not deterministic"
    assert np.array_equal(codes1 != 3, mask), "output intervals differ from the published graded blocks"
    ext = codes1
    old = read_codes(os.path.join(data.ROOT, "submissions", "hmm_v1.csv"))
    assert np.array_equal(old != 3, mask), "old v1 non-X frames differ from the graded mask"
    s50 = read_codes(os.path.join(data.ROOT, "evaluation", "results", "baseline_smooth50.csv"))
    s50 = np.where(mask, s50, 3).astype(np.int8)
    systems = {"v1_external_all": ext, "smooth50": s50, "old v1 (not compliant)": old}
    prox = {k: proxies(v) for k, v in systems.items()}
    ref = {}
    for g in games.GAMES:
        lab = read_codes(os.path.join(LOGO, "labels", "%s_primary.csv" % g))
        lg = read_codes(os.path.join(LOGO, "predictions", "%s_asis_v1_logo.csv" % g))
        sm = read_codes(os.path.join(LOGO, "predictions", "%s_asis_smooth50.csv" % g))
        ref[g] = dict(labels=proxies(lab), v1_logo=proxies(lg), smooth50=proxies(sm), agree_logo_vs_s50=agreement(sm, lg))
    rng = {k: (min(ref[g]["labels"][k] for g in games.GAMES), max(ref[g]["labels"][k] for g in games.GAMES)) for k in PROXIES}
    flags = {k: flag_row(k, prox[k], rng, prox["old v1 (not compliant)"]) for k in prox}
    agree = {"v1_external_all vs smooth50 (ref smooth50)": agreement(s50, ext),
             "v1_external_all vs old v1 (ref old v1)": agreement(old, ext),
             "old v1 vs smooth50 (ref smooth50)": agreement(s50, old)}
    json.dump(dict(proxies=prox, sample_reference=ref, ranges=rng, flags=flags, agreement=agree, md5=md5a,
                   frozen_bins=n_bins(pack)), open(os.path.join(OUT, "partB_proxies.json"), "w"), indent=1)
    fmt = lambda k, v: ("%.1f%%" % (100 * v)) if k in ("pct_lt_2s", "reversal_3s", "dead_share", "home_share_alive") else "%.2f" % v
    L = ["# B2/B3: label-free output proxies of the frozen model on the provided match (descriptive, not a score)", "",
         "Frozen model: v1_external_all (Metrica Sports sample data, github.com/metrica-sports/sample-data; %d player-speed bins). The "
         "provided match was used only as input; per-frame output is in `private/` (gitignored). Decode deterministic (md5 %s, twice)."
         % (n_bins(pack), md5a), "",
         "Definitions: PREREGISTRATION_B.md s.4. Sample-game columns are the primary proxy labels (min - max over the 3 games); "
         "the flag band is [0.5 x min, 2 x max] of that range.", "",
         "| proxy | v1_external_all | smooth50 | old v1 (not compliant) | sample proxy labels (min-max) | flag band | sample v1_logo (min-max) | sample smooth50 (min-max) |",
         "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for k in PROXIES:
        rr = lambda src: "%s - %s" % (fmt(k, min(ref[g][src][k] for g in games.GAMES)), fmt(k, max(ref[g][src][k] for g in games.GAMES)))
        fl = flags["v1_external_all"][k]
        mark = " **[flag a]**" if fl["range_flag"] else ""
        mark += " **[flag b]**" if fl["old_flag"] else ""
        L.append("| %s | %s%s | %s | %s | %s | %s - %s | %s | %s |" % (
            k, fmt(k, prox["v1_external_all"][k]), mark, fmt(k, prox["smooth50"][k]), fmt(k, prox["old v1 (not compliant)"][k]),
            "%s - %s" % (fmt(k, rng[k][0]), fmt(k, rng[k][1])), fmt(k, flags["v1_external_all"][k]["allowed"][0]),
            fmt(k, flags["v1_external_all"][k]["allowed"][1]), rr("v1_logo"), rr("smooth50")))
    L += ["", "Counts (spells / direct transitions / graded minutes): " + "; ".join(
        "%s %d / %d / %.1f" % (k, v["n_spells"], v["n_direct"], v["graded_min"]) for k, v in prox.items()), "",
        "Context flags (smooth50 and old v1, same two rules): " + "; ".join(
            "%s: %s" % (s, ", ".join(k for k in PROXIES if flags[s][k]["range_flag"] or flags[s][k]["old_flag"]) or "none")
            for s in ("smooth50", "old v1 (not compliant)")), "",
        "## Agreement (descriptive, NOT a score; the named system is treated as the reference)", "",
        "| pair | frame agreement | spell-level F1 (organiser matching) |", "|---|---:|---:|"]
    for k, v in agree.items():
        L.append("| %s | %.3f | %.3f |" % (k, v["frame_agreement"], v["spell_f1"]))
    L.append("| sample games: v1_logo vs smooth50 (ref smooth50), per game | " + " / ".join(
        "%.3f" % ref[g]["agree_logo_vs_s50"]["frame_agreement"] for g in games.GAMES) + " | " + " / ".join(
        "%.3f" % ref[g]["agree_logo_vs_s50"]["spell_f1"] for g in games.GAMES) + " |")
    flagged = [k for k in PROXIES if flags["v1_external_all"][k]["range_flag"] or flags["v1_external_all"][k]["old_flag"]]
    L += ["", "**Flagged for v1_external_all (needs investigation, not a failure):** " + (", ".join(flagged) or "none"), ""]
    open(os.path.join(OUT, "partB_proxies.md"), "w").write("\n".join(L))
    print("\n".join(L))


# ------------------------------------------------------------------------------------------------ B4
def b4(pack):
    res = json.load(open(os.path.join(OUT, "partB_proxies.json")))
    flagged = [k for k in PROXIES if res["flags"]["v1_external_all"][k]["range_flag"]
               or res["flags"]["v1_external_all"][k]["old_flag"]]
    if not flagged:
        print("nothing flagged: B4 not run")
        return
    ship = json.load(open(os.path.join(data.ROOT, "analysis", "hmm_v1", "model.json")))
    atd, _, _, _ = provided_inputs()
    changes = [("radius := shipped %.4f" % ship["radius"], lambda p, a: p.update(radius=ship["radius"]), None),
               ("carry := shipped %.3f" % ship["carry"], lambda p, a: p.update(carry=ship["carry"]), None)]
    for k in ("gap", "dwell", "ball_speed", "heading", "player_speed"):
        changes.append(("edges %s := shipped" % k, (lambda k: lambda p, a: p["edges"].__setitem__(k, np.asarray(ship["edges"][k])))(k), k))
    changes.append(("transition matrix := shipped", lambda p, a: p["params"].__setitem__("A", np.array(ship["A"])), None))
    changes.append(("player speed := positions-derived (+-8 frames)", None, "pspeed"))
    base = res["proxies"]["v1_external_all"]
    rows = [("(frozen, unchanged)", base)]
    skipped = []
    for label, fn, tag in changes:
        p = copy.deepcopy(pack)
        a = atd
        if tag == "player_speed" and len(ship["edges"]["player_speed"]) + 1 != n_bins(pack):
            skipped.append(label)
            continue
        if tag == "pspeed":
            a = dict(atd)
            a["pspeed"] = adapters.derive_pspeed(atd["players"])
        else:
            fn(p, a)
        codes = decode_provided(p, a)
        rows.append((label, proxies(codes)))
        print("done:", label, flush=True)
    old = res["proxies"]["old v1 (not compliant)"]
    fmt = lambda k, v: ("%.1f%%" % (100 * v)) if k in ("pct_lt_2s", "reversal_3s", "dead_share", "home_share_alive") else "%.2f" % v
    L = ["# B4: one-change-at-a-time diagnosis on the provided match (diagnostic only; nothing is adopted)", "",
         "Each row changes ONE frozen quantity to the shipped v1 value (which was fitted on the provided match, so this only locates a cause). "
         "Flagged proxies of v1_external_all: %s. Old shipped v1 shown for orientation." % ", ".join(flagged), "",
         "| change | " + " | ".join(PROXIES) + " |", "|---|" + "---:|" * len(PROXIES)]
    for label, p in rows:
        L.append("| %s | %s |" % (label, " | ".join(fmt(k, p[k]) + (" *" if k in flagged else "") for k in PROXIES)))
    L.append("| old shipped v1 (reference) | %s |" % " | ".join(fmt(k, old[k]) for k in PROXIES))
    if skipped:
        L += ["", "Skipped (bin count differs from the shipped 12): " + ", ".join(skipped)]
    L += ["", "(* = proxy flagged for the unchanged frozen model.)", ""]
    open(os.path.join(OUT, "partB_diagnosis.md"), "w").write("\n".join(L))
    json.dump([(l, p) for l, p in rows], open(os.path.join(OUT, "partB_diagnosis.json"), "w"), indent=1)
    print("\n".join(L))


def main(argv=None):
    a = argv or sys.argv[1:]
    if len(a) < 3 or a[1] != "--frozen":
        print(__doc__)
        return
    pack = logo_v1.load_frozen(a[2])
    pack["_name"] = os.path.relpath(a[2], data.ROOT)
    {"b1": b1, "b23": b23, "b4": b4}[a[0]](pack)


if __name__ == "__main__":
    main()
