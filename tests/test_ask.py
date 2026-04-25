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
    Path("spec.md").write_text("a pendulum\n")
    compile_run(claude_cmd_override=FAKE + ["--scenario", "done_simple"])


def test_ask_appends_qa_to_session_no_git_change(git_repo: Path):
    _normal_compile_state(git_repo)
    head_before = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True,
    ).stdout.strip()

    ask_run("why scipy?",
            claude_cmd_override=FAKE + ["--scenario", "done_simple"])

    head_after = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert head_before == head_after  # no git ops

    data = json.loads(Path(".textc/sessions/pendulum-1.json").read_text())
    assert len(data["transcript"]) > 3  # original events + ask events
    assert any(a["question"] == "why scipy?" for a in data["metadata"].get("asks", []))


def test_ask_blocks_when_no_session(git_repo: Path):
    from textc.verbs.start import run as start_run
    start_run("pendulum")
    from textc.errors import NoActiveSessionError
    with pytest.raises(NoActiveSessionError):
        ask_run("anything", claude_cmd_override=FAKE + ["--scenario", "done_simple"])
