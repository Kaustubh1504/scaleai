#!/usr/bin/env bash
# Run the hidden grader against this round. Extra args go to pytest (e.g. -x, -k part1).
cd "$(dirname "$0")"
SOLUTION_DIR="$(pwd)" "/Users/kaustubh/Desktop/scaleai/scale-scratch-sets/../.venv/bin/python" -m pytest "/Users/kaustubh/Desktop/scaleai/scale-scratch-sets/05-task-processor/_grader" -q -p no:cacheprovider "$@" | tee .last_grade.txt
echo "$(date '+%Y-%m-%d %H:%M')  05-task-processor  round-08  $(tail -1 .last_grade.txt)" >> "/Users/kaustubh/Desktop/scaleai/scale-scratch-sets/drills/PROGRESS.log"
