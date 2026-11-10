# possession/ : our code

Per-frame possession labels (H / A / D / X) from tracking data, plus the experiments around it. The
organizers' files (`evaluation/`, `starter/`, `games.py`, the top-level docs) are not modified; everything
here is new.

| path | what it is |
|---|---|
| `data.py`, `features.py`, `hmm.py`, `diagnostics.py`, `run.py`, `report.py` | **v1**: unsupervised 3-state HMM, Baum-Welch fit, Viterbi decode |
| `v2/` | tempered evidence, flight gate + touch evidence, mirror test (none beat v1) |
| `v3/` | relative-motion control feature (no effect) |
| `pilot/` | Game 3 pilot: event-derived proxy labels, adapters, scoring |
| `harness/` | multi-game validation harness; `example_plugin.py` shows how to add a method |
| `harness/baseline_windows.py`, `check_baseline_windows.py` | the organizers' raw / smooth25 / smooth125 baselines through the harness, and a check that they reproduce the organizers' files exactly |
| `harness/logo_v1.py`, `logo_decisions.py`, `logo_stability.py`, `test_logo_v1.py` | **rule-compliant v1** (`v1_logo`): every parameter fitted on other games only, then frozen |
| `harness/npspeed.py`, `domain_shift.py` | choose the number of player-speed bins on external data; label-free domain-shift check on the provided match |
| `harness/all_metrics.py`, `summarize_baselines.py` | every organizer metric per method; summary tables |

Reports and results for each stage are in [`../analysis/`](../analysis/README.md). Prediction files are in
`../submissions/`.

## Setup
Install `requirements.txt` (repo root) and `possession/requirements.txt`. Put the competition data in
`data/` (see `DATA.md`). The data is not in this repository and must not be committed. The pilot and
harness also need Metrica's public sample data (see `analysis/README.md`).

## Commands (as listed in each stage's report)
```
python -m possession.run                        # v1  -> submissions/hmm_v1.csv
python -m possession.report                     # v1 plots and tables

python -m possession.v2.run_v2a
python -m possession.v2.run_v2b
python -m possession.v2.compare hmm_v1 hmm_v2a hmm_v2b hmm_v2b_p95

python -m possession.v3.run_v3a
python -m possession.v3.compare
python -m possession.v3.tagging_share

python -m possession.pilot.make_labels
python -m possession.pilot.validate_adapters
python -m possession.pilot.run_pilot

python -m possession.harness.run --methods smooth50,v1_refit,v1_transfer
python -m possession.harness.run --methods smooth50,my_method --plugin my_package.my_module

# organizer baselines vs v1 (needs the Metrica sample data)
python -m possession.harness.check_baseline_windows
python -m possession.harness.run --plugin possession.harness.baseline_windows --methods raw,smooth25,smooth50,smooth125,v1_refit,v1_transfer --out analysis/harness_baselines
python -m possession.harness.summarize_baselines analysis/harness_baselines
python -m possession.harness.all_metrics analysis/harness_baselines

# rule-compliant v1: see analysis/logo_v1/REPORT.md and analysis/logo_v1_followup/REPORT.md for the exact commands
python -m possession.harness.test_logo_v1
```
Check a prediction file with `python evaluation/validate_submission.py submissions/hmm_v1.csv`. Score against
the public 5-minute window with
`python evaluation/run_evaluation.py --results submissions --bootstrap 1000`.

## Reproducibility
Runs are deterministic. `hmm_v1.csv` has md5 `83b587d7b36a665a69f2eaf88566e60b`; the other md5s are
recorded in each stage's report.

## Rules followed
No ground truth was used to fit, tune or choose anything. Labels for other games are produced by code
from the sample data's events, never by hand. The public 5-minute window was used to check the pipeline
and understand the labelling, never to fit or choose anything; some reports show scores on it for
reference, and 17 possessions cannot rank methods. Variants were judged against criteria written down
before running them.

**Which v1 can be submitted.** The organizers' latest rules require that anything fitted or tuned uses
external data only. `hmm_v1.csv` (the original v1) was fitted on the provided match, so it does not meet
that. The compliant version fits on the Metrica sample games and is frozen (`harness/logo_v1.py`,
`analysis/logo_v1_followup/frozen_params_np24.json`); `analysis/logo_v1/PROVENANCE.md` lists where each
constant came from.

Metrica Sports' public sample data (https://github.com/metrica-sports/sample-data) is used as external
data, with attribution as its README asks.
