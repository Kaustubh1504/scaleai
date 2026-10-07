"""Render ANSWER_KEY.md, INTERVIEWER_NOTES.md and SCORING.md from interviewer/bugs.json.

    python tools/render_docs.py set-001 [set-002 ...]

Run after verify_set.py so the observed failures in verification.json are current.
"""
from __future__ import annotations

import difflib
import json
import sys

from common import load_spec, set_dir

TIMELINE = {
    "MINI": [("0-3", "Orient: read README spec, skim layout, run the tests."),
             ("3-25", "Debug: work Test 1 then Test 2; expect ~7 min per bug."),
             ("25-30", "Explain: candidate walks through each fix (symptom, location, why, fix).")],
    "FULL": [("0-6", "Orient: read README spec and data, skim layout, run the tests."),
             ("6-50", "Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug."),
             ("50-60", "Explain: candidate walks through each fix (symptom, location, why, fix).")],
}


def fix_diff(bug: dict) -> str:
    """Diff from the candidate's (buggy) text to the reference text, one hunk per edit."""
    hunks = []
    edits = [(bug["file"], bug["old"], bug["new"])]
    edits += [(e.get("file", bug["file"]), e["old"], e["new"]) for e in bug.get("extra", [])]
    for path, old, new in edits:
        lines = difflib.unified_diff(new.splitlines(), old.splitlines(), lineterm="", n=2)
        body = [ln for ln in lines if not ln.startswith(("---", "+++", "@@"))]
        if len(edits) > 1:
            body.insert(0, f"# {path}")
        hunks.append("\n".join(body))
    return "\n\n".join(hunks)


def answer_key(spec: dict, observed: dict) -> str:
    out = [f"# {spec['id']} answer key: {spec['title']}", ""]
    out += [f"**Domain:** {spec['domain']}  |  **Length:** {spec['length']}  |  **Difficulty:** {spec['difficulty']}", ""]
    if spec.get("format") == "one_to_one":
        out += ["**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.", "",
                "| Failing test | Bug |", "|---|---|"]
        out += [f"| `{b['test']}` | {b['id']} {b['title']} |" for b in spec["bugs"]]
        out.append("")
    else:
        out += ["**Format:** multi-bug. Tests can fail for several bugs at once, and some bugs stay hidden until others are fixed.", ""]
    out += ["## Failing pattern with all bugs present", ""]
    for tid in observed.get("ALL", {}).get("failing_tests", []):
        out.append(f"- `{tid}`")
    out += ["", "## Bugs (recommended order)", ""]
    for bug in spec["bugs"]:
        out += [f"### {bug['id']}: {bug['title']}", ""]
        out.append(f"- **Type:** {bug['type']}")
        out.append(f"- **Symptom:** {bug['symptom']}")
        out.append(f"- **Location:** `{bug['file']}` → `{bug['function']}`")
        out.append(f"- **Why it fails:** {bug['why']}")
        if bug.get("test"):
            out.append(f"- **Failing test:** `{bug['test']}`")
        out.append(f"- **Unblocks:** {bug['unblocks']}")
        if bug.get("masked_by"):
            out.append(f"- **Masked:** invisible until {', '.join(bug['masked_by'])} is fixed (identical test output either way).")
        if bug.get("visible_only_in"):
            out.append(f"- **Masked:** only surfaces in {', '.join(bug['visible_only_in'])}.")
        out += ["", "Fix:", "", "```diff", fix_diff(bug), "```", ""]
        obs = observed.get(bug["id"])
        if obs and obs["failures"]:
            tid, msg = next(iter(sorted(obs["failures"].items())))
            msg = msg.strip().replace("```", "'''")
            if len(msg) > 400:
                msg = msg[:400] + " ..."
            out += [f"Observed with only this bug applied (`{tid}`):", "", "```", msg, "```", ""]
    if spec.get("verified"):
        out += ["## Red herrings (marked `# VERIFIED`, genuinely correct)", ""]
        for v in spec["verified"]:
            out.append(f"- `{v['file']}` → `{v['symbol']}`: {v['why_correct']}")
        out.append("")
    return "\n".join(out)


