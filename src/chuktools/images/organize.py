"""Rename/sort images by EXIF DateTime."""
from __future__ import annotations

import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer

EXIF_DATETIME_TAGS = (36867, 36868, 306)  # DateTimeOriginal, DateTimeDigitized, DateTime


def _read_exif_datetime(path: Path) -> datetime | None:
    from PIL import Image, ExifTags  # noqa: F401

    try:
        with Image.open(path) as img:
            exif = img.getexif()
            if not exif:
                return None
            for tag in EXIF_DATETIME_TAGS:
                if tag in exif:
                    raw = exif[tag]
                    if isinstance(raw, bytes):
                        raw = raw.decode("ascii", errors="ignore")
                    try:
                        return datetime.strptime(raw, "%Y:%m:%d %H:%M:%S")
                    except ValueError:
                        continue
    except Exception:
        pass
    return None


def organize(
    src: Annotated[Path, typer.Argument(help="Directory with images.", exists=True, file_okay=False, dir_okay=True)],
    out: Annotated[Path, typer.Option("--out", "-o", help="Output directory.")] = None,
    glob: Annotated[str, typer.Option(help="Match pattern.")] = "*.JPG",
    by: Annotated[str, typer.Option(help="Layout: 'flat' (YYYY-MM-DD_NNN.jpg) or 'tree' (YYYY/MM/DD/NNN.jpg).")] = "flat",
    fallback: Annotated[str, typer.Option(help="Subdir for files without EXIF date.")] = "unknown_date",
    copy: Annotated[bool, typer.Option("--copy/--move", help="Copy (default) or move files.")] = True,
) -> None:
    """Reorganize images by EXIF DateTime into dated filenames or folders."""
    from tqdm import tqdm

    if by not in ("flat", "tree"):
        typer.secho("by must be 'flat' or 'tree'", fg=typer.colors.RED, err=True)
        raise typer.Exit(2)

    out = out or (src.parent / f"{src.name}_organized")
    out.mkdir(parents=True, exist_ok=True)

    files = [p for p in sorted(src.glob(glob)) if p.is_file()]
    if not files:
        typer.secho(f"no files matching {glob} in {src}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    counters: dict[str, int] = defaultdict(int)
    no_date: list[Path] = []
    op = shutil.copy2 if copy else shutil.move

    for p in tqdm(files, desc="organizing"):
        dt = _read_exif_datetime(p)
        if dt is None:
            no_date.append(p)
            continue

        date_key = dt.strftime("%Y-%m-%d")
        counters[date_key] += 1
        n = counters[date_key]
        suffix = p.suffix.lower()

        if by == "flat":
            dest = out / f"{date_key}_{n:03d}{suffix}"
        else:
            day_dir = out / dt.strftime("%Y") / dt.strftime("%m") / dt.strftime("%d")
            day_dir.mkdir(parents=True, exist_ok=True)
            dest = day_dir / f"{n:03d}{suffix}"

        op(str(p), dest)

    if no_date:
        unk_dir = out / fallback
        unk_dir.mkdir(parents=True, exist_ok=True)
        for p in no_date:
            op(str(p), unk_dir / p.name)
        typer.secho(f"{len(no_date)} files had no EXIF date -> {unk_dir}", fg=typer.colors.YELLOW)

    typer.secho(f"done. {len(files)} files -> {out}", fg=typer.colors.GREEN)
