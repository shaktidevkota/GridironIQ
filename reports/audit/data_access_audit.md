# Official Data Access Audit

**Retrieved and verified:** 2026-10-11 (UTC)
**Competition:** [NFL Big Data Bowl 2027](https://www.kaggle.com/competitions/nfl-big-data-bowl-2027)
**Official data page:** https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/data
**Listed data license:** [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)

## Access and storage

The authenticated Kaggle CLI 2.2.4 successfully listed and downloaded the
official competition data. The complete archive is
`C:\GridironIQ-data\nfl-big-data-bowl-2027.zip` (512,718,566 bytes); ZIP CRC
validation passed. All extracted raw files are in
`C:\GridironIQ-data\nfl-big-data-bowl-2027`, outside the Git repository.

The official inventory and extracted file checks are recorded in the
[data inventory report](data_inventory.md) and
[machine-readable inventory](data_inventory.csv). Each of the nine listed CSV
files matched its official byte size and verified header. Combined extracted
size is 2,306,804,135 bytes and the files contain 23,434,208 data rows.

The verified files are:

- `combine_results.csv`
- `combine_tracking.csv`
- `game_tracking_2023.csv`
- `game_tracking_2024.csv`
- `game_tracking_2025.csv`
- `games.csv`
- `player_career_successes.csv`
- `player_play.csv`
- `players.csv`

## Reproducible access commands

From the project root, with local Kaggle authentication already configured:

```powershell
.\.venv312\Scripts\kaggle.exe competitions files -c nfl-big-data-bowl-2027
New-Item -ItemType Directory -Force C:\GridironIQ-data | Out-Null
.\.venv312\Scripts\kaggle.exe competitions download nfl-big-data-bowl-2027 -p C:\GridironIQ-data
Expand-Archive -LiteralPath C:\GridironIQ-data\nfl-big-data-bowl-2027.zip -DestinationPath C:\GridironIQ-data -Force
```

The CLI resumed an existing partial archive when rerun. Authentication inputs
were not printed, recorded, or copied into the repository. The environment
audit records only whether common credential indicators are present; their
absence does not contradict the successful authenticated CLI requests.

## Data handling

Raw source CSVs remain immutable and outside Git. The pipeline reads large
tracking files in chunks and records schemas, sizes, checksums, row counts,
missingness, duplicate composite keys, range checks, identifier linkage, and
rookie-season tracking coverage. No unofficial substitute data were used.
