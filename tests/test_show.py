import sys
from pathlib import Path

from textc.verbs.show import run as show_run

FAKE = [sys.executable, str(Path(__file__).parent / "fixtures" / "fake_claude.py")]


def test_show_default_prints_latest_session(git_repo: Path, capsys):
    from textc.verbs.start import run as start_run
    from textc.verbs.compile import run as compile_run

    start_run("pendulum")
    Path("spec.md").write_text("a pendulum\n")
    compile_run(claude_cmd_override=FAKE + ["--scenario", "done_simple"])

    show_run(None)
    out = capsys.readouterr().out
    assert "pendulum" in out
    assert "fake-sess-001" in out


def test_show_specific_index(git_repo: Path, capsys):
    from textc.verbs.start import run as start_run
    from textc.verbs.compile import run as compile_run

    start_run("pendulum")
    Path("spec.md").write_text("a\n")
    compile_run(claude_cmd_override=FAKE + ["--scenario", "done_simple"])
    Path("spec.md").write_text("a\nb\n")
    compile_run(claude_cmd_override=FAKE + ["--scenario", "done_simple"])

    show_run(1)
    out = capsys.readouterr().out
    assert '"index": 1' in out
