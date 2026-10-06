# Scale-style debugging practice library

100 practice codebases that mimic the "Debugging Practical" round: an unfamiliar
multi-file Python repo, a small messy dataset, and numbered failing tests.

## Layout

```
manifest.json            plan + status for all 100 sets (resumable source of truth)
set-NNN/
  candidate/             the buggy repo; hand this to the candidate
  interviewer/
    reference/           the correct codebase (tests pass)
    bugs.json            authored bug spec: exact (file, old, new) edits + docs text
    verification.json    observed failures per bug (written by verify_set.py)
    ANSWER_KEY.md  INTERVIEWER_NOTES.md  SCORING.md   (rendered from bugs.json)
tools/
  plan.py                seed or extend manifest.json (safe to re-run)
  verify_set.py          mutation check, timing, candidate generation, hint grep
  render_docs.py         answer key / notes / scoring sheet from bugs.json
  summary.py             batch summary table
  package.py             zip candidate/ and interviewer/ per set into dist/
```

## Building a set

1. Write `interviewer/reference/` (README spec, data, package, tests) and make it pass.
2. Write `interviewer/bugs.json`.
3. `python tools/verify_set.py set-NNN`: regenerates `candidate/`, and marks the set
   `verified` in the manifest only if every check passes.
4. `python tools/render_docs.py set-NNN`

To resume: `python tools/summary.py` shows the next pending set. Use Python 3.10+
(`../.venv/bin/python` here).
