# run_code.lua — executable code cells for Pandoc

`filters/run_code.lua` executes fenced code blocks at build time and embeds their
output back into the document. It turns a plain Pandoc pipeline into a lightweight
computational-document system (Sage/Lean/Python cells) without adopting a notebook
engine like Jupyter or knitr.

It follows the `tikzcd.lua` precedent already in this repo: intercept a block,
shell out to an external interpreter, cache by content hash, splice the result
back into the AST.

## Quick start

```bash
pandoc doc.md --lua-filter="$HOME/.pandoc/filters/run_code.lua" -o doc.html
```

````markdown
```{.python .run}
print("hello", 2 + 2)
```

```{.lean .run}
#eval (2 + 2 : Nat)
```
````

renders each source block followed by a `<div class="code-output">` holding its
captured output.

## Trigger

Execution is **opt-in**, so ordinary display-only code is never run. A code block
executes iff it carries the class `run` (or `silent`) **and** exactly one
registered language class:

| Fence | Behavior |
|---|---|
| `` ```{.python .run} `` | run; show source **and** output |
| `` ```{.lean .run} `` | run; show source **and** output |
| `` ```{.python .silent} `` | run for side effects; emit nothing (setup cells) |
| `` ```{.python} `` | untouched — ordinary highlighted source |
| `` ```{.python .run .bash} `` | untouched — ambiguous (two language classes) |

## Supported languages

| Class | Interpreter (default) | Temp ext |
|---|---|---|
| `python` | `python3` | `.py` |
| `bash` | `bash` | `.sh` |
| `sh` | `sh` | `.sh` |
| `lean` | `lake env lean` in the standard env (below) | `.lean` |

`sage` is **not** handled here — Sage cells are owned by the dedicated
`filters/sagemath-pandoc-filter` (panflute, runs under `sage --python`, renders
plots). Keep both filters in the chain if you use both.

## Lean: imports and the standard environment

Lean imports (`import Mathlib`, …) are resolved by **Lake via `LEAN_PATH`**, not by
the toolchain. There is no global "default imports" setting in Lean; the working
equivalent is a **prebuilt lake project** the filter runs cells inside.

- **Default env:** the research DSL-spike project
  `~/research/computations/experiments/lean_category_dsl_spike` — an already-built
  lake project (mathlib, batteries, aesop, Qq, ProofWidgets, Paperproof, …). Lean
  cells run as `lake env lean` from there, so they can import anything it depends
  on. Override with `RUN_CODE_LEAN_PROJECT`; a local project's own `lakefile`
  naturally takes precedence when you point the filter at it.
- **Default preamble:** `import Mathlib` is prepended to every Lean cell (not shown
  in the source), so cells skip import boilerplate. Disable with
  `RUN_CODE_LEAN_PREAMBLE=` (empty) or replace with any other text.
- **Toolchain:** dictated by Mathlib (currently `leanprover/lean4:v4.32.0`), set as
  the elan global default. Local `lean-toolchain` files still override per project.

> **Coupling note:** the default Lean env lives inside the `research` repo. If that
> experiment is removed, set `RUN_CODE_LEAN_PROJECT` to another built mathlib
> project or Lean cells will fail.

## Output structure

The original source block is kept (for display + syntax highlighting) and the
captured combined stdout/stderr is appended as a div:

```html
<div class="code-output"> … </div>   <!-- exit 0 -->
<div class="code-error"> … </div>    <!-- nonzero exit -->
```

Style these classes in your theme. `silent` cells produce neither the source nor
an output div.

## Errors

By default a failing cell renders its error inline as `.code-error` and the build
continues. Set `RUN_CODE_STRICT=1` to abort the whole build on any nonzero exit
instead.

## Caching

Results are cached by a SHA-1 of `(language, command, env dir, preamble, source)`
under `RUN_CODE_CACHE` (default `$PANDOC_DIR/figures/run-code-cache`). Unchanged
cells are not re-run. A changed cell, command, or preamble invalidates just that
entry.

**Persist this directory in CI** to avoid re-paying cold execution on every run.

## Timing (measured, this machine)

| Cell | Time |
|---|---|
| trivial Lean cell, cold | ~2.0s (per-cell `lake env lean` process spawn) |
| `import Mathlib` Lean cell, cold | ~8.6s |
| any cell, warm (cache hit) | ~0.5s (pandoc only; interpreter not invoked) |

Incremental rebuilds are effectively free — only changed cells re-run. Cold/CI
builds scale with the number of *unique* executed cells; cache the cache dir to
make that a one-time cost.

## Environment knobs

`<LANG>` is `PYTHON` | `LEAN` | `BASH` | `SH`.

| Variable | Effect |
|---|---|
| `RUN_CODE_<LANG>` | full interpreter-command override (escape hatch) |
| `RUN_CODE_<LANG>_PROJECT` | lake project dir; runs `lake env <cmd>` from that cwd so imports resolve |
| `RUN_CODE_<LANG>_PREAMBLE` | text prepended to each cell (not shown). Lean defaults to `import Mathlib`; set empty to disable |
| `RUN_CODE_CACHE` | cache directory (default `$PANDOC_DIR/figures/run-code-cache`) |
| `RUN_CODE_STRICT=1` | abort the build on any nonzero exit instead of rendering the error inline |
| `PANDOC_DIR` | filter home (default `$HOME/.pandoc`); only affects the default cache path |

## Tests

`tests/test_run_code.py` drives the real pandoc + filter path with `python3`
(always present) to prove routing, output embedding, `.silent`, display-only
pass-through, inline error rendering, and preamble injection. The Lean live test
runs only when a Lean toolchain is configured; otherwise it skips.

```bash
uv run --python 3.14 --with pytest pytest tests/test_run_code.py -q
```
