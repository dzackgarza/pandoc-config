#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRATCH="$(mktemp -d -t pandoc-project-refs-XXXXXXXX)"
trap 'rm -rf "$SCRATCH"' EXIT

FAILURES=0
check() {
  local desc="$1"; shift
  if "$@" >/dev/null; then
    echo "  ✅ $desc"
  else
    echo "  ❌ $desc"
    FAILURES=$((FAILURES + 1))
  fi
}

echo "[1/9] theorem prefix registry matches zettlr-pandoc"
EXPECTED_PREFIXES="ass clm conj cons conv cor def ex exr lem not obs prob prop qst rmk thm warn"
ACTUAL_PREFIXES=$(sed -n '/^local ref_prefixes = {/,/^}/p' \
    "$REPO/filters/convert_amsthm_envs.lua" \
  | grep -oE '(\["?)?[a-z]+("?\])?=true' | sed -E 's/^\["?//; s/"?\]?=true$//' | sort | xargs)
check "filter ref_prefixes == THEOREM_DIV_PREFIXES keys ($EXPECTED_PREFIXES)" \
  test "$ACTUAL_PREFIXES" = "$EXPECTED_PREFIXES"

mkdir -p "$SCRATCH/workspace"
cp "$REPO/tests/fixtures/theorem-references/workspace/Theorems.md" "$SCRATCH/workspace/"
cp "$REPO/tests/fixtures/theorem-references/workspace/Halphen_Surfaces.md" "$SCRATCH/workspace/"
cp "$REPO/tests/fixtures/theorem-references/references.bib" "$SCRATCH/workspace/refs.bib"

cd "$SCRATCH/workspace"

echo "[2/9] compile-pandoc-project tex stage (Theorems.md Halphen_Surfaces.md)"
just --justfile "$REPO/justfile" \
  _compile-pandoc-tex crossref "$REPO/templates/research_draft.tex" "$SCRATCH/workspace/refs.bib" .build_pandoc \
  Theorems.md Halphen_Surfaces.md

TEX=".build_pandoc/output.tex"
check "intermediate .tex produced" test -f "$TEX"

POS1=$(grep -nF '\label{structural-results-for-enriques' "$TEX" | head -1 | cut -d: -f1)
POS2=$(grep -nF '\label{halphen-surfaces-of-index-two' "$TEX" | head -1 | cut -d: -f1)
check "order markers found in .tex" test -n "$POS1" -a -n "$POS2"
check "file 1 content precedes file 2 content ($POS1 < $POS2)" test "$POS1" -lt "$POS2"

check 'theorem div with explicit id emits \label{thm:torelli}' grep -F '\label{thm:torelli}' "$TEX"
check 'bare @thm:torelli in the other file becomes \cref{thm:torelli}' grep -F '\cref{thm:torelli}' "$TEX"
check 'cluster [@thm:torelli; @lem:kodaira:embedding] becomes \cref{thm:torelli,lem:kodaira:embedding}' \
  grep -F '\cref{thm:torelli,lem:kodaira:embedding}' "$TEX"
check 'theorem environment emitted (\begin{theorem})' grep -F '\begin{theorem}' "$TEX"
check 'bibliography citation [@Ols04, Lem. 7.1] untouched (natbib/biblatex path)' \
  grep -F '\autocite[Lem. 7.1]{Ols04}' "$TEX"

flat_grep() { tr -s '[:space:]' ' ' < "$1" | grep -qF "$2"; }
check 'prefixed citation [see @thm:torelli] keeps its prefix (see \cref{thm:torelli})' \
  flat_grep "$TEX" 'see \cref{thm:torelli}'
check 'suffixed citation [@thm:torelli, part (ii)] keeps its suffix (\cref{thm:torelli}, part (ii))' \
  flat_grep "$TEX" '\cref{thm:torelli}, part (ii)'
check 'suppressed citation [-@thm:torelli] emits number-only \ref{thm:torelli}' \
  grep -F '\ref{thm:torelli}' "$TEX"
