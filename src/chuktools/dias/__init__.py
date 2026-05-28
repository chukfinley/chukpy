"""`chuktools dias` subcommand group."""
from __future__ import annotations

import typer

from chuktools.dias.rotate import rotate
from chuktools.dias.caption import caption

app = typer.Typer(help="Tools for scanned slides (Dias).", no_args_is_help=True)
app.command()(rotate)
app.command()(caption)
