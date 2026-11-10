# possession model v1: control signal + 3-state HMM, fitted without labels

Code: `possession/` (`python -m possession.run` -> `submissions/hmm_v1.csv`; `python -m possession.report`
-> the plots and tables here). Determinism checked: two consecutive runs give the same md5
(`83b587d7b36a665a69f2eaf88566e60b`). `validate_submission.py`: OK, 199,319 rows.

## TL;DR (read this first)

* The model works mechanically: EM converges (23 iterations, log-likelihood monotone), H/A are
  anchored correctly (posterior mean signed gap +5.3 m under H, -5.1 m under A), and the learned
  dead-ball state is slow (0.89 m/s mean player speed vs 2.3 in H/A).
* **It does not clearly beat `baseline_smooth50` in v1.** Label-free it is mixed (slightly fewer
  and fewer-short possessions; *more* reversals; poor restart agreement). On the public window
  spellF1 is 0.2824 vs 0.3256 (smooth50), well inside the noise; macroF1 is the best of all
  files (0.7495 vs 0.6207) because D is now actually detected.
* Player speed is **not** bimodal, so the stoppage-speed threshold is only weakly identified
  (cutoff 1.2-1.5 m/s depending on binning).
* Nothing was tuned on the public window. No changes were made after seeing it.

## Step 0: look before modelling (`step0.png`, `em.png`)

Graded frames only, 1 s smoothed mean player speed (`step0.png` top-left, log y):

* **Is it bimodal? No, not convincingly.** The histogram is one skewed hump (mode ~1.1 m/s, long
  right tail; percentiles 5/50/95 = 0.55 / 1.52 / 3.67 m/s). The 2-component GMM puts components
  at **1.16 m/s (sd 0.43, weight 0.53)** and **2.44 m/s (sd 1.00, weight 0.47)**. Ashman's D =
  1.67 (< 2, the usual bar for clean bimodality). BIC favours 2 components (410,858 vs 446,301),
  but that only says the distribution is non-Gaussian/skewed, not that it has two modes. **Flag:
  the D state relies on the other features (ball speed, ball-out, set-piece lead-in) as much as
  on speed.**
* Ball visible on 59.3% of graded frames. Ball speed (position difference over +-0.2 s): median
  ~5 m/s, so the ball is in "flight" (faster than the 99th-percentile player speed, 6.44 m/s) on
  39.7% of visible frames: a lot, and these frames are excluded from the control evidence.
* Ball beyond the lines by more than 0.5 m on 3.5% of visible graded frames (3,339 frames).
* Nearest-player distance: median 1.91 m; |g| = |d_A - d_H| < 1 m on a sizeable share of frames
  (contested ball), see `step0.png` bottom row.
* Event-triggered mean player speed around Smart Tagging restarts (corner/free kick): depressed
  (~0.8 m/s) from ~10 s before the tag start to ~5 s after, then jumps to 2+ m/s. Used only to
  pick `SETPIECE_LEAD`.

## Fixed constants and why

| constant | value | justification |
|---|---|---|
| `BLOCK` | 10 frames (0.4 s) | HMM runs at 2.5 Hz. Emissions are assumed conditionally independent; at 25 Hz consecutive frames are nearly identical so the evidence would be overcounted ~25x and swamp the transition prior. 0.4 s ~ one touch/pass cycle, above tracker jitter. Cost: boundaries placed to +-0.2 s. |
| control radius | 1.91 m, **computed** | median nearest-player-to-ball distance over visible graded frames; ~one stride + metre-scale tracker noise. |
| carry speed | 6.44 m/s, **computed** | 99th percentile of player speeds; a ball faster than almost any player runs is in flight, so "closest" says nothing about control -> control features set missing. |
| outside margin | 0.5 m | tracked ball position noise is sub-metre; an in-play ball often sits on a line. |
| speed smoothing | 25 frames (1 s) | removes stride oscillation. |
| flight / heading window | 5 frames (0.2 s) | short enough to see a touch, long enough that jitter does not dominate. |
| heading min move | 0.5 m per window | 2.5 m/s, above walking pace and far above noise; otherwise heading is missing. |
| set-piece lead-in | 10 s before tag start | from the unlabeled event-triggered speed profile above. Team-blind (N/A teams handled by ignoring team). |
| bins | \|g\| 4, dwell 3 (per sign, plus "none"), ball speed 5, heading 4, **player speed 12** | edges are percentiles of the pooled full-match distribution (equal mass). Player speed has 12 because with 6 bins the learned cutoff sat exactly on a bin edge; chosen from the shape of the learned emission, *before* any scoring (6/12/24 bins gave cutoffs ~1.2/1.4/1.5 m/s and D share 33/39/37%). |
| prior sojourn | 10 s for H, A and D | football reasoning: possessions and stoppages last "several to a few tens of seconds"; used only to initialise EM. |
| transition prior | Dirichlet, 10 pseudo-transitions per row | prevents exact zeros; negligible against thousands of observed steps. |
| emission pseudo-count | 1 per category | Laplace. |
| initial tilt | rho = 0.5 | weak: H tilted toward positive team-feature categories, A negative; D toward slow / ball-out / set-piece categories. EM moves freely from there. |
| pi | uniform | two sequences cannot support learning it. |

