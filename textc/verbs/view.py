"""Implements `textc view` — launches the local viewer server and opens the browser."""
from __future__ import annotations

import socket
import webbrowser

import uvicorn

from textc import git_ops
from textc.errors import NotInGitRepoError
from textc.viewer import server


def _pick_free_port() -> int:
    """Bind to port 0, ask the kernel for a free port, return it. Releases the socket immediately."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run(port: int | None = None, open_browser: bool = True) -> None:
    if not git_ops.in_git_repo():
        raise NotInGitRepoError("Not in a git repository.")

    chosen = port if port is not None else _pick_free_port()
    url = f"http://localhost:{chosen}"

    print(f"textc viewer: serving at {url}")
    print("press Ctrl-C to stop.")

    if open_browser:
        webbrowser.open(url)

    app = server.create_app()
    uvicorn.run(app, host="127.0.0.1", port=chosen, log_level="warning")
