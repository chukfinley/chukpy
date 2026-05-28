# chuktools

Personal CLI grab-bag. Random Python utilities exposed as subcommands of one
binary (`chuktools`). Extend by dropping a new subcommand group into
`src/chuktools/`.

## Install

```bash
git clone git@github.com:chukfinley/chukpy.git
cd chukpy
uv venv
uv pip install -e ".[ai]"     # includes torch/transformers for caption + rotate
# or skip [ai] for just hash/exif/thumbnail tools
```

Or, ad-hoc with `uv tool`:

```bash
uv tool install --from . chuktools
```

## Usage

```bash
chuktools --help
chuktools images --help
chuktools dias --help
```

### `chuktools images dupes`

Find pixel-identical duplicates via SHA256.

```bash
chuktools images dupes ~/photos                 # report only
chuktools images dupes ~/photos --move ~/dupes  # move all but the first occurrence
chuktools images dupes ~/photos --delete        # delete all but the first
```

### `chuktools images similar`

Find near-duplicates via perceptual hashing (default pHash). Hamming
distance ≤ threshold groups files together.

```bash
chuktools images similar ~/photos --threshold 5
chuktools images similar ~/photos --method dhash --move ~/similar
```

Methods: `phash` (default), `dhash`, `ahash`, `whash`.

### `chuktools images organize`

Reorganize by EXIF DateTime into dated filenames or folders.

```bash
chuktools images organize ~/scans              # flat: 2024-08-12_001.jpg
chuktools images organize ~/scans --by tree    # tree: 2024/08/12/001.jpg
chuktools images organize ~/scans --move       # move instead of copy
```

Files without EXIF date land in `unknown_date/`.

### `chuktools images thumbnails`

Batch-generate thumbnails (longest edge = `--size`, default 512 px).

```bash
chuktools images thumbnails ~/photos --size 256 --format webp
```

### `chuktools images caption`

Caption each image with BLIP and (by default) copy files to `out/` with
slugified filenames. Optional `--lang` runs en→target translation
(Helsinki-NLP MarianMT) so the slug ends up in the target language.

```bash
chuktools images caption ~/scans --model blip-large
chuktools images caption ~/scans --lang de        # German slugs + captions
chuktools images caption ~/scans --no-rename      # only write the TSV
```

Models: `blip-base`, `blip-large`. Languages: `en` (default), `de`, `fr`,
`es`, `it`, `nl`, `ru`.

### `chuktools images translate`

Take an existing `_captions.tsv` (from a previous English caption run) and
produce a new directory of files renamed with translated slugs. Useful when
you've already paid for BLIP and just want a different language.

```bash
chuktools images translate ~/scans/rotated_named --lang de
```

### `chuktools dias rotate`

Auto-rotate scanned slides upright using
[`check_orientation`](https://github.com/ternaus/check_orientation) (pretrained
ResNeXt50, 4-class CCW classifier).

```bash
chuktools dias rotate /path/to/scans
# writes to /path/to/scans/rotated/ + _rotation_log.txt
```

## Adding a new subcommand group

1. Create `src/chuktools/<group>/__init__.py` with a `typer.Typer()` `app`.
2. Add command functions and register them: `app.command()(func)`.
3. Wire it in `src/chuktools/cli.py`:

```python
from chuktools.<group> import app as <group>_app
app.add_typer(<group>_app, name="<group>")
```

Done.

## License

MIT.
