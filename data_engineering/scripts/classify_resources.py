
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

input_file = BASE_DIR / "data/interim/analysis/resource_distribution.csv"

output_dir = BASE_DIR / "data/interim/analysis"
output_dir.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(input_file, sep=";")


def classify_resource(resource):
    text = str(resource).upper()

    if "FITNES" in text or "BARBELL" in text or "BOXTRAINING" in text:
        return "fitness"

    if "PISCINA" in text or "PISCINES" in text or "P. 25M" in text or "P. 16M" in text:
        return "piscina"

    if "AADD" in text or "CYCLING" in text or "RITMES" in text or "ZEN" in text:
        return "actividades_dirigidas"

    if any(x in text for x in ["PÀDEL", "PADEL", "TENNIS", "PIKLEBALL", "BÀDMINTON", "ESQUAIX"]):
        return "pistas_deportivas"

    if any(x in text for x in ["FUTBOL", "RUGBI"]):
        return "campos_deportivos"

    if any(x in text for x in ["BÀSQUET", "VÒLEI", "VOLEI"]):
        return "deportes_colectivos"

    if any(x in text for x in ["ROCÒDROM", "CAL·LISTÈNIA", "CALISTÈNIA", "CAL.LISTÈNIA"]):
        return "espacios_deportivos"

    if "VESTIDORS" in text:
        return "servicios"

    return "pendiente_revision"


df["categoria"] = df["Recurs"].apply(classify_resource)

df["tipo_metrica"] = "pendiente_validacion"
df["unidad"] = "pendiente_validacion"
df["requiere_validacion"] = "Sí"
df["observaciones"] = ""

# Guardar el resultado
output_file = output_dir / "resource_classification.csv"

df.to_csv(
    output_file,
    index=False,
    sep=";",
    encoding="utf-8-sig"
)

# Mostrar resumen
print("\n========== RESUMEN DE CLASIFICACIÓN ==========\n")
print(df["categoria"].value_counts().to_string())

print("\n========== RECURSOS PENDIENTES ==========\n")
pending = df[df["categoria"] == "pendiente_revision"]

if pending.empty:
    print("Ninguno")
else:
    print(pending[["EspaiPare", "Recurs"]].to_string(index=False))

print(f"\nTotal de recursos: {len(df)}")
print(f"Archivo generado: {output_file}")
