# Pre-registration: rule-compliant leave-one-game-out (LOGO) evaluation of v1

Written 2026-11-10, **before `v1_logo` has been run or scored on any game, ball condition or rule.** Append-only afterwards
(dated notes with reasons). Builds on `analysis/harness/PREREGISTRATION.md` (unchanged, referred to as "H-PREREG") and on
`analysis/logo_v1/PROVENANCE.md` (which lists every quantity fitted or fixed).

## 0. What I have already seen (disclosure)

* I have seen the scores of `raw, smooth25, smooth50, smooth125, v1_refit, v1_transfer` on the three sample games
  (`analysis/harness_baselines/`). Their predictions are deterministic; the new run recomputes them and I confirm identical
  md5s (s.6). Nothing below was chosen to favour or disfavour `v1_logo` against those numbers.
* **No `v1_logo` or `v1_external_all` prediction or score exists.** Before this file was written I only read code, ran no
  fit, and timed nothing.
* Not yet seen: how `v1_logo`'s parameters differ from the shipped v1 (it is possible, even likely, that they differ a lot;
  that is a finding, not a defect).

## 1. Question

Does v1, with **no parameter fitted on the match it is applied to (nor on the provided match)**, still beat the organisers'
`smooth50` baseline on held-out games? This is the version of v1 that satisfies the organisers' latest rules, so it is the
only one that can be submitted. `v1_refit` (EM on the very game it is scored on) and `v1_transfer` (parameters from the
provided match) are **not rule-compliant**; they are shown as reference points only.

## 2. Methods

| name | what | status |
|---|---|---|
| `raw`, `smooth25`, `smooth50`, `smooth125` | the organisers' four baselines (vote half-width 0/25/50/125 frames), organisers' code unchanged | comparators |
| `v1_refit` | v1 with EM, constants and bin edges refitted on the scored game itself | comparator, **not compliant** (fits on the scored game) |
| `v1_transfer` | v1 parameters fitted on the provided match, decoding only | comparator, **not compliant** (fitted on the provided match); run for continuity if cheap, else reported from `analysis/harness_baselines` (same code, deterministic) |
| **`v1_logo`** | for held-out game G: fit every parameter in PROVENANCE section A on the **other two** games' tracking only, unsupervised; freeze; Viterbi on G | **the method under test** |
| `v1_external_all` | same fit on all three sample games pooled, frozen, exported to `frozen_params.json`. **Not run on any game here** | deliverable only |

Registered primary comparison: **`v1_logo` vs `smooth50`** (the same reference as H-PREREG). Secondary, reported with the same
rule but labelled descriptive and not corrected for multiplicity: `v1_logo` vs `raw`, `smooth25`, `smooth125`, `v1_refit`,
`v1_transfer`.

## 3. The exact LOGO procedure (fixed)

For each held-out game G in {game1, game2, game3} and each ball condition C in {asis, degraded_seed0, degraded_seed1}:

1. Training games T = the two other games. Each training game's ball is put through **the same condition C** (as-is: raw;
   degraded: `adapters.degrade_ball` with the same seed, gap lengths and visible share as for G). Training on the matching
   condition type is a deliberate choice: the model sees the same kind of ball it will be run on.
2. Training intervals = the games' **tracking period boundaries** (Period column / EPTS metadata), **not** the label-derived
   blocks (conservative; PROVENANCE C2). No label of any kind, including event-derived, is read by any fit.
3. Per training game: frame signals with the game's own provisional constants, then **pooled radius** = median
   nearest-player distance over the two games' pooled graded visible frames and **pooled carry** = 99th percentile of player
   speed over their pooled graded frames. Signals are re-derived with the pooled constants (`adapters.rederive`).
4. Per-block values from every half of both games; **bin edges** = the same percentiles as `features.build`, computed on the
   pooled blocks of the two games. Sequences built with those edges (`adapters.build_with_edges`); the set-piece column is
   missing (-1), as the sample games have no Smart Tagging.
5. **EM** (`hmm.fit`, unchanged settings: `PRIOR_DWELL_S` (10,10,10), prior strength 10, tol 1e-7, max 300 iterations) on the
   four sequences (two games x two halves) with shared parameters.
6. **Freeze.** Run on G: frame signals, `rederive` with the frozen radius and carry, `build_with_edges` with the frozen edges,
   `hmm.decode` with the frozen parameters, `features.upsample`. G's blocks (`ctx.blocks`) are used only as the inference
   intervals, exactly as for every other harness method. Nothing is refitted on G; G's labels are never read by the method.
7. `v1_external_all`: steps 1 (as-is only), 2-5 on all three games; written to `frozen_params.json` with a loader function.

Fits are cached per (training set, condition); the cache holds only fitted parameters.

**Regression test of the code (not a result).** Running the *same* fit function on the provided match alone (one game, its
published graded blocks and Smart Tagging, set-piece feature present) must reproduce the shipped v1 submission byte for byte
(md5 `83b587d7b36a665a69f2eaf88566e60b`). This shows the LOGO fit and the inference path are the shipped code, with only the
training data changed. It is reported as pass/fail and is never scored.

