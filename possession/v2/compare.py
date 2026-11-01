"""Label-free comparison of submissions against the pre-registered criteria (a)-(e).

    python -m possession.v2.compare hmm_v1 hmm_v2a ...   (names of files in submissions/)

Always includes baseline_smooth50 (from evaluation/results). Writes analysis/hmm_v2/compare.md/json.
"""

import json
import os
import sys

from .. import data, diagnostics, features

OUT = os.path.join(data.ROOT, "analysis", "hmm_v2")
BASE = "v1"  # criteria are judged against hmm_v1


def criteria(row, v1):
    a = row["pct_possessions_lt_2s"] < v1["pct_possessions_lt_2s"]
    b = row["reversal_rate_3s_pct"] < v1["reversal_rate_3s_pct"]
    c = (row["ball_outside_labelled_D_pct"] >= v1["ball_outside_labelled_D_pct"] - 5
         and row["restart_any_D_within_2s_pct"] >= v1["restart_any_D_within_2s_pct"] - 5
         and abs(row["D_share_pct"] - v1["D_share_pct"]) <= 5)
    e = row["possessions_per_min"] >= 3.0
    helped = bool(a and b and c and e)
    verdict = "HELPED" if helped else ("NOT HELPING" if not (a or b) else "MIXED")
    return dict(a=bool(a), b=bool(b), c=bool(c), e=bool(e), verdict=verdict)


def main(names):
    sig = features.frame_signals(data.load_atd())
    sps = data.load_set_pieces()
    rows = {"baseline_smooth50": diagnostics.summarise(diagnostics.read_codes(
        os.path.join(data.ROOT, "evaluation", "results", "baseline_smooth50.csv")), sig, sps)}
    for n in names:
        rows[n] = diagnostics.summarise(diagnostics.read_codes(
            os.path.join(data.ROOT, "submissions", n + ".csv")), sig, sps)
    v1 = rows["hmm_v1"]
    crit = {n: criteria(rows[n], v1) for n in names if n != "hmm_v1"}
    keys = list(v1.keys())
    cols = ["baseline_smooth50"] + names
    lines = ["| metric | " + " | ".join(cols) + " |", "|---|" + "---:|" * len(cols)]
    for k in keys:
        lines.append("| %s | %s |" % (k, " | ".join("%.2f" % rows[c][k] for c in cols)))
    for n, c in crit.items():
        lines.append("")
        lines.append("%s vs v1: (a) %s  (b) %s  (c) %s  (e) %s  => %s" % (
            n, c["a"], c["b"], c["c"], c["e"], c["verdict"]))
    text = "\n".join(lines)
    with open(os.path.join(OUT, "compare.md"), "w") as handle:
        handle.write(text + "\n")
    with open(os.path.join(OUT, "compare.json"), "w") as handle:
        json.dump(dict(rows=rows, criteria=crit), handle, indent=1)
    print(text)


if __name__ == "__main__":
    main(sys.argv[1:] or ["hmm_v1", "hmm_v2a"])
