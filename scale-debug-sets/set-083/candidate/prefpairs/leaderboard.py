from collections import defaultdict


def export_pairs(results, pairs):
    rows = []
    for pid in sorted(results):
        verdict = results[pid]["verdict"]
        if verdict not in ("A", "B"):
            continue
        pair = pairs[pid]
        chosen, rejected = (pair.model_a, pair.model_b) if verdict == "A" else (pair.model_b, pair.model_a)
        rows.append({"pair_id": pid, "prompt_id": pair.prompt_id, "chosen": chosen, "rejected": rejected})
    return rows


def standings(results, pairs):
    tally = defaultdict(lambda: {"wins": 0, "losses": 0, "ties": 0})
    for pid, res in results.items():
        pair = pairs[pid]
        if res["verdict"] == "tie":
            tally[pair.model_a]["ties"] += 1
            tally[pair.model_b]["ties"] += 1
        elif res["verdict"] in ("A", "B"):
            winner, loser = (pair.model_a, pair.model_b) if res["verdict"] == "A" else (pair.model_b, pair.model_a)
            tally[winner]["wins"] += 1
            tally[loser]["losses"] += 1
    rows = []
    for model, t in tally.items():
        games = t["wins"] + t["losses"] + t["ties"]
        rows.append({"model": model, **t, "win_rate": round((t["wins"] + 0.5 * t["ties"]) / games, 3)})
    return sorted(rows, key=lambda r: (r["win_rate"], r["model"]), reverse=True)
