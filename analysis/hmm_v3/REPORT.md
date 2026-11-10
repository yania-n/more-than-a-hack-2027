# possession model v3a: relative-motion control signal

Registered in `PREREGISTRATION.md` before any code ran. Code: `possession/v3/`. Output:
`submissions/hmm_v3a.csv`. Nothing is committed.

## TL;DR

* **Verdict against the pre-registered criteria: NOT HELPING.** (a) fail, (b) fail, (c) pass, (e)
  pass, (f) **fail**, (g) pass, (h) pass. Per the stopping rule I stop here and do not rescue it.
* **`hmm_v3a.csv` is byte-identical to `hmm_v1.csv`** (md5 `83b587d7b36a665a69f2eaf88566e60b` for both).
  The new feature fires on 106 of 9,521 observed blocks (1.11%), too few to change a single Viterbi
  decision. So (a) and (b) cannot pass, and the table below is v1 twice.
* **The signal itself is informative, but the registered rule makes it too rare.** Its learned
  likelihood ratio is about 45:1 in the right direction (home carried is 45x more likely under H than
  under A), and real windows agree far more than either null. The bottleneck is the strict
  candidate condition (ball inside the control radius on *every* observed frame of a 1.6 s window),
  which leaves only 12.5% of observed blocks eligible.
* **One deviation from the brief, stated openly in the pre-registration:** the brief says "both above
  thresholds for the whole window". I registered the sustained requirement as (i) near-radius and
  same team on every observed frame of the window, plus (ii) agreement judged on the window mean
  against a null of the same window statistic, because a literal all-frames-pass rule on noisy
  per-frame velocities has almost no power.
* **Home lean cross-check:** Smart Tagging gives Barcelona 59-62% of tagged attacking time, between
  smooth50 (57.0%) and v1 (65.9%).
* md5 identical across two runs; validates; public window run once and changes nothing.

## 1. The feature and its null (`null.png`, `v3a.json`)

Velocities are central differences over +-0.2 s for the ball and every player slot. The nearest
player to the ball is compared with it: cosine C and |ln speed ratio| L per frame, over a 1.6 s
window centred on each 0.4 s block.

| quantity | value |
|---|---:|
| ball position noise (upper bound) | 0.071 m (speed floor 1.00 m/s = 4x noise speed) |
| player position noise (upper bound) | 0.0095 m (speed floor 0.13 m/s) |
| control radius (v1) | 1.91 m |
| window | 40 frames (1.6 s); frame-level autocorrelation of C near the ball falls below 1/e after 11 frames (0.44 s), so a window contains several independent looks |
| blocks / observed (>= 12 visible frames in the window) | 15,886 / 9,521 |
| **candidates** (near on every observed frame, same team, >= 12 valid) | **1,193 (12.5% of observed)** |
| carried: home / away | 60 / 46 |
| carried share of candidates / of observed | 8.9% / **1.11%** |

Thresholds, from the null at the registered 99th percentile (more stringent of the two nulls):
**theta_C = 0.987** (window-mean cosine must exceed it) and **theta_L = 0.116** (window-mean
|ln ratio| must be below it). Null quantiles of the window statistic on the same candidate windows:

| | C 1% / 50% / 95% / 99% | L 1% / 5% / 50% |
|---|---|---|
| time-shifted player (+-7, +-10 s) | -0.99 / -0.04 / 0.93 / 0.987 | 0.116 / 0.185 / 0.686 |
| random teammate, same time | -0.63 / 0.43 / 0.91 / 0.967 | 0.262 / 0.334 / 0.690 |
| **real candidate windows** | -0.24 / **0.96** / 0.998 / 0.999 | 0.028 / 0.065 / **0.255** |

Real windows agree far more than either null (median cosine 0.96 vs -0.04 and 0.43; median speed
mismatch 0.26 vs 0.69). Joint false-positive rate of the rule: 0.02% (time-shift null), 0.0%
(teammate null). So the hypothesis holds *at the feature level*: a ball that stays near a player for
1.6 s moves with them.

