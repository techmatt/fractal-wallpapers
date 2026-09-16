"""The atlas: every place the search kept, as dots on a plate of the plane they sit in.

`curate atlas` writes one directory per plane, `artifacts/atlas/<plane>/`, and the
website's `builder atlas --ingest` turns it into the committed record and pictures the
atlas page ships. [`README.md`](README.md) says what is in the directory and who reads it;
[`population`] says which places qualify and how they are thinned, [`slots`] what each dot
shows and what a link to it can carry, and [`pictures`] how the plate and thumbnails are
drawn.
"""

from __future__ import annotations

import time
from pathlib import Path

#: The planes an atlas can be made of, by the name `--plane` takes: the family the plate
#: draws and the ledger partitions whose places land on it. The multibrot and phoenix
#: planes are this same table with a different family and home view, and are not in it
#: until the search has places on them.
PLANES: dict[str, dict] = {
    "mandelbrot": {
        "family": {"kind": "mandelbrot", "degree": 2},
        "partitions": ("mandelbrot", "julia:mandelbrot"),
    },
}

#: The absorption radius, in pixels of the plate. At 4096 wide one pixel is 1.07e-3 of the
#: Mandelbrot plate, so 12 px is 0.0129 of plane width — wide enough that a deep-zoom
#: cluster reads as one place rather than as a smear, narrow enough that the seated
#: record's own neighbourhoods stay apart.
RADIUS_PX = 12.0

#: The plate's pixels, and the width a dynamical place's neighbourhood plate is drawn at
#: as a fraction of the plate's own. 0.05 of 4.4 is 0.22 — a few times the width of the
#: largest hyperbolic component a `c` is likely to sit beside, so the dot's parameter is
#: shown in its own structure rather than as a speck of the whole set.
PLATE = (4096, 2304)
PLATE_FRACTION = 0.05

#: The map the plate is drawn through: a grey ramp stopping short of white, so the dots
#: drawn over it read. A real library map, so a figure of the plate cites a name.
PLATE_COLORMAP = "atlas_grey"

#: Three per dot, and the page scales them. The page's strip is a third of the plate's
#: width, so a slot lands at roughly 0.41 of the viewport's remaining height: 400 px is
#: right at a 1000-tall window and a modest upscale above that.
THUMB = (400, 225)

#: The names the website's ingest reads, beside each other in one directory.
DOTS_NAME = "dots.json"
SUMMARY_NAME = "dots_summary.json"
PLATE_NAME = "base.jpg"
PLATE_REPORT_NAME = "base.json"
THUMBS_NAME = "thumbs"
THUMBS_REPORT_NAME = "thumbs.json"

#: What the record says made it, which the website writes into its method row.
GENERATOR = "fractal-wallpapers curate atlas"


class AtlasRefused(RuntimeError):
    """The atlas cannot be made from what was asked for."""


def default_out(plane: str) -> Path:
    from fractal_wallpapers.paths import under

    return under("atlas", plane)


