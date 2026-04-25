"""Implements `textc ask <question>` — cases 6, 7 of behavior matrix."""
from datetime import datetime, timezone

from textc import agent, git_ops, prompts, session
from textc.errors import NoActiveSessionError, NotInGitRepoError


def _previous_compile_index(branch: str) -> int | None:
    subject = git_ops.head_subject()
    if not subject.startswith("[textc] ") or subject.startswith("[textc] start "):
        return None
    return session.next_index(branch) - 1


def run(question: str, claude_cmd_override: list[str] | None = None) -> None:
    if not git_ops.in_git_repo():
        raise NotInGitRepoError("Not in a git repository.")

    branch = git_ops.current_branch()
    prev_index = _previous_compile_index(branch)

    if prev_index is None or not session.exists(branch, prev_index):
        raise NoActiveSessionError(
            "No active session. Run `textc compile` or `textc sculpt` first."
        )

    data = session.read(branch, prev_index)
    cc_session_id = data["metadata"]["cc_session_id"]

    result = agent.dispatch(
        system_prompt=prompts.ask_system_prompt(question=question),
        user_prompt=question,
        resume_session_id=cc_session_id,
        claude_cmd=claude_cmd_override,
        stream_to_terminal=True,
    )

    answered_at = datetime.now(timezone.utc).isoformat()

    # Persist regardless of agent status — even a confused reply is the answer.
    session.append_transcript_events(branch, prev_index, result.events)
    session.append_ask(
        branch, prev_index,
        question=question, answer=result.final_text, at=answered_at,
    )
