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
