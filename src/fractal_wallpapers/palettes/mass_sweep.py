"""The leg that measures what colour a map makes, for the maps nothing measured.

[`color_mass`] is the tracked answer and this is how a row gets into it. The map
is a *measurement* over the roster and the library of the day, so a colormap drop
lands as a set of palette groups with no row at all — reachable only through the
carrier prior, which is a bound on the ramp rather than a reading of this
pipeline. Closing that hole is a render leg, and until this module there was
nothing to run it with: the first sweep ran out of a disposable `scratch/`, which
is why the log's own rebuild command is `restore` twice.

## What it renders, and why it cannot choose

**The panel is the one the map was cut on, and this module reads it back rather
than restating it.** [`PANEL`] carries the two locations as family-and-viewport
records; [`panel`] checks each one's [`supply.location.key_text`] against the
tracked manifest's `panel.keys` before handing any of them out, so a coordinate
mistyped here is a refusal instead of a row measured somewhere else and filed
beside rows that were not. The iteration cap is not stored on the manifest and is
not a constant here either — `engine.maxiter_for` derives 5,467 and 22,794 from
the two widths, which is what the original sweep drew at.

Geometry, recipe and operator are [`curation.colorize`]'s, through
[`curation.colorize.render`] — the one place a curation picture is made. That is
the point of routing through it: a leg that built its own spec would drift from
what production draws on the first knob either side moved, and the rows would be
a measurement of a pipeline nobody runs.

## What a mode costs, which is the whole shape of a leg here

Only the four `field`-kind modes share an iteration pass: the field is dumped once
per (location, mode) and every map at it is a colormap lookup. A composite, a
modulate and a direct trap have no single scalar field, so each of their maps is a
full render — and at the `mandelbrot` panel location, whose cap is 22,794, that is
tens of seconds apiece against a field mode's third of one. Priced off the first
sweep's own per-render `seconds`, over the two panel locations:

```text
the four field modes together     3.0 s a map
itinerary + the three direct traps   39.9 s a map
threads                             18.1 s a map
the four big composites            169.3 s a map
```

So a roster is a budget decision and [`run`] takes its modes in the order it is
given, stopping on the clock rather than part way through a mode — a mode measured
over some of the maps and not others is a column that reads as a difference
between maps when it is a difference between when the leg stopped.
"""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

#: The schema the rows this writes carry, which is the sweep log's own.
SCHEMA = 1

#: What every row here is, in the log's spelling. The log's other kind is its
#: `header`, written once by the first sweep and never rewritten.
RENDER_ROW = "render"

#: The two panel locations, as the family-and-viewport records the engine reads.
#: Checked against the tracked manifest's own keys by [`panel`] before use — the
#: manifest is the owner of *which* locations the map was cut on and this is the
#: only place they are spelled as something renderable.
PANEL: tuple[dict, ...] = (
    {
        "family": {
            "kind": "julia",
            "degree": 5,
            "c": ["0.22703883150276297", "0.7099321279535775"],
        },
        "viewport": {
            "center_re": "0.21328013825213143",
            "center_im": "-0.040758678337073515",
            "width": "1.2853612761582334",
        },
    },
    {
        "family": {"kind": "mandelbrot", "degree": 2},
        "viewport": {
            "center_re": "-0.7420778398275718",
            "center_im": "-0.1137752237317548",
            "width": "0.00005785591417811585",
        },
    },
)


class MassSweepError(RuntimeError):
    """The leg cannot be run against the panel the map was cut on."""


