# B1: feature shift of the provided match against the sample games, over the FROZEN bins

Bins = frozen radius / carry / edges of `analysis\logo_v1_followup\frozen_params_np24.json` (24 player-speed bins). Training = Sample Games 1-3 as-is (Metrica Sports sample data), provided match = its tracking as the shipped v1 reads it. TV = total variation between observed-category distributions; the scale is each sample game vs the pooled other two. Missing share = blocks whose feature is absent (ball absent, ball in flight, heading undefined...).

| feature | TV provided vs sample | largest sample-game TV (LOO) | mass in rare bins | missing share provided | missing share sample games (min-max) | flags |
|---|---:|---:|---:|---:|---:|---|
| gap | 0.075 | 0.086 | 0.0% | 59.6% | 58.6% - 62.1% | - |
| dwell | 0.494 | 0.188 | 0.0% | 59.6% | 58.6% - 62.1% | TV > 2 x largest sample-game TV |
| ball_speed | 0.074 | 0.064 | 0.0% | 40.8% | 32.2% - 41.1% | - |
| heading | 0.481 | 0.126 | 0.0% | 54.5% | 46.3% - 54.5% | TV > 2 x largest sample-game TV |
| outside | 0.025 | 0.018 | 3.6% | 39.9% | 31.5% - 40.1% | - |
| player_speed | 0.066 | 0.115 | 0.0% | 0.2% | 0.0% - 0.0% | missing share outside [0.5 x min, 2 x max] of sample games |

Bins that gain / lose most mass (category index: delta share provided - training; categories ordered low to high; for gap and dwell, below the middle = away side):

* **gap** gain 4 (+3.1 pp), 7 (+2.2 pp), 3 (+1.2 pp); lose 1 (-3.4 pp), 2 (-2.2 pp), 0 (-1.4 pp)
* **dwell** gain 3 (+49.4 pp); lose 6 (-12.0 pp), 0 (-11.3 pp), 1 (-9.7 pp)
* **ball_speed** gain 0 (+2.8 pp), 1 (+2.4 pp), 2 (+2.2 pp); lose 3 (-4.5 pp), 4 (-3.0 pp)
* **heading** gain 2 (+29.6 pp), 3 (+18.5 pp); lose 0 (-24.2 pp), 1 (-23.9 pp)
* **outside** gain 1 (+2.5 pp); lose 0 (-2.5 pp)
* **player_speed** gain 23 (+1.7 pp), 5 (+0.8 pp), 4 (+0.8 pp); lose 16 (-1.1 pp), 17 (-1.0 pp), 18 (-0.8 pp)

Set-piece feature: missing everywhere (the frozen model has no informative set-piece emission).
