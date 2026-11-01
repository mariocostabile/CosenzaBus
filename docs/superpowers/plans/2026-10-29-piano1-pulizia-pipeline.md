# Piano 1 — Pulizia + pipeline dati CORe su Pages

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ripartire da una cartella pulita e pubblicare ogni notte su GitHub Pages i dati statici di tutta la Calabria (fermate, varianti, corse con orari e calendario per giorno), presi dall'API REST CORe e controllati contro il GTFS regionale.

**Architecture:** script Python a moduli piccoli in `pipeline/` (solo libreria standard). `core.py` scarica (REST + GTFS), `calendario.py` decide in quali giorni gira una corsa, `hub.py` classifica le varianti, `build.py` normalizza, valida e scrive i JSON. Workflow GitHub Actions notturno: build, pubblica su Pages solo se la versione cambia, issue se la validazione fallisce.

**Tech Stack:** Python 3.12 (stdlib: `urllib`, `json`, `zipfile`, `csv`, `unittest`), GitHub Actions, GitHub Pages.

Specifica: `docs/superpowers/specs/2026-10-29-cosenzabus-calabria-design.md`. Piani successivi (da scrivere dopo questo): 2 app base (dati + mappa + fermate/linee/corse + extraurbane), 3 mirino + preferiti, 4 planner, 5 GPS live, 6 PWA + APK.

