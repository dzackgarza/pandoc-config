# Pandoc Configuration

Personal Pandoc and LaTeX configuration for generating PDFs from markdown and managing LaTeX macros.

## Directory Structure

```
styles/                     # LaTeX macro system (styles assemble macros)
├── dzg-unified.sty        # Main style - loads all macros
├── dzg-mathjax.sty        # MathJax subset (tiers 1-2)
├── freetikz.sty           # External TikZ helper
├── quiver.sty             # Commutative diagrams
├── tikzit.sty             # TikZ editor integration
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
\usepackage{dzg-unified}  % Loads all macros
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

Required in `~/.zshrc`:

```bash
# Canonical source: ~/.envrc
export TEXINPUTS=".:$HOME/.pandoc/templates//:$HOME/.pandoc/styles//:$HOME/.pandoc/styles/macros//:${TEXINPUTS:-}:"
export BIBINPUTS=".:$HOME/.pandoc/bib//:${BIBINPUTS:-}"
export PATH="$HOME/.pandoc/bin:$PATH"
```

## Authoring Style

`AUTHORING_STYLE.md` holds the markdown conventions for prose compiled through
this configuration: fenced divs for theorem-like environments, `align`
environments rather than `\[ \]` for display math, and list and heading
spacing. `just format-md <dir>` enforces the mechanical parts.

## Macro Semantics: object-valued macros are atomic

Macros in this repository are an authoring language, not merely abbreviations for
individual glyphs. A macro that names a mathematical construction MUST take the data
of that construction as arguments and expand to the complete mathematical object.
Its arguments are the semantic boundary of the object.

For example, the fibre product is written

```latex
\fiberprod{X}{S}{Y}
```

and means the complete object `X \times_S Y`. It must never be reduced to a one-argument
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
