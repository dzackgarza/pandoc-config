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

Consolidated from `research/writing/Coble Paper Draft`, where they were the only
copies.
