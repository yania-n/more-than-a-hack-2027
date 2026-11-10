# Summary of the analysis work (v1, v2, v3, pilot, harness)

Plain-language summary of everything in `analysis/`, put together from the reports in each subfolder.
For the full details, numbers and methods, see each folder's `REPORT.md` and `PREREGISTRATION.md`.

## The task in one line

The model watches tracking data from one football match (FC Barcelona vs Athletic Club, LaLiga 2024-25,
matchday 2) and decides, moment by moment, whether **home has the ball, away has it, or it's dead**
(out of play, a stoppage).

## Data used

* **v1, v2, v3** use only the **organizers' data**: the tactical-camera tracking (player and ball
  positions, 199,319 frames) and the Smart Tagging events that come with it. The broadcast camera and the
  video were not used.
* **pilot_game3 and harness** also use **Metrica Sports' free sample data** (`data/other_games/metrica_sample`):
  **3 full matches** (Sample Games 1, 2, 3). Games 1 and 2 are CSV files with anonymised teams; Game 3 is
  EPTS tracking plus JSON events. They were used as a test bench where the correct answers can be worked
  out. No submission file was trained on them.
  * The rules allow data from other games. Metrica's README asks for responsible use and credit to the
    source; the data is free to use with that attribution, and we credit Metrica Sports (sample-data
    repository) here and in the technical document.

---

## The organizers' baseline (smooth50)

This is the starter code given to everyone (`starter/baseline.py`), not our own model:

1. Every frame, find the player closest to the ball and give possession to their team.
2. If the ball isn't visible, call it dead ball.
3. Smooth the result with a majority vote over 50 frames (2 seconds).

It only uses distance to the ball, and it never marks the ball as dead when it's off the pitch.

---

## v1: "use several clues, and remember possessions last a while"

Our own model (`possession/`), built to fix the baseline's flickering and poor dead-ball detection.
It's a type of model called an HMM: think of a detective who sees clues every 0.4 seconds and also
knows the usual pattern of a game.

**Clues used (per 0.4 s slice):**
* **Who's closer to the ball, and by how much.** A big gap is strong evidence, a tiny gap weak.
* **Who's been hanging around the ball.** A team that has stayed close is more likely to have it.
* **Ball speed.** If the ball is faster than any player can run, it's a pass or a shot, so "who's
  closest" is ignored at that moment.
* **Player speed.** When everyone slows to walking pace, play has probably stopped.
* **Ball off the pitch:** a clear dead-ball sign.
* **An upcoming corner or free kick** from the match's event tags (players stand around before one).

**The "usual pattern" part:** possessions and stoppages tend to last several seconds, so switching
team needs enough evidence. The model learns how much to trust each clue, and how often switches
happen, from the match data itself, without seeing the correct answers.

**Results on the provided match:**
* **Much better at dead ball** than the baseline, so the best overall score (macroF1 0.75 vs 0.62).
* **Only slightly less jumpy:** 27% of possessions under 2 s vs 31%. It still predicts 34
  possessions where there were really 17 in the test window.
* **More quick back-and-forth** (team A, then B, then A within 3 s): 37% vs 30%.
* **Restart timing is off:** it knows there's a stoppage but ends it at the wrong moment.
* **Gives Barcelona about 66% of the ball.** Later checks (below) showed this is real data, not a bug.

**v1 is still the best model.**

---

## v2: two attempts to make v1 less jumpy

### v2a: "the model is too easily convinced"

**Idea:** v1 treats each 0.4 s slice as fresh, separate evidence, when neighbouring slices say almost
the same thing. That's like hearing one rumour from five people who all heard it from the same source
and counting it as five confirmations. So v2a measured how long the evidence repeats itself (about
5 seconds) and made the model count it less: about 1/12.

**Result: MIXED (it overcorrected).** The model barely believed anything anymore and almost stopped
switching teams: **1 direct team-to-team change in the whole match** (v1 has 419). It went through
"dead ball" whenever unsure (dead-ball share 49% vs 39%), and possessions fell to 2 per minute.

**Finding:** the evidence isn't simply repeating itself. Player-to-ball distance just changes slowly,
and discounting it threw away real information.

### v2b: "catch the kick, and rethink the 'ball in the air' rule"

* **Kick detection:** when a player touches the ball it should suddenly change direction or speed.
  But in this tracking a freely rolling ball changes speed just as much, because the tracker smooths
  and jumps. Kicks couldn't be told apart: **only 15 found in the whole match**, and the feature had
  no effect.
