"""Implements `textc sculpt <note>` — cases 4, 5, 8, 12 of behavior matrix."""
import re
from datetime import datetime, timezone

from textc import agent, git_ops, prompts, session
from textc.errors import (
    AgentFailureError, DirtyWorkingTreeError, NoCompileToSculptError,
    NotInGitRepoError,
)


def _previous_compile_index(branch: str) -> int | None:
    """The index of the [textc] commit at HEAD, or None if HEAD is the start
    commit or not a textc commit."""
    subject = git_ops.head_subject()
    if not subject.startswith("[textc] "):
        return None
    if subject.startswith("[textc] start "):
        return None
    # next_index returns count+1; the latest committed index is count.
    return session.next_index(branch) - 1


def _anchor_compiled_at_from_head() -> str | None:
    """Parse `Compiled: <ts>` from HEAD's body. Returns the timestamp if present."""
    body = git_ops.head_body()
    m = re.search(r"^Compiled:\s*(\S+)", body, re.MULTILINE)
    return m.group(1) if m else None


def run(note: str, claude_cmd_override: list[str] | None = None) -> None:
    if not git_ops.in_git_repo():
        raise NotInGitRepoError("Not in a git repository.")

    branch = git_ops.current_branch()

    if git_ops.working_tree_dirty():
        raise DirtyWorkingTreeError(
            "Working tree dirty. Commit or stash first."
        )

    prev_index = _previous_compile_index(branch)
    if prev_index is None:
        raise NoCompileToSculptError(
            "No compile to sculpt. Run `textc compile` first."
        )

    has_session = session.exists(branch, prev_index)

    if has_session:
        # Case 4 — resume existing session.
        data = session.read(branch, prev_index)
        cc_session_id = data["metadata"]["cc_session_id"]
        result = agent.dispatch(
            system_prompt=prompts.sculpt_system_prompt(note=note),
            user_prompt=note,
            resume_session_id=cc_session_id,
            claude_cmd=claude_cmd_override,
            stream_to_terminal=True,
        )
    else:
        # Case 5 — anchor with no prior session. Fresh dispatch.
        result = agent.dispatch(
            system_prompt=prompts.sculpt_system_prompt(note=note),
            user_prompt=note,
            claude_cmd=claude_cmd_override,
            stream_to_terminal=True,
        )

    sculpted_at = datetime.now(timezone.utc).isoformat()

    if result.status != "DONE":
        # Forensic write under .failed.json (use prev_index, not next_index).
        session.write_failed({
            "metadata": {
                "branch": branch, "index": prev_index, "compiled_at": sculpted_at,
                "cc_session_id": result.session_id, "model": "claude-opus-4-7",
                "spec_diff": "", "sculpts": [{"note": note, "at": sculpted_at}],
                "failure_reason": result.subject,
            },
            "transcript": result.events,
        }, branch, prev_index)
        raise AgentFailureError(f"sculpt failed: {result.subject}")

    if has_session:
        # Case 4 — update existing session JSON in-place.
        session.append_sculpt(branch, prev_index, note=note, at=sculpted_at)
        session.append_transcript_events(branch, prev_index, result.events)
    else:
        # Case 5 — first-time write of session JSON for this anchor.
        # Preserve the anchor commit's original Compiled: timestamp (audit accuracy).
        compile_anchor_at = _anchor_compiled_at_from_head() or sculpted_at
        session.write({
            "metadata": {
                "branch": branch, "index": prev_index,
                "compiled_at": compile_anchor_at,
                "cc_session_id": result.session_id, "model": "claude-opus-4-7",
                "spec_diff": "",
                "sculpts": [{"note": note, "at": sculpted_at}],
            },
            "transcript": result.events,
        }, branch, prev_index)

    # Stage everything (the agent may have written code anywhere) + the session JSON.
    git_ops.add([str(session.session_path(branch, prev_index)), "."])
    git_ops.amend(append_body_line=f"Sculpted: {note}")
