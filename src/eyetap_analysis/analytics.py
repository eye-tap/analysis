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
                if text_id == -2:
                    idx += 1
                    continue

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

            if text_id != -2:
                res[uid].append(d)
    return res


def sum_analytics(a: dict[int, list[AnalyticsAnalysisResults]]):
    data: dict[int, list[AnalyticsAnalysisResults]] = {}

    for uid, user in a.items():
        d: dict[int, AnalyticsAnalysisResults] = {}

        for val in user:
            text_id = val["text_id"]

            if text_id not in d:
                d[text_id] = val.copy()
                continue

            d[text_id]["assignments"]["added"] += val["assignments"]["added"]
            d[text_id]["assignments"]["removed"] += val["assignments"]["removed"]
            d[text_id]["assignments"]["invalidated"] += val["assignments"]["invalidated"]
            d[text_id]["assignments"]["un_invalidated"] += val["assignments"]["un_invalidated"]

            d[text_id]["events"]["completion"] += val["events"]["completion"]
            d[text_id]["events"]["res_bind"] += val["events"]["res_bind"]
            d[text_id]["events"]["res_click"] += val["events"]["res_click"]
            d[text_id]["events"]["scanpath_move"] += val["events"]["scanpath_move"]
            d[text_id]["events"]["export"] += val["events"]["export"]
            d[text_id]["events"]["undo_redo"] += val["events"]["undo_redo"]
            d[text_id]["events"]["zoom"] += val["events"]["zoom"]

            d[text_id]["elapsed"] += val["elapsed"]

        data[uid] = list(d.values())

    return data