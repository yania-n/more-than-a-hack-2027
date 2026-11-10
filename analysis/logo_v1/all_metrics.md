# All organiser metrics: baselines vs v1 on the three Metrica sample games

Each number is the equal-weight mean over games 1-3 (and over the columns named in the heading). Best value per row in bold; for count/error rows the best is the one closest to the target. Labels are event-derived proxies, not the competition ground truth.

## primary rule, ball as-is

**Ranking metrics**

| metric | raw | smooth25 | smooth50 | smooth125 | v1_refit | v1_logo |
|---|---:|---:|---:|---:|---:|---:|
| spell_f1_mean | 0.106 | 0.378 | 0.430 | 0.311 | 0.466 | **0.474** |
| macro_f1 | 0.803 | **0.814** | 0.801 | 0.728 | 0.766 | 0.766 |

**Spell F1 per IoU threshold**

| metric | raw | smooth25 | smooth50 | smooth125 | v1_refit | v1_logo |
|---|---:|---:|---:|---:|---:|---:|
| spellF1@0.3 | 0.185 | 0.510 | 0.551 | 0.429 | 0.628 | **0.629** |
| spellF1@0.4 | 0.136 | 0.450 | 0.504 | 0.379 | 0.570 | **0.571** |
| spellF1@0.5 | 0.097 | 0.390 | 0.440 | 0.312 | 0.467 | **0.479** |
| spellF1@0.6 | 0.068 | 0.310 | 0.368 | 0.254 | 0.378 | **0.391** |
| spellF1@0.7 | 0.045 | 0.228 | 0.285 | 0.181 | 0.286 | **0.302** |

**Frame level**

| metric | raw | smooth25 | smooth50 | smooth125 | v1_refit | v1_logo |
|---|---:|---:|---:|---:|---:|---:|
| accuracy | 0.804 | **0.813** | 0.802 | 0.735 | 0.768 | 0.767 |
| kappa | 0.705 | **0.719** | 0.701 | 0.600 | 0.651 | 0.650 |
| alive_dead_f1 | **0.943** | 0.930 | 0.915 | 0.883 | 0.875 | 0.879 |
| team_acc_gt_alive | 0.729 | 0.784 | 0.807 | **0.808** | 0.746 | 0.761 |
| team_acc_both_alive | 0.805 | 0.855 | 0.872 | 0.856 | **0.883** | 0.881 |
| F1_H | 0.771 | 0.804 | **0.806** | 0.760 | 0.778 | 0.776 |
| F1_A | 0.747 | 0.785 | **0.790** | 0.752 | 0.767 | 0.773 |
| F1_D | **0.891** | 0.853 | 0.808 | 0.673 | 0.754 | 0.749 |
| share_err | **0.011** | 0.014 | 0.012 | 0.012 | 0.032 | 0.052 |

**Possession structure (real count is the target)**

| metric | raw | smooth25 | smooth50 | smooth125 | v1_refit | v1_logo |
|---|---:|---:|---:|---:|---:|---:|
| n_gt_spells | 353 | 353 | 353 | 353 | 353 | 353 |
| n_pred_spells | 2257 | 679 | 500 | 374 | **357** | 360 |
| spell_count_error | 1904 | 326 | 147 | 21.333 | **3.667** | 7.333 |
| mean_spell_duration_s | 1.597 | 5.624 | 7.977 | 11.844 | 10.207 | **10.440** |
| gt_mean_spell_duration_s | 11.074 | 11.074 | 11.074 | 11.074 | 11.074 | 11.074 |
| fragmentation | 5.519 | 1.765 | 1.342 | **1.004** | 1.181 | 1.181 |

**Transitions, tau = 12 frames**

