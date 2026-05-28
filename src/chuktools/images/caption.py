"""Caption images with a small VLM (BLIP), optionally translate, rename."""
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

MT_MODELS = {
    "de": "Helsinki-NLP/opus-mt-en-de",
    "fr": "Helsinki-NLP/opus-mt-en-fr",
    "es": "Helsinki-NLP/opus-mt-en-es",
    "it": "Helsinki-NLP/opus-mt-en-it",
    "nl": "Helsinki-NLP/opus-mt-en-nl",
    "ru": "Helsinki-NLP/opus-mt-en-ru",
}


def _slugify(text: str, max_words: int = 6) -> str:
    text = text.lower().strip().rstrip(".")
    text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    words = text.split()[:max_words]
    return "_".join(words) or "untitled"


def caption(
    src: Annotated[Path, typer.Argument(help="Directory with images to caption.", exists=True, file_okay=False, dir_okay=True)],
    out: Annotated[Path, typer.Option("--out", "-o", help="Output directory.")] = None,
    glob: Annotated[str, typer.Option(help="Glob to match images in src.")] = "*.JPG",
    model: Annotated[str, typer.Option(help=f"Caption model. One of: {', '.join(MODELS)}.")] = "blip-large",
    lang: Annotated[str, typer.Option(help=f"Output language. 'en' or one of: {', '.join(MT_MODELS)}.")] = "en",
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
    if lang != "en" and lang not in MT_MODELS:
        typer.secho(f"unknown lang '{lang}'. Choices: en, {list(MT_MODELS)}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2)

    model_id = MODELS[model]
    out = out or (src.parent / f"{src.name}_named_{lang}")
    out.mkdir(parents=True, exist_ok=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    typer.echo(f"device={device} model={model_id} lang={lang}")

    processor = BlipProcessor.from_pretrained(model_id)
    net = BlipForConditionalGeneration.from_pretrained(model_id, torch_dtype=dtype).to(device).eval()

    mt_tok = mt_net = None
    if lang != "en":
        from transformers import MarianMTModel, MarianTokenizer
        mt_id = MT_MODELS[lang]
        typer.echo(f"loading translator {mt_id}")
        mt_tok = MarianTokenizer.from_pretrained(mt_id)
        mt_net = MarianMTModel.from_pretrained(mt_id).to(device).eval()

    images = sorted(src.glob(glob))
    if not images:
        typer.secho(f"no images matching {glob} in {src}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    used: dict[str, int] = {}
    manifest: list[str] = []
    header = "orig\trenamed\tcaption_en" + ("\tcaption_" + lang if lang != "en" else "")
    manifest.append(header)

    for p in tqdm(images):
        img = Image.open(p).convert("RGB")
        inputs = processor(images=img, return_tensors="pt").to(device, dtype)
        with torch.no_grad():
            ids = net.generate(pixel_values=inputs["pixel_values"], max_new_tokens=40, num_beams=3)
        text_en = processor.decode(ids[0], skip_special_tokens=True).strip()

        text_target = text_en
        if lang != "en":
            batch = mt_tok([text_en], return_tensors="pt", padding=True).to(device)
            with torch.no_grad():
                gen = mt_net.generate(**batch, max_new_tokens=64, num_beams=3)
            text_target = mt_tok.decode(gen[0], skip_special_tokens=True).strip()

        if rename:
            slug = _slugify(text_target, max_words=max_words)
            n = used.get(slug, 0) + 1
            used[slug] = n
            new_name = f"{slug}_{n:03d}{p.suffix.lower()}"
            shutil.copy2(p, out / new_name)
            row = f"{p.name}\t{new_name}\t{text_en}"
        else:
            row = f"{p.name}\t\t{text_en}"
        if lang != "en":
            row += f"\t{text_target}"
        manifest.append(row)

    (out / f"_captions_{lang}.tsv").write_text("\n".join(manifest))
    typer.secho(f"done. {len(images)} images -> {out}", fg=typer.colors.GREEN)
