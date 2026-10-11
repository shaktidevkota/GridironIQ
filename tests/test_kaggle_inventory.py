import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gridiron_iq.audit.kaggle_inventory import parse_competition_files_output  # noqa: E402


class KaggleInventoryTests(unittest.TestCase):
    def test_parse_competition_files_output_keeps_filename_and_size(self):
        output = """name,size,creationDate
-----------------------------
nfl-big-data-bowl-2027/players.csv 12KB 2026-01-01
nfl-big-data-bowl-2027/tracking.parquet 3GB 2026-01-01
"""
        rows = parse_competition_files_output(output, "nfl-big-data-bowl-2027")
        self.assertEqual(rows[0]["filename"], "players.csv")
        self.assertEqual(rows[0]["size"], "12KB")
        self.assertEqual(rows[1]["filename"], "tracking.parquet")
        self.assertEqual(rows[1]["competition"], "nfl-big-data-bowl-2027")


if __name__ == "__main__":
    unittest.main()
