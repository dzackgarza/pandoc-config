#!/usr/bin/env python3
"""Contract tests for the wikilinks filter: it applies the editor's resolutions."""

import json
import os
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
FILTER = ROOT / "filters" / "wikilinks.lua"

INDEX = """# Index

See [[chain#Second step|the step]], [[chain]], [[elsewhere]] and [[a b]].
"""

CHAIN = """# First step

Text.

# Second step

Done.
"""

MAP = {
    "inputs": [{"headings": 1}, {"headings": 2}],
    "links": {
        "chain#Second step": {"input": 1, "heading": 1},
        "chain": {"input": 1, "heading": 0},
    },
}


def render(files: dict[str, str], resolutions: dict | None) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as directory:
        inputs = []
        for name, text in files.items():
            Path(directory, name).write_text(text)
            inputs.append(name)
        environment = dict(os.environ)
        environment.pop("PANDOC_WIKILINKS", None)
        if resolutions is not None:
            Path(directory, "wikilinks.json").write_text(json.dumps(resolutions))
            environment["PANDOC_WIKILINKS"] = str(Path(directory, "wikilinks.json"))
        return subprocess.run(
            [
                "pandoc",
                *inputs,
                "--from=markdown+tex_math_single_backslash+wikilinks_title_after_pipe",
                "--lua-filter",
                str(FILTER),
                "-t",
                "latex",
            ],
            capture_output=True,
            text=True,
            cwd=directory,
            env=environment,
        )


def test_resolved_links_point_at_their_headings() -> None:
    result = render({"index.md": INDEX, "chain.md": CHAIN}, MAP)
    assert result.returncode == 0, result.stderr
    assert r"\hyperref[second-step]{the step}" in result.stdout
    assert r"\hyperref[first-step]{chain}" in result.stdout


def test_unresolved_links_become_their_labels() -> None:
    result = render({"index.md": INDEX, "chain.md": CHAIN}, MAP)
    assert result.returncode == 0, result.stderr
    assert "elsewhere and a b." in result.stdout
    assert r"\href" not in result.stdout


def test_without_resolutions_every_link_is_its_label() -> None:
    result = render({"index.md": INDEX}, None)
    assert result.returncode == 0, result.stderr
    assert "See the step, chain, elsewhere and a b." in result.stdout
    assert "hyperref" not in result.stdout


def test_a_heading_count_that_pandoc_does_not_read_fails() -> None:
    wrong = {**MAP, "inputs": [{"headings": 1}, {"headings": 3}]}
    result = render({"index.md": INDEX, "chain.md": CHAIN}, wrong)
    assert result.returncode != 0
    assert "counted 4 headings" in result.stderr


if __name__ == "__main__":
    test_resolved_links_point_at_their_headings()
    test_unresolved_links_become_their_labels()
    test_without_resolutions_every_link_is_its_label()
    test_a_heading_count_that_pandoc_does_not_read_fails()
    print("Wikilinks filter tests passed")
