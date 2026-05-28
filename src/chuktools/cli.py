"""chuktools root CLI. Register subcommand groups here."""
from __future__ import annotations

import typer

from chuktools.dias import app as dias_app

app = typer.Typer(
    help="Chuk's personal CLI grab-bag.",
    no_args_is_help=True,
    add_completion=False,
)

app.add_typer(dias_app, name="dias", help="Tools for scanned slides (Dias).")


if __name__ == "__main__":
    app()
