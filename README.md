# chuktools

Personal CLI grab-bag. Random Python utilities exposed as subcommands of one
binary (`chuktools`). Extend by dropping a new subcommand group into
`src/chuktools/`.

## Install

```bash
git clone git@github.com:chukfinley/chukpy.git
cd chukpy
uv venv
uv pip install -e ".[dias]"     # extras: image tools
```

Or, ad-hoc with `uv tool`:

```bash
uv tool install --from . chuktools
```

## Usage

```bash
chuktools --help
chuktools dias --help
```

### `chuktools dias rotate`

Auto-rotate a directory of scanned slides upright using
[`check_orientation`](https://github.com/ternaus/check_orientation)
(pretrained ResNeXt50, 4-class CCW classifier).

```bash
chuktools dias rotate /path/to/scans
# writes to /path/to/scans/rotated/ + _rotation_log.txt
```

Options:
- `--out, -o`  output directory (default `<src>/rotated`)
- `--glob`     match pattern (default `*.JPG`)
- `--quality`  JPEG quality (default 95)

### `chuktools dias caption`

Caption every image with BLIP and (by default) copy files into a new directory
with slugified filenames.

```bash
chuktools dias caption /path/to/scans/rotated --model blip-large
```

Options:
- `--out, -o`     output directory (default `<src>_named` next to src)
- `--glob`        match pattern (default `*.JPG`)
- `--model`       `blip-base` or `blip-large` (default `blip-large`)
- `--no-rename`   only write `_captions.tsv`, don't copy files
- `--max-words`   words used for slug (default 6)

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
