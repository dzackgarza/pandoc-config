#!/usr/bin/env bash
# Compile captionless Markdown tables inside theorem-family divs using the
# actual research-draft template and filter (issue #17).
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

pandoc tables.md --standalone --to=latex --syntax-highlighting=none \
    --template="$REPO/templates/research_draft.tex" \
    --lua-filter="$REPO/filters/convert_amsthm_envs.lua" -o tables.tex
if ! TEXINPUTS="$REPO/styles//:" lualatex -interaction=nonstopmode \
    -halt-on-error tables.tex > compile.log 2>&1; then
    tail -n 40 compile.log >&2
    exit 1
fi
test -s tables.pdf

# Both tables must remain in their original environments. Check the rendered
# document too: the titles, rows and first numbered caption must be visible.
for env in example proposition; do
    awk -v env="$env" '
        index($0, "\\begin{" env "}") { inside = 1 }
        index($0, "\\end{" env "}") { inside = 0 }
        inside && index($0, "\\begin{longtable}") { found = 1 }
        END { exit !found }
    ' tables.tex
done
grep -F '\newlabel{ex:table}' tables.aux >/dev/null
grep -F '\newlabel{prop:table}' tables.aux >/dev/null
pdftotext -layout tables.pdf tables.txt
# Join lines and normalize spaces so the test tolerates column widths and
# line wrapping but still checks each title, heading, row, and their order.
tr -s '[:space:]' ' ' < tables.txt > flat.txt
grep -E 'A table in an example.*Object Value.*Point 1.*A table in a proposition.*Input Output.*Line 2.*Table 1[.:] First numbered table' flat.txt >/dev/null
echo 'Theorem tables compile, retain their contents and labels, and do not advance the table counter.'