The *design* of the features (dwell, flight gating, set-piece lead-in, speed for D) was motivated
by the qualitative failure modes in `analysis/diagnose_smooth50/REPORT.md`; no number from it is
used anywhere. No ground truth, public CSV or derived quantity entered fitting or constants.

## Learned HMM parameters (plain units)

Transition matrix (rows from H, A, D; columns to H, A, D):

```
H: 0.935 0.049 0.016      expected stay: H 6.2 s
A: 0.077 0.908 0.015                      A 4.4 s
D: 0.014 0.012 0.975                      D 15.9 s
```

Posterior-weighted means:

| | H | A | D |
|---|---:|---:|---:|
| mean player speed (m/s) | 2.27 | 2.36 | **0.89** |
| mean ball speed (m/s) | 7.12 | 7.30 | 3.97 |
| signed gap g (m, + = home closer) | **+5.31** | **-5.08** | -1.06 |
| P(ball outside) | 0.020 | 0.020 | 0.118 |
| P(set-piece lead-in) | 0.052 | 0.052 | 0.152 |
| posterior share of blocks | 0.370 | 0.245 | 0.385 |

The player-speed likelihood ratio D:alive crosses 1 at **1.34 m/s**: below it the block looks dead.
D mostly shows up as a plateau of slow blocks then a cliff, the signature of a feature that is not
bimodal. Anchoring check passed (`anchor_ok`).

## Full-match label-free comparison (`comparison.md`)

All numbers computed by the same code (`possession/diagnostics.py`) for every file; possessions
are the scorer's own H/A runs.

| metric | smooth50 | **hmm_v1** | raw | smooth25 | smooth125 |
|---|---:|---:|---:|---:|---:|
| possessions | 594 | **563** | 1949 | 746 | 398 |
| possessions / min | 5.61 | 5.32 | 18.40 | 7.04 | 3.76 |
| median possession (s) | 4.60 | 4.40 | 0.92 | 3.04 | 8.14 |
| % possessions < 2 s | 31.3 | **26.6** | 69.3 | 34.3 | 27.6 |
| transitions / min | 6.85 | 6.67 | 19.80 | 8.28 | 4.49 |
| reversal rate (regain < 3 s), % | 29.5 | **36.8** | 76.9 | 42.7 | 26.1 |
| D share of graded, % | 32.3 | 38.7 | 40.7 | 36.5 | 22.3 |
| median D stretch (s) | 7.6 | 8.8 | 10.7 | 9.6 | 10.9 |
| restart: D ends within +-2 s of tag start, % (58 restarts) | 15.5 | **8.6** | 13.8 | 17.2 | 29.3 |
| restart: any D within +-2 s, % | 69.0 | 84.5 | 77.6 | 77.6 | 48.3 |
| ball outside pitch labelled D, % | 0.0 | **53.9** | 0.0 | 0.0 | 0.0 |
| hand-over plausible (new team still nearest & in radius 1-2 s later), % | 32.9 | 36.2 | 29.1 | 36.4 | 25.3 |
| home share of alive, % | 57.0 | 65.9 | 56.4 | 57.4 | 56.7 |

(Smooth50 here: 594 possessions, 5.6/min, median 4.6 s, 31% < 2 s, 6.9 trans/min: matches what the
diagnosis quotes, so the definitions agree.)

What it says, plainly:

* **Dead ball:** much better than the baseline. 54% of ball-outside frames are D (baseline 0%, but
  note the HMM is *given* this feature, so it is not independent evidence), D share 38.7%.
