# possession model v2: tempering (v2a) and gate + touches (v2b)

Rules, criteria and stopping rule were fixed in `PREREGISTRATION.md` before any variant was run
(append-only notes dated 2026-11-01). Code: `possession/v2/`. Outputs: `submissions/hmm_v2a.csv`,
`hmm_v2b.csv`, `hmm_v2b_p95.csv`. Nothing is committed.

## TL;DR

* **Neither variant helped.** By the registered criteria v2a is **MIXED** and v2b is **NOT HELPING**.
  v1 (`submissions/hmm_v1.csv`) remains the best model of this work.
* **The over-confident-evidence hypothesis is not confirmed.** Tempering the team evidence by the
  registered factor (1/12) did not clean up fragmentation; it removed hand-overs altogether (one
  direct H<->A change in the whole match) and inflated the dead-ball state.
* **The v1 flight gate stands; the touch signal is not recoverable from this tracking.** Ball
  position noise is tiny (the 40% of visible frames above 6.44 m/s are real fast ball), the speed
  histogram has no valley to justify another gate, and ball velocity change is *not* larger when a
  player is close than when nobody is, so velocity-change touch detection finds essentially nothing
  (15 touches at the registered threshold).
* **The home lean is real data, not a bug** (mirror test: exact).
* A duration-chain (semi-Markov) model was also tried before this and failed on held-out likelihood.
* All four submissions are byte-identical across two runs and pass `validate_submission.py`.
  Public window was run once, at the end, and changed nothing.

## 1. Negative result: explicit durations (before v2; `negative_results/`)

*What:* each class (H, A, D) replaced by a left-to-right chain of m substates sharing the class
emission (Erlang-like durations with a minimum of m blocks), all parameters by EM, m = 1 is the
plain HMM. *Why:* the geometric durations of v1 make a one-block (0.4 s) possession cheap.

*Label-free metric:* 2-fold held-out log-likelihood over the two halves (fit on one half, score the
other), per block, higher is better. Rule fixed beforehand: take the best m; if m = 1 wins, the
duration structure is not supported.

| m | held-out logL/step |
|---|---:|
| **1** | **-5.27963** |
| 2 | -5.28897 |
| 3 | -5.30207 |
| 4 | -5.31615 |

*Sanity check:* m = 1 reproduces v1: final training logL/step -5.24363 vs -5.24361, max |dA| 0.0015;
10 of 199,319 frames decode differently (a small difference in how the transition prior is applied).
So the code is correct and the negative result is real.

*Why I think it fails (hypothesis, not tested here):* the likelihood gets worse as the minimum
duration grows because the data contain genuinely short, well-supported flips under these
emissions. The model believes its own evidence; forcing durations fights it. That points at the
evidence, not the duration shape, which is what v2a tested.

## 2. Mirror test (`mirror.json`)