* **Ball-in-the-air rule:** v1 ignores "who's closest" for about 40% of moments because the ball is
  fast. Was the cutoff too low? No: the tracking is accurate, so the fast balls really are fast. The
  rule was kept, and only impossible speeds (glitches, above 35 m/s) were thrown out.

**Result: NOT HELPING.** The output was essentially the same as v1.

### Mirror test (bug check)

With home and away swapped, Barcelona's share stayed at exactly 65.9%. So the home lean comes from
the data, not from a bug in the model.

### Tried before v2: minimum possession length

Forcing possessions to last a minimum time made the held-out likelihood worse, so it was dropped.

---

## v3: "a dribbled ball moves with the dribbler"

**Idea:** instead of looking for a sudden kick, look for something steady. A player who has the ball
runs with it, so the ball goes in the same direction and at the same speed as them. Over a 1.6 s
window, check whether the ball stayed near one player and moved with them.

To make sure it's not a coincidence, real pairs were compared with fake ones (the ball against a random
teammate, or against the same player 10 seconds later).

**Results:**
* **The clue is real and strong.** Real pairs matched far better than the fakes (median direction
  agreement 0.96 vs -0.04 and 0.43). The model learned that "home is carrying" is about 45 times more
  likely when home really has the ball.
* **But it fired far too rarely.** The rules were strict: the ball had to stay close to the same team
  for the whole 1.6 seconds, and the match had to be better than 99% of the fake pairings. Only
  about **1% of the match** qualified (2% was the minimum needed).
* **The output was byte-identical to v1. Verdict: NOT HELPING.** The work stopped there, as planned,
  without loosening the rules after seeing the result.

**Home lean check:** the Smart Tagging data gives Barcelona about 59-62% of attacking time, which
supports a real lean, slightly below v1's 66%.

---

## Comparison of all versions (provided match)

| | **Baseline** (organizers) | **v1** | **v2a** (trust evidence less) | **v2b** (kick detection) | **v3** (ball moves with player) |
|---|---|---|---|---|---|
| **Idea** | Whoever's closest has it | Several clues, and possessions last a while | v1, but trusts each slice less | v1 plus kicks and a stricter "ball in the air" rule | v1 plus "does the ball move with the nearest player?" |
| **Possessions found (whole match)** | 594 | 563 | 213 | 563 | 563 |
| **Tiny possessions (< 2 s)** | 31% | 27% | 9% | 27% | 27% |
| **Quick back-and-forth** | 30% | 37% | 0%* | 37% | 37% |
| **Direct team-to-team changes** | 461 | 419 | **1** | 419 | 419 |
| **Time marked as dead ball** | 32% | 39% | 49% | 39% | 39% |
| **Ball off pitch marked dead** | 0% | 54% | 64% | 54% | 54% |
| **Barcelona's share of the ball** | 57% | 66% | 75% | 66% | 66% |
| **Overall score on the small test set (macroF1)** | 0.62 | **0.75** | 0.69 | 0.75 | 0.75 |
| **Possession-match score on the small test set (spellF1)** | 0.33 | 0.28 | 0.15 | 0.28 | 0.28 |
| **Verdict** | Starting point | **Best so far** | Mixed: overcorrected | Not helping | Not helping |
| **Why** | Never spots dead ball | Good at dead ball, still too jumpy | Almost stopped switching teams | Kicks can't be seen in this data (15 found) | Real clue but fired on ~1% of the match, so the output equals v1 |

\* 0% only because there was a single team-to-team change in the whole match; meaningless.

On the small test set: macroF1 checks how often each moment is labelled correctly (home, away or
dead); spellF1 checks how well whole possessions line up with the real ones. The test window has only
**17 real possessions**, so it can catch bugs but can't reliably rank the versions.

---

## Testing on other games: pilot_game3 and harness

**Question:** is v1 really better than the **organizers' baseline (smooth50)**? The provided match only gives
5 minutes with correct answers, which is too little, so v1 and the baseline were tested on Metrica's
3 sample games, where the answers can be worked out.

