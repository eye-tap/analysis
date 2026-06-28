from __future__ import annotations

from pathlib import Path

import pandas as pd

from eyetap_analysis.load import ValidationReport
from eyetap_analysis.stats import TestResult


def write_validation_report(report: ValidationReport, output_dir: Path) -> Path:
    path = output_dir / "validation_report.txt"
    lines = ["=== Validation Report ===", ""]
    if report.messages:
        lines.append("Info:")
        lines.extend(f"  - {message}" for message in report.messages)
        lines.append("")
    if report.warnings:
        lines.append("Warnings:")
        lines.extend(f"  - {message}" for message in report.warnings)
        lines.append("")
    if report.errors:
        lines.append("Errors:")
        lines.extend(f"  - {message}" for message in report.errors)
        lines.append("")
    lines.append(f"Status: {'OK' if report.ok else 'FAILED'}")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_csv(frame: pd.DataFrame, output_dir: Path, name: str) -> Path | None:
    if frame is None or frame.empty:
        return None
    path = output_dir / name
    frame.to_csv(path, index=False)
    return path


def write_analysis_outputs(
    output_dir: Path,
    *,
    validation_report: ValidationReport,
    session_efficiency: pd.DataFrame,
    cohort_efficiency_summary: pd.DataFrame,
    reading_session_efficiency: pd.DataFrame,
    agreement_by_reading_session: pd.DataFrame,
    cohort_agreement_summary: pd.DataFrame,
    cohort_agreement_ci: pd.DataFrame,
    efficiency_tests: list[TestResult],
    efficiency_pairwise: pd.DataFrame,
) -> dict[str, Path | None]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "validation_report.txt": write_validation_report(validation_report, output_dir),
        "session_efficiency.csv": write_csv(session_efficiency, output_dir, "session_efficiency.csv"),
        "cohort_efficiency_summary.csv": write_csv(
            cohort_efficiency_summary, output_dir, "cohort_efficiency_summary.csv"
        ),
        "reading_session_efficiency.csv": write_csv(
            reading_session_efficiency, output_dir, "reading_session_efficiency.csv"
        ),
        "agreement_by_reading_session.csv": write_csv(
            agreement_by_reading_session, output_dir, "agreement_by_reading_session.csv"
        ),
        "cohort_agreement_summary.csv": write_csv(
            cohort_agreement_summary, output_dir, "cohort_agreement_summary.csv"
        ),
        "cohort_agreement_ci.csv": write_csv(
            cohort_agreement_ci, output_dir, "cohort_agreement_ci.csv"
        ),
        "efficiency_tests.csv": write_csv(
            pd.DataFrame([result.__dict__ for result in efficiency_tests]),
            output_dir,
            "efficiency_tests.csv",
        ),
        "efficiency_pairwise.csv": write_csv(
            efficiency_pairwise, output_dir, "efficiency_pairwise.csv"
        ),
    }
    return outputs
