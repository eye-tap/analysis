from __future__ import annotations

from dataclasses import dataclass

import krippendorff
import numpy as np
import pandas as pd

from eyetap_analysis.config import AnalysisConfig

ICC_TYPE_PREFERENCE = ("ICC(A,1)", "ICC(2,1)", "ICC2")


@dataclass
class AgreementResult:
    cohort: str
    cohort_label: str
    reading_session_id: str
    n_fixations: int
    n_raters: int
    icc_2_1: float | None
    icc_ci_lower: float | None
    icc_ci_upper: float | None
    fleiss_kappa: float | None
    krippendorff_alpha: float | None
    exact_agreement_rate: float | None
    spatial_icc_x: float | None = None
    spatial_icc_y: float | None = None
    warning: str | None = None


def build_wide_matrix(group: pd.DataFrame) -> pd.DataFrame:
    wide = group.pivot_table(
        index="FIXATIONUID",
        columns="ANNOTATORID",
        values="CHARUID",
        aggfunc="first",
    )
    return wide.dropna(how="all")


def _fixations_with_multiple_raters(wide: pd.DataFrame, min_raters: int = 2) -> pd.DataFrame:
    counts = wide.notna().sum(axis=1)
    return wide.loc[counts >= min_raters]


def _exact_agreement_rate(wide: pd.DataFrame) -> float | None:
    if wide.shape[0] == 0 or wide.shape[1] < 2:
        return None

    agreements = []
    for _, row in wide.iterrows():
        values = row.dropna().to_numpy()
        if len(values) < 2:
            continue
        agreements.append(values.max() == values.min())
    if not agreements:
        return None
    return float(np.mean(agreements))


def _compute_icc(wide: pd.DataFrame) -> tuple[float | None, float | None, float | None]:
    import pingouin as pg

    complete = wide.dropna()
    if complete.shape[0] < 2 or complete.shape[1] < 2:
        return None, None, None

    long = complete.reset_index().melt(
        id_vars="FIXATIONUID",
        var_name="rater",
        value_name="rating",
    )
    try:
        icc = pg.intraclass_corr(
            data=long,
            targets="FIXATIONUID",
            raters="rater",
            ratings="rating",
        )
        row = None
        for icc_type in ICC_TYPE_PREFERENCE:
            match = icc.loc[icc["Type"] == icc_type]
            if not match.empty:
                row = match.iloc[0]
                break
        if row is None:
            return None, None, None
        value = float(row["ICC"])
        ci_column = "CI95%" if "CI95%" in icc.columns else "CI95"
        ci = row[ci_column]
        if isinstance(ci, str):
            ci = ci.strip("[]").split(",")
        return value, float(ci[0]), float(ci[1])
    except Exception:
        return None, None, None


def _compute_fleiss_kappa(wide: pd.DataFrame) -> float | None:
    complete = wide.dropna()
    if complete.shape[0] < 1 or complete.shape[1] < 2:
        return None

    categories = sorted(set(complete.to_numpy().ravel().tolist()))
    if len(categories) < 2:
        return None

    cat_to_idx = {cat: idx for idx, cat in enumerate(categories)}
    encoded = complete.map(lambda value: cat_to_idx[value]).to_numpy(dtype=int)
    n_subjects, n_raters = encoded.shape
    n_categories = len(categories)
    counts = np.zeros((n_subjects, n_categories), dtype=int)
    for i in range(n_subjects):
        for j in range(n_raters):
            counts[i, encoded[i, j]] += 1

    n = n_raters
    p_i = ((counts * (counts - 1)).sum(axis=1)) / (n * (n - 1))
    p_bar = float(np.mean(p_i))
    p_j = counts.sum(axis=0) / (n_subjects * n)
    p_e = float(np.sum(p_j**2))
    if np.isclose(1.0 - p_e, 0.0):
        return None
    return (p_bar - p_e) / (1.0 - p_e)


def _compute_krippendorff_alpha(wide: pd.DataFrame) -> float | None:
    if wide.shape[0] < 1 or wide.shape[1] < 2:
        return None
    matrix = wide.to_numpy(dtype=float).T
    try:
        return float(krippendorff.alpha(reliability_data=matrix, level_of_measurement="nominal"))
    except Exception:
        return None


