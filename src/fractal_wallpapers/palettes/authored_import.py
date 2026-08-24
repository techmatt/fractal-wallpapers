"""Turning a drop of authored palettes into maps the engine can bake.

An authored palette is six to fifteen OKLCH control points with a brief attached
— a mood, a colour architecture, a lightness skeleton, a value key, a complexity
— written by a person against the generator brief in `data/palette_authoring`. The engine
does not read control points. It reads a dense, evenly spaced `[position, [r, g,
b]]` table in sRGB8 and bakes it into an OKLab lookup. This module is that one
bridge, and it is the only place in this repository that turns authored stops
into a gradient.

## A drop, and why the directory name is the stamp

The generator emits one file per run — `<mood family>_c<band>_v<major>_<minor>.json`
— and a set of runs commissioned together arrives as one **drop**. The drop is
what a later reader needs: "which maps were added to chase the thin swatches"
is not a question a per-run batch name can answer, because the runs have
different mood families and nothing else joins them.

So a drop is a directory under `data/palettes/batches`, its name is its stamp,
and every provenance row a drop produces carries it as `drop`. A map with no
`drop` is a map from before drops existed — the separation is the absence, which
means no row anywhere had to be rewritten to introduce the idea.

## `kind` is read off the gradient, never off the group it arrived in

A map is **cyclic** when it closes on the colour it opened with and
**sequential** when it does not, and the difference is not bookkeeping: the whole
repository colours by `mirror = the map is not cyclic`, a sequential map being
folded out-and-back to hide the seam its two ends would otherwise show. Call a
sequential map cyclic and every render of it shows that seam; call a cyclic map
sequential and every render shows half the gradient. Neither announces itself.

The archive's densifier stamped `cyclic` on every authored palette because the
briefs it was fed all closed. That is a fact about those batches, not a property
of authoring, so here it is measured: the authored stops must close in OKLCH
within [`CLOSES`], and the dense result is required to close exactly in sRGB8 —
which is the same equality `tests/test_colormaps.py` holds every cyclic map to.

## The densification is the archive's, re-expressed against this repository's colour

Interpolation is linear in **OKLab**, which is what the engine's own bake does
between stops, so the dense table and the engine agree about the middle of a
segment. The arithmetic is [`space.srgb`] — this repository keeps one copy of
Ottosson's matrices and this is not a second one.

Three segment semantics, each describing the span from a stop to the next:

* `smooth` — linear in OKLab. The default, and what a stop with no `segment` gets.
* `ease` — the same interpolation with a smoothstep on its parameter.
* `cliff` (`hard`) — a step. Realised as a smoothstep ramp of width
  [`SOFT_CLIFF`] ending exactly on the next stop, so the edge is crisp without
  being a wall; a stop may carry its own `width`, and a width of zero restores
  the raw one-sample snap.

`tests/test_authored_import.py` holds this to the 175 authored maps already
tracked: densifying each one from the OKLCH stops its provenance row carries
reproduces its tracked file **stop for stop**. That is what makes this a port of
the archive's densifier rather than a second gradient standing next to it.

## A name collision is refused, not resolved

The name is the join key the batch entry, the dense file and the provenance row
all meet on. Two maps under one name silently collapse records, so a drop whose
run emitted a name another map in the drop or in the shipped library already
holds does not ingest: the drop's `renames.json` has to say what it ships as and
why. Renaming is a decision somebody makes and writes down; it is not something
this module is clever enough to do quietly.
"""

from __future__ import annotations

import json
from pathlib import Path

from fractal_wallpapers.palettes import library_import
from fractal_wallpapers.paths import colormap_dir, repo_root

#: The record every colormap file carries, and the record a drop's renames carry.
SCHEMA = 1

#: How many evenly spaced stops a densified map ships with. The engine
#: interpolates between them in OKLab, so this is fine enough that no segment of
#: an authored palette is described by fewer than a handful of them.
DENSE = 512

#: The default width of the ramp a `cliff` segment is realised as, in position
#: units. Crisp but not a wall; a stop's own `width` overrides it.
SOFT_CLIFF = 0.08

#: How near the first and last control point must be, per OKLCH component, for a
#: palette to be called closed. Tolerance rather than equality: a loop that
#: closes to within a thousandth of a lightness bakes seam-free, and one that
#: does not is a different map.
CLOSES = 1e-3

