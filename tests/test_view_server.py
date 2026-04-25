"""Tests for FastAPI viewer endpoints."""
from fastapi.testclient import TestClient

from textc.viewer import server


def test_state_endpoint_returns_branches_and_commits(monkeypatch):
    monkeypatch.setattr("textc.viewer.branches.list_textc_branches",
                        lambda: ["pendulum", "parser"])
    monkeypatch.setattr("textc.git_ops.current_branch", lambda: "pendulum")
    monkeypatch.setattr("textc.viewer.commits.list_textc_commits",
                        lambda limit=200: [
                            {"sha": "c2", "subject": "add gravity", "compiled_at": "t2",
                             "sculpts": [{"note": "fix sign"}], "files_changed": 1},
                            {"sha": "c1", "subject": "scaffold", "compiled_at": "t1",
                             "sculpts": [], "files_changed": 1},
                        ])

    app = server.create_app()
    client = TestClient(app)
    response = client.get("/api/state")
    assert response.status_code == 200
    data = response.json()
    assert data["current_branch"] == "pendulum"
    assert data["branches"] == ["pendulum", "parser"]
    assert len(data["commits"]) == 2
    assert data["commits"][0]["sha"] == "c2"
    assert data["commits"][0]["sculpts"] == [{"note": "fix sign"}]


def test_commit_endpoint_returns_bundle(monkeypatch):
    monkeypatch.setattr("textc.git_ops.current_branch", lambda: "pendulum")
    monkeypatch.setattr("textc.viewer.diffs.parent_sha", lambda sha: "c1")
    monkeypatch.setattr("textc.viewer.diffs.read_spec_at",
                        lambda branch, sha: "alpha\n" if sha == "c1" else "alpha\nbeta\n")
    monkeypatch.setattr("textc.viewer.diffs.code_diff", lambda parent, sha: [{"file": "a.py", "hunks": []}])
    monkeypatch.setattr("textc.viewer.commits.list_textc_commits",
                        lambda limit=200: [
                            {"sha": "c2", "subject": "add", "compiled_at": "t",
                             "sculpts": [], "files_changed": 1},
                        ])

    # Provide a fake session JSON read for c2
    def fake_session_read(*args, **kwargs):
        return {"metadata": {"sculpts": [], "asks": []}, "transcript": []}
    monkeypatch.setattr("textc.session.read", fake_session_read)
    monkeypatch.setattr("textc.viewer.server._session_index_for_sha", lambda sha: 1)

    app = server.create_app()
    client = TestClient(app)
    response = client.get("/api/commit/c2")
    assert response.status_code == 200
    data = response.json()
    assert data["sha"] == "c2"
    assert data["subject"] == "add"
    spec_kinds = [line["kind"] for line in data["spec_lines"]]
    assert "added" in spec_kinds
    assert data["code_diff"] == [{"file": "a.py", "hunks": []}]
    assert data["conversation"] == []


def test_session_index_for_sha_parses_branch_with_hyphen(monkeypatch):
    class FakeProc:
        stdout = ".textc/sessions/feature-a-3.json\nsome_code.py\n"
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: FakeProc())
    assert server._session_index_for_sha("any") == 3


def test_session_index_for_sha_skips_failed_sessions(monkeypatch):
    class FakeProc:
        stdout = ".textc/sessions/feature-2.failed.json\n.textc/sessions/feature-2.json\n"
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: FakeProc())
    assert server._session_index_for_sha("any") == 2


def test_session_index_for_sha_returns_none_when_no_session_in_commit(monkeypatch):
    class FakeProc:
        stdout = "some_code.py\nREADME.md\n"
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: FakeProc())
    assert server._session_index_for_sha("any") is None
