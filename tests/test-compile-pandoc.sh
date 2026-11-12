#!/usr/bin/env bash
# test-compile-pandoc.sh — the single-file compile-pandoc recipe end to end:
# cross-references resolve, each file of PANDOC_BIB_SOURCE is a bibliography,
# and an export with an unresolved citation or a
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

echo "[1/6] cross-references and citations resolve"
check "export succeeds" compile "$SCRATCH/refs.bib" references.md resolved
check "table reference is numbered" \
  bash -c "pdftotext resolved-*.pdf - | grep -q 'See tbl. 1 and eq. (1)'"
check "citation is resolved" bash -c "pdftotext resolved-*.pdf - | grep -q 'FS86'"

echo "[2/6] backslash-delimited math is math"
printf 'Inline \\(x_i^2\\) and display\n\n\\[\n\\sum_{n \\ge 1} a_n\n\\]\n' > backslash.md
check "export succeeds" compile "$SCRATCH/refs.bib" backslash.md backslash
check "inline math is typeset, not printed as (x_i^2)" \
  bash -c "! pdftotext backslash-*.pdf - | grep -qF '(x_i^2)'"
check "the tex source holds math, not escaped parentheses" \
  grep -qF '\(x_i^2\)' .build_pandoc/output.tex

echo "[3/6] an unknown citation key fails the export"
printf 'See [@NoSuchKey2099].\n' > unknown.md
check "export fails" bash -c "! compile '$SCRATCH/refs.bib' unknown.md unknown"
check "no PDF is written" bash -c "! ls unknown-*.pdf"
check "the failure names the key" grep -q "Citation 'NoSuchKey2099'" unknown.log

echo "[4/6] a missing bibliography fails the export before pandoc runs"
check "export fails" bash -c "! compile /nonexistent/refs.bib references.md nobib"
check "the failure names the file" grep -q "/nonexistent/refs.bib does not exist" nobib.log

echo "[5/6] each file of PANDOC_BIB_SOURCE is a bibliography of the export"
# Keys that no library of a workstation has: the export finds them only in
# these two files.
sed "s/@article{FS86,/@article{StepFiveDegenerations,/" refs.bib > first.bib
cat > book.bib <<'EOF'
@book{StepFivePackings,
  author = {Conway, John H. and Sloane, Neil J. A.},
  title = {Sphere Packings, Lattices and Groups},
  publisher = {Springer},
  year = {1988}
}
EOF
mkdir chapter
printf 'Degenerations [@StepFiveDegenerations] and packings [@StepFivePackings].\n' > chapter/two.md
check "export succeeds" bash -c "cd chapter && PANDOC_BIB_SOURCE='$SCRATCH/first.bib:$SCRATCH/book.bib' \
  just --justfile '$REPO/justfile' compile-pandoc two.md two > two.log 2>&1"
check "the citation of the first file is resolved" \
  bash -c "pdftotext chapter/two-*.pdf - | grep -q 'FS86'"
check "the citation of the second file is resolved" \
  bash -c "pdftotext chapter/two-*.pdf - | grep -q 'CS88'"
check "the folder of the document gets no bibliography link" bash -c "! test -e chapter/global.bib"

echo "[6/6] an empty PANDOC_BIB_SOURCE is an export without a bibliography"
mkdir plain
printf 'A lattice is a free abelian group.\n' > plain/plain.md
check "export succeeds" bash -c "cd plain && PANDOC_BIB_SOURCE='' \
  just --justfile '$REPO/justfile' compile-pandoc plain.md plain > plain.log 2>&1"
check "the tex source names no bibliography" bash -c "! grep -q addbibresource plain/.build_pandoc/output.tex"

if [ "$FAILURES" -ne 0 ]; then
  echo "❌ $FAILURES check(s) failed"
  exit 1
fi
echo "✅ compile-pandoc checks passed"