def interviewer_notes(spec: dict) -> str:
    out = [f"# {spec['id']} interviewer notes", ""]
    out += [f"**Scenario:** {spec['scenario']}", ""]
    out += ["## Timeline", "", "| Minutes | Phase |", "|---|---|"]
    out += [f"| {m} | {p} |" for m, p in TIMELINE[spec["length"]]]
    out += ["", "Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,",
            "and give one level at a time. Record every hint on the scoring sheet.", ""]
    out += ["## Hint ladders", ""]
    for bug in spec["bugs"]:
        n, area, exact = bug["hints"]
        out += [f"### {bug['id']}: {bug['title']}", "",
                f"1. **Nudge:** {n}", f"2. **Area:** {area}", f"3. **Exact:** {exact}", ""]
    out += ["## \"Why did that fix work?\" probes", ""]
    for bug in spec["bugs"]:
        out.append(f"**{bug['id']}**")
        out += [f"- {q}" for q in bug["probes"]]
        out.append("")
    if spec.get("verified"):
        out += ["## If the candidate edits a `# VERIFIED` region", "",
                "Stop them and ask them to show, from the spec and the data, why it is wrong. "
                "These regions are correct:", ""]
        out += [f"- `{v['file']}` → `{v['symbol']}`: {v['why_correct']}" for v in spec["verified"]]
        out.append("")
    return "\n".join(out)


def context_assistant(spec: dict) -> str:
    out = [f"# {spec['id']} context questions for an AI assistant", "",
           "Use these to practise asking an assistant for **context** (what a file or function does,",
           "where a value comes from, what the data looks like) rather than for the fix. The answers",
           "describe what the candidate repo's code does. They don't say whether it is correct.", "",
           "Interviewers: if the candidate has an assistant, questions like these are fair game.",
           "\"What's wrong with this?\" or \"Fix test 2\" is not.", ""]
    for n, item in enumerate(spec["context_qa"], 1):
        out += [f"### {n}. {item['q']}", "", item["a"], ""]
    return "\n".join(out)


def scoring(spec: dict) -> str:
    out = [f"# {spec['id']} scoring sheet", "",
           f"Candidate: ________________   Date: ________   Interviewer: ________", "",
           "| Bug | Found & fixed | Minutes | Hints used (0-3) | Explanation (1-4) |",
           "|---|---|---|---|---|"]
    for bug in spec["bugs"]:
        out.append(f"| {bug['id']} {bug['title']} | ☐ | | | |")
    total = len(spec["bugs"])
    out += ["", "## Explanation quality", "",
            "| Score | Meaning |", "|---|---|",
            "| 1 | Names the symptom only (\"Test 2 fails\"). |",
            "| 2 | Symptom + location (file and function). |",
            "| 3 | Symptom + location + why the code produces that output. |",
            "| 4 | All of the above + the fix stated clearly, and why it does not break anything else. |",
            "", "## Overall", "",
            f"- **Strong:** all {total} bugs fixed, ≤ 2 hints total, average explanation ≥ 3.",
            f"- **Pass:** ≥ {total - 1} bugs fixed (all tests passing for that set requires all {total}), ≤ 4 hints, average explanation ≥ 2.5.",
            "- **Below bar:** fewer bugs, heavy hint use, or edits to tests/data/`# VERIFIED` code.",
            "", "Notes:", "", ""]
    return "\n".join(out)


def main(argv: list[str]) -> int:
    for set_id in argv:
        spec = load_spec(set_id)
        idir = set_dir(set_id) / "interviewer"
        vpath = idir / "verification.json"
        observed = json.loads(vpath.read_text()) if vpath.exists() else {}
        (idir / "ANSWER_KEY.md").write_text(answer_key(spec, observed))
        (idir / "INTERVIEWER_NOTES.md").write_text(interviewer_notes(spec))
        (idir / "SCORING.md").write_text(scoring(spec))
        (idir / "CONTEXT_ASSISTANT.md").write_text(context_assistant(spec))
        print(f"rendered docs for {set_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
