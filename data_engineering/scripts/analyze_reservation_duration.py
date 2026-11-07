
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

input_file = BASE_DIR / "data/raw/saf-espais-2026-equips.xlsx"

df = pd.read_excel(input_file, sheet_name="Reserves")

print("\n========== ESTADÍSTICAS DE DURACIÓN ==========")

print(df["DuradaMin"].describe())

print("\n========== DURACIONES MÁS FRECUENTES ==========")

print(
    df["DuradaMin"]
    .value_counts()
    .head(20)
    .to_string()
)

print("\n========== DURACIÓN POR CATEGORÍA ==========")

classification_file = (
        BASE_DIR
        / "data/interim/analysis/resource_classification.csv"
)

classification = pd.read_csv(classification_file, sep=";")

df = df.merge(
    classification[["Recurs", "categoria"]].drop_duplicates(),
    on="Recurs",
    how="left"
)

print(
    df.groupby("categoria")["DuradaMin"]
    .agg(["count", "mean", "median", "min", "max"])
    .round(2)
    .to_string()
)
