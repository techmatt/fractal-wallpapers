"""Bringing colormaps across from the source project's pooled library.

The tracked maps under `data/palettes` were curated by hand and are the ones a
render *chooses*. This module is for the other case: a corpus that already
exists names the map each of its pictures was colored through, and a picture
cannot be regenerated from a name this repository does not hold. Those maps are
not a curation decision — they are part of the join — so they arrive by
mechanical conversion and say so in their `source` line.

## The one thing the conversion has to get right

The source library samples a map on a grid and does not always include the far
end. A **cyclic** map is usually sampled *half-open*: `n` stops at positions
`i/n`, the closing stop left off because the bake wrapped. Written here
unchanged, that map would be missing its last segment — the gradient would run
to `(n−1)/n` and then hold flat, and the seam would land in the wrong place.

Every map in that library is evenly spaced, checked rather than assumed, so its
positions carry nothing its order does not. The conversion is therefore one
decision — **does a color have to be added back** — followed by re-indexing the
result evenly across `[0, 1]`:

* **cyclic, sampled half-open** (its last stop sits short of `1.0`) — the
  opening color is appended, which is the segment the wrap used to supply;
* **cyclic, sampled closed** (a stop already sits at `1.0`) — nothing is added,
  and its last color is required to be its first;
* **sequential** — it runs end to end rather than round, so nothing is missing
  and nothing is added.

The rule is not invented here. It reproduces every one of the 76 already-tracked
maps the source library also holds, stop for stop, which is what
`tests/test_library_import.py` checks — a conversion that disagreed with the
tracked files would color one half of a corpus differently from the other.

## Cyclic, and the second bit that is not stored

The source carries two cyclic-ness facts. `cycle` decides whether the bake
pre-mirrors a map to hide its seam, and it is what this repository calls `kind`.
A separate `type` decides whether the phase and cycle-count knobs may be used on
it at all. That second bit is **not** transferred: a row records the knob values
its own picture was made with, and a row of a map whose type forbade them
records the identity values. Reading the knobs off the row rather than
re-deriving eligibility here is what keeps one answer to "how was this colored".
"""

from __future__ import annotations

import json
from pathlib import Path

from fractal_wallpapers.paths import colormap_dir

#: The pooled library in the source project, relative to its root. It holds every
#: map any corpus batch names, curated and extracted alike.
POOL = Path("data") / "palettes" / "pool_colormaps.json"

#: What a converted map's `source` line says. The name it came from is enough to
#: find it again; the rest is what a reader needs to know it was not curated.
SOURCE_LINE = (
    "{name}, converted from the source project's pooled colormap library "
    "({stops} stops, {kind}). Present because a labeled corpus names it, not "
    "because it was curated."
)


class PaletteImportError(RuntimeError):
    """The conversion cannot proceed, and guessing would be worse than stopping."""


def read_pool(root: Path) -> dict[str, dict]:
    """`{name: entry}` for every map in the source project's pooled library."""
    path = Path(root) / POOL
    if not path.is_file():
        raise PaletteImportError(
            f"{path} is missing. It is the source project's pooled colormap library, "
            f"and it is what a corpus's palette names resolve against."
        )
    entries = json.loads(path.read_text(encoding="utf-8"))
    return {entry["name"]: entry for entry in entries}


def kind_of(entry: dict) -> str:
    """This repository's `kind` for one source entry.

    The source's `cycle` and its `mirror_needed` are the same fact written twice
    — a sequential map is the one that bakes pre-mirrored — and the pair is
    checked rather than trusted, because a library where they disagreed would
    color half its maps through a seam fix the other half did not get.
    """
    cycle = entry.get("cycle")
    if cycle not in ("cyclic", "sequential"):
        raise PaletteImportError(f"{entry.get('name')!r}: unknown cycle {cycle!r}")
    if bool(entry.get("mirror_needed")) != (cycle == "sequential"):
        raise PaletteImportError(
            f"{entry.get('name')!r}: cycle={cycle!r} but mirror_needed="
            f"{entry.get('mirror_needed')!r}. Those are one fact and they disagree."
        )
    return cycle


