"""Scarico dai servizi della Regione Calabria (CORe). Server fragile: pausa, timeout, pochi retry."""
import json, time, urllib.error, urllib.request

REST = "https://mobilita.regione.calabria.it:8083/CoreRestServices/api/"
GTFS = "https://mobilita.regione.calabria.it/gtfs/otp_gtfs.zip"
UA = "CosenzaBus (github.com/mariocostabile/CosenzaBus)"
PAUSA_S = 2.0


def scarica(url: str, tentativi: int = 3, timeout: int = 90) -> bytes:
    for n in range(tentativi):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except (urllib.error.URLError, TimeoutError) as e:
            if n == tentativi - 1:
                raise RuntimeError(f"{url}: {e}") from e
            time.sleep(10 * (n + 1))


def rest(percorso: str):
    time.sleep(PAUSA_S)
    return json.loads(scarica(REST + percorso))


def tutto(log=print) -> dict:
    """Operatori, linee con corse, calendario e GTFS grezzi."""
    operatori = rest("operators")
    linee = {}
    for op in operatori:
        ids = sorted({l["id"] for l in rest(f"operators/{op['id']}/lines")})
        log(f"{op['id']} {op['name']}: {len(ids)} linee")
        for i in ids:
            linee[i] = rest(f"lines/{i}")
    return {"operatori": operatori, "linee": linee,
            "calendario": rest("calendarperiods"), "gtfs": scarica(GTFS, timeout=180)}
