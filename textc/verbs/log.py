"""Implements `textc log` — Phase 4.1 of PRD."""
from rich.console import Console
from rich.tree import Tree

from textc import git_ops
from textc.errors import NotInGitRepoError


def run() -> None:
    if not git_ops.in_git_repo():
        raise NotInGitRepoError("Not in a git repository.")

    branch = git_ops.current_branch()
    console = Console()
    tree = Tree(f"[bold]branch[/]: {branch}")

    for c in git_ops.log_commits_with_files():
        if not str(c["subject"]).startswith("[textc] "):
            continue
        node = tree.add(f"[cyan]{c['subject']}[/]  [dim]{str(c['sha'])[:7]}[/]")
        for line in str(c["body"]).splitlines():
            line = line.strip()
            if not line.startswith("Sculpted: "):
                continue
            note = line[len("Sculpted: "):]
            symbol = "±" if any(
                f.startswith(".textc/specs/") for f in c["files"]
            ) else "~"
            node.add(f"[yellow]{symbol}[/] {note}")
    console.print(tree)
