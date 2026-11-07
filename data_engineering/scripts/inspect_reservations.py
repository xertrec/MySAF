
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

input_file = BASE_DIR / "data/raw/saf-espais-2026-equips.xlsx"

df = pd.read_excel(input_file, sheet_name="Reserves")

print("\n========== COLUMNAS ==========")
print(df.columns.tolist())

print("\n========== PRIMERAS 10 FILAS ==========")
print(df.head(10).to_string(index=False))

print("\n========== TIPOS DE DATOS ==========")
print(df.dtypes)

print("\n========== HORAS DE INICIO ==========")
print(sorted(df["HoraInici"].dropna().astype(str).unique()))

print("\n========== HORAS DE FIN ==========")
print(sorted(df["HoraFi"].dropna().astype(str).unique()))

print("\n========== FECHAS ==========")
print("Fecha mínima:", df["DataUs"].min())
print("Fecha máxima:", df["DataUs"].max())
print("Fechas distintas:", df["DataUs"].nunique())
