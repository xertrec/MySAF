"""Tests del paso 4 (create_database.py) y del validador.

Unitarios: datos sinteticos, no necesitan el Excel.
Integracion: usan los parquet de data/interim/clean (se saltan si no existen;
ejecuta antes clean_data.py).

    python -m pytest data_engineering/tests -q
"""
import re
import sqlite3
from pathlib import Path

import pandas as pd
import pytest

import create_database as cd
import validate_database as vd

BASE = Path(__file__).resolve().parents[1]
HAS_CLEAN = (cd.CLEAN / "reservation_slot_agg.parquet").exists() and cd.RAW.exists()
needs_clean = pytest.mark.skipif(not HAS_CLEAN, reason="faltan datos limpios (clean_data.py)")

OPENING = {"dl": (420, 1260), "dt": (420, 1260), "dc": (420, 1260), "dj": (420, 1260),
           "dv": (420, 1260), "ds": (480, 1200), "dg": (540, 840)}


# ------------------------------------------------------------------
# reglas puras
# ------------------------------------------------------------------

@pytest.mark.parametrize("hour,open_,close,closed", [
    (6, 420, 1260, True),     # antes de abrir
    (7, 420, 1260, False),    # primera hora
    (20, 420, 1260, False),   # ultima hora (20:00-21:00)
    (21, 420, 1260, True),    # al cierre
    (13, 540, 840, False),    # domingo 13-14
    (14, 540, 840, True),     # domingo cierra a las 14
    (8, 510, 1200, False),    # abre 8:30 -> la hora 8 esta parcialmente abierta
])
def test_is_hour_closed(hour, open_, close, closed):
    assert cd.is_hour_closed(hour, open_, close) is closed


def test_display_hours_spans_first_open_to_last_close():
    assert cd.display_hours(OPENING) == range(7, 21)
    assert cd.display_hours({"dl": (450, 1290)}) == range(7, 22)


@pytest.mark.parametrize("date,lectiu", [
    ("2026-04-01", True), ("2026-06-30", True), ("2026-07-01", False),
    ("2026-08-15", False), ("2026-09-01", True), ("2026-10-31", True),
])
def test_period_matches(date, lectiu):
    d = pd.Timestamp(date)
    assert cd.period_matches("lectiu", d) is lectiu
    assert cd.period_matches("all", d) is True


def test_period_matches_rejects_unknown():
    with pytest.raises(ValueError):
        cd.period_matches("estiu", pd.Timestamp("2026-07-01"))


def test_active_dates_drops_days_with_few_reservations():
    res = pd.DataFrame({"date_use": pd.to_datetime(
        ["2026-05-04"] * 40 + ["2026-05-01"] * 3 + ["2026-05-05"] * 30)})
    assert list(cd.active_dates(res, max_rows=30)) == [
        pd.Timestamp("2026-05-04"), pd.Timestamp("2026-05-05")]


def test_capacity_for_people_units_and_override():
    caps = {"A": 25.0, "B": 25.0, "C": 10.0}
    assert cd.capacity_for(cd.Activity("x", True, ("A", "C")), caps) == 35
    assert cd.capacity_for(cd.Activity("x", True, ("A", "B"), capacity_resources=("A",)), caps) == 25
    assert cd.capacity_for(cd.Activity("x", False, ("P1", "P2", "P3")), caps) == 3


def test_capacity_for_fails_without_inventory_capacity():
    with pytest.raises(SystemExit):
        cd.capacity_for(cd.Activity("x", True, ("UNKNOWN",)), {"UNKNOWN": float("nan")})


def test_parse_opening_hours():
    df = pd.DataFrame({"Dies": ["Dilluns a divendres", "Dissabte", "Diumenge"],
                       "Horari": ["7.00 a 21.00 h", "8.00 a 20.00 h", "9.00 a 14.00 h"]})
    assert cd.parse_opening_hours(df) == OPENING


def test_parse_opening_hours_rejects_incomplete():
    df = pd.DataFrame({"Dies": ["Dissabte"], "Horari": ["8.00 a 20.00 h"]})
    with pytest.raises(SystemExit):
        cd.parse_opening_hours(df)


# ------------------------------------------------------------------
# agregacion con datos sinteticos
# ------------------------------------------------------------------

MON1, MON2 = pd.Timestamp("2026-05-04"), pd.Timestamp("2026-05-11")   # dos lunes lectivos


