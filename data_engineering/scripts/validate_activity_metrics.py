
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

input_file = BASE_DIR / "data/raw/saf-espais-2026-equips.xlsx"
output_dir = BASE_DIR / "data/interim/analysis"
output_dir.mkdir(parents=True, exist_ok=True)

df = pd.read_excel(
    input_file,
    sheet_name="Activitats dirigides"
)

# 1. Comparar las fórmulas posibles del porcentaje
valid = df["AforamentMax"] > 0
df = df[valid].copy()

percentage = (
        df["Inscrits"] / df["AforamentMax"] * 100
)

df["pct_truncado"] = np.floor(percentage).astype(int)
df["pct_redondeado"] = percentage.round().astype(int)

print("\n========== VALIDACIÓN DE PORCENTAJES ==========")

print(
    "Diferencias con truncamiento:",
    (df["pct_truncado"] != df["PctOcupacio"]).sum()
)

print(
    "Diferencias con redondeo:",
    (df["pct_redondeado"] != df["PctOcupacio"]).sum()
)

# 2. Comprobar duplicados exactos
print("\n========== DUPLICADOS ==========")

print("Filas originales:", len(df))
print("Filas distintas:", len(df.drop_duplicates()))
print("Repeticiones exactas:", df.duplicated().sum())

# 3. Analizar grupos con distintos valores de inscritos
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
        valores_inscritos=("Inscrits", "nunique"),
        inscritos_min=("Inscrits", "min"),
        inscritos_max=("Inscrits", "max"),
        aforo=("AforamentMax", "max")
    )
    .reset_index()
)

varying = groups[groups["valores_inscritos"] > 1].copy()

varying.to_csv(
    output_dir / "activity_groups_with_different_enrollment.csv",
    index=False,
    sep=";",
    encoding="utf-8-sig"
)

print("\n========== GRUPOS CON INSCRITOS DIFERENTES ==========")
print("Total:", len(varying))

print(
    varying.head(10).to_string(index=False)
)

# 4. Anomalías de aforo, contando grupos y filas
excess = df[df["Inscrits"] > df["AforamentMax"]]

print("\n========== EXCESOS DE AFORO ==========")
print("Filas:", len(excess))
print("Grupos distintos:", excess.groupby(keys).ngroups)

print("\nAnálisis completado.")
print(
    "Informe guardado en:",
    output_dir / "activity_groups_with_different_enrollment.csv"
)

