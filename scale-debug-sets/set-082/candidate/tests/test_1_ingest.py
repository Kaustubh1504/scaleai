import unittest

from meterbill.reports import build_report


class TestIngest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_skipped_rows(self):
        self.assertEqual(self.report["skipped"], {
            "malformed": ["gw1-0010", "gw2-0012"],
            "unknown_tenant": ["gw2-0008", "gw2-0015"],
        })

    def test_same_instant_keeps_log_order(self):
        self.assertEqual(self.report["timeline"]["garnet"], ["gw2-0011", "gw1-0011", "gw2-0010", "gw1-0012"])

    def test_tenant_settings(self):
        tenants = self.report["tenants"]
        self.assertEqual(sorted(tenants), ["acme", "borealis", "cinder", "dunmore", "elm-labs",
                                           "fjord", "garnet", "halcyon", "juniper", "kestrel"])
        self.assertEqual({t: v["plan"] for t, v in tenants.items() if v["discount_pct"] != "0"},
                         {"acme": "growth", "kestrel": "scale"})
        self.assertEqual(self.report["timeline"]["cinder"], ["gw1-0001", "gw2-0002", "gw2-0009", "gw1-0016", "gw1-0018"])


if __name__ == "__main__":
    unittest.main()
