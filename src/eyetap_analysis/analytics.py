from eyetap_analysis.dtype import Analytics, AnalyticsAnalysisResults


def aggregate_analytics(a: dict[int, list[Analytics]]):
    res: dict[int, list[AnalyticsAnalysisResults]] = {}

    for uid in a:
        user = a[uid]
        res[uid] = []
        idx = 0
        while idx < len(user):
            text_id = user[idx]["text_id"]
            d: AnalyticsAnalysisResults = {
                "assignments": {
                    "added": 0,
                    "invalidated": 0,
                    "removed": 0,
                    "un_invalidated": 0,
                },
                "elapsed": 0,
                "timestamp": user[0]["timestamp"] - int(user[0]["elapsed"] * 1000),
                "events": {
                    "completion": 0,
                    "export": 0,
                    "res_bind": 0,
                    "res_click": 0,
                    "scanpath_move": 0,
                    "undo_redo": 0,
                    "zoom": 0,
                },
                "text_id": text_id,
            }

            while idx < len(user) and user[idx]["text_id"] == text_id:
                frame = user[idx]
                d["assignments"] = {
                    "removed": d["assignments"]["removed"]
                    + frame["assignments"]["removed"],
                    "added": d["assignments"]["added"] + frame["assignments"]["added"],
                    "invalidated": d["assignments"]["invalidated"]
                    + frame["assignments"]["invalidated"],
                    "un_invalidated": d["assignments"]["un_invalidated"]
                    + frame["assignments"]["un_invalidated"],
                }
                d["events"] = {
                    "completion": d["events"]["completion"]
                    + frame["events"]["completion"],
                    "export": d["events"]["export"] + frame["events"]["export"],
                    "res_bind": d["events"]["res_bind"] + frame["events"]["res_bind"],
                    "res_click": d["events"]["res_bind"] + frame["events"]["res_click"],
                    "scanpath_move": d["events"]["scanpath_move"]
                    + frame["events"]["scanpath_move"],
                    "undo_redo": d["events"]["undo_redo"]
                    + frame["events"]["undo_redo"],
                    "zoom": d["events"]["zoom"] + frame["events"]["zoom"],
                }
                d["elapsed"] += frame["elapsed"]
                idx += 1

            res[uid].append(d)
    return res
