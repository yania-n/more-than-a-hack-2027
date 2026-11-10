# Rule-compliant v1 (leave-one-game-out) vs the organisers' baselines

Run 2026-11-10 under `PREREGISTRATION.md` (written before any `v1_logo` score; corrections in its note 1). Parameter inventory:
`PROVENANCE.md`. Data: Metrica Sports public sample data, https://github.com/metrica-sports/sample-data (Sample Games 1-3), used
as the repository asks ("be responsible", "acknowledge the source"). Labels are event-derived **proxies**, not the competition's
ground truth. Own work only: no organiser file was modified.

## 1. Verdict (pre-registered rule, `v1_logo` vs `smooth50`)

**No clear winner, leaning `v1_logo`. Clauses (a)-(d) hold; (e) fails.**

| clause                                                  | result                                                                                                                                                |
| ------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| (a) pooled, primary, as-is: spellF1 diff, 90% paired CI | **+0.045 [+0.027, +0.063]**, excludes 0                                                                                                         |
| (b) same sign in each game (primary, as-is)             | yes: game1 +0.012, game2 +0.072, game3 +0.050                                                                                                         |
| (c) same sign pooled under S1 and S2                    | yes (+0.044, +0.029)                                                                                                                                  |
| (d) same sign pooled under degraded seeds 0 and 1       | yes (+0.042, +0.041)                                                                                                                                  |
| (e) both halves agree in >= 80% of 27 cells             | **no, 67% (18/27)**. All 9 failing cells are Game 1: one of its halves has `v1_logo` not ahead of `smooth50` under every rule and condition |

Against the other comparators, same rule (`decisions.md`):

| comparator                           | primary/as-is diff [90% CI] | verdict                                        |
| ------------------------------------ | --------------------------: | ---------------------------------------------- |
| raw                                  |     +0.368 [+0.347, +0.392] | `v1_logo` wins                               |
| smooth25                             |     +0.097 [+0.078, +0.117] | `v1_logo` wins                               |
| smooth50 (registered primary)        |     +0.045 [+0.027, +0.063] | no clear winner, leaning `v1_logo` (fails e) |
| smooth125                            |     +0.163 [+0.143, +0.184] | `v1_logo` wins                               |
| v1_refit (not compliant)             |     +0.009 [-0.004, +0.022] | no clear winner (fails a, b, c, e)             |
| v1_transfer (not compliant, old run) |     -0.001 [-0.010, +0.009] | indistinguishable                              |

For reference, `v1_refit` vs `smooth50` fails the same clause (e, 52% of cells). So the strict half-by-half agreement clause is the
binding constraint for both versions of v1, not the size of the gain. By the rule as written I cannot claim `v1_logo` beats
`smooth50`; the evidence is that it is ahead on average, in every game and condition on the pooled number, with a CI above 0.

## 2. Results (primary rule, ball as-is unless stated; equal-weight mean over the 3 games)

| method                               |         spellF1 | macroF1 | alive/dead F1 | team acc (both alive) | team acc (GT alive) | predicted / real possessions | trans. F1 tau 12 | trans. F1 tau 25 |
| ------------------------------------ | --------------: | ------: | ------------: | --------------------: | ------------------: | ---------------------------: | ---------------: | ---------------: |
| raw                                  |           0.106 |   0.803 |         0.943 |                 0.805 |               0.729 |                         6.39 |            0.257 |            0.285 |
| smooth25                             |           0.378 |   0.814 |         0.930 |                 0.855 |               0.784 |                         1.92 |            0.151 |            0.391 |
| smooth50                             |           0.430 |   0.801 |         0.915 |                 0.872 |               0.807 |                         1.42 |            0.134 |            0.235 |
| smooth125                            |           0.311 |   0.728 |         0.883 |                 0.856 |               0.808 |                         1.06 |            0.060 |            0.120 |
| v1_refit (not compliant)             |           0.466 |   0.766 |         0.875 |                 0.883 |               0.746 |                         1.01 |            0.242 |            0.349 |
| v1_transfer (not compliant, old run) |           0.475 |   0.769 |         0.880 |                 0.881 |               0.759 |                         1.16 |            0.269 |            0.381 |
| **v1_logo**                    | **0.474** |   0.766 |         0.879 |                 0.881 |               0.761 |               **1.02** |            0.241 |            0.362 |

spellF1 per game (primary, as-is) with the harness' per-method 90% bootstrap over possessions:

| method   |                game1 |                game2 |                game3 | pooled |
| -------- | -------------------: | -------------------: | -------------------: | -----: |
| smooth50 | 0.452 [0.420, 0.486] | 0.433 [0.403, 0.463] | 0.404 [0.372, 0.433] |  0.430 |
| v1_refit | 0.494 [0.454, 0.534] | 0.456 [0.424, 0.493] | 0.446 [0.413, 0.478] |  0.466 |
| v1_logo  | 0.464 [0.426, 0.502] | 0.505 [0.467, 0.542] | 0.454 [0.417, 0.489] |  0.474 |

