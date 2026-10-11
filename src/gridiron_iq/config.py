"""Project configuration and path helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ProjectPaths:
    """Resolved project paths used by audit and pipeline commands."""

    root: Path
    raw_data: Path
    interim_data: Path
    processed_data: Path
    audit_reports: Path
    figures: Path
    tables: Path


def find_project_root(start: Path | None = None) -> Path:
    """Find the repository root by walking upward to pyproject.toml."""

    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise RuntimeError("Could not find project root containing pyproject.toml.")


def load_project_config(path: Path | None = None) -> dict:
    """Load the YAML project configuration."""

    config_path = path or find_project_root() / "configs" / "project.yml"
    return yaml.safe_load(config_path.read_text(encoding="utf-8"))


def get_project_paths(root: Path | None = None) -> ProjectPaths:
    """Return configured paths resolved from the repository root."""

    project_root = (root or find_project_root()).resolve()
    config = load_project_config(project_root / "configs" / "project.yml")
    paths = config["paths"]
    return ProjectPaths(
        root=project_root,
        raw_data=project_root / paths["raw_data"],
        interim_data=project_root / paths["interim_data"],
        processed_data=project_root / paths["processed_data"],
        audit_reports=project_root / paths["audit_reports"],
        figures=project_root / paths["figures"],
        tables=project_root / paths["tables"],
    )


def ensure_project_directories(paths: ProjectPaths) -> None:
    """Create non-raw output directories needed for reproducible reports."""

    for path in [paths.audit_reports, paths.figures, paths.tables]:
        path.mkdir(parents=True, exist_ok=True)
