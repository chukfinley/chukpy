"""Find exact-duplicate image files via SHA256 hashing."""
from __future__ import annotations

import hashlib
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Annotated

import typer


def _sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            buf = f.read(chunk)
            if not buf:
                break
            h.update(buf)
    return h.hexdigest()


def dupes(
    src: Annotated[Path, typer.Argument(help="Directory to scan.", exists=True, file_okay=False, dir_okay=True)],
    glob: Annotated[str, typer.Option(help="Match pattern (use ** for recursive).")] = "**/*",
    move: Annotated[Path, typer.Option("--move", help="Move duplicates here (keeps first occurrence).")] = None,
    delete: Annotated[bool, typer.Option("--delete", help="Delete duplicates (keeps first). Mutually exclusive with --move.")] = False,
) -> None:
    """Find pixel-identical duplicates via SHA256. By default only reports.

    Files are grouped by hash; for each group with >1 file, the first one (by
    sorted path) is the keeper. Pass --move or --delete to act on the rest.
    """
    from tqdm import tqdm

    if move and delete:
        typer.secho("--move and --delete are mutually exclusive", fg=typer.colors.RED, err=True)
        raise typer.Exit(2)

    files = [p for p in sorted(src.glob(glob)) if p.is_file()]
    if not files:
        typer.secho(f"no files matching {glob} in {src}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    by_hash: dict[str, list[Path]] = defaultdict(list)
    for p in tqdm(files, desc="hashing"):
        by_hash[_sha256(p)].append(p)

    groups = [paths for paths in by_hash.values() if len(paths) > 1]
    if not groups:
        typer.secho("no duplicates found.", fg=typer.colors.GREEN)
        return

    total_dupes = sum(len(g) - 1 for g in groups)
    typer.echo(f"found {len(groups)} dupe groups, {total_dupes} extra files")

    if move:
        move.mkdir(parents=True, exist_ok=True)

    for group in groups:
        keeper, *rest = group
        typer.echo(f"\nkeep: {keeper}")
        for p in rest:
            if move:
                dest = move / p.name
                if dest.exists():
                    dest = move / f"{p.stem}_{_sha256(p)[:8]}{p.suffix}"
                shutil.move(str(p), dest)
                typer.echo(f"  moved -> {dest}")
            elif delete:
                p.unlink()
                typer.echo(f"  deleted {p}")
            else:
                typer.echo(f"  dupe: {p}")
