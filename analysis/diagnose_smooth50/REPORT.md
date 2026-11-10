# Where `baseline_smooth50` loses points on the public window

Diagnosis only: no fixes and no tuning. Every number here comes from `diagnose.py`, which goes
through `evaluation/possession_metrics.py` and first checks that it reproduces the published
report (macroF1 0.6207, spellF1 0.3256, 26 vs 17 possessions). Graded window: video frames
11185–18684 (7,500 frames, 5 min). Outputs: `results.json`, `tables/*.csv`, `timeline.png`.

## TL;DR

| rank | source of lost spellF1 | error frames | spellF1 if only this were fixed | spellF1 lost to it if everything else were perfect | pipeline part |
|---|---|---|---|---|---|
| 1 | **Team switches at the wrong moment at hand-overs** (late/early, or a short possession erased) | 575 (27%) | 0.326 → **0.616** | 0.43 | team assignment with the ball visible + temporal model (short possessions) |
| 2 | **Brief wrong-team flips inside a possession** (splits one GT possession, adds a spurious one) | 257 (12%) | 0.326 → 0.449 | 0.25 | temporal model + team assignment with the ball visible |
| 3 | **Dead ball not detected** (stoppages labelled alive, plus a few alive stretches labelled dead when the ball vanishes) | 1,319 (61%) | 0.326 → 0.400 | 0.21 | dead-ball detection (+ team assignment with the ball missing for the alive→dead part) |

The headline: **dead-ball errors are 61% of the wrong frames but the smallest spellF1 lever.**
They drive macroF1 (fixing them alone takes it from 0.62 to 0.91), but they mostly widen or
shift a possession rather than create or destroy one. **Team calls are 39% of the wrong frames
but make up most of the spellF1 loss:** fixing all of them gives 0.79. #2 and #3 are within
noise of each other on 17 possessions.

"Fixed" means those frames were given their GT label and everything was scored again (an oracle
ablation, used to measure cost and never to choose a parameter). Errors are fixed as whole
stretches, so the oracle never splits a run.

---

## 1. Frame-level breakdown (graded window)

Confusion, rows = GT, columns = prediction:

| GT \ pred | H | A | D | X |
|---|---:|---:|---:|---:|
| **H** (3,454) | 3,041 | 413 | 0 | 0 |
| **A** (2,577) | 419 | 1,994 | 164 | 0 |
| **D** (1,469) | **902** | **253** | 314 | 0 |

2,151 error frames (28.7% of graded):

