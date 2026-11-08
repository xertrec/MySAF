"""
02_build_resource_alias.py

Lee data/interim/analysis/resource_classification.csv (118 filas)
y genera data/interim/mapping/resource_alias.csv con:
- resource_id canónico
- parent_resource_id (jerarquía padre/hijo)
- fraction_of_parent (para mitades, subdivisiones)
- metric_type (personas vs unidad_recurso)
- calendar_label (dl-dv / ds-dg)
- time_segment (fins_18_30 / desde_18_30)
- mapping_status (regla_documentada / pendiente_validacion)

No borra filas. Lo que no matchea queda como pendiente_validacion con nota.
"""
import re
import unicodedata
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
INPUT = BASE / "data/interim/analysis/resource_classification.csv"
OUT = BASE / "data/interim/mapping"
OUT.mkdir(parents=True, exist_ok=True)


def norm(s):
    s = str(s).upper().strip()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("DSS-DG", "DS-DG")
    return s


def cal(r):
    if "DS-DG" in r:
        return "ds-dg"
    if "DL-DV" in r:
        return "dl-dv"
    return None


def seg(f):
    if "FINS" in f and "18.30" in f:
        return "fins_18_30"
    if "A PARTIR" in f and "18.30" in f:
        return "desde_18_30"
    return None


def _mk(rid, rname, kind, metric, cap, parent=None, frac=None,
        seg_=None, status="regla_documentada", notes=""):
    return dict(
        resource_id=rid, resource_name=rname, resource_kind=kind,
        metric_type=metric, capacity_units=cap,
        parent_resource_id=parent, fraction_of_parent=frac,
        time_segment=seg_, mapping_status=status, notes=notes,
    )


# ---------- reglas (orden: específico → genérico) ----------

def r_padel(p, r, f):
    m = re.search(r"PADEL.*PISTA\s*(\d+)", f)
    if not m:
        return None
    return _mk(f"PADEL_PISTA_{m.group(1)}", f"Padel pista {m.group(1)}",
               "pista", "unidad_recurso", 1.0, seg_=seg(f))


def r_piscina_25_carril(p, r, f):
    m = re.search(r"P\.\s*25M-\s*C\s*/\s*(\d+)", f)
    if not m:
        return None
    return _mk(f"PISCINA_25M_CARRER_{m.group(1)}",
               f"Piscina 25m carrer {m.group(1)}",
               "carrer", "personas", 5.0,
               parent="PISCINA_25M_COBERTA", frac=1 / 8)


def r_piscina_25_contenedor(p, r, f):
    if "P. 25M" in f or "P.25M" in f:
        return None
    if "PISCINES" in f and "SOLARIUM" in f:
        return _mk("PISCINA_25M_SOLARIUM", "Piscines i solarium",
                   "bundle", "pendiente", None,
                   status="pendiente_validacion",
                   notes="Solo 2 filas. Bundle piscina+solarium.")
    if "PISCINA" in f and "25" in f and "COBERTA" in f:
        return _mk("PISCINA_25M_COBERTA", "Piscina 25m coberta",
                   "piscina", "personas", 40.0,
                   notes="Contenedor de 8 calles x 5 pax.")
    return None


def r_piscina_16(p, r, f):
    if "16M" not in f and "16 M" not in f:
        return None
    if "MEITAT A" in f:
        return _mk("PISCINA_16M_MEITAT_A", "Piscina 16m meitat A",
                   "meitat_piscina", "personas", None,
                   parent="PISCINA_16M_COMPLETA", frac=0.5)
    if "MEITAT B" in f:
        return _mk("PISCINA_16M_MEITAT_B", "Piscina 16m meitat B",
                   "meitat_piscina", "personas", None,
                   parent="PISCINA_16M_COMPLETA", frac=0.5)
    return _mk("PISCINA_16M_COMPLETA", "Piscina 16m completa",
               "piscina", "personas", None)


