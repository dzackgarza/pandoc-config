#!/usr/bin/env bash
# Captionless Markdown tables inside theorem-family divs (issue #17), through
# the compile-pandoc recipe: pandoc with the recipe's filters and the
# research_draft template, then latexmk with pdflatex.
#
# The recipe runs latexmk in force mode, so a TeX error still gives a PDF and
# exit code 0. The test therefore reads the log of the last LaTeX pass: an
# export with a TeX error is a failed export.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRATCH="$(mktemp -d -t pandoc-theorem-tables-XXXXXXXX)"
trap 'rm -rf "$SCRATCH"' EXIT
cd "$SCRATCH"

cat > tables.md <<'MARKDOWN'
::: {.example #ex:table title="A table in an example"}

| Object | Value |
|---|---|
| Point | $1$ |

:::

::: {.proposition #prop:table title="A table in a proposition"}

| Input | Output |
|---|---|
| Line | $2$ |

:::

| Item | Count |
|---|---|
| Other | 3 |

: First numbered table.
MARKDOWN

if ! PANDOC_BIB_SOURCE='' just --justfile "$REPO/justfile" compile-pandoc tables.md tables \
    > compile.log 2>&1; then
    tail -n 40 compile.log >&2
    exit 1
fi
BUILD=.build_pandoc

# The last LaTeX pass has no error.
if grep -n '^!' "$BUILD/output.log" >&2; then
    echo "❌ The LaTeX log of the export has errors." >&2
    exit 1
fi

# Each table stays inside its theorem environment.
for env in example proposition; do
    awk -v env="$env" '
        index($0, "\\begin{" env "}") { inside = 1 }
        index($0, "\\end{" env "}") { inside = 0 }
        inside && index($0, "\\begin{longtable}") { found = 1 }
        END { exit !found }
    ' "$BUILD/output.tex"
done
grep -F '\newlabel{ex:table}' "$BUILD/output.aux" >/dev/null
grep -F '\newlabel{prop:table}' "$BUILD/output.aux" >/dev/null

# The rendered order: each theorem title before its table, and the captioned
# table is Table 1, so a captionless table does not advance the table counter.
# Lines are joined and spaces normalized, so column widths and line wrapping
# do not matter.
pdftotext -layout tables-*.pdf - | tr -s '[:space:]' ' ' > flat.txt
grep -E 'A table in an example.*Object Value.*Point 1.*A table in a proposition.*Input Output.*Line 2.*Table 1[.:] First numbered table' flat.txt >/dev/null
echo '✅ Theorem tables compile without TeX errors, stay in their environments, and do not advance the table counter.'
