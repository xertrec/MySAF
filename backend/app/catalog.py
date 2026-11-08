"""Static description of what the Android database covers.

Mirrors, without adding data:
- activity ids and units: ``activity`` table / ``ActivityCatalog.kt``
- display names: ``app/src/main/res/values*/strings.xml`` (Spanish added here)
- validation status: ``data_engineering/data/interim/mapping/resource_alias.csv``
- dataset coverage and limitations: ``dataset_info`` + methodology strings

No capacities or occupancy figures live here: those always come from tool results.
"""
from __future__ import annotations

from dataclasses import dataclass, field

WEEKDAYS = ("dl", "dt", "dc", "dj", "dv", "ds", "dg")
WEEKDAY_NAMES = {
    "dl": {"ca": "dilluns", "es": "lunes", "en": "Monday"},
    "dt": {"ca": "dimarts", "es": "martes", "en": "Tuesday"},
    "dc": {"ca": "dimecres", "es": "miércoles", "en": "Wednesday"},
    "dj": {"ca": "dijous", "es": "jueves", "en": "Thursday"},
    "dv": {"ca": "divendres", "es": "viernes", "en": "Friday"},
    "ds": {"ca": "dissabte", "es": "sábado", "en": "Saturday"},
    "dg": {"ca": "diumenge", "es": "domingo", "en": "Sunday"},
}
PERIODS = ("lectiu", "all")


@dataclass(frozen=True)
class ActivityMeta:
    id: str
    unit: str  # "people" (rooms/pools) or "courts" (courts/pitches)
    names: dict[str, str]
    aliases: tuple[str, ...] = ()
    metric_validated: bool = True
    notes: tuple[str, ...] = field(default_factory=tuple)


ACTIVITIES: tuple[ActivityMeta, ...] = (
    ActivityMeta("piscina_25m", "people",
                 {"ca": "Piscina de 25 m", "es": "Piscina de 25 m", "en": "25 m swimming pool"},
                 ("piscina", "pool", "natació", "natación", "swimming")),
    ActivityMeta("sala_fitness", "people",
                 {"ca": "Sala fitness", "es": "Sala de fitness", "en": "Fitness room"},
                 ("gimnàs", "gimnasio", "gym", "fitness", "sala de musculació", "musculación"),
                 notes=("Shift changes at 10:00 and 15:00 have no reliable data.",)),
    ActivityMeta("padel", "courts", {"ca": "Pàdel", "es": "Pádel", "en": "Padel"}, ("padbol",)),
    ActivityMeta("tennis", "courts", {"ca": "Tennis", "es": "Tenis", "en": "Tennis"}, ("pickleball", "tenis")),
    ActivityMeta("esquaix", "courts", {"ca": "Esquaix", "es": "Squash", "en": "Squash"}, ("squash", "c. soccer")),
    ActivityMeta("pavello", "courts",
                 {"ca": "Pavelló (bàsquet, vòlei, bàdminton)", "es": "Pabellón (baloncesto, vóley, bádminton)",
                  "en": "Sports hall (basketball, volleyball, badminton)"},
                 ("pabellón", "bàsquet", "baloncesto", "basketball", "vòlei", "voleibol", "bàdminton", "bádminton")),
    ActivityMeta("futbol_sala", "courts", {"ca": "Futbol sala", "es": "Fútbol sala", "en": "Futsal"}, ("futsal",)),
    ActivityMeta("futbol_7_11", "courts",
                 {"ca": "Futbol 7/11", "es": "Fútbol 7/11", "en": "7-a-side / 11-a-side football"},
                 ("futbol", "fútbol", "football", "soccer", "rugbi", "rugby")),
    ActivityMeta("barbell", "people", {"ca": "Espai barbell", "es": "Espacio barbell", "en": "Barbell area"},
                 ("halterofília", "halterofilia", "weightlifting", "crossfit")),
    ActivityMeta("callistenia", "people", {"ca": "Cal·listènia", "es": "Calistenia", "en": "Calisthenics"},
                 ("calistènia",), metric_validated=False),
    ActivityMeta("rocodrom", "people", {"ca": "Rocòdrom", "es": "Rocódromo", "en": "Climbing wall"},
                 ("escalada", "climbing", "boulder"), metric_validated=False),
)
ACTIVITY_IDS = tuple(a.id for a in ACTIVITIES)
ACTIVITY_BY_ID = {a.id: a for a in ACTIVITIES}
UNVALIDATED_ACTIVITY_IDS = frozenset(a.id for a in ACTIVITIES if not a.metric_validated)

# Facilities that exist at the SAF but that the database does not cover.
NOT_COVERED = (
    "16 m pool (piscina petita)",
    "cycling room, rhythm rooms, zen room, box training room",
    "beach volleyball, outdoor basketball court",
    "directed activities / classes (timetables, enrolment)",
    "per-facility opening hours (only the general SAF schedule is available)",
    "prices, memberships, bookings, rules, staff, changing rooms",
    "real-time or live occupancy",
)

DATASET_FACTS = {
    "date_min": "2026-04-01",
    "date_max": "2026-10-31",
    "lectiu": "April–June and September–October 2026 (default period)",
    "all": "every month April–October 2026, including the much quieter July and August",
}
