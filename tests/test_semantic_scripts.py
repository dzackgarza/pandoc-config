"""Object-valued scripts expand in the authored and MathJax vocabularies."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from pandoc_config.expand_macros import expand_macros, parse_macros

ROOT = Path(__file__).resolve().parents[1]


def test_semantic_scripts_expand_from_generated_mathjax(tmp_path: Path) -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "bin/generate-mathjax-config.py"), "--out-dir", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    generated = json.loads((tmp_path / "mathjax-macros.json").read_text())
    source = r"\units{A/I},\chaincomplex{C},\ascendingfiltration{G},\descendingfiltration{G}"
    expected = r"{{A/I}^{\times}},{{C}^{\bullet}},{{G}^{\bullet}},{{G}_{\bullet}}"
    macros = parse_macros(ROOT / "styles/macros/tier2-mathjax-args.tex")
    assert "".join(expand_macros(source, *macros).split()) == expected
    for name, body in (
        ("units", r"{{#1}^{\times}}"),
        ("chaincomplex", r"{{#1}^{\bullet}}"),
        ("ascendingfiltration", r"{{#1}^{\bullet}}"),
        ("descendingfiltration", r"{{#1}_{\bullet}}"),
    ):
        assert "".join(generated[name][0].split()) == body
        assert generated[name][1] == 1
