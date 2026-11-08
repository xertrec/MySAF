"""Validation and presentation of tool results returned by Android.

Android sends raw values straight from Room and Kotlin P2 (``HourAvailability``,
``Recommendations``...). This module:

1. validates them (an untrusted client must not inject arbitrary data), and
2. adds presentation-only fields for the model: ``time`` ("18:00"), ``load_pct``
   (load x 100, rounded), unit, display name, validation flags.

It performs **no** occupancy or recommendation logic: labels, usability,
alternatives and reductions all come from Kotlin.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.catalog import ACTIVITY_BY_ID, DATASET_FACTS, WEEKDAY_NAMES

Weekday = Literal["dl", "dt", "dc", "dj", "dv", "ds", "dg"]
Period = Literal["lectiu", "all"]


class _Out(BaseModel):
    # Unknown extra fields from newer app versions are dropped, not forwarded.
    model_config = ConfigDict(extra="ignore")


class ActivityRow(_Out):
    activity_id: str
    is_person_count: bool
    capacity: int = Field(ge=0)
    resource_ids: list[str] = Field(default_factory=list)


class ListActivitiesResult(_Out):
    activities: list[ActivityRow]


class FacilityInfoResult(_Out):
    activity: ActivityRow | None  # null when the id is not in the database


class OpeningHoursRow(_Out):
    weekday: Weekday
    open_min: int = Field(ge=0, le=1440)
    close_min: int = Field(ge=0, le=1440)


class OpeningHoursResult(_Out):
    opening_hours: list[OpeningHoursRow]


class HourRow(_Out):
    """Serialised ``HourAvailability`` plus Kotlin's ``occupancyLabel`` and ``isUsable``."""
    hour: int = Field(ge=0, le=23)
    occupied: int = Field(ge=0)
    capacity: int = Field(ge=0)
    load: float = Field(ge=0, le=10)
    is_closed: bool = False
    shift_change: bool = False
    low_data: bool = False
    long_block: bool = False
    usable: bool
    label: Literal["QUIET", "MODERATE", "FULL"]


class DayHours(_Out):
    weekday: Weekday
    hours: list[HourRow]


class HourlyOccupancyResult(_Out):
    activity_id: str
    period: Period
    days: list[DayHours]


class QuietSlot(_Out):
    weekday: Weekday
    row: HourRow


class QuieterSlotsResult(_Out):
    activity_id: str
    period: Period
    slots: list[QuietSlot]


class AlternativeOut(_Out):
    kind: Literal["SAME_DAY", "OTHER_DAY", "OTHER_ACTIVITY"]
    activity_id: str
    weekday: Weekday
    reduction_pp: int
    row: HourRow


class RecommendationResult(_Out):
    activity_id: str
    weekday: Weekday
    hour: int = Field(ge=0, le=23)
    period: Period
    requested: HourRow | None
    is_already_quiet: bool
    alternatives: list[AlternativeOut]
    no_result_reason: Literal["unknown_activity", "closed", "no_data", "already_quiet", "no_alternative_10pp"] | None = None


class DatasetInfoResult(_Out):
    entries: dict[str, str]


RESULT_MODELS: dict[str, type[_Out]] = {
    "list_activities": ListActivitiesResult,
    "get_opening_hours": OpeningHoursResult,
    "get_facility_info": FacilityInfoResult,
    "get_hourly_occupancy": HourlyOccupancyResult,
    "find_quieter_slots": QuieterSlotsResult,
    "recommend_alternatives": RecommendationResult,
    "get_dataset_info": DatasetInfoResult,
}

SOURCE_LABELS = {
    "list_activities": ("activity", "Catàleg d'activitats del SAF (base de dades mySAF)"),
    "get_facility_info": ("activity", "Inventari d'espais del SAF (aforaments provisionals)"),
    "get_opening_hours": ("opening_hours", "Horari general del SAF"),
    "get_hourly_occupancy": ("hourly_availability", "Ocupació històrica, abril–octubre 2026"),
    "find_quieter_slots": ("hourly_availability", "Motor de recomanacions (P2) sobre l'ocupació històrica"),
    "recommend_alternatives": ("hourly_availability", "Motor de recomanacions (P2) sobre l'ocupació històrica"),
    "get_dataset_info": ("dataset_info", "Metadades del conjunt de dades"),
}


