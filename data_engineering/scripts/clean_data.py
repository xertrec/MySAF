"""
03_clean_data.py

Paso 3 del pipeline mySAF.

Entradas:
- data/raw/saf-espais-2026-equips.xlsx     (Reserves, Activitats dirigides)
- data/interim/mapping/resource_alias.csv   (paso 2 + enrich_inventory)

Salidas:
- data/interim/clean/reservations_clean.parquet
- data/interim/clean/reservation_slot.parquet
- data/interim/clean/reservation_slot_agg.parquet
- data/interim/clean/directed_activity_class.parquet
- data/interim/clean/clean_report.txt

Reglas:
- No se borran filas del raw. Se añaden flags.
- Personas: cada fila = 1 persona en la franja.
- Recurso: cada fila = 1 unidad ocupada, capada al padre.
- Reservas > 4h: is_long_block=True, siguen ocupando.
- Calendar mismatch: se marca, no se borra. Manda DataUs.
- Directed activities: DataInscripcio != fecha de sesión.
"""
import re
import unicodedata
from pathlib import Path
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data/raw/saf-espais-2026-equips.xlsx"
ALIAS = BASE / "data/interim/mapping/resource_alias.csv"
OUT = BASE / "data/interim/clean"
OUT.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------

def norm(s):
    s = str(s).upper().strip()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("DSS-DG", "DS-DG")
    return s


def cal(text):
    """Detecta dl-dv / ds-dg sobre texto normalizado."""
    if "DS-DG" in text:
        return "ds-dg"
    if "DL-DV" in text:
        return "dl-dv"
    return None


WEEKDAY_MAP = {
    "Monday": "dl", "Tuesday": "dt", "Wednesday": "dc",
    "Thursday": "dj", "Friday": "dv", "Saturday": "ds",
    "Sunday": "dg",
}


def weekday_code_from_date(d):
    if pd.isna(d):
        return None
    return WEEKDAY_MAP.get(pd.Timestamp(d).day_name())


def period_from_date(d):
    if pd.isna(d):
        return None
    m = pd.Timestamp(d).month
    if m in (4, 5, 6, 9, 10):
        return "lectiu"
    if m in (7, 8):
        return "estiu"
    return "altres"


def to_minutes(t):
    if pd.isna(t):
        return None
    if hasattr(t, "hour"):
        return int(t.hour) * 60 + int(t.minute)
    s = str(t).strip()
    m = re.match(r"^(\d{1,2}):(\d{2})", s)
    if not m:
        return None
    return int(m.group(1)) * 60 + int(m.group(2))


def expand_hours(start_min, end_min):
    """
    Franjas horarias (0-23) que ocupa la reserva.
    10:30-12:30 -> [10, 11, 12]
    10:00-11:00 -> [10]
    10:00-10:30 -> [10]
    """
    if start_min is None or end_min is None or end_min <= start_min:
        return []
    h_start = start_min // 60
    h_end = (end_min - 1) // 60
    return list(range(h_start, h_end + 1))


def norm_activity_name(s):
    s = str(s).upper().strip()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\s+", " ", s)
    s = s.replace("(LES MILLS)", "LES MILLS")
    s = s.replace("LESMILLS", "LES MILLS")
    return s


# ------------------------------------------------------------------
# 1. cargar alias
# ------------------------------------------------------------------

print("=" * 70)
print("PASO 3 — clean_data")
print("=" * 70)

alias = pd.read_csv(ALIAS, sep=";")
alias["espai_pare_key"] = alias["espai_pare"].map(norm)
alias["recurs_key"] = alias["recurs"].map(norm)

alias_key = alias[[
    "espai_pare_key", "recurs_key", "resource_id", "resource_name",
    "resource_kind", "metric_type", "capacity_units",
    "parent_resource_id", "fraction_of_parent", "mapping_status",
]].copy()

dup = alias_key.duplicated(subset=["espai_pare_key", "recurs_key"]).sum()
if dup:
    print(f"WARN: {dup} duplicados en alias. Me quedo con el primero.")
    alias_key = alias_key.drop_duplicates(subset=["espai_pare_key", "recurs_key"])

# Lookup rápido para enriquecer agg al final
metric_lookup = (
    alias.drop_duplicates("resource_id")
    .set_index("resource_id")[["metric_type", "capacity_units"]]
)

# ------------------------------------------------------------------
# 2. cargar Reserves y cruzar
# ------------------------------------------------------------------

print("\nCargando Reserves...")
res = pd.read_excel(RAW, sheet_name="Reserves")
print(f"  Reserves raw: {len(res)}")

res["espai_pare_key"] = res["EspaiPare"].map(norm)
res["recurs_key"] = res["Recurs"].map(norm)

res = res.merge(
    alias_key,
    on=["espai_pare_key", "recurs_key"],
    how="left",
    validate="many_to_one",
)

missing = res["resource_id"].isna() | (res["resource_id"] == "")
print(f"  Reservas sin resource_id: {missing.sum()} ({missing.mean():.2%})")
res["has_resource"] = ~missing

# ------------------------------------------------------------------
# 3. flags
# ------------------------------------------------------------------

