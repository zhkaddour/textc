import pytest

from textc.errors import (
    TextcError,
    NotInGitRepoError,
    NotOnFeatureBranchError,
    DirtyWorkingTreeError,
    NoCompileToSculptError,
    NoActiveSessionError,
)


def test_all_errors_inherit_from_textc_error():
    for cls in [
        NotInGitRepoError,
        NotOnFeatureBranchError,
        DirtyWorkingTreeError,
        NoCompileToSculptError,
        NoActiveSessionError,
    ]:
        assert issubclass(cls, TextcError)


def test_errors_carry_user_message():
    e = NotInGitRepoError("Not in a git repository.")
    assert str(e) == "Not in a git repository."


def test_textc_error_is_an_exception():
    assert issubclass(TextcError, Exception)
