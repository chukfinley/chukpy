"""`chuktools images` subcommand group: general image tools."""
from __future__ import annotations

import typer

from chuktools.images.dupes import dupes
from chuktools.images.similar import similar
from chuktools.images.organize import organize
from chuktools.images.thumbnails import thumbnails
from chuktools.images.caption import caption
from chuktools.images.translate import translate

app = typer.Typer(help="General image utilities.", no_args_is_help=True)
app.command()(dupes)
app.command()(similar)
app.command()(organize)
app.command()(thumbnails)
app.command()(caption)
app.command()(translate)