**Where the "correct answers" came from:** the sample games have hand-tagged events (passes, shots,
ball out, fouls, ...). A script turned them into possession labels ("a pass by Team A means Team A has
the ball", "ball out means dead ball"). Since it's unclear what counts as possession, three rule
versions were used: **normal, stricter and looser**. To make the samples look more like the provided match,
the ball was also hidden in extra places and some noise was added (**degraded** conditions, 2 seeds).

Only the baseline and v1 were tested on these games, not v2 or v3 (which gave the same output as v1,
or worse, on the provided match).

### pilot_game3: first try, Game 3 only

* v1 was ahead in **all 9 setups** (3 rules x 3 ball conditions) by about 2-5 points of spellF1, beyond
  chance in 8 of 9.
* **Not called a clear win:** the pre-set rule also required winning both halves, and in 3 setups v1
  lost one half by a tiny amount. Verdict: **no clear winner, leaning v1**.

### harness: all 3 games, plus a reusable testing tool

Same test on Games 1, 2 and 3, plus a tool so any future model can be plugged in and tested the same
way. Every run first checks that it still reproduces v1 and the baseline exactly on the provided match. Game 3
was re-run as a check and gave exactly the pilot's results.

| Game | Baseline score (spellF1) | v1 score | v1 ahead by |
|---|---|---|---|
| Game 1 | 0.45 | 0.49 | +0.04 |
| Game 2 | 0.43 | 0.46 | +0.02 |
| Game 3 | 0.40 | 0.45 | +0.04 |
| **All 3 combined** | | | **+0.036** (beyond chance) |

* **v1 beat the baseline in all 27 setups** (3 games x 3 rules x 3 ball conditions).
* **Why v1 wins:** it finds about the right number of possessions. The baseline finds 30-45% too many
  because it chops them up.
* **Team call (who has it):** about equal.
* **Still "no clear winner, leaning v1":** the pre-set rule required winning both halves in at least
  80% of setups; v1 managed 52% (14 of 27). Each game has one half where the baseline edges slightly ahead.
* **The quick checks used in v2 and v3** (fewer tiny possessions, fewer back-and-forth flips) do go
  with a better real score for big differences like v1 vs the baseline, but can't tell apart two
  close models.

### Important caveat on dead ball

In all 3 Metrica games, the ball disappears from the tracking almost exactly when play stops
(visible on only 8%, 0.2% and 0.2% of dead-ball frames). The baseline says "no ball = dead ball", so it
gets those moments right for free and looks better at dead ball there. The provided match isn't like that
(the ball is present in about two thirds of its stoppages), so **the dead-ball comparison doesn't carry over**.

---

## Bottom line

* **v1 is the best model so far.** On real football with known answers, it's consistently better
  than the organizers' baseline at finding possessions, mainly because it doesn't chop them into
  pieces. It just doesn't pass the strict half-by-half rule for a "clear win".
* **Every attempt since v1 to make it less jumpy failed:** trusting the evidence less (v2a),
  detecting kicks (v2b), and "ball moves with the player" (v3).
* **Most promising next steps** (from the reports):
  1. Redesign v3's "moves with the player" clue with looser rules (no "close on every frame"
     requirement), pre-registered as a new design.
  2. Tackle the **41% of frames where the ball is missing**, which is where most hand-overs get lost.
  3. Consider **supervised training on other games** (Metrica, PFF, SkillCorner, DFL) after checking
     licences and planning for the differences between their data and this match.

---

## Update: baselines, and a rule-compliant v1

The organizers' latest rules say anything fitted or tuned must use external data only. The shipped v1
was fitted on the provided match, so it cannot be the final model. The later folders address this.

* **`harness_baselines/`** runs all four organizer baselines against v1 on the three sample games. The
  best baseline window is smooth50 everywhere. v1 has the highest spellF1; the baselines keep an edge on
  macroF1 and dead-ball F1, helped by the blank ball in stoppages.
* **`logo_v1/`** refits every v1 parameter on two sample games and applies it, frozen, to the third
  (leave-one-game-out). spellF1 is 0.474 against 0.430 for smooth50. It matches the non-compliant fits, so
  compliance costs nothing measurable. `PROVENANCE.md` records the source of every constant.
* **`logo_v1_followup/`** picks the number of player-speed bins (24) on external data using a label-free
  criterion, and runs the frozen model on the provided match as input only. No output proxy looks wrong;
  the dwell and heading features are the most provider-dependent.

Caveats that still apply: the labels are proxies, the sample games have a blank ball in stoppages, and
there are only three games. The registered verdict against smooth50 is "no clear winner, leaning v1".
