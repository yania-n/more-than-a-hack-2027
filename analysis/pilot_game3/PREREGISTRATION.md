# Pre-registration: pilot on Metrica Sample Game 3 (smooth50 vs v1)

Written 2026-11-01 (session date), **before any method has been run on Game 3 and before any score
exists.** Append-only afterwards (dated notes with a reason).

What I have looked at so far (no scores involved): the sample repo README and the event-definitions
PDF; Game 3's metadata (25 Hz, two contiguous periods, 22 tracked columns per frame, 143,761 frames);
the events JSON structure; the alignment of events to tracking (at event start the ball is a median
0.06 m from the passer and 0.09 m from the shooter at frame offset 0, so there is no shift to
correct); ball visibility (67.8%); and the sequence of events around stoppages.

Source acknowledgement (the sample README's "Legal stuff", quoted): "Please be responsible with the
use of this data. If you use it for anything public, please aknowledge the source." The data is
Metrica Sports' public sample data, https://github.com/metrica-sports/sample-data. It sits in the
gitignored `data/other_games/` and is never committed.

## 1. Question

Does v1 beat baseline_smooth50 on spellF1 on a full game scored against event-derived proxy labels?
Reported with a per-component view: alive/dead F1, team accuracy when both call it alive
(`team_acc_both_alive`), macroF1.

## 2. Frames, periods, graded intervals

* 25 Hz (metadata `FrameRate`), the same as the provided match: **no resampling**; all frame-based
  constants in the pipeline (blocks of 10 frames, 1 s speed smoothing, 0.2 s windows) keep their meaning.
* Frame index: event/tracking frame_id counts from 1; arrays are 0-based (frame_id - 1), as for the
  provided match.
* **Graded (play) interval per period** = from the first event of the period (the KICK OFF set piece)
  to the end frame of the `BALL LOST ... END HALF` event of the period. Frames outside = X in the
  labels. These two boundaries per half are the analogue of the published graded blocks of the
  provided match (boundaries only); both methods receive the same boundaries. The v1 model is run on
  these intervals, one half at a time; smooth50 runs over the whole file as in the organizers' code.
* Home = Team A (first Team in the metadata, `idLocalTeam`) = H; Team B = A.

## 3. Label rules (all by code, no manual edits)

Events sorted by an **effective time**, ties broken by their order in the file. Per event:

| event | effect |
|---|---|
| `PASS`, `CARRY`, `SHOT`, `RECOVERY`, `SET PIECE`, `CHALLENGE` with subtype WON | **controlling**: at its start frame the event's team holds the ball (state = that team) |
| `CHALLENGE` LOST, `BALL LOST` (without stoppage subtype), `CARD` | no effect |
| `BALL OUT`, `FAULT RECEIVED`, `SHOT` with subtype GOAL, `BALL LOST` with subtype FORCED, OFFSIDE, HAND BALL or REFEREE HIT | **stoppage**: state = D from the event's **end** frame |
| `BALL LOST` with subtype END HALF | end of play: X from the event's end frame |

* Effective time = event **end** frame for stoppage events (a BALL OUT starts at the last touch and
  ends when the ball crosses the line, up to ~2 s later: possession belongs to the toucher until
  then), event **start** frame otherwise.
* D lasts until the next controlling event, which restarts play for its team. Frames before the
  first controlling event of a period (the kick-off) are X.
* Possession "stays with the last team while the ball is loose" (CHALLENGE.md): a BALL LOST by team X
  does not hand the ball to Y; Y's own controlling event (normally the RECOVERY that follows) does.

**Primary rule** = the table above (CHALLENGE WON counts as controlling).

**S1 (stricter on control):** as primary, except (i) CHALLENGE WON is not controlling, and (ii) a
controlling event of the *other* team triggers a switch only if the next controlling-or-stoppage
event that follows it does not belong to the original team (a lone touch / deflection / duel win
immediately followed by the original team's action is "touch without control" and ignored).

**S2 (looser):** as primary, and in addition a `CHALLENGE` (WON or LOST) event of the other team
switches possession to that team at its start frame (any on-ball type counts).

Sanity report per rule: possessions, mean and median duration, D share, home share of alive frames,
timeline plot of 5 minutes with the events overlaid; compared with the provided match's public-window
figures (17 possessions of 14.2 s, D about 20%) as a plausibility check only.

## 4. Pipelines and adapters

Existing code is never edited. Adapters in `possession/pilot/` feed Game 3 to it.

* **smooth50:** `starter/baseline.py` (`nearest_player_labels`, `smooth`, `team_of_each_track`) called
  unchanged on a converted raw file (ATD layout: `frame:x,y,speed;...:x,y,speed`, speed NaN). Validated
  first on the provided match: must equal `evaluation/results/baseline_smooth50.csv` byte for byte.
* **v1:** `possession.features` / `possession.hmm` called unchanged under a runtime context that points
  `possession.data` at Game 3 (frame count, graded blocks, tracking, set pieces). Validated first on
  the provided match through the same adapter: must reproduce md5 `83b587d7b36a665a69f2eaf88566e60b`.
* **Player speed:** Game 3 has no speed column. v1's `pspeed` is derived from positions by a central
  difference over +-k frames, with k chosen as the one (k in {1,2,3,5,8}) whose derived speed is
  closest (median absolute difference) to the provided ATD's own speed column on the provided match.
  Unlabeled; fixed before running Game 3.
* **Smart Tagging:** none for Game 3, so the set-piece feature is **missing** on every block
  (marginalised, as v1 does for any missing feature).
* **v1 refit (primary v1):** EM refitted on Game 3 alone; control radius, carry speed and percentile
  bin edges recomputed on Game 3. **v1 transfer (secondary):** parameters, radius (1.91 m), carry speed
  (6.44 m/s) and bin edges from the provided match; only decoding is done on Game 3. A different edge
  set requires re-categorising; this is done by a copy of v1's categorisation that takes the edges as
  an argument, validated to reproduce v1's own categories when given its own edges.

## 5. Ball conditions

* **As-is:** the sample's own ball track.
* **Degraded:** to mimic the provided tracking's ball. (a) Extra ball gaps: lengths drawn from the
  empirical distribution of ball-missing run lengths of the provided match's graded frames; onsets
  placed as a Poisson process over currently visible ball frames, with the rate found by bisection so
  that the final graded visible share equals the provided match's (59.3%). (b) Gaussian position noise,
  sigma = 0.07 m per coordinate (v3's measured upper bound for the provided ATD) on visible ball
  frames. Seeds 0 and 1 (`numpy.random.default_rng`). The same degraded tracking goes to both methods;
  v1 refit is refitted on it (constants recomputed). The distributions used are reported.

## 6. Scoring

`possession_metrics.evaluate(gt, pred, bootstrap_n=1000)` and the same functions the scorer uses:
spell_f1_mean, spell_f1_at_headline (IoU 0.5), macro_f1, alive_dead_f1, team_acc_gt_alive,
team_acc_both_alive; for every method x rule (primary, S1, S2) x condition (as-is, degraded seed 0,
degraded seed 1) x scope (whole game, half 1, half 2; a half is scored by marking the other half X).
The paired difference v1 - smooth50 in spellF1 gets a 90% paired bootstrap interval (same resample of
ground-truth possessions for both methods, whole game, 1000 draws, seed 0), built from the same
matching flags as `bootstrap_spell_f1`.

## 7. What counts as a robust answer

* **"v1 wins"** only if v1 (refit) is ahead on spellF1 (a) in all nine cells {primary, S1, S2} x
  {as-is, degraded seed 0, degraded seed 1}, (b) with the same sign in half 1 and half 2 in every
  cell, **and** (c) the 90% paired-bootstrap interval of the difference excludes 0 in the primary
  as-is cell. **"smooth50 wins"** is the mirror image.
* Anything else is reported as **"no clear winner"**, naming the leaning (if all signs agree but the
  interval includes 0, "leaning v1/smooth50, not separable") and which cells disagree.
* The bootstrap intervals are over Game 3's possessions (hundreds, not 17). Overlapping per-method
  intervals mean the methods cannot be separated on that cell.
* Transfer v1 is reported alongside; it does not enter the win rule but I say whether it agrees.
* Nothing from the provided match's private ground truth is used, and the public window is not used to
  choose anything.

## 8. Proxy check

Label-free proxies used in v2 and v3 (percentage of possessions < 2 s, reversal rate within 3 s,
possessions per minute) are computed on every Game 3 prediction and compared with the spellF1 ordering
of the same predictions. Reported whether they point the same way.

## 9. Stopping

If the data or a validation step shows a surprise (sync off, a frame-rate mismatch, an adapter that
does not reproduce the provided-match output), stop and report it rather than forcing it.

---
## Append-only notes

### 2026-11-01 (note 1) — S2 excludes challenges that carry the FAULT subtype

Reason: the label timeline plot (`label_timeline.png`, made before any method was run or scored)
showed that S2 as registered counted a `CHALLENGE ... FAULT, LOST` event by the fouling team, logged two
frames after the stoppage, as an "on-ball" event: it ended the dead-ball stretch and created a false
18 s possession for that team. A foul is not an on-ball action. Change: in S2 a CHALLENGE (WON or LOST)
is switching/restarting only if it does **not** carry the FAULT subtype. Primary and S1 are unchanged
(they count only CHALLENGE WON, and a fault challenge won by the fouled team is followed by the
FAULT RECEIVED stoppage at the same frame, so it does not reopen play). Applied before any prediction
existed on Game 3; no score informed it.
