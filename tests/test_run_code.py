"""Behavioral proof for filters/run_code.lua.

Exercises the real pandoc + Lua-filter path with an interpreter that is present
(python3). Lean routes through the identical mechanism; its live test is skipped
when no Lean toolchain is configured.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

FILTER = Path(__file__).resolve().parent.parent / "filters" / "run_code.lua"


def render(md: str, tmp_path: Path, extra_env: dict | None = None) -> str:
    """Render markdown to HTML through run_code.lua, cache isolated to tmp_path."""
    src = tmp_path / "in.md"
    src.write_text(md)
    env = {
        "HOME": str(Path.home()),
        "PATH": __import__("os").environ["PATH"],
        "RUN_CODE_CACHE": str(tmp_path / "cache"),
    }
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        ["pandoc", str(src), "--lua-filter", str(FILTER), "-t", "html"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, f"pandoc failed (non-strict should never abort):\n{proc.stderr}"
    return proc.stdout


def test_python_run_shows_source_and_output(tmp_path: Path) -> None:
    html = render("```{.python .run}\nprint('hi', 2 + 2)\n```\n", tmp_path)
    assert "hi 4" in html                    # executed output embedded
    assert "code-output" in html             # tagged as output, not error
    assert 'class="sourceCode python' in html  # source block preserved for display


def test_silent_runs_but_emits_nothing(tmp_path: Path) -> None:
    html = render("```{.python .silent}\nUNIQUE_SILENT_MARKER = 1\n```\n", tmp_path)
    assert "UNIQUE_SILENT_MARKER" not in html   # source removed
    assert "code-output" not in html and "code-error" not in html


def test_plain_block_is_not_executed(tmp_path: Path) -> None:
    html = render("```{.python}\nDISPLAY_ONLY = 1\n```\n", tmp_path)
    assert "DISPLAY_ONLY" in html        # shown as ordinary code
    assert "code-output" not in html and "code-error" not in html


def test_error_rendered_inline_without_aborting(tmp_path: Path) -> None:
    html = render("```{.python .run}\n1 / 0\n```\n", tmp_path)
    assert "code-error" in html
    assert "ZeroDivisionError" in html


def test_preamble_is_prepended_but_not_shown(tmp_path: Path) -> None:
    # preamble makes `math` available without the cell importing it, and the
    # preamble itself must not appear in the displayed source.
    html = render(
        "```{.python .run}\nprint(round(math.pi, 2))\n```\n",
        tmp_path,
        extra_env={"RUN_CODE_PYTHON_PREAMBLE": "import math"},
    )
    assert "3.14" in html          # preamble import resolved at run time
    assert "import math" not in html  # preamble not leaked into the source block


def _lean_usable() -> bool:
    if not shutil.which("lean"):
        return False
    r = subprocess.run(["lean", "--version"], capture_output=True, text=True)
    return r.returncode == 0


@pytest.mark.skipif(not _lean_usable(), reason="no Lean toolchain configured (elan default stable)")
def test_lean_run(tmp_path: Path) -> None:
    html = render("```{.lean .run}\n#eval 2 + 2\n```\n", tmp_path)
    assert "4" in html
    assert "code-output" in html
