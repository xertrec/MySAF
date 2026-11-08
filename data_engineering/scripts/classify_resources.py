
import pandas as pd
import unicodedata
from pathlib import Path


# =====================================================
# 1. RUTAS
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = (
        BASE_DIR / "data/interim/analysis/resource_distribution.csv"
)

OUTPUT_DIR = BASE_DIR / "data/interim/analysis"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "resource_classification.csv"


# =====================================================
# 2. NORMALIZAR TEXTOS
# =====================================================

def normalize(text):
    text = str(text).upper().strip()
    text = unicodedata.normalize("NFKD", text)

    return "".join(
        char for char in text
        if not unicodedata.combining(char)
    )


# =====================================================
# 3. CLASIFICAR RECURSOS
# =====================================================

def classify_resource(resource):

    text = normalize(resource)

    if "VESTIDORS" in text:
        return "servicios"

    if any(word in text for word in [
        "FITNES",
        "BARBELL",
        "BOXTRAINING"
    ]):
        return "fitness"

    # Piscinas: comprobar el nombre del recurso,
    # no solamente el espacio principal.
    if any(word in text for word in [
        "PISCINA",
        "PISCINES",
        "P. 25M",
        "P. 16M",
        "MEITAT A",
        "MEITAT B"
    ]):
        return "piscina"

    if any(word in text for word in [
        "AADD",
        "CYCLING",
        "RITMES",
        "ZEN"
    ]):
        return "actividades_dirigidas"

    if any(word in text for word in [
        "ROCODROM",
        "CAL.LISTENIA",
        "CALISTENIA"
    ]):
        return "espacios_deportivos"

    # Básquet y vóley antes de buscar la palabra PISTA.
    if any(word in text for word in [
        "BASQUET",
        "VOLEI"
    ]):
        return "deportes_colectivos"

    if any(word in text for word in [
        "FUTBOL",
        "RUGBI",
        "CAMPS EXTERIORS"
    ]):
        return "campos_deportivos"

    if any(word in text for word in [
        "PADEL",
        "TENNIS",
        "PIKLEBALL",
        "BADMINTON",
        "ESQUAIX",
        "PISTA"
    ]):
        return "pistas_deportivas"

    return "pendiente_revision"


# =====================================================
# 4. ASIGNAR MÉTRICA
# =====================================================

def classify_metric(category):

    # Salas y piscinas: personas.
    if category in [
        "fitness",
        "piscina",
        "actividades_dirigidas"
    ]:
        return "personas", "personas"

    # Pistas y campos: recurso ocupado o libre.
    if category in [
        "pistas_deportivas",
        "campos_deportivos",
        "deportes_colectivos"
    ]:
        return "ocupacion_recurso", "ocupada_libre"

    return "pendiente_validacion", "pendiente_validacion"


# =====================================================
# 5. LEER Y VALIDAR DATOS
# =====================================================

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"No se encuentra: {INPUT_FILE}"
    )

df = pd.read_csv(INPUT_FILE, sep=";")

required_columns = [
    "EspaiPare",
    "Recurs",
    "total_registros",
    "fechas_distintas",
    "horas_distintas"
]

missing_columns = [
    column for column in required_columns
    if column not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Faltan columnas: {missing_columns}"
    )

if len(df) != 118:
    raise ValueError(
        f"Se esperaban 118 recursos y hay {len(df)}."
    )

if df.duplicated(
        subset=["EspaiPare", "Recurs"]
).any():
    raise ValueError(
        "Existen combinaciones espacio-recurso duplicadas."
    )


# =====================================================
# 6. APLICAR CLASIFICACIÓN
# =====================================================

df["categoria"] = df["Recurs"].apply(classify_resource)

metric_results = df["categoria"].apply(classify_metric)

df["tipo_metrica"] = metric_results.apply(
    lambda x: x[0]
)

df["unidad"] = metric_results.apply(
    lambda x: x[1]
)


# =====================================================
# 7. ESTADO DE VALIDACIÓN
# =====================================================

df["requiere_validacion"] = "Sí"
df["observaciones"] = ""

df.loc[
    df["categoria"] == "pendiente_revision",
    "observaciones"
] = "Categoría pendiente de revisión"

df.loc[
    df["tipo_metrica"] == "pendiente_validacion",
    "observaciones"
] = "Métrica pendiente de validación"


# =====================================================
# 8. GUARDAR CSV
# =====================================================

df = df.sort_values(
    ["categoria", "EspaiPare", "Recurs"]
)

df.to_csv(
    OUTPUT_FILE,
    index=False,
    sep=";",
    encoding="utf-8-sig"
)


# =====================================================
# 9. MOSTRAR RESULTADOS
# =====================================================

print("\n========== CLASIFICACIÓN DE RECURSOS ==========\n")
print(df["categoria"].value_counts().to_string())

print("\n========== TIPO DE MÉTRICA ==========\n")
print(df["tipo_metrica"].value_counts().to_string())

print("\n========== RECURSOS PENDIENTES ==========\n")

pending = df[
    (df["categoria"] == "pendiente_revision")
    | (df["tipo_metrica"] == "pendiente_validacion")
    ]

if pending.empty:
    print("Ninguno")
else:
    print(
        pending[
            ["EspaiPare", "Recurs", "categoria", "tipo_metrica"]
        ].to_string(index=False)
    )

print("\n========== RESULTADO FINAL ==========")
print("Total de recursos:", len(df))
print("Archivo generado:", OUTPUT_FILE)

print("\nClasificación completada correctamente.")
