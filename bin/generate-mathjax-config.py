#!/usr/bin/env -S uv run
"""
Generate MathJax 3 macro configuration (JS/TS) from compatible LaTeX macro files.

Reads the canonical MathJax-compatible macro sources, parses the \\newcommand /
\\renewcommand / \\providecommand / \\DeclareMathOperator and parameterless \\def
definitions with the LaTeX parser of pylatexenc, and
outputs:

  - A JavaScript ESM module exporting a { macros } object
  - A TypeScript module exporting the same with type annotations
  - A JSON file for direct embedding in HTML
  - The \\newcommand lines as the first input of a Pandoc Markdown reader
    (math-macros.md), for each writer without a template that loads them

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

from pylatexenc.latexwalker import (
    LatexCommentNode,
    LatexEnvironmentNode,
    LatexGroupNode,
    LatexMacroNode,
    LatexNode,
    LatexWalker,
    get_default_latex_context_db,
)
from pylatexenc.macrospec import LatexContextDb, MacroSpec

REPO_ROOT = Path(__file__).resolve().parent.parent
MACRO_DIR = REPO_ROOT / "styles" / "macros"

MACRO_MANIFEST = MACRO_DIR / "mathjax-sources.txt"
OUT_DIR = REPO_ROOT / "templates" / "css"

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

_NEWCOMMANDS = ("newcommand", "renewcommand", "providecommand")
_DEFINITION_MACROS = (*_NEWCOMMANDS, "DeclareMathOperator", "DeclarePairedDelimiter", "def")


def _latex_context() -> LatexContextDb:
    context = get_default_latex_context_db()
    context.add_context_category(
        "macro-definitions",
        prepend=True,
        macros=[
            MacroSpec("def", "{{"),
            MacroSpec("DeclarePairedDelimiter", "{{{"),
        ],
    )
    return context


_LATEX_CONTEXT = _latex_context()


def _without_comments(nodes: list[LatexNode]) -> str:
    return "".join(
        node.latex_verbatim() for node in nodes if not isinstance(node, LatexCommentNode)
    )


def _defined_name(argument: LatexNode | None) -> str:
    if isinstance(argument, LatexMacroNode):
        return argument.macroname
    if isinstance(argument, LatexGroupNode):
        inner = [node for node in argument.nodelist if not isinstance(node, LatexCommentNode)]
        if inner and isinstance(inner[0], LatexMacroNode):
            return inner[0].macroname
    return ""


def _group_text(argument: LatexNode | None) -> str:
    if not isinstance(argument, LatexGroupNode) or argument.delimiters != ("{", "}"):
        return ""
    return _without_comments(argument.nodelist).strip()


def _arg_count(argument: LatexNode | None) -> int:
    if not isinstance(argument, LatexGroupNode):
        return 0
    text = _without_comments(argument.nodelist).strip()
    return int(text) if text.isdecimal() else 0


def _definition(node: LatexMacroNode) -> MacroDef | None:
    arguments = node.nodeargd.argnlist
    if node.macroname == "DeclarePairedDelimiter":
        return None
    if node.macroname in _NEWCOMMANDS:
        _star, name_arg, count_arg, _default, body_arg = arguments
        name, arg_count, body = _defined_name(name_arg), _arg_count(count_arg), _group_text(body_arg)
    elif node.macroname == "DeclareMathOperator":
        _star, name_arg, body_arg = arguments
        name, arg_count, body = _defined_name(name_arg), 0, _group_text(body_arg)
        body = f"\\operatorname{{{body}}}" if body else ""
    else:
        name_arg, body_arg = arguments
        name, arg_count, body = _defined_name(name_arg), 0, _group_text(body_arg)
    if not name or not body:
        return None
    return MacroDef(name=name, arg_count=arg_count, body=body)


def _definitions_in(nodes: list[LatexNode | None]) -> list[MacroDef]:
    macros: list[MacroDef] = []
    for node in nodes:
        if isinstance(node, LatexMacroNode) and node.macroname in _DEFINITION_MACROS:
            definition = _definition(node)
            if definition is not None:
                macros.append(definition)
        elif isinstance(node, LatexMacroNode) and node.nodeargd is not None:
            macros.extend(_definitions_in(node.nodeargd.argnlist))
        elif isinstance(node, (LatexGroupNode, LatexEnvironmentNode)):
            macros.extend(_definitions_in(node.nodelist))
    return macros


def parse_macros(content: str) -> list[MacroDef]:
    """Parse all \\newcommand, \\def, \\DeclareMathOperator definitions."""
    nodes, _pos, _len = LatexWalker(
        content, latex_context=_LATEX_CONTEXT, tolerant_parsing=False
    ).get_latex_nodes()
    return _definitions_in(nodes)

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
        print(
            f"ERROR: manifest declares no macro files: {manifest_path}", file=sys.stderr
        )
        sys.exit(1)
    return tuple(files)


def _read_macros(source_files: tuple[Path, ...]) -> list[MacroDef]:
    macros: list[MacroDef] = list(MATHJAX_SHIMS)
    for source_file in source_files:
        macros.extend(parse_macros(_read_file(source_file)))
    return _unique_macros(macros)


TS_PRELUDE = """\
type ZeroArgMacro = string;
type NArgMacro = [replacement: string, argCount: number];

