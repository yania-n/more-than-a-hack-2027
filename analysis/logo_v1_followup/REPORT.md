# Follow-up to the rule-compliant v1: N_PSPEED on external data, and a domain-shift check on the provided match

Run 2026-11-10 under `PREREGISTRATION_A.md` and `PREREGISTRATION_B.md` (written before any run; notes appended after).
Fitted numbers come from Metrica Sports' public sample data (Sample Games 1-3), https://github.com/metrica-sports/sample-data,
acknowledged as its README asks; the data stays gitignored. Labels are event-derived proxies. This is a follow-up to the registered
`analysis/logo_v1` run, not a replacement of it. Nothing was committed; no organiser file was modified.

## Part A: N_PSPEED chosen on external data, label-free

### Result
Leave-one-game-out, as-is ball, tracking-period intervals. Each cell is the held-out game's forward log-likelihood per block under the
fit on the other two games. Selection uses the **density-corrected** value (a histogram-density likelihood; the raw discrete value
cannot rank bin counts because it falls by about log n by construction, which I registered before running). Full tables, including the
dead-ball cutoffs and EM iterations: `partA_table.md`, `partA_ll.json`.

| N_PSPEED | held-out game1 | held-out game2 | held-out game3 | mean | best - this | SE (paired) | within 1 SE | raw discrete mean |
|---:|---:|---:|---:|---:|---:|---:|---|---:|
| 6 | -4.1163 | -3.9791 | -4.5776 | -4.2243 | 0.405 | 0.061 | no | -4.252 |
| 8 | -4.0210 | -3.8703 | -4.3964 | -4.0959 | 0.276 | 0.035 | no | -4.538 |
| 12 | -3.8936 | -3.7578 | -4.2095 | -3.9537 | 0.134 | 0.012 | no | -4.935 |
| 16 | -3.8418 | -3.6933 | -4.1418 | -3.8923 | 0.073 | 0.009 | no | -5.225 |
| **24** | -3.7761 | -3.6315 | -4.0512 | **-3.8196** | 0 | 0 | **yes** | -5.628 |

**Chosen N_PSPEED = 24, which differs from 12.** Every step to a finer grid improved all three folds, and 12 is beaten on every fold by
0.12-0.16 nats per block (about 3% of the likelihood), so 12 has no external justification under this rule. The alternative 0.5%
tolerance also picks 24. **Limitation:** the best value is the largest candidate, so the likelihood is still rising at the edge of the
registered set; 24 is the best of {6, 8, 12, 16, 24}, not a located optimum. I did not extend the set after seeing this.

Diagnostic (criterion 2), learned dead-ball cutoff in player speed (D:alive likelihood ratio first below 1), per fold:
12 bins 1.31 / 1.27 / 1.36 m/s (spread 0.09); 24 bins 1.39 / 1.37 / 1.36 (spread 0.03); the other candidates 1.21-1.39. One clean
crossing in every fold. The cutoff is a bin edge by construction; with 24 bins the bins around it are about 0.08 m/s wide (0.17 with 12),
and the three folds agree more closely. So the cutoff is about 1.3-1.4 m/s whatever the grid, and the finer grid pins it down better.

### Re-run with 24 bins (follow-up; same harness, same checks)
Checks: the 9 label files and all 54 prediction files of `raw, smooth25, smooth50, smooth125, v1_refit, v1_logo` are byte-identical to
`analysis/logo_v1`; the adapter validation passed; the code regression (shipped v1 md5 `83b587d7...`) passes.

| primary rule, as-is | spellF1 | game1 | game2 | game3 | macroF1 | alive/dead F1 | team acc (both alive) | predicted / real possessions | trans. F1 tau 12 / 25 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| smooth50 | 0.430 | 0.452 | 0.433 | 0.404 | 0.801 | 0.915 | 0.872 | 1.42 | 0.134 / 0.235 |
| v1_refit (not compliant) | 0.466 | 0.494 | 0.456 | 0.446 | 0.766 | 0.875 | 0.883 | 1.01 | 0.242 / 0.349 |
| v1_logo (12 bins) | 0.474 | 0.464 | 0.505 | 0.454 | 0.766 | 0.879 | 0.881 | 1.02 | 0.241 / 0.362 |
| **v1_logo_p24** | **0.485** | 0.468 | 0.510 | 0.478 | 0.771 | 0.877 | 0.888 | 1.02 | 0.250 / 0.367 |

Pre-registered decision rule, unchanged (`rerun/decisions_v1_logo_p24.md`):

| comparator | primary/as-is diff [90% CI] | clauses a b c d e | halves | verdict |
|---|---:|---|---:|---|
| smooth50 | **+0.055 [+0.038, +0.074]** | Y Y Y Y **n** | 67% | no clear winner, leaning `v1_logo_p24` (fails e; all 9 failing cells are Game 1, as before) |
| v1_logo (12 bins) | +0.011 [+0.003, +0.019] | Y Y Y Y **n** | 37% | no clear winner, leaning 24 bins |
| v1_refit (not compliant) | +0.020 [+0.006, +0.034] | Y n Y Y n | 44% | no clear winner |
| raw / smooth25 / smooth125 | +0.379 / +0.107 / +0.174 | all Y | 100 / 100 / 89% | `v1_logo_p24` wins |

