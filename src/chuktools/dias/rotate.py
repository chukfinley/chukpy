"""Auto-rotate scanned slides with a pretrained orientation classifier."""
from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

ROTATE_PIL = {0: 0, 1: -90, 2: 180, 3: 90}


def rotate(
    src: Annotated[Path, typer.Argument(help="Directory with images to rotate.", exists=True, file_okay=False, dir_okay=True)],
    out: Annotated[Path, typer.Option("--out", "-o", help="Output directory.")] = None,
    glob: Annotated[str, typer.Option(help="Glob to match images in src.")] = "*.JPG",
    quality: Annotated[int, typer.Option(help="JPEG quality.")] = 95,
) -> None:
    """Rotate scanned slides upright using check_orientation (ResNeXt50, 4-class CCW)."""
    import torch
    from check_orientation.pre_trained_models import create_model
    from PIL import Image
    from torchvision.transforms import functional as TF
    from tqdm import tqdm

    out = out or (src / "rotated")
    out.mkdir(parents=True, exist_ok=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    typer.echo(f"device={device}")
    model = create_model("swsl_resnext50_32x4d").eval().to(device)

    images = sorted(src.glob(glob))
    if not images:
        typer.secho(f"no images matching {glob} in {src}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    log: list[str] = []
    for p in tqdm(images):
        img = Image.open(p).convert("RGB")
        small = img.resize((224, 224), Image.BILINEAR)
        t = TF.to_tensor(small)
        t = TF.normalize(t, mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        with torch.no_grad():
            probs = torch.softmax(model(t.unsqueeze(0).to(device))[0], dim=0).cpu().tolist()
        cls = int(max(range(4), key=lambda i: probs[i]))
        deg = ROTATE_PIL[cls]
        result = img if deg == 0 else img.rotate(deg, expand=True)
        result.save(out / p.name, "JPEG", quality=quality, subsampling=0)
        log.append(f"{p.name}\tcls={cls}\tdeg={deg}\tprobs={[round(x, 3) for x in probs]}")

    (out / "_rotation_log.txt").write_text("\n".join(log))
    typer.secho(f"done. {len(images)} images -> {out}", fg=typer.colors.GREEN)
