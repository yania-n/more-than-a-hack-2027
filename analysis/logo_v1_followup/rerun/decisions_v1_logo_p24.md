# Pre-registered decision rule: v1_logo_p24 against each comparator

Differences are spellF1 (v1_logo_p24 - comparator), equal-weight mean over games, paired bootstrap 90% interval (1,000 draws, seed 0). Clauses a-e as in PREREGISTRATION.md s.5.

| comparator | primary/as-is diff [90% CI] | P(logo better) | clauses a b c d e | halves | verdict |
|---|---:|---:|---|---:|---|
| raw | +0.379 [+0.357, +0.403] | 1.00 | a=Y b=Y c=Y d=Y e=Y | 100% | v1_logo_p24 wins |
| smooth25 | +0.107 [+0.088, +0.127] | 1.00 | a=Y b=Y c=Y d=Y e=Y | 100% | v1_logo_p24 wins |
| smooth50 | +0.055 [+0.038, +0.074] | 1.00 | a=Y b=Y c=Y d=Y e=n | 67% | no clear winner (leaning v1_logo_p24; clauses failing: e) |
| smooth125 | +0.174 [+0.153, +0.194] | 1.00 | a=Y b=Y c=Y d=Y e=Y | 89% | v1_logo_p24 wins |
| v1_refit | +0.020 [+0.006, +0.034] | 0.99 | a=Y b=n c=Y d=Y e=n | 44% | no clear winner (leaning v1_logo_p24; clauses failing: b, e) |
| v1_logo | +0.011 [+0.003, +0.019] | 0.98 | a=Y b=Y c=Y d=Y e=n | 37% | no clear winner (leaning v1_logo_p24; clauses failing: e) |

Per ball condition and rule, pooled difference (v1_logo_p24 - comparator):

| comparator | primary/asis | primary/degraded_seed0 | primary/degraded_seed1 | S1/asis | S1/degraded_seed0 | S1/degraded_seed1 | S2/asis | S2/degraded_seed0 | S2/degraded_seed1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| raw | +0.379 | +0.364 | +0.365 | +0.380 | +0.370 | +0.370 | +0.286 | +0.280 | +0.283 |
| smooth25 | +0.107 | +0.098 | +0.104 | +0.141 | +0.134 | +0.141 | +0.061 | +0.059 | +0.065 |
| smooth50 | +0.055 | +0.044 | +0.049 | +0.051 | +0.045 | +0.054 | +0.035 | +0.033 | +0.035 |
| smooth125 | +0.174 | +0.158 | +0.166 | +0.068 | +0.065 | +0.076 | +0.148 | +0.138 | +0.144 |
| v1_refit | +0.020 | +0.006 | +0.011 | +0.001 | -0.008 | -0.004 | +0.012 | +0.006 | +0.010 |
| v1_logo | +0.011 | +0.002 | +0.008 | +0.007 | +0.005 | +0.004 | +0.006 | -0.000 | +0.006 |
