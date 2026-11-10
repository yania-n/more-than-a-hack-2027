# Pilot: smooth50 vs v1 on Metrica Sample Game 3 with event-derived proxy labels

Registered in `PREREGISTRATION.md` before any prediction existed (one dated note, a fix to S2, made
before any scoring). Code: `possession/pilot/`. Nothing is committed.

**Data source and acknowledgement.** Metrica Sports' public sample data,
https://github.com/metrica-sports/sample-data (Sample Game 3). Its README, quoted: *"Please be
responsible with the use of this data. If you use it for anything public, please aknowledge the
source."* There is no formal licence file; the data is free to use with this attribution. The data sits in `data/other_games/metrica_sample/` (gitignored,
never committed or redistributed). The labels are produced by code from the sample's human-annotated
events; no hand labelling, no manual correction.

## 1. TL;DR

* **Registered verdict: "no clear winner (leaning v1)".** v1 (EM refitted on Game 3) is ahead of
  smooth50 on spellF1 in **all 9** whole-game cells (3 label rules x 3 ball conditions), by +0.023 to
  +0.048, and the paired 90% bootstrap interval of the difference excludes 0 in 8 of the 9 cells,
  including the primary as-is cell the rule names (+0.042, [+0.015, +0.073]). It fails the registered
  rule on one count: the sign is not the same in both halves in **3 cells**, all "half 1, degraded
  seed 0" (v1 trails by 0.003 to 0.013). I report the verdict as registered and do not upgrade it.
* **v1 with transfer** (parameters learned on the provided match, decoded on Game 3) is ahead in all
  9 whole-game cells **and** in both halves of every cell (27 of 27). It is not the registered v1, so
  it does not enter the rule, but it agrees on the direction.
* **Where the advantage comes from:** possession structure, not the team call. v1 predicts 378-400
  possessions (refit) against 388 in the labels; smooth50 predicts 517-557. Team accuracy among frames
  both call alive is better for v1 only in the as-is condition (+0.027) and equal under degradation.
* **A big caveat on the dead-ball side.** In Game 3 the ball is visible on 93% of alive frames but on
  **0.2% of dead-ball frames**: the ball track is blank almost exactly when play is stopped. smooth50
  writes D when the ball is missing, so on Game 3 it gets dead ball nearly for free (alive/dead F1
  0.930 as-is vs 0.898 for v1 refit). The degraded condition adds gaps but cannot restore the ball in
  stoppages, so **it does not remove this effect**. This is very likely not true of the provided match,
  so Game 3 flatters smooth50's dead-ball detection; v1's lead on spellF1 is despite it.
* Label-free proxies (short possessions, reversal rate, possessions per minute) all favour v1 over
  smooth50 in every condition, the same direction as spellF1. They do not resolve the finer v1-refit
  vs v1-transfer ordering.
* All predictions and labels are byte-identical across two full runs.

## 2. Data facts (Game 3)

| | |
|---|---|
| frame rate | **25 Hz** (metadata `FrameRate`; the sample README does not say). Same as the provided match, so **no resampling** and every frame-based constant of the pipeline keeps its meaning |
| frames | 143,761; period 1 = frames 1-69,661, period 2 = 69,662-143,761 (contiguous, no halftime gap in the file) |
| pitch / coordinates | 105 x 68 m (README); 0-1 per axis, (0,0) top-left, (0.5,0.5) kick-off (README); converted to metres |
| teams | Team A (metadata `idLocalTeam`, first Team) = home = H; Team B = A. Home attacks right-to-left in period 1 (metadata); irrelevant for possession |
| tracked players | exactly **22 on every frame** (mean 22.00, min 22); the file has 22 position columns, with the column-to-player map defined per data-format segment (substitutes swap into the same columns; team split fixed: columns 0-10 home, 11-21 away) |
| speed column | none (positions only). v1's player speed is derived from positions by a +-8 frame central difference; k = 8 was the registered best of {1,2,3,5,8} against the provided ATD's own speed column (median abs diff 0.105 m/s, all candidates within 0.11) |
| ball visibility | 67.8% of all frames; **68.3% of the play intervals** (as-is). Players are complete, the ball is not |
| play intervals (from events, boundaries only) | frames 360-69,592 and 70,089-143,551 (0-based, inclusive): **95.2 minutes** (46.2 + 49.0), the analogue of the provided match's published graded blocks (106 min) |
| automatic or corrected? | cannot be determined with certainty. `TrackingType` says Optical, but players are never missing and the ball channel is blank while play is stopped (below), which looks post-processed rather than raw |
| Smart Tagging | none: the set-piece feature is **missing** on every block (marginalised) for v1 |

