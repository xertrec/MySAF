"""
04_create_database.py

Paso 4 del pipeline mySAF: exporta los datos limpios a la base de datos SQLite
que la app Android carga con Room (`createFromAsset`).

Entradas (generadas por clean_data.py):
- data/interim/clean/reservation_slot_agg.parquet
- data/interim/clean/reservations_clean.parquet
- data/interim/mapping/resource_alias.csv
- data/raw/saf-espais-2026-equips.xlsx  (hoja "Horari general")

Salidas:
- database/mysaf.db                                  (copia de trabajo)
- ../app/src/main/assets/database/mysaf.db           (la que empaqueta la app)
- data/processed/hourly_availability.csv             (misma tabla, para revisar)

Tablas (el esquema debe coincidir EXACTAMENTE con las @Entity de Room,
ver app/.../data/db/Entities.kt; Room lo valida al abrir):
- activity              una fila por actividad de la app
- hourly_availability   actividad x periodo x dia de la semana x hora
- opening_hours         horario general por dia de la semana
- dataset_info          metadatos (rango de fechas, reglas, version)

Reglas:
- Ocupacion de una hora = media de sus 4 franjas de 15 min (una franja sin fila
  cuenta como 0). Personas: avg_concurrent. Pistas/camps: units_busy_avg
  (fraccion de la pista ocupada, ya incluye mitades/subdivisiones).
- Una actividad agrega varios resource_id sumando su ocupacion. capacity:
  personas = aforo de inventario de `capacity_resources`; pistas = numero de
  recursos.
- Alcance "all" (incluye bloques largos y nocturnos). long_block_share = parte
  de los minutos reservados que vienen de bloques largos/nocturnos.
- Dias sin actividad del centro (festivos, fines de semana de agosto): un dia
  con menos de CLOSED_DAY_MAX_ROWS reservas en total se excluye de las medias.
- Media = media sobre los dias activos de ese dia de la semana y periodo.
  sample_days = numero de esos dias. Periodos: "lectiu" (abr-jun, sep-oct) y
  "all" (todo el rango de datos).
"""
from __future__ import annotations

import argparse
import math
import shutil
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
CLEAN = BASE / "data/interim/clean"
RAW = BASE / "data/raw/saf-espais-2026-equips.xlsx"
ALIAS = BASE / "data/interim/mapping/resource_alias.csv"
DB_OUT = BASE / "database/mysaf.db"
APP_ASSET_OUT = BASE.parent / "app/src/main/assets/database/mysaf.db"
CSV_OUT = BASE / "data/processed/hourly_availability.csv"

# Debe coincidir con @Database(version = ...) en MySafDatabase.kt.
DB_VERSION = 1
SLOT = 15
SLOTS_PER_HOUR = 60 // SLOT
CLOSED_DAY_MAX_ROWS = 30
WEEKDAY_CODES = ["dl", "dt", "dc", "dj", "dv", "ds", "dg"]
PERIODS = ("lectiu", "all")
SCOPE = "all"


@dataclass(frozen=True)
class Activity:
    id: str
    is_person_count: bool
    resources: tuple[str, ...]
    # Solo personas: recursos cuyo aforo de inventario se suma. Por defecto,
    # los mismos `resources` (no sirve cuando dos recursos son el mismo espacio).
    capacity_resources: tuple[str, ...] = field(default=())


# Orden = orden de la pantalla de inicio. ids = ActivityCatalog.kt.
ACTIVITIES: tuple[Activity, ...] = (
    # PISCINA_25M_COBERTA ya incluye sus 8 carriles (includes_children).
    Activity("piscina_25m", True, ("PISCINA_25M_COBERTA",)),
    # PISCINA_16M_COMPLETA ya incluye sus dos mitades (MEITAT A/B).
    Activity("piscina_16m", True, ("PISCINA_16M_COMPLETA",)),
    Activity("sala_fitness", True, ("SALA_FITNES",)),
    Activity("sala_boxtraining", True, ("SALA_6_BOXTRAINING",)),
    # Salas de actividades dirigidas: las reservas son inscripciones a clases.
    Activity("sala_1_ritmes", True, ("AADD_SALA_1_RITMES",)),
    Activity("sala_2_ritmes", True, ("AADD_SALA_2_RITMES",)),
    Activity("sala_3_zen", True, ("AADD_SALA_3_ZEN",)),
    Activity("sala_4_cycling", True, ("SALA_4_CYCLING",)),
    Activity("padel", False, tuple(f"PADEL_PISTA_{i}" for i in range(1, 5))),
    Activity("tennis", False, tuple(f"TENIS_PISTA_{i}" for i in range(1, 6))),
    Activity("esquaix", False, tuple(f"ESQUAIX_PISTA_{i}" for i in range(2, 5))),
    # Padres: units_busy_avg ya cuenta mitades y subdivisiones.
    Activity("pavello", False, ("PAVELLO_PISTA_2", "PAVELLO_PISTA_3", "PAVELLO_BADMINTON_1")),
    Activity("futbol_sala", False, ("FUTBOL_SALA_1",)),
    Activity("futbol_7_11", False, tuple(f"FUTBOL7_CAMP_{i}" for i in range(1, 5))),
    Activity("basquet_exterior", False, ("BASQUET_EXTERIOR",)),
    Activity("volei_platja", False, ("VOLEI_PLATJA",)),
    # Uso libre + actividades dirigidas comparten el mismo espacio (aforo 25).
    Activity("barbell", True, ("ESPAI_BARBELL", "AADD_ESPAI_BARBELL"),
             capacity_resources=("ESPAI_BARBELL",)),
    Activity("callistenia", True, ("CALISTENIA",)),
    Activity("rocodrom", True, ("ROCODROM_INTERIOR", "ROCODROM_EXTERIOR")),
)

