# LaTeX Macro Library Organization

**Location:** `~/.pandoc/styles/macros/`

This directory contains the organized LaTeX macro library, consolidated from scattered legacy files into a tier-based system.

## Tier System

### Tier 1: Simple MathJax-Compatible Shortcuts
**File:** `tier1-mathjax-simple.tex`

**Criteria:**
- `\newcommand` or `\DeclareMathOperator` with NO arguments
- Only uses MathJax-safe primitives: `\mathbb`, `\mathcal`, `\mathsf`, `\mathrm`, `\mathfrak`
- No `\makeatletter`, `\mathpalette`, or TeX programming constructs

**Examples:**
```latex
\newcommand{\ZZ}{\mathbb{Z}}
\newcommand{\QQ}{\mathbb{Q}}
\newcommand{\RR}{\mathbb{R}}
\newcommand{\CC}{\mathbb{C}}
\DeclareMathOperator{\Hom}{Hom}
\DeclareMathOperator{\Aut}{Aut}
```

**Works in:** LaTeX, Pandoc, Obsidian MathJax

### Tier 2: Commands with Arguments (MathJax-Compatible)
**File:** `tier2-mathjax-args.tex`

**Criteria:**
- `\newcommand` with 1-9 arguments
- Uses only MathJax-safe constructs: `\left`, `\right`, `\frac`, `\text`, basic math mode
- No spacing hacks (`\,`, `\!`, `\mkern`), no boxes, no `\mathchoice`

**Examples:**
```latex
\newcommand{\gens}[1]{\left\langle{#1}\right\rangle}
\newcommand{\abs}[1]{{\left\lvert #1 \right\rvert}}
\newcommand{\norm}[1]{{\left\lVert #1 \right\rVert}}
\newcommand{\dd}[2]{\frac{\partial #1}{\partial #2}}
```

**Works in:** LaTeX, Pandoc, Obsidian MathJax

### Semantic script notation

Choose the macro by the mathematical object it names. Each macro takes the
complete base as its argument.

| Meaning | Macro | Expansion |
| --- | --- | --- |
| Group of units | `\units{A}` | `A^{\times}` |
| Upper-indexed complex | `\chaincomplex{C}` | `C^{\bullet}` |
| Ascending filtration | `\ascendingfiltration{G}` | `G^{\bullet}` |
| Descending filtration | `\descendingfiltration{G}` | `G_{\bullet}` |
| Nonzero elements | `\nonzeroof{A}` | `A^{\bullet}` |
| Dual | `\dualof{V}` | `V^{\vee}` |

Flowmark's `math/script-macro-candidates` rule uses the loaded macro definitions
to suggest these meanings for manual symbolic scripts, including alternate
glyphs. A suggestion requires the author to select the intended meaning.

### Tier 3: Complex TeX-Specific Commands
**File:** `tier3-tex-complex.tex`

**Criteria:**
- Uses TeX primitives not in MathJax: `\mathpalette`, `\ooalign`, `\mathchoice`
- Spacing/kerning hacks: `\mkern`, `\mskip`, `\phantom`
- Box manipulation: `\hbox`, `\vbox`, `\rlap`, `\llap`
- `\makeatletter` ... `\makeatother` blocks

**Examples:**
```latex
\makeatletter
\newcommand{\superimpose}[2]{{\ooalign{$#1$\cr\hfil$#2$\hfil\cr}}}
\makeatother
```

**Works in:** LaTeX, Pandoc only (NOT Obsidian MathJax)

### Tier 4: Preamble Content (Package Loading & Document Setup)
**File:** `tier4-preamble.tex`

**Criteria:**
- `\usepackage` statements
- `\setkomafont`, `\addtokomafont`, page geometry
- `\hypersetup`, `\definecolor`, global theorem styles
- Anything that configures document-level behavior

**Examples:**
```latex
\usepackage{amsmath,amsthm,amssymb}
\usepackage{tikz-cd}
\usetikzlibrary{arrows,positioning}
\hypersetup{colorlinks=true, linkcolor=blue}
```

**Works in:** LaTeX, Pandoc only (document-level configuration)

## Domain-Specific Files

**`categories.tex`:**
- Category theory macros (from `latexmacs_categories.tex`)
- Organized internally by tier (tier 1 shortcuts, tier 2 commands, tier 3 complex)
- Clear section headers for each tier

