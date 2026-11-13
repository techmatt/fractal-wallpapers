"""`style sweep`: draw every style small, at the places it was kept, and check each picture.

The checker a bug hunt runs over the style library, and anyone after an engine or stack
change. For each style it draws, at a small size:

- its **seats**: the locations of its first keeps (`<name>.keeps.json`), each at the
  colormap the keep was drawn in, or seeded gallery seats for a style with no keeps;
- each **public knob** at both ends of its range, at the first seat;
- each **palette entry** of its mode's set (`catalog.json`), at the first seat.

Every picture is checked where it lands ([`look`], [`FLAGS`]): an engine refusal, a flat
frame, one washed white or drowned black, a knob whose two ends draw the same picture, a
palette entry drawn identical to the default, a render far slower per sample than the
others drawn at its seat, and, with `--tones`, a seat or palette entry outside its reference's tone
band. The pictures are the captures (one folder per style, a contact sheet
each under `sheets/`), and `sweep.jsonl` holds one row per picture with its numbers and
flags. Nothing is written outside `--out`.

It reads the stacks as `style render` does (`styles.spec_of`), so a picture here is the
one `style render` would draw at that size.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

#: The sweep's picture size: small enough that ~300 pictures take minutes, wide enough
#: that a contact sheet tile reads.
RESOLUTION = (320, 200)
SUPERSAMPLE = 1

#: Keeps drawn per style, and gallery seats for a style with none.
SEATS = 2

#: What each flag means, and the threshold it fires at.
#: A frame whose lightness barely varies drew nothing (the stack, its map or the seat).
FLAT_SPREAD = 0.02
#: Shares of the frame at the ends of lightness that read as a wash or a void.
WASHED_SHARE = 0.60
DROWNED_SHARE = 0.95
#: Mean absolute difference (0..1 per channel) at or under which two pictures are one:
#: none at all. A faint knob (a sparkle's opacity) moves a 320-wide picture by well under
#: a level, so anything above nothing is a knob doing something.
SAME_PICTURE = 0.0
#: Seconds per million samples above this many times the median at the same seat: a knob end
#: or palette entry far slower than the rest drawn there (a heavy stack is slow everywhere).
SLOW_FACTOR = 8.0

FLAGS = {
    "failed": "the engine refused or stopped",
    "flat": f"lightness spread under {FLAT_SPREAD}: the frame drew nothing",
    "washed": f"over {WASHED_SHARE:.0%} of the frame near white",
    "drowned": f"over {DROWNED_SHARE:.0%} of the frame near black",
    "dead_knob": "the knob's two ends draw the same picture",
    "same_palette": "a palette entry draws the same picture as the default",
    "slow": f"over {SLOW_FACTOR:g}x the median seconds per sample at its seat",
    "tone_miss": "with --tones at a checked width, outside its reference's band (TONE_BAND)",
}


def look(path: Path) -> dict[str, float]:
    """A picture's numbers: lightness spread and its shares near white and near black."""
    import numpy as np
    from PIL import Image

    from fractal_wallpapers import styles

    with Image.open(path) as image:
        rgb = np.asarray(image.convert("RGB"), dtype=np.float64) / 255.0
    lightness = np.cbrt(styles.luminance_of(rgb))  # monotone in L*; enough for shares
    return {
        "spread": float(np.percentile(lightness, 95) - np.percentile(lightness, 5)),
        "white": float((rgb.min(axis=-1) > 0.97).mean()),
        "black": float((rgb.max(axis=-1) < 0.03).mean()),
    }


def flags_of(numbers: dict[str, float]) -> list[str]:
    """The picture flags [`look`]'s numbers raise."""
    flags = []
    if numbers["spread"] < FLAT_SPREAD:
        flags.append("flat")
    if numbers["white"] > WASHED_SHARE:
        flags.append("washed")
    if numbers["black"] > DROWNED_SHARE:
        flags.append("drowned")
    return flags


def difference(a: Path, b: Path) -> float:
    """Mean absolute difference of two pictures, 0..1 per channel (1 when sizes differ)."""
    import numpy as np
    from PIL import Image

    with Image.open(a) as first, Image.open(b) as second:
        if first.size != second.size:
            return 1.0
        x = np.asarray(first.convert("RGB"), dtype=np.float64)
        y = np.asarray(second.convert("RGB"), dtype=np.float64)
    return float(np.abs(x - y).mean() / 255.0)