res["weekday_actual"] = res["DataUs"].map(weekday_code_from_date)
res["calendar_label"] = (res["espai_pare_key"] + " " + res["recurs_key"]).map(cal)

res["calendar_mismatch"] = (
        res["weekday_actual"].notna()
        & res["calendar_label"].notna()
        & ~(
        (res["calendar_label"] == "dl-dv")
        & res["weekday_actual"].isin(["dl", "dt", "dc", "dj", "dv"])
)
        & ~(
        (res["calendar_label"] == "ds-dg")
        & res["weekday_actual"].isin(["ds", "dg"])
)
)
print(f"  calendar_mismatch: {res['calendar_mismatch'].sum()}")

res["is_long_block"] = res["DuradaMin"] > 240
print(f"  is_long_block: {res['is_long_block'].sum()}")

res["period_id"] = res["DataUs"].map(period_from_date)
res["start_min"] = res["HoraInici"].map(to_minutes)
res["end_min"] = res["HoraFi"].map(to_minutes)

res = res[res["start_min"].notna() & res["end_min"].notna()].copy()

# ------------------------------------------------------------------
# 4. expandir a franjas horarias
# ------------------------------------------------------------------

print("\nExpandiendo reservas a franjas...")
slot_rows = []
for row in res.itertuples(index=False):
    hours = expand_hours(row.start_min, row.end_min)
    if not hours:
        continue
    rid = row.resource_id if pd.notna(row.resource_id) else ""
    metric = row.metric_type if pd.notna(row.metric_type) else "pendiente"
    cap = row.capacity_units if pd.notna(row.capacity_units) else None
    parent = row.parent_resource_id if pd.notna(row.parent_resource_id) else None
    frac = row.fraction_of_parent if pd.notna(row.fraction_of_parent) else None
    for h in hours:
        slot_rows.append({
            "resource_id": rid,
            "metric_type": metric,
            "capacity_units": cap,
            "parent_resource_id": parent,
            "fraction_of_parent": frac,
            "date_use": row.DataUs,
            "weekday_actual": row.weekday_actual,
            "period_id": row.period_id,
            "hour": h,
            "start_min": row.start_min,
            "end_min": row.end_min,
            "duration_min": row.DuradaMin,
            "is_long_block": bool(row.is_long_block),
            "calendar_mismatch": bool(row.calendar_mismatch),
            "has_resource": bool(row.has_resource),
        })

slots = pd.DataFrame(slot_rows)
print(f"  reservation_slot (long): {len(slots)} filas")

slots["people_count"] = np.where(slots["metric_type"] == "personas", 1, 0)
slots["booking_count"] = np.where(slots["metric_type"] == "unidad_recurso", 1, 0)

# ------------------------------------------------------------------
# 5. resolver padre/mitad
# ------------------------------------------------------------------

print("\nResolviendo padre/mitad...")

# Solo slots con resource_id válido (excluye la anomalía TENNIS ds-dg)
slots_valid = slots[slots["resource_id"] != ""].copy()

# --- hijos ---
children_slots = slots_valid[slots_valid["parent_resource_id"].notna()].copy()

# unidades fraccionadas (solo para unidad_recurso, ya que personas no usan fracción)
children_slots["fraction_units"] = (
        children_slots["fraction_of_parent"].fillna(0)
        * children_slots["booking_count"]
)

children_agg = (
    children_slots.groupby(
        ["parent_resource_id", "date_use", "weekday_actual", "period_id", "hour"],
        dropna=False,
    ).agg(
        children_units=("fraction_units", "sum"),
        children_people=("people_count", "sum"),
    ).reset_index()
    .rename(columns={"parent_resource_id": "resource_id"})
)

# --- padres con reservas directas ---
parent_slots = slots_valid[slots_valid["parent_resource_id"].isna()].copy()

parent_agg = (
    parent_slots.groupby(
        ["resource_id", "date_use", "weekday_actual", "period_id", "hour"],
        dropna=False,
    ).agg(
        direct_booking=("booking_count", "sum"),
        direct_people=("people_count", "sum"),
        capacity_units=("capacity_units", "max"),
        metric_type=("metric_type", "first"),
    ).reset_index()
)

# --- combinar ---
agg = parent_agg.merge(
    children_agg,
    on=["resource_id", "date_use", "weekday_actual", "period_id", "hour"],
    how="outer",
)

for c in ["direct_booking", "direct_people", "children_units", "children_people"]:
    if c not in agg.columns:
        agg[c] = 0
    agg[c] = agg[c].fillna(0)

agg["capacity_units"] = agg["capacity_units"].fillna(1.0)

# enriquecer metric_type / capacity desde alias (padres que solo aparecen por hijos)
enriched = agg["resource_id"].map(
    lambda rid: metric_lookup.loc[rid] if rid in metric_lookup.index else None
)
agg["metric_type_alias"] = enriched.map(
    lambda x: x["metric_type"] if x is not None else None
)
agg["capacity_alias"] = enriched.map(
    lambda x: x["capacity_units"] if x is not None else None
)
agg["metric_type"] = agg["metric_type_alias"].fillna(agg["metric_type"])
agg["capacity_units"] = agg["capacity_alias"].fillna(agg["capacity_units"])
agg = agg.drop(columns=["metric_type_alias", "capacity_alias"])

