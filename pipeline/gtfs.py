"""GTFS regionale: usato solo come controllo di completezza delle corse REST."""
import csv, io, zipfile
from collections import Counter


def _righe(z: zipfile.ZipFile, nome: str):
    return csv.DictReader(io.TextIOWrapper(z.open(nome), "utf-8-sig"))


def corse_per_azienda(zip_bytes: bytes) -> dict:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        azienda = {r["route_id"]: r["agency_id"] for r in _righe(z, "routes.txt")}
        return dict(Counter(azienda[r["route_id"]] for r in _righe(z, "trips.txt")))