def slot(rid, date, start, avg=0.0, units=None, mx=None, booked=0, scope="all"):
    return dict(resource_id=rid, booking_scope=scope, date_use=date, slot_start_min=start,
                avg_concurrent=avg, max_concurrent=mx if mx is not None else int(avg),
                units_busy_avg=units, booked_minutes=booked, rule_version="T")


def test_hourly_per_date_people_missing_slots_count_as_zero():
    agg = pd.DataFrame([slot("SALA", MON1, 600, avg=4, mx=5), slot("SALA", MON1, 615, avg=8, mx=9)])
    act = cd.Activity("sala", True, ("SALA",))
    out = cd.hourly_per_date(agg, act, pd.DatetimeIndex([MON1, MON2]), range(10, 12))
    row = out[(out.date_use == MON1) & (out.hour == 10)].iloc[0]
    assert row.occupied == pytest.approx(3.0)      # (4 + 8 + 0 + 0) / 4
    assert row.peak == 9
    # fecha y hora sin filas -> ceros
    assert out[(out.date_use == MON2)].occupied.sum() == 0
    assert len(out) == 4


def test_hourly_per_date_units_sum_across_courts():
    rows = [slot(f"P{i}", MON1, s, units=1.0) for i in (1, 2) for s in (600, 615, 630, 645)]
    rows += [slot("P3", MON1, 600, units=0.5)]
    act = cd.Activity("padel", False, ("P1", "P2", "P3"))
    out = cd.hourly_per_date(pd.DataFrame(rows), act, pd.DatetimeIndex([MON1]), range(10, 11))
    assert out.iloc[0].occupied == pytest.approx(2.125)   # 1 + 1 + 0.5/4
    assert out.iloc[0].peak == pytest.approx(2.125)       # en pistas el pico es la fraccion


def test_hourly_per_date_fails_on_unknown_resource():
    agg = pd.DataFrame([slot("SALA", MON1, 600, avg=1)])
    with pytest.raises(SystemExit):
        cd.hourly_per_date(agg, cd.Activity("x", True, ("SALA", "MISSING")),
                           pd.DatetimeIndex([MON1]), range(10, 11))


def synthetic_inputs():
    """Dos lunes activos; SALA tiene 20 personas a las 10h solo el primero."""
    rows = [slot("SALA", MON1, s, avg=20, mx=22, booked=300) for s in (600, 615, 630, 645)]
    rows += [slot("SALA", MON1, s, avg=10, booked=150, scope="standard") for s in (600, 615, 630, 645)]
    rows += [slot("P1", MON2, s, units=1.0, booked=15) for s in (1080, 1095)]
    rows += [slot("P1", MON2, s, units=1.0, booked=15, scope="standard") for s in (1080, 1095)]
    res = pd.DataFrame({"date_use": [MON1] * 50 + [MON2] * 50 + [pd.Timestamp("2026-05-18")] * 2})
    acts = (cd.Activity("sala", True, ("SALA",)), cd.Activity("pista", False, ("P1",)))
    return pd.DataFrame(rows), res, {"SALA": 40.0}, acts


def test_build_hourly_rows_grid_means_and_flags():
    agg, res, caps, acts = synthetic_inputs()
    rows = cd.build_hourly_rows(agg, res, OPENING, caps, acts)
    assert len(rows) == len(acts) * len(cd.PERIODS) * 7 * 14
    assert not rows.duplicated(["activity_id", "period", "weekday", "hour"]).any()

    def cell(aid, wd, h, period="lectiu"):
        return rows.set_index(["activity_id", "period", "weekday", "hour"]).loc[(aid, period, wd, h)]

    sala = cell("sala", "dl", 10)
    assert sala.capacity == 40
    assert sala.avg_occupied == pytest.approx(10.0)   # media de 20 y 0 (dia 18 inactivo)
    assert sala.peak_occupied == pytest.approx(11.0)
    assert sala.sample_days == 2
    assert sala.long_block_share == pytest.approx(0.5)  # 1200 min en total, 600 estandar
    assert sala.is_closed == 0

    pista = cell("pista", "dl", 18)
    assert pista.capacity == 1
    assert pista.avg_occupied == pytest.approx(0.25)   # (0.5 + 0) / 2 dias
    assert pista.long_block_share == 0

    # sin datos ese dia de la semana -> 0 dias observados
    assert cell("sala", "dt", 10).sample_days == 0
    # horas cerradas: valores a cero
    closed = rows[rows.is_closed == 1]
    assert (closed[["avg_occupied", "peak_occupied", "sample_days"]] == 0).all().all()
    assert set(closed[closed.weekday == "dg"].hour) == {7, 8, 14, 15, 16, 17, 18, 19, 20}


