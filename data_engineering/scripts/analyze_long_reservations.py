
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

input_file = BASE_DIR / "data/raw/saf-espais-2026-equips.xlsx"

output_dir = BASE_DIR / "data/interim/analysis"
output_dir.mkdir(parents=True, exist_ok=True)

df = pd.read_excel(input_file, sheet_name="Reserves")

# Filtrar reservas superiores a 4 horas
long_reservations = df[df["DuradaMin"] > 240].copy()

# Resumen por recurso
summary = (
    long_reservations
    .groupby(["EspaiPare", "Recurs"])
    .agg(
        total_reservas=("DuradaMin", "size"),
        duracion_media=("DuradaMin", "mean"),
        duracion_maxima=("DuradaMin", "max")
    )
    .reset_index()
    .sort_values("total_reservas", ascending=False)
)

output_file = output_dir / "long_reservations.csv"

long_reservations.to_csv(
    output_file,
    index=False,
    sep=";",
    encoding="utf-8-sig"
)

print("\n========== RESERVAS DE MÁS DE 4 HORAS ==========")
print("Total de registros:", len(long_reservations))

print("\n========== RECURSOS CON MÁS RESERVAS LARGAS ==========")
print(summary.head(20).to_string(index=False))

print(f"\nArchivo guardado en: {output_file}")
