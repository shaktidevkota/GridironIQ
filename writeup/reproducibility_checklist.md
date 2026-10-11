# Reproducibility Checklist

## Environment and source data

- [x] Use the project `.venv312` Python 3.12 environment.
- [x] Use the authenticated official Kaggle CLI for the data download.
- [x] Keep downloaded archives and extracted competition CSVs outside Git at
  `C:\GridironIQ-data`.
- [x] Record official filenames, actual/listed sizes, SHA-256, headers, and
  retrieval date.
- [x] Read large tracking files in bounded chunks and keep source files immutable.

## Re-run

From the repository root:

```powershell
.\.venv312\Scripts\python.exe -m gridiron_iq.pipeline --data-dir C:\GridironIQ-data\nfl-big-data-bowl-2027
.\.venv312\Scripts\python.exe -m pytest -q
.\.venv312\Scripts\python.exe -m pip check
```

The analysis can also be directed to another official-data folder with
`--data-dir`, and the CSV read size and bootstrap count can be changed with
`--chunksize` and `--bootstrap-replicates`.

## Analytical safeguards

- [x] Join players only on `nfl_id`; retain `draft_year` for Combine rows.
- [x] Check key duplicates, missing keys, schema, value ranges, and join coverage.
- [x] Use only rookie-year regular-season tracking for the primary game outcome.
- [x] Select the position/drill cohort by complete-case coverage, not by outcome
  association.
- [x] Adjust associations for draft cohort and compare the sensor metric with
  the 40-yard time.
- [x] Report uncertainty and distinguish descriptive associations from causal
  or predictive claims.
- [x] Do not create a prediction submission without an official schema.
- [ ] Attach a public Kaggle Notebook and publish a competition write-up; this
  requires an explicit publication decision and is not done by the local
  pipeline.
