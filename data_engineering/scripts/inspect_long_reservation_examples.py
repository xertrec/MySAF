
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

input_file = (
        BASE_DIR
        / "data/interim/analysis/long_reservations.csv"
)

df = pd.read_csv(input_file, sep=";")

print("\n========== 25 RESERVAS MÁS LARGAS ==========\n")

columns = [
    "EspaiPare",
    "Recurs",
    "DataUs",
    "DiaSetmana",
    "HoraInici",
    "HoraFi",
    "DuradaMin"
]

print(
    df.sort_values("DuradaMin", ascending=False)
    [columns]
    .head(25)
    .to_string(index=False)
)

print("\n========== RESERVAS DE 8 HORAS O MÁS ==========\n")

very_long = df[df["DuradaMin"] >= 480]

print("Total:", len(very_long))

print(
    very_long.groupby(["EspaiPare", "Recurs"])
    .size()
    .sort_values(ascending=False)
    .head(15)
    .to_string()
)

print("\n========== INTERVALOS REPETIDOS ==========\n")

keys = [
    "EspaiPare",
    "Recurs",
    "DataUs",
    "HoraInici",
    "HoraFi",
    "DuradaMin"
]

repeated = (
    df.groupby(keys)
    .size()
    .reset_index(name="repeticiones")
)

repeated = repeated[repeated["repeticiones"] > 1]

print("Intervalos repetidos:", len(repeated))

print(
    repeated.sort_values("repeticiones", ascending=False)
    .head(15)
    .to_string(index=False)
)
