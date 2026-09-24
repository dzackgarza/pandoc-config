"""Regenerate the reference section of README.md from the sources.

The section between the markers below lists every math macro (name, number of
arguments, expansion) of the files styles/dzg-macros.sty inputs and of the
environment files, every theorem-like environment, and every figure object
under figures/objects/ with the first sentence of its leading comment. The
macro parser is the one bin/generate-mathjax-config.py uses for MathJax.

    python3 bin/generate-readme-reference.py           # rewrite README.md
    python3 bin/generate-readme-reference.py --check   # fail if README.md is stale
"""

import argparse
import importlib.util
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"
STYLES = REPO_ROOT / "styles"
MACROS = STYLES / "macros"
OBJECTS = REPO_ROOT / "figures" / "objects"
BEGIN = "<!-- BEGIN GENERATED REFERENCE: bin/generate-readme-reference.py -->"
END = "<!-- END GENERATED REFERENCE -->"
# Loaded by dzg-unified.sty after dzg-macros.sty (environments-arxiv under the
# arxiv option) and by dzg-dissertation.sty (dissertation-overrides).
EXTRA_MACRO_FILES = ("environments.tex", "environments-arxiv.tex", "dissertation-overrides.tex")

_spec = importlib.util.spec_from_file_location(
    "generate_mathjax_config", REPO_ROOT / "bin" / "generate-mathjax-config.py")
_mathjax = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mathjax)

ENVIRONMENT_RE = re.compile(
    r"\\(?:newtheorem\*?|newenvironment|NewDocumentEnvironment)\s*\{([^}]+)\}(?:\[[^\]]*\])?\s*\{([^}]*)\}")


def macro_files() -> list[Path]:
    inputs = re.findall(r"^\\input\{([^}]+)\}", (STYLES / "dzg-macros.sty").read_text(), re.M)
    return [MACROS / f"{name}.tex" for name in inputs] + [MACROS / name for name in EXTRA_MACRO_FILES]


def code(text: str) -> str:
    text = " ".join(text.split()).replace("|", "\\|")
    fence = "``" if "`" in text else "`"
    pad = " " if fence == "``" else ""
    return f"{fence}{pad}{text}{pad}{fence}"


def macro_section(path: Path) -> list[str]:
    content = path.read_text()
    macros = _mathjax.parse_macros(content)
    environments = ENVIRONMENT_RE.findall(content)
    lines = [f"### `{path.relative_to(REPO_ROOT)}`", ""]
    if macros:
        lines += ["| Macro | Args | Expansion |", "| --- | --- | --- |"]
        lines += [f"| {code(chr(92) + m.name)} | {m.arg_count} | {code(m.body)} |" for m in macros]
        lines.append("")
    if environments:
        lines += ["| Environment | Heading or definition |", "| --- | --- |"]
        lines += [f"| `{name}` | {code(title) if title else ''} |" for name, title in environments]
        lines.append("")
    if not macros and not environments:
        lines += ["No macro or environment definitions.", ""]
    return lines


def first_sentence(path: Path, comment: str) -> str:
    text = []
    for line in path.read_text().splitlines():
        if not line.startswith(comment):
            break
        text.append(line[len(comment):].strip())
    joined = " ".join(text)
    match = re.match(r"(.+?\.)(\s+[A-Z(]|$)", joined)
    sentence = match.group(1) if match else joined
    return sentence if len(sentence) <= 200 else sentence[:200].rsplit(" ", 1)[0] + " ..."


def object_section() -> list[str]:
    lines = ["| Object | Placed with | Description |", "| --- | --- | --- |"]
    for path in sorted(OBJECTS.rglob("*.tikz")):
        name = path.relative_to(OBJECTS).with_suffix("")
        lines.append(f"| `{name}` | `\\pic {{object={name}}}` | {code(first_sentence(path, '%'))} |")
    lines += ["", "| Poset data | Written by | Description |", "| --- | --- | --- |"]
    for path in sorted(OBJECTS.rglob("*.sage")):
        written = sorted(p.name for p in path.parent.glob("*.json")
                         if p.name in path.read_text())
        lines.append(f"| {', '.join(f'`{w}`' for w in written)} | "
                     f"`{path.relative_to(REPO_ROOT)}` | {code(first_sentence(path, '#'))} |")
    return lines + [""]


def reference() -> str:
    lines = [BEGIN, "", "## Reference (generated)", "",
             "Regenerate with `just readme-reference`; `just test` fails when this "
             "section is stale.", "", "## Math macros and environments", ""]
    for path in macro_files():
        lines += macro_section(path)
    lines += ["## Figure objects", ""] + object_section() + [END]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if README.md is stale")
    args = parser.parse_args()
    readme = README.read_text()
    assert BEGIN in readme and END in readme, f"{README} has no generated-reference markers"
    head, rest = readme.split(BEGIN, 1)
    tail = rest.split(END, 1)[1].lstrip("\n")
    updated = head + reference() + tail
    if args.check:
        if updated != readme:
            sys.exit("README.md reference is stale: run `just readme-reference`")
        return
    README.write_text(updated)


if __name__ == "__main__":
    main()