def panel() -> list[dict]:
    """The panel, each location carrying its key, its partition and its cap.

    Refuses where a location here does not answer to a key the tracked manifest
    names. The two files are a pair — one says where the map was measured, the
    other says how to draw it — and a pair that disagrees is worse than a missing
    half, because the rows it writes look like the rows it should have written.
    """
    from fractal_wallpapers import engine
    from fractal_wallpapers.palettes import color_mass
    from fractal_wallpapers.supply.location import key_text, location_key
    from fractal_wallpapers.supply.partitions import partition_of_family

    where = color_mass.sweep_manifest_path()
    if not where.is_file():
        raise MassSweepError(
            f"{where} is not there, so nothing says which panel the colour-mass map was "
            f"cut on. The manifest is tracked; a checkout missing it is a checkout with "
            f"no record of the instrument."
        )
    named = set(json.loads(where.read_text(encoding="utf-8"))["panel"]["keys"])
    out = []
    for entry in PANEL:
        key = key_text(location_key(entry["family"], entry["viewport"]))
        if key not in named:
            raise MassSweepError(
                f"{key} is not one of the panel keys {where} names, so a row measured "
                f"here would be filed beside rows measured somewhere else."
            )
        out.append(
            {
                "family": entry["family"],
                "viewport": entry["viewport"],
                "key": key,
                "partition": partition_of_family(entry["family"]),
                "maxiter": engine.maxiter_for([entry["viewport"]["width"]])[0],
            }
        )
    return out


def unmeasured_maps() -> list[str]:
    """Every map a leg may draw that the colour-mass map holds no row for.

    The draw pool and not the library: a map production cannot pick is a map whose
    realized colour nothing would read. `blue_orange` is the one the two lists
    differ by today — it is in the library, it has no mass row, and
    `colorize.pool` does not offer it.
    """
    from fractal_wallpapers.curation import colorize
    from fractal_wallpapers.palettes import color_mass, groups

    table = color_mass.read()
    measured = {group for group, _mode in table}
    member = groups.member_groups()
    return [name for name in colorize.pool(0) if groups.group_of(name, member) not in measured]


def row_of(
    colormap: str,
    mode: str,
    location: dict,
    shares: dict,
    mirror: bool,
    leveled: bool,
    seconds: float,
) -> dict:
    """One measurement, in the sweep log's own row shape and field order."""
    from fractal_wallpapers.curation import colorize
    from fractal_wallpapers.palettes import groups

    return {
        "schema": SCHEMA,
        "group": groups.group_of(colormap),
        "colormap": colormap,
        "mode": mode,
        "mode_kind": colorize.kind_of(mode),
        "location": location["key"],
        "partition": location["partition"],
        "mirror": bool(mirror),
        "maxiter": int(location["maxiter"]),
        "resolution": list(colorize.RESOLUTION),
        "supersample": colorize.SUPERSAMPLE,
        "leveled": bool(leveled),
        "shares": {name: value for name, value in shares.items() if value > 0.0},
        "seconds": round(float(seconds), 3),
        "error": None,
        "kind": RENDER_ROW,
    }


def _measure(place: dict, mode: str, colormap: str, cyclic: set, workdir: Path, band) -> dict:
    """Render one (map, mode, location) and read its census off the picture."""
    from fractal_wallpapers.curation import colorize
    from fractal_wallpapers.palettes import codebook

    picture = workdir / f"{mode}_{place['partition'].replace(':', '-')}_{colormap}.jpg"
    picture.unlink(missing_ok=True)
    started = time.perf_counter()
    _made, stamp = colorize.render(
        {"family": place["family"], "viewport": place["viewport"], "maxiter": place["maxiter"]},
        mode,
        colormap,
        cyclic,
        picture,
        level=True,
        band=band,
        fields=workdir / "fields",
    )
    spent = time.perf_counter() - started
    # The **raw** 52-cell vector, neutrals included, because that is what a sweep
    # row holds: `color_mass.tally` takes the chromatic reduction itself, and a
    # row already reduced would be renormalised a second time.
    shares = codebook.of_picture(picture)["shares"]
    row = row_of(
        colormap,
        mode,
        place,
        shares,
        mirror=colormap not in cyclic,
        leveled=bool(stamp and stamp.get("acted")),
        seconds=spent,
    )
    picture.unlink(missing_ok=True)
    leveled_dir = picture.parent / f"{picture.stem}.leveled"
    if leveled_dir.is_dir():
        for one in leveled_dir.iterdir():
            one.unlink(missing_ok=True)
        leveled_dir.rmdir()
    return row


