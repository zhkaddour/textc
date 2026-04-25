"""Tests for the textc view launcher (port pick + browser open)."""
from unittest.mock import patch

from textc.verbs import view


def test_pick_free_port_returns_int_in_user_range():
    port = view._pick_free_port()
    assert isinstance(port, int)
    assert 1024 < port < 65536


def test_run_opens_browser_and_calls_uvicorn(monkeypatch):
    calls = {}

    def fake_uvicorn_run(app, host, port, log_level):
        calls["uvicorn"] = {"host": host, "port": port}

    def fake_browser_open(url):
        calls["browser"] = url

    monkeypatch.setattr("textc.git_ops.in_git_repo", lambda: True)
    monkeypatch.setattr("uvicorn.run", fake_uvicorn_run)
    monkeypatch.setattr("webbrowser.open", fake_browser_open)

    view.run(port=54321, open_browser=True)

    assert calls["uvicorn"]["port"] == 54321
    assert calls["browser"] == "http://localhost:54321"


def test_run_skips_browser_when_disabled(monkeypatch):
    opened = []
    monkeypatch.setattr("textc.git_ops.in_git_repo", lambda: True)
    monkeypatch.setattr("uvicorn.run", lambda *a, **kw: None)
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url))

    view.run(port=54322, open_browser=False)
    assert opened == []
