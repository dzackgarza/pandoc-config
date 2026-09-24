# pandoc

LaTeX styles, pandoc filters, and templates for the dzackgarza publishing pipeline.

## Principles

These principles govern all work in this subtree.
They are not suggestions.

### Personal macros are absolute, never conditional

Personal style definitions must never hedge on availability, wrap in `\@ifundefined`,
`\ifdefined`, or any other conditional guard.
They exist to enforce uniformity across the author's content.
Every macro means the same thing everywhere, or it is not defined.
There is no fallback, no graceful degradation, no "best effort."

### Macro breakouts serve multiple rendering targets

The separation of macros into category files and tiers exists to support multiple
consuming applications, each with different capabilities:

- **GUI editors** (QTikz, TikZiT, quiver app, Inkscape) need clean subsets of the macro
  set to render correctly.
- **MathJax-based targets** (personal blog, Obsidian notes, pandoc-preview) need a
  restricted subset that avoids TeX primitives and `\pgf`/TikZ code.
  Macro files are organized so that a MathJax-compatible subset can be extracted
  mechanically.

The goal is a single personal macro language that is interpretable everywhere, from
research papers to blog posts to interactive previews.

### Centralize, never duplicate

No file in this subtree may be copied or reproduced elsewhere.
The entire point of this tree is:

- **Centralize** every macro, style, filter, and template in one place.
- **Uniformize** definitions so there is exactly one way to express a given concept.
- **Propagate automatically** through a canonical rebuild recipe that runs the
  regression suite, regenerates derivative files (MathJax definitions, SVG caches,
  etc.), and pushes changes to consuming systems.

Any duplication creates desync.
Desync is the root cause of the problems this tree exists to solve.

### Single source, multiple outputs

A single source document must cleanly produce:

- A research paper LaTeX draft (via `dzg-unified.sty` or `dzg-tikz.sty`)
- A PDF (via `xelatex`/`lualatex`)
- An HTML version for blog posts (via pandoc + MathJax)
- A viewable preview in pandoc-preview
- An Obsidian note with rendered mathematics and diagrams

Filters in `filters/` handle the rendering pipeline uniformly.
TikZ diagrams are compiled into SVGs via minimal standalone templates, then included as
SVG in both LaTeX and HTML outputs.
This approach:

- Eliminates all TikZ scaling issues (SVG is vector, scales uniformly)
- Produces cached SVG artifacts that can be reused across documents
- Decouples diagram rendering from document compilation

### Centralized figure library

All TikZ figures and diagrams live in a centralized library, not alongside individual
papers or notes. This prevents:

- **Diagram drift** -- the same Coxeter diagram, cusp diagram, or commutative square
  looks identical across every document that uses it.
- **Reinvention** -- commonly reused diagrams (Coxeter diagrams, cusp diagrams, Dynkin
  diagrams, spectral sequence pages) are defined once and iterated, not recreated
  per-paper.
- **Stale variants** -- when a diagram is improved, every document that uses it gets the
  improvement automatically.

Rendering a diagram from the library should be trivial: invoke it by name, get a cached
SVG (or PDF), include it anywhere.

### Escape hatches for collaboration

When a document must leave this ecosystem (e.g., submitted to Overleaf for collaborative
editing), the pipeline must produce a self-contained artifact that:

- Includes all required macro definitions inline (no external dependencies)
- Optionally renders all diagrams to macro-free PDF/PNG (for collaborators who cannot
  compile the source TikZ)

The macro breakout structure enables this: extract the relevant subset, prepend it to
the document, and flatten.

### The rebuild recipe

The canonical workflow for making changes:

1. Add or modify macros in `styles/macros/`.
2. Run the regression suite (`just test-*`) to verify nothing is broken.
3. Regenerate derivative files (MathJax definitions, SVG caches, etc.)
   via the canonical rebuild recipe.
4. Push updates to consuming systems (blog, Obsidian vault, etc.).

This pipeline should be stable: set up something that works well and leave it mostly
untouched for years.
New macros are additive.
Structural changes to the pipeline itself are rare.

## Setup

`~/.pandoc` is this repository. TeX finds its files through `TEXINPUTS`, set in
`~/.envrc`:

```bash
export TEXINPUTS=".:$HOME/.pandoc/figures//:$HOME/.pandoc/templates//:$HOME/.pandoc/styles//:$HOME/.pandoc/styles/macros//:$HOME/.pandoc/lib//:$HOME/.pandoc/preambles//:$HOME/.pandoc/config//:"
export BIBINPUTS=".:$HOME/.pandoc/bib//:${BIBINPUTS:-}"
export PATH="$HOME/.pandoc/bin:$PATH"
```

`figures//` must be on the path: figures load objects (`figures/objects/`) and
poset data by relative path. External tools: `lualatex` and `pdflatex` (TeX
Live), `latexmk`, `biber`, `pandoc`, `pdf2svg`, Graphviz `dot` (poset layout),
and Sage (writing poset data).

