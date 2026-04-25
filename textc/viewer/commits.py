"""Extract textc compile commits with sculpt and timestamp parsing."""
from __future__ import annotations

from textc import git_ops


def parse_commit(raw: dict) -> dict:
    """Convert a raw `git_ops.log_commits_with_files` entry into a viewer-shaped commit."""
    subject = str(raw["subject"])
    if subject.startswith("[textc] "):
        subject = subject[len("[textc] "):]

    sculpts: list[dict] = []
    compiled_at = ""
    for line in str(raw["body"]).splitlines():
        line = line.strip()
        if line.startswith("Sculpted: "):
            sculpts.append({"note": line[len("Sculpted: "):]})
        elif line.startswith("Compiled: "):
            compiled_at = line[len("Compiled: "):]

    return {
        "sha": raw["sha"],
        "subject": subject,
        "compiled_at": compiled_at,
        "sculpts": sculpts,
        "files_changed": len(raw.get("files") or []),
    }


def list_textc_commits(limit: int = 200) -> list[dict]:
    """Return parsed `[textc] ` commits on the current branch (newest first), excluding the `start` anchor."""
    out: list[dict] = []
    for raw in git_ops.log_commits_with_files(limit=limit):
        subject = str(raw["subject"])
        if not subject.startswith("[textc] "):
            continue
        if subject.startswith("[textc] start "):
            continue
        out.append(parse_commit(raw))
    return out
