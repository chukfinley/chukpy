"""Caption images with a small VLM (BLIP) and rename based on caption."""
from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Annotated

import typer

MODELS = {
    "blip-base": "Salesforce/blip-image-captioning-base",
    "blip-large": "Salesforce/blip-image-captioning-large",
}


def _slugify(text: str, max_words: int = 6) -> str:
    text = text.lower().strip().rstrip(".")
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    words = text.split()[:max_words]
    return "_".join(words) or "untitled"


def caption(
    src: Annotated[Path, typer.Argument(help="Directory with images to caption.", exists=True, file_okay=False, dir_okay=True)],
    out: Annotated[Path, typer.Option("--out", "-o", help="Output directory.")] = None,
    glob: Annotated[str, typer.Option(help="Glob to match images in src.")] = "*.JPG",
    model: Annotated[str, typer.Option(help=f"Caption model. One of: {', '.join(MODELS)}.")] = "blip-large",
    rename: Annotated[bool, typer.Option("--rename/--no-rename", help="Copy files into out/ with slugified names.")] = True,
    max_words: Annotated[int, typer.Option(help="Max words used for slug.")] = 6,
) -> None:
    """Caption each image and (by default) copy it to out/ with a slugified filename."""
    import torch
    from PIL import Image
    from tqdm import tqdm
    from transformers import BlipForConditionalGeneration, BlipProcessor

    if model not in MODELS:
        typer.secho(f"unknown model '{model}'. Choices: {list(MODELS)}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2)
    model_id = MODELS[model]

    out = out or (src.parent / f"{src.name}_named")
    out.mkdir(parents=True, exist_ok=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    typer.echo(f"device={device} model={model_id}")

    processor = BlipProcessor.from_pretrained(model_id)
    net = BlipForConditionalGeneration.from_pretrained(model_id, torch_dtype=dtype).to(device).eval()

    images = sorted(src.glob(glob))
    if not images:
        typer.secho(f"no images matching {glob} in {src}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    used: dict[str, int] = {}
    manifest: list[str] = []

    for p in tqdm(images):
        img = Image.open(p).convert("RGB")
        inputs = processor(images=img, return_tensors="pt").to(device, dtype)
        with torch.no_grad():
            ids = net.generate(pixel_values=inputs["pixel_values"], max_new_tokens=40, num_beams=3)
        text = processor.decode(ids[0], skip_special_tokens=True).strip()

        if rename:
            slug = _slugify(text, max_words=max_words)
            n = used.get(slug, 0) + 1
            used[slug] = n
            new_name = f"{slug}_{n:03d}{p.suffix.lower()}"
            shutil.copy2(p, out / new_name)
            manifest.append(f"{p.name}\t{new_name}\t{text}")
        else:
            manifest.append(f"{p.name}\t\t{text}")

    (out / "_captions.tsv").write_text("\n".join(manifest))
    typer.secho(f"done. {len(images)} images -> {out}", fg=typer.colors.GREEN)
