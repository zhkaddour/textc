import json
import sys
import subprocess
from pathlib import Path

import pytest

from textc.verbs.compile import run as compile_run

FAKE = [sys.executable, str(Path(__file__).parent / "fixtures" / "fake_claude.py")]


def _start_branch(name: str = "pendulum"):
    from textc.verbs.start import run
    run(name)


def test_compile_with_spec_diff_creates_commit(git_repo: Path, monkeypatch):
    _start_branch()
    Path("spec.md").write_text("Build a pendulum.\n")
    monkeypatch.setenv("TEXTC_TIMEOUT", "10")

    compile_run(claude_cmd_override=FAKE + ["--scenario", "done_simple"])

    subject = subprocess.run(
        ["git", "log", "-n1", "--format=%s"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert subject == "[textc] add pendulum gravity"

    body = subprocess.run(
        ["git", "log", "-n1", "--format=%b"],
        capture_output=True, text=True, check=True,
    ).stdout
    assert "Compiled:" in body

    sj = Path(".textc/sessions/pendulum-1.json")
    assert sj.exists()
    data = json.loads(sj.read_text())
    assert data["metadata"]["branch"] == "pendulum"
    assert data["metadata"]["index"] == 1
    assert data["metadata"]["cc_session_id"] == "fake-sess-001"
    assert "spec_diff" in data["metadata"]


def test_compile_blocks_when_spec_unchanged_with_dirty_tree(git_repo: Path):
    """Case 11 — non-spec dirty file blocks compile."""
    _start_branch()
    Path("other.py").write_text("hi")
    from textc.errors import DirtyWorkingTreeError
    with pytest.raises(DirtyWorkingTreeError):
        compile_run(claude_cmd_override=FAKE + ["--scenario", "done_simple"])


def test_compile_blocks_outside_repo(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from textc.errors import NotInGitRepoError
    with pytest.raises(NotInGitRepoError):
        compile_run(claude_cmd_override=FAKE + ["--scenario", "done_simple"])


def test_compile_no_spec_change_creates_anchor_commit(git_repo: Path):
    _start_branch()
    # No spec edit; clean tree.
    compile_run(claude_cmd_override=FAKE + ["--scenario", "done_simple"])

    subject = subprocess.run(
        ["git", "log", "-n1", "--format=%s"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert subject == "[textc] 1 - no spec change"

    # No session JSON yet.
    assert not Path(".textc/sessions/pendulum-1.json").exists()


def test_compile_anchor_then_anchor_again(git_repo: Path):
    _start_branch()
    compile_run(claude_cmd_override=FAKE + ["--scenario", "done_simple"])
    compile_run(claude_cmd_override=FAKE + ["--scenario", "done_simple"])
    subjects = subprocess.run(
        ["git", "log", "--format=%s"],
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    assert subjects[0] == "[textc] 2 - no spec change"
    assert subjects[1] == "[textc] 1 - no spec change"


def test_compile_agent_failed_writes_forensic_json_no_commit(git_repo: Path):
    _start_branch()
    Path("spec.md").write_text("broken spec\n")

    head_before = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True,
    ).stdout.strip()

    from textc.errors import AgentFailureError
    with pytest.raises(AgentFailureError):
        compile_run(claude_cmd_override=FAKE + ["--scenario", "failed"])

    # No new commit.
    head_after = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert head_before == head_after

    # Forensic JSON written.
    failed = Path(".textc/sessions/pendulum-1.failed.json")
    assert failed.exists()
    data = json.loads(failed.read_text())
    assert data["metadata"]["failure_reason"]
    assert data["transcript"]

    # Successful session JSON not written.
    assert not Path(".textc/sessions/pendulum-1.json").exists()


def test_compile_timeout_writes_forensic_json(git_repo: Path, monkeypatch):
    _start_branch()
    Path("spec.md").write_text("hangs forever\n")
    monkeypatch.setenv("TEXTC_TIMEOUT", "1")

    from textc.errors import AgentFailureError
    with pytest.raises(AgentFailureError):
        compile_run(claude_cmd_override=FAKE + ["--scenario", "hang"])

    failed = Path(".textc/sessions/pendulum-1.failed.json")
    assert failed.exists()
