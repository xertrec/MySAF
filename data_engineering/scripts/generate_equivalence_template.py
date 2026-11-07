
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

EXCEL_FILE = BASE_DIR / "data/raw/saf-espais-2026-equips.xlsx"

CLASSIFICATION_FILE = (
        BASE_DIR / "data/interim/analysis/resource_classification.csv"
)

OUTPUT_DIR = BASE_DIR / "data/interim/mapping"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Leer datos originales
reservations = pd.read_excel(
    EXCEL_FILE,
    sheet_name="Reserves"
)

inventory = pd.read_excel(
    EXCEL_FILE,
    sheet_name="Espais"
)

classification = pd.read_csv(
    CLASSIFICATION_FILE,
    sep=";"
)

# Generar un resumen de cada combinación espacio-recurso
resources = (
    reservations.groupby(["EspaiPare", "Recurs"])
    .agg(
        total_reservas=("Recurs", "size"),
        fechas_distintas=("DataUs", "nunique"),
        horas_distintas=("HoraInici", "nunique"),
        reservas_mas_4h=(
            "DuradaMin",
            lambda x: (x > 240).sum()
        )
    )
    .reset_index()
)

# Añadir la clasificación existente
resources = resources.merge(
    classification[
        ["EspaiPare", "Recurs", "categoria"]
    ],
    on=["EspaiPare", "Recurs"],
    how="left",
    validate="one_to_one"
)

# Añadir campos para revisión manual
resources["espai_inventari"] = ""
resources["subespai_inventari"] = ""
resources["id_recurs_fisic"] = ""
resources["tipus_calendari"] = ""
resources["tipus_mesura"] = ""
resources["estat_validacio"] = "pendent"
resources["observacions"] = ""

resources = resources.sort_values(
    ["categoria", "EspaiPare", "Recurs"]
)

# Guardar plantilla principal
resources.to_csv(
    OUTPUT_DIR / "resource_equivalence_template.csv",
    index=False,
    sep=";",
    encoding="utf-8-sig"
)

# Exportar inventario como referencia independiente
inventory.to_csv(
    OUTPUT_DIR / "inventory_reference.csv",
    index=False,
    sep=";",
    encoding="utf-8-sig"
)

print("\n========== PLANTILLAS GENERADAS ==========")
print("Recursos:", len(resources))
print("Registros del inventario:", len(inventory))

print("\nArchivos:")
print(OUTPUT_DIR / "resource_equivalence_template.csv")
print(OUTPUT_DIR / "inventory_reference.csv")

print("\nNo se han modificado los Excel originales.")
