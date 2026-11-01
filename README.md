# CosenzaBus

Orari, fermate, bus in tempo reale e percorsi a piedi + bus per chi si muove tra **Cosenza, Rende e l'Unical**, e da lì verso il resto della Calabria. Alternativa leggera e aperta a Moovit.

> **Stato: in sviluppo.** Ripartito il 29/10/2026 sulle fonti della Regione Calabria.

## Fonti
Dati della **Regione Calabria** (piattaforma CORe): GTFS regionale e servizi CORe, licenza [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Mappa © OpenStreetMap. Progetto indipendente, non affiliato alla Regione né alle aziende di trasporto: gli orari ufficiali restano i loro.

## Struttura
- `pipeline/`: scarica i dati ogni notte (GitHub Actions) e li pubblica su GitHub Pages come JSON.
- `docs/superpowers/`: specifiche e piani.

Test: `python -m unittest discover -s pipeline/tests`