def make(
    plane: str = "mandelbrot",
    record: str | None = None,
    radius_px: float = RADIUS_PX,
    out: Path | None = None,
    pictures: bool = True,
    workers: int = 3,
) -> dict:
    """Read the stores, thin the places, write the record, then draw what it names.

    The record is written **before** any picture is drawn, so a thumbnail leg that dies
    leaves a record that is right and pictures that are short, never the other way round.
    """
    from fractal_wallpapers import engine
    from fractal_wallpapers.curation import backfill as backfill_module
    from fractal_wallpapers.curation import colorize, stamps, tentative
    from fractal_wallpapers.curation.candidate_ledger import store
    from fractal_wallpapers.models import location_view
    from fractal_wallpapers.palettes import groups

    from . import pictures as drawing
    from . import population, slots

    if plane not in PLANES:
        raise AtlasRefused(f"{plane}: the planes an atlas is made of are {', '.join(PLANES)}")
    if radius_px <= 0:
        raise AtlasRefused(f"--radius {radius_px}: an absorption radius is positive")
    started = time.time()
    spec = PLANES[plane]
    record = record or tentative.latest()
    out = Path(out) if out is not None else default_out(plane)
    out.mkdir(parents=True, exist_ok=True)

    family = spec["family"]
    view = engine.home_view(family)
    plate_width = repr(round(float(view["width"]) * PLATE_FRACTION, 12))

    read = population.collect(record, spec["partitions"])
    places = read["places"]
    dots, tally = population.thin(places.values(), view, PLATE, radius_px)
    tally["radius_px"] = radius_px
    population.stamp(f"{len(places):,} places queued, {tally['dots']:,} dots")

    wanted = set()
    for dot in dots:
        if dot.place.seat is not None:
            wanted.add(str(dot.place.seat["key"]))
        wanted.update(key for _value, key in dot.place.fine_rows)
    population.stamp(f"reading {len(wanted):,} ledger recipes back")
    ledger = store.by_key(wanted)

    canonical = location_view.canonical_map()
    julia_home = engine.home_view(slots.julia_family(["0", "0"]))
    library = set(groups.library())
    cyclic = colorize.cyclic()

    drawn = []
    for dot in dots:
        views = slots.views_of(dot.place, family, julia_home, plate_width, canonical)
        found = slots.gallery_of(dot.place, ledger)
        views["gallery"] = None if found is None else found[1]
        drawn.append(views)

    galleries = {
        views["gallery"]["key"]: ledger[views["gallery"]["key"]]
        for views in drawn
        if views["gallery"] is not None
    }
    population.stamp(f"reading the tone stamps of {len(galleries):,} gallery rows")
    held_stamps = stamps.for_rows(galleries, backfill_module.read())

    # The engine owns the iteration cap, and it is asked once for every distinct width
    # rather than once per view: a `maxiter` call is a subprocess.
    widths = sorted(
        {
            str(recipe["viewport"]["width"])
            for views in drawn
            for recipe in views.values()
            if recipe is not None and recipe.get("maxiter") in (None, 0)
        }
    )
    population.stamp(f"asking the engine for {len(widths):,} iteration caps")
    caps = dict(zip(widths, engine.maxiter_for(widths), strict=True))

    rows, jobs = [], []
    tones = {slots.CLEAN: 0, slots.CURVED: 0, slots.LOST: 0}
    seated_tones = dict(tones)
    thumbs = out / THUMBS_NAME
    for index, (dot, views) in enumerate(zip(dots, drawn, strict=True)):
        held = dot.place
        entry = {
            "id": index,
            "px": round(dot.px, 2),
            "py": round(dot.py, 2),
            "kind": population.KIND[held.partition],
            "dropped": dot.dropped,
            "place": {
                "location": held.location,
                "x": held.x,
                "y": held.y,
                "p_fine": held.p_fine,
                "rows_at_bar": held.fine_at_bar,
                "p_ge4": held.p_ge4,
                "judged_rows": held.judged_rows,
                "seat": held.seat,
            },
            "slots": {},
        }
        for name in slots.SLOTS:
            recipe = views[name]
            if recipe is None:
                entry["slots"][name] = None
                continue
            if recipe.get("maxiter") in (None, 0):
                recipe["maxiter"] = int(caps[str(recipe["viewport"]["width"])])
            tone = borrowed = None
            if name == "gallery":
                key = recipe["key"]
                tone = slots.tone_of(ledger[key], held_stamps.get(key))
                tones[tone["tone"]] += 1
                if recipe["seated"]:
                    seated_tones[tone["tone"]] += 1
                borrowed = stamps.borrowed_for(key, held_stamps.get(key), ledger[key], atlas=key)
            slot = {
                "what": recipe.get("what"),
                "source": recipe.get("source"),
                "seated": recipe.get("seated"),
                "key": recipe.get("key"),
                "mode": recipe["mode"],
                "mode_params": recipe.get("mode_params") or {},
                "colormap": recipe["colormap"],
                "viewport": recipe["viewport"],
                "family": recipe["family"],
                "maxiter": recipe["maxiter"],
                "p_fine": recipe.get("p_fine"),
                "palette": recipe.get("palette"),
                "curve": recipe.get("curve"),
                "refused": slots.refusals(
                    recipe, library, cyclic, None if tone is None else tone["tone"]
                ),
                "picture": f"{THUMBS_NAME}/{index:04d}_{name}.jpg",
            }
            if tone is not None:
                slot.update(tone)
            entry["slots"][name] = slot
            jobs.append(
                drawing.job_of(
                    recipe,
                    thumbs / f"{index:04d}_{name}.jpg",
                    THUMB,
                    drawing.SUPERSAMPLE,
                    borrowed=borrowed,
                )
            )
        rows.append(entry)

    summary = dict(tally)
    summary["seats_under_bar"] = read["seats_under_bar"]
    summary["gallery_seated"] = sum(1 for d in rows if (d["slots"]["gallery"] or {}).get("seated"))
    summary["gallery_missing"] = sum(1 for d in rows if d["slots"]["gallery"] is None)
    summary["tone"] = tones
    summary["tone_seated"] = seated_tones
    payload = {
        "schema": 1,
        "generator": GENERATOR,
        "plane": plane,
        "base": {"image": PLATE_NAME, "viewport": view, "resolution": list(PLATE)},
        "radius_px": radius_px,
        "plate_width": plate_width,
        "thumb": {"resolution": list(THUMB), "supersample": drawing.SUPERSAMPLE},
        "record": record,
        "judge_artifact": read["live"],
        "fine_bar": read["fine_bar"],
        "seats_under_bar": read["seats_under_bar"],
        "canonical_map": canonical,
        "tally": tally,
        "dots": rows,
        "seconds": round(time.time() - started, 1),
    }
    drawing.write_json(out / DOTS_NAME, payload)
    drawing.write_json(out / SUMMARY_NAME, summary, indent=2)
    population.stamp(f"wrote {out / DOTS_NAME}")

    if not pictures:
        return summary

    population.stamp(f"drawing the plate at {PLATE[0]}x{PLATE[1]}")
    plate = drawing.render_plate(family, PLATE, PLATE_COLORMAP, out / PLATE_NAME)
    drawing.write_json(out / PLATE_REPORT_NAME, plate, indent=2)

    cleared = drawing.clear(thumbs)
    thumbs.mkdir(parents=True, exist_ok=True)
    if cleared:
        population.stamp(f"cleared {cleared:,} entries an earlier run left in {THUMBS_NAME}/")
    drawn_report = drawing.draw_all(jobs, workers=workers)
    drawn_report["files"] = len(list(thumbs.glob("*.jpg")))
    drawn_report["bytes"] = sum(path.stat().st_size for path in thumbs.glob("*.jpg"))
    drawing.write_json(out / THUMBS_REPORT_NAME, drawn_report, indent=2)
    summary["plate_seconds"] = plate["seconds"]
    summary["thumbs"] = {k: v for k, v in drawn_report.items() if k != "why"}
    summary["seconds"] = round(time.time() - started, 1)
    drawing.write_json(out / SUMMARY_NAME, summary, indent=2)
    if drawn_report["failed"]:
        for line in drawn_report["why"][:10]:
            print("  " + line, flush=True)
    return summary
