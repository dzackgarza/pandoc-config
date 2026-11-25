#!/usr/bin/env python3
"""Contract tests for generated MathJax macro configuration."""

import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GENERATOR = ROOT / "bin" / "generate-mathjax-config.py"
LEGACY_MACROS = ROOT / "templates" / "css" / "math-macros.html"
GENERATED_JSON = ROOT / "templates" / "css" / "mathjax-macros.json"
TEMPLATES = ROOT / "templates"
MATHJAX_CONFIG_PARTIAL = TEMPLATES / "mathjax-config.html"
PREVIEW_TEMPLATE = TEMPLATES / "pandoc_preview_template.html"
REVEALJS_TEMPLATE = TEMPLATES / "pandoc_revealjs_template.html"
# Each HTML writer whose template includes the MathJax configuration partial.
# zettlr-pandoc exports with these templates (PANDOC_DIRECTORY_TEMPLATES).
HTML_WRITER_TEMPLATES = {
    "html": PREVIEW_TEMPLATE,
    "html5": PREVIEW_TEMPLATE,
    "html4": PREVIEW_TEMPLATE,
    "s5": TEMPLATES / "pandoc_s5_template.html",
    "slidy": TEMPLATES / "pandoc_slidy_template.html",
    "slideous": TEMPLATES / "pandoc_slideous_template.html",
    "dzslides": TEMPLATES / "pandoc_dzslides_template.html",
    "chunkedhtml": TEMPLATES / "pandoc_chunkedhtml_template.html",
}
# Each TeX writer and the template that loads the macro style for it.
TEX_WRITER_TEMPLATES = {
    "latex": TEMPLATES / "research_draft.tex",
    "pdf": TEMPLATES / "research_draft.tex",
    "beamer": TEMPLATES / "research_beamer.tex",
}
TEXINPUTS = (
    f".:{ROOT / 'styles'}//:{ROOT / 'styles' / 'macros'}//:"
    f"{ROOT / 'styles' / 'preambles'}//:{ROOT / 'config'}//:"
)
# A slide document whose formulas use macros of styles/macros: a TeX writer
# that does not define one stops with "Undefined control sequence".
TEX_DOCUMENT = (
    "---\ntitle: Macros\n---\n\n# A slide\n\n"
    "A formula $\\Hom(\\ZZ, \\QQ)$ and $\\fiberprod{X}{S}{Y}$.\n"
)
# A document with a formula: Pandoc sets the math variables of a template
# only for a document that has math.
MATH_DOCUMENT = "---\ntitle: Macros\n---\n\nA formula $\\ZZ$.\n"
MATHJAX_URL = "file:///opt/mathjax/tex-chtml.js"
ROOT_URL = "file:///opt/mathjax"
FONTS_URL = "file:///opt/mathjax/fonts"
LOCAL_MATHJAX = [f"mathjax-root={ROOT_URL}", f"mathjax-fonts={FONTS_URL}"]
# The macro definitions as the first input of a Markdown reader, for each
# writer without a template of this repository that loads the macros.
READER_INPUT = TEMPLATES / "css" / "math-macros.md"
MACROS_FILTER = ROOT / "filters" / "math-macros.lua"
CONTEXT_MATHML_FILTER = ROOT / "filters" / "context-mathml.lua"
CONTEXT_TEMPLATE = TEMPLATES / "pandoc_context_template.tex"
# A title in YAML: a % title block holds only in the first input, and the
# macro input is first.
READER_DOCUMENT = (
    "---\ntitle: Macros\n---\n\n"
    "A formula $\\Hom(\\ZZ, \\QQ)$ and $\\fiberprod{X}{S}{Y}$.\n\n"
    "$$\\Hom(\\ZZ, \\QQ) = \\frac{a}{b}$$\n"
)

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
                sys.executable,
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
    # One name per meaning (d823b92): \Set is \Sets and \cC is \mcc.
    assert_macro(macros, "Sets", "{\\mathsf{Set}}")
    assert_macro(macros, "mcc", "{\\mathcal{C}}")
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
    # One name per meaning (#10): \Sp is the symplectic group and \Spectra the
    # category of spectra; \diagonal is an object and takes no argument.
    assert_macro(macros, "Sp", "{\\operatorname{Sp}}")
    assert_macro(macros, "Spectra", "{\\mathsf{Sp}}")
    assert_macro(macros, "Symp", "{\\operatorname{Symp}}")
    assert_macro(macros, "diagonal", "\\Delta")
    assert_macro(macros, "diagonalfunctor", "\\Delta")
    assert_macro(macros, "divisorof", "\\operatorname{div}")
    assert_macro(macros, "divisibility", "\\operatorname{div}")
    assert_macro(macros, "semistable", "{\\mathrm{ss}}")
    # A LaTeX primitive keeps its own meaning: the projection defines no
    # \bar, \hat, \div or \ss.
    for retired in (
        "sign", "coeq", "cocoeq", "OStab", "OrthObs", "wref",
        "otherbar", "Diagonal", "bar", "hat", "div", "ss",
    ):
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


