# scripts/debug/audit_mapping.py
import pandas as pd
from pathlib import Path
BASE = Path(__file__).resolve().parents[2]
df = pd.read_csv(BASE / "data/interim/analysis/resource_classification.csv", sep=";")

# ¿Qué recursos NO están en padel/pool?
mask_known = df["Recurs"].str.contains(
    r"PÀDEL|PADEL|P\. 25M|P\. 16M|MEITAT", case=False, regex=True
)
print("Recursos sin mapeo físico:")
print(df.loc[~mask_known, ["EspaiPare", "Recurs", "categoria"]].to_string())
print("Total sin mapeo:", (~mask_known).sum())