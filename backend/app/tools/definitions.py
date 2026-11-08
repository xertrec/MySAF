"""Tool definitions: the JSON schemas sent to the model and the Pydantic models
that validate the arguments the model produces.

Every tool here is executed **on the Android device** (Room + Kotlin P2). The
backend never runs SQL. See docs/safia/ANDROID_INTEGRATION.md for the mapping of
each tool to existing Kotlin code.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.catalog import ACTIVITY_IDS, PERIODS, WEEKDAYS

ActivityId = Enum("ActivityId", {a: a for a in ACTIVITY_IDS}, type=str)  # type: ignore[misc]
Weekday = Literal["dl", "dt", "dc", "dj", "dv", "ds", "dg"]
Period = Literal["lectiu", "all"]


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class NoArgs(_Args):
    pass


class OpeningHoursArgs(_Args):
    weekdays: list[Weekday] | None = Field(default=None, min_length=1, max_length=7)


class FacilityArgs(_Args):
    activity_id: ActivityId


def _unique(v: list[str]) -> list[str]:
    seen: list[str] = []
    for d in v:
        if d not in seen:
            seen.append(d)
    return seen


class HourlyOccupancyArgs(_Args):
    activity_id: ActivityId
    weekdays: list[Weekday] = Field(min_length=1, max_length=7)
    hour_from: int | None = Field(default=None, ge=0, le=23)
    hour_to: int | None = Field(default=None, ge=0, le=23)
    period: Period = "lectiu"

    @field_validator("weekdays")
    @classmethod
    def _dedupe(cls, v: list[str]) -> list[str]:
        return _unique(v)

    @model_validator(mode="after")
    def _range(self) -> "HourlyOccupancyArgs":
        if self.hour_from is not None and self.hour_to is not None and self.hour_from > self.hour_to:
            raise ValueError("hour_from must be <= hour_to")
        return self


class QuieterSlotsArgs(_Args):
    activity_id: ActivityId
    weekdays: list[Weekday] = Field(min_length=1, max_length=7)
    period: Period = "lectiu"
    limit: int = Field(default=3, ge=1, le=5)

    @field_validator("weekdays")
    @classmethod
    def _dedupe(cls, v: list[str]) -> list[str]:
        return _unique(v)


class RecommendAlternativesArgs(_Args):
    activity_id: ActivityId
    weekday: Weekday
    hour: int = Field(ge=0, le=23)
    period: Period = "lectiu"


_ACTIVITY = {"type": "string", "enum": list(ACTIVITY_IDS),
             "description": "Activity id from the SAFIA catalogue."}
_WEEKDAYS = {"type": "array", "items": {"type": "string", "enum": list(WEEKDAYS)}, "minItems": 1, "maxItems": 7,
             "description": "Catalan weekday codes: dl=Mon, dt=Tue, dc=Wed, dj=Thu, dv=Fri, ds=Sat, dg=Sun. "
                            "Weekend = [\"ds\",\"dg\"]; weekdays = [\"dl\",\"dt\",\"dc\",\"dj\",\"dv\"]."}
_PERIOD = {"type": "string", "enum": list(PERIODS),
           "description": "lectiu = Apr-Jun and Sep-Oct 2026 (default). all = Apr-Oct 2026 including July/August."}


def _fn(name: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required,
                           "additionalProperties": False},
        },
    }


TOOL_SCHEMAS: list[dict[str, Any]] = [
    _fn("list_activities",
        "List every SAF activity/facility covered by the database, with its unit (people or courts), "
        "capacity and the physical resources it aggregates.",
        {}, []),
    _fn("get_opening_hours",
        "General SAF opening hours per weekday. Only the general schedule exists; there are no "
        "per-facility hours.",
        {"weekdays": _WEEKDAYS}, []),
    _fn("get_facility_info",
        "Capacity, unit (people for rooms/pools, courts for courts/pitches) and resources of one activity. "
        "Use for 'how many courts', 'what is the capacity of...'.",
        {"activity_id": _ACTIVITY}, ["activity_id"]),
    _fn("get_hourly_occupancy",
        "Historical average occupancy per hour for one activity on the given weekdays (Apr-Oct 2026). "
        "Historical patterns only, never live data.",
        {"activity_id": _ACTIVITY, "weekdays": _WEEKDAYS,
         "hour_from": {"type": "integer", "minimum": 0, "maximum": 23, "description": "Optional first hour (inclusive)."},
         "hour_to": {"type": "integer", "minimum": 0, "maximum": 23, "description": "Optional last hour (inclusive)."},
         "period": _PERIOD},
        ["activity_id", "weekdays"]),
    _fn("find_quieter_slots",
        "Recommendation engine (P2): the historically quietest reliable hours of one activity on the "
        "given weekdays. Use for 'when is X less crowded / best time to go'.",
        {"activity_id": _ACTIVITY, "weekdays": _WEEKDAYS, "period": _PERIOD,
         "limit": {"type": "integer", "minimum": 1, "maximum": 5, "description": "Slots per weekday (default 3)."}},
        ["activity_id", "weekdays"]),
    _fn("recommend_alternatives",
        "Recommendation engine (P2): quieter alternatives to one activity at a given weekday and hour: "
        "a nearby hour the same day, the same hour another day, or another comparable activity. "
        "Use for 'alternative to X', 'X is busy at H, what else'.",
        {"activity_id": _ACTIVITY, "weekday": {"type": "string", "enum": list(WEEKDAYS)},
         "hour": {"type": "integer", "minimum": 0, "maximum": 23, "description": "Requested hour, 0-23."},
         "period": _PERIOD},
        ["activity_id", "weekday", "hour"]),
    _fn("get_dataset_info",
        "Coverage of the historical dataset (date range, active days, cleaning rule version).",
        {}, []),
]

ARG_MODELS: dict[str, type[_Args]] = {
    "list_activities": NoArgs,
    "get_opening_hours": OpeningHoursArgs,
    "get_facility_info": FacilityArgs,
    "get_hourly_occupancy": HourlyOccupancyArgs,
    "find_quieter_slots": QuieterSlotsArgs,
    "recommend_alternatives": RecommendAlternativesArgs,
    "get_dataset_info": NoArgs,
}

DEVICE_TOOLS = frozenset(ARG_MODELS)
P2_TOOLS = frozenset({"find_quieter_slots", "recommend_alternatives"})
