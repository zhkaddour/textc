"""Tests for branch discovery in the viewer."""
from textc.viewer import branches

from tests.conftest import git_repo  # existing fixture


def test_list_textc_branches_returns_only_branches_with_textc_commits(git_repo, monkeypatch):
    monkeypatch.chdir(git_repo)
    import subprocess
    # main is the initial branch with no textc commits
    subprocess.run(["git", "checkout", "-b", "feature-a"], check=True, capture_output=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "[textc] start feature-a"], check=True, capture_output=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "[textc] add gravity"], check=True, capture_output=True)
    subprocess.run(["git", "checkout", "-b", "feature-b"], check=True, capture_output=True)
    subprocess.run(["git", "checkout", "main"], check=True, capture_output=True)
    subprocess.run(["git", "checkout", "-b", "no-textc"], check=True, capture_output=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "regular commit"], check=True, capture_output=True)

    result = branches.list_textc_branches()
    assert "feature-a" in result
    assert "feature-b" in result  # has the [textc] start from feature-a
    assert "no-textc" not in result