v1 features + EM + Viterbi re-run with home and away swapped. Barcelona's share of alive blocks:
**65.90% in both runs (difference 0.0 points); 0.0% of blocks decode differently** after
relabelling. The learned transition matrix is the exact mirror. The model is exactly equivariant,
so the home lean (65.9% vs 57% for the baseline) is not an artefact of the initial tilt, sign
anchoring, tie-breaking or the transition prior. It comes from the data. (Whether it is football or
a tracking effect, e.g. which team's players are better tracked near the ball, was not tested.)
Criterion (d) satisfied.

## 3. v2a: tau and the tempering factor (`acf.png`, `v2a.json`)

Rule (registered): tau = integrated autocorrelation time of the state-conditional residual of each
team feature at block level (v1 decoded states, H/A blocks only), weight = 1/clip(tau, 1, 12).

| feature | residual tau (blocks) | raw tau (blocks) | weight |
|---|---:|---:|---:|
| gap | 15.6 | 32.3 | 1/12 (clipped) |
| dwell | 12.1 | 27.6 | 1/12 (clipped) |

Both residual taus lie at or above the registered cap (12 blocks = 4.8 s): after removing the
state mean the evidence is still strongly correlated over many seconds. Tempered EM converged
(89 iterations, tempered objective monotone). Learned transitions and durations:

| | v1 | v2a |
|---|---:|---:|
| expected H sojourn (s) | 6.2 | 13.1 |
| expected A sojourn (s) | 4.4 | 18.4 |
| expected D sojourn (s) | 15.9 | 13.9 |
| P(H -> A) per block | 0.049 | 0.002 |
| P(A -> H) per block | 0.077 | 0.001 |
| P(H -> D), P(D -> H) | 0.016, 0.014 | 0.028, 0.024 |

v2a almost never moves directly between teams; hand-overs go through D, and D grows to 48.5% of
graded frames.

*Why it overshoots (hypothesis, not tested):* a residual that stays correlated for >5 s is not a
list of repeated copies of the same observation; the gap simply varies slowly (where the ball is
relative to the nearest players) even inside a fixed possession. Dividing by tau treats slow
covariation as duplication and deletes the evidence rather than correcting its multiplicity. A
weaker cap would give an intermediate result, but picking it now would be tuning on outcomes and
needs its own registration.

## 4. v2b: flight gate and touches (`gate_touch.json`, `gate_touch.png`)

*Gate.* Position noise is small: sigma_pos <= 0.071 m (upper bound; real accelerations included),
implying about 0.25 m/s of noise in the +-0.2 s speed estimate. So the fast ball is real:

| ball speed threshold (m/s) | share of visible graded frames above |
|---|---:|
| 6.44 (v1 gate) | 40.3% |
| 10 | 22.8% |
| 15 | 8.1% |
| 25 | 0.8% |
| 35 | 0.29% |

The smoothed log-speed histogram has **no valley between 3 and 15 m/s**, so the registered fallback
applies: the gate stays at the 99th percentile of player speed (6.44 m/s). The only change is that
speeds above 35 m/s (0.29% of visible frames, 269 graded frames) are treated as tracking glitches
and excluded. The suspicion that the gate was too low for a rolling ball is not supported by the
data: a ball above player running speed is not being carried.

*Touches.* A touch = velocity change |v(t+0.2 s) - v(t-0.2 s)| above a threshold with a player
within the control radius (1.91 m), thinned to one event per touch. Threshold = a percentile of
|dv| on graded frames where nobody is within 5 m (a free ball cannot be touched).

| reference percentile | threshold (m/s) | touches in the match | per min | home share |
|---|---:|---:|---:|---:|
| 95 | 4.94 | 178 | 1.68 | 64% |
| **99 (registered)** | 14.0 | **15** | 0.14 | 67% |
| 99.9 | 30.8 | 6 | 0.06 | 83% |

The count is extremely sensitive to the threshold (178 -> 15 -> 6), and the reason is visible in the
distributions: the percentiles of |dv| with a player within the control radius (50/90/95/99% =
1.1/3.4/4.1/5.6 m/s) are **not larger** than for a free ball (1.0/3.6/4.9/14.0 m/s). Velocity change
over a 0.4 s window therefore does not separate touches from the tracker's own behaviour (smoothing
of kicks, dropouts, jumps). The detected "touches" are mostly noise; the learned touch emission is
almost flat across states (P(touch) 0.1-0.2% in every state), i.e. an inert feature. Touch tau
(information only) = 1.0 because events are too sparse to correlate.

## 5. Label-free table against the criteria (full match, `compare.md`)

| metric | smooth50 | **v1** | v2a | v2b | v2b (p95, diagnostic) |
|---|---:|---:|---:|---:|---:|
| possessions | 594 | 563 | 213 | 563 | 565 |
| possessions / min | 5.61 | 5.32 | 2.01 | 5.32 | 5.33 |
| median possession (s) | 4.60 | 4.40 | 11.60 | 4.40 | 4.40 |
| % possessions < 2 s | 31.3 | 26.6 | 9.4 | 26.6 | 26.9 |
| reversal rate (3 s), % | 29.5 | 36.8 | 0.0* | 36.8 | 36.8 |
| D share, % | 32.3 | 38.7 | 48.5 | 38.7 | 38.7 |
| median D stretch (s) | 7.6 | 8.8 | 5.6 | 8.8 | 8.8 |
| ball-outside labelled D, % | 0.0 | 53.9 | 64.1 | 53.9 | 53.9 |
| restart: any D within 2 s, % | 69.0 | 84.5 | 87.9 | 84.5 | 84.5 |
| restart: D ends within 2 s, % | 15.5 | 8.6 | 3.4 | 8.6 | 8.6 |
| hand-over plausible, % | 32.9 | 36.2 | 0.0* | 36.2 | 35.7 |
| direct H<->A hand-overs | 461 | 419 | **1** | 419 | 421 |
| home share of alive, % | 57.0 | 65.9 | 75.3 | 65.9 | 65.9 |

