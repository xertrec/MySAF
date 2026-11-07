import pandas as pd
from pathlib import Path

# Directorios del proyecto
BASE_DIR = Path(__file__).resolve().parents[1]

input_file = BASE_DIR / "data" / "raw" / "saf-espais-2026-equips.xlsx"
output_file = BASE_DIR / "data" / "interim" / "resource_mapping_template.csv"

# Comprobar que existe el Excel
if not input_file.exists():
    raise FileNotFoundError(f"No se encuentra el archivo: {input_file}")

# Leer la hoja Reserves
df = pd.read_excel(input_file, sheet_name="Reserves")

# Comprobar las columnas necesarias
required_columns = ["EspaiPare", "Recurs"]

if not all(col in df.columns for col in required_columns):
    raise ValueError("Faltan columnas necesarias en la hoja Reserves")

# Extraer combinaciones únicas
mapping = df[required_columns].drop_duplicates().copy()

# Ordenar
mapping = mapping.sort_values(
    ["EspaiPare", "Recurs"],
    na_position="last"
)

# Añadir campos para validar las equivalencias
mapping["espai_canonico"] = ""
mapping["subespai_canonico"] = ""
mapping["tipo_recurso"] = ""
mapping["unidad_metrica"] = ""
mapping["estado_validacion"] = "PENDIENTE"
mapping["notas"] = ""

# Crear directorio de salida
output_file.parent.mkdir(parents=True, exist_ok=True)

# Exportar CSV
mapping.to_csv(
    output_file,
    index=False,
    sep=";",
    encoding="utf-8-sig"
)

print("Plantilla de equivalencias generada correctamente.")
print(f"Combinaciones espacio-recurso: {len(mapping)}")
print(f"Recursos distintos: {mapping['Recurs'].nunique()}")
print(f"Archivo guardado en: {output_file}")