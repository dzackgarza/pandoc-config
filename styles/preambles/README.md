# Preambles

Shared preamble fragments — `\input`-ed by `.sty` package files.
These are not full document templates (see `../templates/`).

### `dzg-preamble.tex`

Shared `\RequirePackage` block loaded by both `dzg-unified.sty` and `dzg-tikz.sty`.
It inputs `dzg-math-preamble.tex`, then loads the document packages: microtype,
hyperref, bookmark and enumitem.

### `dzg-math-preamble.tex`

The packages that the macros and the figures need: the math packages, TikZ and
its libraries, the diagram packages. `dzg-preamble.tex` and `dzg-beamer.sty`
input it. Beamer loads hyperref itself and owns its lists, so a beamer document
loads this part only.

## Document Templates

Full document starters (`\documentclass` + preamble) live in `templates/`:

- `templates/koma-article.tex` — KOMA-Script `scrartcl` for general documents
- `templates/ams-article.tex` — AMS `amsart` for journal submissions

## Macro Loading

Both preamble fragments and templates load `dzg-unified.sty`, which includes:
- Tier 1: Simple MathJax-compatible shortcuts
- Tier 2: Commands with arguments (MathJax-compatible)
- Tier 3: Complex TeX-specific commands
- Tier 4: Package loading and document setup
- Domain-specific macros (categories, spectral sequences, TikZ)

See `macros/README.md` for details on the tier system.
