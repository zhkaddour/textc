"""Subprocess dispatch to `claude`, with stream-json parsing and timeout.

Only module that knows the stream-json event shape (per addendum §1.2).
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from typing import Any

from textc.prompts import STATUS_MARKER_RE


DEFAULT_TIMEOUT_SECONDS = 300  # 5 minutes; PRD Q-i-2.
SIGTERM_GRACE_SECONDS = 5


@dataclass
class AgentResult:
    """Outcome of a single `claude` invocation."""
    status: str  # "DONE" or "FAILED"
    subject: str  # commit subject on DONE, failure reason on FAILED
    session_id: str | None  # captured from stream-json system/init event
    events: list[dict[str, Any]] = field(default_factory=list)  # raw events
    final_text: str = ""  # concatenated assistant text (for status marker)


def _resolve_claude_cmd(claude_cmd: list[str] | None) -> list[str]:
    if claude_cmd is not None:
        return list(claude_cmd)
    return [os.environ.get("TEXTC_CLAUDE_BIN", "claude")]


def _resolve_timeout(timeout_seconds: int | None) -> int:
    if timeout_seconds is not None:
        return timeout_seconds
    env = os.environ.get("TEXTC_TIMEOUT")
    if env:
        return int(env)
    return DEFAULT_TIMEOUT_SECONDS


def dispatch(
    *,
    system_prompt: str,
    user_prompt: str,
    resume_session_id: str | None = None,
    claude_cmd: list[str] | None = None,
    timeout_seconds: int | None = None,
    stream_to_terminal: bool = False,
) -> AgentResult:
    """Spawn `claude --print --output-format stream-json ...`, stream events,
    parse status marker, return AgentResult.

    On timeout: SIGTERM, then SIGKILL after SIGTERM_GRACE_SECONDS. Returns
    AgentResult(status='FAILED', subject='timed out after Ns', ...).
    """
    cmd = _resolve_claude_cmd(claude_cmd)
    timeout = _resolve_timeout(timeout_seconds)

    args = list(cmd)
    # Only add claude-specific flags if we're invoking claude itself,
    # not the fake_claude.py stub used by tests. The stub doesn't need them.
    # Detect by checking if "claude" is the binary basename.
    if cmd and os.path.basename(cmd[0]) in ("claude",):
        args.extend(["--print", "--output-format", "stream-json"])
        args.extend(["--append-system-prompt", system_prompt])
        if resume_session_id:
            args.extend(["--resume", resume_session_id])

    proc = subprocess.Popen(
        args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Send the user prompt on stdin and close it.
    if proc.stdin:
        proc.stdin.write(user_prompt)
        proc.stdin.close()

    events: list[dict[str, Any]] = []
    session_id: str | None = None
    final_text_parts: list[str] = []

    def _read_stdout():
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            events.append(event)
            if stream_to_terminal:
                _render_event(event)
            nonlocal session_id
            if session_id is None and event.get("type") == "system" and event.get("subtype") == "init":
                session_id = event.get("session_id")
            if event.get("type") == "assistant":
                msg = event.get("message", {})
                for c in msg.get("content", []):
                    if c.get("type") == "text":
                        final_text_parts.append(c.get("text", ""))

    reader = threading.Thread(target=_read_stdout, daemon=True)
    reader.start()

    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=SIGTERM_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        reader.join(timeout=2)
        return AgentResult(
            status="FAILED",
            subject=f"timed out after {timeout}s",
            session_id=session_id,
            events=events,
            final_text="".join(final_text_parts),
        )

    reader.join(timeout=5)

    final_text = "".join(final_text_parts)
    match = STATUS_MARKER_RE.search(final_text)
    if not match:
        return AgentResult(
            status="FAILED",
            subject="agent did not signal completion (no [STATUS: ...] marker)",
            session_id=session_id,
            events=events,
            final_text=final_text,
        )

    return AgentResult(
        status=match.group(1),
        subject=match.group(2).strip(),
        session_id=session_id,
        events=events,
        final_text=final_text,
    )


def _render_event(event: dict[str, Any]) -> None:
    """Render a stream-json event to stdout for the user. Best-effort, terse."""
    etype = event.get("type")
    if etype == "assistant":
        msg = event.get("message", {})
        for c in msg.get("content", []):
            if c.get("type") == "text":
                sys.stdout.write(c.get("text", ""))
                sys.stdout.flush()
    elif etype == "result":
        sys.stdout.write("\n")
        sys.stdout.flush()