def test_write_sqlite_is_valid_and_room_compatible(tmp_path):
    agg, res, caps, acts = synthetic_inputs()
    db = tmp_path / "t.db"
    cd.write_sqlite(db, cd.build_activity_rows(caps, acts),
                    cd.build_hourly_rows(agg, res, OPENING, caps, acts), OPENING, {"k": "v"})
    con = sqlite3.connect(db)
    assert con.execute("PRAGMA user_version").fetchone()[0] == cd.DB_VERSION
    pk = [r[1] for r in sorted(con.execute("PRAGMA table_info(hourly_availability)"),
                               key=lambda r: r[5]) if r[5]]
    assert pk == ["activity_id", "period", "weekday", "hour"]
    # todas las columnas NOT NULL (las entidades Kotlin no tienen tipos nulables)
    for table in cd.SCHEMA:
        assert all(r[3] == 1 for r in con.execute(f"PRAGMA table_info({table})")), table
    con.close()
    errors = vd.validate(db)
    # el validador espera las 11 actividades reales; solo ese chequeo debe fallar
    assert [e for e in errors if not e.startswith("actividades")] == []


def test_validator_detects_corruption(tmp_path):
    agg, res, caps, acts = synthetic_inputs()
    db = tmp_path / "t.db"
    cd.write_sqlite(db, cd.build_activity_rows(caps, acts),
                    cd.build_hourly_rows(agg, res, OPENING, caps, acts), OPENING, {})
    con = sqlite3.connect(db)
    con.execute("UPDATE hourly_availability SET is_closed = 1 - is_closed "
                "WHERE activity_id='sala' AND period='all' AND weekday='dl' AND hour=10")
    con.execute("UPDATE hourly_availability SET long_block_share = 2 "
                "WHERE activity_id='pista' AND period='all' AND weekday='dl' AND hour=11")
    con.commit()
    con.close()
    errors = " | ".join(vd.validate(db))
    assert "sala/all/dl/10h: is_closed" in errors
    assert "pista/all/dl/11h: long_block_share" in errors


def test_validator_detects_schema_drift(tmp_path):
    db = tmp_path / "bad.db"
    con = sqlite3.connect(db)
    for table, ddl in cd.SCHEMA.items():
        con.execute(ddl.replace("`capacity` INTEGER NOT NULL", "`capacity` REAL")
                    if table == "activity" else ddl)
    con.execute(f"PRAGMA user_version = {cd.DB_VERSION}")
    con.commit()
    con.close()
    assert "esquema distinto en activity" in vd.validate(db)


# ------------------------------------------------------------------
# coherencia con la app Android
# ------------------------------------------------------------------

APP = BASE.parent / "app/src/main"


def test_activity_ids_match_kotlin_catalog():
    src = (APP / "java/com/uab/mysaf/data/ActivityCatalog.kt").read_text(encoding="utf-8")
    entries = re.findall(r'ActivityInfo\(\s*"([a-z0-9_]+)"[^\n]*?(, false)?\),?\n', src)
    assert [e[0] for e in entries] == [a.id for a in cd.ACTIVITIES]
    for (aid, is_units), act in zip(entries, cd.ACTIVITIES):
        assert act.is_person_count == (is_units == ""), aid


def test_db_version_matches_room_database():
    src = (APP / "java/com/uab/mysaf/data/db/MySafDatabase.kt").read_text(encoding="utf-8")
    assert re.search(r"version\s*=\s*(\d+)", src).group(1) == str(cd.DB_VERSION)
    assert f'"{Path(cd.APP_ASSET_OUT).relative_to(APP / "assets").as_posix()}"' in src


