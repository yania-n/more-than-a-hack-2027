# Pre-registration: multi-game validation harness (Sample Games 1-3), v1 vs smooth50

Written 2026-11-01 (session date) **before any method has been scored on Game 1 or Game 2.** Append-only
afterwards (dated notes with reasons). Builds on `analysis/pilot_game3/PREREGISTRATION.md` (unchanged).

Source acknowledgement, quoted from the sample README: *"Please be responsible with the use of this
data. If you use it for anything public, please aknowledge the source."* Metrica Sports' public sample
data, https://github.com/metrica-sports/sample-data (Sample Games 1, 2, 3). Kept in the gitignored
`data/other_games/metrica_sample/`; never committed. No new method is built in this task.

## 0. What I have looked at before registering (no method score exists)

Frame rate, frame counts, slots, players per frame, ball visibility, event/tracking sync, event types,
period boundaries and the dead-ball ball visibility of all three games (table below), plus a label-only
check of what dropping CARRY events does to Game 3's labels. These facts shaped two registered choices
(the CARRY handling in s.2 and the leak-free trigger in s.5); I say so rather than pretend otherwise.

| | Game 1 | Game 2 | Game 3 (pilot) |
|---|---|---|---|
| format | CSV (Home/Away tracking + RawEvents) | CSV | EPTS tracking + JSON events |
| frame rate (Time column / metadata) | 25 Hz | 25 Hz | 25 Hz |
| frames; tracking periods (0-based) | 145,006; 0-71,267 and 71,268-145,005 | 141,156; 0-67,940 and 67,941-141,155 | 143,761; 0-69,660 and 69,661-143,760 |
| tracked slots | 28 (14 per team) | 26 | 22 |
| players on pitch per frame | 22 (23 on 6 frames at substitutions) | 22 (23 on 4 frames) | 22 on every frame |
| ball visible (all frames) | 60.9% | 59.0% | 67.8% |
| events | 1,745 | 1,935 | 3,620 (incl. 1,395 CARRY) |
| sync: PASS ball-to-passer at event start, offset 0 | median 0.08 m, p90 0.22 (n 799) | 0.09, 0.22 (n 964) | 0.06, 0.50 (n 1,121) |
| sync: SHOT, offset 0 | 0.13 m (n 24) | 0.10 m (n 24) | 0.09 m (n 20) |
| frame offset that fits best | 0 (no correction) | 0 | 0 |
| primary D frames with the ball visible | **8.4%** | **0.2%** | **0.2%** |
| primary alive frames with the ball visible | 89-90% | 88-89% | 92-94% |

Coordinates are 0-1 per axis, (0,0) top-left (sample README); converted to 105 x 68 m. Home/Away
tracking files share the same ball. Both CSV games have one KICK OFF row whose End Frame < Start Frame
(Game 1: 1 row) which is handled in s.2. The tracking looks clean for players (22 present on every
frame, substitutes enter by switching which slot is non-NaN) and the ball channel is blank during
stoppages in all three games, which points to provider post-processing; whether it is "automatic" or
"corrected" cannot be determined from the files.

## 1. Games, methods, reference

* Scored games: **game1, game2, game3.** The provided match is used only to validate the adapters, to
  fit v1's transfer parameters, and for the ball-degradation statistics (as in the pilot).
