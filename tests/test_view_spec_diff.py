"""Tests for spec line-level diff used by the viewer."""
from textc.viewer import diffs


def test_spec_diff_marks_added_and_removed_lines():
    parent = "alpha\nbeta\ngamma\n"
    current = "alpha\nBETA\ngamma\ndelta\n"
    result = diffs.spec_diff_lines(parent, current)
    kinds = [(line["kind"], line["text"]) for line in result]
    assert kinds == [
        ("unchanged", "alpha"),
        ("removed", "beta"),
        ("added", "BETA"),
        ("unchanged", "gamma"),
        ("added", "delta"),
    ]


def test_spec_diff_handles_empty_parent():
    parent = ""
    current = "first\nsecond\n"
    result = diffs.spec_diff_lines(parent, current)
    assert [(r["kind"], r["text"]) for r in result] == [
        ("added", "first"),
        ("added", "second"),
    ]


def test_spec_diff_handles_empty_current():
    parent = "old\n"
    current = ""
    result = diffs.spec_diff_lines(parent, current)
    assert [(r["kind"], r["text"]) for r in result] == [("removed", "old")]