def test_room_entities_declare_same_columns_as_schema():
    src = (APP / "java/com/uab/mysaf/data/db/Entities.kt").read_text(encoding="utf-8")
    for table, ddl in cd.SCHEMA.items():
        body = src.split(f'tableName = "{table}"', 1)[1].split("@Entity", 1)[0]
        kotlin_cols = re.findall(r'@ColumnInfo\(name = "([a-z_]+)"\)', body)
        sql_cols = re.findall(r"`([a-z_]+)` (?:TEXT|INTEGER|REAL)", ddl)
        assert sorted(kotlin_cols) == sorted(sql_cols), table


# ------------------------------------------------------------------
# integracion con los datos reales
# ------------------------------------------------------------------

@pytest.fixture(scope="module")
def real_db(tmp_path_factory):
    if not HAS_CLEAN:
        pytest.skip("faltan datos limpios")
    out = tmp_path_factory.mktemp("db") / "mysaf.db"
    old_csv = cd.CSV_OUT
    cd.CSV_OUT = out.with_suffix(".csv")
    try:
        cd.main(["--out", str(out), "--no-app-copy"])
    finally:
        cd.CSV_OUT = old_csv
    return out


@needs_clean
def test_real_database_passes_validation(real_db):
    assert vd.validate(real_db) == []


@needs_clean
def test_real_database_cell_matches_independent_computation(real_db):
    """sala_fitness, lectiu, lunes 18h recalculado directamente del parquet."""
    agg = pd.read_parquet(cd.CLEAN / "reservation_slot_agg.parquet")
    res = pd.read_parquet(cd.CLEAN / "reservations_clean.parquet", columns=["date_use"])
    days = res.groupby("date_use").size()
    mondays = [d for d in days[days >= cd.CLOSED_DAY_MAX_ROWS].index
               if d.dayofweek == 0 and d.month in (4, 5, 6, 9, 10)]
    f = agg[(agg.resource_id == "SALA_FITNES") & (agg.booking_scope == "all")
            & (agg.slot_start_min // 60 == 18)]
    per_day = f.groupby("date_use").avg_concurrent.sum().div(4).reindex(mondays, fill_value=0)

    con = sqlite3.connect(real_db)
    avg, days_n, cap = con.execute(
        "SELECT avg_occupied, sample_days, capacity FROM hourly_availability "
        "WHERE activity_id='sala_fitness' AND period='lectiu' AND weekday='dl' AND hour=18"
    ).fetchone()
    assert days_n == len(mondays)
    assert cap == 120
    assert avg == pytest.approx(per_day.mean(), abs=1e-3)


@needs_clean
def test_real_database_expected_shape(real_db):
    con = sqlite3.connect(real_db)
    caps = dict(con.execute("SELECT id, capacity FROM activity"))
    assert caps == {"piscina_25m": 40, "piscina_16m": 25, "sala_fitness": 120,
                    "sala_boxtraining": 14, "sala_1_ritmes": 35, "sala_2_ritmes": 20,
                    "sala_3_zen": 20, "sala_4_cycling": 35, "basquet_exterior": 1, "volei_platja": 1, "padel": 4, "tennis": 5,
                    "esquaix": 3, "pavello": 3, "futbol_sala": 1, "futbol_7_11": 4,
                    "barbell": 25, "callistenia": 20, "rocodrom": 26}
    # domingo: solo de 9 a 14
    open_sunday = [h for (h,) in con.execute(
        "SELECT hour FROM hourly_availability WHERE activity_id='padel' AND period='all' "
        "AND weekday='dg' AND is_closed=0 ORDER BY hour")]
    assert open_sunday == [9, 10, 11, 12, 13]
    # el periodo completo tiene al menos tantos dias observados como el lectivo
    rows = con.execute(
        "SELECT a.sample_days, l.sample_days FROM hourly_availability a "
        "JOIN hourly_availability l USING (activity_id, weekday, hour) "
        "WHERE a.period='all' AND l.period='lectiu'").fetchall()
    assert all(a >= l for a, l in rows)


@needs_clean
def test_app_asset_is_up_to_date(real_db):
    """La base de datos empaquetada en la app debe ser la del pipeline actual."""
    asset = cd.APP_ASSET_OUT
    if not asset.exists():
        pytest.fail(f"falta {asset}: ejecuta scripts/create_database.py")

    def dump(p):
        con = sqlite3.connect(p)
        try:
            return {t: con.execute(f"SELECT * FROM {t} ORDER BY 1,2").fetchall() for t in cd.SCHEMA}
        finally:
            con.close()

    assert dump(asset) == dump(real_db)
