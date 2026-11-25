# LaTeX Macro System - Test Documents

This directory contains test documents that exercise the unified LaTeX macro system.

## Test Files

### LaTeX Test

- **test-latex-macros.tex** - Comprehensive LaTeX document testing all macro tiers
- **test-macros.sty** - Test package using the installed style tree
- **test-latex-macros.pdf** - Generated output from `just _test-macros` (ignored)

### Pandoc Test

- **test-pandoc-macros.md** - Markdown document with same macro tests
- **just test** - Runs the complete repository test recipe

### MathJax Test

- **test-mathjax-generator.py** - Checks canonical macro expansions, generated
  template projections, rendered Pandoc preview/reveal.js configuration, legacy
  shims, and LaTeX compilation of the MathJax subset
  (`just _test-mathjax-generator`).
- **test-mathjax-macros.ts** - Typesets every macro of
  `templates/css/mathjax-macros.json` in MathJax 4 with the ams, mathtools and
  stmaryrd packages and fails on a TeX error (`just _test-mathjax-macros`)

## Compiling the LaTeX Test

Run the LaTeX test from the repository root:

```bash
just _test-macros
```

This produces `test-latex-macros.pdf` which exercises:
- **Tier 1:** Number systems (ℤ, ℚ, ℝ, ℂ), operators (Hom, Aut, Ext, Tor)
- **Tier 2:** Delimiters (abs, norm, gens), constructions (fps, laurent)
- **Tier 3:** Matrices (matt, cvec), stacking (stack)
- **Tier 4:** Declared operators (spanof, supp, hilb)
- **Categories:** Category names (Set, Grp, Ring), limits/colimits
- **Spectral:** Bordism spectra (MO, MSO), K-theory (KO, KU), tmf

## Known Issues

### Command Conflicts

Some macros conflict with LaTeX defaults:
- `\ae` (already defined by LaTeX)
- `\too` (conflicts with a standard command)

These are handled by the macro files but may generate warnings.

### TEXINPUTS Configuration

For the macro system to work correctly in production, TEXINPUTS must include:
```bash
export TEXINPUTS=".:$HOME/.pandoc/styles//:$HOME/.pandoc/styles/macros//:$HOME/.pandoc/styles/preambles//:$HOME/.pandoc/config//:"
```

This is already configured in `~/.zshrc`. Reload your shell or run `source ~/.zshrc` to
apply.

### Test-Specific Package

`test-macros.sty` uses absolute paths to avoid TEXINPUTS issues during testing.
In production, use `\usepackage{dzg-unified}` instead (requires TEXINPUTS).

## What the Tests Verify

✅ **Tier 1 macros** (simple shortcuts) compile without errors ✅ **Tier 2 macros** (with
arguments) render correctly ✅ **Tier 3 macros** (complex TeX) produce correct output ✅
**Tier 4 macros** (DeclareMathOperator) work with amsmath loaded ✅ **Category theory
macros** from categories.tex work ✅ **Spectral sequence macros** from spectral.tex work
✅ **Domain separation** is maintained (categories, spectral as separate files)

## Production Usage

In real documents, `\usepackage{dzg-unified}` loads each tier:

```latex
\documentclass{scrartcl}
\usepackage{dzg-unified}
\begin{document}
$\ZZ, \QQ, \RR$
\end{document}
```

`\input{koma-article}` loads dzg-unified too:

```latex
\input{koma-article}
\begin{document}
$\ZZ, \QQ, \RR$
\end{document}
```

## Test Coverage

The test documents include examples of:
- All number systems and field extensions
- Calligraphic and fraktur letters
- Mathematical operators (100+ operators)
- Delimiters and brackets
- Algebraic constructions (polynomial rings, power series, quotients)
- Chain/cochain complexes
- Matrices and vectors
- Category theory (categories, functors, limits)
- Spectral sequences (bordism, K-theory, tmf)
- Algebraic geometry (Pic, Spec, cohomology)
- Number theory (p-adics, Galois groups)
- Topology (homology, homotopy groups)
- Differential geometry (tangent bundles, exterior algebra)

All macros successfully tested in the LaTeX compilation.

## Theorem references (`just test-references`)

`tests/test-project-references.sh` runs the Pandoc stage of the recipes
(`_compile-pandoc-tex`) in a scratch directory and checks the `.tex` that it
writes. The stage is the first dependency of `compile-pandoc-project` (mode
`crossref`) and of `compile-pandoc` (mode `no-crossref`). Each step names the template of this checkout by its absolute
path, so Pandoc does not read it from `~/.pandoc`, which can be another
checkout.

| Step | What it proves |
| --- | --- |
| 1 | The `ref_prefixes` table of `filters/convert_amsthm_envs.lua` has the keys of `THEOREM_DIV_PREFIXES` in zettlr-pandoc (`source/common/util/pandoc-quick-reference.ts`). The test holds the one copy of that list in this repository, so a prefix that one repository adds, removes or renames fails it. `not` is a Lua keyword, so the table writes it as `["not"]=true`. |
| 2 | Two ordered inputs: the content of the first file comes before the content of the second; a theorem div with an id has its `\label`; `@thm:` citations become `\cref`, with the prefix, the suffix, the suppressed form (`\ref`) and the clusters of the authored text; a bibliography citation stays `\autocite`. The LaTeX writer wraps lines, so a match of more than one word runs on a copy with the whitespace collapsed. |
| 3 | A file name with a space stays one argument, and its content goes in its place in the order. |
| 4 | A proof div has no number and no label; an empty key gives no `\label{thm:}`. |
| 5 | The attribute-style sample (`title=`/`ref=` attributes, no theorem citations) gives the `.tex` of `fixtures/theorem-references/expected_attribute_style.tex` through `research_draft.tex`. Lines that start with `%` are not compared: they are TeX comments, and the comment check of the commit hook refuses them in the fixture. Pandoc writes one, from its partial `passoptions.latex`. |
| 6 | On the single-file path, `@thm:` citations become `\cref` too. |
| 7 | The `.tex` of step 2 compiles with latexmk under the plain style branch of this checkout (`TEXINPUTS` names this checkout, not `~/.pandoc`), so each environment that the filter writes is defined (#6). latexmk runs without `-f`, so an undefined environment fails the exit code. |
| 8 | `_compile-pandoc-tex` refuses a mode other than `crossref` and `no-crossref` before it makes a directory (zettlr-pandoc#5, item B19). |
| 9 | The same fixture compiles under the arxiv branch (`research_paper.tex`, by absolute path): no undefined environment (#7) and no LaTeX error. |

The workspace fixtures are copies of
`zettlr-pandoc/test/fixtures/reference-workspace/ProjectA/`. `Theorems.md` is
a verbatim copy. `Halphen_Surfaces.md` has its cross-file lemma key changed to
`lem:kodaira:embedding`, a bare `@thm:torelli`, and citations with a prefix, a
suffix, the suppressed form and a mixed cluster.
