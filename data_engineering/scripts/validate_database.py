"""
05_validate_database.py

Comprueba la base de datos generada por create_database.py antes de
empaquetarla en la app. Sale con codigo 1 si encuentra algun problema.

Uso:  python scripts/validate_database.py [ruta/a/mysaf.db]
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from create_database import (  # noqa: E402
    ACTIVITIES, DB_OUT, DB_VERSION, PERIODS, SCHEMA, WEEKDAY_CODES, is_hour_closed,
)

MAX_LOAD = 1.5   # personas pueden superar el aforo puntualmente (ver clean_report)


def _table_info(con, table):
    return [(r[1], r[2].upper(), bool(r[3]), r[5])
            for r in con.execute(f"PRAGMA table_info(`{table}`)")]


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"no existe {path}"]
    con = sqlite3.connect(path)
    try:
        # 1. esquema identico al que espera Room
        ref = sqlite3.connect(":memory:")
        for table, ddl in SCHEMA.items():
            ref.execute(ddl)
            if _table_info(con, table) != _table_info(ref, table):
                errors.append(f"esquema distinto en {table}")
        extra = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        } - set(SCHEMA)
        if extra:
            errors.append(f"tablas inesperadas: {sorted(extra)}")
        if con.execute("PRAGMA user_version").fetchone()[0] != DB_VERSION:
            errors.append(f"user_version != {DB_VERSION}")
        if errors:
            return errors

        # 2. actividades
        ids = [r[0] for r in con.execute("SELECT id FROM activity ORDER BY sort_order")]
        if ids != [a.id for a in ACTIVITIES]:
            errors.append(f"actividades: {ids}")
        if con.execute("SELECT COUNT(*) FROM activity WHERE capacity <= 0").fetchone()[0]:
            errors.append("actividad con capacidad <= 0")

        # 3. rejilla completa actividad x periodo x dia x hora
        hours = sorted({r[0] for r in con.execute("SELECT DISTINCT hour FROM hourly_availability")})
        expected = len(ids) * len(PERIODS) * len(WEEKDAY_CODES) * len(hours)
        n = con.execute("SELECT COUNT(*) FROM hourly_availability").fetchone()[0]
        if n != expected:
            errors.append(f"hourly_availability: {n} filas, se esperaban {expected}")
        if hours != list(range(hours[0], hours[-1] + 1)):
            errors.append(f"horas no consecutivas: {hours}")

        # 4. coherencia con el horario y la capacidad
        opening = {wd: (o, c) for wd, o, c in con.execute("SELECT * FROM opening_hours")}
        if sorted(opening, key=WEEKDAY_CODES.index) != WEEKDAY_CODES:
            errors.append("opening_hours incompleto")
        cap = dict(con.execute("SELECT id, capacity FROM activity"))
        for (aid, period, wd, hour, avg, peak, capacity, days, share, closed) in con.execute(
                "SELECT * FROM hourly_availability"):
            where = f"{aid}/{period}/{wd}/{hour}h"
            if wd in opening and bool(closed) != is_hour_closed(hour, *opening[wd]):
                errors.append(f"{where}: is_closed no coincide con el horario")
            if capacity != cap.get(aid):
                errors.append(f"{where}: capacity {capacity} != {cap.get(aid)}")
            if closed and (avg or peak or days):
                errors.append(f"{where}: hora cerrada con valores")
            if avg < 0 or avg > MAX_LOAD * capacity:
                errors.append(f"{where}: avg_occupied fuera de rango ({avg})")
            if peak + 1e-9 < avg:
                errors.append(f"{where}: peak_occupied < avg_occupied")
            if not 0 <= share <= 1:
                errors.append(f"{where}: long_block_share fuera de [0,1]")
            if len(errors) > 50:
                errors.append("... (demasiados errores)")
                break
    finally:
        con.close()
    return errors


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    path = Path(argv[0]) if argv else DB_OUT
    errors = validate(path)
    if errors:
        print(f"INVALIDA: {path}")
        for e in errors:
            print("  -", e)
        return 1
    print(f"OK: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
