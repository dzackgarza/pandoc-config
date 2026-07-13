"""Command-line interface for macro and citation expansion."""

from pathlib import Path
from typing import Annotated

from cyclopts import App, Parameter
from pydantic import validate_call

from pandoc_config.expand_macros import expand_all
from pandoc_config.models import ExpandRequest

app = App(help="Expand LaTeX macros and citations in a text file.")


@app.default
@validate_call
def expand(
    input_path: Annotated[Path, Parameter(help="Markdown or LaTeX input file")],
    *,
    output_path: Annotated[Path | None, Parameter(name="--output")] = None,
    style_path: Annotated[Path | None, Parameter(name="--sty")] = None,
    bibliography_path: Annotated[Path | None, Parameter(name="--bib")] = None,
    strip: Annotated[bool, Parameter(negative="--no-strip")] = True,
) -> None:
    """Expand the input and write it to a file or standard output."""
    request = ExpandRequest(
        input_path=input_path,
        output_path=output_path,
        style_path=style_path,
        bibliography_path=bibliography_path,
        strip=strip,
    )
    result = expand_all(
        request.input_path.read_text(),
        sty_file=request.style_path,
        bib_file=request.bibliography_path,
        strip=request.strip,
    )
    if request.output_path is None:
        print(result)
        return
    request.output_path.write_text(result)


def main() -> None:
    """Run the command-line application."""
    app()
