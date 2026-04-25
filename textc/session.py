"""Session JSON read/write and index bookkeeping.

Only module that touches `.textc/sessions/`. JSON shape per addendum §1.2.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from textc import git_ops

SESSIONS_DIR = Path(".textc/sessions")


def session_path(branch: str, index: int) -> Path:
    """Path to the session JSON file for a (branch, index) pair."""
    return SESSIONS_DIR / f"{branch}-{index}.json"


def failed_session_path(branch: str, index: int) -> Path:
    """Path to the failed-session forensic JSON file (uncommitted)."""
    return SESSIONS_DIR / f"{branch}-{index}.failed.json"


def exists(branch: str, index: int) -> bool:
    """True iff a successful session JSON exists for (branch, index)."""
    return session_path(branch, index).exists()


def next_index(branch: str) -> int:
    """Next available index for `branch`. Counts existing `[textc] *` commits
    on the branch (excluding `[textc] start *`). First compile/anchor is 1."""
    subjects = git_ops.log_subjects()
    count = sum(
        1 for s in subjects
        if s.startswith("[textc] ") and not s.startswith("[textc] start ")
    )
    return count + 1


def write(data: dict[str, Any], branch: str, index: int) -> Path:
    """Write session JSON, creating the directory if needed. Returns the path."""
    p = session_path(branch, index)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2))
    return p


def write_failed(data: dict[str, Any], branch: str, index: int) -> Path:
    """Write a forensic .failed.json (uncommitted, not part of the audit trail)."""
    p = failed_session_path(branch, index)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2))
    return p


def read(branch: str, index: int) -> dict[str, Any]:
    """Read session JSON for (branch, index). Raises FileNotFoundError if missing."""
    return json.loads(session_path(branch, index).read_text())


def append_sculpt(branch: str, index: int, note: str, at: str) -> None:
    """Append a sculpt note to the session metadata in-place."""
    data = read(branch, index)
    data["metadata"]["sculpts"].append({"note": note, "at": at})
    write(data, branch, index)


def append_transcript_events(
    branch: str, index: int, events: list[dict[str, Any]]
) -> None:
    """Append stream-json events to the session transcript in-place."""
    data = read(branch, index)
    data["transcript"].extend(events)
    write(data, branch, index)


def append_ask(branch: str, index: int, question: str, answer: str, at: str) -> None:
    """Append a Q&A turn to the session metadata in-place."""
    data = read(branch, index)
    data["metadata"].setdefault("asks", []).append(
        {"question": question, "answer": answer, "at": at}
    )
    write(data, branch, index)