**Sync check (tracking vs events, no correction applied).** Distance from the ball to the event
player's own track at the event start frame: PASS median 0.06 m (p90 0.50 m, n = 1,121), SHOT median
0.09 m (n = 20). At frame offsets of +-1 to 3 it is clearly worse (PASS median 0.12 to 1.01 m). CARRY
events fit best one frame later (median 0.10 m at +1 vs 0.19 m at 0), consistent with a carry being
logged one frame before the touch. So tracking and events are synchronised with **no constant
offset**; event frame_id counts from 1 like the tracking.

**The ball is blank during stoppages (primary labels):** ball visible on 93.5% of H frames, 92.5% of A
frames, **0.2% of D frames**. This is the key domain fact for reading the results.

## 3. Label rules and sanity (`label_stats.json`, `label_timeline.png`)

Event types used (from the Metrica event-definitions PDF): PASS, CARRY, SHOT, RECOVERY, SET PIECE
(kick off, throw in, free kick, corner kick, penalty), CHALLENGE (WON / LOST, GROUND / AERIAL /
TACKLE / DRIBBLE, FAULT / ADVANTAGE), BALL LOST (subtypes INTERCEPTION, THEFT, CLEARANCE, FORCED,
OFFSIDE, HAND BALL, REFEREE HIT, END HALF), BALL OUT, FAULT RECEIVED, CARD. A BALL OUT event starts at
the last touch and ends when the ball crosses the line (up to ~2 s later), so a stoppage begins at the
event's **end** frame; possession belongs to the toucher until then.

| rule | what it does |
|---|---|
| **primary** | PASS, CARRY, SHOT, RECOVERY, SET PIECE and CHALLENGE-WON set possession to the event's team at its start frame. BALL OUT, FAULT RECEIVED, SHOT-GOAL, BALL LOST (FORCED / OFFSIDE / HAND BALL / REFEREE HIT) set D from their **end** frame. D lasts until the next controlling event. BALL LOST END HALF ends play (X). CHALLENGE-LOST and plain BALL LOST change nothing |
| **S1 (stricter)** | primary, but CHALLENGE-WON is not controlling, and a controlling event of the other team is ignored when the next controlling-or-stoppage event is the original team's (a touch / deflection without control) |
| **S2 (looser)** | primary, and any CHALLENGE (WON or LOST) of the other team also takes possession, except challenges carrying the FAULT subtype (a foul is not an on-ball action; see the PREREGISTRATION note) |

| | primary | S1 | S2 | provided match, public window (plausibility only) |
|---|---:|---:|---:|---|
| possessions | 388 | 379 | 532 | 17 (5 min) |
| per minute | 4.08 | 3.98 | 5.59 | |
| mean / median duration (s) | 10.8 / 5.3 | 11.0 / 5.5 | 7.9 / 3.1 | mean 14.2 |
| % possessions < 2 s | 24.5 | 23.2 | 38.2 | |
| D share of graded frames, % | 26.7 | 26.7 | 26.7 | about 20 |
| home share of alive, % | 50.9 | 52.1 | 52.2 | |
| reversal rate (3 s), % | 23.0 | 24.0 | 43.4 | |

Plausible: the same order of magnitude as the provided window (a 5-minute sample of 17 possessions
cannot calibrate more than that). Dead-ball stretches end at restart events (set pieces dominate, then
goal-kick PASSes and RECOVERY), as intended. The dead-ball stretch after a foul can last 50+ s (see the
timeline), which is real, not an artefact of the labelling.

## 4. Adapter validation on the provided match (`validate/validation.json`)

