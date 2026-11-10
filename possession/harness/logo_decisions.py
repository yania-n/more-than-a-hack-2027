"""Pre-registered decision rule (analysis/logo_v1/PREREGISTRATION.md s.5) for v1_logo against every comparator.

    python -m possession.harness.logo_decisions analysis/logo_v1

The harness already evaluates v1_logo vs its --reference (smooth50). This applies the very same functions
(pooled.pooled_paired, pooled.decide; 1,000 draws, seed 0) to the other comparators, reading the saved predictions,
label files and results.json. Writes <dir>/decisions.json and <dir>/decisions.md.
"""
import json
import os
import pickle
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "evaluation"))
import possession_metrics as pm  # noqa: E402

from . import games, pooled  # noqa: E402

RULES = ("primary", "S1", "S2")
CONDS = ("asis", "degraded_seed0", "degraded_seed1")


def main(folder, method="v1_logo", n_boot=1000):
    suffix = "" if method == "v1_logo" else "_" + method
    res = json.load(open(os.path.join(folder, "results.json")))
    preds = pickle.load(open(os.path.join(folder, "predictions", "preds.pkl"), "rb"))
    names = sorted(games.GAMES)
    gts = {r: {g: pm.label_codes(pm.read_label_csv(os.path.join(folder, "labels", "%s_%s.csv" % (g, r))))
               for g in names} for r in RULES}
    out = {}
    for ref in [m for m in res["methods"] if m != method]:
        pm_ = {(r, c): pooled.pooled_paired(gts[r], {g: preds[(g, c, method)] for g in names},
                                            {g: preds[(g, c, ref)] for g in names}, n_boot, 0)
               for r in RULES for c in CONDS}
        d = pooled.decide(method, ref, names, res["table"], pm_)
        d["pooled_all"] = {"%s|%s" % k: v for k, v in pm_.items()}
        out[ref] = d
    json.dump(out, open(os.path.join(folder, "decisions%s.json" % suffix), "w"), indent=1,
              default=lambda o: o.item() if hasattr(o, "item") else str(o))
    lines = ["# Pre-registered decision rule: %s against each comparator" % method, "",
             "Differences are spellF1 (%s - comparator), equal-weight mean over games, paired bootstrap 90%% interval "
             "(1,000 draws, seed 0). Clauses a-e as in PREREGISTRATION.md s.5." % method, "",
             "| comparator | primary/as-is diff [90% CI] | P(logo better) | clauses a b c d e | halves | verdict |",
             "|---|---:|---:|---|---:|---|"]
    for ref, d in out.items():
        p = d["pooled_primary_asis"]
        lines.append("| %s | %+.3f [%+.3f, %+.3f] | %.2f | %s | %.0f%% | %s |" % (
            ref, p["point_diff"], p["low90"], p["high90"], p["p_a_better"],
            " ".join("%s=%s" % (k, "Y" if v else "n") for k, v in d["clauses"].items()),
            100 * d["halves_fraction"], d["verdict"]))
    lines += ["", "Per ball condition and rule, pooled difference (%s - comparator):" % method, "",
              "| comparator | " + " | ".join("%s/%s" % (r, c) for r in RULES for c in CONDS) + " |",
              "|---|" + "---:|" * (len(RULES) * len(CONDS))]
    for ref, d in out.items():
        lines.append("| %s | %s |" % (ref, " | ".join("%+.3f" % d["pooled_all"]["%s|%s" % (r, c)]["point_diff"]
                                                      for r in RULES for c in CONDS)))
    open(os.path.join(folder, "decisions%s.md" % suffix), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "analysis/logo_v1", sys.argv[2] if len(sys.argv) > 2 else "v1_logo")