| metric | raw | smooth25 | smooth50 | smooth125 | v1_refit | v1_logo |
|---|---:|---:|---:|---:|---:|---:|
| trans12_precision | 0.152 | 0.119 | 0.117 | 0.060 | **0.225** | 0.223 |
| trans12_recall | **0.838** | 0.209 | 0.156 | 0.060 | 0.263 | 0.263 |
| trans12_f1 | **0.257** | 0.151 | 0.134 | 0.060 | 0.242 | 0.241 |
| trans12_mean_abs_latency | **2.071** | 5.011 | 5.668 | 6.087 | 5.095 | 5.033 |

**Transitions, tau = 25 frames**

| metric | raw | smooth25 | smooth50 | smooth125 | v1_refit | v1_logo |
|---|---:|---:|---:|---:|---:|---:|
| trans25_precision | 0.169 | 0.306 | 0.205 | 0.120 | 0.325 | **0.335** |
| trans25_recall | **0.930** | 0.540 | 0.275 | 0.121 | 0.379 | 0.395 |
| trans25_f1 | 0.285 | **0.391** | 0.235 | 0.120 | 0.349 | 0.362 |
| trans25_mean_abs_latency | **5.600** | 16.383 | 11.815 | 12.733 | 9.380 | 9.733 |

## primary rule, mean of 3 ball conditions

**Ranking metrics**

| metric | raw | smooth25 | smooth50 | smooth125 | v1_refit | v1_logo |
|---|---:|---:|---:|---:|---:|---:|
| spell_f1_mean | 0.100 | 0.366 | 0.420 | 0.303 | 0.457 | **0.462** |
| macro_f1 | 0.780 | **0.794** | 0.784 | 0.719 | 0.759 | 0.759 |

**Spell F1 per IoU threshold**

| metric | raw | smooth25 | smooth50 | smooth125 | v1_refit | v1_logo |
|---|---:|---:|---:|---:|---:|---:|
| spellF1@0.3 | 0.175 | 0.501 | 0.544 | 0.422 | **0.621** | 0.618 |
| spellF1@0.4 | 0.129 | 0.439 | 0.496 | 0.371 | **0.557** | 0.556 |
| spellF1@0.5 | 0.090 | 0.376 | 0.430 | 0.303 | 0.456 | **0.467** |
| spellF1@0.6 | 0.063 | 0.298 | 0.356 | 0.246 | 0.370 | **0.380** |
| spellF1@0.7 | 0.042 | 0.217 | 0.275 | 0.174 | 0.282 | **0.291** |

**Frame level**

| metric | raw | smooth25 | smooth50 | smooth125 | v1_refit | v1_logo |
|---|---:|---:|---:|---:|---:|---:|
| accuracy | 0.782 | **0.794** | 0.785 | 0.725 | 0.761 | 0.760 |
| kappa | 0.674 | **0.691** | 0.677 | 0.584 | 0.640 | 0.639 |
| alive_dead_f1 | **0.922** | 0.911 | 0.900 | 0.873 | 0.874 | 0.878 |
| team_acc_gt_alive | 0.699 | 0.756 | 0.780 | **0.788** | 0.737 | 0.751 |
| team_acc_both_alive | 0.805 | 0.855 | 0.872 | 0.855 | **0.874** | 0.872 |
| F1_H | 0.755 | 0.790 | **0.793** | 0.750 | 0.772 | 0.768 |
| F1_A | 0.728 | 0.768 | **0.776** | 0.743 | 0.754 | 0.762 |
| F1_D | **0.857** | 0.823 | 0.784 | 0.663 | 0.752 | 0.747 |
| share_err | **0.012** | 0.015 | 0.013 | 0.013 | 0.034 | 0.061 |

**Possession structure (real count is the target)**

| metric | raw | smooth25 | smooth50 | smooth125 | v1_refit | v1_logo |
|---|---:|---:|---:|---:|---:|---:|
| n_gt_spells | 353 | 353 | 353 | 353 | 353 | 353 |
| n_pred_spells | 2273 | 659 | 492 | 374 | **351** | 359 |
| spell_count_error | 1920 | 306 | 139 | 20.667 | **-2.111** | 5.667 |
| mean_spell_duration_s | 1.519 | 5.569 | 7.833 | **11.561** | 10.344 | 10.469 |
| gt_mean_spell_duration_s | 11.074 | 11.074 | 11.074 | 11.074 | 11.074 | 11.074 |
| fragmentation | 5.577 | 1.731 | 1.333 | **1.009** | 1.172 | 1.186 |

