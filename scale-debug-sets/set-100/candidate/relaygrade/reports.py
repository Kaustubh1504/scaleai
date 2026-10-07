import asyncio
from pathlib import Path

from .client import RelayClient
from .history import fetch_baselines, latest_baselines
from .loader import load_config, load_prompts, load_suites
from .runner import Runner

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def normalize(text):
    return " ".join(text.lower().split())


def grade(completion, prompt):
    return normalize(prompt.expected) in normalize(completion.text)


def suite_scores(prompts, completions):
    scores = {}
    for prompt in prompts:
        if prompt.id not in completions:
            continue
        entry = scores.setdefault(prompt.suite, {"graded": 0, "passed": 0})
        entry["graded"] += 1
        entry["passed"] += int(grade(completions[prompt.id], prompt))
    return dict(sorted(scores.items()))


def find_regressions(prompts, completions, baselines):
    return sorted(
        p.id for p in prompts
        if p.id in completions and not grade(completions[p.id], p) and baselines.get(p.id, 0) >= 1
    )


async def evaluate(base_url, api_key, data_dir, sleep):
    config = load_config(data_dir / "config.json")
    suites = load_suites(data_dir / "suites.csv", config.default_max_tokens)
    prompts = load_prompts(data_dir / "prompts.csv", suites)
    client = RelayClient(base_url, api_key, config.model)
    runner = Runner(client, config, **({"sleep": sleep} if sleep else {}))
    completions, failed = await runner.run_all(prompts)
    baselines = latest_baselines(await fetch_baselines(client, config.baseline_page_size))
    by_id = {p.id: p for p in prompts}
    return {
        "model": config.model,
        "answers": {pid: c.text for pid, c in sorted(completions.items())},
        "finish_reasons": {pid: c.finish_reason for pid, c in sorted(completions.items())},
        "completion_tokens": sum(c.tokens for c in completions.values()),
        "passed": sorted(pid for pid, c in completions.items() if grade(c, by_id[pid])),
        "blocked": sorted(runner.blocked),
        "failed": dict(sorted(failed.items())),
        "attempts": dict(sorted(runner.attempts.items())),
        "suites": suite_scores(prompts, completions),
        "regressions": find_regressions(prompts, completions, baselines),
        "new_prompts": sorted(p.id for p in prompts if p.added >= config.new_since),
    }


def build_report(base_url, api_key, data_dir=None, sleep=None):
    return asyncio.run(evaluate(base_url, api_key, Path(data_dir or DATA_DIR), sleep))
