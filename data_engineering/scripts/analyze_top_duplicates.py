import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

input_file = (
        BASE_DIR
        / "data/interim/duplicates/reserves_duplicates.csv"
)

output_file = (
        BASE_DIR
        / "data/interim/duplicates/reserves_top_20.csv"
)

df = pd.read_csv(input_file, sep=";")

top_20 = (
    df.sort_values("frequency", ascending=False)
    .head(20)
)

top_20.to_csv(
    output_file,
    index=False,
    sep=";",
    encoding="utf-8-sig"
)

print("\n========== TOP 20 DUPLICADOS ==========")
print(top_20.to_string(index=False))

print(f"\nInforme guardado en: {output_file}")