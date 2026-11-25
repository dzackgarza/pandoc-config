#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRATCH="$(mktemp -d -t 'pandoc tikz paths XXXXXXXX')"
trap 'trash "$SCRATCH"' EXIT
mkdir "$SCRATCH/work"
cd "$SCRATCH/work"

export SVG_DIR="$SCRATCH/figure cache/rendered"
NONCE="$(date +%s%N)"
printf '\\begin{tikzcd}\nX_{%s} \\arrow[r] & Y\n\\end{tikzcd}\n' "$NONCE" > note.md

FAILURES=0
check() {
  local desc="$1"; shift
  if "$@"; then
    echo "  ✅ $desc"
  else
    echo "  ❌ $desc"
    FAILURES=$((FAILURES + 1))
  fi
}

echo "[1/1] a figure cache whose path has a space"
if pandoc --lua-filter="$REPO/filters/tikzcd.lua" -f markdown+raw_tex -t html note.md > note.html 2> filter.log; then
  rc=0
else
  rc=$?
fi
check "the filter succeeds" test "$rc" -eq 0
check "the page holds the figure as SVG" grep -q '<svg' note.html
check "the SVG is in the cache directory" compgen -G "$SVG_DIR/dzgtikz-*.svg"
check "the PDF is in the cache directory" compgen -G "$SVG_DIR/dzgtikz-*.pdf"
check "the filter makes no directory in the working directory" test -z "$(find . -mindepth 1 -type d)"

if [ "$FAILURES" -ne 0 ]; then
  sed 's/^/     /' filter.log
  echo "❌ $FAILURES tikz path checks failed"
  exit 1
fi
echo "✅ tikzcd filter paths"
