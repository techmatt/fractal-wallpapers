"""`judges`: hand the four shipped judges a picture or a place, and check they still agree.

`score` reads any picture files through the render, gallery and palette judges and
any location records through the location judge, prints a table, and can write
JSON and a page. `check` is the install check: it renders a tracked handful of
recipes and holds each to two halves, **the picture matches** (its cell-mean print
against a tracked text reference, within `PICTURE_TOLERANCE`, since the engine
promises the same picture and not the same bytes across machines) and **the scores
match** (all four judges within `TOLERANCE`). It times each render beside a tracked
reference time from `REFERENCE_BOX`, so a reader can calibrate their machine. It is
the one-command answer to *does my install draw and judge what the project ships*.
[`models.judges`] is the door both read through.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fractal_wallpapers.cli.common import (
    bundle_flag,
    device_flag,
    display_path,
    resolve_output,
)

#: How far a check score may sit from its expected value and still pass. The
#: fresh-install audit of 2026-10-04 measured CPU against CUDA on the same pictures
#: at under 7e-6 for every head; this leaves an order of magnitude for a torch
#: version, a BLAS and the fp16 weights' rounding to differ in.
TOLERANCE = 1e-4

#: The cells a check picture is printed into, columns by rows: 20x20 pixels each at
#: the check's 640x360.
GRID = (32, 18)

#: How far a cell's mean colour may sit from the reference, in levels of 255 per
#: channel. The engine draws the same picture everywhere but promises no byte
#: identity across machines (a platform's libm may round an orbit differently and
#: flip a pixel on a boundary). One flipped pixel moves its cell's mean by at most
#: 0.64 of a level and the JPEG round trip by well under one, so four levels lets a
#: few boundary pixels a cell differ and still catches any change to the family,
#: the view, the palette or the levelling band, each of which moves cells by tens.
PICTURE_TOLERANCE = 4.0

#: The machine the tracked reference seconds were measured on, stated once.
REFERENCE_BOX = "Intel i5-10400F, Windows 10, release engine, one render at a time"


def check_path() -> Path:
    """The tracked check cases. **The one accessor.**"""
    from fractal_wallpapers.paths import repo_root

    return repo_root() / "data" / "judges" / "check.jsonl"


def _out_dir(args: argparse.Namespace, leaf: str) -> Path:
    from fractal_wallpapers.paths import under

    return resolve_output(args.out_dir) if args.out_dir else under("judges", leaf)


def _pictures_of(args: argparse.Namespace) -> list[Path]:
    pictures = [Path(text) for text in args.pictures or ()]
    if args.manifest:
        text = resolve_output(args.manifest).read_text(encoding="utf-8")
        pictures += [Path(line.strip()) for line in text.splitlines() if line.strip()]
    return [resolve_output(picture) for picture in pictures]


def judges_score(args: argparse.Namespace) -> int:
    """Score picture files, and location records, with the shipped judges."""
    from fractal_wallpapers import grid_page, locations
    from fractal_wallpapers.models import judges

    pictures = _pictures_of(args)
    missing = [picture for picture in pictures if not picture.is_file()]
    if missing:
        print(f"{len(missing)} picture(s) are not there, the first {display_path(missing[0])}.")
        return 1
    places = locations.read(resolve_output(args.location)) if args.location else []
    if not pictures and not places:
        print("name at least one picture, a --manifest of pictures, or a --location file.")
        return 1
    wanted = args.judge or list(judges.JUDGES)
    rows = [{"picture": display_path(picture)} for picture in pictures]
    loading = {}
    for name in (judge for judge in wanted if judge in judges.PICTURE_JUDGES):
        if not pictures:
            continue
        try:
            loaded = judges.load(name, args.device)
        except FileNotFoundError as refusal:
            print(refusal)
            return 1
        loading[name] = round(loaded.seconds, 2)
        for row, read in zip(rows, judges.score_pictures(loaded, pictures), strict=True):
            row[name] = read
    place_rows = []
    if places and "location" in wanted:
        try:
            read, seconds = judges.score_places(places, args.device, log=lambda line: None)
        except FileNotFoundError as refusal:
            print(refusal)
            return 1
        loading["location"] = round(seconds, 2)
        for number, (place, reading) in enumerate(zip(places, read, strict=True)):
            place_rows.append({"place": number, "family": place["family"], "location": reading})

    def number(value) -> str:
        return "—" if value is None else f"{float(value):.4f}"

    if rows:
        print(f"{'picture':<44} {'render P>=4':>11} {'gallery P>=4':>12} {'palette':>8}")
        for row in rows:
            print(
                f"{row['picture'][-44:]:<44} "
                f"{number((row.get('render') or {}).get('p_ge4')):>11} "
                f"{number((row.get('gallery_grade') or {}).get('p_ge4')):>12} "
                f"{number((row.get('palette') or {}).get('score')):>8}"
            )
    for row in place_rows:
        reading = row["location"]
        print(
            f"place {row['place']} {row['family'].get('kind')}: location P>=3 "
            f"{number(reading['p_ge3'])}, P>=4 {number(reading['p_ge4'])}"
            + (f" ({reading['error']})" if reading["error"] else "")
        )
    print(f"model load seconds: {loading}")
    report = {"schema": 1, "pictures": rows, "places": place_rows, "load_seconds": loading}
    if args.json:
        path = resolve_output(args.json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(display_path(path))
    if args.page:
        directory = _out_dir(args, "score")
        tiles = [
            grid_page.Tile(
                picture=picture,
                title=row["picture"],
                caption=[
                    ("render P(>=3)", (row.get("render") or {}).get("p_ge3")),
                    ("render P(>=4)", (row.get("render") or {}).get("p_ge4")),
                    ("gallery P(>=4)", (row.get("gallery_grade") or {}).get("p_ge4")),
                    ("palette", (row.get("palette") or {}).get("score")),
                ],
            )
            for picture, row in zip(pictures, rows, strict=True)
        ]
        tiles += [
            grid_page.Tile(
                picture=Path(row["location"]["view"]) if row["location"]["view"] else None,
                title=f"place {row['place']}",
                caption=[
                    ("location P(>=3)", row["location"]["p_ge3"]),
                    ("location P(>=4)", row["location"]["p_ge4"]),
                ],
            )
            for row in place_rows
        ]
        print(
            display_path(
                grid_page.write(
                    directory / "index.html",
                    "Judge scores",
                    [
                        "The render and gallery judges read the picture stretched to 384x224; "
                        "they were fit on 640x360 candidate pictures. The palette score is "
                        "comparable only between pictures of one place."
                    ],
                    [grid_page.Section("Scores", tiles=tiles)],
                )
            )
        )
    return 0


def picture_print(picture: Path) -> list[list[float]]:
    """A picture as `GRID` cells' mean colours: `[[r, g, b], ...]`, row by row, 0–255.

    The text a check case's picture is compared through. Cell means rather than
    pixels, because the engine promises the same picture and not the same bytes
    across machines: a libm that rounds one orbit differently flips a pixel or two
    on a boundary, which moves a cell's mean by a fraction of a level, while a
    wrong family, view, palette or band moves whole cells by tens.
    """
    import numpy as np
    from PIL import Image

    columns, rows = GRID
    with Image.open(picture) as image:
        pixels = np.asarray(image.convert("RGB"), dtype=np.float64)
    height, width, _ = pixels.shape
    cells = pixels[: height - height % rows, : width - width % columns]
    cells = cells.reshape(rows, cells.shape[0] // rows, columns, cells.shape[1] // columns, 3)
    means = cells.mean(axis=(1, 3)).reshape(-1, 3)
    return [[round(float(value), 1) for value in cell] for cell in means]


def picture_gap(expected: list, actual: list) -> float:
    """The largest per-channel gap between two prints' cells, in levels of 255."""
    if len(expected) != len(actual):
        return float("inf")
    return max(
        abs(float(a) - float(b))
        for cell, other in zip(expected, actual, strict=True)
        for a, b in zip(cell, other, strict=True)
    )


