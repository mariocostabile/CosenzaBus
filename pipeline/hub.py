"""Fermate hub (Autostazione Cosenza, pensiline Unical) e tipo di ogni variante."""
import json
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

CONF = json.loads((Path(__file__).with_name("hub.json")).read_text(encoding="utf-8"))


def metri(la1, lo1, la2, lo2) -> float:
    h = sin(radians(la2 - la1) / 2) ** 2 + cos(radians(la1)) * cos(radians(la2)) * sin(radians(lo2 - lo1) / 2) ** 2
    return 12742000 * asin(sqrt(h))


def fermate_hub(stops: dict) -> set:
    # per distanza, non per nome: ogni azienda ha il suo stop_id e i nomi non sono affidabili
    return {sid for sid, (_, la, lo) in stops.items()
            if any(metri(la, lo, h["lat"], h["lon"]) <= h["raggio_m"] for h in CONF["hub"])}


def tipo_variante(azienda: str, fermate_corse: list, hub: set) -> str:
    if azienda in CONF["urbane"]:
        return "urbana"
    return "extraurbana" if any(hub.intersection(f) for f in fermate_corse) else "altro"