# DDL identico al que genera Room para las entidades (Room compara nombre,
# afinidad, NOT NULL y posicion en la clave primaria).
SCHEMA = {
    "activity": (
        "CREATE TABLE IF NOT EXISTS `activity` ("
        "`id` TEXT NOT NULL, "
        "`sort_order` INTEGER NOT NULL, "
        "`is_person_count` INTEGER NOT NULL, "
        "`capacity` INTEGER NOT NULL, "
        "`resource_ids` TEXT NOT NULL, "
        "PRIMARY KEY(`id`))"
    ),
    "hourly_availability": (
        "CREATE TABLE IF NOT EXISTS `hourly_availability` ("
        "`activity_id` TEXT NOT NULL, "
        "`period` TEXT NOT NULL, "
        "`weekday` TEXT NOT NULL, "
        "`hour` INTEGER NOT NULL, "
        "`avg_occupied` REAL NOT NULL, "
        "`peak_occupied` REAL NOT NULL, "
        "`capacity` INTEGER NOT NULL, "
        "`sample_days` INTEGER NOT NULL, "
        "`long_block_share` REAL NOT NULL, "
        "`is_closed` INTEGER NOT NULL, "
        "PRIMARY KEY(`activity_id`, `period`, `weekday`, `hour`))"
    ),
    "opening_hours": (
        "CREATE TABLE IF NOT EXISTS `opening_hours` ("
        "`weekday` TEXT NOT NULL, "
        "`open_min` INTEGER NOT NULL, "
        "`close_min` INTEGER NOT NULL, "
        "PRIMARY KEY(`weekday`))"
    ),
    "dataset_info": (
        "CREATE TABLE IF NOT EXISTS `dataset_info` ("
        "`key` TEXT NOT NULL, "
        "`value` TEXT NOT NULL, "
        "PRIMARY KEY(`key`))"
    ),
}

HOURLY_COLUMNS = ["activity_id", "period", "weekday", "hour", "avg_occupied",
                  "peak_occupied", "capacity", "sample_days", "long_block_share",
                  "is_closed"]


# ------------------------------------------------------------------
# reglas puras (testeadas en tests/test_create_database.py)
# ------------------------------------------------------------------

def period_matches(period: str, date: pd.Timestamp) -> bool:
    """Misma regla PERIOD v1 que clean_data.py."""
    if period == "all":
        return True
    if period == "lectiu":
        return date.month in (4, 5, 6, 9, 10)
    raise ValueError(f"periodo desconocido: {period}")


def is_hour_closed(hour: int, open_min: int, close_min: int) -> bool:
    """Una hora esta cerrada si no se solapa con [open_min, close_min)."""
    return hour * 60 >= close_min or (hour + 1) * 60 <= open_min


def display_hours(opening: dict[str, tuple[int, int]]) -> range:
    """Horas que muestra la app: de la primera apertura al ultimo cierre."""
    first = min(o for o, _ in opening.values()) // 60
    last = math.ceil(max(c for _, c in opening.values()) / 60)
    return range(first, last)


def active_dates(reservations: pd.DataFrame, max_rows: int = CLOSED_DAY_MAX_ROWS) -> pd.DatetimeIndex:
    """Dias con actividad real del centro: >= max_rows reservas en total."""
    per_day = reservations.groupby("date_use").size()
    return pd.DatetimeIndex(sorted(per_day[per_day >= max_rows].index))


def capacity_for(activity: Activity, capacity_people: dict[str, float]) -> int:
    if not activity.is_person_count:
        return len(activity.resources)
    total = 0.0
    for rid in activity.capacity_resources or activity.resources:
        cap = capacity_people.get(rid)
        if cap is None or pd.isna(cap) or cap <= 0:
            raise SystemExit(f"ERROR: {activity.id}: {rid} sin aforo de inventario")
        total += float(cap)
    return int(round(total))


