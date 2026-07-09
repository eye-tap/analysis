from pathlib import Path
from typing import Optional, TypedDict, cast

import pandas as pd
import numpy as np
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
    decoded: dict[int, list[AnalyticsData]] = {}
    time_intervals: dict[int, list[float]] = {}
    for idx, analytics in enumerate(ud[analytics_column]):
        uid: int = int(cast(np.int64, ud[user_id_column][idx]))
        data: list[AnalyticsData] = json.loads(analytics)
        interval = 0
        intervals: list[float] = []
        for record in data:
            interval += record["e"]
            if record["e"] < 59 and record["e"] > 0 and interval > 61:
                # We (likely) have a new text here
                intervals.append(interval)
                interval = 0
        if interval > 0:
            intervals.append(interval)
        if len(intervals) > 3:
            print(
                "WARNING: More than three intervals found for user with id",
                uid,
                "The intervals are",
                intervals,
            )
        total = 0
        for el in intervals:
            total += el
        print("Total time for user", uid, "is", total)
        time_intervals[uid] = intervals
        decoded[uid] = data

    print(time_intervals)

    # Count fixations created per text
    grouped = annotations.groupby(
        ["ANNOTATORID", "reading_session_id"],
        as_index=False,
    ).agg(
        annotations_in_session=("reading_session_id", "size"),
    )
    print(grouped)

    # Extrapolate which text user edited in given interval
    # For that:
    return 0
