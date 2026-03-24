"""CLI entrypoints for OpenSprite."""

from __future__ import annotations

import typer

from .. import __version__
from ..runtime import main as run_service

app = typer.Typer(
    add_completion=False,
    no_args_is_help=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)


def version_callback(value: bool) -> None:
    """Print the package version and exit."""
    if value:
        typer.echo(f"opensprite {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show the OpenSprite version and exit.",
    ),
) -> None:
    """OpenSprite CLI."""
    if version:
        return
    if ctx.invoked_subcommand is None:
        run_service()


@app.command()
def run() -> None:
    """Start the OpenSprite service."""
    run_service()


if __name__ == "__main__":
    app()
