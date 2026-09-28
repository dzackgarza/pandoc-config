# Semantic macro audit

This is a working audit note, not a second macro authority. Canonical definitions remain
in `styles/macros/`.

## Repaired

- `\fiberprod{X}{S}{Y}`: complete fibre product `X \times_S Y`. The inherited legacy
  source already contained a one-argument `\times_S` fragment; the newer authored
  vocabulary/corpus establishes the intended three-argument semantic API.
- `\fprod`: no live call sites found; restored as a three-argument alias of
  `\fiberprod` rather than another symbol fragment.
- Zero-use power constructors `\disjointpower{X}{n}`, `\prodpower{X}{n}`,
  `\smashpower{X}{n}`, `\wedgepower{X}{n}`, `\tensorpowerk{X}{n}`, and
  `\fiberpower{X}{S}{n}` now include the powered object inside the macro boundary.
  `\fiberpower` uses the low-level `\fiberproduct{S}` glyph internally; it does not
  misuse the semantic three-argument `\fiberprod` object constructor.
- `\lktt{x}`: repaired the inherited literal `\1` typo to `L_{\mathrm{K3},x}`; the
  declared argument is now part of the object.
- `\GSpaces`: corrected to a zero-argument fixed-`G` alias. The neighboring
  `\gspaces{H}` remains the parameterized `H`-spaces constructor.

## Audit candidates requiring call-site-driven redesign

- Power/decorative family still requiring call-site migration or semantic recovery: `\cartpower`,
  `\sumpower`, `\tensorpower`, and `\derivedtensorpower`. Live authored source uses
  postfix forms such as `R\sumpower{n}` and `\mcl\tensorpower{}{n}`; these place the
  object outside the macro argument boundary and therefore violate the semantic API
  principle unless deliberately reclassified as private typography helpers.
- `\basechange`: current one-argument body is a fragment (`\times_k` followed by one
  operand) and has no live call sites found. Its intended semantic signature must be
  recovered before changing it.
- `\mix` and `\fiberproduct`: low-level decorated multiplication glyphs. Older/imported
  source still uses `\fiberproduct{S}` infix, so migration must be explicit rather than
  silently changing its arity.
- Ignored-argument definitions `\addbase[1]`, `\diagonal[1]`, and `\Diagonal[1]`
  still require individual semantic recovery.
- Slice/coslice suffix fragments (`\slice`, `\coslice`, `\liesover`, `\liesabove`)
  should be checked against authored usage to determine whether they are intended
  typography helpers or collapsed object/category constructors.

## Confirmed fragment-style public APIs

These are not speculative naming concerns: current authored call sites place the object
outside the macro and use the macro only as a suffix/infix decoration. Under the semantic
API rule, the public signatures should eventually become whole-object constructors.
They are not changed until their call sites are migrated atomically.

| Current form | Live authored surface observed | Proposed semantic form | Meaning |
| --- | ---: | --- | --- |
| `X\cartpower{n}` | 2 source call sites (plus generated copies) | `\cartpower{X}{n}` | `X^{\times n}` |
| `M\sumpower{n}` | many source call sites (35 incl. generated copies) | `\sumpower{M}{n}` | `M^{\oplus n}` |
| `M\tensorpower{R}{n}` | 3 source call sites (plus generated copies) | `\tensorpower{M}{R}{n}` | `M^{\otimes_R n}` |
| `R\adjoin{x}` | several source call sites (14 incl. generated copies) | `\adjoin{R}{x}` | `R[x]` |
| `R\localize{S}` | several source call sites (21 incl. generated copies) | `\localize{R}{S}` | `R[S^{-1}]` |
| `X\slice S` / `X\slice{S}` | broad use (53 incl. generated copies) | `\slice{X}{S}` | `X_{/S}` |

Related zero-use fragment helpers still unresolved (`\derivedtensorpower`,
`\basechange`, `\polynomialring`, `\functionfield`,
`\primelocalize`, `\complete`) should be recovered/redefined before new authored
uses are allowed. Their exact signatures should be chosen from mathematical semantics,
not by preserving the current detached glyph expansion.