def template_matches_generated_projection(name: str, template_path: Path) -> None:
    expected = json.loads(GENERATED_JSON.read_text())
    template = template_path.read_text()
    matches = re.findall(r"(?m)^\s*macros:\s*(\{.*\}),\s*$", template)
    if len(matches) != 1:
        fail(f"{name} macro projection", f"{len(matches)} generated macros lines, expected 1")
        return
    actual = json.loads(matches[0])
    if actual == expected:
        check(f"{name} macro projection matches canonical generated JSON")
    else:
        fail(f"{name} macro projection", "embedded macro map is stale")


def test_mathjax_config_matches_generated_projection() -> None:
    template_matches_generated_projection("MathJax configuration", MATHJAX_CONFIG_PARTIAL)


def test_html_templates_hold_no_macro_map_of_their_own() -> None:
    """The macro map of an HTML writer has one copy: the partial."""
    for path in sorted(set(HTML_WRITER_TEMPLATES.values())):
        text = path.read_text()
        if "$mathjax-config.html()$" in text and "macros:" not in text:
            check(f"{path.name} includes the MathJax configuration partial")
        else:
            fail(f"{path.name} MathJax configuration", "not the partial alone")


def test_revealjs_template_matches_generated_projection() -> None:
    template_matches_generated_projection("reveal.js", REVEALJS_TEMPLATE)


def rendered(writer: str, template_path: Path, variables: list[str]) -> str:
    """The standalone page that Pandoc writes with a template of this repository.

    For chunkedhtml, which writes a folder of pages, the page with the formula.
    """
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "out"
        cp = subprocess.run(
            [
                "pandoc",
                "--from=markdown",
                f"--to={writer}",
                "--standalone",
                f"--template={template_path}",
                f"--math-method=mathjax:{MATHJAX_URL}",
                *[f"--variable={variable}" for variable in variables],
                f"--output={output}",
            ],
            input=MATH_DOCUMENT,
            capture_output=True,
            text=True,
        )
        if cp.returncode != 0:
            raise RuntimeError(cp.stderr.strip())
        if output.is_dir():
            pages = [p.read_text() for p in sorted(output.glob("*.html"))]
            return next(page for page in pages if "\\ZZ" in page)
        return output.read_text()