| check | result |
|---|---|
| smooth50 through the adapter vs `evaluation/results/baseline_smooth50.csv` | **0 differing labels** of 199,319. Raw md5 differs from the repo copy only through line endings (repo working-tree file is CRLF); after normalising line endings the md5s are identical (`23924df8...`) |
| v1 through the adapter, EM refit, with set pieces | md5 `83b587d7b36a665a69f2eaf88566e60b`, **identical to `submissions/hmm_v1.csv`** |
| `rederive` (v1's radius/carry-dependent signals, a copy) vs `features.frame_signals` | identical (flight, gap, dwell) |
| `build_with_edges` (v1's categorisation with given edges, a copy) vs `features.build` | identical |
| transfer decode path given v1's own parameters, constants, edges | reproduces v1 exactly |

smooth50 runs through the organizers' functions unchanged on a converted raw file (ATD layout,
speed NaN); v1 runs through its own functions under a runtime context that points `possession.data`
at Game 3. No existing file was edited.

Constants on Game 3 (v1 refit, recomputed): control radius **1.27 m** (provided: 1.91 m), carry speed
5.95 m/s (provided: 6.44). With the transfer variant the provided values are used.

## 5. Results (`results.json`; whole game, 1,000 bootstrap draws)

**Ball conditions.** As-is: 68.3% visible in the play intervals. Degraded (two seeds): extra gaps with
lengths drawn from the provided match's graded ball-missing runs (150 gaps; length percentiles
10/25/50/75/90/99 = 12/152/268/527/845/2,619 frames; mean 431), onsets Poisson with the rate found by
bisection so that the visible share equals the provided match's **59.3%** (achieved 59.31%; this drops
13.1% of the currently visible ball frames; rate 3.6e-4 and 4.8e-4 per frame for seeds 0 and 1), then
Gaussian position noise 0.07 m. Ball visibility is thus matched, but see the caveat: the stoppage
frames were already blank.

**spellF1 (mean over IoU 0.3-0.7), with the organizers' per-method 5-95% bootstrap over the possessions
of that rule's labels:**

| rule | ball | smooth50 | v1 refit | v1 transfer |
|---|---|---|---|---|
| primary (388) | as-is | 0.404 [0.372, 0.433] | **0.446** [0.413, 0.478] | 0.452 [0.420, 0.483] |
| | degraded s0 | 0.380 [0.348, 0.411] | **0.410** [0.377, 0.445] | 0.410 [0.377, 0.442] |
| | degraded s1 | 0.371 [0.339, 0.400] | **0.409** [0.374, 0.442] | 0.405 [0.371, 0.436] |
| S1 (379) | as-is | 0.400 [0.370, 0.430] | **0.447** [0.412, 0.482] | 0.452 [0.421, 0.485] |
| | degraded s0 | 0.378 [0.348, 0.410] | **0.409** [0.374, 0.447] | 0.408 [0.374, 0.443] |
| | degraded s1 | 0.367 [0.336, 0.397] | **0.408** [0.373, 0.444] | 0.404 [0.371, 0.438] |
| S2 (532) | as-is | 0.338 [0.309, 0.368] | **0.370** [0.337, 0.401] | 0.381 [0.351, 0.411] |
| | degraded s0 | 0.312 [0.284, 0.342] | **0.335** [0.304, 0.367] | 0.347 [0.316, 0.380] |
| | degraded s1 | 0.315 [0.286, 0.346] | **0.344** [0.312, 0.378] | 0.351 [0.320, 0.382] |

The per-method intervals overlap in every row, so each method alone cannot be separated from the other
on that reading. The **paired** view (same resample of the labels' possessions for both methods, the
registered test) is sharper:

| rule | ball | v1 refit - smooth50 (paired 90%) | half 1 | half 2 | v1 transfer - smooth50: half 1 / half 2 |
|---|---|---|---:|---:|---|
| primary | as-is | +0.042 [+0.015, +0.073] | +0.014 | +0.067 | +0.034 / +0.060 |
| | degraded s0 | +0.030 [+0.001, +0.062] | **-0.005** | +0.060 | +0.024 / +0.035 |
| | degraded s1 | +0.038 [+0.009, +0.069] | +0.041 | +0.035 | +0.045 / +0.024 |
| S1 | as-is | +0.046 [+0.018, +0.077] | +0.018 | +0.071 | +0.038 / +0.062 |
| | degraded s0 | +0.031 [+0.001, +0.062] | **-0.003** | +0.061 | +0.025 / +0.035 |
| | degraded s1 | +0.041 [+0.011, +0.073] | +0.045 | +0.037 | +0.048 / +0.026 |
| S2 | as-is | +0.032 [+0.004, +0.059] | +0.006 | +0.054 | +0.045 / +0.041 |
| | degraded s0 | +0.023 [-0.006, +0.050] | **-0.013** | +0.052 | +0.040 / +0.029 |
| | degraded s1 | +0.029 [+0.002, +0.057] | +0.032 | +0.026 | +0.061 / +0.014 |

