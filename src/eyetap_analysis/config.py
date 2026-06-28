from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REQUIRED_COLUMNS = frozenset(
    {
        "ANNOTATIONSESSIONID",
        "ANNOTATORID",
        "CHARUID",
        "FIXATIONUID",
        "READERUID",
        "TEXTLANG",
        "TEXTUID",
    }
)


@dataclass
class CohortConfig:
    name: str
    file: Path
    preset: str
    label: str


@dataclass
class AnalysisConfig:
    base_dir: Path
    cohorts: list[CohortConfig]
    reading_session_keys: list[str] = field(
        default_factory=lambda: ["READERUID", "TEXTUID", "TEXTLANG"]
    )
    default_timeout_sec: float | None = None
    session_metadata_file: Path | None = None
    characters_file: Path | None = None
    skip_missing_cohort_files: bool = True

    def resolve(self, path: str | Path | None) -> Path | None:
        if path is None:
            return None
        candidate = Path(path)
        if candidate.is_absolute():
            return candidate
        return self.base_dir / candidate


def load_config(
    config_path: Path,
    *,
    skip_missing_cohort_files: bool = True,
    cohort_overrides: dict[str, Path] | None = None,
) -> AnalysisConfig:
    base_dir = config_path.parent
    with config_path.open(encoding="utf-8") as handle:
        raw: dict[str, Any] = yaml.safe_load(handle)

    cohorts: list[CohortConfig] = []
    for name, details in raw["cohorts"].items():
        file_path = (
            cohort_overrides[name]
            if cohort_overrides and name in cohort_overrides
            else base_dir / details["file"]
        )
        cohorts.append(
            CohortConfig(
                name=name,
                file=file_path,
                preset=details["preset"],
                label=details["label"],
            )
        )

    metadata = raw.get("session_metadata_file")
    characters = raw.get("characters_file")

    return AnalysisConfig(
        base_dir=base_dir,
        cohorts=cohorts,
        reading_session_keys=raw.get(
            "reading_session_keys", ["READERUID", "TEXTUID", "TEXTLANG"]
        ),
        default_timeout_sec=raw.get("default_timeout_sec"),
        session_metadata_file=base_dir / metadata if metadata else None,
        characters_file=base_dir / characters if characters else None,
        skip_missing_cohort_files=skip_missing_cohort_files,
    )