Figures that use Lua (`\posetfromjson`, PGF graph drawing, `luahyperbolic`)
compile only with `lualatex --shell-escape`. The figure renderers pass both;
the whole-document recipes run pdflatex, so such a figure is rendered
standalone and included (see [Rendering figures](#rendering-figures)).

## LaTeX entry points

| Package | Loads | Use for |
| --- | --- | --- |
| `dzg-unified` | the shared preamble, `dzg-macros`, the theorem environments, tables and floats, `biblatex` (biber, alphabetic), `cleveref`, pandoc compatibility | every paper, note and pandoc PDF. Option `arxiv` swaps in `environments-arxiv.tex`. |
| `dzg-macros` | macro tiers 1-4, `categories`, `spectral`, `figure-include` | a document with its own preamble that wants the macros only |
| `dzg-tikz` | the shared preamble and the macros, without document-level packages | standalone figures (the renderers use it) |
| `dzg-mathjax` | tiers 1-2, `categories`, `spectral` | the MathJax-safe subset (Obsidian, blog) |
| `dzg-dissertation` | the shared preamble, the tiers, then `dissertation-overrides.tex` | the dissertation |
| `dzg-beamer` | `dzg-macros`, clearing Beamer's theorem names first | slides |

```latex
\documentclass{amsart}
\usepackage{dzg-unified}
\begin{document}
$\ZZ \subset \QQ \subset \RR \subset \CC$, \quad $\Hom(A, B)$, \quad $\gens{x, y}$
\end{document}
```

`styles/preambles/dzg-preamble.tex` is the one place packages and TikZ
libraries are loaded; every entry point inputs it. Adding a package or a TikZ
library means one line there (AGENTS.md, "Adding a library").

## Math macros

The macros live in `styles/macros/`, split by where they can render:

| File | Contents | Renders in |
| --- | --- | --- |
| `tier1-mathjax-simple.tex` | zero-argument shortcuts and operators: `\ZZ`, `\Hom`, `\Aut`, ... | LaTeX, MathJax |
| `tier2-mathjax-args.tex` | commands with arguments: `\gens{...}`, `\abs{...}`, `\fiberprod{X}{S}{Y}`, ... | LaTeX, MathJax |
| `tier3-tex-complex.tex` | commands using TeX primitives MathJax lacks (`\mathpalette`, boxes, kerning) | LaTeX |
| `tier4-preamble.tex` | preamble-level settings | LaTeX |
| `categories.tex` | category theory: named categories, functors, limits | LaTeX, MathJax |
| `spectral.tex` | spectral sequences | LaTeX, MathJax |
| `figure-include.tex` | `\ctikzsvg` | LaTeX with `--shell-escape` |
| `environments.tex`, `environments-arxiv.tex` | theorem-like environments | LaTeX |
| `dissertation-overrides.tex` | the dissertation's own definitions | LaTeX (dissertation) |

Every macro and environment, with its arguments and expansion, is listed in the
[generated reference](#math-macros-and-environments) below.
`styles/macros/README.md` states the tier criteria.

A macro that names a mathematical construction takes the data of the
construction as arguments and expands to the whole object (`\fiberprod{X}{S}{Y}`
is `X \times_S Y`, never a postfix `\times_S`); AGENTS.md, "Macro Semantics",
and `MACRO-SEMANTICS-AUDIT.md` hold the rule and the migration ledger.

MathJax targets read a generated copy: `just generate-math-macros` parses the
files in `styles/macros/mathjax-sources.txt` and writes
`templates/css/mathjax-macros.{mjs,ts,json,html}` and the macro map of
`templates/pandoc_preview_template.html`. `styles/obsidian/` holds the Obsidian
setup.

## Figures

### The dzg TikZ library

`\usetikzlibrary{dzg}` (loaded by the preamble) defines one style per
mathematical element. Figures use these names and define no styles, colours,
layers or drawing macros of their own; a missing element is added to
`styles/macros/tikz/tikzlibrarydzg.code.tex` (AGENTS.md, rules 1-7). Sizes are
absolute: a picture's `scale` spaces coordinates and leaves node sizes alone.

**Layers**, bottom to top: `background`, `Dynkin behind`, `edges`, `main`,
`foreground`. Scope keys `on background layer`, `on edge layer`,
`on foreground layer`. Diagram edges go on the edge layer between node centres,
so vertices cover their ends; highlights go on the background layer.

**Colours**: `dzg accent` (rays, maps), `dzg singular` (singular points,
surgeries), `dzg highlight` (parabolic subdiagrams, emphasis), `dzg region`
(filled regions), `dzg grid`, `dzg muted`, `dzg blob` (moduli schematics),
`dzg elliptic`, `dzg parabolic` (subdiagram types).

| Family | Styles |
| --- | --- |
| Coxeter, Dynkin, Vinberg | `vertex=white\|black\|doubled\|even`, `vertex label`, `coxeter edge=3\|4\|5\|6\|infinity\|dotted`, `coxeter edge label=<m>` (m >= 7), `parabolic`, `fold`, `fold axis`, `inactive`, `marked vertex`, `reflected root`, `quotient map`, `subdiagram cell=elliptic\|parabolic\|other` |
| Baily-Borel cusps | `cusp0` (rounded box), `cusp1` (box), `cusp label`, `incidence`, `cusp brace`, `cusp map`, `cusp image`, `doubled mark` |
| IAS, fans, Kulikov models | `ias region`, `ias boundary`, `ias edge`, `ias singularity=<multiplicity>`, `ias surgery`, `fan ray`, `kulikov component`, `double curve`, `nontoric blowup`, `exceptional curve`, `triple point`, `self intersection` |
| Lattice polygons | `lattice grid`, `lattice point`, `polygon region`, `long side`, `short side`, `axis side`, `boundary point=<fill>`, `marked point=<label>`, `side label=<text>`, `monomial`, `polygon title`, `polytope edge`, `distinguished point`, `coordinate axis`, `hatched region` |
| Posets, moduli schematics | `poset node`, `degeneration` (generic to degenerate), `morphism`, `poset group`, `moduli blob`, `stratum`, `boundary stratum`, `mirror move=complement\|U\|U(2)`, `hyperplane`, `poset element`, `poset cover` |
| Stable curves, dual graphs | `curve component`, `curve node`, `dual vertex`, `genus`, `curve point`, `singular point`, `constructed point` |
| Spaces, maps, contours | `point`, `map arrow`, `distinguished curve`, `contour=<fractions>`, `over strand`, `branch cut`, `glued edge=1\|2`, pgfplots `complex plane` |

AGENTS.md, "Figures: survey the library landscape before drawing", maps figure
kinds to the TeX packages that own them (Hobby curves, knots, TQFT surfaces,
`dynkin-diagrams`, `lie-hasse`, graph drawing, hyperbolic geometry, ...).

### Objects

Each mathematical object (a Coxeter diagram, cusp diagram, lattice polygon,
integral-affine sphere, lattice table, stratum, space, commutative diagram) is
one file `figures/objects/<family>/<name>.tikz`: drawing commands without a
`tikzpicture`, built from the constructors below, with its data source in its
leading comment. A figure places it and draws on its named points:

```latex
\begin{tikzpicture}
  \pic (Q) {object=ade/minus-E8-minus};                          % points Q-pstar, Q-1, ...
  \pic[scale=0.4, ias labels=multiplicities, ell={2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,4,6,4}]
    (S) at (8,0) {object=ias/symington-18-2-0};
  \draw[degeneration] (Q-pstar) -- (S-p16);
\end{tikzpicture}
```

- `\pic (Q) at (x,y) [<keys>] {object=<family>/<name>}` inputs the file. Its
  points, named `-<point>` in the file, become `Q-<point>`.
- Keys in the pic options reach the object: label schemes, `ell={...}`,
  `maximal parabolic=<name>`, and so on.
- The picture's `scale` spaces the object's coordinates; node sizes stay
  absolute.
- A document that shows one object alone uses its render,
  `figures/rendered/objects/<family>/<name>.pdf`, or a `tikzpicture` holding
  the one `\pic`.

The [generated catalogue](#figure-objects) lists every object.

### Constructors

`styles/macros/tikz/constructors/` holds the building blocks objects are made
of. No constructor names a particular object.

**Coxeter diagrams** (`dzg-coxeter.tex`). The root `<i>` is the node `-<i>`.
- `\coxeterlabels{<scheme>}`: the object's canonical label scheme.
- `\coxeterroot{<i>}{<mark>}{<coordinate>}{<label direction>}`: one root.
- `\coxeterroots{<i>/<mark>/<coordinate>/<dir>, ...}`: several roots.
- `\coxeteredges{<weight>}{<path through -<i> names>}`: edges of one weight.
- `\coxeterchain{<weight>}{<first>}{<last>}`: the edges i -- i+1.
- `\coxetersquare{<side>}{<edges per side>}{<first>}{sw|nw}{<corner mark>}{<mark between>}`:
  a cycle of simple edges around a square.
- `\coxeterparabolic{<name>}{{<i>,...}, ...}`: a maximal parabolic subdiagram,
  stored in the object and highlighted when the figure passes
  `maximal parabolic=<name>`.
- `\coxeterpair[<keys>]`, `\coxetervertex{<mark>}`: legends.
- Pics `dynkin folding={<opts>}{<diagram>}{<opts>}{<diagram>}` and
  `root chain={<mark>/<norm label>/<weight>, ...}`.
- Keys: `root labels=alpha|r|ell|index|none`, `parity marks=true|false`,
  `maximal parabolic=<name>`.

**Vinberg diagrams and mirror moves** (`dzg-vinberg.tex`).
- `\coxeterEdiagram{<n>}{<mark>}`: the tree T_{2,3,n-3}, numbered as in Bourbaki.
- `\latticevertex[<node opts>][<label opts>]{<name>}{<mark>}{<coordinate>}{<lattice>}{<dir>}`:
  a lattice in a mirror-move poset.
- `\mirrorstages{<y>}`: the column heads S, T, T̄, T̄̄.
- Key: `mirror targets=valid|all`.

**Baily-Borel cusp diagrams** (`dzg-bb-cusps.tex`).
- `\bbcusp{<cusp0|cusp1, opts>}{<name>}{<coordinate>}{<content>}{<label dir>}{<canonical label>}{<eta label>}`.
- `\bblabel{<canonical>}{<eta>}`: the text of the active scheme.
- `\bbincidences{<0-cusp>/<1-cusp>/<divisibility>, ...}`: incidence arrows.
- `\bbbrace{<x from>}{<x to>}{<y>}{<text>}`: a brace with a column's invariants.
- `\bbcolumn{<x>}{<prefix>}{<first>}{<second>}{<next to last>}{<last>}`: a column
  of 1-cusps with an ellipsis.
- Keys: `cusp labels=canonical|eta|none`, `incidence divisibility`.

**Lattice polygons, Symington polygons, fans** (`dzg-polygons.tex`).
- `\adepolygon[ade affine]{<px>/<py>}{<x/y, ...>}`: the toric ADE pair of
  Alexeev-Thompson, Notation 3.7. It draws the polygon, p* (`-pstar`), the
  boundary divisor with its side lengths, the Dynkin diagram along C' and the
  monomials.
- `\adetitle{<math>}`: the decorated symbol.
- `\symingtonpolygon[first=, last=, closed, charges={i/c, ...}]{<sides>}{<surgeries>}`:
  a polygon from edge vectors l_i d_i with Symington surgeries.
- `\setell{<first index>}{<default l values>}` and `\ellvalue{<i>}`: the
  values l_i, which a figure overrides with `ell={...}`.
- `\iassingularity{<point>}{<charge>}`.
- `\fanrays{<i/a/b/anchor, ...>}` and `\fancones{<i/coordinate, ...>}`.
- Keys: `ade labels=monomials|none`, `ade title=true|false`,
  `ias labels=canonical|multiplicities|none`, `ias involutions`, `ell={...}`,
  `fan labels=canonical|none`, `fan length=<factor>`.

**Tables of lattice invariants** (`dzg-nikulin.tex`).
- `\latticetable{<x name>}{<x max>}{<y name>}{<y max>}{<x/y/mark, ...>}`: a grid
  with a vertex mark at each listed point, named `-<x>-<y>`.
- Key: `lattice table labels=axes|none`.

**Moduli strata** (`dzg-moduli.tex`).
- `\dualvertex[<label distance>]{<name>}{<x,y>}{<genus>}{<placement>}`.
- `\dualloop{<x,y>}{left|right}`.
- `\genuslabel{<placement>}{<x,y>}{<genus>}`.
- Key: `genus labels=all|none`.
- Strata posets are drawn with `\posetfromjson`.

**Spaces and spectral sequences** (`dzg-spaces.tex`).
- `\spacelabel{<x,y>}{<label>}`.
- `\complexaxes{<xmin>}{<xmax>}{<ymin>}{<ymax>}`.
- The pic `ss page` with keys `ss p={...}`, `ss q={...}`, `ss p labels`,
  `ss q labels`, `ss p name`, `ss q name`, `ss ticks`, `ss column sep`,
  `ss row sep`, `ss homological`.
- `\ssentry{E}{p}{q}{<content>}` and `\ssdifferential[<opts>]{E}{r}{p}{q}`.
- Key: `space labels=canonical|none`.

### Posets: `\posetfromjson`

`\posetfromjson` draws the Hasse diagram of any finite poset. Sage writes the
poset; the library grades it, lets Graphviz `dot` order and space each grade,
and names every element's box so the figure can put arbitrary content in it.
LuaLaTeX with `--shell-escape` only.

1. Write the poset as networkx node-link JSON with the Sage helper:

   ```python
   load("~/.pandoc/bin/poset_json.sage")
   P = posets.DivisorLattice(24).subposet([d for d in divisors(24) if d > 1])
   poset_json(P, "m2-strata.json", name=str, label=lambda d: "$%s$" % d)
   ```

   Each element carries an `id` (its TikZ node name), and optionally a
   `label` (TeX), a `style` (TikZ keys, e.g. `subdiagram cell=elliptic`) and a
   `grade` (an integer or `p/q`; the helper writes the rank function when P is
   graded). `order=` fixes the left-to-right order dot starts from. Keep the
   generating script, with its mathematical source in a comment, next to the
   JSON under `figures/objects/`.

2. Draw it, then place content at the elements:

   ```latex
   \begin{tikzpicture}
     \posetfromjson[name prefix=G-, poset axis=horizontal, grade distance=4.6cm,
       element width=2.4cm, element height=1.2cm, element labels=false,
       cover style=degeneration]{objects/moduli/m2-strata.json}
     \foreach \e in \posetelements \pic at (G-\e) {object=moduli/m2-graph-\e};
   \end{tikzpicture}
   ```

| Key | Default | Meaning |
| --- | --- | --- |
| `poset grading` | `balanced` | used when the elements carry no grade: `balanced` ((longest chain from bottom − longest chain to top)/2; symmetric under duality), `longest chain from bottom` (the rank; for subgroup lattices the number of prime factors of the order), `longest chain to top`, `minimum total cover length` (dot's own layering) |
| `poset axis` | `vertical` | grades bottom to top, or `horizontal`: right to left with the top element leftmost |
| `grade distance` | `1cm` | distance per unit of grade; rational grades are spaced exactly |
| `element width`, `element height` | `1cm`, `0.6cm` | the box every element's content fits in; the spacing follows it |
| `element sep` | `3mm` | least gap between two boxes of one grade |
| `element positions` | `dot` | dot's coordinates (vertical covers, rows with gaps; sparse or irregular posets), or `even`: dot's order, evenly spaced rows (full rows, such as Boolean and face lattices) |
| `element style` | none | added to every element node, e.g. `poset node` |
| `element labels` | `true` | the JSON labels in the boxes |
| `element layer`, `cover layer` | `main`, `edges` | layers of the element nodes and of the covers |
| `cover style` | `poset cover` | the covers, e.g. `degeneration` |
| `cover direction` | `down` | covers drawn from the larger element to the smaller, or `up` |

Other keys (`name prefix`, `yshift`, ...) apply to the scope around the
diagram; each layout is centred horizontally on 0, with the top element at
height 0. A grading that would draw a cover level or downward is an error.
`styles/macros/tikz/lua/dzg-poset.lua` documents the layout and why the
default grading was chosen.

### Rendering figures

- `just render-figures` renders every figure in `figures/tikz/` (top level),
  `figures/tikzcd/` and `figures/objects/` to `figures/rendered/` as PDF and
  SVG. `just render-figures <file>` renders one; `--force` skips the cache.
  - The engine is `lualatex --shell-escape`, with `templates/standalone-tikz.tex`
    (`\usepackage{dzg-tikz}`) as the wrapper.
  - An object file is wrapped in a `tikzpicture` and rendered to
    `rendered/objects/<family>/`.
  - The cache key covers the figure and every library file.
- In a LaTeX document, `\ctikzsvg[<includesvg options>]{<figure path>}`
  renders the figure through the same script and includes its SVG. It needs
  `--shell-escape`.
- In markdown, a `tikzpicture` or `tikzcd` block, or `\input{<figure>.tikz}`,
  is compiled by `filters/tikzcd.lua` into an SVG (HTML) or PDF (LaTeX).
- `templates/qtikz-template.pgs` is the QTikz editor template.

## Pandoc

The justfile is a module: a project imports it with `mod pandoc '~/.pandoc/justfile'` and
calls `just pandoc::<recipe>` (`just --list` in this repository shows all):

```bash
just pandoc::compile-pandoc input_file=main.md output_name=paper template=research_draft.tex
just pandoc::compile-tex main_file=main.tex output_name=paper
just pandoc::preview notes.md pdf research_draft.tex
```

| Recipe | Does |
| --- | --- |
| `compile-pandoc`, `compile-pandoc-project` | markdown to PDF through a LaTeX template and latexmk |
| `compile-tex` | a LaTeX project with latexmk and the global bibliography |
| `preview` | compile a markdown file and recompile on every change (entr), viewing the PDF in zathura |
| `format-md`, `format-markdown` | one sentence per line (prettier), or semantic line breaks (flowmark) |
| `render-figures` | see [Rendering figures](#rendering-figures) |
| `generate-math-macros` | the MathJax macro files |
| `readme-reference` | the generated reference below |
| `download-arxiv`, `extract-ref`, `test-references`, `clean-refs` | fetch arXiv sources and extract references to markdown |
| `clean` | remove build artifacts |
| `test` | the full test suite |

**Templates** (`templates/`): `research_draft.tex` and `research_paper.tex`
(amsart), `ams-article.tex`, `koma-article.tex`, `homework_template.tex`,
`pandoc_problem_template.tex`, `beamer_template.latex`, HTML templates
(`pandoc_HTML.template`, `pandoc_preview_template.html`, `research_draft.html`,
reveal.js and impress.js), `standalone-tikz.tex` (figures),
`qtikz-template.pgs`; `metadata/` holds default YAML metadata, `css/` the
stylesheets and the generated MathJax macros.

**Filters** (`filters/`):

| Filter | Does |
| --- | --- |
| `tikzcd.lua` | compiles TikZ and tikz-cd blocks and `\input` figures to SVG or PDF |
| `convert_amsthm_envs.lua` | fenced divs (`::: {.Theorem}`) to theorem environments |
| `lamport_proof.lua` | structured (Lamport) proofs in markdown |
| `include.lua` | include other markdown files |
| `run_code.lua` | run fenced code blocks at build time and embed the output (RUN_CODE.md) |
| `sagemath-pandoc-filter` | evaluate Sage code blocks |
| `convert_math_delimiters.lua`, `normalize_displaymath.lua`, `align-math.lua` | math delimiters and display-math layout |
| `normalize_fenced_divs.lua` | fenced-div layout |
| `obsidian.lua`, `obsidian_callouts.lua` | strip Obsidian wikilinks, comments and tags; render callouts |
| `hide_solutions_html.lua`, `hide_solutions_pdf.lua` | collapse or drop solution blocks |
| `replace_symbols_html.lua` | MathJax replacements for symbols it lacks (`\coloneqq`) |
| `components.lua`, `post-navigation.lua`, `youtube.lua`, `select_images.lua`, `semanticlean.lua` | blog components, navigation, embeds, image selection, make4ht HTML cleanup |

`defaults/`, `csl/` and `bib/` hold pandoc defaults, citation styles and the
bibliography.

## Tests

`just test` loads every macro file and exercises the macros
(`tests/test-latex-macros.tex`), compiles every
template, the TikZ vocabulary and every figure object (`tests/test-tikz-macros.tex`,
pdflatex), the tikzcd filter, the Lamport-proof filter, the poset layout
(`tests/test-posets.tex`, lualatex) and checks that the generated reference
below is current. The commit hook runs it.

<!-- BEGIN GENERATED REFERENCE: bin/generate-readme-reference.py -->

## Reference (generated)

Regenerate with `just readme-reference`; `just test` fails when this section is stale.

## Math macros and environments

### `styles/macros/tier1-mathjax-simple.tex`

| Macro | Args | Expansion |
| --- | --- | --- |
| `\AA` | 0 | `{\mathbf{A}}` |
| `\CC` | 0 | `{\mathbf{C}}` |
| `\DD` | 0 | `\mathbb{D}` |
| `\EE` | 0 | `{\mathbb{E}}` |
| `\FF` | 0 | `{ \mathbf{F} }` |
| `\GG` | 0 | `{\mathbf{G}}` |
| `\HH` | 0 | `{\mathbb{H}}` |
| `\KK` | 0 | `{\mathbb{K}}` |
| `\LL` | 0 | `{\mathbb{L}}` |
| `\NN` | 0 | `{\mathbb{N}}` |
| `\PP` | 0 | `{\mathbf{P}}` |
| `\QQ` | 0 | `{\mathbf{Q}}` |
| `\RR` | 0 | `{\mathbf{R}}` |
| `\SS` | 0 | `{\mathbb{S}}` |
| `\TT` | 0 | `{\mathbb{T}}` |
| `\UU` | 0 | `\mathbb{U}` |
| `\VV` | 0 | `{\mathbf{V}}` |
| `\ZZ` | 0 | `{\mathbf{Z}}` |
| `\bbm` | 0 | `{\mathbb{M}}` |
| `\GGr` | 0 | `{\mathbb{Gr}}` |
| `\OP` | 0 | `{\mathbb{OP}}` |
| `\SpSp` | 0 | `{\mathbb{S}}` |
| `\CCpadic` | 0 | `{ \CC_p }` |
| `\CCstar` | 0 | `{\CC\units }` |
| `\cstar` | 0 | `{\CC\units }` |
| `\FFbar` | 0 | `{\bar\FF}` |
| `\FFp` | 0 | `{\FF_p}` |
| `\FFpn` | 0 | `{\FF_{p^n}}` |
| `\Fp` | 0 | `{\FF_p}` |
| `\Fpbar` | 0 | `\bar{\FF_p}` |
| `\Fpn` | 0 | `{\FF_{p^n} }` |
| `\fq` | 0 | `{\FF_{q}}` |
| `\fqbar` | 0 | `\bar{\FF_{q}}` |
| `\fqr` | 0 | `{\FF_{q^r}}` |
| `\kG` | 0 | `{kG}` |
| `\kk` | 0 | `{\mathbf{k}}` |
| `\QQbar` | 0 | `{ \bar{ \mathbf{Q} } }` |
| `\QQladic` | 0 | `{ \QQ_\ell }` |
| `\QQpadic` | 0 | `{ \QQ_{\hat p} }` |
| `\Qbar` | 0 | `{ \bar{ \mathbf{Q} } }` |
| `\ZZbar` | 0 | `{ \bar{ \ZZ } }` |
| `\ZZelladic` | 0 | `{ \ZZ_\ell }` |
| `\ZZG` | 0 | `{\ZZ G}` |
| `\ZZH` | 0 | `{\ZZ H}` |
| `\ZZhat` | 0 | `{ \widehat{ \ZZ } }` |
| `\ZZladic` | 0 | `{ \ZZ_{\hat \ell} }` |
| `\ZZpadic` | 0 | `{ \ZZ_{\hat p} }` |
| `\ZZpcomplete` | 0 | `{ \ZZpadic }` |
| `\ZZplocal` | 0 | `{ L_p \ZZ }` |
| `\ZZprof` | 0 | `{ \hat{\ZZ} }` |
| `\ZpZ` | 0 | `\ZZ/p` |
| `\zlnz` | 0 | `\ZZ/\ell^n\ZZ` |
| `\zlz` | 0 | `\ZZ/\ell\ZZ` |
| `\znz` | 0 | `\ZZ/n\ZZ` |
| `\zpz` | 0 | `\ZZ/p\ZZ` |
| `\Banach` | 0 | `\mathcal{B}` |
| `\cA` | 0 | `{\mathcal{A}}` |
| `\cF` | 0 | `{\mathcal{F}}` |
| `\cG` | 0 | `{\mathcal{G}}` |
| `\cM` | 0 | `{\mathcal{M}}` |
| `\cX` | 0 | `{\mathcal{X}}` |
| `\Hsh` | 0 | `{ \mathcal{H} }` |
| `\mca` | 0 | `{\mathcal{A}}` |
| `\mcb` | 0 | `{\mathcal{B}}` |
| `\mcc` | 0 | `{\mathcal{C}}` |
| `\mcd` | 0 | `{\mathcal{D}}` |
| `\mce` | 0 | `{\mathcal{E}}` |
| `\mcf` | 0 | `{\mathcal{F}}` |
| `\mcg` | 0 | `{\mathcal{G}}` |
| `\mch` | 0 | `{\mathcal{H}}` |
| `\mci` | 0 | `{\mathcal{I}}` |
| `\mcj` | 0 | `{\mathcal{J}}` |
| `\mck` | 0 | `{\mathcal{K}}` |
| `\mcl` | 0 | `{\mathcal{L}}` |
| `\mcm` | 0 | `{\mathcal{M}}` |
| `\mcn` | 0 | `{\mathcal{N}}` |
| `\mco` | 0 | `{\mathcal{O}}` |
| `\mcp` | 0 | `{\mathcal{P}}` |
| `\mcr` | 0 | `{\mathcal{R}}` |
| `\mcs` | 0 | `{\mathcal{S}}` |
| `\mct` | 0 | `{\mathcal{T}}` |
| `\mcTop` | 0 | `\mathcal{T}\mathsf{op}` |
| `\mcu` | 0 | `{\mathcal{U}}` |
| `\mcv` | 0 | `{\mathcal{V}}` |
| `\mcw` | 0 | `{\mathcal{W}}` |
| `\mcx` | 0 | `{\mathcal{X}}` |
| `\mcX` | 0 | `{\mathcal{X}}` |
| `\mcy` | 0 | `{\mathcal{Y}}` |
| `\mcz` | 0 | `{\mathcal{Z}}` |
| `\MM` | 0 | `{\mathcal{M}}` |
| `\OO` | 0 | `{\mathcal{O}}` |
| `\Path` | 0 | `\mathcal{P}` |
| `\gl` | 0 | `{\mathfrak{gl}}` |
| `\liea` | 0 | `{\mathfrak{a}}` |
| `\lieb` | 0 | `{\mathfrak{b}}` |
| `\lied` | 0 | `{\mathfrak{d}}` |
| `\lief` | 0 | `{\mathfrak{f}}` |
| `\lieg` | 0 | `{\mathfrak{g}}` |
| `\liegl` | 0 | `{\mathfrak{gl}}` |
| `\lieh` | 0 | `{\mathfrak{h}}` |
| `\liel` | 0 | `{\mathfrak{l}}` |
| `\lien` | 0 | `{\mathfrak{n}}` |
| `\lieo` | 0 | `{\mathfrak{o}}` |
| `\liep` | 0 | `{\mathfrak{p}}` |
| `\lieq` | 0 | `{\mathfrak{q}}` |
| `\lier` | 0 | `{\mathfrak{r}}` |
| `\lies` | 0 | `{\mathfrak{s}}` |
| `\liesl` | 0 | `{\mathfrak{sl}}` |
| `\lieso` | 0 | `{\mathfrak{so}}` |
| `\liesp` | 0 | `{\mathfrak{sp}}` |
| `\liesu` | 0 | `{\mathfrak{su}}` |
| `\liet` | 0 | `{\mathfrak{t}}` |
| `\lieu` | 0 | `{\mathfrak{u}}` |
| `\lieW` | 0 | `{\mathfrak{W}}` |
| `\liey` | 0 | `{\mathfrak{y}}` |
| `\mfa` | 0 | `{\mathfrak{a}}` |
| `\mfb` | 0 | `{\mathfrak{b}}` |
| `\mfc` | 0 | `{\mathfrak{c}}` |
| `\mfC` | 0 | `{\mathfrak{C}}` |
| `\mfe` | 0 | `{\mathfrak{e}}` |
| `\mff` | 0 | `{\mathfrak{f}}` |
| `\mfF` | 0 | `{\mathfrak{F}}` |
| `\mfg` | 0 | `{\mathfrak{g}}` |
| `\mfh` | 0 | `{\mathfrak{h}}` |
| `\mfi` | 0 | `{\mathfrak{I}}` |
| `\mfk` | 0 | `{\mathfrak{k}}` |
| `\mfm` | 0 | `{\mathfrak{m}}` |
| `\mfn` | 0 | `{\mathfrak{n}}` |
| `\mfo` | 0 | `{\mathfrak{o}}` |
| `\mfp` | 0 | `{\mathfrak{p}}` |
| `\mfq` | 0 | `{\mathfrak{q}}` |
| `\mfr` | 0 | `{\mathfrak{r}}` |
| `\mfs` | 0 | `{\mathfrak{s}}` |
| `\mfS` | 0 | `{\mathfrak{S}}` |
| `\mfu` | 0 | `{\mathfrak{u}}` |
| `\mfv` | 0 | `{\mathfrak{v}}` |
| `\mfx` | 0 | `{\mathfrak{X}}` |
| `\mfX` | 0 | `{\mathfrak{X}}` |
| `\mfy` | 0 | `{\mathfrak{Y}}` |
| `\mm` | 0 | `{\mathfrak{m}}` |
| `\bigo` | 0 | `{ \mathsf{O}}` |
| `\Gal` | 0 | `{ \mathsf{Gal}}` |
| `\Herm` | 0 | `{\mathsf{Herm}}` |
| `\AMGM` | 0 | `{\mathrm{AMGM}}` |
| `\CM` | 0 | `{\mathrm{CM}}` |
| `\CR` | 0 | `{\mathrm{CR}}` |
| `\CS` | 0 | `\mathrm{CS}` |
| `\CY` | 0 | `{ \text{CY} }` |
| `\dR` | 0 | `\mathrm{dR}` |
| `\EKL` | 0 | `{\mathrm{EKL}}` |
| `\Ell` | 0 | `\mathrm{Ell}` |
| `\Fix` | 0 | `\mathrm{Fix}` |
| `\FP` | 0 | `\mathrm{FP}` |
| `\FS` | 0 | `{ \text{FS} }` |
| `\Hasse` | 0 | `{\mathrm{Hasse}}` |
| `\homog` | 0 | `{ \mathrm{homog} }` |
| `\IAS` | 0 | `\mathrm{IAS}` |
| `\KSBA` | 0 | `\mathrm{KSBA}` |
| `\Lat` | 0 | `\mathrm{Lat}` |
| `\LC` | 0 | `{\mathrm{LC}}` |
| `\lci` | 0 | `\mathrm{lci}` |
| `\MHS` | 0 | `\mathrm{MHS}` |
| `\mot` | 0 | `{ \mathrm{mot}}` |
| `\nef` | 0 | `\mathrm{nef}` |
| `\Nil` | 0 | `{\mathrm{Nil}}` |
| `\Nis` | 0 | `{\mathrm{Nis}}` |
| `\Noeth` | 0 | `{ \mathrm{Noeth} }` |
| `\Orb` | 0 | `{\mathrm{Orb}}` |
| `\PD` | 0 | `\mathrm{PD}` |
| `\Pet` | 0 | `{\mathrm{Pet}}` |
| `\QH` | 0 | `{\mathrm{QH}}` |
| `\Quad` | 0 | `\mathrm{Quad}` |
| `\RT` | 0 | `{\mathrm{RT}}` |
| `\SC` | 0 | `\mathrm{SC}` |
| `\slc` | 0 | `\mathrm{slc}` |
| `\SNF` | 0 | `\mathrm{SNF}` |
| `\spinor` | 0 | `\mathrm{sp}` |
| `\tame` | 0 | `{\mathrm{tame}}` |
| `\tb` | 0 | `\mathrm{tb}` |
| `\td` | 0 | `\mathrm{td}` |
| `\tw` | 0 | `\mathrm{tw}` |
| `\VHS` | 0 | `{\mathrm{VHS} }` |
| `\vir` | 0 | `{\mathrm{vir}}` |
| `\VMHS` | 0 | `\mathrm{VMHS}` |
| `\WI` | 0 | `\mathrm{WI}` |
| `\Zar` | 0 | `{\mathrm{Zar}}` |
| `\alev` | 0 | `{\,\mathrm{a.e.}}` |
| `\amp` | 0 | `{\mathrm{amp}}` |
| `\an` | 0 | `{\mathrm{an}}` |
| `\can` | 0 | `{\mathrm{can}}` |
| `\cell` | 0 | `{ \mathrm{cell}}` |
| `\crys` | 0 | `{\mathrm{crys}}` |
| `\cusp` | 0 | `{ \mathrm{cusp} }` |
| `\elliptic` | 0 | `{\mathrm{ell}}` |
| `\ess` | 0 | `{\mathrm{ess}}` |
| `\even` | 0 | `\text{even}` |
| `\fd` | 0 | `{\mathrm{fd}}` |
| `\fg` | 0 | `{\mathrm{fg}}` |
| `\fin` | 0 | `{\mathrm{fin}}` |
| `\free` | 0 | `{\mathrm{free}}` |
| `\ft` | 0 | `\mathrm{ft}` |
| `\hol` | 0 | `\text{hol}` |
| `\holonomy` | 0 | `{\mathrm{holon}}` |
| `\holomorphic` | 0 | `\text{holo}` |
| `\inc` | 0 | `{\mathrm{inc}}` |
| `\irr` | 0 | `{\mathrm{irr}}` |
| `\isotrop` | 0 | `\mathrm{isotrop}` |
| `\lf` | 0 | `{\mathrm{lf}}` |
| `\lft` | 0 | `\mathrm{lft}` |
| `\odd` | 0 | `\text{odd}` |
| `\perf` | 0 | `{\mathrm{perf}}` |
| `\poly` | 0 | `\mathrm{poly}` |
| `\prop` | 0 | `{\mathrm{prop}}` |
| `\qproj` | 0 | `{\mathrm{qproj}}` |
| `\ram` | 0 | `{\mathrm{ram}}` |
| `\red` | 0 | `{ \text{red} }` |
| `\reg` | 0 | `\mathrm{reg}` |
| `\semi` | 0 | `{\mathrm{semi}}` |
| `\semisimple` | 0 | `{\mathrm{ss}}` |
| `\semisimplification` | 0 | `{\mathrm{ss}}` |
| `\sing` | 0 | `{\mathrm{sing}}` |
| `\smol` | 0 | `{\mathrm{small}}` |
| `\snc` | 0 | `{\mathrm{snc}}` |
| `\ss` | 0 | `{\mathrm{ss}}` |
| `\stable` | 0 | `\mathrm{st}` |
| `\std` | 0 | `\text{std}` |
| `\trop` | 0 | `\mathrm{trop}` |
| `\unstable` | 0 | `\mathrm{unst}` |
| `\vamp` | 0 | `{\mathrm{v.amp}}` |
| `\zar` | 0 | `{\mathrm{zar}}` |
| `\ab` | 0 | `{\operatorname{ab}}` |
| `\ad` | 0 | `{ \operatorname{ad}}` |
| `\Ad` | 0 | `{ \operatorname{Ad} }` |
| `\adjoint` | 0 | `\dagger` |
| `\ae` | 0 | `{ \text{a.e.} }` |
| `\afp` | 0 | `A_{/\FF_p}` |
| `\AG` | 0 | `\operatorname{AG}` |
| `\AGL` | 0 | `\operatorname{AGL}` |
| `\AJ` | 0 | `\operatorname{AJ}` |
| `\Alb` | 0 | `\operatorname{Alb}` |
| `\Amp` | 0 | `{\operatorname{Amp}}` |
| `\ann` | 0 | `\operatorname{Ann}` |
| `\Ann` | 0 | `\operatorname{Ann}` |
| `\annd` | 0 | `{\operatorname{ and }}` |
| `\AO` | 0 | `\operatorname{AO}` |
| `\arccot` | 0 | `\operatorname{arccot}` |
| `\arccsc` | 0 | `\operatorname{arccsc}` |
| `\arcsec` | 0 | `\operatorname{arcsec}` |
| `\area` | 0 | `\operatorname{area}` |
| `\Arg` | 0 | `\operatorname{Arg}` |
| `\ASL` | 0 | `\operatorname{ASL}` |
| `\Aut` | 0 | `\operatorname{Aut}` |
| `\aut` | 0 | `\operatorname{Aut}` |
| `\Ball` | 0 | `{B}` |
| `\barz` | 0 | `\bar{z}` |
| `\Base` | 0 | `{ \operatorname{Base}}` |
| `\bb` | 0 | `\operatorname{BB}` |
| `\bd` | 0 | `{\del}` |
| `\Betti` | 0 | `{\operatorname{Betti}}` |
| `\BiHol` | 0 | `\operatorname{BiHol}` |
| `\Bil` | 0 | `\operatorname{Bil}` |
| `\Bl` | 0 | `\operatorname{Bl}` |
| `\BM` | 0 | `{\operatorname{BM}}` |
| `\Brauer` | 0 | `\mathrm{Br}` |
| `\Bs` | 0 | `\operatorname{Bs}` |
| `\by` | 0 | `\times` |
| `\candim` | 0 | `\operatorname{candim}` |
| `\Cart` | 0 | `\operatorname{Cart}` |
| `\CDiv` | 0 | `\operatorname{CDiv}` |
| `\CF` | 0 | `\operatorname{CF}` |
| `\CH` | 0 | `{\operatorname{CH}}` |
| `\ch` | 0 | `\operatorname{ch}` |
| `\character` | 0 | `\operatorname{ch}` |
| `\characteristic` | 0 | `\operatorname{ch}` |
| `\charpoly` | 0 | `{\mathrm{charpoly}}` |
| `\chern` | 0 | `{\mathrm{ch}}` |
| `\chp` | 0 | `\operatorname{ch. p}` |
| `\Chow` | 0 | `{\operatorname{Ch}}` |
| `\chr` | 0 | `\operatorname{ch}` |
| `\cl` | 0 | `{ \operatorname{cl}}` |
| `\Cl` | 0 | `\operatorname{Cl}` |
| `\codom` | 0 | `\operatorname{codom}` |
| `\codim` | 0 | `\operatorname{codim}` |
| `\coev` | 0 | `\operatorname{coev}` |
| `\coh` | 0 | `\operatorname{coh}` |
| `\cohdim` | 0 | `\operatorname{cohdim}` |
| `\coim` | 0 | `\operatorname{coim}` |
| `\coinfl` | 0 | `\operatorname{coinf}` |
| `\coinv` | 0 | `{\operatorname{coinv}}` |
| `\cok` | 0 | `\operatorname{coker}` |
| `\coker` | 0 | `\operatorname{coker}` |
| `\colspace` | 0 | `\operatorname{colspace}` |
| `\compact` | 0 | `\operatorname{cpt}` |
| `\Cone` | 0 | `{ \mathrm{Cone} }` |
| `\cone` | 0 | `\operatorname{cone}` |
| `\Conf` | 0 | `{\mathrm{Conf}}` |
| `\Conj` | 0 | `{\mathrm{Conj}}` |
| `\const` | 0 | `{\operatorname{const.}}` |
| `\Convv` | 0 | `\operatorname{Conv}` |
| `\cores` | 0 | `\operatorname{coRes}` |
| `\corank` | 0 | `\operatorname{corank}` |
| `\covol` | 0 | `\operatorname{coVol}` |
| `\Cox` | 0 | `{ \operatorname{Cox} }` |
| `\CP` | 0 | `{\mathbf{CP}}` |
| `\Crit` | 0 | `\operatorname{Crit}` |
| `\crit` | 0 | `\operatorname{crit}` |
| `\cross` | 0 | `\times` |
| `\csch` | 0 | `\operatorname{csch}` |
| `\cts` | 0 | `\text{cts}` |
| `\curl` | 0 | `\operatorname{curl}` |
| `\Curv` | 0 | `\operatorname{Curv}` |
| `\Cyl` | 0 | `{ \mathrm{Cyl} }` |
| `\da` | 0 | `\coloneqq` |
| `\Deck` | 0 | `\operatorname{Deck}` |
| `\ddim` | 0 | `\operatorname{ddim}` |
| `\Def` | 0 | `\operatorname{Def}` |
| `\definedas` | 0 | `\coloneqq` |
| `\del` | 0 | `{\partial}` |
| `\delbar` | 0 | `{ \bar{\del}}` |
| `\depth` | 0 | `\operatorname{depth}` |
| `\Der` | 0 | `{ \operatorname{Der} }` |
| `\det` | 0 | `\operatorname{det}` |
| `\diag` | 0 | `\operatorname{diag}` |
| `\diam` | 0 | `{\operatorname{diam}}` |
| `\Diff` | 0 | `\operatorname{Diff}` |
| `\diff` | 0 | `\operatorname{Diff}` |
| `\Diffeo` | 0 | `{\operatorname{Diffeo}}` |
| `\disc` | 0 | `{\operatorname{disc}}` |
| `\discriminant` | 0 | `{\Delta}` |
| `\Disk` | 0 | `{\operatorname{Disk}}` |
| `\Dist` | 0 | `\operatorname{Dist}` |
| `\dist` | 0 | `\operatorname{dist}` |
| `\div` | 0 | `\operatorname{div}` |
| `\Div` | 0 | `\operatorname{Div}` |
| `\dlog` | 0 | `\operatorname{dLog}` |
| `\dom` | 0 | `\operatorname{dom}` |
| `\dP` | 0 | `{\operatorname{dP}}` |
| `\DSt` | 0 | `{ \operatorname{DSt}}` |
| `\Eff` | 0 | `\operatorname{Eff}` |
| `\Emb` | 0 | `{\operatorname{Emb}}` |
| `\En` | 0 | `{\operatorname{En}}` |
| `\End` | 0 | `\operatorname{End}` |
| `\Endo` | 0 | `{ \operatorname{End} }` |
| `\eo` | 0 | `{\operatorname{eo}}` |
| `\essdim` | 0 | `\operatorname{essdim}` |
| `\et` | 0 | `\text{ét}` |
| `\Et` | 0 | `\text{Ét}` |
| `\eul` | 0 | `{\operatorname{eul}}` |
| `\ev` | 0 | `\operatorname{ev}` |
| `\exist` | 0 | `{\exists}` |
| `\Exists` | 0 | `\operatorname{\exists}` |
| `\ext` | 0 | `\operatorname{Ext}` |
| `\Ext` | 0 | `\operatorname{Ext}` |
| `\EZ` | 0 | `\operatorname{EZ}` |
| `\F` | 0 | `{\operatorname{F}}` |
| `\fet` | 0 | `\text{fét}` |
| `\ff` | 0 | `\operatorname{ff}` |
| `\Fil` | 0 | `{\operatorname{Fil}}` |
| `\Fl` | 0 | `\operatorname{Fl}` |
| `\Flat` | 0 | `{\operatorname{Flat}}` |
| `\Forall` | 0 | `\operatorname{\forall}` |
| `\Forget` | 0 | `Forget` |
| `\fp` | 0 | `{ \operatorname{fp} }` |
| `\fppf` | 0 | `{\operatorname{fppf}}` |
| `\Fppf` | 0 | `\mathrm{\operatorname{Fppf}}` |
| `\fpqc` | 0 | `{\operatorname{fpqc}}` |
| `\Fr` | 0 | `\operatorname{Fr}` |
| `\Frac` | 0 | `\operatorname{Frac}` |
| `\Frame` | 0 | `\operatorname{Frame}` |
| `\Frob` | 0 | `\operatorname{Frob}` |
| `\gal` | 0 | `{ \operatorname{Gal}}` |
| `\gen` | 0 | `{\operatorname{gen}}` |
| `\gendim` | 0 | `\operatorname{gendim}` |
| `\generic` | 0 | `{\mathrm{gen}}` |
| `\genus` | 0 | `{\operatorname{gen}}` |
| `\GF` | 0 | `{\mathbf{GF}}` |
| `\GL` | 0 | `\operatorname{GL}` |
| `\Gl` | 0 | `\operatorname{GL}` |
| `\gp` | 0 | `{\operatorname{gp} }` |
| `\Gr` | 0 | `{\operatorname{Gr}}` |
| `\grad` | 0 | `\operatorname{grad}` |
| `\graded` | 0 | `\operatorname{gr}` |
| `\grdim` | 0 | `{\operatorname{gr\,dim}}` |
| `\Griff` | 0 | `\operatorname{Griff}` |
| `\GU` | 0 | `\operatorname{GU}` |
| `\GW` | 0 | `{\operatorname{GW}}` |
| `\hash` | 0 | `{\sharp}` |
| `\HC` | 0 | `{\operatorname{HC}}` |
| `\hd` | 0 | `\operatorname{Head}` |
| `\he` | 0 | `\operatorname{h.e.}` |
| `\height` | 0 | `\operatorname{ht}` |
| `\HF` | 0 | `\operatorname{HF}` |
| `\HFK` | 0 | `\operatorname{HFK}` |
| `\hilb` | 0 | `\operatorname{Hilb}` |
| `\Hilb` | 0 | `\operatorname{Hilb}` |
| `\hilbdim` | 0 | `\operatorname{hilbdim}` |
| `\Hol` | 0 | `\operatorname{Hol}` |
| `\Hom` | 0 | `{ \operatorname{Hom} }` |
| `\Homcx` | 0 | `\operatorname{Hom}^{\bullet}` |
| `\Homeo` | 0 | `{\operatorname{Homeo}}` |
| `\Honda` | 0 | `\mathrm{\operatorname{Honda}}` |
| `\HP` | 0 | `{\operatorname{HP}}` |
| `\HT` | 0 | `{\operatorname{HT}}` |
| `\hyp` | 0 | `{\operatorname{hyp}}` |
| `\Id` | 0 | `\operatorname{Id}` |
| `\id` | 0 | `\operatorname{id}` |
| `\im` | 0 | `\operatorname{im}` |
| `\Index` | 0 | `\operatorname{Index}` |
| `\Inertia` | 0 | `{\mathrm{In}}` |
| `\infl` | 0 | `\operatorname{inf}` |
| `\Inn` | 0 | `\operatorname{Inn}` |
| `\Intersect` | 0 | `\bigcap` |
| `\Isom` | 0 | `{\mathrm{Isom}}` |
| `\Jac` | 0 | `\operatorname{Jac}` |
| `\jan` | 0 | `\operatorname{Jan}` |
| `\JCF` | 0 | `\operatorname{JCF}` |
| `\Kah` | 0 | `{ \operatorname{Kähler} }` |
| `\Kahler` | 0 | `\operatorname{Kähler}` |
| `\Kl` | 0 | `\operatorname{Kl}` |
| `\ko` | 0 | `{\operatorname{ko}}` |
| `\krulldim` | 0 | `\operatorname{krulldim}` |
| `\ks` | 0 | `\operatorname{ks}` |
| `\Kthree` | 0 | `\mathrm{K3}` |
| `\lcm` | 0 | `\operatorname{lcm}` |
| `\Ld` | 0 | `\operatorname{{\mathbb{L} }}` |
| `\len` | 0 | `\operatorname{len}` |
| `\length` | 0 | `\operatorname{length}` |
| `\LGr` | 0 | `{\operatorname{LGr}}` |
| `\Li` | 0 | `\mathrm{Li}` |
| `\lk` | 0 | `\operatorname{lk}` |
| `\Log` | 0 | `\operatorname{Log}` |
| `\Map` | 0 | `\operatorname{Maps}` |
| `\maps` | 0 | `\operatorname{Maps}` |
| `\Maps` | 0 | `\operatorname{Maps}` |
| `\mat` | 0 | `\operatorname{mat}` |
| `\Mat` | 0 | `\operatorname{Mat}` |
| `\maxspec` | 0 | `{\operatorname{maxSpec}}` |
| `\MC` | 0 | `\operatorname{MC}` |
| `\MCG` | 0 | `{\operatorname{MCG}}` |
| `\Mero` | 0 | `\operatorname{Mero}` |
| `\mHH` | 0 | `{\operatorname{HH}}` |
| `\minor` | 0 | `{\operatorname{minor}}` |
| `\minpoly` | 0 | `{\operatorname{minpoly}}` |
| `\mod` | 0 | `\operatorname{mod}` |
| `\Mor` | 0 | `\operatorname{Mor}` |
| `\mproj` | 0 | `\operatorname{mProj}` |
| `\mspec` | 0 | `\operatorname{mSpec}` |
| `\MT` | 0 | `\operatorname{MT}` |
| `\mTHH` | 0 | `{\operatorname{THH}}` |
| `\mult` | 0 | `{\operatorname{mult}}` |
| `\MW` | 0 | `\operatorname{MW}` |
| `\nd` | 0 | `\operatorname{nd}` |
| `\NE` | 0 | `{\operatorname{NE}}` |
| `\Nef` | 0 | `\operatorname{Nef}` |
| `\nil` | 0 | `{\operatorname{nil}}` |
| `\Norm` | 0 | `\operatorname{Nm}` |
| `\NS` | 0 | `{\operatorname{NS}}` |
| `\nullity` | 0 | `\operatorname{nullspace}` |
| `\nullspace` | 0 | `\operatorname{nullspace}` |
| `\Num` | 0 | `\operatorname{Num}` |
| `\Ob` | 0 | `{\operatorname{Ob}}` |
| `\obs` | 0 | `\operatorname{obs}` |
| `\Obs` | 0 | `\operatorname{Obs}` |
| `\OFrame` | 0 | `\operatorname{OFrame}` |
| `\OGr` | 0 | `{\operatorname{OGr}}` |
| `\op` | 0 | `^{\operatorname{op}}` |
| `\Op` | 0 | `{\operatorname{Op}}` |
| `\ord` | 0 | `{\operatorname{Ord}}` |
| `\Ord` | 0 | `{ \mathrm{Ord} }` |
| `\order` | 0 | `{\operatorname{Ord}}` |
| `\oriented` | 0 | `{ \operatorname{oriented} }` |
| `\Orth` | 0 | `{\operatorname{O}}` |
| `\orr` | 0 | `{\operatorname{ or }}` |
| `\Out` | 0 | `\operatorname{Out}` |
| `\per` | 0 | `\operatorname{per}` |
| `\period` | 0 | `\operatorname{period}` |
| `\PGL` | 0 | `\operatorname{PGL}` |
| `\PHS` | 0 | `\operatorname{PHS}` |
| `\pic` | 0 | `{\operatorname{Pic}}` |
| `\Pic` | 0 | `\operatorname{Pic}` |
| `\Pin` | 0 | `{\operatorname{Pin}}` |
| `\Pl` | 0 | `\operatorname{Pl}` |
| `\Places` | 0 | `{\operatorname{Places}}` |
| `\PO` | 0 | `{\operatorname{PO}}` |
| `\pr` | 0 | `{\operatorname{pr}}` |
| `\prim` | 0 | `{\operatorname{prim}}` |
| `\prin` | 0 | `\operatorname{prin}` |
| `\Prin` | 0 | `\operatorname{Prin}` |
| `\proj` | 0 | `\operatorname{proj}` |
| `\Proj` | 0 | `\operatorname{Proj}` |
| `\projection` | 0 | `\operatorname{Proj}` |
| `\PSL` | 0 | `{\operatorname{PSL}}` |
| `\PSU` | 0 | `{\operatorname{PSU}}` |
| `\pt` | 0 | `{\operatorname{pt}}` |
| `\PV` | 0 | `{ \operatorname{PV} }` |
| `\qc` | 0 | `{\operatorname{qc}}` |
| `\QHB` | 0 | `\operatorname{QHB}` |
| `\qst` | 0 | `{\quad \operatorname{such that} \quad}` |
| `\Quot` | 0 | `\operatorname{Quot}` |
| `\radic` | 0 | `\operatorname{rad}` |
| `\Rad` | 0 | `\operatorname{Rad}` |
| `\Ram` | 0 | `\operatorname{Ram}` |
| `\range` | 0 | `\operatorname{range}` |
| `\rank` | 0 | `\operatorname{rank}` |
| `\Rat` | 0 | `\operatorname{Rat}` |
| `\RCF` | 0 | `\operatorname{RCF}` |
| `\Rd` | 0 | `\operatorname{{\mathbb{R} }}` |
| `\Rees` | 0 | `{\operatorname{Rees}}` |
| `\Reg` | 0 | `\operatorname{Reg}` |
| `\Rel` | 0 | `\operatorname{Rel}` |
| `\reldim` | 0 | `\operatorname{reldim}` |
| `\res` | 0 | `\operatorname{res}` |
| `\Res` | 0 | `\operatorname{Res}` |
| `\resultant` | 0 | `{\mathrm{res}}` |
| `\RHom` | 0 | `\operatorname{\mathbb{R}Hom}` |
| `\Ric` | 0 | `\operatorname{Ric}` |
| `\rc` | 0 | `{\operatorname{rc}}` |
| `\rk` | 0 | `{\operatorname{rank}}` |
| `\rot` | 0 | `\operatorname{rot}` |
| `\rowspace` | 0 | `\operatorname{rowspace}` |
| `\RP` | 0 | `{\mathbf{RP}}` |
| `\rref` | 0 | `\operatorname{RREF}` |
| `\RREF` | 0 | `\operatorname{RREF}` |
| `\Sat` | 0 | `\operatorname{Sat}` |
| `\Sec` | 0 | `\operatorname{Sec}` |
| `\sech` | 0 | `{ \mathrm{sech} }` |
| `\selfmap` | 0 | `{\circlearrowleft}` |
| `\Sel` | 0 | `\operatorname{Sel}` |
| `\sep` | 0 | `{ {}^{ \operatorname{sep} } }` |
| `\SF` | 0 | `\operatorname{SF}` |
| `\SGr` | 0 | `{\operatorname{SGr}}` |
| `\sgn` | 0 | `\operatorname{sgn}` |
| `\SHerm` | 0 | `{\operatorname{SHerm}}` |
| `\Sieg` | 0 | `{\mathrm{Sieg}}` |
| `\sig` | 0 | `\operatorname{sig}` |
| `\sign` | 0 | `\operatorname{sign}` |
| `\signature` | 0 | `\operatorname{sig}` |
| `\Sim` | 0 | `\operatorname{Sim}` |
| `\sinc` | 0 | `\operatorname{sinc}` |
| `\Sing` | 0 | `{\operatorname{Sing}}` |
| `\size` | 0 | `{\sharp}` |
| `\SL` | 0 | `{\operatorname{SL}}` |
| `\slope` | 0 | `{\mathrm{slope}}` |
| `\Sm` | 0 | `{\operatorname{Sm}}` |
| `\sm` | 0 | `\setminus` |
| `\smz` | 0 | `\setminus\theset{0}` |
| `\SO` | 0 | `{\operatorname{SO}}` |
| `\soc` | 0 | `\operatorname{Soc}` |
| `\spanof` | 0 | `\operatorname{span}` |
| `\Spc` | 0 | `\operatorname{Spc}` |
| `\spc` | 0 | `\operatorname{Spc}` |
| `\spec` | 0 | `\operatorname{Spec}` |
| `\Spec` | 0 | `\operatorname{Spec}` |
| `\Spf` | 0 | `\operatorname{Spf}` |
| `\Spin` | 0 | `{\operatorname{Spin}}` |
| `\spinornorm` | 0 | `{\mathrm{spinornorm}}` |
| `\Sq` | 0 | `\operatorname{Sq}` |
| `\sq` | 0 | `\square` |
| `\SSym` | 0 | `{\operatorname{SSym}}` |
| `\stab` | 0 | `{\operatorname{Stab}}` |
| `\Stab` | 0 | `{\operatorname{Stab}}` |
| `\Star` | 0 | `\operatorname{Star}` |
| `\Sub` | 0 | `{\mathrm{Sub}}` |
| `\submfds` | 0 | `\operatorname{SubMfds}` |
| `\SU` | 0 | `{\operatorname{SU}}` |
| `\Sum` | 0 | `\sum` |
| `\supp` | 0 | `\operatorname{supp}` |
| `\Supp` | 0 | `{\operatorname{Supp}}` |
| `\Sw` | 0 | `{\mathrm{Sw}}` |
| `\syl` | 0 | `{\operatorname{Syl}}` |
| `\Syl` | 0 | `{\operatorname{Syl}}` |
| `\Sym` | 0 | `\operatorname{Sym}` |
| `\sym` | 0 | `\operatorname{Sym}^*` |
| `\Symalg` | 0 | `\sym` |
| `\symalg` | 0 | `\sym` |
| `\Symb` | 0 | `\operatorname{Symb}` |
| `\Symbil` | 0 | `\operatorname{SymBil}` |
| `\Symp` | 0 | `{\operatorname{Sp}}` |
| `\Tatesymbol` | 0 | `\operatorname{TateSymb}` |
| `\Taut` | 0 | `\operatorname{Taut}` |
| `\TC` | 0 | `{\operatorname{TC}}` |
| `\TCH` | 0 | `{\operatorname{TCH}}` |
| `\Th` | 0 | `\operatorname{Th}` |
| `\THC` | 0 | `{\operatorname{THC}}` |
| `\thinrank` | 0 | `T_n\dash\operatorname{rank}` |
| `\Todd` | 0 | `\operatorname{Td}` |
| `\tor` | 0 | `\operatorname{Tor}` |
| `\Tor` | 0 | `\operatorname{Tor}` |
| `\tors` | 0 | `{\operatorname{tors}}` |
| `\Tot` | 0 | `{ \operatorname{Tot} }` |
| `\TP` | 0 | `{\operatorname{TP}}` |
| `\tr` | 0 | `{\mathrm{tr}}` |
| `\Tr` | 0 | `\operatorname{Tr}` |
| `\trace` | 0 | `\operatorname{tr}` |
| `\Trace` | 0 | `\operatorname{Trace}` |
| `\trdeg` | 0 | `{\mathrm{trdeg}}` |
| `\transfer` | 0 | `\operatorname{transfer}` |
| `\triv` | 0 | `\operatorname{triv}` |
| `\Triv` | 0 | `\operatorname{Triv}` |
| `\tspt` | 0 | `{\{\operatorname{pt}\}}` |
| `\txand` | 0 | `{\operatorname{ and }}` |
| `\txor` | 0 | `{\operatorname{ or }}` |
| `\type` | 0 | `{\operatorname{type}}` |
| `\U` | 0 | `{\operatorname{U}}` |
| `\UFrame` | 0 | `\operatorname{UFrame}` |
| `\unital` | 0 | `{\operatorname{unital}}` |
| `\Union` | 0 | `\bigcup` |
| `\unram` | 0 | `{\scriptscriptstyle\mathrm{un}}` |
| `\USp` | 0 | `{\operatorname{USp}}` |
| `\val` | 0 | `{\operatorname{val}}` |
| `\Verts` | 0 | `{ \operatorname{Verts} }` |
| `\vol` | 0 | `\operatorname{vol}` |
| `\volume` | 0 | `\operatorname{Vol}` |
| `\Vor` | 0 | `\operatorname{Vor}` |
| `\WDiv` | 0 | `\operatorname{WDiv}` |
| `\WP` | 0 | `{\mathbf{WP}}` |
| `\Wedge` | 0 | `\bigwedge` |
| `\weight` | 0 | `{ \operatorname{weight} }` |
| `\Wittvectors` | 0 | `{\mathbb{W}}` |
| `\wt` | 0 | `{\operatorname{wt}}` |
| `\zbar` | 0 | `\bar{z}` |
| `\ZHB` | 0 | `\operatorname{ZHB}` |
| `\Ag` | 0 | `{\mathcal{A}_g}` |
| `\agbar` | 0 | `\bar{\Ag}` |
| `\Af` | 0 | `{\mathbf{A}}` |
| `\Ahat` | 0 | `\hat{ \operatorname{A}}_g` |
| `\B` | 0 | `{\mathbf{B}}` |
| `\bmgn` | 0 | `{ \bar{\mathcal{M}}_{g, n} }` |
| `\boxtensor` | 0 | `\boxtimes` |
| `\Cc` | 0 | `{\check{C}}` |
| `\cechH` | 0 | `{\check{H}}` |
| `\coind` | 0 | `\operatorname{coInd}` |
| `\D` | 0 | `{ \mathsf{D} }` |
| `\dtensor` | 0 | `\overset{\mathbb{L}}{ \otimes}` |
| `\dual` | 0 | `{}^{ \vee }` |
| `\dualnumbers` | 0 | `{ [\eps] / \eps^2 }` |
| `\E` | 0 | `{\mathbf{E}}` |
| `\Extprod` | 0 | `\bigwedge\nolimits` |
| `\Extpower` | 0 | `\bigwedge\nolimits` |
| `\fracId` | 0 | `{ \ddot{\Id} }` |
| `\G` | 0 | `{\mathsf{G}}` |
| `\Hc` | 0 | `{\check{H}}` |
| `\hocolim` | 0 | `\operatorname{hocolim}` |
| `\HZ` | 0 | `{H\ZZ}` |
| `\I` | 0 | `\mathrm{I}` |
| `\II` | 0 | `\mathrm{II}` |
| `\III` | 0 | `\mathrm{III}` |
| `\intcl` | 0 | `\operatorname{cl}^{\mathrm{int}}` |
| `\algcl` | 0 | `\operatorname{cl}^{\mathrm{alg}}` |
| `\sepcl` | 0 | `\operatorname{cl}^{\mathrm{sep}}` |
| `\iso` | 0 | `\isomorphic` |
| `\IV` | 0 | `\mathrm{IV}` |
| `\K` | 0 | `{\mathsf{K}}` |
| `\kbar` | 0 | `{ \overline{k} }` |
| `\kfq` | 0 | `K_{/\FF_q}` |
| `\KH` | 0 | `\K^{\scriptscriptstyle \mathrm{H}}` |
| `\KM` | 0 | `\K^{\scriptstyle\mathrm{M}}` |
| `\KMimp` | 0 | `\hat{\K}^{\scriptscriptstyle \mathrm{M}}` |
| `\KMW` | 0 | `\K^{\scriptscriptstyle \mathrm{MW}}` |
| `\ksep` | 0 | `{ k\sep }` |
| `\lderive` | 0 | `\leftderive` |
| `\leftderive` | 0 | `{\mathbf{L}}` |
| `\liealgk` | 0 | `{ \liealg_{/k} }` |
| `\lkt` | 0 | `{L_{\mathrm{K3}}}` |
| `\lktcc` | 0 | `{L_{\mathrm{K3}, \CC}}` |
| `\lkttd` | 0 | `{L_{\mathrm{K3}, 2d}}` |
| `\Ltensor` | 0 | `\overset{\mathbb{L}}{ \otimes}` |
| `\mbar` | 0 | `\bar{\mathcal{M}}` |
| `\Mg` | 0 | `{\mathcal{M}_g}` |
| `\mg` | 0 | `{ \mathcal{M}_{g} }` |
| `\Mgbar` | 0 | `\bar{\Mg}` |
| `\mgbar` | 0 | `\bar{\Mg}` |
| `\Mgn` | 0 | `{ \mathcal{M}_{g, n} }` |
| `\mgn` | 0 | `{ \mathcal{M}_{g, n} }` |
| `\Mell` | 0 | `{ \mathcal{M}_{\mathrm{ell}} }` |
| `\mH` | 0 | `{ \mathsf{H} }` |
| `\modiso` | 0 | `{_{\scriptstyle / \sim} }` |
| `\ms` | 0 | `\xrightarrow{\sim}` |
| `\mveq` | 0 | `{\mapsvia{\sim}}` |
| `\mviso` | 0 | `{\mapsvia{\sim}}` |
| `\nonzero` | 0 | `^{\bullet}` |
| `\OX` | 0 | `{\mathcal{O}_X}` |
| `\Presh` | 0 | `\presh` |
| `\Prod` | 0 | `\displaystyle\prod` |
| `\primetop` | 0 | `{\scriptscriptstyle \mathrm{prime-to-}p}` |
| `\ptd` | 0 | `{\scriptstyle { \ast } }` |
| `\qiso` | 0 | `\homotopic` |
| `\quillenplus` | 0 | `{ {}^{+} }` |
| `\rderive` | 0 | `\rightderive` |
| `\resprod` | 0 | `\prod^{\res}` |
| `\restensor` | 0 | `\bigotimes^{\res}` |
| `\rightderive` | 0 | `{\mathbf{R}}` |
| `\rrarrows` | 0 | `\rightrightarrows` |
| `\sdot` | 0 | `{ \mathsf{S}_{\cdot} }` |
| `\Sgn` | 0 | `{ \Sigma_{g, n} }` |
| `\shriek` | 0 | `{ ! }` |
| `\Spinc` | 0 | `\mathrm{Spin}^{{ \scriptscriptstyle \mathbf C} }` |
| `\T` | 0 | `{\mathbf{T}}` |
| `\Tensor` | 0 | `\bigotimes` |
| `\tensor` | 0 | `\otimes` |
| `\tgn` | 0 | `{ \mathcal{T}_{g, n} }` |
| `\tilt` | 0 | `{}^{ \flat }` |
| `\TM` | 0 | `{\T M}` |
| `\Totprod` | 0 | `\Tot^{\Pi}` |
| `\Totsum` | 0 | `\Tot^{\oplus}` |
| `\TX` | 0 | `{\T X}` |
| `\Ug` | 0 | `{\mathcal{U}(\mathfrak{g}) }` |
| `\Uh` | 0 | `{\mathcal{U}(\mathfrak{h}) }` |
| `\V` | 0 | `{\textrm{V}}` |
| `\VI` | 0 | `{\textrm{VI}}` |
| `\wdot` | 0 | `{ \mathsf{w}_{\cdot} }` |
| `\Wedgepower` | 0 | `\bigwedge\nolimits` |
| `\Xff` | 0 | `{X_\mathrm{FF}}` |
| `\xpn` | 0 | `{ x^{p^n} }` |
| `\ZHS` | 0 | `\ZZ\operatorname{HS}` |
| `\ZVHS` | 0 | `{ \ZZ\mathrm{VHS} }` |
| `\abuts` | 0 | `\Rightarrow` |
| `\actson` | 0 | `\curvearrowright` |
| `\actsonl` | 0 | `\curvearrowleft` |
| `\asymptotic` | 0 | `\ll` |
| `\capprod` | 0 | `\frown` |
| `\capp` | 0 | `\frown` |
| `\cocovers` | 0 | `\leftleftarrows` |
| `\containedin` | 0 | `\subseteq` |
| `\contains` | 0 | `\supseteq` |
| `\containing` | 0 | `\supseteq` |
| `\convolve` | 0 | `\ast` |
| `\coveredby` | 0 | `\leftleftarrows` |
| `\covers` | 0 | `\rightrightarrows` |
| `\covariant` | 0 | `\nabla` |
| `\cupprod` | 0 | `\smile` |
| `\cupp` | 0 | `\smile` |
| `\dash` | 0 | `{\hbox{-}}` |
| `\decreasesto` | 0 | `\searrow` |
| `\disjoint` | 0 | `{\amalg}` |
| `\Disjoint` | 0 | `\bigsqcup` |
| `\divergence` | 0 | `{ \nabla\cdot }` |
| `\divides` | 0 | `\mathrel{\|}` |
| `\dV` | 0 | `\,dV` |
| `\dalpha` | 0 | `\,d\alpha` |
| `\dA` | 0 | `\,dA` |
| `\dm` | 0 | `\,dm` |
| `\dmu` | 0 | `\,d\mu` |
| `\dn` | 0 | `\,dn` |
| `\dphi` | 0 | `\,d\phi` |
| `\dr` | 0 | `\,dr` |
| `\drho` | 0 | `\,d\rho` |
| `\ds` | 0 | `\displaystyle` |
| `\dt` | 0 | `\,dt` |
| `\dtau` | 0 | `\,d\tau` |
| `\dtheta` | 0 | `\,d\theta` |
| `\du` | 0 | `\,du` |
| `\dw` | 0 | `\,dw` |
| `\dx` | 0 | `\,dx` |
| `\dxi` | 0 | `\,d\xi` |
| `\dy` | 0 | `\,dy` |
| `\dz` | 0 | `\,dz` |
| `\dzbar` | 0 | `\,d\bar{z}` |
| `\dzeta` | 0 | `\,d\zeta` |
| `\embeds` | 0 | `\hookrightarrow` |
| `\embedsdense` | 0 | `{ \underset{ {\scriptscriptstyle\mathrm{dense}} }{\hookrightarrow} }` |
| `\eps` | 0 | `{\varepsilon}` |
| `\freeprod` | 0 | `\ast` |
| `\from` | 0 | `\leftarrow` |
| `\gon` | 0 | `{\dash\mathrm{gon}}` |
| `\gradient` | 0 | `\nabla` |
| `\hodgestar` | 0 | `\star` |
| `\homotopic` | 0 | `\simeq` |
| `\hq` | 0 | `{/}` |
| `\increasesto` | 0 | `\nearrow` |
| `\injects` | 0 | `\hookrightarrow` |
| `\injectivelim` | 0 | `\varinjlim` |
| `\injectsfrom` | 0 | `\hookleftarrow` |
| `\injresolve` | 0 | `\leftleftarrows` |
| `\interior` | 0 | `^\circ` |
| `\intersect` | 0 | `\cap` |
| `\into` | 0 | `\to` |
| `\inv` | 0 | `^{-1}` |
| `\inverselim` | 0 | `\varprojlim` |
| `\iscontainedin` | 0 | `\supseteq` |
| `\isomorphic` | 0 | `{ \, \mapsvia{\sim}\, }` |
| `\join` | 0 | `{ \ast }` |
| `\laplacian` | 0 | `\Delta` |
| `\Laplacian` | 0 | `\Delta` |
| `\mapbackforth` | 0 | `\operatorname*{\rightleftharpoons}` |
| `\mapstofrom` | 0 | `\rightleftharpoons` |
| `\modmod` | 0 | `\gitquot` |
| `\htyquot` | 0 | `\gitquot` |
| `\normal` | 0 | `{~\trianglelefteq~}` |
| `\normalizer` | 0 | `{ N }` |
| `\notimplies` | 0 | `\centernot\implies` |
| `\ofrom` | 0 | `\overset{\circ}{\leftarrow}` |
| `\onto` | 0 | `\twoheadhthtarrow` |
| `\oto` | 0 | `\overset{\circ}{\rightarrow}` |
| `\padic` | 0 | `p\dash\text{adic}` |
| `\plocal` | 0 | `{ \scriptsize {}_{ \localize{p} } }` |
| `\projectivelim` | 0 | `\varprojlim` |
| `\projresolve` | 0 | `\rightrightarrows` |
| `\proportional` | 0 | `\propto` |
| `\qed` | 0 | `\hfill\ensuremath{\blacksquare}` |
| `\rational` | 0 | `\torational` |
| `\rationalmap` | 0 | `\dashrightarrow` |
| `\semidirect` | 0 | `\rtimes` |
| `\st` | 0 | `{~\mathrel{\Big\vert}~}` |
| `\suchthat` | 0 | `\st` |
| `\surjects` | 0 | `\twoheadrightarrow` |
| `\too` | 0 | `\longrightarrow` |
| `\torational` | 0 | `\dashrightarrow` |
| `\transverse` | 0 | `\pitchfork` |
| `\uniformlyconverges` | 0 | `\rightrightarrows` |
| `\union` | 0 | `\cup` |
| `\unioninfty` | 0 | `{\union\ts{\infty}}` |
| `\units` | 0 | `^{\times}` |
| `\up` | 0 | `\uparrow` |
| `\wait` | 0 | `{-}` |
| `\wedgeprod` | 0 | `\vee` |
| `\wreath` | 0 | `\wr` |
| `\cB` | 0 | `{\mathcal{B}}` |
| `\cC` | 0 | `{\mathcal{C}}` |
| `\cD` | 0 | `{\mathcal{D}}` |
| `\cE` | 0 | `{\mathcal{E}}` |
| `\cH` | 0 | `{\mathcal{H}}` |
| `\cI` | 0 | `{\mathcal{I}}` |
| `\cJ` | 0 | `{\mathcal{J}}` |
| `\cK` | 0 | `{\mathcal{K}}` |
| `\cL` | 0 | `{\mathcal{L}}` |
| `\cN` | 0 | `{\mathcal{N}}` |
| `\cO` | 0 | `{\mathcal{O}}` |
| `\cP` | 0 | `{\mathcal{P}}` |
| `\cQ` | 0 | `{\mathcal{Q}}` |
| `\cR` | 0 | `{\mathcal{R}}` |
| `\cS` | 0 | `{\mathcal{S}}` |
| `\cT` | 0 | `{\mathcal{T}}` |
| `\cU` | 0 | `{\mathcal{U}}` |
| `\cV` | 0 | `{\mathcal{V}}` |
| `\cW` | 0 | `{\mathcal{W}}` |
| `\cY` | 0 | `{\mathcal{Y}}` |
| `\cZ` | 0 | `{\mathcal{Z}}` |
| `\bA` | 0 | `{\mathbb{A}}` |
| `\bB` | 0 | `{\mathbb{B}}` |
| `\bC` | 0 | `{\mathbb{C}}` |
| `\bD` | 0 | `{\mathbb{D}}` |
| `\bE` | 0 | `{\mathbb{E}}` |
| `\bF` | 0 | `{\mathbb{F}}` |
| `\bG` | 0 | `{\mathbb{G}}` |
| `\bH` | 0 | `{\mathbb{H}}` |
| `\bI` | 0 | `{\mathbb{I}}` |
| `\bJ` | 0 | `{\mathbb{J}}` |
| `\bK` | 0 | `{\mathbb{K}}` |
| `\bL` | 0 | `{\mathbb{L}}` |
| `\bM` | 0 | `{\mathbb{M}}` |
| `\bN` | 0 | `{\mathbb{N}}` |
| `\bO` | 0 | `{\mathbb{O}}` |
| `\bP` | 0 | `{\mathbb{P}}` |
| `\bQ` | 0 | `{\mathbb{Q}}` |
| `\bR` | 0 | `{\mathbb{R}}` |
| `\bS` | 0 | `{\mathbb{S}}` |
| `\bT` | 0 | `{\mathbb{T}}` |
| `\bU` | 0 | `{\mathbb{U}}` |
| `\bV` | 0 | `{\mathbb{V}}` |
| `\bW` | 0 | `{\mathbb{W}}` |
| `\bX` | 0 | `{\mathbb{X}}` |
| `\bY` | 0 | `{\mathbb{Y}}` |
| `\bZ` | 0 | `{\mathbb{Z}}` |
| `\fA` | 0 | `{\mathfrak{A}}` |
| `\fB` | 0 | `{\mathfrak{B}}` |
| `\fC` | 0 | `{\mathfrak{C}}` |
| `\fD` | 0 | `{\mathfrak{D}}` |
| `\fE` | 0 | `{\mathfrak{E}}` |
| `\fF` | 0 | `{\mathfrak{F}}` |
| `\fG` | 0 | `{\mathfrak{G}}` |
| `\fH` | 0 | `{\mathfrak{H}}` |
| `\fI` | 0 | `{\mathfrak{I}}` |
| `\fJ` | 0 | `{\mathfrak{J}}` |
| `\fK` | 0 | `{\mathfrak{K}}` |
| `\fL` | 0 | `{\mathfrak{L}}` |
| `\fM` | 0 | `{\mathfrak{M}}` |
| `\fN` | 0 | `{\mathfrak{N}}` |
| `\fO` | 0 | `{\mathfrak{O}}` |
| `\fP` | 0 | `{\mathfrak{P}}` |
| `\fQ` | 0 | `{\mathfrak{Q}}` |
| `\fR` | 0 | `{\mathfrak{R}}` |
| `\fS` | 0 | `{\mathfrak{S}}` |
| `\fT` | 0 | `{\mathfrak{T}}` |
| `\fU` | 0 | `{\mathfrak{U}}` |
| `\fV` | 0 | `{\mathfrak{V}}` |
| `\fW` | 0 | `{\mathfrak{W}}` |
| `\fX` | 0 | `{\mathfrak{X}}` |
| `\fY` | 0 | `{\mathfrak{Y}}` |
| `\fZ` | 0 | `{\mathfrak{Z}}` |
| `\hA` | 0 | `{\widehat{A}}` |
| `\hB` | 0 | `{\widehat{B}}` |
| `\hC` | 0 | `{\widehat{C}}` |
| `\hD` | 0 | `{\widehat{D}}` |
| `\hE` | 0 | `{\widehat{E}}` |
| `\hF` | 0 | `{\widehat{F}}` |
| `\hG` | 0 | `{\widehat{G}}` |
| `\hH` | 0 | `{\widehat{H}}` |
| `\hI` | 0 | `{\widehat{I}}` |
| `\hJ` | 0 | `{\widehat{J}}` |
| `\hK` | 0 | `{\widehat{K}}` |
| `\hL` | 0 | `{\widehat{L}}` |
| `\hM` | 0 | `{\widehat{M}}` |
| `\hN` | 0 | `{\widehat{N}}` |
| `\hO` | 0 | `{\widehat{O}}` |
| `\hP` | 0 | `{\widehat{P}}` |
| `\hQ` | 0 | `{\widehat{Q}}` |
| `\hR` | 0 | `{\widehat{R}}` |
| `\hS` | 0 | `{\widehat{S}}` |
| `\hT` | 0 | `{\widehat{T}}` |
| `\hU` | 0 | `{\widehat{U}}` |
| `\hV` | 0 | `{\widehat{V}}` |
| `\hW` | 0 | `{\widehat{W}}` |
| `\hX` | 0 | `{\widehat{X}}` |
| `\hY` | 0 | `{\widehat{Y}}` |
| `\hZ` | 0 | `{\widehat{Z}}` |
| `\wA` | 0 | `{\widetilde{A}}` |
| `\wB` | 0 | `{\widetilde{B}}` |
| `\wC` | 0 | `{\widetilde{C}}` |
| `\wD` | 0 | `{\widetilde{D}}` |
| `\wE` | 0 | `{\widetilde{E}}` |
| `\wF` | 0 | `{\widetilde{F}}` |
| `\wG` | 0 | `{\widetilde{G}}` |
| `\wH` | 0 | `{\widetilde{H}}` |
| `\wI` | 0 | `{\widetilde{I}}` |
| `\wJ` | 0 | `{\widetilde{J}}` |
| `\wK` | 0 | `{\widetilde{K}}` |
| `\wL` | 0 | `{\widetilde{L}}` |
| `\wM` | 0 | `{\widetilde{M}}` |
| `\wN` | 0 | `{\widetilde{N}}` |
| `\wO` | 0 | `{\widetilde{O}}` |
| `\wP` | 0 | `{\widetilde{P}}` |
| `\wQ` | 0 | `{\widetilde{Q}}` |
| `\wR` | 0 | `{\widetilde{R}}` |
| `\wS` | 0 | `{\widetilde{S}}` |
| `\wT` | 0 | `{\widetilde{T}}` |
| `\wU` | 0 | `{\widetilde{U}}` |
| `\wV` | 0 | `{\widetilde{V}}` |
| `\wW` | 0 | `{\widetilde{W}}` |
| `\wX` | 0 | `{\widetilde{X}}` |
| `\wY` | 0 | `{\widetilde{Y}}` |
| `\wZ` | 0 | `{\widetilde{Z}}` |
| `\oA` | 0 | `{\overline{A}}` |
| `\oB` | 0 | `{\overline{B}}` |
| `\oC` | 0 | `{\overline{C}}` |
| `\oD` | 0 | `{\overline{D}}` |
| `\oE` | 0 | `{\overline{E}}` |
| `\oF` | 0 | `{\overline{F}}` |
| `\oG` | 0 | `{\overline{G}}` |
| `\oH` | 0 | `{\overline{H}}` |
| `\oI` | 0 | `{\overline{I}}` |
| `\oJ` | 0 | `{\overline{J}}` |
| `\oK` | 0 | `{\overline{K}}` |
| `\oL` | 0 | `{\overline{L}}` |
| `\oM` | 0 | `{\overline{M}}` |
| `\oN` | 0 | `{\overline{N}}` |
| `\oO` | 0 | `{\overline{O}}` |
| `\oP` | 0 | `{\overline{P}}` |
| `\oQ` | 0 | `{\overline{Q}}` |
| `\oR` | 0 | `{\overline{R}}` |
| `\oS` | 0 | `{\overline{S}}` |
| `\oT` | 0 | `{\overline{T}}` |
| `\oU` | 0 | `{\overline{U}}` |
| `\oV` | 0 | `{\overline{V}}` |
| `\oW` | 0 | `{\overline{W}}` |
| `\oX` | 0 | `{\overline{X}}` |
| `\oY` | 0 | `{\overline{Y}}` |
| `\oZ` | 0 | `{\overline{Z}}` |
| `\uA` | 0 | `{\underline{A}}` |
| `\uB` | 0 | `{\underline{B}}` |
| `\uC` | 0 | `{\underline{C}}` |
| `\uD` | 0 | `{\underline{D}}` |
| `\uE` | 0 | `{\underline{E}}` |
| `\uF` | 0 | `{\underline{F}}` |
| `\uG` | 0 | `{\underline{G}}` |
| `\uH` | 0 | `{\underline{H}}` |
| `\uI` | 0 | `{\underline{I}}` |
| `\uJ` | 0 | `{\underline{J}}` |
| `\uK` | 0 | `{\underline{K}}` |
| `\uL` | 0 | `{\underline{L}}` |
| `\uM` | 0 | `{\underline{M}}` |
| `\uN` | 0 | `{\underline{N}}` |
| `\uO` | 0 | `{\underline{O}}` |
| `\uP` | 0 | `{\underline{P}}` |
| `\uQ` | 0 | `{\underline{Q}}` |
| `\uR` | 0 | `{\underline{R}}` |
| `\uS` | 0 | `{\underline{S}}` |
| `\uT` | 0 | `{\underline{T}}` |
| `\uU` | 0 | `{\underline{U}}` |
| `\uV` | 0 | `{\underline{V}}` |
| `\uW` | 0 | `{\underline{W}}` |
| `\uX` | 0 | `{\underline{X}}` |
| `\uY` | 0 | `{\underline{Y}}` |
| `\uZ` | 0 | `{\underline{Z}}` |
| `\Co` | 0 | `{\mathrm{Co}}` |
| `\Nik` | 0 | `{\mathrm{Nik}}` |
| `\Nod` | 0 | `{\mathrm{Nod}}` |
| `\latI` | 0 | `\mathrm{I}` |
| `\latII` | 0 | `\mathrm{II}` |
| `\lEn` | 0 | `L_{\mathrm{En}}` |
| `\lEnII` | 0 | `{\mathrm{II}}_{1, 9}` |
| `\lias` | 0 | `L_{\mathrm{IAS}}` |
| `\liasplus` | 0 | `\lias^+` |
| `\liasminus` | 0 | `\lias^-` |
| `\rhok` | 0 | `\rho_{\mathrm{K3}}` |
| `\rhoias` | 0 | `\rho_{\mathrm{IAS}}` |
| `\uslc` | 0 | `^{\mathrm{KSBA}}` |
| `\utor` | 0 | `^{\mathrm{tor}}` |
| `\di` | 0 | `\operatorname{div}` |
| `\dnor` | 0 | `_{\mathrm{nor}}` |
| `\fco` | 0 | `F_{\Co}` |
| `\fell` | 0 | `F_{ \mathrm{ell} }` |
| `\fen` | 0 | `F_{\En}` |
| `\fent` | 0 | `F_{\En, 2}` |
| `\fentwo` | 0 | `F_{\En,2}` |
| `\ftd` | 0 | `F_{2d}` |
| `\fken` | 0 | `F_{(2,2,0)}` |
| `\fttz` | 0 | `F_{(2,2,0)}` |
| `\ofco` | 0 | `\overline{F}_{\Co}` |
| `\ofen` | 0 | `\overline{F}_{\En}` |
| `\ofentwo` | 0 | `\overline{F}_{\En,2}` |
| `\ofken` | 0 | `\overline{F}_{(2,2,0)}` |
| `\ten` | 0 | `T_{\En}` |
| `\tdp` | 0 | `T_{\dP}` |
| `\sdp` | 0 | `S_{\dP}` |
| `\sen` | 0 | `S_{\En}` |
| `\gdp` | 0 | `{\Gamma_{\dP}}` |
| `\gent` | 0 | `{\Gamma_{\En, 2}}` |
| `\gell` | 0 | `\Gamma^{ \mathrm{ell} }` |
| `\tell` | 0 | `T_{ \mathrm{ell} }` |
| `\idp` | 0 | `\iota_{\dP}` |
| `\ien` | 0 | `\iota_{\En}` |
| `\Idp` | 0 | `I_{\dP}` |
| `\Ien` | 0 | `I_{\En}` |
| `\inik` | 0 | `\iota_{ \Nik }` |
| `\Inik` | 0 | `I_{ \Nik }` |
| `\ienzero` | 0 | `\iota_{\En, 0}` |
| `\gref` | 0 | `\Gamma\dref` |
| `\dref` | 0 | `_{\rm r}` |
| `\OrthObs` | 0 | `\Orth_*` |
| `\ADE` | 0 | `\mathrm{ADE}` |
| `\ADEBC` | 0 | `\mathrm{ADE}+\mathrm{BC}` |
| `\tADE` | 0 | `\widetilde{ \ADE }` |
| `\Bir` | 0 | `\operatorname{Bir}` |
| `\Conv` | 0 | `\operatorname{Conv}` |
| `\Exc` | 0 | `\operatorname{Exc}` |
| `\GCD` | 0 | `\operatorname{GCD}` |
| `\M` | 0 | `\operatorname{M}` |
| `\Projm` | 0 | `\operatorname{Projm}` |
| `\Specm` | 0 | `\operatorname{Specm}` |
| `\Ver` | 0 | `\operatorname{Ver}` |
| `\Vol` | 0 | `\operatorname{Vol}` |
| `\isoto` | 0 | `\xrightarrow{\sim}` |
| `\acts` | 0 | `\curvearrowright` |
| `\wh` | 0 | `\widehat` |
| `\la` | 0 | `\langle` |
| `\ra` | 0 | `\rangle` |
| `\lrc` | 0 | `\lrcorner` |
| `\llc` | 0 | `\llcorner` |
| `\urc` | 0 | `\urcorner` |
| `\ulc` | 0 | `\ulcorner` |
| `\uopp` | 0 | `^{\rm opp}` |
| `\ubb` | 0 | `^{\rm BB}` |
| `\dto` | 0 | `\Rightarrow` |
| `\fign` | 0 | `Fig.~\ref{fig:discforms}` |
| `\fignb` | 0 | `Fig.~\ref{fig:discforms}` |
| `\hoV` | 0 | `\widehat{\overline V}` |
| `\hoD` | 0 | `\widehat{\overline D}` |
| `\ooT` | 0 | `\overline{\overline T}` |
| `\ias` | 0 | `\operatorname{IAS}^2` |
| `\lge` | 0 | `_{\ge0}` |
| `\ocC` | 0 | `\overline{\cC}` |
| `\lred` | 0 | `_{\rm red}` |
| `\mr` | 0 | `\bar r` |
| `\ma` | 0 | `\bar a` |
| `\mdelta` | 0 | `\bar \delta` |
| `\mk` | 0 | `\bar k` |
| `\me` | 0 | `\hat e` |
| `\miota` | 0 | `\hat \iota` |
| `\hiota` | 0 | `\hat \iota` |
| `\oPic` | 0 | `\overline{\Pic}` |
| `\ucox` | 0 | `^{\rm cox}` |
| `\lir` | 0 | `_{\rm ir}` |
| `\usat` | 0 | `^{\rm sat}` |
| `\Cur` | 0 | `\operatorname{Cur}` |
| `\ohV` | 0 | `\overline{\hV}` |
| `\dgen` | 0 | `_{\rm gen}` |
| `\dmon` | 0 | `_{\rm mon}` |
| `\dias` | 0 | `_{\rm IAS}` |
| `\dram` | 0 | `_{\rm ram}` |
| `\drel` | 0 | `_{\rm rel}` |
| `\dirr` | 0 | `_{\rm irr}` |
| `\vrel` | 0 | `V\drel` |
| `\virr` | 0 | `V\dirr` |
| `\wref` | 0 | `W\dref` |
| `\chref` | 0 | `\ch\dref` |
| `\fref` | 0 | `\fF\dref` |
| `\fram` | 0 | `\fF\dram` |
| `\relpart` | 0 | `\operatorname{rel}` |
| `\irrpart` | 0 | `\operatorname{irr}` |
| `\fcref` | 0 | `\fC\dref` |
| `\fgen` | 0 | `\fF_{\rm gen}` |
| `\fsfref` | 0 | `\fF_S^{\fref}` |
| `\ofsfref` | 0 | `\oF_S^{\fref}` |
| `\upar` | 0 | `^{\rm par}` |
| `\dleft` | 0 | `{}_{\rm left}` |
| `\dright` | 0 | `{}_{\rm right}` |
| `\evn` | 0 | `\text{even }n` |
| `\odn` | 0 | `\text{odd }n` |
| `\BB` | 0 | `\operatorname{BB}` |
| `\ConvOp` | 0 | `\operatorname{Conv}` |
| `\perfOp` | 0 | `\operatorname{perf}` |
| `\GIT` | 0 | `\operatorname{GIT}` |
| `\isoGr` | 0 | `\operatorname{IsoGr}` |
| `\FG` | 0 | `F_\Gamma` |
| `\IA` | 0 | `\mathrm{IA}` |
| `\IAD` | 0 | `\mathrm{IAD}` |
| `\IARP` | 0 | `\mathrm{IARP}` |
| `\OStab` | 0 | `\Orth^*` |
| `\ZZtwoadic` | 0 | `\ZZ_{\hat 2}` |
| `\cox` | 0 | `\Cox` |
| `\genop` | 0 | `\mathrm{gen}` |
| `\irrelevant` | 0 | `\mathrm{irr}` |
| `\relevant` | 0 | `\mathrm{rel}` |
| `\rcop` | 0 | `\mathrm{rc}` |
| `\opop` | 0 | `\mathrm{op}` |
| `\opp` | 0 | `^{\mathrm{op}}` |
| `\liek` | 0 | `\mathfrak{k}` |
| `\liev` | 0 | `\mathfrak{v}` |
| `\tiling` | 0 | `\mathcal{T}` |
| `\weylgroup` | 0 | `\mathcal{W}` |
| `\mcH` | 0 | `\mathcal{H}` |
| `\diverge` | 0 | `\uparrow` |
| `\uksba` | 0 | `^{\mathrm{KSBA}}` |
| `\uktriv` | 0 | `^{K\text{-}\mathrm{triv}}` |
| `\textand` | 0 | `\text{ and }` |
| `\textelse` | 0 | `\text{ otherwise }` |
| `\textfor` | 0 | `\text{ for }` |
| `\textif` | 0 | `\text{ if }` |
| `\textor` | 0 | `\text{ or }` |
| `\where` | 0 | `\text{ where }` |
| `\Poincare` | 0 | `Poincar\'e` |
| `\Bbb` | 0 | `\mathbb` |
| `\HalphenInvariants` | 0 | `(10, 10, 1)` |
| `\EnriquesInvariants` | 0 | `(10, 10, 0)` |

### `styles/macros/tier2-mathjax-args.tex`

| Macro | Args | Expansion |
| --- | --- | --- |
| `\abs` | 1 | `{\left\lvert {#1} \right\rvert}` |
| `\norm` | 1 | `{\left\lVert {#1} \right\rVert}` |
| `\normm` | 1 | `{\left\lVert \left\lVert {#1} \right\rVert\right\rVert}` |
| `\pnorm` | 2 | `{\left\lVert {#1} \right\rVert}_{#2}` |
| `\matt` | 4 | `{ \begin{bmatrix} {#1} & {#2} \\ {#3} & {#4} \end{bmatrix} }` |
| `\adjoin` | 1 | `{ \left[ \scriptstyle {#1} \right] }` |
| `\polynomialring` | 1 | `{ \left[ {#1} \right] }` |
| `\bracket` | 1 | `\left\langle #1 \right\rangle` |
| `\gens` | 1 | `\left\langle{#1}\right\rangle` |
| `\generators` | 1 | `\left\langle{#1}\right\rangle` |
| `\sqgens` | 1 | `\left[ {#1} \right]` |
| `\freeon` | 1 | `\left[ {#1} \right]` |
| `\dgens` | 1 | `\gens{\gens{ #1 }}` |
| `\ceiling` | 1 | `{\left\lceil #1 \right\rceil}` |
| `\floor` | 1 | `{\left\lfloor #1 \right\rfloor}` |
| `\bicomplex` | 1 | `{ {#1}_{\scriptscriptstyle \bullet, \bullet}}` |
| `\cobicomplex` | 1 | `{ {#1}^{\scriptscriptstyle \bullet, \bullet}}` |
| `\cocomplex` | 1 | `{ {#1}^{\scriptscriptstyle \bullet}}` |
| `\complex` | 1 | `{ {#1}_{\scriptscriptstyle \bullet}}` |
| `\decfiltration` | 1 | `{#1}_{\bullet}` |
| `\incfiltration` | 1 | `{#1}^{\bullet}` |
| `\conj` | 1 | `{\overline{{#1}}}` |
| `\ctz` | 1 | `\, {{\converges{{#1} \to\infty}\longrightarrow 0}} \,` |
| `\fps` | 1 | `{\llbracket #1 \rrbracket }` |
| `\formalpowerseries` | 1 | `\fps{#1}` |
| `\formalseries` | 1 | `\fps{#1}` |
| `\functionfield` | 1 | `{ \left( {#1} \right) }` |
| `\powerseries` | 1 | `\fps{#1}` |
| `\rff` | 1 | `\functionfield{#1}` |
| `\htyclass` | 1 | `{ \left[ {#1} \right] }` |
| `\ideal` | 1 | `\mathcal{#1}` |
| `\inner` | 2 | `{\left\langle {#1},~{#2} \right\rangle}` |
| `\inp` | 2 | `{\left\langle {#1},~{#2} \right\rangle}` |
| `\invert` | 1 | `{ \left[ { \scriptstyle \frac{1}{#1} } \right] }` |
| `\localize` | 1 | `\left[ { \scriptstyle { {#1}\inv} } \right]` |
| `\plocalize` | 1 | `\primelocalize{#1}` |
| `\primelocalize` | 1 | `\left[ { \scriptstyle { { ({#1}^c) }\inv} } \right]` |
| `\fls` | 1 | `(\hspace{-0.25em}( #1 )\hspace{-0.22em})` |
| `\laurent` | 1 | `\fls{#1}` |
| `\laurentseries` | 1 | `\fls{#1}` |
| `\embedsvia` | 1 | `\xhookrightarrow{#1}` |
| `\fromvia` | 1 | `\xleftarrow{#1}` |
| `\open` | 1 | `\overset{\circ}{#1}` |
| `\poisbrack` | 2 | `{\left\{ {#1},~{#2} \right\} }` |
| `\dcoset` | 3 | `{#1}\mkern-3mu\diagdown\mkern-3mu{}^{#2}\mkern-3mu\diagup\mkern-3mu{#3}` |
| `\dcosetl` | 2 | `{#1}\mkern-3mu\diagdown\mkern-3mu{}^{#2}` |
| `\dcosetr` | 2 | `{#1}\mkern-3mu\diagup\mkern-3mu{#2}` |
| `\leftquotient` | 2 | `{#1}\mkern-3mu\diagdown\mkern-3mu{}^{#2}` |
| `\jacobsonrad` | 1 | `{J ({#1}) }` |
| `\nilrad` | 1 | `{\sqrt{0_{#1}} }` |
| `\Restriction` | 2 | `\mathrm{Res}^{#1}_{#2}` |
| `\coRestriction` | 2 | `\mathrm{coRes}^{#1}_{#2}` |
| `\Induction` | 2 | `\mathrm{Ind}^{#1}_{#2}` |
| `\coInduction` | 2 | `\mathrm{coInd}^{#1}_{#2}` |
| `\sheafify` | 1 | `\left( #1 \right)^{\scriptscriptstyle \mathrm{sh}}` |
| `\complete` | 1 | `{ {}_{ \hat{#1} } }` |
| `\takecompletion` | 1 | `{ \overbrace{#1}^{\widehat{\hspace{4em}}} }` |
| `\pcomplete` | 0 | `{ {}^{ \wedge }_{p} }` |
| `\procomplete` | 0 | `{}^{ \wedge_{\scriptscriptstyle \pro }}` |
| `\kv` | 0 | `{ k_{\hat{v}} }` |
| `\Lv` | 0 | `{ L_{\hat{v}} }` |
| `\coslice` | 1 | `_{{#1/}}` |
| `\liesabove` | 1 | `{ {}_{/ {#1}} }` |
| `\liesover` | 1 | `{ {}_{/ {#1}} }` |
| `\slice` | 1 | `_{/ {#1}}` |
| `\symb` | 2 | `{ \qty{ #1 \over #2 } }` |
| `\tl` | 2 | `{ #1_1, \cdots, #1_{#2} }` |
| `\tlset` | 2 | `\ts{ {#1}_{1}, \cdots, {#1}_{#2} }` |
| `\tlz` | 2 | `{ #1_0, \cdots, #1_{#2} }` |
| `\tsl` | 3 | `\ts{ {#1}_{#2}, \cdots, {#1}_{#3} }` |
| `\fourier` | 1 | `\widehat{#1}` |
| `\cartpower` | 1 | `{ {}^{ \scriptscriptstyle\times^{#1} } }` |
| `\disjointpower` | 2 | `{#1}^{\scriptscriptstyle\coprod^{#2}}` |
| `\derivedtensorpower` | 3 | `{ {}^{ \scriptstyle {}_{#1} {\otimes_{#2}^{#3}} } }` |
| `\fiberpower` | 3 | `{#1}^{\scriptscriptstyle\fiberproduct{#2}^{#3}}` |
| `\powers` | 1 | `{ {}^{\cdot #1} }` |
| `\prodpower` | 2 | `{#1}^{\scriptscriptstyle\times^{#2}}` |
| `\skel` | 1 | `{ {}^{ (#1) } }` |
| `\smashpower` | 2 | `{#1}^{\scriptscriptstyle\smashprod^{#2}}` |
| `\sumpower` | 1 | `{ {}^{ \oplus{#1} } }` |
| `\tensorpower` | 2 | `{ {}^{ \scriptstyle\otimes_{#1}^{#2} } }` |
| `\tensorpowerk` | 2 | `{#1}^{\scriptscriptstyle\otimes_{k}^{#2}}` |
| `\transp` | 1 | `{ \, {}^{t}{ \left( #1 \right) } }` |
| `\wedgepower` | 2 | `{#1}^{\scriptscriptstyle\smashprod^{#2}}` |
| `\twistleft` | 2 | `{ {}^{#1} #2 }` |
| `\twistright` | 2 | `{ #2 {}^{#1} }` |
| `\Globsec` | 1 | `{\Gamma\qty{#1} }` |
| `\globsec` | 1 | `{\Gamma\qty{#1} }` |
| `\addbase` | 1 | `{ {}_{pt} }` |
| `\catspan` | 3 | `\roof{#1}{#2}{#3}` |
| `\cptf` | 1 | `\overline{ #1 }` |
| `\cpt` | 1 | `\overline{#1}` |
| `\normalize` | 1 | `{#1}^{\nu}` |
| `\ksbacpt` | 1 | `\cpt{#1}^{\operatorname{KSBA}}` |
| `\normksbacpt` | 1 | `\normalize{ \cpt{#1} }` |
| `\bbcpt` | 1 | `\cpt{#1}^{ \operatorname{BB} }` |
| `\gitcpt` | 1 | `\cpt{#1}^{ \operatorname{GIT} }` |
| `\semifan` | 1 | `\mathcal{#1}` |
| `\semifans` | 1 | `\semifan{#1}_{\bullet}` |
| `\semitorfan` | 0 | `\semifans{F}` |
| `\semitorcpt` | 1 | `\cpt{#1}^{\semitorfan}` |
| `\semifancpt` | 2 | `\cpt{#1}^{#2}` |
| `\torfan` | 0 | `\Sigma` |
| `\torfans` | 0 | `\torfan_{\bullet}` |
| `\torcpt` | 1 | `\semifancpt{#1}{ \torfans }` |
| `\coxfan` | 0 | `\torfan^{\operatorname{Cox}}` |
| `\coxfans` | 0 | `\torfans^{\operatorname{Cox}}` |
| `\coxcpt` | 1 | `\semifancpt{#1}{\coxfans}` |
| `\BBfan` | 0 | `\Sigma^{\operatorname{BB}}` |
| `\halfpd` | 1 | `D_{#1}` |
| `\fullpd` | 1 | `\Omega_{#1}` |
| `\dmodgamma` | 2 | `{#1}/{#2}` |
| `\discgroup` | 1 | `A_{#1}` |
| `\diverges` | 0 | `\mapstofrom` |
| `\langL` | 1 | `{}^{L}{#1}` |
| `\modulo` | 0 | `{ \bigg/ }` |
| `\openimmerse` | 0 | `\underset{\scriptscriptstyle O}{\hookrightarrow}` |
| `\qtext` | 1 | `{\quad \operatorname{#1} \quad}` |
| `\roof` | 3 | `#1 {\, \scriptstyle {}^\swarrow\, } #2 {\, \scriptstyle {}^\searrow\,} #3` |
| `\shift` | 2 | `{ \Sigma^{\scriptstyle[#2]} #1 }` |
| `\squares` | 1 | `{ {#1}_{\scriptscriptstyle \square} }` |
| `\weakeq` | 0 | `\underset{\scriptscriptstyle W}{\rightarrow}` |
| `\congas` | 1 | `\underset{#1}{\cong}` |
| `\congbecause` | 1 | `\overset{#1}{\cong}` |
| `\equalsbecause` | 1 | `\overset{#1}{=}` |
| `\isoas` | 1 | `\underset{#1}{\cong}` |
| `\pwiso` | 0 | `\underset{\mathrm{pw}}{\cong}` |
| `\lshriek` | 0 | `{}_{!}` |
| `\pushf` | 0 | `{}^{*}` |
| `\cofinal` | 0 | `\mathsf{\emptyset}` |
| `\final` | 0 | `\ts{\pt}` |
| `\freezmod` | 1 | `\ZZ\left[ {#1} \right]` |
| `\conjugate` | 1 | `{\overline{{#1}}}` |
| `\closure` | 1 | `\overline{#1}` |
| `\ol` | 1 | `\overline{#1}` |
| `\univcover` | 1 | `\overline{#1}` |
| `\bar` | 1 | `\overline{#1}` |
| `\hat` | 1 | `\widehat{#1}` |
| `\bundle` | 1 | `\mathcal{#1}` |
| `\vector` | 1 | `\mathbf{#1}` |
| `\vhat` | 1 | `\widehat{ \vector{#1} }` |
| `\diagonal` | 1 | `\Delta` |
| `\Diagonal` | 1 | `\Delta` |
| `\correspond` | 1 | `\theset{\substack{#1}}` |
| `\converges` | 1 | `\overset{#1}` |
| `\convergesto` | 1 | `\overset{#1}\too` |
| `\ddd` | 2 | `{\frac{d #1}{d #2}\,}` |
| `\dd` | 2 | `{\frac{\partial #1}{\partial #2}\,}` |
| `\evalfrom` | 0 | `\Big\|` |
| `\restrictionof` | 2 | `{\left.{{#1}} \right\|_{{#2}} }` |
| `\ro` | 2 | `{ \left.{{#1}} \right\|_{{#2}} }` |
| `\ip` | 2 | `{\left\langle {#1},~{#2} \right\rangle}` |
| `\ddt` | 0 | `\tfrac{\dif}{\dif t}` |
| `\ddx` | 0 | `\tfrac{\dif}{\dif x}` |
| `\logd` | 0 | `{ \del^{\scriptsize \log} }` |
| `\theset` | 1 | `\left\{{#1}\right\}` |
| `\thevector` | 1 | `{\left[ {#1} \right]}` |
| `\ts` | 1 | `\left\{{#1}\right\}` |
| `\tv` | 1 | `{\left[ {#1} \right]}` |
| `\mltext` | 1 | `\left\{\begin{array}{c}#1\end{array}\right\}` |
| `\Suchthat` | 0 | `\middle\vert` |
| `\multinomial` | 1 | `\left(\!\!{#1}\!\!\right)` |
| `\realpart` | 1 | `{\mathcal{Re}({#1})}` |
| `\sheaf` | 1 | `\operatorname{\mathcal{#1}}` |
| `\smpt` | 1 | `\setminus\theset{#1}` |
| `\smts` | 1 | `\setminus\theset{ #1 }` |
| `\stirlingfirst` | 2 | `\genfrac{[}{]}{0pt}{}{#1}{#2}` |
| `\stirling` | 2 | `\genfrac\{\}{0pt}{}{#1}{#2}` |
| `\thecat` | 1 | `\mathbf{#1}` |
| `\constantsheaf` | 1 | `\underline{#1}` |
| `\ul` | 1 | `\underline{#1}` |
| `\vecc` | 2 | `\textcolor{#1}{\textbf{#2}}` |
| `\places` | 1 | `\mathrm{Pl}\qty{#1}` |
| `\ZZlocal` | 1 | `{ \ZZ_{\hat{#1}} }` |
| `\rad` | 1 | `\sqrt{#1}` |
| `\elts` | 2 | `{ {#1}_1, {#1}_2, \cdots, {#1}_{#2}}` |
| `\tselts` | 2 | `{ \theset{ {#1}_1, {#1}_2, \cdots, {#1}_{#2} } }` |
| `\mix` | 1 | `\overset{\scriptscriptstyle {#1} }{\times}` |
| `\fiberproduct` | 1 | `\underset{\scriptscriptstyle {#1} }{\times}` |
| `\fiberprod` | 3 | `{#1} \fiberproduct{#2} {#3}` |
| `\basechange` | 1 | `{ \fiberproduct{k} {#1} }` |
| `\fprod` | 3 | `\fiberprod{#1}{#2}{#3}` |
| `\qsymb` | 2 | `{ \left( {#1} \over {#2} \right) }` |
| `\kx` | 1 | `k[x_1, \cdots, x_{#1}]` |
| `\lktt` | 1 | `{L_{\mathrm{K3}, #1}}` |
| `\fractional` | 1 | `\theset{#1}` |
| `\fractionalpart` | 1 | `\theset{#1}` |
| `\integerpart` | 1 | `\left[ {#1}\right]` |
| `\zadjoin` | 1 | `\ZZ\left[ {#1} \right]` |
| `\mapscorrespond` | 2 | `\mathrel{\operatorname*{\rightleftharpoons}_{#2}^{#1}}` |
| `\mapsvia` | 1 | `\xrightarrow{#1}` |
| `\mapsfromvia` | 1 | `\xleftarrow{#1}` |
| `\mapstovia` | 1 | `\xmapsto{#1}` |
| `\tovia` | 1 | `\xrightarrow{#1}` |
| `\birational` | 0 | `\overset{\sim}{\torational}` |
| `\birationaliso` | 0 | `\overset{\sim}{\torational}` |
| `\sbirational` | 0 | `\overset{\sim_{ \stab} }{\torational}` |
| `\isovia` | 1 | `\underset{#1}{\iso}` |
| `\isoin` | 1 | `\overset{#1}{\iso}` |
| `\injectsvia` | 1 | `\xhookrightarrow{#1}` |
| `\injectsfromvia` | 1 | `\xhookleftarrow{#1}` |
| `\relspec` | 0 | `\ul{ \operatorname{Spec}}` |
| `\nerve` | 1 | `{ \mathcal{N}({#1}) }` |
| `\realize` | 1 | `{ \abs{#1} }` |
| `\opcat` | 1 | `{ {#1}\op }` |
| `\glue` | 1 | `{ \Disjoint_{#1} }` |
| `\normcomplex` | 1 | `{\norm{\complex{#1}}}` |
| `\Extalgebra` | 0 | `\cocomplex{\bigwedge}` |
| `\Extalg` | 0 | `\Extalgebra` |
| `\Extcomplex` | 0 | `\cocomplex{ \Extalgebra}` |
| `\drcomplex` | 0 | `{\cocomplex{\Omega}}` |
| `\cxH` | 0 | `{\complex{H}}` |
| `\ccxH` | 0 | `{\cocomplex{H}}` |
| `\sheafhom` | 0 | `\mathop{\mathcal{H}\! \mathit{om}}` |
| `\smallprod` | 0 | `{ \scriptscriptstyle\prod }` |
| `\eqLH` | 0 | `{ \equalsbecause{\scriptscriptstyle\text{LH}} }` |
| `\eqae` | 0 | `\underset{\ae}{=}` |
| `\eq` | 0 | `\operatorname*{=}` |
| `\RM` | 1 | `\textup{\uppercase\expandafter{\romannumeral#1}}%` |
| `\caniso` | 0 | `{ \underset{\can}{\iso} }` |
| `\dif` | 0 | `\mathop{}\!\operatorname{d}` |
| `\rotate` | 2 | `{\style{display: inline-block; transform: rotate(#1deg)}{#2}}` |
| `\rrrarrows` | 0 | `\mathrel{\substack{\textstyle\rightarrow\\[-0.6ex] \textstyle\rightarrow \\[-0.6ex] \textstyle\rightarrow}}` |
| `\righttriplearrows` | 0 | `\operatorname{{\; \tikz{ \foreach \y in {0, 0.1, 0.2} { \draw [-stealth] (0, \y) -- +(0.5, 0);}} \; }}` |
| `\bdlattice` | 2 | `\overline{#1}_{ #2 }` |
| `\orthcomp` | 2 | `#1^{\perp #2}` |
| `\thecone` | 1 | `\mathfrak{#1}` |
| `\theposet` | 1 | `\mathcal{#1}` |
| `\modulistack` | 1 | `\mathcal{#1}` |
| `\RN` | 1 | `\textup{\uppercase\expandafter{\romannumeral#1}}` |
| `\torcptf` | 2 | `\overline{#1}^{#2}` |

### `styles/macros/tier3-tex-complex.tex`

| Macro | Args | Expansion |
| --- | --- | --- |
| `\dqty` | 1 | `\left( \left( {#1} \right) \right)` |
| `\fourcase` | 4 | `\begin{cases}{#1} & {#2} \\ {#3} & {#4}\end{cases}` |
| `\cvec` | 2 | `{ \begin{bmatrix} {#1} \\ {#2} \end{bmatrix} }` |
| `\mattt` | 9 | `{ \begin{bmatrix} {#1} & {#2} & {#3} \\ {#4} & {#5} & {#6} \\ {#7} & {#8} & {#9} \end{bmatrix} }` |
| `\stack` | 1 | `\mathclap{\substack{ #1 }}` |
| `\stacksymbol` | 3 | `\mathrel{\stackunder[2pt]{\stackon[4pt]{$#3$}{$\scriptscriptstyle#1$}}{ $\scriptscriptstyle#2$}}` |
| `\textoperatorname` | 1 | `\operatorname{\textnormal{#1}}` |
| `\trianglerightneq` | 0 | `\mathrel{\ooalign{\raisebox{-0.5ex}{\reflectbox{\rotatebox{90}{$\nshortmid$}}}\cr$\triangleright$\cr}\mkern-3mu}` |
| `\normalneq` | 0 | `\mathrel{\reflectbox{$\trianglerightneq$}}` |
| `\dirac` | 0 | `\mkern-3mu \not{ \partial}` |
| `\stardstar` | 0 | `\hodgestar \mathrm{d} \mkern-1mu \hodgestar` |
| `\HHom` | 0 | `\mathscr{H}\kern-2pt\operatorname{om}` |
| `\shom` | 0 | `{\mathcal{H}}\kern-0.5pt{\operatorname{om}}` |
| `\QHS` | 0 | `\mathbf{Q}\kern-0.5pt\operatorname{HS}` |
| `\BGL` | 0 | `\mathbf{B}\mkern-3mu \operatorname{GL}` |
| `\gitquot` | 0 | `{ \mathbin{/\mkern-6mu/}}` |
| `\quotleft` | 2 | `{}_{#2}\mkern-.5mu\backslash\mkern-2mu^{#1}` |
| `\quotright` | 2 | `{}^{#1}\mkern-2mu/\mkern-2mu_{#2}` |
| `\dcoset` | 3 | `\,\scriptscriptstyle {\textstyle #1} \mkern-4mu\scalebox{1.5}{$\diagdown$}\mkern-5mu^{\textstyle #2} \mkern-4mu\scalebox{1.5}{$\diagup$}\mkern-5mu{\textstyle #3}` |
| `\dcosetl` | 2 | `\scriptscriptstyle {\textstyle #1} \mkern-4mu\scalebox{1.5}{$\diagdown$}\mkern-5mu^{\textstyle #2}` |
| `\dcosetr` | 2 | `\scriptscriptstyle {\textstyle #1} \mkern-4mu\scalebox{1.5}{$\diagup$}\mkern-5mu{\textstyle #2}` |
| `\leftquotient` | 2 | `{\textstyle #1} \mkern-4mu\scalebox{1.5}{$\diagdown$}\mkern-5mu^{\textstyle #2}` |
| `\aug` | 0 | `\fboxsep=-\fboxrule\!\!\!\fbox{\strut}\!\!\!` |
| `\bigast` | 0 | `{\mathop{\text{\Large $\ast$}}}` |
| `\connectsum` | 0 | `\mathop{ \Large\mypound }` |
| `\horzbar` | 0 | `\rule[.5ex]{2.5ex}{0.5pt}` |
| `\vertbar` | 0 | `\rule[-1ex]{0.5pt}{2.5ex}` |
| `\mypound` | 0 | `\scalebox{0.8}{\raisebox{0.4ex}{\#}}` |
| `\p` | 0 | `\prime` |
| `\pp` | 0 | `{\prime\prime}` |
| `\ph` | 0 | `\protect\kern -2pt\protect\phantom{.}` |
| `\ke` | 0 | `\protect\kern -2pt` |
| `\kee` | 0 | `\protect\kern -3pt` |
| `\php` | 0 | `\ph^\p\ke` |
| `\phpp` | 0 | `\ph^\pp\prime\ke` |
| `\myraise` | 0 | `\raise.65pt` |
| `\phmi` | 0 | `\myraise\hbox{$\ph^-$}\protect\kern -2pt` |
| `\phpl` | 0 | `\myraise\hbox{$\ph^+$}\protect\kern -2pt` |
| `\otherbar` | 0 | `\prime` |
| `\exo` | 0 | `*` |
| `\mA` | 0 | `\myraise\hbox{$\ph^-$}\protect\kern -4pt A` |
| `\mD` | 0 | `\myraise\hbox{$\ph^-$}\protect\kern -2pt D` |
| `\mE` | 0 | `\myraise\hbox{$\ph^-$}\protect\kern -2pt E` |
| `\mX` | 0 | `\myraise\hbox{$\ph^-$}\protect\kern -2pt X` |
| `\mS` | 0 | `\myraise\hbox{$\ph^-$}\protect\kern -2pt S` |
| `\foA` | 0 | `\raise 1.17pt\hbox{$\ph^f$}\protect\kern -4pt A` |
| `\foD` | 0 | `\myraise\hbox{$\ph^f$}\protect\kern -2pt D` |
| `\foE` | 0 | `\myraise\hbox{$\ph^f$}\protect\kern -2pt E` |
| `\plA` | 0 | `\myraise\hbox{$\ph^+$}\protect\kern -4pt A` |
| `\plD` | 0 | `\myraise\hbox{$\ph^+$}\protect\kern -2pt D` |
| `\plE` | 0 | `\myraise\hbox{$\ph^+$}\protect\kern -2pt E` |
| `\plX` | 0 | `\myraise\hbox{$\ph^+$}\protect\kern -2pt X` |
| `\plS` | 0 | `\myraise\hbox{$\ph^+$}\protect\kern -2pt S` |
| `\quA` | 0 | `^?\kern -3pt A` |
| `\pA` | 0 | `\php \kern -1pt A` |
| `\pD` | 0 | `\php D` |
| `\pE` | 0 | `\php E` |
| `\pX` | 0 | `\php X` |
| `\pS` | 0 | `\php S` |
| `\ppA` | 0 | `\phpp \kern -1pt A` |
| `\ppD` | 0 | `\phpp D` |
| `\ppE` | 0 | `\phpp E` |
| `\ppX` | 0 | `\phpp X` |
| `\ppS` | 0 | `\phpp S` |
| `\testminusalignment` | 0 | `$A_2^- \mA_3$ $A^-_0 \mA_0 A_0^-$ $D_0^- \mD_3$ $D^-_0 \mD_0 D_0^-$ $E_0^- \mE_3$ $E^-_0 \mE_0 E_0^-$` |
| `\testplusalignment` | 0 | `$A_2^+ \plA_3$ $A^+_0 \plA_0 A_0^+$ $D_0^+ \plD_3$ $D^+_0 \plD_0 D_0^+$ $E_0^+ \plE_3$ $E^+_0 \plE_0 E_0^+$` |
| `\ccy` | 0 | `\rowcolor{black!8}` |
| `\mapsfrom` | 0 | `\mathrel{\reflectbox{\ensuremath{\mapsto}}}` |
| `\dzg` | 1 | `\@ifundefined{todo}{#1}{\todo[color=blue!40]{#1}}` |
| `\dzginline` | 1 | `\@ifundefined{todo}{#1}{\todo[inline,color=blue!40]{#1}}` |

### `styles/macros/tier4-preamble.tex`

| Macro | Args | Expansion |
| --- | --- | --- |
| `\mid` | 0 | `\mathrel{\Big\|}` |
| `\thesubsection` | 0 | `\thesection.\arabic{subsection}` |
| `\thesubsection` | 0 | `\thesection\Alph{subsection}` |

### `styles/macros/categories.tex`

| Macro | Args | Expansion |
| --- | --- | --- |
| `\Sets` | 0 | `{\mathsf{Set}}` |
| `\Set` | 0 | `{\mathsf{Set}}` |
| `\sets` | 0 | `{\mathsf{Set}}` |
| `\set` | 0 | `{\mathsf{Set}}` |
| `\Poset` | 0 | `\mathsf{Poset}` |
| `\Groups` | 0 | `{\mathsf{Group}}` |
| `\Grp` | 0 | `{\mathsf{Grp}}` |
| `\cC` | 0 | `{\mathsf{C}}` |
| `\Ar` | 0 | `{\mathsf{Ar}}` |
| `\Mot` | 0 | `{\mathsf{Mot}}` |
| `\SW` | 0 | `{\mathsf{SW}}` |
| `\cof` | 0 | `{\mathsf{cof}}` |
| `\fib` | 0 | `{\mathsf{fib}}` |
| `\der` | 0 | `{\mathsf{d}}` |
| `\dg` | 0 | `{\mathsf{dg}}` |
| `\comm` | 0 | `{\mathsf{C}}` |
| `\pre` | 0 | `{\mathsf{pre}}` |
| `\fn` | 0 | `{\mathsf{fn}}` |
| `\smooth` | 0 | `{\mathsf{sm}}` |
| `\Aff` | 0 | `{\mathsf{Aff}}` |
| `\Ab` | 0 | `{\mathsf{Ab}}` |
| `\Add` | 0 | `{\mathsf{Add}}` |
| `\Assoc` | 0 | `\mathsf{Assoc}` |
| `\Ch` | 0 | `\mathsf{Ch}` |
| `\Coh` | 0 | `{\mathsf{Coh}}` |
| `\Comm` | 0 | `\mathsf{Comm}` |
| `\Cor` | 0 | `\mathsf{Cor}` |
| `\Corr` | 0 | `\mathsf{Cor}` |
| `\Fin` | 0 | `{\mathsf{Fin}}` |
| `\Free` | 0 | `\mathsf{Free}` |
| `\Tors` | 0 | `\mathsf{Tors}` |
| `\Perf` | 0 | `\mathsf{Perf}` |
| `\Unital` | 0 | `\mathsf{Unital}` |
| `\eff` | 0 | `\mathsf{eff}` |
| `\Dc` | 0 | `\mathbf{D}` |
| `\Db` | 0 | `\mathsf{D}^b` |
| `\db` | 0 | `\Db` |
| `\Const` | 0 | `\mathsf{Const}` |
| `\Cx` | 0 | `\mathsf{Ch}` |
| `\Stable` | 0 | `\mathsf{Stab}` |
| `\Vect` | 0 | `{ \mathsf{Vect}}` |
| `\kvect` | 0 | `{ \mathsf{Vect}\slice{k}}` |
| `\loc` | 0 | `{\mathsf{loc}}` |
| `\locfree` | 0 | `{\mathsf{locfree}}` |
| `\Bun` | 0 | `{\mathsf{Bun}}` |
| `\Prinbun` | 0 | `{ \mathsf{PrinBun}}` |
| `\bung` | 0 | `{\mathsf{Bun}_G}` |
| `\Local` | 0 | `\mathsf{Local}` |
| `\Field` | 0 | `\mathsf{Field}` |
| `\Number` | 0 | `\mathsf{Number}` |
| `\Numberfield` | 0 | `\Field\slice{\QQ}` |
| `\NF` | 0 | `\Numberfield` |
| `\Art` | 0 | `\mathsf{Art}` |
| `\Global` | 0 | `\mathsf{Global}` |
| `\Ring` | 0 | `\mathsf{Ring}` |
| `\Mon` | 0 | `\mathsf{Mon}` |
| `\CMon` | 0 | `\mathsf{CMon}` |
| `\CRing` | 0 | `\mathsf{CRing}` |
| `\DedekindDomain` | 0 | `\mathsf{DedekindDom}` |
| `\IntDomain` | 0 | `\mathsf{IntDom}` |
| `\Dom` | 0 | `\mathsf{Dom}` |
| `\Domain` | 0 | `\mathsf{Domain}` |
| `\DVR` | 0 | `\mathsf{DVR}` |
| `\Dedekind` | 0 | `\mathsf{Dedekind}` |
| `\Quat` | 0 | `{\mathsf{Quat}}` |
| `\Mod` | 0 | `{\mathsf{Mod}}` |
| `\modr` | 0 | `\modsright{R}` |
| `\grMod` | 0 | `{\mathsf{grMod}}` |
| `\zmod` | 0 | `\modsleft{\ZZ}` |
| `\qmod` | 0 | `\modsleft{\QQ}` |
| `\rmod` | 0 | `\modsleft{R}` |
| `\kmod` | 0 | `\modsleft{k}` |
| `\cmod` | 0 | `\modsleft{ \CC }` |
| `\fmod` | 0 | `\modsleft{ \FF }` |
| `\oxmods` | 0 | `\mods{\OO_X}` |
| `\amod` | 0 | `\mods{A}` |
| `\gmod` | 0 | `\mods{G}` |
| `\lmod` | 0 | `\mods{L}` |
| `\Dmod` | 0 | `\modsleft{\mathcal{D}}` |
| `\dmod` | 0 | `\Dmod` |
| `\gr` | 0 | `{\mathsf{gr}\,}` |
| `\mmod` | 0 | `{\dash\mathsf{Mod}}` |
| `\Rep` | 0 | `{\mathsf{Rep}}` |
| `\Irr` | 0 | `{\mathsf{Irr}}` |
| `\Adm` | 0 | `{\mathsf{Adm}}` |
| `\semisimp` | 0 | `{\mathsf{ss}}` |
| `\Hodge` | 0 | `{\mathsf{Hodge}}` |
| `\VectBundle` | 0 | `{ \Bun\qty{\GL_r}}` |
| `\VectSp` | 0 | `{ \VectSp }` |
| `\VectBun` | 0 | `{ \VectBundle }` |
| `\Bung` | 0 | `{ \Bun\qty{G}}` |
| `\Alg` | 0 | `\mathsf{Alg}` |
| `\Hopf` | 0 | `\mathsf{Hopf}` |
| `\alg` | 0 | `\Alg` |
| `\scalg` | 0 | `\mathsf{sCAlg}` |
| `\cAlg` | 0 | `{\mathsf{cAlg}}` |
| `\calg` | 0 | `\mathsf{CAlg}` |
| `\liegmod` | 0 | `{\mathfrak{g}\dash\mathsf{Mod}}` |
| `\liealg` | 0 | `{\mathsf{Lie}\dash\Alg}` |
| `\Lie` | 0 | `\mathsf{Lie}` |
| `\kalg` | 0 | `{}_{k} \Alg` |
| `\kAlg` | 0 | `\kalg` |
| `\falg` | 0 | `{}_{\FF} \Alg` |
| `\ralg` | 0 | `{}_{R} \Alg` |
| `\rAlg` | 0 | `\ralg` |
| `\zalg` | 0 | `{}_{\ZZ} \Alg` |
| `\CCalg` | 0 | `{}_{\CC} \Alg` |
| `\dga` | 0 | `{\mathsf{dg\Alg}}` |
| `\cdga` | 0 | `{ \mathsf{c}\dga }` |
| `\FMP` | 0 | `\mathsf{FMP}` |
| `\dgla` | 0 | `\dg\Lie\Alg` |
| `\DGLA` | 0 | `\dgla` |
| `\Poly` | 0 | `{\mathsf{Poly}}` |
| `\Hk` | 0 | `{\mathsf{Hk}}` |
| `\Asm` | 0 | `{\mathsf{Asm}}` |
| `\kSch` | 0 | `{\mathsf{Sch}_{/k}}` |
| `\Grpd` | 0 | `{\mathsf{Grpd}}` |
| `\inftyGrpd` | 0 | `{ \underset{\infty}{ \Grpd }}` |
| `\Algebroid` | 0 | `{\mathsf{Algd}}` |
| `\Loc` | 0 | `\mathsf{Loc}` |
| `\Locsys` | 0 | `\mathsf{LocSys}` |
| `\Ringedspace` | 0 | `\mathsf{RingSp}` |
| `\RingedSpace` | 0 | `\mathsf{RingSp}` |
| `\LRS` | 0 | `\Loc\RingedSpace` |
| `\IndCoh` | 0 | `{\mathsf{IndCoh}}` |
| `\dbcoh` | 0 | `\mathsf{D}^b\mathsf{Coh}` |
| `\DbCoh` | 0 | `\dbcoh` |
| `\DCoh` | 0 | `\mathsf{D}\mathsf{Coh}` |
| `\dcoh` | 0 | `\DCoh` |
| `\QCoh` | 0 | `{\mathsf{QCoh}}` |
| `\qcoh` | 0 | `\QCoh` |
| `\Ind` | 0 | `{\mathsf{Ind}}` |
| `\ind` | 0 | `\Ind` |
| `\Pro` | 0 | `\mathsf{pro}` |
| `\pro` | 0 | `\Pro` |
| `\Cov` | 0 | `{\mathsf{Cov}}` |
| `\sch` | 0 | `{\mathsf{Sch}}` |
| `\presh` | 0 | `\underset{ \mathsf{pre}} {\mathsf{Sh}}` |
| `\prest` | 0 | `{\underset{ \mathsf{pre}} {\mathsf{St}} }` |
| `\Descent` | 0 | `{\mathsf{Descent}}` |
| `\Desc` | 0 | `{\mathsf{Desc}}` |
| `\FFlat` | 0 | `{\mathsf{FFlat}}` |
| `\Perv` | 0 | `\mathsf{Perv}` |
| `\smsch` | 0 | `{ \smooth\Sch }` |
| `\Sch` | 0 | `{\mathsf{Sch}}` |
| `\Schf` | 0 | `{\mathsf{Schf}}` |
| `\Sh` | 0 | `{\mathsf{Sh}}` |
| `\St` | 0 | `{\mathsf{St}}` |
| `\Stacks` | 0 | `{\mathsf{St}}` |
| `\Var` | 0 | `{\mathsf{Var}}` |
| `\Vark` | 0 | `{ \Var_{/k}}` |
| `\kvar` | 0 | `{ \Var_{/k}}` |
| `\Open` | 0 | `{\mathsf{Open}}` |
| `\CW` | 0 | `{\mathsf{CW}}` |
| `\sset` | 0 | `{\mathsf{sSet}}` |
| `\sSet` | 0 | `{\mathsf{sSet}}` |
| `\ssets` | 0 | `\mathsf{sSet}` |
| `\hoTop` | 0 | `{\mathsf{hoTop}}` |
| `\hoType` | 0 | `{\mathsf{hoType}}` |
| `\ho` | 0 | `{\mathsf{ho}}` |
| `\SHC` | 0 | `{\mathsf{SHC}}` |
| `\SH` | 0 | `{\mathsf{SH}}` |
| `\Spaces` | 0 | `{\mathsf{Spaces}}` |
| `\Spectra` | 0 | `{\mathsf{Sp}}` |
| `\Sp` | 0 | `{\mathsf{Sp}}` |
| `\Top` | 0 | `{\mathsf{Top}}` |
| `\Bord` | 0 | `{\mathsf{Bord}}` |
| `\TQFT` | 0 | `{\mathsf{TQFT}}` |
| `\Kc` | 0 | `{\mathsf{K^c}}` |
| `\triang` | 0 | `{\mathsf{triang}}` |
| `\TTC` | 0 | `{\mathsf{TTC}}` |
| `\dchrmod` | 0 | `{\derivedcat{\Ch(\rmod)}}` |
| `\Finset` | 0 | `{\mathsf{FinSet}}` |
| `\Cat` | 0 | `\mathsf{Cat}` |
| `\Fun` | 0 | `{\mathsf{Fun}}` |
| `\Kan` | 0 | `{\mathsf{Kan}}` |
| `\Monoid` | 0 | `\mathsf{Mon}` |
| `\Arrow` | 0 | `\mathsf{Arrow}` |
| `\quasiCat` | 0 | `{ \mathsf{quasiCat}}` |
| `\inftycat` | 0 | `{ \underset{\infty}{ \Cat} }` |
| `\core` | 0 | `{ \mathsf{core}}` |
| `\Indcat` | 0 | `\mathsf{Ind}` |
| `\Prism` | 0 | `\mathsf{Prism}` |
| `\Solid` | 0 | `\mathsf{Solid}` |
| `\WCart` | 0 | `\mathsf{WCart}` |
| `\Quadform` | 0 | `{\mathsf{QuadForm}}` |
| `\HI` | 0 | `{\mathsf{HI}}` |
| `\DM` | 0 | `{\mathsf{DM}}` |
| `\hoA` | 0 | `{\mathsf{ho}_*^{\scriptstyle \AA^1}}` |
| `\Tw` | 0 | `\mathsf{Tw}` |
| `\SB` | 0 | `\mathsf{SB}` |
| `\CSA` | 0 | `\mathsf{CSA}` |
| `\CSS` | 0 | `{ \mathsf{CSS}}` |
| `\FGL` | 0 | `\mathsf{FGL}` |
| `\FI` | 0 | `{\mathsf{FI}}` |
| `\CE` | 0 | `{\mathsf{CE}}` |
| `\Fuk` | 0 | `{\mathsf{Fuk}}` |
| `\Lag` | 0 | `{\mathsf{Lag}}` |
| `\Mfd` | 0 | `{\mathsf{Mfd}}` |
| `\Riem` | 0 | `\mathsf{Riem}` |
| `\Wein` | 0 | `{\mathsf{Wein}}` |
| `\deltaring` | 0 | `{\delta\dash\mathsf{Ring}}` |
| `\terminal` | 0 | `{ 0_{\scriptscriptstyle \uparrow}}` |
| `\initial` | 0 | `{ \mathscr \emptyset^{\scriptscriptstyle \downarrow}}` |
| `\coeq` | 0 | `\operatorname{coeq}` |
| `\cocoeq` | 0 | `\operatorname{eq}` |
| `\cat` | 1 | `\mathsf{#1}` |
| `\GSets` | 0 | `{G\dash\mathsf{Set}}` |
| `\derivedcat` | 1 | `\Dc {#1}` |
| `\bderivedcat` | 1 | `\Db {#1}` |
| `\ChainCx` | 1 | `\mathsf{Ch}\qty{ #1 }` |
| `\Fieldsover` | 1 | `{ \mathsf{Fields}_{#1}}` |
| `\torsors` | 1 | `{\mathsf{#1}\dash\mathsf{Torsors}}` |
| `\torsorsright` | 1 | `\mathsf{Torsors}\dash\mathsf{#1}` |
| `\torsorsleft` | 1 | `\mathsf{#1}\dash\mathsf{Torsors}` |
| `\bimod` | 2 | `({#1}, {#2})\dash\mathsf{biMod}` |
| `\bimods` | 2 | `({#1}, {#2})\dash\mathsf{biMod}` |
| `\modsleft` | 1 | `{}_{#1}\Mod` |
| `\modsright` | 1 | `\Mod_{#1}` |
| `\mods` | 1 | `\modsleft{#1}` |
| `\stmods` | 1 | `{\mathsf{#1}\dash\mathsf{stMod}}` |
| `\grmods` | 1 | `{\mathsf{#1}\dash\mathsf{grMod}}` |
| `\comods` | 1 | `{\mathsf{#1}\dash\mathsf{coMod}}` |
| `\gsetsleft` | 1 | `{}_{#1}\Set` |
| `\gsetsright` | 1 | `\Set_{#1}` |
| `\gset` | 1 | `\gsetsleft{#1}` |
| `\gsets` | 1 | `\gset{#1}` |
| `\VectBundlerk` | 1 | `{ \Bun\qty{\GL_{#1}}}` |
| `\VectBunrk` | 1 | `{ \VectBundlerk{#1}}` |
| `\algs` | 1 | `{ {}_{#1} \Alg }` |
| `\inftycatn` | 1 | `{ \underset{(\infty, {#1})}{ \Cat} }` |
| `\GSpaces` | 0 | `{G\dash\mathsf{Spaces}}` |
| `\gspaces` | 1 | `{#1}\dash{\mathsf{Spaces}}` |
| `\Torsor` | 1 | `{\mathsf{#1}\dash\mathsf{Torsor}}` |
| `\Torsorleft` | 1 | `{\mathsf{#1}\dash\mathsf{Torsor}}` |
| `\Torsorright` | 1 | `{\mathsf{Torsor}\dash\mathsf{#1}}` |
| `\adj` | 4 | `#1 \mathrel{\underset{#4}{\overset{#3}{\rightleftarrows}}} #2` |

### `styles/macros/spectral.tex`

| Macro | Args | Expansion |
| --- | --- | --- |
| `\tmf` | 0 | `\mathrm{tmf}` |
| `\taf` | 0 | `\mathrm{taf}` |
| `\TAF` | 0 | `\mathrm{TAF}` |
| `\TMF` | 0 | `\mathrm{TMF}` |
| `\String` | 0 | `\mathrm{String}` |
| `\BO` | 0 | `{\B \Orth}` |
| `\EO` | 0 | `{\mathsf{E} \Orth}` |
| `\BSO` | 0 | `{\B\SO}` |
| `\ESO` | 0 | `{\mathsf{E}\SO}` |
| `\BG` | 0 | `{\B G}` |
| `\EG` | 0 | `{\mathsf{E} G}` |
| `\BP` | 0 | `{\operatorname{BP}}` |
| `\BU` | 0 | `\B{\operatorname{U}}` |
| `\MO` | 0 | `{\operatorname{MO}}` |
| `\MSO` | 0 | `{\operatorname{MSO}}` |
| `\MSpin` | 0 | `{\operatorname{MSpin}}` |
| `\MSp` | 0 | `{\operatorname{MSpin}}` |
| `\MString` | 0 | `{\operatorname{MString}}` |
| `\MStr` | 0 | `{\operatorname{MString}}` |
| `\MU` | 0 | `{\operatorname{MU}}` |
| `\KO` | 0 | `{\operatorname{KO}}` |
| `\KU` | 0 | `{\operatorname{KU}}` |
| `\ku` | 0 | `{\operatorname{ku}}` |
| `\smashprod` | 0 | `\wedge` |
| `\hofib` | 0 | `{\operatorname{hofib}}` |
| `\cofib` | 0 | `{\operatorname{cofib}}` |
| `\hocofib` | 0 | `{\operatorname{hocofib}}` |
| `\Loop` | 0 | `{\Omega}` |
| `\Loops` | 0 | `\Loop` |
| `\Suspend` | 0 | `{\Sigma}` |
| `\Suspendpinf` | 0 | `\operatorname{{\Sigma_+^\infty}}` |
| `\Loopinf` | 0 | `\operatorname{{\Omega^\infty}}` |
| `\Loopsinf` | 0 | `\Loopinf` |

### `styles/macros/figure-include.tex`

No macro or environment definitions.

### `styles/macros/environments.tex`

| Macro | Args | Expansion |
| --- | --- | --- |
| `\rmargnote` | 1 | `\marginnote{{\footnotesize #1}}` |
| `\quote` | 0 | `\myblock` |
| `\endquote` | 0 | `\endmyblock` |
| `\stacktype` | 0 | `L` |

| Environment | Heading or definition |
| --- | --- |
| `theorem` | `Theorem` |
| `proposition` | `Proposition` |
| `conjecture` | `Conjecture` |
| `lemma` | `Lemma` |
| `corollary` | `Corollary` |
| `pf` | `Proof` |
| `definition` | `Definition` |
| `construction` | `Construction` |
| `goal` | `Goal` |
| `assumption` | `Assumption` |
| `problem` | `Problem` |
| `claim` | `Claim` |
| `solution` | `Solution` |
| `strategy` | `Strategy` |
| `concept` | `Concepts Used` |
| `exercise` | `Exercise` |
| `exercise` | `Exercise` |
| `slogan` | `Slogan` |
| `question` | `Question` |
| `answer` | `Answer` |
| `observation` | `Observation` |
| `fact` | `Fact` |
| `example` | `Example` |
| `remark` | `Remark` |
| `nb` | `NB` |
| `note` | `NB` |
| `warnings` | `Warning` |
| `warning` | `Warning` |

### `styles/macros/environments-arxiv.tex`

| Environment | Heading or definition |
| --- | --- |
| `theorem` | `Theorem` |
| `claim` | `Claim` |
| `conjecture` | `Conjecture` |
| `corollary` | `Corollary` |
| `lemma` | `Lemma` |
| `metatheorem` | `Meta-Theorem` |
| `proposition` | `Proposition` |
| `acknowledgements` | `Acknowledgements` |
| `addendum` | `Addendum` |
| `answer` | `Answer` |
| `assumption` | `Assumption` |
| `fact` | `Fact` |
| `condition` | `Condition` |
| `construction` | `Construction` |
| `convention` | `Convention` |
| `definition` | `Definition` |
| `example` | `Example` |
| `examples` | `Examples` |
| `exercise` | `Exercise` |
| `goal` | `Goal` |
| `notation` | `Notation` |
| `notations` | `Notations` |
| `num` |  |
| `numl` |  |
| `observation` | `Observation` |
| `project` | `Project` |
| `problem` | `Problem` |
| `proposal` | `Proposal` |
| `question` | `Question` |
| `remark` | `Remark` |
| `setup` | `Setup` |
| `warning` | `Warning` |
| `sketch` | `Sketch` |

### `styles/macros/dissertation-overrides.tex`

| Macro | Args | Expansion |
| --- | --- | --- |
| `\Aff` | 0 | `\operatorname{Aff}` |
| `\BBfan` | 0 | `\Sigma^{\BB}` |
| `\DD` | 0 | `\mathbf{D}` |
| `\Sch` | 0 | `\operatorname{Sch}` |
| `\Set` | 0 | `\operatorname{\mathsf{Sets}}` |
| `\Sp` | 0 | `\operatorname{Sp}` |
| `\bbcpt` | 1 | `\cpt{#1}^{ \BB }` |
| `\bd` | 0 | `\partial` |
| `\coxfan` | 0 | `\torfan^{\cox}` |
| `\gitcpt` | 1 | `\cpt{#1}^{ \GIT }` |
| `\ksbacpt` | 1 | `\cpt{#1}` |
| `\matt` | 4 | `\begin{pmatrix} #1 & #2 \\ #3 & #4 \end{pmatrix}` |
| `\st` | 0 | `\operatorname{st}` |

## Figure objects

| Object | Placed with | Description |
| --- | --- | --- |
| `ade/A0-minus` | `\pic {object=ade/A0-minus}` | `The toric ADE pair A_{0}^{-} [Alexeev-Thompson, arXiv:1712.07932, Table 1]: Q = conv{(0,2), (0,0), (1,0)}, p* = (0,2) a vertex.` |
| `ade/A2-minus` | `\pic {object=ade/A2-minus}` | `The toric ADE pair A_{2}^{-} [Alexeev-Thompson, arXiv:1712.07932, Table 1]: Q = conv{(0,2), (0,0), (3,0)}, p* = (0,2) a vertex.` |
| `ade/A3` | `\pic {object=ade/A3}` | `The toric ADE pair A_{3} [Alexeev-Thompson, arXiv:1712.07932, Table 1]: Q = conv{(0,2), (0,0), (4,0)}, p* = (0,2) a vertex.` |
| `ade/A4-minus` | `\pic {object=ade/A4-minus}` | `The toric ADE pair A_{4}^{-} [Alexeev-Thompson, arXiv:1712.07932, Table 1]: Q = conv{(0,2), (0,0), (5,0)}, p* = (0,2) a vertex.` |
| `ade/A5` | `\pic {object=ade/A5}` | `The toric ADE pair A_{5} [Alexeev-Thompson, arXiv:1712.07932, Table 1]: Q = conv{(0,2), (0,0), (6,0)}, p* = (0,2) a vertex.` |
| `ade/A6-minus` | `\pic {object=ade/A6-minus}` | `The toric ADE pair A_{6}^{-} [Alexeev-Thompson, arXiv:1712.07932, Table 1]: Q = conv{(0,2), (0,0), (7,0)}, p* = (0,2) a vertex.` |
| `ade/D10-prime` | `\pic {object=ade/D10-prime}` | `The toric ADE pair D_{10}' [Alexeev-Thompson, arXiv:1712.07932, Table 4]: Q = conv{(2,2), (0,2), (0,0), (6,0), (5,1)}, p* = (2,2) a vertex.` |
| `ade/D12-prime` | `\pic {object=ade/D12-prime}` | `The toric ADE pair D_{12}' [Alexeev-Thompson, arXiv:1712.07932, Table 4]: Q = conv{(2,2), (0,2), (0,0), (8,0), (6,1)}, p* = (2,2) a vertex.` |
| `ade/D4` | `\pic {object=ade/D4}` | `The toric ADE pair D_{4} [Alexeev-Thompson, arXiv:1712.07932, Table 1]: Q = conv{(2,2), (0,2), (0,0), (2,0)}, p* = (2,2) a vertex.` |
| `ade/D5-minus` | `\pic {object=ade/D5-minus}` | `The toric ADE pair D_{5}^{-} [Alexeev-Thompson, arXiv:1712.07932, Table 1]: Q = conv{(2,2), (0,2), (0,0), (3,0)}, p* = (2,2) a vertex.` |
| `ade/D6-prime` | `\pic {object=ade/D6-prime}` | `The toric ADE pair D_{6}' [Alexeev-Thompson, arXiv:1712.07932, Table 4]: Q = conv{(2,2), (0,2), (0,0), (2,0), (3,1)}, p* = (2,2) a vertex.` |
| `ade/D6` | `\pic {object=ade/D6}` | `The toric ADE pair D_{6} [Alexeev-Thompson, arXiv:1712.07932, Table 1]: Q = conv{(2,2), (0,2), (0,0), (4,0)}, p* = (2,2) a vertex.` |
| `ade/D7-minus` | `\pic {object=ade/D7-minus}` | `The toric ADE pair D_{7}^{-} [Alexeev-Thompson, arXiv:1712.07932, Table 1]: Q = conv{(2,2), (0,2), (0,0), (5,0)}, p* = (2,2) a vertex.` |
| `ade/D8-prime` | `\pic {object=ade/D8-prime}` | `The toric ADE pair D_{8}' [Alexeev-Thompson, arXiv:1712.07932, Table 4]: Q = conv{(2,2), (0,2), (0,0), (4,0), (4,1)}, p* = (2,2) a vertex.` |
| `ade/D8` | `\pic {object=ade/D8}` | `The toric ADE pair D_{8} [Alexeev-Thompson, arXiv:1712.07932, Table 1]: Q = conv{(2,2), (0,2), (0,0), (6,0)}, p* = (2,2) a vertex.` |
| `ade/minus-A1-minus` | `\pic {object=ade/minus-A1-minus}` | `The toric ADE pair {}^{-}A_{1}^{-} [Alexeev-Thompson, arXiv:1712.07932, Table 1, row -A^-_{2n-3}, and Remark 3.9]: Q = conv{(0,2), (1,0), (3,0)}, p* = (0,2) a vertex.` |
| `ade/minus-A3-minus` | `\pic {object=ade/minus-A3-minus}` | `The toric ADE pair {}^{-}A_{3}^{-} [Alexeev-Thompson, arXiv:1712.07932, Table 1, row -A^-_{2n-3}, and Remark 3.9]: Q = conv{(0,2), (1,0), (5,0)}, p* = (0,2) a vertex.` |
| `ade/minus-A4` | `\pic {object=ade/minus-A4}` | `The toric ADE pair {}^{-}A_{4} [Alexeev-Thompson, arXiv:1712.07932, Table 1, row -A^-_{2n-3}, and Remark 3.9]: Q = conv{(0,2), (1,0), (6,0)}, p* = (0,2) a vertex.` |
| `ade/minus-A5-minus` | `\pic {object=ade/minus-A5-minus}` | `The toric ADE pair {}^{-}A_{5}^{-} [Alexeev-Thompson, arXiv:1712.07932, Table 1, row -A^-_{2n-3}, and Remark 3.9]: Q = conv{(0,2), (1,0), (7,0)}, p* = (0,2) a vertex.` |
| `ade/minus-A6` | `\pic {object=ade/minus-A6}` | `The toric ADE pair {}^{-}A_{6} [Alexeev-Thompson, arXiv:1712.07932, Table 1, row -A^-_{2n-3}, and Remark 3.9]: Q = conv{(0,2), (1,0), (8,0)}, p* = (0,2) a vertex.` |
| `ade/minus-E6-minus` | `\pic {object=ade/minus-E6-minus}` | `The toric ADE pair {}^{-}E_{6}^{-} [Alexeev-Thompson, arXiv:1712.07932, Table 1]: Q = conv{(2,2), (0,3), (0,0), (3,0)}, p* = (2,2) a vertex.` |
| `ade/minus-E7` | `\pic {object=ade/minus-E7}` | `The toric ADE pair {}^{-}E_{7} [Alexeev-Thompson, arXiv:1712.07932, Table 1]: Q = conv{(2,2), (0,3), (0,0), (4,0)}, p* = (2,2) a vertex.` |
| `ade/minus-E8-minus` | `\pic {object=ade/minus-E8-minus}` | `The toric ADE pair {}^{-}E_{8}^{-} [Alexeev-Thompson, arXiv:1712.07932, Table 1]: Q = conv{(2,2), (0,3), (0,0), (5,0)}, p* = (2,2) a vertex.` |
| `ade/prime-A11-prime` | `\pic {object=ade/prime-A11-prime}` | `The toric ADE pair {}'A_{11}' [Alexeev-Thompson, arXiv:1712.07932, Table 4]: Q = conv{(2,2), (0,1), (0,0), (8,0), (6,1)}, p* = (2,2) a vertex.` |
| `ade/prime-A3` | `\pic {object=ade/prime-A3}` | `The toric ADE pair {}'A_{3} [Alexeev-Thompson, arXiv:1712.07932, Table 4]: Q = conv{(2,2), (0,1), (0,0), (2,0)}, p* = (2,2) a vertex.` |
| `ade/prime-A4-minus` | `\pic {object=ade/prime-A4-minus}` | `The toric ADE pair {}'A_{4}^{-} [Alexeev-Thompson, arXiv:1712.07932, Table 4]: Q = conv{(2,2), (0,1), (0,0), (3,0)}, p* = (2,2) a vertex.` |
| `ade/prime-A5-prime` | `\pic {object=ade/prime-A5-prime}` | `The toric ADE pair {}'A_{5}' [Alexeev-Thompson, arXiv:1712.07932, Table 4]: Q = conv{(2,2), (0,1), (0,0), (2,0), (3,1)}, p* = (2,2) a vertex.` |
| `ade/prime-A5` | `\pic {object=ade/prime-A5}` | `The toric ADE pair {}'A_{5} [Alexeev-Thompson, arXiv:1712.07932, Table 4]: Q = conv{(2,2), (0,1), (0,0), (4,0)}, p* = (2,2) a vertex.` |
| `ade/prime-A6-minus` | `\pic {object=ade/prime-A6-minus}` | `The toric ADE pair {}'A_{6}^{-} [Alexeev-Thompson, arXiv:1712.07932, Table 4]: Q = conv{(2,2), (0,1), (0,0), (5,0)}, p* = (2,2) a vertex.` |
| `ade/prime-A7-prime` | `\pic {object=ade/prime-A7-prime}` | `The toric ADE pair {}'A_{7}' [Alexeev-Thompson, arXiv:1712.07932, Table 4]: Q = conv{(2,2), (0,1), (0,0), (4,0), (4,1)}, p* = (2,2) a vertex.` |
| `ade/prime-A9-prime` | `\pic {object=ade/prime-A9-prime}` | `The toric ADE pair {}'A_{9}' [Alexeev-Thompson, arXiv:1712.07932, Table 4]: Q = conv{(2,2), (0,1), (0,0), (6,0), (5,1)}, p* = (2,2) a vertex.` |
| `ade/tilde-D10` | `\pic {object=ade/tilde-D10}` | `The toric ADE pair \widetilde{D}_{10} [Alexeev-Thompson, arXiv:1712.07932, Table 1]: Q = conv{(0,2), (0,0), (6,0), (4,2)}, p* = (2,2) interior to the side [v_k, v_1].` |
| `ade/tilde-D6` | `\pic {object=ade/tilde-D6}` | `The toric ADE pair \widetilde{D}_{6} [Alexeev-Thompson, arXiv:1712.07932, Table 1]: Q = conv{(0,2), (0,0), (2,0), (4,2)}, p* = (2,2) interior to the side [v_k, v_1].` |
| `ade/tilde-D8` | `\pic {object=ade/tilde-D8}` | `The toric ADE pair \widetilde{D}_{8} [Alexeev-Thompson, arXiv:1712.07932, Table 1]: Q = conv{(0,2), (0,0), (4,0), (4,2)}, p* = (2,2) interior to the side [v_k, v_1].` |
| `ade/tilde-E7` | `\pic {object=ade/tilde-E7}` | `The toric ADE pair \widetilde{E}_{7} [Alexeev-Thompson, arXiv:1712.07932, Table 1]: Q = conv{(0,4), (0,0), (4,0)}, p* = (2,2) interior to the side [v_k, v_1].` |
| `ade/tilde-E8-minus` | `\pic {object=ade/tilde-E8-minus}` | `The toric ADE pair \widetilde{E}_{8}^{-} [Alexeev-Thompson, arXiv:1712.07932, Table 1]: Q = conv{(0,3), (0,0), (6,0)}, p* = (2,2) interior to the side [v_k, v_1].` |
| `bb-cusps/f2` | `\pic {object=bb-cusps/f2}` | `F_2, K3 surfaces of degree 2: one 0-cusp -P [Sca87 §6]. 1-cusps named by the root system of the boundary lattice (Scattone); the unimodular D_16 lattice is D_16^+.` |
| `bb-cusps/f220` | `\pic {object=bb-cusps/f220}` | `F_{(2,2,0)}, the quartic hyperelliptic K3 surfaces, T = U+U(2)+E_8^2 [AE22 §10].` |
| `bb-cusps/f2d-1` | `\pic {object=bb-cusps/f2d-1}` | `The shape of Scattone's diagram of F_{2d} for d of class N = 1 [Sca87 §6]: a 0-cusp p_0 meeting the 1-cusps C_i over H/SL_2(Z).` |
| `bb-cusps/f2d-3` | `\pic {object=bb-cusps/f2d-3}` | `The shape of Scattone's diagram of F_{2d} for d of class N = 3 [Sca87 §6]: a 0-cusp p_0 meeting the 1-cusps C_i over H/SL_2(Z), and a 0-cusp p_1 meeting the 1-cusps C_i^{(3)} over H/Gamma'(3), which ...` |
| `bb-cusps/f2d-5` | `\pic {object=bb-cusps/f2d-5}` | `The shape of Scattone's diagram of F_{2d} for d of class N = 5 [Sca87 §6]: a 0-cusp p_0 meeting the 1-cusps C_i over H/SL_2(Z), and 0-cusps p_1, p_2 meeting the 1-cusps C_i^{(5)} over H/Gamma'(5), ...` |
| `bb-cusps/f2d-p` | `\pic {object=bb-cusps/f2d-p}` | `The shape of Scattone's diagram of F_{2d} for d of class N, an odd prime [Sca87 §6]: a 0-cusp p_0 meeting the 1-cusps C_i over H/SL_2(Z), and 0-cusps p_1, ..., p_{(N-1)/2} meeting the 1-cusps ...` |
| `bb-cusps/f4` | `\pic {object=bb-cusps/f4}` | `F_4, K3 surfaces of degree 4: one 0-cusp -P [Sca87 §6]. 1-cusps named by the root system of the boundary lattice (Scattone).` |
| `bb-cusps/fco` | `\pic {object=bb-cusps/fco}` | `Unpolarized Coble F_Co (writing/coble/cusp-correspondence), T_Co = <2>+E_10(2).` |
| `bb-cusps/fell` | `\pic {object=bb-cusps/fell}` | `F_ell, elliptic K3 surfaces: one 0-cusp -P [Sca87 §6]. 1-cusps named by the root system of the boundary lattice (Scattone); the unimodular D_16 lattice is D_16^+.` |
| `bb-cusps/fen` | `\pic {object=bb-cusps/fen}` | `Unpolarized Enriques F_En [AEGS25], [Ste91 §4.2], T_En = U+U(2)+E_8(2).` |
| `bb-cusps/fen2` | `\pic {object=bb-cusps/fen2}` | `Sterk's F_{En,2} [Ste91 §4]: five 0-cusps -1, ..., -5 and nine 1-cusps named by the 0-cusps in their closure (-12, -245, -13, ...).` |
| `contours/quarter-disc` | `\pic {object=contours/quarter-disc}` | `The boundary of the sector {\|z\| <= R, 0 <= arg z <= pi/2} in C, R = 3, counterclockwise: [0,R], the arc, [iR,0]; with coordinate axes and the label C.` |
| `contours/strip-rectangle` | `\pic {object=contours/strip-rectangle}` | `The boundary of the rectangle [-R,R] x i[-b,0] in C, counterclockwise, R = 2.5, b = 1.5; with coordinate axes and the label C.` |
| `coxeter/A4` | `\pic {object=coxeter/A4}` | `The Coxeter diagram of the root lattice A_4 [Bourbaki, Groupes et algebres de Lie IV-VI, Planche I]: the chain 1..4 of roots of square -2 (white).` |
| `coxeter/E8` | `\pic {object=coxeter/E8}` | `The Coxeter diagram of the root lattice E_8, in Bourbaki's numbering [Bourbaki, Groupes et algebres de Lie IV-VI, Planche VII]: roots of square -2 (white).` |
| `coxeter/G2-affine` | `\pic {object=coxeter/G2-affine}` | `The Coxeter diagram of the affine group G~_2 [Humphreys, Reflection Groups and Coxeter Groups, §2.5], drawn with multiple edges: an edge of weight m is m-2 lines, so the edge 1-2 of weight 6 is a ...` |
| `coxeter/G2` | `\pic {object=coxeter/G2}` | `The Coxeter diagram of G_2 = I_2(6) [Humphreys, Reflection Groups and Coxeter Groups, §2.4], drawn with multiple edges: an edge of weight m is m-2 lines, so the edge of weight 6 is a quadruple edge.` |
| `coxeter/H3` | `\pic {object=coxeter/H3}` | `The Coxeter diagram of H_3 [Humphreys, Reflection Groups and Coxeter Groups, §2.4], drawn with multiple edges: an edge of weight m is m-2 lines, so the edge 1-2 of weight 5 is a triple edge.` |
| `coxeter/H4` | `\pic {object=coxeter/H4}` | `The Coxeter diagram of H_4 [Humphreys, Reflection Groups and Coxeter Groups, §2.4], drawn with multiple edges: an edge of weight m is m-2 lines, so the edge 1-2 of weight 5 is a triple edge.` |
| `coxeter/k3-F4` | `\pic {object=coxeter/k3-F4}` | `The Coxeter diagram for the moduli F_4 of degree-4 K3 surfaces: 24 roots of square -2 spanning U+E_8^2+<-4> (rank 19, signature (1,18), discriminant Z/4, computed from this Gram matrix; roots of ...` |
| `coxeter/sterk-cusp-1` | `\pic {object=coxeter/sterk-cusp-1}` | `The Coxeter diagram of the 0-cusp eta_1 of F_{En,2} (Sterk 1991, diagram I; the dissertation numbers the cusps as Sterk does).` |
| `coxeter/sterk-cusp-3` | `\pic {object=coxeter/sterk-cusp-3}` | `The Coxeter diagram of the 0-cusp eta_3 of F_{En,2} (Sterk 1991, diagram III; the dissertation numbers the cusps as Sterk does).` |
| `coxeter/sterk-cusp-4` | `\pic {object=coxeter/sterk-cusp-4}` | `The Coxeter diagram of the 0-cusp eta_4 of F_{En,2} (Sterk 1991, diagram IV; the dissertation numbers the cusps as Sterk does).` |
| `coxeter/sterk-cusp-5` | `\pic {object=coxeter/sterk-cusp-5}` | `The Coxeter diagram of the 0-cusp eta_5 of F_{En,2} (Sterk 1991, diagram V; the dissertation numbers the cusps as Sterk does).` |
| `coxeter/sterk-cusp-cover-1` | `\pic {object=coxeter/sterk-cusp-cover-1}` | `The K3 cusp diagram covering the Coxeter diagram of the 0-cusp eta_1 of F_{En,2} (objects/coxeter/sterk-cusp-1): the (18,2,0)_1 diagram with the involution J_1 whose folding gives it ...` |
| `coxeter/sterk-cusp-cover-2` | `\pic {object=coxeter/sterk-cusp-cover-2}` | `The K3 cusp diagram covering the Coxeter diagram of the 0-cusp eta_2 of F_{En,2} (objects/coxeter/vinberg-10-8-0): the (18,0,0)_1 diagram with the involution J_2 whose folding gives it ...` |
| `coxeter/sterk-cusp-cover-3` | `\pic {object=coxeter/sterk-cusp-cover-3}` | `The K3 cusp diagram covering the Coxeter diagram of the 0-cusp eta_3 of F_{En,2} (objects/coxeter/sterk-cusp-3): the (18,2,0)_1 diagram with the involution J_3 whose folding gives it ...` |
| `coxeter/sterk-cusp-cover-4` | `\pic {object=coxeter/sterk-cusp-cover-4}` | `The K3 cusp diagram covering the Coxeter diagram of the 0-cusp eta_4 of F_{En,2} (objects/coxeter/sterk-cusp-4): the (18,2,0)_1 diagram with the involution J_4 whose folding gives it ...` |
| `coxeter/sterk-cusp-cover-5` | `\pic {object=coxeter/sterk-cusp-cover-5}` | `The K3 cusp diagram covering the Coxeter diagram of the 0-cusp eta_5 of F_{En,2} (objects/coxeter/sterk-cusp-5): the (18,2,0)_1 diagram with the involution J_5 whose folding gives it ...` |
| `coxeter/vinberg-10-10-0` | `\pic {object=coxeter/vinberg-10-10-0}` | `The Vinberg diagram of (10,10,0)_1 = E_10(2): ten roots of square -4 (black) forming T_{2,3,7} = E_10, in Bourbaki's numbering.` |
| `coxeter/vinberg-10-8-0` | `\pic {object=coxeter/vinberg-10-8-0}` | `The Vinberg diagram of (10,8,0)_1 = U + E_8(2): nine roots of square -4 (black) forming T_{2,3,6} in Bourbaki's numbering of E_9, and one root 10 of square -2 (white) joined to the end 9 of the long ...` |
| `coxeter/vinberg-18-0-0` | `\pic {object=coxeter/vinberg-18-0-0}` | `The Vinberg diagram of II_{1,17} = (18,0,0)_1 = U + E_8^2 [Vinberg 1972], the boundary lattice at a 0-cusp of F_{(2,2,0)}.` |
| `coxeter/vinberg-18-2-0` | `\pic {object=coxeter/vinberg-18-2-0}` | `The Vinberg diagram of (18,2,0)_1 = U(2) + E_8^2, the boundary lattice at a 0-cusp of F_{(2,2,0)}.` |
| `coxeter/vinberg-19-1-1` | `\pic {object=coxeter/vinberg-19-1-1}` | `The Vinberg diagram of (19,1,1)_1 = U + E_8^2 + A_1.` |
| `coxeter/vinberg-8-8-1` | `\pic {object=coxeter/vinberg-8-8-1}` | `The Vinberg diagram of (8,8,1)_1 = U(2) + A_1^6: seven roots of square -4 (black) forming E_7 in Bourbaki's numbering, and one root 8 of square -2 (white) at the end 7 of the long arm with weight 4.` |
| `coxeter/vinberg-9-9-1` | `\pic {object=coxeter/vinberg-9-9-1}` | `The Vinberg diagram of (9,9,1)_1 = <2> + E_8(2) = G_{(9,9,1)_1}: eight roots of square -4 (black) forming E_8 in Bourbaki's numbering, and one root 9 of square -2 (white) joined to the end 8 of the ...` |
| `diagrams/cowedge-square-AB` | `\pic {object=diagrams/cowedge-square-AB}` | `The cowedge condition for a bifunctor F: C^op x C -> D, a morphism f: A -> B and a cowedge h: F => X (dinaturality to a constant), identities written as objects.` |
| `diagrams/cowedge-square` | `\pic {object=diagrams/cowedge-square}` | `The cowedge condition for a bifunctor F: C^op x C -> D, a morphism g: c -> d and a cowedge zeta: F => X (dinaturality to a constant) (Definition 1.1.16).` |
| `diagrams/enriques-correspondence-E` | `\pic {object=diagrams/enriques-correspondence-E}` | `The correspondence between the moduli of degree 2 polarized Enriques surfaces E_2, unpolarized Enriques surfaces E_\emptyset, and degree 4 hyperelliptic K3 surfaces F_{4,h.e.}: phi_1 forgets the ...` |
| `diagrams/enriques-correspondence` | `\pic {object=diagrams/enriques-correspondence}` | `The correspondence between the moduli of degree 2 polarized Enriques surfaces F_{En,2}, unpolarized Enriques surfaces F_{En}, and degree 4 hyperelliptic K3 surfaces F_{(2,2,0)} (lattice U(2)): phi_1 ...` |
| `diagrams/klein-quotients-pairs` | `\pic {object=diagrams/klein-quotients-pairs}` | `The quotients of a K3 surface X by the Klein four-group generated by the del Pezzo involution (X -> Y), the Enriques involution (X -> Z) and the Nikulin involution (X -> Z'), all over W = X/G: the ...` |
| `diagrams/klein-quotients` | `\pic {object=diagrams/klein-quotients}` | `The quotients of a K3 surface X by the Klein four-group generated by the del Pezzo involution (X -> Y), the Enriques involution (X -> Z) and the Nikulin involution (X -> Z'), all over W = X/G: the ...` |
| `diagrams/monad-descent-axioms-tensor` | `\pic {object=diagrams/monad-descent-axioms-tensor}` | `The axioms of a descent datum (x, rho, delta) for the monad A (x) - of an algebra A: (1) rho is an A-module action (associativity), (2) its unit law, (3) delta is a morphism of A-modules, (4) ...` |
| `diagrams/monad-descent-axioms` | `\pic {object=diagrams/monad-descent-axioms}` | `The axioms of a descent datum (x, rho, delta) for a monad (M, mu, eta): (1) rho is an M-module action (associativity), (2) its unit law, (3) delta is a morphism of M-modules, (4) coassociativity of ...` |
| `dynkin-folding/A-to-C` | `\pic {object=dynkin-folding/A-to-C}` | `The folding A_{2n-1} -> C_n by the reflection of A_{2n-1} (the group S_2): the classical foldings of simply-laced Dynkin diagrams, table in the dissertation, ...` |
| `dynkin-folding/D-to-B` | `\pic {object=dynkin-folding/D-to-B}` | `The folding D_{n+1} -> B_n by the reflection of D_{n+1} swapping its two short arms (the group S_2): the classical foldings of simply-laced Dynkin diagrams, table in the dissertation, ...` |
| `dynkin-folding/D4-to-G2` | `\pic {object=dynkin-folding/D4-to-G2}` | `The folding D_4 -> G_2 by the rotation of D_4 by 2 pi / 3 (the group S_3): the classical foldings of simply-laced Dynkin diagrams, table in the dissertation, ...` |
| `dynkin-folding/E6-to-F4` | `\pic {object=dynkin-folding/E6-to-F4}` | `The folding E_6 -> F_4 by the reflection of E_6 (the group S_2): the classical foldings of simply-laced Dynkin diagrams, table in the dissertation, ...` |
| `ias/sterk3-ias` | `\pic {object=ias/sterk3-ias}` | `Gamma(X_0) = B_3(l) at Sterk cusp 3, l = (2,0^15,2,4,6,4,0,4) [AEGS Ex. 4.13, Fig. 13 left], drawn in the integral lattice of unit squares: R the triangulated region: the six unit squares of ...` |
| `ias/sterk3-kulikov` | `\pic {object=ias/sterk3-kulikov}` | `The Kulikov central fibre X_0 of B_3(l) at Sterk cusp 3, l = (2,0^15,2,4,6,4,0,4) [AEGS Ex. 4.13, Fig. 13 middle]: the dual complex of the triangulation of Gamma(X_0) (objects/ias/sterk3-ias, same ...` |
| `ias/symington-18-0-0` | `\pic {object=ias/symington-18-0-0}` | `The Symington polygon P(l) of the 0-cusp (18,0,0)_1 = U + E_8^2 of F_{(2,2,0)} [AEGS §4.2, Fig. 12], cut open along p_19 p_2: sides 2..18, and Symington surgeries with the roots 1 and 19 on the sides ...` |
| `ias/symington-18-2-0` | `\pic {object=ias/symington-18-2-0}` | `The Symington polygon P(l) of the 0-cusp (18,2,0)_1 = U(2) + E_8^2 of F_{(2,2,0)} [AEGS §4.2, Fig. 11 right]: sixteen sides in the directions of the moment polygon, and Symington surgeries with the ...` |
| `mirror-moves/coble` | `\pic {object=mirror-moves/coble}` | `The mirror moves (Alexeev-Engel 2022, Thm. 5.10) of the Coble lattice S_Co = (11,11,1)_1.` |
| `mirror-moves/enriques` | `\pic {object=mirror-moves/enriques}` | `The mirror moves (Alexeev-Engel 2022, Thm. 5.10) of the Enriques lattice S_En = (10,10,0)_1.` |
| `moduli/m2-coxeter` | `\pic {object=moduli/m2-coxeter}` | `The Coxeter diagram whose nonempty subdiagrams, up to its S_3 symmetry, index the strata of \overline{M}_2 (objects/moduli/m2-strata.json): stratum d = 2^k * 3^c is k of the three black vertices and ...` |
| `moduli/m2-curve-12` | `\pic {object=moduli/m2-curve-12}` | `A stable curve of the stratum d = 12 of \overline{M}_2 (Deligne-Mumford): one genus-1 vertex, one loop (Delta_0), 1 node.` |
| `moduli/m2-curve-2` | `\pic {object=moduli/m2-curve-2}` | `A stable curve of the stratum d = 2 of \overline{M}_2 (Deligne-Mumford): two genus-0 vertices, one edge, a loop at each (dumbbell), 3 nodes.` |
| `moduli/m2-curve-24` | `\pic {object=moduli/m2-curve-24}` | `A stable curve of the stratum d = 24 of \overline{M}_2 (Deligne-Mumford): one genus-2 vertex (smooth), 0 nodes.` |
| `moduli/m2-curve-3` | `\pic {object=moduli/m2-curve-3}` | `A stable curve of the stratum d = 3 of \overline{M}_2 (Deligne-Mumford): two genus-0 vertices, three edges (theta), 3 nodes.` |
| `moduli/m2-curve-4` | `\pic {object=moduli/m2-curve-4}` | `A stable curve of the stratum d = 4 of \overline{M}_2 (Deligne-Mumford): genus-1 vertex, edge, genus-0 vertex with a loop, 2 nodes.` |
| `moduli/m2-curve-6` | `\pic {object=moduli/m2-curve-6}` | `A stable curve of the stratum d = 6 of \overline{M}_2 (Deligne-Mumford): one genus-0 vertex, two loops, 2 nodes.` |
| `moduli/m2-curve-8` | `\pic {object=moduli/m2-curve-8}` | `A stable curve of the stratum d = 8 of \overline{M}_2 (Deligne-Mumford): two genus-1 vertices, one edge (Delta_1), 1 node.` |
| `moduli/m2-graph-12` | `\pic {object=moduli/m2-graph-12}` | `The stable graph of the stratum d = 12 of \overline{M}_2 (Deligne-Mumford): one genus-1 vertex, one loop (Delta_0), 1 node.` |
| `moduli/m2-graph-2` | `\pic {object=moduli/m2-graph-2}` | `The stable graph of the stratum d = 2 of \overline{M}_2 (Deligne-Mumford): two genus-0 vertices, one edge, a loop at each (dumbbell), 3 nodes.` |
| `moduli/m2-graph-24` | `\pic {object=moduli/m2-graph-24}` | `The stable graph of the stratum d = 24 of \overline{M}_2 (Deligne-Mumford): one genus-2 vertex (smooth), 0 nodes.` |
| `moduli/m2-graph-3` | `\pic {object=moduli/m2-graph-3}` | `The stable graph of the stratum d = 3 of \overline{M}_2 (Deligne-Mumford): two genus-0 vertices, three edges (theta), 3 nodes.` |
| `moduli/m2-graph-4` | `\pic {object=moduli/m2-graph-4}` | `The stable graph of the stratum d = 4 of \overline{M}_2 (Deligne-Mumford): genus-1 vertex, edge, genus-0 vertex with a loop, 2 nodes.` |
| `moduli/m2-graph-6` | `\pic {object=moduli/m2-graph-6}` | `The stable graph of the stratum d = 6 of \overline{M}_2 (Deligne-Mumford): one genus-0 vertex, two loops, 2 nodes.` |
| `moduli/m2-graph-8` | `\pic {object=moduli/m2-graph-8}` | `The stable graph of the stratum d = 8 of \overline{M}_2 (Deligne-Mumford): two genus-1 vertices, one edge (Delta_1), 1 node.` |
| `nikulin/two-elementary-table` | `\pic {object=nikulin/two-elementary-table}` | `Nikulin's table: the even hyperbolic 2-elementary lattices S of signature (1, r-1) that embed primitively in the K3 lattice II_{3,19}, by rank r, 2-rank a of the discriminant group A_S = (Z/2)^a, and ...` |
| `spaces/ball-1` | `\pic {object=spaces/ball-1}` | `The closed ball B^1 = [-1,1] with its boundary sphere S^0, drawn in dzg singular.` |
| `spaces/ball-2` | `\pic {object=spaces/ball-2}` | `The closed ball B^2, radius 1 about the origin, with its boundary sphere S^1 drawn in dzg singular.` |
| `spaces/ball-3` | `\pic {object=spaces/ball-3}` | `The closed ball B^3, radius 1 about the origin, with its boundary sphere S^2 drawn in dzg singular with the front halves of its equator and a meridian.` |
| `spaces/coffee-cup` | `\pic {object=spaces/coffee-cup}` | `A coffee cup, rim centred at the origin (rim radii 1 and 1/2).` |
| `spaces/cylinder` | `\pic {object=spaces/cylinder}` | `The cylinder S^1 x I: radius 3, height 4, centred at the origin.` |
| `spaces/mobius-band` | `\pic {object=spaces/mobius-band}` | `The Moebius band [0,2pi] x [-1/2,1/2] / (0,t) ~ (2pi,-t), embedded as ((1 + t/2 cos(s/2)) cos s, (1 + t/2 cos(s/2)) sin s, t/2 sin(s/2)), with its core circle t = 0; a pgfplots axis.` |
| `spaces/sphere-0` | `\pic {object=spaces/sphere-0}` | `The 0-sphere S^0 = {-1,1}, radius 1 about the origin.` |
| `spaces/sphere-1` | `\pic {object=spaces/sphere-1}` | `The unit circle S^1, radius 1 about the origin.` |
| `spaces/sphere-2` | `\pic {object=spaces/sphere-2}` | `The 2-sphere S^2, radius 1 about the origin, drawn with its equator and a meridian, back halves dashed.` |
| `spaces/torus-fundamental-square` | `\pic {object=spaces/torus-fundamental-square}` | `The fundamental square of the torus, word a b a^{-1} b^{-1}: the square [0,6]^2 with the horizontal sides glued (a, one arrow tip) and the vertical sides glued (b, two arrow tips).` |
| `spaces/torus` | `\pic {object=spaces/torus}` | `The torus T^2: outer radii 4 and 2, centred at the origin.` |
| `toric/fan-F2` | `\pic {object=toric/fan-F2}` | `The fan of the Hirzebruch surface F_2, the normal fan of the lattice quadrilateral P_{2,4} = conv{(0,0), (2,0), (4,1), (0,1)} [CLS Example 2.3.16]: rays rho_1..rho_4 = (1,0), (0,1), (-1,2), (0,-1) ...` |
| `toric/fan-P1` | `\pic {object=toric/fan-P1}` | `The fan of P^1 in N_R = R: sigma_0 = R_{>=0} = Cone(rho_0), sigma_1 = R_{<=0} = Cone(rho_1), the normal fan of an interval [CLS Example 2.4.10].` |

| Poset data | Written by | Description |
| --- | --- | --- |
| `m2-strata.json` | `figures/objects/moduli/m2-strata.sage` | `The stratification poset of \overline{M}_2 (Deligne-Mumford), by topological type; writes m2-strata.json for \posetfromjson. \overline{M}_2 has dimension 3 and seven strata, one for each stable ...` |
| `semitoroidal.json`, `toroidal.json` | `figures/objects/posets/compactifications-over-BB.sage` | `The compactifications of F_T over the Baily-Borel compactification, as two posets; writes semitoroidal.json and toroidal.json for \posetfromjson (figures/tikz/compactification_posets_over_BB.tex).` |
| `subdiagrams-C-L.json` | `figures/objects/posets/subdiagrams-C-L.sage` | `The poset of subdiagrams of the Coxeter diagram C(L) of the lattice with root Gram matrix G_L below, ordered by inclusion; writes subdiagrams-C-L.json for \posetfromjson ...` |

<!-- END GENERATED REFERENCE -->
