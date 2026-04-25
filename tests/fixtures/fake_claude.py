"""Fake `claude` binary for tests. Reads `--scenario <name>` from argv and
emits canned stream-json events to stdout.

Scenarios:
  done_simple   — emits init + assistant with [STATUS: DONE] subject + result
  failed        — emits init + assistant with [STATUS: FAILED] reason + result
  no_marker     — emits assistant with no status marker (treated as failure)
  hang          — sleeps 30 seconds (used for timeout testing)
"""
import json
import sys
import time


def emit(obj: dict) -> None:
    print(json.dumps(obj), flush=True)


def main() -> int:
    scenario = "done_simple"
    if "--scenario" in sys.argv:
        scenario = sys.argv[sys.argv.index("--scenario") + 1]

    if scenario == "hang":
        time.sleep(30)
        return 0

    emit({"type": "system", "subtype": "init", "session_id": "fake-sess-001",
          "model": "claude-opus-4-7"})

    if scenario == "done_simple":
        emit({"type": "assistant", "message": {"content": [
            {"type": "text", "text": "Working...\n[STATUS: DONE] add pendulum gravity"}
        ]}})
        emit({"type": "result", "subtype": "success"})
    elif scenario == "failed":
        emit({"type": "assistant", "message": {"content": [
            {"type": "text", "text": "[STATUS: FAILED] tests do not pass"}
        ]}})
        emit({"type": "result", "subtype": "success"})
    elif scenario == "no_marker":
        emit({"type": "assistant", "message": {"content": [
            {"type": "text", "text": "I just rambled with no marker"}
        ]}})
        emit({"type": "result", "subtype": "success"})

    return 0


if __name__ == "__main__":
    sys.exit(main())
