"""Light Catalan / Spanish / English detection for the response metadata and a
prompt hint. The model itself decides the reply language; this is best effort."""
from __future__ import annotations

import re

_WORDS = {
    "ca": {"què", "quin", "quina", "quins", "quines", "quan", "quants", "quantes", "hi", "més", "menys", "gent",
           "tanca", "obre", "és", "són", "està", "estan", "avui", "dilluns", "dimarts", "dimecres", "dijous",
           "divendres", "dissabte", "diumenge", "setmana", "pistes", "puc", "vull", "aforament", "tranquil",
           "tranquil·la", "i", "els", "les", "amb", "per", "algun", "alguna", "mica", "nosaltres", "aquí",
           "on", "fer", "jugar", "anar", "hores", "hora", "matí", "tarda", "nit", "gimnàs", "piscina", "doncs",
           "tancat", "obert", "molt", "poca", "alternativa", "recomanes", "recomana", "sisplau", "si", "us", "plau"},
    "es": {"qué", "cuál", "cuáles", "cuándo", "cuántos", "cuántas", "hay", "más", "menos", "gente", "cierra",
           "abre", "es", "son", "está", "están", "hoy", "lunes", "martes", "miércoles", "jueves", "viernes",
           "sábado", "domingo", "semana", "pistas", "puedo", "quiero", "aforo", "tranquilo", "tranquila", "y",
           "los", "las", "con", "para", "algún", "alguna", "poco", "aquí", "dónde", "hacer", "jugar", "ir",
           "horas", "mañana", "tarde", "noche", "gimnasio", "entonces", "cerrado", "abierto", "mucho", "poca",
           "recomiendas", "recomienda", "favor", "el", "la", "del", "qué"},
    "en": {"what", "when", "which", "how", "many", "is", "are", "the", "there", "open", "close", "closes",
           "opens", "less", "more", "crowded", "busy", "quiet", "quieter", "today", "monday", "tuesday",
           "wednesday", "thursday", "friday", "saturday", "sunday", "weekend", "weekends", "courts", "can",
           "want", "capacity", "and", "with", "for", "where", "play", "go", "time", "morning", "afternoon",
           "evening", "gym", "pool", "recommend", "please", "best", "about", "of", "to", "does", "do"},
}
_TOKEN = re.compile(r"[a-zàáèéíïòóúüçñ·']+", re.IGNORECASE)


def detect_language(text: str, fallback: str = "ca") -> str:
    tokens = [t.lower().strip("'") for t in _TOKEN.findall(text)]
    # Strong single-token markers.
    joined = " " + " ".join(tokens) + " "
    if "l·l" in text.lower() or " caps de setmana " in joined or "què" in tokens:
        return "ca"
    if any(ch in text for ch in "¿¡ñ") or " fin de semana " in joined:
        return "es"
    scores = {lang: sum(1 for t in tokens if t in words) for lang, words in _WORDS.items()}
    best = max(scores, key=lambda k: scores[k])
    if scores[best] == 0:
        return fallback
    tied = [k for k, v in scores.items() if v == scores[best]]
    return fallback if len(tied) > 1 and fallback in tied else best
