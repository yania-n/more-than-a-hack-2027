# Pre-registered decision rule: v1_logo against each comparator

Differences are spellF1 (v1_logo - comparator), equal-weight mean over games, paired bootstrap 90% interval (1,000 draws, seed 0). Clauses a-e as in PREREGISTRATION.md s.5.

| comparator | primary/as-is diff [90% CI] | P(logo better) | clauses a b c d e | halves | verdict |
|---|---:|---:|---|---:|---|
| raw | +0.368 [+0.347, +0.392] | 1.00 | a=Y b=Y c=Y d=Y e=Y | 100% | v1_logo wins |
| smooth25 | +0.097 [+0.078, +0.117] | 1.00 | a=Y b=Y c=Y d=Y e=Y | 100% | v1_logo wins |
| smooth50 | +0.045 [+0.027, +0.063] | 1.00 | a=Y b=Y c=Y d=Y e=n | 67% | no clear winner (leaning v1_logo; clauses failing: e) |
| smooth125 | +0.163 [+0.143, +0.184] | 1.00 | a=Y b=Y c=Y d=Y e=Y | 89% | v1_logo wins |
| v1_refit | +0.009 [-0.004, +0.022] | 0.86 | a=n b=n c=n d=Y e=n | 33% | no clear winner (leaning v1_logo; clauses failing: a, b, c, e) |

Per ball condition and rule, pooled difference (v1_logo - comparator):

| comparator | primary/asis | primary/degraded_seed0 | primary/degraded_seed1 | S1/asis | S1/degraded_seed0 | S1/degraded_seed1 | S2/asis | S2/degraded_seed0 | S2/degraded_seed1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| raw | +0.368 | +0.362 | +0.357 | +0.373 | +0.365 | +0.365 | +0.279 | +0.280 | +0.277 |
| smooth25 | +0.097 | +0.096 | +0.095 | +0.134 | +0.129 | +0.137 | +0.055 | +0.059 | +0.059 |
| smooth50 | +0.045 | +0.042 | +0.041 | +0.044 | +0.040 | +0.050 | +0.029 | +0.033 | +0.029 |
| smooth125 | +0.163 | +0.156 | +0.157 | +0.061 | +0.060 | +0.072 | +0.141 | +0.138 | +0.138 |
| v1_refit | +0.009 | +0.004 | +0.003 | -0.006 | -0.012 | -0.008 | +0.006 | +0.006 | +0.004 |
