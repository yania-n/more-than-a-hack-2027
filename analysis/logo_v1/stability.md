# Stability of fitted v1 parameters across fits

All fits unsupervised, ball as-is. `logo_hold_gK` = trained on the two games other than K (the fits `v1_logo` uses for game K); `only_gK` = trained on game K alone (stability only, never scored); `all3` = frozen_params.json; `shipped_provided` = the shipped v1 (fitted on the provided match). Relative range = (max-min)/mean.

## Scalars

| parameter | logo_hold_game1 | only_game1 | logo_hold_game2 | only_game2 | logo_hold_game3 | only_game3 | all3 | shipped_provided | rel.range LOGO | rel.range 7 sample fits |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| radius (m) | 0.922 | 0.276 | 0.925 | 0.277 | 0.277 | 1.273 | 0.758 | 1.914 | 0.92 | 1.48 |
| carry speed (m/s) | 5.971 | 6.175 | 6.061 | 5.994 | 6.087 | 5.950 | 6.040 | 6.440 | 0.02 | 0.04 |
| edge gap[0] | 2.146 | 2.408 | 2.194 | 2.272 | 2.334 | 1.998 | 2.218 | 1.824 | 0.08 | 0.18 |
| edge gap[1] | 4.572 | 4.963 | 4.724 | 4.628 | 4.784 | 4.497 | 4.692 | 4.412 | 0.05 | 0.10 |
| edge gap[2] | 8.158 | 9.037 | 8.656 | 8.011 | 8.487 | 8.327 | 8.440 | 8.545 | 0.06 | 0.12 |
| edge dwell[0] | 15.000 | 21.000 | 16.000 | 18.000 | 20.000 | 14.000 | 17.000 | 15.000 | 0.29 | 0.40 |
| edge dwell[1] | 36.000 | 53.000 | 39.000 | 42.000 | 47.000 | 32.000 | 41.000 | 37.000 | 0.27 | 0.51 |
| edge ball_speed[0] | 2.438 | 1.790 | 2.087 | 2.543 | 2.178 | 2.319 | 2.223 | 1.969 | 0.16 | 0.34 |
| edge ball_speed[1] | 4.741 | 4.138 | 4.476 | 4.671 | 4.437 | 4.804 | 4.545 | 3.968 | 0.07 | 0.15 |
| edge ball_speed[2] | 7.899 | 7.318 | 7.780 | 7.714 | 7.559 | 8.038 | 7.776 | 6.479 | 0.04 | 0.09 |
| edge ball_speed[3] | 11.700 | 11.812 | 11.763 | 11.659 | 11.750 | 11.713 | 11.723 | 10.803 | 0.01 | 0.01 |
| edge heading[0] | 0.013 | 0.013 | 0.012 | 0.015 | 0.014 | 0.011 | 0.013 | 0.876 | 0.12 | 0.25 |
| edge heading[1] | 0.034 | 0.351 | 0.034 | 0.357 | 0.355 | 0.025 | 0.040 | 2.739 | 2.28 | 1.94 |
| edge heading[2] | 3.342 | 3.947 | 3.201 | 4.219 | 4.089 | 2.151 | 3.568 | 7.651 | 0.25 | 0.59 |
| edge player_speed[0] | 0.701 | 0.662 | 0.688 | 0.679 | 0.671 | 0.731 | 0.685 | 0.661 | 0.04 | 0.10 |
| edge player_speed[1] | 0.930 | 0.846 | 0.899 | 0.891 | 0.868 | 0.975 | 0.896 | 0.864 | 0.07 | 0.14 |
| edge player_speed[2] | 1.131 | 1.019 | 1.098 | 1.073 | 1.045 | 1.199 | 1.090 | 1.027 | 0.08 | 0.16 |
| edge player_speed[3] | 1.305 | 1.182 | 1.273 | 1.232 | 1.207 | 1.399 | 1.258 | 1.187 | 0.08 | 0.17 |
| edge player_speed[4] | 1.476 | 1.336 | 1.455 | 1.378 | 1.359 | 1.567 | 1.429 | 1.344 | 0.08 | 0.16 |
| edge player_speed[5] | 1.656 | 1.515 | 1.635 | 1.553 | 1.535 | 1.754 | 1.610 | 1.520 | 0.08 | 0.15 |
| edge player_speed[6] | 1.860 | 1.721 | 1.838 | 1.757 | 1.740 | 1.946 | 1.814 | 1.752 | 0.07 | 0.12 |
| edge player_speed[7] | 2.071 | 1.951 | 2.062 | 1.990 | 1.971 | 2.140 | 2.038 | 2.003 | 0.05 | 0.09 |
| edge player_speed[8] | 2.292 | 2.228 | 2.305 | 2.209 | 2.219 | 2.361 | 2.272 | 2.316 | 0.04 | 0.07 |
| edge player_speed[9] | 2.594 | 2.615 | 2.634 | 2.529 | 2.567 | 2.646 | 2.600 | 2.706 | 0.03 | 0.05 |
| edge player_speed[10] | 3.063 | 3.198 | 3.122 | 3.045 | 3.124 | 3.071 | 3.101 | 3.253 | 0.02 | 0.05 |
| stay prob H | 0.950 | 0.954 | 0.953 | 0.950 | 0.952 | 0.953 | 0.952 | 0.935 | 0.00 | 0.00 |
| stay prob A | 0.948 | 0.952 | 0.950 | 0.951 | 0.952 | 0.946 | 0.950 | 0.908 | 0.00 | 0.01 |
| stay prob D | 0.962 | 0.976 | 0.970 | 0.965 | 0.971 | 0.963 | 0.966 | 0.975 | 0.01 | 0.02 |

Scalars that moved most between the three LOGO folds (relative range): edge heading[1] 2.28, radius (m) 0.92, edge dwell[0] 0.29, edge dwell[1] 0.27, edge heading[2] 0.25, edge ball_speed[0] 0.16, edge heading[0] 0.12, edge gap[0] 0.08

## Emission tables: mean total-variation distance (0 identical, 1 disjoint), mean over the 3 states

| feature | LOGO folds, mean pairwise TV | all 7 sample fits | sample fits vs shipped |
|---|---:|---:|---:|
| ball_speed | 0.073 | 0.084 | 0.092 |
| dwell | 0.073 | 0.081 | 0.141 |
| player_speed | 0.071 | 0.073 | 0.066 |
| heading | 0.040 | 0.040 | 0.056 |
| gap | 0.037 | 0.041 | 0.056 |
| outside | 0.017 | 0.018 | 0.031 |

(The set-piece feature is missing in every sample-game fit, so its emission is the uninformative prior; omitted.)

EM iterations to converge: logo_hold_game1 33, only_game1 21, logo_hold_game2 29, only_game2 30, logo_hold_game3 40, only_game3 26, all3 35, shipped_provided 23