(The headline value of the per-cell point difference is the first number; the interval is the paired
bootstrap, which interval-excludes 0 in 8 of 9 cells, all but S2 / degraded s0. Per-half scores have
about 180-210 labelled possessions each and no interval was computed at half level.)

**Registered rule:** v1 wins needs (a) ahead in all 9 cells, (b) same sign in both halves in every
cell, (c) the primary as-is paired interval excludes 0. (a) holds, (c) holds, **(b) fails in three
cells** => **no clear winner, leaning v1**. The failures are small (-0.003 to -0.013) and all in one
half of one degraded seed; v1 transfer shows no such failure.

## 6. Where each method wins (component metrics, primary rule)

| | ball | smooth50 | v1 refit | v1 transfer |
|---|---|---:|---:|---:|
| macroF1 | as-is | **0.801** | 0.779 | 0.785 |
| | degraded s0 / s1 | 0.745 / 0.747 | 0.753 / 0.757 | **0.766 / 0.763** |
| alive/dead F1 | as-is | **0.930** | 0.898 | 0.905 |
| | degraded s0 / s1 | 0.879 / 0.883 | 0.893 / 0.893 | **0.906 / 0.905** |
| team accuracy, both alive | as-is | 0.863 | **0.890** | 0.888 |
| | degraded s0 / s1 | **0.865 / 0.861** | 0.855 / 0.862 | 0.857 / 0.853 |
| predicted possessions (labels: 388) | as-is | 557 | **400** | 458 |
| | degraded s0 / s1 | 517 / 534 | **383 / 378** | 434 / 434 |

* **Dead ball.** As-is smooth50 wins (0.930 vs 0.898), which the stoppage-blank ball explains: its D
  share is 24.6% against 26.7% in the labels. Under degradation extra gaps in live play make it label
  D wrongly (D share 32-33%) and it falls to 0.88, below v1.
* **Team call.** v1 is better as-is (+0.027) but not under degradation (-0.010 to +0.001). Not a robust
  advantage.
* **Possession structure** is the consistent difference: v1's counts match the labels' while smooth50
  over-fragments by 33-44%.

**Is a hybrid justified?** The pilot does not clearly support one. The dead-ball comparison is
contaminated by the blank-ball effect (smooth50's apparent edge as-is is probably unavailable in the
provided match, where the ball is often visible during stoppages), and v1's team call advantage is
not robust. What the pilot does support is the temporal structure (fewer, longer possessions). I did
not build anything.

## 7. Do the label-free proxies point the same way as spellF1?

On the primary labels, proxies computed on each prediction (the labels themselves: 4.08 poss/min,
24.5% < 2 s, reversal 23.0%):

| | possessions/min | median (s) | % < 2 s | reversal rate (3 s) | D share |
|---|---:|---:|---:|---:|---:|
| smooth50 as-is | 5.86 | 3.7 | 37.7 | 40.0 | 24.6 |
| v1 refit as-is | 4.20 | 6.4 | 15.0 | 22.8 | 30.1 |
| v1 transfer as-is | 4.81 | 4.8 | 23.1 | 35.9 | 27.7 |
| smooth50 degraded s0 / s1 | 5.43 / 5.61 | 3.7 / 3.8 | 38.1 / 38.4 | 39.2 / 38.2 | 33.2 / 32.3 |
| v1 refit degraded s0 / s1 | 4.03 / 3.97 | 6.4 / 7.0 | 13.8 / 13.8 | 20.5 / 19.4 | 30.8 / 30.8 |
| v1 transfer degraded s0 / s1 | 4.56 / 4.56 | 4.8 / 5.6 | 23.3 / 22.6 | 37.7 / 34.6 | 27.5 / 27.7 |

