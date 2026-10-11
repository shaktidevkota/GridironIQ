"""Submission-file validation primitives.

The official 2027 schema is not assumed here. Callers must pass the exact
columns from the official sample submission once it is available.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from gridiron_iq.validation import (
    assert_no_missing_key_values,
    assert_unique_key,
    require_columns,
)


def validate_submission_frame(
    submission: pd.DataFrame,
    required_columns: Sequence[str],
    key_columns: Sequence[str],
) -> None:
    """Validate schema, missing keys, duplicate keys, and finite predictions."""

    require_columns(submission, required_columns)
    assert_no_missing_key_values(submission, key_columns)
    assert_unique_key(submission, key_columns)

    prediction_columns = [
        column for column in required_columns if column not in set(key_columns)
    ]
    for column in prediction_columns:
        if pd.api.types.is_numeric_dtype(submission[column]):
            invalid = submission[column].isna() | ~submission[column].map(pd.notna)
            if invalid.any():
                raise ValueError(f"Prediction column {column!r} contains invalid values.")


def validate_submission_csv(
    path: Path,
    required_columns: Sequence[str],
    key_columns: Sequence[str],
) -> None:
    """Load and validate a submission CSV."""

    validate_submission_frame(pd.read_csv(path), required_columns, key_columns)
