"""A location record, and the manifest that holds many of them.

Every record this project writes down says where a place is the same way: a
`family` with all its constants, a `viewport` of three decimal strings, and a
`render` block saying at what size and through which coloring it was drawn. A
walk ledger's candidate rows, the label store's rows and a release's decision
rows are all that shape, which means *most of what anybody wants to do with this
repository is a loop over records that already exist* — draw these twelve, screen
these hundred, score this list.

Nothing could take one. Every command that renders spelled the location out as
flags, so the only way to redraw a row somebody already had was to retype its
constants, and the one caller outside this repository that needed to do it
bypassed [`fractal_wallpapers.engine`] and shelled the binary instead. This
module is the reader that closes that: one place that knows what a location
record is, what it means when a field is missing, and how it becomes an engine
spec.

## What a record has to say, and what it may leave out

`family` and `viewport` are the identity and are required. Everything else is
presentation, and a record that omits it gets the same default the command line
gives a flag nobody passed — so a two-key record is a legal record and draws the
family's own home framing at the standard size.

The one field with a *third* answer is `maxiter`. Absent means "let the
depth-aware policy decide", which is what an engine spec means by leaving it out
and is not the same as any particular number. So it stays absent rather than
being filled in here.

## Three spellings of the same thing, because three records already exist

```text
{"family": ..., "viewport": ..., "render": {...}}    a label row
{"family": ..., "viewport": ..., "maxiter": 13140}   a walk ledger's candidate
{"location": {"family": ..., "viewport": ...}, ...}  a release decision row
```

All three are read. A ledger row keeps its cap at the top level because it has no
render block to put one in — it records a *frame the gates measured*, not a
picture — and a release row nests the location under a key because the rest of
that row is about a wallpaper. Which spelling a file uses is the writer's
business; a reader that only took one of them would send half this repository's
own records back to being retyped.

## Coordinates stay strings

The whole way through, for the reason
[`fractal_wallpapers.discovery.ledger`] gives: the decimal string is the identity
of a location and `f64` is a lossy view of it. A number in a manifest is accepted
and written back out through `repr`, because JSON has no other way to spell one —
but a record written by this project carries strings and gets them back
unaltered.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from fractal_wallpapers.paths import colormap_dir

#: The schema a manifest of location records carries. A file whose rows say
#: nothing is read anyway — the label store and the ledgers stamp their own
#: schema, which is about *those* records rather than about this shape — but a
#: row that names a schema this reader does not know is refused rather than
#: guessed at.
SCHEMA = 1

#: What a location is drawn at when its record does not say. The same numbers the
#: `render` subcommand's flags default to, because a record with no render block
#: and a command line with no render flags are asking the identical question.
DEFAULT_RESOLUTION = (1920, 1080)
DEFAULT_SUPERSAMPLE = 2
DEFAULT_MODE = "smooth"
DEFAULT_COLORMAP = "twilight_shifted"

#: The keys a `render` block may carry. Anything else is a typo or a field from
#: some other record shape, and both are worth refusing: a misspelled
#: `supersamples` that silently drew at the default is a picture nobody can tell
#: from the one they asked for.
RENDER_KEYS = ("resolution", "supersample", "mode", "colormap", "maxiter")

__all__ = [
    "DEFAULT_COLORMAP",
    "DEFAULT_MODE",
    "DEFAULT_RESOLUTION",
    "DEFAULT_SUPERSAMPLE",
    "RENDER_KEYS",
    "SCHEMA",
    "LocationError",
    "frame_of",
    "maxiter_of",
    "name_of",
    "read",
    "read_one",
    "record",
    "spec_of",
    "write",
]


class LocationError(RuntimeError):
    """A row that does not describe a location, or describes one impossibly."""


def record(row: dict, where: str = "record") -> dict:
    """One row as the location record the rest of this module takes.

    Reads all three spellings, checks the two required halves, and fills the
    presentation defaults — so everything downstream sees one shape and no
    caller has to know which kind of file its row came out of.
    """
    if not isinstance(row, dict):
        raise LocationError(f"{where}: a location is a JSON object, not {type(row).__name__}")
    schema = row.get("schema")
    if schema is not None and not isinstance(schema, int):
        raise LocationError(f"{where}: schema {schema!r} is not an integer")

    # A release decision row keeps the location under its own key, because the
    # rest of that row is about a wallpaper rather than about a place.
    nested = row.get("location")
    inner = nested if isinstance(nested, dict) and "family" in nested else row

    family = inner.get("family")
    viewport = inner.get("viewport")
    if not isinstance(family, dict) or not family.get("kind"):
        raise LocationError(f"{where}: no family — a location's identity is half its constants")
    if not isinstance(viewport, dict):
        raise LocationError(f"{where}: no viewport")
    for key in ("center_re", "center_im", "width"):
        if viewport.get(key) is None:
            raise LocationError(f"{where}: viewport names no {key}")

    block = inner.get("render") or row.get("render") or {}
    if not isinstance(block, dict):
        raise LocationError(f"{where}: render is not an object")
    unknown = sorted(set(block) - set(RENDER_KEYS))
    if unknown:
        raise LocationError(
            f"{where}: render carries {', '.join(unknown)}, which nothing here draws. "
            f"A render block says {', '.join(RENDER_KEYS)}"
        )

    resolution = block.get("resolution") or list(DEFAULT_RESOLUTION)
    if len(list(resolution)) != 2:
        raise LocationError(f"{where}: resolution is [width, height], not {resolution!r}")

    # The cap is the one field with a third answer: absent means "the
    # depth-aware policy decides", which is not any particular number.
    maxiter = block.get("maxiter")
    if maxiter is None:
        maxiter = inner.get("maxiter")

    out: dict[str, Any] = {
        "family": family,
        "viewport": {key: str(viewport[key]) for key in ("center_re", "center_im", "width")},
        "render": {
            "resolution": [int(resolution[0]), int(resolution[1])],
            "supersample": int(block.get("supersample") or DEFAULT_SUPERSAMPLE),
            "mode": block.get("mode") or DEFAULT_MODE,
            "colormap": block.get("colormap") or DEFAULT_COLORMAP,
        },
    }
    if maxiter is not None:
        out["render"]["maxiter"] = int(maxiter)
    return out


def read(path: Path) -> list[dict]:
    """Every location in a JSONL manifest, in the order it was written.

    Blank lines are skipped and every other line has to be a location, so a file
    that is half something else fails on the row that is, naming it.
    """
    path = Path(path)
    rows = []
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as bad:
                raise LocationError(f"{path}:{number}: not JSON: {bad}") from bad
            rows.append(record(row, f"{path}:{number}"))
    if not rows:
        raise LocationError(f"{path} holds no location")
    return rows


def read_one(path: Path) -> dict:
    """One location, from a JSON object or from a manifest holding exactly one.

    Both, because "a location" arrives written both ways and neither spelling is
    wrong — a record copied out of a ledger row is an object, and a one-row
    manifest is what a batch of one looks like.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise LocationError(f"{path} is empty")
    if text.lstrip().startswith("["):
        rows = json.loads(text)
        if len(rows) != 1:
            raise LocationError(f"{path} holds {len(rows)} locations; --manifest takes many")
        return record(rows[0], str(path))
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) > 1:
        raise LocationError(
            f"{path} holds {len(lines)} rows, and this takes one location. A file of many "
            f"is a manifest — pass it as one."
        )
    return record(json.loads(lines[0]), str(path))