* Methods (all registered through the harness API): `smooth50` (organizers' code, unchanged),
  `v1_refit` (EM refitted on each game and ball condition; **the registered v1**), `v1_transfer`
  (parameters, radius, carry speed and bin edges from the provided match, decoding only).
* Paired-difference reference: `smooth50`. Set-piece feature missing for v1 in every game (no Smart
  Tagging). Player speed derived from positions, +-8 frame central difference (pilot registration).

## 2. Labels: same rules as the pilot, one common event vocabulary

Rules **primary, S1, S2** are exactly those of the pilot (`possession/pilot/labels.py`, including the
S2 FAULT exclusion of the pilot's note 1). Event normalisation for the CSV schema:

| CSV column | meaning in the pilot's event dict |
|---|---|
| `Team` Home / Away | team 0 (H) / 1 (A) |
| `Type` | `type`, same strings (PASS, SHOT, RECOVERY, SET PIECE, CHALLENGE, BALL LOST, BALL OUT, FAULT RECEIVED, CARD) |
| `Subtype` | **hyphen-joined tokens** split on `-` into a set of lower-case subtypes (`GROUND-FAULT-WON` -> {ground, fault, won}; `ON TARGET-GOAL` -> {on target, goal}; `FORCED-END HALF` -> {forced, end half}); no subtype name contains a hyphen |
| `Start Frame`, `End Frame` | `start`, `end` = Frame - 1 (0-based, same index as tracking); **if End < Start, end = start** (only the kick-off row of Game 1) |
| `Period` | `period` |
| `From` | `player` (the event player's own track, used by the sync check) |
| `To`, `Start/End X/Y`, times | unused |

Semantic classes, checked against the event-definitions PDF (the same PDF applies to all three games):

| class | CSV types / subtypes | handling |
|---|---|---|
| controlling | PASS, SHOT, RECOVERY, SET PIECE; CHALLENGE with token `won` (primary only); any CHALLENGE without `fault` (S2) | as the pilot |
| stoppage (D from the event's end frame) | BALL OUT; FAULT RECEIVED; SHOT with token `goal`; BALL LOST with a token in {forced, offside, hand ball, referee hit} | as the pilot |
| end of play (X from the event's end frame) | BALL LOST with token `end half` | as the pilot; **Game 1 period 2 has no END HALF event**, so play is taken to end at the last event's end frame of that period (the pilot's fallback) |
| no effect | CHALLENGE without `won` in primary/S1, CHALLENGE-LOST, plain BALL LOST, CARD | as the pilot |
| **CARRY** | **does not exist in the CSV schema** (Games 1, 2 have 0 CARRY events; Game 3 has 1,395) | see below |

**CARRY handling (registered).** To make the three rules mean the same thing in every game, labels for
**all three games are built from the same vocabulary, with CARRY events excluded** (Game 3's CARRY events
are dropped in the harness). Label-only evidence, computed before any scoring: for Game 3, excluding CARRY
leaves the **primary labels identical** (0.00% of graded frames differ, 388 possessions either way), S2
nearly identical (0.83% of frames, 532 vs 523 possessions) and changes S1 substantially (379 vs 265
possessions, because S1's lone-touch test used CARRY events as the "next controlling event"). So
the harness's Game 3 primary results must reproduce the pilot's (a regression check), while Game 3's S1
and S2 results will differ from the pilot's by the amounts above; this is expected and is reported.

**Graded (play) intervals** per period: from the first event of the period (the kick-off) to the end
frame of the period's END HALF event (or the last event's end frame if there is none); outside = X.
Both methods receive the same boundaries (the analogue of the provided match's published graded
blocks); smooth50 still runs over the whole file as in the organizers' code.

## 3. Ball conditions

Exactly the pilot's: **as-is**; **degraded seed 0 / seed 1** (extra gaps with lengths drawn from the
provided match's ball-missing runs, onsets Poisson with the rate found by bisection to reach the provided
match's 59.3% graded visible share; then Gaussian noise 0.07 m). Where a game's own graded visibility is
already below 59.3% the procedure adds essentially no gaps and only the noise; the achieved visible
share is reported for every game and condition.

## 4. Scoring and the pooled statistic

The organizers' `possession_metrics.evaluate` with 1,000 bootstrap draws for the whole-game scope
(per-half scopes without intervals), for every game x rule x condition x method; spell_f1_mean and
the IoU-0.5 value, macroF1, alive/dead F1, team accuracy (strict and both-alive), predicted vs labelled
possessions; plus label-free proxies (possessions/min, % < 2 s, reversal rate within 3 s, D share).
Paired bootstrap of the spellF1 difference against `smooth50`, 1,000 draws, seed 0.

**Pooled statistic** (registered): per draw, resample each game's labelled possessions with replacement
(the same resample for both methods, as in the pilot), compute each method's per-game spell_f1_mean,
and take the **equal-weight mean over the games** (games are the units that generalise; they have
similar possession counts anyway); the pooled difference is X - Y of that mean, interval = 5th-95th
percentile of the draws, point estimate = mean of the per-game point differences.

## 5. Decision rule for "method X beats method Y" (X = v1_refit, Y = smooth50)

All clauses refer to spell_f1_mean differences X - Y. The **direction** is the sign of clause (a).

* (a) pooled over all games, **primary rule, as-is**: the difference is non-zero and its paired 90%
  interval excludes 0;
* (b) in **each game's** primary rule, as-is, the difference has the sign of (a);
* (c) in the pooled result, as-is, the difference has the sign of (a) under **S1** and under **S2**;
* (d) in the pooled result, primary rule, the difference has the sign of (a) under **degraded seed 0** and
  **degraded seed 1** (both ball conditions other than as-is);
* (e) in at least **80%** of the game x rule x condition cells (27 cells) the difference has the sign of
  (a) in **both halves**.

"X wins" = (a)-(e) all hold in X's favour; "Y wins" = all hold in Y's favour; anything else = **no clear
winner**, with the failing clauses named. v1_transfer vs smooth50 is evaluated by the same rule for
information only; v1_refit stays the registered v1. (Adjustments to the suggested rule: (a) is pinned to
the as-is condition because (d) handles the other conditions; (e) counts a cell only when both halves
have the claimed sign, a stricter reading than "the halves agree with each other".)

## 6. Dead-ball artefact and the leak-free condition

For every game the share of primary-D frames with a visible ball is reported (table above; recomputed in
the harness output). **Trigger (registered): a game gets an extra leak-free condition only if at least 25%
of its dead-ball frames have the ball visible**, i.e. a substantial part of the stoppage-frame ball
exists to keep. The observed values (8.4%, 0.2%, 0.2%; the provided match is described as about 66%) mean
**no game qualifies**, so no leak-free row is run and I do not invent a ball track. (I chose 25% after
having seen those three numbers; I say so. Game 1's 8.4% leaves smooth50's "ball missing => D" rule
almost as strong as in the pilot, so a leak-free row would not change its dead-ball behaviour in any
case.) The harness implements the condition (gaps added only on alive frames, stoppage frames untouched)
and runs it automatically for any future game that meets the trigger.

## 7. Harness requirements (fixed)

One entry point `python -m possession.harness.run --methods smooth50,v1_refit,v1_transfer`; a method is a
function `ctx -> per-frame codes` registered with `@register(name)` from any module loaded with
`--plugin`, with no edit to the harness; the adapter validation on the provided match (smooth50
byte-equal to its repo file, v1 reproducing md5 `83b587d7b36a665a69f2eaf88566e60b`, the helper copies
identical, the transfer path reproducing v1) runs inside every harness run and **fails loudly**;
deterministic, md5 of every label and prediction file from two runs.

---
## Append-only notes

### 2026-11-01 (note 1) — a plumbing smoke run scored Game 1 once before the full run

To test the harness end to end I ran it on **Game 1 only**, with `smooth50`, the trivial plugin method
`always_home` and `v1_transfer`, 20 bootstrap draws, adapter validation skipped, writing to
`analysis/harness_smoke/` (a separate, throwaway folder that was not kept). It therefore produced Game 1 scores before the
full run, so I have seen Game 1 numbers for those methods. Nothing in this pre-registration, the
decision rule, the harness or the labels was changed because of it; the full run (all games, all methods,
validation on, 1,000 draws) is what counts. The smoke run confirmed the plumbing (the trivial method
loses on every clause, as it must).
