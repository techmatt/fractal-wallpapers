"""How much of the codebook the finished collection expresses.

[`palette_coverage`] asks what a *map* can do: how many of the nine hundred baked
colormaps can put a swatch on a real share of some picture's pixels. This module
asks the question one step downstream, about the pictures that actually exist:

```text
COVERAGE(s) = the fraction of finished wallpapers in which at least
              10% of the pixels are assigned to swatch s
```

Measurement only. Nothing here gates, filters or removes anything, and no floor
is declared — the module reports the numbers a floor would have to live inside.

## The budget is the whole finding, and it is arithmetic rather than taste

Summed over the fifty-two swatches, COVERAGE is the **mean number of swatches a
wallpaper expresses above 10%**. That single number decides whether a uniform
per-swatch floor can exist at all: a floor of `f` across `k` swatches demands
`f * k` expressed colours from the average picture, so the largest uniform floor
the pool can support is `mean / k` and nothing about curation policy can move it.
A picture has one hundred percent of its pixels to spend and a swatch's claim on
ten of them is not free.

## Measured on the shipped render, at its own resolution

A share vector is not scale-free. Supersampling averages adjacent ramp colours
before they reach a pixel and the codebook's assignment is soft, so the same
recipe at `640x360 x2` and at `2560x1440 x4` produces different numbers — a
median of two points apart over the pictures this project has released, and up to
sixty-four where the autolevel operator read the two frames differently. So the
census here reads the release PNG at **its own** resolution — taken off the file
and written onto the row — and never the candidate render that stands behind it.

That the release regime is now a per-pass decision does not change the definition
and is exactly why it is worded this way. A share vector taken over pictures made
at one regime is a **different population** from one taken over another; which
regime a pass shipped is on its pass record and on each of its release rows, and
that is what tells two populations apart. Nothing here re-reads a picture at a
regime it was not made at.

The 160x90 decode [`codebook.of_picture`] uses is checked against that rather
than assumed: [`agreement`] reports both, and on the released population the
worst swatch moves 0.7 of a point.

## What the census is and is not read for

Every line of this is a reading. Until 2026-09-06 one of them was not: `thin` named
the swatches at most five finished pictures expressed, `curation.rank_key`'s
`stratum_score` column read that list at the merge's prune and again at the solve,
and `curation.manufacture` aimed a whole batch of renders at it. A count-shaped
threshold read as policy over a growing collection is wrong in a *direction* — the
21 cells it named over 246 pictures were **one** cell over the 645 released since,
which moved 98,000 of the candidate pool's 308,000 rows across a partition a fitted
coefficient was pointed at.

Matt's ruling of 2026-09-06 removed the whole apparatus rather than repairing it:
the colour ceiling already keeps any one colour from dominating, as a hard
constraint at the seat, and a soft nudge doing a fuzzier version of that job in the
merge prune was deleting rows permanently for it. The thin list, its threshold, the
population-drift guard and the recolor pricing that stood behind it all went with
the `stratum_score` column.

What is left is measurement that decides nothing, which is what the top of this
docstring already said the module was. **Nothing downstream reads this file.**
"""

from __future__ import annotations

import json
from pathlib import Path

from fractal_wallpapers.palettes import codebook

#: The artifact's schema, carried from the first row.
SCHEMA = 1

#: A swatch is EXPRESSED in a picture when it holds at least this share of the
#: pixels. The census's own "present" threshold [`codebook.SHARE_THRESHOLDS`], so
#: a coverage figure and a census figure mean the same thing by the word.
THRESHOLD = 0.10

#: The candidate-geometry share a recolor must show before it is worth measuring
#: at release geometry. Measured, not chosen: zero of the 788 released
#: (picture, swatch) cells at or above [`THRESHOLD`] on the shipped render sit
#: below this at candidate geometry. [`agreement`] re-derives it on demand.
SCREEN = 0.06

#: Where a candidate is judged, and where the screen is taken. The geometry both
#: release floors were fitted at and the one `curation.rescore` reads the pool at.
CANDIDATE_RESOLUTION = (640, 360)
CANDIDATE_SUPERSAMPLE = 2

#: There is deliberately no release geometry here. Coverage is measured at
#: **whatever the picture is**, read off the file by [`full_shares`] and written
#: onto the row as `resolution`; which regime a wallpaper was made under is the
#: pass's own decision and is on the pass record and on the release row. A
#: constant here would be a second claim about a population this module measures,
#: and it would go stale the first time a pass shipped another size — which one
#: did, on 2026-08-25.

#: There is deliberately no thinness threshold here either, and there is no
#: population-drift guard standing over one. Both went with the `stratum_score`
#: column on 2026-09-06 — see *What the census is and is not read for* above.