Judgment calls made now, most conservative option each time: training intervals are tracking periods (above); the
degraded-ball statistics come from the harness' existing `reference_from_provided` aggregates (PROVENANCE C3); `N_PSPEED=12`
is inherited rather than silently tuned (PROVENANCE B9).

## 4. Metrics

Scoring is the organisers' `possession_metrics.evaluate` through the harness (1,000 bootstrap draws for whole-game scope,
seed 0). Ranking metric: **spellF1 (`spell_f1_mean`, mean over IoU 0.3-0.7)**, the organisers' ranking metric. Also reported:
macro F1, alive/dead F1, team accuracy (both-alive and GT-alive), predicted / labelled possession count, transition F1 at
tau = 12 and 25 frames, per game and pooled (equal-weight mean over games). Headline view: **primary label rule, ball
as-is.** Labels are the harness' event-derived proxies (same files as `analysis/harness_baselines`).

## 5. Decision rule (reused from H-PREREG s.5, unchanged)

X = `v1_logo`, Y = `smooth50`; differences are in `spell_f1_mean`, X - Y; pooled statistic and paired bootstrap as H-PREREG s.4
(game-stratified, 1,000 draws, seed 0). The direction is the sign of clause (a).

* (a) pooled over games, primary rule, as-is: non-zero and the paired 90% interval excludes 0;
* (b) in each game, primary rule, as-is: the difference has the sign of (a);
* (c) pooled, as-is: the sign of (a) under S1 and under S2;
* (d) pooled, primary rule: the sign of (a) under degraded seed 0 and seed 1;
* (e) in at least 80% of the 27 game x rule x condition cells, the sign of (a) in both halves.

"X wins" = (a)-(e) all hold in X's favour; "Y wins" = all in Y's favour; otherwise "no clear winner", failing clauses named.
Computed by the harness (`decisions["v1_logo"]`, reference smooth50) and, for the secondary comparisons, by
`possession/harness/logo_decisions.py`, which calls the same `pooled.pooled_paired` and `pooled.decide`.

Descriptive quantities (no decision rule): the loss of `v1_logo` relative to `v1_refit` and `v1_transfer` (pooled paired
difference with its 90% interval); the stability of the fitted parameters (s.7).

## 6. Run and checks

`python -m possession.harness.run --plugin possession.harness.baseline_windows --plugin possession.harness.logo_v1
--methods raw,smooth25,smooth50,smooth125,v1_refit,v1_logo --out analysis/logo_v1` (`v1_transfer` added if time allows).
Then `possession.harness.all_metrics` and `possession.harness.summarize_baselines` on the new folder.

Checks that must pass or be reported as failures: (i) the 27 label files are byte-identical (md5) to those in
`analysis/harness_baselines/labels`; (ii) the baselines' prediction files are byte-identical to the previous run's; (iii) the
harness' adapter validation (shipped v1 and smooth50 on the provided match, code regression only) passes; (iv) the regression
test of s.3 passes; (v) a leakage audit: the fit function receives only the two training games' tracking arrays and
period boundaries, and its signature has no label or provided-match argument.

## 7. Parameter-stability analysis (fixed in advance)

Quantities: radius, carry, each bin edge, diagonal of A, and per-feature emission tables. Compared across (1) the three LOGO
as-is fits, (2) three single-game as-is fits (each game alone, reported for stability only, never scored), (3) the
all-games fit, (4) the shipped v1 (provided match) and (5) each game's own `v1_refit` fit where available. For scalars:
range and relative range ((max-min)/mean). For emission tables: mean total-variation distance between fits per feature.
"Moved most" = largest relative range among scalars and largest mean TV among features, ranked, no threshold.

## 8. Not done / out of scope

No submission CSV; no run on the provided match; no tuning of any kind on any sample game (the number of bins, the priors and
the EM settings are frozen from the shipped v1); no second variant of `v1_logo` is scored. If any variant is later added it is
labelled exploratory.

---
## Append-only notes

### 2026-11-10 (note 1): corrections and deviations, written after the run

* s.6(i) says "27 label files"; there are **9** (3 games x 3 rules). All 9 are byte-identical to `analysis/harness_baselines/labels` (md5).
  The check in s.6(ii) was run on all 45 baseline/`v1_refit` prediction files: all byte-identical.
* `v1_transfer` was **not re-run** (s.2 allowed this). Its numbers come from `analysis/harness_baselines` (same code, deterministic).
  The paired `v1_logo` - `v1_transfer` difference is computed from that run's saved predictions with the same function.
* s.7 item (5) "each game's own v1_refit fit" is not available (the harness does not save `v1_refit` parameters); the single-game
  fits (item 2) stand in for it. They use tracking periods as intervals, `v1_refit` used the label-derived blocks.
* The harness run re-ran the adapter validation on the provided match (shipped v1 fitted on it, md5 check). That is the code
  regression the task asks for; it feeds no `v1_logo` number. `run.py` also fits v1 on the provided match inside
  `reference_from_provided()` to build the `v1_transfer` reference pack; no `v1_logo` code path reads that pack.
* No decision rule, metric, procedure or constant was changed after seeing results.
