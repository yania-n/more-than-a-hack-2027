# Pre-registration, Part B: domain-shift check of the frozen model on the provided match (label-free, descriptive)

Written 2026-11-10 **before the frozen model was run on, or any feature statistic computed from, the provided match in this task.**
Append-only after. Metrica Sports sample data (https://github.com/metrica-sports/sample-data) is acknowledged as the source of
the fitted numbers; it stays gitignored.

## 0. Rules and what is read
The provided match is **input to a frozen model only**: no refit, no tuning, no scoring against its ground truth. Read: the tactical
ATD tracking file and its metadata (via `possession.data.load_atd`, the same loader as the shipped v1) and the published graded blocks
(`data.graded_blocks()`, constants of `games.py`). **Not read:** any ground-truth CSV (`*_possession_gt*.csv`, `evaluation/gt/`), the
public window, the video, Smart Tagging (the set-piece feature is missing in the frozen model). Read-only reference outputs (labels,
not ground truth): `evaluation/results/baseline_smooth50.csv` (organisers' baseline output) and `submissions/hmm_v1.csv` (the old,
non-compliant shipped v1). Derived per-frame output of the frozen model goes to `analysis/logo_v1_followup/private/` (a nested
`.gitignore` ignores everything there) and nowhere else; not to `submissions/`.

Disclosure: earlier sessions' reports (`analysis/hmm_v1`) describe the old shipped v1 on the provided match; I have not read them in this
task and the thresholds below were not set from them. I have not yet seen the frozen model's output on the provided match.

## 1. Model
The frozen all-sample-games model: `analysis/logo_v1_followup/frozen_params_np<N>.json` if Part A changes N_PSPEED, otherwise
`analysis/logo_v1/frozen_params.json`. Pipeline = `adapters.run_v1(mode="transfer")` with the provided match's tracking as loaded for
the shipped v1 (including the ATD file's own player-speed column, which is what the shipped v1 used), intervals `data.graded_blocks()`,
no set pieces, `setpiece_missing=True` (the frozen set-piece emission is uninformative, so this changes nothing).

## 2. B1 feature-shift diagnostic
Blocks of the provided match are binned with the frozen radius, carry speed and bin edges (`rederive` + `build_with_edges`). The
reference ("training") distribution is the three sample games, as-is, over their tracking periods, binned with the same frozen pack
(player speed derived from positions, +-8 frames, as in fitting). For each feature (gap, dwell, ball speed, heading, outside, player speed;
set-piece reported as missing in all):
* observed-category distributions p_prov and p_train (missing blocks excluded) and **TV = 0.5 * sum |p_prov - p_train|**;
* scale for TV: each sample game against the pooled other two (same bins);
* the three bins that gain and the three that lose most mass;
* missing share of every feature in the provided match, in each sample game and pooled (the control features gap and dwell are missing
  when the ball is absent or in flight).
Flags ("needs investigation"): (i) TV(prov) > 2 x the largest sample-game TV on that feature; (ii) more than 10% of the provided match's
observed mass lies in bins whose training share is < 2%; (iii) a missing share outside [0.5 x min, 2 x max] of the three sample games'.

## 3. B2 run
One decode with the pipeline of s.1; deterministic (run twice, md5 compared). Output `frame,label` (H/A/D, X outside the graded blocks)
to `private/`.

## 4. B3 proxies, defined exactly
Applied identically to: `v1_external_all` (provided match), `smooth50` (organisers' CSV, masked to the same graded frames), old v1
(`submissions/hmm_v1.csv`), and, as references, for each sample game: the primary-rule proxy labels, the `v1_logo` as-is predictions
(`analysis/logo_v1`), and `smooth50` predictions. All codes get X outside the graded blocks (assert that the mask equals the old v1's
non-X frames); runs = `pm.valid_runs(codes)`; spells = `pm.possession_spells`; segments = `pm.segments`; transitions = `pm.transitions`
(organisers' functions); fps 25.
1. `poss_per_alive_min` = number of spells / ((#H + #A) / fps / 60).
2. `mean_poss_len_s` = mean spell length in seconds.
3. `pct_lt_2s` = share of spells shorter than 2 s.
4. `reversal_3s` = among *direct* transitions (from and to both in {H, A}), the share whose next transition (in the same run) goes
   directly back (from' = to, to' = from) within 3 s (75 frames). (Same definition as `labels.label_stats`; a system that always
   inserts D between teams has few direct transitions, so `n_direct` is reported next to it.)
5. `dead_share` = D frames / graded frames; `mean_dead_spell_s` = mean length of D segments; (median also shown).
6. `home_share_alive` = H / (H + A).
7. Agreement (descriptive, **not a score**): frame agreement over graded frames (share of equal codes, D included) and organiser spellF1
   (`pm.evaluate(ref, pred, bootstrap_n=0)["spell_f1_mean"]`) with the named system as reference, for (ext vs smooth50, ref smooth50),
   (ext vs old v1, ref old v1), (old v1 vs smooth50, ref smooth50); on each sample game the same for (v1_logo vs smooth50, ref smooth50).
**Flags ("needs investigation"), v1_external_all only, nothing is pass/fail:** (a) a proxy outside [0.5 x min, 2 x max] of the three
sample games' primary proxy labels; (b) a proxy whose ratio to the old shipped v1 lies outside [1/1.5, 1.5] (for `home_share_alive` an
absolute difference > 0.10 instead). The same two flags are shown for smooth50 and the old v1 for context only. A value inside the
range means "plausible", never "correct".

## 5. B4 diagnosis (only if something is flagged)
For each flagged proxy, re-decode the provided match with **one change at a time** to the frozen pack, each alone, from this fixed list:
radius := shipped 1.9139 m; carry := shipped 6.440 m/s; each of the five edge groups := shipped edges (gap, dwell, ball speed, heading,
player speed) separately; transition matrix := shipped; player speed := positions-derived (+-8 frames) instead of the file column.
(The shipped constants come from a fit on the provided match, so this is diagnosis only.) Report each proxy under each change.
**No change is adopted.** A change can only be adopted if re-derived on external data under a new pre-registered rule; otherwise it is
listed as a recommendation.

## 6. Not done
No scoring against ground truth, no public window, no video, no hand labels, no refit, no submission file, no upload of provided data.

---
## Append-only notes

### 2026-11-10 (note 1): outcome and deviations
* Frozen model used: `frozen_params_np24.json` (Part A changed N_PSPEED to 24).
* **B4 was not run:** its registered trigger is a flagged output proxy, and none of the seven proxies fell outside the registered bands.
  The feature-shift flags of B1 (dwell, heading) do not trigger B4 under s.5 as written.
* The B1 "gain / lose" lists were changed from "top 3 by sign-agnostic order" to "top 3 with the right sign" after the first print showed
  overlapping entries for features with few bins (cosmetic; no statistic changed).
* The registered missing-share band gives a degenerate flag for player speed (0.2% provided against 0.0% in every sample game: 2 x 0 = 0).
  It is reported as written and read as immaterial in the report.
* The registered home-share band ([0.5 x min, 2 x max] of about 51-52%) is vacuous (about 26% to 105%). Reported as written; the
  report comments on the value anyway.
