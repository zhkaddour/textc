"""Typed exceptions for textc block conditions.

Each subclass maps to a row in the behavior matrix (addendum §2).
The CLI catches TextcError at the top level and renders the message to the
user without a traceback.
"""


class TextcError(Exception):
    """Base class for all textc-level errors. The CLI catches these and
    renders the message to the user without a traceback."""


class NotInGitRepoError(TextcError):
    """Case 13 — current directory is not inside a git repo."""


class NotOnFeatureBranchError(TextcError):
    """Case 14 — current branch is `main` or detached HEAD."""


class DirtyWorkingTreeError(TextcError):
    """Cases 11, 12 — working tree has unexpected uncommitted changes."""


class NoCompileToSculptError(TextcError):
    """Case 8 — sculpt requested but no [textc] compile commit exists yet."""


class NoActiveSessionError(TextcError):
    """Case 7 — ask requested but no session JSON exists for HEAD."""


class NoSpecChangeError(TextcError):
    """Used internally by compile to distinguish anchor case 3 from case 2.
    Not raised to the user."""


class AgentFailureError(TextcError):
    """Case 9 — the agent returned [STATUS: FAILED] or timed out."""
