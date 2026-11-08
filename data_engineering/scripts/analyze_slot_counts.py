
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

slots_file = BASE_DIR / "data/raw/saf-espais-2026-equips.xlsx"
classification_file = (
        BASE_DIR / "data/interim/analysis/resource_classification.csv"
)

output_dir = BASE_DIR / "data/interim/analysis"
output_dir.mkdir(parents=True, exist_ok=True)

# Leer los datos
slots = pd.read_excel(
    slots_file,
    sheet_name="Reserves per franja"
)

classification = pd.read_csv(
    classification_file,
    sep=";"
)

# Comprobar que cada combinación espacio-recurso
# tiene una única clasificación
keys = ["EspaiPare", "Recurs"]

if classification.duplicated(subset=keys).any():
    raise ValueError(
        "Hay combinaciones EspaiPare + Recurs duplicadas "
        "en la clasificación."
    )

# Unir utilizando las dos columnas, no solo Recurs
df = slots.merge(
    classification[keys + ["categoria"]],
    on=keys,
    how="left",
    validate="many_to_one"
)

if df["categoria"].isna().any():
    print("ATENCIÓN: hay recursos sin clasificar.")
    print(
        df[df["categoria"].isna()][keys]
        .drop_duplicates()
        .to_string(index=False)
    )

# Resumen por categoría
category_summary = (
    df.groupby("categoria")
    .agg(
        total_franjas=("Reserves", "size"),
        total_registros=("Reserves", "sum"),
        media_registros=("Reserves", "mean"),
        mediana_registros=("Reserves", "median"),
        maximo_registros=("Reserves", "max"),
        franjas_con_varios_registros=(
            "Reserves",
            lambda x: (x > 1).sum()
        )
    )
    .round(2)
    .reset_index()
)

# Resumen por recurso concreto
resource_summary = (
    df.groupby(keys + ["categoria"])
    .agg(
        total_franjas=("Reserves", "size"),
        total_registros=("Reserves", "sum"),
        maximo_por_franja=("Reserves", "max"),
        franjas_con_varios_registros=(
            "Reserves",
            lambda x: (x > 1).sum()
        )
    )
    .reset_index()
    .sort_values("maximo_por_franja", ascending=False)
)

# Guardar resultados
category_summary.to_csv(
    output_dir / "slot_counts_by_category.csv",
    index=False,
    sep=";",
    encoding="utf-8-sig"
)

resource_summary.to_csv(
    output_dir / "slot_counts_by_resource.csv",
    index=False,
    sep=";",
    encoding="utf-8-sig"
)

print("\n========== RESUMEN POR CATEGORÍA ==========\n")
print(category_summary.to_string(index=False))

print("\n========== TOP 20 RECURSOS ==========\n")
print(resource_summary.head(20).to_string(index=False))

print("\nTotal de franjas:", len(df))
print("Total de registros:", df["Reserves"].sum())
print("\nInformes guardados correctamente.")
