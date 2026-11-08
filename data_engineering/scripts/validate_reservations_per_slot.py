
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

input_file = BASE_DIR / "data/raw/saf-espais-2026-equips.xlsx"
output_dir = BASE_DIR / "data/interim/analysis"
output_dir.mkdir(parents=True, exist_ok=True)

# Leer las dos hojas
detail = pd.read_excel(input_file, sheet_name="Reserves")
slots = pd.read_excel(input_file, sheet_name="Reserves per franja")

# Claves que identifican una franja
keys = [
    "EspaiPare",
    "Recurs",
    "DataUs",
    "DiaSetmana",
    "HoraInici"
]

# Contar cuántas filas de Reserves hay en cada franja
calculated = (
    detail.groupby(keys)
    .size()
    .reset_index(name="Reserves_calculadas")
)

# Comprobar si hay claves repetidas en la hoja agregada
duplicate_keys = slots.duplicated(subset=keys).sum()

# Comparar ambas hojas
comparison = calculated.merge(
    slots,
    on=keys,
    how="outer",
    indicator=True
)

# Detectar diferencias
comparison["diferencia"] = (
        comparison["Reserves_calculadas"].fillna(0)
        - comparison["Reserves"].fillna(0)
)

missing = comparison[comparison["_merge"] == "left_only"]
extra = comparison[comparison["_merge"] == "right_only"]
different = comparison[
    (comparison["_merge"] == "both")
    & (comparison["diferencia"] != 0)
    ]

print("\n========== VALIDACIÓN ==========")
print("Filas en Reserves:", len(detail))
print("Filas en Reserves per franja:", len(slots))
print("Grupos calculados desde Reserves:", len(calculated))
print("Claves duplicadas en la hoja agregada:", duplicate_keys)

print("\n========== COMPARACIÓN ==========")
print("Franjas coincidentes:", (comparison["_merge"] == "both").sum())
print("Franjas que faltan en la hoja agregada:", len(missing))
print("Franjas adicionales en la hoja agregada:", len(extra))
print("Franjas con cantidades diferentes:", len(different))

print("\nSuma de Reserves per franja:", slots["Reserves"].sum())
print("Total de filas en Reserves:", len(detail))

# Guardar las diferencias para poder revisarlas
differences = comparison[
    (comparison["_merge"] != "both")
    | (comparison["diferencia"] != 0)
    ]

differences.to_csv(
    output_dir / "reservation_slot_differences.csv",
    index=False,
    sep=";",
    encoding="utf-8-sig"
)

if (
        duplicate_keys == 0
        and missing.empty
        and extra.empty
        and different.empty
):
    print("\nRESULTADO: las dos hojas coinciden exactamente.")
else:
    print("\nRESULTADO: hay diferencias que debemos investigar.")

print(
    "\nInforme de diferencias:",
    output_dir / "reservation_slot_differences.csv"
)
