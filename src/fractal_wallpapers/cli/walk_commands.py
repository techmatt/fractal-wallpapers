"""`walk` and `reframe`: the two discovery legs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fractal_wallpapers.cli.common import (
    build_scorer,
    grace_flag,
    refine_limits,
    reframing_default,
    reframings_from,
    resolve_input,
    resolve_output,
    scoring_flags,
    walk_default,
)


def refuse_impossible_walk(args: argparse.Namespace) -> str | None:
    """Say why this walk has nowhere to start, or `None` if it has.

    Checked before anything is built, because "there is no supply for this" is a
    refusal and a refusal should not leave a run directory behind it.
    """
    if args.seeds:
        return None
    if args.family == "julia" and args.degree != 2:
        return (
            "the tracked c-pool is degree 2; a higher-degree julia walk needs --seeds, "
            "because its parameters live in a different plane and no pool of them is "
            "tracked yet"
        )
    if args.family in ("mandelbrot", "multibrot"):
        from fractal_wallpapers.discovery import plane_seeds

        return (
            f"a {args.family} walk has no sampler: an unscreened draw over the parameter "
            f"plane measured zero good locations in 144, so none is built. Its roots come "
            f"from the tracked plane seed pool — pass --seeds {plane_seeds.pool_path()} "
            f"(derive it with `fractal-wallpapers derive-plane-seeds --write` if it is not "
            f"there), or let the reframing operators find them from a walk that already "
            f"reached somewhere."
        )
    return None


def walk(args: argparse.Namespace) -> int:
    """Run one discovery walk and print what it found."""
    from fractal_wallpapers.discovery.walk import Gates, Limits, Policy, Walk

    complaint = refuse_impossible_walk(args)
    if complaint is not None:
        print(complaint)
        return 1

    run = Walk(
        scorer=build_scorer(args),
        out_dir=resolve_output(args.out_dir),
        seed=args.seed,
        limits=Limits(
            batch=args.batch,
            batches=args.batches,
            root_expansions=args.root_expansions,
            pinned_root_expansions=args.pinned_root_expansions,
            probe_probability=args.probe,
            plane_grace_rungs=args.plane_grace_rungs,
            **refine_limits(args),
        ),
        policy=Policy(candidates=args.candidates, node_width=args.node_width),
        gates=Gates(),
        reframings=reframings_from(args, enabled=not args.no_reframings),
        colormap=args.colormap,
        report_foci=args.foci,
    )

    if args.seeds:
        roots = run.seed_from_file(Path(args.seeds), limit=args.roots)
    elif args.family == "phoenix":
        roots = run.seed_from_phoenix_pool(limit=args.roots)
    else:
        roots = run.seed_from_julia_pool(limit=args.roots)

    if roots == 0:
        print("no roots: nothing to walk")
        return 1
    print(json.dumps(run.run(), indent=2))
    return 0


def reframe(args: argparse.Namespace) -> int:
    """Fire the reframing operators at proven roots and record their own views."""
    from fractal_wallpapers.discovery import reframing

    scorer = build_scorer(args)
    if scorer is None:
        print(
            "the reframing channel scores every view it builds, and the whole point of it is "
            "that those views become scored candidates. --no-scoring would write a ledger of "
            "unclassed rows the supply engine cannot count."
        )
        return 1
    if args.no_prior and args.prior:
        print(
            "--no-prior and --prior say opposite things about the same queue. Name the legs "
            "to continue, or say --no-prior, or say neither and let the ledgers answer."
        )
        return 1
    # None is not "no priors" here: it is what asks the ledgers. The empty list
    # is how --no-prior says the other thing.
    if args.no_prior:
        prior = []
    elif args.prior:
        prior = [resolve_input(each) for each in args.prior]
    else:
        prior = None
    try:
        report = reframing.run(
            out_dir=resolve_output(args.out_dir),
            scorer=scorer,
            seed=args.seed,
            rungs=[float(rung) for rung in args.rungs],
            minutes=args.minutes,
            generations=args.generations,
            tier_floor=args.tier_floor,
            partitions=args.partition or None,
            roots=args.roots,
            seed_batch=args.seed_batch,
            max_period=args.seed_max_period,
            prior=prior,
            reprobe=args.reprobe,
        )
    except (reframing.ChannelRefused, reframing.PinnedPlace) as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    return 0


def add_commands(subcommands) -> None:
    """Register this group's commands, in the order they ship in."""
    from fractal_wallpapers.discovery.walk import Limits as WalkLimits
    from fractal_wallpapers.supply.partitions import PARAMETER_PLANES

    search = subcommands.add_parser(
        "walk",
        help="descend from seeds, keeping what survives the structural gates",
        description=(
            "Run one discovery walk. Roots come from the tracked seed pools for the "
            "dynamical families and from an explicit --seeds file for the parameter "
            "plane; there is no sampler behind either. Everything the walk sees — "
            "survivors and rejects alike — lands in walk.jsonl under --out-dir, with the "
            "gate that refused it or a thumbnail if none did."
        ),
    )
    search.add_argument(
        "--family",
        choices=["mandelbrot", "multibrot", "julia", "phoenix"],
        default="julia",
        help="which family to walk (default: julia, the one with a tracked c-pool)",
    )
    search.add_argument("--degree", type=int, default=2, help="exponent d, for multibrot and julia")
    search.add_argument(
        "--seeds",
        help="JSONL file of root locations: one {family, viewport} object per line",
    )
    search.add_argument("--roots", type=int, help="use only this many of the available roots")
    search.add_argument("--seed", type=int, default=0, help="run seed (default: 0)")
    search.add_argument("--batch", type=int, default=8, help="nodes expanded per batch")
    search.add_argument("--batches", type=int, default=4, help="batches to run")
    search.add_argument(
        "--root-expansions",
        type=int,
        default=walk_default("root_expansions"),
        help=f"expansions any one root may pay for, its reframings included "
        f"(default: {walk_default('root_expansions')})",
    )
    search.add_argument(
        "--pinned-root-expansions",
        type=int,
        default=walk_default("pinned_root_expansions"),
        help=f"the same, for a root on a pinned plane, which has no free parameter and "
        f"therefore no second root to answer a dead lineage with "
        f"(default: {walk_default('pinned_root_expansions')})",
    )
    search.add_argument("--candidates", type=int, default=4, help="candidates drawn per node")
    search.add_argument(
        "--node-width",
        type=int,
        default=384,
        help="node render width in pixels. A scored run refuses anything but the node "
        "regime's own width: the head reads that frame as a tile",
    )
    search.add_argument(
        "--probe",
        type=float,
        default=0.25,
        help="probability the reframing probe fires on an admission (default: 0.25)",
    )
    search.add_argument(
        "--refine-per-walk",
        type=int,
        default=None,
        metavar="K",
        help="how many of this walk's best gate survivors have their FRAMING refined when the "
        "walk closes, best first by the seating statistic. The gallery pass's step 5a at the "
        "other end of the pipeline and through the same code: a small window of framings drawn "
        "at the node regime, read through the location head, the best adopted if it beats the "
        "recorded framing by --refine-margin. It is recorded as a later ledger row that the "
        "readers prefer, never as an edit; nothing feeds back into this walk's reward or "
        f"descent (default: {WalkLimits.refine_per_walk}; 0 disables the leg)",
    )
    search.add_argument(
        "--refine-margin",
        type=float,
        default=None,
        metavar="DELTA",
        help="how much better a framing has to read before it is adopted, in NATS of log-odds "
        "on P(>=4). The gallery pass's own default unless said otherwise, so a scan taken here "
        "and a scan taken at a pass are the same decision",
    )
    search.add_argument(
        "--no-reframings",
        action="store_true",
        help="expand only what the walk descends into; fire no reframing operators",
    )
    neighborhood = search.add_mutually_exclusive_group()
    neighborhood.add_argument(
        "--neighborhood",
        dest="neighborhood",
        action="store_true",
        default=None,
        help="enumerate neighbouring nuclei (on by default; the expensive operator)",
    )
    neighborhood.add_argument(
        "--no-neighborhood",
        dest="neighborhood",
        action="store_false",
        help="fire only the snap and the lateral step, and pay neither the "
        "neighbourhood enumeration's clock nor its frontier",
    )
    search.add_argument(
        "--colormap",
        default="twilight_shifted",
        help="colormap the gate renders are drawn through. A scored run refuses any map "
        "but the tile pool's floor palette: the head reads the gate render as a tile",
    )
    search.add_argument(
        "--out-dir",
        default=str(Path("artifacts") / "walk"),
        help="where the ledger and thumbnails go (default: artifacts/walk)",
    )
    search.add_argument(
        "--foci",
        action="store_true",
        help="record each expanded node's kept focus set beside its candidates: where the "
        "peaks were, which blurring scales found each one, how alone it stands and how far "
        "the nearest kept neighbour is. Off by default, and a run without it writes the "
        "ledger it always wrote - the set is read either way and this decides only whether "
        "it is kept",
    )
    grace_flag(search)
    scoring_flags(search)
    search.set_defaults(handler=walk)

    reframing_leg = subcommands.add_parser(
        "reframe",
        help="fire the reframing operators at proven roots; their own views become candidates",
        description=(
            "The reframing channel. A walk pushes an operator's nucleus-centred view onto "
            "the frontier as a node and only ever scores what it draws BELOW it, so that "
            "picture is never a candidate. This leg fires the same operators at locations a "
            "human already scored a keeper, draws each nucleus it finds at every rung of the "
            "framing ladder, reads them all through the location head, and writes ONE "
            "candidate row per nucleus at the rung the head picked. A nucleus that clears the "
            "keeper floor becomes a seed for the next generation, behind every proven root on "
            "a queue ordered matt-q4, matt-q3, head-q4, head-keeper. The ledger is walk-shaped "
            "and lands at <out-dir>/walk.jsonl, so `curate score --harvest <out-dir>` reads "
            "it like any other supply. Nothing about the walk changes."
        ),
    )
    reframing_leg.add_argument("--seed", type=int, default=0, help="run seed (default: 0)")
    reframing_leg.add_argument(
        "--minutes",
        type=float,
        default=None,
        help="stop when this many minutes of the leg have been spent, at the next seed-batch "
        "boundary (default: none; run the seed set out)",
    )
    reframing_leg.add_argument(
        "--generations",
        type=int,
        default=1,
        help="how many generations to fire (default: 1, the proven roots alone). A nucleus "
        "the head scores at or above the q4 admission bar joins the next generation's seeds, "
        "and one that merely clears the keeper floor joins behind it; the generation and the "
        "queue class the seed came from are both on every row",
    )
    reframing_leg.add_argument(
        "--rungs",
        type=float,
        nargs="+",
        default=list(reframing_default("RUNGS")),
        metavar="K",
        help=f"the framings to draw, in atom sizes (default: "
        f"{' '.join(f'{k:g}' for k in reframing_default('RUNGS'))}). They are one location's "
        f"framings and not several locations: all of them are drawn and scored, the head "
        f"picks one, and every reading is on the row",
    )
    reframing_leg.add_argument(
        "--tier-floor",
        type=int,
        default=reframing_default("SEED_TIER_FLOOR"),
        help=f"the lowest human label tier a seed may carry (default: "
        f"{reframing_default('SEED_TIER_FLOOR')}, both of the currency's paid classes)",
    )
    reframing_leg.add_argument(
        "--partition",
        action="append",
        choices=list(PARAMETER_PLANES),
        help="seed from this parameter plane alone (repeatable; default: every one). The "
        "dynamical partitions are never served here: a Julia viewport is a z-plane point "
        "and has no nucleus in the parameter-plane sense",
    )
    reframing_leg.add_argument(
        "--roots", type=int, help="use only this many of the available proven roots"
    )
    reframing_leg.add_argument(
        "--prior",
        metavar="DIR",
        action="append",
        help="an earlier run of this channel to continue (repeatable). DEFAULT: every earlier "
        "leg the ledgers know about, on both storage tiers, found by the run-header row rather "
        "than by any name — so a chain continues itself and naming them is an override rather "
        "than a chore. Their nuclei are already found, so an atom reached again is counted "
        "rather than written twice; the proven roots they consumed are off the queue; and "
        "their admitted rows ARE this run's promotions — head-q4 first, then head-keeper, both "
        "behind whatever is left of the label store. Naming a list that omits a leg the "
        "ledgers hold is a WARNING and not a refusal, because that leg's atoms then get "
        "written twice: on 2026-09-01 a leg handed only its predecessor wrote 192 of its 302 "
        "rows on atoms the first leg already held",
    )
    reframing_leg.add_argument(
        "--no-prior",
        action="store_true",
        help="continue nothing: derive the seeds off the label store alone, as the first leg "
        "of a chain does. This is what --prior defaulted to before the ledgers were consulted, "
        "and on a machine that already holds legs it writes their nuclei a second time",
    )
    reframing_leg.add_argument(
        "--reprobe",
        action=argparse.BooleanOptionalAction,
        default=reframing_default("REPROBE"),
        help="fire at the proven roots an earlier leg already spent, as well as at what is "
        "left. DEFAULT: read the chain and decide — a chain is spent when a plain continuation "
        "has no seed at all, or when its latest leg (having consumed at least 100 seeds) "
        "already held 90%% or more of the nuclei it reached. `expand_neighborhood` probes at "
        "random, so a second pass at one root is a different sample of its neighbourhood and "
        "reaches atoms the first missed; the earlier legs' nuclei are still deduped, so "
        "nothing is written twice and no unfired root is skipped. --no-reprobe forces the "
        "plain continuation. The run record says which branch was taken, why, and what the "
        "ledgers would have said. Give the leg its own --seed or it draws the same probes",
    )
    reframing_leg.add_argument(
        "--seed-max-period",
        type=int,
        default=reframing_default("SEED_SNAP_MAX_PERIOD"),
        help=f"the period ceiling the seed snap scans to (default: "
        f"{reframing_default('SEED_SNAP_MAX_PERIOD')}). Higher than the operator module's "
        f"own default on purpose: seeds are the scarce thing here and the snap is a tenth "
        f"of the operator clock",
    )
    reframing_leg.add_argument(
        "--seed-batch",
        type=int,
        default=reframing_default("SEED_BATCH"),
        help=f"seeds fired before their nuclei are drawn and scored (default: "
        f"{reframing_default('SEED_BATCH')})",
    )
    reframing_leg.add_argument(
        "--out-dir",
        default=str(reframing_default("DEFAULT_OUT")),
        help=f"the run directory, a TOP-LEVEL name of the regenerable tree (default: "
        f"{reframing_default('DEFAULT_OUT')})",
    )
    scoring_flags(reframing_leg)
    reframing_leg.set_defaults(handler=reframe)
