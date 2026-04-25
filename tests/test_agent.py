import sys
from pathlib import Path

import pytest

from textc import agent

FAKE_CLAUDE = [sys.executable, str(Path(__file__).parent / "fixtures" / "fake_claude.py")]


def test_dispatch_done_returns_status_and_subject():
    result = agent.dispatch(
        system_prompt="sys", user_prompt="user",
        claude_cmd=FAKE_CLAUDE + ["--scenario", "done_simple"],
        timeout_seconds=10,
    )
    assert result.status == "DONE"
    assert result.subject == "add pendulum gravity"
    assert result.session_id == "fake-sess-001"
    assert len(result.events) >= 2


def test_dispatch_failed_returns_failure():
    result = agent.dispatch(
        system_prompt="sys", user_prompt="user",
        claude_cmd=FAKE_CLAUDE + ["--scenario", "failed"],
        timeout_seconds=10,
    )
    assert result.status == "FAILED"
    assert "tests do not pass" in result.subject


def test_dispatch_no_marker_treated_as_failed():
    result = agent.dispatch(
        system_prompt="sys", user_prompt="user",
        claude_cmd=FAKE_CLAUDE + ["--scenario", "no_marker"],
        timeout_seconds=10,
    )
    assert result.status == "FAILED"
    assert "did not signal completion" in result.subject.lower()


def test_dispatch_timeout_kills_process():
    result = agent.dispatch(
        system_prompt="sys", user_prompt="user",
        claude_cmd=FAKE_CLAUDE + ["--scenario", "hang"],
        timeout_seconds=1,
    )
    assert result.status == "FAILED"
    assert "timeout" in result.subject.lower() or "timed out" in result.subject.lower()
