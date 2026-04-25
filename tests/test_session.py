import json
from pathlib import Path

import pytest

from textc import session, git_ops


def _setup_branch(name: str = "pendulum") -> None:
    git_ops.create_branch(name)


def test_next_index_starts_at_one(git_repo: Path):
    _setup_branch()
    assert session.next_index("pendulum") == 1


def test_next_index_counts_textc_commits(git_repo: Path):
    _setup_branch()
    Path("a").write_text("a"); git_ops.add(["a"]); git_ops.commit("[textc] subj1")
    Path("b").write_text("b"); git_ops.add(["b"]); git_ops.commit("[textc] subj2")
    assert session.next_index("pendulum") == 3


def test_next_index_ignores_non_textc_commits(git_repo: Path):
    _setup_branch()
    Path("a").write_text("a"); git_ops.add(["a"]); git_ops.commit("[textc] one")
    Path("b").write_text("b"); git_ops.add(["b"]); git_ops.commit("manual commit")
    assert session.next_index("pendulum") == 2


def test_next_index_ignores_start_commit(git_repo: Path):
    _setup_branch()
    git_ops.commit("[textc] start pendulum", allow_empty=True)
    assert session.next_index("pendulum") == 1


def test_session_path(git_repo: Path):
    p = session.session_path("pendulum", 3)
    assert p == Path(".textc/sessions/pendulum-3.json")


def test_failed_session_path(git_repo: Path):
    p = session.failed_session_path("pendulum", 3)
    assert p == Path(".textc/sessions/pendulum-3.failed.json")


def test_write_and_read_roundtrip(git_repo: Path):
    data = {
        "metadata": {
            "branch": "pendulum",
            "index": 1,
            "compiled_at": "2026-04-25T10:23:00Z",
            "cc_session_id": "abc123",
            "model": "claude-opus-4-7",
            "spec_diff": "+hello",
            "sculpts": [],
        },
        "transcript": [{"type": "system", "subtype": "init"}],
    }
    p = session.write(data, "pendulum", 1)
    assert p.exists()
    assert p.parent == Path(".textc/sessions")
    loaded = session.read("pendulum", 1)
    assert loaded == data


def test_session_exists(git_repo: Path):
    assert session.exists("pendulum", 1) is False
    Path(".textc/sessions").mkdir(parents=True)
    Path(".textc/sessions/pendulum-1.json").write_text("{}")
    assert session.exists("pendulum", 1) is True


def test_append_sculpt_note_in_place(git_repo: Path):
    data = {
        "metadata": {
            "branch": "pendulum", "index": 1, "compiled_at": "...",
            "cc_session_id": "x", "model": "claude-opus-4-7",
            "spec_diff": "", "sculpts": [],
        },
        "transcript": [],
    }
    session.write(data, "pendulum", 1)
    session.append_sculpt("pendulum", 1, note="use scipy", at="2026-04-25T11:00:00Z")
    reloaded = session.read("pendulum", 1)
    assert reloaded["metadata"]["sculpts"] == [
        {"note": "use scipy", "at": "2026-04-25T11:00:00Z"}
    ]


def test_append_transcript_events(git_repo: Path):
    data = {"metadata": {"branch": "p", "index": 1, "compiled_at": "...",
            "cc_session_id": "x", "model": "m", "spec_diff": "", "sculpts": []},
            "transcript": []}
    session.write(data, "p", 1)
    session.append_transcript_events("p", 1, [{"type": "assistant"}, {"type": "result"}])
    reloaded = session.read("p", 1)
    assert len(reloaded["transcript"]) == 2
