import json
import sys
import subprocess
from pathlib import Path

import pytest

from textc.verbs.ask import run as ask_run

FAKE = [sys.executable, str(Path(__file__).parent / "fixtures" / "fake_claude.py")]


def _normal_compile_state(git_repo: Path):
    from textc.verbs.start import run as start_run
    from textc.verbs.compile import run as compile_run
    start_run("pendulum")
    Path(".textc/specs/pendulum.md").write_text("a pendulum\n")
    compile_run(claude_cmd_override=FAKE + ["--scenario", "done_simple"])


def test_ask_amends_head_with_qa_in_session(git_repo: Path):
    """Ask amends HEAD so the audit lives inside the compile cycle it belongs
    to. SHA changes (amend), but subject and body are preserved — asks aren't
    `Sculpted:`-style annotations."""
    _normal_compile_state(git_repo)
    head_before = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True,
    ).stdout.strip()
    subj_before = subprocess.run(
        ["git", "log", "-n1", "--format=%s"], capture_output=True, text=True, check=True,
    ).stdout.strip()
    body_before = subprocess.run(
        ["git", "log", "-n1", "--format=%b"], capture_output=True, text=True, check=True,
    ).stdout

    ask_run("why scipy?",
            claude_cmd_override=FAKE + ["--scenario", "done_simple"])

    head_after = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True,
    ).stdout.strip()
    subj_after = subprocess.run(
        ["git", "log", "-n1", "--format=%s"], capture_output=True, text=True, check=True,
    ).stdout.strip()
    body_after = subprocess.run(
        ["git", "log", "-n1", "--format=%b"], capture_output=True, text=True, check=True,
    ).stdout

    assert head_before != head_after, "ask should amend HEAD (SHA changes)"
    assert subj_before == subj_after, "ask must not change the commit subject"
    assert body_before == body_after, "ask must not pollute the commit body"

    data = json.loads(Path(".textc/sessions/pendulum-1.json").read_text())
    assert len(data["transcript"]) > 3  # original events + ask events
    assert any(a["question"] == "why scipy?" for a in data["metadata"].get("asks", []))

    # Working tree clean after ask (audit baked in).
    porcelain = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True, check=True,
    ).stdout
    assert porcelain == ""


def test_ask_blocks_when_no_session(git_repo: Path):
    from textc.verbs.start import run as start_run
    start_run("pendulum")
    from textc.errors import NoActiveSessionError
    with pytest.raises(NoActiveSessionError):
        ask_run("anything", claude_cmd_override=FAKE + ["--scenario", "done_simple"])
