from collections import defaultdict


def better(a, b, direction):
    return a > b if direction == "higher" else a < b


# VERIFIED
def normalise(score, best, direction):
    """Scale a score into (0, 1] relative to the best score on the benchmark."""
    if direction == "lower":
        return best / score
    return score / best


def team_bests(submissions, benchmarks):
    """team -> {benchmark: best score}, plus team -> time of its last counted submission."""
    bests = defaultdict(dict)
    times = defaultdict(list)
    for sub in submissions:
        bench = benchmarks.get(sub.benchmark)
        if bench is None:
            continue
        current = bests[sub.team].get(sub.benchmark)
        if current is None or better(sub.score, current, bench["direction"]):
            bests[sub.team][sub.benchmark] = sub.score
        times[sub.team].append(sub.submitted_at)
    last_seen = {team: max(ts) for team, ts in times.items()}
    return dict(bests), last_seen


def benchmark_leaders(bests, benchmarks):
    leaders = {}
    for name, bench in benchmarks.items():
        entries = [(team, scores[name]) for team, scores in bests.items() if name in scores]
        if not entries:
            continue
        leader = entries[0]
        for entry in entries[1:]:
            if better(entry[1], leader[1], bench["direction"]):
                leader = entry
        leaders[name] = leader
    return leaders


def composite(scores, leaders, benchmarks):
    total_weight = sum(b["weight"] for b in benchmarks.values())
    weighted = 0.0
    for name, bench in benchmarks.items():
        if name in scores:
            weighted += bench["weight"] * normalise(scores[name], leaders[name][1], bench["direction"])
    return round(weighted / total_weight, 4)
