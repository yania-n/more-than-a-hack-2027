"""Validate the baseline windows on the PROVIDED match: each must reproduce the organizers' own CSV.

    python -m possession.harness.check_baseline_windows

Same check the pilot made for smooth50 (possession/pilot/validate_adapters.py), for all four variants.
Exits with status 1 if any label differs.
"""

import os
import sys

import numpy as np

from .. import data
from ..pilot import adapters

WINDOWS = (("raw", 0, "baseline_raw.csv"), ("smooth25", 25, "baseline_smooth25.csv"),
           ("smooth50", 50, "baseline_smooth50.csv"), ("smooth125", 125, "baseline_smooth125.csv"))


def main():
    meta_path, raw_path = data.require(["atd_meta", "atd_raw"], data.GAME)
    team = adapters.baseline.team_of_each_track(meta_path)
    pitch = data.GAMES[data.GAME]["pitch"]
    ok = True
    for name, window, csv_name in WINDOWS:
        codes = adapters.smooth50_codes(raw_path, team, data.N_FRAMES, pitch, window=window)
        ref = os.path.join(data.ROOT, "evaluation", "results", csv_name)
        ref_codes = np.array([{"H": 0, "A": 1, "D": 2}[line.strip().split(",")[1]]
                              for line in open(ref).read().split("\n")[1:] if line.strip()], dtype=np.int8)
        differing = int((codes != ref_codes).sum()) if len(codes) == len(ref_codes) else -1
        ok &= differing == 0
        print("{:<10} window {:>3}  frames {}  differing labels vs {}: {}".format(
            name, window, len(codes), csv_name, differing if differing >= 0 else "LENGTH MISMATCH"))
    print("ALL IDENTICAL" if ok else "MISMATCH: do not trust the new baselines")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