class ExpressedError(RuntimeError):
    """The collection's colour cannot be read over the stores as they are."""


# --------------------------------------------------------------------------- #
# Where it lands.
# --------------------------------------------------------------------------- #
def expressed_dir() -> Path:
    """Where this measurement lives. Ignored, and regenerable."""
    from fractal_wallpapers.paths import under

    return under("curation", "expressed")


def pictures_path() -> Path:
    """One row per finished wallpaper: its share vector off the shipped PNG."""
    return expressed_dir() / "pictures.jsonl"


def readout_path() -> Path:
    """The coverage vector, the budget and the agreement table."""
    return expressed_dir() / "expressed.json"


def _write_jsonl(path: Path, rows) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


def _read_jsonl(path: Path) -> list[dict]:
    if not Path(path).is_file():
        raise ExpressedError(f"{path} is missing — take the step that writes it first")
    return [
        json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line
    ]


def _write_json(path: Path, document: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return path


# --------------------------------------------------------------------------- #
# The population.
# --------------------------------------------------------------------------- #
def neutrals() -> list[str]:
    """The four achromatic swatches, off the codebook rather than by name here."""
    return [entry["swatch"] for entry in codebook.swatches() if entry["kind"] == "neutral"]


def finished() -> list[dict]:
    """Every finished full-size render on record, with the picture that proves it.

    A `released` row is one that took a slot **and** whose picture exists; the
    store's other three verdicts each mean there is no wallpaper at the end of
    the row, and `unrendered` in particular is a seat whose release leg was never
    spent. The file is checked anyway, because presence is what the verdict is
    claiming and a claim worth reading is worth testing.

    A row taken back afterwards by [`rejection`] is **kept**. This is a question
    about colour and not about seating: the picture was made at full size, it is
    on record, and what a bar would do to it today says nothing about what
    colours it holds.
    """
    from fractal_wallpapers.curation import records, run_layout

    rows = []
    for row in records.read_decisions(records.RELEASE):
        if row.get("verdict") != records.RELEASED:
            continue
        picture = run_layout.run_dir(row["run"]) / str(row["picture"]).replace("\\", "/")
        if not picture.is_file():
            raise ExpressedError(
                f"{row['key']} reads `released` and its picture is not at {picture}. "
                f"A verdict that cannot be checked is worse than one that is wrong."
            )
        rows.append({"row": row, "picture": picture})
    if not rows:
        raise ExpressedError(
            "the release store holds no finished wallpaper, so there is no population "
            "to measure colour coverage over"
        )
    return rows


def full_shares(picture: Path) -> dict:
    """One picture's census at its own resolution, with nothing downsampled.

    [`codebook.of_picture`] reads at 160x90, which is exact for the two sizes the
    *candidate* path stores and a 1-in-256 sample of a release PNG. The soft
    assignment is a mean over pixels either way, so the two agree closely — but
    "closely" is a measurement and [`agreement`] takes it rather than assuming it.
    """
    import numpy
    from PIL import Image

    from fractal_wallpapers.palettes import space

    path = Path(picture)
    with Image.open(path) as opened:
        pixels = numpy.asarray(opened.convert("RGB"), dtype=numpy.uint8)
    colours, counts = codebook.distinct(pixels)
    read = codebook.census(space.oklab(colours), counts)
    read["resolution"] = [int(pixels.shape[1]), int(pixels.shape[0])]
    return read


def census(log=print) -> int:
    """Read every finished wallpaper, at full resolution and at census resolution.

    Both, on every picture, because the second is the cheap instrument the rest of
    this project uses and the whole population is small enough to price the
    difference exactly rather than on a sample.
    """
    import time

    from fractal_wallpapers.curation import records, rescore

    pool = {row["key"]: row for row in records.read_decisions(records.RELEASE)}
    population = finished()
    started = time.time()
    rows = []
    for index, entry in enumerate(population, start=1):
        row, picture = entry["row"], entry["picture"]
        candidate = rescore.picture_of(row, pool)
        read = full_shares(picture)
        rows.append(
            {
                "schema": SCHEMA,
                "key": row["key"],
                "run": row["run"],
                "candidate": row["candidate"],
                "collection": row.get("collection"),
                "rejected": bool(row.get("rejected")),
                "kind": row["scores"]["head"],
                "mode": row["recipe"]["mode"],
                "mode_kind": row["recipe"]["mode_kind"],
                "curve": row["recipe"]["curve"],
                "colormap": row["recipe"]["colormap"],
                "mirror": bool(row["recipe"]["mirror"]),
                "partition": row["location"]["partition"],
                "family": row["location"]["family"],
                "viewport": row["location"]["viewport"],
                "maxiter": int(row["location"]["maxiter"]),
                "picture": str(picture),
                "candidate_picture": str(candidate) if candidate.is_file() else None,
                "score": row.get("scores_current"),
                "shares": read["shares"],
                "dominant": read["dominant"],
                "entropy_bits": read["entropy_bits"],
                "resolution": read["resolution"],
                # Two comparisons, and each has to isolate ONE effect. The census
                # decode is the same picture read at 160x90, so `census_shares`
                # differs from `shares` by the sampling and nothing else. The
                # candidate render is a different picture, so `candidate_shares`
                # is read at ITS full resolution — reading it at 160x90 too would
                # fold the decode's error into the geometry's and neither column
                # would answer its own question.
                "census_shares": codebook.of_picture(picture)["shares"],
                "candidate_shares": (
                    full_shares(candidate)["shares"] if candidate.is_file() else None
                ),
            }
        )
        if index % 25 == 0:
            log(f"[census] {index}/{len(population)}, {time.time() - started:.0f}s")
    count = _write_jsonl(pictures_path(), rows)
    log(f"[census] {count} finished wallpapers in {time.time() - started:.0f}s")
    return count


# --------------------------------------------------------------------------- #
# Part 1 — the coverage vector. Part 2 — the budget.
# --------------------------------------------------------------------------- #
def coverage(rows: list[dict], key: str = "shares") -> dict:
    """Per swatch, the fraction of these pictures that express it above [`THRESHOLD`]."""
    total = len(rows)
    return {
        name: (sum(1 for row in rows if (row[key] or {}).get(name, 0.0) >= THRESHOLD) / total)
        for name in codebook.names()
    }


def expressed_counts(rows: list[dict], names=None, key: str = "shares") -> list[int]:
    """Per picture, how many of these swatches it expresses above [`THRESHOLD`]."""
    wanted = list(names if names is not None else codebook.names())
    return [
        sum(1 for name in wanted if (row[key] or {}).get(name, 0.0) >= THRESHOLD) for row in rows
    ]


def distribution(counts: list[int]) -> dict:
    """The spread of a per-picture count, as the quantiles and the whole histogram.

    The histogram rather than a summary alone: the population is 246 pictures over
    seven integers, and every one of those bars is a sentence about what a floor
    would have to be true of.
    """
    import statistics

    ordered = sorted(counts)

    def at(fraction: float) -> float:
        return float(ordered[min(int(fraction * len(ordered)), len(ordered) - 1)])

    return {
        "n": len(counts),
        "mean": round(statistics.mean(counts), 4),
        "sd": round(statistics.pstdev(counts), 4),
        "min": min(counts),
        "p5": at(0.05),
        "p25": at(0.25),
        "median": statistics.median(counts),
        "p75": at(0.75),
        "p95": at(0.95),
        "max": max(counts),
        "histogram": {str(value): ordered.count(value) for value in sorted(set(ordered))},
    }


def budget(rows: list[dict]) -> dict:
    """What the mean picture has to spend, and the largest uniform floor that fits.

    `sum(COVERAGE)` over a set of swatches is *identically* the mean number of
    those swatches a picture expresses — the same double sum read down the
    columns instead of across the rows — so the ceiling below is arithmetic and
    not a model. A uniform floor `f` over `k` swatches asks for `f * k` expressed
    colours from the average picture; the pool supplies `mean`; so no `f` above
    `mean / k` can exist however curation is steered.
    """
    achromatic = set(neutrals())
    names = codebook.names()
    chromatic = [name for name in names if name not in achromatic]
    table = coverage(rows)
    whole = sum(table.values())
    colour = sum(table[name] for name in chromatic)
    return {
        "all": {
            "swatches": len(names),
            "sum_coverage": round(whole, 4),
            "distribution": distribution(expressed_counts(rows, names)),
            "implied_ceiling": round(whole / len(names), 4),
        },
        "non_neutral": {
            "swatches": len(chromatic),
            "sum_coverage": round(colour, 4),
            "distribution": distribution(expressed_counts(rows, chromatic)),
            "implied_ceiling": round(colour / len(chromatic), 4),
        },
        "neutrals": sorted(achromatic),
        "identity": (
            "sum(COVERAGE) over a set of swatches IS the mean number of them a picture "
            "expresses above the threshold; the ceiling is that mean divided by the count, "
            "and it bounds every uniform floor there could be"
        ),
    }


def agreement(rows: list[dict]) -> dict:
    """What the cheap instruments cost, against the shipped render at full resolution.

    Two of them, and they are different sizes of wrong. The 160x90 census decode
    of the same PNG is a sampling question and the answer is small. The candidate
    render is a *different picture* — half the supersampling at a sixteenth of the
    area, levelled off its own histogram — and the answer is not small, which is
    why the screen this module runs at candidate geometry is a screen and never a
    measurement.
    """
    import statistics

    names = codebook.names()

    def compare(left: str, right: str) -> dict:
        pairs = [row for row in rows if row.get(left) and row.get(right)]
        gaps = [
            max(abs((row[left]).get(name, 0.0) - (row[right]).get(name, 0.0)) for name in names)
            for row in pairs
        ]
        flips = sum(
            1
            for row in pairs
            for name in names
            if ((row[left]).get(name, 0.0) >= THRESHOLD)
            != ((row[right]).get(name, 0.0) >= THRESHOLD)
        )
        ordered = sorted(gaps)
        return {
            "pictures": len(pairs),
            "worst_swatch_move": round(max(gaps), 4) if gaps else 0.0,
            "p95_swatch_move": round(ordered[int(0.95 * (len(ordered) - 1))], 4) if gaps else 0.0,
            "median_swatch_move": round(statistics.median(gaps), 4) if gaps else 0.0,
            "pictures_moving_over_a_point": sum(1 for gap in gaps if gap > 0.01),
            "threshold_cells_flipped": flips,
            "threshold_cells": len(pairs) * len(names),
        }

    reached = [
        (row, name)
        for row in rows
        if row.get("candidate_shares")
        for name in names
        if row["shares"].get(name, 0.0) >= THRESHOLD
    ]
    screens = {}
    for height in (0.10, 0.09, 0.08, 0.07, 0.06, 0.05):
        missed = sum(1 for row, name in reached if row["candidate_shares"].get(name, 0.0) < height)
        screens[f"{height:.2f}"] = {"missed": missed, "of": len(reached)}
    return {
        "census_decode": compare("shares", "census_shares"),
        "candidate_geometry": compare("shares", "candidate_shares"),
        "screen_misses": screens,
        "screen": SCREEN,
    }


# --------------------------------------------------------------------------- #
# The readout.
# --------------------------------------------------------------------------- #
def take(log=print) -> dict:
    """Coverage, the budget, and what the cheap instruments cost."""
    from datetime import UTC, datetime

    rows = _read_jsonl(pictures_path())
    table = coverage(rows)
    document = {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "threshold": THRESHOLD,
        "population": {
            "pictures": len(rows),
            "runs": {
                run: sum(1 for row in rows if row["run"] == run)
                for run in sorted({row["run"] for row in rows})
            },
            "collections": {
                name: sum(1 for row in rows if row["collection"] == name)
                for name in sorted({str(row["collection"]) for row in rows})
            },
            "kinds": {
                kind: sum(1 for row in rows if row["kind"] == kind)
                for kind in sorted({row["kind"] for row in rows})
            },
            "mode_kinds": {
                kind: sum(1 for row in rows if row["mode_kind"] == kind)
                for kind in sorted({row["mode_kind"] for row in rows})
            },
            "rejected_afterwards": sum(1 for row in rows if row["rejected"]),
            "resolutions": sorted({tuple(row["resolution"]) for row in rows}),
            "rule": (
                "every release row whose verdict is `released` and whose full-size picture "
                "is on disk, over every pass on record. A row taken back afterwards is kept: "
                "this is a question about colour and not about seating"
            ),
        },
        "coverage": {name: round(value, 6) for name, value in table.items()},
        "ranked": sorted(table, key=lambda name: (table[name], name)),
        "budget": budget(rows),
        "agreement": agreement(rows),
    }
    _write_json(readout_path(), document)
    log(
        f"[expressed] {len(rows)} finished wallpapers, mean "
        f"{document['budget']['all']['distribution']['mean']} swatches expressed "
        f"({document['budget']['non_neutral']['distribution']['mean']} non-neutral)"
    )
    return document


def readout() -> dict:
    """The readout as it was last taken.

    No guard over it any more and deliberately none: nothing downstream acts on
    this document, so a stale one is a stale reading rather than a stale policy.
    Its own `taken_at` and `population` say what it covers.
    """
    path = readout_path()
    if not path.is_file():
        raise ExpressedError(f"{path} is missing — take the reading before reading it")
    return json.loads(path.read_text(encoding="utf-8"))


__all__ = [
    "CANDIDATE_RESOLUTION",
    "CANDIDATE_SUPERSAMPLE",
    "SCHEMA",
    "SCREEN",
    "THRESHOLD",
    "ExpressedError",
    "agreement",
    "budget",
    "census",
    "coverage",
    "distribution",
    "expressed_counts",
    "expressed_dir",
    "finished",
    "full_shares",
    "neutrals",
    "pictures_path",
    "readout",
    "readout_path",
    "take",
]
