from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import kruskal, mannwhitneyu

PAIRWISE_COHORT_COMPARISONS = (
    ("cohort2", "cohort1"),
    ("cohort3", "cohort1"),
    ("cohort3", "cohort2"),
)


@dataclass
class TestResult:
    test_name: str
    metric: str
    statistic: float | None
    p_value: float | None
    details: str


def _rank_biserial(u_stat: float, n1: int, n2: int) -> float:
    return (2.0 * u_stat) / (n1 * n2) - 1.0


def _holm_correction(p_values: list[float]) -> list[float]:
    m = len(p_values)
    order = np.argsort(p_values)
    adjusted = [0.0] * m
    running_max = 0.0
    for rank, idx in enumerate(order):
        corrected = min(1.0, p_values[idx] * (m - rank))
        running_max = max(running_max, corrected)
        adjusted[idx] = running_max
    return adjusted


def compare_efficiency_across_cohorts(session_metrics: pd.DataFrame) -> tuple[list[TestResult], pd.DataFrame]:
    results: list[TestResult] = []
    cohorts = sorted(session_metrics["cohort"].unique())
    samples = [
        session_metrics.loc[session_metrics["cohort"] == cohort, "annotation_count"].to_numpy()
        for cohort in cohorts
    ]

    if len(cohorts) >= 2 and all(len(sample) > 0 for sample in samples):
        stat, p_value = kruskal(*samples)
        results.append(
            TestResult(
                test_name="kruskal_wallis",
                metric="annotation_count",
                statistic=float(stat),
                p_value=float(p_value),
                details=f"cohorts={cohorts}",
            )
        )

    pairwise_rows = []
    raw_p_values = []
    for left, right in PAIRWISE_COHORT_COMPARISONS:
        left_values = session_metrics.loc[
            session_metrics["cohort"] == left, "annotation_count"
        ].to_numpy()
        right_values = session_metrics.loc[
            session_metrics["cohort"] == right, "annotation_count"
        ].to_numpy()
        if len(left_values) == 0 or len(right_values) == 0:
            continue
        u_stat, p_value = mannwhitneyu(left_values, right_values, alternative="two-sided")
        raw_p_values.append(float(p_value))
        pairwise_rows.append(
            {
                "comparison": f"{left}_vs_{right}",
                "metric": "annotation_count",
                "u_statistic": float(u_stat),
                "p_value_raw": float(p_value),
                "rank_biserial": _rank_biserial(float(u_stat), len(left_values), len(right_values)),
                "n_left": len(left_values),
                "n_right": len(right_values),
            }
        )

    if pairwise_rows:
        adjusted = _holm_correction(raw_p_values)
        for row, p_adj in zip(pairwise_rows, adjusted):
            row["p_value_holm"] = p_adj
            results.append(
                TestResult(
                    test_name="mann_whitney_u",
                    metric=row["metric"],
                    statistic=row["u_statistic"],
                    p_value=row["p_value_holm"],
                    details=row["comparison"],
                )
            )

    return results, pd.DataFrame(pairwise_rows)


def bootstrap_mean_ci(
    values: pd.Series,
    *,
    n_bootstrap: int = 2000,
    alpha: float = 0.05,
    seed: int = 42,
) -> tuple[float, float, float]:
    clean = values.dropna().to_numpy()
    if len(clean) == 0:
        return np.nan, np.nan, np.nan
    if len(clean) == 1:
        return float(clean[0]), float(clean[0]), float(clean[0])

    rng = np.random.default_rng(seed)
    means = []
    for _ in range(n_bootstrap):
        sample = rng.choice(clean, size=len(clean), replace=True)
        means.append(float(np.mean(sample)))
    lower = float(np.quantile(means, alpha / 2))
    upper = float(np.quantile(means, 1 - alpha / 2))
    return float(np.mean(clean)), lower, upper


def summarize_agreement_with_ci(agreement_frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    metrics = ["icc_2_1", "fleiss_kappa", "krippendorff_alpha", "exact_agreement_rate"]
    for (cohort, cohort_label), group in agreement_frame.groupby(["cohort", "cohort_label"]):
        row = {"cohort": cohort, "cohort_label": cohort_label}
        for metric in metrics:
            if metric not in group.columns:
                continue
            mean, lower, upper = bootstrap_mean_ci(group[metric])
            row[f"{metric}_mean"] = mean
            row[f"{metric}_ci_lower"] = lower
            row[f"{metric}_ci_upper"] = upper
        rows.append(row)
    return pd.DataFrame(rows)


def test_results_to_frame(results: list[TestResult]) -> pd.DataFrame:
    return pd.DataFrame([result.__dict__ for result in results])
