"""Tests for unified-diff parsing."""
from textc.viewer import diffs

SAMPLE = """\
diff --git a/pendulum.py b/pendulum.py
index 0123abc..def4567 100644
--- a/pendulum.py
+++ b/pendulum.py
@@ -1,4 +1,5 @@
 import pygame
 from math import sin
-omega += alpha * dt
+damping = 0.05
+omega = (omega + alpha*dt) * (1 - damping*dt)
 return theta, omega
diff --git a/util.py b/util.py
new file mode 100644
index 0000000..89abcde
--- /dev/null
+++ b/util.py
@@ -0,0 +1,2 @@
+def helper():
+    return 1
"""


def test_parse_unified_diff_two_files():
    result = diffs.parse_unified_diff(SAMPLE)
    assert len(result) == 2
    pendulum, util = result

    assert pendulum["file"] == "pendulum.py"
    assert len(pendulum["hunks"]) == 1
    hunk = pendulum["hunks"][0]
    assert hunk["header"].startswith("@@ -1,4 +1,5 @@")
    kinds = [(line["kind"], line["text"]) for line in hunk["lines"]]
    assert kinds == [
        ("context", "import pygame"),
        ("context", "from math import sin"),
        ("removed", "omega += alpha * dt"),
        ("added", "damping = 0.05"),
        ("added", "omega = (omega + alpha*dt) * (1 - damping*dt)"),
        ("context", "return theta, omega"),
    ]

    assert util["file"] == "util.py"
    assert util["hunks"][0]["lines"] == [
        {"kind": "added", "text": "def helper():"},
        {"kind": "added", "text": "    return 1"},
    ]


def test_parse_unified_diff_empty():
    assert diffs.parse_unified_diff("") == []


DELETION_SAMPLE = """\
diff --git a/old.py b/old.py
deleted file mode 100644
index 1234567..0000000
--- a/old.py
+++ /dev/null
@@ -1,3 +0,0 @@
-line 1
-line 2
-line 3
"""


def test_parse_unified_diff_handles_file_deletion():
    result = diffs.parse_unified_diff(DELETION_SAMPLE)
    assert len(result) == 1
    deleted = result[0]
    assert deleted["file"] == "old.py"
    assert len(deleted["hunks"]) == 1
    assert [(l["kind"], l["text"]) for l in deleted["hunks"][0]["lines"]] == [
        ("removed", "line 1"),
        ("removed", "line 2"),
        ("removed", "line 3"),
    ]
