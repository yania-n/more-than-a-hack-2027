# Baselines vs v1 on the three Metrica sample games

Methods: raw, smooth25, smooth50, smooth125, v1_refit, v1_logo. Games: game1, game2, game3. spellF1 = mean over IoU 0.3-0.7 (the ranking metric), whole game.

## 1. Pooled spellF1 (equal-weight mean of the games), by label rule and ball condition

| method | primary / asis | primary / degraded_seed0 | primary / degraded_seed1 | S1 / asis | S1 / degraded_seed0 | S1 / degraded_seed1 | S2 / asis | S2 / degraded_seed0 | S2 / degraded_seed1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| raw | 0.106 | 0.097 | 0.097 | 0.066 | 0.060 | 0.059 | 0.114 | 0.105 | 0.105 |
| smooth25 | 0.378 | 0.363 | 0.359 | 0.304 | 0.295 | 0.288 | 0.339 | 0.325 | 0.323 |
| smooth50 | 0.430 | 0.417 | 0.413 | 0.395 | 0.384 | 0.375 | 0.365 | 0.352 | 0.354 |
| smooth125 | 0.311 | 0.303 | 0.297 | 0.378 | 0.365 | 0.353 | 0.252 | 0.246 | 0.244 |
| v1_refit | 0.466 | 0.455 | 0.451 | **0.445** | **0.437** | **0.433** | 0.388 | 0.379 | 0.378 |
| v1_logo | **0.474** | **0.459** | **0.454** | 0.439 | 0.425 | 0.425 | **0.393** | **0.384** | **0.382** |

Mean over all 9 columns: v1_logo 0.426, v1_refit 0.426, smooth50 0.387, smooth25 0.330, smooth125 0.305, raw 0.090.
**Highest pooled spellF1: v1_logo (0.426), ahead of v1_refit (0.426) by 0.001.**

## 2. Per game, primary rule, ball as-is (5-95% bootstrap over the game's possessions)

| method | game1 | game2 | game3 |
|---|---:|---:|---:|
| raw | 0.124 [0.115, 0.135] | 0.100 [0.092, 0.109] | 0.093 [0.086, 0.101] |
| smooth25 | 0.399 [0.371, 0.426] | 0.379 [0.354, 0.404] | 0.356 [0.332, 0.377] |
| smooth50 | 0.452 [0.420, 0.486] | 0.433 [0.403, 0.463] | 0.404 [0.372, 0.433] |
| smooth125 | 0.315 [0.281, 0.349] | 0.302 [0.268, 0.335] | 0.316 [0.281, 0.350] |
| v1_refit | **0.494 [0.454, 0.534]** | 0.456 [0.424, 0.493] | 0.446 [0.413, 0.478] |
| v1_logo | 0.464 [0.426, 0.502] | **0.505 [0.467, 0.542]** | **0.454 [0.417, 0.489]** |

Per-method intervals overlap whenever two methods are close; the harness' paired intervals (results.json, `paired` and `pooled`) are the sharper test.

## 3. Which method has the highest spellF1 in each game x rule x condition cell (27 cells)

| method | cells won |
|---|---:|
| raw | 0 |
| smooth25 | 0 |
| smooth50 | 0 |
| smooth125 | 0 |
| v1_refit | 10 |
| v1_logo | 17 |

Winner by game (primary rule, as-is): game1: v1_refit, game2: v1_logo, game3: v1_logo

## 4. Where each method wins: component metrics (primary rule, ball as-is, mean of the games)

| method | spellF1 | macroF1 | alive/dead F1 | team acc (both alive) | predicted / real possessions |
|---|---:|---:|---:|---:|---:|
| raw | 0.106 | 0.803 | **0.943** | 0.805 | 6.406 |
| smooth25 | 0.378 | **0.814** | 0.930 | 0.855 | 1.921 |
| smooth50 | 0.430 | 0.801 | 0.915 | 0.872 | 1.418 |
| smooth125 | 0.311 | 0.728 | 0.883 | 0.856 | 1.067 |
| v1_refit | 0.466 | 0.766 | 0.875 | **0.883** | 1.013 |
| v1_logo | **0.474** | 0.766 | 0.879 | 0.881 | 1.028 |

(The last column should be near 1.00; the best value there is the closest to 1, not the highest.)

## Caveats

- Labels are proxies built from event data, not the competition's ground truth.
- The ball is blank during stoppages in all three games, which flatters rules that read a missing ball as dead ball (the baselines); the provided match is not like that.
- Choosing the best window on three games selects on those games; the organizers' own full-match numbers rank the windows differently from their public window.
