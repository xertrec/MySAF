import pandas as pd
from pathlib import Path

# Rutas
BASE_DIR = Path(__file__).resolve().parents[1]

input_file = BASE_DIR / "data/raw/saf-espais-2026-equips.xlsx"
output_dir = BASE_DIR / "data/interim/duplicates"

output_dir.mkdir(parents=True, exist_ok=True)

# Hojas que queremos investigar
sheets = [
    "Espais",
    "Reserves",
    "Activitats dirigides"
]

for sheet in sheets:

    print(f"\n========== {sheet} ==========")

    df = pd.read_excel(input_file, sheet_name=sheet)

    # Agrupar registros exactamente iguales
    grouped = (
        df.groupby(
            list(df.columns),
            dropna=False
        )
        .size()
        .reset_index(name="frequency")
    )

    # Conservar únicamente grupos repetidos
    duplicates = grouped[grouped["frequency"] > 1]

    print(f"Filas originales: {len(df)}")
    print(f"Grupos de registros repetidos: {len(duplicates)}")
    print(f"Filas pertenecientes a grupos repetidos: "
          f"{duplicates['frequency'].sum()}")
    print(f"Máxima frecuencia de un mismo registro: "
          f"{duplicates['frequency'].max() if len(duplicates) else 1}")

    # Guardar patrones repetidos
    output_file = output_dir / f"{sheet.lower().replace(' ', '_')}_duplicates.csv"

    duplicates.to_csv(
        output_file,
        index=False,
        sep=";",
        encoding="utf-8-sig"
    )

    print(f"Informe guardado: {output_file}")

# Revisar específicamente los espacios con valores vacíos
spaces = pd.read_excel(input_file, sheet_name="Espais")

missing_spaces = spaces[spaces.isna().any(axis=1)]

missing_spaces.to_csv(
    output_dir / "spaces_missing_values.csv",
    index=False,
    sep=";",
    encoding="utf-8-sig"
)

print("\n========== ESPAIS: VALORES VACÍOS ==========")
print(missing_spaces.to_string(index=False))