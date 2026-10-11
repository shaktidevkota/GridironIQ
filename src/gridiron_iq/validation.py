"""Small validation helpers shared by data and submission checks."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import pandas as pd


def require_columns(frame: pd.DataFrame, required_columns: Iterable[str]) -> None:
    """Raise ValueError if a dataframe is missing required columns."""

    missing = [column for column in required_columns if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def assert_unique_key(frame: pd.DataFrame, key_columns: Sequence[str]) -> None:
    """Raise ValueError when key columns do not uniquely identify rows."""

    require_columns(frame, key_columns)
    duplicates = frame.duplicated(list(key_columns), keep=False)
    if duplicates.any():
        duplicate_count = int(duplicates.sum())
        raise ValueError(
            f"Key columns {list(key_columns)} are not unique; "
            f"{duplicate_count} duplicate-key rows found."
        )


def assert_no_missing_key_values(frame: pd.DataFrame, key_columns: Sequence[str]) -> None:
    """Raise ValueError when key columns contain missing values."""

    require_columns(frame, key_columns)
    missing_by_column = frame[list(key_columns)].isna().sum()
    missing = {
        column: int(count)
        for column, count in missing_by_column.items()
        if int(count) > 0
    }
    if missing:
        raise ValueError(f"Missing key values found: {missing}")


def validate_temporal_order(
    frame: pd.DataFrame,
    group_columns: Sequence[str],
    time_column: str,
) -> None:
    """Raise ValueError if time moves backward within any group."""

    require_columns(frame, [*group_columns, time_column])
    sorted_frame = frame.sort_values([*group_columns, time_column])
    original_order = frame[[*group_columns, time_column]].reset_index(drop=True)
    sorted_order = sorted_frame[[*group_columns, time_column]].reset_index(drop=True)
    if not original_order.equals(sorted_order):
        raise ValueError(
            f"Rows are not sorted by {list(group_columns)} then {time_column}."
        )
