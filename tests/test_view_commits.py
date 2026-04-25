"""Tests for commit list extraction with sculpt parsing."""
from textc.viewer import commits


def test_parse_commit_extracts_sculpts_and_compiled_at():
    raw = {
        "sha": "abc123",
        "subject": "[textc] add friction",
        "body": (
            "Compiled: 2026-04-25T14:23:11Z\n"
            "Sculpted: fix sign\n"
            "Sculpted: use scipy\n"
        ),
        "files": ["pendulum.py", ".textc/specs/pendulum.md"],
    }
    parsed = commits.parse_commit(raw)
    assert parsed["sha"] == "abc123"
    assert parsed["subject"] == "add friction"
    assert parsed["compiled_at"] == "2026-04-25T14:23:11Z"
    assert parsed["sculpts"] == [{"note": "fix sign"}, {"note": "use scipy"}]
    assert parsed["files_changed"] == 2


def test_parse_commit_no_sculpts():
    raw = {
        "sha": "def456",
        "subject": "[textc] initial",
        "body": "Compiled: 2026-04-25T14:00:00Z\n",
        "files": ["a.py"],
    }
    parsed = commits.parse_commit(raw)
    assert parsed["sculpts"] == []
    assert parsed["compiled_at"] == "2026-04-25T14:00:00Z"


def test_list_textc_commits_excludes_start(monkeypatch):
    fake_log = [
        {"sha": "c3", "subject": "[textc] add render", "body": "Compiled: 2026-04-25T14:30:00Z\n", "files": []},
        {"sha": "c2", "subject": "[textc] add gravity", "body": "Compiled: 2026-04-25T14:20:00Z\n", "files": []},
        {"sha": "c1", "subject": "[textc] start pendulum", "body": "", "files": []},
        {"sha": "c0", "subject": "init", "body": "", "files": []},
    ]
    monkeypatch.setattr("textc.git_ops.log_commits_with_files", lambda limit=100: fake_log)

    result = commits.list_textc_commits()
    assert [c["sha"] for c in result] == ["c3", "c2"]
