"""`judges`: hand the four shipped judges a picture or a place, and check they still agree.

`score` reads any picture files through the render, gallery and palette judges and
any location records through the location judge, prints a table, and can write
JSON and a page. `check` renders a tracked handful of recipes — text only, since a
render is byte-identical across installs — scores them with all four judges, and
fails on any score off its expected value by more than the stated tolerance. It is
the one-command answer to *did my install load the same judges the project ships*.
[`models.judges`] is the door both read through.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fractal_wallpapers.cli.common import device_flag, display_path, resolve_output

#: How far a check score may sit from its expected value and still pass. The
#: fresh-install audit of 2026-10-04 measured CPU against CUDA on the same pictures
#: at under 7e-6 for every head; this leaves an order of magnitude for a torch
#: version, a BLAS and the fp16 weights' rounding to differ in.
TOLERANCE = 1e-4


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


def judges_check(args: argparse.Namespace) -> int:
    """Render the tracked check cases, score them with all four judges, compare."""
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
    for case in cases:
        recipe = recipes.of_record(case["recipe"])
        if recipes.key_of(recipe) != case["key"]:
            print(
                f"check case {case['name']}: its recipe computes to {recipes.key_of(recipe)} and "
                f"the file says {case['key']}. The engine or the recipe schema moved."
            )
            return 1
        try:
            picture, _stamp = draw_recipe(recipe, pictures_dir / f"{case['name']}.jpg")
        except recipes.RecipeError as refusal:
            print(f"check case {case['name']}: {refusal}")
            return 1
        pictures.append(Path(picture))
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
    read, loading["location"] = judges.score_places(places, args.device, log=lambda line: None)
    for row, reading in zip(actual, read, strict=True):
        row["location"] = {"p_ge3": reading["p_ge3"], "p_ge4": reading["p_ge4"]}
    if args.write_expected:
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for case, row in zip(cases, actual, strict=True):
                handle.write(json.dumps({**case, "expected": row}, ensure_ascii=False) + "\n")
        print(f"{display_path(path)}: expected scores rewritten from this reading")
        return 0
    misses = []
    worst = 0.0
    results = []
    for case, row in zip(cases, actual, strict=True):
        off = {}
        for judge, block in case["expected"].items():
            for column, expected in block.items():
                got = (row.get(judge) or {}).get(column)
                gap = float("inf") if got is None else abs(float(got) - float(expected))
                worst = max(worst, gap)
                if gap > TOLERANCE:
                    off[f"{judge}.{column}"] = {"expected": expected, "actual": got}
        if off:
            misses.append(case["name"])
        results.append({"name": case["name"], "key": case["key"], "actual": row, "missed": off})
    report = {
        "schema": 1,
        "tolerance": TOLERANCE,
        "cases": len(cases),
        "missed": misses,
        "largest_gap": worst,
        "load_seconds": loading,
        "results": results,
    }
    (directory / "check.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    tiles = []
    for case, row, picture in zip(cases, actual, pictures, strict=True):
        caption = []
        for judge, block in case["expected"].items():
            for column, expected in block.items():
                got = (row.get(judge) or {}).get(column)
                caption.append((f"{judge} {column}", f"{float(expected):.5f} → {_shown(got)}"))
        tiles.append(
            grid_page.Tile(
                picture=picture,
                title=f"{case['name']} · {case['recipe']['mode']}",
                caption=caption,
                mark="MISS" if case["name"] in misses else "",
            )
        )
    page = grid_page.write(
        directory / "index.html",
        "Judge check",
        [
            f"{len(cases)} tracked recipes rendered here and scored by all four judges; each "
            f"line reads expected → actual. Tolerance {TOLERANCE:g}; largest gap {worst:.2g}.",
            "PASS" if not misses else f"MISSED: {', '.join(misses)}",
        ],
        [grid_page.Section("Cases", tiles=tiles)],
    )
    print(f"{len(cases)} case(s), largest gap {worst:.2g} against a tolerance of {TOLERANCE:g}")
    print(f"model load seconds: {loading}")
    print(display_path(page))
    if misses:
        print(f"MISSED: {', '.join(misses)}")
        return 1
    print("PASS")
    return 0


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
        help="render the tracked check recipes, score them with all four judges, compare",
        description=(
            f"Reads data/judges/check.jsonl — recipes and expected scores, text only — renders "
            f"each at its own regime, scores it with the render, gallery and palette judges "
            f"and its place with the location judge, and exits non-zero if any score is more "
            f"than {TOLERANCE:g} from its expected value. Writes check.json and a page showing "
            f"each picture beside expected and actual scores (default artifacts/judges/check/)."
        ),
    )
    checking.add_argument("--out-dir", metavar="DIR", help="where the pictures and page go")
    checking.add_argument(
        "--write-expected",
        action="store_true",
        help="rewrite the tracked expected scores from this reading. For a maintainer after a "
        "deliberate change to a judge or the engine, never to make a miss pass",
    )
    device_flag(checking)
    group.set_defaults(handler=judges)


def judges(args: argparse.Namespace) -> int:
    """`judges score` or `judges check`."""
    return judges_score(args) if args.what == "score" else judges_check(args)
