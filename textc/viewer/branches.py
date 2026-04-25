"""Discover textc-using branches in the current repo."""
from __future__ import annotations

import subprocess


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def list_textc_branches() -> list[str]:
    """Return local branches that contain at least one `[textc] ` commit, alphabetically."""
    branch_lines = _git("branch", "--format=%(refname:short)").splitlines()
    out: list[str] = []
    for branch in (b.strip() for b in branch_lines if b.strip()):
        log = _git("log", branch, "--format=%s")
        if any(line.startswith("[textc] ") for line in log.splitlines()):
            out.append(branch)
    return sorted(out)
