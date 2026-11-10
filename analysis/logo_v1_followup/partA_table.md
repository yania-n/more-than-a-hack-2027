# Part A: held-out log-likelihood per block, by N_PSPEED (label-free)

Leave-one-game-out, as-is ball, tracking-period intervals; each cell is the held-out game's forward log-likelihood per block under the fit on the other two games. Source data: Metrica Sports sample data (github.com/metrica-sports/sample-data).

## Density-corrected (selection criterion)

| N_PSPEED | held-out game1 | held-out game2 | held-out game3 | mean | best - this (mean) | SE of paired diff | within 1 SE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 6 | -4.1163 | -3.9791 | -4.5776 | -4.2243 | 0.4047 | 0.0609 | no |
| 8 | -4.0210 | -3.8703 | -4.3964 | -4.0959 | 0.2763 | 0.0345 | no |
| 12 | -3.8936 | -3.7578 | -4.2095 | -3.9537 | 0.1341 | 0.0124 | no |
| 16 | -3.8418 | -3.6933 | -4.1418 | -3.8923 | 0.0727 | 0.0090 | no |
| 24 | -3.7761 | -3.6315 | -4.0512 | -3.8196 | 0.0000 | 0.0000 | yes |

Best by mean: **24**. Smallest candidate within one SE of the paired difference: **24** (registered rule). Alternative tolerance (0.5% of |best|), diagnostic only: 24.

## Raw discrete log-likelihood per block (not comparable across bin counts; shown as the task states it)

| N_PSPEED | held-out game1 | held-out game2 | held-out game3 | mean |
|---|---:|---:|---:|---:|
| 6 | -4.1361 | -4.0998 | -4.5196 | -4.2518 |
| 8 | -4.4285 | -4.3913 | -4.7948 | -4.5382 |
| 12 | -4.8207 | -4.7889 | -5.1950 | -4.9349 |
| 16 | -5.1145 | -5.0773 | -5.4839 | -5.2252 |
| 24 | -5.5173 | -5.4811 | -5.8851 | -5.6278 |

## Diagnostic: learned dead-ball cutoff in player speed (D:alive likelihood ratio first below 1), m/s

| N_PSPEED | fold game1 | fold game2 | fold game3 | range across folds | interpolated (3 folds) | crossings (3 folds) | bin width at cutoff (3 folds) |
|---|---:|---:|---:|---:|---:|---:|---:|
| 6 | 1.305 | 1.273 | 1.207 | 0.098 | 1.268 / 1.245 / 1.192 | 1 / 1 / 1 | 0.38+0.35 / 0.37+0.36 / 0.34+0.33 |
| 8 | 1.390 | 1.366 | 1.278 | 0.112 | 1.322 / 1.293 / 1.248 | 1 / 1 / 1 | 0.26+0.27 / 0.27+0.27 / 0.23+0.26 |
| 12 | 1.305 | 1.273 | 1.359 | 0.086 | 1.278 / 1.280 / 1.324 | 1 / 1 / 1 | 0.17+0.17 / 0.17+0.18 / 0.15+0.18 |
| 16 | 1.390 | 1.366 | 1.278 | 0.112 | 1.341 / 1.329 / 1.270 | 1 / 1 / 1 | 0.13+0.13 / 0.13+0.13 / 0.10+0.12 |
| 24 | 1.390 | 1.366 | 1.359 | 0.031 | 1.348 / 1.330 / 1.326 | 1 / 1 / 1 | 0.08+0.09 / 0.09+0.09 / 0.08+0.08 |

In a categorical model the cutoff is always a bin edge; the last column is the width of the bins either side (resolution), and 'interpolated' is a continuous estimate from the log-ratio between bin centres.

EM iterations: 6:24/24/27, 8:23/28/40, 12:33/29/40, 16:29/34/67, 24:38/36/58
