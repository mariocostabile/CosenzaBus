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
        self.assertTrue(attiva(c, date(2027, 2, 1), FEST, SCUOLA))     # oltre il calendario noto: stima
        self.assertFalse(attiva(c, date(2027, 1, 5), FEST, SCUOLA))    # vacanza dichiarata dalla corsa
        self.assertFalse(attiva(c, date(2027, 7, 1), FEST, SCUOLA))    # estate stimata

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

    def test_festiva_holiday(self):  # Z41: profilo tutto vero, solo domeniche e festivi
        c = corsa(tipo="holiday", profilo={k: True for k in TUTTI}, lav=[P("2019-01-01", "2019-07-31"), P("2019-09-01", "2019-12-31")])
        self.assertTrue(attiva(c, date(2026, 11, 1), FEST, SCUOLA))    # domenica
        self.assertTrue(attiva(c, date(2026, 12, 8), FEST, SCUOLA))    # festivo martedì
        self.assertFalse(attiva(c, date(2026, 10, 29), FEST, SCUOLA))  # giovedì
        self.assertFalse(attiva(c, date(2027, 8, 1), FEST, SCUOLA))    # domenica di agosto

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
