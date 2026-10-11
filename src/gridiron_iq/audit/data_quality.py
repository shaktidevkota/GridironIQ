"""Generic tabular data-quality summaries for official files after download."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


SUPPORTED_SUFFIXES = {".csv", ".parquet"}


def load_table(path: Path) -> pd.DataFrame:
    """Load a supported tabular file."""

    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported file type {suffix!r}; supported: {SUPPORTED_SUFFIXES}")


def summarize_frame(frame: pd.DataFrame) -> dict[str, object]:
    """Return a JSON-serializable summary for a dataframe."""

    missing = frame.isna().sum()
    return {
        "rows": int(len(frame)),
        "columns": int(len(frame.columns)),
        "column_names": list(frame.columns),
        "dtypes": {column: str(dtype) for column, dtype in frame.dtypes.items()},
        "missing_values": {
            column: int(count) for column, count in missing.items() if int(count) > 0
        },
        "duplicate_rows": int(frame.duplicated().sum()),
    }


def summarize_file(path: Path) -> dict[str, object]:
    """Load and summarize one supported file."""

    frame = load_table(path)
    return {"path": str(path), **summarize_frame(frame)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/audit/data_quality_summary.json"),
    )
    args = parser.parse_args()

    summary = summarize_file(args.path)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