def _hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _activity_meta(activity_id: str) -> dict[str, Any]:
    meta = ACTIVITY_BY_ID.get(activity_id)
    if meta is None:
        return {"activity_id": activity_id, "known_to_assistant": False}
    out: dict[str, Any] = {
        "activity_id": activity_id,
        "name": meta.names,
        "unit": meta.unit,
        "metric_validated": meta.metric_validated,
    }
    if meta.notes:
        out["notes"] = list(meta.notes)
    return out


def _hour(row: HourRow, unit: str | None) -> dict[str, Any]:
    d = row.model_dump()
    d["time"] = f"{row.hour:02d}:00"
    if row.is_closed:
        d["status"] = "closed"
    elif row.shift_change:
        d["status"] = "shift_change_no_data"
    else:
        d["load_pct"] = round(row.load * 100)
    if unit:
        d["unit"] = unit
    return d


def _unit(activity_id: str) -> str | None:
    meta = ACTIVITY_BY_ID.get(activity_id)
    return meta.unit if meta else None


def narrow(result: BaseModel, args: dict[str, Any]) -> BaseModel:
    """Defensive filter: keep only the weekdays/hours that were requested."""
    days = args.get("weekdays")
    if isinstance(result, OpeningHoursResult) and days:
        return result.model_copy(update={"opening_hours": [r for r in result.opening_hours if r.weekday in days]})
    if isinstance(result, HourlyOccupancyResult):
        lo, hi = args.get("hour_from", 0), args.get("hour_to", 23)
        kept = [d.model_copy(update={"hours": [h for h in d.hours if lo <= h.hour <= hi]})
                for d in result.days if not days or d.weekday in days]
        return result.model_copy(update={"days": kept})
    if isinstance(result, QuieterSlotsResult) and days:
        return result.model_copy(update={"slots": [x for x in result.slots if x.weekday in days]})
    return result


def present(name: str, result: BaseModel) -> dict[str, Any]:
    """Model-facing view of a validated result (formatting only)."""
    historical = {"historical_only": True, "coverage": f"{DATASET_FACTS['date_min']}..{DATASET_FACTS['date_max']}"}
    if isinstance(result, ListActivitiesResult):
        return {"activities": [{**r.model_dump(), **_activity_meta(r.activity_id),
                                "capacity_status": "provisional_inventory"} for r in result.activities]}
    if isinstance(result, FacilityInfoResult):
        if result.activity is None:
            return {"activity": None, "note": "Not found in the database."}
        r = result.activity
        return {"activity": {**r.model_dump(), **_activity_meta(r.activity_id),
                             "capacity_status": "provisional_inventory"}}
    if isinstance(result, OpeningHoursResult):
        return {"scope": "general SAF schedule (no per-facility hours available)",
                "opening_hours": [{"weekday": r.weekday, "weekday_name": WEEKDAY_NAMES[r.weekday],
                                   "open": _hhmm(r.open_min), "close": _hhmm(r.close_min)}
                                  for r in result.opening_hours]}
    if isinstance(result, HourlyOccupancyResult):
        u = _unit(result.activity_id)
        return {**_activity_meta(result.activity_id), "period": result.period, **historical,
                "days": [{"weekday": d.weekday, "hours": [_hour(h, u) for h in d.hours]} for d in result.days]}
    if isinstance(result, QuieterSlotsResult):
        u = _unit(result.activity_id)
        return {**_activity_meta(result.activity_id), "period": result.period, **historical,
                "source": "P2 recommendation engine",
                "slots": [{"weekday": s.weekday, **_hour(s.row, u)} for s in result.slots]}
    if isinstance(result, RecommendationResult):
        u = _unit(result.activity_id)
        return {**_activity_meta(result.activity_id), "period": result.period, **historical,
                "source": "P2 recommendation engine",
                "criteria": "Alternatives must be at least 10 percentage points quieter; other activities "
                            "only if measured in the same unit.",
                "weekday": result.weekday, "hour": result.hour,
                "requested": _hour(result.requested, u) if result.requested else None,
                "is_already_quiet": result.is_already_quiet,
                "no_result_reason": result.no_result_reason,
                "alternatives": [{"kind": a.kind, **_activity_meta(a.activity_id), "weekday": a.weekday,
                                  "reduction_pp": a.reduction_pp, **_hour(a.row, _unit(a.activity_id))}
                                 for a in result.alternatives]}
    if isinstance(result, DatasetInfoResult):
        return {"entries": result.entries, "periods": {"lectiu": DATASET_FACTS["lectiu"], "all": DATASET_FACTS["all"]}}
    return result.model_dump()
