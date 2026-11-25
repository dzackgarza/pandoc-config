GLOBAL_BIB_SOURCE := env_var_or_default("ZOTERO_GLOBAL_BIB", home_dir() / "zotero_global.bib")

GLOBAL_FIGURES_DIR := env_var_or_default("FIGURES_DIR", home_dir() / "figures")

BUILD_DIR_PANDOC := ".build_pandoc"
BUILD_DIR_TEX := ".build_tex"

DEFAULT_TEMPLATE := "research_draft.tex"

PROJECT_BIB_SOURCE := env_var_or_default("PANDOC_BIB_SOURCE", GLOBAL_BIB_SOURCE)
PROJECT_BUILD_DIR := env_var_or_default("PANDOC_BUILD_DIR", BUILD_DIR_PANDOC)

CROSSREF_MODE := env_var_or_default("PANDOC_CROSSREF", "crossref")

TOP_LEVEL_DIVISION := env_var_or_default("PANDOC_TOP_LEVEL_DIVISION", "default")

export PANDOC_DIR := home_dir() / ".pandoc"
export TEXINPUTS := ".:" + home_dir() + "/.pandoc/styles//:" + home_dir() + "/.pandoc/macros//:" + home_dir() + "/.pandoc/config//:" + home_dir() + "/.pandoc:" + home_dir() + "/.pandoc/figures:" + env_var_or_default("TEXINPUTS", "")

[doc("Compile a Markdown file to a PDF in a sandbox, show it in zathura and compile it again at each change")]
[script("bash")]
preview file format="pdf" template="research_draft.tex":
  set -euo pipefail
  cd "{{invocation_directory()}}"
  
  FILE=$(realpath "{{file}}")
  DIR=$(dirname "$FILE")
  NAME=$(basename "$FILE" .md)
  ROOT="{{invocation_directory()}}"
  
  export TMP_DIR=$(mktemp -d -t preview-XXXXXXXXXX)
  echo "Preview sandbox created at: $TMP_DIR"
  [ -d "$DIR/figures" ] && ln -sf "$DIR/figures" "$TMP_DIR/figures"
  
  export VIEWER_PID_FILE="$TMP_DIR/viewer.pid"
  
  cleanup() {
      echo -e "\nCleaning up preview environment..."
      if [ -f "$VIEWER_PID_FILE" ]; then
          kill -9 $(cat "$VIEWER_PID_FILE") 2>/dev/null || true
      fi
      rm -rf "$TMP_DIR"
      exit 0
  }
  trap cleanup SIGINT SIGTERM EXIT

  export FORMAT="{{format}}"
  export TEMPLATE="{{template}}"
  export NAME
  export FILE
  export ROOT
  export BIB_SOURCE="{{PROJECT_BIB_SOURCE}}"

  compile_and_view() {
      echo "[preview] Compiling $FILE..."
      just pandoc::compile-pandoc "$FILE" "$NAME" "$TEMPLATE" "$BIB_SOURCE" "$TMP_DIR"
      
      if [ "$FORMAT" = "pdf" ]; then
          OUTFILE="$TMP_DIR/$NAME-$(date +%d-%m-%y).pdf"
          LITTERED_PDF="$ROOT/$NAME-$(date +%d-%m-%y).pdf"
          if [ -f "$LITTERED_PDF" ]; then
              mv "$LITTERED_PDF" "$OUTFILE"
          fi
          
          if [ ! -f "$VIEWER_PID_FILE" ]; then
              zathura "$OUTFILE" &>/dev/null &
              echo $! > "$VIEWER_PID_FILE"
          fi
      fi
  }
  export -f compile_and_view
  
  compile_and_view
  
  echo "[preview] Watching for changes via entr..."
  find "$DIR" -maxdepth 1 -name "*.md" | entr -n -p bash -c 'compile_and_view'

