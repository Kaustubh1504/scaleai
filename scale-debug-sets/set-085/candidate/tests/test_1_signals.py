import unittest

from refwatch.links import build_rings, ring_index
from refwatch.loader import load_accounts, load_deposits, load_logins
from refwatch.rules import qualifying_accounts, referrals, self_referrals


class TestSignals(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.accounts = load_accounts()
        cls.deposits = load_deposits(cls.accounts)
        logins, shared = load_logins(cls.accounts)
        cls.rings = build_rings(cls.accounts, logins, shared)
        cls.index = ring_index(cls.rings)

    def test_1_rings(self):
        self.assertEqual(self.rings, [
            ["acc-06", "acc-28", "acc-29"],
            ["acc-03", "acc-16"],
            ["acc-07", "acc-08"],
        ])

    def test_shared_networks_do_not_link(self):
        for a, b in [("acc-01", "acc-11"), ("acc-02", "acc-14"), ("acc-01", "acc-02")]:
            self.assertFalse(a in self.index and self.index.get(a) == self.index.get(b), (a, b))

    def test_referral_lists(self):
        self.assertEqual(referrals(self.accounts), {
            "acc-01": ["acc-11", "acc-12", "acc-13"],
            "acc-02": ["acc-14", "acc-15"],
            "acc-03": ["acc-16", "acc-17", "acc-18"],
            "acc-04": ["acc-19", "acc-23", "acc-24"],
            "acc-05": ["acc-25", "acc-26", "acc-27"],
            "acc-06": ["acc-28"],
        })

    def test_qualifying_accounts(self):
        self.assertEqual(sorted(qualifying_accounts(self.accounts, self.deposits)), [
            "acc-11", "acc-12", "acc-14", "acc-15", "acc-16", "acc-17",
            "acc-19", "acc-23", "acc-25", "acc-27", "acc-28",
        ])

    def test_self_referrals(self):
        self.assertEqual(sorted(self_referrals(self.accounts, self.index)), ["acc-16", "acc-28"])


if __name__ == "__main__":
    unittest.main()