def test_html_templates_configure_mathjax_before_it_loads() -> None:
    for writer, template in HTML_WRITER_TEMPLATES.items():
        page = rendered(writer, template, [])
        config = page.find("window.MathJax = {")
        script = page.find(MATHJAX_URL)
        if 0 <= config < script and '"ZZ":' in page[config:script]:
            check(f"{writer} page defines the macros before it loads MathJax")
        else:
            fail(f"{writer} page MathJax order", f"config at {config}, script at {script}")
        if "mathjax:" not in page[config:script] and "fonts:" not in page[config:script]:
            check(f"{writer} page names no place of a local MathJax when none is given")
        else:
            fail(f"{writer} page MathJax places", "a loader path without its variable")

        local = rendered(writer, template, LOCAL_MATHJAX)
        for name, text in {
            "takes the folder of MathJax from the mathjax-root variable": (
                f'mathjax: "{ROOT_URL}",'
            ),
            "takes its fonts from the mathjax-fonts variable": f'fonts: "{FONTS_URL}",',
        }.items():
            if text in local:
                check(f"{writer} page {name}")
            else:
                fail(f"{writer} page {name}", f"{text!r} is not in the page")


def tex_program(name: str) -> Path:
    """The program in the bin folder of the TeX distribution of kpsewhich.

    mtxrun and context find the tree of their distribution from the path by
    which they run (SELFAUTODIR). Through a link in /usr/bin they find no
    texmfcnf.lua and stop with "unknown script 'mtx-context.lua'"; kpsewhich
    gives the folder of the distribution (SELFAUTOLOC).
    """
    found = subprocess.run(
        ["kpsewhich", "-var-value=SELFAUTOLOC"], capture_output=True, text=True, check=True
    )
    return Path(found.stdout.strip()) / name