[doc("Format Markdown files with one sentence per line (prettier)")]
[script("bash")]
format-md *targets:
  set -euo pipefail
  ROOT="{{invocation_directory()}}"
  
  if [ -s "$HOME/.nvm/nvm.sh" ]; then
    . "$HOME/.nvm/nvm.sh"
    nvm use node
  fi
  npm install --no-save prettier prettier-plugin-sentences-per-line
  
  FINAL_TARGETS=()
  for t in {{targets}}; do
    if [[ "$t" == /* ]]; then
      FINAL_TARGETS+=("$t")
    else
      FINAL_TARGETS+=("$ROOT/$t")
    fi
  done

  if [ ${#FINAL_TARGETS[@]} -eq 0 ]; then
    echo "Usage: just pandoc::format-md <targets...>"
    exit 1
  fi

  REAL_FILES=()
  while IFS=  read -r -d $'\0'; do
      REAL_FILES+=("$REPLY")
  done < <(find "${FINAL_TARGETS[@]}" -type f -name "*.md" -not -path '*/.*' -tr '\n' '\0' 2>/dev/null)

  if [ ${#REAL_FILES[@]} -eq 0 ]; then
    echo "No markdown files found in targets."
    exit 0
  fi

  CONFIG_ARGS=()
  if [ -f "$ROOT/.prettierrc" ]; then
    CONFIG_ARGS+=(--config "$ROOT/.prettierrc")
  elif [ -f "$HOME/.pandoc/.prettierrc" ]; then
    CONFIG_ARGS+=(--config "$HOME/.pandoc/.prettierrc")
  fi

  npx prettier "${CONFIG_ARGS[@]}" --ignore-path=/dev/null --write "${REAL_FILES[@]}"

[doc("Format Markdown files with flowmark (semantic line breaks, Pandoc structure)")]
[script("bash")]
format-markdown *files:
  set -euo pipefail
  for f in {{files}}; do
    uvx --from 'git+https://github.com/dzackgarza/flowmark.git' flowmark --semantic "$f" > "$f.tmp" && mv "$f.tmp" "$f"
  done

[doc("Render TikZ figures to SVG+PDF via templates/standalone-tikz.tex; no argument renders all, a path or figure name renders one (add --force to skip the cache)")]
[script("bash")]
render-figures *args:
  set -euo pipefail
  uv run "$HOME/.pandoc/bin/render_figures.py" {{args}}

[doc("Compile a LaTeX file to a PDF with latexmk and the global bibliography")]
[script("bash")]
compile-tex main_file="main.tex" output_name="paper" bib_source=GLOBAL_BIB_SOURCE build_dir=BUILD_DIR_TEX:
  set -euo pipefail
  ROOT="{{invocation_directory()}}"
  
  DIR=$(dirname "{{main_file}}")
  FILE=$(basename "{{main_file}}")
  
  mkdir -p "$ROOT/{{build_dir}}"
  
  ln -sf "{{bib_source}}" "$ROOT/global.bib"
  
  export BIBINPUTS=".:$ROOT:${BIBINPUTS:-}"
  
  cd "$ROOT/$DIR"
  latexmk -gg -pdf -outdir="$ROOT/{{build_dir}}" "$FILE" -use-make
  
  cp "$ROOT/{{build_dir}}/${FILE%.tex}.pdf" "$ROOT/{{output_name}}-$(date +%d-%m-%y).pdf"

[doc("Compile a Pandoc Markdown file to a PDF through a LaTeX template and latexmk")]
compile-pandoc input_file="main.md" output_name="output" template=DEFAULT_TEMPLATE bib_source=PROJECT_BIB_SOURCE build_dir=BUILD_DIR_PANDOC: (_compile-pandoc-tex CROSSREF_MODE template bib_source build_dir input_file) (_compile-pandoc-latexmk output_name build_dir)

[positional-arguments]
[doc("Compile ordered Pandoc Markdown files to one PDF; a template of '' or '-' is the default template")]
[script("bash")]
compile-pandoc-project output_name template +input_files:
  set -euo pipefail
  cd "{{invocation_directory()}}"
  TEMPLATE="{{template}}"
  if [ -z "$TEMPLATE" ] || [ "$TEMPLATE" = "-" ]; then
    TEMPLATE="{{DEFAULT_TEMPLATE}}"
  fi
  just --justfile "{{source_file()}}" _compile-pandoc-tex "{{CROSSREF_MODE}}" "$TEMPLATE" "{{PROJECT_BIB_SOURCE}}" "{{PROJECT_BUILD_DIR}}" "${@:3}"
  just --justfile "{{source_file()}}" _compile-pandoc-latexmk "{{output_name}}" "{{PROJECT_BUILD_DIR}}"

HTML_MATHJAX_URL := "https://cdn.jsdelivr.net/npm/mathjax@4.0.0/tex-chtml.js"

[positional-arguments]
[doc("Compile a Pandoc note to standalone HTML with MathJax and inline TikZ SVG; a failed build keeps the previous output_file")]
[script("bash")]
compile-html input_file output_file bib_source=PROJECT_BIB_SOURCE:
  set -euo pipefail
  cd "{{invocation_directory()}}"
  INPUT="$1"
  OUTPUT="$2"
  BIB_SOURCE="$3"

  CROSSREF_ARGS=()
  TOOLS=(pandoc lualatex pdf2svg)
  case "{{CROSSREF_MODE}}" in
    crossref)
      CROSSREF_ARGS=(-F pandoc-crossref -M cref=true)
      TOOLS+=(pandoc-crossref)
      ;;
    no-crossref) ;;
    *)
      echo "❌ compile-html: unknown PANDOC_CROSSREF '{{CROSSREF_MODE}}' (expected 'crossref' or 'no-crossref')" >&2
      exit 1
      ;;
  esac
  for tool in "${TOOLS[@]}"; do
    if ! command -v "$tool" >/dev/null; then
      echo "❌ compile-html: $tool is not on PATH; $OUTPUT is not changed." >&2
      exit 1
    fi
  done
  if [ ! -f "$INPUT" ]; then
    echo "❌ compile-html: input $INPUT does not exist." >&2
    exit 1
  fi
  OUTPUT_DIR="$(dirname "$OUTPUT")"
  if [ ! -d "$OUTPUT_DIR" ]; then
    echo "❌ compile-html: the directory $OUTPUT_DIR of $OUTPUT does not exist." >&2
    exit 1
  fi

  BIB_FILES=()
  IFS=':' read -r -a BIB_FILES <<< "$BIB_SOURCE"
  BIB_ARGS=()
  for bib in "${BIB_FILES[@]}"; do
    if [ ! -f "$bib" ]; then
      echo "❌ Bibliography $bib does not exist (set ZOTERO_GLOBAL_BIB or PANDOC_BIB_SOURCE)." >&2
      exit 1
    fi
    BIB_ARGS+=(--bibliography="$bib")
  done

  STAGED="$(mktemp -p "$OUTPUT_DIR" ".$(basename "$OUTPUT").XXXXXX")"
  LOG="$(mktemp -t compile-html-log-XXXXXX)"
  trap 'rm -f "$STAGED" "$LOG"' EXIT

  STATUS=0
  pandoc "$INPUT" \
      --from=markdown+tex_math_single_backslash+wikilinks_title_after_pipe \
      --lua-filter="{{source_directory()}}/filters/wikilinks.lua" \
      --lua-filter="{{source_directory()}}/filters/include.lua" \
      "${CROSSREF_ARGS[@]}" \
      --lua-filter="{{source_directory()}}/filters/convert_amsthm_envs.lua" \
      --lua-filter="{{source_directory()}}/filters/tikzcd.lua" \
      --lua-filter="{{source_directory()}}/filters/replace_symbols_html.lua" \
      --lua-filter="{{source_directory()}}/filters/convert_math_delimiters.lua" \
      --citeproc \
      --csl="{{source_directory()}}/csl/alpha-preview.csl" \
      "${BIB_ARGS[@]}" \
      --to=html5 --standalone \
      --template="{{source_directory()}}/templates/pandoc_preview_template.html" \
      --math-method=mathjax:"{{HTML_MATHJAX_URL}}" \
      --number-sections \
      --toc --toc-depth=2 \
      -o "$STAGED" 2> "$LOG" || STATUS=$?
  cat "$LOG" >&2
  if [ "$STATUS" -ne 0 ]; then
    echo "❌ compile-html: pandoc exited $STATUS; $OUTPUT is not changed." >&2
    exit 1
  fi
  if grep -qE '^\[tikzcd-latex-log-begin\]|^\[tikzcd\] (lualatex|pdf2svg) failed' "$LOG"; then
    echo "❌ compile-html: a TikZ figure did not compile (see the log above); $OUTPUT is not changed." >&2
    exit 1
  fi
  if grep -qE 'Citeproc: citation .* not found' "$LOG"; then
    echo "❌ compile-html: a citation is not in the bibliography (see the log above); $OUTPUT is not changed." >&2
    exit 1
  fi
  chmod "$(printf '%o' $(( 0666 & ~0$(umask) )))" "$STAGED"
  mv "$STAGED" "$OUTPUT"
  echo "✅ $OUTPUT"

[private]
[positional-arguments]
[doc("The Pandoc stage of compile-pandoc: Markdown to build_dir/output.tex")]
[script("bash")]
_compile-pandoc-tex crossref_mode template bib_source build_dir +input_files:
  set -euo pipefail
  CROSSREF_ARGS=()
  case "{{crossref_mode}}" in
    crossref) CROSSREF_ARGS=(-F pandoc-crossref -M cref=true) ;;
    no-crossref) ;;
    *)
      echo "❌ _compile-pandoc-tex: unknown crossref_mode '{{crossref_mode}}' (expected 'crossref' or 'no-crossref')" >&2
      exit 1
      ;;
  esac

  ROOT="{{invocation_directory()}}"
  mkdir -p "$ROOT/{{build_dir}}"

  cd "$ROOT"
  BIB_FILES=()
  IFS=':' read -r -a BIB_FILES <<< "{{bib_source}}"
  BIB_ARGS=()
  for bib in "${BIB_FILES[@]}"; do
    if [ ! -f "$bib" ]; then
      echo "❌ Bibliography $bib does not exist (set ZOTERO_GLOBAL_BIB or PANDOC_BIB_SOURCE)." >&2
      exit 1
    fi
    BIB_ARGS+=(--bibliography="$bib")
  done

  pandoc "${@:5}" \
      --from=markdown+tex_math_single_backslash+wikilinks_title_after_pipe \
      --lua-filter="{{source_directory()}}/filters/wikilinks.lua" \
      --lua-filter="{{source_directory()}}/filters/include.lua" \
      "${CROSSREF_ARGS[@]}" \
      --lua-filter="{{source_directory()}}/filters/convert_amsthm_envs.lua" \
      --lua-filter="{{source_directory()}}/filters/select_images.lua" \
      --natbib \
      "${BIB_ARGS[@]}" \
      --template={{template}} \
      --biblatex \
      --number-sections \
      --top-level-division={{TOP_LEVEL_DIVISION}} \
      --toc --toc-depth=2 \
      -s -o "{{build_dir}}/output.tex"

