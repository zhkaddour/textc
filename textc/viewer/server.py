"""FastAPI app for the textc viewer."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from textc import git_ops, session
from textc.viewer import branches, commits, conversation, diffs

_STATIC_DIR = Path(__file__).parent / "static"


def _session_index_for_sha(sha: str) -> int | None:
    """Find the session index for a given commit sha.

    The compile commit's session JSON is `<branch>-<index>.json` and is committed
    alongside the code change. We grep the commit for an added/modified
    `.textc/sessions/<branch>-N.json` and return N.
    """
    import subprocess
    result = subprocess.run(
        ["git", "show", "--name-only", "--format=", sha],
        capture_output=True, text=True, check=False,
    )
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith(".textc/sessions/") and line.endswith(".json") \
                and not line.endswith(".failed.json"):
            stem = Path(line).stem  # "<branch>-<index>"
            try:
                return int(stem.rsplit("-", 1)[1])
            except (IndexError, ValueError):
                continue
    return None


def create_app() -> FastAPI:
    app = FastAPI(title="textc viewer")

    @app.get("/api/state")
    def state():
        return {
            "current_branch": git_ops.current_branch(),
            "branches": branches.list_textc_branches(),
            "commits": commits.list_textc_commits(),
        }

    @app.get("/api/commit/{sha}")
    def commit_detail(sha: str):
        branch = git_ops.current_branch()
        # Find the parsed entry for this commit
        all_commits = commits.list_textc_commits()
        match = next((c for c in all_commits if c["sha"].startswith(sha) or c["sha"] == sha), None)
        if match is None:
            raise HTTPException(status_code=404, detail=f"Commit {sha} not found in [textc] history")

        psha = diffs.parent_sha(match["sha"])
        parent_spec = diffs.read_spec_at(branch, psha) if psha else ""
        current_spec = diffs.read_spec_at(branch, match["sha"])
        spec_lines = diffs.spec_diff_lines(parent_spec, current_spec)
        cdiff = diffs.code_diff(psha, match["sha"])

        idx = _session_index_for_sha(match["sha"])
        if idx is not None:
            try:
                sess = session.read(branch, idx)
            except FileNotFoundError:
                sess = {"metadata": {"sculpts": [], "asks": []}, "transcript": []}
        else:
            sess = {"metadata": {"sculpts": [], "asks": []}, "transcript": []}

        conv = conversation.shape(sess.get("transcript", []), sess.get("metadata", {}))

        return {
            "sha": match["sha"],
            "subject": match["subject"],
            "compiled_at": match["compiled_at"],
            "sculpts": match["sculpts"],
            "spec_lines": spec_lines,
            "code_diff": cdiff,
            "conversation": conv,
            "session_index": idx,
        }

    @app.get("/")
    def index():
        index_path = _STATIC_DIR / "index.html"
        if not index_path.exists():
            raise HTTPException(status_code=503, detail="Frontend assets not built yet")
        return FileResponse(index_path)

    if _STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    return app
