import unittest

from leasebox.reports import build_report


def view(state, owner, attempts):
    return {"state": state, "owner": owner, "attempts": attempts}


class TestReplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_final_states(self):
        self.maxDiff = None
        self.assertEqual(self.report["final"], {
            "T01": view("done", None, 1), "T02": view("dead", None, 3), "T03": view("done", None, 1),
            "T04": view("done", None, 1), "T05": view("dead", None, 1), "T06": view("done", None, 1),
            "T07": view("done", None, 2), "T08": view("done", None, 1), "T09": view("done", None, 1),
            "T10": view("done", None, 2), "T11": view("leased", "W1", 2), "T12": view("ready", None, 0),
        })

    def test_poll_log(self):
        self.assertEqual(self.report["polls"], [
            ["W1", "T03"], ["W2", "T02"], ["W3", "T01"], ["W4", "T05"], ["W1", None], ["W3", "T07"],
            ["W4", "T04"], ["W2", "T02"], ["W1", "T06"], ["W3", "T07"], ["W4", "T02"], ["W2", "T10"],
            ["W3", "T10"], ["W1", "T08"], ["W2", "T09"], ["W4", "T11"], ["W1", "T11"],
        ])

    def test_checkpoint(self):
        self.maxDiff = None
        self.assertEqual(self.report["checkpoint"], {
            "T01": view("done", None, 1), "T02": view("leased", "W4", 3), "T03": view("done", None, 1),
            "T04": view("done", None, 1), "T05": view("dead", None, 1), "T06": view("done", None, 1),
            "T07": view("done", None, 2), "T08": view("ready", None, 0), "T09": view("ready", None, 0),
            "T10": view("leased", "W2", 1), "T11": view("ready", None, 0), "T12": view("ready", None, 0),
        })


if __name__ == "__main__":
    unittest.main()
