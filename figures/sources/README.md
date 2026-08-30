# Native authored sources

Editable originals behind rendered figures, kept so that a figure can be
*revised* rather than only reused. Nothing here is consumed by the pandoc build
(`figures/tikz`, `figures/tikzcd`, `figures/vector` are); these are the upstream
files an author opens to change a picture.

| file | tool | renders to |
| --- | --- | --- |
| `triangulated_sphere.blend` | Blender | the triangulated-sphere figures (`triangulated_sphere_fan`) |
| `Sterk2-ias-bigger.ggb` | GeoGebra | the Sterk-2 integral affine structure |
| `sterk2_ias2_template.tikz` | TikZ | drawing template for the Sterk-2 IAS2 diagrams |
| `sterk_ias_export.svg`, `sterk_ias_export_v2.svg` | Inkscape/GeoGebra export | intermediate exports of the same IAS |
| `nikulin_diagram_axes_scaffold.tikz` | pgfplots | the empty 22x11 axis grid the Nikulin 2-elementary diagram is drawn on |
| `tikzit-coble-palette.sty` | TikZiT | the node/edge palette (`black node`, `white node`, `doubled node`, `starred node`, `double edge`, …) the Coble TikZ figures were drawn against; needed to reopen them in TikZiT |

Consolidated from `research/writing/Coble Paper Draft`, where they were the only
copies.

The repository also owns the imported TikZ source trees in
`figures/tikz/dissertation/`, `figures/tikz/uga-dissertation-template/`,
`figures/tikz/visualizations/`, `figures/tikz/obsidian/`, and
`figures/tikz/legacy/`. The repository also owns the archived extracted figure
assets in `figures/rendered/legacy/v4-best-candidates/`. The original paths in
the notes, archive, and dissertation repositories are symlinks to these
directories, so existing documents keep their relative `\input` paths while the
editable sources have one canonical owner.

Standalone TikZ documents imported from the Notes and dissertation repositories
live in `figures/tikz/visualizations/standalone/` and
`figures/tikz/legacy/standalone/`. Obsidian diagram sidecars live in
`figures/tikz/obsidian/`; archived raw sources live in
`figures/tikz/legacy/unique-diagrams/` and `figures/tikz/legacy/v4-originals/`.
The Algebra II standalone figures live in `figures/tikz/legacy/algebra-franke/`.
Their original paths remain symlinks.