def r_tenis(p, r, f):
    if "TENNIS/PIKLEBALL" not in f:
        return None
    m = re.search(r"PISTA\s*(\d+)", f)
    if not m:
        return None
    return _mk(f"TENIS_PISTA_{m.group(1)}",
               f"Tennis/pickleball pista {m.group(1)}",
               "pista", "unidad_recurso", 1.0)


def r_futbol7(p, r, f):
    if "FUTBOL 7" not in f:
        return None
    mh = re.search(r"CAMP\s*(\d+)\.(\d+)\s*\(1/2 CAMP\)", f)
    if mh:
        n, k = mh.group(1), mh.group(2)
        return _mk(f"FUTBOL7_CAMP_{n}_MITAT_{k}",
                   f"Futbol 7 camp {n} meitat {k}",
                   "meitat_camp", "unidad_recurso", 0.5,
                   parent=f"FUTBOL7_CAMP_{n}", frac=0.5)
    m = re.search(r"CAMP\s*(\d+)", f)
    if m:
        return _mk(f"FUTBOL7_CAMP_{m.group(1)}",
                   f"Futbol 7 camp {m.group(1)}",
                   "camp", "unidad_recurso", 1.0)
    return None


def r_futbol_sala(p, r, f):
    if "FUTBOL SALA 1" in f:
        return _mk("FUTBOL_SALA_1", "Futbol sala 1",
                   "camp", "unidad_recurso", 1.0)
    return None


def r_camps_exteriors_reservables(p, r, f):
    # Fix: "CAMPS EXTERIORS" como RECURSO reservable (no como padre)
    if "CAMPS EXTERIORS" in r and "SAF 1- POLIESPORTIU" in p:
        return _mk("CAMPS_EXTERIORS", "Camps exteriors",
                   "camp", "unidad_recurso", 1.0)
    return None


def r_esquaix(p, r, f):
    m = re.search(r"ESQUAIX/C\.SOCCER-?\s*PISTA\s*(\d+)", f)
    if not m:
        return None
    return _mk(f"ESQUAIX_PISTA_{m.group(1)}",
               f"Esquaix pista {m.group(1)}",
               "pista", "unidad_recurso", 1.0)


def r_badminton(p, r, f):
    if "BADMINTON" not in f:
        return None
    mh = re.search(r"PISTA\s*(\d+)\.(\d+)\s*PAVELLO", f)
    if mh:
        n, k = mh.group(1), mh.group(2)
        return _mk(f"PAVELLO_BADMINTON_{n}_SUB_{k}",
                   f"Badminton pista {n}.{k}",
                   "subdivisio_pista", "unidad_recurso", 1 / 3,
                   parent=f"PAVELLO_BADMINTON_{n}", frac=1 / 3,
                   notes="3 subdivisiones por pista.")
    m = re.search(r"PISTA\s*(\d+)", f)
    if m:
        return _mk(f"PAVELLO_BADMINTON_{m.group(1)}",
                   f"Badminton pista {m.group(1)} pavello",
                   "pista", "unidad_recurso", 1.0)
    return None


def r_basquet_volei_pavello(p, r, f):
    # Hijos: "BÀSQUET- N.K PAVELLÓ (1/2 PISTA)"
    mh = re.search(r"BASQUET-\s*(\d+)\.(\d+)\s*PAVELLO", f)
    if mh:
        n, k = mh.group(1), mh.group(2)
        return _mk(f"PAVELLO_PISTA_{n}_MITAT_{k}",
                   f"Pista {n} pavello meitat {k}",
                   "meitat_pista", "unidad_recurso", 0.5,
                   parent=f"PAVELLO_PISTA_{n}", frac=0.5)
    # Fix: aceptar "BÀSQUET/VÒLEI - PISTA N" y "BÀSQUET/VÒLEI- PISTA N"
    m = re.search(r"BASQUET/VOLEI\s*-?\s*PISTA\s*(\d+)\s*PAVELLO", f)
    if m:
        return _mk(f"PAVELLO_PISTA_{m.group(1)}",
                   f"Pista {m.group(1)} pavello",
                   "pista", "unidad_recurso", 1.0)
    return None