[private]
[doc("The latexmk stage of compile-pandoc: build_dir/output.tex to a dated PDF in the invocation directory")]
[script("bash")]
_compile-pandoc-latexmk output_name build_dir:
  set -euo pipefail
  ROOT="{{invocation_directory()}}"
  cd "$ROOT"
  cd "{{build_dir}}"
  export BIBINPUTS=".:$ROOT:${BIBINPUTS:-}"
  LATEXMK_RC=0
  latexmk -pdf -interaction=nonstopmode -f -gg output.tex || LATEXMK_RC=$?
  if [ ! -f output.pdf ]; then
    echo "❌ latexmk failed to produce output.pdf (exit code $LATEXMK_RC)"
    exit 1
  fi
  if [ $LATEXMK_RC -ne 0 ]; then
    echo "⚠️  latexmk exited $LATEXMK_RC but PDF was produced — check warnings above"
  fi
  UNDEFINED=$(grep -oE "(Citation|Reference) [\`'][^']+' on page [0-9]+ undefined" output.log \
    | sed -E "s/ on page [0-9]+ undefined//" | sort -u || true)
  if [ -n "$UNDEFINED" ]; then
    echo "❌ Undefined citations or references (PDF left in {{build_dir}}/output.pdf):" >&2
    echo "$UNDEFINED" >&2
    exit 1
  fi
  cp output.pdf "$ROOT/{{output_name}}-$(date +%d-%m-%y).pdf"

