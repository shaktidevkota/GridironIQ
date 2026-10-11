import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gridiron_iq.submission.validate import validate_submission_frame  # noqa: E402


class SubmissionValidationTests(unittest.TestCase):
    def test_validate_submission_frame_accepts_minimal_valid_schema(self):
        frame = pd.DataFrame({"row_id": [1, 2], "prediction": [0.1, 0.2]})
        validate_submission_frame(frame, ["row_id", "prediction"], ["row_id"])

    def test_validate_submission_frame_rejects_duplicate_keys(self):
        frame = pd.DataFrame({"row_id": [1, 1], "prediction": [0.1, 0.2]})
        with self.assertRaisesRegex(ValueError, "duplicate-key"):
            validate_submission_frame(frame, ["row_id", "prediction"], ["row_id"])

    def test_validate_submission_frame_rejects_missing_prediction_column(self):
        frame = pd.DataFrame({"row_id": [1, 2]})
        with self.assertRaisesRegex(ValueError, "Missing required columns"):
            validate_submission_frame(frame, ["row_id", "prediction"], ["row_id"])


if __name__ == "__main__":
    unittest.main()