def parse_opening_hours(df: pd.DataFrame) -> dict[str, tuple[int, int]]:
    """Horari general -> {"dl": (open_min, close_min), ...}."""
    import re
    import unicodedata

    def norm(s):
        s = unicodedata.normalize("NFKD", str(s).upper().strip())
        return "".join(c for c in s if not unicodedata.combining(c))

    days = {"DILLUNS A DIVENDRES": WEEKDAY_CODES[:5], "DISSABTE": ["ds"], "DIUMENGE": ["dg"]}
    out: dict[str, tuple[int, int]] = {}
    for r in df.itertuples(index=False):
        m = re.match(r"\s*(\d{1,2})[.:](\d{2})\s*a\s*(\d{1,2})[.:](\d{2})", str(r.Horari))
        if not m or norm(r.Dies) not in days:
            raise SystemExit(f"ERROR: horario no reconocido: {r.Dies!r} {r.Horari!r}")
        o = int(m.group(1)) * 60 + int(m.group(2))
        c = int(m.group(3)) * 60 + int(m.group(4))
        for wd in days[norm(r.Dies)]:
            out[wd] = (o, c)
    if sorted(out, key=WEEKDAY_CODES.index) != WEEKDAY_CODES:
        raise SystemExit(f"ERROR: horario general incompleto: {out}")
    return out