**`spectral.tex`:**
- Spectral sequence macros (from `latexmacs_spectra.tex`)
- Same internal tier organization

**`tikz.tex`:**
- Consolidated TikZ styles, node definitions, edge styles
- Merged from `tikz_macros.tex` + `tikzmacros.tex` + `Tikz_Macros.tex`
- Inherently tier 3 (LaTeX-only)

**`environments.tex`:**
- Preserved from `macros/environments.tex`
- Theorem environment styling with tcolorbox
- Tier 4 content (document-level setup)

## Semantic API rule

The macro library encodes mathematical objects and constructions as an authoring API.
Public construction macros are therefore atomic: they take all semantic operands as
arguments and render the whole object. They are not aliases for a single symbol which
expects neighboring TeX to complete the expression.

Canonical example, which renders $X \times_S Y$:

```latex
\fiberprod{X}{S}{Y}
```

A definition such as `\fiberprod{S} -> \times_S` is invalid even if it can be used
infix, because it loses the operands from the macro's semantic boundary. The same review
criterion applies to tensor/cartesian/direct-sum powers, base change, quotient,
localization, completion, and related constructions. Existing fragment-style macros are
to be audited from authored call sites before their signatures are changed.

Generated MathJax JSON/JS/HTML files are projections of this canonical API. Never edit
or independently override their macro semantics.

## The MathJax projection

- `mathjax-sources.txt` names the files that feed MathJax. The generator
  (`bin/generate-mathjax-config.py`) and the bundled extractor of the site read
  the same manifest, so the two consumers agree.
- The generator writes `templates/css/mathjax-macros.{json,mjs,ts,html}`,
  `templates/css/math-macros.{html,md}` and the one `macros: {...},` line of
  `templates/mathjax-config.html` and `templates/pandoc_revealjs_template.html`.
  Do not edit these outputs; run `just generate-math-macros`. A template with no
  such line or with more than one stops the generator.
- **The generator projects each definition or stops.** It parses each file
  of the manifest with pylatexenc and gives MathJax the LaTeX meaning of:
  - `\newcommand`, `\renewcommand`, `\providecommand`, with an optional
    default (`\newcommand{\x}[2][d]{...}` gives `["...", 2, "d"]`);
  - `\def` with the parameter text `#1#2...#n` and nothing else;
  - `\DeclareMathOperator` (`\operatorname`) and its star form
    (`\operatorname*`);
  - `\DeclarePairedDelimiter{\x}{L}{R}`, as `\mathopen{L}#1\mathclose{R}`
    in the macro map: the form of mathtools without a star and without a
    size. The generator also writes the pair `["L", "R"]` into
    `templates/css/mathjax-paired-delimiters.json` and into the generated
    `pairedDelimiters` line of `templates/mathjax-config.html` and
    `templates/pandoc_revealjs_template.html`. That is the option
    `tex.mathtools.pairedDelimiters` of MathJax mathtools, which takes
    precedence over the macro map and gives the three forms of LaTeX: `\x`
    without scaling, `\x*` with `\left` and `\right`, and `\x[\big]`
    with `\bigl` and `\bigr`. A consumer of the macro map without that
    option (a `\newcommand` include, the texmath reader of `math-macros.md`)
    has only the form without a star; `\x*` and `\x[\big]` are then
    errors;
  - `\let\x\relax`, which defines nothing.

  Each other definition (`\gdef`, `\edef`, `\xdef`, another `\let`, a `\def`
  with a delimited parameter text, `\DeclareRobustCommand`, the xparse
  commands, `\DeclarePairedDelimiterX`, `\DeclareMathSymbol`,
  `\mathchardef`, `\chardef`) stops the generator with its file, its line
  and its name. A definition between `\makeatletter` and `\makeatother`
  can have `@` in its name.
- `bin/generate-readme-reference.py` lists the definitions of each macro
  file with the same parser, also of the files outside the manifest.
- A tier 1 or tier 2 expansion uses only commands that MathJax defines with
  the packages that the configuration loads: the default set, `mathtools`,
  `centernot` and `stmaryrd` (`templates/js/mathjax-stmaryrd.js`: `\llbracket`,
  `\rrbracket`, `\mapsfrom`, `\lightning`). MathJax shows an unknown command in
  red and raises no error, so `tests/test-mathjax-macros.ts` typesets each macro
  and fails on each such command.