\* based on a single hand-over; meaningless.

Pre-registered criteria vs v1:

| variant | (a) fewer <2 s | (b) lower reversals | (c) dead-ball not worse | (d) home lean | (e) >= 3 poss/min | verdict |
|---|---|---|---|---|---|---|
| v2a | pass (9.4 < 26.6) | pass (0.0 < 36.8) | **FAIL** (D share +9.8 pts) | explained (data) | **FAIL** (2.0) | **MIXED** |
| v2b | fail | fail | pass | explained (data) | pass | **NOT HELPING** |
| v2b p95 | fail | fail | pass | explained (data) | pass | **NOT HELPING** |

v2a's (a) and (b) pass only because the model stopped making hand-overs; the non-degeneracy guard
(e) and (c) were registered for exactly this and caught it. v2b is identical to v1 to within a
few blocks (563 possessions, same D behaviour), as expected from an inert touch feature and a
0.29% glitch exclusion.

## 6. Public window (bug check only, run once, `eval.log`, 1000 bootstrap draws)

| submission | macroF1 | spellF1 | spellF1 5-95% | poss |
|---|---:|---:|---|---:|
| baseline_smooth50 | 0.6207 | 0.3256 | 0.214 .. 0.447 | 26 |
| hmm_v1 | 0.7495 | 0.2824 | 0.188 .. 0.377 | 34 |
| hmm_v2b | 0.7495 | 0.2824 | 0.188 .. 0.377 | 34 |
| hmm_v2b_p95 | 0.7477 | 0.2824 | 0.188 .. 0.377 | 34 |
| hmm_v2a | 0.6863 | 0.1467 | 0.027 .. 0.293 | 13 |

Nothing was changed because of it and no variant was selected with it. It is consistent with the
label-free verdicts (v2a collapses; v2b = v1), but 17 possessions cannot rank anything: one
possession moves spellF1 by ~6 points and the widest interval is ~0.33. Note v2a gets the number of
possessions closer to the truth (13 vs 17) while scoring worse, a reminder that possession count
alone is not the target.

## 7. What did not work

1. **Minimum-duration chains** (held-out likelihood prefers m = 1).
2. **Tempering team evidence by 1/tau** (collapses hand-overs; D inflates). The over-confidence
   diagnosis is not confirmed by it.
3. **A higher flight gate** (no support: no valley, noise is small).
4. **Velocity-change touch detection** (not separable from free-ball behaviour; 15 events).

## 8. Next steps

1. **Control from relative motion.** A carried ball moves with its carrier. Use the correlation
   between ball velocity and the nearest player's velocity (and its persistence) as the control
   signal. It does not rely on a kick leaving a sharp velocity signature, which this tracking
   smooths away.
2. **A milder, separately registered way of discounting evidence.** For example a cap equal to the
   timescale at which residual autocorrelation first drops below 0.5, instead of the full
   integrated time, registered with its own criteria. Only worth doing together with (1).
3. **Model hand-over timing explicitly**: the diagnosis put the biggest loss there. Use v1's
   smoothed state posterior to place boundaries at the most probable block rather than the Viterbi
   path's first change, and check the label-free hand-over plausibility.

## 9. Reproducibility and housekeeping

md5, two independent runs each: hmm_v1 `83b587d7b36a665a69f2eaf88566e60b`, hmm_v2a
`b1551bda15fa9c0ea02574692758cf0a`, hmm_v2b `b8d1dc4d7b81c2241ea26ca13ba927a8`, hmm_v2b_p95
`4a2d28bbc43b35c9c128717a53b5a938` (identical both times). All validate. Regenerate with
`python -m possession.run`, `python -m possession.v2.run_v2a`, `python -m possession.v2.run_v2b
[95 hmm_v2b_p95]`, `python -m possession.v2.compare hmm_v1 hmm_v2a hmm_v2b hmm_v2b_p95`.
`git status`: only new files (`possession/v2/`, three new CSVs in `submissions/`); `.gitignore`
shows modified from before the session and was not touched. The earlier duration code was moved to
`analysis/hmm_v2/negative_results/` (not part of the pipeline).