[doc("Download and extract an arXiv tarball")]
[script("bash")]
download-arxiv arxiv_id dir:
  set -euo pipefail
  ROOT="{{invocation_directory()}}"
  mkdir -p "$ROOT/knowledge/papers/{{dir}}"
  wget -qO - "https://arxiv.org/e-print/{{arxiv_id}}" | tar -xz -C "$ROOT/knowledge/papers/{{dir}}"

[doc("Compile a reference LaTeX file to Markdown (Modern extraction pipeline)")]
[script("bash")]
extract-ref dir file="main":
  set -euo pipefail
  ROOT="{{invocation_directory()}}"
  mkdir -p "$ROOT/knowledge/papers"

  cd "$ROOT/{{dir}}"
  rm -f {{file}}.aux

  xpandlatex -x on -m on -I on $(ls *.sty 2>/dev/null | sed 's/^/-f /' | xargs) {{file}}.tex > {{file}}_expanded.tex

  pandoc {{file}}_expanded.tex -s -f latex+raw_tex -t latex --lua-filter="$HOME/.pandoc/filters/wrap_tikzcd_semantic.lua" -o {{file}}_wrapped.tex

  make4ht -c "$HOME/.pandoc/config/tex4ht.cfg" -u -f html5 {{file}}_wrapped.tex "mathjax,section+" || true

  pandoc {{file}}_wrapped.html --lua-filter="$HOME/.pandoc/filters/semanticlean.lua" -f html -t gfm-tex_math_gfm+tex_math_dollars -o "$ROOT/knowledge/papers/$(basename {{dir}}).md"

