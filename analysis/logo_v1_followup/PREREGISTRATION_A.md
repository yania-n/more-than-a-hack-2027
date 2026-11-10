# Pre-registration, Part A: derive N_PSPEED on external data (label-free)

Written 2026-11-10 **before any LOGO fit with N_PSPEED != 12 and before any held-out likelihood was computed.** Append-only after.
Builds on `analysis/logo_v1/{PREREGISTRATION,PROVENANCE,REPORT}.md`. Source of all data used: Metrica Sports public sample data
(Sample Games 1-3), https://github.com/metrica-sports/sample-data, acknowledged as the repository asks; kept gitignored.

Rules: nothing is read from the provided match in Part A, and no label of any kind (event-derived or otherwise) is read by any
step below. The 5-minute public window is not used.

## 0. What I have seen
The N_PSPEED=12 results of `analysis/logo_v1` (spellF1 etc.) and the 12-bin LOGO fits. I have **not** fitted, decoded or scored
any other bin count, and have not computed any held-out likelihood.

## 1. Fixed design
* Candidates: **N_PSPEED in {6, 8, 12, 16, 24}.** Nothing else changes (every other constant, prior, bin count, EM setting and the
  set-piece-missing convention are those of `v1_logo`).
* Procedure per candidate and fold (held-out G in {game1, game2, game3}): fit on the other two games' tracking, **as-is ball**, intervals
  = tracking periods, exactly `logo_v1.fit_frozen`. Held-out sequences are built from G's as-is tracking over **G's tracking
  periods** (not label blocks) with the frozen radius, carry speed and bin edges of that fold.
* Likelihood: forward algorithm (log-space recursion, uniform fixed pi) of the fold's fitted HMM on each half of G; sum the two halves'
  log-likelihoods; divide by the number of G's blocks (all blocks, including those whose features are missing).

## 2. Criterion 1 (selection): density-corrected held-out log-likelihood per block
The task's criterion is the mean held-out log-likelihood per block. **A literal discrete log-likelihood cannot rank bin counts**:
with n equal-mass categories, probabilities per block shrink as n grows (an uninformative model scores log(1/n) per block), so the raw
number mechanically favours the smallest candidate. I therefore register the quantity that is comparable across bin counts, a
histogram-density likelihood:

LL_d = [ sum over halves of log P(sequence) - sum over blocks with an observed player speed of log w(bin) ] / n_blocks

where w(bin) is the width in m/s of the block's player-speed bin, with the outer bins closed at the **training games' pooled minimum
and maximum block player speed** (held-out values beyond that range use the outer bin's width; the bin edges are the fold's frozen
edges). Because 1/w(bin) is state-independent it multiplies every state's emission equally, so it is exact to subtract it after the
forward pass. The raw (uncorrected) per-block log-likelihood is also reported in the table, as the task states it, but **selection
uses LL_d**. (If the raw number had been used it would pick 6 by construction; I say so now.)

## 3. Selection rule (exact tolerance)
Let LL_d(c, f) be candidate c's value on fold f; the best candidate b maximises the mean over the 3 folds. For every candidate define
the paired fold differences d(c, f) = LL_d(b, f) - LL_d(c, f) (so d(b, .) = 0). Candidate c is **within tolerance** iff

mean_f d(c, f) <= SE_c,   SE_c = sd_f(d(c, f)) / sqrt(3)  (sample sd, ddof = 1)

(one standard error of the paired difference; the best candidate is always within tolerance). **Chosen N_PSPEED = the smallest
candidate within tolerance.** Reported but **not used** for the choice: the same rule with the alternative tolerance "mean d <= 0.5% of
|mean LL_d(b)|". No spellF1, macroF1 or any label-based score is used. If the chosen value differs from 12, it is adopted as a follow-up
(not a re-tuned registered run); if it equals 12, 12 is recorded as externally justified.

## 4. Criterion 2 (diagnostic only)
From each fitted fold, the player-speed emission gives ratio r_k = P(category k | D) / P(category k | alive) (H and A share the
alive emission). The **dead-ball cutoff** = the upper edge of the last category before r first drops below 1, scanning from the slowest
category; also reported: the number of times r crosses 1 (1 = a clean cutoff), the widths of the two bins either side of the cutoff
(resolution), a continuous cutoff from linear interpolation of log r between bin centres, and the range of the cutoff across the three
folds. In a categorical model the cutoff is always on a bin edge by construction, so "sits on a bin edge" is reported as which edge and
how wide the neighbouring bins are, not as a surprise.

## 5. Consequences (fixed now)
* Chosen = 12: no re-run; record it.
* Chosen != 12: (i) fit the remaining conditions for that value (degraded seeds 0 and 1, 6 more fits) and the all-games as-is fit;
  (ii) export `analysis/logo_v1_followup/frozen_params_np<N>.json` (the old `analysis/logo_v1/frozen_params.json` is untouched);
  (iii) re-run the same harness with methods `raw,smooth25,smooth50,smooth125,v1_refit,v1_logo,v1_logo_p<N>` into
  `analysis/logo_v1_followup/rerun`, check the label and baseline md5s against `analysis/logo_v1`, apply the unchanged decision rule
  (`analysis/logo_v1/PREREGISTRATION.md` s.5) of `v1_logo_p<N>` vs smooth50 and report the paired difference to the old `v1_logo`.
  Labelled a follow-up; the original `v1_logo` verdict stays the registered result.
* Code check: with N_PSPEED=12 the new code path must give fits identical to the cached `analysis/logo_v1/fits` and the regression test
  (shipped v1 md5 `83b587d7...`) must still pass.

---
## Append-only notes

### 2026-11-10 (note 1): outcome and deviations
* The rule picked **24**, the largest candidate: the density-corrected held-out log-likelihood rose monotonically with the bin count
  (see `partA_table.md`), so the optimum is at the edge of the registered candidate set. Not extended after seeing this (it would need a
  new registration); listed as a recommendation.
* Consequence s.5 applied: fits for the remaining conditions, `frozen_params_np24.json`, harness re-run into `rerun/` with
  `v1_logo` (12 bins) and `v1_logo_p24` side by side. Labels (9 files) and all 54 baseline / `v1_refit` / `v1_logo` prediction files are
  byte-identical to `analysis/logo_v1`; the regression test (shipped v1 md5 `83b587d7...`) still passes with the new code.
* Not a deviation but worth stating: the `v1_logo_p24` fits were produced while the re-run started; the cached fits are deterministic, so
  nothing depends on the order.
