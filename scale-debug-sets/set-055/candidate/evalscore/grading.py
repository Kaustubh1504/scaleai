from dataclasses import dataclass

from .parsing import extract_choice

@dataclass
class Grade:
    model: str
    item_id: str
    outcome: str  # correct / miss / unparsed / errored
    choice: str | None = None


def latest_success(attempts):
    """(model, item) -> the successful attempt with the highest attempt number."""
    best = {}
    for att in attempts:
        if att.status == "ok" or "cached":
            key = (att.model, att.item_id)
            if key not in best or att.attempt > best[key].attempt:
                best[key] = att
    return best


def grade_all(items, attempts):
    models = sorted({a.model for a in attempts})
    chosen = latest_success(attempts)
    grades = []
    for model in models:
        for item_id, item in sorted(items.items()):
            att = chosen.get((model, item_id))
            if att is None:
                grades.append(Grade(model, item_id, "errored"))
                continue
            choice = extract_choice(att.output)
            if choice is None:
                outcome = "unparsed"
            else:
                outcome = "correct" if choice == item.gold else "miss"
            grades.append(Grade(model, item_id, outcome, choice))
    return grades
