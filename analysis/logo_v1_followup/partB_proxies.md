# B2/B3: label-free output proxies of the frozen model on the provided match (descriptive, not a score)

Frozen model: v1_external_all (Metrica Sports sample data, github.com/metrica-sports/sample-data; 24 player-speed bins). The provided match was used only as input; per-frame output is in `private/` (gitignored). Decode deterministic (md5 46004ab26c520b255e84e2a196d3c8cf, twice).

Definitions: PREREGISTRATION_B.md s.4. Sample-game columns are the primary proxy labels (min - max over the 3 games); the flag band is [0.5 x min, 2 x max] of that range.

| proxy | v1_external_all | smooth50 | old v1 (not compliant) | sample proxy labels (min-max) | flag band | sample v1_logo (min-max) | sample smooth50 (min-max) |
|---|---:|---:|---:|---:|---:|---:|---:|
| poss_per_alive_min | 7.47 | 8.29 | 8.67 | 5.05 - 5.69 | 2.52 - 11.38 | 5.25 - 6.27 | 7.39 - 7.78 |
| mean_poss_len_s | 8.04 | 7.24 | 6.92 | 10.54 - 11.89 | 5.27 - 23.77 | 9.57 - 11.43 | 7.71 - 8.12 |
| pct_lt_2s | 19.4% | 31.3% | 26.6% | 19.7% - 24.5% | 9.9% - 49.0% | 10.4% - 15.0% | 35.5% - 37.9% |
| reversal_3s | 26.6% | 29.5% | 36.8% | 17.7% - 24.5% | 8.9% - 49.1% | 18.3% - 21.7% | 36.4% - 40.6% |
| dead_share | 39.4% | 32.3% | 38.7% | 26.7% - 34.1% | 13.3% - 68.3% | 28.7% - 38.4% | 25.1% - 33.7% |
| mean_dead_spell_s | 14.91 | 15.45 | 16.95 | 16.90 - 23.94 | 8.45 - 47.89 | 11.80 - 13.47 | 15.17 - 22.18 |
| home_share_alive | 65.2% | 57.0% | 65.9% | 50.9% - 52.4% | 25.5% - 104.8% | 55.1% - 58.3% | 51.4% - 53.2% |

Counts (spells / direct transitions / graded minutes): v1_external_all 479 / 312 / 105.9; smooth50 594 / 461 / 105.9; old v1 (not compliant) 563 / 419 / 105.9

Context flags (smooth50 and old v1, same two rules): smooth50: none; old v1 (not compliant): none

## Agreement (descriptive, NOT a score; the named system is treated as the reference)

| pair | frame agreement | spell-level F1 (organiser matching) |
|---|---:|---:|
| v1_external_all vs smooth50 (ref smooth50) | 0.709 | 0.362 |
| v1_external_all vs old v1 (ref old v1) | 0.962 | 0.828 |
| old v1 vs smooth50 (ref smooth50) | 0.713 | 0.353 |
| sample games: v1_logo vs smooth50 (ref smooth50), per game | 0.727 / 0.764 / 0.800 | 0.388 / 0.382 / 0.396 |

**Flagged for v1_external_all (needs investigation, not a failure):** none