[doc("Clean build artifacts")]
[script("bash")]
clean build_dir_pandoc=BUILD_DIR_PANDOC build_dir_tex=BUILD_DIR_TEX:
  set -euo pipefail
  ROOT="{{invocation_directory()}}"
  command -v trash >/dev/null 2>&1 || { echo "clean requires the trash command" >&2; exit 1; }

  trash_if_present() {
    local path="$1"
    if [ -e "$path" ]; then
      trash "$path"
    fi
  }

  for path in \
    "$ROOT/{{build_dir_pandoc}}" \
    "$ROOT/{{build_dir_tex}}" \
    "$ROOT/.build" \
    "$ROOT/.build_test_templates" \
    "$ROOT/global.bib"; do
    trash_if_present "$path"
  done

  while IFS= read -r -d '' path; do
    trash_if_present "$path"
  done < <(find "$ROOT" -maxdepth 1 -type f \( \
    -name "*.pdf" -o -name "*.aux" -o -name "*.log" -o -name "*.fls" \
    -o -name "*.fdb_latexmk" -o -name "*.bbl" -o -name "*.bcf" \
    -o -name "*.blg" -o -name "*.run.xml" -o -name "*.out" \
    -o -name "*.toc" -o -name "*SAVE-ERROR" \) -print0)

  for directory in "$ROOT/tests" "$ROOT/templates"; do
    if [ -d "$directory" ]; then
      while IFS= read -r -d '' path; do
        trash_if_present "$path"
      done < <(find "$directory" -type f \( \
        -name "*.pdf" -o -name "*.aux" -o -name "*.log" \
        -o -name "*.fls" -o -name "*.fdb_latexmk" \
        -o -name "*.synctex.gz" -o -name "*.bcf" -o -name "*.run.xml" \
        -o -name "*.out" -o -name "*.toc" \) -print0)
    fi
  done

[doc("Clean all build artifacts from reference directories")]
[script("bash")]
clean-refs:
  set -euo pipefail
  ROOT="{{invocation_directory()}}"
  command -v trash >/dev/null 2>&1 || { echo "clean-refs requires the trash command" >&2; exit 1; }
  if [ -d "$ROOT/references" ]; then
    while IFS= read -r -d '' path; do
      trash "$path"
    done < <(find "$ROOT/references" -type f ! \( \
      -name "*.tex" -o -name "*.sty" -o -name "*.cls" -o -name "*.bib" \
      -o -name "*.bbl" -o -name "*.png" -o -name "*.jpg" \
      -o -name "tex4ht.cfg" \) -print0)
  fi

[doc("Test macro compilation")]
[script("bash")]
_test-macros:
  set -euo pipefail
  PANDOC_DIR="{{source_directory()}}"
  export TEXINPUTS=".:$PANDOC_DIR/styles//:$PANDOC_DIR/styles/macros//:$PANDOC_DIR/styles/preambles//:$PANDOC_DIR/config//:"
  cd "$PANDOC_DIR/tests"
  pdflatex -interaction=nonstopmode -halt-on-error test-latex-macros.tex
  if [ -f test-latex-macros.pdf ]; then
    echo "✅ LaTeX test compiled: test-latex-macros.pdf ($(du -h test-latex-macros.pdf | cut -f1))"
  else
    echo "❌ Compilation failed - no PDF produced"
    exit 1
  fi

