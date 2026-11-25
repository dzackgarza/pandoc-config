# Pandoc Configuration

Use the [shared math container](https://github.com/dzackgarza/ai-review-ci/blob/main/SAGE-CONTAINER.md#use-the-image)
(`ghcr.io/dzackgarza/sage:develop`) for Lean/elan, Sage with mypy, GAP,
Julia/Oscar, Macaulay2, and Singular. The guide covers image pull/run commands,
CI use, and the host launchers.

Personal Pandoc and LaTeX configuration for generating PDFs from markdown and managing LaTeX macros.

## `bib/references.bib` is generated: never edit it

`bib/references.bib` is written by Zotero's Better BibTeX auto-export. Zotero is
the only source of its content. The file in this repository is a published copy
of that export.

- Do not edit the file. This includes an editor, `sed`, a script, a formatter,
  and a hand-resolved merge conflict.
- Make every change in Zotero: a new entry, a corrected field, a changed
  citation key, a removed duplicate. Better BibTeX then writes the file again.
- A missing or wrong citation key is a Zotero library problem. Correct the
  Zotero item, then use the key that the export gives.
- If this checkout and its remote disagree on the file, the current export
  replaces the file whole. Do not combine the two versions.
- Zotero syncs each library change to the file immediately. Commit and push the
  file whenever it differs from `HEAD`; that is how the published copy stays up
  to date.

## Directory Structure

```
styles/                     # LaTeX macro system (styles assemble macros)
├── dzg-unified.sty        # Main style - loads all macros
├── dzg-mathjax.sty        # MathJax subset (tiers 1-2)
├── freetikz.sty           # External TikZ helper
├── quiver.sty             # Commutative diagrams
├── macros/tikz/tikzlibrarydzg.code.tex  # TikZ figure vocabulary (\usetikzlibrary{dzg})
├── macros/                # Raw .tex macro files (tier system)
│   ├── tier1-mathjax-simple.tex
│   ├── tier2-mathjax-args.tex
│   ├── tier3-tex-complex.tex
│   ├── tier4-preamble.tex
│   ├── categories.tex
│   ├── spectral.tex
│   ├── tikz.tex
│   └── environments.tex
├── preambles/             # Shared preamble fragments (\input-ed by .sty files)
│   └── dzg-preamble.tex   # Core package loading block
├── obsidian/              # MathJax macros for Obsidian
    └── mathjax-macros.tex

templates/                  # Pandoc document templates
├── koma-article.tex       # KOMA-Script (general docs, homework)
├── ams-article.tex        # AMS article (journal submissions)
├── research_draft.tex     # Research draft (amsart-based)
├── research_paper.tex     # Research paper (amsart, arxiv mode)
├── homework_template.tex  # Homework problem sets
├── pandoc_problem_template.tex
├── *.html, *.latex
├── css/                   # CSS for HTML templates
└── metadata/              # YAML metadata files

bin/                        # Scripts and Lua filters
├── *.lua                  # Pandoc Lua filters
├── *.sh                   # Shell scripts
└── *.py                   # Python utilities

config/                     # Miscellaneous configuration
tests/                      # Test suite
bib/                        # Bibliography files
archive/                    # Archived legacy files
```

## Usage

### LaTeX Documents

```latex
\documentclass{article}
\usepackage{dzg-unified}
\begin{document}
$\ZZ, \QQ, \RR, \CC$
\end{document}
```

### Pandoc

```bash
pandoc input.md -o output.pdf \
    --template=research_draft.tex \
    -H styles/dzg-unified.sty
```

### Environment Setup

Required in `~/.zshrc`; the canonical source is `~/.envrc`:

```bash
export TEXINPUTS=".:$HOME/.pandoc/templates//:$HOME/.pandoc/styles//:$HOME/.pandoc/styles/macros//:${TEXINPUTS:-}:"
export BIBINPUTS=".:$HOME/.pandoc/bib//:${BIBINPUTS:-}"
export PATH="$HOME/.pandoc/bin:$PATH"
```

## The justfile

A project imports the justfile as a module (`mod pandoc '~/.pandoc/justfile'`)
and calls `just pandoc::<recipe>`. The `[doc]` attribute of a recipe is its
line in `just --list`. A recipe with a body in bash has the attribute
`[script("bash")]`, not a shebang line. The justfile holds no comments; a
reason for a recipe goes in this section.

- **Environment variables are read when just parses the file.**
  `ZOTERO_GLOBAL_BIB` (default `~/zotero_global.bib`), `FIGURES_DIR`,
  `PANDOC_BIB_SOURCE`, `PANDOC_BUILD_DIR`, `PANDOC_CROSSREF` and
  `PANDOC_TOP_LEVEL_DIVISION` must be in the environment of the `just`
  process. An `export FOO := ...` at the top level of an importing justfile
  sets only the environment of its recipes, which is too late, and the
  default is then used without an error. Give them to a nested `just`:

  ```just
  [script("bash")]
  compile:
    PANDOC_BIB_SOURCE=refs.bib PANDOC_CROSSREF=no-crossref \
      just pandoc::compile-pandoc-project out template.tex main.md
  ```

  When a setting seems to have no effect, read the `\addbibresource` lines
  of the generated `output.tex`.
- **Bibliographies.** `PANDOC_BIB_SOURCE` is a list of files separated by
  `:`; an empty value is a document without a bibliography; without the
  variable the bibliography is `ZOTERO_GLOBAL_BIB`. `compile-pandoc`,
  `compile-pandoc-project` and `compile-html` read it. A relative file is
  relative to the invocation directory. A file that does not exist stops
  the build: biber would read it as an unknown resource, and each citation
  of it would be undefined.
- **`PANDOC_CROSSREF`** is `crossref` (default) or `no-crossref`. With
  crossref, `@fig:`/`@tbl:`/`@eq:`/`@sec:`/`@lst:` resolve to numbered
  references; without it they reach biblatex as unknown citation keys.
  Crossref adds a preamble block that declares a `codelisting` float and
  redefines `\footnote` in subfigures; a document that writes its own
  `\label`/`\Cref` and has no crossref references does not need it, and the
  block clashes with the caption and sidenotes packages.
- **`PANDOC_TOP_LEVEL_DIVISION`** is the `--top-level-division` of the
  compile-pandoc family: `default` (Pandoc chooses from the document class),
  `section`, `chapter` or `part`. A book whose `#` headings are parts sets
  `part`.
- **`DEFAULT_TEMPLATE`** is the one name of the default LaTeX template:
  `compile-pandoc` has it as its default, and `compile-pandoc-project` uses
  it for a template argument of `''` or `-` (its template argument is
  before the list of inputs, so it cannot be left out).
- **`compile-pandoc-project`** gives its inputs to Pandoc in the given
  order, and pandoc-crossref resolves the targets across the files. The list
  of inputs is the last parameter, so the bibliography and the build folder
  come from `PANDOC_BIB_SOURCE` and `PANDOC_BUILD_DIR`. just joins a
  variadic argument of a dependency into one string, which splits a file
  name with spaces; `[positional-arguments]` and `"${@:3}"` give each input
  to the nested `just` as one argument.
- **The Pandoc stage (`_compile-pandoc-tex`)** uses the filters of the
  checkout of the justfile, not of `~/.pandoc`, so `--justfile <checkout>`
  tests that checkout. It runs Pandoc in the invocation directory, so the
  relative paths of `include.lua` resolve. The reader has
  `tex_math_single_backslash`: `\(...\)` and `\[...\]` are math in these
  documents (the Zettlr editor and the Flowmark lint read them so).
  `wikilinks.lua` runs before `include.lua` adds the headings of included
  files, and applies the resolutions that `PANDOC_WIKILINKS` names.
  pandoc-crossref runs after `include.lua`, so it sees the whole document,
  and before `convert_amsthm_envs.lua`: it passes theorem divs and `@thm:`
  citations through unchanged.
- **The latexmk stage (`_compile-pandoc-latexmk`)** adds the invocation
  directory to `BIBINPUTS`, so a relative bibliography is found. It reads
  the undefined citations and references from the log of the last LaTeX
  pass and fails on each, with the PDF left in the build folder.
- **`compile-html`** writes a staged file beside its target and renames it
  only after a build without error (see "Note HTML is `compile-html`"
  above). `--citeproc` is after the filters, so pandoc-crossref takes its
  references first. `HTML_MATHJAX_URL` pins one release of the MathJax major
  version that `templates/pandoc_preview_template.html` configures.
- **`preview`** builds in a temporary folder. `compile-pandoc` copies the
  dated PDF to the invocation directory; `preview` moves it to that folder
  and shows it in zathura.
- **`format-md`** formats only files below its targets and follows no
  symbolic link out of them, so it does not format Zotero storage. It uses
  the `.prettierrc` of the invocation directory, else
  `~/.pandoc/.prettierrc`.
- **`render-figures`** reads `TEXINPUTS` from the environment of the shell.
- **`generate-math-macros`** is the one path that writes the MathJax
  projections; `generate-math-macros-legacy` is an alias of it.
- **`_test-templates`** compiles only the standalone LaTeX templates; a
  Pandoc template (`research_draft.tex`, `pandoc_problem_template.tex`)
  needs Pandoc.

## Templates that zettlr-pandoc exports with

zettlr-pandoc (the editor) assembles no math for an export. The template of an
export owns its math, and an export without a template of its own uses a
template of this repository, by name:

| Writer | Template |
| --- | --- |
| `html`, `html5`, `html4` | `templates/pandoc_preview_template.html` |
| `s5` | `templates/pandoc_s5_template.html` |
| `slidy` | `templates/pandoc_slidy_template.html` |
| `slideous` | `templates/pandoc_slideous_template.html` |
| `dzslides` | `templates/pandoc_dzslides_template.html` |
| `chunkedhtml` | `templates/pandoc_chunkedhtml_template.html` |
| `revealjs` | `templates/pandoc_revealjs_template.html` |
| `latex`, `pdf` | `templates/research_draft.tex` |
| `beamer` | `templates/research_beamer.tex` |
| `context` | `templates/pandoc_context_template.tex` |

So a change of one of these files changes each such export of the editor, and
a rename or a removal stops those exports (the editor names the missing file).
The list is `PANDOC_DIRECTORY_TEMPLATES` in zettlr-pandoc
(`source/app/service-providers/commands/exporter/resolve-export.ts`); its CI
clones `main` of this repository, so a change here that the editor needs lands
here first.

Each other writer gets the macros from the Markdown reader, not from a
template:

- `templates/css/math-macros.md` holds the `\newcommand` line of each macro
  of `styles/macros/mathjax-sources.txt` in a fenced div of the class
  `math-macros`. `bin/generate-mathjax-config.py` writes it; never edit it by
  hand. `just test-commit` runs the generator and fails when it changes a
  generated file.
- The editor gives that file as the first input of the export. The
  `latex_macros` extension of the Markdown reader (on by default) applies
  each definition to the TeX math of the inputs after it, so the writer gets
  the expansion: the OMML of `docx` and `pptx`, the MathML of `odt`, `epub*`,
  `jats*` and `docbook*`, the math of `typst` and `ms`, and the TeX of the
  expansion for each writer that keeps TeX (`markdown`, `rst`, `org`, ...).
  A definition after its use expands nothing, so the file must be first.
- `filters/math-macros.lua` removes the div. A writer that keeps raw TeX
  would otherwise write the definitions into its output.
- A first input of its own changes one thing for the document: a `% title`
  block of Pandoc holds only in the first input. A title in YAML front matter
  holds.
- The TeX writers do not get the file: their templates load the macro style.
- texmath converts the expansion of 1503 of the 1580 macros. For the other
  77 (`\rm`, `\hbox`, `\mkern`, `\vcenter`, `\xhookrightarrow`, ... in the
  body) Pandoc warns "Could not convert TeX math" and keeps the TeX of the
  expansion.

`context` gets the reader input and its template
(`pandoc -D context` with the block before `$for(header-includes)$`), and
the filter `filters/context-mathml.lua`:

- The ConTeXt writer keeps the TeX of each formula, and ConTeXt is no LaTeX:
  it does not define `\operatorname`, `\mathsf`, `\genfrac`, `\textrm` and
  other commands of the expansions. The filter gives each formula as the
  MathML of texmath in `\startmml ... \stopmml`, and the template loads the
  `mathml` module of ConTeXt (`x-mathml`), which typesets it.
- A formula that texmath cannot convert stops the export with the formula.
- The module writes an `<mi>` of some names as the command of the same name
  (`i_replacements` in `x-mathml.lmt`), and ConTeXt defines 17 of them in no
  file (`\arccot`, `\sech`, `\lcm`, `\id`, ...). The template defines each one
  with `\definemathfunction`, as `math-def.mkxl` defines `\arcsin`. After a
  ConTeXt update, the test names each new command that the module writes and
  that is not defined.

The HTML templates other than reveal.js include one MathJax configuration, the
Pandoc partial `templates/mathjax-config.html` (`$mathjax-config.html()$` in
the place of `$math$`). Each such template is `pandoc -D <writer>` with that
line; after a Pandoc release, compare it with the new `pandoc -D <writer>` and
carry the changes over. A template that includes the partial must stay in
`templates/`, as Pandoc finds a partial in the folder of its template.

- The one `macros: {...},` line of the partial and of the reveal.js template
  is written by `bin/generate-mathjax-config.py` (`GENERATED_TEMPLATES`); a
  template with no such line or with more than one stops the generator. Never
  edit it by hand; the same `just test-commit` check covers it. The configuration loads the MathJax packages `mathtools`,
  `centernot` and `stmaryrd`, which the macro expansions use
  (`styles/macros/README.md`). A new HTML template includes the partial; a template with a
  macro map of its own goes into that list.
- **Note HTML is `compile-html`.** A class note (the Makefiles of
  `~/notes`) and `bin/vimpreview.sh` build HTML through
  `just compile-html <note.md> <note.html> [bib_source]`. The note carries
  its metadata in its front matter; the recipe reads no other environment
  variable than those of the justfile (`PANDOC_BIB_SOURCE`,
  `PANDOC_CROSSREF`) and of `tikzcd.lua`. It writes a staged file beside the
  target and renames it only after a build without a Pandoc error, a TikZ
  failure (`[tikzcd-latex-log-begin]`, `[tikzcd] lualatex failed`,
  `[tikzcd] pdf2svg failed`) or an unknown citation in its log: in HTML
  `tikzcd.lua` drops a failed figure and Pandoc exits 0. `tikzcd.lua` writes
  the `[tikzcd-latex-log-begin]` block for each figure whose lualatex run
  fails; its `[tikzcd-figure-error]` marker is only for an error on a line
  of the figure body, so an error in an imported file (an Inkscape
  `.pdf_tex`) has no such marker. A caller gives the path; a shell
  redirection (`> note.html`) empties the file before the build starts.
  `bin/pandoc_stripmacros.sh` expands the macros through
  `templates/css/math-macros.html`, found from its own location.
- `mathjax-root` and `mathjax-fonts` are Pandoc variables for a MathJax that is
  not loaded from its CDN: the folder of the MathJax component and the folder
  of its font packages. The editor sets both to its own copy of MathJax 4. A
  page that embeds the component (`--embed-resources`) cannot find its TeX
  extensions without `mathjax-root`. Without the variables a page loads
  MathJax as Pandoc names it (the default URL depends on the Pandoc version),
  so the configuration must stay valid for MathJax 3 and 4. The partial uses
  `js/mathjax-stmaryrd.js` as a Pandoc template partial and registers it at
  startup only for MathJax 4, before `defaultReady()`. MathJax 3 cannot render
  `\fps`. Do not copy the extension's implementation into the template.
- The reveal.js template is the template of Pandoc (`pandoc -D revealjs`) with
  the MathJax 3 plugin of reveal.js (`RevealMath.MathJax3`) in the place of
  the MathJax 2 plugin. After a Pandoc release, compare it with the new
  `pandoc -D revealjs` and carry the changes over.
- `research_beamer.tex` is `pandoc -D beamer` with the class option
  `notheorems` and `\usepackage{dzg-beamer}` after `$common.latex()$`.
  `dzg-beamer` stops without `notheorems`: beamer otherwise defines theorem
  environments that the macro tree defines too.

`tests/test-mathjax-generator.py` checks each template of the table: the
macro map of each HTML page, pdflatex on each TeX writer and `context` on the
ConTeXt template. It also runs each other writer of `pandoc --list-output-formats`
with the reader input: no output holds a raw macro or a definition, and the
math of the converting writers holds the expansion.

## The `tikzcd.lua` filter contract

`filters/tikzcd.lua` compiles each TikZ block of a document to a PDF and an
SVG. zettlr-pandoc runs it for its live preview
(`packages/tikz-render/src/tikz-render.ts`), so these rules are an interface.
The first line of the filter is the code line
`local ZETTLR_TIKZ_RENDER_PROTOCOL = <n>`. zettlr-pandoc reads the number
from that line and refuses a filter without it. A change to one of the rules
raises that number and the constant `TIKZ_RENDER_PROTOCOL` of zettlr-pandoc.
The filter loads no other Lua file of this repository.

- **Which blocks.** A raw TeX block that starts with `\begin{tikzcd}` or
  `\begin{tikzpicture}`, a block that is `\input{file}` of a figure, a
  `tikz` code block, and, in HTML, an inline `\dynkin` (the LaTeX preamble
  loads `dynkin-diagrams`, so LaTeX output needs no handler). An `\input`
  names a figure when its extension is `.tikz` or `.tikzcd`, or when the
  body of the file, after its leading comment lines, opens a `tikzpicture`
  or a `tikzcd`.
- **Where an `\input` is found.** An absolute path; else the folder of the
  document (`PANDOC_DOC_PATH`); else `FIGURES_SOURCE_DIR` (default
  `figures/`), then its `tikz/` and `tikzcd/`; else one level of
  subfolders of those three. A path without an extension also tries
  `.tikz`, `.tikzcd` and `.tex`.
- **The per-figure template.** `FIGURE_TEMPLATE_FILE` (default
  `templates/standalone-tikz.tex`), read when the first figure compiles: a
  load of the filter with empty input needs no render environment.
  zettlr-pandoc gives the template of `~/.pandoc`, so no other filter data
  tree owns a preamble. The figure body goes in at the `<>` marker (the QTikz
  convention) after Pandoc applies the template, so a `$` in the figure
  never reaches the template engine. The count of lines before the marker
  maps a TeX `l.NN` line to the line of the figure body.
- **The cache key.** The SHA-1 of the figure after `\input` resolution, the
  template text, `TIKZ_RENDER_CONTEXT_HASH` and the folder of the document.
  zettlr-pandoc gives a digest of the whole template, package and input
  graph in `TIKZ_RENDER_CONTEXT_HASH`, because the template itself only
  says `\usepackage{dzg-tikz}`. The folder is in the key because TeX loads
  relative assets (`\includegraphics`) from it. A full-document `tikz` code
  block has no template, so its key has no template text.
- **The cache files.** `SVG_DIR/dzgtikz-<hash>.svg` and `.pdf` (default
  `FIGURES_DIR/rendered`). A pair that exists is a hit unless
  `TIKZ_FORCE_REBUILD=1`. With `TIKZ_CACHE_ONLY=1` a miss writes
  `[tikzcd-cache-miss] <hash>` and stops the filter: a viewer that must not
  wait leaves the compile to another job. The PDF is copied as soon as
  lualatex succeeds, so LaTeX output has it when the SVG conversion fails.
  pdf2svg writes into the scratch folder; the SVG is copied beside its
  target and renamed over it, so a failed conversion or copy keeps the last
  good SVG that the editor shows.
- **The processes.** lualatex (`--shell-escape`, with `TEXINPUTS` the
  folder of the document, `FIGURE_STYLES_DIR//` and `FIGURES_SOURCE_DIR//`)
  and pdf2svg run through `pandoc.system.command`, with no shell, so a path
  with a space is one argument (`tests/test-tikz-paths.sh`). Their output is
  captured: stdout of the filter is its document, and a TeX log in it would
  break a later `pandoc -f latex` of the output.
- **The failure markers, on stderr.** For each `! message` of the TeX log
  whose `l.NN` line is in the figure body:
  `[tikzcd-figure-error] <body line>|<message>|<source line>`; the source is
  last, so a reader splits on the first two `|`. Then the whole TeX log
  between `[tikzcd-latex-log-begin]` and `[tikzcd-latex-log-end]`. Without a
  TeX log: `[tikzcd] lualatex failed (exit N) without a TeX log:` and the
  output. A failed conversion or copy of the SVG:
  `[tikzcd] pdf2svg failed (exit N):` and the cause.
- **A figure that fails.** LaTeX output stops the filter. HTML output keeps
  the raw block, which the HTML writer drops, so the page renders without
  that figure (a template that lacks a library shows as a missing figure).
- **IDs in an SVG** get a prefix of the hash of the SVG, so two inline SVGs
  in one page have no common `id`.

## Releases and downstream sites

Downstream sites (pandoc-ssg sites) float on the current `main` of this
repository. Nothing pins them. Each site commits `pandoc-config.known-good`
at its root: the `git describe --tags` name of the pandoc-config commit
that it was last verified against (`pandoc-config bump` in pandoc-ssg writes
it). A release gives those names a version.

- **Release.** `just release` cuts the next release of `main`. git-cliff
  (`cliff.toml`) computes the version from the conventional commits since
  the last tag: a `!` or `BREAKING CHANGE` bumps the major version, a
  `feat` the minor version, and each other type the patch version. The
  recipe writes `CHANGELOG.md`, commits it, pushes `main`, then pushes an
  annotated tag and makes the GitHub release with the notes of the
  version. Write commit subjects as conventional commits, so that the
  version and the changelog are right. Tags are history: never move or
  delete one.
- **Staleness report.** `just staleness-report [site...]` reads the marker
  of each site and compares its commit with `HEAD` by Git ancestry. With no
  arguments it reads `downstream-sites.txt`; add a new site there. A tag
  only labels a commit, so a marker behind `HEAD` is stale also when no
  release is between them. The statuses are `stale` (with the releases
  and every commit since the marker), `current`, `ahead`, `diverged`,
  `no marker` and `unresolvable`. The report reads the local checkout of
  each site, so fetch the site first. `tests/test-staleness-report.py`
  proves it.

## Authoring Style

`AUTHORING_STYLE.md` holds the markdown conventions for prose compiled through
this configuration: fenced divs for theorem-like environments, `align`
environments rather than `\[ \]` for display math, and list and heading
spacing. `just format-md <dir>` enforces the mechanical parts.

## Macro Semantics: object-valued macros are atomic

Macros in this repository are an authoring language, not merely abbreviations for
individual glyphs. A macro that names a mathematical construction must take the data
of that construction as arguments and expand to the complete mathematical object.
Its arguments are the semantic boundary of the object.

For example, the fibre product is written

```latex
\fiberprod{X}{S}{Y}
```

and means the complete object `X \times_S Y`. Do not reduce it to a one-argument
shortcut for the decorated multiplication sign `\times_S` and then rely on adjacent
source text to provide `X` and `Y`.

This principle applies equally to products, powers, base changes, localizations,
quotients, completions, derived constructions, and similar notation. If a construction
has operands/base/index/object data, those belong in the macro's argument list. Do not
rewrite a semantic macro into a postfix/prefix decoration or a bare operator symbol just
because the rendered glyphs look similar.

Low-level typography helpers are permitted only when they are genuinely implementation
details. Do not substitute such a helper for a public semantic macro, change a public
macro's arity, or discard operands during cleanup/migration without auditing authored
call sites and preserving the mathematical object represented.

When migrating or consolidating macros:

1. Determine the mathematical object/function represented, not merely the current TeX
   expansion.
2. Search real authored call sites before changing arity or argument order.
3. Treat an argument that is ignored, or a macro used as a detached infix/postfix
   fragment, as a semantic-redesign warning requiring review.
4. Regenerate all derivative MathJax artifacts from the canonical `styles/macros/`
   sources; never hand-maintain a divergent consumer copy.
5. Add a regression for repaired semantic signatures so future normalization cannot
   collapse them again.

Known inherited fragment-style APIs and their call-site migration status are tracked in
`MACRO-SEMANTICS-AUDIT.md`. Read that ledger before changing an existing macro signature.

## Macro Vocabulary: one name per meaning

Each mathematical meaning has exactly one macro. Two names with one meaning are
drift: keep the longer, more semantic name and delete the other. Mathcal letters
are `\mc<letter>` and fraktur letters are `\mf<Letter>`.

Short spellings belong to the editor, not to the macro set.
`styles/shortcuts.json` maps each retired alias to its canonical name, for
quicktex-style expansion and autocomplete. An alias whose old macro had
more than one meaning maps to the list of canonical names, one per meaning
(`"di": ["divisorof", "divisibility"]`); the author chooses. A new short form goes there, never
into `styles/macros/`.

Different meanings that share notation are intended. `\closure` and
`\univcover` both render an overline, and `\discriminant` and `\laplacian`
both render Δ: the macro records which object the author means. Semantic names
also stay separate from typographic ones (`\lieg` versus `\mfg`, `\OO` versus
`\mco`).

## Macro Tier System

Macros in `styles/macros/` organized by MathJax compatibility:

- **Tier 1**: Simple shortcuts, no args (MathJax-safe)
- **Tier 2**: With arguments (MathJax-safe)
- **Tier 3**: Complex TeX primitives (LaTeX-only)
- **Tier 4**: Package-dependent (LaTeX-only)

Plus domain files: categories, spectral, tikz, environments.

## Key Files

- **dzg-unified.sty**: Main unified package (loads all tiers)
- **dzg-mathjax.sty**: MathJax subset for Obsidian (tiers 1-2 only)
- **preambles/**: Shared preamble fragments (loaded via \input by .sty files)
- **templates/**: Document templates and starters (KOMA-Script, AMS, pandoc)
- **bin/*.lua**: Pandoc filters (tikzcd, callouts, image handling)
- **tests/**: Comprehensive test suite verifying all macros compile

See subdirectory READMEs for detailed documentation.

## Figures: the dzg TikZ library

Every figure draws with the style vocabulary in
`styles/macros/tikz/tikzlibrarydzg.code.tex`, which the preamble loads with
`\usetikzlibrary{dzg}`. Constructors that draw an object from its data live in
`styles/macros/tikz/constructors/`; the objects are figures in
`figures/objects/` (rule 6). Read the library file before drawing.

1. **One style per mathematical element.** Coxeter vertices are
   `vertex=white|black|doubled`, edges `coxeter edge=<m>` (3, 4, 5, 6,
   `infinity`, `dotted`) or `coxeter edge label=<m>`, parabolic subdiagrams
   `parabolic`. Baily–Borel diagrams use `cusp0`, `cusp1`, `incidence`,
   `cusp label`, `cusp brace`. IAS and Kulikov pictures use `ias region`,
   `ias boundary`, `ias edge`, `ias singularity=<multiplicity>`, `ias surgery`,
   `fan ray`, `kulikov component`, `double curve`, `triple point`,
   `self intersection`. Lattice polygons use
   `lattice grid`, `lattice point`, `polygon region`, `long side`, `short side`,
   `boundary point`, `marked point`. Posets and schematics use `poset node`,
   `poset element` and `poset cover` (`\posetfromjson`),
   `degeneration`, `moduli blob`, `stratum`, `boundary stratum`. Stable curves
   use `curve component`, `curve node`, `dual vertex`, `genus`.
2. **Figures define no styles.** No `\tikzset`, `\tikzstyle`, `\colorlet`,
   `\pgfsetlayers`, `\usetikzlibrary`, or drawing macros in a figure file, and
   no raw colours or line widths. A missing element is added to the library,
   in its family section, with its meaning in a comment.
3. **Conventions.** Degeneration arrows and poset cover edges point from the
   generic stratum to the more degenerate one. A 0-cusp is a rounded box and a
   1-cusp a box, with the lattice inside the node. The vertex mark is the
   datum; the document states what it encodes (root norm, or δ).
4. **Layers.** The library sets `background, Dynkin behind, edges, main,
   foreground`. Diagram edges go in `[on edge layer]` scopes between node
   centres so vertices cover the edge ends; highlights go
   `[on background layer]`.
5. **Sizes are absolute.** A picture's `scale` spaces coordinates and does
   not change glyph sizes, so the same element looks the same in every figure.
6. **Constructors build; objects are figures.**
   `styles/macros/tikz/constructors/dzg-<family>.tex` holds building blocks
   only: commands and keys that take the data of an object (a vertex and edge
   list, the vertices of a polygon, edge vectors and surgeries) and draw it.
   No constructor names a particular object. Each mathematical object — a
   Coxeter diagram, cusp diagram, lattice polygon, integral-affine sphere,
   lattice table, or stratum — is one file,
   `figures/objects/<family>/<name>.tikz`: drawing commands without a
   `tikzpicture`, assembled from constructors, with its data source in the
   leading comment, its points named `-<point>`, and its canonical labels
   behind the constructors' label keys. `just render-figures` renders it alone
   to `figures/rendered/objects/<family>/<name>.{pdf,svg}`. A figure that
   decorates or combines objects places each with
   `\pic (Q) at (x,y) [<keys>] {object=<family>/<name>};` and draws on
   `Q-<point>`: highlights, extra labels, arrows, overlays. A document that
   shows one object alone uses its render, or a `tikzpicture` holding the one
   `\pic`. A second drawing of the same object anywhere — another file, a
   legacy copy, inline TikZ in a document — is a defect.
7. **Data comes from the mathematics.** When copies disagree, compute the
   correct data (Gram matrices, root norms, polygon rules, lattice invariants)
   with the research preamble (`~/research/src/dzack_research/preamble/`) or
   derive it from the source paper, and cite the source in the object's
   comment. Keep one version, chosen by the data and not by appearance.

## Figures: survey the library landscape before drawing

Read this section before writing any TikZ under `figures/`. It records what
went wrong when a figure was built without it, the procedure for finding the
right library, how to add a library to the shared preamble, and the verified
map of libraries that own the figure kinds this repository needs.

### What went wrong, and the rules that follow

The genus-2 boundary poset figure was first built from `.. controls` with
hand-computed control offsets and `to[out=, in=, looseness=]` segments. The
loops came out as peaks, then the sine waves came out as polylines, then the
tails carried inflections. Three patch commits each fixed one symptom inside
the same wrong construction. The hobby library, which draws a smooth curve
through listed points, had been loaded by the preamble the entire time.

1. **Survey before drawing.** Before the first `\draw`, name the kind of
   object in each cell (smooth curve, self-intersecting curve, surface of
   genus g, Coxeter diagram, graph, polytope, hyperbolic domain) and find the
   library that owns it, using the procedure and the map below. Do not start
   from `.. controls` or `to[out=, in=]`.
2. **Hand-placed Bézier control points are hand-rolled code.** Computing
   control offsets, out/in angles, or `looseness` by arithmetic encodes the
   author's calculation in the source. Nobody can edit the figure without
   redoing the calculation. A curve is specified by the points it passes
   through, in order; the library computes the tangents.
3. **One fix that needs a second fix means the method is wrong.** Do not
   patch parameters a second time. Replace the construction.
4. **Visual verification has a resolution and a scope.** A 110 dpi overview
   and one crop are not a check. Rasterize the entire figure at 300 dpi
   (`pdftoppm -png -r 300 -singlefile <pdf> <out>`), look at every cell, and
   only then claim a visual property. Inflections, polyline facets, and
   tangent breaks are invisible below print resolution.
5. **A user report of a visual defect is an observation, not a claim to
   rebut.** Re-render and look before explaining why the output must be fine.
   "It is a Bézier" says nothing about whether it looks smooth.
6. **"Not in the preamble" is not a blocker.** Any TikZ library or LaTeX
   package on CTAN can be added to the shared preamble in one line; see
   *Adding a library* below. Hand-rolling because a library is not yet loaded
   is the same failure as not surveying.
7. **Both figure renderers run lualatex.** `bin/render_figures.py` and
   `filters/tikzcd.lua` compile with `lualatex --shell-escape`, so packages that do their
   arithmetic in Lua through the `\directlua` primitive are available:
   PGF's `graphdrawing` implements its layout algorithms in Lua, `\posetfromjson`
   runs Graphviz `dot` from Lua, and
   `luahyperbolic` is a LuaLaTeX package. The whole-document recipes
   (`compile-tex`, `compile-pandoc`) still run latexmk in pdflatex mode, so
   a figure that needs a Lua package must be rendered as a standalone figure
   and included, not inlined in a pdflatex document. The preamble guards the
   pdfTeX-only lines (`inputenc`, microtype `kerning`/`spacing`, the `xypdf`
   driver behind `luatex85`) by engine, so both engines compile it.

### Procedure: finding the library before starting

Run these in order and stop at the first hit. Every command is available on
this machine.

1. **Check the map below.** If the figure kind has a row, use that library.
2. **Check the preamble.** `styles/preambles/dzg-preamble.tex` has the
   single `\usetikzlibrary{...}` line and the `\RequirePackage` block that
   every document and every standalone figure inherits.
3. **Check the local TeX Live for a candidate.** A TikZ library ships as
   `tikzlibrary<name>.code.tex`; a package ships as `<name>.sty`. The
   first two commands find a TikZ library and a package; `texdoc` opens
   the manual.

   ```bash
   kpsewhich tikzlibraryhobby.code.tex
   kpsewhich dynkin-diagrams.sty
   texdoc hobby
   ```

4. **Search TeX Live by description and by file name.** Search several
   phrasings; package names rarely match the mathematical term. The first
   command matches descriptions, the second the names of shipped files.

   ```bash
   tlmgr search --global 'hyperbolic'
   tlmgr search --global --all --file 'tikzlibrary.*knot'
   ```

5. **Search CTAN topics.** `https://ctan.org/topic/pgf-tikz` lists every
   TikZ library and package on CTAN; `https://ctan.org/topic/graphics-curve`,
   `graphics-3d`, `diagram-comm`, `diagram-maths`, and `diagram-block` are the
   topics most figure kinds here fall under. Read the package description
   and skim its manual before deciding it does not fit.
6. **Check the PGF manual.** Part V of `texdoc pgf` lists every library that
   ships with PGF itself (`graphs`, `shapes.*`, `decorations.*`, `perspective`,
   `intersections`, `spy`, `through`, `turtle`, ...). Many figure needs are
   already covered there.
7. **Only if every step fails**, record the negative search (the terms and
   topics tried) in the figure's leading comment, then draw by hand with the
   highest-level primitive available (`hobby` for any curve, `graphs` for any
   graph), and add a row to the map saying no library was found.

### Adding a library to the preamble

There is one owner for loaded libraries: `styles/preambles/dzg-preamble.tex`.
It is `\input` by `dzg-unified.sty`, `dzg-tikz.sty`, and
`dzg-dissertation.sty`, so one edit reaches every pandoc document, every
standalone figure rendered by `just render-figures`, every figure the
`tikzcd.lua` filter compiles, and the dissertation. Never load a library
inside a figure file; the figure body is inserted after `\begin{document}`.

1. **TikZ library:** add its name to the `\usetikzlibrary{...}` line in the
   `% TikZ and diagrams` block.
2. **LaTeX package:** add `\RequirePackage{<name>}` to the same block, after
   `\RequirePackage{tikz}`.
3. **Package not installed** (`kpsewhich` finds nothing): TeX Live lives in
   `/opt/texlive/2026` and is root-owned, so install with
   `sudo tlmgr install <package>` (type `! sudo tlmgr install <package>` in
   the prompt to run it in this session), or use a user tree via
   `tlmgr init-usertree` followed by `tlmgr --usermode install <package>`.
4. **Verify:** `just render-figures <one figure>` compiles a standalone
   figure through the preamble, and `just test` compiles the macro, template,
   and TikZ suites that catch a library that breaks an existing document.
5. **Commit the preamble change on its own** with the figure kind that
   needed it in the commit body, so the library's purpose is recoverable.

### Verified library map

Every row was checked against the local TeX Live with `kpsewhich` on
2026-09-23. *preamble* means `dzg-preamble.tex` already loads it. *add to
preamble* means it is installed and one line in the preamble enables it.
*install* means it is on CTAN but not in the local TeX Live. *Lua-based* means
the package computes in Lua via `\directlua`, so it works in rendered figures but not in the pdflatex document recipes (rule 7).

Go to these first, in this order, for the figure kinds this repository draws:

| Figure kind | Library | Status | Manual |
| --- | --- | --- | --- |
| Smooth curves through given points; nodal curves; closed blobs for moduli-space schematics | `hobby` (`to[curve through={...}]`, `closed hobby`, `use Hobby shortcut`) | preamble | `texdoc hobby` |
| Over/under crossings, breaking a path at intersections, path surgery, knot diagrams | `spath3` library, `knots` library | add to preamble | `texdoc spath3`, `texdoc knots` |
| Braids, mapping-class pictures | `braids` library | add to preamble | `texdoc braids` |
| Surfaces of genus g, cobordisms, pants decompositions, degenerations drawn as surfaces | `tqft` library | add to preamble | `texdoc tqft` |
| Coxeter and Dynkin diagrams of a named type: finite, affine, folded, marked, with edge labels | `dynkin-diagrams` package | preamble; the objects `coxeter/G2`, `G2-affine`, `H3` and `H4` use it. `coxeter/A4` and `coxeter/E8` are drawn by `dzg-coxeter.tex` and can move to `\dynkin A4` and `\dynkin E8` | `texdoc dynkin-diagrams` |
| Coxeter diagrams of no named type: hyperbolic reflection groups, with roots at given coordinates and weighted edges | `styles/macros/tikz/constructors/dzg-coxeter.tex` (README, **Coxeter diagrams**) | preamble; `dynkin-diagrams` draws only the named Kac-Moody types, so `coxeter/k3-F4`, `sterk-cusp-*`, `vinberg-*` and `sterk-cusp-cover-*` (drawn over a `vinberg-*` object) need it | README |
| Commutative diagrams | `tikz-cd`, `quiver` | preamble; `styles/quiver.sty` | `texdoc tikz-cd` |
| Hasse diagram of any finite poset: divisor lattices, subgroup lattices, strata posets, Tamari lattices | `\posetfromjson` (`styles/macros/tikz/constructors/dzg-posets.tex`): Sage writes the poset as JSON with `bin/poset_json.sage`; the library grades it (default `balanced`), lets Graphviz `dot` order and space each grade, and names each element's box so a figure places any content in it | preamble; LuaLaTeX with `--shell-escape`, figures only (rule 7) | `styles/macros/tikz/lua/dzg-poset.lua` |
| Root posets of simple Lie algebras, coloured by simple root | `lie-hasse` package | add to preamble | `texdoc lie-hasse` |
| Dual graphs, stable-graph posets, stratification Hasse diagrams drawn by hand placement | `graphs` library (node/edge syntax, `graphs.standard`) | add to preamble | `texdoc pgf`, Part V |
| The same, with automatic layered or force-directed layout | `graphdrawing` library with `layered` / `force` | add to preamble; Lua-based, figures only (rule 7) | `texdoc pgf`, Part IV |
| Hasse diagrams of finite posets without graph drawing | `causets` package | add to preamble | `texdoc causets` |
| Two-dimensional Euclidean lattices and their sublattices | `euclidean-lattice` package | add to preamble | `texdoc euclidean-lattice` |
| Polytopes, fans, integral affine spheres, 3D projections | `tikz-3dplot` package, `perspective` library, `pgfplots` for surfaces | add to preamble (`perspective` is a PGF library); no toric-fan library found on CTAN | `texdoc tikz-3dplot`, `texdoc pgfplots` |
| Regular complex polytopes | `pst-cox` | install; PSTricks, not TikZ; last resort | `texdoc pst-cox` |
| Hyperbolic plane, Poincaré disk, fundamental domains | `luahyperbolic` package | add to preamble; Lua-based, figures only (rule 7); no pdfTeX alternative found on CTAN | `texdoc luahyperbolic` |
| Euclidean constructions, circles through points, tangents | `tkz-euclide` package | add to preamble | `texdoc tkz-euclide` |
| Snakes, zigzags, coils, random steps along a path | `decorations.pathmorphing` | preamble | `texdoc pgf` |
| Arrow tips and marks placed along a path | `decorations.markings`, `arrows.meta`, `bending` | preamble (`bending`: add) | `texdoc pgf` |
| Braces, brackets, and text along a path | `decorations.pathreplacing`, `decorations.text` | preamble (`decorations.text`: add) | `texdoc pgf` |
| Intersections of two named paths as coordinates | `intersections`, `calc` | preamble | `texdoc pgf` |
| Zoomed insets | `spy` library | add to preamble | `texdoc pgf` |
| Function plots, data plots, 3D surface plots | `pgfplots` | preamble | `texdoc pgfplots` |
| Node shapes beyond circle and rectangle | `shapes.geometric`, `shapes.misc`, `shapes.multipart` | preamble (`shapes.*` loads all) | `texdoc pgf` |
| Matrices of nodes, tables of diagrams | `matrix` library | preamble | `texdoc pgf` |
| Positioning nodes relative to each other, fitting a box around nodes | `positioning`, `fit`, `backgrounds` | preamble | `texdoc pgf` |
| Celtic and other periodic knotwork | `celtic` library | add to preamble | `texdoc celtic` |
| Graphs from Graphviz layouts | `dot2texi` | requires the `dot2tex` tool; last resort | `texdoc dot2texi` |

### Worked example

`figures/objects/moduli/m2-curve-*.tikz`, the stable curves that
`figures/tikz/m2_boundary_stable_curves_poset.tikz` places, draw every nodal
curve as a Hobby spline. A self-node is four points around the loop; a node
between two components is the shared point listed in both curves; the alpha
curve lists its node point twice. The git history of the figure file shows the
three hand-rolled attempts that preceded it and what each one got wrong.
