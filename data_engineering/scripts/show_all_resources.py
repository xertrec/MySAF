
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

input_file = (
        BASE_DIR
        / "data/interim/analysis/resource_distribution.csv"
)

df = pd.read_csv(input_file, sep=";")

print("\n========== LISTADO COMPLETO DE RECURSOS ==========\n")

for i, row in df.iterrows():
    print(
        f"{i + 1:03d}. "
        f"{row['EspaiPare']} | {row['Recurs']}"
    )

print(f"\nTotal de recursos: {len(df)}")
