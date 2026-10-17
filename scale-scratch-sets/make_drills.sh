#!/usr/bin/env bash
# Create blank practice rounds for every scratch problem.
#
#   ./make_drills.sh            # 10 rounds per problem (skips rounds that already exist)
#   ./make_drills.sh 15         # up to 15 rounds
#   ./make_drills.sh reset 01 3 # wipe drills/01-*/round-03 back to blank
#
# Each round gets: SPEC.md, data/ (if the problem has it), empty code folders, grade.sh.
set -euo pipefail
cd "$(dirname "$0")"
HERE="$(pwd)"

make_round() {  # $1 = problem dir, $2 = round number
  local prob="$1" n
  n=$(printf "%02d" "$2")
  local dest="drills/$prob/round-$n"
  [ -d "$dest" ] && return 0
  mkdir -p "$dest/tests"
  cp "$prob/SPEC.md" "$dest/"
  [ -d "$prob/data" ] && cp -R "$prob/data" "$dest/data"
  [ -d "$prob/tools" ] && cp -R "$prob/tools" "$dest/tools"
  for code_dir in app lb output; do
    [ -d "$prob/$code_dir" ] && mkdir -p "$dest/$code_dir"
  done
  cat > "$dest/grade.sh" <<EOF
#!/usr/bin/env bash
# Run the hidden grader against this round. Extra args go to pytest (e.g. -x, -k part1).
cd "\$(dirname "\$0")"
SOLUTION_DIR="\$(pwd)" "$HERE/../.venv/bin/python" -m pytest "$HERE/$prob/_grader" -q -p no:cacheprovider "\$@" | tee .last_grade.txt
echo "\$(date '+%Y-%m-%d %H:%M')  $prob  round-$n  \$(tail -1 .last_grade.txt)" >> "$HERE/drills/PROGRESS.log"
EOF
  chmod +x "$dest/grade.sh"
  echo "created $dest"
}

if [ "${1:-}" = "reset" ]; then
  prob=$(ls -d 0"${2#0}"-*/ 2>/dev/null | head -1); prob="${prob%/}"
  [ -n "$prob" ] || { echo "no problem $2"; exit 1; }
  rm -rf "drills/$prob/round-$(printf "%02d" "$3")"
  make_round "$prob" "$3"
  exit 0
fi

rounds="${1:-10}"
for prob in 0*-*/; do
  prob="${prob%/}"
  for i in $(seq 1 "$rounds"); do make_round "$prob" "$i"; done
done
