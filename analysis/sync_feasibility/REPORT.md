# Would syncing the broadcast fill the tactical ball gaps?

**Short answer: rarely. Drop the idea.** The sync itself works well. But the broadcast has the ball
on only **9.0%** of the graded tactical frames where the ball is missing. Ball coverage would go
from **59.3% to 63.0%** of graded frames.

Reproduce: `.venv/Scripts/python.exe analysis/sync_feasibility/sync_check.py` (about 17 min, plus
about 90 s on the first run to parse the ATD through kloppy). It is deterministic: two runs gave
an identical `results.json`. Every number below is in `results.json`. No ground truth was read.
The alignment is found by code, with no frame numbers or offsets of this game in the script.

## 1. Data

| | tactical | broadcast |
|---|---|---|
| frames | 199,319 | 164,488 |
| ball present | 56.9% | 50.5% |
| players tracked per frame | 19.0 | 11.5 (11.9 where any) |
| track slots (home / away) | 46 (24 / 22) | 51 (26 / 25) |

- **Teams.** kloppy exposes them as `metadata.teams[i].players`. Each player's `player_id` is the
  slot number, so the `{id}_x` columns map to a team directly. Barcelona is `teams[0]` in both
  files.
- **The broadcast sees only the players in shot.** So the cost is one-sided: each broadcast player
  is compared with the nearest tactical player of the same team.
- **Orientation.** The 8 longest segments were aligned both plain and mirrored (x → 1−x,
  y → 1−y). The median cost was 0.82 m plain and 6.88 m mirrored, so the two sources share an
  orientation and nothing is flipped. The centroid gap (home x − away x) agrees: it is negative
  early and positive late in both sources.

## 2. Broadcast shots

The broadcast homography is valid on 65.8% of frames, and 65.2% once fits with
reprojection error ≥ 10 are dropped. A new segment starts at:
- any invalid stretch;
- a jump of more than 3 m/frame in the camera's look-at point (the pitch point under the image
  centre). Inside a shot it moves less than 0.6 m/frame at p99;
- a step of more than 3 in reprojection error.

This gives **161 segments**, of which **120 are at least 2 s** long, totalling 71.3 min. Lengths:
median 23 s, p10 4.7 s, p90 82 s, max 167 s. See `segment_lengths.png`.

## 3. Alignment

**Cost of a frame pair, in metres.** Each broadcast player is matched to the nearest tactical
player of the same team, with distances capped at 10 m. The ball counts as one more point when
the broadcast has it: its distance to the tactical ball, or a 5 m penalty if tactical has no ball.

**Search.** For each segment:
1. Coarse search: up to 40 broadcast frames (at least 1 s apart) against every 5th tactical frame
   over the whole match.
2. Refine the 5 best minima (at least 2 s apart) at frame resolution.
3. Runner-up = the best candidate at least 2 s away from the winner.
4. Constant-offset check: refine each half of the segment on its own. "Drift" is the difference
   between the two halves' offsets.

**Acceptance.** A segment is accepted if:
- cost ≤ 2 m;
- runner-up / best ≥ 1.5;
- |drift| ≤ 3 frames;
- its offset is within 2 s of the median offset of the 5 accepted-candidate neighbours on at
  least one side.

A segment more than 2 s behind both neighbourhoods is flagged as a **replay**.

| status | segments |
|---|---|
| accepted | **89** |
| replay | 3 |
| high cost (pre-match, halftime, close-ups) | 16 |
| ambiguous (margin < 1.5) | 6 |
| drift | 4 |
| no usable players | 2 |

**What the accepted segments look like:**
- Median cost 0.93 m; the worst is 1.66 m.
- Median margin (runner-up / best) is about 4×.
- Every accepted segment has |drift| ≤ 3 frames.
- They sit on **two live offsets**: tactical − broadcast is about 4014 frames in the first half
  and about 26920 in the second, each within ±2 frames (1 outlier at −5).

So the broadcast is a constant-delay recording within each half, with about 15 min of halftime
cut. The 3 replays sit 1–2 min behind live, with large margins (2.7–8.4×), as expected for
replays. See `offsets.png`.

