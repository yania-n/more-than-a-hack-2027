# Multi-game validation harness: v1 vs smooth50 on Metrica Sample Games 1, 2 and 3

Registered in `PREREGISTRATION.md` before any method was scored on Games 1 and 2 (one dated note: a
plumbing smoke run scored Game 1 once with 20 draws before the full run; nothing was changed because of
it). Code: `possession/harness/`. Nothing is committed. No new method was built.

**Source acknowledgement.** Metrica Sports' public sample data,
https://github.com/metrica-sports/sample-data (Sample Games 1, 2, 3). Its README, quoted: *"Please be
responsible with the use of this data. If you use it for anything public, please aknowledge the
source."* There is no formal licence file; the data is free to use with this attribution. The data lives in the gitignored `data/other_games/metrica_sample/` and is
never committed. Labels are produced by code from the sample's human-annotated events; no hand labelling.

## 1. TL;DR

* **Registered verdict, v1 (refit) vs smooth50 across three games: "no clear winner (leaning v1)".**
  Clauses (a) to (d) hold; **clause (e) decided it**: v1 is ahead in *both halves* in only **14 of 27**
  game x rule x condition cells (52%), below the registered 80%.
  * (a) pooled primary, as-is: **+0.036**, paired 90% interval [+0.018, +0.054] excludes 0: pass.
  * (b) each game's primary rule, as-is: Game 1 +0.042, Game 2 +0.024, Game 3 +0.042, all positive: pass.
  * (c) pooled S1 +0.050 and S2 +0.023: pass. (d) pooled primary, degraded seeds 0/1: +0.037, +0.038: pass.
  * (e) fails: in each game one half has v1 behind smooth50 (Game 1 half 2 by up to 0.036; Game 2
    half 1 by up to 0.026, mostly under S2; two Game 3 degraded cells in half 1 by up to 0.012).
* **Stronger than the verdict reads:** v1 refit is ahead on whole-game spellF1 in **all 27** cells and every
  one of the 9 pooled intervals excludes 0. What does not hold up is the per-half sign.
* **v1 transfer vs smooth50 gets the same verdict** (a-d pass, (e) 18/27 = 67%): its only half-sign
  failures are all in Game 1 half 2 (9 cells, v1 behind by 0.016 to 0.068).
* **Dead ball is where smooth50 holds up, and the data make this unreliable:** the ball is blank during
  stoppages in all three games (visible on **8.4%**, **0.2%** and **0.2%** of dead-ball frames), so
  smooth50's "ball missing = D" rule is nearly a leak. Alive/dead F1 and macroF1 favour smooth50 as-is in
  every game. v1's gain is possession structure: predicted possessions near the labelled counts instead of
  30-45% too many.
* Harness validated: adapters re-verified on the provided match inside the run (smooth50 byte-equal to its
  repo file, v1 md5 `83b587d7...`), Game 3 predictions byte-identical to the pilot's, all 36 label and
  prediction files byte-identical over two runs.

## 2. Data facts per game

| | Game 1 | Game 2 | Game 3 |
|---|---|---|---|
| format | CSV (Home/Away tracking + events CSV) | CSV | EPTS tracking + JSON events |
| frame rate | 25 Hz (Time column) | 25 Hz | 25 Hz (metadata) |
| frames | 145,006 | 141,156 | 143,761 |
| periods (tracking, 0-based) | 0-71,267 / 71,268-145,005 | 0-67,940 / 67,941-141,155 | 0-69,660 / 69,661-143,760 |
| graded play intervals (from events) | 0-70,576 / 72,134-143,629 | 50-67,855 / 67,991-140,297 | 360-69,592 / 70,089-143,551 |
| graded minutes | 94.7 | 93.4 | 95.1 |
| pitch, coordinates | 105 x 68 m; 0-1 per axis, (0,0) top-left (sample README) | same | same |
| tracked slots / players on pitch per frame | 28 / 22 (23 on 6 frames) | 26 / 22 (23 on 4 frames) | 22 / 22 always |
| ball visible: all frames / graded | 60.9% / 62.1% | 59.0% / 59.4% | 67.8% / 68.3% |
| ball visible on **alive** frames | 89.9% | 88.6% | 93.0% |
| ball visible on **dead-ball** frames (primary labels) | **8.4%** | **0.19%** | **0.25%** |
| sync, PASS: ball to passer at event start, offset 0 | median 0.08 m, p90 0.22 (n 799) | 0.09, 0.22 (n 964) | 0.06, 0.50 (n 1,121) |
| sync, SHOT, offset 0 | 0.13 m (n 24) | 0.10 m (n 24) | 0.09 m (n 20) |
| best frame offset (none applied) | 0 | 0 | 0 |
| looks automatic or corrected? | clean players (22 on every frame), ball blank in stoppages: looks post-processed; cannot be confirmed | same | same |

