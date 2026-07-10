from typing import TypedDict


class AnalyticsEvents(TypedDict):
    undo_redo: int
    completion: int
    # Disagreement resolution
    res_click: int
    res_bind: int
    zoom: int
    scanpath_move: int
    export: int


class AnalyticsAssignments(TypedDict):
    added: int
    removed: int
    invalidated: int
    un_invalidated: int


class AnalyticsEventsRaw(TypedDict):
    ur: int
    c: int
    dc: int
    db: int
    z: int
    sp: int
    e: int


class AnalyticsAssignmentsRaw(TypedDict):
    a: int  # added ann
    u: int  # deleted ann
    f: int  # invalidate
    d: int  # Undo invalidate


class Analytics(TypedDict):
    timestamp: int
    elapsed: float
    text_id: int
    assignments: AnalyticsAssignments
    events: AnalyticsEvents


class AnalyticsRaw(TypedDict):
    d: AnalyticsEventsRaw
    f: AnalyticsAssignmentsRaw
    t: int
    e: float
    x: int


class AnalyticsAnalysisResults(Analytics):
    pass


class AnalyticsDetails(TypedDict):
    raw: dict[int, list[Analytics]]
    aggregate: dict[int, list[AnalyticsAnalysisResults]]
    total: dict[int, list[AnalyticsAnalysisResults]]
