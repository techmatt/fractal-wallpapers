"""The supply engine: `harvest`, the two scoring reads, and the four derivations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fractal_wallpapers import schedule as schedule_module
from fractal_wallpapers.cli.common import (
    build_scorer,
    declared_ledgers,
    device_flag,
    display_path,
    grace_flag,
    ledger_flags,
    novelty_default,
    plane_seed_default,
    proven_default,
    refine_limits,
    reframings_from,
    resolve_output,
    sampler_default,
    scoring_flags,
    walk_default,
    write_tracked_json,
)
from fractal_wallpapers.paths import (
    tracked_name,
)

#: The harvest's active-minute budget when neither `--minutes` nor `--finish-by`
#: says otherwise. Here rather than as the flag's `default=` because the two
#: flags are exclusive and `--minutes 0` is a real answer: a default filled in by
#: argparse could not be told from a caller who asked for it.
DEFAULT_HARVEST_MINUTES = 10.0


def build_proven_channel(args: argparse.Namespace, partitions):
    """The proven-label channel this run asked for by name, or `None`.

    Derived from the label store as it stands rather than read from a file: a
    keeper labelled this morning is a root this afternoon, and there is nothing
    to refresh. Off by default — the channel feeds on this project's own past
    output, so adopting it is a decision a run states.
    """
    from fractal_wallpapers.supply import proven

    if proven.CHANNEL not in (getattr(args, "root_channels", None) or ()):
        return None
    return proven.build(partitions=partitions)


def build_sampler_channel(args: argparse.Namespace, partitions, walk_run, log=print):
    """The viewport sampler this run asked for by name, or `None`.

    Drawn and screened when the run is built rather than at the first refill: the
    ladder is a few hundred frames through the gate battery, which is seconds,
    and paying it inside the refill's share of the loop clock would price a
    channel's whole supply against a bound meant for a draw.

    The run's own seed, so two harvests at one seed sample the same viewports and
    a resumed session re-derives the list its cursor is standing in. The walk's
    ledger, so every attempt and its fate land in the run's record rather than
    only in a summary.
    """
    from fractal_wallpapers.discovery import viewport_sampler

    if viewport_sampler.CHANNEL not in (getattr(args, "root_channels", None) or ()):
        return None
    return viewport_sampler.build(
        partitions=partitions,
        seed=args.seed,
        rungs=args.sampler_rungs,
        colormap=args.colormap,
        node_width=args.node_width,
        ledger=walk_run.ledger,
        log=log,
    )


def score_parity(args: argparse.Namespace) -> int:
    """Score one batch of real locations both ways and compare."""
    from fractal_wallpapers.curation import binding, intake
    from fractal_wallpapers.discovery import scoring

    try:
        rows, _diagnostics = intake.gate_survivors(declared_ledgers(args))
    except binding.Unbound as refusal:
        print(refusal)
        return 1
    candidates = rows[: max(1, int(args.rows))]
    if not candidates:
        print(
            "no walk ledger holds a gate-surviving candidate, so there is nothing to score "
            "both ways. Run `fractal-wallpapers harvest` first."
        )
        return 1
    report = scoring.parity(candidates, args.score_workers, resolve_output(args.out_dir))
    print(json.dumps(report, indent=2))
    return 0 if report["held"] else 1


def derive_plane_seeds(args: argparse.Namespace) -> int:
    """Re-derive the parameter-plane seed pool; verify unless told to write."""
    from fractal_wallpapers.discovery import plane_seeds

    out = Path(args.out) if args.out else plane_seeds.pool_path()
    derived = plane_seeds.derive(
        columns=args.columns if args.columns is not None else plane_seeds.COLUMNS,
        per_partition=(
            args.per_partition if args.per_partition is not None else plane_seeds.PER_PARTITION
        ),
    )
    if args.write:
        plane_seeds.write(derived["rows"], out)
        print(json.dumps({"wrote": str(out), **derived["record"]}, indent=2))
        return 0
    verdict = plane_seeds.verify(derived["rows"], out)
    print(json.dumps({"verify": verdict, **derived["record"]}, indent=2))
    if not verdict["held"]:
        print(
            "\nthe tracked pool is not what this procedure produces. Nothing was written: "
            "re-run with --write if the procedure is the thing that changed."
        )
    return 0 if verdict["held"] else 1


def derive_proven_seeds(args: argparse.Namespace) -> int:
    """Print the proven-label seed set, and say how it compares to a file."""
    from fractal_wallpapers.supply import proven

    derived = proven.derive(
        tier_floor=args.tier_floor if args.tier_floor is not None else proven.TIER_FLOOR,
        partitions=tuple(args.partition or proven.SERVED),
    )
    out: dict = {"record": derived["record"]}
    if args.against:
        out["against"] = proven.compare(derived["rows"], resolve_output(args.against))
    if args.write:
        path = resolve_output(args.out)
        proven.write(derived["rows"], path)
        out["wrote"] = display_path(path)
    print(json.dumps(out, indent=2))
    lost = (out.get("against") or {}).get("lost", 0)
    if lost:
        print(
            f"\n{lost} location(s) the file holds are not in the derived set. A verdict was "
            "withdrawn, lowered, or is no longer readable — that is a thing to explain, not "
            "a thing to re-derive past."
        )
        return 1
    return 0


def score_locations(args: argparse.Namespace) -> int:
    """Score a list of locations through the shipped location head."""
    from fractal_wallpapers import locations
    from fractal_wallpapers.models import location_scoring
    from fractal_wallpapers.models import tiles as tile_module

    try:
        rows = locations.read(resolve_output(args.manifest))
    except locations.LocationError as refusal:
        print(refusal)
        return 1
    if args.limit is not None:
        rows = rows[: max(0, args.limit)]

    regime = tile_module.regime_of(args.regime)
    report = location_scoring.score(
        rows,
        out=resolve_output(args.out),
        regime=None if regime == tile_module.CANONICAL_REGIME else regime,
        device=args.device,
        workers=args.score_workers,
        views=resolve_output(args.views) if args.views else None,
    )
    print(json.dumps(report, indent=2))
    return 0


def harvest_minutes(args: argparse.Namespace):
    """`(minutes, plan)` — the active-minute budget this leg is held to, and why.

    `--finish-by` is a *derivation* of `--minutes` rather than a second budget:
    the loop still stops on active minutes and nothing here paces it. What the
    plan buys is that the number was arrived at from a time somebody named, on
    the record, in terms a readout can subtract afterwards.
    """
    from fractal_wallpapers import schedule

    if args.finish_by is None:
        minutes = DEFAULT_HARVEST_MINUTES if args.minutes is None else args.minutes
        return minutes, None
    derived = schedule.plan(
        args.finish_by,
        args.release_slots,
        curation_attempts(args),
        renders_views=harvest_draws_views(args),
        release_workers=args.release_workers,
    )
    for line in derived.lines():
        print(f"[plan] {line}")
    return derived.active_minutes, derived


def curation_attempts(args: argparse.Namespace) -> int:
    """Colorize attempts the curation leg this night reserves for will actually plan.

    Derived through `curation.budget` rather than restated here, and derived from
    the shape the night will run the curation at — the release ceiling, the
    strange share, the modes each head draws. The reservation used to be `4n`
    times this module's own copies of those three, which was a restatement of
    curation's arithmetic and was pinned to it by the suite; it stopped being
    pinnable the moment the mode table became a parameter of a run.
    """
    from fractal_wallpapers.curation import budget

    modes = None if args.strange_modes is None else {budget.STRANGE: args.strange_modes}
    slots = budget.head_slots(args.release_slots, args.strange_share)
    wanted, _ = budget.head_attempts(slots, None, modes=budget.modes_of(modes))
    return sum(wanted.values())


def harvest_draws_views(args: argparse.Namespace) -> bool:
    """Whether this run will render views for its judge, or score the gate renders.

    The one thing that decides it is whether the walk's own gate render *is* the
    picture the head reads — `discovery.identity`'s claim, asked here of the same
    four settings the walk will assert it on a moment later. A run that fails that
    claim is refused when the walk is built, so answering `True` for it costs
    nothing and guessing the other way would silently pick the cheap ratio for a
    night that draws a view per survivor.

    A run with no scorer at all draws nothing either, and gets the same answer as
    one that scores what it drew: the ratio is about views rendered, not about
    whether anything was judged.
    """
    from fractal_wallpapers.discovery import identity
    from fractal_wallpapers.models import tiles as tile_module

    if args.no_scoring:
        return False
    try:
        identity.enforce(
            args.colormap, args.node_width, tile_module.NODE_REGIME, log=lambda *_: None
        )
    except identity.IdentityBroken:
        return True
    return False


def harvest(args: argparse.Namespace) -> int:
    """Run the production loop: keep finding material where it is scarcest."""
    from fractal_wallpapers.discovery.walk import Limits, Policy, Walk
    from fractal_wallpapers.supply import autopsy, ledgers, novelty, saturation, twins
    from fractal_wallpapers.supply.census import stock_census
    from fractal_wallpapers.supply.harvest import Budget, Harvest
    from fractal_wallpapers.supply.partitions import ALL_PARTITIONS
    from fractal_wallpapers.supply.prices import load_table
    from fractal_wallpapers.supply.quota import Quota
    from fractal_wallpapers.supply.refill import Refill

    minutes, derived = harvest_minutes(args)
    run_dir = resolve_output(args.out_dir)
    limits = Limits(
        batch=args.batch,
        root_expansions=args.root_expansions,
        pinned_root_expansions=args.pinned_root_expansions,
        plane_grace_rungs=args.plane_grace_rungs,
        **refine_limits(args),
        # `None` and not `0`: zero is a real answer to "how many admissions may a
        # lineage book" and it is not the one the flag's zero means.
        lineage_admissions=args.lineage_cap if args.lineage_cap > 0 else None,
    )
    if args.probe is not None:
        limits.probe_probability = args.probe
    walk_run = Walk(
        out_dir=run_dir,
        seed=args.seed,
        limits=limits,
        policy=Policy(candidates=args.candidates, node_width=args.node_width),
        reframings=reframings_from(args),
        colormap=args.colormap,
        scorer=build_scorer(args),
        report_foci=args.foci,
    )
    # A run told which partitions to keep books for keeps them for those alone:
    # the census, the allocation, the refill census and the served mix all read
    # this list, so naming one partition is how a leg spends a whole clock there
    # rather than steering toward it and hoping.
    partitions = list(args.partition or ALL_PARTITIONS)
    # Found once, read by three builders. Each of them used to look the ledgers up
    # for itself, which on an archive root is the same directory walk three times
    # over — the whole of what `schedule.LEDGER_LOAD_SECONDS` had grown to reserve.
    ledger_files = ledgers.ledger_paths(
        root=resolve_output(args.ledgers), exclude=walk_run.ledger.path
    )
    print(f"[plan] ledgers: {len(ledger_files)} under {display_path(resolve_output(args.ledgers))}")
    # The protected exploration share, and the cross-run record of which lineages
    # have ever produced that decides who is in it. Built off the same ledger root
    # the saturation memory reads, minus this run's own file.
    exploration = (
        None
        if args.no_exploration
        else novelty.Exploration(
            lineages=novelty.build(paths=ledger_files),
            floor=args.exploration_floor,
            start=args.exploration_start,
            ema=args.exploration_ema,
        )
    )
    quota = Quota(
        partitions,
        run_dir,
        floor=args.floor,
        prices_config=load_table(Path(args.prices) if args.prices else None),
        census=stock_census(partitions, discount=args.discount),
        exploration=exploration,
    )
    # Primed before the first batch, off the same two legs of admitted stock the
    # census reads, and extended by whatever this run books. Its ledger is the
    # walk's, so what the channel accepted and what the c-spacing floor refused
    # land in the run's own record rather than only in a summary.
    twin_channel = (
        None if args.no_twins else twins.build(ledger=walk_run.ledger, ledger_paths=ledger_files)
    )
    refill = Refill(
        walk_run,
        low_water=args.low_water,
        cooldown=args.cooldown,
        share=args.refill_share,
        seeds=Path(args.seeds) if args.seeds else None,
        partitions=partitions,
        twins=twin_channel,
        proven=build_proven_channel(args, partitions),
        sampler=build_sampler_channel(args, partitions, walk_run),
    )
    memory = None if args.no_saturation else saturation.build(paths=ledger_files)
    run = Harvest(
        walk_run,
        quota,
        budget=Budget(minutes=minutes, batches=args.batches),
        refill=refill,
        memory=memory,
        saturation_strength=0.0 if args.no_saturation else saturation.STRENGTH,
        discount_k=args.lineage_discount,
        discount_floor=args.lineage_discount_floor,
        partitions=partitions,
        finish_by=None if derived is None else derived.record(),
    )
    # Before the first batch, not in the readout. run10 opened with 39, 46 and 52
    # derived parameters in its three julia twins and 209 and 96 in the two
    # tracked `c`-pools, against 413 to 507 a parameter plane; all five ran dry
    # and the readout is where that surfaced, the following morning. What the
    # share can reach is a fact about the pools at launch, and it was readable
    # then.
    for line in refill.pool_lines():
        print(f"[plan] {line}")
    if run.resume():
        print(f"resumed at batch {run.batch} ({run.active_minutes:.2f} active minutes spent)")
    summary = run.run()
    sheet = autopsy.write(run_dir, summary)
    if sheet is not None:
        print(f"channel autopsy -> {display_path(sheet)}")
    print(json.dumps(summary, indent=2))
    return 0


def census(args: argparse.Namespace) -> int:
    """Print the standing deficit and the allocation it implies, running nothing.

    Three reads off one census, because the question anybody asks first is what
    the machine leg moved: the labels-only deficit as it was, the effective
    deficit as it now is, and the discounted currency that separates them. Both
    allocations are quoted at seed prices — a price table is a fact about a run,
    and this is not a run.
    """
    from fractal_wallpapers.supply import census as census_module
    from fractal_wallpapers.supply import release_mix
    from fractal_wallpapers.supply.allocation import allocate
    from fractal_wallpapers.supply.partitions import ALL_PARTITIONS
    from fractal_wallpapers.supply.prices import load_table

    partitions = list(ALL_PARTITIONS)
    stock_census = census_module.stock_census(partitions, discount=args.discount)
    ratios = release_mix.ratios(partitions)
    seed = load_table(Path(args.prices) if args.prices else None)["prices"]

    labels = stock_census.currency
    stock = stock_census.stock()
    labels_target, labels_anchor = census_module.targets(labels, partitions, ratios)
    labels_deficit = {p: max(0.0, labels_target[p] - float(labels.get(p, 0.0))) for p in partitions}
    target, anchor = census_module.targets(stock, partitions, ratios)
    deficit = {p: max(0.0, target[p] - float(stock.get(p, 0.0))) for p in partitions}

    labels_allocation = allocate(labels_deficit, seed, partitions, args.floor)
    allocation = allocate(deficit, seed, partitions, args.floor)
    print(
        json.dumps(
            {
                "currency": stock_census.summary(),
                "target_rule": census_module.TARGET_RULE,
                "ratio": ratios,
                "labels_only": {
                    "anchor": round(labels_anchor, 3),
                    "target": {p: round(labels_target[p], 3) for p in partitions},
                    "deficit": {p: round(labels_deficit[p], 3) for p in partitions},
                    "allocation_at_seed_prices": labels_allocation.summary(),
                },
                "with_machine_stock": {
                    "discount": stock_census.machine_leg().discount,
                    "anchor": round(anchor, 3),
                    "stock": {p: round(stock[p], 3) for p in partitions},
                    "target": {p: round(target[p], 3) for p in partitions},
                    "deficit": {p: round(deficit[p], 3) for p in partitions},
                    "allocation_at_seed_prices": allocation.summary(),
                },
                "deficit_delta": {p: round(deficit[p] - labels_deficit[p], 3) for p in partitions},
                "share_delta": {
                    p: round(allocation.share[p] - labels_allocation.share[p], 4)
                    for p in partitions
                },
            },
            indent=2,
        )
    )
    return 0


def derive_prices(args: argparse.Namespace) -> int:
    """Regenerate the cost-to-find seed table from finished runs."""
    from fractal_wallpapers.supply import prices as price_module
    from fractal_wallpapers.supply.partitions import ALL_PARTITIONS

    blocks, sources = [], []
    for name in args.run:
        run_dir = resolve_output(name)
        summary = run_dir / "summary.json"
        if not summary.is_file():
            # The summary is written when a run finishes, so its presence is what
            # says the run reached an end. A checkpoint holds the same counters
            # mid-flight and would price a partial population as a whole one.
            print(f"{summary} is missing - that run has not finished; state.json is not a")
            print("substitute, it would price a partial population as a whole one.")
            return 1
        document = json.loads(summary.read_text(encoding="utf-8"))
        cost = ((document.get("quota") or {}).get("cost")) or {}
        if not cost:
            print(f"{summary} carries no cost block - nothing to derive a price table from")
            return 1
        blocks.append(cost)
        # The table this derives is tracked, so the run it was derived from is
        # named as a tracked record names a place under the regenerable tree.
        sources.append({"name": run_dir.name, "path": tracked_name(run_dir)})

    try:
        table = price_module.derive(blocks, sources, ALL_PARTITIONS)
        if args.regularize:
            table = price_module.regularize(
                table, alpha=args.alpha, clamp=args.clamp, source=args.measured or ""
            )
    except price_module.PriceTableError as refusal:
        # Fail closed rather than fall back to the seed: a regenerated table that
        # is byte-identical to the flat seed reports itself as a measurement and
        # is not one, and afterwards nobody can tell the two apart.
        print(refusal)
        return 1
    out = (
        resolve_output(args.out)
        if args.out
        else (
            price_module.seed_table_path()
            if args.regularize
            else price_module.measured_table_path()
        )
    )
    if args.write:
        out.parent.mkdir(parents=True, exist_ok=True)
        # `newline="\n"` because this writes a TRACKED table: without it Windows
        # writes CRLF, `.gitattributes` normalizes it back to LF on the way into
        # the index, and every regeneration leaves a working tree whose bytes are
        # not the bytes that were committed.
        write_tracked_json(out, table)
        print(f"wrote {out}")
    else:
        print(json.dumps(table, indent=2))
        print("(dry run - pass --write to replace the shipped table)")
    return 0


def derive_tau_h(args: argparse.Namespace) -> int:
    """Re-derive the cheap cut from this repository's own walks."""
    from fractal_wallpapers.supply import tau_h as tau_module
    from fractal_wallpapers.supply.partitions import ALL_PARTITIONS

    rows = tau_module.rows_from_ledgers([Path(p) for p in args.ledger] if args.ledger else None)
    table = tau_module.artifact(rows, ALL_PARTITIONS, keep=args.keep)
    out = resolve_output(args.out) if args.out else tau_module.table_path()
    if args.write:
        out.parent.mkdir(parents=True, exist_ok=True)
        write_tracked_json(out, table)
        print(f"wrote {out}")
    else:
        print(json.dumps(table, indent=2))
        print("(dry run - pass --write to replace the shipped table)")
    return 0


