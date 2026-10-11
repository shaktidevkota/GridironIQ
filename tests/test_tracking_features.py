import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gridiron_iq.features.tracking import (  # noqa: E402
    euclidean_distance,
    finite_difference,
    path_efficiency,
    path_length,
    turning_angle_degrees,
)


class TrackingFeatureTests(unittest.TestCase):
    def test_euclidean_distance_uses_field_coordinates(self):
        self.assertEqual(euclidean_distance(0, 0, 3, 4), 5)

    def test_path_length_sums_ordered_segments(self):
        self.assertEqual(path_length([(0, 0), (3, 4), (6, 8)]), 10)

    def test_path_efficiency_is_displacement_over_distance(self):
        self.assertEqual(path_efficiency([(0, 0), (3, 4), (6, 8)]), 1)
        self.assertEqual(path_efficiency([(0, 0), (1, 0), (0, 0)]), 0)

    def test_path_efficiency_returns_none_when_no_movement(self):
        self.assertIsNone(path_efficiency([(1, 1)]))
        self.assertIsNone(path_efficiency([(1, 1), (1, 1)]))

    def test_finite_difference_uses_observed_time_delta(self):
        self.assertEqual(finite_difference([0, 2, 5], [0, 0.5, 2.0]), [None, 4.0, 2.0])

    def test_finite_difference_rejects_mismatched_lengths(self):
        with self.assertRaisesRegex(ValueError, "same length"):
            finite_difference([1, 2], [1])

    def test_finite_difference_flags_non_increasing_time(self):
        self.assertEqual(finite_difference([0, 1, 2], [0, 0, -1]), [None, None, None])

    def test_turning_angle_degrees_handles_right_angle_and_zero_segments(self):
        self.assertEqual(round(turning_angle_degrees((0, 0), (1, 0), (1, 1)), 6), 90)
        self.assertIsNone(turning_angle_degrees((1, 0), (1, 0), (1, 1)))


if __name__ == "__main__":
    unittest.main()
