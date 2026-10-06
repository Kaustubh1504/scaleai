import unittest

from lbsim.reports import build_report


class TestRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.routes = build_report()["routes"]

    def pool(self, ids):
        return {rid: self.routes[rid] for rid in ids}

    def test_api_routes(self):
        self.assertEqual(self.pool(["R01", "R02", "R03", "R04", "R09", "R10", "R12", "R13", "R14",
                                    "R18", "R19", "R21", "R22", "R26"]), {
            "R01": "api-1", "R02": "api-2", "R03": "api-3", "R04": "api-1",
            "R09": "api-2", "R10": "api-3", "R12": "api-1", "R13": "api-2",
            "R14": "api-1", "R18": "api-2", "R19": "api-1", "R21": "api-1",
            "R22": "api-2", "R26": "api-3",
        })

    def test_static_routes(self):
        self.assertEqual(self.pool(["R05", "R08", "R15", "R16", "R23", "R27"]), {
            "R05": "st-1", "R08": "st-2", "R15": "st-1", "R16": "st-2", "R23": "st-1", "R27": None,
        })

    def test_batch_routes(self):
        self.assertEqual(self.pool(["R06", "R07", "R11", "R17", "R20", "R24", "R25"]), {
            "R06": "bt-1", "R07": "bt-3", "R11": "bt-1", "R17": "bt-1", "R20": "bt-3", "R24": "bt-3", "R25": "bt-1",
        })

    def test_disabled_backends_unused(self):
        self.assertFalse({"api-4", "st-3", "bt-2"} & set(self.routes.values()))


if __name__ == "__main__":
    unittest.main()
