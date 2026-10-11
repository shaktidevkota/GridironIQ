import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gridiron_iq.audit.competition_data import (  # noqa: E402
    _duplicate_key_rows,
    _hashed_keys,
)
from gridiron_iq.research import (  # noqa: E402
    adjusted_rank_correlation,
    aggregate_combine_tracking,
    bootstrap_adjusted_rank_correlation,
    _select_drill_cohort,
)


class ResearchPipelineTests(unittest.TestCase):
    def test_drill_selection_does_not_mix_drill_type_categories(self):
        candidates = pd.DataFrame(
            {
                "combine_position": ["DL", "DL", "DL"],
                "drill_type": ["SKILL_DRILLS_DL", "SKILL_DRILLS_LB", "SKILL_DRILLS_DL"],
                "drill_name": ["PASS_RUSH_DRILL"] * 3,
                "draft_year": [2023, 2023, 2024],
                "nfl_id": [1, 2, 3],
                "complete_case": [True, True, True],
            }
        )

        selected = _select_drill_cohort(
            candidates, "DL", "SKILL_DRILLS_DL", "PASS_RUSH_DRILL"
        )

        self.assertEqual(selected["nfl_id"].tolist(), [1, 3])

    def test_combine_tracking_aggregation_is_time_ordered_and_attempt_aware(self):
        rows = pd.DataFrame(
            {
                "draft_year": [2024] * 5,
                "nfl_id": [10] * 5,
                "entity_type": ["PLAYER", "PLAYER", "PLAYER", "PLAYER", "BALL"],
                "time": [
                    "2024-03-01T00:00:00.100",
                    "2024-03-01T00:00:00.000",
                    "2024-03-01T00:00:01.100",
                    "2024-03-01T00:00:01.000",
                    "2024-03-01T00:00:00.000",
                ],
                "drill_type": ["SKILL_DRILLS_DB"] * 5,
                "drill_name": ["BREAK"] * 5,
                "attempt": [1, 1, 2, 2, 1],
                "x": [1.0, 0.0, 3.0, 1.0, 100.0],
                "y": [0.0] * 5,
                "s": [2.0, 1.0, 4.0, 3.0, 99.0],
                "a": [0.4, 0.2, 0.8, 0.6, 99.0],
            }
        )

        result = aggregate_combine_tracking(rows)

        self.assertEqual(len(result), 1)
        self.assertEqual(result.loc[0, "attempt_count"], 2)
        self.assertEqual(result.loc[0, "frame_count"], 4)
        self.assertEqual(result.loc[0, "combine_peak_speed"], 3.0)
        self.assertAlmostEqual(result.loc[0, "combine_path_efficiency"], 1.0)

    def test_combine_tracking_requires_real_timestamp_and_keys(self):
        rows = pd.DataFrame(
            {
                "draft_year": [2024],
                "nfl_id": [10],
                "entity_type": ["PLAYER"],
                "time": ["invalid"],
                "drill_type": ["SKILL_DRILLS_DB"],
                "drill_name": ["BREAK"],
                "attempt": [1],
                "x": [0.0],
                "y": [0.0],
                "s": [1.0],
                "a": [0.1],
            }
        )
        with self.assertRaisesRegex(ValueError, "invalid timestamps"):
            aggregate_combine_tracking(rows)

    def test_cohort_adjusted_rank_correlation_removes_year_level_shift(self):
        frame = pd.DataFrame(
            {
                "draft_year": [2023] * 4 + [2024] * 4,
                "x": [1, 2, 3, 4, 101, 102, 103, 104],
                "y": [2, 4, 6, 8, 200, 202, 204, 206],
            }
        )
        self.assertAlmostEqual(adjusted_rank_correlation(frame, "x", "y"), 1.0)

    def test_bootstrap_interval_is_reproducible(self):
        frame = pd.DataFrame(
            {
                "draft_year": [2023] * 6 + [2024] * 6,
                "x": list(range(6)) + list(range(20, 26)),
                "y": [value * 2 for value in range(6)]
                + [value * 3 for value in range(20, 26)],
            }
        )
        first = bootstrap_adjusted_rank_correlation(
            frame, "x", "y", replicates=40, seed=7
        )
        second = bootstrap_adjusted_rank_correlation(
            frame, "x", "y", replicates=40, seed=7
        )
        np.testing.assert_allclose(first, second)

    def test_duplicate_key_hashes_find_duplicates_across_parts(self):
        first = _hashed_keys(
            pd.DataFrame({"game_id": [1, 1], "play_id": [10, 11]}),
            ["game_id", "play_id"],
        )
        second = _hashed_keys(
            pd.DataFrame({"game_id": [1, 2], "play_id": [10, 20]}),
            ["game_id", "play_id"],
        )
        self.assertEqual(_duplicate_key_rows([first, second]), 1)


if __name__ == "__main__":
    unittest.main()