def r_basquet_exterior(p, r, f):
    if "BASQUET - PISTA EXTERIOR" in f or "BASQUET EXTERIOR" in f:
        return _mk("BASQUET_EXTERIOR", "Basquet exterior",
                   "pista", "unidad_recurso", 1.0)
    return None


def r_aadd_pista(p, r, f):
    if "AADD- PISTA PAVELLO" in f:
        return _mk("AADD_PISTA_PAVELLO", "AADD pista pavello",
                   "aadd", "personas", None)
    return None


def r_aadd_fora(p, r, f):
    if "AADD- ESPAIS FORA SAF" in f:
        return _mk("AADD_FORA_SAF", "AADD espais fora SAF",
                   "aadd", "pendiente", None,
                   status="pendiente_validacion",
                   notes="Espacio fuera del SAF. Como se cuenta?")
    return None


def r_aadd_sala(p, r, f):
    if "AADD" not in f:
        return None
    m = re.search(r"AADD-?\s*SALA\s*(\d)\s*[- ]\s*(RITMES|ZEN)", f)
    if not m:
        return None
    n, kind = m.group(1), m.group(2)
    return _mk(f"AADD_SALA_{n}_{kind}", f"AADD sala {n} {kind.lower()}",
               "aadd", "personas", None)


def r_aadd_espaibarbell(p, r, f):
    if "AADD" in f and "ESPAI BARBELL" in f:
        return _mk("AADD_ESPAI_BARBELL", "AADD espai barbell",
                   "aadd", "personas", None)
    return None


def r_espaibarbell(p, r, f):
    if "ESPAI BARBELL" in f:
        return _mk("ESPAI_BARBELL", "Espai barbell",
                   "sala", "personas", None)
    return None


def r_salafitnes(p, r, f):
    if "SALA FITNES" in f:
        return _mk("SALA_FITNES", "Sala fitness",
                   "sala", "personas", 120.0)
    return None


def r_sala4cycl(p, r, f):
    if re.search(r"SALA\s*4[- ]\s*CYCLING", f):
        return _mk("SALA_4_CYCLING", "Sala 4 cycling",
                   "sala", "personas", None)
    return None


def r_sala6box(p, r, f):
    if "SALA 6" in f and "BOXTRAINING" in f:
        return _mk("SALA_6_BOXTRAINING", "Sala 6 box training",
                   "sala", "personas", None)
    return None


def r_calistenia(p, r, f):
    if "CAL.LISTENIA" in f or "CALISTENIA" in f:
        return _mk("CALISTENIA", "Calistenia",
                   "espai", "pendiente", None,
                   status="pendiente_validacion",
                   notes="Metrica no validada.")
    return None


def r_rocodrom(p, r, f):
    if "ROCODROM" not in f:
        return None
    if "INTERIOR" in f:
        return _mk("ROCODROM_INTERIOR", "Rocodrom interior",
                   "espai", "pendiente", None,
                   status="pendiente_validacion",
                   notes="Metrica no validada.")
    return _mk("ROCODROM_EXTERIOR", "Rocodrom exterior",
               "espai", "pendiente", None,
               status="pendiente_validacion",
               notes="Metrica no validada.")


def r_volei_platja(p, r, f):
    if "VOLEI PLATJA" in f:
        return _mk("VOLEI_PLATJA", "Volei platja",
                   "pista", "unidad_recurso", 1.0)
    return None


def r_correr(p, r, f):
    if "CORRER CAMPUS" in f:
        return _mk("CORRER_CAMPUS", "Correr campus (vestidors)",
                   "servei", "pendiente", None,
                   status="pendiente_validacion",
                   notes="No es reserva de pista.")
    return None