Across all 9 rule x condition columns the mean spellF1 is v1_logo 0.426, v1_refit 0.426, smooth50 0.387, smooth25 0.330,
smooth125 0.305, raw 0.090. `v1_logo` has the highest spellF1 in 17 of 27 game x rule x condition cells, `v1_refit` in 10, no baseline
in any. Full tables (every organiser metric, five views): `all_metrics.md`; baseline summary: `summary.md`.

What `v1_logo` does and does not buy: the gain over `smooth50` is in spellF1, team accuracy when both are alive (+0.009), the
possession count (1.02x the real count vs 1.42x) and transition F1 (0.24 vs 0.13 at tau 12; 0.36 vs 0.24 at tau 25). It is **worse**
than the baselines on macroF1 (0.766 vs 0.801-0.814) and alive/dead F1 (0.879 vs 0.915-0.943), and `smooth125` is better on team
accuracy when the GT is alive. Those losses come from the sample games' blank ball in stoppages, which hands the baselines the dead
ball for free (see caveats).

## 3. Cost of compliance

* vs `v1_refit` (EM on the scored game itself): pooled **+0.009 [-0.004, +0.022]** spellF1 in the primary/as-is column; -0.012 to +0.006
  in the other columns. So `v1_logo` loses **nothing measurable** (the point estimate is even slightly positive; it is a tie).
  Per game: Game 1 -0.030, Game 2 +0.049, Game 3 +0.008.
* vs the old `v1_transfer` (parameters from the provided match): -0.001 [-0.010, +0.009] primary/as-is; +0.022 under S1 (CI above 0);
  -0.009 under degraded seed 1. A tie as well.
* Reading: v1's score does not depend on where its parameters were fitted, within the noise of three games. That is the useful
  finding for the compliance question: dropping the provided-match fit costs nothing on the sample games. It does **not** show that the
  parameters will suit the provided match (section 5).

## 4. Which parameters moved, and is the fit stable? (`stability.md`)

Three LOGO folds (as-is), three single-game fits, the all-games fit, and the shipped v1:

* **Control radius is the one that does not transfer:** 0.277 m for the fold that holds out game 3 (trained on games 1+2), 0.922 / 0.925 m for the folds
  that include game 3, game 3 alone 1.27 m, games 1 and 2 alone 0.276 / 0.277 m, **shipped (provided match) 1.91 m**. Relative range across LOGO folds 0.92.
  In Games 1 and 2 the ball sits within about 0.3 m of the nearest player on at least half of the visible frames, which looks like
  provider post-processing that snaps the ball to a player; Game 3 and the provided match are looser. "Median nearest-player distance"
  is therefore a property of the tracking provider, not of football. `v1_logo` is nevertheless as good as `v1_refit`, so the model
  tolerates the change (the radius only feeds the dwell feature).
* **Heading bin edges** collapse in the sample games: edge[1] 0.03-0.36 degrees vs 2.74 shipped (relative range 2.28). The sample
  games' ball track has almost no heading jitter (it looks smoothed or interpolated), so the lowest heading bins are nearly empty. Flagged;
  heading is a weak feature (TV distance between folds 0.04).
* Dwell edges (relative range 0.27-0.29) and the lowest ball-speed edge (0.16) move moderately. Gap, player-speed, upper ball-speed edges and
  the carry speed (5.97-6.09 m/s vs 6.44 shipped) are stable (relative range <= 0.08).
* **Transition stay-probabilities are very stable** (H 0.950-0.953, A 0.948-0.952, D 0.962-0.971) but differ from the shipped fit
  (0.935 / 0.908 / 0.975): the sample games' possession is stickier than the provided match's.
* Emission tables: mean total-variation distance between folds is small (0.02-0.07 per feature: ball speed 0.073, dwell 0.073,
  player speed 0.071, heading 0.040, gap 0.037, outside 0.017) and similar to that between single-game fits, but larger against the shipped
  fit for dwell (0.14). The fitted structure is stable across games; the units (radius, heading) are not.
* EM converged in all fits (21-72 iterations; shipped 23).

## 5. Caveats

* **Proxy labels.** Event-derived, with CARRY excluded for all games; the organisers' ground truth is different. Ranking among methods
  may differ on the real match.
* **Blank ball in stoppages in all three sample games** (ball visible on 8% / 0.2% / 0.2% of dead frames). It makes "missing ball = dead"
  (the baselines) look better than on the provided match, and means v1 is trained on dead-ball data that carries an unrealistic cue.
  The provided match is described as having the ball visible about 66% of the time, so `v1_external_all` may meet a different
  dead-ball signature than it was fitted on. The degraded condition only adds gaps; it does not remove this artefact.
