"""textc CLI entry point. Dispatches to verb modules."""
import sys

import click

from textc import __version__
from textc.errors import TextcError


def _safe_run(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except TextcError as e:
        click.echo(f"textc: {e}", err=True)
        sys.exit(1)


@click.group()
@click.version_option(version=__version__, prog_name="textc")
def main():
    """textc — spec-driven coding harness."""


@main.command()
@click.argument("name")
def start(name: str):
    """Create a new feature branch with an empty spec.md."""
    from textc.verbs.start import run
    _safe_run(run, name)


@main.command()
def compile():
    """Read spec.md diff, dispatch agent, atomically commit on success."""
    from textc.verbs.compile import run
    _safe_run(run)


@main.command()
@click.argument("note")
def sculpt(note: str):
    """Tweak the previous compile's implementation."""
    from textc.verbs.sculpt import run
    _safe_run(run, note)


@main.command()
@click.argument("question")
def ask(question: str):
    """Query the agent within the current session."""
    from textc.verbs.ask import run
    _safe_run(run, question)


@main.command()
def log():
    """Show the spec ↔ code history on the current branch."""
    from textc.verbs.log import run
    _safe_run(run)


@main.command()
@click.argument("index", type=int, required=False)
def show(index: int | None):
    """Show a specific session log (defaults to latest)."""
    from textc.verbs.show import run
    _safe_run(run, index)


if __name__ == "__main__":
    main()
