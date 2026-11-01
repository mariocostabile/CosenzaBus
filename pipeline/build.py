"""Normalizza i dati CORe, li valida e scrive i JSON per l'app. Uso: python pipeline/build.py site/data"""
import hashlib, json, sys, urllib.request
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

from calendario import festivi, maschera
from hub import gruppi_hub, tipo_variante

GIORNI = 400
PUBBLICATI = "https://mariocostabile.github.io/CosenzaBus/data/index.json"
FONTI = ["Regione Calabria - CORe (REST) e GTFS regionale, CC BY 4.0"]


def minuti(orari: list) -> list:
    out, prima = [], None
    for o in orari:
        h, m = map(int, o.split(":")[:2])
        t = h * 60 + m
        while prima is not None and t < prima - 720:  # passaggio della mezzanotte
            t += 1440
        out.append(t)
        prima = t
    return out


def sospesa(t: dict, oggi: date) -> bool:
    return bool(t.get("message")) and (t.get("messageExpire") is None or date.fromisoformat(t["messageExpire"][:10]) >= oggi)


def difetto(mins: list):
    if len(mins) < 2:
        return "meno di 2 fermate con orario"
    if any(b < a for a, b in zip(mins, mins[1:])):
        return "orari decrescenti"
    if mins[-1] - mins[0] > 300:
        return "durata oltre 5 h"
    return None


def normalizza(g: dict, giorno0: date, giorni: int = GIORNI):
    cal = g["calendario"]
    fest = festivi(cal["holidays"], giorno0.year, giorno0.year + 2)
    scuola = [(date.fromisoformat(p["startDate"]), date.fromisoformat(p["endDate"])) for p in cal["schoolPeriods"]]
    stops, varianti, corse, calendari, rep, scartate = {}, {}, [], {}, Counter(), []
    per_var = {}
    for linea in g["linee"].values():
        for t in linea["travels"]:
            if sospesa(t, giorno0):
                rep["sospese"] += 1
                rep[f"sospese:{t['operatorId']}"] += 1  # il GTFS le contiene: servono alla copertura
                continue
            # alcune fermate hanno orario vuoto: le togliamo invece di inventarlo
            ferm = [s for s in t["stops"] if (s.get("time") or "").strip()]
            rep["fermate_senza_orario"] += len(t["stops"]) - len(ferm)
            mins = minuti([s["time"] for s in ferm])
            # errori della fonte (refusi, fermate in coda con l'orario di partenza): si scarta la corsa
            if motivo := difetto(mins):
                rep["scartate"] += 1
                rep[f"scartate:{t['operatorId']}"] += 1
                scartate.append([str(t["legacyCode"]), t["code"], motivo])
                continue
            for s in ferm:
                stops[str(s["durfCode"])] = [s["name"].strip(), round(s["latitude"], 6), round(s["longitude"], 6)]
            vid = str(t["journeyId"])
            varianti.setdefault(vid, {"codice": t["code"].split("-(")[0], "azienda": str(t["operatorId"]),
                                      "da": ferm[0]["name"].strip(), "a": ferm[-1]["name"].strip()})
            per_var.setdefault(vid, []).append([str(s["durfCode"]) for s in ferm])
            m = maschera(t, giorno0, giorni, fest, scuola)
            ci = calendari.setdefault(m, len(calendari))
            seq = [x for s, mi in zip(ferm, mins) for x in (str(s["durfCode"]), mi)]
            corse.append([str(t["legacyCode"]), vid, 0 if t["travelDirection"] == "outbound" else 1, ci,
                          int(t["periodicity"]["type"] in ("school", "nonSchool")), seq])
            rep[f"azienda:{t['operatorId']}"] += 1
    gruppi = gruppi_hub(stops)
    hub = {sid for ids in gruppi.values() for sid in ids}
    for vid, v in varianti.items():
        v["tipo"] = tipo_variante(v["azienda"], per_var[vid], hub)
    aziende = {str(o["id"]): {"nome": o["name"].strip(), "sito": o.get("website")} for o in g["operatori"]}
    fine_scuola = max((b for _, b in scuola), default=None)
    dati = {"stops": stops, "routes": {"aziende": aziende, "varianti": varianti},
            "trips": {"calendari": sorted(calendari, key=calendari.get), "corse": corse},
            "index": {"giorno0": giorno0.isoformat(), "giorni": giorni,
                      "scuola_nota_fino": fine_scuola.isoformat() if fine_scuola else None,
                      "conteggi": {"aziende": len({v["azienda"] for v in varianti.values()}), "varianti": len(varianti),
                                   "corse": len(corse), "fermate": len(stops)},
                      "hub": gruppi, "fonti": FONTI},
            "scartate": scartate}
    return dati, rep


def valida(d: dict, rep: Counter, gtfs: dict, prima) -> list:
    err = []
    n_scart, n_corse = len(d["scartate"]), len(d["trips"]["corse"])
    if n_scart > 0.02 * (n_scart + n_corse):  # oltre il 2% non è rumore della fonte
        err.append(f"{n_scart} corse scartate su {n_scart + n_corse} (oltre 2%)")
    for az, n in gtfs.items():
        rest = sum(rep.get(f"{k}:{az}", 0) for k in ("azienda", "sospese", "scartate"))
        if n and rest / n < 0.9:
            err.append(f"azienda {az}: {rest} corse REST su {n} GTFS (< 90%)")
    if prima:
        a, b = prima["conteggi"]["corse"], d["index"]["conteggi"]["corse"]
        if a and abs(b - a) / a > 0.2:
            err.append(f"corse: {b} contro {a} pubblicate (oltre ±20%)")
    return err


def versione(d: dict) -> str:
    corpo = json.dumps([d["stops"], d["routes"], d["trips"]], sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(corpo.encode()).hexdigest()[:12]


def pubblicati():
    try:
        with urllib.request.urlopen(PUBBLICATI, timeout=30) as r:
            return json.loads(r.read())
    except Exception:
        return None  # primo run o Pages giù: niente confronto


def main(out: str) -> int:
    from core import tutto
    from gtfs import corse_per_azienda
    g = tutto()
    oggi = datetime.now(timezone.utc).date()
    d, rep = normalizza(g, oggi)
    prima = pubblicati()
    err = valida(d, rep, corse_per_azienda(g["gtfs"]), prima)
    d["index"].update(versione=versione(d), generato=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    o = Path(out)
    o.mkdir(parents=True, exist_ok=True)
    (o / "report.json").write_text(json.dumps({"errori": err, "conteggi": rep, "scartate": d["scartate"]}, ensure_ascii=False, indent=1), encoding="utf-8")
    if d["index"]["scuola_nota_fino"] and (date.fromisoformat(d["index"]["scuola_nota_fino"]) - oggi).days < 30:
        print(f"AVVISO: calendario scolastico CORe noto solo fino al {d['index']['scuola_nota_fino']}")
    if err:
        print("\n".join(err[:50]))
        return 1
    for nome in ("index", "stops", "routes", "trips"):
        (o / f"{nome}.json").write_text(json.dumps(d[nome], ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    cambiata = not prima or prima.get("versione") != d["index"]["versione"]
    print(f"versione {d['index']['versione']} ({'nuova' if cambiata else 'invariata'}): {d['index']['conteggi']}")
    (o / ".cambiata").write_text("1" if cambiata else "0")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "site/data"))