| group | frames | % of errors | mechanism (from the baseline's own two steps) |
|---|---:|---:|---|
| dead → alive (GT D, pred H/A) | 1,155 | **53.7%** | ball **visible** during the stoppage: 975; ball missing but the vote carries in the neighbouring alive label: 180 |
| wrong team (GT H↔A) | 832 | 38.7% | nearest player is the other team: 588; nearest player correct but the ±50 vote overrides it: 151; ball missing, vote inherits a neighbour: 93 |
| alive → dead (GT H/A, pred D) | 164 | 7.6% | ball missing for the whole ±50 window: 164 |

Supporting facts:
- The baseline has no dead-ball detector at all. It only writes D when the ball is missing for
  the entire 101-frame window. **The ball is present on 66% of GT-dead frames**, so most
  stoppages get a team label.
- The raw nearest-player call (before smoothing) is right on **77.8%** of frames where the GT
  says alive and the ball is visible (5,640 frames). After smoothing, the team call is right on
  85.8% of frames that both GT and prediction call alive.

## 2. Possession-level breakdown

spellF1 per IoU threshold: 0.51 / 0.47 / 0.33 / 0.23 / 0.09 at 0.3 / 0.4 / 0.5 / 0.6 / 0.7.
At IoU 0.5: 7 of 17 GT possessions matched, 19 of 26 predicted possessions unmatched.

### GT possessions (17)

Ends are inclusive. `thr` = how many of the 5 IoU thresholds the possession is matched at.

| GT | start | end | dur s | team | best pred | IoU | @0.5 | thr | class | pred labels inside (%H/A/D) |
|---|---:|---:|---:|---|---|---:|---|---:|---|---|
| G1 | 11185 | 11350 | 6.6 | A | P1 | 0.587 | ✔ | 3 | | 0/100/0 |
| G2 | 11351 | 11552 | 8.1 | H | P2 | 0.241 | ✘ | 0 | merged | 42/58/0 |
| G3 | 11553 | 11623 | 2.8 | A | – | 0 | ✘ | 0 | wrong team | 100/0/0 |
| G4 | 11624 | 12664 | 41.6 | H | P4 | 0.793 | ✔ | 5 | | 87/13/0 |
| G5 | 12665 | 12850 | 7.4 | A | P5 | 0.384 | ✘ | 1 | boundary | 54/46/0 |
| G6 | 12989 | 13703 | 28.6 | H | P7 | 0.862 | ✔ | 5 | | 93/7/0 |
| G7 | 13704 | 13784 | 3.2 | A | P8 | 0.604 | ✔ | 4 | | 0/100/0 |
| G8 | 13785 | 14845 | 42.4 | H | P11 | 0.558 | ✔ | 3 | | 95/5/0 |
| G9 | 14846 | 15345 | 20.0 | A | P12 | 0.620 | ✔ | 4 | | 0/100/0 |
| G10 | 15346 | 15364 | 0.8 | H | – | 0 | ✘ | 0 | wrong team | 0/100/0 |
| G11 | 15365 | 15765 | 16.0 | A | P12 | 0.309 | ✘ | 0 | split | 16/84/0 |
| G12 | 15766 | 15798 | 1.3 | H | – | 0 | ✘ | 0 | wrong team | 0/100/0 |
| G13 | 15799 | 15888 | 3.6 | A | P14 | 0.237 | ✘ | 0 | merged | 53/47/0 |
| G14 | 16400 | 17292 | 35.7 | A | P19 | 0.413 | ✘ | 2 | split | 12/70/18 |
| G15 | 17293 | 17379 | 3.5 | H | P20 | 0.464 | ✘ | 2 | boundary | 89/11/0 |
| G16 | 17838 | 18026 | 7.6 | A | P25 | 0.633 | ✔ | 4 | | 16/84/0 |
| G17 | 18389 | 18684 | 11.8 | H | P26 | 0.430 | ✘ | 2 | boundary | 100/0/0 |

### Predicted possessions (26)

| pred | start | end | dur s | team | best GT | IoU | @0.5 | thr | class | GT labels inside (%H/A/D) |
|---|---:|---:|---:|---|---|---:|---|---:|---|---|
| P1 | 11185 | 11467 | 11.3 | A | G1 | 0.587 | ✔ | 3 | | 41/59/0 |
| P2 | 11468 | 11703 | 9.4 | H | G2 | 0.241 | ✘ | 0 | merged | 70/30/0 |
| P3 | 11704 | 11800 | 3.9 | A | – | 0 | ✘ | 0 | wrong team | 100/0/0 |
| P4 | 11801 | 12626 | 33.0 | H | G4 | 0.793 | ✔ | 5 | | 100/0/0 |
| P5 | 12627 | 12750 | 5.0 | A | G5 | 0.384 | ✘ | 1 | boundary | 31/69/0 |
| P6 | 12751 | 12880 | 5.2 | H | – | 0 | ✘ | 0 | wrong team | 0/77/23 |
| P7 | 12929 | 13656 | 29.1 | H | G6 | 0.862 | ✔ | 5 | | 92/0/8 |
| P8 | 13657 | 13790 | 5.4 | A | G7 | 0.604 | ✔ | 4 | | 40/60/0 |
| P9 | 13791 | 14206 | 16.6 | H | G8 | 0.392 | ✘ | 0 | split | 100/0/0 |
| P10 | 14207 | 14252 | 1.8 | A | – | 0 | ✘ | 0 | wrong team | 100/0/0 |
| P11 | 14253 | 14847 | 23.8 | H | G8 | 0.558 | ✔ | 3 | | 100/0/0 |
| P12 | 14848 | 15648 | 32.0 | A | G9 | 0.620 | ✔ | 4 | | 2/98/0 |
| P13 | 15649 | 15711 | 2.5 | H | – | 0 | ✘ | 0 | wrong team | 0/100/0 |
| P14 | 15712 | 15840 | 5.2 | A | G13 | 0.237 | ✘ | 0 | merged | 26/74/0 |
| P15 | 15841 | 16276 | 17.4 | H | – | 0 | ✘ | 0 | spurious | 0/11/89 |
| P16 | 16277 | 16627 | 14.0 | A | G14 | 0.224 | ✘ | 0 | split | 0/65/35 |
| P17 | 16628 | 16668 | 1.6 | H | – | 0 | ✘ | 0 | wrong team | 0/100/0 |
| P18 | 16669 | 16695 | 1.1 | A | G14 | 0.030 | ✘ | 0 | split | 0/100/0 |
| P19 | 16728 | 17096 | 14.8 | A | G14 | 0.413 | ✘ | 2 | split | 0/100/0 |
| P20 | 17229 | 17362 | 5.4 | H | G15 | 0.464 | ✘ | 2 | boundary | 52/48/0 |
| P21 | 17363 | 17372 | 0.4 | A | – | 0 | ✘ | 0 | wrong team | 100/0/0 |
| P22 | 17373 | 17381 | 0.4 | H | G15 | 0.079 | ✘ | 0 | boundary | 78/0/22 |
| P23 | 17382 | 17449 | 2.7 | A | – | 0 | ✘ | 0 | spurious | 0/0/100 |
| P24 | 17450 | 17509 | 2.4 | H | – | 0 | ✘ | 0 | spurious | 0/0/100 |
| P25 | 17776 | 17996 | 8.8 | A | G16 | 0.633 | ✔ | 4 | | 0/72/28 |
| P26 | 17997 | 18684 | 27.5 | H | G17 | 0.430 | ✘ | 2 | boundary | 43/4/53 |

### Classes of the unmatched ones (IoU 0.5)

| class | GT side (10 unmatched) | pred side (19 unmatched) |
|---|---:|---:|
| wrong team | 3 (G3, G10, G12) | 6 (P3, P6, P10, P13, P17, P21) |
| boundary | 3 (G5, G15, G17) | 4 (P5, P20, P22, P26) |
| split | 2 (G11, G14) | 4 (P9, P16, P18, P19) |
| merged | 2 (G2, G13) | 2 (P2, P14) |
| spurious | – | 3 (P15, P23, P24) |
| missed | 0 | – |

How the classes are assigned (`classify_spell`), with "meaningful" = overlap ≥ 1 s:
- No same-team overlap at all: **wrong team** if the other side mostly shows the other team,
  otherwise **missed** (GT side) or **spurious** (pred side).
- Several meaningful same-team counterparts: **split** (GT side) or **merged** (pred side).
- The best counterpart also covers other spells on this side: the reverse (merged / split).
- Otherwise: **boundary** (right team, overlapping, start or end off).

These classes are partly a matter of definition. For example, G2 counts as "merged" because P2
also runs 3 s into G4, but the root cause is that P2 starts 4.7 s late.

**Six of the 17 GT possessions are shorter than the vote's 101-frame (4 s) window** (G3, G7,
G10, G12, G13, G15). Only one of them (G7) is matched. A centred ±50 majority vote cannot keep a
run shorter than about half its window, so G10 (0.8 s) and G12 (1.3 s) can't be recovered by
this design at any setting near 50.

