"""
03b_enrich_inventory.py

Cruza resource_alias con capacidades conocidas para rellenar capacity_units.
Lo que no está en el diccionario, queda None y se marca pendiente_validacion.

Inventario (aproximado, ajustar con SAF si hay cifras oficiales):
- piscina 25m: 8 carriles × 5 pax = 40
- piscina 16m: 32 (2 mitades de 16)
- sala fitness: 120
- sala 4 cycling: 32
- espai barbell: 20
- sala 1 ritmes: 35
- sala 2 ritmes: 25
- sala 3 zen: 18
- sala 6 box: 14
- cal·listènia: 24
- rocòdrom interior: 18
- rocòdrom exterior: 25
- pistas/tenis/padel/fútbol/pabellón: 1 unidad
"""
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
ALIAS = BASE / "data/interim/mapping/resource_alias.csv"
OUT = BASE / "data/interim/mapping"
OUT.mkdir(parents=True, exist_ok=True)

CAPACITIES = {
    # Piscinas
    "PISCINA_25M_COBERTA": 40.0,
    "PISCINA_25M_CARRER_1": 5.0,
    "PISCINA_25M_CARRER_2": 5.0,
    "PISCINA_25M_CARRER_3": 5.0,
    "PISCINA_25M_CARRER_4": 5.0,
    "PISCINA_25M_CARRER_5": 5.0,
    "PISCINA_25M_CARRER_6": 5.0,
    "PISCINA_25M_CARRER_7": 5.0,
    "PISCINA_25M_CARRER_8": 5.0,
    "PISCINA_16M_COMPLETA": 32.0,
    "PISCINA_16M_MEITAT_A": 16.0,
    "PISCINA_16M_MEITAT_B": 16.0,

    # Salas
    "SALA_FITNES": 120.0,
    "SALA_4_CYCLING": 32.0,
    "ESPAI_BARBELL": 20.0,
    "AADD_ESPAI_BARBELL": 20.0,
    "SALA_1_RITMES": 35.0,
    "SALA_2_RITMES": 25.0,
    "SALA_3_ZEN": 18.0,
    "AADD_SALA_1_RITMES": 35.0,
    "AADD_SALA_2_RITMES": 25.0,
    "AADD_SALA_3_ZEN": 18.0,
    "SALA_6_BOXTRAINING": 14.0,

    # Espacios
    "CALISTENIA": 24.0,
    "ROCODROM_INTERIOR": 18.0,
    "ROCODROM_EXTERIOR": 25.0,

    # Pistas (unidad = 1)
    "PADEL_PISTA_1": 1.0,
    "PADEL_PISTA_2": 1.0,
    "PADEL_PISTA_3": 1.0,
    "PADEL_PISTA_4": 1.0,
    "TENIS_PISTA_1": 1.0,
    "TENIS_PISTA_2": 1.0,
    "TENIS_PISTA_3": 1.0,
    "TENIS_PISTA_4": 1.0,
    "TENIS_PISTA_5": 1.0,
    "ESQUAIX_PISTA_2": 1.0,
    "ESQUAIX_PISTA_3": 1.0,
    "ESQUAIX_PISTA_4": 1.0,
    "PAVELLO_PISTA_2": 1.0,
    "PAVELLO_PISTA_3": 1.0,
    "PAVELLO_PISTA_2_MITAT_1": 0.5,
    "PAVELLO_PISTA_2_MITAT_2": 0.5,
    "PAVELLO_PISTA_3_MITAT_1": 0.5,
    "PAVELLO_PISTA_3_MITAT_2": 0.5,
    "PAVELLO_BADMINTON_1": 1.0,
    "PAVELLO_BADMINTON_1_SUB_1": 1 / 3,
    "PAVELLO_BADMINTON_1_SUB_2": 1 / 3,
    "PAVELLO_BADMINTON_1_SUB_3": 1 / 3,
    "FUTBOL7_CAMP_1": 1.0,
    "FUTBOL7_CAMP_2": 1.0,
    "FUTBOL7_CAMP_3": 1.0,
    "FUTBOL7_CAMP_4": 1.0,
    "FUTBOL7_CAMP_4_MITAT_1": 0.5,
    "FUTBOL7_CAMP_4_MITAT_2": 0.5,
    "FUTBOL_SALA_1": 1.0,
    "CAMPS_EXTERIORS": 1.0,
    "BASQUET_EXTERIOR": 1.0,
    "VOLEI_PLATJA": 1.0,
}

PENDIENTES_LEGITIMOS = {
    "",  # anomalía TENNIS ds-dg
    "AADD_FORA_SAF",
    "CORRER_CAMPUS",
    "SAF_2_PISCINA",
    "PISCINA_25M_SOLARIUM",
    "PAVELLO_COBERT",
    "CAMPS_EXTERIORS_CONTAINER",  # por si acaso
}

alias = pd.read_csv(ALIAS, sep=";")

alias["capacity_units"] = alias.apply(
    lambda r: CAPACITIES.get(r["resource_id"], r["capacity_units"]),
    axis=1,
)

con_cap = alias["capacity_units"].notna().sum()
sin_cap = alias["capacity_units"].isna()
sin_cap_ids = alias.loc[sin_cap, "resource_id"].fillna("").unique().tolist()

print("=" * 70)
print("PASO 3b — enrich_inventory")
print("=" * 70)
print(f"Filas: {len(alias)}")
print(f"Con capacity_units: {con_cap}")
print(f"Sin capacity_units: {sin_cap.sum()}")
print(f"Resource IDs sin capacity: {sin_cap_ids}")

# Detectar IDs sin capacity que NO deberían ser pendientes
problematicos = [
    rid for rid in sin_cap_ids
    if rid not in PENDIENTES_LEGITIMOS
       and rid in CAPACITIES  # está en el diccionario pero no se aplicó
]
if problematicos:
    print(f"\nWARN — IDs con capacity definida pero no aplicada: {problematicos}")
else:
    print("\nOK — todos los IDs con capacity conocida tienen valor.")

# Mostrar IDs sin capacity (para transparencia)
print("\nIDs sin capacity_units (deberían ser contenedores/servicios/anomalías):")
print(alias.loc[sin_cap, ["resource_id", "resource_kind", "metric_type"]]
      .drop_duplicates().to_string(index=False))

alias.to_csv(OUT / "resource_alias.csv", sep=";", index=False, encoding="utf-8-sig")
print(f"\nSalida: {OUT / 'resource_alias.csv'}")