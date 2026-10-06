import pytest

from app.consensus import Outcome, decide


@pytest.mark.parametrize("labels, redundancy, expected", [
    (["a"], 1, Outcome("submitted", None, None)),
    (["a", "a", "a"], 3, Outcome("completed", "a", 1.0)),
    (["a", "b", "a"], 3, Outcome("completed", "a", 0.67)),
    (["a", "b", "c"], 3, Outcome("disputed", None, 0.33)),
    (["a", "b"], 2, Outcome("disputed", None, 0.5)),       # 1 of 2 is not a strict majority
    (["a", "a", "b", "b"], 4, Outcome("disputed", None, 0.5)),
    (["a", "b", "a", "a", "c"], 5, Outcome("completed", "a", 0.6)),
])
def test_decide(labels, redundancy, expected):
    assert decide(labels, redundancy) == expected
