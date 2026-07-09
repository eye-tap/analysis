from pathlib import Path
from typing import Optional, TypedDict

import pandas as pd
import json

from eyetap_analysis.config import AnalysisConfig
from eyetap_analysis.load import load_annotations
from eyetap_analysis.report import write_validation_report


class AnalyticsData(TypedDict):
    d: dict
    e: float
    t: float
    x: Optional[str]


def run_analysis(
    userdata: str,
    analytics_column: str,
    user_id_column: str,
    config: AnalysisConfig,
    out_dir: Path,
):
    ud = pd.read_csv(userdata)
    annotations, validation = load_annotations(config)

    out_dir.mkdir(parents=True, exist_ok=True)
    if not validation.ok or annotations.empty:
        write_validation_report(validation, out_dir)
        return 1

    # Compute time spent on texts
    decoded: list[list[AnalyticsData]] = []
    time_intervals: list[list[float]] = []
    for idx, user in enumerate(ud[analytics_column]):
        data: list[AnalyticsData] = json.loads(user)
        interval = 0
        intervals: list[float] = []
        for record in data:
            interval += record["e"]
            if record["e"] < 60:
                # We (likely) have a new text here
                intervals.append(interval)
                interval = 0
        if len(intervals) > 3:
            print(
                "WARNING: More than three intervals found for user with id",
                ud[user_id_column][idx],
                "The intervals are",
                intervals,
            )
        time_intervals.append(intervals)
        decoded.append(data)

    print(time_intervals)

    # Count fixations created per text
    grouped = annotations.groupby(
        [
            "reading_session_id",
            "ANNOTATORID",
        ],
        as_index=False,
    ).agg(
        annotations_per_session=("reading_session_id", "size"),
    )
    print(grouped)

    # Extrapolate which text user edited in given interval
    # For that:
    return 0
