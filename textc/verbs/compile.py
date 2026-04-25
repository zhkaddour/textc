"""Implements `textc compile` — cases 2, 3, 10, 11 of behavior matrix.

Task 3.1 implements case 2 + case 11 + case 13.
Task 3.2 will fill in the case 3 (anchor) branch.
"""
from datetime import datetime, timezone

from textc import agent, git_ops, prompts, session
from textc.errors import (
    AgentFailureError, DirtyWorkingTreeError, NotInGitRepoError,
)


def run(claude_cmd_override: list[str] | None = None) -> None:
    if not git_ops.in_git_repo():
        raise NotInGitRepoError("Not in a git repository.")

    branch = git_ops.current_branch()
    spec = str(session.spec_path(branch))
    spec_modified = git_ops.is_modified(spec)

    # Exclude `.textc/` because session JSON updates from `textc ask` are
    # textc-owned audit state, not user code; they get baked into the next
    # compile/sculpt commit via `git add .` below. The spec file lives under
    # `.textc/specs/` and is therefore covered by the same exclusion.
    if git_ops.working_tree_dirty(exclude=[".textc"]):
        raise DirtyWorkingTreeError(
            "Working tree has uncommitted changes besides the spec file. "
            "Commit or stash first."
        )

    index = session.next_index(branch)

    if not spec_modified:
        # Case 3: anchor compile — no agent invoked, empty commit.
        compiled_at = datetime.now(timezone.utc).isoformat()
        message = f"[textc] {index} - no spec change\n\nCompiled: {compiled_at}"
        git_ops.commit(message, allow_empty=True)
        return

    # Case 2: normal compile.
    spec_diff = git_ops.diff_against_head(spec)

    result = agent.dispatch(
        system_prompt=prompts.compile_system_prompt(spec_path=spec),
        user_prompt=prompts.compile_user_prompt(spec_diff=spec_diff, spec_path=spec),
        claude_cmd=claude_cmd_override,
        stream_to_terminal=True,
    )

    compiled_at = datetime.now(timezone.utc).isoformat()

    if result.status != "DONE":
        # Case 9 — write forensic session, no commit.
        session.write_failed({
            "metadata": {
                "branch": branch, "index": index, "compiled_at": compiled_at,
                "cc_session_id": result.session_id, "model": "claude-opus-4-7",
                "spec_diff": spec_diff, "sculpts": [],
                "failure_reason": result.subject,
            },
            "transcript": result.events,
        }, branch, index)
        raise AgentFailureError(f"compile failed: {result.subject}")

    # On DONE: write session JSON, stage everything, commit atomically.
    session.write({
        "metadata": {
            "branch": branch, "index": index, "compiled_at": compiled_at,
            "cc_session_id": result.session_id, "model": "claude-opus-4-7",
            "spec_diff": spec_diff, "sculpts": [],
        },
        "transcript": result.events,
    }, branch, index)

    git_ops.add([spec, str(session.session_path(branch, index)), "."])
    message = f"[textc] {result.subject}\n\nCompiled: {compiled_at}"
    git_ops.commit(message)
