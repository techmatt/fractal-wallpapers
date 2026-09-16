"""`curate`'s colour verbs: the census, the coverage, and what to make next.

`colors` counts what the pool holds per colormap and per cell, `coverage` reads
the same census as a question about what is MISSING, `manufacture` turns an
answer to that into a render batch, and `autolevel` says which seats can replay
the levelling they were drawn under and re-derives a curve for the ones that
cannot. The four are one module because each reads
[`curation/colors.py`]'s census and the first three are the same numbers asked
three ways.

Cut out of `curate_commands` on 2026-09-12 with four sibling families; that
module's docstring carries the reversal and what it cost.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fractal_wallpapers.cli.common import (
    device_flag,
    display_path,
    resolve_output,
)
from fractal_wallpapers.curation import backfill as backfill_module
from fractal_wallpapers.curation import manufacture as manufacture_module
from fractal_wallpapers.paths import repo_root


def curate_autolevel(args: argparse.Namespace) -> int:
    """What a seat can replay of its levelling, and a curve for the seats that cannot."""
    from fractal_wallpapers.curation import backfill

    doing = {
        "survey": lambda: backfill.survey(args.record, atlas=args.atlas),
        "backfill": lambda: backfill.sweep(args.record, limit=args.limit, atlas=args.atlas),
    }[args.what]
    try:
        report = doing()
    except (backfill.BackfillError, OSError) as refusal:
        print(refusal)
        return 1
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(f"{out}")
        return 0
    print(json.dumps(report, indent=2))
    return 0


def curate_colors(args: argparse.Namespace) -> int:
    """Take the colour census, and optionally draw the sheets a person rules from."""
    from fractal_wallpapers.curation import color_sheets, colors, swatch_frequency

    stages = tuple(args.stage) if args.stage else colors.STAGES
    if args.sheets and "survival" not in stages:
        print(
            "the sheets are drawn from the candidate renders, so they need the survival "
            "stage. Add --stage survival, or drop --sheets."
        )
        return 1
    try:
        readout = colors.take(stages=stages)
    except colors.CensusError as refusal:
        print(refusal)
        return 1

    for name in stages:
        table = readout["stages"][name]
        print(f"\n=== {name}")
        if name == "library":
            missing = [
                swatch
                for swatch, cell in table["metrics"]["swatches"].items()
                if cell["at_10pct"] == 0
            ]
            print(f"  {table['maps']} maps ({table['in_pool']} in the pool)")
            print(f"  swatches no map carries at 10%: {missing or 'none'}")
        elif name == "picks":
            ranked = sorted(
                table["swatches"].items(),
                key=lambda item: (item[1]["selection_ratio"] is None, item[1]["selection_ratio"]),
            )
            print(f"  {table['sets']} candidate sets")
            for swatch, cell in ranked[:5]:
                print(
                    f"  least picked  {swatch:<26} offered {cell['offered']:>6} "
                    f"picked {cell['picked']:>5}  x{cell['selection_ratio']}"
                )
        elif name == "survival":
            print(f"  {table['pool']['renders']} candidate renders (score-free)")
            for head, cell in table["floor_referenced"].items():
                print(
                    f"  {head:<15} n={cell['n']:>4} floor={cell['floor']} clears={cell['clears']}"
                )
        elif name == "labels":
            for head, cell in table.items():
                keepers = cell["keepers"]
                print(
                    f"  {head:<15} {cell['pictures']} judged, {keepers['n']} at 3 or 4, "
                    f"{len(keepers['unrepresented_swatches'])} swatches with no keeper"
                )

    print(f"\ncensus  {display_path(colors.readout_path())}")
    print(f"rows    {display_path(colors.rows_path())}")
    print(f"manifest {display_path(colors.manifest_path())}")

    if args.sheets:
        rows = [
            json.loads(line)
            for line in colors.rows_path().read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        written = color_sheets.write(rows, repo_root() / "scratch")
        print(f"sheets  {display_path(Path(written['by_swatch']))}")
        print(f"        {display_path(Path(written['sparse']))}")

    if args.frequency:
        try:
            table = swatch_frequency.write(readout, repo_root() / "scratch")
        except swatch_frequency.SheetError as refusal:
            print(refusal)
            return 1
        print()
        print(f"frequency {display_path(Path(table['csv']))}")
        print(f"          {display_path(Path(table['page']))}")
        print(f"  {table['swatches']} swatches over {table['renders']} judged renders")
        print(f"  most common: {', '.join(f'{n} ({c})' for n, c in table['top'])}")
        print(f"  never dominant: {len(table['zero_dominance'])}")
        print(f"  carried by no map at 10%: {len(table['uncarried'])}")
    return 0


def curate_coverage(args: argparse.Namespace) -> int:
    """Coverage on pixels: how many maps can put each swatch on a real share of a picture."""
    from fractal_wallpapers.curation import palette_coverage as coverage

    try:
        if args.step_of_coverage in ("panel", "all"):
            coverage.build_panel()
        if args.step_of_coverage in ("probe", "all"):
            coverage.probe(workers=args.workers)
        if args.step_of_coverage in ("read", "all"):
            readout = coverage.take()
        else:
            return 0
    except coverage.CoverageError as refusal:
        print(refusal)
        return 1

    thin = coverage.thinnest(readout)
    table = readout["capability"]
    print(f"\npanel   {len(readout['panel']['cells'])} cells, {readout['panel']['modes']}")
    print(
        f"maps    {table['all']['maps']} ({table['prior']['maps']} pre-existing, "
        f"{table['drop']['maps']} in the drop)"
    )
    print(f"thinnest at 10%: {', '.join(thin)}")
    for swatch in thin:
        cells = table["all"]["swatches"][swatch]
        prior = table["prior"]["swatches"][swatch]
        print(
            f"  {swatch:<26} "
            + "  ".join(
                f"{int(t * 100):>2}%: {cells[f'at_{int(t * 100)}pct']:>3}"
                f"({prior[f'at_{int(t * 100)}pct']:>3})"
                for t in coverage.THRESHOLDS
            )
        )
    print(f"false capabilities (fold off only): {len(readout['false_capabilities'])}")
    print(
        f"realized: {readout['realized']['maps']} maps over "
        f"{readout['realized']['renders']} pool renders"
    )
    print(f"\ncoverage {display_path(coverage.readout_path())}")
    print(f"rows     {display_path(coverage.rows_path())}")

    if args.sheet or args.by_swatch:
        rows = coverage.read_rows()
        where = repo_root() / "scratch" / "palette_coverage"
        if args.sheet:
            print(f"sheet    {display_path(coverage.contact_sheet(readout, rows, where))}")
        if args.by_swatch:
            print(f"by-swatch {display_path(coverage.by_swatch_sheet(readout, rows, where))}")
    return 0


def curate_manufacture(args: argparse.Namespace) -> int:
    """Force the rare swatches onto good places, measure what landed, and cut the sheets."""
    from fractal_wallpapers.curation import manufacture

    steps = ("register", "plan", "screen", "confirm", "select", "read")
    wanted = steps if args.step_of_manufacture == "all" else (args.step_of_manufacture,)
    try:
        if "register" in wanted:
            for line in manufacture.register(write=args.write):
                print(line)
            if wanted == ("register",):
                return 0
        if "plan" in wanted:
            manufacture.build_plan(
                oversample=args.oversample,
                rows_per_kind=args.rows_per_kind,
                seed=args.seed,
                batch=args.batch,
            )
        if "screen" in wanted:
            manufacture.screen(workers=args.workers, device=args.device, batch=args.batch)
        if "confirm" in wanted:
            manufacture.confirm(workers=args.workers, device=args.device, batch=args.batch)
        if "select" in wanted:
            manufacture.select(rows_per_kind=args.rows_per_kind, batch=args.batch)
        if args.step_of_manufacture == "top-up":
            manufacture.top_up(oversample=args.oversample, batch=args.batch)
            return 0
        if args.step_of_manufacture == "knobs":
            probe = manufacture.probe_knobs(sample=args.knob_sample, batch=args.batch)
            print(json.dumps(probe, indent=2))
            return 0
        if args.step_of_manufacture == "verify":
            if not args.sheet:
                print("--step verify needs --sheet, the built sheet to check")
                return 1
            held = manufacture.verify(resolve_output(args.sheet), args.batch)
            print(json.dumps(held, indent=2))
            return 0 if held["held"] else 1
        if "read" not in wanted:
            return 0
        readout = manufacture.read(args.batch)
    except manufacture.ManufactureError as refusal:
        print(refusal)
        return 1

    spent = readout["yield"]
    print(
        f"\n{spent['attempts']} attempts over {spent['locations']} locations -> "
        f"{spent['attempts_past_screen']} past the screen -> {spent['confirmed']} confirmed -> "
        f"{spent['served']} served "
        f"({spent['lost_to_colour']} lost to colour, {spent['lost_to_tier']} to the tier cut)"
    )
    selection = readout["selection"]
    for kind, rows in sorted(selection["rows"].items()):
        print(f"{kind:<16} {rows} rows")
    if selection["shortfall"]:
        print(f"short in {len(selection['shortfall'])} cell(s): {selection['shortfall']}")
    spread = selection["rows_per_map"]
    print(
        f"maps {spread['maps_used']} carrying at most {spread['cap']} rows each, "
        f"{spread['distribution']}; tiers {selection['tiers']}; arms {selection['arms']}"
    )

    print("\nper target swatch: locations that reached 10%, worst first")
    for swatch, cell in readout["hit_rate"].items():
        flag = "  DEFECT?" if cell["probable_defect"] else ""
        print(
            f"  {swatch:<24} {cell['reached']:>3}/{cell['locations']:<3} "
            f"{cell['rate']:.2f}  best {cell['best_share']:.3f}{flag}"
        )
    moved = readout["drift"]
    if moved["rows"]:
        print(
            f"\ncandidate -> sheet geometry over {moved['rows']} rows: share moves a median "
            f"{moved['share_median']:.4f}, p95 {moved['share_p95']:.4f}, worst "
            f"{moved['share_worst']:.4f}; {moved['crossed_the_threshold']} cross 10%; "
            f"tier {moved['tier']}"
        )
    print(f"\nplan      {display_path(manufacture.plan_path(args.batch))}")
    for kind in sorted(selection["rows"]):
        print(f"sheet plan {display_path(manufacture.sheet_plan_path(kind, args.batch))}")
    print(f"record    {display_path(manufacture.record_dir(args.batch))}")
    return 0


def add_steps(steps) -> None:
    """The colour verbs: the census, the coverage, and what to make next."""
    from fractal_wallpapers.curation import colors as colors_module
    from fractal_wallpapers.curation import release as release_module

    colouring_census = steps.add_parser(
        "colors",
        help="the colour census: what can be expressed, picked, kept and labelled",
        description=(
            "A standing record-and-rank over colour. It carries no cut and removes nothing: "
            "it describes the colour distribution at four stages so a bias claim can be "
            "checked against numbers. The stages exist to tell apart four situations that "
            "look identical from outside and have different fixes — a colour the library "
            "cannot express, one the palette head never picks, one that is picked and dies "
            "at a render floor, and one nobody has ever labelled. Counted through 52 "
            "swatches in Oklab; the codebook is written into the artifact so a share vector "
            "read next year is read under the codebook that produced it."
        ),
    )
    colouring_census.add_argument(
        "--stage",
        action="append",
        choices=list(colors_module.STAGES),
        help="run only this stage; repeatable. Omit for all four",
    )
    colouring_census.add_argument(
        "--sheets",
        action="store_true",
        help="also write the two glance sheets to scratch/ — the pool by dominant swatch, "
        "and the sparsest swatches drawn whole. Needs the survival stage",
    )
    colouring_census.add_argument(
        "--frequency",
        action="store_true",
        help="also write the swatch frequency sheet to scratch/ — all 52 swatches ordered by "
        "how often each dominates a judged render, as a csv and as a colour-filled page. "
        "Joins the library and survival stages, so it reads them off the merged artifact",
    )
    colouring_census.set_defaults(handler=curate_colors)

    covering = steps.add_parser(
        "coverage",
        help="coverage on pixels: how many maps can put each swatch on a real share of an image",
        description=(
            "The census counts a swatch's share of a colormap's ramp; this counts its share "
            "of an image's pixels, which is a different number. An escape-time field piles "
            "up at one end of its own stretch and production folds every non-cyclic map, so "
            "a map can carry a colour across a quarter of its gradient and put it almost "
            "nowhere. Two reads, side by side and never pooled: capability, a max over a "
            "fixed probe panel chosen for its field shapes; and realized supply, a count "
            "over the renders the pool already holds, which re-renders nothing. A map "
            "reaching a swatch only with the fold off is reported apart as a false "
            "capability, because production never colours that way."
        ),
    )
    covering.add_argument(
        "--step",
        dest="step_of_coverage",
        choices=["all", "panel", "probe", "read"],
        default="all",
        help="run one step only: draw and choose the panel, put every map through it, or "
        "read the tables off rows already written (default: all three)",
    )
    covering.add_argument(
        "--workers",
        type=int,
        default=release_module.DEFAULT_WORKERS,
        help=f"how many cells are probed at once (default {release_module.DEFAULT_WORKERS}, "
        "this machine's render pool). Every probe is a recolor through the engine, so this "
        "is the locked three and not a tuning knob",
    )
    covering.add_argument(
        "--sheet",
        action="store_true",
        help="also write the contact sheet to scratch/ — the weakest picture each threshold "
        "admits, for the swatches fewest maps can reach, so the bar is set by eye",
    )
    covering.add_argument(
        "--by-swatch",
        action="store_true",
        help="also write the by-swatch sheet to scratch/ — all 52, ordered by scarcity on "
        "pixels, each with its counts against the pre-existing library, a picture of every "
        "rung, and the maps reaching 20%% with the drop's members marked",
    )
    covering.set_defaults(handler=curate_coverage)

    manufacturing = steps.add_parser(
        "manufacture",
        help="force the rare swatches onto good places, and cut the correction sheets",
        description=(
            "Every other population here is found; this one is made. A location a person "
            "already scored a keeper is coloured through a map CHOSEN because the coverage "
            "read says it can reach a target swatch, in a mode drawn the way a run draws "
            "one, under the identity recipe production uses. A map's ramp does not predict "
            "what a picture holds, so the order is build, measure, then select: every "
            "attempt is screened at candidate geometry, the best one at each location is "
            "re-rendered at the sheet's own, and both cuts — a tenth of the pixels on the "
            "target, at least a 2 from the render judge — act on that second reading. The "
            "batch is model- and construction-conditioned and is registered train-side "
            "before a pixel is made; a tenth of its rows force the same swatches through "
            "maps the library already held, so a correction cannot be read as being about "
            "the drop when it is about the colour."
        ),
    )
    manufacturing.add_argument(
        "--step",
        dest="step_of_manufacture",
        choices=[
            "all",
            "register",
            "plan",
            "screen",
            "confirm",
            "select",
            "read",
            "top-up",
            "verify",
            "knobs",
        ],
        default="all",
        help="run one step only (default: all six, in order). Three are not among them: "
        "`top-up` extends the plan for the cells a selection came back short in, `verify` is "
        "taken against a sheet after it has been built, and `knobs` measures the "
        "counterfactual the diagnostic asks about",
    )
    manufacturing.add_argument(
        "--sheet",
        help="a built sheet, for --step verify: does it serve the picture the cuts were "
        "taken on, byte for byte, and does its own reading of the judge agree",
    )
    manufacturing.add_argument(
        "--batch",
        default=manufacture_module.BATCH,
        help=f"the batch this is (default: {manufacture_module.BATCH})",
    )
    manufacturing.add_argument(
        "--rows-per-kind",
        type=int,
        default=manufacture_module.ROWS_PER_KIND,
        help=f"rows on each kind's sheet (default: {manufacture_module.ROWS_PER_KIND})",
    )
    manufacturing.add_argument(
        "--oversample",
        type=float,
        default=4.0,
        help="how many locations a cell attempts per row it owes (default: 4). The yield is "
        "a property of this population and nothing measured elsewhere predicts it, so pilot "
        "it on a small plan before spending the night's build on a guess",
    )
    manufacturing.add_argument(
        "--seed", type=int, default=manufacture_module.SEED, help="the draw's seed"
    )
    manufacturing.add_argument(
        "--workers",
        type=int,
        default=release_module.DEFAULT_WORKERS,
        help=f"how many groups are built at once (default {release_module.DEFAULT_WORKERS}, "
        "this machine's render pool). A group is built by rendering, so this is the locked "
        "three and not a tuning knob",
    )
    device_flag(manufacturing)
    manufacturing.add_argument(
        "--knob-sample",
        type=int,
        default=120,
        help="how many missed attempts --step knobs re-colours through the knob grid "
        "(default: 120). Nothing in this project renders through those knobs; the sweep "
        "prices what a draw production does not make would have bought",
    )
    manufacturing.add_argument(
        "--write",
        action="store_true",
        help="the register step appends; otherwise it prints what it would register",
    )
    manufacturing.set_defaults(handler=curate_manufacture)

    levelling = steps.add_parser(
        "autolevel",
        help="the levelling curve a seat inherits, and the seats that have none to inherit",
        description=(
            "Levelling is decided once, at candidate geometry, and every larger render of "
            "that row replays the decision rather than measuring its own. A seat whose leg "
            "never wrote the curve down cannot replay it, so `backfill` re-derives one and "
            "records it in a sidecar the release path overlays. A re-derivation is not a "
            "recovery: the original base render is gone, the row says so, and where the "
            "seat's own levelled colormap survived on disk the two are compared."
        ),
    )
    levelling.set_defaults(handler=curate_autolevel)
    levelling_verbs = levelling.add_subparsers(dest="what", required=True)

    surveying = levelling_verbs.add_parser(
        "survey",
        help="what a record's seats can replay, and what filling the rest would cost",
        description=(
            "Read-only and renders nothing. Per record: the seats, how many already carry a "
            "whole stamp on some run record, how many take no operator at all, how many "
            "have no curve anywhere — and of those, how many still have the levelled "
            "colormap they shipped through, which is what a backfill can be checked "
            "against. Prices a store-wide sweep off the protected seats."
        ),
    )
    filling_curves = levelling_verbs.add_parser(
        "backfill",
        help="re-derive a curve for the seats that have none, and record it in the sidecar",
        description=(
            "Renders. Each seat is re-made at candidate geometry through the one door a "
            "candidate is ever made by, and the stamp that comes back is appended to "
            "artifacts/curation/autolevel_backfill.jsonl keyed by recipe key. Serial, one "
            "engine at below-normal priority. Nothing rewrites, deletes or re-keys an "
            "existing row, and no leg's sequence.jsonl is touched."
        ),
    )
    filling_curves.add_argument(
        "--limit", type=int, help="stop after this many seats (the whole record by default)"
    )
    for verb in (surveying, filling_curves):
        population = verb.add_mutually_exclusive_group()
        population.add_argument(
            "--atlas",
            metavar="PLANE",
            help="sweep the gallery slot of every dot in artifacts/atlas/<PLANE>/dots.json "
            "instead of a record's seats — the unseated dots stand behind a place's best row, "
            "which no record seats and so `--record` cannot reach",
        )
        population.add_argument(
            "--record",
            metavar="STAMP",
            default=backfill_module.DEFAULT_RECORD,
            help=f"the recorded gallery whose seats to sweep "
            f"(default {backfill_module.DEFAULT_RECORD}). "
            f"`{backfill_module.EVERY_PROTECTED}` sweeps every seat of every KEPT "
            f"gallery instead — `tentative.protected_keys`, which is what retention must "
            f"keep and therefore what has to stay replayable, de-duplicated across records "
            f"and published or not. Hours, so survey it first",
        )
        verb.add_argument("--out", metavar="PATH", help="write the record there")
