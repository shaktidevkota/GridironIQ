import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gridiron_iq.validation import (  # noqa: E402
    assert_no_missing_key_values,
    assert_unique_key,
    require_columns,
    validate_temporal_order,
)


class ValidationTests(unittest.TestCase):
    def test_require_columns_reports_missing_columns(self):
        frame = pd.DataFrame({"a": [1]})
        with self.assertRaisesRegex(ValueError, "Missing required columns"):
            require_columns(frame, ["a", "b"])

    def test_assert_unique_key_accepts_unique_rows(self):
        frame = pd.DataFrame({"game_id": [1, 1], "play_id": [1, 2]})
        assert_unique_key(frame, ["game_id", "play_id"])

    def test_assert_unique_key_rejects_duplicates(self):
        frame = pd.DataFrame({"game_id": [1, 1], "play_id": [1, 1]})
        with self.assertRaisesRegex(ValueError, "duplicate-key"):
            assert_unique_key(frame, ["game_id", "play_id"])

    def test_assert_no_missing_key_values_rejects_nulls(self):
        frame = pd.DataFrame({"game_id": [1, None], "play_id": [1, 2]})
        with self.assertRaisesRegex(ValueError, "Missing key values"):
            assert_no_missing_key_values(frame, ["game_id", "play_id"])

    def test_validate_temporal_order_accepts_sorted_rows(self):
        frame = pd.DataFrame(
            {"game_id": [1, 1, 2], "frame_id": [1, 2, 1], "x": [0, 1, 2]}
        )
        validate_temporal_order(frame, ["game_id"], "frame_id")

    def test_validate_temporal_order_rejects_unsorted_rows(self):
        frame = pd.DataFrame({"game_id": [1, 1], "frame_id": [2, 1]})
        with self.assertRaisesRegex(ValueError, "not sorted"):
            validate_temporal_order(frame, ["game_id"], "frame_id")


if __name__ == "__main__":
    unittest.main()
