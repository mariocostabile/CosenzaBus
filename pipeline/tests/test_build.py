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

    def test_fermate_senza_orario(self):
        g = json.loads(json.dumps(G))
        g["linee"]["256"]["travels"][0]["stops"].insert(1, {"durfCode": 1, "name": "X", "latitude": 39.3, "longitude": 16.2, "time": ""})
        d, rep = normalizza(g, G0, 8)
        self.assertEqual(d["trips"]["corse"][0][5], ["4162", 1020, "4181", 1022])
        self.assertEqual(rep["fermate_senza_orario"], 1)

    def test_corsa_difettosa_scartata(self):
        g = json.loads(json.dumps(G))
        g["linee"]["256"]["travels"][0]["stops"][1]["time"] = "16:30"  # refuso: torna indietro
        d, rep = normalizza(g, G0, 8)
        self.assertEqual([c[0] for c in d["trips"]["corse"]], ["5"])
        self.assertEqual(d["scartate"], [["200610", "136-A-(A)-1-1-L", "orari decrescenti"]])
        self.assertEqual(valida(d, rep, {"33": 2, "22": 1}, None), ["1 corse scartate su 2 (oltre 2%)"])

    def test_valida_ok_e_ko(self):
        self.assertEqual(valida(self.d, self.rep, {"33": 2, "22": 1}, None), [])
        errori = valida(self.d, self.rep, {"33": 2, "22": 10}, None)
        self.assertTrue(any("22" in e for e in errori))
        prima = {"conteggi": {"corse": 100}}
        self.assertTrue(any("corse" in e for e in valida(self.d, self.rep, {"33": 2, "22": 1}, prima)))

if __name__ == "__main__":
    unittest.main()
