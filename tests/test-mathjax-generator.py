#!/usr/bin/env python3
"""Contract tests for generated MathJax macro configuration."""

import importlib.util
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
MACROS_README = ROOT / "styles" / "macros" / "README.md"
LEGACY_MACROS = ROOT / "templates" / "css" / "math-macros.html"
GENERATED_JSON = ROOT / "templates" / "css" / "mathjax-macros.json"
TEMPLATES = ROOT / "templates"
MATHJAX_CONFIG_PARTIAL = TEMPLATES / "mathjax-config.html"
PREVIEW_TEMPLATE = TEMPLATES / "pandoc_preview_template.html"
REVEALJS_TEMPLATE = TEMPLATES / "pandoc_revealjs_template.html"
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
TEX_WRITER_TEMPLATES = {
    "latex": TEMPLATES / "research_draft.tex",
    "pdf": TEMPLATES / "research_draft.tex",
    "beamer": TEMPLATES / "research_beamer.tex",
}
TEXINPUTS = (
    f".:{ROOT / 'styles'}//:{ROOT / 'styles' / 'macros'}//:"
    f"{ROOT / 'styles' / 'preambles'}//:{ROOT / 'config'}//:"
)
TEX_DOCUMENT = (
    "---\ntitle: Macros\n---\n\n# A slide\n\n"
    "A formula $\\Hom(\\ZZ, \\QQ)$ and $\\fiberprod{X}{S}{Y}$.\n"
)
MATH_DOCUMENT = "---\ntitle: Macros\n---\n\nA formula $\\ZZ$.\n"
MATHJAX_URL = "file:///opt/mathjax/tex-chtml.js"
ROOT_URL = "file:///opt/mathjax"
FONTS_URL = "file:///opt/mathjax/fonts"
LOCAL_MATHJAX = [f"mathjax-root={ROOT_URL}", f"mathjax-fonts={FONTS_URL}"]
READER_INPUT = TEMPLATES / "css" / "math-macros.md"
MACROS_FILTER = ROOT / "filters" / "math-macros.lua"
CONTEXT_MATHML_FILTER = ROOT / "filters" / "context-mathml.lua"
CONTEXT_TEMPLATE = TEMPLATES / "pandoc_context_template.tex"
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


