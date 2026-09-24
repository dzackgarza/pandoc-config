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

## Styles Architecture

The canonical LaTeX style definitions live in `styles/`:

- `styles/preambles/dzg-preamble.tex` -- the one place packages and TikZ libraries are
  loaded; every `.sty` entry point inputs it.
- `styles/macros/` -- the tiered math macros and domain macros.
- `styles/macros/tikz/tikzlibrarydzg.code.tex` -- the TikZ figure vocabulary, loaded by
  `\usetikzlibrary{dzg}` in the preamble. It defines one style per mathematical element
  (Coxeter vertices and edges by weight, Baily-Borel cusps, IAS singularities, lattice
  polygons, poset and degeneration arrows, stable-curve components), the colours, and the
  layer list.
- `styles/macros/tikz/constructors/` -- constructors that draw a mathematical object from
  its data, loaded by the library. The objects themselves are figures, one file each, in
  `figures/objects/<family>/`; a figure places one with `\pic {object=<family>/<name>}`.
- `styles/vendor/` -- third-party packages kept verbatim.

Figures use the library's style names and do not define their own styles, colours, or
layers. A figure that needs an element the library lacks adds it to the library.
