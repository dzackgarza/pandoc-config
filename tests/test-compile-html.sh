#!/usr/bin/env bash
# test-compile-html.sh — the compile-html recipe end to end: a note becomes
# standalone HTML with the central MathJax macros, inline TikZ SVG and a
# resolved bibliography, and a build that cannot finish (a missing tool, a
# figure that does not compile, an unknown citation) exits nonzero and leaves
# the previous HTML file byte for byte as it was.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRATCH="$(mktemp -d -t pandoc-compile-html-XXXXXXXX)"
trap 'rm -rf "$SCRATCH"' EXIT
cd "$SCRATCH"
# The figure cache of tikzcd.lua: a fresh one, so the figures of this test
# compile here and do not come from an earlier run.
export SVG_DIR="$SCRATCH/svg"

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
compile_html() {
  just --justfile "$REPO/justfile" compile-html "$@"
}
export -f compile_html

# A PATH on which the named program is absent: each directory that holds it
# is replaced by a directory of links to its other entries.
path_without() {
  local tool="$1" dir entry result="" shadow
  local -a dirs
  IFS=':' read -r -a dirs <<< "$PATH"
  for dir in "${dirs[@]}"; do
    if [ -e "$dir/$tool" ]; then
      shadow="$(mktemp -d -p "$SCRATCH" path-XXXXXX)"
      for entry in "$dir"/*; do
        [ "$(basename "$entry")" = "$tool" ] || ln -s "$entry" "$shadow/"
      done
      dir="$shadow"
    fi
    result="${result:+$result:}$dir"
  done
  printf '%s' "$result"
}

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

cat > note.md <<'EOF'
---
title: "A Note On Points"
---

# Points

The set $\theset{x \in X \st x^2 = 1}$ is finite, following [@FS86].

\begin{tikzcd}
A \arrow[r, "f"] & B
\end{tikzcd}

A display of the notes is the body of an alignment:
\[
A &\to B \\
C &\to D
\]
EOF

echo "[1/5] a note becomes standalone HTML"
check "build succeeds" bash -c "compile_html note.md note.html refs.bib > build.log 2>&1"
check "the output is an HTML document" bash -c "head -c 200 note.html | grep -qi '<!DOCTYPE html>'"
check "the output holds the text of the note" grep -q 'is finite' note.html
check "the title is the title of the note" grep -q '<h1 class="title">A Note On Points</h1>' note.html
# Pandoc wraps the HTML at spaces, so a formula can span two lines.
check "the math is MathJax math" \
  bash -c "command tr '\n' ' ' < note.html | grep -qF 'class=\"math inline\">\(\theset{x \in X \st x^2 = 1}\)'"
check "MathJax gets the central macros" grep -qE '"?theset"?:' note.html
# The notes write a display as the body of align* (convert_math_delimiters.lua).
check "a display with & is an align* environment" \
  bash -c "command tr '\n' ' ' < note.html | grep -qE 'class=\"math display\">[[:space:]]*\\\\begin\{align\*\}[[:space:]]*A &amp;\\\\to B'"
check "the figure is an inline SVG" bash -c "grep -A2 'class=\"tikzcd' note.html | grep -q '<svg'"
check "the citation is resolved" grep -q 'Friedman' note.html
check "no temporary output is left beside the target" bash -c "! ls -A | grep -q '^\.note\.html\.'"

cp note.html previous.html

echo "[2/5] a missing pdf2svg stops the build before it writes"
check "build fails" bash -c "! PATH='$(path_without pdf2svg)' compile_html note.md note.html refs.bib > nosvg.log 2>&1"
check "the failure names the tool" grep -q 'pdf2svg' nosvg.log
check "the previous HTML is unchanged" cmp -s previous.html note.html

echo "[3/5] a missing pandoc-crossref stops the build before it writes"
check "build fails" bash -c "! PATH='$(path_without pandoc-crossref)' compile_html note.md note.html refs.bib > nocrossref.log 2>&1"
check "the failure names the tool" grep -q 'pandoc-crossref' nocrossref.log
check "the previous HTML is unchanged" cmp -s previous.html note.html

echo "[4/5] a figure that does not compile fails the build"
cat > broken.md <<'EOF'
# Points

\begin{tikzcd}
A \arrow[r, "\nosuchcommandanywhere"] & B
\end{tikzcd}
EOF
check "build fails" bash -c "! compile_html broken.md note.html '' > broken.log 2>&1"
check "the failure names the figure error" grep -q 'nosuchcommandanywhere' broken.log
check "the previous HTML is unchanged" cmp -s previous.html note.html
check "no temporary output is left beside the target" bash -c "! ls -A | grep -q '^\.note\.html\.'"

echo "[5/5] an unknown citation fails the build"
printf '# Points\n\nSee [@NoSuchKey2099].\n' > unknown.md
check "build fails" bash -c "! compile_html unknown.md note.html refs.bib > unknown.log 2>&1"
check "the failure names the key" grep -q 'NoSuchKey2099' unknown.log
check "the previous HTML is unchanged" cmp -s previous.html note.html

if [ "$FAILURES" -ne 0 ]; then
  echo "❌ $FAILURES check(s) failed"
  exit 1
fi
echo "✅ compile-html checks passed"