def _load_character_centroids(characters_file) -> pd.DataFrame:
    chars = pd.read_csv(characters_file, encoding="utf-8-sig")
    chars["char_uid"] = pd.to_numeric(chars["char_uid"], errors="coerce")
    chars["centroid_x"] = (chars["x_min"] + chars["x_max"]) / 2.0
    chars["centroid_y"] = (chars["y_min"] + chars["y_max"]) / 2.0
    return chars.set_index("char_uid")[["centroid_x", "centroid_y"]]


def _compute_spatial_icc(
    wide: pd.DataFrame, centroids: pd.DataFrame
) -> tuple[float | None, float | None]:
    spatial = wide.copy()
    for column in spatial.columns:
        spatial[column] = spatial[column].map(
            lambda char_uid: centroids.loc[char_uid, "centroid_x"]
            if char_uid in centroids.index
            else np.nan
        )
    icc_x = _compute_icc(spatial)[0]

    spatial = wide.copy()
    for column in spatial.columns:
        spatial[column] = spatial[column].map(
            lambda char_uid: centroids.loc[char_uid, "centroid_y"]
            if char_uid in centroids.index
            else np.nan
        )
    icc_y = _compute_icc(spatial)[0]
    return icc_x, icc_y


def compute_agreement_by_group(
    annotations: pd.DataFrame,
    config: AnalysisConfig,
) -> list[AgreementResult]:
    centroids = None
    if config.characters_file is not None and config.characters_file.exists():
        centroids = _load_character_centroids(config.characters_file)

    results: list[AgreementResult] = []
    group_keys = ["cohort", "cohort_label", "reading_session_id"]

    for (cohort, cohort_label, reading_session_id), group in annotations.groupby(group_keys):
        wide = build_wide_matrix(group)
        wide = _fixations_with_multiple_raters(wide)
        n_raters = wide.notna().any(axis=0).sum()
        warning = None
        if n_raters < 2:
            warning = "Fewer than 2 raters with overlapping fixations"

        icc, icc_lo, icc_hi = _compute_icc(wide)
        kappa = _compute_fleiss_kappa(wide)
        alpha = _compute_krippendorff_alpha(wide)
        exact = _exact_agreement_rate(wide)

        spatial_x = spatial_y = None
        if centroids is not None and not wide.empty:
            spatial_x, spatial_y = _compute_spatial_icc(wide, centroids)

        results.append(
            AgreementResult(
                cohort=cohort,
                cohort_label=cohort_label,
                reading_session_id=reading_session_id,
                n_fixations=int(wide.shape[0]),
                n_raters=int(n_raters),
                icc_2_1=icc,
                icc_ci_lower=icc_lo,
                icc_ci_upper=icc_hi,
                fleiss_kappa=kappa,
                krippendorff_alpha=alpha,
                exact_agreement_rate=exact,
                spatial_icc_x=spatial_x,
                spatial_icc_y=spatial_y,
                warning=warning,
            )
        )

    return results


def agreement_results_to_frame(results: list[AgreementResult]) -> pd.DataFrame:
    return pd.DataFrame([result.__dict__ for result in results])


def summarize_cohort_agreement(agreement_frame: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        "icc_2_1",
        "fleiss_kappa",
        "krippendorff_alpha",
        "exact_agreement_rate",
        "spatial_icc_x",
        "spatial_icc_y",
    ]
    rows = []
    for (cohort, cohort_label), group in agreement_frame.groupby(["cohort", "cohort_label"]):
        row = {"cohort": cohort, "cohort_label": cohort_label, "n_reading_sessions": len(group)}
        for metric in metrics:
            if metric not in group.columns:
                continue
            row[f"{metric}_mean"] = group[metric].mean()
            row[f"{metric}_std"] = group[metric].std(ddof=0)
            row[f"{metric}_count"] = group[metric].notna().sum()
        rows.append(row)
    return pd.DataFrame(rows)
