"""Spec line-diff and code-diff parsing for the viewer."""
from __future__ import annotations

import difflib
import subprocess


def spec_diff_lines(parent_text: str, current_text: str) -> list[dict]:
    """Return a unified line stream tagged with diff kind.

    Each item: {"kind": "added"|"removed"|"unchanged", "text": str}.
    Replace regions emit removes first, then adds.
    """
    parent_lines = parent_text.splitlines()
    current_lines = current_text.splitlines()
    matcher = difflib.SequenceMatcher(a=parent_lines, b=current_lines, autojunk=False)
    out: list[dict] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for line in current_lines[j1:j2]:
                out.append({"kind": "unchanged", "text": line})
        elif tag == "delete":
            for line in parent_lines[i1:i2]:
                out.append({"kind": "removed", "text": line})
        elif tag == "insert":
            for line in current_lines[j1:j2]:
                out.append({"kind": "added", "text": line})
        elif tag == "replace":
            for line in parent_lines[i1:i2]:
                out.append({"kind": "removed", "text": line})
            for line in current_lines[j1:j2]:
                out.append({"kind": "added", "text": line})
    return out


def read_spec_at(branch: str, sha: str) -> str:
    """Return the contents of `.textc/specs/<branch>.md` at the given commit. Empty string if missing."""
    path = f".textc/specs/{branch}.md"
    result = subprocess.run(
        ["git", "show", f"{sha}:{path}"],
        capture_output=True, text=True, check=False,
    )
    return result.stdout if result.returncode == 0 else ""


def parent_sha(sha: str) -> str | None:
    """Return the first parent of `sha`, or None if root commit."""
    result = subprocess.run(
        ["git", "rev-parse", f"{sha}^"],
        capture_output=True, text=True, check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def parse_unified_diff(text: str) -> list[dict]:
    """Parse `git diff` unified output into [{file, hunks: [{header, lines: [{kind, text}]}]}].

    Handles file deletions: when `+++ /dev/null` follows a `--- a/<path>` line,
    the deleted file's path is taken from the minus marker so the deletion's
    hunks are not silently dropped.
    """
    files: list[dict] = []
    current_file: dict | None = None
    current_hunk: dict | None = None
    pending_minus_path: str | None = None  # last seen `--- a/<path>` for this file

    for raw_line in text.splitlines():
        if raw_line.startswith("diff --git "):
            current_file = None
            current_hunk = None
            pending_minus_path = None
            continue
        if raw_line.startswith("--- a/"):
            pending_minus_path = raw_line[len("--- a/"):]
            continue
        if raw_line.startswith("--- ") or raw_line.startswith("index ") or \
           raw_line.startswith("new file mode") or raw_line.startswith("deleted file mode") or \
           raw_line.startswith("similarity index") or raw_line.startswith("rename "):
            continue
        if raw_line.startswith("+++ /dev/null"):
            if pending_minus_path is not None:
                current_file = {"file": pending_minus_path, "hunks": []}
                files.append(current_file)
            current_hunk = None
            continue
        if raw_line.startswith("+++ b/"):
            current_file = {"file": raw_line[len("+++ b/"):], "hunks": []}
            files.append(current_file)
            current_hunk = None
            continue
        if raw_line.startswith("@@"):
            if current_file is None:
                continue
            current_hunk = {"header": raw_line, "lines": []}
            current_file["hunks"].append(current_hunk)
            continue
        if current_hunk is None:
            continue
        if raw_line.startswith("+"):
            current_hunk["lines"].append({"kind": "added", "text": raw_line[1:]})
        elif raw_line.startswith("-"):
            current_hunk["lines"].append({"kind": "removed", "text": raw_line[1:]})
        elif raw_line.startswith(" "):
            current_hunk["lines"].append({"kind": "context", "text": raw_line[1:]})
        # any other prefix (e.g. "\\ No newline at end of file") is ignored
    return files


def code_diff(parent: str | None, sha: str) -> list[dict]:
    """Return parsed unified diff between parent and commit, excluding `.textc/`.

    `parent` is the parent SHA (None for root commits). Named `parent` rather
    than `parent_sha` to avoid shadowing the module-level `parent_sha` function.
    """
    if parent is None:
        # Root commit: show all introduced files via empty-tree diff
        empty_tree = subprocess.run(
            ["git", "hash-object", "-t", "tree", "/dev/null"],
            capture_output=True, text=True, check=False,
        ).stdout.strip() or "4b825dc642cb6eb9a060e54bf8d69288fbee4904"  # well-known empty tree
        diff_text = subprocess.run(
            ["git", "diff", empty_tree, sha, "--", ":!.textc/*"],
            capture_output=True, text=True, check=False,
        ).stdout
    else:
        diff_text = subprocess.run(
            ["git", "diff", parent, sha, "--", ":!.textc/*"],
            capture_output=True, text=True, check=False,
        ).stdout
    return parse_unified_diff(diff_text)