def test_reader_input_matches_generated_projection() -> None:
    """templates/css/math-macros.md is the output of the generator for the macro sources."""
    with tempfile.TemporaryDirectory() as tmp:
        cp = subprocess.run(
            [sys.executable, str(GENERATOR), "--out-dir", tmp],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        if cp.returncode != 0:
            fail("reader input generated", cp.stderr.strip())
            return
        expected = (Path(tmp) / "math-macros.md").read_text()
    if READER_INPUT.read_text() == expected:
        check("math-macros.md matches the generated projection")
    else:
        fail("math-macros.md", "stale; run just generate-math-macros")


def converted(
    writer: str, filters: list[Path], tmp_dir: Path, template: Path | None = None
) -> Path:
    """The file in tmp_dir that Pandoc writes from the reader input and READER_DOCUMENT."""
    document = tmp_dir / "document.md"
    document.write_text(READER_DOCUMENT)
    output = tmp_dir / f"out.{writer}"
    cp = subprocess.run(
        [
            "pandoc",
            "--from=markdown",
            f"--to={writer}",
            "--standalone",
            *([f"--template={template}"] if template is not None else []),
            *[f"--lua-filter={f}" for f in filters],
            f"--output={output}",
            str(READER_INPUT),
            str(document),
        ],
        capture_output=True,
        text=True,
    )
    if cp.returncode != 0:
        raise RuntimeError(f"pandoc -t {writer}: {cp.stderr.strip()}")
    return output


def zip_text(path: Path, member: str) -> str:
    with zipfile.ZipFile(path) as archive:
        return "".join(
            archive.read(name).decode()
            for name in archive.namelist()
            if re.fullmatch(member, name)
        )


def test_converting_writers_get_the_expansion_of_each_macro() -> None:
    """A writer that converts TeX math gets the expansion of \\Hom(\\ZZ, \\QQ) and \\fiberprod."""
    mathml_hom = r'<(mml:)?mi (mml:)?mathvariant="normal">Hom</(mml:)?mi>'
    mathml_z = r'<(mml:)?mi (mml:)?mathvariant="bold-italic">\U0001d481</(mml:)?mi>'
    mathml_fiber = r"<(mml:)?munder><(mml:)?mo>×</(mml:)?mo><(mml:)?mi>S</(mml:)?mi>"
    # The text runs of the OMML of Word and PowerPoint, one after the other.
    omml = [r"Hom\(Z,Q\)", r"X×SY"]
    expected = {
        "docx": (r"word/document\.xml", omml),
        "pptx": (r"ppt/slides/slide\d+\.xml", omml),
        "odt": (r"Formula-\d+/content\.xml", [mathml_hom, mathml_z, mathml_fiber]),
        "epub3": (r"EPUB/text/ch\d+\.xhtml", [mathml_hom, mathml_z, mathml_fiber]),
        "jats": (None, [mathml_hom, mathml_z, mathml_fiber]),
        "docbook5": (None, [mathml_hom, mathml_z, mathml_fiber]),
        "typst": (None, [r'"Hom"\\\(upright\(bold\(Z\)\)', r"X times_S Y"]),
        "ms": (None, [r'"Hom" \( roman \{bold \{Z\}\}', r"X times from S Y"]),
    }
    for writer, (member, patterns) in expected.items():
        with tempfile.TemporaryDirectory() as tmp:
            output = converted(writer, [MACROS_FILTER], Path(tmp))
            text = zip_text(output, member) if member is not None else output.read_text()
            if writer in ("docx", "pptx"):
                text = "".join(re.findall(r"<m:t>([^<]*)</m:t>", text))
        missing = [p for p in patterns if re.search(p, text) is None]
        if missing:
            fail(f"{writer} gets the expansion of the macros", f"no match for {missing}")
        else:
            check(f"{writer} gets the expansion of \\Hom(\\ZZ, \\QQ) and \\fiberprod")


def test_no_writer_gets_a_raw_macro_or_a_definition() -> None:
    """For each writer of Pandoc the output holds no \\ZZ and no \\newcommand of the reader input."""
    skipped = {
        # No document: the output is the bibliography of the document.
        "biblatex",
        "bibtex",
        "csljson",
        # A folder of pages; chunkedhtml has a template of this repository.
        "chunkedhtml",
        # A TeX writer gets the macros from the style that its template loads
        # (test_tex_templates_compile_macros_with_pdflatex), not from the
        # reader input, and it keeps raw TeX.
        *TEX_WRITER_TEMPLATES,
    }
    writers = subprocess.run(
        ["pandoc", "--list-output-formats"], capture_output=True, text=True, check=True
    ).stdout.split()
    for writer in writers:
        if writer in skipped:
            continue
        with tempfile.TemporaryDirectory() as tmp:
            output = converted(writer, [MACROS_FILTER], Path(tmp))
            data = output.read_bytes()
            if zipfile.is_zipfile(output):
                with zipfile.ZipFile(output) as archive:
                    data = b"".join(archive.read(name) for name in archive.namelist())
        leaks = [token for token in (b"\\ZZ", b"newcommand", b"math-macros") if token in data]
        if leaks:
            fail(f"{writer} output", f"holds {leaks}")
        else:
            check(f"{writer} output holds no raw macro and no definition")


def test_context_template_typesets_the_macros() -> None:
    """ConTeXt typesets the expansion of the macros as the MathML of texmath."""
    with tempfile.TemporaryDirectory() as tmp:
        tex = converted(
            "context", [MACROS_FILTER, CONTEXT_MATHML_FILTER], Path(tmp), CONTEXT_TEMPLATE
        )
        context_typesets(tex)


def context_typesets(tex: Path) -> None:
    cp = subprocess.run(
        [str(tex_program("context")), "--batchmode", "--nonstopmode", tex.name],
        capture_output=True,
        text=True,
        cwd=tex.parent,
    )
    pdf = tex.with_suffix(".pdf")
    if cp.returncode != 0 or not pdf.exists():
        fail("context compiles the macros", (cp.stdout + cp.stderr)[-1500:])
        return
    text = subprocess.run(
        ["pdftotext", str(pdf), "-"], capture_output=True, text=True, check=True
    ).stdout
    # ConTeXt sets the bold Z and Q of tier1 as the mathematical bold letters
    # of Unicode; NFKC gives them as Z and Q.
    plain = unicodedata.normalize("NFKC", text)
    if "Hom(Z, Q)" in plain and "×" in plain:
        check("context template typesets \\Hom(\\ZZ, \\QQ) and \\fiberprod")
    else:
        fail("context template typesets the macros", plain[:300])


def test_context_template_defines_each_function_of_the_mathml_module() -> None:
    """Each command that x-mathml writes for an <mi> is defined with the template."""
    found = subprocess.run(["kpsewhich", "x-mathml.lmt"], capture_output=True, text=True)
    module = Path(found.stdout.strip())
    if found.returncode != 0 or not module.is_file():
        fail("x-mathml.lmt", "kpsewhich does not find the mathml module of ConTeXt")
        return
    source = module.read_text()
    table = re.search(r"local i_replacements = \{(.*?)\n\}", source, re.S)
    if table is None:
        fail("x-mathml.lmt", "no i_replacements table")
        return
    commands = sorted(set(re.findall(r'= "\\\\([A-Za-z]+)"', table.group(1))))
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        document = tmp_dir / "document.md"
        document.write_text(
            "".join(
                f"\\ifdefined\\{c}\\else MISSING-{c}\\par\\fi\n\n" for c in commands
            )
        )
        tex = tmp_dir / "functions.tex"
        subprocess.run(
            [
                "pandoc",
                "--from=markdown",
                "--to=context",
                "--standalone",
                f"--template={CONTEXT_TEMPLATE}",
                f"--output={tex}",
                str(document),
            ],
            check=True,
        )
        cp = subprocess.run(
            [str(tex_program("context")), "--batchmode", "--nonstopmode", tex.name],
            capture_output=True,
            text=True,
            cwd=tmp_dir,
        )
        if cp.returncode != 0:
            fail("context function check", (cp.stdout + cp.stderr)[-1500:])
            return
        text = subprocess.run(
            ["pdftotext", str(tex.with_suffix(".pdf")), "-"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    missing = re.findall(r"MISSING-(\w+)", text)
    if missing:
        fail("context template functions", f"x-mathml writes undefined {missing}")
    else:
        check(f"context template defines each of the {len(commands)} functions of x-mathml")


def test_context_mathml_filter_refuses_a_formula_that_texmath_cannot_convert() -> None:
    cp = subprocess.run(
        [
            "pandoc",
            "--from=markdown",
            "--to=context",
            f"--lua-filter={CONTEXT_MATHML_FILTER}",
        ],
        input="A $\\vcenter{x}$.\n",
        capture_output=True,
        text=True,
    )
    if cp.returncode != 0 and "cannot convert the formula \\vcenter{x}" in cp.stderr:
        check("context-mathml.lua stops at a formula that texmath cannot convert")
    else:
        fail("context-mathml.lua refusal", f"exit {cp.returncode}: {cp.stderr[-300:]}")


def test_tex_templates_compile_macros_with_pdflatex() -> None:
    """Each TeX writer typesets the macros of styles/macros through its template."""
    env = os.environ.copy()
    env["TEXINPUTS"] = TEXINPUTS
    for writer, template in TEX_WRITER_TEMPLATES.items():
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            tex = tmp_dir / "slides.tex"
            pdf = tmp_dir / "slides.pdf"
            # pandoc -t pdf runs pdflatex itself; -t latex and -t beamer give the
            # TeX file, which pdflatex then compiles.
            target = pdf if writer == "pdf" else tex
            cp = subprocess.run(
                [
                    "pandoc",
                    "--from=markdown",
                    f"--to={writer}",
                    "--standalone",
                    f"--template={template}",
                    "--pdf-engine=pdflatex",
                    f"--output={target}",
                ],
                input=TEX_DOCUMENT,
                capture_output=True,
                text=True,
                cwd=tmp_dir,
                env=env,
            )
            if cp.returncode == 0 and writer != "pdf":
                cp = subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex.name],
                    capture_output=True,
                    text=True,
                    cwd=tmp_dir,
                    env=env,
                )
            if cp.returncode != 0 or not pdf.exists():
                fail(f"{writer} template compiles the macros", (cp.stdout + cp.stderr)[-1500:])
                continue
            text = subprocess.run(
                ["pdftotext", str(pdf), "-"], capture_output=True, text=True, check=True
            ).stdout
            # \Hom(\ZZ, \QQ) is Hom(Z, Q), the bold Z and Q of tier1.
            if "Hom(Z, Q)" in text:
                check(f"{writer} template typesets \\Hom(\\ZZ, \\QQ) with pdflatex")
            else:
                fail(f"{writer} template typesets the macros", text[:300])


def test_revealjs_template_loads_mathjax_through_the_mathjax3_plugin() -> None:
    page = rendered("revealjs", REVEALJS_TEMPLATE, LOCAL_MATHJAX)
    expectations = {
        "the MathJax 3 plugin is a plugin of the deck": "RevealMath.MathJax3,",
        "the plugin loads the MathJax of the export": f"mathjax: '{MATHJAX_URL}'",
        "the deck takes the folder of MathJax from the mathjax-root variable": (
            f"mathjax: '{ROOT_URL}',"
        ),
        "the deck takes its fonts from the mathjax-fonts variable": f"fonts: '{FONTS_URL}',",
        "the deck has the macros": '"ZZ":',
    }
    for name, text in expectations.items():
        if text in page:
            check(name)
        else:
            fail(name, f"{text!r} is not in the deck")
    if "$" in re.sub(r"(?s)macros: \{.*?\},\n", "", page.split("mathjax3: {")[1].split("},\n        },")[0]):
        fail("reveal.js MathJax block", "an unfilled template variable")
    else:
        check("the MathJax block of the deck has no unfilled template variable")

    plain = rendered("revealjs", REVEALJS_TEMPLATE, [])
    places = plain.split("mathjax3: {")[1].split("tex: {")[0].split("paths: {")[1]
    if "mathjax:" not in places and "fonts:" not in places:
        check("the deck names no place of a local MathJax when none is given")
    else:
        fail("reveal.js MathJax places", "a loader path without its variable")


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
                    r"$\Sets\quad\tmf\quad\Suspendpinf\quad\modsleft{R}\quad x\coloneqq\qty{y}\quad\fiberprod{X}{S}{Y}\quad\lktt{2d}\quad\GSpaces\quad\disjointpower{X}{n}\quad\prodpower{X}{n}\quad\smashpower{X}{n}\quad\wedgepower{X}{n}\quad\tensorpowerk{M}{n}\quad\fiberpower{X}{S}{n}\quad\chaincomplex{C}\quad\ascendingfiltration{F}\quad\descendingfiltration{F}\quad\opcat{\mcc}\quad\oppositeof{P}\quad\CCstar\quad\localize{f}\quad\doubledualof{V}\quad\inverseof{x}\quad\units{R}\quad\nonzeroof{R}\quad\interiorof{X}\quad\sepclosure{k}\quad\ksep\quad\tiltof{K}\quad\plusconstruction{X}\quad\completionat{X}{p}\quad\procompletion{G}\quad\isoclasses{X}\quad\dualof{V^{2}}$",
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
    test_mathjax_config_matches_generated_projection()
    test_html_templates_hold_no_macro_map_of_their_own()
    test_revealjs_template_matches_generated_projection()
    test_html_templates_configure_mathjax_before_it_loads()
    test_reader_input_matches_generated_projection()
    test_converting_writers_get_the_expansion_of_each_macro()
    test_no_writer_gets_a_raw_macro_or_a_definition()
    test_context_template_typesets_the_macros()
    test_context_template_defines_each_function_of_the_mathml_module()
    test_context_mathml_filter_refuses_a_formula_that_texmath_cannot_convert()
    test_tex_templates_compile_macros_with_pdflatex()
    test_revealjs_template_loads_mathjax_through_the_mathjax3_plugin()
    test_dzg_mathjax_style_compiles_domain_macros()
    test_legacy_mathjax_injection_defines_required_shims()
    total = passed + failed
    print(f"\n{'=' * 50}")
    print(f"  {passed}/{total} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