def seats_of(name: str, gallery: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    """`[{location, colormap}]`: a style's first kept places, or gallery seats."""
    from fractal_wallpapers import style_keeps

    seats = []
    for keep in style_keeps.read_record(name)["keeps"]:
        render = keep.get("render") or {}
        if render.get("location"):
            seats.append({"location": render["location"], "colormap": render.get("colormap")})
        if len(seats) == count:
            return seats
    return seats or [{"location": row, "colormap": None} for row in gallery[:count]]


def plan(
    names: list[str], seats: int, gallery: list[dict[str, Any]], from_gallery: bool = False
) -> list[dict[str, Any]]:
    """Every picture the sweep draws: `{style, variant, location, colormap, knobs}`.

    `from_gallery` draws every style at the gallery seats instead of its keeps: places
    nobody picked it for, which is where a stack meets what it was never tuned on.
    """
    from fractal_wallpapers import styles

    rows = styles.catalog_rows()
    todo = []
    for name in names:
        document = styles.load(name)
        if from_gallery:
            places = [{"location": row, "colormap": None} for row in gallery]
        else:
            places = seats_of(name, gallery, seats)
        if not places:
            continue  # no keeps and no gallery on this box: nothing to draw it at
        for index, place in enumerate(places):
            todo.append(
                {"style": name, "variant": f"seat{index}", **place, "knobs": {}, "against": None}
            )
        first = places[0]
        for knob in (document.get("public") or {}).get("knobs") or []:
            low, high = knob["range"]
            for end, value in (("low", low), ("high", high)):
                todo.append(
                    {
                        "style": name,
                        "variant": f"knob_{knob['name']}_{end}",
                        **first,
                        "knobs": {knob["name"]: value},
                        "against": f"knob_{knob['name']}_low" if end == "high" else None,
                    }
                )
        row = next((r for r in rows if r.get("style") == name), None)
        entries = (row or {}).get("palettes") or []
        for index, entry in enumerate(entries):
            todo.append(
                {
                    "style": name,
                    "variant": f"palette{index}_{entry['colormap']}",
                    "location": first["location"],
                    "colormap": entry["colormap"],
                    "knobs": {},
                    "against": None if not index else f"palette0_{entries[0]['colormap']}",
                }
            )
    return todo


#: References already measured, by path: a sweep reads each once.
_HELD: dict[Path, dict[str, float]] = {}


def tone_flags(picture: Path, document: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """The picture's tones against its style's reference (a merged entry's own), and
    `tone_miss` when it misses the band at a checked width; nothing without a reference."""
    from fractal_wallpapers import styles

    reference = styles.reference_path(document)
    if not reference.is_file():
        return {}, []
    if reference not in _HELD:
        _HELD[reference] = styles.tones(reference)
    stats = styles.tones(picture)
    misses = styles.tone_misses(stats, _HELD[reference])
    checked = stats["width"] >= styles.CHECKED_WIDTH
    numbers = {"tone_misses": misses, "tone_checked": checked}
    return numbers, ["tone_miss"] if misses and checked else []


def draw(
    item: dict[str, Any], folder: Path, resolution, supersample: int, tones: bool = False
) -> dict[str, Any]:
    """Draw one planned picture as `style render` would; its row, without flags yet.

    `tones` holds a seat or palette entry (not a knob end, which may move the balance by
    design) to its reference ([`tone_flags`]).
    """
    from fractal_wallpapers import engine, locations, styles

    document = styles.at_palette(styles.load(item["style"]), item["colormap"])
    document = styles.with_knobs(document, item["knobs"])
    output = folder / item["style"] / f"{item['variant']}.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)  # a refusal must not leave last run's picture on a sheet
    row = {"style": item["style"], "variant": item["variant"], "picture": str(output)}
    try:
        record = locations.one_location(item["location"], item["style"], drawing=True)
        record["render"] = {
            **record["render"],
            "resolution": list(resolution),
            "supersample": supersample,
        }
        spec = styles.spec_of(
            record, document, output, colormap=item["colormap"], knobs=item["knobs"]
        )
        started = time.perf_counter()
        report = engine.render_report(spec)
    except (RuntimeError, styles.StyleError) as refusal:
        return {**row, "flags": ["failed"], "why": str(refusal)[-400:]}
    seconds = time.perf_counter() - started
    samples = resolution[0] * resolution[1] * supersample**2
    numbers = look(output)
    toned, missed = tone_flags(output, document) if tones and not item["knobs"] else ({}, [])
    return {
        **row,
        "colormap": spec["colormap"],
        "location": item["location"].get("name") or locations.name_of(record),
        "seconds": round(seconds, 3),
        "per_msample": round(seconds / (samples / 1e6), 3),
        "interior": report.get("interior_fraction"),
        **{key: round(value, 4) for key, value in numbers.items()},
        **toned,
        "flags": flags_of(numbers) + missed,
    }


def compare(rows: list[dict[str, Any]], todo: list[dict[str, Any]]) -> None:
    """Raise the flags that read two pictures (knob ends, palette entries) and `slow`."""
    import statistics

    by = {(row["style"], row["variant"]): row for row in rows}
    for item, row in zip(todo, rows, strict=True):
        other = by.get((item["style"], item["against"])) if item["against"] else None
        if other is None or "failed" in row["flags"] or "failed" in other["flags"]:
            continue
        gap = difference(Path(row["picture"]), Path(other["picture"]))
        row["against"] = {"variant": other["variant"], "difference": round(gap, 5)}
        if gap <= SAME_PICTURE:
            row["flags"].append("dead_knob" if item["knobs"] else "same_palette")
    # Judged against pictures at the same seat: a location's cap and interior share set
    # its cost per sample (a deep-capped Phoenix seat runs ~20x a shallow one under one
    # stack), so a second seat drawn alone is not judged; every knob end and palette
    # entry is drawn at the first seat, so those still are.
    for name in {row["style"] for row in rows}:
        own = [row for row in rows if row["style"] == name and "per_msample" in row]
        for seat in {row.get("location") for row in own}:
            mates = [row for row in own if row.get("location") == seat]
            if len(mates) < 3:
                continue
            median = statistics.median(row["per_msample"] for row in mates)
            for row in mates:
                if row["per_msample"] > SLOW_FACTOR * median:
                    row["flags"].append("slow")


def gallery_seats(count: int, seed: int) -> list[dict[str, Any]]:
    """Seeded seats from the default published gallery, for styles with no keeps."""
    from fractal_wallpapers import style_scout

    seats, _ = style_scout.candidates([style_scout.default_record()])
    drawn, _ = style_scout.draw(seats, count, seed)
    return drawn


def sweep(
    out: Path,
    names: list[str],
    seats: int = SEATS,
    seed: int = 0,
    resolution=RESOLUTION,
    supersample: int = SUPERSAMPLE,
    log=print,
    from_gallery: bool = False,
    tones: bool = False,
) -> list[dict[str, Any]]:
    """Draw and check every planned picture into `out`; the rows, also in `sweep.jsonl`.

    `from_gallery` draws each style at `seats` seeded gallery seats instead of its keeps.
    """
    from fractal_wallpapers import style_sheet

    out.mkdir(parents=True, exist_ok=True)
    try:
        gallery = gallery_seats(seats, seed)
    except Exception as unread:  # noqa: BLE001 - a box without the published records
        if log is not None:
            log(f"no gallery seats ({unread}); styles without keeps are skipped")
        gallery = []
    todo = [item for item in plan(names, seats, gallery, from_gallery) if item["location"]]
    rows = []
    for index, item in enumerate(todo, start=1):
        row = draw(item, out, resolution, supersample, tones)
        rows.append(row)
        if log is not None:
            mark = ",".join(row["flags"]) or "ok"
            log(f"[{index}/{len(todo)}] {item['style']}/{item['variant']}: {mark}")
    compare(rows, todo)
    with (out / "sweep.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    for name in dict.fromkeys(row["style"] for row in rows):
        pictures = [
            Path(row["picture"])
            for row in rows
            if row["style"] == name and Path(row["picture"]).is_file()
        ]
        if pictures:
            style_sheet.contact_sheet(
                pictures, out / "sheets" / f"{name}.jpg", columns=4, width=RESOLUTION[0]
            )
    return rows
