"""Streaming integrity and identifier audit for the official competition CSVs."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd


OFFICIAL_FILES = {
    "combine_results.csv": 41020,
    "combine_tracking.csv": 83788174,
    "game_tracking_2023.csv": 335463637,
    "game_tracking_2024.csv": 717952893,
    "game_tracking_2025.csv": 1022575093,
    "games.csv": 43174,
    "player_career_successes.csv": 13801,
    "player_play.csv": 146879042,
    "players.csv": 47301,
}

EXPECTED_COLUMNS = {
    "combine_results.csv": [
        "draft_year", "nfl_id", "combine_position", "combine_height",
        "combine_weight", "hand_size", "arm_length", "wing_span",
        "ten_yd_split", "forty", "vertical", "broad_jump", "three_cone",
        "short_shuttle", "bench_reps", "ngs_athleticism_score",
        "ngs_college_production_score", "ngs_final_score",
    ],
    "combine_tracking.csv": [
        "draft_year", "event_id", "nfl_id", "entity_type", "time",
        "drill_type", "drill_name", "attempt", "x", "y", "s", "a",
        "dis", "dir",
    ],
    "game_tracking_2023.csv": [
        "game_id", "play_id", "nfl_id", "time", "x", "y", "s", "a",
        "dis", "o", "dir", "event",
    ],
    "game_tracking_2024.csv": [
        "game_id", "play_id", "nfl_id", "time", "x", "y", "s", "a",
        "dis", "o", "dir", "event",
    ],
    "game_tracking_2025.csv": [
        "game_id", "play_id", "nfl_id", "time", "x", "y", "s", "a",
        "dis", "o", "dir", "event",
    ],
    "games.csv": [
        "game_id", "game_key", "season", "season_type", "week",
        "home_team_abbr", "visitor_team_abbr",
    ],
    "player_career_successes.csv": [
        "nfl_id", "career_offensive_snaps", "career_defensive_snaps",
        "career_special_teams_snaps", "career_games_active",
        "career_games_started", "ap_all_pro_1st_team",
        "ap_all_pro_2nd_team", "pro_bowl_original_ballot",
    ],
    "player_play.csv": [
        "game_id", "play_id", "team_abbr", "nfl_id", "lined_up_position",
        "play_description", "quarter", "down", "yards_to_go",
        "possession_team", "yardline_side", "yardline_number", "game_clock",
        "pre_snap_home_score", "pre_snap_visitor_score", "play_direction",
        "pre_snap_home_team_win_probability",
        "pre_snap_visitor_team_win_probability",
        "home_team_win_probability_added",
        "visitor_team_win_probility_added", "expected_points_added",
        "expected_points", "offense_formation", "receiver_alignment",
        "pass_result", "pass_length", "play_nullified_by_penalty",
        "penalty_yards", "pre_penalty_yards_gained", "yards_gained",
        "team_coverage_man_zone", "team_coverage_type",
        "in_motion_at_ball_snap", "target", "rec_yards", "rush_yards",
        "yards_after_catch", "fumble", "fumble_lost", "route_ran",
        "separation_at_pass_forward", "cushion",
        "expected_yards_after_catch", "dropback_duration",
        "extended_sack_allowed", "pass_rushers_encountered",
        "peak_pressure_probability_allowed", "pressure_allowed",
        "sack_allowed", "time_to_pressure_allowed", "quick_pressure",
        "unblocked_pressure", "blitzing", "player_get_off", "sack",
        "tackle", "assist", "caused_forced_fumble", "recovered_fumble",
        "tackle_for_loss", "time_to_pressure", "time_to_qb_hurry",
        "coverage_assignment", "coverage_assignment_at_snap",
    ],
    "players.csv": [
        "nfl_id", "display_name", "draft_year", "nfl_position", "birth_date",
        "college_name", "college_conference", "draft_round",
        "draft_pick_within_round", "draft_overall_pick",
    ],
}

KEY_COLUMNS = {
    "combine_results.csv": ["draft_year", "nfl_id"],
    "combine_tracking.csv": [
        "event_id", "nfl_id", "entity_type", "drill_type", "drill_name",
        "attempt", "time",
    ],
    "game_tracking_2023.csv": ["game_id", "play_id", "nfl_id", "time"],
    "game_tracking_2024.csv": ["game_id", "play_id", "nfl_id", "time"],
    "game_tracking_2025.csv": ["game_id", "play_id", "nfl_id", "time"],
    "games.csv": ["game_id"],
    "player_career_successes.csv": ["nfl_id"],
    "player_play.csv": ["game_id", "play_id", "nfl_id"],
    "players.csv": ["nfl_id"],
}

_HASH_KEYS = ("0123456789abcdef", "fedcba9876543210")


def _check_interpretation(check: str) -> str:
    if check.startswith("x_outside_") or check.startswith("y_outside_"):
        return (
            "Outside nominal playing-surface bounds; retained because tracking can "
            "include out-of-play locations."
        )
    if check == "a_negative_rows":
        return (
            "Negative acceleration values are reported, not dropped; the source "
            "does not document whether acceleration is signed."
        )
    if check.startswith("entity_type_"):
        return "Entity-type counts; only PLAYER rows are used for Combine features."
    if check == "invalid_time_rows":
        return "Rows whose source timestamp could not be parsed."
    if check.endswith("_negative_rows"):
        return "Negative speed or distance values; these are reviewed as anomalies."
    if check == "dir_outside_0_360":
        return "Direction values outside the expected degree range."
    if check.endswith("_infinite_rows"):
        return "Infinite numeric values; missing values are reported separately."
    return "Range or integrity check; inspect the source summary before excluding rows."


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _hashed_keys(frame: pd.DataFrame, columns: list[str]) -> np.ndarray:
    keys = frame.loc[:, columns].dropna()
    hashes = np.empty(
        len(keys),
        dtype=[("first", "<u8"), ("second", "<u8")],
    )
    for index, hash_key in enumerate(_HASH_KEYS):
        hashes["first" if index == 0 else "second"] = (
            pd.util.hash_pandas_object(
                keys, index=False, hash_key=hash_key
            ).to_numpy(dtype=np.uint64)
        )
    return hashes


def _duplicate_key_rows(parts: list[np.ndarray]) -> int:
    if not parts:
        return 0
    hashes = np.concatenate(parts)
    if len(hashes) < 2:
        return 0
    hashes.sort(order=["first", "second"])
    repeated = (
        (hashes["first"][1:] == hashes["first"][:-1])
        & (hashes["second"][1:] == hashes["second"][:-1])
    )
    return int(repeated.sum())


def _merge_game_stats(
    summary: dict[int, dict[str, float]],
    games_seen: dict[int, set[int]],
    frame: pd.DataFrame,
    game_seasons: dict[int, int],
    game_types: dict[int, str],
    draft_year_by_id: dict[int, int],
) -> None:
    if frame.empty:
        return

    rows = frame[["game_id", "nfl_id", "s", "a", "dis"]].copy()
    rows["season"] = rows["game_id"].map(game_seasons)
    rows["season_type"] = rows["game_id"].map(game_types)
    rows["draft_year"] = rows["nfl_id"].map(draft_year_by_id)
    rookie = rows.loc[
        rows["season_type"].eq("REG")
        & rows["season"].eq(rows["draft_year"])
        & rows["nfl_id"].notna()
    ]
    if rookie.empty:
        return
    for nfl_id, game_id in rookie[["nfl_id", "game_id"]].drop_duplicates().itertuples(
        index=False, name=None
    ):
        games_seen.setdefault(int(nfl_id), set()).add(int(game_id))

    grouped = rookie.groupby("nfl_id", sort=False).agg(
        frame_count=("nfl_id", "size"),
        speed_count=("s", "count"),
        speed_sum=("s", "sum"),
        max_speed=("s", "max"),
        acceleration_count=("a", "count"),
        acceleration_sum=("a", "sum"),
        distance_sum=("dis", "sum"),
    )
    for nfl_id, values in grouped.iterrows():
        key = int(nfl_id)
        aggregate = summary.setdefault(
            key,
            {
                "frame_count": 0,
                "speed_count": 0,
                "speed_sum": 0.0,
                "max_speed": float("nan"),
                "acceleration_count": 0,
                "acceleration_sum": 0.0,
                "distance_sum": 0.0,
            },
        )
        aggregate["frame_count"] += int(values["frame_count"])
        aggregate["speed_count"] += int(values["speed_count"])
        aggregate["speed_sum"] += float(values["speed_sum"])
        aggregate["acceleration_count"] += int(values["acceleration_count"])
        aggregate["acceleration_sum"] += float(values["acceleration_sum"])
        aggregate["distance_sum"] += float(values["distance_sum"])
        if pd.notna(values["max_speed"]):
            current_max = aggregate["max_speed"]
            aggregate["max_speed"] = (
                float(values["max_speed"])
                if pd.isna(current_max)
                else max(float(current_max), float(values["max_speed"]))
            )


def audit_official_data(
    data_dir: Path,
    *,
    chunksize: int = 200_000,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Audit all nine source files using bounded-memory CSV chunk reads.

    Duplicate composite keys are counted by two independent 64-bit pandas
    hashes (128 bits total) to avoid retaining large key tables in memory.
    """

    data_dir = data_dir.resolve()
    missing_files = sorted(set(OFFICIAL_FILES) - {p.name for p in data_dir.glob("*.csv")})
    if missing_files:
        raise FileNotFoundError(
            f"Missing official competition CSV files in {data_dir}: {missing_files}"
        )

    combine = pd.read_csv(data_dir / "combine_results.csv")
    if combine.duplicated(["draft_year", "nfl_id"]).any():
        raise ValueError("combine_results.csv has duplicate (draft_year, nfl_id) keys.")
    draft_year_by_id = {
        int(nfl_id): int(year)
        for nfl_id, year in combine[["nfl_id", "draft_year"]].itertuples(
            index=False, name=None
        )
    }
    games = pd.read_csv(
        data_dir / "games.csv",
        usecols=["game_id", "season", "season_type"],
    )
    if games["game_id"].duplicated().any():
        raise ValueError("games.csv has duplicate game_id values.")
    game_seasons = dict(zip(games["game_id"], games["season"], strict=True))
    game_types = dict(zip(games["game_id"], games["season_type"], strict=True))

    inventory: list[dict[str, Any]] = []
    quality: list[dict[str, Any]] = []
    value_checks: list[dict[str, Any]] = []
    player_ids: dict[str, set[int]] = {}
    game_ids_by_file: dict[str, set[int]] = {}
    rookie_summary: dict[int, dict[str, float]] = {}
    rookie_games: dict[int, set[int]] = {}

    for filename in sorted(OFFICIAL_FILES):
        path = data_dir / filename
        if not path.is_file():
            raise FileNotFoundError(f"Missing official file: {path}")
        if progress:
            progress(f"Auditing {filename} ({path.stat().st_size:,} bytes)")
        header = list(pd.read_csv(path, nrows=0).columns)
        expected_columns = EXPECTED_COLUMNS[filename]
        header_matches = header == expected_columns
        key_columns = KEY_COLUMNS[filename]
        missing_key_rows = 0
        hashes: list[np.ndarray] = []
        missing_counts: defaultdict[str, int] = defaultdict(int)
        dtype_values: defaultdict[str, set[str]] = defaultdict(set)
        column_min: dict[str, float] = {}
        column_max: dict[str, float] = {}
        checks: defaultdict[str, int] = defaultdict(int)
        row_count = 0
        ids: set[int] = set()
        game_ids: set[int] = set()
        next_progress_row = 1_000_000

        for chunk in pd.read_csv(path, chunksize=chunksize):
            row_count += len(chunk)
            if progress and row_count >= next_progress_row:
                progress(f"  {row_count:,} rows read from {filename}")
                next_progress_row = ((row_count // 1_000_000) + 1) * 1_000_000
            for column in header:
                missing_counts[column] += int(chunk[column].isna().sum())
                dtype_values[column].add(str(chunk[column].dtype))

            numeric = chunk.select_dtypes(include=[np.number])
            for column in numeric:
                values = numeric[column].replace([np.inf, -np.inf], np.nan)
                if values.notna().any():
                    minimum = float(values.min())
                    maximum = float(values.max())
                    column_min[column] = min(column_min.get(column, minimum), minimum)
                    column_max[column] = max(column_max.get(column, maximum), maximum)
                checks[f"{column}_infinite_rows"] += int(
                    np.isinf(numeric[column].to_numpy(dtype=float, na_value=np.nan)).sum()
                )

            if "nfl_id" in chunk:
                id_values = pd.to_numeric(chunk["nfl_id"], errors="coerce").dropna()
                ids.update(id_values.astype("int64").unique().tolist())
            if "game_id" in chunk:
                game_id_values = pd.to_numeric(
                    chunk["game_id"], errors="coerce"
                ).dropna()
                game_ids.update(game_id_values.astype("int64").unique().tolist())

            key_frame = chunk[key_columns]
            missing_key_rows += int(key_frame.isna().any(axis=1).sum())
            hashes.append(_hashed_keys(chunk, key_columns))

            if filename.startswith("game_tracking_"):
                _merge_game_stats(
                    rookie_summary,
                    rookie_games,
                    chunk,
                    game_seasons,
                    game_types,
                    draft_year_by_id,
                )

            for column in ("x", "y", "s", "a", "dis", "dir"):
                if column not in chunk:
                    continue
                numeric_values = pd.to_numeric(chunk[column], errors="coerce")
                if column == "x" and filename.startswith("game_tracking_"):
                    checks["x_outside_0_120"] += int(
                        ((numeric_values < 0) | (numeric_values > 120)).sum()
                    )
                elif column == "y" and filename.startswith("game_tracking_"):
                    checks["y_outside_0_53_333"] += int(
                        ((numeric_values < 0) | (numeric_values > 53.333)).sum()
                    )
                elif column in {"s", "dis"}:
                    checks[f"{column}_negative_rows"] += int((numeric_values < 0).sum())
                elif column == "a":
                    checks["a_negative_rows"] += int((numeric_values < 0).sum())
                elif column == "dir":
                    checks["dir_outside_0_360"] += int(
                        ((numeric_values < 0) | (numeric_values > 360)).sum()
                    )

            if filename == "combine_tracking.csv":
                entity_counts = chunk["entity_type"].value_counts(dropna=False)
                for entity_type, count in entity_counts.items():
                    checks[f"entity_type_{entity_type}_rows"] += int(count)
                checks["entity_type_other_rows"] += int(
                    (~chunk["entity_type"].isin(["PLAYER", "BALL"])).sum()
                )

            if "time" in chunk:
                invalid_time = pd.to_datetime(chunk["time"], errors="coerce").isna()
                checks["invalid_time_rows"] += int(invalid_time.sum())

        if "nfl_id" in header:
            player_ids[filename] = ids
        if "game_id" in header:
            game_ids_by_file[filename] = game_ids
        actual_size = path.stat().st_size
        inventory.append(
            {
                "filename": filename,
                "rows": row_count,
                "size_bytes": actual_size,
                "kaggle_listed_size_bytes": OFFICIAL_FILES[filename],
                "size_matches_kaggle_listing": actual_size == OFFICIAL_FILES[filename],
                "sha256": _sha256(path),
                "header_matches_verified_schema": header_matches,
                "columns": "|".join(header),
                "duplicate_key_rows": _duplicate_key_rows(hashes),
                "missing_key_rows": missing_key_rows,
                "player_id_count": len(ids),
            }
        )
        if not header_matches:
            quality.append(
                {
                    "filename": filename,
                    "column": "__header__",
                    "dtype": "",
                    "missing_count": "",
                    "missing_pct": "",
                    "expected_columns": "|".join(expected_columns),
                    "actual_columns": "|".join(header),
                }
            )
        for column in header:
            missing = missing_counts[column]
            quality.append(
                {
                    "filename": filename,
                    "column": column,
                    "dtype": "|".join(sorted(dtype_values[column])),
                    "missing_count": missing,
                    "missing_pct": round(100 * missing / row_count, 4)
                    if row_count
                    else 0.0,
                    "min": column_min.get(column),
                    "max": column_max.get(column),
                    "expected_columns": "",
                    "actual_columns": "",
                }
            )
        for check, count in sorted(checks.items()):
            value_checks.append(
                {
                    "filename": filename,
                    "check": check,
                    "rows_flagged": count,
                    "interpretation": _check_interpretation(check),
                }
            )

    cohort_rows = combine[["nfl_id", "draft_year"]].drop_duplicates()
    join_coverage: list[dict[str, Any]] = []
    sources = {
        name.removesuffix(".csv"): ids for name, ids in player_ids.items()
        if name != "combine_results.csv"
    }
    sources["rookie_regular_season_tracking"] = set(rookie_summary)
    for year in sorted(cohort_rows["draft_year"].unique()):
        cohort_ids = set(
            cohort_rows.loc[cohort_rows["draft_year"].eq(year), "nfl_id"]
            .astype("int64")
            .tolist()
        )
        for source, ids in sources.items():
            if source.startswith("game_tracking_"):
                source_year = source.rsplit("_", 1)[-1]
                if source_year != str(int(year)):
                    continue
            matched = len(cohort_ids & ids)
            join_coverage.append(
                {
                    "draft_year": int(year),
                    "source": source,
                    "combine_players": len(cohort_ids),
                    "matched_players": matched,
                    "unmatched_players": len(cohort_ids) - matched,
                    "coverage_pct": round(100 * matched / len(cohort_ids), 2)
                    if cohort_ids
                    else 0.0,
                }
            )

    known_game_ids = set(games["game_id"].astype("int64"))
    game_join_coverage = []
    for filename, ids in sorted(game_ids_by_file.items()):
        if not filename.startswith("game_tracking_"):
            continue
        matched = len(ids & known_game_ids)
        game_join_coverage.append(
            {
                "filename": filename,
                "tracking_game_ids": len(ids),
                "matched_games_table_ids": matched,
                "unmatched_game_ids": len(ids) - matched,
                "coverage_pct": round(100 * matched / len(ids), 2) if ids else 0.0,
            }
        )

    rookie_tracking = []
    for nfl_id, values in sorted(rookie_summary.items()):
        speed_count = int(values["speed_count"])
        acceleration_count = int(values["acceleration_count"])
        rookie_tracking.append(
            {
                "nfl_id": nfl_id,
                "draft_year": draft_year_by_id.get(nfl_id),
                "rookie_regular_season_games": len(rookie_games.get(nfl_id, set())),
                "rookie_regular_season_frames": int(values["frame_count"]),
                "speed_observations": speed_count,
                "mean_speed": values["speed_sum"] / speed_count
                if speed_count
                else np.nan,
                "max_speed": values["max_speed"],
                "acceleration_observations": acceleration_count,
                "mean_acceleration": values["acceleration_sum"] / acceleration_count
                if acceleration_count
                else np.nan,
                "tracked_distance_sum": values["distance_sum"],
            }
        )
    rookie_tracking_frame = pd.DataFrame(
        rookie_tracking,
        columns=[
            "nfl_id",
            "draft_year",
            "rookie_regular_season_games",
            "rookie_regular_season_frames",
            "speed_observations",
            "mean_speed",
            "max_speed",
            "acceleration_observations",
            "mean_acceleration",
            "tracked_distance_sum",
        ],
    )
    if rookie_tracking_frame.empty:
        rookie_tracking_frame = rookie_tracking_frame.astype(
            {"nfl_id": "int64", "draft_year": "int64"}
        )

    return {
        "inventory": pd.DataFrame(inventory),
        "quality": pd.DataFrame(quality),
        "value_checks": pd.DataFrame(value_checks),
        "join_coverage": pd.DataFrame(join_coverage),
        "game_join_coverage": pd.DataFrame(game_join_coverage),
        "rookie_tracking": rookie_tracking_frame,
        "player_ids": player_ids,
    }
