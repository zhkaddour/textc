import subprocess
from pathlib import Path

import pytest

from textc import git_ops
from textc.errors import NotInGitRepoError


def test_in_git_repo_true(git_repo: Path):
    assert git_ops.in_git_repo() is True


def test_in_git_repo_false(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert git_ops.in_git_repo() is False


def test_current_branch(git_repo: Path):
    assert git_ops.current_branch() == "main"


def test_create_branch_and_switch(git_repo: Path):
    git_ops.create_branch("pendulum")
    assert git_ops.current_branch() == "pendulum"


def test_is_modified_relative_to_head(git_repo: Path):
    Path("spec.md").write_text("hello")
    assert git_ops.is_modified("spec.md") is True
    subprocess.run(["git", "add", "spec.md"], check=True)
    subprocess.run(["git", "commit", "-m", "add spec"], check=True, capture_output=True)
    assert git_ops.is_modified("spec.md") is False
    Path("spec.md").write_text("changed")
    assert git_ops.is_modified("spec.md") is True


def test_working_tree_dirty_excluding(git_repo: Path):
    assert git_ops.working_tree_dirty(exclude=["spec.md"]) is False
    Path("spec.md").write_text("hello")
    assert git_ops.working_tree_dirty(exclude=["spec.md"]) is False  # excluded
    Path("other.py").write_text("hi")
    assert git_ops.working_tree_dirty(exclude=["spec.md"]) is True


def test_diff_against_head(git_repo: Path):
    Path("spec.md").write_text("hello\n")
    diff = git_ops.diff_against_head("spec.md")
    assert "+hello" in diff


def test_commit_creates_commit(git_repo: Path):
    Path("foo.txt").write_text("x")
    git_ops.add(["foo.txt"])
    git_ops.commit("first commit\n\nbody line")
    log = subprocess.run(["git", "log", "--format=%s%n%b", "-n", "1"],
                         capture_output=True, text=True, check=True).stdout
    assert "first commit" in log
    assert "body line" in log


def test_commit_allow_empty(git_repo: Path):
    git_ops.commit("empty commit", allow_empty=True)
    log = subprocess.run(["git", "log", "--format=%s", "-n", "1"],
                         capture_output=True, text=True, check=True).stdout.strip()
    assert log == "empty commit"


def test_amend_keeps_subject_appends_body(git_repo: Path):
    Path("foo.txt").write_text("x")
    git_ops.add(["foo.txt"])
    git_ops.commit("subject\n\nbody1")
    Path("bar.txt").write_text("y")
    git_ops.add(["bar.txt"])
    git_ops.amend(append_body_line="body2")
    log = subprocess.run(["git", "log", "--format=%s%n%b", "-n", "1"],
                         capture_output=True, text=True, check=True).stdout
    assert "subject" in log
    assert "body1" in log
    assert "body2" in log


def test_log_subjects_on_branch(git_repo: Path):
    Path("a").write_text("a"); git_ops.add(["a"]); git_ops.commit("first")
    Path("b").write_text("b"); git_ops.add(["b"]); git_ops.commit("second")
    subjects = git_ops.log_subjects()
    assert subjects[:2] == ["second", "first"]


def test_head_subject_and_body(git_repo: Path):
    Path("foo").write_text("x"); git_ops.add(["foo"]); git_ops.commit("subj\n\nbody")
    assert git_ops.head_subject() == "subj"
    assert "body" in git_ops.head_body()
