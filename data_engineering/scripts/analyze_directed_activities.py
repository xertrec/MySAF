
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

input_file = BASE_DIR / "data/raw/saf-espais-2026-equips.xlsx"

df = pd.read_excel(
    input_file,
    sheet_name="Activitats dirigides"
)

print("\n========== INFORMACIÓN GENERAL ==========")
print("Total registros:", len(df))
print("Fechas distintas:", df["DataInscripcio"].nunique())
print("Fecha mínima:", df["DataInscripcio"].min())
print("Fecha máxima:", df["DataInscripcio"].max())
print("Códigos de actividad:", df["CodiActivitat"].nunique())

print("\n========== DUPLICADOS EXACTOS ==========")
print("Filas duplicadas:", df.duplicated().sum())

# Buscar posibles registros de una misma actividad
# con la misma fecha, hora y sala.
keys = [
    "DataInscripcio",
    "CodiActivitat",
    "Activitat",
    "HoraInici",
    "HoraFi",
    "Sala"
]

groups = (
    df.groupby(keys, dropna=False)
    .agg(
        numero_registros=("Inscrits", "size"),
        inscritos_distintos=("Inscrits", "nunique"),
        aforos_distintos=("AforamentMax", "nunique"),
        porcentajes_distintos=("PctOcupacio", "nunique"),
        inscritos_min=("Inscrits", "min"),
        inscritos_max=("Inscrits", "max"),
        aforo=("AforamentMax", "max")
    )
    .reset_index()
)

print("\n========== GRUPOS DE ACTIVIDAD ==========")
print("Grupos identificados:", len(groups))
print(
    "Grupos con varios valores de inscritos:",
    (groups["inscritos_distintos"] > 1).sum()
)

print("\n========== EJEMPLOS CON INSCRITOS DIFERENTES ==========")

varying = groups[groups["inscritos_distintos"] > 1]

print(
    varying.head(20).to_string(index=False)
)

print("\n========== INSCRITOS POR ENCIMA DEL AFORO ==========")

excess = df[df["Inscrits"] > df["AforamentMax"]]

print("Registros que superan el aforo:", len(excess))

print(
    excess[
        ["DataInscripcio", "CodiActivitat", "Activitat",
         "AforamentMax", "Inscrits", "HoraInici", "HoraFi", "Sala"]
    ].head(15).to_string(index=False)
)

print("\n========== VALIDACIÓN DEL PORCENTAJE ==========")

df["pct_calculado"] = (
        df["Inscrits"] / df["AforamentMax"] * 100
).round()

different_pct = df[df["pct_calculado"] != df["PctOcupacio"]]

print("Porcentajes diferentes:", len(different_pct))

print("\n========== ACTIVIDADES POR CÓDIGO ==========")

print(
    df.groupby("CodiActivitat")["Activitat"]
    .nunique()
    .sort_values(ascending=False)
    .head(15).to_string()
)

print("\nANÁLISIS COMPLETADO.")
