"""Style scouting: a picker's locations, drawn from the published galleries.

A style picker shows Matt the style at places he already judged worth a seat, so its
locations come from the published gallery records, **never a spiral** (his ruling: a
spiral is a poor demonstration of a style). Hand-placed points and the atlas tune
drafts, and go to a picker only for a style that needs a structure the galleries lack,
measured by [`measure`] (Matt's ruling on item 011). Every gallery row carries the spiral probe's
verdict (`spiral`, and `p_spiral` behind it), and its record's `recipes.jsonl` the
`family`, `viewport` and `maxiter` a location record needs, so the draw renders
nothing until a style needs a structure measured.

**The draw** is seeded and stratified over the gallery's partitions (`mandelbrot`,
`julia:multibrot3`, …), round-robin in partition order, so forty candidates are not
forty Mandelbrot seats. A seat narrower than [`MIN_WIDTH`] is passed over: a style
render is double precision.

**A structure a style needs** is a filter. The cheap ones read the gallery row
(partition, family kind, degree, the seat's own mode). The measured one is **ink**:
the share of the frame a hair of light at the set paints, read off a 320x200 render of
[`PROBE`] (one `glow` on the distance estimate at `falloff` 2e-4 frame widths, half a
pixel at 2560, over black, the inside white). It is the mean linear luminance, so it is
a resolution-free reading of how much of the plane lies within a hair of the set: lace
and dense spirals read high and paint solid under any distance glow, thin dendrites
read low. `--max-ink` keeps the thin ones and `--thinnest` the thinnest of a probed
batch; the calibration is in `data/styles/README.md`'s *A new style from a reference
image*.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

#: The narrowest viewport a style render resolves (it iterates in doubles).
MIN_WIDTH = 1e-9

#: The structure probe: a hair of white light at the set, everything else black.
PROBE = {
    "name": "structure_probe",
    "interior": {"rgb": "#ffffff"},
    "layers": [
        {
            "kind": "glow",
            "channel": {"field": {"kind": "de"}},
            "falloff": 2e-4,
            "color": {"rgb": "#ffffff"},
            "blend": "normal",
            "opacity": 1.0,
        }
    ],
}

#: The probe's size: enough samples for a share, small enough for a second a seat.
PROBE_RESOLUTION = (320, 200)

#: How many seats a measured draw probes per seat it is asked for, unless told. Thin
#: structure is rare in the galleries (median ink 0.23 over 120 `final139_general`
#: seats, 11 at or under 0.10), so a thin draw needs about ten probes a seat.
PROBE_TRIES = 10


class ScoutError(ValueError):
    """A gallery that cannot be drawn from as asked."""


def records() -> dict[str, str]:
    """`{record name: stamp}` for every published record this machine holds."""
    from fractal_wallpapers.curation import tentative

    held = {}
    for stamp in tentative.published():
        held[tentative.read_manifest(stamp)["solve"]["name"]] = stamp
    return held


def stamp_of(named: str) -> tuple[str, str]:
    """`(record name, stamp)` for a record named either way."""
    held = records()
    if named in held:
        return named, held[named]
    for name, stamp in held.items():
        if stamp == named:
            return name, stamp
    raise ScoutError(f"no published record '{named}' here; there are: {', '.join(sorted(held))}")


def default_record() -> str:
    """The record an unnamed scout draws from: `tentative.DEFAULT`'s."""
    from fractal_wallpapers.curation import tentative

    return tentative.DEFAULT


def kind_of(recipe: dict[str, Any]) -> str:
    """`julia` for a dynamical-plane seat, `plane` for a parameter-plane one."""
    return "julia" if recipe["family"].get("kind") == "julia" else "plane"


def degree_of(recipe: dict[str, Any]) -> int | None:
    """A z^d + c family's degree (2 when unstated); `None` for a family that has none,
    so a phoenix seat never answers a `--degree` filter."""
    family = recipe["family"]
    if family.get("kind") not in ("mandelbrot", "multibrot", "julia"):
        return None
    return int(float(family.get("degree", 2)))


