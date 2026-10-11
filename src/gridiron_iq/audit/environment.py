"""Collect a local environment audit without exposing secrets."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from gridiron_iq.audit.kaggle_inventory import kaggle_executable


def command_exists(command: str) -> bool:
    """Return whether command is available on PATH."""

    return shutil.which(command) is not None


def run_command(args: list[str]) -> dict[str, object]:
    """Run a read-only command and capture a compact result."""

    try:
        completed = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception as exc:  # pragma: no cover - defensive audit capture
        return {"args": args, "returncode": None, "error": repr(exc)}

    return {
        "args": args,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def collect_environment_audit() -> dict[str, object]:
    """Collect environment facts relevant to reproducibility."""

    kaggle_config_dir = Path(
        os.environ.get("KAGGLE_CONFIG_DIR", Path.home() / ".kaggle")
    )
    kaggle_path = kaggle_executable()
    kaggle_version = (
        run_command([kaggle_path, "--version"]) if kaggle_path else None
    )
    kaggle_access = (
        run_command(
            [
                kaggle_path,
                "competitions",
                "files",
                "-c",
                "nfl-big-data-bowl-2027",
            ]
        )
        if kaggle_path
        else None
    )
    audit: dict[str, object] = {
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python_executable": sys.executable,
        "python_version": sys.version,
        "working_directory": str(Path.cwd()),
        "path_tools": {
            "python": shutil.which("python"),
            "py": shutil.which("py"),
            "kaggle": kaggle_path,
            "git": shutil.which("git"),
        },
        "kaggle_config_dir": str(kaggle_config_dir),
        "kaggle_json_present": (kaggle_config_dir / "kaggle.json").exists(),
        "environment_variables_present": {
            "KAGGLE_USERNAME": bool(os.environ.get("KAGGLE_USERNAME")),
            "KAGGLE_KEY": bool(os.environ.get("KAGGLE_KEY")),
        },
        "commands": {
            "git_status": run_command(["git", "status", "--short", "--branch"]),
            "git_remote": run_command(["git", "remote", "--verbose"]),
            "kaggle_version": kaggle_version,
            "kaggle_competition_access": kaggle_access,
        },
    }
    return audit


def main() -> None:
    """Write environment audit JSON to reports/audit."""

    output_dir = Path("reports/audit")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "environment_audit.json"
    output_path.write_text(
        json.dumps(collect_environment_audit(), indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
