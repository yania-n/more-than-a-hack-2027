"""Independent check of the home lean from Smart Tagging team tags (diagnostic; changes no model).

Share of graded time covered by phases tagged Barcelona vs Athletic. N/A excluded; the mirrored
'DEFENDING ...' / 'DEFENSIVE TRANSITION' instances excluded (they duplicate the attacking instance of
the other team). Each team's covered time is the union of its intervals inside graded frames.
    python -m possession.v3.tagging_share  ->  analysis/hmm_v3/tagging_share.json
"""

import json
import os

import numpy as np

from .. import data



def main():
    meta_path = data.require(["atd_meta"], data.GAME)[0]
    home, away = data._baseline.team_names(meta_path)
    graded = data.graded_mask()
    cover = {"H": np.zeros(data.N_FRAMES, dtype=bool), "A": np.zeros(data.N_FRAMES, dtype=bool)}
    per_code = {}
    n_used = n_na = n_def = 0
    for e in data._tags.load(data.GAME):
        code = (e["code"] or "").strip().lower()
        team = (e["tags"].get("Team") or "").strip()
        if code.startswith("defending") or code == "defensive transition":
            n_def += 1
            continue
        if not team or team.lower() == "n/a":
            n_na += 1
            continue
        side = "H" if team == home else "A"
        cover[side][e["start_frame"]:e["end_frame"]] = True
        per_code.setdefault(code, {"H": 0, "A": 0})[side] += 1
        n_used += 1
    h, a = int((cover["H"] & graded).sum()), int((cover["A"] & graded).sum())
    both = int((cover["H"] & cover["A"] & graded).sum())
    union = int(((cover["H"] | cover["A"]) & graded).sum())
    res = dict(home_name=home, away_name=away, instances_used=n_used, instances_na_excluded=n_na,
               instances_defending_excluded=n_def, frames_home=h, frames_away=a, frames_both=both,
               frames_union=union, graded_frames=int(graded.sum()),
               covered_share_of_graded=union / graded.sum(),
               home_share_union_of_attributed=h / (h + a), home_share_exclusive_only=(h - both) / max(h + a - 2 * both, 1),
               instances_by_code=per_code)
    with open(os.path.join(data.ROOT, "analysis", "hmm_v3", "tagging_share.json"), "w") as handle:
        json.dump(res, handle, indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