#: Where the drops live, relative to the repository root. Beside the library they
#: densify into, and *not* inside it: every reader of the library globs
#: `data/palettes/*.json` and takes the stem as a map name.
BATCHES = Path("data") / "palettes" / "batches"

#: What a drop's rename record is called, inside the drop.
RENAMES = "renames.json"

#: What a densified map's `source` line says. Enough to find the control points
#: it came from, and to say that the gradient is not where it started.
SOURCE_LINE = (
    "{name}, densified to {dense} stops in OKLab from the {control} OKLCH control "
    "points authored in {batch}, drop {drop}."
)


class AuthoredImportError(RuntimeError):
    """A drop cannot be ingested, and a half-ingested drop would be worse."""


# --------------------------------------------------------------------------- #
# The densifier.
# --------------------------------------------------------------------------- #
def _oklab(stop: dict):
    """One authored control point as OKLab.

    `oklch` is `[L, C, H°]` and the unpack to Cartesian is `a = C·cos H`,
    `b = C·sin H` — a cylindrical-to-rectangular change of coordinates inside one
    space, not a conversion between two.
    """
    import numpy

    lightness, chroma, hue = (float(value) for value in stop["oklch"])
    radians = numpy.deg2rad(hue)
    return numpy.array(
        [lightness, chroma * numpy.cos(radians), chroma * numpy.sin(radians)], dtype=numpy.float64
    )


def _smoothstep(parameter):
    """Hermite's `3u² − 2u³`: zero slope at both ends, monotone between."""
    return parameter * parameter * (3.0 - 2.0 * parameter)


def _segment_of(stop: dict) -> str:
    """The span from this stop to the next. `cliff` is the brief's word for a step."""
    segment = stop.get("segment") or "smooth"
    if segment == "cliff":
        return "hard"
    if segment not in ("smooth", "ease", "hard"):
        raise AuthoredImportError(f"unknown segment {segment!r}; expected smooth, ease or cliff")
    return segment


def densify(stops: list[dict], dense: int = DENSE, soft_cliff: float = SOFT_CLIFF) -> list[list]:
    """Authored control points to `dense` evenly spaced `[position, [r, g, b]]` stops.

    The written positions are `index / (dense − 1)` — the same even re-indexing
    [`library_import`] puts on a converted map, so a map's position column does
    not say which door it came in through.
    """
    import numpy

    if len(stops) < 2:
        raise AuthoredImportError("a gradient needs two ends")
    positions = numpy.array([float(stop["pos"]) for stop in stops], dtype=numpy.float64)
    if positions[0] != 0.0 or positions[-1] != 1.0:
        raise AuthoredImportError(
            f"stops span [{positions[0]}, {positions[-1]}] rather than [0, 1], so densifying "
            f"them would stretch the palette rather than sample it"
        )
    if any(later < earlier for earlier, later in zip(positions, positions[1:], strict=False)):
        raise AuthoredImportError("stops are out of order")

    segments = [_segment_of(stop) for stop in stops]
    widths = [stop.get("width") for stop in stops]
    corners = numpy.array([_oklab(stop) for stop in stops], dtype=numpy.float64)

    where = numpy.linspace(0.0, 1.0, dense)
    index = numpy.clip(
        numpy.searchsorted(positions, where, side="right") - 1, 0, len(positions) - 2
    )

    walked = numpy.empty((dense, 3), dtype=numpy.float64)
    for step in range(dense):
        left = int(index[step])
        span = positions[left + 1] - positions[left]
        parameter = 0.0 if span <= 0 else (where[step] - positions[left]) / span
        segment = segments[left]
        if segment == "hard":
            # Held across the span; the step itself is the post-pass below, which
            # is the only place that knows how wide this cliff is.
            walked[step] = corners[left]
            continue
        if segment == "ease":
            parameter = float(_smoothstep(numpy.array(parameter)))
        walked[step] = (1.0 - parameter) * corners[left] + parameter * corners[left + 1]

    for left in range(len(positions) - 1):
        if segments[left] != "hard":
            continue
        width = soft_cliff if widths[left] is None else float(widths[left])
        if width <= 0:
            continue  # The raw snap: hold, then land on the next stop in one sample.
        edge = positions[left + 1]
        window = (where >= edge - width) & (where < edge)
        ramp = _smoothstep((where[window] - (edge - width)) / width)[:, None]
        walked[window] = (1.0 - ramp) * corners[left] + ramp * corners[left + 1]

    from fractal_wallpapers.palettes import space

    srgb = numpy.clip(numpy.rint(space.srgb(walked)), 0, 255).astype(int)
    return [
        [step / (dense - 1), [int(srgb[step, 0]), int(srgb[step, 1]), int(srgb[step, 2])]]
        for step in range(dense)
    ]


