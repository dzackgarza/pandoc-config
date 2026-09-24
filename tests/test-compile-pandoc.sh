#!/usr/bin/env bash
# test-compile-pandoc.sh — the single-file compile-pandoc recipe end to end:
# cross-references resolve, and an export with an unresolved citation or a
# missing bibliography fails instead of writing a PDF.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRATCH="$(mktemp -d -t pandoc-compile-XXXXXXXX)"
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
export REPO
compile() {
  ZOTERO_GLOBAL_BIB="$1" just --justfile "$REPO/justfile" compile-pandoc "$2" "$3" >"$3.log" 2>&1
}

export -f compile

cat > refs.bib <<'EOF'
@article{FS86,
  author = {Friedman, Robert and Scattone, Francesco},
  title = {Type {III} degenerations of {K3} surfaces},
  journal = {Inventiones Mathematicae},
  volume = {83},
  year = {1986},
  pages = {1--39}
}
EOF

cat > references.md <<'EOF'
| $n$ | rank |
|----:|-----:|
|   1 |   10 |

: Ranks. {#tbl:ranks}

$$ x = 1 $$ {#eq:one}

See @tbl:ranks and @eq:one, following [@FS86].
EOF

echo "[1/3] cross-references and citations resolve"
check "export succeeds" compile "$SCRATCH/refs.bib" references.md resolved
check "table reference is numbered" \
  bash -c "pdftotext resolved-*.pdf - | grep -q 'See tbl. 1 and eq. (1)'"
check "citation is resolved" bash -c "pdftotext resolved-*.pdf - | grep -q 'FS86'"

echo "[2/3] an unknown citation key fails the export"
printf 'See [@NoSuchKey2099].\n' > unknown.md
check "export fails" bash -c "! compile '$SCRATCH/refs.bib' unknown.md unknown"
check "no PDF is written" bash -c "! ls unknown-*.pdf"
check "the failure names the key" grep -q "Citation 'NoSuchKey2099'" unknown.log

echo "[3/3] a missing bibliography fails the export before pandoc runs"
check "export fails" bash -c "! compile /nonexistent/refs.bib references.md nobib"
check "the failure names the file" grep -q "/nonexistent/refs.bib does not exist" nobib.log

if [ "$FAILURES" -ne 0 ]; then
  echo "❌ $FAILURES check(s) failed"
  exit 1
fi
echo "✅ compile-pandoc checks passed"
