# Pre-registration: v2a (tempering) and v2b (gate + touches)

Written 2026-11-01, **before any v2 variant has been built or run**. After this point the file is
append-only: dated notes with a reason, never edits of the rules below.

State of knowledge at writing: v1 exists (`submissions/hmm_v1.csv`, md5 83b587d7...). Its label-free
numbers are known (563 possessions, 26.6% < 2 s, reversal rate 36.8%, D share 38.7%, ball-outside
labelled D 53.9%, restart "any D within 2 s" 84.5%, home share 65.9%). The duration-chain experiment
failed on held-out likelihood (m=1 best) and is recorded in REPORT.md. No v2 number exists yet.
The public window is used once, at the very end, as a bug check only.

## 0. Hypothesis under test

The 3-state HMM fragments possessions because emissions are over-confident: consecutive 0.4 s
blocks of team evidence are strongly correlated *given the state*, but the model multiplies them as
if independent. If so, discounting the team evidence by its effective sample size should cut short
possessions and reversals. If it does not, the hypothesis is not supported.

## 1. Tempering rule (v2a)

Applies to the **team-related emission log-likelihoods only**: the `gap` and `dwell` features (and,
in v2b, the `touch` feature). Dead-ball features (ball speed, heading, outside, set-piece,
player speed) and the transition matrix are untouched. Tempered emission:
`log b_s(t) = sum_f w_f * log p_f(x_ft | s)`, with `w_f = 1` for untempered features and
`w_f = 1/tau_f` for team features.

**tau_f** = integrated autocorrelation time, **in blocks**, of the *state-conditional residual* of
feature f at block level:

1. Numeric score per team feature: `gap` -> block median of g (m); `dwell` -> block signed dwell
   (frames) clipped at +-its 99th percentile; `touch` -> block net signed touch count.
2. State: the v1 Viterbi path (unlabeled, available). Use only blocks decoded H or A.
   Residual `e_t = x_t - mean(x | decoded state)` (mean over blocks of that state, pooled halves).
   Reason: raw autocorrelation of the evidence contains the *state's own persistence*, which is
   signal, not redundancy; the quantity that causes over-counting is the correlation that remains
   after conditioning on the state.
3. `rho_k = sum e_t e_{t+k} / sum e_t^2`, over pairs (t, t+k) in the same half where both blocks
   are observed and both decoded H/A (stretches without the ball simply contribute no pairs).
4. `K` = first lag with `rho_k <= 0` (cap 50). `tau = 1 + 2 * sum_{k=1}^{K-1} rho_k`.
5. **Clip** `tau` to `[1, 12]` blocks. Lower bound 1: evidence is never up-weighted. Upper bound 12
   blocks (4.8 s) is about the timescale at which the *state itself* decorrelates (the learned v1
   mean sojourn is 4-6 s); correlation of residuals beyond that is indistinguishable from slow state
   signal, and discounting by more would delete the evidence rather than correct its multiplicity.
6. The raw-evidence tau (no state removal) is computed and reported for information only.

EM: E-step uses the tempered emissions; M-step is the usual weighted count update of the
(untempered) per-frame categorical emissions. This is a "power likelihood" pseudo-EM, not exact ML;
convergence is judged by parameter change, and monotonicity of the tempered objective is reported
but not required. Same initialisation, priors, tying and block size as v1. tau is computed once from
v1 and **not** re-estimated or tuned.

## 2. "Good direction" criteria (label-free table, full match, vs v1)

* (a) % of possessions < 2 s is lower than v1 (26.64%).
* (b) A->B->A reversal rate (within 3 s) is lower than v1 (36.75%).
* (c) Dead-ball behaviour not worse than v1: ball-outside labelled D >= v1 - 5 points (>= 48.9%),
  restart "any D within 2 s" >= v1 - 5 points (>= 79.5%), and D share within +-5 points of v1.
* (d) Home lean (65.9% of alive frames): explained by the mirror test (section 4). A verdict, not a
  number.
* (e) Non-degeneracy guard: possessions per minute >= 3.0. A model that merges everything into a few
  huge possessions would pass (a) and (b) trivially; 3.0/min (mean possession of at most ~12 s given
  the ball is alive about 60% of the time) rules that out. Football reasoning, not a tuned number.

**Helped** = passes (a), (b), (c) and (e). The public window plays no part in any criterion.

## 3. Stopping / building rule

* A variant failing both (a) and (b) is reported as **not helping**.
* A variant passing exactly one of (a)/(b), or failing (c) or (e), is reported as **mixed** and, to be
  conservative, is treated like not helping for the purpose of what the next variant builds on.