* **Three games, three tracking providers' conventions, one tracking-derived speed.** The radius and heading evidence in section 4 shows
  the games differ in tracking post-processing. 3 games is too few for the registered pass/fail rule to be sharp (clause e fails
  because of one game, Game 1).
* **Frozen parameters are not validated on the provided match** (by design: not run here, no submission produced). The parameters
  for it come from three other matches whose radius is 0.28-1.27 m against 1.91 m measured on it.
* **Inherited hand choices.** `N_PSPEED = 12` was chosen by looking at the provided match's learned emission (PROVENANCE B9); it is
  kept as is, not re-derivable without a human decision. `SETPIECE_LEAD` (10 s) is also provided-match-informed but inert: the sample
  games have no Smart Tagging, so the set-piece feature is missing. **If the provided match's Smart Tagging were used at submission time,
  `v1_external_all` has no fitted set-piece emission** (uninformative prior): that feature would add nothing, or the model would need
  external data with set-piece tags.
* **Training intervals** are tracking periods (no label-derived blocks), which include up to about 60 s per half before kick-off / after the
  final whistle. The held-out game's blocks are the harness' event-derived play intervals, as for all methods (the analogue of the
  published graded blocks).
* **Degraded-ball condition** uses the provided match's ball-gap statistics (an unlabelled aggregate, shared by all methods and by the
  training games). It tunes nothing in v1, but it is a read of the provided tracking, flagged in PROVENANCE C3.
* **Licence.** The Metrica repository has no LICENSE file; the only terms are the README's "be responsible" and "acknowledge the source".
  The data stays gitignored; this folder holds fitted numbers and aggregate scores, not tracking or event rows. Whether fitted
  parameters derived from it count as "external data" for the competition, and whether using them is "public use", is a question
  for the organisers; I did not assume.
* **Selection.** Picking `smooth50` as the reference was registered before this run, but "best baseline window" is itself a choice made
  on these same three games.

## 6. Compliance statement

| quantity                                                                                                  | fitted on                                                                 | provided match? ground truth? public window? video? hand labels?                                                                 |
| --------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| control radius, carry speed, bin edges, emission tables, transition matrix (`v1_logo`, fold for game K) | tracking of the two other sample games, unsupervised, same ball condition | none used                                                                                                                        |
| `frozen_params.json` (`v1_external_all`)                                                              | tracking of sample games 1-3 pooled, as-is, unsupervised                  | none used                                                                                                                        |
| hand-fixed constants (BLOCK, thresholds, bin counts, priors, EM settings)                                 | none (inherited from v1)                                                  | `N_PSPEED` and `SETPIECE_LEAD` were originally chosen with the provided match in view (inherited, flagged, the second inert) |

Confirmed: no provided-match data, ground truth, public window, video or hand label entered any `v1_logo` or `v1_external_all` fit.
Sample-game labels were used only to score held-out predictions. The fit function takes tracking arrays and interval boundaries only
(`fit_frozen(train, setpiece_missing, verbose)`; `test_logo_v1.py` asserts the signature). The provided match was read in three places,
none of which fits a `v1_logo` parameter: (1) the harness' adapter validation (shipped v1 reproduced to md5 `83b587d7...`, a code
regression), (2) `reference_from_provided()` which builds the `v1_transfer` comparator pack and the degraded-ball statistics, (3) the
ball-gap statistics read by `logo_v1.provided_ball_stats()` for the degraded condition. No data was uploaded anywhere. No submission CSV
was produced and nothing was committed.

Code regression: fitting on the provided match alone with the LOGO fit function and decoding it reproduces the shipped v1 submission
byte for byte (md5 `83b587d7b36a665a69f2eaf88566e60b`), so the fit and inference are the shipped code with only the training data
changed. Run `python -m possession.harness.test_logo_v1`.

Judgment calls (most conservative option each time): training intervals = tracking periods; `N_PSPEED` inherited, not tuned;
`v1_external_all` fitted as-is only; `v1_transfer` not re-run; no variant of `v1_logo` scored.

## 7. Files

`PROVENANCE.md`, `PREREGISTRATION.md` (+ note 1), `results.json/csv` (harness), `decisions.md/json` (all comparators),
`all_metrics.md/json`, `summary.md`, `stability.md/json`, `frozen_params.json`, `fits/` (cached fitted numbers), `labels/`, `predictions/`,
`run.log`, `fit.log`. Code: `possession/harness/{logo_v1,logo_decisions,logo_stability,test_logo_v1}.py`; `all_metrics.py` and
`summarize_baselines.py` now accept `v1_logo`.