The low-level `\fiberproduct{S}` helper is intentionally retained only as an internal/
legacy glyph primitive while old infix call sites are migrated. Public content should use
`\fiberprod{X}{S}{Y}`.

## Ignored-argument defects

A mechanical audit of the generated API finds three unresolved declarations still discard a declared argument: `\addbase[1]`,
`\diagonal[1]`, and `\Diagonal[1]`. None currently has a live authored call site in
the active corpus search. Historical sources do not establish a unique intended semantic
signature (`\diagonal` appears historically in both zero- and one-argument forms), so
these remain quarantined audit items rather than receiving invented semantics.
`\lktt` and `\GSpaces` were separately recoverable from neighboring definitions and
are repaired above.

## Ring/object constructor fragments

The same ambient-object-outside-the-macro defect occurs in the ring-construction family.
Current authored forms include `R\adjoin{x}`, `R\localize{S}`, and
`A(X)\invert{f}`. The complete semantic APIs should be of the form
`\adjoin{R}{x}`, `\localize{R}{S}`, and `\invert{R}{f}`. The power-series and
Laurent-series aliases (`\fps`, `\formalpowerseries`, `\powerseries`, `\fls`,
`\laurent`, `\laurentseries`, `\functionfield`) need the same ambient-ring/field
argument when promoted as public constructors. `\kx{n}` and `\freezmod{x}` are useful
counterexamples: they already include the ambient ring in the expansion and therefore
represent complete objects.

These used signatures are not changed independently of their source call sites. The
current corpus search found active `\adjoin`, `\localize`, and `\invert` usage, so this
is a coordinated migration, not a safe arity-only edit.

## Postfix semantic operators

A zero-argument postfix macro such as `V\dual` names a symbol, not the operation.
Each operation now has a one-argument operator in `tier2-mathjax-args.tex` that takes
the object it acts on. New authored text uses the operator. The postfix form is
deleted after its call sites are migrated.

Call-site counts are occurrences in `*.md` and `*.tex` under `~/notes`,
`~/gitclones` (excluding this repository), and `~/research`, excluding `archive/`
directories, on 2026-09-28. Duplicated source layers count separately.

| Postfix form | Operator | Meaning | Call sites |
| --- | --- | --- | ---: |
| `\mathcal{C}\op` | `\opcat{\mathcal{C}}` | opposite category | 486 |
| `V\dual` | `\dualof{V}` | dual | 5465 |
| — | `\doubledualof{V}` | double dual | — |
| `x\inv` | `\inverseof{x}` | inverse | 7741 |
| `R\units` | `\unitsof{R}` | group of units | 3255 |
| `R\nonzero` | `\nonzeroof{R}` | nonzero elements | 114 |
| `X\interior` | `\interiorof{X}` | interior | 96 |
| `k\sep` | `\sepclosure{k}` | separable closure | 382 |
| `K\tilt` | `\tiltof{K}` | tilt of a perfectoid field | 60 |
| `X\quillenplus` | `\plusconstruction{X}` | Quillen plus construction | 43 |
| `X\pcomplete` | `\completionat{X}{p}` | completion at `p` | 48 |
| `G\procomplete` | `\procompletion{G}` | pro-completion | 6 |
| `X\modiso` | `\isoclasses{X}` | isomorphism classes | few |

`\opp` (`^{\mathrm{op}}`, 11 call sites) and `\uopp` (`^{\rm opp}`) are not the
opposite category in their authored uses. In the dissertation notes, `P^\opp` is the
image of the polygon `P` under the involution `\iota` of `\IAS^2`. Those call sites
need an operator for that involution, not `\opcat`.

Unresolved: the zero-use functor decorations `\lshriek` (`{}_{!}`) and `\pushf`
(`{}^{*}`, a pullback despite its name), and the dissertation superscript and
subscript markers (`\uksba`, `\utor`, `\dnor`, `\lred`, `\usat`, ...).
