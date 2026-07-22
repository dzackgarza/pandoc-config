#!/usr/bin/env bash
# test-project-references.sh — proof harness for compile-pandoc-project
# (ordered multi-file inputs, workspace-resolved theorem references) and
# for byte-stability of the compile-pandoc attribute-style theorem path.
#
# Fixture provenance: workspace/*.md are copies of
# zettlr-pandoc/test/fixtures/reference-workspace/ProjectA/ files
# (Theorems.md verbatim; Halphen_Surfaces.md with its cross-file lemma
# key aligned to lem:kodaira:embedding and a bare @thm:torelli
# reference added so both citation shapes are exercised).
#
# Assertions run on the intermediate .tex only. Full latexmk/PDF runs
# are owned by the recipes' normal use, so this script invokes the
# recipes' pandoc stage (_compile-pandoc-tex), which is exactly the
# first dependency of compile-pandoc-project ("crossref" mode) and of
# compile-pandoc ("no-crossref" mode).
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

# --- Workspace setup -------------------------------------------------
mkdir -p "$SCRATCH/workspace"
cp "$REPO/tests/fixtures/theorem-references/workspace/Theorems.md" "$SCRATCH/workspace/"
cp "$REPO/tests/fixtures/theorem-references/workspace/Halphen_Surfaces.md" "$SCRATCH/workspace/"
cp "$REPO/tests/fixtures/theorem-references/references.bib" "$SCRATCH/workspace/refs.bib"

cd "$SCRATCH/workspace"

# --- 1. compile-pandoc-project pandoc stage: two ordered inputs ------
echo "[1/3] compile-pandoc-project tex stage (Theorems.md Halphen_Surfaces.md)"
just --justfile "$REPO/justfile" \
  _compile-pandoc-tex crossref research_draft.tex "$SCRATCH/workspace/refs.bib" .build_pandoc \
  Theorems.md Halphen_Surfaces.md

TEX=".build_pandoc/output.tex"
check "intermediate .tex produced" test -f "$TEX"

# Source order: file 1 content precedes file 2 content (section labels
# are single tokens, immune to the writer's line wrapping)
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

# --- 2. proof divs stay unlabeled ------------------------------------
echo "[2/3] proof divs unnumbered/unlabeled"
check 'proof div emitted as \begin{proof}' grep -F '\begin{proof}' "$TEX"
check 'proof div id produced no label (thm:should-not-index absent)' \
  bash -c "! grep -q 'thm:should-not-index' '$TEX'"
check 'empty-key id produced no label (\label{thm:} absent)' \
  bash -c "! grep -qF '\\label{thm:}' '$TEX'"

# --- 3. compile-pandoc attribute path: byte-for-byte vs baseline -----
# The baseline was generated with the pre-change filter at commit
# 81792cc; this run uses compile-pandoc's tex stage (its exact defaults:
# no-crossref, research_draft.tex, bib symlinked as global.bib).
echo "[3/3] compile-pandoc attribute-style path byte-stability"
mkdir -p "$SCRATCH/single"
cd "$SCRATCH/single"
cp "$REPO/tests/fixtures/theorem-references/attribute_style_sample.md" .
cp "$REPO/tests/fixtures/theorem-references/references.bib" refs.bib
just --justfile "$REPO/justfile" \
  _compile-pandoc-tex no-crossref research_draft.tex "$SCRATCH/single/refs.bib" .build_pandoc \
  attribute_style_sample.md
check "attribute-style .tex byte-identical to pre-change baseline" \
  diff "$REPO/tests/fixtures/theorem-references/expected_attribute_style.tex" .build_pandoc/output.tex

# --- Result ----------------------------------------------------------
if [ "$FAILURES" -eq 0 ]; then
  echo "✅ test-project-references: all assertions passed"
else
  echo "❌ test-project-references: $FAILURES assertion(s) failed"
  exit 1
fi
