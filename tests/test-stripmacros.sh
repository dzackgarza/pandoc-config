#!/usr/bin/env bash
# test-stripmacros.sh — bin/pandoc_stripmacros.sh expands the macros of
# styles/macros (through their generated \newcommand projection) and reads
# no environment variable to find them or its filters.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRATCH="$(mktemp -d -t pandoc-stripmacros-XXXXXXXX)"
trap 'rm -rf "$SCRATCH"' EXIT
cd "$SCRATCH"

FAILURES=0
check() {
  local desc="$1"; shift
  if "$@" >/dev/null 2>&1; then
    echo "  ✅ $desc"
  else
    echo "  ❌ $desc"
    FAILURES=$((FAILURES + 1))
  fi
}

printf 'The set $\\theset{x \\in X}$ and the ring $\\ZZ$.\n' > note.md

echo "[1/2] the central macros are expanded"
check "stripmacros succeeds without PANDOC_DIR" \
  bash -c "env -u PANDOC_DIR -u PANDOC_RESOURCE_PATH '$REPO/bin/pandoc_stripmacros.sh' note.md > stripped.md 2> strip.log"
check "the output keeps the text" grep -q 'and the ring' stripped.md
check "\\theset is expanded to its definition" grep -qF '\left\{' stripped.md
check "no macro of styles/macros is left" bash -c "! grep -qE '\\\\(theset|ZZ)([^A-Za-z]|$)' stripped.md"
check "the definitions are not in the output" bash -c "! grep -q newcommand stripped.md"

echo "[2/2] a missing input fails"
check "stripmacros fails" bash -c "! '$REPO/bin/pandoc_stripmacros.sh' /nonexistent/note.md > missing.md 2> missing.log"
check "the failure names the file" grep -q '/nonexistent/note.md' missing.log

if [ "$FAILURES" -ne 0 ]; then
  echo "❌ $FAILURES check(s) failed"
  exit 1
fi
echo "✅ stripmacros checks passed"
