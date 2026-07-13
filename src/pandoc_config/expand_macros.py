"""LaTeX macro expansion and Pandoc citation resolution."""

import re
import subprocess
import tempfile
from collections.abc import Mapping
from pathlib import Path

MacroMap = dict[str, str]
ParsedMacros = tuple[MacroMap, MacroMap, MacroMap]

_MACRO_DECLARATION = re.compile(
    r"\\(newcommand|providecommand|renewcommand|DeclareMathOperator)"
    r"\*?\s*\{\s*\\([a-zA-Z]+)\s*\}"
)


def parse_macros(style_file: Path) -> ParsedMacros:
    r"""Parse zero-, one-, and two-argument macros from a LaTeX style file."""
    style_content = re.sub(r"(?m)%.*$", "", style_file.read_text())
    macros_0: MacroMap = {}
    macros_1: MacroMap = {}
    macros_2: MacroMap = {}
    index = 0

    while match := _MACRO_DECLARATION.search(style_content, index):
        command_type, name = match.groups()
        index = match.end()
        argument_count = 0
        if index < len(style_content) and style_content[index] == "[":
            bracket_end = style_content.find("]", index)
            if bracket_end != -1:
                count_text = style_content[index + 1 : bracket_end]
                if count_text.isdecimal():
                    argument_count = int(count_text)
                index = bracket_end + 1

        while index < len(style_content) and style_content[index].isspace():
            index += 1
        body, index = _read_braced_group(style_content, index)
        if body is None:
            continue
        if command_type == "DeclareMathOperator":
            macros_0[name] = rf"\operatorname{{{body}}}"
        elif argument_count == 0:
            macros_0[name] = body
        elif argument_count == 1:
            macros_1[name] = body
        elif argument_count == 2:
            macros_2[name] = body

    return macros_0, macros_1, macros_2


def _read_braced_group(text: str, start: int) -> tuple[str | None, int]:
    if start >= len(text) or text[start] != "{":
        return None, start
    depth = 1
    index = start + 1
    while index < len(text) and depth > 0:
        character = text[index]
        if character == "\\":
            index += 2
            continue
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
        index += 1
    if depth != 0:
        return None, index
    return text[start + 1 : index - 1], index


def _read_macro_argument(text: str, start: int) -> tuple[str | None, int]:
    index = start
    while index < len(text) and text[index].isspace():
        index += 1
    group, group_end = _read_braced_group(text, index)
    if group is not None:
        return group, group_end
    if index >= len(text):
        return None, index
    if text[index] != "\\":
        return text[index], index + 1
    token = re.match(r"\\[a-zA-Z]+", text[index:])
    if token is None:
        return text[index], index + 1
    return token.group(), index + token.end()


def expand_macros(
    text: str,
    macros_0: Mapping[str, str],
    macros_1: Mapping[str, str],
    macros_2: Mapping[str, str],
    *,
    max_passes: int = 5,
) -> str:
    r"""Expand known LaTeX macros, including nested expansion passes."""
    names = sorted(macros_0.keys() | macros_1.keys() | macros_2.keys(), key=len, reverse=True)
    for _ in range(max_passes):
        changed = False
        for name in names:
            pattern = re.compile(r"\\" + re.escape(name) + r"(?![a-zA-Z])")
            index = 0
            while match := pattern.search(text, index):
                start, end = match.span()
                if name in macros_0:
                    body = macros_0[name]
                    text = text[:start] + body + text[end:]
                    index = start + len(body)
                    changed = True
                    continue

                arguments: list[str] = []
                argument_end = end
                required = 1 if name in macros_1 else 2
                for _ in range(required):
                    argument, argument_end = _read_macro_argument(text, argument_end)
                    if argument is None:
                        break
                    arguments.append(argument)
                if len(arguments) != required:
                    index = end
                    continue

                template = macros_1[name] if required == 1 else macros_2[name]
                body = template.replace("#1", arguments[0])
                if required == 2:
                    body = body.replace("#2", arguments[1])
                text = text[:start] + body + text[argument_end:]
                index = start + len(body)
                changed = True
        if not changed:
            break
    return text


def strip_tex_formatting(text: str) -> str:
    r"""Remove Pandoc raw-TeX wrappers while preserving their contents."""
    text = re.sub(r"`(.*?)`\{=tex\}", r"\1", text)
    text = re.sub(r"```tex\n(.*?)\n```", r"\1", text, flags=re.DOTALL)
    return text.replace(r"\[", "[").replace(r"\]", "]")


def preprocess_citations(text: str) -> str:
    r"""Convert LaTeX cite commands and inline-math delimiters for Pandoc."""

    def replace_suffixed_citation(match: re.Match[str]) -> str:
        suffix, keys_text = match.groups()
        keys = [key.strip() for key in keys_text.split(",")]
        citations = [
            f"@{key}, {suffix}" if index == len(keys) - 1 and suffix else f"@{key}"
            for index, key in enumerate(keys)
        ]
        return "[" + "; ".join(citations) + "]"

    text = re.sub(r"\\cite\[(.*?)\]\{(.*?)\}", replace_suffixed_citation, text)
    text = re.sub(
        r"\\cite\{(.*?)\}",
        lambda match: "[" + "; ".join(f"@{key.strip()}" for key in match.group(1).split(",")) + "]",
        text,
    )
    return text.replace(r"\(", "$").replace(r"\)", "$")


def resolve_citations(text: str, bibliography_file: Path) -> str:
    r"""Resolve citations with Pandoc and the supplied bibliography."""
    if not bibliography_file.is_file():
        raise FileNotFoundError(bibliography_file)
    with tempfile.TemporaryDirectory() as temporary_directory:
        input_path = Path(temporary_directory) / "input.md"
        output_path = Path(temporary_directory) / "output.md"
        input_path.write_text(text)
        subprocess.run(
            [
                "pandoc",
                "--from=markdown",
                "--to=markdown-citations+tex_math_dollars+raw_tex",
                "--citeproc",
                f"--bibliography={bibliography_file}",
                "--standalone",
                "--wrap=none",
                str(input_path),
                "-o",
                str(output_path),
            ],
            check=True,
        )
        return output_path.read_text()


def expand_all(
    text: str,
    sty_file: Path | None = None,
    bib_file: Path | None = None,
    *,
    strip: bool = True,
) -> str:
    r"""Apply citation preprocessing, optional resolution, macro expansion, and cleanup."""
    result = preprocess_citations(text)
    if bib_file is not None:
        result = resolve_citations(result, bib_file)
    if sty_file is not None:
        macros_0, macros_1, macros_2 = parse_macros(sty_file)
        result = expand_macros(result, macros_0, macros_1, macros_2)
    return strip_tex_formatting(result) if strip else result
