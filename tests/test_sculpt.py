import json
import sys
import subprocess
from pathlib import Path

import pytest

from textc.verbs.sculpt import run as sculpt_run

FAKE = [sys.executable, str(Path(__file__).parent / "fixtures" / "fake_claude.py")]


def _normal_compile_state(git_repo: Path):
    """Set up a branch with one normal compile commit and session."""
    from textc.verbs.start import run as start_run
    from textc.verbs.compile import run as compile_run
    start_run("pendulum")
    Path(".textc/specs/pendulum.md").write_text("a pendulum\n")
    compile_run(claude_cmd_override=FAKE + ["--scenario", "done_simple"])


def test_sculpt_after_normal_compile_amends_with_note(git_repo: Path):
    _normal_compile_state(git_repo)
    head_before = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True,
    ).stdout.strip()

    sculpt_run("use scipy not numpy",
               claude_cmd_override=FAKE + ["--scenario", "done_simple"])

    head_after = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert head_before != head_after  # amend changes SHA

    body = subprocess.run(
        ["git", "log", "-n1", "--format=%b"], capture_output=True, text=True, check=True,
    ).stdout
    assert "Sculpted: use scipy not numpy" in body

    data = json.loads(Path(".textc/sessions/pendulum-1.json").read_text())
    assert len(data["metadata"]["sculpts"]) == 1
    assert data["metadata"]["sculpts"][0]["note"] == "use scipy not numpy"


def test_sculpt_blocks_when_no_compile_commit(git_repo: Path):
    from textc.verbs.start import run as start_run
    start_run("pendulum")
    from textc.errors import NoCompileToSculptError
    with pytest.raises(NoCompileToSculptError):
        sculpt_run("anything", claude_cmd_override=FAKE + ["--scenario", "done_simple"])


def test_sculpt_blocks_when_dirty_tree(git_repo: Path):
    _normal_compile_state(git_repo)
    Path("other.py").write_text("dirt")
    from textc.errors import DirtyWorkingTreeError
    with pytest.raises(DirtyWorkingTreeError):
        sculpt_run("anything", claude_cmd_override=FAKE + ["--scenario", "done_simple"])


def test_sculpt_after_anchor_creates_session_and_amends(git_repo: Path):
    """Case 5 — anchor compile, then sculpt: fresh session, amend keeps anchor subject."""
    from textc.verbs.start import run as start_run
    from textc.verbs.compile import run as compile_run
    start_run("pendulum")
    # Anchor compile (no spec change).
    compile_run(claude_cmd_override=FAKE + ["--scenario", "done_simple"])
    # Anchor commit exists, no session JSON yet.
    assert not Path(".textc/sessions/pendulum-1.json").exists()

    sculpt_run("add pyproject.toml",
               claude_cmd_override=FAKE + ["--scenario", "done_simple"])

    # Anchor subject preserved on amend.
    subject = subprocess.run(
        ["git", "log", "-n1", "--format=%s"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert subject == "[textc] 1 - no spec change"

    # Sculpted line appears in body.
    body = subprocess.run(
        ["git", "log", "-n1", "--format=%b"], capture_output=True, text=True, check=True,
    ).stdout
    assert "Sculpted: add pyproject.toml" in body

    # Session JSON now exists, with the new cc_session_id.
    data = json.loads(Path(".textc/sessions/pendulum-1.json").read_text())
    assert data["metadata"]["cc_session_id"] == "fake-sess-001"
    assert data["metadata"]["sculpts"][0]["note"] == "add pyproject.toml"


def test_sculpt_after_anchor_then_sculpt_again_resumes(git_repo: Path):
    """Case 5 then case 4 — second sculpt should resume the now-existing session."""
    from textc.verbs.start import run as start_run
    from textc.verbs.compile import run as compile_run
    start_run("pendulum")
    compile_run(claude_cmd_override=FAKE + ["--scenario", "done_simple"])
    sculpt_run("first sculpt",
               claude_cmd_override=FAKE + ["--scenario", "done_simple"])
    sculpt_run("second sculpt",
               claude_cmd_override=FAKE + ["--scenario", "done_simple"])

    data = json.loads(Path(".textc/sessions/pendulum-1.json").read_text())
    notes = [s["note"] for s in data["metadata"]["sculpts"]]
    assert notes == ["first sculpt", "second sculpt"]


def test_sculpt_after_anchor_preserves_anchor_compiled_at(git_repo: Path):
    """Case 5: the new session JSON's compiled_at matches the anchor's `Compiled:` body line."""
    from textc.verbs.start import run as start_run
    from textc.verbs.compile import run as compile_run

    start_run("pendulum")
    compile_run(claude_cmd_override=FAKE + ["--scenario", "done_simple"])

    # Read the anchor commit's body to get its Compiled: timestamp.
    body = subprocess.run(
        ["git", "log", "-n1", "--format=%b"], capture_output=True, text=True, check=True,
    ).stdout
    import re
    m = re.search(r"^Compiled:\s*(\S+)", body, re.MULTILINE)
    assert m is not None, "anchor commit must have Compiled: line"
    anchor_ts = m.group(1)

    sculpt_run("add pyproject.toml",
               claude_cmd_override=FAKE + ["--scenario", "done_simple"])

    data = json.loads(Path(".textc/sessions/pendulum-1.json").read_text())
    assert data["metadata"]["compiled_at"] == anchor_ts, (
        f"sculpt-on-anchor should preserve anchor's compiled_at "
        f"(expected {anchor_ts}, got {data['metadata']['compiled_at']})"
    )
