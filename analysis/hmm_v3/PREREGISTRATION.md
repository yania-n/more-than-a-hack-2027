# Pre-registration: v3a (relative-motion control signal)

Written 2026-11-01 (session date), **before any v3 code has run**. New file; v2's preregistration is
untouched. After this point this file is append-only (dated notes with a reason).

Knowledge at writing: v1 exists and is the base (md5 83b587d7...). v2a was MIXED and v2b NOT HELPING;
v2b showed that velocity change (a kick signature) is not separable from free-ball behaviour in this
tracking. No v3 number exists yet. Tempering is not used (w = 1 everywhere). The public window is run
once at the very end as a bug check; it plays no part in any criterion.

## 1. Hypothesis

A carried ball moves with its carrier. The agreement between the ball's velocity and the nearest
player's velocity, sustained over about a second and a half, separates "controlled" from
"contested or loose" better than proximity alone, and does not need a sharp kick signature.

## 2. The feature (computed per 0.4 s block, v1 blocks and halves)

**Velocities.** Central difference over +-5 frames (0.2 s each side, as for the ball speed in v1):
`v(t) = (p(t+5) - p(t-5)) / 0.4 s` for the ball and for every player slot; NaN if either end is
missing. Nearest player `j*(t)` = nearest observed slot to the ball (either team); `d_min(t)` its
distance; its team is the "nearest team".

**Per-frame agreement statistics** (only where both speeds exceed their noise floors):
* `C(t)` = cosine of the angle between `v_ball(t)` and `v_player(t, j*)`.
* `L(t)` = `|ln(|v_ball| / |v_player|)|` (0 = equal speed).
* Noise floors: `f = 4 * sigma_pos * sqrt(2) / 0.4 s`, where `sigma_pos` is the robust
  (MAD-based) position-noise upper bound from the second difference of the track
  (`x(t+5) - 2x(t) + x(t-5)`, sigma = MAD/0.6745/sqrt(6)); computed separately for the ball and for
  the pooled player tracks over graded frames. A velocity below 4x its noise speed has no usable
  direction.

**Window.** 40 frames (1.6 s) centred on the block: frames `[s - 15, s + 25)` for a block starting at
`s`. Physics: players touch a dribbled ball roughly every 0.5-1 s, so 1.6 s spans at least two touches
and excludes a single touch; it is within the range of the unlabeled frame-level autocorrelation time
of `C(t)` near the ball, which is reported for information.

**Window decision, per block.**
* *Missing* (category -1) if fewer than 12 frames in the window have a visible ball with a finite
  ball velocity (12 frames = 0.48 s of evidence).
* *Candidate* if, in addition, **every** such frame has `d_min <= R` (R = the v1 control radius,
  1.91 m), the nearest *team* is the same on all of them, and at least 12 of them have valid
  (above-floor) velocities.
* *Carried* if a candidate has window means `mean(C) > theta_C` and `mean(L) < theta_L`, over its valid
  frames. Carrying team = the nearest team. Otherwise *none*.
* Evidence category: {0 away carried, 1 none, 2 home carried}; `FeatureSpec(kind="team")`, mirror-tied
  like gap and dwell, **untempered (w = 1)**. Same blocks, priors, tying, initial tilt and EM as v1.

**Deviation from the brief, stated openly.** The brief says "carried = both above thresholds for the
whole window". Applied literally to per-frame statistics this has almost no power (noisy velocities,
12+ frames all passing) and (f) would fail by construction. The registered version keeps the
sustained requirement in two parts: (i) near-radius and the same team on *every* observed frame of the
window (strict, "whole window"), and (ii) agreement judged on the *window mean* of C and L against a
null of the same window statistic. The false-positive rate is then fixed at the window level.

## 3. Thresholds from a null, not from scores

Null of the window statistics, built on exactly the candidate windows of section 2, with only the
player velocity replaced:
* **Time-shift null:** pair `v_ball(t)` with `v_player(t + Delta, j*(t))` for `Delta` in
  {-250, -175, +175, +250} frames (+-7 s and +-10 s: several seconds, longer than the decorrelation
  of a player's heading), same window means, pooled over the four shifts.
* **Same-team random-player null:** pair `v_ball(t)` with the velocity at the same `t` of a random
  other observed player of the nearest team (seeded generator, `default_rng(0)`). This is the harder
  null: it keeps team-level motion in common with the ball.
* `theta_C` = **99th percentile** of the null window-mean `C`, `theta_L` = **1st percentile** of the
  null window-mean `L`; each taken as the more stringent of the two nulls (larger `theta_C`, smaller
  `theta_L`). 99 is fixed here. The joint false-positive rate of the decision rule under each null is
  reported, and the sensitivity of the carried share to the percentile (95 / 99 / 99.9) is reported
  for information only; no choice among them is made by scoring.

## 4. Criteria vs v1 (full match, label-free; same code as v2)

* (a) % of possessions < 2 s lower than v1 (26.64%).
* (b) reversal rate (within 3 s) lower than v1 (36.75%).
* (c) dead-ball not worse: ball-outside labelled D >= 48.9% (v1 - 5 pts), restart "any D within
  2 s" >= 79.5% (v1 - 5 pts), D share within +-5 pts of v1 (33.7%-43.7%).
* (d) home lean: reported, **not gating**; explained by the mirror test (v2, exact) and the
  independent Smart Tagging cross-check (section 5).
* (e) possessions per minute >= 3.0.
* (f) **informativeness:** the share of *observed* blocks with the carried category (either team)
  must be >= 2% (the v2b touch feature sat at ~0.2%), **and** the learned likelihood ratio
  `P(home carried | H) / P(home carried | A)` >= 3 (the conventional "substantial evidence" bar).
  The learned P(feature | state) for H, A, D and the data share are reported either way.
* (g) non-collapse: direct H<->A hand-overs >= 50% of v1's count (>= 210 of 419).
* (h) hand-over plausibility not below v1's (36.22%).

**Helped** = (a), (b), (c), (e), (f), (g), (h) all pass. Anything else is *mixed* or *not helping*
and the next step builds on v1. (Verdict wording follows `compare.md` in v2: NOT HELPING if both
(a) and (b) fail; HELPED if all pass; otherwise MIXED.)

## 5. Independent home-lean check (diagnostic, changes nothing in the model)

Share of graded time covered by Smart Tagging phases tagged with a Barcelona vs an Athletic Team
tag, `N/A` excluded, the mirrored `DEFENDING ...` / `DEFENSIVE TRANSITION` instances excluded (they
duplicate the attacking instance of the other team). Phases overlap, so the covered time of each
team is the union of its intervals within graded frames; overlap between the two teams is reported.
Compared with v1's 65.9% and smooth50's 57.0% of alive frames. Reported as an independent automatic
data point only.

## 6. Stopping rule

If v3a does not help, report why and stop. No features are added to rescue it, no thresholds or
percentiles are revisited. Only registered variants get a submission file (`submissions/hmm_v3a.csv`).

## 7. Dataset feasibility note (read-only)

Section 4 of the report records what open tracking+event datasets exist, their licences and the
domain-shift risk, using only public documentation; nothing is downloaded or placed in the repo.

## 8. Reporting and reproducibility

`analysis/hmm_v3/REPORT.md`: TL;DR vs criteria, null distribution and thresholds, learned emissions,
label-free table, home-lean cross-check, feasibility note, public window once at the end
(`--bootstrap 1000`, output to `analysis/hmm_v3/eval_out`, noise caveat), what did not work, next
steps; md5 of the submission from two runs; `git status` confirming only new files.
