
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

input_file = (
        BASE_DIR
        / "data/interim/analysis/resource_distribution.csv"
)

output_dir = BASE_DIR / "data/interim/analysis"
output_dir.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(input_file, sep=";")

# Columnas que rellenaremos manualmente
df["categoria"] = ""
df["tipo_metrica"] = ""
df["unidad"] = ""
df["requiere_validacion"] = "Sí"
df["observaciones"] = ""

output_file = output_dir / "resource_classification_template.csv"

df.to_csv(
    output_file,
    index=False,
    sep=";",
    encoding="utf-8-sig"
)

print("Plantilla de clasificación generada correctamente.")
print(f"Total de recursos: {len(df)}")
print(f"Archivo: {output_file}")
