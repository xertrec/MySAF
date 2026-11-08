"""
03b_enrich_inventory.py

Asigna a cada resource_id de resource_alias.csv su aforo en PERSONAS
tomado EXCLUSIVAMENTE de la hoja `Espais` del Excel original.

Reglas (corrigen la version anterior, que escribia cifras propias):
- Ningun aforo se escribe a mano en este script. Solo se declara QUE filas
  del inventario corresponden a cada recurso (INVENTORY_MAP). Esa
  correspondencia es provisional hasta que la confirme el SAF.
- Un recurso con una fila de inventario -> capacity_people_source = "inventory".
- Un recurso que agrega varias filas (p. ej. la piscina de 25 m = 8 carriles)
  -> suma de esas filas, capacity_people_source = "derived_sum".
- Filas exactamente duplicadas del inventario (p. ej. "carrer 6" x2) cuentan
  una sola vez; se informa en pantalla.
- Recurso sin fila de inventario -> capacity_people = NULL y
  capacity_people_source = "unknown". Nunca se inventa (ni se divide un aforo
  entre mitades).
- capacity_units (fraccion estructural de pista: 1, 0.5, 1/3) NO se toca aqui.

Salida: sobrescribe data/interim/mapping/resource_alias.csv anadiendo
capacity_people, capacity_people_source, capacity_people_inventory_rows,
capacity_people_mapping_status. Es idempotente.
"""
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data/raw/saf-espais-2026-equips.xlsx"
ALIAS = BASE / "data/interim/mapping/resource_alias.csv"

# resource_id -> lista de (Espai, Subespai) del inventario, textos EXACTOS de la
# hoja Espais. Subespai None = celda vacia. Correspondencia PROVISIONAL.
INVENTORY_MAP = {
    "SALA_FITNES": [("Sala fitnes + sala cardio", None)],
    "ESPAI_BARBELL": [("Espai Barbell", None)],
    "AADD_ESPAI_BARBELL": [("Espai Barbell", None)],
    "AADD_SALA_1_RITMES": [("sales activitats dirigides", "sala 1")],
    "AADD_SALA_2_RITMES": [("sales activitats dirigides", "sala 2")],
    "AADD_SALA_3_ZEN": [("sales activitats dirigides", "sala 3")],
    "SALA_4_CYCLING": [("sales activitats dirigides", "sala 4")],
    "SALA_6_BOXTRAINING": [("sala boxtraining (esquaix 1)", None)],
    "CALISTENIA": [("zona cal·listènia", None)],
    "ROCODROM_INTERIOR": [("rocòdrom interior", None)],
    "ROCODROM_EXTERIOR": [("rocòdrom exterior", None)],
    "PISCINA_16M_COMPLETA": [("piscina de 16 metres", None)],
    # PISCINA_16M_MEITAT_A / _B: no estan en el inventario -> unknown.
    **{f"PISCINA_25M_CARRER_{n}": [("piscina 25 metres", f"carrer {n}")]
       for n in range(1, 9)},
    "PISCINA_25M_COBERTA": [("piscina 25 metres", f"carrer {n}")
                            for n in range(1, 9)],
    # Pistas: aforo en personas por pista (informativo; la ocupacion de pistas
    # se mide en unidades, no en personas).
    **{f"TENIS_PISTA_{n}": [("tennis", f"tennis {n}")] for n in range(1, 6)},
    **{f"ESQUAIX_PISTA_{n}": [("esquaix", f"esquaix {n}")] for n in (2, 3, 4)},
    "PADEL_PISTA_1": [("pistes de pàdel", "pista 1")],
    # PADEL_PISTA_2: el inventario tiene "pista 1" dos veces y ninguna
    # "pista 2". Probable errata, pendiente del SAF -> unknown.
    "PADEL_PISTA_3": [("pistes de pàdel", "pista 3")],
    "PADEL_PISTA_4": [("pistes de pàdel", "pista 4")],
    "FUTBOL7_CAMP_1": [("futbol 7", "camp 1")],
    "FUTBOL7_CAMP_2": [("futbol 7", "camp 2")],
    "FUTBOL7_CAMP_3": [("futbol 7", "camps 3")],   # texto tal cual del Excel
    "FUTBOL7_CAMP_4": [("futbol 7", "camp 4")],
    "BASQUET_EXTERIOR": [("Bàsquet exterior", None)],
    "FUTBOL_SALA_1": [("futbol sala extrerior", None)],  # texto tal cual
    "VOLEI_PLATJA": [("voleibol platja", None)],
    # Pabellon (poli 1/2/3?) y resto: sin correspondencia confirmada -> unknown.
}


def main():
    inv = pd.read_excel(RAW, sheet_name="Espais")
    inv["source_row"] = inv.index + 2          # fila de Excel (cabecera = 1)
    inv["is_exact_duplicate"] = inv.duplicated(["Espai", "Subespai", "Aforament"])

    dups = inv[inv["is_exact_duplicate"]]
    if len(dups):
        print("Filas de inventario exactamente duplicadas (cuentan una vez):")
        print(dups[["source_row", "Espai", "Subespai", "Aforament"]].to_string(index=False))

    keyed = inv[~inv["is_exact_duplicate"]]
    lookup = {}
    for r in keyed.itertuples():
        sub = None if pd.isna(r.Subespai) else str(r.Subespai)
        lookup.setdefault((str(r.Espai), sub), []).append(r)

    alias = pd.read_csv(ALIAS, sep=";")
    out_cap, out_src, out_rows, out_status = [], [], [], []
    missing_keys = []
    for rid in alias["resource_id"].fillna(""):
        keys = INVENTORY_MAP.get(rid)
        if not keys:
            out_cap.append(None); out_src.append("unknown")
            out_rows.append(None); out_status.append(None)
            continue
        matched = []
        for k in keys:
            hits = lookup.get(k, [])
            if len(hits) != 1:
                missing_keys.append((rid, k, len(hits)))
            matched.extend(hits)
        if not matched or len(matched) != len(keys):
            out_cap.append(None); out_src.append("unknown")
            out_rows.append(None); out_status.append("mapping_error")
            continue
        out_cap.append(float(sum(m.Aforament for m in matched)))
        out_src.append("inventory" if len(matched) == 1 else "derived_sum")
        out_rows.append(",".join(str(m.source_row) for m in matched))
        out_status.append("provisional")

    if missing_keys:
        raise SystemExit(
            "ERROR: claves de INVENTORY_MAP sin una unica fila en Espais: "
            f"{missing_keys}")

    alias["capacity_people"] = out_cap
    alias["capacity_people_source"] = out_src
    alias["capacity_people_inventory_rows"] = out_rows
    alias["capacity_people_mapping_status"] = out_status

    # capacity_units solo tiene sentido para recursos de unidad (pistas).
    is_unit = alias["metric_type"] == "unidad_recurso"
    alias.loc[~is_unit, "capacity_units"] = None

    alias.to_csv(ALIAS, sep=";", index=False, encoding="utf-8-sig")

    s = alias.drop_duplicates("resource_id")
    print("=" * 70)
    print("PASO 3b — enrich_inventory (aforo desde Espais)")
    print("=" * 70)
    print(s["capacity_people_source"].value_counts().to_string())
    print("\nAforos asignados (personas):")
    print(s[s["capacity_people"].notna()][
        ["resource_id", "capacity_people", "capacity_people_source",
         "capacity_people_inventory_rows"]].to_string(index=False))
    print(f"\nSalida: {ALIAS}")


if __name__ == "__main__":
    main()
