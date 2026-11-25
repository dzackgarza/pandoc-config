#!/usr/bin/env bash
# pandoc_stripmacros.sh FILE   (or: ... | pandoc_stripmacros.sh)
#
# Writes FILE as Pandoc Markdown with each macro of styles/macros expanded,
# for a consumer that has no macro definitions. The definitions come from
# templates/css/math-macros.html, the \newcommand projection that
# bin/generate-mathjax-config.py writes from styles/macros; the filters come
# from this checkout. The script reads no environment variable.
set -euo pipefail

REPO="$(cd "$(dirname "$(realpath "${BASH_SOURCE[0]}")")/.." && pwd)"
input="${1:--}"
if [ "$input" != "-" ] && [ ! -f "$input" ]; then
  echo "❌ pandoc_stripmacros.sh: input $input does not exist." >&2
  exit 1
fi

# The definitions go first without their %-comment header: Pandoc reads a
# definition block that follows text as raw TeX of that paragraph and
# defines nothing. A blank line separates them from the input. Pandoc
# writes a %-comment line of the input as an escaped \% paragraph; those
# lines and the Xournal markers are removed.
{ grep -v '^%' "$REPO/templates/css/math-macros.html"; echo; cat "$input"; } | pandoc \
  --quiet \
  -r markdown+latex_macros+tex_math_dollars+tex_math_single_backslash \
  --to=markdown \
  --lua-filter="$REPO/filters/convert_amsthm_envs.lua" \
  --lua-filter="$REPO/filters/convert_math_delimiters.lua" \
  --wrap=none \
  | sed -e '/^\\%/d' -e '/Xournal file/d'