* **Flicker:** only a modest improvement. 563 vs 594 possessions, 27% vs 31% under 2 s. The HMM
  still produces ~5.3 possessions/min, far above what the sojourn it learned (4-6 s) implies is
  smooth. The stay probabilities learned by EM are not sticky enough to suppress flips.
* **Reversals got worse** (36.8% vs 29.5%): the model flips to the other team and back more often
  than the vote does, i.e. problem #2 of the diagnosis is not fixed.
* **Restart agreement is poor:** only 8.6% of D stretches end within 2 s of a tag *start*. Caveat:
  the tags are 35 s phases and may not start at the whistle, so this metric may be biased; "any D
  within 2 s" is 84.5%, so D is present around restarts but ends at the wrong time.
* **Hand-over plausibility** 36% vs 33%: marginally better, still low.
* **Home share 65.9% vs 57%**: the HMM leans home. Possibly real (Barcelona), but a +9-point shift
  from a symmetric-by-construction emission model deserves a look (asymmetric learned transitions:
  A -> H 0.077 vs H -> A 0.049, shorter A sojourns).

## Public window (correctness check only; 17 possessions)

`python evaluation/run_evaluation.py --results submissions --bootstrap 1000 --out analysis/hmm_v1/eval_out`

| submission | macroF1 | spellF1 | 5-95% bootstrap (spellF1) | poss | dur |
|---|---:|---:|---|---:|---:|
| baseline_smooth125 | 0.5812 | 0.4242 | 0.267 .. 0.594 | 16 | 18.5 |
| baseline_smooth50 | 0.6207 | 0.3256 | 0.214 .. 0.447 | 26 | 10.8 |
| baseline_smooth25 | 0.6200 | 0.2868 | 0.196 .. 0.385 | 36 | 7.6 |
| **hmm_v1** | **0.7495** (0.576 .. 0.810) | 0.2824 | 0.188 .. 0.377 | 34 | 7.2 |
| baseline_raw | 0.5972 | 0.0378 | 0.019 .. 0.060 | 131 | 2.0 |

Sanity checks (this is the bug-hunt the task asked for, not tuning): H/A are not swapped (H F1
0.75, A F1 0.72; team accuracy on both-alive frames 0.78); halves are not mixed; frames are
aligned (D F1 0.77, alive/dead F1 0.947). hmm_v1 is not "much worse" than smooth50, so there is no
evidence of a bug. **Noise caveat:** one possession moves spellF1 by ~6 points here and the widest
bootstrap interval is ~0.33 wide; all spellF1 gaps among the top four are inside it. The only
robust public-window signal is the macroF1 gain, which comes from D (D F1 0.77 vs 0.32).
Remaining weakness visible here: 34 predicted vs 17 true possessions (too fragmented).

## Known weaknesses

1. **Over-fragmentation / reversals.** Block-level conditional independence is still too generous;
   the model flips on brief contacts. Evidence is overcounted even at 2.5 Hz.
2. **Weak dead-ball threshold.** Speed is unimodal; the D/alive cutoff (1.2-1.5 m/s) depends on
   binning, and D share moves between 33% and 39%.
3. **Restart timing** is off (D ends at the wrong moment), and the Smart Tagging anchor itself is
   unreliable (35 s phases).
4. **40% of visible frames are gated as ball-in-flight**, a consequence of using the position-based
   ball speed against a player-speed percentile; the gate may be too aggressive and throws away
   touch information. Not examined further in v1.
5. Home bias (65.9% of alive frames).
6. No minimum-duration constraint: geometric durations cannot represent "0.8 s possessions are
   rare but 2-3 s ones are common".

## Most promising next steps

1. **Duration modelling:** replace the 3-state geometric HMM with an explicit-duration (semi-Markov)
   or multi-substate-per-team HMM, and/or temper the emission log-likelihood by an
   autocorrelation-derived factor, to directly attack fragmentation and reversals.
2. **Better control evidence:** touch detection (ball direction change co-located with a nearby
   player), ball possession by *player* continuity rather than team distance gap, and a re-examined
   flight gate.
3. **Restart structure:** model the dead-ball -> alive exit explicitly (ball speed jump + player
   speed rise), with Smart Tagging as soft evidence on *time since tag start* rather than a
   lead-in indicator.

## Files

`step0.png`, `em.png`, `results.json`, `comparison.md`, `model.json`, `eval.log`, `eval_out/`,
`run.log`, `report.log` (all gitignored under `analysis/`).