- `templates/css/mathjax-macros.html` is the include for a host that loads
  MathJax itself (Quarto). The host loads MathJax 4 and registers
  `templates/js/mathjax-stmaryrd.js` before typesetting; without it `\fps`
  does not render.

## Rules of particular definitions

- **One macro per meaning.** Letters with several meanings get one macro for
  each meaning, so each meaning keeps one display choice. The same holds for
  the macros that display as a pair of bars.
- **A native command keeps its definition**, except for the overrides of
  the section "Overrides". The tree does not redefine
  `\boldsymbol` (bm.sty makes it `\bm` in LaTeX; MathJax renders its own),
  `\det`, `\mod` (amsmath and MathJax: `\mod{m}`, one argument) or `\mid`
  (`\st` is the big-bar "such that"). A `tex.macros` entry for such a
  command would replace the native one; the generator test asserts that
  the projection has none.
- **`\qed`** is the command of amsthm. Tier 3 sets its symbol,
  `\qedsymbol`, to `\blacksquare` in `\ensuremath`, as amsthm sets the
  symbol in text mode. In math mode amsthm gives `\quad\qedsymbol`
  (`\mathqed`). MathJax has no `\qed`; the generator's shim gives
  `\quad\blacksquare`.
- **`\coloneqq`** is `\vcentcolon\mathrel{\mkern-1.2mu}=` in mathtools.
  MathJax mathtools has a `\coloneqq` of its own (one `:=` relation), and no
  `\vcentcolon`. The generator's shims give `\coloneqq` the definition of
  mathtools and `\vcentcolon` the colon of MathJax mathtools that is
  centred on the math axis (`\vcentercolon`). A `\mathop` round a colon,
  as mathtools centres it in TeX, does not centre it in MathJax.
- **`\qty{X}` is `\left( X \right)`**: parentheses that always grow with
  `X`. It is a `\newcommand`, not a `\DeclarePairedDelimiter`: a paired
  delimiter of mathtools without a star never grows.
- **The shims are tested against the PDF.**
  `tests/test-mathjax-generator.py` gives each shim, `\qty`, each macro
  that uses `\qty` and each form of `\ceil` with its LaTeX meaning to
  pdflatex and to MathJax, and requires the same page in each engine.
- **`\fls`** builds the Laurent series delimiter: no font has a stretchy double
  parenthesis, so each outer parenthesis is a `\left` delimiter sized to a
  `\vphantom` of the argument, and a 5mu kern overlaps the pair.
- **`\fiberprod{X}{S}{Y}`** is the semantic constructor of $X \times_S Y$.
  `\fiberproduct` is the low-level glyph helper of older sources.
- `\mappingclassgroup{X}` is the complete object $\operatorname{MCG}(X)$;
  the opposite and unary operations take the object that they act on.
- `\RN` and `\RM` use the TeX primitive `\romannumeral`, so they are tier 3.
  `\envlist` pulls a list up to the line of the environment heading before it.

## Overrides

Tier 3 loads after tier 2 and redefines some tier 2 macros with a
LaTeX-only form: the double cosets (`\dcoset`, `\dcosetl`, `\dcosetr`,
`\leftquotient`: `\scalebox` in LaTeX, natural-size `\diagdown`/`\diagup` in
MathJax), `\gitquot` (`\mkern` in LaTeX) and `\righttriplearrows` (a TikZ
drawing in LaTeX, a `\substack` of three arrows in MathJax).

