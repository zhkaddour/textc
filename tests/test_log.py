import sys
import subprocess
from pathlib import Path

from textc.verbs.log import run as log_run

FAKE = [sys.executable, str(Path(__file__).parent / "fixtures" / "fake_claude.py")]


def test_log_renders_compile_and_sculpts(git_repo: Path, capsys):
    from textc.verbs.start import run as start_run
    from textc.verbs.compile import run as compile_run
    from textc.verbs.sculpt import run as sculpt_run

    start_run("pendulum")
    Path(".textc/specs/pendulum.md").write_text("a pendulum\n")
    compile_run(claude_cmd_override=FAKE + ["--scenario", "done_simple"])
    sculpt_run("use scipy", claude_cmd_override=FAKE + ["--scenario", "done_simple"])

    log_run()
    out = capsys.readouterr().out

    assert "add pendulum gravity" in out  # agent-derived subject
    assert "use scipy" in out  # sculpt note
    assert "pendulum" in out  # branch reference somewhere


def test_log_handles_anchor_subject(git_repo: Path, capsys):
    from textc.verbs.start import run as start_run
    from textc.verbs.compile import run as compile_run

    start_run("pendulum")
    compile_run(claude_cmd_override=FAKE + ["--scenario", "done_simple"])

    log_run()
    out = capsys.readouterr().out
    assert "no spec change" in out
