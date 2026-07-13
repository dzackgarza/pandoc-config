"""Behavioral proof for the installed macro-expansion command."""

from pathlib import Path

from pandoc_config.cli import expand


def test_expand_writes_expanded_macro_to_requested_output(tmp_path: Path) -> None:
    input_path = tmp_path / "input.md"
    style_path = tmp_path / "macros.sty"
    output_path = tmp_path / "output.md"
    input_path.write_text(r"The group is $\GL{V}$.")
    style_path.write_text(r"\newcommand{\GL}[1]{\operatorname{GL}(#1)}")

    expand(input_path, output_path=output_path, style_path=style_path)

    assert output_path.read_text() == r"The group is $\operatorname{GL}(V)$."