def generator_module():
    spec = importlib.util.spec_from_file_location("generate_mathjax_config", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_macro(macros: dict, name: str, expected) -> None:
    if macros.get(name) == expected:
        check(f"{name} generated")
    else:
        fail(f"{name} generated", repr(macros.get(name)))


def test_domain_aux_files_are_generated() -> None:
    macros = generated_macros()
    assert_macro(macros, "coloneqq", "\\vcentcolon\\mathrel{\\mkern-1.2mu}=")
    assert_macro(macros, "qty", ["\\left( #1 \\right)", 1])
    assert_macro(macros, "cardinality", ["{\\left\\lvert {#1} \\right\\rvert}", 1])
    assert_macro(macros, "disc", ["{\\operatorname{disc}\\left( {#1} \\right)}", 1])
    assert_macro(macros, "discrete", "{\\mathrm{disc}}")
    assert_macro(macros, "discriminantmap", "{\\operatorname{disc}}")
    assert_macro(macros, "padiccompletion", ["{ {#1}_{\\widehat{#2}} }", 2])
    assert_macro(macros, "Sets", "{\\mathsf{Set}}")
    assert_macro(macros, "mcc", "{\\mathcal{C}}")
    assert_macro(macros, "modsleft", ["{}_{#1}\\Mod", 1])
    assert_macro(macros, "tmf", "\\mathrm{tmf}")
    assert_macro(macros, "Suspendpinf", "\\operatorname{{\\Sigma_+^\\infty}}")
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
    assert_macro(macros, "Sp", "{\\operatorname{Sp}}")
    assert_macro(macros, "Spectra", "{\\mathsf{Sp}}")
    assert_macro(macros, "Symp", "{\\operatorname{Symp}}")
    assert_macro(macros, "diagonal", "\\Delta")
    assert_macro(macros, "diagonalfunctor", "\\Delta")
    assert_macro(macros, "divisorof", "\\operatorname{div}")
    assert_macro(macros, "divisibility", "\\operatorname{div}")
    assert_macro(macros, "semistable", "{\\mathrm{ss}}")
    for retired in (
        "sign",
        "coeq",
        "cocoeq",
        "OStab",
        "OrthObs",
        "wref",
        "otherbar",
        "Diagonal",
        "bar",
        "hat",
        "div",
        "ss",
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
    assert_macro(macros, "mirandamorrisongroup", ["\\operatorname{MM}\\qty{#1}", 1])
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


RENDERERS = ("LaTeX", "MathJax")


def declared_native_overrides() -> dict[str, set[str]]:
    """For each renderer, the commands of the table of the section
    "Overrides" of MACROS_README whose second column names it."""
    text = MACROS_README.read_text()
    section = re.search(r"(?ms)^## Overrides\n(.*?)(?=^## |\Z)", text)
    if section is None:
        raise RuntimeError(f"{MACROS_README} has no section '## Overrides'")
    declared: dict[str, set[str]] = {renderer: set() for renderer in RENDERERS}
    for name, cell in re.findall(
        r"(?m)^\| `\\([A-Za-z@]+)` \| ([^|]*) \|", section.group(1)
    ):
        renderers = {part.strip() for part in cell.split(",")}
        if not renderers or not renderers <= set(RENDERERS):
            raise RuntimeError(
                f"the row of \\{name} names no renderer of {RENDERERS}: {cell!r}"
            )
        for renderer in renderers:
            declared[renderer].add(name)
    return declared


def mathjax_overrides(names: list[str]) -> set[str] | str:
    """The names that MathJax 4 of node_modules defines with the
    configuration of the preview template and no macros of the tree."""
    cp = subprocess.run(
        ["bun", str(HERE / "mathjax-native-commands.ts")],
        input=json.dumps(names),
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    if cp.returncode != 0:
        return cp.stdout + cp.stderr
    return set(json.loads(cp.stdout))


def test_tree_overrides_only_the_declared_native_commands() -> None:
    """A macro of the projection that changes the meaning of a command that
    the document already has, at the load of dzg-macros under dzg-unified
    and amsart, is a LaTeX override. A macro of the projection whose name
    MathJax already defines is a MathJax override. For each renderer, the
    set of overrides equals the rows of the table of styles/macros/README.md
    that name it. The shims of the generator are MathJax entries and no
    macro of the tree."""
    shims = {shim.name for shim in generator_module().MATHJAX_SHIMS}
    names = sorted(set(generated_macros()) - shims)
    declared = declared_native_overrides()
    found = mathjax_overrides(names)
    if isinstance(found, str):
        fail("MathJax overrides of native commands", found[-2000:])
    else:
        compare_overrides("MathJax", found, declared["MathJax"])
    saves = "\n".join(
        f"\\ifcsname {n}\\endcsname\\expandafter\\let\\csname dzgnative@{n}\\expandafter\\endcsname\\csname {n}\\endcsname\\fi"
        for n in names
    )
    compares = "\n".join(
        f"\\ifcsname dzgnative@{n}\\endcsname"
        f"\\expandafter\\let\\expandafter\\dzg@native\\csname dzgnative@{n}\\endcsname"
        f"\\expandafter\\let\\expandafter\\dzg@tree\\csname {n}\\endcsname"
        f"\\ifx\\dzg@native\\dzg@tree\\else\\typeout{{DZG-OVERRIDE:{n}}}\\fi\\fi"
        for n in names
    )
    document = "\n".join(
        [
            r"\documentclass{amsart}",
            r"\makeatletter",
            f"\\def\\dzg@savenative{{{saves}}}",
            f"\\def\\dzg@comparenative{{{compares}\\typeout{{DZG-OVERRIDES-CHECKED}}}}",
            r"\AddToHook{package/dzg-macros/before}{\dzg@savenative}",
            r"\AddToHook{package/dzg-macros/after}{\dzg@comparenative}",
            r"\makeatother",
            r"\usepackage{dzg-unified}",
            r"\begin{document}x\end{document}",
        ]
    )
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        (tmp_dir / "overrides.tex").write_text(document)
        cp = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "overrides.tex"],
            capture_output=True,
            text=True,
            cwd=tmp_dir,
            env={**os.environ, "TEXINPUTS": TEXINPUTS},
        )
        log = (tmp_dir / "overrides.log").read_text(errors="replace")
    if cp.returncode != 0 or "DZG-OVERRIDES-CHECKED" not in log:
        fail("overrides of native commands", cp.stdout[-2000:])
        return
    compare_overrides(
        "LaTeX", set(re.findall(r"DZG-OVERRIDE:([A-Za-z@]+)", log)), declared["LaTeX"]
    )


def compare_overrides(renderer: str, overrides: set[str], declared: set[str]) -> None:
    if overrides - declared:
        fail(
            f"the tree overrides only the declared native commands of {renderer}",
            "undeclared: " + ", ".join(sorted(overrides - declared)),
        )
    else:
        check(
            f"the tree overrides only the native commands of {renderer} of the README table"
        )
    if declared - overrides:
        fail(
            f"each declared override of {renderer} overrides a native command",
            "no override: " + ", ".join(sorted(declared - overrides)),
        )
    else:
        check(
            f"each {renderer} row of the README table is a native command that the tree overrides"
        )


def template_matches_generated_projection(name: str, template_path: Path) -> None:
    expected = json.loads(GENERATED_JSON.read_text())
    template = template_path.read_text()
    matches = re.findall(r"(?m)^\s*macros:\s*(\{.*\}),\s*$", template)
    if len(matches) != 1:
        fail(
            f"{name} macro projection",
            f"{len(matches)} generated macros lines, expected 1",
        )
        return
    actual = json.loads(matches[0])
    if actual == expected:
        check(f"{name} macro projection matches canonical generated JSON")
    else:
        fail(f"{name} macro projection", "embedded macro map is stale")


def test_mathjax_config_matches_generated_projection() -> None:
    template_matches_generated_projection(
        "MathJax configuration", MATHJAX_CONFIG_PARTIAL
    )


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
            fail(
                f"{writer} page MathJax order",
                f"config at {config}, script at {script}",
            )
        if (
            "mathjax:" not in page[config:script]
            and "fonts:" not in page[config:script]
        ):
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
        ["kpsewhich", "-var-value=SELFAUTOLOC"],
        capture_output=True,
        text=True,
        check=True,
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
            text = (
                zip_text(output, member) if member is not None else output.read_text()
            )
            if writer in ("docx", "pptx"):
                text = "".join(re.findall(r"<m:t>([^<]*)</m:t>", text))
        missing = [p for p in patterns if re.search(p, text) is None]
        if missing:
            fail(
                f"{writer} gets the expansion of the macros", f"no match for {missing}"
            )
        else:
            check(f"{writer} gets the expansion of \\Hom(\\ZZ, \\QQ) and \\fiberprod")


def test_no_writer_gets_a_raw_macro_or_a_definition() -> None:
    """For each writer of Pandoc the output holds no \\ZZ and no \\newcommand of the reader input."""
    skipped = {
        "biblatex",
        "bibtex",
        "csljson",
        "chunkedhtml",
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
        leaks = [
            token for token in (b"\\ZZ", b"newcommand", b"math-macros") if token in data
        ]
        if leaks:
            fail(f"{writer} output", f"holds {leaks}")
        else:
            check(f"{writer} output holds no raw macro and no definition")


def test_context_template_typesets_the_macros() -> None:
    """ConTeXt typesets the expansion of the macros as the MathML of texmath."""
    with tempfile.TemporaryDirectory() as tmp:
        tex = converted(
            "context",
            [MACROS_FILTER, CONTEXT_MATHML_FILTER],
            Path(tmp),
            CONTEXT_TEMPLATE,
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
    plain = unicodedata.normalize("NFKC", text)
    if "Hom(Z, Q)" in plain and "×" in plain:
        check("context template typesets \\Hom(\\ZZ, \\QQ) and \\fiberprod")
    else:
        fail("context template typesets the macros", plain[:300])


def test_context_template_defines_each_function_of_the_mathml_module() -> None:
    """Each command that x-mathml writes for an <mi> is defined with the template."""
    found = subprocess.run(
        ["kpsewhich", "x-mathml.lmt"], capture_output=True, text=True
    )
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
        check(
            f"context template defines each of the {len(commands)} functions of x-mathml"
        )


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
                    [
                        "pdflatex",
                        "-interaction=nonstopmode",
                        "-halt-on-error",
                        tex.name,
                    ],
                    capture_output=True,
                    text=True,
                    cwd=tmp_dir,
                    env=env,
                )
            if cp.returncode != 0 or not pdf.exists():
                fail(
                    f"{writer} template compiles the macros",
                    (cp.stdout + cp.stderr)[-1500:],
                )
                continue
            text = subprocess.run(
                ["pdftotext", str(pdf), "-"], capture_output=True, text=True, check=True
            ).stdout
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
    if "$" in re.sub(
        r"(?s)macros: \{.*?\},\n",
        "",
        page.split("mathjax3: {")[1].split("},\n        },")[0],
    ):
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
        check("legacy qty projection generated")
    else:
        fail("legacy qty projection generated", "missing \\newcommand{\\qty}[1]")
    expected_fiberprod = r"\newcommand{\fiberprod}[3]{{#1} \fiberproduct{#2} {#3}}"
    if expected_fiberprod in content:
        check("legacy fiberprod semantic signature generated")
    else:
        fail("legacy fiberprod semantic signature", f"missing {expected_fiberprod}")


def test_readme_reference_lists_each_definition_of_the_macro_files() -> None:
    spec = importlib.util.spec_from_file_location(
        "generate_readme_reference", ROOT / "bin" / "generate-readme-reference.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    reference = module.reference()
    expected_rows = {
        "\\danger with an optional argument": "| `\\danger` | 1 |",
        "\\ratmap with an optional argument": "| `\\ratmap` | 1 |",
        "\\surjectsvia with an optional argument": "| `\\surjectsvia` | 2 |",
    }
    for name, row in expected_rows.items():
        if row in reference:
            check(f"README reference lists {name}")
        else:
            fail(f"README reference lists {name}", f"no row {row!r}")
    if "| `\\stacktype` |" in reference:
        fail(
            "README reference leaves out a definition nested in a body",
            "\\stacktype of the body of \\danger is listed as a macro",
        )
    else:
        check("README reference leaves out a definition nested in a body")


def test_parameterised_definitions_reach_the_projection() -> None:
    macros = generated_macros()
    assert_macro(macros, "rising", ["\\qty{#1}^{ \\qty{#2} }", 2])
    assert_macro(macros, "falling", ["\\qty{#1}_{ \\qty{#2} }", 2])
    assert_macro(
        macros,
        "multichoose",
        [
            "{\\left(\\kern-.3em\\left(\\genfrac{}{}{0pt}{}{#1}{#2}\\right)\\kern-.3em\\right)}",
            2,
        ],
    )


def test_optional_default_reaches_each_projection() -> None:
    module = generator_module()
    macros = module.parse_macros("\\newcommand{\\pair}[2][d]{(#1, #2)}\n", "pair.tex")
    projected = json.loads(module.generate_json(macros))
    if projected == {"pair": ["(#1, #2)", 2, "d"]}:
        check("an optional default is the third member of the MathJax entry")
    else:
        fail(
            "an optional default is the third member of the MathJax entry",
            repr(projected),
        )
    definition = "\\newcommand{\\pair}[2][d]{(#1, #2)}"
    for name, text in (
        ("reader input", module.generate_reader_input(macros)),
        ("HTML include", module.generate_html(macros)),
        ("legacy HTML", module.generate_legacy_html(macros)),
    ):
        if definition in text:
            check(f"the {name} keeps the optional default")
        else:
            fail(f"the {name} keeps the optional default", text)
    if '"pair": ["(#1, #2)", 2, "d"]' in module.generate_js(macros):
        check("the JavaScript module keeps the optional default")
    else:
        fail(
            "the JavaScript module keeps the optional default",
            module.generate_js(macros),
        )


def test_a_definition_without_a_projection_stops_the_generator() -> None:
    module = generator_module()
    cases = {
        "\\def\\dotted#1.{#1}": "\\dotted",
        "\\gdef\\global{x}": "\\global",
        "\\let\\copied\\alpha": "\\copied",
        "\\DeclareRobustCommand{\\robust}{x}": "\\robust",
        "\\DeclarePairedDelimiter{\\pair}{(}{)}": "\\pair",
    }
    for source, name in cases.items():
        text = f"\\newcommand{{\\fine}}{{y}}\n\n{source}\n"
        try:
            module.parse_macros(text, "cases.tex")
        except module.ProjectionError as error:
            message = str(error)
            if "cases.tex:3" in message and name in message:
                check(f"{source} stops the generator with its file, line and name")
            else:
                fail(
                    f"{source} stops the generator with its file, line and name",
                    message,
                )
            continue
        fail(f"{source} stops the generator", "parse_macros returned")
    undefined = module.parse_macros(
        "\\let\\hyp\\relax\n\\newcommand{\\hyp}{h}\n", "relax.tex"
    )
    if [(m.name, m.body) for m in undefined] == [("hyp", "h")]:
        check("\\let to \\relax before a definition defines nothing")
    else:
        fail("\\let to \\relax before a definition defines nothing", repr(undefined))


PROJECTED_LATEX_CASES = {
    "ceiling": ["x+1"],
    "rising": ["x", "n"],
    "falling": ["x", "n"],
    "multichoose": ["n", "k"],
}


def page_image(formula: str, tmp_dir: Path) -> bytes:
    (tmp_dir / "page.tex").write_text(
        "\\documentclass{article}\\usepackage{dzg-unified}\\pagestyle{empty}\n"
        f"\\begin{{document}}${formula}$\\end{{document}}\n"
    )
    env = os.environ.copy()
    env["TEXINPUTS"] = TEXINPUTS
    subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "page.tex"],
        capture_output=True,
        text=True,
        cwd=tmp_dir,
        env=env,
        check=True,
    )
    subprocess.run(
        ["pdftoppm", "-png", "-r", "300", "-singlefile", "page.pdf", "page"],
        cwd=tmp_dir,
        check=True,
    )
    return (tmp_dir / "page.png").read_bytes()


def test_projection_typesets_as_the_latex_definition() -> None:
    """pdflatex gives the same page for a macro of dzg-unified and for its projected expansion."""
    macros = generated_macros()
    for name, arguments in PROJECTED_LATEX_CASES.items():
        body, count = macros[name]
        expanded = body
        for number, argument in enumerate(arguments, start=1):
            expanded = expanded.replace(f"#{number}", argument)
        call = "\\" + name + "".join(f"{{{argument}}}" for argument in arguments)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            defined = page_image(f"a{call}b", tmp_dir)
            projected = page_image(f"a{expanded}b", tmp_dir)
        if count == len(arguments) and defined == projected:
            check(f"{call} and its projection give the same pdflatex page")
        else:
            fail(f"{call} and its projection give the same pdflatex page", expanded)


QTY_CASES = {
    "\\qty{\\frac ab}": "\\left(\\frac ab\\right)",
    "\\qty{x}": "\\left(x\\right)",
}

DELIMITER_CASES = {
    "\\ceiling{\\frac ab}": "{\\left\\lceil\\frac ab\\right\\rceil}",
    "\\intvl{\\frac ab}": "\\left[\\frac ab\\right]",
    "\\rising{x}{\\frac ab}": "\\left(x\\right)^{\\left(\\frac ab\\right)}",
    "\\falling{x}{\\frac ab}": "\\left(x\\right)_{\\left(\\frac ab\\right)}",
}

SHIM_CASES = {
    "\\coloneqq": "\\vcentcolon\\mathrel{\\mkern-1.2mu}=",
    "\\qed": "\\quad\\blacksquare",
}

QTY_CALL_RE = re.compile(r"\\qty(?![A-Za-z])\s*\{")


def without_qty(text: str) -> str:
    """Replace each \\qty{X} by \\left(X\\right), the parentheses that grow with X."""
    while (match := QTY_CALL_RE.search(text)) is not None:
        depth, end = 1, match.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(text[end], 0)
            end += 1
        inner = text[match.end() : end - 1]
        text = f"{text[: match.start()]}\\left({inner}\\right){text[end:]}"
    return text


def qty_macro_cases(macros: dict) -> dict[str, str]:
    cases: dict[str, str] = {}
    for name, value in macros.items():
        if name == "qty":
            continue
        body, count = (value, 0) if isinstance(value, str) else (value[0], value[1])
        if not QTY_CALL_RE.search(body):
            continue
        arguments = ["x", "y", "z", "w", "v", "u", "t", "s", "r"][:count]
        expanded = body
        for number, argument in enumerate(arguments, start=1):
            expanded = expanded.replace(f"#{number}", argument)
        call = "\\" + name + "".join(f"{{{argument}}}" for argument in arguments)
        cases[call] = without_qty(expanded)
    return cases


def pdflatex_pages(formulas: list[str], tmp_dir: Path) -> list[bytes] | str:
    pages = "\\newpage\n".join(f"$a {formula} b$\n" for formula in formulas)
    (tmp_dir / "pages.tex").write_text(
        "\\documentclass{article}\\usepackage{dzg-unified}\\pagestyle{empty}\n"
        f"\\begin{{document}}\n{pages}\\end{{document}}\n"
    )
    env = os.environ.copy()
    env["TEXINPUTS"] = TEXINPUTS
    cp = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "pages.tex"],
        capture_output=True,
        text=True,
        cwd=tmp_dir,
        env=env,
    )
    if cp.returncode != 0:
        return cp.stdout
    subprocess.run(
        ["pdftoppm", "-png", "-r", "300", "pages.pdf", "page"], cwd=tmp_dir, check=True
    )
    return [path.read_bytes() for path in sorted(tmp_dir.glob("page-*.png"))]


