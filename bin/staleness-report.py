#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["cyclopts>=4.5.1"]
# ///
"""Report the downstream sites whose pandoc-config known-good marker lags.

A downstream site (a pandoc-ssg site, dzackgarza/pandoc-ssg#13) commits the
file `pandoc-config.known-good`: the `git describe --tags` name of the
pandoc-config commit that the site was last verified against. Builds float on
the current pandoc-config; this report lists, for each site, how its marker
relates to the commit of this checkout.

The comparison is Git ancestry between commits. A tag only labels a commit,
so an advance with no release in between is still an advance
(pandoc-config#2, finding PCFG-002-01). Statuses:

- stale: the marker is an ancestor of HEAD; the report lists the releases
  and every commit in marker..HEAD.
- current: the marker is HEAD.
- ahead: HEAD is an ancestor of the marker (this checkout is older).
- diverged: neither commit is an ancestor of the other.
- no marker: the file is absent or empty.
- unresolvable: the marker names no commit of this repository (for example
  a commit this clone has not fetched, or a `-dirty` name).
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import cyclopts
from cyclopts.types import ExistingDirectory

MARKER = "pandoc-config.known-good"

app = cyclopts.App(help=__doc__)


@dataclass(frozen=True)
class Repository:
    path: Path

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.path), *args], check=True, capture_output=True, text=True
        ).stdout.strip()

    def commit_of(self, name: str) -> str | None:
        """The commit that `name` (a tag, a describe name, a hash) names, or None."""
        result = subprocess.run(
            ["git", "-C", str(self.path), "rev-parse", "--verify", "--quiet", f"{name}^{{commit}}"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 1:
            return None
        result.check_returncode()
        return result.stdout.strip()

    def is_ancestor(self, ancestor: str, descendant: str) -> bool:
        result = subprocess.run(
            ["git", "-C", str(self.path), "merge-base", "--is-ancestor", ancestor, descendant]
        )
        if result.returncode not in (0, 1):
            result.check_returncode()
        return result.returncode == 0

    def count(self, revisions: str) -> int:
        return int(self.git("rev-list", "--count", revisions))


def plural(count: int) -> str:
    return f"{count} commit" if count == 1 else f"{count} commits"


def site_block(repository: Repository, head: str, site: Path) -> list[str]:
    lines = [f"site {site}"]
    marker_file = site / MARKER
    if not marker_file.is_file():
        return [*lines, "  status: no marker", f"  marker: {marker_file} is absent"]
    marker = marker_file.read_text().strip()
    if marker == "":
        return [*lines, "  status: no marker", f"  marker: {marker_file} is empty"]
    commit = repository.commit_of(marker)
    if commit is None:
        return [
            *lines,
            "  status: unresolvable",
            f"  marker: {marker} names no commit of {repository.path}",
        ]
    lines.append(f"  marker: {marker} ({commit})")
    if commit == head:
        return [*lines, "  status: current"]
    if repository.is_ancestor(commit, head):
        releases = repository.git(
            "tag", "--list", "v*", "--sort=v:refname", "--merged", head, "--no-merged", commit
        ).split()
        changes = repository.git("log", "--format=%h %s", f"{commit}..{head}").splitlines()
        return [
            *lines,
            "  status: stale",
            f"  behind: {plural(repository.count(f'{commit}..{head}'))}",
            f"  releases since the marker: {', '.join(releases) or 'none'}",
            "  changes:",
            *(f"    {change}" for change in changes),
        ]
    if repository.is_ancestor(head, commit):
        return [*lines, "  status: ahead", f"  ahead: {plural(repository.count(f'{head}..{commit}'))}"]
    return [
        *lines,
        "  status: diverged",
        f"  behind: {plural(repository.count(f'{commit}..{head}'))}",
        f"  ahead: {plural(repository.count(f'{head}..{commit}'))}",
    ]


def registered_sites(registry: Path) -> list[Path]:
    """The sites of the registry: one directory per line, `#` starts a comment."""
    entries = (line.split("#", 1)[0].strip() for line in registry.read_text().splitlines())
    return [Path(entry).expanduser() for entry in entries if entry]


@app.default
def report(
    *sites: ExistingDirectory,
    repository: Annotated[ExistingDirectory, cyclopts.Parameter(name="--repository")],
    registry: Annotated[Path, cyclopts.Parameter(name="--registry")],
) -> None:
    """Print one block for each site.

    Parameters
    ----------
    sites
        Site directories that hold a `pandoc-config.known-good` marker. When
        none is given, the sites of the registry.
    repository
        The pandoc-config checkout whose HEAD is the current revision.
    registry
        File that lists the downstream site directories, one per line.
    """
    checkout = Repository(repository)
    head = checkout.git("rev-parse", "HEAD")
    print(f"pandoc-config {checkout.git('describe', '--tags', '--always', head)} ({head})")
    if checkout.git("status", "--porcelain", "--untracked-files=all") != "":
        print("The working tree has uncommitted changes; the report compares commits.")
    for site in sites or registered_sites(registry):
        if not site.is_dir():
            raise SystemExit(f"{site} (from {registry}) is no directory")
        print()
        print("\n".join(site_block(checkout, head, site)))


if __name__ == "__main__":
    app()