def r_saf2_piscina(p, r, f):
    if r.startswith("SAF 2- PISCINA"):
        return _mk("SAF_2_PISCINA", "SAF 2 piscina (contenedor)",
                   "contenedor", "pendiente", None,
                   status="pendiente_validacion")
    return None


def r_camps_exteriors(p, r, f):
    if "CAMPS EXTERIORS" in f:
        return _mk("CAMPS_EXTERIORS", "Camps exteriors (contenedor)",
                   "contenedor", "pendiente", None,
                   status="pendiente_validacion")
    return None


def r_pavello_contenedor(p, r, f):
    if "PAVELLO COBERT SENCER" in f or "PISTES PAVELLO" in f:
        return _mk("PAVELLO_COBERT", "Pavello cobert (contenedor)",
                   "contenedor", "pendiente", None,
                   status="pendiente_validacion")
    return None


RULES = [
    r_padel, r_piscina_25_carril, r_piscina_25_contenedor, r_piscina_16,
    r_tenis, r_futbol7, r_futbol_sala, r_camps_exteriors_reservables,
    r_esquaix, r_badminton,
    r_basquet_volei_pavello, r_basquet_exterior,
    r_aadd_pista, r_aadd_fora, r_aadd_sala, r_aadd_espaibarbell,
    r_espaibarbell, r_salafitnes, r_sala4cycl, r_sala6box,
    r_calistenia, r_rocodrom, r_volei_platja, r_correr,
    r_saf2_piscina, r_camps_exteriors, r_pavello_contenedor,
]


def map_one(espai_pare, recurs):
    p, r = norm(espai_pare), norm(recurs)
    f = f"{p} {r}"
    for fn in RULES:
        out = fn(p, r, f)
        if out:
            out["espai_pare"] = espai_pare
            out["recurs"] = recurs
            out["calendar_label"] = cal(r)
            return out
    return dict(
        espai_pare=espai_pare, recurs=recurs,
        resource_id="", resource_name="", resource_kind="",
        metric_type="pendiente", capacity_units=None,
        parent_resource_id=None, fraction_of_parent=None,
        time_segment=None, calendar_label=cal(r),
        mapping_status="pendiente_validacion",
        notes="Sin regla aplicable",
    )


def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"No existe: {INPUT}")

    df = pd.read_csv(INPUT, sep=";")
    print(f"Input: {len(df)} filas")

    rows = [map_one(row["EspaiPare"], row["Recurs"]) for _, row in df.iterrows()]
    out = pd.DataFrame(rows)

    cols = ["espai_pare", "recurs", "resource_id", "resource_name",
            "resource_kind", "metric_type", "capacity_units",
            "parent_resource_id", "fraction_of_parent",
            "calendar_label", "time_segment", "mapping_status", "notes"]
    out = out[cols]
    out.to_csv(OUT / "resource_alias.csv", sep=";", index=False,
               encoding="utf-8-sig")

    total = len(out)
    mapped = (out["mapping_status"] == "regla_documentada").sum()
    pending = (out["mapping_status"] == "pendiente_validacion").sum()
    print(f"\nTotal: {total}")
    print(f"Mapeados (regla_documentada): {mapped}")
    print(f"Pendientes: {pending}")

    print("\n--- Pendientes ---")
    if pending == 0:
        print("(ninguno)")
    else:
        print(out[out["mapping_status"] == "pendiente_validacion"][
                  ["espai_pare", "recurs", "resource_id", "notes"]
              ].to_string(index=False))

    print("\n--- Resource IDs únicos ---")
    print(f"Total recursos únicos: {out['resource_id'].nunique()}")
    print(f"Con parent: {out['parent_resource_id'].notna().sum()}")
    print(f"Con fraction: {out['fraction_of_parent'].notna().sum()}")

    print(f"\nSalida: {OUT / 'resource_alias.csv'}")


if __name__ == "__main__":
    main()