**Scostamento dalla specifica (deciso scrivendo il piano, 29/10/2026):** le corse si prendono dal REST, non dal GTFS. Motivo verificato: su 424 corse 136/157 lo scarto orario GTFS−REST è 0 (dopo il cambio d'ora) e `durfCode` = `stop_id` GTFS; il REST ha già orari locali corretti, coordinate, direzione e calendario. Il GTFS serve solo come controllo di completezza (corse per azienda). Così sparisce la logica di correzione oraria. `calendario.json` della specifica confluisce in `index.json`.

---

## Fatti verificati che il codice usa

REST base `https://mobilita.regione.calabria.it:8083/CoreRestServices/api/`.
- `operators` → `[{id, name, website, ...}]` (31). `operators/<id>/lines` → `[{id, code, ...}]` (più `code` per lo stesso `id`).
- `lines/<id>` → `{id, code, travels: [travel]}`. `travel`:
  `{legacyCode: 200610, operatorId: 33, journeyId: 1526, travelDirection: "outbound"|"inbound", code: "136-A-(A)-1-1-L", stops: [{durfCode: 4162, name, latitude, longitude, time: "17:00"}], periodicity: {type, shortName, description, operatingProfile: {sunday..saturday: bool, holidays, school}, workingPeriods: [{startDate, endDate}], nonWorkingPeriods: [...]}, validPeriods: [...], notValidPeriods: [...], message, messageExpire}`.
- `calendarperiods` → `{holidays: [{startDate, endDate}], schoolPeriods: [{startDate, endDate}]}`.
- Tipi di `periodicity.type` visti: `workingDay`, `school`, `nonSchool`, `daily`.
- Periodi con anno < 2021 (2018/2019/2020) sono **ricorrenti** (vale solo mese-giorno; es. Z36 "Feriale 1/01-31/07 e 10/09-31/12" = 2018-01-01..2018-07-31 + 2018-09-10..2018-12-31). Periodi con anno ≥ 2021 sono **date vere** (es. vacanze di Natale delle corse "Scolastica": 2026-12-23..2026-12-31, 2027-01-01..2027-01-06). Regola dedotta dai dati: da tenere sotto test.
- `workingPeriods` vuoto = tutto l'anno (Z79: "tutto l'anno tranne agosto" ha `workingPeriods: []`, `nonWorkingPeriods: [agosto 2020]`). Il portale CORe qui sbaglia (non la mostra mai attiva): noi no.
- Festivo: una corsa gira in un giorno festivo solo se ha `sunday: true` (festivo = domenica). Inferenza, da verificare col GPS l'8/12/2026.
- `calendarperiods.holidays` NON contiene il Lunedì dell'Angelo: limite noto, lo aggiungiamo noi calcolando la Pasqua.
- GTFS `https://mobilita.regione.calabria.it/gtfs/otp_gtfs.zip`: `agency_id` = `operatorId` REST, `trip_id` = `legacyCode`.
- Hub: Autostazione Cosenza = 16 `stop_id` diversi (uno per azienda) attorno a 39.30379, 16.25333; pensiline Unical attorno a 39.35600, 16.22740 (8 `stop_id`); la fermata 5586 "Università della Calabria" a 39.353, 16.242 NON è una pensilina (1,3 km).

## File

| File | Responsabilità |
|---|---|
| `pipeline/core.py` | HTTP verso CORe (pausa, timeout, retry, User-Agent) e scarico di tutti i dati grezzi |
| `pipeline/gtfs.py` | conteggio corse per azienda dal GTFS zip |
| `pipeline/calendario.py` | `attiva(corsa, giorno, festivi, scuola)` e maschera dei giorni |
| `pipeline/hub.py` + `pipeline/hub.json` | fermate hub e tipo di variante |
| `pipeline/build.py` | normalizza, valida, scrive `site/data/*.json` e `report.json`; uscita 1 se non valida |
| `pipeline/tests/test_*.py` + `pipeline/tests/fixtures/` | test `unittest` con dati ridotti scritti a mano dal formato reale |
| `.github/workflows/data.yml` | ogni notte: build → Pages se versione nuova; issue se fallisce |
| `CLAUDE.md` (locale, escluso da git), `README.md` | contesto e presentazione riscritti |

Formato di uscita (contratto per il Piano 2):
- `index.json`: `{"versione": "<sha1 12 hex dei dati>", "generato": "2026-10-29T03:30:00Z", "giorno0": "2026-10-29", "giorni": 400, "scuola_nota_fino": "2026-12-22", "conteggi": {"aziende": n, "varianti": n, "corse": n, "fermate": n}, "fonti": [...]}`
- `stops.json`: `{"4162": ["Autostazione Cosenza", 39.303792, 16.253333], ...}` (coordinate a 6 decimali)
- `routes.json`: `{"aziende": {"33": {"nome": "...", "sito": "..."}}, "varianti": {"1526": {"codice": "136-A", "azienda": "33", "tipo": "urbana"|"extraurbana"|"altro", "da": "<nome prima fermata>", "a": "<nome ultima fermata>"}}}`
- `trips.json`: `{"calendari": ["<hex>", ...], "corse": [[trip_id, variante, dir, cal, scuola, [stop_id, minuti, stop_id, minuti, ...]], ...]}`
  - `dir`: 0 = outbound, 1 = inbound. `cal`: indice in `calendari`. `scuola`: 1 se `type` è `school`/`nonSchool` (l'app avvisa dopo `scuola_nota_fino`).
  - `minuti`: minuti dalla mezzanotte del giorno di partenza, non decrescenti (dopo mezzanotte > 1440).
  - `calendari[i]`: maschera di `giorni` bit in esadecimale; bit k (k=0 = `giorno0`) = 1 se la corsa gira il giorno `giorno0 + k`. Bit k sta nel carattere hex k//4, peso 8 >> (k%4).
  - Corse con `message` e `messageExpire` futuro o nullo: escluse, contate nel report (sospese).

---

### Task 1: Pulizia della cartella

**Files:**
- Delete: `app/`, `config/`, `data/`, `scripts/`, `tests/`, `requirements.txt`, `.github/workflows/data.yml`, `.github/workflows/discovery.yml`, `.github/workflows/pages.yml`
- Modify: `README.md` (riscritto), `.gitignore` (aggiunge `site/`)
- Modify (locale, non in git): `CLAUDE.md`

- [ ] **Step 1: Controlla cosa c'è prima di cancellare**

Run: `git status --short; git ls-files | sed 's|/.*||' | sort | uniq -c`
Expected: albero pulito; cartelle `.github app config data docs scripts tests` + file `.gitignore README.md requirements.txt`. Se `git status` non è pulito, fermati e chiedi.

- [ ] **Step 2: Cancella**

```bash
git rm -r -q app config data scripts tests requirements.txt .github/workflows
```
Run: `git ls-files`
Expected: solo `.gitignore`, `README.md`, `docs/...`.

- [ ] **Step 3: `.gitignore`: aggiungi l'uscita della pipeline**

Aggiungi in fondo a `.gitignore`:
```
# --- Uscita della pipeline (si pubblica su Pages, non si committa) --------
/site/
```

- [ ] **Step 4: Riscrivi `README.md`**

```markdown
# CosenzaBus

Orari, fermate, bus in tempo reale e percorsi a piedi + bus per chi si muove tra **Cosenza, Rende e l'Unical**, e da lì verso il resto della Calabria. Alternativa leggera e aperta a Moovit.

> **Stato: in sviluppo.** Ripartito il 29/10/2026 sulle fonti della Regione Calabria.

## Fonti
Dati della **Regione Calabria** (piattaforma CORe): GTFS regionale e servizi CORe, licenza [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Mappa © OpenStreetMap. Progetto indipendente, non affiliato alla Regione né alle aziende di trasporto: gli orari ufficiali restano i loro.

## Struttura
- `pipeline/`: scarica i dati ogni notte (GitHub Actions) e li pubblica su GitHub Pages come JSON.
- `docs/superpowers/`: specifiche e piani.

Test: `python -m unittest discover -s pipeline/tests`
```

- [ ] **Step 5: Riscrivi `CLAUDE.md` (locale)**

Sostituisci tutto il contenuto con:
```markdown
# CosenzaBus — contesto progetto

App stile Moovit per Cosenza-Rende-Unical (urbane Consorzio + extraurbane che toccano Autostazione/pensiline Unical; planner su tutta la Calabria). AMACO esclusa (nessun dato aperto). Ripartito da zero il 29/10/2026.
Specifica: `docs/superpowers/specs/2026-10-29-cosenzabus-calabria-design.md`. Piani: `docs/superpowers/plans/`.
Stack: pipeline Python stdlib → JSON su GitHub Pages; app Expo (SDK 57) web + APK (piani successivi). Repo pubblico `mariocostabile/CosenzaBus`.

## Collaborazione
- Rispondi in italiano, diretto e sintetico. Fai da mentore critico: dimmi chiaramente quando sbaglio, evidenzia rischi e trade-off, niente complimenti a vuoto.
- Quando dai comandi da terminale, specifica sempre dove eseguirli (shell e cartella). Il PC di sviluppo è Windows (PowerShell).

## Fonti (verificate 28-29/10/2026, REA + chiamate dirette) — dettagli nella specifica
- REST CORe `https://mobilita.regione.calabria.it:8083/CoreRestServices/api/` (corse, orari corretti, calendario). GPS: `vehiclestatus/bytravellegacycode/<trip_id>`. Planner: OTP `https://mobilita.regione.calabria.it:8801/otp/routers/default/plan`. GTFS zip regionale solo come controllo.
- CORS: rimandano l'Origin. Nessuna chiave. API non documentate.
- `legacyCode` = `trip_id` GTFS; `durfCode` = `stop_id` GTFS; `operatorId` = `agency_id`.
- Calendario: periodi con anno < 2021 = ricorrenti (mese-giorno), ≥ 2021 = date vere; `workingPeriods` vuoto = tutto l'anno; festivo = domenica. Il portale CORe ha bug qui: non copiarlo.
- `calendarperiods` ha il calendario scolastico solo a pezzi (al 29/10/2026 fino al 22/12/2026) e non ha il Lunedì dell'Angelo.
- OTP: orari sfasati di +1 h in ora legale (il portale CORe lo compensa).
- GPS: `event 5` = passaggio in fermata (`parameter` = durfCode); pacchetti in ritardo di ~50 s; una richiesta per corsa, ~16 KB.
- Server fragile: User-Agent del progetto, pausa tra le richieste, una volta per notte.

## Stato
- 29/10/2026: pulizia + pipeline (Piano 1).
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "Ripartenza: rimossa la pipeline PDF e la vecchia app, README per le fonti CORe"
```
Run: `git ls-files`
Expected: `.gitignore`, `README.md`, `docs/superpowers/specs/...`, `docs/superpowers/plans/...`.

---

### Task 2: Calendario (`pipeline/calendario.py`)

**Files:**
- Create: `pipeline/calendario.py`
- Test: `pipeline/tests/test_calendario.py`

- [ ] **Step 1: Test che fallisce**

`pipeline/tests/test_calendario.py`:
```python
import sys, unittest
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from calendario import attiva, festivi, maschera, pasquetta

TUTTI = {"sunday": False, "monday": True, "tuesday": True, "wednesday": True,
         "thursday": True, "friday": True, "saturday": True, "holidays": False, "school": False}
DOM = {k: k == "sunday" for k in TUTTI}
P = lambda a, b: {"startDate": a, "endDate": b}

def corsa(tipo="workingDay", profilo=TUTTI, lav=(), non_lav=(), valid=(), not_valid=()):
    return {"periodicity": {"type": tipo, "operatingProfile": profilo,
                            "workingPeriods": list(lav), "nonWorkingPeriods": list(non_lav)},
            "validPeriods": list(valid), "notValidPeriods": list(not_valid)}

FEST = {date(2026, 12, 8), date(2026, 12, 25)}
SCUOLA = [(date(2026, 9, 15), date(2026, 12, 22))]

class TestAttiva(unittest.TestCase):
    def test_feriale_tutto_lanno(self):  # "L": 2019-01-01..2019-12-31 ricorrente
        c = corsa(lav=[P("2019-01-01", "2019-12-31")])
        self.assertTrue(attiva(c, date(2026, 10, 29), FEST, SCUOLA))   # giovedì
        self.assertFalse(attiva(c, date(2026, 11, 1), FEST, SCUOLA))   # domenica
        self.assertFalse(attiva(c, date(2026, 12, 8), FEST, SCUOLA))   # festivo martedì

    def test_periodi_ricorrenti_z36(self):  # 1/01-31/07 e 10/09-31/12
        c = corsa(lav=[P("2018-01-01", "2018-07-31"), P("2018-09-10", "2018-12-31")])
        self.assertTrue(attiva(c, date(2027, 7, 31), FEST, SCUOLA))
        self.assertFalse(attiva(c, date(2027, 8, 20), FEST, SCUOLA))
        self.assertFalse(attiva(c, date(2027, 9, 9), FEST, SCUOLA))
        self.assertTrue(attiva(c, date(2027, 9, 10), FEST, SCUOLA))

    def test_lavorativi_vuoti_tranne_agosto_z79(self):
        c = corsa(non_lav=[P("2020-08-01", "2020-08-31")])
        self.assertTrue(attiva(c, date(2026, 10, 29), FEST, SCUOLA))
        self.assertFalse(attiva(c, date(2027, 8, 10), FEST, SCUOLA))

    def test_periodo_ricorrente_a_cavallo_danno(self):
        c = corsa(lav=[P("2019-12-20", "2020-01-10")])
        self.assertTrue(attiva(c, date(2026, 12, 30), FEST, SCUOLA))
        self.assertTrue(attiva(c, date(2027, 1, 5), FEST, SCUOLA))
        self.assertFalse(attiva(c, date(2027, 1, 11), FEST, SCUOLA))

    def test_scolastica_con_vacanze_assolute(self):
        c = corsa(tipo="school", lav=[P("2020-01-01", "2020-12-31")],
                  non_lav=[P("2026-12-23", "2026-12-31"), P("2027-01-01", "2027-01-06")])
        self.assertTrue(attiva(c, date(2026, 10, 29), FEST, SCUOLA))
        self.assertFalse(attiva(c, date(2026, 12, 23), FEST, SCUOLA))  # vacanza
        self.assertFalse(attiva(c, date(2027, 2, 1), FEST, SCUOLA))    # oltre il calendario noto

    def test_non_scolastica(self):
        c = corsa(tipo="nonSchool")
        self.assertFalse(attiva(c, date(2026, 10, 29), FEST, SCUOLA))
        self.assertTrue(attiva(c, date(2027, 7, 1), FEST, SCUOLA))

    def test_domenicale_anche_nei_festivi(self):
        c = corsa(tipo="daily", profilo=DOM, lav=[P("2020-01-01", "2020-12-31")])
        self.assertTrue(attiva(c, date(2026, 11, 1), FEST, SCUOLA))    # domenica
        self.assertTrue(attiva(c, date(2026, 12, 8), FEST, SCUOLA))    # festivo martedì
        self.assertFalse(attiva(c, date(2026, 12, 9), FEST, SCUOLA))

    def test_valid_e_not_valid_assoluti(self):
        c = corsa(valid=[P("2026-10-01", "2026-11-30")], not_valid=[P("2026-11-02", "2026-11-03")])
        self.assertTrue(attiva(c, date(2026, 10, 29), FEST, SCUOLA))
        self.assertFalse(attiva(c, date(2026, 11, 2), FEST, SCUOLA))
        self.assertFalse(attiva(c, date(2026, 12, 1), FEST, SCUOLA))

    def test_tipo_sconosciuto(self):
        with self.assertRaises(ValueError):
            attiva(corsa(tipo="boh"), date(2026, 10, 29), FEST, SCUOLA)

class TestFestiviMaschera(unittest.TestCase):
    def test_pasquetta(self):
        self.assertEqual(pasquetta(2027), date(2027, 3, 29))
        self.assertEqual(pasquetta(2026), date(2026, 4, 6))

    def test_festivi_aggiunge_pasquetta(self):
        f = festivi([P("2026-12-08", "2026-12-08")], 2026, 2027)
        self.assertIn(date(2026, 12, 8), f)
        self.assertIn(date(2027, 3, 29), f)

    def test_maschera(self):
        # giorno0 = giovedì 29/10/2026; 8 giorni: gio ven sab DOM lun mar mer gio
        c = corsa(lav=[P("2019-01-01", "2019-12-31")])
        self.assertEqual(maschera(c, date(2026, 10, 29), 8, FEST, SCUOLA), "ef")  # 1110 1111

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Esegui e verifica che fallisce**

Run: `python -m unittest discover -s pipeline/tests -p "test_calendario.py"`
Expected: ERROR `ModuleNotFoundError: No module named 'calendario'`

- [ ] **Step 3: Implementa**

`pipeline/calendario.py`:
```python
"""In quali giorni gira una corsa CORe. Regole dedotte dai dati REST (vedi specifica)."""
from datetime import date, timedelta

GIORNI = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
ANNO_RICORRENTE = 2021  # periodi con anno < 2021 (2018-2020 nei dati) valgono ogni anno
TIPI = {"workingDay", "daily", "school", "nonSchool"}


def _d(s: str) -> date:
    return date.fromisoformat(s[:10])


def nel_periodo(g: date, p: dict) -> bool:
    a, b = _d(p["startDate"]), _d(p["endDate"])
    if a.year >= ANNO_RICORRENTE:
        return a <= g <= b
    x, da, a_ = (g.month, g.day), (a.month, a.day), (b.month, b.day)
    # un periodo ricorrente che finisce in un anno successivo attraversa il 31/12
    return da <= x <= a_ if b.year == a.year else x >= da or x <= a_


def _in(g: date, periodi: list) -> bool:
    return any(nel_periodo(g, p) for p in periodi)


def attiva(corsa: dict, g: date, fest: set, scuola: list) -> bool:
    per = corsa["periodicity"]
    tipo, prof = per["type"], per["operatingProfile"]
    if tipo not in TIPI:
        raise ValueError(f"tipo di periodicità sconosciuto: {tipo}")
    # festivo = domenica (inferenza: da verificare col GPS in un festivo infrasettimanale)
    if not prof["sunday" if g in fest else GIORNI[g.weekday()]]:
        return False
    if per["workingPeriods"] and not _in(g, per["workingPeriods"]):
        return False
    if _in(g, per["nonWorkingPeriods"]):
        return False
    if corsa["validPeriods"] and not _in(g, corsa["validPeriods"]):
        return False
    if _in(g, corsa["notValidPeriods"]):
        return False
    a_scuola = any(a <= g <= b for a, b in scuola)
    if tipo == "school" and not a_scuola:
        return False
    if tipo == "nonSchool" and a_scuola:
        return False
    return True


def pasquetta(anno: int) -> date:
    # algoritmo di Gauss/Meeus per la Pasqua gregoriana, più un giorno
    a, b, c = anno % 19, anno // 100, anno % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mese, giorno = divmod(h + l - 7 * m + 114, 31)
    return date(anno, mese, giorno + 1) + timedelta(days=1)


def festivi(holidays: list, da_anno: int, a_anno: int) -> set:
    out = set()
    for p in holidays:
        g, fine = _d(p["startDate"]), _d(p["endDate"])
        while g <= fine:
            out.add(g)
            g += timedelta(days=1)
    out.update(pasquetta(y) for y in range(da_anno, a_anno + 1))  # manca in calendarperiods
    return out


def maschera(corsa: dict, giorno0: date, giorni: int, fest: set, scuola: list) -> str:
    bits = [attiva(corsa, giorno0 + timedelta(days=k), fest, scuola) for k in range(giorni)]
    bits += [False] * (-len(bits) % 4)
    return "".join("%x" % (8 * a + 4 * b + 2 * c + d) for a, b, c, d in zip(*[iter(bits)] * 4))
```

- [ ] **Step 4: Esegui e verifica che passa**

Run: `python -m unittest discover -s pipeline/tests -p "test_calendario.py" -v`
Expected: 12 test OK.

- [ ] **Step 5: Commit**

```bash
git add pipeline/calendario.py pipeline/tests/test_calendario.py
git commit -m "pipeline: calendario delle corse CORe (periodi ricorrenti e assoluti, festivi, scuola)"
```

---

### Task 3: Fermate hub e tipo di variante (`pipeline/hub.py`)

**Files:**
- Create: `pipeline/hub.json`, `pipeline/hub.py`
- Test: `pipeline/tests/test_hub.py`

- [ ] **Step 1: Test che fallisce**

`pipeline/tests/test_hub.py`:
```python
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hub import fermate_hub, tipo_variante, metri

STOPS = {
    "4162": ["Autostazione Cosenza", 39.303792, 16.253333],
    "4194": ["Autostazione Cosenza", 39.3039, 16.2535],
    "4416": ["Università della Calabria - Arcavacata", 39.356022, 16.227353],
    "5586": ["Università della Calabria - Arcavacata", 39.353085, 16.242311],  # NON pensilina
    "4181": ["Viale Falcone, 158", 39.309282, 16.253253],
}

class TestHub(unittest.TestCase):
    def test_metri(self):
        self.assertAlmostEqual(metri(39.30, 16.25, 39.31, 16.25), 1112, delta=3)

    def test_fermate_hub(self):
        self.assertEqual(fermate_hub(STOPS), {"4162", "4194", "4416"})

    def test_tipo(self):
        h = {"4162", "4416"}
        self.assertEqual(tipo_variante("33", [["4181", "4162"]], h), "urbana")
        self.assertEqual(tipo_variante("22", [["4181"], ["4162", "4181"]], h), "extraurbana")
        self.assertEqual(tipo_variante("22", [["4181"]], h), "altro")

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Esegui e verifica che fallisce**

Run: `python -m unittest discover -s pipeline/tests -p "test_hub.py"`
Expected: ERROR `No module named 'hub'`

- [ ] **Step 3: Implementa**

`pipeline/hub.json`:
```json
{
  "urbane": ["33"],
  "hub": [
    {"nome": "Autostazione Cosenza", "lat": 39.30379, "lon": 16.25333, "raggio_m": 200},
    {"nome": "Pensiline Unical", "lat": 39.35600, "lon": 16.22740, "raggio_m": 200}
  ]
}
```

`pipeline/hub.py`:
```python
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
```

- [ ] **Step 4: Esegui e verifica che passa**

Run: `python -m unittest discover -s pipeline/tests -p "test_hub.py" -v`
Expected: 3 test OK.

- [ ] **Step 5: Commit**

```bash
git add pipeline/hub.json pipeline/hub.py pipeline/tests/test_hub.py
git commit -m "pipeline: fermate hub per distanza e tipo di variante (urbana/extraurbana)"
```

---

### Task 4: Download da CORe e GTFS (`pipeline/core.py`, `pipeline/gtfs.py`)

**Files:**
- Create: `pipeline/core.py`, `pipeline/gtfs.py`
- Test: `pipeline/tests/test_gtfs.py`

`core.py` fa solo rete: si prova con un run reale nel Task 6, non con test unitari (mock di `urllib` = codice di prova più grande del codice). `gtfs.py` è logica pura e ha il suo test.

- [ ] **Step 1: Test che fallisce per `gtfs.py`**

`pipeline/tests/test_gtfs.py`:
```python
import io, sys, unittest, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gtfs import corse_per_azienda

def zip_gtfs() -> bytes:
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("routes.txt", "﻿route_id,agency_id,route_short_name\n1526,33,136 A\n9,22,7 A\n")
        z.writestr("trips.txt", "route_id,service_id,trip_id\n1526,s,200610\n1526,s,200611\n9,s,5\n")
    return b.getvalue()

class TestGtfs(unittest.TestCase):
    def test_conteggio(self):
        self.assertEqual(corse_per_azienda(zip_gtfs()), {"33": 2, "22": 1})

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Esegui e verifica che fallisce**

Run: `python -m unittest discover -s pipeline/tests -p "test_gtfs.py"`
Expected: ERROR `No module named 'gtfs'`

- [ ] **Step 3: Implementa `gtfs.py`**

```python
"""GTFS regionale: usato solo come controllo di completezza delle corse REST."""
import csv, io, zipfile
from collections import Counter


def _righe(z: zipfile.ZipFile, nome: str):
    return csv.DictReader(io.TextIOWrapper(z.open(nome), "utf-8-sig"))


def corse_per_azienda(zip_bytes: bytes) -> dict:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        azienda = {r["route_id"]: r["agency_id"] for r in _righe(z, "routes.txt")}
        return dict(Counter(azienda[r["route_id"]] for r in _righe(z, "trips.txt")))
```

- [ ] **Step 4: Esegui e verifica che passa**

Run: `python -m unittest discover -s pipeline/tests -p "test_gtfs.py" -v`
Expected: 1 test OK.

- [ ] **Step 5: Implementa `core.py`**

```python
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
```

- [ ] **Step 6: Commit**

```bash
git add pipeline/core.py pipeline/gtfs.py pipeline/tests/test_gtfs.py
git commit -m "pipeline: download da CORe REST e conteggio corse GTFS"
```

---

### Task 5: Normalizzazione, validazione e scrittura (`pipeline/build.py`)

**Files:**
- Create: `pipeline/build.py`, `pipeline/tests/fixtures/grezzi.json`
- Test: `pipeline/tests/test_build.py`

- [ ] **Step 1: Fixture con il formato reale (ridotta a mano)**

`pipeline/tests/fixtures/grezzi.json`:
```json
{
  "operatori": [
    {"id": 33, "name": "Consorzio Autolinee TPL s.r.l.", "website": "www.consorzioautolineetpl.it"},
    {"id": 22, "name": "Ferrovie Della Calabria S.R.L.", "website": "www.ferroviedellacalabria.it"}
  ],
  "calendario": {
    "holidays": [{"startDate": "2026-12-08", "endDate": "2026-12-08"}],
    "schoolPeriods": [{"startDate": "2026-09-15", "endDate": "2026-12-22"}]
  },
  "linee": {
    "256": {"id": 256, "code": "136-A", "travels": [
      {"legacyCode": 200610, "operatorId": 33, "journeyId": 1526, "travelDirection": "outbound",
       "code": "136-A-(A)-1-1-L", "message": null, "messageExpire": null,
       "validPeriods": [], "notValidPeriods": [],
       "periodicity": {"type": "workingDay", "operatingProfile": {"sunday": false, "monday": true, "tuesday": true, "wednesday": true, "thursday": true, "friday": true, "saturday": true, "holidays": false, "school": false},
                       "workingPeriods": [{"startDate": "2019-01-01", "endDate": "2019-12-31"}], "nonWorkingPeriods": []},
       "stops": [
         {"durfCode": 4162, "name": "Autostazione Cosenza", "latitude": 39.3037919447191, "longitude": 16.253333200746, "time": "17:00"},
         {"durfCode": 4181, "name": "Viale Giovanni e Francesca Falcone, 158", "latitude": 39.3092819337726, "longitude": 16.2532532000145, "time": "17:02"}]},
      {"legacyCode": 200999, "operatorId": 33, "journeyId": 1526, "travelDirection": "outbound",
       "code": "136-A-(A)-1-1-L", "message": "Corsa sospesa", "messageExpire": null,
       "validPeriods": [], "notValidPeriods": [],
       "periodicity": {"type": "workingDay", "operatingProfile": {"sunday": false, "monday": true, "tuesday": true, "wednesday": true, "thursday": true, "friday": true, "saturday": true, "holidays": false, "school": false},
                       "workingPeriods": [], "nonWorkingPeriods": []},
       "stops": [
         {"durfCode": 4162, "name": "Autostazione Cosenza", "latitude": 39.3037919447191, "longitude": 16.253333200746, "time": "18:00"},
         {"durfCode": 4181, "name": "Viale Giovanni e Francesca Falcone, 158", "latitude": 39.3092819337726, "longitude": 16.2532532000145, "time": "18:02"}]}
    ]},
    "900": {"id": 900, "code": "7-A", "travels": [
      {"legacyCode": 5, "operatorId": 22, "journeyId": 9, "travelDirection": "inbound",
       "code": "7-A-(A)-1-1-D", "message": null, "messageExpire": null,
       "validPeriods": [], "notValidPeriods": [],
       "periodicity": {"type": "daily", "operatingProfile": {"sunday": true, "monday": false, "tuesday": false, "wednesday": false, "thursday": false, "friday": false, "saturday": false, "holidays": false, "school": false},
                       "workingPeriods": [], "nonWorkingPeriods": []},
       "stops": [
         {"durfCode": 77, "name": "Acri", "latitude": 39.49, "longitude": 16.38, "time": "23:50"},
         {"durfCode": 4162, "name": "Autostazione Cosenza", "latitude": 39.3037919447191, "longitude": 16.253333200746, "time": "00:40"}]}
    ]}
  }
}
```

- [ ] **Step 2: Test che fallisce**

`pipeline/tests/test_build.py`:
```python
import json, sys, unittest
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build import normalizza, valida, minuti

G = json.loads((Path(__file__).parent / "fixtures" / "grezzi.json").read_text(encoding="utf-8"))
G0 = date(2026, 10, 29)  # giovedì

class TestBuild(unittest.TestCase):
    def setUp(self):
        self.d, self.rep = normalizza(G, G0, 8)

    def test_minuti_dopo_mezzanotte(self):
        self.assertEqual(minuti(["23:50", "00:40"]), [1430, 1480])
        self.assertEqual(minuti(["07:00", "07:05"]), [420, 425])

    def test_fermate(self):
        self.assertEqual(self.d["stops"]["4162"], ["Autostazione Cosenza", 39.303792, 16.253333])

    def test_varianti_e_tipo(self):
        v = self.d["routes"]["varianti"]
        self.assertEqual(v["1526"], {"codice": "136-A", "azienda": "33", "tipo": "urbana",
                                     "da": "Autostazione Cosenza", "a": "Viale Giovanni e Francesca Falcone, 158"})
        self.assertEqual(v["9"]["tipo"], "extraurbana")

    def test_corse_e_sospese(self):
        corse = self.d["trips"]["corse"]
        self.assertEqual([c[0] for c in corse], ["200610", "5"])
        self.assertEqual(self.rep["sospese"], 1)
        c = corse[0]
        self.assertEqual(c[1:3], ["1526", 0])
        self.assertEqual(self.d["trips"]["calendari"][c[3]], "ef")  # gio ven sab (dom no) lun mar mer gio
        self.assertEqual(c[4], 0)
        self.assertEqual(c[5], ["4162", 1020, "4181", 1022])
        self.assertEqual(corse[1][2], 1)
        self.assertEqual(self.d["trips"]["calendari"][corse[1][3]], "10")  # solo domenica 1/11

    def test_valida_ok_e_ko(self):
        self.assertEqual(valida(self.d, self.rep, {"33": 2, "22": 1}, None), [])
        errori = valida(self.d, self.rep, {"33": 2, "22": 10}, None)
        self.assertTrue(any("22" in e for e in errori))
        prima = {"conteggi": {"corse": 100}}
        self.assertTrue(any("corse" in e for e in valida(self.d, self.rep, {"33": 2, "22": 1}, prima)))

if __name__ == "__main__":
    unittest.main()
```

Nota sul conteggio GTFS del test: `{"33": 2, ...}` conta anche la corsa sospesa, che il GTFS contiene. La copertura si calcola su corse REST totali (pubblicate + sospese) / corse GTFS.

- [ ] **Step 3: Esegui e verifica che fallisce**

Run: `python -m unittest discover -s pipeline/tests -p "test_build.py"`
Expected: ERROR `No module named 'build'`

- [ ] **Step 4: Implementa `build.py`**

```python
"""Normalizza i dati CORe, li valida e scrive i JSON per l'app. Uso: python pipeline/build.py site/data"""
import hashlib, json, sys, urllib.request
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

from calendario import festivi, maschera
from hub import fermate_hub, tipo_variante

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


def normalizza(g: dict, giorno0: date, giorni: int = GIORNI):
    cal = g["calendario"]
    fest = festivi(cal["holidays"], giorno0.year, giorno0.year + 2)
    scuola = [(date.fromisoformat(p["startDate"]), date.fromisoformat(p["endDate"])) for p in cal["schoolPeriods"]]
    stops, varianti, corse, calendari, rep = {}, {}, [], {}, Counter()
    per_var = {}
    for linea in g["linee"].values():
        for t in linea["travels"]:
            if sospesa(t, giorno0):
                rep["sospese"] += 1
                rep[f"sospese:{t['operatorId']}"] += 1  # il GTFS le contiene: servono alla copertura
                continue
            ferm = t["stops"]
            for s in ferm:
                stops[str(s["durfCode"])] = [s["name"].strip(), round(s["latitude"], 6), round(s["longitude"], 6)]
            vid = str(t["journeyId"])
            varianti.setdefault(vid, {"codice": t["code"].split("-(")[0], "azienda": str(t["operatorId"]),
                                      "da": ferm[0]["name"].strip(), "a": ferm[-1]["name"].strip()})
            per_var.setdefault(vid, []).append([str(s["durfCode"]) for s in ferm])
            m = maschera(t, giorno0, giorni, fest, scuola)
            ci = calendari.setdefault(m, len(calendari))
            mins = minuti([s["time"] for s in ferm])
            seq = [x for s, mi in zip(ferm, mins) for x in (str(s["durfCode"]), mi)]
            corse.append([str(t["legacyCode"]), vid, 0 if t["travelDirection"] == "outbound" else 1, ci,
                          int(t["periodicity"]["type"] in ("school", "nonSchool")), seq])
            rep[f"azienda:{t['operatorId']}"] += 1
    hub = fermate_hub(stops)
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
                      "hub": sorted(hub), "fonti": FONTI}}
    return dati, rep


def valida(d: dict, rep: Counter, gtfs: dict, prima) -> list:
    err = []
    for c in d["trips"]["corse"]:
        tempi, seq = c[5][1::2], c[5][0::2]
        if len(seq) < 2:
            err.append(f"corsa {c[0]}: meno di 2 fermate")
        elif any(b < a for a, b in zip(tempi, tempi[1:])):
            err.append(f"corsa {c[0]}: orari decrescenti")
        elif tempi[-1] - tempi[0] > 300:
            err.append(f"corsa {c[0]}: durata oltre 5 h")
    for az, n in gtfs.items():
        rest = rep.get(f"azienda:{az}", 0) + rep.get(f"sospese:{az}", 0)
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
    (o / "report.json").write_text(json.dumps({"errori": err, "conteggi": rep}, ensure_ascii=False, indent=1), encoding="utf-8")
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
```

- [ ] **Step 5: Esegui e verifica**

Run: `python -m unittest discover -s pipeline/tests -p "test_build.py" -v`
Expected: 5 test OK.

- [ ] **Step 6: Tutti i test**

Run: `python -m unittest discover -s pipeline/tests -v`
Expected: 21 test OK.

- [ ] **Step 7: Commit**

```bash
git add pipeline/build.py pipeline/tests/test_build.py pipeline/tests/fixtures/grezzi.json
git commit -m "pipeline: normalizzazione, validazione e JSON per l'app"
```

---

### Task 6: Run reale dal PC

**Files:** nessuno nuovo (eventuali correzioni a `pipeline/*.py` con test).

- [ ] **Step 1: Esegui** (PowerShell, cartella del repo)

```powershell
python pipeline/build.py site/data
```
Expected: ~150-200 righe di log `<id> <azienda>: <n> linee`, durata 5-15 min, poi `versione ... (nuova): {...}` ed exit code 0. Se esce 1, leggi `site/data/report.json`.

- [ ] **Step 2: Controlli a mano**

Run:
```powershell
python -c "import json;i=json.load(open('site/data/index.json',encoding='utf-8'));print(i['conteggi'],i['scuola_nota_fino'],len(i['hub']))"
python -c "import json,collections as C;r=json.load(open('site/data/routes.json',encoding='utf-8'));print(C.Counter((v['azienda'],v['tipo']) for v in r['varianti'].values()).most_common(15))"
python -c "import os;[print(f,os.path.getsize('site/data/'+f)) for f in os.listdir('site/data')]"
```
Expected:
- corse ~4.500-5.100, fermate ~6.000-6.600, aziende 25-27;
- `hub` contiene i 16 stop dell'Autostazione (tra cui 4162, 4194, 4767) e le pensiline Unical (tra cui 4416, 885), NON 5586;
- varianti della 33 tutte `urbana`; Ferrovie della Calabria (22), Federico (9), IAS Scura (16) con molte `extraurbana`;
- `trips.json` sotto 6 MB (gzip ~1 MB).
Se i conteggi escono fuori da questi intervalli, fermati e indaga prima di andare avanti (con `superpowers:systematic-debugging`).

- [ ] **Step 3: Controllo calendario su un caso reale**

Run:
```powershell
python -c "import json;t=json.load(open('site/data/trips.json',encoding='utf-8'));c=[x for x in t['corse'] if x[0]=='200610'][0];m=t['calendari'][c[3]];print(c[:5],m[:4])"
```
Expected: corsa 200610 (136 A, feriale) con i primi bit della maschera coerenti con i giorni a partire da oggi (feriali 1, domeniche 0).

- [ ] **Step 4: Commit di eventuali correzioni**

```bash
git add pipeline
git commit -m "pipeline: correzioni dal primo run reale"
```
(Salta se non hai cambiato nulla.)

---

### Task 7: Workflow notturno e pubblicazione su Pages

**Files:**
- Create: `.github/workflows/data.yml`

- [ ] **Step 1: Scrivi il workflow**

```yaml
name: data
# Ogni notte: scarica i dati CORe, valida, pubblica su Pages se la versione è cambiata.
on:
  schedule:
    - cron: "30 3 * * *"
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write
  issues: write

concurrency: pages

jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 40
    outputs:
      cambiata: ${{ steps.build.outputs.cambiata }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Test
        run: python -m unittest discover -s pipeline/tests
      - name: Build
        id: build
        run: |
          python pipeline/build.py _site/data
          echo "cambiata=$(cat _site/data/.cambiata)" >> "$GITHUB_OUTPUT"
          rm _site/data/.cambiata
          printf '<!doctype html><meta charset="utf-8"><title>CosenzaBus</title><p>Dati: <a href="data/index.json">data/index.json</a></p>' > _site/index.html
      - name: Issue se la validazione fallisce
        if: failure()
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          gh issue create --repo "$GITHUB_REPOSITORY" --label dati-ko \
            --title "Dati non pubblicati: validazione fallita ($(date -u +%F))" \
            --body "Run: $GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID. Report in _site/data/report.json (artifact del run)." \
            || gh issue create --repo "$GITHUB_REPOSITORY" --title "Dati non pubblicati ($(date -u +%F))" --body "Run: $GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID"
      - name: Report come artifact
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: report
          path: _site/data/report.json
          if-no-files-found: ignore
      - uses: actions/configure-pages@v5
        if: steps.build.outputs.cambiata == '1'
      - uses: actions/upload-pages-artifact@v3
        if: steps.build.outputs.cambiata == '1'

  deploy:
    needs: build
    if: needs.build.outputs.cambiata == '1'
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

Nota: Pages pubblica tutto `_site/` a ogni deploy. Quando arriverà la build web dell'app (Piano 6) i due contenuti vanno pubblicati dallo stesso workflow, altrimenti un deploy cancella l'altro.

- [ ] **Step 2: Commit e push del branch**

```bash
git add .github/workflows/data.yml
git commit -m "Workflow notturno: dati CORe su Pages, issue se la validazione fallisce"
git push -u origin ripartenza
```

- [ ] **Step 3: Merge su main e run manuale** (chiedi conferma all'utente prima del merge: cancella la vecchia app e i vecchi dati da `main`)

```bash
git switch main && git merge --ff-only ripartenza && git push
gh workflow run data.yml --ref main
gh run watch "$(gh run list --workflow data.yml --limit 1 --json databaseId -q '.[0].databaseId')"
```
Expected: job `build` e `deploy` verdi.

- [ ] **Step 4: Verifica la pubblicazione**

Run: `curl -s https://mariocostabile.github.io/CosenzaBus/data/index.json`
Expected: JSON con `versione`, `conteggi` uguali al run del Task 6 (± corse cambiate nella notte).

- [ ] **Step 5: Secondo run a vuoto**

Run: `gh workflow run data.yml --ref main` e poi `gh run watch ...`
Expected: `build` verde con log `(invariata)`, job `deploy` saltato.

---

## Self-review (fatta)
- Copertura specifica, sezione 1-2: pulizia (Task 1), REST + GTFS (Task 4), calendario con festivi/scuola/periodi (Task 2), hub e tipo variante (Task 3), uscite e validazione (Task 5), workflow notturno, issue e "pubblica solo se cambia" (Task 7), avviso scuola (Task 5 `main`). Correzione oraria: non serve più (scostamento motivato in testa). Sezioni 3-5 della specifica (app, interfaccia, planner, GPS): piani successivi.
- Tipi coerenti: `normalizza(g, giorno0, giorni)`, `valida(d, rep, gtfs, prima)`, `maschera(corsa, giorno0, giorni, fest, scuola)`, formato `corse` a 6 campi usato uguale in test e codice.
- Conteggio test: calendario 12, hub 3, gtfs 1, build 5 = 21.
