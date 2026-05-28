"""Translate an existing _captions.tsv and rename files into a new directory."""
from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Annotated

import typer

MT_MODELS = {
    "de": "Helsinki-NLP/opus-mt-en-de",
    "fr": "Helsinki-NLP/opus-mt-en-fr",
    "es": "Helsinki-NLP/opus-mt-en-es",
    "it": "Helsinki-NLP/opus-mt-en-it",
    "nl": "Helsinki-NLP/opus-mt-en-nl",
    "ru": "Helsinki-NLP/opus-mt-en-ru",
}


STOPWORDS = {
    # English
    "a", "an", "the", "this", "that", "these", "those", "there", "here",
    "is", "are", "was", "were", "be", "been", "being",
    "of", "in", "on", "at", "to", "for", "with", "and", "or", "by",
    "it", "its", "as", "from", "into", "picture", "image", "photo",
    # German
    "ein", "eine", "einen", "einer", "eines", "einem",
    "der", "die", "das", "des", "dem", "den",
    "ist", "sind", "war", "waren", "sein", "wird",
    "es", "da", "dort", "hier", "dies", "diese", "dieser", "dieses",
    "gibt", "steht", "sitzt", "sitzen", "im", "in", "auf", "an", "am",
    "und", "oder", "mit", "zu", "zum", "zur", "von", "vom", "bei", "fuer",
    "bild", "foto", "des", "vor", "nach", "ueber", "unter",
}


def _slugify(text: str, max_words: int = 6) -> str:
    text = text.lower().strip().rstrip(".,!?")
    text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    words = [w for w in text.split() if w not in STOPWORDS]
    return "_".join(words[:max_words]) or "untitled"


def translate(
    src: Annotated[Path, typer.Argument(help="Directory containing _captions.tsv (output of `images caption`).", exists=True, file_okay=False, dir_okay=True)],
    out: Annotated[Path, typer.Option("--out", "-o", help="Output directory for renamed files.")] = None,
    lang: Annotated[str, typer.Option(help=f"Target language. One of: {', '.join(MT_MODELS)}.")] = "de",
    max_words: Annotated[int, typer.Option(help="Max words used for slug.")] = 6,
    tsv_name: Annotated[str, typer.Option(help="Name of the captions TSV inside src.")] = "_captions.tsv",
) -> None:
    """Translate captions in `<src>/_captions.tsv` and rename images to slugified target-language names."""
    import torch
    from tqdm import tqdm
    from transformers import MarianMTModel, MarianTokenizer

    if lang not in MT_MODELS:
        typer.secho(f"unknown lang '{lang}'. Choices: {list(MT_MODELS)}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2)

    tsv = src / tsv_name
    if not tsv.exists():
        typer.secho(f"{tsv} not found", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    out = out or (src.parent / f"{src.name}_{lang}")
    out.mkdir(parents=True, exist_ok=True)

    model_id = MT_MODELS[lang]
    typer.echo(f"loading {model_id} ...")
    tok = MarianTokenizer.from_pretrained(model_id)
    net = MarianMTModel.from_pretrained(model_id).eval()

    rows: list[tuple[str, str, str]] = []
    for line in tsv.read_text().splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        rows.append((parts[0], parts[1], parts[2]))

    used: dict[str, int] = {}
    manifest: list[str] = []

    for orig_name, named_file, caption_en in tqdm(rows, desc=f"translating en->{lang}"):
        src_img = src / named_file if named_file else None
        if src_img is None or not src_img.exists():
            # fall back to looking up by orig_name in src
            src_img = src / orig_name
        if not src_img.exists():
            typer.secho(f"skip {orig_name}: source image not found", fg=typer.colors.YELLOW, err=True)
            continue

        batch = tok([caption_en], return_tensors="pt", padding=True)
        with torch.no_grad():
            gen = net.generate(**batch, max_new_tokens=64, num_beams=3)
        caption_target = tok.decode(gen[0], skip_special_tokens=True).strip()

        slug = _slugify(caption_target, max_words=max_words)
        n = used.get(slug, 0) + 1
        used[slug] = n
        new_name = f"{slug}_{n:03d}{src_img.suffix.lower()}"
        shutil.copy2(src_img, out / new_name)
        manifest.append(f"{orig_name}\t{new_name}\t{caption_en}\t{caption_target}")

    (out / f"_captions_{lang}.tsv").write_text("\n".join(manifest))
    typer.secho(f"done. {len(rows)} captions translated -> {out}", fg=typer.colors.GREEN)
