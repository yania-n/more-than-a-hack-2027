"""Pooled paired bootstrap across games and the pre-registered decision rule (PREREGISTRATION.md s.4-5)."""

import numpy as np

from ..pilot import score

CONDITIONS_OTHER = ("degraded_seed0", "degraded_seed1")


def pooled_paired(gts, preds_a, preds_b, n_draws=1000, seed=0):
    """Game-stratified paired bootstrap of the equal-weight mean-over-games spell_f1_mean difference a - b.
    gts / preds_*: dict game -> array. One RandomState, games in sorted order, same picks for a and b."""
    games = sorted(gts)
    pack = {g: (score._flags(gts[g], preds_a[g]), score._flags(gts[g], preds_b[g])) for g in games}
    point = float(np.mean([
        score._f1(pack[g][0][0], np.arange(pack[g][0][1]), pack[g][0][1], pack[g][0][2])
        - score._f1(pack[g][1][0], np.arange(pack[g][1][1]), pack[g][1][1], pack[g][1][2]) for g in games]))
    rng = np.random.RandomState(seed)
    diffs = np.empty(n_draws)
    for i in range(n_draws):
        d = []
        for g in games:
            (fa, n_gt, na), (fb, _, nb) = pack[g]
            picks = rng.randint(0, n_gt, n_gt)
            d.append(score._f1(fa, picks, n_gt, na) - score._f1(fb, picks, n_gt, nb))
        diffs[i] = np.mean(d)
    lo, hi = np.percentile(diffs, [5, 95])
    return dict(point_diff=point, mean_diff=float(diffs.mean()), low90=float(lo), high90=float(hi),
                p_a_better=float(np.mean(diffs > 0)))


def sign(x):
    return 1 if x > 0 else (-1 if x < 0 else 0)


def decide(method, ref, games, table, pooled, rules=("primary", "S1", "S2"),
           conditions=("asis", "degraded_seed0", "degraded_seed1")):
    """Apply clauses (a)-(e) to method vs ref. table[game|rule|cond|method][scope]['spell_f1_mean'];
    pooled[(rule, cond)] -> pooled_paired result for method - ref."""
    def d(game, rule, cond, scope):
        return (table["%s|%s|%s|%s" % (game, rule, cond, method)][scope]["spell_f1_mean"]
                - table["%s|%s|%s|%s" % (game, rule, cond, ref)][scope]["spell_f1_mean"])

    pa = pooled[("primary", "asis")]
    direction = sign(pa["point_diff"])
    a = (direction > 0 and pa["low90"] > 0) or (direction < 0 and pa["high90"] < 0)
    b = all(sign(d(g, "primary", "asis", "whole")) == direction for g in games)
    c = all(sign(pooled[(r, "asis")]["point_diff"]) == direction for r in ("S1", "S2"))
    dd = all(sign(pooled[("primary", cnd)]["point_diff"]) == direction for cnd in CONDITIONS_OTHER)
    cells = [(g, r, cnd) for g in games for r in rules for cnd in conditions]
    ok = [sign(d(g, r, cnd, "half1")) == direction and sign(d(g, r, cnd, "half2")) == direction
          for g, r, cnd in cells]
    frac = float(np.mean(ok))
    e = frac >= 0.8
    clauses = dict(a=bool(a), b=bool(b), c=bool(c), d=bool(dd), e=bool(e))
    leaning = method if direction > 0 else (ref if direction < 0 else "none")
    if all(clauses.values()):
        verdict = "%s wins" % leaning
    else:
        failed = [k for k, v in clauses.items() if not v]
        verdict = "no clear winner (leaning %s; clauses failing: %s)" % (leaning, ", ".join(failed))
    return dict(method=method, reference=ref, direction=direction, clauses=clauses, halves_fraction=frac,
                n_cells=len(cells), pooled_primary_asis=pa, verdict=verdict,
                failing_half_cells=[("%s|%s|%s" % c_) for c_, o in zip(cells, ok) if not o])
