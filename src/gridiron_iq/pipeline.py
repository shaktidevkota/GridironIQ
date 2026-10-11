"""Command-line entry point for the reproducible competition research pipeline."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from gridiron_iq.audit.competition_data import audit_official_data
from gridiron_iq.research import run_research_analysis


def run_pipeline(
    data_dir: Path,
    reports_dir: Path,
    *,
    chunksize: int = 200_000,
    bootstrap_replicates: int = 1000,
) -> dict[str, object]:
    """Run the streaming audit and research analysis and persist small outputs."""

    reports_dir = reports_dir.resolve()
    audit_dir = reports_dir / "audit"
    tables_dir = reports_dir / "tables"
    audit_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    audit = audit_official_data(
        data_dir,
        chunksize=chunksize,
        progress=print,
    )
    audit["inventory"].to_csv(audit_dir / "data_inventory.csv", index=False)
    audit["quality"].to_csv(tables_dir / "data_quality.csv", index=False)
    audit["value_checks"].to_csv(tables_dir / "value_checks.csv", index=False)
    audit["join_coverage"].to_csv(tables_dir / "join_coverage.csv", index=False)
    audit["game_join_coverage"].to_csv(
        tables_dir / "game_id_join_coverage.csv", index=False
    )
    audit["rookie_tracking"].to_csv(
        tables_dir / "rookie_tracking_summary.csv", index=False
    )

    result = run_research_analysis(
        data_dir,
        audit,
        reports_dir,
        bootstrap_replicates=bootstrap_replicates,
    )
    print(
        f"Primary cohort: {result['selected_position']} / "
        f"{result['selected_drill_type']} / {result['selected_drill']}"
    )
    print(f"Complete-case players: {result['selected_players']}")
    print(f"Research report: {result['report_path']}")
    for figure in result["figure_paths"]:
        print(f"Figure: {figure}")
    return result


def main() -> None:
    default_data_dir = Path(
        os.environ.get(
            "GRIDIRON_IQ_DATA_DIR",
            r"C:\GridironIQ-data\nfl-big-data-bowl-2027",
        )
    )
    parser = argparse.ArgumentParser(
        description="Audit official Big Data Bowl files and run the research analysis."
    )
    parser.add_argument("--data-dir", type=Path, default=default_data_dir)
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"))
    parser.add_argument("--chunksize", type=int, default=200_000)
    parser.add_argument("--bootstrap-replicates", type=int, default=1000)
    args = parser.parse_args()
    if args.chunksize < 1:
        parser.error("--chunksize must be a positive integer.")
    if args.bootstrap_replicates < 1:
        parser.error("--bootstrap-replicates must be a positive integer.")
    run_pipeline(
        args.data_dir,
        args.reports_dir,
        chunksize=args.chunksize,
        bootstrap_replicates=args.bootstrap_replicates,
    )


if __name__ == "__main__":
    main()
