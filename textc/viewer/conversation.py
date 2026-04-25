"""Shape stream-json transcript events + sculpts + asks into UI events."""
from __future__ import annotations

_SKIP_SYSTEM_SUBTYPES = {"hook_started", "hook_response"}


def _bash_summary(input_obj: dict) -> str:
    cmd = input_obj.get("command", "")
    return cmd if len(cmd) <= 80 else cmd[:77] + "..."


def _generic_tool_summary(input_obj: dict) -> str:
    # Pick the most informative single string field, else stringify the whole input.
    for key in ("file_path", "path", "pattern", "url", "name", "command"):
        v = input_obj.get(key)
        if isinstance(v, str) and v:
            return v
    return ""


def _shape_assistant(event: dict) -> list[dict]:
    out: list[dict] = []
    content = event.get("message", {}).get("content", [])
    for block in content:
        btype = block.get("type")
        if btype == "text":
            text = block.get("text", "").strip()
            if text:
                out.append({"kind": "assistant_text", "text": text})
        elif btype == "thinking":
            out.append({"kind": "thinking", "text": block.get("thinking", "")})
        elif btype == "tool_use":
            name = block.get("name", "?")
            input_obj = block.get("input", {}) or {}
            summary = _bash_summary(input_obj) if name == "Bash" else _generic_tool_summary(input_obj)
            out.append({"kind": "tool_use", "tool": name, "summary": summary})
    return out


def _shape_system_init(event: dict) -> dict:
    return {
        "kind": "system_init",
        "cwd": event.get("cwd", ""),
        "model": event.get("model", ""),
        "tools": event.get("tools", []) or [],
        "permission_mode": event.get("permissionMode", ""),
    }


def _shape_user(event: dict) -> list[dict]:
    out: list[dict] = []
    content = event.get("message", {}).get("content", [])
    if not isinstance(content, list):
        return out
    for block in content:
        if block.get("type") == "tool_result":
            raw = block.get("content", "")
            if isinstance(raw, list):
                # tool_result content can be a list of typed blocks; flatten
                raw = "\n".join(b.get("text", "") for b in raw if isinstance(b, dict))
            text = str(raw)
            first_line = text.split("\n", 1)[0] if text else ""
            out.append({
                "kind": "tool_result",
                "summary": first_line[:200],
                "full": text,
            })
    return out


def shape(transcript: list[dict], metadata: dict) -> list[dict]:
    """Convert transcript events + metadata into a UI-friendly event list.

    Order: user inputs first (compile_input, sculpts, asks), then transcript events.
    Sculpts and asks are surfaced as prominent user-input events at the top so
    the conversation panel reads as: what the user asked → what the agent did.
    """
    out: list[dict] = []

    spec_diff = metadata.get("spec_diff")
    if isinstance(spec_diff, str) and spec_diff:
        out.append({"kind": "compile_input", "text": spec_diff})

    for sculpt in metadata.get("sculpts", []) or []:
        out.append({
            "kind": "sculpt",
            "note": sculpt.get("note", ""),
            "at": sculpt.get("at", ""),
        })
    for ask in metadata.get("asks", []) or []:
        out.append({
            "kind": "ask",
            "question": ask.get("question", ""),
            "answer": ask.get("answer", ""),
            "at": ask.get("at", ""),
        })

    for event in transcript:
        etype = event.get("type")
        if etype == "system":
            subtype = event.get("subtype")
            if subtype in _SKIP_SYSTEM_SUBTYPES:
                continue
            if subtype == "init":
                out.append(_shape_system_init(event))
            # other system subtypes ignored
        elif etype == "assistant":
            out.extend(_shape_assistant(event))
        elif etype == "user":
            out.extend(_shape_user(event))
        # other types ignored

    return out
