import pandas as pd
import json
from pathlib import Path

# Rutas del proyecto
BASE_DIR = Path(__file__).resolve().parents[1]

input_file = BASE_DIR / "data" / "raw" / "saf-espais-2026-equips.xlsx"
output_dir = BASE_DIR / "data" / "interim" / "eda"

output_dir.mkdir(parents=True, exist_ok=True)

# Comprobar que existe el Excel
if not input_file.exists():
    raise FileNotFoundError(f"No se encuentra: {input_file}")

# Abrir el Excel
excel = pd.ExcelFile(input_file)

sheet_summary = []
column_profile = []

print("\n========== ANÁLISIS EXPLORATORIO mySAF ==========")

# Analizar cada hoja
for sheet_name in excel.sheet_names:

    print(f"\nAnalizando hoja: {sheet_name}")

    df = pd.read_excel(excel, sheet_name=sheet_name)

    # Resumen general
    sheet_summary.append({
        "sheet": sheet_name,
        "rows": len(df),
        "columns": len(df.columns),
        "exact_duplicate_rows": int(df.duplicated().sum()),
        "missing_cells": int(df.isna().sum().sum())
    })

    # Analizar cada columna
    for column in df.columns:

        series = df[column]

        examples = (
            series.dropna()
            .astype(str)
            .drop_duplicates()
            .head(5)
            .tolist()
        )

        column_profile.append({
            "sheet": sheet_name,
            "column": column,
            "dtype": str(series.dtype),
            "missing_count": int(series.isna().sum()),
            "missing_percentage": round(
                series.isna().mean() * 100, 2
            ),
            "unique_values": int(series.nunique()),
            "examples": json.dumps(examples, ensure_ascii=False)
        })

    print(f"Filas: {len(df)}")
    print(f"Columnas: {len(df.columns)}")
    print(f"Duplicados exactos: {df.duplicated().sum()}")
    print(f"Celdas vacías: {df.isna().sum().sum()}")

# Crear informes
summary_df = pd.DataFrame(sheet_summary)
profile_df = pd.DataFrame(column_profile)

summary_df.to_csv(
    output_dir / "sheet_summary.csv",
    index=False,
    sep=";",
    encoding="utf-8-sig"
)

profile_df.to_csv(
    output_dir / "column_profile.csv",
    index=False,
    sep=";",
    encoding="utf-8-sig"
)

print("\n========== RESULTADO ==========")
print(summary_df.to_string(index=False))
print("\nInformes guardados en:", output_dir)