**Transitions, tau = 12 frames**

| metric | raw | smooth25 | smooth50 | smooth125 | v1_refit | v1_logo |
|---|---:|---:|---:|---:|---:|---:|
| trans12_precision | 0.145 | 0.117 | 0.116 | 0.059 | **0.223** | 0.217 |
| trans12_recall | **0.809** | 0.203 | 0.154 | 0.060 | 0.258 | 0.257 |
| trans12_f1 | **0.246** | 0.149 | 0.132 | 0.059 | 0.238 | 0.235 |
| trans12_mean_abs_latency | **2.089** | 5.038 | 5.651 | 6.381 | 5.070 | 5.065 |

**Transitions, tau = 25 frames**

| metric | raw | smooth25 | smooth50 | smooth125 | v1_refit | v1_logo |
|---|---:|---:|---:|---:|---:|---:|
| trans25_precision | 0.161 | 0.300 | 0.201 | 0.116 | 0.318 | **0.325** |
| trans25_recall | **0.897** | 0.520 | 0.268 | 0.117 | 0.368 | 0.386 |
| trans25_f1 | 0.273 | **0.380** | 0.230 | 0.116 | 0.340 | 0.352 |
| trans25_mean_abs_latency | **5.679** | 16.393 | 11.736 | 12.666 | 9.296 | 9.722 |

## mean of all 9 columns (3 rules x 3 conditions)

**Ranking metrics**

| metric | raw | smooth25 | smooth50 | smooth125 | v1_refit | v1_logo |
|---|---:|---:|---:|---:|---:|---:|
| spell_f1_mean | 0.090 | 0.330 | 0.387 | 0.305 | 0.426 | **0.426** |
| macro_f1 | 0.774 | **0.787** | 0.779 | 0.717 | 0.755 | 0.756 |

**Spell F1 per IoU threshold**

| metric | raw | smooth25 | smooth50 | smooth125 | v1_refit | v1_logo |
|---|---:|---:|---:|---:|---:|---:|
| spellF1@0.3 | 0.160 | 0.458 | 0.507 | 0.420 | **0.578** | 0.571 |
| spellF1@0.4 | 0.117 | 0.401 | 0.459 | 0.370 | **0.518** | 0.516 |
| spellF1@0.5 | 0.081 | 0.337 | 0.397 | 0.309 | 0.424 | **0.429** |
| spellF1@0.6 | 0.056 | 0.264 | 0.323 | 0.250 | 0.346 | **0.349** |
| spellF1@0.7 | 0.036 | 0.192 | 0.249 | 0.178 | 0.263 | **0.265** |

**Frame level**

| metric | raw | smooth25 | smooth50 | smooth125 | v1_refit | v1_logo |
|---|---:|---:|---:|---:|---:|---:|
| accuracy | 0.777 | **0.788** | 0.779 | 0.723 | 0.756 | 0.757 |
| kappa | 0.666 | **0.681** | 0.668 | 0.581 | 0.633 | 0.634 |
| alive_dead_f1 | **0.922** | 0.912 | 0.900 | 0.873 | 0.874 | 0.877 |
| team_acc_gt_alive | 0.690 | 0.746 | 0.772 | **0.786** | 0.730 | 0.747 |
| team_acc_both_alive | 0.794 | 0.844 | 0.862 | 0.852 | 0.866 | **0.867** |
| F1_H | 0.739 | 0.774 | **0.779** | 0.745 | 0.761 | 0.760 |
| F1_A | 0.725 | 0.765 | **0.773** | 0.744 | 0.751 | 0.762 |
| F1_D | **0.858** | 0.824 | 0.784 | 0.664 | 0.752 | 0.747 |
| share_err | 0.015 | 0.015 | 0.014 | **0.013** | 0.035 | 0.052 |

