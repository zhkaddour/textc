"""Shared pytest fixtures."""
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def git_repo(tmp_path: Path, monkeypatch) -> Path:
    """Initialize a temp git repo and chdir into it. Returns the repo path."""
    monkeypatch.chdir(tmp_path)
    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)
    # Disable GPG signing for tests in case the user's global config has it on.
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=tmp_path, check=True)
    # Initial empty commit so HEAD is valid.
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=tmp_path, check=True, capture_output=True,
    )
    return tmp_path
