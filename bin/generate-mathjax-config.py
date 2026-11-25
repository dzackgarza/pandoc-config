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
  - The mathtools pairedDelimiters JSON of each \\DeclarePairedDelimiter
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
    LatexCharsNode,
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
    default: str | None = None
    delimiters: tuple[str, str] | None = None


class ProjectionError(Exception):
    pass


MATHJAX_SHIMS = (
    MacroDef("vcentcolon", 0, r"\vcentercolon"),
    MacroDef("coloneqq", 0, r"\vcentcolon\mathrel{\mkern-1.2mu}="),
    MacroDef("qed", 0, r"\quad\blacksquare"),
)

_NEWCOMMANDS = ("newcommand", "renewcommand", "providecommand")
_DEFINITION_MACROS = (
    *_NEWCOMMANDS,
    "DeclareMathOperator",
    "DeclarePairedDelimiter",
    "def",
    "let",
)
_UNPROJECTED_DEFINITIONS = (
    "gdef",
    "edef",
    "xdef",
    "DeclareRobustCommand",
    "DeclarePairedDelimiterX",
    "DeclarePairedDelimiterXPP",
    "NewDocumentCommand",
    "RenewDocumentCommand",
    "ProvideDocumentCommand",
    "DeclareDocumentCommand",
    "DeclareMathSymbol",
    "mathchardef",
    "chardef",
)
_PARAMETER_TEXT_RE = re.compile(r"(?:#[1-9])*")
_AT_LETTER = "ǝ"
_AT_LETTER_REGION_RE = re.compile(r"\\makeatletter(.*?)(?=\\makeatother|\Z)", re.S)