**Possession structure (real count is the target)**

| metric | raw | smooth25 | smooth50 | smooth125 | v1_refit | v1_logo |
|---|---:|---:|---:|---:|---:|---:|
| n_gt_spells | 354 | 354 | 354 | 354 | 354 | 354 |
| n_pred_spells | 2273 | 659 | 492 | 374 | **351** | 359 |
| spell_count_error | 1919 | 305 | 138 | 20.111 | **-2.667** | 5.111 |
| mean_spell_duration_s | 1.519 | 5.569 | 7.833 | **11.561** | 10.344 | 10.469 |
| gt_mean_spell_duration_s | 11.846 | 11.846 | 11.846 | 11.846 | 11.846 | 11.846 |
| fragmentation | 5.813 | 1.807 | 1.393 | **1.054** | 1.221 | 1.239 |

**Transitions, tau = 12 frames**

| metric | raw | smooth25 | smooth50 | smooth125 | v1_refit | v1_logo |
|---|---:|---:|---:|---:|---:|---:|
| trans12_precision | 0.141 | 0.108 | 0.106 | 0.059 | **0.204** | 0.198 |
| trans12_recall | **0.797** | 0.188 | 0.143 | 0.061 | 0.241 | 0.239 |
| trans12_f1 | **0.238** | 0.136 | 0.120 | 0.060 | 0.218 | 0.214 |
| trans12_mean_abs_latency | **2.096** | 5.009 | 5.609 | 6.362 | 5.085 | 5.085 |

**Transitions, tau = 25 frames**

| metric | raw | smooth25 | smooth50 | smooth125 | v1_refit | v1_logo |
|---|---:|---:|---:|---:|---:|---:|
| trans25_precision | 0.157 | 0.283 | 0.185 | 0.114 | 0.295 | **0.301** |
| trans25_recall | **0.883** | 0.498 | 0.250 | 0.117 | 0.350 | 0.364 |
| trans25_f1 | 0.265 | **0.357** | 0.211 | 0.114 | 0.316 | 0.326 |
| trans25_mean_abs_latency | **5.561** | 16.863 | 11.792 | 12.480 | 9.428 | 9.899 |

## S1 (strict) rule, ball as-is

**Ranking metrics**

| metric | raw | smooth25 | smooth50 | smooth125 | v1_refit | v1_logo |
|---|---:|---:|---:|---:|---:|---:|
| spell_f1_mean | 0.066 | 0.304 | 0.395 | 0.378 | **0.445** | 0.439 |
| macro_f1 | 0.797 | **0.809** | 0.799 | 0.735 | 0.767 | 0.768 |

**Spell F1 per IoU threshold**

| metric | raw | smooth25 | smooth50 | smooth125 | v1_refit | v1_logo |
|---|---:|---:|---:|---:|---:|---:|
| spellF1@0.3 | 0.117 | 0.422 | 0.507 | 0.489 | **0.588** | 0.578 |
| spellF1@0.4 | 0.085 | 0.372 | 0.463 | 0.440 | **0.536** | 0.528 |
| spellF1@0.5 | 0.058 | 0.310 | 0.408 | 0.387 | **0.444** | 0.439 |
| spellF1@0.6 | 0.041 | 0.241 | 0.336 | 0.326 | **0.373** | 0.368 |
| spellF1@0.7 | 0.027 | 0.178 | 0.260 | 0.246 | **0.281** | 0.281 |

**Frame level**

