# textc

> *A natural-language compiler. Your spec is the source language; your project's tests are the type system; git is the substrate.*

**One markdown document describes the feature.** You edit prose; the agent ships the code; both are committed together. The document is the source — code is what gets compiled from it.

This is what vibe coding looks like when intent is durable. Your reasoning lives in the repo as a canonical document — edited like source code, versioned like source code, *is* source code.

Edit a section: behavior updates. Delete a section: the feature disappears. Read the git log: you're reading your decisions.

Cursor and Aider ship code with AI assistance. textc ships intent — and the code follows.

## A 30-second look

```bash
mkdir my-game && cd my-game && git init && git commit --allow-empty -m init

# Start a feature branch — scaffolds an empty .textc/specs/<branch>.md
textc start snake

# Edit the spec in your editor of choice
code .textc/specs/snake.md

# Compile: agent reads the spec diff, writes code, commits both atomically
textc compile

# Tweak code without changing the spec
textc sculpt "use a dataclass for game state"

# Ask without committing
textc ask "why a time accumulator?"

# Inspect the spec↔code narrative
textc log
```

## Install

```bash
git clone <this repo> && cd textc && pip install -e .
```

Requirements: Python 3.11+, [Claude Code](https://docs.anthropic.com/en/docs/claude-code) on `PATH`, `ANTHROPIC_API_KEY` set.

## The verbs

| Command | What it does |
|---|---|
| `textc start <name>` | Branch off `main`, scaffold `.textc/specs/<name>.md`, commit |
| `textc compile` | Read spec diff, dispatch agent, atomic spec↔code commit |
| `textc sculpt "<note>"` | Tweak the previous compile's code (amend; spec stays untouched unless leaving it would lie) |
| `textc ask "<question>"` | Query the current session — no git ops |
| `textc log` | Render the spec↔code history on the current branch |
| `textc show [<n>]` | Pretty-print a session JSON |

## Working in your project

textc reads two optional files at the repo root:

- `CONTEXT.md` — project conventions (stack, file layout, style, what *not* to import). The agent reads it on every compile.
- `tests.md` — how to verify changes (test commands, static checks, things to avoid running).

Both are user-authored. The spec stays focused on *what to build*; conventions and test approach live separately.

## How it works

Each `compile` opens a fresh Claude Code session, scoped to one spec change. The session JSON is written to `.textc/sessions/<branch>-<n>.json` and committed alongside the code — the audit trail travels with the work. `sculpt` and `ask` continue that session; the next `compile` opens a new one. Bounded context (no chat-bloat drift) without re-discovery cost between iterations.

## Limitations

- Designed for **feature work** — anything that has a spec. Pure refactors and infra changes should use Claude Code, Cursor, or Aider directly.
- Single author per branch.
- `sculpt` only amends the most recent compile.
- v0 uses Opus 4.7; model selection isn't exposed in the CLI yet.

## License

MIT.
