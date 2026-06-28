from __future__ import annotations

import pandas as pd

from eyetap_analysis.config import AnalysisConfig


def compute_session_efficiency(
    annotations: pd.DataFrame,
    config: AnalysisConfig,
    metadata: pd.DataFrame | None = None,
) -> pd.DataFrame:
    grouped = (
        annotations.groupby(
            [
                "cohort",
                "cohort_label",
                "preset",
                "reading_session_id",
                "ANNOTATIONSESSIONID",
                "ANNOTATORID",
            ],
            as_index=False,
        )
        .agg(
            annotation_count=("FIXATIONUID", "size"),
            unique_fixations_annotated=("FIXATIONUID", "nunique"),
        )
    )

    if grouped["annotation_count"].ne(grouped["unique_fixations_annotated"]).any():
        mismatched = grouped[
            grouped["annotation_count"] != grouped["unique_fixations_annotated"]
        ]
        raise ValueError(
            "Some sessions have duplicate FIXATIONUID assignments: "
            f"{mismatched['ANNOTATIONSESSIONID'].tolist()}"
        )

    if metadata is not None:
        grouped = grouped.merge(metadata, on="ANNOTATIONSESSIONID", how="left")
        if "total_fixations" in grouped.columns:
            grouped["completion_rate"] = grouped["annotation_count"] / grouped["total_fixations"]
        if {"annotation_count", "invalid_count", "total_fixations"}.issubset(grouped.columns):
            grouped["resolution_rate"] = (
                grouped["annotation_count"] + grouped["invalid_count"]
            ) / grouped["total_fixations"]

    timeout_col = None
    if metadata is not None and "timeout_sec" in metadata.columns:
        timeout_col = "timeout_sec"
    elif config.default_timeout_sec is not None:
        grouped["timeout_sec"] = config.default_timeout_sec
        timeout_col = "timeout_sec"

    if timeout_col is not None:
        grouped["annotations_per_minute"] = grouped["annotation_count"] / (
            grouped[timeout_col] / 60.0
        )

    return grouped


def summarize_cohort_efficiency(session_metrics: pd.DataFrame) -> pd.DataFrame:
    summary = (
        session_metrics.groupby(["cohort", "cohort_label", "preset"], as_index=False)
        .agg(
            n_sessions=("ANNOTATIONSESSIONID", "nunique"),
            n_annotators=("ANNOTATORID", "nunique"),
            mean_annotation_count=("annotation_count", "mean"),
            median_annotation_count=("annotation_count", "median"),
            std_annotation_count=("annotation_count", "std"),
            q25_annotation_count=("annotation_count", lambda s: s.quantile(0.25)),
            q75_annotation_count=("annotation_count", lambda s: s.quantile(0.75)),
        )
    )
    return summary


def summarize_reading_session_efficiency(session_metrics: pd.DataFrame) -> pd.DataFrame:
    return (
        session_metrics.groupby(["cohort", "cohort_label", "reading_session_id"], as_index=False)
        .agg(
            mean_annotation_count=("annotation_count", "mean"),
            n_sessions=("ANNOTATIONSESSIONID", "nunique"),
        )
    )