| metric | raw | smooth25 | smooth50 | smooth125 | v1_refit | v1_logo |
|---|---:|---:|---:|---:|---:|---:|
| accuracy | 0.798 | **0.808** | 0.799 | 0.743 | 0.768 | 0.769 |
| kappa | 0.697 | **0.711** | 0.696 | 0.610 | 0.651 | 0.652 |
| alive_dead_f1 | **0.944** | 0.931 | 0.916 | 0.883 | 0.875 | 0.879 |
| team_acc_gt_alive | 0.720 | 0.776 | 0.803 | **0.820** | 0.748 | 0.764 |
| team_acc_both_alive | 0.794 | 0.844 | 0.866 | 0.867 | 0.884 | **0.884** |
| F1_H | 0.752 | 0.787 | **0.794** | 0.765 | 0.774 | 0.774 |
| F1_A | 0.746 | 0.784 | **0.792** | 0.765 | 0.773 | 0.781 |
| F1_D | **0.894** | 0.856 | 0.810 | 0.675 | 0.755 | 0.749 |
| share_err | 0.018 | 0.014 | 0.014 | **0.013** | 0.036 | 0.037 |

**Possession structure (real count is the target)**

| metric | raw | smooth25 | smooth50 | smooth125 | v1_refit | v1_logo |
|---|---:|---:|---:|---:|---:|---:|
| n_gt_spells | 242 | 242 | 242 | 242 | 242 | 242 |
| n_pred_spells | 2257 | 679 | 500 | 374 | **357** | 360 |
| spell_count_error | 2015 | 437 | 258 | 132 | **115** | 118 |
| mean_spell_duration_s | 1.597 | 5.624 | 7.977 | **11.844** | 10.207 | 10.440 |
| gt_mean_spell_duration_s | 16.061 | 16.061 | 16.061 | 16.061 | 16.061 | 16.061 |
| fragmentation | 7.366 | 2.359 | 1.794 | **1.342** | 1.573 | 1.577 |

**Transitions, tau = 12 frames**

| metric | raw | smooth25 | smooth50 | smooth125 | v1_refit | v1_logo |
|---|---:|---:|---:|---:|---:|---:|
| trans12_precision | 0.119 | 0.081 | 0.084 | 0.053 | **0.170** | 0.164 |
| trans12_recall | **0.878** | 0.191 | 0.151 | 0.071 | 0.268 | 0.257 |
| trans12_f1 | **0.209** | 0.114 | 0.108 | 0.061 | 0.208 | 0.200 |
| trans12_mean_abs_latency | **1.610** | 4.624 | 5.387 | 5.989 | 5.140 | 4.966 |

**Transitions, tau = 25 frames**

| metric | raw | smooth25 | smooth50 | smooth125 | v1_refit | v1_logo |
|---|---:|---:|---:|---:|---:|---:|
| trans25_precision | 0.128 | 0.232 | 0.150 | 0.102 | 0.254 | **0.258** |
| trans25_recall | **0.946** | 0.549 | 0.270 | 0.137 | 0.400 | 0.405 |
| trans25_f1 | 0.225 | **0.327** | 0.193 | 0.117 | 0.311 | 0.315 |
| trans25_mean_abs_latency | **4.306** | 17.753 | 11.914 | 12.350 | 9.663 | 10.111 |

## S2 (loose) rule, ball as-is

**Ranking metrics**

| metric | raw | smooth25 | smooth50 | smooth125 | v1_refit | v1_logo |
|---|---:|---:|---:|---:|---:|---:|
| spell_f1_mean | 0.114 | 0.339 | 0.365 | 0.252 | 0.388 | **0.393** |
| macro_f1 | 0.790 | **0.800** | 0.788 | 0.717 | 0.751 | 0.754 |

**Spell F1 per IoU threshold**

| metric | raw | smooth25 | smooth50 | smooth125 | v1_refit | v1_logo |
|---|---:|---:|---:|---:|---:|---:|
| spellF1@0.3 | 0.203 | 0.471 | 0.486 | 0.362 | **0.539** | 0.532 |
| spellF1@0.4 | 0.149 | 0.411 | 0.437 | 0.315 | 0.477 | **0.481** |
| spellF1@0.5 | 0.104 | 0.349 | 0.373 | 0.255 | 0.389 | **0.395** |
| spellF1@0.6 | 0.071 | 0.271 | 0.297 | 0.196 | 0.306 | **0.317** |
| spellF1@0.7 | 0.045 | 0.193 | 0.230 | 0.133 | 0.229 | **0.242** |

