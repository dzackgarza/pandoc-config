#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Generate MathJax 3 macro configuration (JS/TS) from compatible LaTeX macro files.

Reads the canonical MathJax-compatible macro sources, parses \\newcommand /
\\def / \\DeclareMathOperator / \\DeclarePairedDelimiter definitions, and
outputs:

  - A JavaScript ESM module exporting a { macros } object
  - A TypeScript module exporting the same with type annotations
  - A JSON file for direct embedding in HTML

MathJax 3 tex.macros format:
  - Zero-arg macros:  "MacroName": "replacement"
  - N-arg macros:     "MacroName": ["replacement with #1..#n", N]
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parent.parent
MACRO_DIR = REPO_ROOT / "styles" / "macros"
# Single source of truth for *which* macro files feed MathJax. Source filenames
# are NOT hard-coded here — they are declared in the manifest, shared verbatim
# with the SSG's bundled extractor so both consumers stay in lock-step.
MACRO_MANIFEST = MACRO_DIR / "mathjax-sources.txt"
OUT_DIR = REPO_ROOT / "templates" / "css"
# The MathJax configuration of each HTML template except reveal.js: a Pandoc
# partial that the template of each such writer includes, so the macro map
# has one copy for all of them.
MATHJAX_CONFIG_PARTIAL = REPO_ROOT / "templates" / "mathjax-config.html"
REVEALJS_TEMPLATE = REPO_ROOT / "templates" / "pandoc_revealjs_template.html"


class MacroDef(NamedTuple):
    name: str
    arg_count: int
    body: str


MATHJAX_SHIMS = (
    MacroDef("coloneqq", 0, r"\mathrel{\vcenter{:}}="),
    MacroDef("qty", 1, r"\left( {#1} \right)"),
    MacroDef("qed", 0, r"\blacksquare"),
)


# Pattern to locate the start of any macro definition command
DEF_CMD_RE = re.compile(
    r"""
    \\
    (?:newcommand|renewcommand|providecommand
      |DeclareMathOperator|DeclarePairedDelimiter
      |def
    )\*?
    """,
    re.VERBOSE | re.DOTALL,
)

# Lines that are pure comments or empty
_COMMENT_OR_EMPTY = re.compile(r"^\s*(%.*|\s*)$")

# Lines to exclude entirely (preamble boilerplate)
_EXCLUDE_STARTSWITH = (
    "\\NeedsTeXFormat",
    "\\ProvidesPackage",
    "\\usepackage",
    "\\makeatletter",
    "\\makeatother",
    "\\endinput",
)

# Lines to exclude entirely (not macros, or problematic for MathJax)
EXCLUDE_LINES_STARTSWITH = (
    "\\NeedsTeXFormat",
    "\\ProvidesPackage",
    "\\usepackage",
    "\\makeatletter",
    "\\makeatother",
    "\\endinput",
    "\\input{",
)

# Lines that are pure comments or empty
COMMENT_OR_EMPTY = re.compile(r"^\s*(%.*|\s*)$")

# \DeclareMathOperator{{\mathbb{L} }} -> this produces an arg-count issue;
# DeclareMathOperator always wraps in \operatorname{}
DECLARE_MATH_OP_RE = re.compile(
    r"\\DeclareMathOperator\*?\s*\{\s*\\([a-zA-Z@]+)\s*\}\s*\{(.*)\}",
    re.DOTALL,
)


def _strip_comments_and_boilerplate(content: str) -> str:
    """Remove comment-only lines and preamble boilerplate."""
    lines: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if _COMMENT_OR_EMPTY.match(stripped):
            continue
        if stripped.startswith(_EXCLUDE_STARTSWITH):
            continue
        lines.append(line)
    return "\n".join(lines)


def _merge_continuations(raw: str) -> str:
    """Merge lines that end with a trailing % (continuation marker)."""
    lines = raw.splitlines()
    merged: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.rstrip().endswith("%") and i + 1 < len(lines):
            line = line.rstrip()[:-1]  # strip trailing %
            i += 1
            line += " " + lines[i].lstrip()
        merged.append(line)
        i += 1
    return "\n".join(merged)


def _skip_ws(raw: str, pos: int) -> int:
    """Skip whitespace, return new position."""
    while pos < len(raw) and raw[pos] in " \t\n\r":
        pos += 1
    return pos


