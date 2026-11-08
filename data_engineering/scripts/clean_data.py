"""
03_clean_data.py

Paso 3 del pipeline mySAF.

Entradas:
- data/raw/saf-espais-2026-equips.xlsx     (Reserves, Horari general, Activitats dirigides)
- data/interim/mapping/resource_alias.csv   (build_resource_alias.py + enrich_inventory.py)

Salidas:
- data/interim/clean/reservations_clean.parquet   1 fila por fila de Reserves (194.567), con flags
- data/interim/clean/reservation_slot.parquet     fila x franja de 15 min que toca, con minutos solapados
- data/interim/clean/reservation_slot_agg.parquet ocupacion por recurso, dia, franja de 15 min y alcance
- data/interim/clean/directed_activity_class.parquet
- data/interim/clean/clean_report.txt

Reglas:
- No se borran filas del raw. Se anaden flags. Las filas identicas se conservan.
- Intervalos semiabiertos [inicio, fin): una reserva que acaba a las 11:00 no
  ocupa las 11:00. NUNCA se expande una reserva a horas completas.
- Ocupacion por minuto y franjas de 15 min:
    * personas (metric_type = personas): concurrencia = filas activas en ese
      minuto. avg_concurrent = media de la franja, max_concurrent = maximo.
    * unidades (metric_type = unidad_recurso): una pista esta ocupada en un
      minuto si tiene >= 1 reserva propia (o de su padre). El padre esta ocupado
      en la fraccion de hijos ocupados (union, no suma). Las reservas
      solapadas de la misma unidad NO se recortan en silencio: se cuentan en
      conflict_minutes.
- Reservas > 240 min (is_long_block) y 21:00-23:59 (night_block_candidate):
  se marcan y se calculan dos alcances: booking_scope = "all" y "standard"
  (sin esos bloques).
- Aforo: solo capacity_people de enrich_inventory (fuente Espais). Sin aforo
  valido -> rel_occupancy = NULL. No se recorta a 100 %.
- Calendar mismatch: se marca, no se borra. Manda DataUs.
- Activitats dirigides: DataInscripcio != fecha de sesion; no hay ocupacion
  por sesion. Solo agregados por serie (codigo + sala + hora).
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

SLOT = 15                      # minutos por franja
LONG_BLOCK_MIN = 240           # regla LONG_BLOCK v1 (provisional)
NIGHT_START, NIGHT_END = 21 * 60, 23 * 60 + 59   # regla NIGHT_BLOCK v1 (provisional)


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
    """Etiqueta de calendario declarada en el nombre (dl-dv / ds-dg)."""
    if "DS-DG" in text:
        return "ds-dg"
    if "DL-DV" in text:
        return "dl-dv"
    return None


WEEKDAY_CODES = ["dl", "dt", "dc", "dj", "dv", "ds", "dg"]


def period_from_date(d):
    # Regla PERIOD v1 (provisional, sin fuente del SAF): jul-ago = estiu.
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
    m = re.match(r"^(\d{1,2}):(\d{2})", str(t).strip())
    if not m:
        return None
    return int(m.group(1)) * 60 + int(m.group(2))


def norm_activity_name(s):
    s = str(s).upper().strip()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\s+", " ", s)
    s = s.replace("(LES MILLS)", "LES MILLS").replace("LESMILLS", "LES MILLS")
    return s


def parse_opening_hours(df):
    """Horari general -> {weekday 0-6: (open_min, close_min)}."""
    days = {"DILLUNS A DIVENDRES": range(0, 5), "DISSABTE": [5], "DIUMENGE": [6]}
    out = {}
    for r in df.itertuples(index=False):
        m = re.match(r"\s*(\d{1,2})[.:](\d{2})\s*a\s*(\d{1,2})[.:](\d{2})", str(r.Horari))
        if not m:
            raise SystemExit(f"ERROR: horario no reconocido: {r.Horari!r}")
        o = int(m.group(1)) * 60 + int(m.group(2))
        c = int(m.group(3)) * 60 + int(m.group(4))
        key = norm(r.Dies)
        if key not in days:
            raise SystemExit(f"ERROR: dias no reconocidos: {r.Dies!r}")
        for wd in days[key]:
            out[wd] = (o, c)
    if sorted(out) != list(range(7)):
        raise SystemExit(f"ERROR: horario general incompleto: {out}")
    return out


print("=" * 70)
print("PASO 3 — clean_data (ocupacion por intervalos)")
print("=" * 70)

# ------------------------------------------------------------------
# 1. alias
# ------------------------------------------------------------------

alias = pd.read_csv(ALIAS, sep=";")
for col in ("capacity_people", "capacity_people_source"):
    if col not in alias.columns:
        raise SystemExit(f"ERROR: falta {col} en resource_alias.csv; "
                         "ejecuta antes enrich_inventory.py")
alias["espai_pare_key"] = alias["espai_pare"].map(norm)
alias["recurs_key"] = alias["recurs"].map(norm)

dup = alias.duplicated(subset=["espai_pare_key", "recurs_key"]).sum()
if dup:
    raise SystemExit(f"ERROR: {dup} claves duplicadas en resource_alias.csv")

alias_key = alias[[
    "espai_pare_key", "recurs_key", "resource_id", "resource_kind",
    "metric_type", "parent_resource_id", "fraction_of_parent", "mapping_status",
]]

res_info = (
    alias[alias["resource_id"].notna()]
    .drop_duplicates("resource_id")
    .set_index("resource_id")[[
        "metric_type", "parent_resource_id", "fraction_of_parent",
        "capacity_people", "capacity_people_source"]]
)
# Cada resource_id debe tener atributos coherentes en todas sus filas de alias.
incoh = (alias[alias["resource_id"].notna()]
         .groupby("resource_id")[["metric_type", "parent_resource_id"]]
         .nunique(dropna=False).max(axis=1))
if (incoh > 1).any():
    raise SystemExit(f"ERROR: resource_id incoherentes: {list(incoh[incoh > 1].index)}")

# ------------------------------------------------------------------
# 2. Reserves + flags
# ------------------------------------------------------------------

raw = pd.read_excel(RAW, sheet_name="Reserves")
n_raw = len(raw)
raw["source_row"] = raw.index + 2               # fila de Excel
res = raw.copy()
res["espai_pare_key"] = res["EspaiPare"].map(norm)
res["recurs_key"] = res["Recurs"].map(norm)
res = res.merge(alias_key, on=["espai_pare_key", "recurs_key"],
                how="left", validate="many_to_one")
assert len(res) == n_raw, "el cruce con el alias ha cambiado el numero de filas"

res["has_resource"] = res["resource_id"].notna()
res["date_use"] = pd.to_datetime(res["DataUs"]).dt.normalize()
res["weekday_idx"] = res["date_use"].dt.dayofweek
res["weekday_actual"] = res["weekday_idx"].map(lambda i: WEEKDAY_CODES[i])
res["weekday_raw_mismatch"] = res["weekday_actual"] != res["DiaSetmana"]
res["calendar_declared"] = res["espai_pare_key"].map(cal)
res["calendar_mismatch"] = (
    res["calendar_declared"].notna()
    & (res["calendar_declared"] != np.where(res["weekday_idx"] < 5, "dl-dv", "ds-dg"))
)
res["period_id"] = res["date_use"].map(period_from_date)
res["start_min"] = res["HoraInici"].map(to_minutes)
res["end_min"] = res["HoraFi"].map(to_minutes)
bad_time = res["start_min"].isna() | res["end_min"].isna() | (res["end_min"] <= res["start_min"])
res["invalid_interval"] = bad_time
res["duration_mismatch"] = (~bad_time) & ((res["end_min"] - res["start_min"]) != res["DuradaMin"])

hours = parse_opening_hours(pd.read_excel(RAW, sheet_name="Horari general"))
open_min = res["weekday_idx"].map(lambda w: hours[w][0])
close_min = res["weekday_idx"].map(lambda w: hours[w][1])
res["outside_general_hours"] = (res["start_min"] < open_min) | (res["end_min"] > close_min)
res["is_long_block"] = res["DuradaMin"] > LONG_BLOCK_MIN
res["night_block_candidate"] = (res["start_min"] >= NIGHT_START) & (res["end_min"] >= NIGHT_END)
res["booking_class"] = np.select(
    [res["is_long_block"], res["night_block_candidate"]],
    ["long_block", "night_block_candidate"], "standard")

dup_cols = ["EspaiPare", "Recurs", "DataUs", "DiaSetmana", "HoraInici",
            "HoraFi", "DuradaMin", "DuradaHores"]
res["dup_group_size"] = res.groupby(dup_cols)["source_row"].transform("size")

for c in ("invalid_interval", "weekday_raw_mismatch", "duration_mismatch"):
    print(f"  {c}: {int(res[c].sum())}")
print(f"  sin resource_id: {int((~res['has_resource']).sum())}")
print(f"  calendar_mismatch: {int(res['calendar_mismatch'].sum())}")
print(f"  is_long_block: {int(res['is_long_block'].sum())}")
print(f"  night_block_candidate: {int(res['night_block_candidate'].sum())}")
print(f"  outside_general_hours: {int(res['outside_general_hours'].sum())}")

# ------------------------------------------------------------------
# 3. matriz de minutos por recurso y dia
# ------------------------------------------------------------------

valid = res[res["has_resource"] & ~res["invalid_interval"]].copy()
valid["start_min"] = valid["start_min"].astype(int)
valid["end_min"] = valid["end_min"].astype(int)

dates = pd.date_range(res["date_use"].min(), res["date_use"].max(), freq="D")
date_idx = {d: i for i, d in enumerate(dates)}
ND, NM = len(dates), 1440
NS = NM // SLOT
valid["d_idx"] = valid["date_use"].map(date_idx)


def minute_counts(df):
    """(ND, 1440) filas activas por minuto, intervalos [inicio, fin)."""
    diff = np.zeros((ND, NM + 1), dtype=np.int32)
    np.add.at(diff, (df["d_idx"].to_numpy(), df["start_min"].to_numpy()), 1)
    np.add.at(diff, (df["d_idx"].to_numpy(), df["end_min"].to_numpy()), -1)
    return np.cumsum(diff, axis=1)[:, :NM]


open_mask = np.zeros((ND, NM), dtype=bool)
for i, d in enumerate(dates):
    o, c = hours[d.dayofweek]
    open_mask[i, o:c] = True

resources = sorted(valid["resource_id"].unique())
children_of = {}
for rid, info in res_info.iterrows():
    p = info["parent_resource_id"]
    if pd.notna(p):
        children_of.setdefault(p, []).append(rid)

scopes = {"all": valid, "standard": valid[valid["booking_class"] == "standard"]}
agg_parts = []
conflict_rows = 0
for scope, vdf in scopes.items():
    own = {rid: minute_counts(g) for rid, g in vdf.groupby("resource_id")}
    starts = {rid: np.bincount(g["d_idx"] * NS + g["start_min"] // SLOT,
                               minlength=ND * NS).reshape(ND, NS)
              for rid, g in vdf.groupby("resource_id")}
    zero = np.zeros((ND, NM), dtype=np.int32)
    every = sorted(set(resources) | set(children_of))
    for rid in every:
        if rid not in res_info.index:
            continue
        info = res_info.loc[rid]
        mt = info["metric_type"]
        cnt = own.get(rid, zero)
        kids = [k for k in children_of.get(rid, []) if k in res_info.index]
        parent = info["parent_resource_id"]

        if mt == "unidad_recurso":
            busy = (cnt > 0).astype(np.float32)
            if kids:   # padre: union con la fraccion de hijos ocupados
                frac = np.zeros((ND, NM), dtype=np.float32)
                for k in kids:
                    f = res_info.loc[k, "fraction_of_parent"]
                    frac += float(f) * (own.get(k, zero) > 0)
                busy = np.maximum(busy, np.minimum(frac, 1.0))
            if pd.notna(parent):   # hijo: ocupado si el padre lo esta
                busy = np.maximum(busy, (own.get(parent, zero) > 0).astype(np.float32))
            conc = cnt
            conflict = (cnt > 1)
        else:      # personas o pendiente: personas (o filas) concurrentes
            conc = cnt.copy()
            for k in kids:        # personas del padre = propias + hijos
                conc = conc + own.get(k, zero)
            busy = None
            conflict = None

        active_days = np.flatnonzero((conc > 0).any(axis=1) | (cnt > 0).any(axis=1))
        if len(active_days) == 0:
            continue
        d0, d1 = active_days.min(), active_days.max()   # vigencia observada
        cs = conc.reshape(ND, NS, SLOT)
        keep = open_mask.reshape(ND, NS, SLOT).any(axis=2) | (cs > 0).any(axis=2)
        keep[:d0] = False
        keep[d1 + 1:] = False
        di, si = np.nonzero(keep)
        part = pd.DataFrame({
            "resource_id": rid,
            "metric_type": mt,
            "booking_scope": scope,
            "d_idx": di,
            "slot_start_min": si * SLOT,
            "in_general_hours": open_mask.reshape(ND, NS, SLOT).any(axis=2)[di, si],
            "starts_count": starts.get(rid, np.zeros((ND, NS), int))[di, si],
            "booked_minutes": cnt.reshape(ND, NS, SLOT).sum(axis=2)[di, si],
            "avg_concurrent": cs.mean(axis=2)[di, si],
            "max_concurrent": cs.max(axis=2)[di, si],
            "includes_children": bool(kids) and mt != "unidad_recurso",
        })
        if busy is not None:
            part["units_busy_avg"] = busy.reshape(ND, NS, SLOT).mean(axis=2)[di, si]
            part["conflict_minutes"] = conflict.reshape(ND, NS, SLOT).sum(axis=2)[di, si]
            if scope == "all":
                conflict_rows += int(conflict.sum())
        agg_parts.append(part)

agg = pd.concat(agg_parts, ignore_index=True)
agg["date_use"] = dates[agg["d_idx"].to_numpy()]
agg = agg.drop(columns="d_idx")
agg["weekday_actual"] = agg["date_use"].dt.dayofweek.map(lambda i: WEEKDAY_CODES[i])
agg["period_id"] = agg["date_use"].map(period_from_date)
agg["hour"] = agg["slot_start_min"] // 60

agg["capacity_ref"] = agg["resource_id"].map(res_info["capacity_people"])
agg["capacity_source"] = agg["resource_id"].map(res_info["capacity_people_source"])
ok_cap = agg["capacity_source"].isin(["inventory", "derived_sum"]) & agg["capacity_ref"].gt(0)
is_people = agg["metric_type"] == "personas"
agg["rel_occupancy"] = np.where(
    is_people & ok_cap, agg["avg_concurrent"] / agg["capacity_ref"],
    np.where(agg["metric_type"] == "unidad_recurso", agg["units_busy_avg"], np.nan))
agg["rel_occupancy_basis"] = np.where(
    is_people & ok_cap, "personas/aforo_inventario",
    np.where(agg["metric_type"] == "unidad_recurso", "unidad_ocupada", "sin_aforo_valido"))
agg["rule_version"] = f"SLOT{SLOT}_LONG{LONG_BLOCK_MIN}_NIGHT2100_v1"

# ------------------------------------------------------------------
# 4. tabla larga fila x franja (trazabilidad)
# ------------------------------------------------------------------

v = valid[["source_row", "resource_id", "date_use", "start_min", "end_min"]].copy()
v["first_slot"] = v["start_min"] // SLOT
v["n_slots"] = (v["end_min"] - 1) // SLOT - v["first_slot"] + 1
slots = v.loc[v.index.repeat(v["n_slots"])].copy()
slots["slot_start_min"] = (slots["first_slot"]
                           + slots.groupby(level=0).cumcount()) * SLOT
slots["overlap_min"] = (np.minimum(slots["end_min"], slots["slot_start_min"] + SLOT)
                        - np.maximum(slots["start_min"], slots["slot_start_min"]))
slots = slots.drop(columns=["first_slot", "n_slots"]).reset_index(drop=True)

# ------------------------------------------------------------------
# 5. validaciones (fallan con error)
# ------------------------------------------------------------------

assert len(res) == n_raw
assert (slots["overlap_min"] > 0).all()
own_all = agg[(agg["booking_scope"] == "all")]
exp_minutes = int((valid["end_min"] - valid["start_min"]).sum())
got_minutes = int(own_all["booked_minutes"].sum())
assert got_minutes == exp_minutes, f"minutos: {got_minutes} != {exp_minutes}"
assert int(slots["overlap_min"].sum()) == exp_minutes
assert int(own_all["starts_count"].sum()) == len(valid)
u = agg[agg["metric_type"] == "unidad_recurso"]
assert u["units_busy_avg"].between(0, 1).all()

# ------------------------------------------------------------------
# 6. activitats dirigides (sin fecha de sesion)
# ------------------------------------------------------------------

act = pd.read_excel(RAW, sheet_name="Activitats dirigides")
act["source_row"] = act.index + 2
act["activity_norm"] = act["Activitat"].map(norm_activity_name)
act["season"] = act["CodiActivitat"].str.extract(r"^(\d\d/\d\d)", expand=False)
act["start_min"] = act["HoraInici"].map(to_minutes)
act["end_min"] = act["HoraFi"].map(to_minutes)
act["over_capacity_row"] = act["Inscrits"] > act["AforamentMax"]

keys = ["CodiActivitat", "season", "activity_norm", "Sala", "start_min", "end_min"]
# Estados distintos (fecha, codigo, hora, sala, inscritos): evita que el numero
# de filas repetidas pese en la mediana.
states = act.drop_duplicates(["DataInscripcio", "CodiActivitat", "HoraInici",
                              "HoraFi", "Sala", "Inscrits"])
grp = states.groupby(keys, dropna=False).agg(
    name_original=("Activitat", "first"),
    capacity_max=("AforamentMax", "max"),
    capacity_values=("AforamentMax", "nunique"),
    median_enrolled_states=("Inscrits", "median"),
    max_enrolled=("Inscrits", "max"),
    n_states=("Inscrits", "size"),
).reset_index()
rows_per = act.groupby(keys, dropna=False).agg(
    n_rows=("Inscrits", "size"),
    over_capacity_rows=("over_capacity_row", "sum")).reset_index()
grp = grp.merge(rows_per, on=keys, how="left", validate="one_to_one")
grp["room"] = grp["Sala"]
grp["over_capacity_flag"] = (grp["over_capacity_rows"] > 0).astype(int)
grp["fill_indicator"] = grp["median_enrolled_states"] / grp["capacity_max"]
grp["fill_indicator_note"] = ("indicador de la serie, no ocupacion de una sesion: "
                              "DataInscripcio no es fecha de clase")
grp["session_date_known"] = False
assert int(grp["n_rows"].sum()) == len(act)
assert int(grp["over_capacity_rows"].sum()) == int(act["over_capacity_row"].sum())

# ------------------------------------------------------------------
# 7. guardar
# ------------------------------------------------------------------

res_out = res.drop(columns=["espai_pare_key", "recurs_key"])
res_out.to_parquet(OUT / "reservations_clean.parquet", index=False)
slots.to_parquet(OUT / "reservation_slot.parquet", index=False)
agg.to_parquet(OUT / "reservation_slot_agg.parquet", index=False)
grp.to_parquet(OUT / "directed_activity_class.parquet", index=False)

# ------------------------------------------------------------------
# 8. reporte
# ------------------------------------------------------------------

def peak(rid):
    x = agg[(agg["resource_id"] == rid) & (agg["booking_scope"] == "all")]
    return int(x["max_concurrent"].max()) if len(x) else None


people_all = agg[(agg["booking_scope"] == "all") & is_people]
over = people_all[ok_cap.loc[people_all.index]
                  & (people_all["max_concurrent"] > people_all["capacity_ref"])]
r = []
r.append("=" * 70)
r.append("PASO 3 — clean_data — reporte (ocupacion por intervalos)")
r.append("=" * 70)
r.append(f"Reserves raw: {n_raw}")
r.append(f"Reserves con resource_id: {int(res['has_resource'].sum())}")
r.append(f"Reserves sin resource_id: {int((~res['has_resource']).sum())}")
r.append(f"Intervalos invalidos: {int(res['invalid_interval'].sum())}")
r.append(f"calendar_mismatch: {int(res['calendar_mismatch'].sum())}")
r.append(f"is_long_block (> {LONG_BLOCK_MIN} min): {int(res['is_long_block'].sum())}")
r.append(f"night_block_candidate (21:00-23:59): {int(res['night_block_candidate'].sum())}")
r.append(f"outside_general_hours: {int(res['outside_general_hours'].sum())}")
r.append(f"Filas en grupos de filas identicas: {int((res['dup_group_size'] > 1).sum())} (se conservan)")
r.append("")
r.append(f"reservation_slot (fila x franja {SLOT} min): {len(slots)}")
r.append(f"reservation_slot_agg (recurso x dia x franja x alcance): {len(agg)}")
r.append(f"Minutos reservados (alcance all) = suma de duraciones: {got_minutes}")
r.append(f"Minutos con reservas solapadas en la misma pista: {conflict_rows}")
r.append("")
r.append(f"Pico de personas simultaneas SALA_FITNES: {peak('SALA_FITNES')} "
         f"(aforo inventario {res_info.loc['SALA_FITNES', 'capacity_people']:.0f})")
r.append(f"Franjas de personas con maximo > aforo de inventario: {len(over)}")
r.append(over.groupby("resource_id").size().to_string() if len(over) else "(ninguna)")
r.append("")
r.append("Aforo usado por recurso de personas:")
r.append(res_info[res_info["metric_type"] == "personas"][
    ["capacity_people", "capacity_people_source"]].to_string())
r.append("")
wk = agg[(agg["resource_id"] == "SALA_FITNES") & (agg["booking_scope"] == "all")
         & (agg["date_use"].dt.dayofweek < 5) & agg["in_general_hours"]]
r.append("SALA_FITNES laborables: personas simultaneas medias por hora")
r.append(wk.groupby("hour")["avg_concurrent"].mean().round(1).to_string())
r.append("")
r.append(f"Activitats dirigides raw: {len(act)}")
r.append(f"Series (codigo+sala+hora): {len(grp)}")
r.append(f"Filas con sobre-aforo: {int(act['over_capacity_row'].sum())} "
         f"en {int(grp['over_capacity_flag'].sum())} series")
r.append("session_date_known: False para todas (DataInscripcio no es fecha de sesion)")

report_text = "\n".join(str(x) for x in r)
(OUT / "clean_report.txt").write_text(report_text, encoding="utf-8")
print("\n" + report_text)
print(f"\nSalida: {OUT}")