def _latex_context() -> LatexContextDb:
    context = get_default_latex_context_db()
    context.add_context_category(
        "macro-definitions",
        prepend=True,
        macros=[
            MacroSpec("def", "{"),
            MacroSpec("let", "{{"),
            MacroSpec("DeclarePairedDelimiter", "{{{"),
            *(MacroSpec(name, "{") for name in _UNPROJECTED_DEFINITIONS),
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


def _group_text(argument: LatexNode | None) -> str | None:
    if argument is None:
        return None
    if isinstance(argument, LatexGroupNode) and argument.delimiters == ("{", "}"):
        return _without_comments(argument.nodelist).strip()
    if isinstance(argument, LatexGroupNode):
        return None
    return argument.latex_verbatim().strip()


def _arg_count(argument: LatexNode | None) -> int:
    if not isinstance(argument, LatexGroupNode):
        return 0
    text = _without_comments(argument.nodelist).strip()
    return int(text) if text.isdecimal() else 0


def _optional_text(argument: LatexNode | None) -> str | None:
    if not isinstance(argument, LatexGroupNode):
        return None
    return _without_comments(argument.nodelist)


class _Source(NamedTuple):
    name: str
    walker: LatexWalker

    def refuse(self, node: LatexNode, defined: str, cause: str) -> ProjectionError:
        line, _column = self.walker.pos_to_lineno_colno(node.pos)
        named = defined.replace(_AT_LETTER, "@")
        return ProjectionError(f"{self.name}:{line}: \\{named}: {cause}")


def _parameter_count(text: str) -> int | None:
    if not _PARAMETER_TEXT_RE.fullmatch(text):
        return None
    numbers = [int(digit) for digit in text[1::2]]
    return len(numbers) if numbers == list(range(1, len(numbers) + 1)) else None


def _def_definition(
    source: _Source, node: LatexMacroNode, siblings: list[LatexNode | None], start: int
) -> tuple[MacroDef, int]:
    name = _defined_name(node.nodeargd.argnlist[0])
    index = start
    parameter_text = ""
    while index < len(siblings) and not isinstance(siblings[index], LatexGroupNode):
        sibling = siblings[index]
        if not isinstance(sibling, (LatexCharsNode, LatexCommentNode)):
            raise source.refuse(node, name, "its parameter text is not #1#2...")
        if isinstance(sibling, LatexCharsNode):
            parameter_text += sibling.chars
        index += 1
    arg_count = _parameter_count(parameter_text.strip())
    if index == len(siblings) or arg_count is None:
        raise source.refuse(
            node, name, f"a delimited parameter text {parameter_text.strip()!r} has no MathJax form"
        )
    body = _group_text(siblings[index])
    if body is None:
        raise source.refuse(node, name, "the body is not a group")
    return MacroDef(name=name, arg_count=arg_count, body=body), index + 1


def _definition(source: _Source, node: LatexMacroNode) -> MacroDef | None:
    arguments = node.nodeargd.argnlist
    if node.macroname in _UNPROJECTED_DEFINITIONS:
        raise source.refuse(
            node, _defined_name(arguments[0]), f"\\{node.macroname} has no MathJax projection"
        )
    if node.macroname == "let":
        name_arg, target_arg = arguments
        name = _defined_name(name_arg)
        if isinstance(target_arg, LatexMacroNode) and target_arg.macroname == "relax":
            return None
        raise source.refuse(node, name, "a \\let copy of another macro has no MathJax projection")
    if node.macroname == "DeclarePairedDelimiter":
        name_arg, left_arg, right_arg = arguments
        name, left, right = _defined_name(name_arg), _group_text(left_arg), _group_text(right_arg)
        if left is None or right is None:
            raise source.refuse(node, name, "a delimiter of the pair is not a group")
        opening = "" if left == "." else f"\\mathopen{{{left}}}"
        closing = "" if right == "." else f"\\mathclose{{{right}}}"
        definition = MacroDef(
            name=name, arg_count=1, body=f"{opening}#1{closing}", delimiters=(left, right)
        )
    elif node.macroname in _NEWCOMMANDS:
        _star, name_arg, count_arg, default_arg, body_arg = arguments
        definition = MacroDef(
            name=_defined_name(name_arg),
            arg_count=_arg_count(count_arg),
            body=_group_text(body_arg),
            default=_optional_text(default_arg),
        )
    else:
        star_arg, name_arg, body_arg = arguments
        operator = "operatorname*" if star_arg is not None else "operatorname"
        body = _group_text(body_arg)
        definition = MacroDef(
            name=_defined_name(name_arg),
            arg_count=0,
            body=None if body is None else f"\\{operator}{{{body}}}",
        )
    if not definition.name or definition.body is None:
        raise source.refuse(node, definition.name or node.macroname, "the definition has no name or no body")
    return definition


def _definitions_in(source: _Source, nodes: list[LatexNode | None]) -> list[MacroDef]:
    macros: list[MacroDef] = []
    index = 0
    while index < len(nodes):
        node = nodes[index]
        index += 1
        if isinstance(node, LatexMacroNode) and node.macroname == "def":
            definition, index = _def_definition(source, node, nodes, index)
            macros.append(definition)
        elif isinstance(node, LatexMacroNode) and (
            node.macroname in _DEFINITION_MACROS or node.macroname in _UNPROJECTED_DEFINITIONS
        ):
            definition = _definition(source, node)
            if definition is not None:
                macros.append(definition)
        elif isinstance(node, LatexMacroNode) and node.nodeargd is not None:
            macros.extend(_definitions_in(source, node.nodeargd.argnlist))
        elif isinstance(node, (LatexGroupNode, LatexEnvironmentNode)):
            macros.extend(_definitions_in(source, node.nodelist))
    return macros


def parse_macros(content: str, source_name: str) -> list[MacroDef]:
    """Parse each macro definition of a TeX source.

    A definition that has no MathJax form raises ProjectionError with the
    source name, the line and the defined name."""
    if _AT_LETTER in content:
        raise ProjectionError(f"{source_name}: the source holds {_AT_LETTER!r}, which the parser uses for @")
    with_at_letters = _AT_LETTER_REGION_RE.sub(
        lambda region: region.group(0).replace("@", _AT_LETTER), content
    )
    walker = LatexWalker(with_at_letters, latex_context=_LATEX_CONTEXT, tolerant_parsing=False)
    nodes, _pos, _len = walker.get_latex_nodes()
    return [
        MacroDef(*(field.replace(_AT_LETTER, "@") if isinstance(field, str) else field for field in macro))
        for macro in _definitions_in(_Source(source_name, walker), nodes)
    ]


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
        macros.extend(parse_macros(_read_file(source_file), str(source_file)))
    return _unique_macros(macros)


TS_PRELUDE = """\
type ZeroArgMacro = string;
type NArgMacro = [replacement: string, argCount: number];
type DefaultArgMacro = [replacement: string, argCount: number, defaultArgument: string];

export const macros: Record<string, ZeroArgMacro | NArgMacro | DefaultArgMacro> = {"""


def _read_file(path: Path) -> str:
    if not path.exists():
        print(f"ERROR: source file not found: {path}", file=sys.stderr)
        sys.exit(1)
    return path.read_text()


def _js_entry(macro: MacroDef) -> str:
    value = json.dumps(_mathjax_value(macro), ensure_ascii=False, separators=(", ", ": "))
    return f'  "{macro.name}": {value},'


def generate_js(macros: list[MacroDef]) -> str:
    """Generate JavaScript ESM module content."""
    return "\n".join(["export const macros = {", *map(_js_entry, macros), "};", ""])


def generate_ts(macros: list[MacroDef]) -> str:
    """Generate TypeScript module content."""
    return "\n".join([TS_PRELUDE, *map(_js_entry, macros), "};\n"])


def generate_json(macros: list[MacroDef]) -> str:
    """Generate JSON for embedding in HTML.
    json.dumps handles backslash escaping, so we pass raw LaTeX bodies.
    """
    return json.dumps(_macro_object(macros), indent=2)


MathJaxValue = str | list[str | int]


def _mathjax_value(macro: MacroDef) -> MathJaxValue:
    if macro.default is not None:
        return [macro.body, macro.arg_count, macro.default]
    if macro.arg_count:
        return [macro.body, macro.arg_count]
    return macro.body


def _macro_object(macros: list[MacroDef]) -> dict[str, MathJaxValue]:
    """Return the canonical MathJax ``tex.macros`` object."""
    return {macro.name: _mathjax_value(macro) for macro in macros}


def _newcommand(macro: MacroDef) -> str:
    count = f"[{macro.arg_count}]" if macro.arg_count else ""
    default = "" if macro.default is None else f"[{macro.default}]"
    return f"\\newcommand{{\\{macro.name}}}{count}{default}{{{macro.body}}}"


def _paired_delimiter_object(macros: list[MacroDef]) -> dict[str, list[str]]:
    """Return the mathtools ``pairedDelimiters`` object of MathJax.

    With it MathJax mathtools gives each pair its three forms: without a star
    (no scaling), with a star (``\\left`` and ``\\right``) and with a size
    (``\\bigl`` and ``\\bigr``), as ``\\DeclarePairedDelimiter`` does in LaTeX.
    """
    return {macro.name: list(macro.delimiters) for macro in macros if macro.delimiters is not None}


def generate_paired_delimiters_json(macros: list[MacroDef]) -> str:
    return json.dumps(_paired_delimiter_object(macros), indent=2)


GENERATED_TEMPLATES = (MATHJAX_CONFIG_PARTIAL, REVEALJS_TEMPLATE)


def _generated_line_re(key: str) -> re.Pattern[str]:
    return re.compile(rf"(?m)^(\s*{key}:\s*)\{{.*\}},[^\S\n]*$")


def update_template_macros(template_path: Path, macros: list[MacroDef]) -> None:
    """Replace the one ``macros: {...},`` line and the one
    ``pairedDelimiters: {...},`` line of a template.

    The rest of the MathJax configuration belongs to the template. The
    generated lines are a projection of ``styles/macros``, so a template is
    never a second macro authority. A template with no such line or with more
    than one fails.
    """
    text = template_path.read_text()
    projections = {
        "macros": _macro_object(macros),
        "pairedDelimiters": _paired_delimiter_object(macros),
    }
    for key, value in projections.items():
        line_re = _generated_line_re(key)
        if len(line_re.findall(text)) != 1:
            raise RuntimeError(
                f"Template {template_path} must contain exactly one generated {key} line"
            )
        replacement = json.dumps(value, separators=(",", ":"))
        text = line_re.sub(lambda match: f"{match.group(1)}{replacement},", text)
    template_path.write_text(text)


def generate_legacy_html(macros: list[MacroDef]) -> str:
    """Generate raw MathJax TeX definitions for the legacy HTML template.

    ``research_draft.html`` wraps this file in a MathJax delimiter. It is a
    projection of the same parsed macro API as every other target; it must not
    be built by separately concatenating source files.
    """
    lines: list[str] = []
    for m in macros:
        lines.append(_newcommand(m))
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
        lines.append(_newcommand(m))
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
        lines.append(_newcommand(m))

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
        "--paired-delimiters",
        type=Path,
        default=None,
        help=(
            "Output path for the mathtools pairedDelimiters JSON "
            "(default: --out-dir/mathjax-paired-delimiters.json)"
        ),
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
    try:
        all_macros = _read_macros(source_files)
    except ProjectionError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)

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
    paired_delimiters_path = args.paired_delimiters or (out_dir / "mathjax-paired-delimiters.json")
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
    paired_delimiters_path.write_text(generate_paired_delimiters_json(all_macros))
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
    print(f"Generated: {paired_delimiters_path}")
    print(f"Generated: {html_path}")
    print(f"Generated: {legacy_html_path}")
    print(f"Generated: {reader_input_path}")
    for template in templates:
        print(f"Updated: {template}")


if __name__ == "__main__":
    main()