Players are never missing; at substitutions a replacement's slot turns non-NaN, so a few frames show 23.
No red-card variation occurs in any game. At other frame offsets the sync is clearly worse in all three
games (PASS p90 0.78-1.39 m at negative offsets, median up to 0.64 m at +2), so events and tracking are
synchronised with no correction.

**The dead-ball pattern.** In all three games the ball track is blank almost exactly when play is stopped.
For comparison the provided match has the ball present on about 66% of its stoppage frames (figure from
the brief). Game 1 is the least extreme (8.4%) but still far from it. **No game meets the registered
trigger (>= 25% of dead-ball frames with a ball) for a leak-free condition, so none was run and no ball
track was invented.** The harness implements that condition (gaps only in alive play) and will run it
automatically for any future game that qualifies. The pilot's caveat therefore applies to **all three
games**, not only Game 3.

## 3. Event-schema mapping and label rules

The CSV schema differs from Game 3's JSON (`Type`, hyphen-joined `Subtype`, `Start/End Frame`, `From`);
the mapping table is in `PREREGISTRATION.md` s.2 and was checked against the event-definitions PDF:
subtype tokens split on `-` (no subtype name contains a hyphen), frames minus one, an End Frame before
the Start Frame (one kick-off row in Game 1) set to the start. Classes: controlling = PASS, SHOT,
RECOVERY, SET PIECE, CHALLENGE-WON (primary), non-fault CHALLENGE (S2); stoppage (D from the event's end
frame) = BALL OUT, FAULT RECEIVED, SHOT-GOAL, BALL LOST with FORCED / OFFSIDE / HAND BALL / REFEREE HIT;
END HALF ends play. **CARRY exists only in Game 3's schema;** to make the rules identical in every game, all
three are labelled from the same vocabulary with CARRY excluded. Checked on Game 3 before scoring:
primary labels unchanged (0.00% of frames, 388 possessions either way), S2 almost (0.83%), **S1 changes
substantially (379 -> 265 possessions)**, so Game 3's S1 and S2 numbers here differ from the pilot's by
design. Game 1 period 2 has no END HALF event, so its play interval ends at the last event.

| | possessions | per min | mean / median (s) | % < 2 s | D share % | median D stretch (s) | home share of alive % | reversal 3 s % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Game 1 primary** | 355 | 3.75 | 10.5 / 5.3 | 19.7 | 34.1 | 18.7 | 52.4 | 24.5 |
| Game 1 S1 | 229 | 2.42 | 16.2 / 9.6 | 13.1 | 34.7 | 18.7 | 54.0 | 3.4 |
| Game 1 S2 | 417 | 4.40 | 9.0 / 4.0 | 27.6 | 34.0 | 18.7 | 54.2 | 33.4 |
| **Game 2 primary** | 316 | 3.38 | 11.9 / 6.2 | 21.5 | 33.0 | 13.3 | 51.7 | 17.8 |
| Game 2 S1 | 232 | 2.48 | 16.2 / 10.1 | 16.8 | 33.0 | 13.3 | 53.1 | 2.0 |
| Game 2 S2 | 457 | 4.89 | 8.2 / 3.5 | 37.4 | 33.0 | 13.3 | 52.4 | 41.9 |
| **Game 3 primary** | 388 | 4.08 | 10.8 / 5.3 | 24.5 | 26.7 | 11.5 | 50.9 | 23.0 |
| Game 3 S1 | 265 | 2.79 | 15.8 / 9.8 | 14.7 | 26.7 | 11.5 | 52.6 | 3.5 |
| Game 3 S2 | 523 | 5.50 | 8.0 / 3.3 | 36.3 | 26.7 | 11.5 | 52.2 | 41.1 |