## 3. Why each error happens

Error stretches longer than 1 s (23 stretches, **98.2% of all error frames**). `to GT trans` is
the distance in frames to the nearest GT transition. Ball distances are means over the frames
where the ball is present. Smart Tagging excludes the mirrored DEFENDING/DEFENSIVE instances.

| start | end | s | type | ball % | ball→H m | ball→A m | speed m/s | to GT trans | main cause | Smart Tagging (Team) |
|---:|---:|---:|---|---:|---:|---:|---:|---:|---|---|
| 11351 | 11467 | 4.7 | H→A team | 100 | 5.5 | 2.6 | 2.84 | 0 | nearest = other team (98%) | Long Ball, Box, Progression [A] |
| 11553 | 11623 | 2.8 | A→H team | 100 | 2.2 | 2.9 | 3.31 | 0 | nearest = other team (76%) | Box, Progression [A] |
| 11704 | 11800 | 3.9 | H→A team | 100 | 5.5 | 3.2 | 3.41 | 80 | nearest = other team (90%) | Box, Progression [A] |
| 12627 | 12664 | 1.5 | H→A team | 100 | 4.3 | 3.3 | 3.37 | 1 | nearest = other team (63%) | Progression [H]; Att. Transition [A] |
| 12751 | 12850 | 4.0 | A→H team | 80 | 2.8 | 4.0 | 3.89 | 1 | nearest = other team (59%) | Att. Transition [A] |
| 12851 | 12880 | 1.2 | D→H | 0 | – | – | 2.66 | 0 | ball missing, vote carries alive label (100%) | – |
| 12929 | 12988 | 2.4 | D→H | 17 | 1.8 | 6.6 | 1.22 | 1 | ball missing, vote carries alive label (83%) | – |
| 13657 | 13703 | 1.9 | H→A team | 100 | 4.0 | 1.6 | 2.68 | 1 | nearest = other team (81%) | Progression [H] |
| 14207 | 14252 | 1.8 | H→A team | 100 | 6.8 | 5.3 | 2.79 | 422 | nearest = other team (63%) | Final Third [H] |
| 15649 | 15711 | 2.5 | A→H team | 100 | 2.1 | 4.9 | 2.27 | 55 | nearest = other team (87%) | PitB [H] |
| 15766 | 15798 | 1.3 | H→A team | 100 | 2.8 | 1.3 | 3.13 | 0 | nearest = other team (100%) | PitB [H] |
| 15841 | 15888 | 1.9 | A→H team | 100 | 4.2 | 8.9 | 2.72 | 1 | nearest = other team (75%) | PitB [H] |
| **15889** | **16276** | **15.5** | **D→H** | **100** | 6.0 | 23.0 | **1.22** | 0 | ball seen during stoppage (100%) | PitB [H] |
| 16277 | 16399 | 4.9 | D→A | 100 | 6.4 | 1.1 | **0.83** | 1 | ball seen during stoppage (100%) | – |
| 16628 | 16668 | 1.6 | A→H team | 44 | 12.8 | 8.6 | 3.50 | 228 | ball missing, vote inherits neighbour (56%) | – |
| 16696 | 16727 | 1.3 | A→D | 0 | – | – | 3.56 | 296 | ball missing for the whole window (100%) | – |
| 17097 | 17228 | 5.3 | A→D | 0 | – | – | 2.31 | 65 | ball missing for the whole window (100%) | Box, Final Third [A] |
| 17229 | 17292 | 2.6 | A→H team | 22 | 2.4 | 4.5 | 1.96 | 1 | ball missing, vote inherits neighbour (78%) | Box, Final Third [A] |
| 17382 | 17449 | 2.7 | D→A | 100 | 7.0 | 3.8 | **1.20** | 2 | ball seen during stoppage (100%) | Box [A] |
| 17450 | 17509 | 2.4 | D→H | 17 | 7.7 | 11.5 | 1.33 | 70 | ball missing, vote carries alive label (83%) | Box [A] |
| 17776 | 17837 | 2.5 | D→A | 19 | 8.8 | 2.7 | **0.93** | 1 | ball missing, vote carries alive label (81%) | **Set Pieces / Free Kick [A]** |
| 17997 | 18026 | 1.2 | A→H team | 100 | 2.8 | 4.6 | 2.32 | 1 | nearest = other team (63%) | Free Kick [A] |
| **18027** | **18388** | **14.5** | **D→H** | **100** | 3.0 | 17.8 | 2.13 | 0 | ball seen during stoppage (100%) | **Set Pieces / Goal Kick [H]**, Build Up [H] |

