from __future__ import annotations

import pandas as pd

from eyetap_analysis.config import AnalysisConfig


def compute_session_efficiency(
    analytics: pd.DataFrame,
) -> pd.DataFrame:

    analytics["added_per_sec"] = analytics["added"] / analytics["elapsed"]

    result = analytics.groupby("text_id", as_index=False).agg(
        mean_added_per_sec=("added_per_sec", "mean"),
        mean_added=("added", "mean"),
        mean_elapsed=("elapsed", "mean"),
        n_users=("user_id", "count"),
    )

    print(result)
    return result


def summarize_cohort_efficiency(session_metrics: pd.DataFrame) -> pd.DataFrame:
    summary = session_metrics.groupby(
        ["cohort", "cohort_label", "preset"], as_index=False
    ).agg(
        n_sessions=("ANNOTATIONSESSIONID", "nunique"),
        n_annotators=("ANNOTATORID", "nunique"),
        mean_annotation_count=("annotation_count", "mean"),
        median_annotation_count=("annotation_count", "median"),
        std_annotation_count=("annotation_count", "std"),
        q25_annotation_count=("annotation_count", lambda s: s.quantile(0.25)),
        q75_annotation_count=("annotation_count", lambda s: s.quantile(0.75)),
    )
    return summary


def summarize_reading_session_efficiency(session_metrics: pd.DataFrame) -> pd.DataFrame:
    return session_metrics.groupby(
        ["cohort", "cohort_label", "reading_session_id"], as_index=False
    ).agg(
        mean_annotation_count=("annotation_count", "mean"),
        n_sessions=("ANNOTATIONSESSIONID", "nunique"),
    )
