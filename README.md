# GridironIQ

GridironIQ is a reproducible NFL Big Data Bowl 2027 research pipeline. It audits
the official Combine and regular-season tracking files, creates player-level
movement summaries, measures identifier coverage, and evaluates a small,
position-specific Combine-to-rookie tracking relationship.

## Competition objective

The official 2027 Big Data Bowl asks for an analytical framework linking 10 Hz
Combine sensor tracking to future regular-season NFL performance. It is a
human-evaluated write-up challenge, not a prediction leaderboard. The published
evaluation requires an explicit Combine-to-NFL linkage and a complete write-up
with readable markdown, embedded visuals, and an attached public Kaggle
Notebook. Four components are scored: Football (30%), Data Science (30%),
Write-up (20%), and Data Visualization (20%). See the [official overview](
https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/overview),
[data page](https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/data),
and [rules](https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/rules).

The official download has nine CSV files and no sample prediction-submission
file. This project therefore produces research tables, figures, and a report;
it does not invent a prediction schema, create a prediction submission, or
publish a Kaggle write-up/notebook.

## Project structure

```text
configs/                    Project guardrails and path configuration
reports/audit/              Download inventory and data provenance
reports/tables/             Quality, join, cohort, and association tables
reports/figures/            Reproducible visualizations
reports/research_report.md  Findings and methods
notebooks/                  Kaggle-ready analysis notebook
src/gridiron_iq/            Reusable audit, feature, and analysis code
tests/                      Unit tests for validation and transformations
writeup/                    Submission draft and publishing checklist
```

Raw competition data stays outside the Git repository at
`C:\GridironIQ-data\nfl-big-data-bowl-2027`. The pipeline reads source CSVs in
chunks, never modifies them, and writes only small audit/analysis outputs into
the project. The Kaggle data page lists the official competition data under
[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/). This repository
attributes the data source and shares only project code, documentation, and
figures derived from the competition data; it does not include raw files or
player-level analysis tables.

## Environment

The tested interpreter is Python 3.12 in `.venv312`. From the project root:

```powershell
.\.venv312\Scripts\python.exe -m pip install -e .
```

The existing environment and dependency declarations are retained; no extra
packages are required for the pipeline.

## Data access and integrity

Kaggle authentication must be configured locally and must never be copied into
the repository or chat. Check access and download the official archive:

```powershell
.\.venv312\Scripts\kaggle.exe competitions files -c nfl-big-data-bowl-2027
New-Item -ItemType Directory -Force C:\GridironIQ-data | Out-Null
.\.venv312\Scripts\kaggle.exe competitions download nfl-big-data-bowl-2027 -p C:\GridironIQ-data
Expand-Archive -LiteralPath C:\GridironIQ-data\nfl-big-data-bowl-2027.zip -DestinationPath C:\GridironIQ-data -Force
```

The installed Kaggle CLI resumes its existing partial archive when rerun. Keep
the extracted folder outside the repository. The pipeline records listed and
actual byte sizes, SHA-256, row counts, verified headers, missingness, duplicate
keys, numeric range checks, player-ID joins, and rookie-season regular-season
tracking coverage. Its default data location is the extracted folder above; it
can be overridden with `--data-dir` or `GRIDIRON_IQ_DATA_DIR`.

## Run the full pipeline

```powershell
.\.venv312\Scripts\python.exe -m gridiron_iq.pipeline --data-dir C:\GridironIQ-data\nfl-big-data-bowl-2027
```

Optional flags:

```text
--reports-dir reports
--chunksize 200000
--bootstrap-replicates 1000
```

The pipeline selects the most-covered exact position/drill-category/drill cohort
by availability only (not by the observed association), requires at least 100
rookie-season tracking frames and a career-snap summary per player, and compares
Combine movement with rookie-year tracking and career snaps. It uses only
regular-season tracking from the player's draft-year season. Associations are
exploratory, rank-based, cohort-adjusted, and accompanied by cohort-stratified
player-bootstrap intervals. They are not causal estimates or out-of-sample
predictions.

## Current results from official data

For the coverage-selected DL / `SKILL_DRILLS_DL` / `PASS_RUSH_DRILL` cohort
(`n=91`; 27, 27, and 37 players for 2023-2025), Combine peak speed had a
cohort-adjusted rank correlation of **0.579** with rookie mean tracked speed
(player-bootstrap 95% interval **0.423 to 0.706**). After additionally
controlling for 40-yard time, the partial correlation was **0.088**
(95% interval **-0.142 to 0.336**, `n=71`); this interval includes zero and
does not establish a clear association beyond the timed 40. The 40-yard-time
baseline correlation with rookie mean speed was **-0.715** (95% interval
**-0.798 to -0.602**, `n=71`). These are exploratory associations, not causal
effects or held-out prediction results. See the full
[research report](reports/research_report.md) for methods, figures, cohort
coverage, secondary results, and limitations.

The standalone [Kaggle-ready notebook](notebooks/gridiron_iq.ipynb) discovers
the attached competition data, validates file sizes and key schemas, streams
large tracking files, recomputes the analysis, and saves figures and result CSVs.
The submission draft and exact manual upload steps are in
[final_submission.md](writeup/final_submission.md) and
[PUBLISHING_CHECKLIST.md](writeup/PUBLISHING_CHECKLIST.md).

## Tests and dependency check

```powershell
.\.venv312\Scripts\python.exe -m pytest -q
.\.venv312\Scripts\python.exe -m pip check
```

Tests use small in-memory fixtures only; fixture values are not reported as NFL
findings. The full analysis report and figures are generated by the real-data
pipeline and identify any insufficient-coverage conditions explicitly.

## Competition timing and release

The authenticated Kaggle CLI listed the deadline as
`2027-01-06 23:59:00`; the CLI output does not specify a timezone. A final
competition submission requires the official write-up format and an attached
public Kaggle Notebook. Creating, uploading, or publishing those artifacts
requires explicit authorization and is not performed by this local pipeline.