# --- calcular occupied_units / people_occupied ---
agg["occupied_units"] = (
    (agg["direct_booking"] + agg["children_units"])
    .clip(upper=agg["capacity_units"])
)
agg["people_occupied"] = agg["direct_people"] + agg["children_people"]

print(f"  reservation_slot_agg: {len(agg)} filas")
print(f"  resources con ocupacion: {agg['resource_id'].nunique()}")

# ------------------------------------------------------------------
# 6. activitats dirigides
# ------------------------------------------------------------------

print("\nCargando Activitats dirigides...")
dir_df = pd.read_excel(RAW, sheet_name="Activitats dirigides")
print(f"  Filas raw: {len(dir_df)}")

dir_df["activity_norm"] = dir_df["Activitat"].map(norm_activity_name)
dir_df["start_min"] = dir_df["HoraInici"].map(to_minutes)
dir_df["end_min"] = dir_df["HoraFi"].map(to_minutes)

dir_df["over_capacity_row"] = dir_df["Inscrits"] > dir_df["AforamentMax"]

keys = ["activity_norm", "Sala", "start_min", "end_min"]

grp = dir_df.groupby(keys, dropna=False).agg(
    code_first=("CodiActivitat", "first"),
    name_original=("Activitat", "first"),
    capacity_max=("AforamentMax", "max"),
    median_enrolled=("Inscrits", "median"),
    max_enrolled=("Inscrits", "max"),
    median_pct_occupancy=("PctOcupacio", "median"),
    n_records=("Inscrits", "size"),
    n_distinct_enrolled=("Inscrits", "nunique"),
    over_capacity_rows=("over_capacity_row", "sum"),
).reset_index()

grp["room"] = grp["Sala"]
grp["over_capacity_flag"] = (grp["over_capacity_rows"] > 0).astype(int)
grp["session_date_known"] = False
grp["period_id"] = "tot"

print(f"  Clases dirigidas (grupos): {len(grp)}")
print(f"  Clases con over_capacity: {int(grp['over_capacity_flag'].sum())}")

# ------------------------------------------------------------------
# 7. sanear y guardar
# ------------------------------------------------------------------

print("\nGuardando parquet...")

res["resource_id"] = res["resource_id"].fillna("")
slots["resource_id"] = slots["resource_id"].fillna("")
agg["resource_id"] = agg["resource_id"].fillna("")

res.to_parquet(OUT / "reservations_clean.parquet", index=False)
slots.to_parquet(OUT / "reservation_slot.parquet", index=False)
agg.to_parquet(OUT / "reservation_slot_agg.parquet", index=False)
grp.to_parquet(OUT / "directed_activity_class.parquet", index=False)

# ------------------------------------------------------------------
# 8. reporte
# ------------------------------------------------------------------

report = []
report.append("=" * 70)
report.append("PASO 3 — clean_data — reporte")
report.append("=" * 70)
report.append(f"Reserves raw: {len(res)}")
report.append(f"Reserves con resource_id: {int(res['has_resource'].sum())}")
report.append(f"Reserves sin resource_id: {int((~res['has_resource']).sum())}")
report.append(f"calendar_mismatch: {int(res['calendar_mismatch'].sum())}")
report.append(f"is_long_block: {int(res['is_long_block'].sum())}")
report.append(f"reservation_slot (long): {len(slots)}")
report.append(f"reservation_slot_agg: {len(agg)}")
report.append(f"resources con ocupacion: {agg['resource_id'].nunique()}")
report.append("")
report.append(f"Activitats dirigides raw: {len(dir_df)}")
report.append(f"Clases dirigidas (grupos): {len(grp)}")
report.append(f"Clases con over_capacity: {int(grp['over_capacity_flag'].sum())}")
report.append(f"session_date_known: {grp['session_date_known'].mean():.0%} False")
report.append("")
report.append(f"Slots con people_occupied > 0: {int((agg['people_occupied'] > 0).sum())}")
report.append(f"Slots con occupied_units > 0: {int((agg['occupied_units'] > 0).sum())}")
report.append("")
report.append("Distribucion de slots por metric_type:")
report.append(slots["metric_type"].value_counts().to_string())
report.append("")
report.append("Distribucion de period_id (reservas):")
report.append(res["period_id"].value_counts().to_string())
report.append("")
report.append("Top 10 recursos por people_occupied (personas):")
report.append(
    agg[agg["metric_type"] == "personas"]
    .groupby("resource_id")["people_occupied"].sum()
    .sort_values(ascending=False).head(10).to_string()
)
report.append("")
report.append("Top 10 recursos por occupied_units (unidad_recurso):")
report.append(
    agg[agg["metric_type"] == "unidad_recurso"]
    .groupby("resource_id")["occupied_units"].sum()
    .sort_values(ascending=False).head(10).to_string()
)

report_text = "\n".join(str(x) for x in report)
(OUT / "clean_report.txt").write_text(report_text, encoding="utf-8")
print("\n" + report_text)
print(f"\nSalida: {OUT}")