check 'cluster items keep per-item text (see \cref{thm:torelli}; \cref{lem:kodaira:embedding}, part (ii))' \
  flat_grep "$TEX" 'see \cref{thm:torelli}; \cref{lem:kodaira:embedding}, part (ii)'
check 'mixed cluster @lem:kodaira:embedding [@Ols04, Lem. 7.1] keeps both references' \
  flat_grep "$TEX" '\cref{lem:kodaira:embedding} \autocite[Lem. 7.1]{Ols04}'

echo "[3/9] ordered run with a filename containing a space"
cp "$REPO/tests/fixtures/theorem-references/workspace/Coble_Lattice_Table.md" \
   "$SCRATCH/workspace/Coble Lattice Table.md"
just --justfile "$REPO/justfile" \
  _compile-pandoc-tex crossref "$REPO/templates/research_draft.tex" "$SCRATCH/workspace/refs.bib" .build_spaced \
  Theorems.md "Coble Lattice Table.md" Halphen_Surfaces.md

TEX_SPACED=".build_spaced/output.tex"
check "spaced-run .tex produced" test -f "$TEX_SPACED"
SPOS1=$(grep -nF '\label{structural-results-for-enriques' "$TEX_SPACED" | head -1 | cut -d: -f1)
SPOS2=$(grep -nF '\label{coble-lattices-and-rational-surfaces' "$TEX_SPACED" | head -1 | cut -d: -f1)
SPOS3=$(grep -nF '\label{halphen-surfaces-of-index-two' "$TEX_SPACED" | head -1 | cut -d: -f1)
check "spaced-run order markers found" test -n "$SPOS1" -a -n "$SPOS2" -a -n "$SPOS3"
check "spaced file's content lands in order ($SPOS1 < $SPOS2 < $SPOS3)" \
  bash -c "test '$SPOS1' -lt '$SPOS2' && test '$SPOS2' -lt '$SPOS3'"
check "cross-file table ref from spaced file resolves (\\cref{tbl:coble-lattices})" \
  grep -F '\cref{tbl:coble-lattices}' "$TEX_SPACED"

echo "[4/9] proof divs unnumbered/unlabeled"
check 'proof div emitted as \begin{proof}' grep -F '\begin{proof}' "$TEX"
check 'proof div id produced no label (thm:should-not-index absent)' \
  bash -c "! grep -q 'thm:should-not-index' '$TEX'"
check 'empty-key id produced no label (\label{thm:} absent)' \
  bash -c "! grep -qF '\\label{thm:}' '$TEX'"

echo "[5/9] compile-pandoc attribute-style sample byte-stability"
mkdir -p "$SCRATCH/single"
cd "$SCRATCH/single"
cp "$REPO/tests/fixtures/theorem-references/attribute_style_sample.md" .
cp "$REPO/tests/fixtures/theorem-references/references.bib" refs.bib
just --justfile "$REPO/justfile" \
  _compile-pandoc-tex no-crossref "$REPO/templates/research_draft.tex" refs.bib .build_pandoc \
  attribute_style_sample.md
check "attribute-style sample byte-stable (byte-identical to pre-change baseline; sample has no theorem citations)" \
  bash -c "grep -v '^%' .build_pandoc/output.tex | diff '$REPO/tests/fixtures/theorem-references/expected_attribute_style.tex' -"

echo "[6/9] compile-pandoc legacy path: theorem citations emit \\cref"
mkdir -p "$SCRATCH/legacy"
cd "$SCRATCH/legacy"
cp "$REPO/tests/fixtures/theorem-references/legacy_theorem_citation_sample.md" .
cp "$REPO/tests/fixtures/theorem-references/references.bib" refs.bib
just --justfile "$REPO/justfile" \
  _compile-pandoc-tex no-crossref "$REPO/templates/research_draft.tex" "$SCRATCH/legacy/refs.bib" .build_pandoc \
  legacy_theorem_citation_sample.md
