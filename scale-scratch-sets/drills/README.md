# Drills: 10 blank rounds per problem

```
drills/<problem>/round-01 … round-10/
    SPEC.md     the problem
    data/       input files (01, 03)
    app/ lb/    empty: your code goes here (05: processor.py in the round folder)
    tests/      empty: your tests
    grade.sh    runs the hidden grader against THIS folder
```

## One round
```bash
cd drills/01-csv-llm-pipeline/round-01
# start a timer, read SPEC.md, write app/main.py + tests/
../../../../.venv/bin/uvicorn app.main:app --reload   # try it by hand
../../../../.venv/bin/python -m pytest tests -q       # your own tests
./grade.sh                                            # hidden grader (when time's up)
./grade.sh -x -k part1                                # just Part 1, stop at first failure
```

Every `grade.sh` run adds a line to `drills/PROGRESS.log`, so you can watch your score go up across rounds.

## More rounds / redo a round
```bash
cd scale-scratch-sets
./make_drills.sh 15          # add rounds 11–15 everywhere
./make_drills.sh reset 01 3  # wipe 01 round-03 back to blank
```

Rule: don't open earlier rounds or the worked solution in `01-csv-llm-pipeline/app/main.py` during a round.
