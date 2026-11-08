
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

input_file = BASE_DIR / "data/raw/saf-espais-2026-equips.xlsx"

df = pd.read_excel(
    input_file,
    sheet_name="Reserves per franja"
)

print("\n========== COLUMNAS ==========")
print(df.columns.tolist())

print("\n========== PRIMERAS 15 FILAS ==========")
print(df.head(15).to_string(index=False))

print("\n========== TIPOS DE DATOS ==========")
print(df.dtypes)

print("\n========== VALORES VACÍOS ==========")
print(df.isna().sum())

print("\n========== NÚMERO DE REGISTROS ==========")
print(len(df))