[doc("Test TikZ macros (nodes, edges, diagrams, utilities)")]
[script("bash")]
_test-tikz:
  set -euo pipefail
  PANDOC_DIR="{{source_directory()}}"
  export TEXINPUTS=".:$PANDOC_DIR/styles//:$PANDOC_DIR/styles/macros//:$PANDOC_DIR/styles/preambles//:$PANDOC_DIR/config//:$PANDOC_DIR/figures//:"
  OBJECTS=$(cd "$PANDOC_DIR/figures/objects" && find . -name "*.tikz" | sed "s|^\./||; s|\.tikz$||" | sort | paste -sd,)
  cd "$PANDOC_DIR/tests"
  pdflatex -interaction=nonstopmode -jobname=test-tikz-macros "\\def\\dzgobjects{$OBJECTS}\\input{test-tikz-macros.tex}" 2>&1 | tee /tmp/tikz-test.log
  if grep -q '^!' /tmp/tikz-test.log; then
    echo "❌ Errors found:"
    grep '^!' /tmp/tikz-test.log
    rm -f test-tikz-macros.pdf
    exit 1
  fi
  if [ -f test-tikz-macros.pdf ]; then
    echo "✅ TikZ test compiled: test-tikz-macros.pdf ($(du -h test-tikz-macros.pdf | cut -f1))"
  else
    echo "❌ Compilation failed - no PDF produced"
    exit 1
  fi

[doc("Test the poset layout: draw the fixtures of tests/fixtures/posets with every grading")]
[script("bash")]
_test-posets:
  set -euo pipefail
  PANDOC_DIR="{{source_directory()}}"
  export TEXINPUTS=".:$PANDOC_DIR/styles//:$PANDOC_DIR/figures//:"
  cd "$PANDOC_DIR/tests"
  lualatex --shell-escape -interaction=nonstopmode -halt-on-error test-posets.tex > /tmp/posets-test.log 2>&1 \
    || { grep -A4 '^!\|dzg-poset.lua:[0-9]*:' test-posets.log; exit 1; }
  echo "✅ Poset test compiled: test-posets.pdf"

[doc("Cut the next semantic release of main: version from the conventional commits (git-cliff), CHANGELOG.md, an annotated tag, a GitHub release")]
[script("bash")]
release:
  set -euo pipefail
  cd "{{source_directory()}}"
  cliff=(uvx git-cliff@2.14.2 --config cliff.toml)
  if [ -n "$(git status --porcelain --untracked-files=all)" ]; then
    echo "release: the working tree has uncommitted changes" >&2; exit 1
  fi
  git fetch --quiet --tags origin main
  if [ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]; then
    echo "release: HEAD is not origin/main; merge and push first" >&2; exit 1
  fi
  latest="$(git describe --tags --abbrev=0 --match 'v[0-9]*.[0-9]*.[0-9]*')"
  version="$("${cliff[@]}" --bumped-version 2>/dev/null)"
  if [ "$version" = "$latest" ]; then
    echo "release: no commit since $latest gives a new version" >&2; exit 1
  fi
  "${cliff[@]}" --tag "$version" --output CHANGELOG.md 2>/dev/null
  notes="$("${cliff[@]}" --unreleased --tag "$version" --strip all 2>/dev/null)"
  git add CHANGELOG.md
  git commit --quiet -m "chore(release): $version" -m "Changelog of $version, generated by git-cliff from the commits since $latest."
  git push origin HEAD:main
  git tag --annotate "$version" --message "$version"
  git push origin "refs/tags/$version"
  gh release create "$version" --verify-tag --title "$version" --notes "$notes"
  echo "released $version: $(git describe --tags)"

[positional-arguments]
[doc("List the downstream sites whose known-good marker lags this checkout, with the changes since each marker (default: the sites of downstream-sites.txt)")]
staleness-report *sites:
  @uv run --quiet "{{source_directory()}}/bin/staleness-report.py" --repository "{{source_directory()}}" --registry "{{source_directory()}}/downstream-sites.txt" "$@"

[doc("Regenerate the reference section of README.md (every macro, environment and figure object)")]
readme-reference:
  uv run "{{source_directory()}}/bin/generate-readme-reference.py"

[doc("Test the compile-pandoc recipe end to end")]
_test-compile-pandoc:
  bash "{{source_directory()}}/tests/test-compile-pandoc.sh"

[doc("Compile captionless tables inside theorem-family divs")]
_test-theorem-tables:
  bash "{{source_directory()}}/tests/test-theorem-tables.sh"

[doc("Build a note to standalone HTML; a build that cannot finish keeps the previous HTML")]
_test-compile-html:
  bash "{{source_directory()}}/tests/test-compile-html.sh"

[doc("Expand the central macros of a Markdown file without environment variables")]
_test-stripmacros:
  bash "{{source_directory()}}/tests/test-stripmacros.sh"