Effect: +0.011 spellF1 over the 12-bin `v1_logo` (+0.004, +0.005, +0.024 in games 1, 2, 3), positive in eight of the nine rule x
condition columns (+0.002 to +0.011) and a tie in the ninth (S2 / degraded seed 0, -0.000). The verdict against `smooth50`
does not change: same four clauses hold, same clause fails. This was chosen by likelihood, not by spellF1; it happens to help spellF1
slightly. It is a follow-up and the registered `v1_logo` verdict stands as the registered result.

New frozen parameters: `analysis/logo_v1_followup/frozen_params_np24.json` (all three sample games, as-is, 24 player-speed bins). The old
`analysis/logo_v1/frozen_params.json` is untouched.

## Part B: domain-shift check on the provided match (descriptive; the provided match is input to a frozen model only)

Model: `frozen_params_np24.json`. Pipeline: the shipped v1's (the provided ATD tracking including its own player-speed column, the
published graded blocks, no set pieces). Decode deterministic (md5 of the output `46004ab2...`, run twice). Output in `private/`
(gitignored), not in `submissions/`.

### B1 feature shift over the frozen bins (`partB_features.md`)

| feature | TV provided vs sample games | largest sample-game TV (LOO) | missing share provided | sample games | flags |
|---|---:|---:|---:|---:|---|
| gap | 0.075 | 0.086 | 59.6% | 58.6-62.1% | - |
| **dwell** | **0.494** | 0.188 | 59.6% | 58.6-62.1% | TV > 2 x largest sample-game TV |
| ball speed | 0.074 | 0.064 | 40.8% | 32.2-41.1% | - |
| **heading** | **0.481** | 0.126 | 54.5% | 46.3-54.5% | TV > 2 x largest sample-game TV |
| outside | 0.025 | 0.018 | 39.9% | 31.5-40.1% | - |
| player speed | 0.066 | 0.115 | 0.2% | 0.0% | missing share band (degenerate: 0.2% vs 0.0%; immaterial) |
| set piece | missing in all | | | | |

* **Dwell:** +49 pp of blocks fall in the "nobody within the control radius" bin, and the three strongest dwell bins lose 10-12 pp each.
  The frozen radius is 0.76 m (sample games: 0.28-1.27 m); the provided match's median nearest-player distance is 1.91 m (the shipped
  radius, which is that median), so far fewer than half of its visible frames have a player within 0.76 m.
