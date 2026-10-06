from collections import Counter, defaultdict

from .parsing import parse_output


def grade(items, responses):
    graded = {}
    for resp in responses:
        item = items[resp.item_id]
        answer, flags = parse_output(resp.output)
        graded[resp.response_id] = {
            "model": resp.model,
            "item": resp.item_id,
            "category": item.category,
            "weight": item.weight,
            "latency_ms": resp.latency_ms,
            "answer": answer,
            "correct": answer == item.gold,
            "flags": flags,
        }
    return graded


def model_stats(graded):
    by_model = defaultdict(list)
    for row in graded.values():
        by_model[row["model"]].append(row)
    stats = {}
    for model, rows in sorted(by_model.items()):
        total = sum(r["weight"] for r in rows)
        earned = sum(r["weight"] for r in rows if r["correct"])
        by_category = Counter()
        for r in rows:
            if r["correct"]:
                by_category[r["category"]] += 1
        stats[model] = {
            "accuracy": round(earned / total, 3),
            "parse_failures": sum(1 for r in rows if r["answer"] is None),
            "mean_latency_ms": round(sum(r["latency_ms"] for r in rows) / len(rows), 1),
            "by_category": dict(sorted(by_category.items())),
        }
    return stats
