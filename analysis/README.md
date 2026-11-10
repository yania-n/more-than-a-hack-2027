# Analysis and reports

One folder per stage of the work, each with a `REPORT.md` (and a `PREREGISTRATION.md` where the rules
were fixed before running). `SUMMARY.md` is a plain-language overview of everything below.

| folder | question | outcome |
|---|---|---|
| `diagnose_smooth50/` | Where does the organizers' `baseline_smooth50` lose points on the public 5 minutes? | Team switches at hand-overs and brief flips cost the most spellF1. Undetected dead ball is most of the wrong frames but a smaller spellF1 lever. |
| `sync_feasibility/` | Would syncing the broadcast feed fill gaps in the tactical ball tracking? | The sync works (median ball disagreement 0.78 m), but broadcast has the ball on only 9% of the missing-ball frames (coverage 59.3% to 63.0%). Not worth building. |
| `hmm_v1/` | An unsupervised 3-state HMM (H / A / D) on tracking features. | Much better dead-ball detection (public macroF1 0.75 vs 0.62). On the 17-possession public window its spellF1 cannot be separated from smooth50 (0.28 vs 0.33). |
| `hmm_v2/` | Three attempts to cut fragmentation: explicit durations, tempered evidence, flight gate + touch evidence. | None helped. The duration experiment is in `hmm_v2/negative_results/`. |
| `hmm_v3/` | A relative-motion control feature. | Informative but fires on only 1.1% of blocks; the output is identical to v1. |
| `pilot_game3/` | First full-game test: event-derived proxy labels on Metrica sample Game 3, v1 vs smooth50. | v1 ahead on spellF1 in all 9 label-rule and ball-condition combinations. |
| `harness/` | The same comparison on Sample Games 1 to 3, as a reusable harness. | v1 ahead on whole-game spellF1 in all 27 cells; pooled +0.036 [+0.018, +0.054]. Registered verdict: "no clear winner (leaning v1)" because the half-level sign rule failed. |
| `harness_baselines/` | The organizers' four baselines (raw, smooth25, smooth50, smooth125) against v1 on Sample Games 1 to 3. | smooth50 is the best baseline on every game, rule and condition; v1 has the highest spellF1 (0.426 vs 0.387 over 9 columns). Baselines trail v1 on spellF1 but lead on macroF1 (smooth25) and dead-ball F1 (raw). Full metric tables in `all_metrics.md`. |
| `logo_v1/` | Rule-compliant v1: every parameter fitted on the other two sample games, then frozen (leave-one-game-out). | spellF1 0.474 vs smooth50 0.430 (+0.045 [+0.027, +0.063]); no cost against the non-compliant fits. Registered verdict: "no clear winner, leaning v1" (half-level rule fails on Game 1). `PROVENANCE.md` lists where every v1 constant came from. |
| `logo_v1_followup/` | `N_PSPEED` chosen on external data, and a label-free domain-shift check on the provided match. | 24 player-speed bins win on held-out likelihood; spellF1 0.485 (+0.055 over smooth50, same verdict). On the provided match no output proxy is flagged; dwell and heading features shift most. |

Read the caveats in each report before relying on a number. The public ground truth is only 5 minutes
(17 possessions), and the proxy labels for the sample games come from event data and are not the
competition's ground truth. In all three sample games the ball track is blank during stoppages, which
flatters rules that treat a missing ball as dead ball.

## Why some tables repeat
`harness_baselines/`, `logo_v1/` and `logo_v1_followup/rerun/` each have their own `summary.md` and `all_metrics.md`, and the
four organizer baselines appear in all three. This is deliberate: each folder is one self-contained run with its own label
files, predictions and decision rule, and each run compares a different set of methods (v1, then `v1_logo`, then `v1_logo_p24`).
The baseline numbers are identical across them, which doubles as a check that the runs are comparable.

Prediction files for the full match are in `../submissions/` (see its README for which are duplicates and why they stay).

## What is not in this folder, and why
Kept out of git by `analysis/.gitignore`:
- **Parsed tracking caches** (`*/cache/`, `*.npz`). `RULES.md` forbids publishing tracking exports.
- **Per-frame labels, predictions and converted files** derived from Metrica's sample games
  (`labels/`, `predictions/`, `raw/`, `labels_*.csv`, `validate/*.csv`).
- Logs, pickles, and the repeated per-stage `eval_out/reports/` copies.

Every report ends with the commands that regenerate its outputs; the ignored files reappear locally.

## Data needed to reproduce
Neither dataset is included.
- The competition bundle goes in `data/` as described in `DATA.md`.
- `pilot_game3/`, `harness/`, `harness_baselines/`, `logo_v1/` and `logo_v1_followup/` also need Metrica's public sample data,
  https://github.com/metrica-sports/sample-data, placed in `data/other_games/metrica_sample/`.
  Its README says: "Please be responsible with the use of this data. If you use it for anything public,
  please aknowledge the source." There is no formal licence file; the data is free to use with that
  attribution, which this repository gives to Metrica Sports (sample-data repository above).
