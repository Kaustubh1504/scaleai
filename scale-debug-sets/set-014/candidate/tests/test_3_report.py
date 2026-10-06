import unittest

from lbsim.reports import build_report


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.zones = build_report()["zones"]

    def test_zones_listed(self):
        self.assertEqual(list(self.zones), ["ap-south", "eu-west", "us-east"])

    def test_5_zone_served(self):
        self.assertEqual({z: row["served"] for z, row in self.zones.items()},
                         {"ap-south": 6, "eu-west": 5, "us-east": 8})

    def test_6_zone_mean_duration(self):
        self.assertEqual({z: row["mean_duration_ms"] for z, row in self.zones.items()},
                         {"ap-south": 1316.7, "eu-west": 1060.0, "us-east": 1087.5})


if __name__ == "__main__":
    unittest.main()
