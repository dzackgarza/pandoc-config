#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FAILURES=0

render() {
  local filter="$1" to="$2" meta="$3"
  printf -- '---\n%s\n---\n\nThe claim.\n\n::: proof\nThe secret argument.\n:::\n\n::: solution\nThe secret answer.\n:::\n\n::: remark\nA kept remark.\n:::\n' "$meta" \
    | pandoc --lua-filter="$REPO/filters/$filter" -f markdown -t "$to"
}

expect() {
  local desc="$1" output="$2" present="$3" absent="$4"
  if [[ "$output" == *"$present"* && "$output" != *"$absent"* ]]; then
    echo "  ✅ $desc"
  else
    echo "  ❌ $desc"
    printf '%s\n' "$output" | sed 's/^/     /'
    FAILURES=$((FAILURES + 1))
  fi
}

run() {
  local output
  if output="$(render "$@" 2>&1)"; then
    printf '%s' "$output"
  else
    printf 'FILTER FAILED: %s' "$output"
  fi
}

echo "[1/2] hide_solutions_pdf.lua"
out="$(run hide_solutions_pdf.lua latex 'kill_proofs: true')"
expect "kill_proofs replaces a proof by its notice" "$out" "Proof omitted." "The secret argument."
expect "kill_proofs replaces a solution by its notice" "$out" "Solution omitted." "The secret answer."
expect "kill_proofs keeps a div of another class" "$out" "A kept remark." "FILTER FAILED"
out="$(run hide_solutions_pdf.lua latex 'title: t')"
expect "without kill_proofs a proof stays" "$out" "The secret argument." "omitted"

echo "[2/2] hide_solutions_html.lua"
out="$(run hide_solutions_html.lua html 'hide_proofs: true')"
expect "hide_proofs folds a proof into a details element" "$out" "<details><summary><i>(Click to expand proof)</i></summary>" "FILTER FAILED"
expect "hide_proofs keeps the text of the proof" "$out" "The secret argument." "FILTER FAILED"
out="$(run hide_solutions_html.lua html 'kill_proofs: true')"
expect "kill_proofs removes a proof and a solution" "$out" "A kept remark." "The secret"
out="$(run hide_solutions_html.lua html 'title: t')"
expect "without a setting a proof stays open" "$out" "The secret argument." "<details>"

if [ "$FAILURES" -ne 0 ]; then
  echo "❌ $FAILURES hide-solutions checks failed"
  exit 1
fi
echo "✅ hide-solutions filters"
