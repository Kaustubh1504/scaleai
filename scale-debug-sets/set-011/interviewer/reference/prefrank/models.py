from dataclasses import dataclass
from datetime import datetime

OUTCOMES = {"a", "b", "tie", "draw", "both_bad"}


@dataclass(frozen=True)
class Comparison:
    comparison_id: str
    prompt_id: str
    model_a: str
    model_b: str
    winner: str
    annotator: str
    rated_at: datetime


@dataclass
class ModelStats:
    model_id: str
    games: int = 0
    wins: int = 0
    ties: int = 0

    @property
    def win_rate(self):
        if not self.games:
            return 0.0
        return round((self.wins + 0.5 * self.ties) / self.games, 3)
