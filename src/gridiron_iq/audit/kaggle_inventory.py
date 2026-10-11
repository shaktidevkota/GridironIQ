"""Inventory official Kaggle competition files when authenticated access exists."""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class KaggleStatus:
    """Kaggle access facts that do not expose secrets."""

    executable: str | None
    config_dir: str
    credential_file_present: bool
    env_username_present: bool
    env_key_present: bool


def default_kaggle_config_dir() -> Path:
    """Return the configured Kaggle credential directory without exposing it."""

    return Path(os.environ.get("KAGGLE_CONFIG_DIR", Path.home() / ".kaggle"))


def kaggle_executable() -> str | None:
    """Find Kaggle on PATH or beside the active Python interpreter."""

    executable = shutil.which("kaggle")
    if executable:
        return executable
    script_dir = Path(sys.executable).parent
    for name in ("kaggle.exe", "kaggle"):
        candidate = script_dir / name
        if candidate.is_file():
            return str(candidate)
    return None


def collect_kaggle_status() -> KaggleStatus:
    """Collect Kaggle CLI and credential presence without printing secrets."""

    config_dir = default_kaggle_config_dir()
    return KaggleStatus(
        executable=kaggle_executable(),
        config_dir=str(config_dir),
        credential_file_present=(config_dir / "kaggle.json").exists(),
        env_username_present=bool(os.environ.get("KAGGLE_USERNAME")),
        env_key_present=bool(os.environ.get("KAGGLE_KEY")),
    )


def run_kaggle_files_command(competition: str) -> subprocess.CompletedProcess[str]:
    """Run the Kaggle files command with a writable config directory."""

    kaggle = kaggle_executable()
    if kaggle is None:
        raise RuntimeError("Kaggle CLI is not available on PATH.")

    env = os.environ.copy()

    return subprocess.run(
        [kaggle, "competitions", "files", "-c", competition],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )


def parse_competition_files_output(output: str, competition: str) -> list[dict[str, str]]:
    """Parse Kaggle CLI file-list output into inventory rows."""

    lines = [line.rstrip() for line in output.splitlines() if line.strip()]
    if len(lines) < 3:
        return []

    rows: list[dict[str, str]] = []
    for line in lines[2:]:
        parts = line.split()
        if len(parts) < 2:
            continue
        rows.append(
            {
                "filename": Path(parts[0]).name,
                "size": parts[1],
                "raw_listing": line,
                "competition": competition,
                "retrieval_date": date.today().isoformat(),
                "source": f"https://www.kaggle.com/competitions/{competition}/data",
                "accessible": "true",
            }
        )
    return rows


def list_competition_files(competition: str) -> list[dict[str, str]]:
    """Return Kaggle competition file rows from the Kaggle CLI output."""

    completed = run_kaggle_files_command(competition)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())

    return parse_competition_files_output(completed.stdout, competition)


def write_inventory(rows: list[dict[str, str]], output_path: Path) -> None:
    """Write inventory rows to CSV."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "filename",
        "size",
        "raw_listing",
        "competition",
        "retrieval_date",
        "source",
        "accessible",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown_report(
    output_path: Path,
    competition: str,
    status: KaggleStatus,
    rows: list[dict[str, str]] | None,
    error: str | None,
) -> None:
    """Write a human-readable official data inventory status report."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Official Data Inventory",
        "",
        f"Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        f"Competition: `{competition}`",
        f"Source: `https://www.kaggle.com/competitions/{competition}/data`",
        "",
        "## Kaggle Access Status",
        "",
        f"- Kaggle executable: `{status.executable}`",
        f"- Kaggle config dir: `{status.config_dir}`",
        f"- Credential file present: `{status.credential_file_present}`",
        f"- `KAGGLE_USERNAME` present: `{status.env_username_present}`",
        f"- `KAGGLE_KEY` present: `{status.env_key_present}`",
        "",
    ]

    if error:
        lines.extend(
            [
                "## Inventory Status",
                "",
                "BLOCKED",
                "",
                "The official file list could not be retrieved.",
                "",
                "```text",
                error,
                "```",
                "",
                "## Recovery Instructions",
                "",
                "1. Accept the competition rules on Kaggle if required.",
                "2. Create a local Kaggle API token from your Kaggle account settings.",
                "3. Store the token in Kaggle's user-level credential directory outside this repository, or set `KAGGLE_CONFIG_DIR` to another secure local directory.",
                "4. Never store or commit Kaggle credentials inside the repository.",
                "5. Re-run `python -m gridiron_iq.audit.kaggle_inventory` from the project environment.",
            ]
        )
    else:
        lines.extend(["## Inventory Status", "", "COMPLETE", ""])
        lines.append(f"Official files listed: {len(rows or [])}")
        lines.append("")
        if rows:
            lines.extend(["| Filename | Size |", "| --- | --- |"])
            lines.extend(f"| `{row['filename']}` | `{row['size']}` |" for row in rows)

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--competition", default="nfl-big-data-bowl-2027")
    parser.add_argument(
        "--output",
        default="reports/audit/kaggle_file_inventory.csv",
        type=Path,
    )
    parser.add_argument(
        "--markdown-output",
        default="reports/audit/official_data_inventory.md",
        type=Path,
    )
    args = parser.parse_args()

    status = collect_kaggle_status()
    try:
        rows = list_competition_files(args.competition)
    except Exception as exc:
        write_markdown_report(
            args.markdown_output,
            args.competition,
            status,
            rows=None,
            error=str(exc),
        )
        status_path = args.markdown_output.with_suffix(".status.json")
        status_path.write_text(json.dumps(status.__dict__, indent=2), encoding="utf-8")
        print(f"Inventory blocked; wrote {args.markdown_output}")
        raise SystemExit(2) from exc

    write_inventory(rows, args.output)
    write_markdown_report(
        args.markdown_output,
        args.competition,
        status,
        rows=rows,
        error=None,
    )
    print(f"Wrote {len(rows)} file rows to {args.output}")


if __name__ == "__main__":
    main()