export const macros: Record<string, ZeroArgMacro | NArgMacro> = {"""


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


def generate_js(macros: list[MacroDef]) -> str:
    """Generate JavaScript ESM module content."""
    lines: list[str] = ["export const macros = {"]

    for m in macros:
        if m.arg_count == 0:
            lines.append(f'  "{m.name}": {_format_0arg(m.body)},')
        else:
            lines.append(f'  "{m.name}": {_format_narg(m.body, m.arg_count)},')

    lines.append("};")
    lines.append("")
    return "\n".join(lines)


def generate_ts(macros: list[MacroDef]) -> str:
    """Generate TypeScript module content."""
    lines: list[str] = [TS_PRELUDE]

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


GENERATED_TEMPLATES = (MATHJAX_CONFIG_PARTIAL, REVEALJS_TEMPLATE)

MACROS_LINE_RE = re.compile(r"(?m)^(\s*macros:\s*)\{.*\},[^\S\n]*$")


def update_template_macros(template_path: Path, macros: list[MacroDef]) -> None:
    """Replace the one ``macros: {...},`` line of a template.

    The rest of the MathJax configuration belongs to the template. The macro
    line is a projection of ``styles/macros``, so a template is never a second
    macro authority. A template with no such line or with more than one fails.
    """
    text = template_path.read_text()
    if len(MACROS_LINE_RE.findall(text)) != 1:
        raise RuntimeError(
            f"Template {template_path} must contain exactly one generated macros line"
        )
    replacement = json.dumps(_macro_object(macros), separators=(",", ":"))
    template_path.write_text(
        MACROS_LINE_RE.sub(lambda match: f"{match.group(1)}{replacement},", text)
    )


def generate_legacy_html(macros: list[MacroDef]) -> str:
    """Generate raw MathJax TeX definitions for the legacy HTML template.

    ``research_draft.html`` wraps this file in a MathJax delimiter. It is a
    projection of the same parsed macro API as every other target; it must not
    be built by separately concatenating source files.
    """
    lines: list[str] = []
    for m in macros:
        args = "" if m.arg_count == 0 else f"[{m.arg_count}]"
        lines.append(f"\\newcommand{{\\{m.name}}}{args}{{{m.body}}}")
    lines.append("")
    return "\n".join(lines)


READER_INPUT_CLASS = "math-macros"


def generate_reader_input(macros: list[MacroDef]) -> str:
    """Generate the macro definitions as a first input of a Pandoc Markdown reader.

    The ``latex_macros`` extension of the Markdown reader applies each
    ``\\newcommand`` that it reads to the TeX math after it, so each writer gets
    the expansion of a macro and no writer needs a definition of its own
    (Pandoc manual, "Extension: latex_macros"). The definitions are in a
    fenced div that ``filters/math-macros.lua`` removes: a writer that keeps
    raw TeX (ConTeXt, Markdown) would otherwise write them into its output.
    """
    lines: list[str] = [
        f"::: {{.{READER_INPUT_CLASS}}}",
    ]
    for m in macros:
        args = "" if m.arg_count == 0 else f"[{m.arg_count}]"
        lines.append(f"\\newcommand{{\\{m.name}}}{args}{{{m.body}}}")
    lines.append(":::")
    lines.append("")
    return "\n".join(lines)


def generate_html(macros: list[MacroDef]) -> str:
    """Generate a MathJax macro include for HTML documents.

    Quarto and other Pandoc HTML outputs register macros by rendering them:
    the definitions sit in a hidden div inside a math delimiter, so MathJax
    processes them before any content. Downstream projects include this file
    (Quarto: `include-before-body`) instead of defining macros of their own.
    """
    lines: list[str] = [
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
        "--reader-input",
        type=Path,
        default=None,
        help="Output path for the macro input of a Markdown reader (default: --out-dir/math-macros.md)",
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
    reader_input_path = args.reader_input or (out_dir / "math-macros.md")

    js_content = generate_js(all_macros)
    ts_content = generate_ts(all_macros)
    json_content = generate_json(all_macros)
    html_content = generate_html(all_macros)
    legacy_html_content = generate_legacy_html(all_macros)
    reader_input_content = generate_reader_input(all_macros)

    js_path.write_text(js_content)
    ts_path.write_text(ts_content)
    json_path.write_text(json_content)
    html_path.write_text(html_content)
    legacy_html_path.write_text(legacy_html_content)
    reader_input_path.write_text(reader_input_content)

    templates: list[Path] = []
    if args.mathjax_config is not None:
        templates = [args.mathjax_config]
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
    print(f"Generated: {reader_input_path}")
    for template in templates:
        print(f"Updated: {template}")


if __name__ == "__main__":
    main()
