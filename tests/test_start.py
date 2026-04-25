import subprocess
from pathlib import Path

import pytest

from textc.verbs.start import run as start_run


def test_start_creates_branch_with_empty_spec(git_repo: Path):
    start_run("pendulum")
    branch = subprocess.run(
        ["git", "symbolic-ref", "--short", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert branch == "pendulum"

    spec = Path("spec.md")
    assert spec.exists()
    assert spec.read_text() == ""

    subject = subprocess.run(
        ["git", "log", "-n1", "--format=%s"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert subject == "[textc] start pendulum"


def test_start_blocks_outside_git_repo(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from textc.errors import NotInGitRepoError
    with pytest.raises(NotInGitRepoError):
        start_run("foo")


def test_start_writes_gitignore_excluding_failed_sessions(git_repo: Path):
    start_run("pendulum")
    gi = Path(".gitignore")
    assert gi.exists()
    assert ".textc/sessions/*.failed.json" in gi.read_text()


def test_start_appends_to_existing_gitignore(git_repo: Path):
    Path(".gitignore").write_text("*.pyc\n")
    start_run("pendulum")
    gi = Path(".gitignore")
    text = gi.read_text()
    assert "*.pyc" in text
    assert ".textc/sessions/*.failed.json" in text


def test_failed_compile_does_not_block_subsequent_compile(git_repo: Path, monkeypatch):
    """Recovery flow: a failed compile leaves a .failed.json that must NOT
    block a subsequent compile (because it's gitignored)."""
    import sys, subprocess
    from textc.verbs.compile import run as compile_run
    from textc.errors import AgentFailureError

    FAKE = [sys.executable, str(Path(__file__).parent / "fixtures" / "fake_claude.py")]

    start_run("pendulum")
    Path("spec.md").write_text("first attempt\n")
    monkeypatch.setenv("TEXTC_TIMEOUT", "10")

    # First compile fails, leaving pendulum-1.failed.json
    with pytest.raises(AgentFailureError):
        compile_run(claude_cmd_override=FAKE + ["--scenario", "failed"])
    assert Path(".textc/sessions/pendulum-1.failed.json").exists()

    # Re-edit spec, retry — must NOT block on the lingering .failed.json
    Path("spec.md").write_text("second attempt\n")
    compile_run(claude_cmd_override=FAKE + ["--scenario", "done_simple"])

    subject = subprocess.run(
        ["git", "log", "-n1", "--format=%s"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert subject == "[textc] add pendulum gravity"