def kind_of(stops: list[dict], dense: list[list]) -> str:
    """`cyclic` or `sequential`, measured on the gradient rather than assumed.

    Twice, because the two readings answer to different callers: the control
    points decide it within [`CLOSES`], and the dense table has to agree exactly,
    since `stops[0][1] == stops[-1][1]` is what a reader of the library checks.
    """
    first, last = stops[0]["oklch"], stops[-1]["oklch"]
    closes = all(
        abs(float(one) - float(other)) <= CLOSES for one, other in zip(first, last, strict=True)
    )
    baked = dense[0][1] == dense[-1][1]
    if closes and not baked:
        raise AuthoredImportError(
            f"the control points close to within {CLOSES} but the dense gradient does not "
            f"({dense[0][1]} against {dense[-1][1]}) — a map called cyclic on that evidence "
            f"would be baked without the fold that hides the seam it actually has"
        )
    return "cyclic" if closes else "sequential"


# --------------------------------------------------------------------------- #
# A drop on disk.
# --------------------------------------------------------------------------- #
def drop_dir(drop: str, root: Path | None = None) -> Path:
    """Where one drop's batch files live."""
    return (Path(root) if root is not None else repo_root()) / BATCHES / drop


def drops(root: Path | None = None) -> list[str]:
    """Every drop this repository tracks, in the order a listing reads."""
    directory = (Path(root) if root is not None else repo_root()) / BATCHES
    if not directory.is_dir():
        return []
    return sorted(path.name for path in directory.iterdir() if path.is_dir())


def renames_of(directory: Path) -> dict[tuple[str, str], dict]:
    """`{(batch, emitted name): rename row}` for one drop.

    Absent, a drop simply has no renames — which is the common case and not a
    missing file.
    """
    path = Path(directory) / RENAMES
    if not path.is_file():
        return {}
    document = json.loads(path.read_text(encoding="utf-8"))
    out: dict[tuple[str, str], dict] = {}
    for row in document.get("renames") or []:
        for key in ("batch", "emitted", "shipped", "why"):
            if not str(row.get(key) or "").strip():
                raise AuthoredImportError(f"{path}: a rename row has no {key}")
        out[(row["batch"], row["emitted"])] = row
    return out


def briefs(drop: str, root: Path | None = None) -> dict[str, dict]:
    """`{shipped name: provenance row}` for every map one drop authored.

    The row is the archive's authored shape — the run conditioning its batch file
    name records, the brief the palette was written to, and the author's own
    control points — plus the drop stamp, and `emitted_name` where the map does
    not ship under the name its run gave it.
    """
    from fractal_wallpapers.palettes import provenance

    directory = drop_dir(drop, root)
    if not directory.is_dir():
        raise AuthoredImportError(f"{directory} is not a drop; there is nothing to ingest")
    renames = renames_of(directory)
    out: dict[str, dict] = {}
    for path in sorted(directory.glob("*.json")):
        if path.name == RENAMES:
            continue
        conditioning = provenance.batch_conditioning(path.stem)
        for entry in json.loads(path.read_text(encoding="utf-8")):
            emitted = entry["name"]
            rename = renames.get((path.name, emitted))
            name = rename["shipped"] if rename else emitted
            if name in out:
                raise AuthoredImportError(
                    f"{name!r} is emitted twice in drop {drop!r} ({out[name]['batch']} and "
                    f"{path.name}). The name is the join key, so two briefs under it would "
                    f"attach one of them to the wrong gradient — {RENAMES} has to say which "
                    f"name the second one ships under."
                )
            row = {
                "schema": provenance.SCHEMA,
                "name": name,
                "source": provenance.AUTHORED,
                **conditioning,
                "batch": path.name,
                "drop": drop,
                "mood": entry["mood"],
                "architecture": entry["architecture"],
                "skeleton": entry["skeleton"],
                "value_key": entry["value_key"],
                "complexity": int(entry["complexity"]),
                "stops": [provenance.control_point(stop) for stop in entry["stops"]],
            }
            if rename:
                row["emitted_name"] = emitted
            out[name] = row
    return out