def write(rows, path: Path) -> Path:
    """Write a manifest of location records, one per line."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps({"schema": SCHEMA, **row}, ensure_ascii=False) + "\n")
    return path


def maxiter_of(row: dict) -> int:
    """This location's iteration cap, asking the engine's policy where the record
    does not say. A number rather than `None`, for the callers that have to record
    what a picture was actually drawn at."""
    from fractal_wallpapers import engine

    cap = row["render"].get("maxiter")
    if cap is not None:
        return int(cap)
    return engine.maxiter_for([row["viewport"]["width"]])[0]


def spec_of(row: dict, output: Path) -> dict:
    """The JSON object the engine's `render` reads, for one location record."""
    render = row["render"]
    spec: dict[str, Any] = {
        "schema": 1,
        "family": row["family"],
        "viewport": row["viewport"],
        "resolution": list(render["resolution"]),
        "supersample": int(render["supersample"]),
        "mode": render["mode"],
        "colormap": render["colormap"],
        "colormap_dir": str(colormap_dir()),
        "output": str(output),
    }
    if render.get("maxiter") is not None:
        spec["maxiter"] = int(render["maxiter"])
    return spec


def frame_of(row: dict) -> dict:
    """The JSON object the engine's `screen` reads, for one location record.

    The render block is not in it, and that is the point: the gates read a frame
    at *their* geometry — the one an expansion draws every candidate at — so what
    a record says about resolution and coloring is not a fact about the frame
    being screened. The cap is the exception, because it decides what counts as
    interior and therefore what the first gate measures.
    """
    frame = {"family": row["family"], **row["viewport"]}
    if row["render"].get("maxiter") is not None:
        frame["maxiter"] = int(row["render"]["maxiter"])
    return frame


#: Characters of the digest a location's picture is named by. Long enough that a
#: batch of thousands will not collide, short enough to read off a directory.
NAME_LENGTH = 16


def name_of(row: dict) -> str:
    """A stable file name for one location's picture: a digest of what makes it.

    Everything the engine is told goes in and nothing else does, the same rule
    the finished-render cache names by — so two records that would produce the
    same picture name one file, and a record that differs anywhere gets its own.
    """
    material = json.dumps(spec_of(row, Path("x")), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:NAME_LENGTH]
