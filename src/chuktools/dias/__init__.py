"""`chuktools dias` subcommand group: Dia-specific tools."""
from __future__ import annotations

import typer

from chuktools.dias.rotate import rotate

app = typer.Typer(help="Tools for scanned slides (Dias).", no_args_is_help=True)
app.command()(rotate)
