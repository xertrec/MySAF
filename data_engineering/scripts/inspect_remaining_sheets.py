
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

input_file = BASE_DIR / "data/raw/saf-espais-2026-equips.xlsx"

sheets = [
    "Espais",
    "Horari general",
    "Activitats dirigides"
]

for sheet_name in sheets:

    print("\n" + "=" * 65)
    print(f"HOJA: {sheet_name}")
    print("=" * 65)

    df = pd.read_excel(
        input_file,
        sheet_name=sheet_name
    )

    print("\nNúmero de filas:", len(df))
    print("Número de columnas:", len(df.columns))

    print("\nCOLUMNAS:")
    print(df.columns.tolist())

    print("\nTIPOS DE DATOS:")
    print(df.dtypes.to_string())

    print("\nVALORES VACÍOS:")
    print(df.isna().sum().to_string())

    print("\nPRIMERAS 10 FILAS:")
    print(df.head(10).to_string(index=False))

print("\n\nINSPECCIÓN COMPLETADA.")