def candidates(
    named: list[str],
    *,
    max_p_spiral: float | None = None,
    partitions: list[str] | None = None,
    kinds: list[str] | None = None,
    degrees: list[int] | None = None,
    modes: list[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Every seat of the named records a picker may show, once each by key.

    Returns `(seats, passed)`: each seat `{row, recipe, record}`, and how many were
    passed over for each reason.
    """
    from fractal_wallpapers.curation import tentative

    seen: set[str] = set()
    seats: list[dict[str, Any]] = []
    passed = {"spiral": 0, "p_spiral": 0, "deep": 0, "filtered": 0, "repeat": 0}
    for name in named:
        record, stamp = stamp_of(name)
        recipes = tentative.read_recipes(stamp)
        for row in tentative.read_rows(stamp):
            recipe = recipes.get(str(row["key"]))
            if row["key"] in seen:
                passed["repeat"] += 1
                continue
            if row.get("spiral") is not False:
                passed["spiral"] += 1
                continue
            p = row.get("p_spiral")
            if max_p_spiral is not None and (p is None or p > max_p_spiral):
                passed["p_spiral"] += 1
                continue
            if recipe is None or float(recipe["viewport"]["width"]) < MIN_WIDTH:
                passed["deep"] += 1
                continue
            if (
                (partitions and row["partition"] not in partitions)
                or (kinds and kind_of(recipe) not in kinds)
                or (degrees and degree_of(recipe) not in degrees)
                or (modes and row["mode"] not in modes)
            ):
                passed["filtered"] += 1
                continue
            seen.add(row["key"])
            seats.append({"row": row, "recipe": recipe, "record": record})
    return seats, passed


def shuffled(seats: list[dict[str, Any]], seed: int) -> list[dict[str, Any]]:
    """The seats in draw order: seeded, round-robin over partitions in name order."""
    rng = random.Random(seed)
    pools: dict[str, list[dict[str, Any]]] = {}
    for seat in seats:
        pools.setdefault(seat["row"]["partition"], []).append(seat)
    pools = {name: rng.sample(pool, len(pool)) for name, pool in sorted(pools.items())}
    order = []
    while any(pools.values()):
        for name in sorted(pools):
            if pools[name]:
                order.append(pools[name].pop())
    return order


def location_of(seat: dict[str, Any]) -> dict[str, Any]:
    """The location record a seat draws as: what `style render --manifest` reads."""
    row, recipe = seat["row"], seat["recipe"]
    return {
        "schema": 1,
        "name": f"{row['partition'].replace(':', '-')}_{row['alias']}",
        "family": recipe["family"],
        "viewport": recipe["viewport"],
        "maxiter": recipe["maxiter"],
        "note": f"{seat['record']} seat {row['seat']} ({row['mode']}, {row['partition']})",
        "gallery": {
            "record": seat["record"],
            "seat": row["seat"],
            "key": row["key"],
            "p_spiral": row.get("p_spiral"),
        },
    }


def ink(location: dict[str, Any], scratch: Path) -> float:
    """The share of the frame a hair of light at the set paints (see the docstring)."""
    import numpy as np
    from PIL import Image

    from fractal_wallpapers import engine, locations, styles

    row = locations.one_location(location, location["name"], drawing=True)
    row["render"] = {
        **row["render"],
        "resolution": list(PROBE_RESOLUTION),
        "supersample": 1,
    }
    document = {"style": PROBE, "suggested_colormap": "hsv"}
    picture = scratch / f"{location['name']}.png"
    try:
        engine.render_report(styles.spec_of(row, document, picture))
        with Image.open(picture) as image:
            rgb = np.asarray(image.convert("RGB"), dtype=np.float64) / 255.0
    except OSError as unreadable:
        raise RuntimeError(f"probe of {location['name']} unreadable: {unreadable}") from None
    finally:
        picture.unlink(missing_ok=True)
    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    return float((linear @ np.array([0.2126, 0.7152, 0.0722])).mean())


def draw(
    seats: list[dict[str, Any]],
    n: int,
    seed: int,
    max_ink: float | None = None,
    thinnest: bool = False,
    limit: int | None = None,
    scratch: Path | None = None,
    log=None,
    min_ink: float | None = None,
) -> tuple[list[dict[str, Any]], list[float]]:
    """`n` location records, and every ink reading taken on the way.

    With no ink filter (`max_ink`, `min_ink`) and no `thinnest`, nothing is rendered:
    the first `n` seats in draw order. Otherwise seats are probed in draw order, at most
    `limit` of them ([`PROBE_TRIES`] per seat asked for by default): a seat reading
    above `max_ink` or below `min_ink` is passed over and the probing stops once `n` are
    kept; with `thinnest` all `limit` are probed and the `n` thinnest kept, thinnest
    first.
    """
    order = [location_of(seat) for seat in shuffled(seats, seed)]
    if max_ink is None and min_ink is None and not thinnest:
        return order[:n], []
    return measure(
        order[: limit or n * PROBE_TRIES], n, max_ink, thinnest, scratch, log, min_ink=min_ink
    )


def measure(
    order: list[dict[str, Any]],
    n: int,
    max_ink: float | None,
    thinnest: bool,
    scratch: Path | None,
    log=None,
    min_ink: float | None = None,
    every: bool = False,
) -> tuple[list[dict[str, Any]], list[float]]:
    """Probe location records in order for ink and keep as [`draw`] says.

    Also the door for **hand-placed or atlas points**, which a picker may show only for
    a style that needs a structure the galleries lack (Matt's ruling on item 011): they
    are measured exactly as gallery seats are, and carry the reading. With `every`, each
    record is probed and kept in its own order with its reading, whatever `n` and the
    filters say: a measurement, not a draw.
    """
    if scratch is None:
        raise ScoutError("measuring ink needs a scratch folder")
    scratch.mkdir(parents=True, exist_ok=True)
    kept, readings = [], []
    for location in order:
        if not (thinnest or every) and len(kept) >= n:
            break
        location = {**location, "name": location.get("name") or f"point_{len(readings):03d}"}
        reading = ink(location, scratch)
        readings.append(reading)
        if log is not None:
            log(f"[scout] {len(readings)}: {location['name']} ink {reading:.4f}")
        inside = (max_ink is None or reading <= max_ink) and (min_ink is None or reading >= min_ink)
        if every or inside:
            location["ink"] = round(reading, 5)
            kept.append(location)
    if every:
        return kept, readings
    if thinnest:
        kept.sort(key=lambda location: location["ink"])
    return kept[:n], readings


def write(rows: list[dict[str, Any]], path: Path) -> Path:
    """The draw as a location manifest, one record a line."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path
