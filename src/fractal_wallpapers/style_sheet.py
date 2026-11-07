"""`style sheet`: finished pictures laid out as one labelled contact sheet.

A style round looks at many drafts at once (formulations by seats, or a scout's forty),
and this is that look: every picture scaled to one tile width, keeping its own aspect,
labelled `<folder>/<name>` in its top-left corner, in rows of `columns` on black. It
composites pictures the engine already made, so Python still renders nothing.

A source is a folder (its `.png` and `.jpg` pictures by name), a picture, or a `.txt`
manifest naming one picture per line (relative to the manifest's folder): a batch is
handed over as a folder or a manifest, never as hundreds of paths. Pillow is imported
inside [`contact_sheet`], so the base install still imports this module.
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from pathlib import Path

#: What a sheet is laid out at unless told otherwise: the width the item scripts this
#: command replaced settled on, and eight to a row (a forty-seat scout in five rows).
TILE_WIDTH = 640
COLUMNS = 8

#: The pictures a folder source contributes.
PICTURE_SUFFIXES = (".png", ".jpg", ".jpeg")

#: The label's colour, inset and outline, readable on a bright tile and a black one.
LABEL_FILL = (255, 255, 0)
LABEL_INSET = (6, 4)
LABEL_STROKE = (0, 0, 0)

#: JPEG quality when the sheet is written as `.jpg` (a picker's).
QUALITY = 92


class SheetError(ValueError):
    """A sheet that cannot be laid out: no pictures, an unreadable one, a bad crop."""


def pictures_of(sources: Sequence[Path]) -> list[Path]:
    """Every picture the sources name, in order: folders by name, manifests by line."""
    pictures: list[Path] = []
    for source in sources:
        source = Path(source)
        if source.is_dir():
            pictures.extend(
                sorted(
                    path
                    for path in source.iterdir()
                    if path.suffix.lower() in PICTURE_SUFFIXES and path.is_file()
                )
            )
        elif source.suffix.lower() == ".txt" and source.is_file():
            for line in source.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    pictures.append(source.parent / line.strip())
        elif source.is_file():
            pictures.append(source)
        else:
            raise SheetError(f"no picture, folder or manifest at {source}")
    if not pictures:
        raise SheetError("the sources hold no pictures")
    return pictures


def fitted(text: str, room: float, width_of) -> str:
    """`text`, its middle elided with `…` until `width_of` it fits in `room` pixels: a long
    `<folder>/<name>` was cut off at a narrow tile's edge, losing the name's end."""
    if width_of(text) <= room:
        return text
    head, tail = len(text) // 2, len(text) // 2
    while head + tail > 2:
        head, tail = max(1, head - 1), max(1, tail - 1)
        shorter = f"{text[:head]}…{text[-tail:]}"
        if width_of(shorter) <= room:
            return shorter
    return text[:1] + "…"


def label_of(picture: Path) -> str:
    """`<folder>/<name>`: which row of a manifest render a tile is, at a glance."""
    return f"{picture.parent.name}/{picture.stem}"


def contact_sheet(
    pictures: Sequence[Path],
    out: Path,
    columns: int = COLUMNS,
    width: int = TILE_WIDTH,
    crop: tuple[int, int, int, int] | None = None,
    labels: bool = True,
) -> dict[str, int]:
    """Write the sheet to `out` (PNG, or JPEG by suffix) and say how it is laid out.

    `crop` is `(x, y, w, h)` in each picture's own pixels, taken before scaling (a
    detail at full size); a box leaving a picture is refused rather than padded.
    """
    from PIL import Image, ImageDraw, ImageFont

    from fractal_wallpapers.paths import writing_path

    if columns < 1 or width < 1:
        raise SheetError("--columns and --tile-width must be at least 1")
    font = ImageFont.load_default(size=max(11, width // 40))
    tiles = []
    for picture in pictures:
        try:
            with Image.open(picture) as opened:
                tile = opened.convert("RGB")
        except OSError as unreadable:
            raise SheetError(f"cannot read {picture}: {unreadable}") from None
        if crop is not None:
            x, y, w, h = crop
            if x < 0 or y < 0 or w < 1 or h < 1 or x + w > tile.width or y + h > tile.height:
                raise SheetError(f"the crop {crop} leaves {picture} ({tile.width}x{tile.height})")
            tile = tile.crop((x, y, x + w, y + h))
        tile = tile.resize(
            (width, max(1, round(width * tile.height / tile.width))), Image.Resampling.LANCZOS
        )
        if labels:
            draw = ImageDraw.Draw(tile)
            room = tile.width - 2 * LABEL_INSET[0]
            label = fitted(label_of(picture), room, functools.partial(draw.textlength, font=font))
            draw.text(
                LABEL_INSET,
                label,
                fill=LABEL_FILL,
                font=font,
                stroke_width=1,
                stroke_fill=LABEL_STROKE,
            )
        tiles.append(tile)
    columns = min(columns, len(tiles))
    rows = -(-len(tiles) // columns)
    height = max(tile.height for tile in tiles)
    sheet = Image.new("RGB", (columns * width, rows * height), (0, 0, 0))
    for index, tile in enumerate(tiles):
        sheet.paste(tile, ((index % columns) * width, (index // columns) * height))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    scratch = writing_path(out)
    scratch.unlink(missing_ok=True)
    if out.suffix.lower() in (".jpg", ".jpeg"):
        sheet.save(scratch, "JPEG", quality=QUALITY, subsampling=0)
    else:
        sheet.save(scratch, "PNG")
    scratch.replace(out)
    return {
        "tiles": len(tiles),
        "columns": columns,
        "rows": rows,
        "width": sheet.width,
        "height": sheet.height,
    }