Why the shipped feature is still rare: the thresholds are the 99th percentile of a null that
is already strong (its own 95th percentile cosine is 0.93), because candidate windows are selected
for sustained proximity, which by itself makes the ball and player co-move. Most of the information
is in the candidate condition; the extra velocity agreement discriminates little beyond it, and the
conservative p99 cut then keeps only 8.9% of candidates. (Hypothesis, not tested further.)

Sensitivity of the carried share to the null percentile, **information only, no choice made**:

| null percentile | theta_C | theta_L | carried share of observed |
|---|---:|---:|---:|
| 95 | 0.930 | 0.185 | 3.6% |
| **99 (registered)** | 0.987 | 0.116 | **1.11%** |
| 99.9 | 0.998 | 0.069 | 0.26% |

(At p95 the share would have cleared the 2% bar of criterion (f). It was not registered, I did not
run a model with it, and I am not recommending that it be chosen now, since that would be selecting
by outcome.)

## 2. Learned emission (`v3a.json`)

Rows are states, columns {away carried, none, home carried}:

| state | away carried | none | home carried |
|---|---:|---:|---:|
| H | 0.025% | 98.84% | 1.13% |
| A | 1.13% | 98.84% | 0.025% |
| D | 0.63% | 98.74% | 0.63% |

* Likelihood ratio P(home carried | H) / P(home carried | A) = **44.7** (>= 3 passes).
* It is *not flat*, unlike the touch feature of v2b, but the carried categories hold only about 1.1%
  of the probability mass, so the per-block evidence almost never fires. Criterion (f) needs both
  the ratio and a data share >= 2%; the share (1.11%) fails.
* The model otherwise converged exactly as v1 (23 iterations, same transition matrix to 3 decimals,
  expected stays H 6.2 s, A 4.4 s, D 15.9 s).

## 3. Label-free table (`compare.md`, full match; same code as v2)

| metric | smooth50 | v1 | v3a |
|---|---:|---:|---:|
| possessions | 594 | 563 | 563 |
| possessions / min | 5.61 | 5.32 | 5.32 |
| median possession (s) | 4.60 | 4.40 | 4.40 |
| % possessions < 2 s | 31.3 | 26.6 | 26.6 |
| reversal rate (3 s), % | 29.5 | 36.8 | 36.8 |
| D share, % | 32.3 | 38.7 | 38.7 |
| median D stretch (s) | 7.6 | 8.8 | 8.8 |
| ball-outside labelled D, % | 0.0 | 53.9 | 53.9 |
| restart: any D within 2 s, % | 69.0 | 84.5 | 84.5 |
| hand-over plausible, % | 32.9 | 36.2 | 36.2 |
| direct H<->A hand-overs | 461 | 419 | 419 |
| home share of alive, % | 57.0 | 65.9 | 65.9 |

| criterion | result |
|---|---|
| (a) fewer < 2 s than v1 | fail (identical) |
| (b) lower reversal rate | fail (identical) |
| (c) dead-ball not worse | pass |
| (e) >= 3.0 possessions/min | pass |
| (f) informative: share >= 2% **and** LR >= 3 | **fail** (share 1.11%, LR 44.7) |
| (g) hand-overs >= 50% of v1 | pass (419 = 100%) |
| (h) hand-over plausibility >= v1 | pass (equal) |
| **verdict** | **NOT HELPING** |

(c), (g) and (h) pass trivially because the output equals v1.

## 4. Independent check of the home lean (`tagging_share.json`)

Smart Tagging phases tagged for a team, `N/A` and the mirrored DEFENDING / DEFENSIVE instances
excluded (462 attacking instances used, 34 `N/A`, 142 defending excluded), union of intervals per
team inside graded frames:

| | frames | share |
|---|---:|---:|
| tagged Barcelona | 82,853 | |
| tagged Athletic | 57,105 | |
| tagged for both (overlap) | 16,399 | |
| **Barcelona share of attributed time** | | **59.2%** (62.0% counting only time tagged for one team) |
| time covered by any attacking phase | 123,559 | 77.8% of graded |

v1: 65.9%; smooth50: 57.0%. An independent automatic source supports a real lean of roughly 59-62%,
so the lean is not an artefact, and v1's figure is a few points above that, still plausible given
that phases are not possessions and tagging is itself inferred. Combined with the v2 mirror test
(exact equivariance), I see no evidence that the tracking's team assignment near the ball is
biased. Nothing was changed because of this.

