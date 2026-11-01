"""In quali giorni gira una corsa CORe. Regole dedotte dai dati REST (vedi specifica)."""
from datetime import date, timedelta

GIORNI = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
ANNO_RICORRENTE = 2021  # periodi con anno < 2021 (2018-2020 nei dati) valgono ogni anno
TIPI = {"workingDay", "daily", "school", "nonSchool", "holiday"}


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
    # "holiday" (Festiva) ha il profilo tutto vero: gira solo domeniche e festivi
    if tipo == "holiday" and not (g in fest or g.weekday() == 6):
        return False
    if per["workingPeriods"] and not _in(g, per["workingPeriods"]):
        return False
    if _in(g, per["nonWorkingPeriods"]):
        return False
    if corsa["validPeriods"] and not _in(g, corsa["validPeriods"]):
        return False
    if _in(g, corsa["notValidPeriods"]):
        return False
    if scuola and g <= max(b for _, b in scuola):
        a_scuola = any(a <= g <= b for a, b in scuola)
    else:
        # oltre il calendario CORe (pubblicato a pezzi): anno scolastico stimato 15/9-10/6;
        # le vacanze stanno nei nonWorkingPeriods delle corse; l'app avvisa dopo scuola_nota_fino
        a_scuola = (g.month, g.day) >= (9, 15) or (g.month, g.day) <= (6, 10)
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