def converted(row: dict, dense: int = DENSE, soft_cliff: float = SOFT_CLIFF) -> dict:
    """One authored row as the colormap file this repository tracks."""
    stops = densify(row["stops"], dense=dense, soft_cliff=soft_cliff)
    return {
        "schema": SCHEMA,
        "name": row["name"],
        "kind": kind_of(row["stops"], stops),
        "source": SOURCE_LINE.format(
            name=row["name"],
            dense=len(stops),
            control=len(row["stops"]),
            batch=row["batch"],
            drop=row["drop"],
        ),
        "stops": stops,
    }


def run(
    drop: str,
    root: Path | None = None,
    directory: Path | None = None,
    dense: int = DENSE,
    soft_cliff: float = SOFT_CLIFF,
) -> dict:
    """Densify one drop into the library, and say what it wrote.

    Refuses before writing anything if a name the drop ships under is already a
    map here that this drop did not put there — the collision has to be settled
    in the drop's `renames.json`, where it is a decision with a reason attached.
    """
    directory = Path(directory) if directory is not None else colormap_dir()
    rows = briefs(drop, root)
    if not rows:
        raise AuthoredImportError(f"drop {drop!r} holds no palettes")

    documents = {
        name: converted(rows[name], dense=dense, soft_cliff=soft_cliff) for name in sorted(rows)
    }
    taken = []
    for name, document in documents.items():
        path = directory / f"{name}.json"
        if not path.is_file():
            continue
        # A file this drop wrote before says so in its own `source` line, and
        # re-ingesting a drop over itself is how a densifier fix reaches the
        # library. Any other map under the name is a collision.
        held = json.loads(path.read_text(encoding="utf-8"))
        if held.get("source") != document["source"]:
            taken.append(name)
    if taken:
        raise AuthoredImportError(
            f"drop {drop!r} ships {len(taken)} name(s) the library already holds: "
            f"{', '.join(repr(name) for name in taken)}. A name is the join key between a "
            f"gradient and its brief, so the drop's {RENAMES} has to say what these ship as."
        )

    written, kinds = [], {"cyclic": 0, "sequential": 0}
    for name, document in documents.items():
        kinds[document["kind"]] += 1
        library_import.write(document, directory)
        written.append(name)

    from fractal_wallpapers.palettes import provenance

    record = provenance.merge([rows[name] for name in written], directory, drop=drop)
    return {
        "drop": drop,
        "batches": sorted({row["batch"] for row in rows.values()}),
        "maps": len(written),
        "renamed": sorted(name for name, row in rows.items() if "emitted_name" in row),
        "dense": dense,
        "soft_cliff": soft_cliff,
        **kinds,
        "directory": str(directory),
        "retired": retired(drop, written, directory),
        "provenance": record,
    }


def retired(drop: str, written: list[str], directory: Path | None = None) -> list[str]:
    """Maps this drop wrote once and no longer ships, named rather than removed.

    A rename settled in `renames.json` and re-ingested leaves the map under its
    old name still in the library: the drop's provenance row for it is gone —
    the drop is authoritative for its own stamp — but the gradient is still there,
    and a map with no row reads as "converted, nobody authored it", which is a
    lie about how it got here. Deleting a colormap is not a thing an ingest does
    on its own, so it is reported and a person removes it.
    """
    directory = Path(directory) if directory is not None else colormap_dir()
    tail = f"drop {drop}."
    shipped = set(written)
    return sorted(
        path.stem
        for path in directory.glob("*.json")
        if path.stem not in shipped
        and str(json.loads(path.read_text(encoding="utf-8")).get("source", "")).endswith(tail)
    )


__all__ = [
    "BATCHES",
    "CLOSES",
    "DENSE",
    "RENAMES",
    "SCHEMA",
    "SOFT_CLIFF",
    "SOURCE_LINE",
    "AuthoredImportError",
    "briefs",
    "converted",
    "densify",
    "drop_dir",
    "drops",
    "kind_of",
    "renames_of",
    "retired",
    "run",
]
