# CosenzaBus Calabria — progetto (29/10/2026)

App stile Moovit per chi si muove a Cosenza e Rende: orari, fermate, bus in tempo reale, percorso A→B a piedi + bus, scelta del punto con mirino, preferiti. Riparte da zero: sostituisce la pipeline PDF del Consorzio.

## Perimetro (deciso 29/10/2026)
- **Urbane**: tutte le linee del Consorzio Autolinee TPL (agency 33). Compaiono sulla mappa città.
- **Extraurbane**: tutte le corse di altre aziende che toccano un *hub*: Autostazione di Cosenza (`durfCode` 4162) e pensiline Unical (fermate "Università della Calabria - Arcavacata"). Esempi: Ferrovie della Calabria, Federico, IAS Scura, Romano, Preite, Carnevale. Sezione a parte, raggruppate per azienda e destinazione; include anche le corse in arrivo agli hub.
- **Planner**: dati di tutta la Calabria (servono per arrivare ovunque partendo da Cosenza/Rende).
- **Escluso**: AMACO (non è nel GTFS regionale né in CORe; nessun dato aperto: unico documento trovato un libretto PDF scaduto il 31/01/2026). Treni.
- Misura (GTFS 29/10/2026): corse in viaggio contemporaneamente nell'area Cosenza-Rende-Unical 97 (17:00) - 174 (13:00); Consorzio 25-43.

## Fonti (verificate il 28-29/10/2026, REA + chiamate dirette)

Tutte della Regione Calabria (piattaforma CORe). CORS: rimandano l'`Origin` della richiesta (provato con `https://mariocostabile.github.io` e `http://localhost:8081`). Nessuna chiave. Non documentate: possono cambiare senza preavviso.

| Fonte | URL | Uso |
|---|---|---|
| GTFS regionale | `https://mobilita.regione.calabria.it/gtfs/otp_gtfs.zip` (2,5 MB; 26 aziende, 2.766 varianti, 5.047 corse, 6.530 fermate; CC BY 4.0) | struttura e orari |
| REST CORe | `https://mobilita.regione.calabria.it:8083/CoreRestServices/api/` | calendario delle corse, nomi fermate, controllo orari |
| GPS | REST `vehiclestatus/bytravellegacycode/<trip_id>` | posizione e ritardo reali |
| Planner OTP | `https://mobilita.regione.calabria.it:8801/otp/routers/default/plan` | itinerari a piedi + bus |