* **v1 vs smooth50: yes, same direction.** v1 has fewer short possessions and a lower reversal rate in
  all three conditions, and is ahead on spellF1 in all nine whole-game cells. The proxies used in v2
  and v3 (short possessions, reversals) track spellF1 at this coarse level.
* **Within v1: no.** v1 refit has the "better" proxies (reversal 23%, essentially the labels' own 23%)
  yet v1 transfer scores equal or slightly higher spellF1 (differences inside the noise). The proxies
  do not rank closely matched models and a lower reversal rate is not monotonically better.
* Caution: the label-free proxies reward fewer possessions up to the labels' own level; below it (v1
  refit's 15% < 2 s against 24.5% in the labels) they would start to penalise a model that merges
  genuine short possessions.

## 8. Limits

* **Proxy labels** come from human-annotated events and a rule set I wrote; they are not the
  competition's corrected-tracking ground truth. Three rules bracket the main ambiguity, but a rule
  all three share (for example CARRY always counting as possession) is not tested.
* **One game, one competition-like but different tracking.** Players always complete (22/22), ball
  blank in stoppages, different pitch model and provider pipeline: **a real domain shift**, and the
  stoppage-blank ball in particular favours rules that read ball absence as dead ball (smooth50) and
  does not exist in this form in the provided match. The degraded condition equalises ball visibility
  but not this relation; I could not restore a ball track in stoppages.
* **Unverified:** whether Game 3's tracking is automatic or corrected; whether the dead-ball ball
  blanking comes from the provider's post-processing; the exact semantics of event start frames for
  every type (checked only for PASS, SHOT, CARRY).
* **v1 is not tuned for this game**: its constants and bin edges are recomputed (refit) or borrowed
  (transfer); the set-piece feature is missing (no Smart Tagging); player speed is derived.
* Half-level comparisons use about 180-210 possessions and no interval; the three failing cells are
  small and could be noise.
* The proxy-vs-spellF1 check has only 9 predictions per method family, all from one game.

## 9. Next steps (not done)

1. **Test on Sample Games 1 and 2** (CSV format, anonymised). If their ball is not blank in
   stoppages the dead-ball comparison becomes meaningful, and two more full games would settle the
   per-half sign question.
2. **A leak-free ball-condition:** also blank the ball on frames at random positions of the *alive*
   segments **and** make the dead-ball segments look like the provided match (ball present there),
   which requires a ball track that exists during stoppages; Games 1 and 2 may offer one.
3. Keep v1 as the base: the temporal structure is its evidenced advantage here.

## 10. Reproducibility

```
python -m possession.pilot.make_labels         # labels_{primary,S1,S2}.csv + sanity stats and plot
python -m possession.pilot.validate_adapters   # adapter validation on the provided match
python -m possession.pilot.run_pilot           # predictions + scoring -> results.json
```
Two complete runs gave identical md5s for all 12 files (and identical results):

| file | md5 |
|---|---|
| labels_primary | 1a5e88388da10430d09c86b1dc55e922 |
| labels_S1 | ad4df50a9b0924743619fb2f855114c2 |
| labels_S2 | 388f2e2c64ea1708aa3874a287c18b6c |
| smooth50 as-is / deg s0 / deg s1 | 4c8dd092117427bb03d938435ce34a29 / 7be8c20014e83a042108217d5ef764a5 / 024021268b7ba722310f7c6955c9bce6 |
| v1 refit as-is / deg s0 / deg s1 | 3a8eb5c8d532268c4b2ead523a854c86 / 6211f97b925d522cb241ba061b214643 / 27e25f006b7b667d49b2aa29488676a7 |
| v1 transfer as-is / deg s0 / deg s1 | aa40f550f03f7cae9500eb24d042fe14 / d29fd7a8b2db75620b4472e1f6559ed2 / bef581b2ab7d5c36bf4806a011c3ad42 |

Housekeeping: only `possession/pilot/` is new in the repository (`.gitignore` shows modified from
before the session and was not touched); outputs live in the gitignored `analysis/pilot_game3/`; the
sample data is in the gitignored `data/other_games/`. The PDF text was extracted with `pypdf` installed
in a scratch folder (not a project dependency); no new dependency was added to the pipeline.
