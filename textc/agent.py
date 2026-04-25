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
        # `--verbose` is REQUIRED when combining --print + --output-format stream-json.
        # `--permission-mode bypassPermissions` lets the agent write code and run tests
        # without interactive prompts (which can't be answered in --print mode anyway).
        # Safe because the agent operates inside a feature branch — anything it does
        # is reversible via git.
        args.extend(["--print", "--output-format", "stream-json", "--verbose"])
        args.extend(["--permission-mode", "bypassPermissions"])
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


_USE_COLOR = sys.stdout.isatty()


def _ansi(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOR else text


def _summarize_tool_call(name: str, inp: dict[str, Any]) -> str:
    """One-line summary of a tool call's target — what it acts on, not how."""
    if name in ("Read", "Edit", "Write", "NotebookEdit"):
        return str(inp.get("file_path", ""))
    if name == "Bash":
        cmd = str(inp.get("command", ""))
        return cmd if len(cmd) <= 80 else cmd[:77] + "..."
    if name in ("Glob", "Grep"):
        return str(inp.get("pattern", ""))
    return ""


def _render_event(event: dict[str, Any]) -> None:
    """Render a stream-json event to stdout. Streams assistant text and
    surfaces tool activity so the user sees what the agent is doing in near
    real time, mirroring Claude Code's interactive feel."""
    etype = event.get("type")
    if etype == "assistant":
        msg = event.get("message", {})
        for c in msg.get("content", []):
            ctype = c.get("type")
            if ctype == "text":
                sys.stdout.write(c.get("text", ""))
                sys.stdout.flush()
            elif ctype == "tool_use":
                name = c.get("name", "?")
                summary = _summarize_tool_call(name, c.get("input", {}) or {})
                sys.stdout.write(
                    f"\n{_ansi('→', '36')} {_ansi(name, '36;1')} "
                    f"{_ansi(summary, '2')}\n"
                )
                sys.stdout.flush()
            elif ctype == "thinking":
                sys.stdout.write(_ansi("\n  ... thinking\n", "2"))
                sys.stdout.flush()
    elif etype == "user":
        # Tool results come back as user messages with content blocks.
        msg = event.get("message", {})
        content = msg.get("content")
        if isinstance(content, list):
            for c in content:
                if c.get("type") == "tool_result":
                    if c.get("is_error"):
                        sys.stdout.write(_ansi("  ✗\n", "31"))
                    else:
                        sys.stdout.write(_ansi("  ✓\n", "32"))
                    sys.stdout.flush()
    elif etype == "result":
        sys.stdout.write("\n")
        sys.stdout.flush()