def _extract_balanced_group(raw: str, pos: int) -> tuple[str, int]:
    """Extract balanced-brace group starting at raw[pos].  raw[pos] must be '{'.
    Returns (inner_content, position_after_closing_brace).
    """
    assert pos < len(raw) and raw[pos] == "{", (
        f"expected '{{' at pos {pos}, got {raw[pos : pos + 10]!r}"
    )
    depth = 0
    start = pos
    while pos < len(raw):
        ch = raw[pos]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return raw[start + 1 : pos], pos + 1
        elif ch == "\\":
            pos += 1  # skip next char (escaped brace)
        pos += 1
    return raw[start + 1 : pos], pos


def _extract_name(raw: str, pos: int) -> tuple[str, int]:
    """Extract macro name from raw[pos:].  Returns (name, new_position)."""
    pos = _skip_ws(raw, pos)
    if pos >= len(raw):
        return "", pos
    if raw[pos] == "{" and pos + 1 < len(raw) and raw[pos + 1] == "\\":
        # {\name} form
        inner, after = _extract_balanced_group(raw, pos)
        assert inner.startswith("\\"), f"expected \\ name in braces, got {inner!r}"
        return inner[1:], after
    if raw[pos] == "\\":
        # \name form
        end = pos + 1
        while end < len(raw) and raw[end].isalpha():
            end += 1
        return raw[pos + 1 : end], end
    return "", pos


def _extract_opt_arg_count(raw: str, pos: int) -> tuple[int, int]:
    """Extract optional [N] arg count. Returns (N, new_position)."""
    pos = _skip_ws(raw, pos)
    if pos < len(raw) and raw[pos] == "[":
        close = raw.find("]", pos)
        if close != -1:
            try:
                n = int(raw[pos + 1 : close])
                return n, close + 1
            except ValueError:
                pass
    return 0, pos


def _extract_body(raw: str, pos: int) -> tuple[str, int]:
    """Extract body from raw[pos:]. raw[pos] must start with '{'.
    Returns (body_text, position_after_closing_brace)."""
    pos = _skip_ws(raw, pos)
    if pos >= len(raw) or raw[pos] != "{":
        return "", pos
    return _extract_balanced_group(raw, pos)


def parse_macros(content: str) -> list[MacroDef]:
    """Parse all \\newcommand, \\def, \\DeclareMathOperator definitions."""
    text = _strip_comments_and_boilerplate(content)
    text = _merge_continuations(text)

    macros: list[MacroDef] = []
    pos = 0

    while True:
        m = DEF_CMD_RE.search(text, pos)
        if not m:
            break

        cmd = m.group(0).lstrip("\\").rstrip("*")
        pos = m.end()
        pos = _skip_ws(text, pos)

        # --- DeclarePairedDelimiter: skip it (not directly usable in MathJax) ---
        if "DeclarePairedDelimiter" in cmd:
            # Consume name, left, right groups and skip
            name, pos = _extract_name(text, pos)
            _body, pos = _extract_body(text, pos)
            _body, pos = _extract_body(text, pos)
            continue

        # --- Extract macro name ---
        name, pos = _extract_name(text, pos)
        if not name:
            continue

        # --- Extract optional arg count ---
        arg_count, pos = _extract_opt_arg_count(text, pos)

        # --- Extract body ---
        body, pos = _extract_body(text, pos)
        body = body.strip()

        if not body:
            continue

        # --- Special handling ---
        if "DeclareMathOperator" in cmd:
            body = f"\\operatorname{{{body}}}"
            arg_count = 0

        macros.append(MacroDef(name=name, arg_count=arg_count, body=body))

    return macros


def _relative_source_lines(source_files: tuple[Path, ...]) -> str:
    return "\n".join(f" *   {path.relative_to(REPO_ROOT)}" for path in source_files)


def _unique_macros(macros: list[MacroDef]) -> list[MacroDef]:
    """Keep LaTeX-style first definitions when later aux files use providecommand."""
    seen: set[str] = set()
    unique: list[MacroDef] = []
    for macro in macros:
        if macro.name in seen:
            continue
        seen.add(macro.name)
        unique.append(macro)
    return unique


