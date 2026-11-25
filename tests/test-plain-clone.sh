#!/usr/bin/env bash
# A plain `git clone` gives the real files (issue #15).
#
# The research image, its CI jobs and the VMs clone this repository to
# ~/.pandoc with git alone; they have no git-lfs. A file that the clone gives
# as a Git LFS pointer is no figure: pdflatex stops on it, and
# research/scripts/docs_figures.py refuses it. The test clones the committed
# HEAD of this checkout with every LFS filter of the git configuration turned
# off, and fails on each pointer file and on each figure PDF that is no PDF.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRATCH="$(mktemp -d -t pandoc-plain-clone-XXXXXXXX)"
trap 'rm -rf "$SCRATCH"' EXIT

# A clone as a host without git-lfs makes it: no global or system
# configuration, so no lfs filter driver.
GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 \
  git clone --quiet --no-local "$REPO" "$SCRATCH/pandoc"
cd "$SCRATCH/pandoc"

pointers="$(git ls-files -z | xargs -0 grep -l --no-messages \
  '^version https://git-lfs.github.com/spec/v1$' || true)"
if [ -n "$pointers" ]; then
  echo "❌ A plain clone gives $(wc -l <<<"$pointers") Git LFS pointer files, for example:"
  head -5 <<<"$pointers"
  exit 1
fi

not_pdf=0
while IFS= read -r -d '' pdf; do
  if [ "$(head -c 5 "$pdf")" != "%PDF-" ]; then
    echo "❌ $pdf is no PDF"
    not_pdf=$((not_pdf + 1))
  fi
done < <(find figures/rendered -name '*.pdf' -print0)
[ "$not_pdf" -eq 0 ] || exit 1

echo "✅ A plain clone gives $(find figures/rendered -name '*.pdf' | wc -l) figure PDFs and no LFS pointer"