def hourly_per_date(agg: pd.DataFrame, activity: Activity, dates: pd.DatetimeIndex,
                    hours: range) -> pd.DataFrame:
    """Ocupacion por (fecha, hora) de una actividad, con ceros donde no hay filas.

    Devuelve columnas: date_use, hour, occupied, peak, booked_all, booked_standard.
    """
    value_col = "avg_concurrent" if activity.is_person_count else "units_busy_avg"
    sub = agg[agg["resource_id"].isin(activity.resources)]
    missing = set(activity.resources) - set(sub["resource_id"].unique())
    if missing:
        raise SystemExit(f"ERROR: {activity.id}: recursos sin datos {sorted(missing)}")
    sub = sub.assign(hour=sub["slot_start_min"] // 60)

    all_ = sub[sub["booking_scope"] == SCOPE]
    std = sub[sub["booking_scope"] == "standard"]
    keys = ["date_use", "hour"]

    # media de la hora = suma de las franjas / 4 (franja ausente = 0)
    per_res = (all_.groupby(["resource_id"] + keys)
               .agg(v=(value_col, "sum"), peak=("max_concurrent", "max"),
                    booked=("booked_minutes", "sum"))
               .reset_index())
    per_res["v"] = per_res["v"].fillna(0) / SLOTS_PER_HOUR
    if not activity.is_person_count:   # pico en pistas = fraccion maxima, no filas
        per_res["peak"] = per_res["v"]
    per_act = per_res.groupby(keys).agg(occupied=("v", "sum"), peak=("peak", "sum"),
                                        booked_all=("booked", "sum"))
    booked_std = std.groupby(keys)["booked_minutes"].sum().rename("booked_standard")

    grid = pd.MultiIndex.from_product([dates, list(hours)], names=keys)
    out = (per_act.join(booked_std, how="outer").reindex(grid).fillna(0.0).reset_index())
    return out


def build_hourly_rows(agg: pd.DataFrame, reservations: pd.DataFrame,
                      opening: dict[str, tuple[int, int]],
                      capacity_people: dict[str, float],
                      activities: tuple[Activity, ...] = ACTIVITIES) -> pd.DataFrame:
    dates = active_dates(reservations)
    hours = display_hours(opening)
    rows = []
    for act in activities:
        cap = capacity_for(act, capacity_people)
        per_date = hourly_per_date(agg, act, dates, hours)
        per_date["weekday"] = per_date["date_use"].dt.dayofweek.map(lambda i: WEEKDAY_CODES[i])
        for period in PERIODS:
            mask = per_date["date_use"].map(lambda d: period_matches(period, d))
            p = per_date[mask]
            for wd in WEEKDAY_CODES:
                o, c = opening[wd]
                w = p[p["weekday"] == wd]
                n_days = int(w["date_use"].nunique())
                by_hour = w.groupby("hour").agg(
                    occ=("occupied", "mean"), peak=("peak", "mean"),
                    ba=("booked_all", "sum"), bs=("booked_standard", "sum"))
                for h in hours:
                    closed = is_hour_closed(h, o, c)
                    if closed or h not in by_hour.index or n_days == 0:
                        occ = peak = share = 0.0
                    else:
                        r = by_hour.loc[h]
                        occ, peak = float(r["occ"]), float(r["peak"])
                        share = float((r["ba"] - r["bs"]) / r["ba"]) if r["ba"] > 0 else 0.0
                    rows.append(dict(
                        activity_id=act.id, period=period, weekday=wd, hour=h,
                        avg_occupied=round(occ, 4), peak_occupied=round(peak, 4),
                        capacity=cap, sample_days=0 if closed else n_days,
                        long_block_share=round(max(0.0, min(1.0, share)), 4),
                        is_closed=int(closed)))
    return pd.DataFrame(rows, columns=HOURLY_COLUMNS)


def build_activity_rows(capacity_people: dict[str, float],
                        activities: tuple[Activity, ...] = ACTIVITIES) -> pd.DataFrame:
    return pd.DataFrame([
        dict(id=a.id, sort_order=i, is_person_count=int(a.is_person_count),
             capacity=capacity_for(a, capacity_people), resource_ids=",".join(a.resources))
        for i, a in enumerate(activities)
    ])


def write_sqlite(path: Path, activity: pd.DataFrame, hourly: pd.DataFrame,
                 opening: dict[str, tuple[int, int]], info: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    try:
        for ddl in SCHEMA.values():
            con.execute(ddl)
        con.executemany(
            "INSERT INTO activity VALUES (?,?,?,?,?)",
            activity[["id", "sort_order", "is_person_count", "capacity", "resource_ids"]]
            .itertuples(index=False, name=None))
        con.executemany(
            f"INSERT INTO hourly_availability ({','.join(HOURLY_COLUMNS)}) "
            f"VALUES ({','.join('?' * len(HOURLY_COLUMNS))})",
            hourly[HOURLY_COLUMNS].itertuples(index=False, name=None))
        con.executemany("INSERT INTO opening_hours VALUES (?,?,?)",
                        [(wd, o, c) for wd, (o, c) in opening.items()])
        con.executemany("INSERT INTO dataset_info VALUES (?,?)", sorted(info.items()))
        con.execute(f"PRAGMA user_version = {DB_VERSION}")
        con.commit()
        con.execute("VACUUM")
    finally:
        con.close()


def load_inputs():
    for p in (CLEAN / "reservation_slot_agg.parquet", CLEAN / "reservations_clean.parquet", ALIAS):
        if not p.exists():
            raise SystemExit(f"ERROR: falta {p}; ejecuta antes clean_data.py")
    agg = pd.read_parquet(CLEAN / "reservation_slot_agg.parquet", columns=[
        "resource_id", "booking_scope", "date_use", "slot_start_min", "avg_concurrent",
        "max_concurrent", "units_busy_avg", "booked_minutes", "rule_version"])
    res = pd.read_parquet(CLEAN / "reservations_clean.parquet", columns=["date_use"])
    alias = pd.read_csv(ALIAS, sep=";")
    cap = (alias[alias["resource_id"].notna()].drop_duplicates("resource_id")
           .set_index("resource_id")["capacity_people"].to_dict())
    opening = parse_opening_hours(pd.read_excel(RAW, sheet_name="Horari general"))
    return agg, res, cap, opening


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--out", type=Path, default=DB_OUT)
    ap.add_argument("--no-app-copy", action="store_true",
                    help="no copiar la base de datos a app/src/main/assets")
    args = ap.parse_args(argv)

    print("=" * 70)
    print("PASO 4 — create_database (SQLite para Room)")
    print("=" * 70)
    agg, res, cap, opening = load_inputs()
    dates = active_dates(res)
    activity = build_activity_rows(cap)
    hourly = build_hourly_rows(agg, res, opening, cap)
    info = {
        "source_file": RAW.name,
        "date_min": str(res["date_use"].min().date()),
        "date_max": str(res["date_use"].max().date()),
        "active_days": str(len(dates)),
        "closed_day_max_rows": str(CLOSED_DAY_MAX_ROWS),
        "booking_scope": SCOPE,
        "clean_rule_version": str(agg["rule_version"].iloc[0]),
        "db_version": str(DB_VERSION),
    }
    write_sqlite(args.out, activity, hourly, opening, info)
    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    hourly.to_csv(CSV_OUT, sep=";", index=False, encoding="utf-8-sig")
    print(f"activity: {len(activity)} filas | hourly_availability: {len(hourly)} filas")
    print(f"dias activos: {len(dates)} de {res['date_use'].nunique()} con reservas")
    print(f"Salida: {args.out}")
    if not args.no_app_copy:
        APP_ASSET_OUT.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.out, APP_ASSET_OUT)
        print(f"Copia para la app: {APP_ASSET_OUT}")

    # resumen rapido
    view = hourly[(hourly.period == "lectiu") & (hourly.is_closed == 0)]
    view = view.assign(load=view.avg_occupied / view.capacity)
    print("\nOcupacion media (lectiu, horas abiertas) por actividad:")
    print(view.groupby("activity_id")["load"].mean().round(3)
          .reindex([a.id for a in ACTIVITIES]).to_string())


if __name__ == "__main__":
    main()