* **Heading:** mass leaves the two lowest bins (-24 and -24 pp) for bins 2 and 3 (+30 and +19 pp). The lowest frozen heading edges are about
  0.01-0.04 degrees (the sample games' ball track is very smooth); the provided ball track turns more.
* The missing shares are inside the sample games' ranges (near the upper end for ball speed, heading and outside; gap/dwell mid-range):
  the ball is about as available as in the sample games, with no sign of a gross visibility problem. Mass in bins that were rare in training (< 2%): 0% except 3.6% for
  `outside` (the "ball outside" category). Gap, ball speed, outside and player speed are within normal between-game variation.

### B3 label-free output proxies (`partB_proxies.md`)

| proxy | v1_external_all | smooth50 | old v1 (not compliant) | sample proxy labels (min-max) | flag band | sample v1_logo | sample smooth50 |
|---|---:|---:|---:|---:|---:|---:|---:|
| possessions / alive minute | 7.47 | 8.29 | 8.67 | 5.05 - 5.69 | 2.52 - 11.38 | 5.25 - 6.27 | 7.39 - 7.78 |
| mean possession (s) | 8.04 | 7.24 | 6.92 | 10.54 - 11.89 | 5.27 - 23.77 | 9.57 - 11.43 | 7.71 - 8.12 |
| possessions < 2 s | 19.4% | 31.3% | 26.6% | 19.7 - 24.5% | 9.9 - 49.0% | 10.4 - 15.0% | 35.5 - 37.9% |
| reversal within 3 s | 26.6% | 29.5% | 36.8% | 17.7 - 24.5% | 8.9 - 49.1% | 18.3 - 21.7% | 36.4 - 40.6% |
| dead-ball share of frames | 39.4% | 32.3% | 38.7% | 26.7 - 34.1% | 13.3 - 68.3% | 28.7 - 38.4% | 25.1 - 33.7% |
| mean dead-ball spell (s) | 14.91 | 15.45 | 16.95 | 16.90 - 23.94 | 8.45 - 47.89 | 11.80 - 13.47 | 15.17 - 22.18 |
| home share of alive frames | 65.2% | 57.0% | 65.9% | 50.9 - 52.4% | 25.5 - 104.8% | 55.1 - 58.3% | 51.4 - 53.2% |

Counts (spells / direct transitions / graded minutes): v1_external_all 479 / 312 / 105.9, smooth50 594 / 461 / 105.9, old v1 563 / 419 / 105.9.

Agreement (descriptive, not a score): v1_external_all vs the old shipped v1 (reference): frame agreement 0.962, spell-level F1 0.828.
v1_external_all vs smooth50: 0.709 / 0.362, similar to old v1 vs smooth50 (0.713 / 0.353) and to v1_logo vs smooth50 on the sample games
(0.73-0.80 / 0.38-0.40).

**Flagged "needs investigation" (registered bands): none.** The frozen model's proxies sit inside the band set by the sample games' proxy
labels and within a factor 1.5 of the old v1 on every proxy (home share within 10 points). Read as "plausible", not "correct". Honest
observations beyond the registered bands: (1) the possession rate (7.5 per alive minute), mean possession (8.0 s) and dead-ball share
(39%) are all on the faster / deader side of the sample labels (5.1-5.7, 10.5-11.9 s, 27-34%) and sit with the old v1 and smooth50;
this can reflect the match or the model, and I cannot separate them without ground truth, which I did not read. (2) The home share of alive
frames is 65% for both v1 versions and 57% for smooth50, against 51-52% in the sample labels; the registered band for it is vacuous
(26-105%), so no rule could flag it. It is a number to keep an eye on, not evidence of an error.

### B4 diagnosis
**Not run**: its registered trigger (a flagged output proxy) did not occur. The two B1 flags (dwell, heading) point to the likely
sensitive inputs, but the output is still 96% identical, frame by frame, to the old v1, so these shifts have not been shown to change
what the model outputs. I did not probe them on the provided match.

### Recommendations (not adopted; any adoption needs external-data re-derivation under a new pre-registered rule)
1. Extend the N_PSPEED candidates upward (32, 48, ...) on the sample games, since the optimum was at the edge; new registration first.
2. Dwell and heading are the provider-dependent features (radius 0.28-1.91 m across games; ball-track smoothness). A scale-free
   construction, or a leave-one-game-out comparison of v1 without these two features, would test whether the model needs them. Use
   external data only; do not tune on the provided match.
3. Ask the organisers whether parameters fitted on the Metrica sample data count as external data for this competition (the repository has
   no LICENSE file, only "be responsible" and "acknowledge the source").

## Compliance statement

| quantity | fitted on |
|---|---|
| N_PSPEED = 24 | held-out log-likelihood of Sample Games 1-3 tracking, leave-one-game-out; no label of any kind; no provided-match data |
| all `v1_logo_p24` fits and `frozen_params_np24.json` (radius, carry speed, bin edges, emissions, transitions) | tracking of the other sample game(s), unsupervised, as-is or degraded ball as stated; tracking-period intervals |
| everything else (BLOCK, thresholds, priors, EM settings) | none (inherited from v1, see `analysis/logo_v1/PROVENANCE.md`) |

The provided match was used only as the input of a frozen model (Part B) plus the pre-existing comparators of the harness. Read from it:
the ATD tracking and metadata and the published graded blocks. **Not read:** any ground-truth CSV, the public window, the video, any hand
label. Read-only reference outputs used for proxies: `evaluation/results/baseline_smooth50.csv` (the organisers' baseline output) and
`submissions/hmm_v1.csv` (the old v1). Nothing was fitted, tuned or calibrated on the provided match in this task; no submission file
was produced; nothing was uploaded; the derived output is in a gitignored folder. As before, the harness' own adapter validation and
`reference_from_provided()` read the provided tracking (to re-verify the shipped v1 and build the `v1_transfer` comparator); no
`v1_logo` fit uses them. `N_PSPEED`'s earlier by-eye origin (PROVENANCE B9) is now superseded by this external derivation, but
`SETPIECE_LEAD` remains inert and provided-match-derived.

## Caveats
* Proxies say "plausible", not "correct". A model can sit inside every band and still mislabel possession.
* Metrica tracking differs from the provided tracking (ball smoothness, the nearest-player distance, the provider's speed column vs the
  speed derived from positions in the sample games); B1 documents two of these shifts and the model was not adapted to them.
* Three games only; the 1-SE rule rests on three folds; clause (e) of the decision rule fails for one game (Game 1) under both 12 and 24 bins.
* The blank ball during stoppages in the sample games biases the training data towards a cue that may be different in the provided match.
* The N_PSPEED choice depends on the registered density correction (outer bins closed at the training min / max) and on a candidate set
  that did not bracket the optimum.

## Files
`PREREGISTRATION_A/B.md` (+ notes), `partA_table.md`, `partA_ll.json`, `partA_choice.json`, `frozen_params_np24.json`,
`rerun/` (harness output, `decisions_v1_logo_p24.md`, `all_metrics.md`, `summary.md`), `partB_features.md/json`, `partB_proxies.md/json`,
`private/` (gitignored output), logs. Code: `possession/harness/{npspeed,domain_shift}.py`, `logo_v1.py` (bin-count support, methods
`v1_logo_p6/8/16/24`), `logo_decisions.py` (method argument), `test_logo_v1.py` (new test).
