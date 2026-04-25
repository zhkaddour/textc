"""Implements `textc show [<index>]` — Phase 4.2 of PRD."""
import json

from rich.console import Console
from rich.syntax import Syntax

from textc import git_ops, session
from textc.errors import NoActiveSessionError, NotInGitRepoError


def run(index: int | None) -> None:
    if not git_ops.in_git_repo():
        raise NotInGitRepoError("Not in a git repository.")

    branch = git_ops.current_branch()

    if index is None:
        # Walk down indices until we find one with a session JSON.
        next_idx = session.next_index(branch)
        for i in range(next_idx - 1, 0, -1):
            if session.exists(branch, i):
                index = i
                break
        if index is None:
            raise NoActiveSessionError(
                "No session JSON found on this branch."
            )

    if not session.exists(branch, index):
        raise NoActiveSessionError(
            f"No session JSON for {branch}-{index}."
        )

    data = session.read(branch, index)
    console = Console()
    console.print(f"[bold]Session {branch}-{index}[/]")
    console.print(Syntax(json.dumps(data, indent=2), "json", line_numbers=False))