### Circumstances of the error frames, compared with all graded frames

| | error frames | all graded frames | lift |
|---|---:|---:|---:|
| ball missing in the tactical ATD | 20.3% | 11.8% | 1.7× |
| within 2 s (50 frames) of a GT transition | 39.0% | 23.9% | 1.6× |
| during GT dead ball | 53.7% | 19.6% | 2.7× |

- **The ball is missing on only about 1 in 5 error frames.** The baseline mostly fails with
  the ball in view, so "ball missing" is a secondary cause here (93 wrong-team frames,
  164 alive→dead frames, 180 dead→alive frames).
- **Mean player speed separates the stoppages.** It is 2.38 m/s on GT-alive frames and 1.42 m/s
  on GT-dead frames. The long dead→alive stretches sit at 0.8–1.3 m/s. The goal kick at 18027
  (2.1 m/s) is the exception, because players move back into shape for the restart.
- **In wrong-team stretches, both teams are close to the ball.** The wrong team's nearest player
  is typically 1–4 m away and the right team's 2–6 m. These are duels, pressing and balls
  arriving at a player: nearest-player geometry can't separate them, and the possession rules
  say they don't change possession.
- **Smart Tagging gives coarse context, not a reliable team signal.** Its instances last tens of
  seconds. "Ball in Final Third [A]" spans most of the 41.6 s home possession G4. Where it does
  help is restarts: **Free Kick** and **Goal Kick** instances line up with two of the stoppages
  the baseline misses (17776, 18027).
