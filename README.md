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
| `textc start <name>` | Create a feature branch named `<name>`, scaffold an empty spec at `.textc/specs/<name>.md`, and commit the scaffold. |
| `textc compile` | Read what changed in the spec, dispatch the agent to write the matching code, then atomically commit the spec change, the code, and the session log together. |
| `textc sculpt "<note>"` | Tweak the previous compile's implementation. Amends the prior commit; the spec stays untouched unless leaving it would lie about what the code now does. |
| `textc ask "<question>"` | Query the agent within the current session — no git ops, no file changes. Useful for understanding why a compile chose a particular approach. |
| `textc log` | Render the spec↔code history on the current branch as a tree, showing each compile's subject and any sculpt notes. |
| `textc show [<n>]` | Pretty-print a session JSON: spec diff, agent transcript, sculpts, asks. Defaults to the latest session. |
| `textc view` | Launch the browser-based viewer — a live spec↔code timeline that updates as compiles land. |

## How to use it

### Writing a good spec

A textc spec describes **what** the feature should be — observable behavior, components, user-facing capabilities — not **how** to build it. Implementation choices (libraries, algorithms, file layout) are the agent's job; you state intent.

Recommended structure:

```markdown
# <feature-name>

[One-sentence summary.]

## Goal
[Why this feature exists. What problem it solves.]

## Behavior
[What the feature does, observably. Specific verbs. Avoid implementation jargon.]

## Constraints
[What the implementation must respect — performance bounds, integrations, conventions.]

## Notes
[Examples, edge cases, references.]
```

**A good spec:**

```markdown
# pendulum

A 2D pendulum simulation rendered in pygame.

## Behavior
- A single bob hangs from a fixed pivot
- Gravity pulls the bob down; the bob swings in an arc
- Friction proportional to angular velocity decays motion over time
- The simulation runs at 60 FPS; close the window to exit

## Constraints
- Numerical integration stable over 10 minutes (no energy explosion)
- Single-file Python script
```

**A bad spec:**

```markdown
# pendulum
Use scipy.integrate.solve_ivp with RK45.
Set theta_0 = pi/4.
Loop with dt = 1/60.
```

That's implementation, not specification. If you have strong implementation preferences, express them via `textc sculpt` after the compile, or move them into `CONTEXT.md` for project-wide conventions.

### Evolving a spec

Keep the spec describing **what currently is**, not the history of changes. Git captures evolution; the spec captures the present state.

To remove a feature, delete its section and run `textc compile`. The agent removes the dependent code (subject to your tests).

### Project conventions: `CONTEXT.md` and `tests.md`

textc reads two optional files at the repo root:

- `CONTEXT.md` — implementation conventions (*"we use scipy not numpy"*, style preferences, what *not* to import). The agent reads it on every compile.
- `tests.md` — how to verify changes (test commands, static checks, things to avoid running).

Both are user-authored. The spec stays focused on *what to build*; conventions live separately so they don't bloat each spec.

## How it works

Each `compile` opens a fresh Claude Code session, scoped to one spec change. The session JSON is written to `.textc/sessions/<branch>-<n>.json` and committed alongside the code — the audit trail travels with the work. `sculpt` and `ask` continue that session; the next `compile` opens a new one. Bounded context (no chat-bloat drift) without re-discovery cost between iterations.