from textc import prompts


def test_compile_system_prompt_is_string():
    p = prompts.compile_system_prompt(spec_path=".textc/specs/pendulum.md")
    assert isinstance(p, str)
    assert "STATUS: DONE" in p
    assert "Do not modify .textc/specs/pendulum.md" in p
    assert "Do not commit" in p


def test_compile_user_prompt_includes_diff():
    p = prompts.compile_user_prompt(
        spec_diff="+ hello world", spec_path=".textc/specs/pendulum.md"
    )
    assert "+ hello world" in p
    assert ".textc/specs/pendulum.md" in p
    assert "STATUS: DONE" in p


def test_sculpt_system_prompt_includes_note():
    p = prompts.sculpt_system_prompt(
        note="use scipy not numpy", spec_path=".textc/specs/pendulum.md"
    )
    assert "use scipy not numpy" in p
    assert ".textc/specs/pendulum.md" in p
    assert "lie" in p.lower()
    assert "STATUS: DONE" in p


def test_ask_system_prompt_includes_question():
    p = prompts.ask_system_prompt(question="why scipy?")
    assert "why scipy?" in p
    assert "Do not modify" in p


def test_status_marker_regex_extracts_done():
    match = prompts.STATUS_MARKER_RE.search("blah blah\n[STATUS: DONE] add pendulum")
    assert match is not None
    assert match.group(1) == "DONE"
    assert match.group(2) == "add pendulum"


def test_status_marker_regex_extracts_failed():
    match = prompts.STATUS_MARKER_RE.search("[STATUS: FAILED] tests broke")
    assert match is not None
    assert match.group(1) == "FAILED"
    assert match.group(2) == "tests broke"


def test_status_marker_regex_no_match_when_missing():
    assert prompts.STATUS_MARKER_RE.search("just plain text") is None