## 4. Validation (no ground truth)

These are aligned frames where both sources have the ball (71,401 frames).

| ball disagreement | value |
|---|---|
| median | **0.78 m** |
| p75 / p90 | 2.18 m / 6.07 m |
| < 1 m / < 2 m | 56.9% / 73.3% |
| > 5 m | 12.1% |

The median per segment is 0.84 m (p90 1.8 m). The sync is good, and the long tail is the ball
trackers disagreeing, not a wrong offset. The first panel of `overlays.png` shows this: every
player matches to within centimetres, but one source's ball is 25 m away from the other's.

The ball is part of the alignment cost, but it is 1 point against about 12 players, and the offset
is a single constant per segment. So it cannot pull individual frames into agreement.

## 5. The answer (graded frames: 11185–90651 and 110808–190197)

| | all graded | 1st half | 2nd half |
|---|---|---|---|
| tactical ball present | 59.3% | 59.3% | 59.3% |
| covered by an accepted broadcast frame | 60.9% | 61.4% | 60.3% |
| of tactical-ball-**missing** frames: covered | 31.0% | 31.1% | 30.9% |
| **of tactical-ball-missing frames: broadcast has the ball** | **9.0%** | **9.1%** | **9.0%** |
| ball coverage, tactical → tactical + broadcast | **59.3% → 63.0%** | 59.3% → 63.1% | 59.3% → 62.9% |

**By length of the tactical gap.** "Filled" is the share of gap frames where the broadcast has the
ball. "Gaps touched" is the share of gaps with at least one filled frame.

| gap length (frames) | gaps | frames | covered | filled | gaps touched |
|---|---|---|---|---|---|
| 1–5 | 14 | 31 | 94% | 68% | 79% |
| 6–25 | 3 | 44 | 27% | 27% | 33% |
| 26–125 | 1 | 122 | 0% | 0% | 0% |
| >125 | 132 | 64,446 | 31% | 9.0% | 57% |

The tactical ball is not lost in scattered dropouts: **99.7% of the missing frames are in gaps
longer than 5 s** (median gap 10.7 s, longest 221 s). Short dropouts barely exist in this ATD, so
the one bucket where the broadcast does well (1–5 frames) is worth 31 frames for the whole match.

**Why so low.** The two failures stack:
1. **The broadcast is off the pitch when tactical loses the ball.** It covers 61% of graded frames
   overall but only 31% of the ball-missing ones. These stretches seem to be when the director
   shows replays, close-ups and crowd shots. This is an inference: I didn't check it against
   Smart Tagging or the video.
2. **When it is on the pitch, its tracker loses the ball too.** On covered frames the broadcast
   has the ball **93%** of the time when tactical has it, but only **29%** when tactical doesn't.
   The two trackers fail on the same situations.

## Verdict

**Not worth building as a gap-filler.** The alignment is the easy part. It is fully automatic,
frame-accurate (±1–2 frames), catches replays, and the balls agree to a median of 0.78 m, so a
sync module would work if it were ever needed. But it buys only +3.7 percentage points of ball
coverage (59.3% → 63.0%), filling 9% of missing frames. Three things make it worse:
- the fills land inside long gaps (median 10.7 s), where a few seconds of extra ball rarely
  settle who had possession;
- when both sources have the ball, they disagree by more than 5 m 12% of the time, so some
  fills would be wrong, with nothing to tell which;
- running it costs a 17-minute alignment pass.

The missing ball is a situational problem, not a camera-view problem, so a second camera of the
same scene doesn't solve it. Effort is better spent on reasoning through the gaps: player
configuration, Smart Tagging, possession continuity.

## Files (all gitignored, under `analysis/`)

- `sync_check.py`: the whole analysis.
- `results.json`: every number, plus per-segment offsets, costs and statuses.
- `segment_lengths.png`, `offsets.png`, `ball_disagreement.png`, `overlays.png`: the plots.
- `run.log`: output of the last run.
- `cache/`: ATD parsed to `.npz`. This is derived tracking data and must never be committed.
