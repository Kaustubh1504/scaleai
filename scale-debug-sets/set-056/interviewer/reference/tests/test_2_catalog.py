import unittest

from skufeed.reports import build_report

EXPECTED = {
    "CB-120": {"title": "Cable ties 100pk", "category": "electrical", "price_cents": 480, "qty": 60, "source": "supplier_b"},
    "DR-200": {"title": "Cordless drill kit", "category": "tools", "price_cents": 124900, "qty": 3, "source": "supplier_a"},
    "DR-201": {"title": "Drill bit set", "category": "tools", "price_cents": 1600, "qty": 22, "source": "supplier_b"},
    "EL-900": {"title": "Outlet tester", "category": "electrical", "price_cents": 1200, "qty": 0, "source": "supplier_a"},
    "GD-700": {"title": "Garden hose 50ft", "category": "garden", "price_cents": 2950, "qty": 11, "source": "supplier_b"},
    "GD-702": {"title": "Watering can", "category": "garden", "price_cents": 1370, "qty": 5, "source": "supplier_b"},
    "HM-100": {"title": "Claw hammer 16oz", "category": "tools", "price_cents": 2499, "qty": 12, "source": "supplier_a"},
    "LT-400": {"title": "LED shop light 4ft", "category": "lighting", "price_cents": 4400, "qty": 10, "source": "supplier_b"},
    "LT-401": {"title": "Headlamp", "category": "lighting", "price_cents": 1530, "qty": 0, "source": "supplier_b"},
    "PR-050": {"title": "Promo work gloves", "category": "safety", "price_cents": 0, "qty": 25, "source": "supplier_b"},
    "PT-310": {"title": "Exterior paint 1gal", "category": "paint", "price_cents": 3850, "qty": 20, "source": "supplier_a"},
    "SF-801": {"title": "Ear defenders", "category": "safety", "price_cents": 1860, "qty": 12, "source": "supplier_b"},
}


class TestCatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = build_report()["catalog"]

    def test_catalog_skus(self):
        self.assertEqual(sorted(self.catalog), sorted(EXPECTED))

    def test_catalog_records(self):
        self.maxDiff = None
        self.assertEqual(self.catalog, EXPECTED)

    def test_discontinued_not_listed(self):
        self.assertNotIn("GD-701", self.catalog)
        self.assertNotIn("PT-311", self.catalog)


if __name__ == "__main__":
    unittest.main()
