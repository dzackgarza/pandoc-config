#!/usr/bin/env python3
"""Contract tests for generated MathJax macro configuration."""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GENERATOR = ROOT / "bin" / "generate-mathjax-config.py"
LEGACY_MACROS = ROOT / "templates" / "css" / "math-macros.html"
GENERATED_JSON = ROOT / "templates" / "css" / "mathjax-macros.json"
PREVIEW_TEMPLATE = ROOT / "templates" / "pandoc_preview_template.html"

passed = 0
failed = 0


def check(name: str) -> None:
    global passed
    passed += 1
    print(f"  [PASS] {name}")


def fail(name: str, detail: str) -> None:
    global failed
    failed += 1
    print(f"  [FAIL] {name}: {detail}")


def generated_macros() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        cp = subprocess.run(
            [
                os.environ.get("PYTHON", "python3"),
                str(GENERATOR),
                "--out-dir",
                str(out_dir),
            ],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        if cp.returncode != 0:
            raise RuntimeError(cp.stderr.strip())
        return json.loads((out_dir / "mathjax-macros.json").read_text())


def assert_macro(macros: dict, name: str, expected) -> None:
    if macros.get(name) == expected:
        check(f"{name} generated")
    else:
        fail(f"{name} generated", repr(macros.get(name)))


def test_domain_aux_files_are_generated() -> None:
    macros = generated_macros()
    assert_macro(macros, "coloneqq", "\\mathrel{\\vcenter{:}}=")
    assert_macro(macros, "qty", ["\\left( {#1} \\right)", 1])
    assert_macro(macros, "cardinality", ["{\\left\\lvert {#1} \\right\\rvert}", 1])
    assert_macro(macros, "disc", ["{\\operatorname{disc}\\left( {#1} \\right)}", 1])
    assert_macro(macros, "discrete", "{\\mathrm{disc}}")
    assert_macro(macros, "discriminantmap", "{\\operatorname{disc}}")
    assert_macro(macros, "padiccompletion", ["{ {#1}_{\\widehat{#2}} }", 2])
    assert_macro(macros, "Set", "{\\mathsf{Set}}")
    assert_macro(macros, "cC", "{\\mathcal{C}}")
    assert_macro(macros, "modsleft", ["{}_{#1}\\Mod", 1])
    assert_macro(macros, "tmf", "\\mathrm{tmf}")
    assert_macro(macros, "Suspendpinf", "\\operatorname{{\\Sigma_+^\\infty}}")
    # Semantic macro contract: the fibre product is one atomic object-valued
    # construction, not a one-argument alias for the decorated multiplication glyph.
    assert_macro(macros, "fiberprod", ["{#1} \\fiberproduct{#2} {#3}", 3])
    assert_macro(macros, "fprod", ["\\fiberprod{#1}{#2}{#3}", 3])
    assert_macro(macros, "lktt", ["{L_{\\mathrm{K3}, #1}}", 1])
    assert_macro(macros, "GSpaces", "{G\\dash\\mathsf{Spaces}}")
    assert_macro(
        macros, "disjointpower", ["{#1}^{\\scriptscriptstyle\\coprod^{#2}}", 2]
    )
    assert_macro(macros, "prodpower", ["{#1}^{\\scriptscriptstyle\\times^{#2}}", 2])
    assert_macro(
        macros, "smashpower", ["{#1}^{\\scriptscriptstyle\\smashprod^{#2}}", 2]
    )
    assert_macro(
        macros, "wedgepower", ["{#1}^{\\scriptscriptstyle\\smashprod^{#2}}", 2]
    )
    assert_macro(
        macros, "tensorpowerk", ["{#1}^{\\scriptscriptstyle\\otimes_{k}^{#2}}", 2]
    )
    assert_macro(
        macros, "fiberpower", ["{#1}^{\\scriptscriptstyle\\fiberproduct{#2}^{#3}}", 3]
    )
    assert_macro(macros, "chaincomplex", ["{ {#1}^{\\bullet} }", 1])
    assert_macro(macros, "ascendingfiltration", ["{ {#1}^{\\bullet} }", 1])
    assert_macro(macros, "descendingfiltration", ["{ {#1}_{\\bullet} }", 1])
    # Unary operations take the object they act on as their argument.
    assert_macro(macros, "opcat", ["{ {#1}^{\\operatorname{op}} }", 1])
    assert_macro(macros, "oppositeof", ["{ {#1}^{\\mathrm{op}} }", 1])
    assert_macro(macros, "dualof", ["{ {#1}^{\\vee} }", 1])
    assert_macro(macros, "doubledualof", ["{ {#1}^{\\vee\\vee} }", 1])
    assert_macro(macros, "inverseof", ["{ {#1}^{-1} }", 1])
    assert_macro(macros, "units", ["{ {#1}^{\\times} }", 1])
    assert_macro(macros, "completionat", ["{ {#1}^{\\wedge}_{#2} }", 2])
    assert_macro(macros, "signature", ["\\operatorname{sign}\\qty{#1}", 1])
    assert_macro(macros, "spinornorm", ["\\operatorname{sn}\\qty{#1}", 1])
    assert_macro(macros, "cyclicgroup", ["C_{#1}", 1])
    assert_macro(macros, "perpin", ["#2^{\\perp_{#1}}", 2])
    if "orthcomp" in macros:
        fail("orthogonal-complement fragment removed", repr(macros["orthcomp"]))
    else:
        check("orthogonal-complement fragment removed")
    for retired in ("sign", "coeq", "cocoeq", "OStab", "OrthObs", "wref"):
        if retired in macros:
            fail(f"{retired} retired", repr(macros[retired]))
        else:
            check(f"{retired} retired")
    assert_macro(
        macros,
        "discriminantkernel",
        ["\\Orth^{\\mathrm{discker}}\\qty{#1}", 1],
    )
    assert_macro(
        macros,
        "discriminantcokernel",
        ["\\Orth^{\\mathrm{disccoker}}\\qty{#1}", 1],
    )
    assert_macro(macros, "spinorkernel", ["\\Orth^{\\mathrm{snker}}\\qty{#1}", 1])
    assert_macro(macros, "spinorcokernel", ["\\Orth^{\\mathrm{sncoker}}\\qty{#1}", 1])
    assert_macro(
        macros,
        "discriminantspinorkernel",
        ["\\Orth^{\\mathrm{discker},\\mathrm{snker}}\\qty{#1}", 1],
    )
    assert_macro(macros, "orthogonalreflectiongroup", ["W\\qty{#1}", 1])
    assert_macro(macros, "monodromygroup", ["\\operatorname{Mon}\\qty{#1}", 1])
    assert_macro(macros, "eichlergroup", ["E\\qty{#1}", 1])
    assert_macro(
        macros, "mirandamorrisongroup", ["\\operatorname{MM}\\qty{#1}", 1]
    )
    assert_macro(macros, "nikulinobstructiongroup", ["I\\qty{#1}", 1])
    assert_macro(macros, "genusgroup", ["g\\qty{#1}", 1])
    if "OStab" in macros:
        fail("retired orthogonal-group alias removed", repr(macros["OStab"]))
    else:
        check("retired orthogonal-group alias removed")
    assert_macro(
        macros,
        "equalizer",
        [
            "\\operatorname{Eq}\\qty{#3,#4} \\longrightarrow #1 "
            "\\mathrel{\\underset{#4}{\\overset{#3}{\\rightrightarrows}}} #2",
            4,
        ],
    )
    assert_macro(
        macros,
        "coequalizer",
        [
            "#1 \\mathrel{\\underset{#4}{\\overset{#3}{\\rightrightarrows}}} #2 "
            "\\longrightarrow \\operatorname{Coeq}\\qty{#3,#4}",
            4,
        ],
    )


def test_native_mathjax_macros_are_not_shadowed() -> None:
    """Differential-definition contract: macros MathJax renders natively
    must never appear in tex.macros — a generated entry would shadow the
    native implementation (worse output for the same source). The LaTeX
    upgrade of such a macro lives in tier3-tex-complex.tex, which never
    feeds MathJax; tier2 documents the deliberate absence."""
    macros = generated_macros()
    # \boldsymbol: native via MathJax's autoloaded boldsymbol extension;
    # upgraded to bm.sty's \bm in LaTeX by tier3-tex-complex.tex.
    for native in ("boldsymbol",):
        if native in macros:
            fail(
                f"{native} shadowed",
                "tex.macros entry would defeat native MathJax rendering",
            )
        else:
            check(f"{native} left to native MathJax rendering")


def test_preview_template_matches_generated_projection() -> None:
    expected = json.loads(GENERATED_JSON.read_text())
    template = PREVIEW_TEMPLATE.read_text()
    match = re.search(r"(?m)^\s*macros:\s*(\{.*\}),\s*$", template)
    if match is None:
        fail("preview macro projection", "generated macros line missing")
        return
    actual = json.loads(match.group(1))
    if actual == expected:
        check("preview macro projection matches canonical generated JSON")
    else:
        fail("preview macro projection", "embedded macro map is stale")


def test_dzg_mathjax_style_compiles_domain_macros() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        tex_path = tmp_dir / "test.tex"
        tex_path.write_text(
            "\n".join(
                [
                    r"\documentclass{article}",
                    r"\usepackage{dzg-mathjax}",
                    r"\begin{document}",
                    r"$\Set\quad\tmf\quad\Suspendpinf\quad\modsleft{R}\quad x\coloneqq\qty{y}\quad\fiberprod{X}{S}{Y}\quad\lktt{2d}\quad\GSpaces\quad\disjointpower{X}{n}\quad\prodpower{X}{n}\quad\smashpower{X}{n}\quad\wedgepower{X}{n}\quad\tensorpowerk{M}{n}\quad\fiberpower{X}{S}{n}\quad\chaincomplex{C}\quad\ascendingfiltration{F}\quad\descendingfiltration{F}\quad\opcat{\cC}\quad\oppositeof{P}\quad\CCstar\quad\localize{f}\quad\doubledualof{V}\quad\inverseof{x}\quad\units{R}\quad\nonzeroof{R}\quad\interiorof{X}\quad\sepclosure{k}\quad\ksep\quad\tiltof{K}\quad\plusconstruction{X}\quad\completionat{X}{p}\quad\procompletion{G}\quad\isoclasses{X}\quad\dualof{V^{2}}$",
                    r"\end{document}",
                ]
            )
        )
        env = os.environ.copy()
        env.update(
            {
                "TEXINPUTS": f".:{ROOT / 'styles'}//:{ROOT / 'styles' / 'macros'}//:",
            }
        )
        cp = subprocess.run(
            [
                "pdflatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                "-output-directory",
                str(tmp_dir),
                str(tex_path),
            ],
            capture_output=True,
            text=True,
            cwd=ROOT,
            env=env,
        )
        if cp.returncode == 0 and (tmp_dir / "test.pdf").exists():
            check("dzg-mathjax style compiles domain macros")
        else:
            fail("dzg-mathjax style compiles domain macros", cp.stdout + cp.stderr)


def test_legacy_mathjax_injection_defines_required_shims() -> None:
    content = LEGACY_MACROS.read_text()
    if r"\newcommand{\coloneqq}" in content:
        check("legacy coloneqq shim generated")
    else:
        fail("legacy coloneqq shim generated", "missing \\newcommand{\\coloneqq}")
    if r"\newcommand{\qty}[1]" in content:
        check("legacy qty shim generated")
    else:
        fail("legacy qty shim generated", "missing \\newcommand{\\qty}[1]")
    expected_fiberprod = r"\newcommand{\fiberprod}[3]{{#1} \fiberproduct{#2} {#3}}"
    if expected_fiberprod in content:
        check("legacy fiberprod semantic signature generated")
    else:
        fail("legacy fiberprod semantic signature", f"missing {expected_fiberprod}")


def main() -> None:
    test_domain_aux_files_are_generated()
    test_native_mathjax_macros_are_not_shadowed()
    test_preview_template_matches_generated_projection()
    test_dzg_mathjax_style_compiles_domain_macros()
    test_legacy_mathjax_injection_defines_required_shims()
    total = passed + failed
    print(f"\n{'=' * 50}")
    print(f"  {passed}/{total} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
