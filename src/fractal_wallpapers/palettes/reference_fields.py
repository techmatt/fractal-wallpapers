"""The three pictures every palette sheet is judged on, pinned.

A sheet that asks "do these two maps look alike" has to show them *on something*,
and the something has to be the same on every sheet forever. Two sheets rendered
through two different fields are two instruments: a pair that reads as identical
on a smooth gradient can come apart on a `stripe` field that sweeps the ramp four
times across one picture, and a reader comparing yesterday's page with today's
would be reading the field's difference as the maps'.

So the reference fields are pinned here, and this module is the only place that
says what they are. Three of them, one per **class of picture the library has to
survive**:

```text
smooth            a field coloured once, edge to edge.
strange           a field the ramp is swept across several times.
parameter_plane   the shape of a family rather than one member of it.
```

## How the three were chosen, and it was a rule rather than a taste

Within each class: the released `gallery3` location whose *stretched* field has
the **highest 64-bin gradient entropy** — how much of the gradient the picture
actually spends, so a map's whole ramp is on show rather than a third of it —
with the three constrained to **three different modes**, so one coloring cannot
speak twice. The entropies they were picked on are on the rows: 5.13, 5.56 and
5.17 bits.

## The spec is tracked; the dumps are not

A `.f32` field is a megabyte of little-endian floats — regenerable, binary, and
exactly what `tests/test_history_purity.py` keeps out of the history. What is
small enough to track is the **spec**: family, viewport, `maxiter`, mode and
geometry, which is everything the engine needs to make the field again, byte for
byte. [`run`] is the regenerator and it writes under `artifacts/`.

That split is the fix for how these three nearly died. They lived only in one
session's scratchpad through three audit passes, were copied byte-for-byte from
it once, and a cleanup of that directory would have taken the calibration sheet's
instrument with it — while the twelve numbers that define them would have fitted
on a postcard.
"""

from __future__ import annotations

import json
from pathlib import Path

from fractal_wallpapers.paths import colormap_dir

#: The schema every row carries, from its first line.
SCHEMA = 1

#: What the file is called, beside the maps the sheets compare. JSONL, and not a
#: `.json`, for the reason [`fractal_wallpapers.palettes.groups`] gives: every
#: reader of the library globs `data/palettes/*.json` and takes the stem as a map.
RECORD_NAME = "reference_fields.jsonl"

#: The two kinds of row the record holds: one header, then one spec per class.
METHOD_ROW = "method"
FIELD_ROW = "field"

#: The three classes, in the order a sheet shows them.
CLASSES = ("smooth", "strange", "parameter_plane")

#: The geometry every reference field is dumped at. Small on purpose: a sheet
#: shows a hundred and fifty maps three times each, and a thumbnail is what a
#: reader compares. The supersample is the production one, so the picture is the
#: production picture scaled down rather than a different render.
RESOLUTION = (160, 90)
SUPERSAMPLE = 2

#: The curve the field is read through: the mode's own, unmodified, which is
#: the engine's default and so is recorded rather than passed. A dump spec that
#: named it would be refused — `dump-field` takes no transform.
CURVE = "linear"

#: The map the dump is nominally coloured through. A dumped field carries no
#: colour — every sheet recolours it — but the engine's `dump-field` takes the
#: same spec a render does and a spec names a map. Named here rather than left to
#: a caller so two dumps of one field cannot differ by it.
DUMP_COLORMAP = "twilight_shifted"

RULE = (
    "one released gallery3 location per class of picture — a field coloured once, a field "
    "the ramp is swept across several times, and a parameter plane — each the location whose "
    "stretched field carries the highest 64-bin gradient entropy in its class, with the three "
    "constrained to three different modes so one coloring cannot speak twice. Dumped at "
    f"{RESOLUTION[0]}x{RESOLUTION[1]} ss{SUPERSAMPLE} through the {CURVE} curve. The spec is "
    "tracked and the dump is not: `fractal-wallpapers palettes reference-fields` makes the "
    "field again from these numbers."
)


class ReferenceFieldError(RuntimeError):
    """A reference field cannot be read or made."""


def record_path(directory: Path | None = None) -> Path:
    """Where the specs live: beside the maps the sheets they serve compare."""
    return (Path(directory) if directory is not None else colormap_dir()) / RECORD_NAME


def read(directory: Path | None = None) -> list[dict]:
    """The three specs, in file order."""
    path = record_path(directory)
    if not path.is_file():
        raise ReferenceFieldError(
            f"{path} is missing — it is what every palette sheet is rendered on"
        )
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line and json.loads(line).get("kind") == FIELD_ROW
    ]
    found = [row["class"] for row in rows]
    if found != list(CLASSES):
        raise ReferenceFieldError(f"{path} names {found}; the three classes are {list(CLASSES)}")
    return rows


def text_of(rows: list[dict]) -> str:
    """The file's text: one spec to a line."""
    return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)


def write(rows: list[dict], directory: Path | None = None) -> Path:
    path = record_path(directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text_of(rows), encoding="utf-8", newline="\n")
    return path


def dump_dir() -> Path:
    """Where the fields themselves land — regenerable, so under `artifacts/`."""
    from fractal_wallpapers.paths import under

    return under("palettes", "reference_fields")


def field_path(row: dict, directory: Path | None = None) -> Path:
    """Where one class's field is, whether or not it has been made."""
    where = Path(directory) if directory is not None else dump_dir()
    return where / f"{row['class']}.f32"


def spec(row: dict, output: Path) -> dict:
    """The engine spec that makes one reference field."""
    return {
        "schema": 1,
        "family": row["family"],
        "viewport": row["viewport"],
        "resolution": list(RESOLUTION),
        "supersample": SUPERSAMPLE,
        "maxiter": int(row["maxiter"]),
        "mode": row["mode"],
        "colormap": DUMP_COLORMAP,
        "colormap_dir": str(colormap_dir()),
        "output": str(output),
    }


def dump(row: dict, directory: Path | None = None, force: bool = False) -> Path:
    """One reference field, made if it is not already there.

    Rust makes every pixel; this reaches the engine through
    [`fractal_wallpapers.engine`] like everything else does.
    """
    from fractal_wallpapers import engine

    output = field_path(row, directory)
    output.parent.mkdir(parents=True, exist_ok=True)
    if not force and output.is_file() and output.with_suffix(".json").is_file():
        return output
    engine.dump_field(spec(row, output))
    return output


def fields(directory: Path | None = None, force: bool = False) -> dict[str, Path]:
    """`{class: field}` for all three, made where they are missing."""
    return {row["class"]: dump(row, directory, force) for row in read()}


def run(directory: Path | None = None, force: bool = False) -> dict:
    """Regenerate the three dumps. Returns what it made, in one line."""
    made = fields(directory, force)
    return {
        "directory": str(next(iter(made.values())).parent) if made else None,
        "fields": {
            name: {"path": path.name, "bytes": path.stat().st_size} for name, path in made.items()
        },
        "rule": RULE,
    }


__all__ = [
    "CLASSES",
    "CURVE",
    "FIELD_ROW",
    "METHOD_ROW",
    "DUMP_COLORMAP",
    "RECORD_NAME",
    "RESOLUTION",
    "RULE",
    "SCHEMA",
    "SUPERSAMPLE",
    "ReferenceFieldError",
    "dump",
    "dump_dir",
    "field_path",
    "fields",
    "read",
    "record_path",
    "run",
    "spec",
    "text_of",
    "write",
]