[doc("A plain git clone (no git-lfs) gives each figure as a real file")]
_test-plain-clone:
  bash "{{source_directory()}}/tests/test-plain-clone.sh"

[doc("Regenerate the README reference, then run all tests (macros, templates, tikz compilation, filter, poset layout)")]
test: readme-reference _test-mathjax-generator _test-macros _test-mathjax-macros _test-templates _test-tikz _test-tikz-filter _test-lamport-proof _test-wikilinks _test-math-delimiters _test-posets _test-compile-pandoc _test-compile-html _test-stripmacros _test-theorem-tables _test-plain-clone _test-staleness-report

[doc("Run the fast commit check; the commit hook runs this")]
test-commit:
    @just -f ~/ai-review-ci/justfiles/python.just -d . test-commit

[doc("CI gate: the full suite, same as test")]
test-ci: test

[doc("Run the fast push check; the push hook runs this")]
test-push:
    @just -f ~/ai-review-ci/justfiles/python.just -d . test-push

[doc("Test theorem references across ordered inputs, the byte stability of the attribute theorem path, and that each emitted theorem environment is defined")]
test-references:
  bash "{{source_directory()}}/tests/test-project-references.sh"

[doc("Check generator semantics, embedded template projections and LaTeX compatibility")]
_test-mathjax-generator:
  uv run "{{source_directory()}}/tests/test-mathjax-generator.py"

[doc("Typeset every generated macro in MathJax 4 with ams, mathtools, centernot and stmaryrd")]
_test-mathjax-macros:
  cd "{{source_directory()}}" && bun update && bun tests/test-mathjax-macros.ts

[doc("Test the tikzcd filter through the Pandoc JSON AST and the DOM of the HTML")]
_test-tikz-filter:
  uv run "{{source_directory()}}/tests/test-tikz-filter.py"

[doc("Test Lamport-style proof parsing, numbering, references, and LaTeX output")]
_test-lamport-proof:
  uv run "{{source_directory()}}/tests/test-lamport-proof.py"

[doc("Test that wikilinks become links to the headings the editor resolved")]
_test-wikilinks:
  uv run "{{source_directory()}}/tests/test-wikilinks.py"

[doc("Test the conversion of the math delimiters of the notes")]
_test-math-delimiters:
  uv run "{{source_directory()}}/tests/test-math-delimiters.py"

[doc("Test the staleness report on built histories and the marker of a real site")]
_test-staleness-report:
  uv run "{{source_directory()}}/tests/test-staleness-report.py"

[doc("Generate every MathJax projection from the canonical macro manifest")]
generate-math-macros:
  uv run "{{source_directory()}}/bin/generate-mathjax-config.py"

[doc("Alias of generate-math-macros")]
generate-math-macros-legacy: generate-math-macros

[doc("Test that the standalone LaTeX templates compile")]
[script("bash")]
_test-templates clean="true":
  set -euo pipefail
  PANDOC_DIR="{{source_directory()}}"
  BUILD_DIR="$PANDOC_DIR/.build_test_templates"
  export TEXINPUTS=".:$PANDOC_DIR/styles//:$PANDOC_DIR/styles/macros//:$PANDOC_DIR/styles/preambles//:$HOME/.pandoc/config//:"

  rm -rf "$BUILD_DIR"
  mkdir -p "$BUILD_DIR"

  for template in homework_template.tex MakeMeAQual_template.tex; do
    echo "Testing $template..."

    TEMP_DIR="$BUILD_DIR/.tmp_${template%.tex}"
    mkdir -p "$TEMP_DIR"

    cp "$PANDOC_DIR/templates/$template" "$TEMP_DIR/"
    cd "$TEMP_DIR"
    latexmk -pdf -interaction=nonstopmode -gg "$template" >/dev/null 2>&1 || true

    if [ -f "${template%.tex}.pdf" ]; then
      cp "${template%.tex}.pdf" "$BUILD_DIR/"
      echo "  ✅ $template"
    else
      echo "  ❌ $template failed"
      tail -20 "${template%.tex}.log"
      exit 1
    fi
  done

  echo "✅ All standalone templates compiled successfully"
  echo "Note: Pandoc templates (pandoc_problem_template.tex, research_draft.tex) need Pandoc processing"

  if [ "{{clean}}" = "true" ]; then
    rm -rf "$BUILD_DIR"
  else
    echo "Build artifacts kept in: $BUILD_DIR"
  fi