def _read_manifest(manifest_path: Path) -> tuple[Path, ...]:
    """Resolve the macro source files declared in the manifest (one path per
    line, relative to the manifest's directory; '#'-comments and blanks ignored).
    A missing manifest or listed file is a hard error — never a silent skip."""
    if not manifest_path.exists():
        print(f"ERROR: macro manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)
    base = manifest_path.parent
    files: list[Path] = []
    for line in manifest_path.read_text().splitlines():
        stripped = line.strip()
        if stripped == "" or stripped.startswith("#"):
            continue
        resolved = (base / stripped).resolve()
        if not resolved.exists():
            print(
                f"ERROR: macro file listed in {manifest_path.name} not found: {resolved}",
                file=sys.stderr,
            )
            sys.exit(1)
        files.append(resolved)
    if not files:
        print(f"ERROR: manifest declares no macro files: {manifest_path}", file=sys.stderr)
        sys.exit(1)
    return tuple(files)


def _read_macros(source_files: tuple[Path, ...]) -> list[MacroDef]:
    macros: list[MacroDef] = list(MATHJAX_SHIMS)
    for source_file in source_files:
        macros.extend(parse_macros(_read_file(source_file)))
    return _unique_macros(macros)


def _esm_header(source_files: tuple[Path, ...]) -> str:
    return """\
/**
 * MathJax 3 macro configuration — generated by bin/generate-mathjax-config.py.
 *
 * DO NOT EDIT MANUALLY.  Source of truth:
""" + _relative_source_lines(source_files) + "\n" + """\
 *
 * Usage (ESM):
 *   import { macros } from "./mathjax-macros.mjs";
 *   MathJax = { tex: { macros } };
 *
 * Usage (MathJax HTML config):
 *   <script>
 *     window.MathJax = {
 *       tex: { macros: { ... } }
 *     };
 *   </script>
 */

"""


def _ts_header(source_files: tuple[Path, ...]) -> str:
    return """\
/**
 * MathJax 3 macro configuration — generated by bin/generate-mathjax-config.py.
 *
 * DO NOT EDIT MANUALLY.  Source of truth:
""" + _relative_source_lines(source_files) + "\n" + """\
 *
 * Usage:
 *   import { macros } from "./mathjax-macros";
 *   MathJax = { tex: { macros } };
 */

/** A zero-argument macro replacement. */
type ZeroArgMacro = string;

/** A macro with N arguments. */
type NArgMacro = [replacement: string, argCount: number];

/** MathJax 3 tex.macros configuration. */
export const macros: Record<string, ZeroArgMacro | NArgMacro> = {
"""


def _read_file(path: Path) -> str:
    if not path.exists():
        print(f"ERROR: source file not found: {path}", file=sys.stderr)
        sys.exit(1)
    return path.read_text()


def _escape_for_js(body: str) -> str:
    """Make a LaTeX body safe to embed in a JavaScript string literal.

    - Double all backslashes
    - Escape newlines and other control characters via \\n, \\t, etc.
    - Other chars that break JS string literals get \\uXXXX encoding
    """
    body = body.replace("\\", "\\\\")
    # Escape literal newlines (from multiline \\def bodies)
    body = body.replace("\n", "\\n")
    body = body.replace("\r", "\\r")
    body = body.replace("\t", "\\t")
    return body


def _format_0arg(body: str) -> str:
    """Format a zero-arg macro as a JS string."""
    return f'"{_escape_for_js(body)}"'


def _format_narg(body: str, n: int) -> str:
    """Format an N-arg macro as a JS tuple [body, n]."""
    return f'["{_escape_for_js(body)}", {n}]'


def generate_js(macros: list[MacroDef], source_files: tuple[Path, ...]) -> str:
    """Generate JavaScript ESM module content."""
    lines: list[str] = [_esm_header(source_files), "export const macros = {"]

    for m in macros:
        if m.arg_count == 0:
            lines.append(f'  "{m.name}": {_format_0arg(m.body)},')
        else:
            lines.append(f'  "{m.name}": {_format_narg(m.body, m.arg_count)},')

    lines.append("};")
    lines.append("")  # trailing newline
    return "\n".join(lines)


def generate_ts(macros: list[MacroDef], source_files: tuple[Path, ...]) -> str:
    """Generate TypeScript module content."""
    lines: list[str] = [_ts_header(source_files)]

    for m in macros:
        if m.arg_count == 0:
            lines.append(f'  "{m.name}": {_format_0arg(m.body)},')
        else:
            lines.append(f'  "{m.name}": {_format_narg(m.body, m.arg_count)},')

    lines.append("};\n")
    return "\n".join(lines)


def generate_json(macros: list[MacroDef]) -> str:
    """Generate JSON for embedding in HTML.
    json.dumps handles backslash escaping, so we pass raw LaTeX bodies.
    """
    return json.dumps(_macro_object(macros), indent=2)


def _macro_object(macros: list[MacroDef]) -> dict[str, str | list]:
    """Return the canonical MathJax ``tex.macros`` object."""
    obj: dict[str, str | list] = {}
    for m in macros:
        obj[m.name] = m.body if m.arg_count == 0 else [m.body, m.arg_count]
    return obj


class GeneratedTemplate(NamedTuple):
    """A Pandoc template that holds a generated ``macros: {...},`` line.

    The markers are text of the language at their place in the template: an
    HTML comment in the head of a page, a JavaScript comment inside a script.
    """

    path: Path
    start_marker: str
    end_marker: str


HTML_MARKERS = ("<!--MATHJAX_MACROS_START-->", "<!--MATHJAX_MACROS_END-->")
SCRIPT_MARKERS = ("/* MATHJAX_MACROS_START */", "/* MATHJAX_MACROS_END */")

# Each template whose MathJax configuration takes its macros from this
# generator. A template that is not listed here must not hold a macro map.
GENERATED_TEMPLATES = (
    GeneratedTemplate(MATHJAX_CONFIG_PARTIAL, *HTML_MARKERS),
    GeneratedTemplate(REVEALJS_TEMPLATE, *SCRIPT_MARKERS),
)


def update_template_macros(template: GeneratedTemplate, macros: list[MacroDef]) -> None:
    """Replace the generated macro map inside a template.

    The surrounding MathJax configuration is hand-owned by the template; only
    the ``macros: {...},`` line between the explicit generation markers is a
    derivative of ``styles/macros``. Keeping this in the same generator as the
    JSON/JS outputs prevents a template from becoming a second macro authority.
    """
    template_path = template.path
    start_marker = template.start_marker
    end_marker = template.end_marker
    text = template_path.read_text()
    start = text.find(start_marker)
    end = text.find(end_marker, start + len(start_marker))
    if start < 0 or end < 0:
        raise RuntimeError(
            f"Template {template_path} is missing the MathJax generation markers"
        )

    section = text[start:end]
    replacement = json.dumps(_macro_object(macros), separators=(",", ":"))
    section, count = re.subn(
        # The space after the comma is of that line only: the line can be
        # the last one before the end marker.
        r"(?m)^(\s*macros:\s*)\{.*\},[^\S\n]*$",
        lambda match: f"{match.group(1)}{replacement},",
        section,
        count=1,
    )
    if count != 1:
        raise RuntimeError(
            f"Template {template_path} must contain exactly one generated macros line"
        )
    template_path.write_text(text[:start] + section + text[end:])


def generate_legacy_html(macros: list[MacroDef], source_files: tuple[Path, ...]) -> str:
    """Generate raw MathJax TeX definitions for the legacy HTML template.

    ``research_draft.html`` wraps this file in a MathJax delimiter. It is a
    projection of the same parsed macro API as every other target; it must not
    be built by separately concatenating source files.
    """
    lines: list[str] = [
        "% Generated by bin/generate-mathjax-config.py; DO NOT EDIT.",
        "% Source of truth:",
        *[f"%   {line.removeprefix(' * ')}" for line in _relative_source_lines(source_files).splitlines()],
    ]
    for m in macros:
        args = "" if m.arg_count == 0 else f"[{m.arg_count}]"
        lines.append(f"\\newcommand{{\\{m.name}}}{args}{{{m.body}}}")
    lines.append("")
    return "\n".join(lines)


def generate_html(macros: list[MacroDef], source_files: tuple[Path, ...]) -> str:
    """Generate a MathJax macro include for HTML documents.

    Quarto and other Pandoc HTML outputs register macros by rendering them:
    the definitions sit in a hidden div inside a math delimiter, so MathJax
    processes them before any content. Downstream projects include this file
    (Quarto: `include-before-body`) instead of defining macros of their own.
    """
    lines: list[str] = [
        "<!-- MathJax macro include -- generated by bin/generate-mathjax-config.py.",
        r"     This include alone does not support \fps; the host must load MathJax 4",
        "     and register templates/js/mathjax-stmaryrd.js before typesetting.",
        "     DO NOT EDIT MANUALLY.  Source of truth:",
        _relative_source_lines(source_files).replace(" * ", "     "),
        "-->",
        '<div style="display:none">',
        "\\(",
    ]

    for m in macros:
        args = "" if m.arg_count == 0 else f"[{m.arg_count}]"
        lines.append(f"\\newcommand{{\\{m.name}}}{args}{{{m.body}}}")

    lines.append("\\)")
    lines.append("</div>")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate MathJax 3 macro config from compatible LaTeX macro files."
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=OUT_DIR,
        help="Output directory for generated files.",
    )
    parser.add_argument(
        "--js",
        type=Path,
        default=None,
        help="Output path for .mjs file (default: --out-dir/mathjax-macros.mjs)",
    )
    parser.add_argument(
        "--ts",
        type=Path,
        default=None,
        help="Output path for .ts file (default: --out-dir/mathjax-macros.ts)",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        help="Output path for .json file (default: --out-dir/mathjax-macros.json)",
    )
    parser.add_argument(
        "--html",
        type=Path,
        default=None,
        help="Output path for the HTML macro include (default: --out-dir/mathjax-macros.html)",
    )
    parser.add_argument(
        "--legacy-html",
        type=Path,
        default=None,
        help="Output path for the legacy raw-TeX HTML projection (default: --out-dir/math-macros.html)",
    )
    parser.add_argument(
        "--mathjax-config",
        type=Path,
        default=None,
        help=(
            "A copy of templates/mathjax-config.html whose generated MathJax macro map should be "
            "refreshed. The canonical MathJax configuration and the reveal.js template are "
            "updated automatically for the canonical output directory."
        ),
    )
    parser.add_argument(
        "--count",
        action="store_true",
        help="Print macro count summary and exit.",
    )
    args = parser.parse_args()

    source_files = _read_manifest(MACRO_MANIFEST)
    all_macros = _read_macros(source_files)

    if args.count:
        zero = sum(1 for m in all_macros if m.arg_count == 0)
        narg = sum(1 for m in all_macros if m.arg_count > 0)
        print(
            f"Macros parsed: {len(all_macros)} total ({zero} zero-arg, {narg} with args)"
        )
        return

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    js_path = args.js or (out_dir / "mathjax-macros.mjs")
    ts_path = args.ts or (out_dir / "mathjax-macros.ts")
    json_path = args.json or (out_dir / "mathjax-macros.json")
    html_path = args.html or (out_dir / "mathjax-macros.html")
    legacy_html_path = args.legacy_html or (out_dir / "math-macros.html")

    js_content = generate_js(all_macros, source_files)
    ts_content = generate_ts(all_macros, source_files)
    json_content = generate_json(all_macros)
    html_content = generate_html(all_macros, source_files)
    legacy_html_content = generate_legacy_html(all_macros, source_files)

    js_path.write_text(js_content)
    ts_path.write_text(ts_content)
    json_path.write_text(json_content)
    html_path.write_text(html_content)
    legacy_html_path.write_text(legacy_html_content)

    # A run into the canonical output directory refreshes each canonical
    # template. A MathJax configuration that the caller names is the one
    # template of the run.
    templates: list[GeneratedTemplate] = []
    if args.mathjax_config is not None:
        templates = [GeneratedTemplate(args.mathjax_config, *HTML_MARKERS)]
    elif out_dir.resolve() == OUT_DIR.resolve():
        templates = list(GENERATED_TEMPLATES)
    for template in templates:
        update_template_macros(template, all_macros)

    zero = sum(1 for m in all_macros if m.arg_count == 0)
    narg = sum(1 for m in all_macros if m.arg_count > 0)
    print(
        f"Generated: {js_path} ({len(all_macros)} macros: {zero} zero-arg, {narg} with args)"
    )
    print(f"Generated: {ts_path}")
    print(f"Generated: {json_path}")
    print(f"Generated: {html_path}")
    print(f"Generated: {legacy_html_path}")
    for template in templates:
        print(f"Updated: {template.path}")


if __name__ == "__main__":
    main()
