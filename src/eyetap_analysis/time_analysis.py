from typing import Optional, TypedDict

import pandas as pd
import json

from eyetap_analysis.config import AnalysisConfig


class AnalyticsData(TypedDict):
    d: dict
    e: float
    t: float
    x: Optional[str]


def run_analysis(
    userdata: str,
    annotations: str,
    analytics_column: str,
    user_id_column: str,
    config: AnalysisConfig,
):
    ud = pd.read_csv(userdata)
    ann = pd.read_csv(annotations)

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
    ann_counts: dict[int, dict[int, int]] = {}
    for idx, a in ann.iterrows():
        pass

    # Extrapolate which text user edited in given interval
    return 0
