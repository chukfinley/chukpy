"""Batch-generate thumbnails."""
from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer


def thumbnails(
    src: Annotated[Path, typer.Argument(help="Directory with images.", exists=True, file_okay=False, dir_okay=True)],
    out: Annotated[Path, typer.Option("--out", "-o", help="Output directory.")] = None,
    glob: Annotated[str, typer.Option(help="Match pattern.")] = "*.JPG",
    size: Annotated[int, typer.Option(help="Max edge length in pixels.")] = 512,
    quality: Annotated[int, typer.Option(help="JPEG quality.")] = 85,
    format: Annotated[str, typer.Option(help="Output format: jpeg or webp.")] = "jpeg",
) -> None:
    """Generate thumbnails (longest edge = --size) for every image in src."""
    from PIL import Image
    from tqdm import tqdm

    fmt = format.lower()
    if fmt not in ("jpeg", "webp"):
        typer.secho("format must be 'jpeg' or 'webp'", fg=typer.colors.RED, err=True)
        raise typer.Exit(2)
    ext = ".jpg" if fmt == "jpeg" else ".webp"

    out = out or (src.parent / f"{src.name}_thumbs")
    out.mkdir(parents=True, exist_ok=True)

    files = [p for p in sorted(src.glob(glob)) if p.is_file()]
    if not files:
        typer.secho(f"no files matching {glob} in {src}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    for p in tqdm(files, desc="thumbing"):
        try:
            with Image.open(p) as img:
                img = img.convert("RGB")
                img.thumbnail((size, size), Image.LANCZOS)
                img.save(out / f"{p.stem}{ext}", fmt.upper(), quality=quality, optimize=True)
        except Exception as e:
            typer.secho(f"skip {p}: {e}", fg=typer.colors.YELLOW, err=True)

    typer.secho(f"done. {len(files)} thumbs -> {out}", fg=typer.colors.GREEN)