TEX_LEGACY=".build_pandoc/output.tex"
check 'legacy-path bare @thm:legacy-torelli becomes \cref{thm:legacy-torelli}' \
  grep -F '\cref{thm:legacy-torelli}' "$TEX_LEGACY"
check 'legacy-path prefixed citation keeps its prefix (see \cref{thm:legacy-torelli})' \
  flat_grep "$TEX_LEGACY" 'see \cref{thm:legacy-torelli}'

echo "[7/9] plain-branch latexmk compile of the all-theorem-classes fixture"
mkdir -p "$SCRATCH/latexmk-plain"
cd "$SCRATCH/latexmk-plain"
cp "$SCRATCH/workspace/.build_pandoc/output.tex" .
LATEXMK_RC=0
TEXINPUTS=".:$REPO/styles//:$REPO/config//:" BIBINPUTS=".:" \
  latexmk -pdf -interaction=nonstopmode -gg output.tex > latexmk.log 2>&1 \
  || LATEXMK_RC=$?
if [ "$LATEXMK_RC" -ne 0 ]; then
  echo "  latexmk exited $LATEXMK_RC; LaTeX errors:"
  { grep -n '^!' output.log | head -20; } || true
fi
check "plain-branch latexmk exits 0 (was 12: assumption/warning undefined)" \
  test "$LATEXMK_RC" -eq 0
check "output.log has no undefined-environment errors" \
  bash -c "! grep -q 'Environment .* undefined' output.log"

echo "[8/9] _compile-pandoc-tex rejects an unknown crossref_mode"
mkdir -p "$SCRATCH/mode-probe"
cd "$SCRATCH/mode-probe"
MODE_RC=0
just --justfile "$REPO/justfile" \
  _compile-pandoc-tex crosref research_draft.tex refs.bib .build x.md \
  > mode-probe.out 2>&1 || MODE_RC=$?
check "unknown mode exits nonzero" test "$MODE_RC" -ne 0
check "unknown mode names the flag and the accepted values" \
  grep -q "unknown crossref_mode 'crosref'" mode-probe.out
check "validation precedes side effects (no build dir created)" \
  bash -c "! test -e '$SCRATCH/mode-probe/.build'"

echo "[9/9] arxiv-branch latexmk compile of the all-theorem-classes fixture"
mkdir -p "$SCRATCH/arxiv-ws"
cp "$REPO/tests/fixtures/theorem-references/workspace/Theorems.md" "$SCRATCH/arxiv-ws/"
cp "$REPO/tests/fixtures/theorem-references/references.bib" "$SCRATCH/arxiv-ws/refs.bib"
cd "$SCRATCH/arxiv-ws"
just --justfile "$REPO/justfile" \
  _compile-pandoc-tex crossref "$REPO/templates/research_paper.tex" \
  "$SCRATCH/arxiv-ws/refs.bib" .build_arxiv Theorems.md
mkdir -p "$SCRATCH/latexmk-arxiv"
cd "$SCRATCH/latexmk-arxiv"
cp "$SCRATCH/arxiv-ws/.build_arxiv/output.tex" .
ARXIV_RC=0
TEXINPUTS=".:$REPO/styles//:$REPO/config//:" BIBINPUTS=".:" \
  latexmk -pdf -interaction=nonstopmode -gg output.tex > latexmk.log 2>&1 \
  || ARXIV_RC=$?
if [ "$ARXIV_RC" -ne 0 ]; then
  echo "  latexmk exited $ARXIV_RC; LaTeX errors:"
  { grep -n '^!' output.log | head -20; } || true
fi
check "arxiv-branch latexmk exits 0 (was 12: exercise undefined)" \
  test "$ARXIV_RC" -eq 0
check "arxiv output.log has no undefined-environment errors" \
  bash -c "! grep -q 'Environment .* undefined' output.log"
check "arxiv output.log has no LaTeX errors at all" \
  bash -c "! grep -q '^!' output.log"

if [ "$FAILURES" -eq 0 ]; then
  echo "✅ test-project-references: all assertions passed"
else
  echo "❌ test-project-references: $FAILURES assertion(s) failed"
  exit 1
fi
