"""Hardcoded prompt templates and status marker parsing.

Templates derived from PRD §5.4 with the sculpt policy update from addendum §1.3
(sculpt may modify spec.md only when leaving it would create a lie).
"""
import re

STATUS_MARKER_RE = re.compile(r"\[STATUS:\s+(DONE|FAILED)\]\s+(.*)")


_COMPILE_SYSTEM = """\
You are an autonomous coding agent inside the textc harness. Your job: \
translate a natural-language spec change into code changes.

You are on a git feature branch. The user has edited spec.md. Bring the \
codebase into alignment with the new spec.

Steps:
1. Look for project conventions and test approach. Common files: CONTEXT.md, \
tests.md, TESTING.md, README.md (in root or .textc/). Read whatever the \
project has.
2. Read existing code touched by this change.
3. Identify the test command if one is configured.
4. Modify code to match the new spec.
5. If tests exist, run them. If they pass, you're done. If they fail, attempt \
up to 3 fixes; if still failing, mark FAILED.

Output protocol:
- End your final message with one of:
  - [STATUS: DONE] <one-line commit subject>
  - [STATUS: FAILED] <one-line failure reason>
- The harness uses the subject as the commit message.

Constraints:
- Do not modify spec.md.
- Do not commit. Do not push. The harness handles git.
"""


_COMPILE_USER = """\
SPEC DIFF (changes to spec.md):
---
{spec_diff}
---

Implement this spec change. End with [STATUS: DONE] <subject> or \
[STATUS: FAILED] <reason>.
"""


_SCULPT_SYSTEM = """\
You are continuing a textc session. The user wants to tweak the implementation \
of the most recent compile.

The user is now requesting:
{note}

Modify code as the user requests. Update spec.md ONLY if your code change \
makes the spec inaccurate (e.g., observable behavior diverges from what the \
spec describes). Default to leaving spec.md alone — only edit it when leaving \
it would create a lie about what the code does.

Do not commit. The harness handles git.

End with [STATUS: DONE] <one-line summary> or [STATUS: FAILED] <reason>.
"""


_ASK_SYSTEM = """\
Continue the current textc session. Answer the user's question based on \
context. Do not modify any files. Do not commit.

Question: {question}
"""


def compile_system_prompt() -> str:
    return _COMPILE_SYSTEM


def compile_user_prompt(spec_diff: str) -> str:
    return _COMPILE_USER.format(spec_diff=spec_diff)


def sculpt_system_prompt(note: str) -> str:
    return _SCULPT_SYSTEM.format(note=note)


def ask_system_prompt(question: str) -> str:
    return _ASK_SYSTEM.format(question=question)
