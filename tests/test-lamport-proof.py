#!/usr/bin/env python3
"""Contract tests for the Lamport-style proof Pandoc filter."""

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
FILTER = ROOT / "filters" / "lamport_proof.lua"

PROOF = r"""
:::: {.pf #sum-of-odds numbering=short}

::: {.pf-step #theorem}
The sum of the first $n$ odd numbers is $n^2$.

:::: {.pf-proof}
Proof by induction.

::: {.pf-step #base}
For $n=1$, $1=1^2$.
:::

::: {.pf-step #induction}
Assume the claim for $n$.

::: {.pf-assume}
- $1+3+\cdots+(2n-1)=n^2$
:::

::: {.pf-prove}
$1+3+\cdots+(2n+1)=(n+1)^2$
:::

:::: {.pf-proof}
Add $2n+1$ to both sides.
::::
:::

::: {.pf-qed}
By [the base step](#base){.pf-ref} and
[the induction step](#induction){.pf-ref}.
:::
::::
:::
::::
"""


def render(markdown: str, output: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "pandoc",
            "-f",
            "markdown+fenced_divs+link_attributes+tex_math_single_backslash",
            "--lua-filter",
            str(FILTER),
            "-t",
            output,
        ],
        input=markdown,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )


def test_html_numbers_nested_steps_and_references() -> None:
    result = render(PROOF, "html")
    assert result.returncode == 0, result.stderr
    assert 'class="pf"' in result.stdout
    assert 'id="theorem"' in result.stdout
    assert 'data-pf-number="1"' in result.stdout
    assert 'id="base"' in result.stdout
    assert 'data-pf-number="1.1"' in result.stdout
    assert 'class="pf-number">1.1.</span>' in result.stdout
    assert 'id="induction"' in result.stdout
    assert 'data-pf-number="1.2"' in result.stdout
    assert 'href="#base"' in result.stdout
    assert '>1.1<' in result.stdout
    assert 'href="#induction"' in result.stdout
    assert '>1.2<' in result.stdout


def test_latex_uses_nested_pf2_structure() -> None:
    result = render(PROOF, "latex")
    assert result.returncode == 0, result.stderr
    assert r"\begin{proof}" in result.stdout
    assert r"\begin{step+}{theorem}" in result.stdout
    assert r"\begin{step+}{base}" in result.stdout
    assert r"\begin{step+}{induction}" in result.stdout
    assert r"\assume\bgroup" in result.stdout
    assert r"\prove\bgroup" in result.stdout
    assert r"\qedstep" in result.stdout
    assert r"\pfref{base}" in result.stdout
    assert r"\pfref{induction}" in result.stdout


def test_markdown_keeps_proof_structure_without_render_attributes() -> None:
    result = render(PROOF, "markdown")
    assert result.returncode == 0, result.stderr
    assert ".pf-step" in result.stdout
    assert "#theorem" in result.stdout
    assert "data-pf-number" not in result.stdout


def test_long_numbering_and_case_steps_use_pf2_keywords() -> None:
    case = """
::: {.pf numbering=long}
::: {.pf-step .pf-case #case}
$n$ is even.
:::
:::
"""
    result = render(case, "latex")
    assert result.returncode == 0, result.stderr
    assert r"\pflongnumbers" in result.stdout
    assert r"\begin{step+}{case}" in result.stdout
    assert r"\textsc{Case:}" in result.stdout


def test_duplicate_step_labels_fail_at_filter_boundary() -> None:
    duplicate = """
::: {.pf}
::: {.pf-step #same}
First.
:::
::: {.pf-step #same}
Second.
:::
:::
"""
    result = render(duplicate, "html")
    assert result.returncode != 0


def test_unknown_step_reference_fails_at_filter_boundary() -> None:
    unknown = """
::: {.pf}
::: {.pf-step #one}
See [the missing step](#missing){.pf-ref}.
:::
:::
"""
    result = render(unknown, "html")
    assert result.returncode != 0


if __name__ == "__main__":
    test_html_numbers_nested_steps_and_references()
    test_latex_uses_nested_pf2_structure()
    test_markdown_keeps_proof_structure_without_render_attributes()
    test_long_numbering_and_case_steps_use_pf2_keywords()
    test_duplicate_step_labels_fail_at_filter_boundary()
    test_unknown_step_reference_fails_at_filter_boundary()
    print("Lamport proof filter tests passed")