* The next variant builds on the last variant that **helped**; if none, on v1.
* v2b therefore builds on v2a only if v2a helped; otherwise on v1 (v2b is then evaluated against v1).
* No variant is selected, rejected or retuned using the public window or any ground truth.

## 4. Mirror test (runs first, a diagnostic not a variant)

Re-run the v1 features, EM and decoding with the team labels of the tracks swapped (home <-> away).
Because the model ties H and A symmetrically, the *data's* team (Barcelona) should keep roughly the
same alive-share regardless of which label it carries. If the share follows the label ("H" stays
~66%) there is an asymmetry or bug in the model (initial tilt, anchoring, transitions, tie-breaking)
and work stops until it is reported. Tolerance for "follows the data": the Barcelona share differs
between the two runs by less than 2 points.

## 5. v2b rules (fixed now, thresholds by unlabeled statistics only)

**Flight gate.** Currently: ball speed (+-0.2 s differencing) > 6.44 m/s (p99 of player speed) =>
in flight, control features missing.
* Report the ball-speed noise floor: std of the speed estimate on frames where the ball is
  stationary by a 2-point test is not available without labels, so use the lower edge instead: the
  5th percentile of speed among visible-ball graded frames, and the speed implied by position noise
  (second-difference residual of the ball track, sigma_pos * sqrt(2) / (2w/25)).
* Report the share of visible frames above 6.44, 10, 15, 25 and 35 m/s. Speeds above 35 m/s (about
  the fastest professional strike) are treated as tracking glitches: ball set missing for team
  features.
* Proposed gate: if the log ball-speed histogram (smoothed) has a clear valley between ~3 and
  ~15 m/s, the gate is at that antimode (carried vs struck/rolling ball); otherwise the gate stays
  at the 99th percentile of player speed. Decided by the histogram, not by scores.

**Touch evidence.** A touch at frame t = the ball's velocity vector changes by more than a threshold
between the windows before and after t (`|v(t+w) - v(t-w)|`, w = 5 frames), **and** the nearest
player is within the control radius (1.91 m) of the ball at t. The velocity-change threshold is the
99th percentile of `|dv|` over graded frames where *nobody* is within 5 m of the ball (a free ball
cannot be touched, so this fixes the false-positive rate near 1% by construction; physical floor:
a free rolling ball loses at most a couple of m/s in 0.4 s). Sensitivity: report touch counts at the
95th, 99th and 99.9th percentile references. Touch evidence per block: net signed count of touches
(+ home nearest, - away nearest), categories {away, none, home}, mirror-tied like the other team
features, tempered with its own tau by the same rule. No scoring is used to pick the percentile; 99
is fixed here.

## 6. Reporting

`analysis/hmm_v2/REPORT.md`: TL;DR, duration negative result (what, metric, numbers, sanity, why),
mirror test, tau and tempering factors (with ACF plot), gate and touch analysis, label-free table
against (a)-(e), what didn't work, next steps. Determinism: md5 of every submission from two runs.
Public window: once, at the end, `--bootstrap 1000`, output to `analysis/hmm_v2/eval_out`.

---
## Append-only notes

### 2026-11-01 — mirror test and v2a outcome (no rule above was edited)

* Mirror test (section 4): Barcelona's alive share was 65.90% in both the original and the swapped
  run (difference 0.0 points; 0.0% of blocks decode differently after relabelling). The model is
  exactly equivariant, so the home lean comes from the data, not from the tilt, anchoring, tie-breaking
  or transition prior. Criterion (d) is satisfied; work continued.
* v2a (section 1), run exactly as registered: residual tau = 15.6 blocks (gap) and 12.1 (dwell), raw
  tau = 32.3 and 27.6; both residual taus hit the registered clip, so the weight is 1/12 for both.
  Verdict from `possession.v2.compare`: (a) pass, (b) pass, (c) FAIL (D share +9.8 points), (e) FAIL
  (2.0 possessions/min); only 1 direct H<->A hand-over in the whole match, so the 0% reversal rate is
  vacuous. **MIXED => by section 3, v2b builds on v1, not on v2a.**
* Consequence for v2b: section 5 says the touch feature is "tempered with its own tau". Tempering was
  just shown to suppress the team signal, and v2b builds on untempered v1, so the touch feature
  enters **untempered (w = 1)**, like gap and dwell in v1. Its tau is still computed and reported for
  information. Reason: applying a weight to one team feature of an untempered model has no
  registered justification, and the registered rule only licenses tempering inside v2a.
* Attribution runs: besides the registered v2b (new gate + touch), the gate-only and touch-only
  variants are run as **diagnostics** and labelled as such. None of the three is selected using
  the public window; criteria (a)-(e) are applied to each as written.
