import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hub import gruppi_hub, tipo_variante, metri

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

    def test_gruppi_hub(self):
        self.assertEqual(gruppi_hub(STOPS), {"Autostazione Cosenza": ["4162", "4194"], "Pensiline Unical": ["4416"]})

    def test_tipo(self):
        h = {"4162", "4416"}
        self.assertEqual(tipo_variante("33", [["4181", "4162"]], h), "urbana")
        self.assertEqual(tipo_variante("22", [["4181"], ["4162", "4181"]], h), "extraurbana")
        self.assertEqual(tipo_variante("22", [["4181"]], h), "altro")

if __name__ == "__main__":
    unittest.main()
