from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from eyetap_analysis.agreement import (
    agreement_results_to_frame,
    compute_agreement_by_group,
    summarize_cohort_agreement,
)
from eyetap_analysis.config import load_config
from eyetap_analysis.efficiency import (
    compute_session_efficiency,
    summarize_cohort_efficiency,
    summarize_reading_session_efficiency,
)
from eyetap_analysis.load import load_annotations, load_session_metadata
from eyetap_analysis.report import write_analysis_outputs, write_validation_report
from eyetap_analysis.stats import (
    compare_efficiency_across_cohorts,
    summarize_agreement_with_ci,
)


def _parse_cohort_overrides(raw: list[str] | None) -> dict[str, Path]:
    overrides: dict[str, Path] = {}
    if not raw:
        return overrides
    for item in raw:
        name, path = item.split("=", maxsplit=1)
        overrides[name.strip()] = Path(path.strip())
    return overrides


def run_analysis(config_path: Path, output_dir: Path, cohort_overrides: dict[str, Path] | None = None) -> int:
    config = load_config(config_path, cohort_overrides=cohort_overrides or {})
    annotations, validation = load_annotations(config)

    output_dir.mkdir(parents=True, exist_ok=True)
    if not validation.ok or annotations.empty:
        write_validation_report(validation, output_dir)
        return 1

    metadata = load_session_metadata(config)
    session_efficiency = compute_session_efficiency(annotations, config, metadata)
    cohort_efficiency_summary = summarize_cohort_efficiency(session_efficiency)
    reading_session_efficiency = summarize_reading_session_efficiency(session_efficiency)

    agreement_results = compute_agreement_by_group(annotations, config)
    agreement_by_reading_session = agreement_results_to_frame(agreement_results)
    cohort_agreement_summary = summarize_cohort_agreement(agreement_by_reading_session)
    cohort_agreement_ci = summarize_agreement_with_ci(agreement_by_reading_session)

    efficiency_tests, efficiency_pairwise = compare_efficiency_across_cohorts(session_efficiency)

    outputs = write_analysis_outputs(
        output_dir,
        validation_report=validation,
        session_efficiency=session_efficiency,
        cohort_efficiency_summary=cohort_efficiency_summary,
        reading_session_efficiency=reading_session_efficiency,
        agreement_by_reading_session=agreement_by_reading_session,
        cohort_agreement_summary=cohort_agreement_summary,
        cohort_agreement_ci=cohort_agreement_ci,
        efficiency_tests=efficiency_tests,
        efficiency_pairwise=efficiency_pairwise,
    )

    print(f"Analysis complete. Outputs written to {output_dir}")
    for name, path in outputs.items():
        if path is not None:
            print(f"  - {name}")

    print("\nSession annotation counts:")
    print(
        session_efficiency[["cohort", "ANNOTATIONSESSIONID", "annotation_count"]]
        .sort_values(["cohort", "ANNOTATIONSESSIONID"])
        .to_string(index=False)
    )

    if validation.warnings:
        print("\nWarnings:")
        for warning in validation.warnings:
            print(f"  - {warning}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run eyetracking annotation survey analysis")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.yaml"),
        help="Path to config.yaml",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory (default: outputs/run_<today>/)",
    )
    parser.add_argument(
        "--cohort-file",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="Override cohort CSV path, e.g. cohort1=data/cohort1.csv",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config_path = args.config.resolve()
    overrides = _parse_cohort_overrides(args.cohort_file)

    output_dir = args.output
    if output_dir is None:
        output_dir = Path("outputs") / f"run_{date.today().isoformat()}"
    output_dir = output_dir.resolve()

    return run_analysis(config_path, output_dir, overrides or None)


if __name__ == "__main__":
    raise SystemExit(main())