### REST CORe
- `operators` (31), `operators/<id>/lines` (codici variante; più codici condividono un `id` di linea: Consorzio 110 codici, 21 id).
- `lines/<id>`: `travels[]` con `legacyCode` (= `trip_id` GTFS), `stops[]` (`durfCode`, nome, coordinate, `time` locale corretto), `distances`, `travelDirection`, `periodicity`, `validPeriods`, `notValidPeriods`, `message`/`messageExpire` (corsa sospesa). Peso: 0,8-1,4 MB per linea.
- `periodicity`: `operatingProfile` (giorni della settimana + `holidays` + `school`), `workingPeriods`/`nonWorkingPeriods` con anno fittizio (es. 2018-01-01..2018-07-31 = "dal 1/1 al 31/7 di ogni anno"), `description` leggibile ("Feriale nel mese di Agosto da Lunedì a Sabato").
- `calendarperiods`: `holidays` (date), `schoolPeriods` (al 29/10/2026 un solo periodo: 2026-09-15..2026-12-22).
- `travels/bydurf/<durfCode>` (corse di una fermata, ~600 KB all'Autostazione), `lines/bydurf/<durfCode>`, `stops/search/<q>`, `stops/nearto/...` (parametri da capire: risposta vuota al primo tentativo).

Il portale CORe decide se una corsa è attiva oggi controllando la data di oggi e quella di 365 giorni prima nei `workingPeriods` (confronto senza anno), poi `validPeriods`/`notValidPeriods`. Da replicare e verificare con un test.

### GPS (`vehiclestatus`)
Risposta: lista con `lastPacket`, `startPacket`, `packets[]`, `plate`, `lastSeen`, `done`, `travel`. Pacchetto: `timestamp` (s), `location` lat/lon, `heading`, `speed`, `vehicleJourneyID` (= trip_id), `parameter`, `trackingInfo.event`:
- `5` = passaggio in fermata, `parameter` = `durfCode` della fermata. Ritardo = `timestamp` − orario previsto della fermata.
- `0` (type 3) = posizione periodica (~60 s). `1` = inizio corsa. `3`, `4` = soste (significato esatto da confermare).
I pacchetti arrivano a CORe con ~46-50 s di ritardo. Nessun endpoint di massa: una richiesta per corsa.

### OTP
`plan?fromPlace=<nome>::<lat>,<lon>&toPlace=...&time=H:MM&date=MM-DD-YYYY&mode=TRANSIT,WALK&maxWalkDistance=<m>&arriveBy=<bool>&numItineraries=<n>&minTransferTime=<s>&locale=it_IT`. Risposta: `plan.itineraries[].legs[]` con `mode`, `route`, `startTime`/`endTime` (ms), `from`/`to`, `distance`, `legGeometry` (polilinea codificata), `steps`.
**Sfasamento orario**: il portale CORe aggiunge 1 h all'ora richiesta quando il fuso del browser è CEST (`getTimezoneOffset() == -120`). È lo stesso +60 min degli `stop_times` GTFS. Non ci fidiamo di una regola fissa: la correzione si ricava confrontando i viaggi restituiti con le corse note (vedi Planner).

### Correzioni a conclusioni precedenti
- 157 H e 157 Z NON sono duplicati: H = andata (Autostazione → Via Volta), Z = ritorno.
- Molte corse GTFS "morte" (calendario 19700101) sono corse con periodicità particolare (es. solo agosto): il calendario del GTFS è guasto, quello REST no.

## Architettura (ibrida)

```
GTFS zip ─┐
REST lines ┼─> pipeline notturna (GitHub Actions) ─> JSON statici su GitHub Pages ─> app (cache offline)
REST cal. ─┘
                         app ──live──> CORe vehiclestatus (GPS)   app ──live──> OTP plan (planner)
```
Pages fa da "nostro server" gratuito: una richiesta a notte a CORe invece di una per utente a ogni tocco. Se CORe è giù, orari e fermate funzionano lo stesso; mancano solo GPS e OTP.

## 1. Pulizia
Su un branch: cancellare tutto il codice e i dati di `main` (pipeline PDF, `scripts/`, `tests/`, `config/`, `data/`, `app/`, `.github/workflows/`), riscrivere `CLAUDE.md` con le fonti sopra. Resta la storia git e il branch `discovery`. Restano anche questa specifica e `LICENSE`/`README` se presenti (il README va riscritto).

## 2. Pipeline dati (`pipeline/`, Python standard, nessuna dipendenza)
1. Scarica il GTFS zip (1 richiesta).
2. Per ogni azienda: `operators/<id>/lines`, poi `lines/<id>` per ogni id unico (~100-170 richieste, pausa 2 s, timeout, User-Agent `CosenzaBus (github.com/mariocostabile/CosenzaBus)`). Più `calendarperiods`.
3. Abbina le corse REST alle GTFS con `legacyCode` = `trip_id`.
4. Ora: per ogni corsa, scarto = orario GTFS − orario REST alla prima fermata. Atteso costante (0 o 60 min). Si usa l'orario REST quando c'è; una corsa senza corrispondenza REST tiene l'orario GTFS corretto con lo scarto modale della sua azienda, e finisce nel report.
5. Uscita (`site/data/`, pubblicata su Pages):
   - `index.json`: data, versione (hash dei dati normalizzati), conteggi, fonti e licenze.
   - `stops.json`: `{id: [nome, lat, lon]}` (id = `stop_id` GTFS = `durfCode`).
   - `routes.json`: aziende (id, nome, colore) e varianti (id, codice, azienda, capolinea, `tipo`: `urbana` | `extraurbana` | `altro`). Una variante è `extraurbana` se un'azienda diversa dalla 33 ha almeno una corsa che tocca un hub; l'elenco delle fermate hub sta in `pipeline/hub.json` (verificato da un test: nomi e distanza ≤ 400 m dai punti di riferimento).
   - `trips.json` (unico file, ~1 MB con gzip, serve intero alla riserva offline del planner): corse `{trip_id, variante, direzione, calendario: <indice>, fermate: [[stop_id, minuti dalla mezzanotte], ...]}` + tabella dei calendari distinti (regole REST normalizzate: giorni, periodi senza anno, festivi, scuola, validità, sospensione).
   - `calendario.json`: festivi e periodi scolastici.
6. Validazione (se fallisce: issue con label `dati-ko`, nessuna pubblicazione):
   - ogni corsa: orari non decrescenti, durata ≤ 5 h, ≥ 2 fermate con coordinate;
   - numero di corse per azienda entro ±20% rispetto ai dati pubblicati (se esistono);
   - almeno il 90% delle corse GTFS abbinate a REST.
   - avviso (non blocca): l'ultimo `schoolPeriods` di `calendarperiods` finisce entro 30 giorni (la Regione pubblica i periodi a pezzi: al 29/10/2026 solo fino al 22/12/2026).
   Report (`report.json`) con le anomalie, pubblicato.
7. Workflow `.github/workflows/data.yml`: ogni notte + manuale; pubblica solo se l'hash cambia.

Test: `pipeline/test_*.py` con fixture ridotte (un estratto GTFS e una risposta REST salvata), eseguibili con `python -m unittest`.

## 3. App (`app/`, Expo SDK 57, senza Expo Router)
Target: web statico su Pages (PWA) e APK Android (EAS). Debug con Expo Go.

Moduli puri (testati con `node --test`, TypeScript eseguito come nel progetto precedente):
- `data.ts`: scarica `index.json`; se la versione è nuova riscarica `stops.json`, `routes.json`, `trips.json`, `calendario.json`; cache in AsyncStorage (sul web IndexedDB se AsyncStorage non regge la dimensione: da verificare al passo 3).
- `calendario.ts`: `attiva(corsa, giorno)` dalle regole REST + `calendario.json`.
- `orari.ts`: prossime partenze di una fermata (tutte le aziende), corse di una variante, posizione stimata dall'orario.
- `live.ts`: `vehiclestatus` SOLO per ciò che l'utente sta guardando: bus toccato sulla mappa, fermata aperta (le prossime 5 corse), linea aperta (le sue corse in viaggio), corsa aperta, itinerario scelto. Ogni 30 s, mai più di 6 richieste in parallelo, stop quando la schermata si chiude o l'app va in background. Motivo: nessun endpoint di massa e ~16 KB per risposta (40 corse ogni 30 s = ~75 MB/ora). Restituisce posizione, targa, età del dato, ritardo dall'ultimo passaggio `event 5`. Errore o nessun pacchetto ⇒ `null` (orario programmato).
- `planner.ts`:
  - OTP con `numItineraries=5`, `maxWalkDistance=1000`, `minTransferTime=180`; modalità parti adesso / parti alle / arriva entro.
  - Correzione oraria: per ogni tratto bus, si cerca la corsa nostra con stessa variante e stessa fermata di salita; lo scarto (0 o ±60 min) si applica all'intero itinerario. Se nessun tratto si abbina, si usa lo scarto dell'ultima risposta riuscita, e l'itinerario è marcato "orario da verificare".
  - Riserva locale se OTP non risponde in 10 s o dà errore: CSA sulle corse attive, al massimo 1 cambio, tratti a piedi = distanza in linea d'aria × 1,3 a 4,5 km/h entro 1 km, segnalati come stima.
  - I ritardi live si applicano agli itinerari mostrati: se un bus è in ritardo tale da perdere un cambio, l'itinerario è marcato "cambio a rischio".
- `preferiti.ts`: AsyncStorage `{fermate: id[], luoghi: {nome, lat, lon}[], itinerari: {da, a}[]}`.

Mappa: MapLibre GL JS + stile OpenFreeMap, in WebView (Android) e iframe (web), messaggi app↔mappa. Livelli: fermate (cluster a bassa zoom), percorso a piedi (tratteggiato), tratti bus (colore della linea), bus urbani con posizione stimata dall'orario (nessuna richiesta di rete; stile distinto), bus con GPS reale, utente, mirino. Messaggio `centro` al `moveend` in modalità mirino.

## 4. Interfaccia
- Mappa a tutto schermo + pannello in basso (tre altezze).
- Home: barra "Dove vuoi andare?", luoghi preferiti come scorciatoie, fermate preferite con prossime partenze, fermate vicine.
- Mappa città: bus urbani in viaggio con posizione stimata; tocco su un bus ⇒ GPS reale e ritardo.
- Sezione **Extraurbane**: aziende → linee/destinazioni dagli hub, prossime partenze da Autostazione e Unical; aprendo una linea, i suoi bus in viaggio con GPS reale.
- Da/A: posizione GPS, ricerca fermata, **mirino** (mirino fisso al centro, la mappa si sposta; il pannello mostra la fermata più vicina entro 150 m oppure "Punto sulla mappa"; pulsanti "Usa come partenza / arrivo / Salva luogo"), preferiti.
- Ora: parti adesso / parti alle / arriva entro.
- Itinerari: lista (durata, orario partenza/arrivo, sequenza a piedi/linee, ritardo live); dettaglio con tratti e mappa; stella per salvare l'itinerario.
- Fermata: prossime partenze di tutte le aziende, ritardo live, stella.
- Corsa: fermate con orari previsti e reali, bus sulla mappa.
- Sempre visibili: data dei dati, "GPS di N s fa" / "orario programmato", "stima" per i tratti a piedi della riserva, attribuzioni (dati © Regione Calabria CC BY 4.0, mappa © OpenStreetMap / OpenFreeMap).

## 5. Errori e limiti
- CORe REST giù di notte: la pipeline non pubblica, i dati vecchi restano.
- OTP giù: riserva locale. GPS giù: orario programmato. Senza rete: cache.
- Calendario scolastico CORe parziale: le corse "Scolastica" fuori dai `schoolPeriods` noti sono mostrate con avviso "solo giorni di scuola" invece di essere nascoste. Da rivedere se CORe pubblica l'anno intero.
- Limiti dichiarati in app: dati non ufficiali, API non documentate, GPS solo per i mezzi che trasmettono.

## Ordine di sviluppo
1. Pulizia. 2. Pipeline + Pages. 3. App: dati + mappa + fermate/linee/corse. 4. Mirino + preferiti. 5. Planner (OTP + riserva). 6. GPS live. 7. PWA + APK.
Ogni passo è provabile da solo.

## Fuori perimetro (per ora)
Notifiche, account, treni, AMACO.

## Fase 2 (programmata dopo la prima versione)
Backend che segue tutte le corse in viaggio nell'area (~100-175) e pubblica un `vehicles.json` piccolo per tutti i telefoni, così la mappa mostra il GPS reale di tutti i bus contemporaneamente. Dove: VPS piccola (~4 €/mese) o Oracle Cloud Always Free, con Cloudflare davanti. Prima di attivarlo: contattare la Regione (CORe) per concordare il carico (~6 richieste/s).