def judges_check(args: argparse.Namespace) -> int:
    """Render the tracked check cases, compare each picture and its four judges' scores."""
    import time

    from fractal_wallpapers import grid_page
    from fractal_wallpapers.cli.draw_commands import draw_recipe
    from fractal_wallpapers.curation import recipes
    from fractal_wallpapers.models import judges

    path = check_path()
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    directory = _out_dir(args, "check")
    pictures_dir = directory / "pictures"
    pictures_dir.mkdir(parents=True, exist_ok=True)
    pictures = []
    seconds = []
    for case in cases:
        recipe = recipes.of_record(case["recipe"])
        if recipes.key_of(recipe) != case["key"]:
            print(
                f"check case {case['name']}: its recipe computes to {recipes.key_of(recipe)} and "
                f"the file says {case['key']}. The engine or the recipe schema moved."
            )
            return 1
        started = time.perf_counter()
        try:
            picture, _stamp = draw_recipe(recipe, pictures_dir / f"{case['name']}.jpg")
        except recipes.RecipeError as refusal:
            print(f"check case {case['name']}: {refusal}")
            return 1
        seconds.append(round(time.perf_counter() - started, 2))
        pictures.append(Path(picture))
    prints = [picture_print(picture) for picture in pictures]
    actual: list[dict] = [{} for _ in cases]
    loading = {}
    for name in judges.PICTURE_JUDGES:
        try:
            loaded = judges.load(name, args.device)
        except FileNotFoundError as refusal:
            print(refusal)
            return 1
        loading[name] = round(loaded.seconds, 2)
        for row, read in zip(actual, judges.score_pictures(loaded, pictures), strict=True):
            row[name] = read
    places = [
        {
            "family": case["recipe"]["family"],
            "viewport": case["recipe"]["viewport"],
            "maxiter": case["recipe"]["maxiter"],
        }
        for case in cases
    ]
    read, took = judges.score_places(places, args.device, log=lambda line: None)
    loading["location"] = round(took, 2)
    for row, reading in zip(actual, read, strict=True):
        row["location"] = {"p_ge3": reading["p_ge3"], "p_ge4": reading["p_ge4"]}
    if args.write_expected:
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for case, row, cells, took in zip(cases, actual, prints, seconds, strict=True):
                written = {
                    **case,
                    "expected": row,
                    "picture": {"grid": list(GRID), "cells": cells},
                    "reference_seconds": took,
                }
                handle.write(json.dumps(written, ensure_ascii=False) + "\n")
        print(
            f"{display_path(path)}: expected scores, picture prints and reference seconds "
            f"rewritten from this reading. The seconds are this machine's: say which in "
            f"judges_commands.REFERENCE_BOX."
        )
        return 0
    misses = []
    worst = 0.0
    worst_picture = 0.0
    results = []
    for case, row, cells, took in zip(cases, actual, prints, seconds, strict=True):
        off = {}
        for judge, block in case["expected"].items():
            for column, expected in block.items():
                got = (row.get(judge) or {}).get(column)
                gap = float("inf") if got is None else abs(float(got) - float(expected))
                worst = max(worst, gap)
                if gap > TOLERANCE:
                    off[f"{judge}.{column}"] = {"expected": expected, "actual": got}
        reference = case.get("picture") or {}
        picture_off = (
            picture_gap(reference["cells"], cells)
            if reference.get("grid") == list(GRID)
            else float("inf")
        )
        worst_picture = max(worst_picture, picture_off)
        picture_ok = picture_off <= PICTURE_TOLERANCE
        if off or not picture_ok:
            misses.append(case["name"])
        results.append(
            {
                "name": case["name"],
                "key": case["key"],
                "picture_matches": picture_ok,
                "picture_gap": picture_off,
                "scores_match": not off,
                "seconds": took,
                "reference_seconds": case.get("reference_seconds"),
                "actual": row,
                "missed": off,
            }
        )
    report = {
        "schema": 2,
        "tolerance": TOLERANCE,
        "picture_tolerance": PICTURE_TOLERANCE,
        "picture_grid": list(GRID),
        "reference_box": REFERENCE_BOX,
        "cases": len(cases),
        "missed": misses,
        "largest_gap": worst,
        "largest_picture_gap": worst_picture,
        "load_seconds": loading,
        "results": results,
    }
    (directory / "check.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    def yes(value: bool) -> str:
        return "match" if value else "MISS"

    def took_beside(result: dict) -> str:
        reference = result["reference_seconds"]
        return f"{result['seconds']:.2f} · " + ("—" if reference is None else f"{reference:.2f}")

    columns = ["case", "picture", "scores", "render s (yours · reference)"]
    table = [columns] + [
        [
            result["name"],
            yes(result["picture_matches"]),
            yes(result["scores_match"]),
            took_beside(result),
        ]
        for result in results
    ]
    tiles = []
    labels: list[str] = []
    for case, row, picture, result in zip(cases, actual, pictures, results, strict=True):
        caption = [
            ("picture", f"{yes(result['picture_matches'])} (gap {result['picture_gap']:.2g})"),
            ("render s (yours · reference)", took_beside(result)),
        ]
        for judge, block in case["expected"].items():
            for column, expected in block.items():
                got = (row.get(judge) or {}).get(column)
                label = f"{JUDGE_NAMES[judge]} {_column_name(column)}"
                labels.append(label)
                caption.append((label, f"{float(expected):.5f} → {_shown(got)}"))
        tiles.append(
            grid_page.Tile(
                picture=picture,
                title=f"{case['name']} · {case['recipe']['mode']}",
                caption=caption,
                mark="MISS" if case["name"] in misses else "",
            )
        )
    said = {
        "case": "a tracked recipe the check renders and scores",
        "picture": f"whether your render matches the tracked reference picture: every one of "
        f"its {GRID[0]}x{GRID[1]} cells' mean colour within {PICTURE_TOLERANCE:g} of 255",
        "scores": f"whether all four judges' scores are within {TOLERANCE:g} of the expected ones",
        "render s (yours · reference)": f"seconds your machine took to render the picture, "
        f"beside the same render on the reference box ({REFERENCE_BOX})",
    }
    said |= {label: _caption_meaning(label) for label in labels}
    page = grid_page.write(
        directory / "index.html",
        "Judge check",
        [
            f"{len(cases)} tracked recipes rendered here, each picture compared with its tracked "
            f"reference and scored by all four judges. Largest picture gap {worst_picture:.2g} "
            f"(tolerance {PICTURE_TOLERANCE:g}); largest score gap {worst:.2g} (tolerance "
            f"{TOLERANCE:g}). Reference times are from {REFERENCE_BOX}.",
            "PASS" if not misses else f"MISSED: {', '.join(misses)}",
        ],
        [
            grid_page.Section(
                "Each case", table=table, legend=grid_page.legend(*columns, said=said)
            ),
            grid_page.Section(
                "Cases",
                note="each judge line reads expected → yours",
                tiles=tiles,
                legend=grid_page.legend(
                    "picture",
                    "render s (yours · reference)",
                    *dict.fromkeys(labels),
                    said=said,
                ),
            ),
        ],
        bundle=resolve_output(args.bundle) if args.bundle else None,
    )
    print(f"{'case':<30} {'picture':>7} {'scores':>7} {'render s':>9} {'reference':>9}")
    for result in results:
        reference = result["reference_seconds"]
        print(
            f"{result['name']:<30} {yes(result['picture_matches']):>7} "
            f"{yes(result['scores_match']):>7} {result['seconds']:>9.2f} "
            f"{'—' if reference is None else f'{reference:.2f}':>9}"
        )
    print(f"reference times: {REFERENCE_BOX}")
    print(
        f"largest picture gap {worst_picture:.2g} against {PICTURE_TOLERANCE:g}; "
        f"largest score gap {worst:.2g} against {TOLERANCE:g}"
    )
    print(f"model load seconds: {loading}")
    print(display_path(page))
    if args.bundle:
        from fractal_wallpapers import bundle

        print(bundle.said(resolve_output(args.bundle)))
    if misses:
        print(f"MISSED: {', '.join(misses)}")
        return 1
    print("PASS")
    return 0


#: The judges as a reader knows them.
JUDGE_NAMES = {
    "render": "wallpaper judge",
    "gallery_grade": "gallery judge",
    "palette": "palette judge",
    "location": "location judge",
}


def _column_name(column: str) -> str:
    return f"P(>={column[-1]})" if column.startswith("p_ge") else column


def _caption_meaning(label: str) -> str:
    """One legend line for a check tile's `<judge> <column>` caption."""
    judge, _, column = label.rpartition(" ")
    if column == "score":
        return (
            f"the {judge}'s fit of this palette to this place, expected → yours; comparable "
            f"only between palettes of one place"
        )
    level = column[len("P(>=") : -1]
    reads = "place" if judge == "location judge" else "picture"
    return (
        f"the {judge}'s probability that the {reads} rates at least {level} of 5, expected → yours"
    )


def _shown(value) -> str:
    return "—" if value is None else f"{float(value):.5f}"


def add_commands(subcommands) -> None:
    """Register `judges` and its two verbs."""
    group = subcommands.add_parser(
        "judges",
        help="score any picture or place with the shipped judges, or check they still agree",
        description=(
            "The four judges a gallery is chosen by, as a reader calls them. `score` reads "
            "picture files with the render, gallery and palette judges and location records "
            "with the location judge. `check` renders a tracked handful of recipes and "
            "compares all four judges' scores with the expected ones, so a fresh install "
            "proves it loaded the weights the project ships. Both need `fetch-weights` and "
            "the `models` (or `cuda`) extra."
        ),
    )
    verbs = group.add_subparsers(dest="what", required=True)
    scoring = verbs.add_parser(
        "score",
        help="score picture files and location records; a table, and optionally JSON and a page",
        description=(
            "GEOMETRY: the render and gallery judges were fit on 640x360 candidate pictures "
            "(rendered at 2x supersample) and read any picture stretched to 384x224 with no "
            "crop, so a 16:9 picture is the kind whose score means what a gallery's does. The "
            "palette judge reads a picture squashed to 224x224 and returns one score that is "
            "comparable only between pictures of the same place in different palettes. The "
            "location judge reads a PLACE, not your picture: it renders the place's own "
            "640x360ss2 smooth view."
        ),
    )
    scoring.add_argument("pictures", nargs="*", metavar="PICTURE", help="a picture file")
    scoring.add_argument(
        "--manifest", metavar="FILE", help="a text file of picture paths, one a line"
    )
    scoring.add_argument(
        "--location",
        metavar="FILE",
        help="a JSONL of location records ({family, viewport, render}) for the location judge",
    )
    scoring.add_argument(
        "--judge",
        action="append",
        choices=["render", "gallery_grade", "palette", "location"],
        help="only this judge (repeatable; default all four)",
    )
    scoring.add_argument("--json", metavar="PATH", help="also write the scores as JSON here")
    scoring.add_argument(
        "--page", action="store_true", help="also write a page (default artifacts/judges/score/)"
    )
    scoring.add_argument("--out-dir", metavar="DIR", help="where --page writes")
    device_flag(scoring)
    checking = verbs.add_parser(
        "check",
        help="the install check: render the tracked recipes, compare each picture and its scores",
        description=(
            f"Reads data/judges/check.jsonl — recipes, reference pictures as text, expected "
            f"scores and reference render seconds — renders each at its own regime, and holds "
            f"it to two halves: the picture matches (every one of its {GRID[0]}x{GRID[1]} "
            f"cells' mean colour within {PICTURE_TOLERANCE:g} of 255 of the reference) and the "
            f"scores match (the render, gallery and palette judges on the picture and the "
            f"location judge on its place, each within {TOLERANCE:g}). Exits non-zero if either "
            f"half misses. Each render is timed and shown beside the reference time from "
            f"{REFERENCE_BOX}. Writes check.json and a page (default artifacts/judges/check/)."
        ),
    )
    checking.add_argument("--out-dir", metavar="DIR", help="where the pictures and page go")
    checking.add_argument(
        "--write-expected",
        action="store_true",
        help="rewrite the tracked expected scores, picture prints and reference seconds from "
        "this reading. For a maintainer on the reference box after a "
        "deliberate change to a judge or the engine, never to make a miss pass",
    )
    bundle_flag(checking)
    device_flag(checking)
    group.set_defaults(handler=judges)


def judges(args: argparse.Namespace) -> int:
    """`judges score` or `judges check`."""
    return judges_score(args) if args.what == "score" else judges_check(args)
