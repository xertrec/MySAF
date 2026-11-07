
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

input_file = (
        BASE_DIR
        / "data/raw/saf-espais-2026-equips.xlsx"
)

output_dir = BASE_DIR / "data/interim/analysis"
output_dir.mkdir(parents=True, exist_ok=True)

df = pd.read_excel(
    input_file,
    sheet_name="Reserves"
)

# Número de registros por recurso
resource_summary = (
    df.groupby(["EspaiPare", "Recurs"])
    .agg(
        total_registros=("Recurs", "size"),
        fechas_distintas=("DataUs", "nunique"),
        horas_distintas=("HoraInici", "nunique")
    )
    .reset_index()
    .sort_values("total_registros", ascending=False)
)

output_file = output_dir / "resource_distribution.csv"

resource_summary.to_csv(
    output_file,
    index=False,
    sep=";",
    encoding="utf-8-sig"
)

print("\n========== TOP 20 RECURSOS ==========")
print(resource_summary.head(20).to_string(index=False))

print(f"\nTotal de recursos: {len(resource_summary)}")
print(f"Informe guardado en: {output_file}")