The three games are close to each other: 316-388 primary possessions, 3.4-4.1 per minute, medians 5.3-6.2 s,
D 27-34%, home share about 51-52%. Under the common vocabulary S1 is much stricter than in the pilot (few
reversals); that is the intended "touch without control" filter, not a bug.

## 4. Results

**Ball conditions.** As-is, and degraded seeds 0/1 with the pilot's procedure (extra gaps from the provided
match's gap-length distribution, rate bisected to the provided match's 59.3% graded visibility, then 0.07 m
noise). Achieved visible share 59.31% in all cases. The extra gaps cover 4.5% of the visible ball frames in
Game 1, **0.2% in Game 2** (its own visibility is already 59.4%, so "degraded" is essentially as-is plus
noise there) and 13.1% in Game 3.

**spellF1 (mean over IoU 0.3-0.7), primary rule**, with each method's own 5-95% bootstrap over the game's
possessions, then v1 refit - smooth50 with the paired 90% interval and the half-level differences
(half 1, half 2). Full 81-cell results are in `results.json` / `results.csv`.

| game | ball | smooth50 | v1 refit | v1 transfer | refit - smooth50 [paired 90%] | halves | transfer halves |
|---|---|---|---|---|---|---|---|
| 1 | as-is | 0.452 [.420,.486] | **0.494** [.454,.534] | 0.474 [.437,.510] | +0.042 [+0.012, +0.071] | +0.093 / **-0.036** | +0.082 / **-0.068** |
| | deg s0 | 0.439 | **0.497** | 0.467 | +0.058 [+0.029, +0.086] | +0.100 / -0.004 | +0.080 / -0.047 |
| | deg s1 | 0.434 | **0.489** | 0.471 | +0.055 [+0.025, +0.084] | +0.109 / -0.022 | +0.087 / -0.037 |
| 2 | as-is | 0.433 [.403,.463] | 0.456 [.424,.493] | **0.499** [.462,.537] | +0.024 [-0.005, +0.055] | -0.003 / +0.053 | +0.072 / +0.059 |
| | deg s0 | 0.433 | 0.457 | **0.510** | +0.024 [-0.004, +0.056] | -0.004 / +0.057 | +0.078 / +0.075 |
| | deg s1 | 0.434 | 0.454 | **0.514** | +0.020 [-0.008, +0.050] | -0.007 / +0.050 | +0.090 / +0.066 |
| 3 | as-is | 0.404 [.372,.433] | 0.446 [.413,.478] | **0.452** [.420,.483] | +0.042 [+0.015, +0.073] | +0.014 / +0.067 | +0.034 / +0.060 |
| | deg s0 | 0.380 | 0.410 | 0.410 | +0.030 [+0.001, +0.062] | -0.005 / +0.060 | +0.024 / +0.035 |
| | deg s1 | 0.371 | 0.409 | 0.405 | +0.038 [+0.009, +0.069] | +0.041 / +0.035 | +0.045 / +0.024 |

(Game 3's primary rows reproduce the pilot's numbers exactly. Per-method intervals overlap in every row;
the paired intervals are the registered test.)

**Pooled over the three games** (equal-weight mean of per-game spellF1, game-stratified paired bootstrap,
1,000 draws, seed 0; all pooled intervals exclude 0):