## 5. Feasibility note: supervised data from other games (read-only, nothing downloaded)

RULES.md allows hand-labelled and event data from other games. From public documentation only (I
could not verify every licence text, flagged below):

* **Metrica Sports sample data** (GitHub `metrica-sports/sample-data`): 3 sample games with tracking
  and event data; games 1 and 2 are anonymised, game 3 is in the EPTS/FIFA format with JSON events
  (readable with kloppy). I found **no explicit licence**; a fork's README only asks for responsible
  use and acknowledgement of the source. Verify the official repo's LICENSE before any use.
* **PFF FC 2022 World Cup dataset:** free tracking + event data for the tournament, published with a
  blog post; terms of use are on PFF's page and need checking for competition use.
* **SkillCorner open data:** 9 matches of broadcast-derived tracking (with dynamic events); a
  third-party index lists MIT, **not confirmed** against the repo.
* **DFL / Sportec:** a few open Bundesliga matches (reportedly 2 first-division, 5 second-division)
  reachable via the databallpy package; I found no licence text.
* **Main risks:** (i) domain shift: these sources are cleaner or differently produced than this
  match's automatic, gap-ridden tracking (41% ball missing); (ii) their event or possession labels
  follow other definitions than this task's corrected-tracking ground truth; (iii) licences may
  restrict competition use; the organisers must also be able to access whatever is used and the
  technical document must describe it. A supervised model would also need features that survive the
  domain shift. Nothing is built from any of this yet.

## 6. Public window (once, at the end, `eval.log`, 1000 bootstrap draws; bug check only)

| submission | macroF1 | spellF1 | spellF1 5-95% |
|---|---:|---:|---|
| baseline_smooth50 | 0.6207 | 0.3256 | 0.214 .. 0.447 |
| hmm_v1 | 0.7495 | 0.2824 | 0.188 .. 0.377 |
| **hmm_v3a** | 0.7495 | 0.2824 | 0.188 .. 0.377 |

Identical to v1, as it must be for an identical file (34 predicted vs 17 true possessions). No
information about v3a beyond "the pipeline still runs and aligns". 17 possessions cannot rank
anything; one possession moves spellF1 by ~6 points and the widest interval is ~0.33.

## 7. What did not work

* The registered relative-motion rule produced a team-informative but far too rare feature; the
  model output did not change at all. The strict "near on every frame of the window" condition
  leaves 12.5% of blocks eligible, and the p99 null threshold then keeps 8.9% of those.
* The null is strong because candidate windows already co-move with the nearest player by selection,
  so velocity agreement added little over proximity at p99.

## 8. Next steps

1. **Use the proximity-and-co-movement information with a registered design that has power,** for
   example the same window statistics without the all-frames-near condition (allowing the ball to be
   briefly farther) and a null built from the full set of windows rather than from candidates only.
   This is a new design and needs its own registration; it must not be presented as a rescue of
   v3a, and its percentile must not be picked from the table in section 1.
2. **Address the real bottleneck, 41% missing ball.** Most of the lost hand-overs happen where the ball
   is unseen. Carrying evidence is only available when it is seen; modelling the ball position through
   gaps from the surrounding players' motion would extend every control feature.
3. **Decide about supervised data from other games** after verifying licences (section 5), with a
   domain-shift plan, since the unsupervised features in v1-v3 have now been shown to plateau at the
   v1 label-free profile.

## 9. Reproducibility and housekeeping

* md5 of `submissions/hmm_v3a.csv`, two independent runs: `83b587d7b36a665a69f2eaf88566e60b` both
  times (equal to v1's). `validate_submission.py`: OK, 199,319 rows.
* Regenerate: `python -m possession.v3.run_v3a`; criteria: `python -m possession.v3.compare`;
  cross-check: `python -m possession.v3.tagging_share`.
* `git status`: only new files (`possession/v2/`, `possession/v3/`, and CSVs in `submissions/`);
  `.gitignore` shows as modified from before the session and was not touched. Nothing committed.
