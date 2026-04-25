"""Implements `textc start <name>` — case 1 of behavior matrix."""
from pathlib import Path

from textc import git_ops, session
from textc.errors import NotInGitRepoError

_GITIGNORE_LINE = ".textc/sessions/*.failed.json"


def _ensure_gitignore_excludes_failed_sessions() -> None:
    """Make sure failed-session forensic files don't accidentally land in commits.

    Creates or appends to `.gitignore` at the repo root so `<branch>-N.failed.json`
    files don't show up as dirty working-tree entries (which would block the next
    `textc compile` after a failure).
    """
    gi = Path(".gitignore")
    if gi.exists():
        existing = gi.read_text()
        if _GITIGNORE_LINE in existing:
            return
        gi.write_text(existing.rstrip("\n") + f"\n{_GITIGNORE_LINE}\n")
    else:
        gi.write_text(f"{_GITIGNORE_LINE}\n")


def run(name: str) -> None:
    if not git_ops.in_git_repo():
        raise NotInGitRepoError("Not in a git repository.")

    git_ops.create_branch(name)

    spec = session.spec_path(name)
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text("")

    _ensure_gitignore_excludes_failed_sessions()

    git_ops.add([str(spec), ".gitignore"])
    git_ops.commit(f"[textc] start {name}")
