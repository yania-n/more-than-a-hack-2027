"""Label-free comparison against the v3 pre-registered criteria (a)-(h).

    python -m possession.v3.compare       -> analysis/hmm_v3/compare.md / compare.json
Uses the same code as v2 (possession/diagnostics.py). Criteria: analysis/hmm_v3/PREREGISTRATION.md s.4.
"""

import json
import os

from .. import data, diagnostics, features

OUT = os.path.join(data.ROOT, "analysis", "hmm_v3")


def criteria(row, v1, v3json):
    a = row["pct_possessions_lt_2s"] < v1["pct_possessions_lt_2s"]
    b = row["reversal_rate_3s_pct"] < v1["reversal_rate_3s_pct"]
    c = (row["ball_outside_labelled_D_pct"] >= v1["ball_outside_labelled_D_pct"] - 5
         and row["restart_any_D_within_2s_pct"] >= v1["restart_any_D_within_2s_pct"] - 5
         and abs(row["D_share_pct"] - v1["D_share_pct"]) <= 5)
    e = row["possessions_per_min"] >= 3.0
    share, lr = v3json["carried_share_of_observed"], v3json["LR_home_carried_H_over_A"]
    f = bool(share >= 0.02 and lr >= 3.0)
    g = row["n_direct_handovers"] >= 0.5 * v1["n_direct_handovers"]
    h = row["handover_plausible_pct"] >= v1["handover_plausible_pct"]
    allpass = bool(a and b and c and e and f and g and h)
    verdict = "HELPED" if allpass else ("NOT HELPING" if not (a or b) else "MIXED")
    return dict(a=bool(a), b=bool(b), c=bool(c), e=bool(e), f=f, g=bool(g), h=bool(h), verdict=verdict,
                f_share=share, f_LR=lr)


def main():
    sig = features.frame_signals(data.load_atd())
    sps = data.load_set_pieces()
    names = ["hmm_v1", "hmm_v3a"]
    rows = {"baseline_smooth50": diagnostics.summarise(diagnostics.read_codes(
        os.path.join(data.ROOT, "evaluation", "results", "baseline_smooth50.csv")), sig, sps)}
    for n in names:
        rows[n] = diagnostics.summarise(diagnostics.read_codes(
            os.path.join(data.ROOT, "submissions", n + ".csv")), sig, sps)
    v3 = json.load(open(os.path.join(OUT, "v3a.json")))
    crit = criteria(rows["hmm_v3a"], rows["hmm_v1"], v3)
    cols = ["baseline_smooth50"] + names
    lines = ["| metric | " + " | ".join(cols) + " |", "|---|" + "---:|" * len(cols)]
    for k in rows["hmm_v1"]:
        lines.append("| %s | %s |" % (k, " | ".join("%.2f" % rows[c][k] for c in cols)))
    lines += ["", "hmm_v3a vs v1: (a) %s  (b) %s  (c) %s  (e) %s  (f) %s [share %.4f, LR %.1f]  (g) %s  (h) %s  => %s"
              % (crit["a"], crit["b"], crit["c"], crit["e"], crit["f"], crit["f_share"], crit["f_LR"],
                 crit["g"], crit["h"], crit["verdict"])]
    text = "\n".join(lines)
    with open(os.path.join(OUT, "compare.md"), "w") as handle:
        handle.write(text + "\n")
    with open(os.path.join(OUT, "compare.json"), "w") as handle:
        json.dump(dict(rows=rows, criteria=crit), handle, indent=1)
    print(text)


if __name__ == "__main__":
    main()