| rule | ball | v1 refit - smooth50 | v1 transfer - smooth50 |
|---|---|---|---|
| primary | as-is | **+0.036** [+0.018, +0.054] | +0.046 [+0.028, +0.062] |
| | deg s0 / s1 | +0.037 [+0.020, +0.056] / +0.038 [+0.019, +0.055] | +0.045 / +0.050 |
| S1 | as-is | +0.050 [+0.034, +0.066] | +0.021 [+0.006, +0.038] |
| | deg s0 / s1 | +0.053 / +0.058 | +0.024 / +0.029 |
| S2 | as-is | +0.023 [+0.008, +0.038] | +0.032 [+0.016, +0.047] |
| | deg s0 / s1 | +0.027 / +0.025 | +0.038 / +0.038 |

**Pre-registered rule applied (v1 refit vs smooth50):**

| clause | result |
|---|---|
| (a) pooled primary as-is, interval excludes 0 | **pass** (+0.036, [+0.018, +0.054]) |
| (b) ahead in each game's primary as-is | **pass** (+0.042, +0.024, +0.042) |
| (c) same sign pooled under S1 and S2 | **pass** (+0.050, +0.023) |
| (d) same sign pooled under both degraded seeds | **pass** (+0.037, +0.038) |
| (e) same sign in both halves in >= 80% of the 27 cells | **FAIL: 14 / 27 = 52%** (Game 1: 4/9, Game 2: 3/9, Game 3: 7/9) |
| **verdict** | **no clear winner (leaning v1); clause (e)** |

The 13 failing cells: Game 1 primary x 3 conditions and S2 (as-is, seed 1); Game 2 primary x 3 and S2 x 3;
Game 3 primary and S2 under degraded seed 0. v1 transfer vs smooth50 (information only): the same
verdict, (e) 18/27 = 67%, with all nine failures in Game 1 half 2.

## 5. Where each method wins (component metrics, primary rule, whole game)

| game | ball | | macroF1 | alive/dead F1 | team acc., both alive | predicted possessions (labelled) |
|---|---|---|---:|---:|---:|---:|
| 1 | as-is | smooth50 | **0.789** | **0.903** | 0.868 | 479 (355) |
| | | v1 refit | 0.766 | 0.872 | **0.875** | 320 |
| | | v1 transfer | 0.754 | 0.865 | 0.865 | 389 |
| 2 | as-is | smooth50 | **0.814** | **0.913** | 0.886 | 464 (316) |
| | | v1 refit | 0.753 | 0.855 | 0.885 | 350 |
| | | v1 transfer | 0.769 | 0.871 | **0.890** | 380 |
| 3 | as-is | smooth50 | **0.801** | **0.930** | 0.863 | 557 (388) |
| | | v1 refit | 0.779 | 0.898 | **0.890** | 400 |
| | | v1 transfer | 0.785 | 0.905 | 0.888 | 458 |
| 3 | deg s0 | smooth50 | 0.745 | 0.879 | **0.865** | 517 (388) |
| | | v1 refit | 0.753 | 0.893 | 0.855 | 383 |
| | | v1 transfer | **0.766** | **0.906** | 0.857 | 434 |

(Games 1 and 2 degraded rows are nearly identical to as-is because their own visibility is already at the
target; see section 4.)

* **Dead ball:** smooth50 has the best alive/dead F1 and macroF1 in every game as-is (0.903 / 0.913 / 0.930),
  v1 refit trailing by 0.03-0.06, and only in Game 3 degraded does v1 overtake it. All three games have the
  blank-in-stoppages pattern, so this edge is most likely an artefact of the data, not evidence that
  smooth50's dead-ball rule is better in general.
* **Team call:** v1 refit minus smooth50 on both-alive accuracy is +0.007 / -0.001 / +0.027 as-is (games
  1 / 2 / 3); v1 transfer -0.003 / +0.004 / +0.025. Equal within noise, except Game 3. Not a robust v1 edge.
* **Possession structure** is the consistent difference: smooth50 over-fragments by 31-47% (464-557 vs
  316-388 labelled) while v1 refit lands within 10% of the labelled count in Games 1 and 3 and 11% above
  in Game 2.
