# Pandoc Configuration

Personal Pandoc and LaTeX configuration for generating PDFs from markdown and managing LaTeX macros.

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

## Figures: the dzg TikZ library

Every figure draws with the style vocabulary in
`styles/macros/tikz/tikzlibrarydzg.code.tex`, which the preamble loads with
`\usetikzlibrary{dzg}`. Named diagrams built from it live in
`styles/macros/tikz/dzg-diagrams.tex`. Read the library file before drawing.

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
6. **"Not in the preamble" is never a blocker.** Any TikZ library or LaTeX
   package on CTAN can be added to the shared preamble in one line; see
   *Adding a library* below. Hand-rolling because a library is not yet loaded
   is the same failure as not surveying.
7. **Both figure renderers run lualatex.** `bin/render_figures.py` and
   `filters/tikzcd.lua` compile with lualatex, so packages that do their
   arithmetic in Lua through the `\directlua` primitive are available:
   PGF's `graphdrawing` implements its layout algorithms in Lua, and
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
   `tikzlibrary<name>.code.tex`; a package ships as `<name>.sty`.

   ```bash
   kpsewhich tikzlibraryhobby.code.tex     # TikZ library present?
   kpsewhich dynkin-diagrams.sty           # package present?
   texdoc hobby                            # open its manual
   ```

4. **Search TeX Live by description and by file name.** Search several
   phrasings; package names rarely match the mathematical term.

   ```bash
   tlmgr search --global 'hyperbolic'            # match descriptions
   tlmgr search --global --all --file 'tikzlibrary.*knot'   # match shipped file names
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
| Coxeter and Dynkin diagrams: finite, affine, folded, marked, with edge labels | `dynkin-diagrams` package | add to preamble; `styles/macros/tikz/diagrams.tex` still hand-rolls these and should migrate | `texdoc dynkin-diagrams` |
| Commutative diagrams | `tikz-cd`, `quiver` | preamble; `styles/quiver.sty` | `texdoc tikz-cd` |
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

`figures/tikz/m2_boundary_stable_curves_poset.tikz` draws every nodal curve
as a Hobby spline. A self-node is four points around the loop; a node between
two components is the shared point listed in both curves; the alpha curve
lists its node point twice. The git history of that file shows the three
hand-rolled attempts that preceded it and what each one got wrong.