def run(
    maps: list[str],
    modes: list[str],
    workdir: Path,
    workers: int = 3,
    budget: float | None = None,
    log=print,
) -> tuple[list[dict], dict]:
    """`(rows, report)` — the panel rendered for these maps, mode by mode.

    Modes are taken in the order given and a mode is finished or not started:
    what the clock cuts is the tail of the roster, which is a stated absence,
    where a mode cut in the middle would be a column that says one thing about
    some maps and another about the rest.

    `workers` is the render pool this box allows, and the concurrency is over the
    maps inside one (mode, location) cell rather than across cells — a shareable
    mode's field is dumped once, serially, before its maps are handed out, so the
    three that follow are colormap lookups over a file that is already there.
    """
    from fractal_wallpapers.curation import colorize

    places = panel()
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    cyclic = colorize.cyclic()
    band = colorize.band()
    started = time.perf_counter()
    rows: list[dict] = []
    done: list[str] = []
    skipped: list[str] = []
    priced: dict[str, float] = {}
    for mode in modes:
        left = None if budget is None else budget - (time.perf_counter() - started)
        if left is not None and left <= 0:
            skipped.append(mode)
            continue
        at = time.perf_counter()
        made: list[dict] = []
        for place in places:
            if colorize.shareable(mode):
                # Serially, and before the pool opens on this cell: three threads
                # asking for a field nobody has dumped yet is three iteration
                # passes over the same array, and the second and third are paid
                # for nothing.
                colorize.field_of(
                    {
                        "family": place["family"],
                        "viewport": place["viewport"],
                        "maxiter": place["maxiter"],
                    },
                    workdir / "fields",
                    mode=mode,
                    curve=colorize.CURVE,
                )
            with ThreadPoolExecutor(max_workers=max(1, int(workers))) as pool:
                made.extend(
                    pool.map(
                        lambda name, place=place, mode=mode: _measure(
                            place, mode, name, cyclic, workdir, band
                        ),
                        maps,
                    )
                )
        rows.extend(made)
        done.append(mode)
        priced[mode] = round(sum(row["seconds"] for row in made) / max(1, len(maps)), 3)
        log(
            f"[mass-sweep] {mode:22} {len(made):5} render(s)  "
            f"{priced[mode]:7.2f} s a map  {time.perf_counter() - at:8.1f} s wall"
        )
        if budget is not None and time.perf_counter() - started >= budget:
            skipped.extend(name for name in modes if name not in done and name not in skipped)
            break
    report = {
        "maps": len(maps),
        "modes_measured": done,
        "modes_left": [name for name in modes if name not in done],
        "rows": len(rows),
        "seconds_a_map": priced,
        "wall_seconds": round(time.perf_counter() - started, 1),
        "engine_seconds": round(sum(row["seconds"] for row in rows), 1),
    }
    return rows, report


def append(rows: list[dict], path: Path | None = None) -> dict:
    """Append measurements to the sweep log, and say what it holds afterwards.

    The log is the union of every leg that ever measured a pair, so this appends
    and never rewrites: the 27,053 rows the first sweep wrote are the evidence
    behind every existing row of the tracked map, and a leg that rewrote them
    would be a leg that could silently change a number it did not measure.
    """
    from fractal_wallpapers.palettes import color_mass

    where = color_mass.sweep_log_path() if path is None else Path(path)
    if not where.is_file():
        raise MassSweepError(
            f"{where} is not there. The log lives on the archive tier between legs — "
            f"`fractal-wallpapers curate mass-sweep restore` brings it back, and appending "
            f"to a log that is not all here would write a manifest nothing can verify."
        )
    before = sum(1 for line in where.open(encoding="utf-8") if line.strip())
    with where.open("a", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    after = sum(1 for line in where.open(encoding="utf-8") if line.strip())
    return {"log": str(where), "rows_before": before, "appended": len(rows), "rows": after}


__all__ = [
    "PANEL",
    "RENDER_ROW",
    "SCHEMA",
    "MassSweepError",
    "append",
    "panel",
    "row_of",
    "run",
    "unmeasured_maps",
]
