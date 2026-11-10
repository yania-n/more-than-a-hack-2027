# Provenance of every quantity v1 fits or fixes

Written 2026-11-10, before any leave-one-game-out (LOGO) run. Source: `possession/{hmm,features,run,data}.py`,
`possession/pilot/adapters.py`, `analysis/hmm_v1/model.json` (the shipped v1 fit), `analysis/hmm_v1/REPORT.md`.

Rules applied (organisers' latest, which override RULES.md/FAQ.md): no checking output against the video; no hand
labels or human-produced data on the provided game; no uploading provided data to AI services; no training, fitting or
calibrating on the provided ground truth or video; anything that needs tuning is tuned on external data only. Our strict
reading: **v1 must not be fitted on the provided match at all** (not unsupervised EM on its tracking, not constants
derived from it). The provided match is only an input to a frozen model. The 5-minute public window is never used.

"Allowed?" below is judged under that strict reading. "Shipped v1" is the model behind `submissions/hmm_v1.csv`
(md5 83b587d7...), which **was fitted on the provided match** (see section A). That is exactly what this task replaces.

## A. Fitted from data in shipped v1 (all fitted on the PROVIDED match's tracking, no labels)

| # | Quantity | Shipped value | Where it came from | Allowed under the strict reading? | In `v1_logo` |
|---|---|---|---|---|---|
| A1 | **Control radius** (`radius`) | 1.914 m | median over graded, ball-visible frames of the distance from the ball to the nearest player (either team), provided match | **No** (a constant derived from the provided match) | recomputed as the same median over the pooled graded, ball-visible frames of the two TRAINING games |
| A2 | **Carry speed** (`carry`) | 6.440 m/s | 99th percentile of player speeds over graded frames (all slots pooled), provided match | **No** | recomputed as the same percentile over the pooled graded frames of the two training games |
| A3 | **Bin edges, gap** (4 \|g\| bins) | 1.824, 4.412, 8.545 m | percentiles 25/50/75 of block-median \|gap\|, provided match | **No** | percentiles of the two training games' pooled blocks |
| A4 | **Bin edges, dwell** (3 bins) | 15, 37 frames | percentiles 33/67 of block \|dwell\| > 0, provided match | **No** | same, pooled training blocks |
| A5 | **Bin edges, ball speed** (5 bins) | 1.969, 3.968, 6.479, 10.803 m/s | quintiles of block ball speed, provided match | **No** | same, pooled training blocks |
| A6 | **Bin edges, heading change** (4 bins) | 0.876, 2.739, 7.651 deg | quartiles, provided match | **No** | same, pooled training blocks |
| A7 | **Bin edges, player speed** (12 bins) | 0.661 ... 3.253 m/s (11 edges) | twelfths of block mean player speed, provided match | **No** | same, pooled training blocks |
| A8 | **Emission tables** (7 features x 3 states) | `analysis/hmm_v1/model.json` | Baum-Welch (EM) on the provided match's two halves | **No** | Baum-Welch on the training games' halves (4 sequences, shared parameters) |
| A9 | **Transition matrix** (3x3) | stay H 0.935, A 0.908, D 0.975 | same EM, MAP with a Dirichlet prior centred on A0 | **No** | same EM on the training games |
| A10 | **Number of EM iterations** | 23 (converged) | stopping rule: change in log-likelihood < 1e-7 per step, cap 300 | n/a (a rule, not a value). The count is an outcome of the fit | outcome of each LOGO fit; rule unchanged |

## B. Fixed by hand in the code (not fitted). Source of each choice

| # | Quantity | Value | Source of the choice | Allowed? | In `v1_logo` |
|---|---|---|---|---|---|
| B1 | `BLOCK` | 10 frames (0.4 s) | football reasoning (one touch cycle; avoid 25x evidence over-count); no data | Yes | unchanged |
| B2 | `SPEED_SMOOTH` | 25 frames | removes step-frequency oscillation; reasoning | Yes | unchanged |
| B3 | `FLIGHT_W` | 5 frames | reasoning | Yes | unchanged |
| B4 | `HEADING_MIN_MOVE` | 0.5 m | reasoning (above walking pace and tracker noise) | Yes | unchanged |
| B5 | `OUTSIDE_MARGIN` | 0.5 m | reasoning (tracker noise on lines) | Yes | unchanged |
| B6 | `SETPIECE_LEAD` | 10 s | **read off the unlabelled mean-speed profile around the provided match's Smart Tagging set-piece starts** | **No, as a derived constant** (human choice from provided-match data) | **Inert in LOGO.** The sample games have no Smart Tagging, so the set-piece feature is set to missing (-1, marginalised) in training and inference, exactly as `v1_refit`/`v1_transfer` already do. The 10 s never enters any `v1_logo` number. |
| B7 | `RESTART_TYPES` | list of 6 Smart Tagging types | from the provided Smart Tagging vocabulary | Yes (a vocabulary list), inert as above | unchanged, inert |
| B8 | `N_G_BINS, N_DWELL_BINS, N_BSPEED, N_HEAD` | 4, 3, 5, 4 | reasoning | Yes | unchanged |
| B9 | **`N_PSPEED`** | 12 | **chosen from the shape of the learned player-speed emission on the provided match** ("with 6 bins the cutoff was pinned to a bin edge"; sensitivity 6/12/24 reported) | **Not re-derivable without a human decision, and it was influenced by the provided match** | **Inherited unchanged and flagged.** It is a structural hyper-parameter (a number of bins); there is no data-only rule that re-derives it. Not tuned on the sample games either. See Caveats in the report |
| B10 | `PRIOR_DWELL_S` | (10, 10, 10) s | football reasoning ("several to a few tens of seconds"); only initialises A0 | Yes | unchanged |
| B11 | `rho` in `init_params` | 0.5 | weak tilt that anchors home/away and dead-ball start; reasoning | Yes | unchanged |
| B12 | `dead_tilt` per feature | -1 (ball speed, player speed), +1 (outside, set-piece) | which end of a feature is typical of a dead ball; football reasoning | Yes | unchanged |
| B13 | `prior_strength` (transition Dirichlet) | 10 pseudo-transitions/row | negligible vs thousands of steps; only prevents zeros | Yes | unchanged |
| B14 | `alpha` (emission Laplace pseudo-count) | 1.0 | prevents zero probabilities | Yes | unchanged |
| B15 | `tol`, `max_iter` | 1e-7 per step, 300 | convergence rule | Yes | unchanged |
| B16 | `pi` | fixed uniform | nothing to learn it from (two halves) | Yes | unchanged |
| B17 | Initial emissions | pooled marginals of the data being fitted, +1 pseudo-count, tilted by rho | label-free | Yes | marginals now come from the training games |
| B18 | Viterbi tie-break | lowest state index | deterministic | Yes | unchanged |
| B19 | Mirror symmetry (H/A emission mirrored; D symmetric; H/A share "alive" for unsigned features) | structural | design | Yes | unchanged |
| B20 | Player speed source | derived from positions, +-8 frames, in the sample games | harness convention (pilot PREREGISTRATION s.4); chosen to match the provided ATD speed column | Yes for the sample games (this is feature construction on the sample games, the provided column is not consulted at inference); it was chosen by comparing against the provided file, a design-time choice already made for all harness methods | unchanged |

## C. Inputs that are not parameters but come from outside the tracking

| # | Item | Source | Treatment in LOGO |
|---|---|---|---|
| C1 | Held-out game's graded blocks (`ctx.blocks`) | event-derived play intervals (first controlling event to end of half) of the held-out game; the analogue of the provided match's published graded blocks | used as **inference input only**, exactly as every other harness method; this is the common harness convention so the six methods are comparable. No label value is used |
| C2 | Training games' intervals | **tracking-file period boundaries only** (the `Period` column / EPTS metadata) | **conservative choice:** training does NOT use the label-derived blocks, so no event-derived quantity of any kind enters a fit. The cost: training sequences include roughly 0-60 s of pre-kick-off / post-whistle frames per half (see report) |
| C3 | Degraded-ball condition (`degraded_seed0/1`) | gap-length distribution and visible share of the **provided match's ball channel** (an unlabelled aggregate: `reference_from_provided`, `adapters.graded_runs`) | harness-wide test-condition simulation, identical for all methods. The training games are degraded the same way for the degraded condition. It sets how much ball is missing; it does not fit any v1 parameter. Flagged because it reads the provided tracking's ball visibility |
| C4 | Labels (primary, S1, S2) of any sample game | event data | **never read by any fit.** Used only for scoring held-out predictions |

## D. Sample-data licence (Step 0.3)

Repository `metrica-sports/sample-data`: **there is no `LICENSE` file** (GitHub contents listing: `README.md`, `data`,
`documentation`; the repository-license API returns 404). The only terms are the README's "Legal stuff" section, quoted:

* "Please be responsible with the use of this data."
* "If you use it for anything public, please aknowledge the source."

The README also states the intended use: "to allow potential clients to check out this data ... [and] to provide some
sample data to play around with to the broader football analytics community". The data is anonymised (no players, teams
or competition names). So: no stated non-commercial or no-derivatives clause, but **also no explicit licence grant**;
what is allowed beyond "play around" and "be responsible" is not specified, so I do not assume more. Consequences kept in
this work: (1) the raw data stays in the gitignored `data/other_games/metrica_sample/` and is never committed or uploaded;
(2) this repo commits only aggregate results and frozen fitted parameters (bin edges, probabilities), not tracking or event
rows; (3) the source is acknowledged in every report; (4) a derived parameter file (`frozen_params.json`) is a small set of
fitted numbers, not a reproduction of the data, and the team has since taken the data as free to use with attribution, so this is no longer an open question.

**Note on B9 (added later):** `N_PSPEED` is re-derivable on external data after all. `analysis/logo_v1_followup/` chose 24 bins by
held-out likelihood on the sample games; the row above describes the shipped v1 and the registered `v1_logo` run (12 bins).