def stops_of(entry: dict) -> list[list]:
    """The source entry's stops, in this repository's shape.

    See the module docstring: the three cases are "already closes", "cyclic and
    half-open", and "sequential".
    """
    name = entry.get("name")
    stops = [
        (float(position), [int(channel) for channel in rgb]) for position, rgb in entry["stops"]
    ]
    if len(stops) < 2:
        raise PaletteImportError(f"{name!r}: a gradient needs two ends")
    if [position for position, _ in stops] != sorted(position for position, _ in stops):
        raise PaletteImportError(f"{name!r}: stops are out of order")
    if stops[0][0] != 0.0:
        raise PaletteImportError(f"{name!r}: stops start at {stops[0][0]}, not 0.0")

    step = 1.0 / (len(stops) - 1) if len(stops) > 1 else 1.0
    if any(abs(position - index * step) > 1e-9 for index, (position, _) in enumerate(stops)):
        interval = stops[-1][0] / (len(stops) - 1)
        if any(
            abs(position - index * interval) > 1e-9 for index, (position, _) in enumerate(stops)
        ):
            raise PaletteImportError(
                f"{name!r}: the stops are not evenly spaced, so re-indexing them onto "
                f"[0, 1] would move colors relative to one another."
            )

    colors = [rgb for _, rgb in stops]
    if kind_of(entry) == "cyclic" and stops[-1][0] != 1.0:
        # Sampled half-open: the closing stop was left off because the bake
        # wrapped. Put back the segment that wrap used to supply.
        colors.append(stops[0][1])
    elif kind_of(entry) == "cyclic" and stops[0][1] != stops[-1][1]:
        raise PaletteImportError(
            f"{name!r} is cyclic and has a stop at 1.0, but it is not the color the map "
            f"opened with — so it neither wraps nor runs end to end."
        )

    # Evenly spaced in, evenly spaced out: the positions carry no information the
    # order does not, and putting the last one at 1.0 is the whole edit.
    last = len(colors) - 1
    return [[index / last, rgb] for index, rgb in enumerate(colors)]


def converted(entry: dict) -> dict:
    """One source entry as the colormap file this repository tracks."""
    kind = kind_of(entry)
    stops = stops_of(entry)
    return {
        "schema": 1,
        "name": entry["name"],
        "kind": kind,
        "source": SOURCE_LINE.format(name=entry["name"], stops=len(entry["stops"]), kind=kind),
        "stops": stops,
    }


def text_of(document: dict) -> str:
    """One colormap file, formatted the way the tracked ones are.

    A stop to a line. `json.dumps` at an indent would put every number on its own
    line, which is five hundred lines of nothing for a map with five hundred
    stops and makes a diff unreadable; compact would put the whole gradient on
    one. A line per control point is the shape a person reads.
    """
    head = {key: value for key, value in document.items() if key != "stops"}
    lines = [json.dumps(head, indent=2, ensure_ascii=False)[:-2].rstrip(), ",", '  "stops": [']
    stops = [f"    {json.dumps(stop, ensure_ascii=False)}" for stop in document["stops"]]
    return "".join(lines[:2]) + "\n" + lines[2] + "\n" + ",\n".join(stops) + "\n  ]\n}\n"


def write(document: dict, directory: Path | None = None) -> Path:
    """Write one converted map beside the curated ones."""
    directory = directory or colormap_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{document['name']}.json"
    path.write_text(text_of(document), encoding="utf-8", newline="\n")
    return path


def run(root: Path, names: list[str], directory: Path | None = None) -> dict:
    """Convert every named map this repository does not already hold.

    A name already on disk is left alone rather than overwritten: the curated
    files carry hand-written `source` lines, and a mechanical conversion would
    replace one with a sentence that says less.
    """
    directory = directory or colormap_dir()
    pool = read_pool(Path(root))
    missing = sorted(name for name in set(names) if name not in pool)
    if missing:
        raise PaletteImportError(
            f"{len(missing)} named colormaps are not in the source library, e.g. "
            f"{missing[:5]}. A corpus row naming a map nobody holds cannot be rendered."
        )

    written, kept = [], []
    for name in sorted(set(names)):
        if (directory / f"{name}.json").is_file():
            kept.append(name)
            continue
        write(converted(pool[name]), directory)
        written.append(name)
    return {
        "library": str(Path(root) / POOL),
        "requested": len(set(names)),
        "already_tracked": len(kept),
        "written": len(written),
        "names": written,
    }


__all__ = [
    "POOL",
    "PaletteImportError",
    "converted",
    "kind_of",
    "read_pool",
    "run",
    "stops_of",
    "write",
]
