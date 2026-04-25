"""Tests for transcript event shaping."""
from textc.viewer import conversation


def test_shape_skips_hook_events():
    transcript = [
        {"type": "system", "subtype": "hook_started", "hook_name": "X"},
        {"type": "system", "subtype": "hook_response", "hook_name": "X"},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "hi"}]}},
    ]
    metadata = {"sculpts": [], "asks": []}
    result = conversation.shape(transcript, metadata)
    assert result == [{"kind": "assistant_text", "text": "hi"}]


def test_shape_extracts_tool_use_one_liner():
    transcript = [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "Reading the file."},
                    {"type": "tool_use", "name": "Read", "input": {"file_path": "/tmp/pendulum.py"}},
                ]
            },
        }
    ]
    result = conversation.shape(transcript, {"sculpts": [], "asks": []})
    assert result == [
        {"kind": "assistant_text", "text": "Reading the file."},
        {"kind": "tool_use", "tool": "Read", "summary": "/tmp/pendulum.py"},
    ]


def test_shape_extracts_tool_result_summary():
    transcript = [
        {
            "type": "user",
            "message": {
                "content": [
                    {"type": "tool_result", "content": "first line\nsecond line\nthird line"}
                ]
            },
        }
    ]
    result = conversation.shape(transcript, {"sculpts": [], "asks": []})
    assert result == [{
        "kind": "tool_result",
        "summary": "first line",
        "full": "first line\nsecond line\nthird line",
    }]


def test_shape_prepends_sculpts_and_asks_above_transcript():
    metadata = {
        "sculpts": [{"note": "use scipy", "at": "t1"}],
        "asks": [{"question": "why?", "answer": "because", "at": "t2"}],
    }
    transcript = [
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "ok"}]}},
    ]
    result = conversation.shape(transcript, metadata)
    assert result == [
        {"kind": "sculpt", "note": "use scipy", "at": "t1"},
        {"kind": "ask", "question": "why?", "answer": "because", "at": "t2"},
        {"kind": "assistant_text", "text": "ok"},
    ]


def test_shape_orders_compile_input_then_sculpts_then_asks_then_transcript():
    metadata = {
        "spec_diff": "+ new line",
        "sculpts": [{"note": "fix sign", "at": "t1"}],
        "asks": [{"question": "why?", "answer": "because", "at": "t2"}],
    }
    transcript = [
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "done"}]}},
    ]
    result = conversation.shape(transcript, metadata)
    kinds = [e["kind"] for e in result]
    assert kinds == ["compile_input", "sculpt", "ask", "assistant_text"]


def test_shape_extracts_system_init():
    transcript = [
        {
            "type": "system", "subtype": "init",
            "cwd": "/tmp/repo", "model": "claude-opus-4-7",
            "tools": ["Read", "Write", "Bash"],
            "permissionMode": "acceptEdits",
        },
    ]
    result = conversation.shape(transcript, {"sculpts": [], "asks": []})
    assert result == [{
        "kind": "system_init",
        "cwd": "/tmp/repo",
        "model": "claude-opus-4-7",
        "tools": ["Read", "Write", "Bash"],
        "permission_mode": "acceptEdits",
    }]


def test_shape_extracts_thinking_blocks():
    transcript = [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "thinking", "thinking": "Let me read the spec.", "signature": "abc"},
                    {"type": "text", "text": "I'll start by reading the spec."},
                ],
            },
        },
    ]
    result = conversation.shape(transcript, {"sculpts": [], "asks": []})
    assert result == [
        {"kind": "thinking", "text": "Let me read the spec."},
        {"kind": "assistant_text", "text": "I'll start by reading the spec."},
    ]


def test_shape_prepends_compile_input_when_spec_diff_present():
    metadata = {"spec_diff": "+ added line", "sculpts": [], "asks": []}
    transcript = [
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "ok"}]}},
    ]
    result = conversation.shape(transcript, metadata)
    assert result == [
        {"kind": "compile_input", "text": "+ added line"},
        {"kind": "assistant_text", "text": "ok"},
    ]


def test_shape_skips_compile_input_when_spec_diff_empty():
    metadata = {"spec_diff": "", "sculpts": [], "asks": []}
    result = conversation.shape([], metadata)
    assert result == []