* A hybrid (v1's structure plus smooth50-like dead-ball detection) is not supported or ruled out by these
  data: the dead-ball comparison is contaminated in all three games. Not built.

## 6. Do the label-free proxies still point the same way as spellF1?

On the primary labels (possessions per minute, % < 2 s, reversal rate within 3 s, D share), computed per
prediction (full table in `results.json`; each row of `results.csv` carries the proxies):

| game (as-is) | smooth50 | v1 refit | v1 transfer | labels |
|---|---|---|---|---|
| 1: poss/min, % < 2 s, reversals % | 5.06, 35.1, 40.1 | 3.38, 12.2, 20.1 | 4.11, 19.5, 27.0 | 3.75, 19.7, 24.5 |
| 2 | 4.97, 36.2, 36.4 | 3.75, 14.9, 13.8 | 4.07, 18.7, 24.4 | 3.38, 21.5, 17.8 |
| 3 | 5.86, 37.7, 40.0 | 4.20, 15.0, 22.8 | 4.81, 23.1, 35.9 | 4.08, 24.5, 23.0 |

* **v1 vs smooth50: yes, they point the same way everywhere.** In all 9 game x condition combinations v1
  has fewer short possessions and a lower reversal rate, and v1 is ahead on whole-game spellF1 in all 27
  cells. At this coarse level the v2/v3 proxies are validated.
* **Where they fail:** (i) **between v1 variants.** Refit always has the "better" proxies, yet transfer has
  the higher spellF1 in Game 2 (0.499 vs 0.456) and refit in Game 1 (0.494 vs 0.474); the proxies do not
  rank closely matched models. (ii) **Per half:** the proxies say nothing about the half-level reversals
  of sign that sank clause (e). (iii) **Overshoot:** v1 refit's % < 2 s (12-15%) and its D share
  (38.5 / 39.3 / 30.1 vs labelled 34.1 / 33.0 / 26.7) fall on the wrong side of the labels' own values; a
  proxy that rewards "fewer short possessions" would keep rewarding a model past the point where it merges
  real short possessions.

## 7. How to add a method and run the harness

```
python -m possession.harness.run --methods smooth50,v1_refit,v1_transfer          # everything registered
python -m possession.harness.run --plugin my_pkg.my_module --methods smooth50,my_method
python -m possession.harness.run --games game1,game2 --methods smooth50,my_method --reference smooth50
```
A method is a function from a game context to per-frame codes, registered from any module, with no edit
to the harness (details and rules in `possession/harness/api.py`):

```python
# my_pkg/my_module.py
import numpy as np
from possession.harness.api import register

@register("my_method")
def my_method(ctx):                 # ctx: name, fps, pitch, players (N,S,2) m, ball (N,2) m (the ball
    codes = np.full(ctx.n_frames, 3, dtype=np.int8)         # condition already applied), pspeed, team (S,),
    for half, a, b in ctx.blocks:   # blocks = graded play intervals, one half at a time, no state across
        codes[a:b + 1] = 0          # ... your per-half logic here; 0 H, 1 A, 2 D, 3 X
    return codes
```
`possession/harness/example_plugin.py` is a runnable trivial example (`always_home`, spellF1 = 0).
Every run (i) re-runs the adapter validation on the provided match and **stops with an error** if smooth50
stops matching its repo file or v1 stops reproducing md5 `83b587d7...`, (ii) scores every game x rule
(primary, S1, S2) x ball condition (as-is, degraded s0/s1) x half with the organizers' functions,
(iii) writes `analysis/harness/results.json`, `results.csv`, labels, predictions and md5s, and (iv) applies
the pre-registered decision rule to every method against the reference (default smooth50). A method sees
tracking and the graded half blocks only, never labels.

## 8. Limits

* **Proxy labels:** event-derived with rules I wrote; not the competition's corrected-tracking ground
  truth. Three rules bracket the main ambiguity, but a choice common to all three (for example, ignoring
  CARRY everywhere) is not tested.
* **Three games from one provider's public sample,** all with the same ball-blank-in-stoppages property and
  players always complete. A real domain shift from the provided match (ball visible in about two thirds of
  its dead frames, incomplete players), and no game here can restore that, so **smooth50's dead-ball
  results are probably optimistic and the alive/dead comparison is not transferable.**
* **Half-level comparisons** use about 160-230 labelled possessions each, with no interval; the three
  sign failures per game may be noise or a real half-specific effect (Game 1 half 2 is the largest: -0.036 for
  v1 refit and -0.068 for v1 transfer, primary as-is). Not examined further.
* **Degraded condition** does little in Games 1 and 2 (their own visibility is near the target), so the
  as-is vs degraded comparison is informative mainly for Game 3.
* **Unverified:** whether the tracking is automatic or corrected, the cause of the blank stoppage ball,
  and the exact semantics of event frames for every event type (checked for PASS and SHOT only).
* **Decision-rule choices:** the equal-weight pooling, the 80% threshold and the strict reading of
  clause (e) (both halves must have the claimed sign) were set before scoring. A looser reading was not
  computed, and I did not pick the reading after seeing the cells.

## 9. Reproducibility

Two independent full runs (`--out analysis/harness` and a second run to a separate folder, removed after the comparison): all **36** label and
prediction files byte-identical (md5), results, pooled statistics and decisions identical, Game 3 primary
labels and all nine Game 3 predictions equal to the pilot's. md5 (both runs):

| labels | primary | S1 | S2 |
|---|---|---|---|
| game1 | dbc9e2ae3f746bf63fc9c508ee74b58b | 386140b7e081db58d876f907ac182879 | 40a69744db217d531d496b86e3c5ad6a |
| game2 | 24aafc03cccc4298d1374b37f8044fc5 | dd12ed8416e8b755e11da168224343b4 | 54dc477c1efb577433c93a27c2c9795d |
| game3 | 1a5e88388da10430d09c86b1dc55e922 | 04b75493531ab956a01717fcfb2189be | c71a6a0723d371b379f7c48546cf03e3 |

| predictions | as-is | degraded s0 | degraded s1 |
|---|---|---|---|
| game1 smooth50 | 63f7fdaa8332f2067614b226ab12a147 | 67d3bf1ff2665840e2ae64d4b087037c | 33a5c087b004306d4b7a073b61c4bd10 |
| game1 v1 refit | 08abf1f72b415b4fe55fe61cce6a7aef | d70ba8b5ddc17245762cc49aa7f96584 | ca8274cd18177aea9552890d4ace7ad7 |
| game1 v1 transfer | 0969c12a619bd52dcb58fbf97114aca1 | e767596c3710aa7208ed0a8aee8255a8 | 1e9a60dff7d2b89b72e9349b71c96e40 |
| game2 smooth50 | ce88cfc372bf81bd52e7c36e133854ae | d84d379c78d54f37a0856e42e4441582 | 5fa0137d1fd43356711cb5a31ec9d3bd |
| game2 v1 refit | c947980dd7023078a49ce12f79899e36 | 1739b9822c90ca96e202779a8ac869d1 | 855492de6114db9a1ae04e879bd7e3e8 |
| game2 v1 transfer | 6050003880c1f71499f1f223a26ae7e3 | bcba5d5b3640e2c12e65073c820c8b42 | 73e2bb524049b08af0c93ba9deaf0a73 |
| game3 smooth50 | 4c8dd092117427bb03d938435ce34a29 | 7be8c20014e83a042108217d5ef764a5 | 024021268b7ba722310f7c6955c9bce6 |
| game3 v1 refit | 3a8eb5c8d532268c4b2ead523a854c86 | 6211f97b925d522cb241ba061b214643 | 27e25f006b7b667d49b2aa29488676a7 |
| game3 v1 transfer | aa40f550f03f7cae9500eb24d042fe14 | d29fd7a8b2db75620b4472e1f6559ed2 | bef581b2ab7d5c36bf4806a011c3ad42 |

Housekeeping: `possession/harness/` is new in the repository; outputs are in
`analysis/harness/` (per-frame labels and predictions derived from the sample games stay untracked and are regenerated by the commands above); sample data in the gitignored
`data/other_games/`. No existing file was modified, `.gitignore` shows modified from before the session
and was not touched.
