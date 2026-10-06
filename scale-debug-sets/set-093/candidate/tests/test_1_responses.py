import unittest

from quotecache.reports import build_report


class TestResponses(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.responses = build_report()["responses"]

    def pick(self, *ids):
        return {i: (self.responses[i]["outcome"], self.responses[i]["price"]) for i in ids}

    def test_every_request_answered(self):
        self.assertEqual(sorted(self.responses), [f"r{n:02d}" for n in range(1, 27)])

    def test_sku1_quotes(self):
        self.assertEqual(self.pick("r01", "r02", "r17", "r18"), {
            "r01": ("miss", 90.0), "r02": ("hit", 100.0),
            "r17": ("miss", 90.0), "r18": ("hit", 100.0),
        })

    def test_sku2_quotes(self):
        self.assertEqual(self.pick("r03", "r04", "r05", "r19", "r20"), {
            "r03": ("miss", 40.0), "r04": ("miss", 34.5), "r05": ("hit", 34.5),
            "r19": ("miss", 43.2), "r20": ("hit", 43.2),
        })

    def test_catalog_lookups(self):
        self.assertEqual(self.pick("r06", "r07", "r08", "r09", "r10", "r21", "r22"), {
            "r06": ("miss", 12.5), "r07": ("hit", 12.5), "r08": ("miss", 12.5),
            "r09": ("miss", 250.0), "r10": ("miss", 250.0),
            "r21": ("miss", 12.5), "r22": ("miss", 250.0),
        })

    def test_other_quotes(self):
        self.assertEqual(self.pick("r11", "r12", "r13", "r14", "r15", "r16", "r23", "r24", "r25", "r26"), {
            "r11": ("error", None), "r12": ("miss", 8.75), "r13": ("hit", 8.31),
            "r14": ("miss", 8.1), "r15": ("miss", 19.99), "r16": ("hit", 19.99),
            "r23": ("miss", 19.99), "r24": ("hit", 19.99), "r25": ("miss", 11.6),
            "r26": ("error", None),
        })


if __name__ == "__main__":
    unittest.main()
