# Beyond the 40: Does Combine Pass-Rush Speed Carry to the NFL?

## Research question

Among defensive-line prospects, is player peak speed during the NFL Combine's `PASS_RUSH_DRILL` associated with mean tracked speed in that player's rookie regular season? Does that relationship remain after adjusting for draft-year cohort and the conventional 40-yard time?

## Why this matters

Combine stopwatches summarize a narrow outcome; wearable tracking captures how movement unfolds through a football-specific drill. A useful scouting signal would connect that movement to later NFL play, while adding something beyond familiar tests. This analysis makes that Combine-to-NFL connection directly, then tests whether the sensor association remains after accounting for the 40-yard dash. It is an initial, transparent study, not a validated scouting model.

## Data and method

The analysis uses the nine official NFL Big Data Bowl 2027 CSV files. It joins Combine tracking to Combine results on `nfl_id` and `draft_year`, then joins players to regular-season game tracking through `nfl_id` and `games.csv` (`season_type == REG`, `season == draft_year`). It therefore measures subsequent rookie-season activity rather than using later seasons as the primary outcome.

Only `PLAYER` rows from the 10 Hz Combine sensor file are used. Within each attempt, frames are ordered by timestamp and peak speed is calculated; a player's feature is the median of their attempt-level peaks for that drill. The NFL outcome is mean observed speed over rookie-year regular-season tracking frames. These frame-weighted averages depend on playing time, role, assignment, and play mix as well as athletic ability.

We selected the position, drill category, and drill with the largest complete-case cohort using coverage only—not correlation size. The complete-case criterion required a career-snap summary and at least 100 rookie tracking frames. Large NFL tracking files were processed in 200,000-row chunks. Rank-transformed outcomes and features were residualized against draft-year indicators; intervals are 1,000-replicate, draft-year-stratified player-bootstrap percentile intervals. The incremental comparison also controls for ranked 40-yard time and uses only players with a recorded 40.

## Sample and coverage

The coverage-selected group is **DL / `SKILL_DRILLS_DL` / `PASS_RUSH_DRILL`**. It contains **91 unique players**: 27 from the 2023 class, 27 from 2024, and 37 from 2025. Those counts represent 73.0%, 73.0%, and 84.1%, respectively, of the Combine DL class in each year. Across all positions, rookie regular-season tracking was available for 122/160 (2023), 131/177 (2024), and 125/173 (2025) Combine prospects. Only 71 of the 91 selected players had a usable 40-yard time for the incremental comparison.

## Findings

| Relationship | Players | Cohort-adjusted rank correlation (95% bootstrap interval) |
|---|---:|---:|
| Combine pass-rush peak speed vs. rookie mean tracked speed | 91 | 0.579 (0.423 to 0.706) |
| Same relationship, additionally controlling for 40-yard time | 71 | 0.088 (-0.142 to 0.336) |
| 40-yard time vs. rookie mean tracked speed | 71 | -0.715 (-0.798 to -0.602) |
| Combine pass-rush mean acceleration vs. rookie mean acceleration | 91 | 0.490 (0.315 to 0.624) |
| Combine pass-rush peak speed vs. career total snaps | 91 | 0.299 (0.079 to 0.472) |

The unadjusted-for-40 sensor association is positive after draft-cohort adjustment. However, the partial association is small and its interval includes zero. In this sample, Combine pass-rush peak speed does **not** show a clear residual association with rookie mean speed beyond the timed 40. The negative 40-yard correlation is directionally expected: lower times correspond to faster tracked movement.

![Combine pass-rush peak speed and rookie-season mean tracked speed, by draft cohort](../reports/figures/combine_to_rookie_tracking.png)

![Complete-case players by draft cohort](../reports/figures/cohort_coverage.png)

## Scouting implications

Treat Combine sensor speed as a promising description of drill movement, not as a standalone draft grade. The main cohort-adjusted association warrants follow-up, but the attenuation after controlling for the 40-yard result does not support claiming that peak speed adds established scouting value. A team could use this analysis to motivate position-specific video review and a pre-registered validation study, not to rank prospects from this coefficient.

## Limitations

- This is an observational association; it does not establish that Combine movement causes NFL performance.
- Rookie mean speed is exposure- and role-dependent, is not a measure of universal player quality, and does not account for scheme, assignment, play type, or opportunity.
- The selected sample comprises only three draft classes and is selected for data coverage; missing tracking may not be random.
- The 40-yard comparison has fewer complete cases (71). Bootstrap intervals describe sampling variability within this selected cohort, not uncertainty from selection, measurement, confounding, or future classes.
- Career snap totals have unequal follow-up and are secondary outcomes only. No predictive model was trained or evaluated.

## Reproducibility

The public-notebook companion is [`notebooks/gridiron_iq.ipynb`](../notebooks/gridiron_iq.ipynb). Attach the official NFL Big Data Bowl 2027 dataset as notebook input, run all cells, and verify the generated figures and association table before publication. In this repository, the full streaming audit and analysis can be rerun with:

```text
.\.venv312\Scripts\python.exe -m gridiron_iq.pipeline --data-dir C:\GridironIQ-data\nfl-big-data-bowl-2027
.\.venv312\Scripts\python.exe -m pytest -q
```

Official sources: [competition overview and evaluation](https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/overview), [official data](https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/data), and [rules](https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/rules). The authenticated Kaggle CLI listed the deadline as **2027-01-06 23:59:00**, without specifying a timezone.

**Data attribution and license:** NFL Big Data Bowl 2027 competition data,
accessed from the [official Kaggle data page](https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/data),
which lists [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/).
This research and its derived figures are shared for non-commercial purposes
with attribution. Raw competition files and player-level analysis rows are not
included in the public project repository.