- **Transition timing (weak evidence).** Matching transitions to the GT at a loose 5 s
  tolerance pairs 12 of the 20 GT transitions. 8 of those 12 predictions are more than 1 s
  *early* and 2 are more than 1 s late (median −2.1 s). That fits the nearest player flipping
  to the opponent before the GT credits them with control. With transitions this close together
  the pairing is ambiguous, so treat this as a direction to check, not a measured latency.

## 4. Timeline

`timeline.png`, top to bottom: GT, error type, prediction, ball present/missing in the tactical
ATD, and Smart Tagging instances (coloured by the Team tag). Dotted boxes mark error stretches
longer than 1 s.

## 5. The three biggest sources of lost spellF1

Two views of each group's cost: *fix only this group* (how much it is worth on its own today)
and *fix everything except this group* (how much it would still cost once the rest works).

| oracle | spellF1 | macroF1 | # pred spells |
|---|---:|---:|---:|
| none (as submitted) | 0.326 | 0.621 | 26 |
| fix wrong-team stretches at hand-overs | **0.616** | 0.682 | 33 |
| fix wrong-team flips inside a possession | 0.449 | 0.648 | 16 |
| fix all wrong team | **0.790** | 0.709 | 23 |
| fix all dead-ball errors (both directions) | 0.400 | **0.906** | 24 |
| fix everything except hand-over stretches | 0.568 | 0.935 | 14 |
| fix everything except mid-possession flips | 0.746 | 0.971 | 27 |
| fix everything except dead-ball errors | 0.790 | 0.709 | 23 |
| fix everything except dead→alive | 0.863 | 0.730 | 21 |
| fix everything except alive→dead | 0.911 | 0.971 | 19 |

### #1: Team changes at the wrong moment at hand-overs → team assignment with the ball visible (and the temporal model for short possessions)

*575 frames. Fixing only these: +0.29 spellF1. Cost with everything else perfect: 0.43.*

