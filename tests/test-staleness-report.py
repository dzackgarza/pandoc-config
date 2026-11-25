#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Contract tests for `just staleness-report`.

The report reads the `pandoc-config.known-good` marker of each downstream site
and compares the commit it names with the commit of this checkout by Git
ancestry. Tags only label the commits; an advance without a release is still
an advance.

Two kinds of proof:

- A repository whose history the test builds, so each status has an oracle:
  the test made the commits and knows which marker is behind, current, ahead
  or diverged, and which release lies between.
- This repository with the marker that dzackgarza/dzackgarza-site-v2026
  commits (`tests/fixtures/staleness-sites`), the regression case of the
  specification audit of pandoc-config#2.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REAL_SITE = ROOT / "tests" / "fixtures" / "staleness-sites" / "dzackgarza-site-v2026"
REAL_MARKER = "v1.0.0-3-gde19eb5"

# A Git hook runs this file with GIT_DIR and GIT_INDEX_FILE of the outer
# repository; the repositories of the test are others.
for variable in [name for name in os.environ if name.startswith("GIT_")]:
    del os.environ[variable]


def git(repository: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def report(repository: Path, *sites: Path) -> dict[str, dict[str, str | list[str]]]:
    """Run the recipe and read its blocks: `site <path>`, then `key: value` lines."""
    result = subprocess.run(
        ["just", "--justfile", str(repository / "justfile"), "staleness-report", *map(str, sites)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    blocks: dict[str, dict[str, str | list[str]]] = {}
    block: dict[str, str | list[str]] = {}
    changes: list[str] = []
    for line in result.stdout.splitlines():
        if line.startswith("site "):
            block = {}
            changes = []
            block["changes"] = changes
            blocks[line.removeprefix("site ")] = block
        elif line.startswith("    "):
            changes.append(line.split()[0])
        elif line.startswith("  ") and line.strip() != "changes:":
            key, value = line.strip().split(": ", 1)
            block[key] = value
    return blocks


def assert_changes(listed: str | list[str], commits: list[str]) -> None:
    """The listed abbreviations name the commits, in this order."""
    assert isinstance(listed, list)
    assert len(listed) == len(commits), (listed, commits)
    for abbreviation, sha in zip(listed, commits):
        assert len(abbreviation) >= 7 and sha.startswith(abbreviation), (abbreviation, sha)


def commit(repository: Path, message: str) -> str:
    (repository / "history.txt").write_text(message + "\n")
    git(repository, "add", "history.txt")
    git(repository, "commit", "--quiet", "-m", message)
    return git(repository, "rev-parse", "HEAD")


def site(parent: Path, name: str, marker: str | None) -> Path:
    directory = parent / name
    directory.mkdir()
    if marker is not None:
        (directory / "pandoc-config.known-good").write_text(marker + "\n")
    return directory


def built_repository(directory: Path) -> dict[str, str]:
    """A pandoc-config with the recipe and this history:

    c1 [v1.0.0] - c2 - c3 [v1.1.0] - c4 - c5 (HEAD) - later
                                       \\- side
    `later` and `side` are commits that no branch holds.
    """
    shutil.copy(ROOT / "justfile", directory / "justfile")
    (directory / "bin").mkdir()
    shutil.copy(ROOT / "bin" / "staleness-report.py", directory / "bin" / "staleness-report.py")
    git(directory, "init", "--quiet", "--initial-branch=main")
    git(directory, "config", "user.name", "Test")
    git(directory, "config", "user.email", "test@example.invalid")
    git(directory, "add", "justfile", "bin")
    shas = {"c1": commit(directory, "feat: first")}
    git(directory, "tag", "-a", "v1.0.0", "-m", "v1.0.0")
    shas["c2"] = commit(directory, "fix: second")
    shas["c3"] = commit(directory, "feat: third")
    git(directory, "tag", "-a", "v1.1.0", "-m", "v1.1.0")
    shas["c4"] = commit(directory, "fix: fourth")
    shas["c5"] = commit(directory, "fix: fifth")
    tree = git(directory, "rev-parse", "HEAD^{tree}")
    shas["later"] = git(directory, "commit-tree", tree, "-p", shas["c5"], "-m", "later")
    shas["side"] = git(directory, "commit-tree", tree, "-p", shas["c4"], "-m", "side")
    return shas


def test_each_status_is_decided_by_ancestry() -> None:
    with tempfile.TemporaryDirectory() as scratch:
        repository = Path(scratch, "pandoc-config")
        repository.mkdir()
        shas = built_repository(repository)
        sites = Path(scratch, "sites")
        sites.mkdir()
        untagged = site(sites, "untagged", "v1.1.0")
        across = site(sites, "across", git(repository, "describe", "--tags", shas["c2"]))
        current = site(sites, "current", git(repository, "describe", "--tags", "HEAD"))
        ahead = site(sites, "ahead", shas["later"][:7])
        diverged = site(sites, "diverged", shas["side"])
        absent = site(sites, "absent", None)
        empty = site(sites, "empty", "")
        unresolvable = site(sites, "unresolvable", "v9.9.9")

        blocks = report(
            repository, untagged, across, current, ahead, diverged, absent, empty, unresolvable
        )

        # An advance with no release between marker and HEAD is stale.
        assert blocks[str(untagged)]["status"] == "stale"
        assert blocks[str(untagged)]["behind"] == "2 commits"
        assert blocks[str(untagged)]["releases since the marker"] == "none"
        assert_changes(blocks[str(untagged)]["changes"], [shas["c5"], shas["c4"]])

        assert blocks[str(across)]["status"] == "stale"
        assert blocks[str(across)]["behind"] == "3 commits"
        assert blocks[str(across)]["releases since the marker"] == "v1.1.0"
        assert_changes(blocks[str(across)]["changes"], [shas["c5"], shas["c4"], shas["c3"]])

        assert blocks[str(current)]["status"] == "current"
        assert_changes(blocks[str(current)]["changes"], [])

        assert blocks[str(ahead)]["status"] == "ahead"
        assert blocks[str(ahead)]["ahead"] == "1 commit"

        assert blocks[str(diverged)]["status"] == "diverged"

        assert blocks[str(absent)]["status"] == "no marker"
        assert blocks[str(empty)]["status"] == "no marker"
        assert blocks[str(unresolvable)]["status"] == "unresolvable"


def test_without_arguments_the_report_reads_the_registry() -> None:
    with tempfile.TemporaryDirectory() as scratch:
        repository = Path(scratch, "pandoc-config")
        repository.mkdir()
        built_repository(repository)
        sites = Path(scratch, "sites")
        sites.mkdir()
        listed = site(sites, "listed", "v1.1.0")
        (repository / "downstream-sites.txt").write_text(f"# downstream sites\n{listed}\n")

        blocks = report(repository)

        assert list(blocks) == [str(listed)]
        assert blocks[str(listed)]["status"] == "stale"


def test_the_committed_site_marker_lags_this_checkout() -> None:
    assert (REAL_SITE / "pandoc-config.known-good").read_text().strip() == REAL_MARKER
    marker = git(ROOT, "rev-parse", f"{REAL_MARKER}^{{commit}}")
    expected = git(ROOT, "rev-list", f"{marker}..HEAD").split()

    block = report(ROOT, REAL_SITE)[str(REAL_SITE)]

    assert block["status"] == "stale"
    assert block["behind"] == f"{len(expected)} commits"
    assert_changes(block["changes"], expected)
    releases = str(block["releases since the marker"])
    # v1.0.0 is the ancestor of the marker, so it is no release since it.
    assert "v1.0.0" not in releases.split(", ")
    for tag in [] if releases == "none" else releases.split(", "):
        tagged = git(ROOT, "rev-parse", f"{tag}^{{commit}}")
        assert subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", marker, tagged]).returncode == 0
        assert subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", tagged, "HEAD"]).returncode == 0


if __name__ == "__main__":
    test_the_committed_site_marker_lags_this_checkout()
    test_each_status_is_decided_by_ancestry()
    test_without_arguments_the_report_reads_the_registry()
    print("Staleness report tests passed")
