"""Subprocess wrappers around `git`. Only module that calls git."""
from __future__ import annotations

import subprocess
from pathlib import Path


def _git(*args: str, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        check=check,
        capture_output=capture,
        text=True,
    )


def in_git_repo() -> bool:
    """True iff the current working directory is inside a git work tree."""
    result = _git("rev-parse", "--is-inside-work-tree", check=False)
    return result.returncode == 0 and result.stdout.strip() == "true"


def current_branch() -> str:
    """Return the current branch name. Raises if HEAD is detached."""
    return _git("symbolic-ref", "--short", "HEAD").stdout.strip()


def create_branch(name: str) -> None:
    """Create and switch to branch `name` from current HEAD."""
    _git("checkout", "-b", name)


def _is_untracked(path: str) -> bool:
    """True iff `path` is untracked (not known to git at all)."""
    result = _git("ls-files", "--error-unmatch", "--", path, check=False)
    return result.returncode != 0


def is_modified(path: str) -> bool:
    """True iff `path` differs from HEAD in the working tree (staged or unstaged),
    including untracked files."""
    if _is_untracked(path):
        # If the file exists on disk it is "modified" relative to HEAD (not there).
        return Path(path).exists()
    result = _git("diff", "--quiet", "HEAD", "--", path, check=False)
    return result.returncode != 0


def working_tree_dirty(exclude: list[str] | None = None) -> bool:
    """True iff any tracked or untracked file (excluding `exclude`) differs from HEAD.

    `exclude` is a list of paths to ignore (e.g. ['spec.md']).
    """
    exclude = exclude or []
    result = _git("status", "--porcelain")
    for line in result.stdout.splitlines():
        path = line[3:].strip()
        if path in exclude:
            continue
        if path:
            return True
    return False


def diff_against_head(path: str) -> str:
    """Return the unified diff of `path` against HEAD.

    For untracked files (not yet known to git), produces a diff against
    /dev/null so callers always get a unified diff regardless of tracking state.
    """
    if _is_untracked(path):
        # --no-index exits 1 when files differ (normal); capture output, don't raise.
        result = _git("diff", "--no-index", "/dev/null", path, check=False)
        return result.stdout
    return _git("diff", "HEAD", "--", path).stdout


def add(paths: list[str]) -> None:
    """Stage the given paths."""
    _git("add", "--", *paths)


def commit(message: str, allow_empty: bool = False) -> None:
    """Create a commit with the given message. Body lines after the first
    blank line become the commit body."""
    args = ["commit", "-m", message]
    if allow_empty:
        args.append("--allow-empty")
    _git(*args)


def amend(append_body_line: str | None = None) -> None:
    """Amend HEAD with currently staged changes. If `append_body_line` is given,
    append it as a new line to the existing commit message body."""
    if append_body_line is None:
        _git("commit", "--amend", "--no-edit")
        return
    existing = _git("log", "--format=%B", "-n", "1").stdout.rstrip("\n")
    new_message = f"{existing}\n{append_body_line}"
    _git("commit", "--amend", "-m", new_message)


def log_subjects(limit: int = 100) -> list[str]:
    """Return commit subjects on the current branch, newest first."""
    result = _git("log", f"-n{limit}", "--format=%s")
    return [line for line in result.stdout.splitlines() if line]


def head_subject() -> str:
    """Subject of HEAD."""
    return _git("log", "-n1", "--format=%s").stdout.strip()


def head_body() -> str:
    """Body of HEAD (everything after the subject line)."""
    return _git("log", "-n1", "--format=%b").stdout


def log_commits_with_files(limit: int = 100) -> list[dict[str, object]]:
    """Return commit metadata for the current branch, newest first.

    Each entry has keys: sha (str), subject (str), body (str),
    files (list[str] of paths changed by that commit).
    """
    sep = "<<<TEXTCSEP>>>"
    fmt = f"%H{sep}%s{sep}%b{sep}END_OF_COMMIT"
    out = _git("log", f"-n{limit}", f"--format={fmt}").stdout

    commits: list[dict[str, object]] = []
    for chunk in out.split("END_OF_COMMIT"):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        parts = chunk.split(sep)
        if len(parts) < 3:
            continue
        sha, subject, body = parts[0], parts[1], parts[2]
        files = _git("show", "--name-only", "--format=", sha).stdout.splitlines()
        commits.append({"sha": sha, "subject": subject, "body": body, "files": files})
    return commits
