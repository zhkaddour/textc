# textc

> *A natural-language compiler. Your spec is the source language; your project's tests are the type system; git is the substrate.*

`textc` is a spec-driven coding harness that lets you build software by writing and editing a markdown specification. You describe what you want; an AI agent translates it into code; both changes are committed atomically. Each feature is a branch; each merged PR carries its spec into history.

## Why

Most AI coding tools chat their way to a feature. The agent's reasoning lives in scattered chat history; commits don't reflect what was actually requested; intent is lost.

`textc` proposes a different layer: every code change is paired with a corresponding spec change. The spec is the steering document; the code is its projection. The result: a repository that accumulates a clean, readable record of intent → implementation, perfectly traced.

It belongs in the same family as Claude Code, Cursor, Aider, Continue, and Cline — but with a different opinionated workflow: bounded sessions, three verbs, atomic spec↔code commits, audit-ready history.

## Install

```bash
git clone <this repo>
cd textc
pip install -e .
```

Requirements:
- Python 3.11+
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed and on `PATH`
- `ANTHROPIC_API_KEY` set in your environment

## Quickstart

```bash
# Initialize a project
mkdir my-project && cd my-project && git init && git commit --allow-empty -m "init"

# Start a new feature
textc start pendulum

# Edit spec.md in any editor
echo "A pendulum that swings under gravity, rendered in pygame." > spec.md

# Compile — agent reads the spec, writes code, runs tests, commits atomically
textc compile

# Tweak the implementation without changing the spec
textc sculpt "use scipy not numpy"

# Ask without committing
textc ask "why did you choose Verlet integration?"

# Inspect history
textc log
textc show
```

## Concepts

| Concept | Meaning |
|---|---|
| **Spec** (`spec.md`) | A markdown file describing what to build. Lives at the root of the feature branch. |
| **Feature branch** | One branch per feature. Branch name = spec name. |
| **Compile commit** | Pairs a spec diff with the corresponding code change. Atomic. |
| **Sculpt amend** | A code-only modification of the most recent compile. Spec untouched. |
| **Session** | An agent conversation, scoped to one compile. `sculpt` and `ask` continue it; the next `compile` starts a fresh one. |

## Commands

| Command | Purpose |
|---|---|
| `textc start <name>` | Create a feature branch with an empty `spec.md` |
| `textc compile` | Read `spec.md` diff, dispatch agent, atomically commit on success |
| `textc sculpt "<note>"` | Tweak the previous compile's implementation (code only) |
| `textc ask "<question>"` | Query the agent within the current session |
| `textc log` | View the spec ↔ code history on the current branch |
| `textc show [<index>]` | View a specific session log (defaults to latest) |

## Workflow

```
1. textc start <feature-name>
2. Edit spec.md
3. textc compile           (repeat 2–3 as needed for incremental specs)
4. textc sculpt "..."      (if implementation needs tweaking)
5. textc ask "..."         (any time, for clarification)
6. Open PR from feature branch → repo main
7. On merge, move spec.md → /specs/<feature-name>.md (manual for v0)
```

## Files in your repo

After using `textc`, your repo will have:

```
spec.md                           # current feature's spec (on feature branch)
.textc/sessions/<branch>-N.json   # session logs, committed alongside code
specs/                            # archived specs from merged features (on main)
```

Both `.textc/` and `specs/` are committed. The audit trail travels with the code.

## For AI agents writing specs for textc

If you are an AI agent helping a user scaffold a textc spec, follow these conventions.

### What a textc spec is

A textc spec describes **what** the feature should be — observable behavior, components, user-facing capabilities. It does **not** describe implementation choices (libraries, algorithms, line-level structure). Those are the agent's job to decide at compile time.

### Recommended structure

```markdown
# <feature-name>

[One-sentence summary of the feature.]

## Goal

[Why this feature exists. What problem it solves. Who benefits.]

## Behavior

[What the feature does, observably. Use specific verbs. Avoid implementation jargon.]

## Constraints

[Things the implementation must respect — performance bounds, conventions to honor, integrations with existing systems.]

## Notes

[Examples, edge cases, references — anything else.]
```

### A good spec

```markdown
# pendulum

A 2D pendulum simulation rendered in pygame.

## Goal

Demonstrate stable physics simulation as a foundation for more complex mechanism work.

## Behavior

- A single pendulum bob hangs from a fixed pivot
- Gravity pulls the bob down; the bob swings in an arc
- Friction proportional to angular velocity decays the motion over time
- The simulation runs at 60 fps; close the window to exit

## Constraints

- Numerical integration stable over 10 minutes of simulated time (no energy explosion)
- Single-file Python script
```

### A bad spec (don't do this)

```markdown
# pendulum

Use scipy.integrate.solve_ivp with RK45.
Set theta_0 = pi/4.
Loop with dt = 1/60.
```

This is implementation, not specification. Leave decisions like `solve_ivp` for the agent at compile time. If you have a strong implementation preference, express it via a `sculpt` after the compile, not in the spec.

### Evolving the spec

Keep the spec describing **what currently is**, not the history of changes. textc's git history captures evolution; the spec captures the current state.

If a feature is removed: delete the corresponding section from spec.md and `textc compile`. The agent will remove the dependent code (subject to the project's tests).

### Project conventions (CONTEXT.md)

If your project has implementation-level conventions ("we use scipy not numpy", "we prefer Pydantic over dataclasses"), put them in `CONTEXT.md` at the root of the repo. The agent will read it on every compile and respect it without needing to be told repeatedly. The spec stays clean of implementation details.

## How it works

### The pipeline

1. `textc start` creates a branch and scaffolds an empty `spec.md`.
2. User writes the spec.
3. `textc compile` computes `git diff spec.md` and sends it to a Claude Code subprocess with soft hints about where to find project context.
4. The agent reads relevant project files, modifies code, runs any tests it can discover.
5. On success the harness atomically commits everything (spec, code, session log). On failure it reports and doesn't commit.

### Session continuity

Each `compile` opens a fresh agent session. `sculpt` and `ask` continue that session. The next `compile` opens a new one. This is bounded enough to avoid context drift, large enough to avoid expensive re-discovery between sculpts.

Sessions live as JSON in `.textc/sessions/<branch-name>-<index>.json`, committed alongside the code.

### Atomic commits

A `textc compile` either succeeds and commits everything, or fails and changes nothing. There is no half-shipped state.

### Sculpt amends

`textc sculpt` amends the previous compile's commit (code only, spec untouched). Because amend rewrites history, sculpt is only safe before the feature branch is pushed/merged — i.e., during the lifetime of an in-progress PR. This matches normal pre-PR git hygiene.

## Limitations

- Designed for **feature work** — anything that has a spec. Pure refactors, infra changes, and technical-only modifications should use other tools (Claude Code, Cursor, Aider directly).
- Not designed for **multi-engineer concurrent work** on the same feature branch.
- `sculpt` only amends the **most recent** compile. Modifying an earlier commit requires manual git rebase.
- v0 uses Opus 4.7 by default. Model selection is not exposed in the CLI yet.

## License

MIT.
