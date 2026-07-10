from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import TypedDict, cast

from eyetap_analysis.analytics import AnalyticsAnalysisResults, aggregate_analytics
import pandas as pd
import numpy as np

from eyetap_analysis.config import REQUIRED_COLUMNS, AnalysisConfig, CohortConfig


@dataclass
class ValidationReport:
    messages: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def info(self, message: str) -> None:
        self.messages.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def error(self, message: str) -> None:
        self.errors.append(message)

    @property
    def ok(self) -> bool:
        return not self.errors


def _make_reading_session_id(frame: pd.DataFrame, keys: list[str]) -> pd.Series:
    return frame[keys].astype(str).agg("|".join, axis=1)


def _validate_schema(frame: pd.DataFrame, report: ValidationReport) -> None:
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        report.error(f"Missing required columns: {sorted(missing)}")

    extra = (
        set(frame.columns)
        - REQUIRED_COLUMNS
        - {"cohort", "preset", "cohort_label", "reading_session_id"}
    )
    if extra:
        report.warn(f"Unexpected columns will be ignored: {sorted(extra)}")


def _dedupe_annotations(frame: pd.DataFrame, report: ValidationReport) -> pd.DataFrame:
    dupes = frame.duplicated(subset=["ANNOTATIONSESSIONID", "FIXATIONUID"], keep=False)
    if dupes.any():
        count = int(dupes.sum())
        report.warn(
            f"Found {count} duplicate rows on (ANNOTATIONSESSIONID, FIXATIONUID); keeping first occurrence"
        )
        frame = frame.drop_duplicates(
            subset=["ANNOTATIONSESSIONID", "FIXATIONUID"], keep="first"
        )
    return frame


def _validate_rater_counts(frame: pd.DataFrame, report: ValidationReport) -> None:
    grouped = frame.groupby(["cohort", "reading_session_id"])["ANNOTATORID"].nunique()
    for (cohort, reading_session_id), n_raters in grouped.items():
        report.info(
            f"cohort={cohort} reading_session={reading_session_id}: "
            f"{n_raters} annotator(s), {frame[(frame.cohort == cohort) & (frame.reading_session_id == reading_session_id)].shape[0]} rows"
        )
        if n_raters < 2:
            report.warn(
                f"cohort={cohort} reading_session={reading_session_id}: "
                f"only {n_raters} annotator(s); ICC requires at least 2"
            )


def load_cohort_csv(path: Path, cohort: CohortConfig) -> pd.DataFrame:
    frame = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
    frame["cohort"] = cohort.name
    frame["preset"] = cohort.preset
    frame["cohort_label"] = cohort.label
    for column in (
        "ANNOTATIONSESSIONID",
        "ANNOTATORID",
        "CHARUID",
        "FIXATIONUID",
        "READERUID",
        "TEXTUID",
    ):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if frame[list(REQUIRED_COLUMNS)].isna().any().any():
        raise ValueError(f"Non-numeric values found in required columns of {path}")
    return frame


def load_annotations(config: AnalysisConfig) -> tuple[pd.DataFrame, ValidationReport]:
    report = ValidationReport()
    frames: list[pd.DataFrame] = []

    for cohort in config.cohorts:
        if not cohort.file.exists():
            if config.skip_missing_cohort_files:
                report.warn(f"Skipping missing cohort file: {cohort.file}")
                continue
            report.error(f"Missing cohort file: {cohort.file}")
            continue

        frame = load_cohort_csv(cohort.file, cohort)
        frames.append(frame)
        report.info(
            f"Loaded {cohort.name} ({cohort.label}) from {cohort.file}: "
            f"{len(frame)} rows, {frame['ANNOTATIONSESSIONID'].nunique()} sessions, "
            f"{frame['ANNOTATORID'].nunique()} annotators"
        )

    if not frames:
        report.error("No cohort data loaded")
        return pd.DataFrame(), report

    combined = pd.concat(frames, ignore_index=True)
    combined["reading_session_id"] = _make_reading_session_id(
        combined, config.reading_session_keys
    )

    _validate_schema(combined, report)
    if not report.ok:
        return combined, report

    combined = _dedupe_annotations(combined, report)
    _validate_rater_counts(combined, report)
    combined = combined[~combined["ANNOTATORID"].isin(config.invalid)]
    return combined, report


def load_session_metadata(config: AnalysisConfig) -> pd.DataFrame | None:
    path = config.session_metadata_file
    if path is None or not path.exists():
        return None

    metadata = pd.read_csv(path, encoding="utf-8-sig")
    required = {"ANNOTATIONSESSIONID"}
    if not required.issubset(metadata.columns):
        raise ValueError(f"Session metadata must include columns: {sorted(required)}")

    metadata["ANNOTATIONSESSIONID"] = pd.to_numeric(
        metadata["ANNOTATIONSESSIONID"], errors="coerce"
    )
    return metadata


# ┌                                                ┐
# │                   Analytics                    │
# └                                                ┘
class Analytics(TypedDict):
    timestamp: int
    elapsed: float
    text_id: int
    assignments: AnalyticsAssignments
    events: AnalyticsEvents


class AnalyticsEvents(TypedDict):
    undo_redo: int
    completion: int
    # Disagreement resolution
    res_click: int
    res_bind: int
    zoom: int
    scanpath_move: int
    export: int


class AnalyticsAssignments(TypedDict):
    added: int
    removed: int
    invalidated: int
    un_invalidated: int


class AnalyticsRaw(TypedDict):
    d: AnalyticsEventsRaw
    f: AnalyticsAssignmentsRaw
    t: int
    e: float
    x: int


class AnalyticsEventsRaw(TypedDict):
    ur: int
    c: int
    dc: int
    db: int
    z: int
    sp: int
    e: int


class AnalyticsAssignmentsRaw(TypedDict):
    a: int  # added ann
    u: int  # deleted ann
    f: int  # invalidate
    d: int  # Undo invalidate


class AnalyticsDetails(TypedDict):
    raw: dict[int, list[Analytics]]
    aggregate: dict[int, list[AnalyticsAnalysisResults]]


def load_analytics(
    path: str, analytics_column: str = "analytics", user_id_column: str = "user_id"
) -> AnalyticsDetails:
    userdata = pd.read_csv(path)
    data: dict[int, list[Analytics]] = {}

    for idx, analytics in enumerate(userdata[analytics_column]):
        uid: int = int(cast(np.int64, userdata[user_id_column][idx]))
        raw: list[AnalyticsRaw] = json.loads(analytics)
        parsed: list[Analytics] = []
        for el in raw:
            parsed.append(
                {
                    "assignments": {
                        "added": el["f"]["a"],
                        "removed": el["f"]["u"],
                        "invalidated": el["f"]["f"],
                        "un_invalidated": el["f"]["d"],
                    },
                    "elapsed": el["e"],
                    "text_id": el["x"],
                    "events": {
                        "completion": el["d"]["c"],
                        "export": el["d"]["e"],
                        "res_bind": el["d"]["db"],
                        "res_click": el["d"]["dc"],
                        "scanpath_move": el["d"]["sp"],
                        "undo_redo": el["d"]["ur"],
                        "zoom": el["d"]["z"],
                    },
                    "timestamp": el["t"],
                }
            )

        data[uid] = parsed

    return {"raw": data, "aggregate": aggregate_analytics(data)}