def mathjax_pages(formulas: list[str], tmp_dir: Path) -> list[bytes] | str:
    cp = subprocess.run(
        ["bun", str(HERE / "mathjax-pages.ts"), str(tmp_dir)],
        input=json.dumps([f"a {formula} b" for formula in formulas]),
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    if cp.returncode != 0:
        return cp.stdout + cp.stderr
    images: list[bytes] = []
    for index in range(len(formulas)):
        svg, png = tmp_dir / f"{index}.svg", tmp_dir / f"{index}.png"
        subprocess.run(
            ["rsvg-convert", "-z", "8", "-b", "white", str(svg), "-o", str(png)],
            check=True,
        )
        images.append(png.read_bytes())
    return images


def test_mathjax_typesets_each_delimiter_and_shim_as_pdflatex() -> None:
    """For each delimiter macro, each macro that uses \\qty and each shim of the
    generator, the call and its LaTeX meaning give the same pdflatex page, and
    the call with the macros of the preview template gives the same MathJax
    page as that meaning."""
    cases = {
        **QTY_CASES,
        **DELIMITER_CASES,
        **SHIM_CASES,
        **qty_macro_cases(generated_macros()),
    }
    calls, meanings = list(cases), list(cases.values())
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        (tmp_dir / "latex").mkdir()
        (tmp_dir / "mathjax").mkdir()
        mathjax = mathjax_pages(calls + meanings, tmp_dir / "mathjax")
        if isinstance(mathjax, str):
            fail("MathJax pages of the delimiters and shims", mathjax[-2000:])
            return
        latex = pdflatex_pages(calls + meanings, tmp_dir / "latex")
    if isinstance(latex, str):
        fail("pdflatex pages of the delimiters and shims", latex[-2000:])
        return
    count = len(calls)
    if len(latex) != 2 * count:
        fail(
            "pdflatex pages of the delimiters and shims",
            f"{len(latex)} pages for {2 * count} formulas",
        )
        return
    for index, (call, meaning) in enumerate(cases.items()):
        if latex[index] == latex[count + index]:
            check(f"{call} and {meaning} give the same pdflatex page")
        else:
            fail(
                f"{call} and {meaning} give the same pdflatex page", "the pages differ"
            )
        if mathjax[index] == mathjax[count + index]:
            check(f"{call} and {meaning} give the same MathJax page")
        else:
            fail(f"{call} and {meaning} give the same MathJax page", "the pages differ")


def main() -> None:
    test_domain_aux_files_are_generated()
    test_tree_overrides_only_the_declared_native_commands()
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
    test_readme_reference_lists_each_definition_of_the_macro_files()
    test_parameterised_definitions_reach_the_projection()
    test_optional_default_reaches_each_projection()
    test_a_definition_without_a_projection_stops_the_generator()
    test_projection_typesets_as_the_latex_definition()
    test_mathjax_typesets_each_delimiter_and_shim_as_pdflatex()
    total = passed + failed
    print(f"\n{'=' * 50}")
    print(f"  {passed}/{total} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
