from dataclasses import dataclass


@dataclass(frozen=True)
class Comparison:
    comparison_id: str
    round: int
    model_a: str
    model_b: str
    winner: str | None  # None means a tie
    rater: str

    @property
    def models(self):
        return (self.model_a, self.model_b)
