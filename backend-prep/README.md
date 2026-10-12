# backend-prep

LeetCode-style practice for the Scale AI backend round: query flaky APIs, clean
messy data, build small services, and practise the spoken follow-ups.

## Start

```
cd backend-prep
../.venv/bin/python serve.py          # opens http://127.0.0.1:8765
```

* **Problems**: pick one, read the statement, code in the editor.
  * **Run** (`⌘/Ctrl + '`) executes your file's `if __name__ == "__main__":` block.
    Use it to print raw API responses and data before writing logic.
  * **Submit** (`⌘/Ctrl + Enter`) runs the tests and shows each case.
  * **Solution** tab: the reference solution (asks first if you haven't solved it).
  * The timer (top right) is per problem; mock rounds count against 60 minutes.
* **🧪 Tests tab** (every problem except 42): write the pytest tests yourself,
  as the interview expects. **Run on mine** runs them against your solution.
  **Submit tests** runs them against the reference (they must all pass) and
  against 4–12 hidden versions with realistic bugs planted (off-by-one paging,
  retrying a 400, sleeping after the last attempt, wrong tie-break...). The score
  is bugs caught; a bug you missed is shown after you submit. The Solution tab
  can reveal the official test suite as a model answer.
* **Mock rounds** (M1–M4): 60 minutes, three parts. Part 2 unlocks when Part 1's
  tests pass, like the real interview.
* **Debug** (the Debugging Practical): the 100 sets in `../scale-debug-sets`.
  Each set is an unfamiliar multi-file repo with a messy dataset and failing
  tests numbered 1 → 2 → 3. Find and fix every bug (MINI: 3 bugs / 30 min, FULL:
  6 bugs / 60 min) and explain each one.
  * File tree + editor; **Test 1 / Test 2 / Test 3 / Run all tests**, **▶ main.py**,
    **Diff** (your changes), **💡 Hint** (counted, gets more specific each time).
  * `tests/`, `data/` and the README are read-only, and tests always run on the
    originals. Changing `# VERIFIED` code is flagged and blocks "solved".
  * **My notes** for your explanations; **Ask about the code** for how-it-works
    answers; **Answer key** (after you try) shows each bug, found / missed, the
    why, the fix, the interviewer's follow-up questions, and why the VERIFIED
    red herrings are correct. Missed bug types are tallied on the Debug page.
  * Your copy lives in `debug-workspace/<set>/` (editable in VS Code too). It is
    built from each set's `interviewer/reference/` plus its bug edits, so the
    original sets are never modified. **Reset** starts a set over.
* **Flashcards**: the spoken follow-ups (scale-up, reliability, caching, data,
  interview habits). Answer out loud, then reveal.

Your code is saved to `workspace/<problem>.py`, so you can also edit it in VS Code.
The page reloads it when you switch back.

## Terminal only

```
../.venv/bin/python judge.py              # list problems + progress
../.venv/bin/python judge.py 09           # submit workspace/09-*.py
../.venv/bin/python judge.py 09 --run     # run your __main__ block
../.venv/bin/python judge.py 09 -v        # full tracebacks
../.venv/bin/python judge.py 09 --reset   # back to the starter code
../.venv/bin/python judge.py 09 --reveal  # print the reference solution
../.venv/bin/python judge.py 09 --tests   # grade YOUR tests (workspace/09-*_test.py) vs hidden bugs
../.venv/bin/python judge.py 09 --run-tests  # run your tests against your own solution
```

Debug from the terminal:

```
../.venv/bin/python debug.py               # list sets + progress
../.venv/bin/python debug.py 7             # run all tests on debug-workspace/set-007
../.venv/bin/python debug.py 7 --test 1    # just Test 1
../.venv/bin/python debug.py 7 --main      # run main.py
../.venv/bin/python debug.py 7 --hint / --reveal / --reset
```

## Suggested plan

| when | what |
|---|---|
| daily | 2–3 ★ problems (groups 1–5 and 8), then the 🧪 tests for one of them, then 5 flashcards |
| every few days | one group 6–7 problem (concurrency, services) |
| every other day | one Debug set: MINI on weekdays, FULL at the weekend, explaining each bug out loud |
| weekly | one mock round, timed, talking out loud |

When you solve one, read the reference solution anyway and compare structure,
naming and error handling. That's what the interviewer is grading.

## How it works

* `problems/<id>-<slug>/`: `problem.md`, `starter.py`, `solution.py`,
  `test_problem.py`, and usually `problem_api.py` (the mock API).
* `kit/`: the shared mock HTTP API (`MockAPI`: pagination, auth tokens,
  rate limits, scripted 5xx / 429 / timeouts / truncated bodies) and `FakeClock`,
  so retry and backoff code is tested without real sleeping.
* `progress.json`: your submissions and solved status.
* Adding problems: see `AUTHORING.md`; check with `judge.py --verify <id>`.
