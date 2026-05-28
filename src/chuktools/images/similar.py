"""Find near-duplicate / similar images via perceptual hashing."""
from __future__ import annotations

import shutil
from collections import defaultdict
from pathlib import Path
from typing import Annotated

import typer

HASHERS = ("phash", "dhash", "ahash", "whash")


def similar(
    src: Annotated[Path, typer.Argument(help="Directory to scan.", exists=True, file_okay=False, dir_okay=True)],
    glob: Annotated[str, typer.Option(help="Match pattern (use ** for recursive).")] = "**/*.JPG",
    method: Annotated[str, typer.Option(help=f"Hash method: {', '.join(HASHERS)}.")] = "phash",
    threshold: Annotated[int, typer.Option(help="Max Hamming distance to consider similar (0-64). Lower = stricter.")] = 5,
    move: Annotated[Path, typer.Option("--move", help="Move similars (not the keeper) here.")] = None,
    delete: Annotated[bool, typer.Option("--delete", help="Delete similars (not the keeper).")] = False,
) -> None:
    """Cluster near-duplicate images by perceptual hash (default pHash).

    Same group = Hamming distance between hashes <= threshold. For each
    group >1, the first (sorted path) is keeper; the rest are similars.
    """
    import imagehash
    from PIL import Image
    from tqdm import tqdm

    if method not in HASHERS:
        typer.secho(f"unknown method '{method}'. Choices: {HASHERS}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2)
    if move and delete:
        typer.secho("--move and --delete are mutually exclusive", fg=typer.colors.RED, err=True)
        raise typer.Exit(2)

    hash_fn = getattr(imagehash, method)

    files = [p for p in sorted(src.glob(glob)) if p.is_file()]
    if not files:
        typer.secho(f"no files matching {glob} in {src}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    hashes: list[tuple[Path, imagehash.ImageHash]] = []
    for p in tqdm(files, desc="hashing"):
        try:
            with Image.open(p) as img:
                hashes.append((p, hash_fn(img)))
        except Exception as e:
            typer.secho(f"skip {p}: {e}", fg=typer.colors.YELLOW, err=True)

    # Greedy clustering: union-find by pairwise distance.
    parent: dict[int, int] = {i: i for i in range(len(hashes))}

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        a, b = find(i), find(j)
        if a != b:
            parent[a] = b

    for i in range(len(hashes)):
        for j in range(i + 1, len(hashes)):
            if hashes[i][1] - hashes[j][1] <= threshold:
                union(i, j)

    clusters: dict[int, list[Path]] = defaultdict(list)
    for i, (p, _) in enumerate(hashes):
        clusters[find(i)].append(p)

    groups = [sorted(g) for g in clusters.values() if len(g) > 1]
    if not groups:
        typer.secho("no similar groups found.", fg=typer.colors.GREEN)
        return

    total_sims = sum(len(g) - 1 for g in groups)
    typer.echo(f"found {len(groups)} similar groups, {total_sims} non-keeper files (threshold={threshold}, method={method})")

    if move:
        move.mkdir(parents=True, exist_ok=True)

    for group in groups:
        keeper, *rest = group
        typer.echo(f"\nkeep: {keeper}")
        for p in rest:
            if move:
                dest = move / p.name
                if dest.exists():
                    dest = move / f"{p.stem}_sim{p.suffix}"
                shutil.move(str(p), dest)
                typer.echo(f"  moved -> {dest}")
            elif delete:
                p.unlink()
                typer.echo(f"  deleted {p}")
            else:
                typer.echo(f"  similar: {p}")