The tree also overrides native commands of LaTeX, its packages and
MathJax 4. Each name is one of the most-used names of the authoring
language, so the tree keeps it (#26, #27). The column "Overrides in" names
each renderer whose native command the macro replaces.

| Command | Overrides in | Native meaning | Macro meaning | Expansion |
| --- | --- | --- | --- | --- |
| `\AA` | LaTeX, MathJax | Å, a text command of LaTeX; MathJax gives Å (U+212B) in math | affine space | `{\mathbf{A}}` |
| `\SS` | LaTeX | "SS", the capital of ß, a text command of LaTeX | sphere, as `\sphere` | `{\mathbb{S}}` |
| `\ae` | LaTeX | the æ ligature, a text command of LaTeX | "almost everywhere" | `{ \text{a.e.} }` |
| `\vector` | LaTeX | `\vector(x,y){l}`, the arrow of the `picture` environment of LaTeX | a vector | `\vector{v}` gives `\mathbf{v}` |
| `\hyp` | LaTeX | the breakable hyphen of hyphenat, which dzg-unified loads | the operator "hyp" | `{\operatorname{hyp}}` |
| `\U` | MathJax | `\U{hex}`, the Unicode character of the code point `hex`; LaTeX has no `\U` | the operator "U" | `{\operatorname{U}}` |
| `\Bbb` | MathJax | `\mathbb`; amsfonts gives the same `\Bbb` in LaTeX | `\mathbb` | `\mathbb` |

- A document that loads the tree does not have the native command: no Å
  or æ from `\AA` or `\ae`, no "SS" from `\SS`, no `picture` arrow, no
  breakable hyphen from `\hyp`. Write the character itself (Å, æ), or use
  another command for the arrow or the hyphen.
- In math, the PDF and MathJax agree on each row: the projection has the
  expansion of the table, so MathJax uses it in place of its own `\AA`,
  `\U` and `\Bbb`, and LaTeX has no math meaning for `\SS`, `\ae`,
  `\vector` and `\hyp`. Without its entry, `\U` in MathJax takes the next
  group as a code point: `\U{0041}` gives "A" where the PDF gives the
  operator U and the group 0041.
- `\Bbb` changes no MathJax output: MathJax gives the same MathML for
  `\Bbb{R}`, `\Bbb R`, `\Bbb{ZQ}` and `\Bbb{R}^n_{+}` with and without the
  entry, and in LaTeX `\providecommand` keeps the `\Bbb` of amsfonts. The
  macro stays because `templates/css/math-macros.md` is made from the same
  tree: texmath, which converts the math of each other Pandoc writer, has
  no `\Bbb`, and without the definition Pandoc keeps the TeX of `\Bbb{R}`
  in place of the double-struck R.
- `tests/test-mathjax-generator.py` reads the first two columns of this
  table. It finds each macro of the projection that changes the meaning of
  a command that the document has where dzg-macros loads (amsart,
  dzg-unified), and each macro of the projection whose name MathJax 4 of
  `node_modules` defines with the configuration of the preview template
  (`tests/mathjax-native-commands.ts`). For each renderer it fails when
  that set and the rows that name the renderer differ. A new override of a
  native command therefore fails the test until a row of this table
  declares it.

## Adding New Macros

### Decision Tree

```
Does it load packages or configure document? → Tier 4 (tier4-preamble.tex)
Does it use TeX primitives (\mathpalette, boxes)? → Tier 3 (tier3-tex-complex.tex)
Does it take arguments? → Tier 2 (tier2-mathjax-args.tex)
Is it a simple shortcut? → Tier 1 (tier1-mathjax-simple.tex)
Is it domain-specific? → categories.tex, spectral.tex, or tikz.tex
```

### Organization Guidelines

1. **Determine tier** using decision tree above
2. **Add to appropriate file:**
   - General macros: tier1/tier2/tier3/tier4 files
   - Category theory: `categories.tex`
   - Spectral sequences: `spectral.tex`
   - TikZ content: `tikz.tex`
3. **Organize within file:** group by topic, then sort by command name. The
   macro files hold no TeX comments; a reason for a definition goes in
   "Rules of particular definitions" below.
4. **MathJax compatibility:**
   - If MathJax-safe, it auto-loads in Obsidian on reload
   - The generated MathJax config reads `tier1-mathjax-simple.tex`, `tier2-mathjax-args.tex`, `categories.tex`, and `spectral.tex`
   - Tiers 3-4 are LaTeX/Pandoc only

## Migration History

**Migrated from** `macros/` directory on 2025-01-09

**Source files consolidated:**
- `latexmacs.tex` (980 lines) → tier files
- `latexmacs_categories.tex` (267 lines) → `categories.tex`
- `latexmacs_spectra.tex` (41 lines) → `spectral.tex`
- `latexmacs_commands.tex` (150 lines) → tier files
- `tikz_macros.tex` + `tikzmacros.tex` → `tikz.tex`
- `environments.tex` → `environments.tex` (preserved as-is)

**Legacy files archived to:** `archive/legacy-macros-2025-01-09/`

## Usage

### In LaTeX/Pandoc Documents

Load all macros via unified style:
```latex
\usepackage{dzg-unified}
```

### In Obsidian

The maximal MathJax-safe subset loads automatically via symlinked `mathjax-macros.tex` in `.obsidian/` directory.

See `obsidian/README.md` for setup instructions.
