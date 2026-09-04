"""`tiles`: plan and build the tile head's material."""

from __future__ import annotations

import argparse
import json


def tiles_plan(args: argparse.Namespace) -> int:
    """Turn the label store into the population a tile build runs over."""
    from collections import Counter

    from fractal_wallpapers.labeling import store
    from fractal_wallpapers.models import tiles as tile_module

    population = tile_module.plan(store.resolved().scored(), seed=args.seed)
    plan_file, locations_file = tile_module.write_plan(population)
    pool = tile_module.palette_pool()
    print(
        json.dumps(
            {
                "locations": len(population),
                "seed": args.seed,
                "seed_tag": tile_module.SEED_TAG,
                "sides": dict(sorted(Counter(row["side"] for row in population).items())),
                "scores": dict(sorted(Counter(row["score"] for row in population).items())),
                "partitions": dict(sorted(Counter(row["partition"] for row in population).items())),
                "biased": sum(1 for row in population if row["biased"]),
                "groups": len({row["group"] for row in population}),
                "palettes": {
                    "draw": len(pool["draw"]),
                    "floor": pool["floor"],
                    "invariance_holdout": len(pool["invariance_holdout"]),
                },
                "wrote": [str(plan_file), str(locations_file)],
            },
            indent=2,
        )
    )
    return 0


def tile_regime(args: argparse.Namespace):
    """The regime a `tiles` subcommand was aimed at, from its two flags."""
    from fractal_wallpapers.models import tiles as tile_module

    size = str(args.tile).lower().split("x")
    if len(size) != 2 or not all(part.isdigit() for part in size):
        raise SystemExit(f"--tile takes WIDTHxHEIGHT, not {args.tile!r}")
    return tile_module.Regime(tile=(int(size[0]), int(size[1])), supersample=int(args.supersample))


def tiles_build(args: argparse.Namespace) -> int:
    """Render every tile of the plan, one iteration pass per location."""
    from fractal_wallpapers.models import tiles as tile_module

    regime = tile_regime(args)
    log = tile_module.build_log_path(regime)
    report = tile_module.build(limit=args.limit, log=log, regime=regime)
    record = {
        "schema": tile_module.SCHEMA,
        "plan": str(tile_module.plan_path()),
        "locations": str(tile_module.locations_path()),
        "log": str(log),
        "report": report,
    }
    tile_module.build_record_path(regime).write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    summary = {key: value for key, value in report.items() if key != "recipe"}
    summary["recipe"] = {
        key: value for key, value in report["recipe"].items() if key != "palette_pool"
    }
    summary["recipe"]["palette_pool"] = f"{len(report['recipe']['palette_pool'])} names"
    print(json.dumps(summary, indent=2))
    return 0


def add_commands(subcommands) -> None:
    """The training tiles: plan the population, then render it."""
    tiling = subcommands.add_parser(
        "tiles",
        help="build the pictures a head is trained on: plan, then render",
        description=(
            "One iteration pass per location and every tile a colored crop of it, each "
            "drawing its own colormap, framing, reconstruction and JPEG quality. The plan "
            "says which locations; the recipe behind the fan-out belongs to the engine."
        ),
    )
    steps = tiling.add_subparsers(dest="step", required=True)

    planning = steps.add_parser(
        "plan",
        help="turn the label store into the population a build runs over",
        description=(
            "Every labeled location is in the plan, evaluation side included: a held-out "
            "location has to be scored through the same pictures the training side was "
            "learned from, or the number measures the render as much as the head. The plan "
            "is shuffled by a seed, so any prefix of it is a fair sample and a bounded "
            "rehearsal projects the whole build honestly."
        ),
    )
    planning.add_argument("--seed", type=int, default=0, help="the shuffle's seed (default: 0)")
    planning.set_defaults(handler=tiles_plan)

    building = steps.add_parser(
        "build",
        help="render every tile of the plan, at one regime",
        description=(
            "Resumable by construction: a location whose tiles are all on disk is skipped "
            "before its field is iterated, so a killed run continues rather than restarting. "
            "A build is aimed at a regime — a tile size and a field supersample — which is "
            "written into every file name it makes, so two regimes share one cache without "
            "either skipping over the other's pictures. The canonical 640x360 at supersample "
            "2 writes the bare names; anything else adds its own segment, and its manifest, "
            "build record and log take the same segment. Progress goes to "
            "artifacts/tiles/build<regime>.log as it runs."
        ),
    )
    building.add_argument(
        "--limit",
        type=int,
        help="stop after this many locations; every row it writes is stamped partial",
    )
    building.add_argument(
        "--tile",
        default="640x360",
        metavar="WIDTHxHEIGHT",
        help="one tile's output size (default: 640x360)",
    )
    building.add_argument(
        "--supersample",
        type=int,
        default=2,
        help="field samples per output pixel per axis (default: 2)",
    )
    building.set_defaults(handler=tiles_build)