**Frame level**

| metric | raw | smooth25 | smooth50 | smooth125 | v1_refit | v1_logo |
|---|---:|---:|---:|---:|---:|---:|
| accuracy | 0.791 | **0.799** | 0.787 | 0.723 | 0.752 | 0.755 |
| kappa | 0.686 | **0.697** | 0.679 | 0.580 | 0.627 | 0.630 |
| alive_dead_f1 | **0.942** | 0.929 | 0.915 | 0.883 | 0.874 | 0.877 |
| team_acc_gt_alive | 0.710 | 0.763 | 0.786 | **0.790** | 0.725 | 0.744 |
| team_acc_both_alive | 0.785 | 0.832 | 0.850 | 0.837 | 0.860 | **0.863** |
| F1_H | 0.740 | 0.772 | **0.776** | 0.738 | 0.748 | 0.752 |
| F1_A | 0.739 | 0.775 | **0.780** | 0.741 | 0.754 | 0.764 |
| F1_D | **0.891** | 0.852 | 0.807 | 0.672 | 0.752 | 0.746 |
| share_err | 0.015 | 0.014 | 0.014 | **0.013** | 0.035 | 0.040 |

**Possession structure (real count is the target)**

| metric | raw | smooth25 | smooth50 | smooth125 | v1_refit | v1_logo |
|---|---:|---:|---:|---:|---:|---:|
| n_gt_spells | 466 | 466 | 466 | 466 | 466 | 466 |
| n_pred_spells | 2257 | 679 | **500** | 374 | 357 | 360 |
| spell_count_error | 1792 | 213 | **34.333** | -91.333 | -109 | -105 |
| mean_spell_duration_s | 1.597 | 5.624 | **7.977** | 11.844 | 10.207 | 10.440 |
| gt_mean_spell_duration_s | 8.404 | 8.404 | 8.404 | 8.404 | 8.404 | 8.404 |
| fragmentation | 4.384 | 1.405 | 1.069 | **0.801** | 0.936 | 0.942 |

**Transitions, tau = 12 frames**

| metric | raw | smooth25 | smooth50 | smooth125 | v1_refit | v1_logo |
|---|---:|---:|---:|---:|---:|---:|
| trans12_precision | 0.170 | 0.127 | 0.121 | 0.067 | 0.220 | **0.223** |
| trans12_recall | **0.749** | 0.179 | 0.130 | 0.054 | 0.205 | 0.210 |
| trans12_f1 | **0.278** | 0.149 | 0.125 | 0.060 | 0.212 | 0.215 |
| trans12_mean_abs_latency | **2.499** | 5.251 | 5.776 | 6.247 | 5.119 | 5.118 |

**Transitions, tau = 25 frames**

| metric | raw | smooth25 | smooth50 | smooth125 | v1_refit | v1_logo |
|---|---:|---:|---:|---:|---:|---:|
| trans25_precision | 0.196 | 0.325 | 0.214 | 0.132 | 0.323 | **0.336** |
| trans25_recall | **0.863** | 0.458 | 0.229 | 0.107 | 0.301 | 0.316 |
| trans25_f1 | 0.320 | **0.380** | 0.221 | 0.118 | 0.311 | 0.325 |
| trans25_mean_abs_latency | **6.549** | 16.428 | 11.802 | 12.529 | 9.551 | 9.906 |

Cells won on spell_f1_mean (of 27): raw 0, smooth25 0, smooth50 0, smooth125 0, v1_refit 10, v1_logo 17

Cells won on macro_f1 (of 27): raw 0, smooth25 21, smooth50 0, smooth125 0, v1_refit 0, v1_logo 6
