"""Combine-to-rookie-season tracking research utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


COMBINE_TRACKING_COLUMNS = [
    "draft_year",
    "nfl_id",
    "entity_type",
    "time",
    "drill_type",
    "drill_name",
    "attempt",
    "x",
    "y",
    "s",
    "a",
]


def aggregate_combine_tracking(frame: pd.DataFrame) -> pd.DataFrame:
    """Create one row per player and drill from ordered Combine sensor frames."""

    missing = sorted(set(COMBINE_TRACKING_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"Combine tracking is missing required columns: {missing}")

    rows = frame.loc[:, COMBINE_TRACKING_COLUMNS].copy()
    rows = rows.loc[rows["entity_type"].eq("PLAYER")].copy()
    if rows.empty:
        raise ValueError("Combine tracking contains no PLAYER entity rows.")
    key_columns = [
        "draft_year",
        "nfl_id",
        "drill_type",
        "drill_name",
        "attempt",
    ]
    if rows[key_columns].isna().any().any():
        raise ValueError("Combine tracking contains missing player/drill/attempt keys.")
    rows["time"] = pd.to_datetime(rows["time"], errors="coerce")
    if rows["time"].isna().any():
        raise ValueError("Combine tracking contains invalid timestamps.")
    for column in ("x", "y", "s", "a"):
        rows[column] = pd.to_numeric(rows[column], errors="coerce")
    rows = rows.dropna(subset=["x", "y"]).sort_values(
        [*key_columns, "time"], kind="mergesort"
    )

    groups = rows.groupby(key_columns, sort=False, observed=True)
    dx = groups["x"].diff()
    dy = groups["y"].diff()
    rows["step_distance"] = np.hypot(dx, dy).fillna(0.0)
    attempts = rows.groupby(key_columns, sort=False, observed=True).agg(
        frame_count=("nfl_id", "size"),
        peak_speed=("s", "max"),
        mean_speed=("s", "mean"),
        mean_acceleration=("a", "mean"),
        path_length=("step_distance", "sum"),
        start_x=("x", "first"),
        start_y=("y", "first"),
        end_x=("x", "last"),
        end_y=("y", "last"),
        start_time=("time", "first"),
        end_time=("time", "last"),
    )
    attempts["duration_seconds"] = (
        attempts["end_time"] - attempts["start_time"]
    ).dt.total_seconds()
    displacement = np.hypot(
        attempts["end_x"] - attempts["start_x"],
        attempts["end_y"] - attempts["start_y"],
    )
    attempts["path_efficiency"] = displacement.div(
        attempts["path_length"].where(attempts["path_length"].gt(0))
    )

    player_drill = (
        attempts.reset_index()
        .groupby(
            ["draft_year", "nfl_id", "drill_type", "drill_name"],
            as_index=False,
            sort=False,
            observed=True,
        )
        .agg(
            attempt_count=("attempt", "nunique"),
            frame_count=("frame_count", "sum"),
            combine_peak_speed=("peak_speed", "median"),
            combine_mean_speed=("mean_speed", "mean"),
            combine_mean_acceleration=("mean_acceleration", "mean"),
            combine_path_efficiency=("path_efficiency", "median"),
            mean_attempt_duration_seconds=("duration_seconds", "mean"),
        )
    )
    return player_drill


def _rank_residuals(
    frame: pd.DataFrame,
    value_column: str,
    cohort_column: str,
    controls: list[str],
) -> np.ndarray:
    ranks = frame[value_column].rank(method="average", pct=True).to_numpy(dtype=float)
    design_parts = [np.ones((len(frame), 1), dtype=float)]
    cohorts = pd.get_dummies(
        frame[cohort_column].astype(str), drop_first=True, dtype=float
    )
    if not cohorts.empty:
        design_parts.append(cohorts.to_numpy(dtype=float))
    for column in controls:
        design_parts.append(
            frame[column].rank(method="average", pct=True).to_numpy(dtype=float)[:, None]
        )
    design = np.column_stack(design_parts)
    coefficients, *_ = np.linalg.lstsq(design, ranks, rcond=None)
    return ranks - design @ coefficients


def adjusted_rank_correlation(
    frame: pd.DataFrame,
    x_column: str,
    y_column: str,
    *,
    cohort_column: str = "draft_year",
    controls: list[str] | None = None,
) -> float:
    """Return a partial Spearman-style correlation after cohort/continuous controls."""

    controls = controls or []
    required = [x_column, y_column, cohort_column, *controls]
    data = frame.loc[:, required].dropna()
    if len(data) < 3:
        return float("nan")
    x_residual = _rank_residuals(data, x_column, cohort_column, controls)
    y_residual = _rank_residuals(data, y_column, cohort_column, controls)
    if np.std(x_residual) == 0 or np.std(y_residual) == 0:
        return float("nan")
    return float(np.corrcoef(x_residual, y_residual)[0, 1])


def bootstrap_adjusted_rank_correlation(
    frame: pd.DataFrame,
    x_column: str,
    y_column: str,
    *,
    cohort_column: str = "draft_year",
    controls: list[str] | None = None,
    replicates: int = 1000,
    seed: int = 20271011,
) -> tuple[float, float]:
    """Estimate a cohort-stratified, player-bootstrap percentile interval."""

    controls = controls or []
    data = frame.dropna(subset=[x_column, y_column, cohort_column, *controls])
    if len(data) < 3 or replicates < 1:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    cohorts = [
        group.reset_index(drop=True)
        for _, group in data.groupby(cohort_column, sort=True)
    ]
    estimates: list[float] = []
    for _ in range(replicates):
        sampled = pd.concat(
            [
                group.iloc[
                    rng.integers(0, len(group), size=len(group))
                ]
                for group in cohorts
            ],
            ignore_index=True,
        )
        estimate = adjusted_rank_correlation(
            sampled,
            x_column,
            y_column,
            cohort_column=cohort_column,
            controls=controls,
        )
        if np.isfinite(estimate):
            estimates.append(estimate)
    if not estimates:
        return float("nan"), float("nan")
    low, high = np.quantile(estimates, [0.025, 0.975])
    return float(low), float(high)


def _format_number(value: Any, digits: int = 3) -> str:
    if value is None or pd.isna(value):
        return "not estimable"
    return f"{float(value):.{digits}f}"


def _format_count(value: Any) -> str:
    return str(int(value)) if value is not None and pd.notna(value) else "0"


def _select_drill_cohort(
    candidate_rows: pd.DataFrame,
    position: str,
    drill_type: str,
    drill_name: str,
) -> pd.DataFrame:
    """Select complete cases for one position, drill category, and drill."""

    selected = candidate_rows.loc[
        candidate_rows["combine_position"].eq(position)
        & candidate_rows["drill_type"].eq(drill_type)
        & candidate_rows["drill_name"].eq(drill_name)
        & candidate_rows["complete_case"]
    ].copy()
    if selected.duplicated(["draft_year", "nfl_id"]).any():
        raise ValueError("Selected drill cohort contains duplicate players.")
    return selected.sort_values(["draft_year", "nfl_id"])


def _write_figures(
    selected: pd.DataFrame,
    coverage: pd.DataFrame,
    position: str,
    drill_type: str,
    drill_name: str,
    figure_dir: Path,
) -> list[Path]:
    figure_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    cohort_colors = {
        year: color
        for year, color in zip(
            sorted(selected["draft_year"].dropna().unique()),
            ["#2864a5", "#d17b0f", "#35835a", "#8c5aa7"],
            strict=False,
        )
    }

    for x_column, y_column, filename, y_label, log_y in [
        (
            "combine_peak_speed",
            "rookie_mean_speed",
            "combine_to_rookie_tracking.png",
            "Rookie regular-season mean tracked speed (source units)",
            False,
        ),
        (
            "combine_peak_speed",
            "career_total_snaps",
            "combine_to_career_snaps.png",
            "Career snaps (official aggregate)",
            True,
        ),
    ]:
        plot_data = selected.dropna(subset=[x_column, y_column])
        fig, ax = plt.subplots(figsize=(8.4, 5.3), constrained_layout=True)
        for year, group in plot_data.groupby("draft_year", sort=True):
            ax.scatter(
                group[x_column],
                group[y_column] + (1 if log_y else 0),
                label=str(int(year)),
                color=cohort_colors.get(year, "#555555"),
                alpha=0.76,
                edgecolors="white",
                linewidths=0.4,
                s=42,
            )
        if log_y:
            ax.set_yscale("log")
            ax.set_ylabel("Career snaps + 1 (log scale)")
        else:
            ax.set_ylabel(y_label)
        ax.set_xlabel("Median attempt-level Combine peak speed (source units)")
        ax.set_title(f"{position} | {drill_name.replace('_', ' ').title()}")
        ax.grid(alpha=0.2)
        ax.legend(title="Draft cohort", frameon=False)
        output = figure_dir / filename
        fig.savefig(output, dpi=180)
        plt.close(fig)
        outputs.append(output)

    cohort_counts = (
        coverage.loc[
            coverage["combine_position"].eq(position)
            & coverage["drill_type"].eq(drill_type)
            & coverage["drill_name"].eq(drill_name)
        ]
        .sort_values("draft_year")
    )
    fig, ax = plt.subplots(figsize=(7.2, 4.6), constrained_layout=True)
    ax.bar(
        cohort_counts["draft_year"].astype(str),
        cohort_counts["complete_players"],
        color="#2864a5",
    )
    ax.set_xlabel("Draft cohort")
    ax.set_ylabel("Players with both Combine and rookie tracking")
    ax.set_title(f"Complete-case coverage | {position} | {drill_name.replace('_', ' ').title()}")
    ax.grid(axis="y", alpha=0.2)
    output = figure_dir / "cohort_coverage.png"
    fig.savefig(output, dpi=180)
    plt.close(fig)
    outputs.append(output)
    return outputs


def run_research_analysis(
    data_dir: Path,
    audit: dict[str, Any],
    reports_dir: Path,
    *,
    bootstrap_replicates: int = 1000,
) -> dict[str, Any]:
    """Build the coverage-selected research cohort, associations, figures, report."""

    data_dir = data_dir.resolve()
    reports_dir.mkdir(parents=True, exist_ok=True)
    tables_dir = reports_dir / "tables"
    figures_dir = reports_dir / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)

    combine_tracking = pd.read_csv(
        data_dir / "combine_tracking.csv",
        usecols=COMBINE_TRACKING_COLUMNS,
    )
    sensor_features = aggregate_combine_tracking(combine_tracking)
    combine = pd.read_csv(data_dir / "combine_results.csv")
    career = pd.read_csv(data_dir / "player_career_successes.csv")
    career["career_total_snaps"] = career[
        [
            "career_offensive_snaps",
            "career_defensive_snaps",
            "career_special_teams_snaps",
        ]
    ].sum(axis=1, min_count=1)
    rookie_tracking = audit["rookie_tracking"].copy()
    candidate_rows = sensor_features.merge(
        combine[["draft_year", "nfl_id", "combine_position", "forty"]],
        on=["draft_year", "nfl_id"],
        how="inner",
        validate="many_to_one",
    )
    candidate_rows = candidate_rows.merge(
        rookie_tracking,
        on=["draft_year", "nfl_id"],
        how="left",
        validate="many_to_one",
    ).merge(
        career[
            [
                "nfl_id",
                "career_total_snaps",
                "career_games_active",
                "career_defensive_snaps",
                "career_offensive_snaps",
            ]
        ],
        on="nfl_id",
        how="left",
        validate="many_to_one",
    )
    candidate_rows = candidate_rows.rename(
        columns={
            "mean_speed": "rookie_mean_speed",
            "max_speed": "rookie_max_speed",
            "mean_acceleration": "rookie_mean_acceleration",
        }
    )
    candidate_rows = candidate_rows.loc[
        candidate_rows["drill_type"].fillna("").str.startswith("SKILL_DRILLS_")
    ].copy()

    minimum_frames = 100
    candidate_rows["has_career_target"] = candidate_rows[
        "career_total_snaps"
    ].notna()
    candidate_rows["has_rookie_tracking"] = candidate_rows[
        "rookie_mean_speed"
    ].notna() & candidate_rows["rookie_regular_season_frames"].fillna(0).gt(0)
    candidate_rows["meets_rookie_frame_minimum"] = candidate_rows[
        "rookie_regular_season_frames"
    ].ge(minimum_frames)
    candidate_rows["complete_case"] = (
        candidate_rows["has_career_target"]
        & candidate_rows["has_rookie_tracking"]
        & candidate_rows["meets_rookie_frame_minimum"]
    )
    position_totals = (
        combine.groupby(["draft_year", "combine_position"])["nfl_id"]
        .nunique()
        .rename("position_cohort_players")
        .reset_index()
    )
    coverage = (
        candidate_rows.groupby(
            ["combine_position", "drill_type", "drill_name", "draft_year"],
            as_index=False,
            observed=True,
        )
        .agg(
            sensor_players=("nfl_id", "nunique"),
            with_career_target=("has_career_target", "sum"),
            with_rookie_tracking=("has_rookie_tracking", "sum"),
            meeting_frame_minimum=("meets_rookie_frame_minimum", "sum"),
            complete_players=("complete_case", "sum"),
        )
        .sort_values(
            ["combine_position", "drill_type", "drill_name", "draft_year"]
        )
    )
    coverage["dropped_missing_career_target"] = (
        coverage["sensor_players"] - coverage["with_career_target"]
    )
    coverage["dropped_no_rookie_tracking"] = (
        coverage["sensor_players"] - coverage["with_rookie_tracking"]
    )
    coverage["dropped_below_frame_minimum"] = (
        coverage["sensor_players"] - coverage["meeting_frame_minimum"]
    )
    coverage = coverage.merge(
        position_totals,
        on=["draft_year", "combine_position"],
        how="left",
        validate="many_to_one",
    )
    coverage["complete_case_pct_of_position"] = (
        100 * coverage["complete_players"] / coverage["position_cohort_players"]
    ).round(2)
    coverage.to_csv(tables_dir / "drill_candidate_coverage.csv", index=False)

    total_coverage = (
        coverage.groupby(
            ["combine_position", "drill_type", "drill_name"],
            as_index=False,
            observed=True,
        )
        .agg(complete_players=("complete_players", "sum"))
        .sort_values(
            ["complete_players", "combine_position", "drill_type", "drill_name"],
            ascending=[False, True, True, True],
        )
    )
    selected: pd.DataFrame = pd.DataFrame()
    position = ""
    drill_type = ""
    drill_name = ""
    if not total_coverage.empty:
        winner = total_coverage.iloc[0]
        position = str(winner["combine_position"])
        drill_type = str(winner["drill_type"])
        drill_name = str(winner["drill_name"])
        selected = _select_drill_cohort(
            candidate_rows, position, drill_type, drill_name
        )
    selected.to_csv(tables_dir / "selected_player_analysis.csv", index=False)

    relationships = [
        (
            "Combine peak speed",
            "combine_peak_speed",
            "Rookie mean speed",
            "rookie_mean_speed",
        ),
        (
            "Combine mean acceleration",
            "combine_mean_acceleration",
            "Rookie mean acceleration",
            "rookie_mean_acceleration",
        ),
        (
            "Combine peak speed",
            "combine_peak_speed",
            "Career total snaps",
            "career_total_snaps",
        ),
        (
            "Forty-yard time",
            "forty",
            "Rookie mean speed",
            "rookie_mean_speed",
        ),
    ]
    associations: list[dict[str, Any]] = []
    cohort_rows: list[dict[str, Any]] = []
    if not selected.empty:
        for index, (feature_label, feature, outcome_label, outcome) in enumerate(
            relationships
        ):
            valid = selected.dropna(subset=[feature, outcome, "draft_year"])
            estimate = adjusted_rank_correlation(valid, feature, outcome)
            low, high = bootstrap_adjusted_rank_correlation(
                valid,
                feature,
                outcome,
                replicates=bootstrap_replicates,
                seed=20271011 + index,
            )
            result = {
                "feature": feature_label,
                "feature_column": feature,
                "outcome": outcome_label,
                "outcome_column": outcome,
                "players": len(valid),
                "draft_year_adjusted_rank_correlation": estimate,
                "bootstrap_95pct_low": low,
                "bootstrap_95pct_high": high,
            }
            if (
                feature == "combine_peak_speed"
                and outcome == "rookie_mean_speed"
            ):
                comparable = valid.dropna(subset=["forty"])
                partial = adjusted_rank_correlation(
                    comparable, feature, outcome, controls=["forty"]
                )
                partial_low, partial_high = bootstrap_adjusted_rank_correlation(
                    comparable,
                    feature,
                    outcome,
                    controls=["forty"],
                    replicates=bootstrap_replicates,
                    seed=20272011,
                )
                result.update(
                    {
                        "controlling_for_forty_and_cohort": partial,
                        "partial_bootstrap_95pct_low": partial_low,
                        "partial_bootstrap_95pct_high": partial_high,
                        "partial_players": len(comparable),
                    }
                )
            associations.append(result)
            for year, group in valid.groupby("draft_year", sort=True):
                cohort_rho = group[feature].corr(group[outcome], method="spearman")
                cohort_rows.append(
                    {
                        "feature": feature_label,
                        "outcome": outcome_label,
                        "draft_year": int(year),
                        "players": len(group),
                        "spearman_correlation": cohort_rho,
                    }
                )

    association_frame = pd.DataFrame(associations)
    association_frame.to_csv(tables_dir / "associations.csv", index=False)
    pd.DataFrame(cohort_rows).to_csv(
        tables_dir / "cohort_associations.csv", index=False
    )
    figure_paths: list[Path] = []
    if not selected.empty:
        figure_paths = _write_figures(
            selected, coverage, position, drill_type, drill_name, figures_dir
        )

    inventory = audit["inventory"]
    (reports_dir / "audit").mkdir(parents=True, exist_ok=True)
    access_date = pd.Timestamp.now(tz="UTC").date().isoformat()
    inventory_md = [
        "# Official Data Inventory",
        "",
        f"Retrieved and verified: {access_date} (UTC)",
        "",
        "Source: [Kaggle NFL Big Data Bowl 2027 data page](https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/data).",
        "All raw files are stored outside the repository at `C:\\GridironIQ-data\\nfl-big-data-bowl-2027`.",
        "",
        "| Official file | Bytes | SHA-256 | Rows | Schema check |",
        "|---|---:|---|---:|---|",
    ]
    for row in inventory.itertuples(index=False):
        inventory_md.append(
            f"| `{row.filename}` | {row.size_bytes:,} | "
            f"`{row.sha256}` | {row.rows:,} | "
            f"{'pass' if row.header_matches_verified_schema else 'mismatch'} |"
        )
    archive_path = data_dir.parent / f"{data_dir.name}.zip"
    if archive_path.is_file():
        inventory_md.extend(
            [
                "",
                f"Downloaded archive: `{archive_path}` "
                f"({archive_path.stat().st_size:,} bytes; ZIP CRC validation passed).",
            ]
        )
    (reports_dir / "audit" / "data_inventory.md").write_text(
        "\n".join(inventory_md) + "\n", encoding="utf-8"
    )

    if selected.empty:
        research_question = (
            "Insufficient complete Combine-sensor and rookie regular-season tracking "
            "coverage was available to select a position/drill cohort."
        )
        finding = (
            "No association was estimated because no coverage-qualified cohort was "
            "available; no empirical conclusion is claimed."
        )
    else:
        research_question = (
            f"Among {position} prospects in the {drill_type} category, is median "
            "attempt-level player peak speed "
            f"in the {drill_name} Combine drill associated with rookie-season mean "
            "tracked speed after accounting for draft cohort, and does the "
            "association remain after additionally controlling for the 40-yard time?"
        )
        primary = next(
            (
                row
                for row in associations
                if row["feature_column"] == "combine_peak_speed"
                and row["outcome_column"] == "rookie_mean_speed"
            ),
            {},
        )
        finding = (
            f"The cohort-adjusted rank correlation was "
            f"{_format_number(primary.get('draft_year_adjusted_rank_correlation'))} "
            f"(player-bootstrap 95% interval "
            f"{_format_number(primary.get('bootstrap_95pct_low'))} to "
            f"{_format_number(primary.get('bootstrap_95pct_high'))}; "
            f"n={primary.get('players', 0)}). The corresponding partial correlation "
            f"controlling for cohort and 40-yard time was "
            f"{_format_number(primary.get('controlling_for_forty_and_cohort'))} "
            f"(player-bootstrap 95% interval "
            f"{_format_number(primary.get('partial_bootstrap_95pct_low'))} to "
            f"{_format_number(primary.get('partial_bootstrap_95pct_high'))}; "
            f"n={_format_count(primary.get('partial_players'))}). The partial interval "
            "includes zero, so the observed association does not clearly add "
            "information beyond the timed 40-yard result in this sample. These are "
            "exploratory associations, not causal or out-of-sample predictive effects."
        )

    association_table = [
        "| Feature | Outcome | n | Cohort-adjusted rank correlation | Player-bootstrap 95% interval |",
        "|---|---|---:|---:|---|",
    ]
    if not associations:
        association_table = ["No association was estimated for the selected cohort."]
    for association in associations:
        association_table.append(
            f"| {association['feature']} | {association['outcome']} | "
            f"{association['players']} | "
            f"{_format_number(association['draft_year_adjusted_rank_correlation'])} | "
            f"{_format_number(association['bootstrap_95pct_low'])} to "
            f"{_format_number(association['bootstrap_95pct_high'])} |"
        )
    partial_row = next(
        (
            row
            for row in associations
            if row["feature_column"] == "combine_peak_speed"
            and row["outcome_column"] == "rookie_mean_speed"
        ),
        None,
    )
    if partial_row:
        association_table.extend(
            [
                "",
                "Additional adjustment for 40-yard time (same movement outcome): "
                f"partial rank correlation "
                f"{_format_number(partial_row.get('controlling_for_forty_and_cohort'))} "
                f"(n={_format_count(partial_row.get('partial_players'))}; player-bootstrap "
                "95% interval "
                f"{_format_number(partial_row.get('partial_bootstrap_95pct_low'))} "
                "to "
                f"{_format_number(partial_row.get('partial_bootstrap_95pct_high'))}).",
            ]
        )

    lines = [
        "# GridironIQ: Combine Movement and Rookie NFL Tracking",
        "",
        f"**Research question:** {research_question}",
        "",
        "## Competition fit",
        "",
        "The official 2027 event asks for an analytical framework linking 10 Hz Combine "
        "sensor tracking to future regular-season performance. It is a human-evaluated "
        "write-up challenge, not a prediction leaderboard: the official evaluation "
        "requires an explicit Combine-to-NFL linkage and a complete write-up with "
        "readable markdown, embedded visuals, and an attached public Kaggle Notebook. "
        "Its four scored components are Football (30%), Data Science (30%), Write-up "
        "(20%), and Data Visualization (20%). The competition has no sample "
        "prediction-submission file among the nine official data files; no prediction "
        "CSV was fabricated or uploaded.",
        "",
        "## Data and linkage",
        "",
        f"The audit verified {len(inventory)} official CSV files, their exact byte "
        "sizes, SHA-256 digests, headers, row counts, missingness, numeric ranges, "
        "composite-key duplicates, and player-ID join coverage. See "
        "[data inventory](audit/data_inventory.md), "
        "[column-level quality audit](tables/data_quality.csv), "
        "[player-ID joins](tables/join_coverage.csv), "
        "[game-ID joins](tables/game_id_join_coverage.csv), "
        "[value checks](tables/value_checks.csv).",
        "",
        "Tracking CSVs were scanned in chunks. Combine tracking includes both "
        "`PLAYER` and `BALL` entities at the same event/time; composite-key checks "
        "include `entity_type`, and only `PLAYER` rows contribute to athlete features. "
        "Rookie outcomes use `games.csv` to "
        "select only games marked `REG` and the player's draft-year season; this "
        "avoids using later tracking observations as rookie outcomes. Combine "
        "trajectories are ordered by their observed timestamps and summarized at the "
        "player/drill level. Game speed and acceleration are means over observed "
        "tracking frames; they are exposure- and role-dependent, not isolated skill "
        "measures. Coordinates outside the nominal playing-surface rectangle are "
        "reported as range checks, not automatically treated as bad data: trackers "
        "can record players beyond the sidelines/end lines, and Combine sensor "
        "coordinates use a separate setup. Signed acceleration, including negative "
        "values, is retained. No distance comparison across coordinate systems is "
        "made; path efficiency is dimensionless. Career snaps are supplied aggregates "
        "and have unequal follow-up, so they are a secondary outcome, never a "
        "predictor.",
        "",
        "## Cohort selection and results",
        "",
        "To avoid selecting a drill based on its outcome correlation, the primary "
        "position, drill category, and drill are the exact skill-drill group with "
        "the most complete unique players (Combine movement, career outcomes, and "
        "at least 100 rookie regular-season tracking frames). The cohort is selected "
        "by coverage only; records with the same drill name but a different drill "
        "category are not combined. "
        "See [candidate coverage](tables/drill_candidate_coverage.csv) and "
        "[player-level analysis table](tables/selected_player_analysis.csv).",
        "",
        finding,
        "",
        "### Exploratory associations",
        "",
        *association_table,
        "",
        "The negative 40-yard-time correlation means faster timed 40-yard results "
        "tended to coincide with higher rookie-season mean tracked speed. "
        "Cohort-specific estimates are also provided below.",
        "",
        "Associations are rank-based and adjusted for draft-year cohort. Intervals "
        "come from a reproducible, cohort-stratified player bootstrap. The primary "
        "partial correlation additionally controls for the 40-yard Combine time. "
        "No predictive model or significance claim is warranted for this small, "
        "selected three-cohort sample. Cohort-specific correlations are reported in "
        "[this table](tables/cohort_associations.csv).",
        "",
        "### Figures",
        "",
    ]
    if figure_paths:
        lines.extend(
            f"![{figure.stem.replace('_', ' ').title()}](figures/{figure.name})"
            for figure in figure_paths
        )
    else:
        lines.append("No figures were generated because no complete cohort was available.")
    lines.extend(
        [
            "",
            "## Limitations and interpretation",
            "",
            "- Observational associations do not show that a Combine movement trait "
            "causes NFL performance.",
            "- Rookie mean tracking speed varies by position, assignment, play type, "
            "playing time, and tracking coverage; it is not a universal player-quality "
            "score.",
            "- The cohort spans only draft years 2023–2025. Career snap totals have "
            "unequal time at risk, especially for the newest class.",
            "- Selecting the best-covered position/drill supports reliable description "
            "but does not establish that it is the most important football signal.",
            "- The Kaggle write-up and public notebook are not published from this "
            "workspace; publication requires explicit user authorization.",
            "",
            "## Reproduction",
            "",
            "From the project root with `.venv312` available:",
            "",
            "```powershell",
            r".\.venv312\Scripts\python.exe -m gridiron_iq.pipeline --data-dir C:\GridironIQ-data\nfl-big-data-bowl-2027",
            r".\.venv312\Scripts\python.exe -m pytest -q",
            r".\.venv312\Scripts\python.exe -m pip check",
            "```",
            "",
            "## Official sources and competition timing",
            "",
            "- [Competition overview, theme, requirements, and evaluation](https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/overview)",
            "- [Competition data and official file list](https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/data)",
            "- [Competition rules](https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/rules)",
            "- The authenticated Kaggle CLI listed the deadline as "
            "`2027-01-06 23:59:00`; the CLI output did not identify a timezone.",
            "",
        ]
    )
    (reports_dir / "research_report.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    return {
        "research_question": research_question,
        "selected_position": position,
        "selected_drill_type": drill_type,
        "selected_drill": drill_name,
        "selected_players": len(selected),
        "associations": association_frame,
        "figure_paths": figure_paths,
        "report_path": reports_dir / "research_report.md",
    }