def add_commands(subcommands) -> None:
    """Register this group's commands, in the order they ship in."""
    from fractal_wallpapers.curation import run as curation_run
    from fractal_wallpapers.discovery.walk import Limits as WalkLimits
    from fractal_wallpapers.supply.partitions import ALL_PARTITIONS

    production = subcommands.add_parser(
        "harvest",
        help="the production loop: keep finding material where it is scarcest",
        description=(
            "Run batches until the active-time budget is spent, dividing each batch's slots "
            "between partitions by how far each one is below its intended share of the "
            "release. Checkpoints at every batch boundary and resumes from the checkpoint "
            "if one is there, so a killed run continues rather than restarting."
        ),
    )
    production.add_argument("--seed", type=int, default=0, help="run seed (default: 0)")
    production.add_argument("--batch", type=int, default=8, help="node slots per batch")
    harvest_clock = production.add_mutually_exclusive_group()
    harvest_clock.add_argument(
        "--minutes",
        type=float,
        default=None,
        help=f"active-minute budget across every session of this run "
        f"(default: {DEFAULT_HARVEST_MINUTES:g}; 0 for none)",
    )
    harvest_clock.add_argument(
        "--finish-by",
        metavar="HH:MM",
        help="derive --minutes from a wall-clock finish time instead of naming it: the "
        "span to the next HH:MM, less the release leg (--release-slots), the closing "
        "re-score, the ledger load and a margin, converted from wall to ACTIVE minutes. "
        "The derived plan is printed at startup and written into the run summary",
    )
    production.add_argument(
        "--release-slots",
        type=int,
        default=curation_run.DEFAULT_N,
        help=f"the release ceiling the curation leg will be asked for (default: "
        f"{curation_run.DEFAULT_N}, the diagnostic release a run keeps). Read only with "
        f"--finish-by, which reserves this many pictures at the measured rate",
    )
    production.add_argument(
        "--strange-share",
        type=float,
        default=curation_run.STRANGE_SHARE,
        help=f"the share of those slots the strange judge will fill (default: "
        f"{curation_run.STRANGE_SHARE:g}). Read only with --finish-by: it is one of the "
        f"three terms that turn a release ceiling into a colorize attempt count, and the "
        f"reservation has to be for the night that will actually be run",
    )
    production.add_argument(
        "--strange-modes",
        type=int,
        default=None,
        help="modes the strange judge will draw at each location (default: curation's own). "
        "Read only with --finish-by, for the same reason as --strange-share",
    )
    production.add_argument(
        "--release-workers",
        type=int,
        default=schedule_module.RELEASE_WORKERS,
        help=f"worker processes the release leg will run at, which is what the reserved "
        f"rate is scaled to (default: {schedule_module.RELEASE_WORKERS}, the count every "
        f"release on record was measured at). Read only with --finish-by; it reserves "
        f"the clock, it does not pass anything to `curate run`",
    )
    production.add_argument(
        "--batches", type=int, help="stop after this many batches, whatever the clock says"
    )
    production.add_argument(
        "--seeds",
        help="a JSONL seed file for the parameter planes, which have no sampler "
        "(default: the tracked plane seed pool, data/discovery/plane_seed_pool.jsonl)",
    )
    production.add_argument(
        "--root-expansions",
        type=int,
        default=walk_default("root_expansions"),
        help=f"expansions any one root may pay for, its reframings included "
        f"(default: {walk_default('root_expansions')})",
    )
    production.add_argument(
        "--pinned-root-expansions",
        type=int,
        default=walk_default("pinned_root_expansions"),
        help=f"the same, for a root on a pinned plane. Higher because a pinned plane has no "
        f"free parameter, so a lineage the cap closes is not replaced by a fresh root "
        f"somewhere else. Measured on the first leg that ever walked one: its two "
        f"productive roots hit the ordinary cap while still finding "
        f"(default: {walk_default('pinned_root_expansions')})",
    )
    production.add_argument("--candidates", type=int, default=4, help="candidates drawn per node")
    production.add_argument(
        "--node-width",
        type=int,
        default=384,
        help="node render width in pixels. A scored run refuses anything but the node "
        "regime's own width: the head reads that frame as a tile",
    )
    production.add_argument(
        "--partition",
        action="append",
        choices=list(ALL_PARTITIONS),
        help="keep the books for this partition alone (repeatable; default: every one). A "
        "run told one partition allocates its whole clock there, and its census, price "
        "and refill census cover that partition only",
    )
    production.add_argument(
        "--probe",
        type=float,
        default=None,
        help="probability the reframing probe fires on an admission (default: "
        f"{WalkLimits.probe_probability})",
    )
    production.add_argument(
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
    production.add_argument(
        "--refine-margin",
        type=float,
        default=None,
        metavar="DELTA",
        help="how much better a framing has to read before it is adopted, in NATS of log-odds "
        "on P(>=4). The gallery pass's own default unless said otherwise, so a scan taken here "
        "and a scan taken at a pass are the same decision",
    )
    harvest_neighborhood = production.add_mutually_exclusive_group()
    harvest_neighborhood.add_argument(
        "--neighborhood",
        dest="neighborhood",
        action="store_true",
        default=None,
        help="enumerate neighbouring nuclei (on by default; the expensive operator)",
    )
    harvest_neighborhood.add_argument(
        "--no-neighborhood",
        dest="neighborhood",
        action="store_false",
        help="fire only the snap and the lateral step, and pay neither the "
        "neighbourhood enumeration's clock nor its frontier",
    )
    production.add_argument(
        "--floor",
        type=float,
        default=0.05,
        help="the share of the clock every partition floors at (default: 0.05)",
    )
    production.add_argument(
        "--discount",
        type=float,
        help="what an unlabelled machine-scored find is worth against the deficit "
        "(default: 0.2); 0 reproduces the labels-only deficit exactly",
    )
    production.add_argument("--prices", help="a cost-to-find seed table other than the shipped one")
    production.add_argument(
        "--low-water", type=int, default=8, help="a partition below this many nodes is starved"
    )
    production.add_argument(
        "--cooldown", type=int, default=10, help="batches a partition waits between refills"
    )
    production.add_argument(
        "--refill-share",
        type=float,
        default=0.25,
        help="share of the loop's clock refills may spend (default: 0.25)",
    )
    production.add_argument(
        "--lineage-cap",
        type=int,
        default=0,
        help="admissions any one lineage may book before the walk stops expanding it "
        "(default: 0, no cap). The hard stop that stands above the soft discount below",
    )
    production.add_argument(
        "--lineage-discount",
        type=float,
        default=novelty_default("DISCOUNT_K"),
        help=f"how fast a lineage's contest credit decays with what it has already booked "
        f"this run: credit x= max(floor, 1/(1+k*n)) (default: "
        f"{novelty_default('DISCOUNT_K')}; 0 turns the discount off). In the contest only - "
        f"the exploration share is never priced",
    )
    production.add_argument(
        "--lineage-discount-floor",
        type=float,
        default=novelty_default("DISCOUNT_FLOOR"),
        help=f"the floor that discount never falls below "
        f"(default: {novelty_default('DISCOUNT_FLOOR')})",
    )
    production.add_argument(
        "--exploration-floor",
        type=float,
        default=novelty_default("SHARE_FLOOR"),
        help=f"share of the post-floor slots reserved for lineages no run has ever booked "
        f"an admission from, which the share never falls below "
        f"(default: {novelty_default('SHARE_FLOOR')})",
    )
    production.add_argument(
        "--exploration-start",
        type=float,
        default=novelty_default("SHARE_START"),
        help=f"what that share opens at before it has priced itself "
        f"(default: {novelty_default('SHARE_START')})",
    )
    production.add_argument(
        "--exploration-ema",
        type=float,
        default=novelty_default("SHARE_EMA"),
        help=f"per-served-batch smoothing weight for the share's self-pricing "
        f"(default: {novelty_default('SHARE_EMA')})",
    )
    production.add_argument(
        "--no-exploration",
        action="store_true",
        help="allocate the whole post-floor batch by deficit; no protected share",
    )
    production.add_argument(
        "--no-saturation",
        action="store_true",
        help="do not read earlier runs' ledgers; every place ranks as untouched",
    )
    production.add_argument(
        "--no-twins",
        action="store_true",
        help="do not derive Julia parameters from admitted parameter-plane locations; the "
        "three higher-degree Julia partitions then have no channel at all and say so",
    )
    production.add_argument(
        "--root-channel",
        action="append",
        dest="root_channels",
        choices=[proven_default("CHANNEL"), sampler_default("CHANNEL")],
        help=f"draw roots from this channel as well as the partition's own pool; "
        f"repeatable. {proven_default('CHANNEL')!r} roots the walk at every location a human "
        f"has scored a keeper, interleaved with the pool rather than replacing it — on the "
        f"dynamical partitions at the labelled viewport, which is a frame their `c`-pools "
        f"cannot express. {sampler_default('CHANNEL')!r} draws viewports over a PINNED "
        f"plane's own home view at a ladder of scales and keeps the ones the structural "
        f"gates pass, which is the only way a plane with no free parameter gets a fresh "
        f"place at all",
    )
    production.add_argument(
        "--sampler-rungs",
        type=int,
        default=sampler_default("RUNGS"),
        help=f"octaves in from the home width the viewport sampler draws over, each rung a "
        f"2^k x 2^k jittered grid at width home/2^k (default: {sampler_default('RUNGS')}, "
        f"which is {sum(4**k for k in range(1, sampler_default('RUNGS') + 1))} frames). Read "
        f"only with --root-channel {sampler_default('CHANNEL')}",
    )
    production.add_argument(
        "--ledgers",
        default="artifacts",
        help="where earlier runs' ledgers live (default: artifacts)",
    )
    production.add_argument(
        "--colormap",
        default="twilight_shifted",
        help="colormap the gate renders are drawn through. A scored run refuses any map "
        "but the tile pool's floor palette: the head reads the gate render as a tile",
    )
    production.add_argument(
        "--out-dir",
        default=str(Path("artifacts") / "harvest"),
        help="the run directory (default: artifacts/harvest)",
    )
    production.add_argument(
        "--foci",
        action="store_true",
        help="record each expanded node's kept focus set beside its candidates: where the "
        "peaks were, which blurring scales found each one, how alone it stands and how far "
        "the nearest kept neighbour is. Off by default, and a run without it writes the "
        "ledger it always wrote - the set is read either way and this decides only whether "
        "it is kept",
    )
    grace_flag(production)
    scoring_flags(production)
    production.set_defaults(handler=harvest)

    checking = subcommands.add_parser(
        "score-parity",
        help="score one batch of locations serially and through the pool, and compare",
        description=(
            "The scoring pass renders each location's canonical view in worker processes "
            "and reads the batch through the head in the parent. This makes the same views "
            "both ways, into two directories, and compares the bytes and the scores — so a "
            "disagreement is attributable to the render or to the read rather than to "
            "either by elimination."
        ),
    )
    ledger_flags(checking)
    checking.add_argument("--rows", type=int, default=6, help="locations to score both ways")
    checking.add_argument(
        "--out-dir",
        default=str(Path("scratch") / "score_parity"),
        help="where the two arms' views go (default: scratch/score_parity)",
    )
    scoring_flags(checking)
    checking.set_defaults(handler=score_parity)

    reading_locations = subcommands.add_parser(
        "score-locations",
        help="score a list of locations through the shipped location head",
        description=(
            "Everything else that scores locations reads a ledger. This reads a JSONL of "
            "location records and writes one score row apiece — the row a panel that wants "
            "to print P(>=3) under a picture needs. Every row names the sha256 of the "
            "artifact that produced it and the regime it was read at, because heads are "
            "re-shipped and the floors that read them are restated at the flip: a score "
            "that cannot say what produced it goes quietly stale."
        ),
    )
    reading_locations.add_argument(
        "--manifest", required=True, metavar="FILE", help="JSONL of location records"
    )
    reading_locations.add_argument(
        "--out",
        default=str(Path("artifacts") / "location_scores.jsonl"),
        help="where the score rows go (default: artifacts/location_scores.jsonl)",
    )
    reading_locations.add_argument("--limit", type=int, help="score only the first N rows")
    reading_locations.add_argument(
        "--regime",
        default="640x360ss2",
        metavar="WxHssN",
        help="the geometry to read the pictures at (default: 640x360ss2, the deploy view)",
    )
    reading_locations.add_argument(
        "--views", help="where the rendered views are cached (default: the regime's own tree)"
    )
    reading_locations.add_argument(
        "--score-workers",
        type=int,
        default=1,
        help="worker processes rendering the views the head reads (default: 1, which "
        "renders in this process; one render already spends the whole machine)",
    )
    device_flag(reading_locations)
    reading_locations.set_defaults(handler=score_locations)

    seeding = subcommands.add_parser(
        "derive-plane-seeds",
        help="re-derive the tracked parameter-plane seed pool, and check the shipped one",
        description=(
            "Walk a grid over each parameter plane's home frame, identify the atom under "
            "every point, and keep one root per distinct atom spread over periods. Verifies "
            "against the tracked pool by default and writes only with --write: the pool is "
            "shipped data, and the claim it makes is that this procedure still produces it."
        ),
    )
    seeding.add_argument(
        "--columns",
        type=int,
        default=None,
        help=f"grid columns over each home frame (default: {plane_seed_default('COLUMNS')})",
    )
    seeding.add_argument(
        "--per-partition",
        type=int,
        default=None,
        help=f"roots kept per partition (default: {plane_seed_default('PER_PARTITION')})",
    )
    seeding.add_argument(
        "--out", help="path to verify against or write (default: the tracked pool)"
    )
    seeding.add_argument(
        "--write", action="store_true", help="write it; otherwise verify and print the difference"
    )
    seeding.set_defaults(handler=derive_plane_seeds)

    proving = subcommands.add_parser(
        "derive-proven-seeds",
        help="build the proven-label seed set from the label store",
        description=(
            "One root per location a human scored a keeper, on every partition but the "
            "pinned classic phoenix. Not a tracked file: the seed set is a query over the "
            "label store, re-derived whenever it is asked for, and a harvest draws it live "
            "with `--root-channel proven`. Printing one is for reading it, diffing it, or "
            "passing it as --seeds."
        ),
    )
    proving.add_argument(
        "--tier-floor",
        type=int,
        default=None,
        help=f"the label class a location must reach (default: {proven_default('TIER_FLOOR')})",
    )
    proving.add_argument(
        "--partition",
        action="append",
        # Refused at the parser, the way an unregistered channel name is. Without
        # this the subcommand will happily print a seed set for a partition the
        # channel does not serve, and a file no harvest can consume reads exactly
        # like one it can.
        choices=list(proven_default("SERVED")),
        help="derive for this partition alone; repeatable (default: every served partition)",
    )
    proving.add_argument(
        "--out",
        default="artifacts/proven_seeds.jsonl",
        help="where --write puts the seed file (default: artifacts/proven_seeds.jsonl)",
    )
    proving.add_argument("--write", action="store_true", help="write the seed file")
    proving.add_argument(
        "--against",
        help="a seed file to compare the derived set against, by location and not by id",
    )
    proving.set_defaults(handler=derive_proven_seeds)

    standing = subcommands.add_parser(
        "census",
        help="print the standing deficit and the allocation it implies, running nothing",
        description=(
            "Census what every partition holds — human labels, plus discounted machine-scored "
            "finds a human has not looked at — against what the release mix says it is owed, "
            "and show the allocation that follows. Quoted at seed prices, because a price "
            "table is a fact about a run and this is not one."
        ),
    )
    standing.add_argument(
        "--discount",
        type=float,
        help="what an unlabelled machine-scored find is worth against the deficit "
        "(default: 0.2); 0 reproduces the labels-only deficit exactly",
    )
    standing.add_argument("--floor", type=float, default=0.05, help="the per-partition floor")
    standing.add_argument("--prices", help="a cost-to-find seed table other than the shipped one")
    standing.set_defaults(handler=census)

    pricing = subcommands.add_parser(
        "derive-prices",
        help="regenerate the cost-to-find seed table from finished runs",
        description=(
            "Pool the minutes and the currency of every source run, divide once, and write "
            "the measured table. With --regularize, shrink it toward its own median and "
            "write the seed a run is actually handed. Never hand-edit either file: every "
            "constant reaches a shipped table through a regeneration."
        ),
    )
    pricing.add_argument(
        "--run", action="append", required=True, help="a finished run directory (repeatable)"
    )
    pricing.add_argument(
        "--regularize", action="store_true", help="shrink the measured table into a seed"
    )
    pricing.add_argument("--alpha", type=float, default=0.9, help="shrinkage weight in log space")
    pricing.add_argument(
        "--clamp", type=float, default=16.0, help="band the live estimate may occupy"
    )
    pricing.add_argument("--measured", help="path recorded as the regularizer's source")
    pricing.add_argument("--out", help="where to write (default: the shipped table)")
    pricing.add_argument("--write", action="store_true", help="write it; otherwise print it")
    pricing.set_defaults(handler=derive_prices)

    cut = subcommands.add_parser(
        "derive-tau-h",
        help="re-derive the cheap cut from this repository's own walks",
        description=(
            "τ_h is the cut on a cheap score that decides which candidates are worth a "
            "full-resolution confirmation. It is a point on one scorer's probability scale, "
            "so it is derived here and never transferred; a partition with too few good "
            "rows fails open and confirms everything."
        ),
    )
    cut.add_argument("--ledger", action="append", help="a walk ledger (repeatable)")
    cut.add_argument(
        "--keep", type=float, default=0.90, help="fraction of good frames the cut retains"
    )
    cut.add_argument("--out", help="where to write (default: the shipped table)")
    cut.add_argument("--write", action="store_true", help="write it; otherwise print it")
    cut.set_defaults(handler=derive_tau_h)