Evidence: 9 of the 13 wrong-team stretches longer than 1 s start or end exactly on a GT
transition (±1 frame), almost always with the ball visible and the nearest player on the wrong
team. They produce every **boundary** and **merged** case: G2 starts 4.7 s late, G5 and G15 are
cut short, and G13 is merged. Three short GT possessions (G3 2.8 s, G10 0.8 s, G12 1.3 s) are
erased completely (**wrong team**). Nearest-player-to-ball can't tell "ball arriving at /
contested by" from "controlled by". The challenge defines possession by control, and keeps it
with the last team while the ball is loose. Separately, the ±50 vote erases any possession
shorter than about 2 s whatever the team model does, and 6 of 17 GT possessions are shorter than
the window.

### #2: Brief wrong-team flips inside a possession → temporal model + team assignment with the ball visible

*257 frames (12% of errors). Fixing only these: +0.12. Cost with everything else perfect: 0.25.*

Evidence: P3 (inside G4), P10 (inside G8), P13 (inside G11), P17 (inside G14) and P21 are 0.4–3.9 s
opponent runs in the middle of a GT possession. Each adds a spurious possession and splits a
real one: G8's best match only reaches IoU 0.56, and G11 and G14 fall below 0.5. Four of the
five have the ball visible with the opponent nearest (duels, pressing). P17 has the ball
missing for half its length. These are the "touch without control" / "deflection" cases the
rules exclude, and a majority vote over a fixed window keeps them whenever they outlast half
the window. A small share of frames, but a large share of the extra possessions (26 predicted
vs 17).

### #3: Dead ball not detected → dead-ball detection (+ team assignment with the ball missing for alive→dead)

*1,319 frames (61% of errors). Fixing only these: +0.07 spellF1 (+0.29 macroF1). Cost with
everything else perfect: 0.21.*

Evidence: the baseline only outputs D when the ball is missing for the whole ±50 window, and the
ball is tracked on 66% of GT-dead frames. So 975 of the 1,155 dead→alive frames have the ball
in view. The two long stoppages (15889, 15.5 s and 18027, 14.5 s) are labelled as possessions,
which creates the spurious 17 s P15, pulls P16's start 4.9 s early (G14 split) and stretches
P26 over 14.5 s of dead ball (G17 boundary, IoU 0.43). Two short stoppages around 17382–17509
become spurious P23 and P24. In the other direction, 164 alive frames become D when the ball
disappears for over 4 s in the box (17097–17228), which splits G14 again. Available signals:
mean player speed (0.8–1.3 m/s in the stoppages vs 2.4 alive) and Smart Tagging set-piece
instances.

**What to work on first:** team assignment around hand-overs (#1), together with a temporal
model that doesn't flip on brief contact (#2). The two are tied: both come from "nearest player"
standing in for "controlling team". Dead-ball detection (#3) is the biggest macroF1 lever and
the third spellF1 lever. Its cost grows once the team calls improve (0.07 alone vs 0.21 when
everything else is right).

## 6. Caveat: this is 17 possessions

**These are hypotheses, not conclusions.** One possession moves spellF1 by about 6 points here,
and the public window already ranks the smoothing windows the wrong way round (EVALUATION.md).
The ranking of #2 vs #3 is within that noise. Specific cases, like a long goal kick or a
5 s ball dropout in the box, may be over-represented in this 5-minute stretch.

How to check them on the full match without labels (and without tuning to any GT count):
- **Flicker:** share of predicted possessions under 2 s, and transitions per minute. A model
  that fixes #2 should cut both sharply. Baseline, full match: 594 possessions,
  5.6 possessions/min, median 4.6 s, **31% under 2 s**, 6.9 transitions/min.
- **Hand-over plausibility (#1):** for each predicted transition, is the new team's nearest
  player still close to the ball 1–2 s later (control) or was it a one-frame touch? The rate of
  A→B→A reversals within a few seconds is a direct label-free read of #1 and #2.
- **Dead ball (#3):** predicted-D share (baseline 32.3% of graded frames), whether long
  low-speed stretches are labelled D, and agreement with Smart Tagging set-piece starts
  (Free Kick, Goal Kick, Corner, Throw-in), which are independent restart markers.
- When comparing two pipeline versions on the public window, run `--bootstrap 1000` and treat
  overlapping intervals as no difference.
