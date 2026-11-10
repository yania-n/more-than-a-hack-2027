# submissions/ : prediction files

Per-frame label files (H / A / D / X, 199,319 rows) for the full provided match. They are inputs for
`python evaluation/run_evaluation.py --results submissions`, which scores every `.csv` in the folder against the public
5-minute window. This is not the final competition entry (that file is `<team_name>.csv`, see `SUBMISSION.md`).

| file | what it is | md5 |
|---|---|---|
| `baseline_raw.csv`, `baseline_smooth25.csv`, `baseline_smooth50.csv`, `baseline_smooth125.csv` | **Copies of the organizers' baselines**, byte for byte the same as the files in `evaluation/results/`. Kept on purpose so the scoring command above prints the baselines next to our models. | raw `ee338c3d...`, smooth25 `e7424566...`, smooth50 `68ab9548...`, smooth125 `9cab6eaa...` |
| `hmm_v1.csv` | The original v1 (`possession/run.py`). Fitted on the provided match, so it does **not** meet the organizers' latest external-data-only rule; see `possession/README.md`. | `83b587d7b36a665a69f2eaf88566e60b` |
| `hmm_v2a.csv`, `hmm_v2b.csv`, `hmm_v2b_p95.csv` | v2 experiments (tempered evidence, flight gate + touch evidence). None beat v1. | v2a `b1551bda...`, v2b `b8d1dc4d...`, v2b_p95 `4a2d28bb...` |
| `hmm_v3a.csv` | v3 experiment (relative-motion control feature). **Identical to `hmm_v1.csv`** (same md5): the feature fired on too few blocks to change any label. Kept because `possession/v3/compare.py` reads it and the v3 report documents the result. | `83b587d7b36a665a69f2eaf88566e60b` |

Do not delete the duplicate files without updating the scripts and reports that name them (`analysis/hmm_v3/`,
`possession/v3/`, the scoring commands in `analysis/hmm_v1/REPORT.md` and `possession/README.md`).
