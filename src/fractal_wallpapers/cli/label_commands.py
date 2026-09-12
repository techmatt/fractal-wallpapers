"""`label`: register, cut, serve, ingest and pin the human labels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fractal_wallpapers.cli.common import (
    NON_LOCATION_HEADS,
    build_scorer,
    display_path,
    resolve_output,
    scoring_flags,
)
from fractal_wallpapers.labeling import sheets as sheets_module
from fractal_wallpapers.labeling.attributes import NAMES as ATTRIBUTE_NAMES
from fractal_wallpapers.paths import (
    repo_root,
)


def label_stores(head: str):
    """`(read the registry, write one)` for whichever store `head` names.

    One resolution, so `register` and `ingest` cannot disagree about which store
    a head is. An empty head is the location corpus, which is the one store that
    predates the flag.
    """
    from fractal_wallpapers.labeling import attributes, finished, gallery_grade, store

    if not head:
        return store.registry, store.register
    if head in attributes.NAMES:
        return (lambda: attributes.registry(head)), (
            lambda registration: attributes.register(head, registration)
        )
    if head == gallery_grade.NAME:
        return gallery_grade.registry, gallery_grade.register
    return (lambda: finished.registry(head)), (
        lambda registration: finished.register(head, registration)
    )


def label_register(args: argparse.Namespace) -> int:
    """Register a batch's generation method, before it has any rows."""
    from fractal_wallpapers.labeling import registry as registry_module

    registration = registry_module.Registration(
        batch=args.batch,
        method=args.method,
        score_unconditioned=args.score_unconditioned,
        anchored=args.anchored,
        eval_only=args.eval_only,
        why=args.why or "",
    )
    read, write = label_stores(args.head)
    if args.batch in read():
        print(f"batch {args.batch!r} is already registered; a second row would restate it")
        return 1
    row = write(registration)
    eligible = registry_module.registration_of(row).eval_eligible
    print(json.dumps({**row, "head": args.head or "location", "eval_eligible": eligible}, indent=2))
    return 0


def label_build(args: argparse.Namespace) -> int:
    """Cut a labeling sheet and render every unit of it."""
    from fractal_wallpapers.labeling import attributes, gallery_grade, sheets

    if args.head and not args.from_plan:
        print(
            "--head names a store other than the location corpus, and those sheets are cut "
            "from --from-plan"
        )
        return 1
    if args.reuse_renders and not args.head:
        print("--reuse-renders reads a finished-render cache, so it needs --head")
        return 1

    if args.head in attributes.NAMES:
        units = sheets.units_from_plan(resolve_output(args.from_plan))
        # PAIRED or not is the attribute's own answer and never a flag: a unit of
        # a paired store is two renders composited into one tile, and a page that
        # could be asked for the wrong shape would serve one half of every
        # comparison. See `attributes.Attribute.paired`.
        if attributes.attribute(args.head).paired:
            if args.reuse_renders:
                print(
                    f"--reuse-renders reads a finished-render cache and {args.head!r} is a "
                    "paired store: a comparison tile is a composite of two renders and the "
                    "cache holds neither composites nor the variant half's recipe"
                )
                return 1
            source = sheets.comparison_source(
                args.head,
                resolution=tuple(args.resolution),
                supersample=args.supersample,
            )
        else:
            source = sheets.attribute_source(
                args.head,
                resolution=tuple(args.resolution),
                supersample=args.supersample,
                reuse_cache=args.reuse_renders,
            )
    elif args.head == gallery_grade.NAME:
        units = sheets.units_from_plan(resolve_output(args.from_plan))
        # Blind or correction is the PLAN's answer and never a second flag's: the
        # prefill on this page is the fine head's decode read at candidate
        # geometry, so it can only come off the plan, and a flag that could
        # disagree with it is a flag that eventually does. `sheets.build` reads
        # `suggested_by` off the same test.
        source = sheets.gallery_grade_source(
            resolution=tuple(args.resolution),
            supersample=args.supersample,
            reuse_cache=args.reuse_renders,
            prefilled=any(unit.get("suggestion") is not None for unit in units),
        )
    elif args.head:
        units = sheets.units_from_plan(resolve_output(args.from_plan))
        source = sheets.finished_source(
            args.head,
            seed=args.seed,
            resolution=tuple(args.resolution),
            supersample=args.supersample,
            reuse_cache=args.reuse_renders,
            order_by=args.order_by,
        )
    else:
        if args.from_plan:
            units = sheets.units_from_location_plan(resolve_output(args.from_plan))
        elif args.from_ledger:
            units = sheets.units_from_ledger(
                resolve_output(args.from_ledger), admitted_only=args.admitted_only
            )
        else:
            units = sheets.units_from_batch(args.from_batch)
        # The same builder the walk and the harvest consult, so the judge that
        # prefills a correction sheet is the judge that scored the ledger it was
        # cut from — and `--no-scoring` is the one way to a blind page.
        source = sheets.location_source(
            scorer=build_scorer(args),
            resolution=tuple(args.resolution),
            supersample=args.supersample,
        )
    if args.limit:
        units = units[: args.limit]
    if not units:
        print("no units: there is nothing to judge")
        return 1

    # Every batch a row will LAND in, which on a revision sheet is the batch each
    # unit came out of and not the sheet's own name. Checked after the units are
    # read and before a pixel is rendered.
    known = label_stores(args.head)[0]()
    unregistered = sorted({unit.get("batch") or args.batch for unit in units} - set(known))
    if unregistered:
        head = f" --head {args.head}" if args.head else ""
        print(f"not registered: {unregistered}; register a batch before its rows exist:")
        print(f"  fractal-wallpapers label register --batch {unregistered[0]} --method '...'{head}")
        return 1

    sheet = sheets.build(
        source,
        units,
        directory=resolve_output(args.out_dir),
        batch=args.batch,
        seed=args.seed,
        title=args.title,
    )
    print(json.dumps(sheet.manifest, indent=2))
    return 0


def sheet_identity(manifest: dict, units: int) -> str:
    """What a sheet is, said the one way both `label sheets` and `label serve` say it."""
    batch = manifest.get("batch") or "(no batch)"
    return f"{manifest.get('head', '?')} · {batch} · {units} units"


def label_sheets(args: argparse.Namespace) -> int:
    """Print every built sheet under a directory: where it is, and what it holds.

    A sheet's directory name is chosen by whoever cut it and need not be the
    batch inside it, so the only authority on what a directory holds is its own
    manifest. Without this, finding a sheet to serve means opening them by hand.
    """
    from fractal_wallpapers.labeling import sheets, store

    root = resolve_output(args.under)
    if not root.is_dir():
        print(f"{display_path(root)} is not a directory")
        return 1
    found = 0
    for manifest_path in sorted(root.rglob(sheets.MANIFEST_NAME)):
        directory = manifest_path.parent
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as unreadable:
            # One unreadable manifest is not a reason to hide the others.
            print(f"{display_path(directory)}  unreadable: {unreadable}")
            found += 1
            continue
        units = manifest.get("units")
        if units is None:
            units = sum(1 for _ in (directory / sheets.ROWS_NAME).open(encoding="utf-8"))
        print(f"{display_path(directory):34}  {sheet_identity(manifest, units)}")
        if args.drops:
            try:
                drop = display_path(store.export_path(manifest.get("head", ""), manifest["batch"]))
            except (store.LabelError, KeyError) as unnamed:
                # A sheet whose manifest cannot name a drop is worth listing anyway.
                drop = f"(none: {unnamed})"
            print(f"{'':34}  labels -> {drop}")
        found += 1
    if not found:
        print(f"no sheet under {display_path(root)}")
    return 0


def label_serve(args: argparse.Namespace) -> int:
    """Serve a built sheet to a browser on this machine."""
    from fractal_wallpapers.labeling import server, sheets, store

    directory = resolve_output(args.sheet)
    sheet = sheets.read(directory)  # refuse a directory that is not a sheet, before binding a port
    manifest = sheet.manifest
    # What a labeler actually needs to know before typing into the page: which
    # sheet this is, and where their verdicts will land when they save.
    drop = store.export_path(manifest["head"], manifest.get("batch", ""))
    banner = [
        sheet_identity(manifest, len(sheet.rows)),
        f"labels -> {display_path(drop)}",
    ]
    return server.serve(directory, host=args.host, port=args.port, banner=banner)


def label_ingest(args: argparse.Namespace) -> int:
    """Resolve a sheet's export into store rows, through the one writer."""
    from fractal_wallpapers.labeling import intake

    report = intake.run(
        sheet=resolve_output(args.sheet),
        labels=args.labels,
        labeler=args.labeler,
        write=args.write,
    )
    print(json.dumps(report, indent=2))
    return 0


def label_pin(args: argparse.Namespace) -> int:
    """Reserve part of an attribute sitting's own units as its evaluation side."""
    import random

    from fractal_wallpapers.labeling import attributes, sheets, store

    try:
        units = sheets.units_from_plan(resolve_output(args.from_plan))
    except sheets.SheetError as refusal:
        print(refusal)
        return 1
    if args.reserve > len(units):
        print(f"asked to reserve {args.reserve} of {len(units)} units; there are not that many")
        return 1

    indices = sorted(random.Random(args.seed).sample(range(len(units)), args.reserve))
    try:
        rows = [
            attributes.pin_row({**units[index], "batch": units[index].get("batch") or args.batch})
            for index in indices
        ]
    except attributes.AttributeRefused as refusal:
        print(refusal)
        return 1
    places = {repr(attributes.place_of(row)) for row in rows}
    if len(places) != len(rows):
        print(
            f"{len(rows)} reserved units sit on {len(places)} distinct locations. The pin is "
            f"asserted on the place, so a duplicate is a unit that reserves nothing."
        )
        return 1

    recipe = {
        "schema": attributes.SCHEMA,
        "rule": (
            "a seeded uniform draw over this sitting's own units, taken BEFORE any verdict "
            "exists. The reservation is intra-batch: `eval_only` is a flag on a batch and a "
            "second batch would print a second name on the reserved cards, telling the "
            "labeler which ones they were"
        ),
        "attribute": args.head,
        "batch": args.batch,
        "seed": args.seed,
        "plan": tracked_or_given(args.from_plan),
        "units": len(units),
        "reserved": len(rows),
        "realized_eval_share": round(len(rows) / len(units), 4) if units else 0.0,
        "drawn_at": store.now(),
    }
    if not args.write:
        print(json.dumps({**recipe, "note": "dry run — pass --write to ship the pin"}, indent=2))
        return 0
    members, document = attributes.write_pin(args.head, rows, recipe)
    print(json.dumps({**recipe, "eval_split": str(members), "split": str(document)}, indent=2))
    return 0


def tracked_or_given(path: str) -> str:
    """A path as a record should carry it: repository-relative where it is inside one."""
    try:
        return Path(path).resolve().relative_to(repo_root()).as_posix()
    except ValueError:
        return str(path)


def label_show(args: argparse.Namespace) -> int:
    """Print what the store currently says, resolved."""
    from collections import Counter

    from fractal_wallpapers.labeling import pins, store
    from fractal_wallpapers.labeling import registry as registry_module
    from fractal_wallpapers.labeling import split as split_module
    from fractal_wallpapers.supply.partitions import partition_of_family

    del args
    resolution = store.resolved()
    scored = resolution.scored()
    keys = pins.pinned()
    print(
        json.dumps(
            {
                "store": resolution.summary(),
                "registry": registry_module.summary(store.registry()),
                "scores": {
                    str(score): sum(1 for row in scored if row["score"] == score)
                    for score in store.SCORES
                },
                "partitions": dict(
                    sorted(Counter(partition_of_family(row["family"]) for row in scored).items())
                ),
                "batches": dict(sorted(Counter(row["batch"] for row in scored).items())),
                "eval_side": {"pinned_locations": len(keys), "recipe": split_module.recipe()},
            },
            indent=2,
        )
    )
    return 0


def label_split(args: argparse.Namespace) -> int:
    """Re-derive the train/evaluation split, keeping every pin that already exists."""
    from fractal_wallpapers.labeling import pins, store
    from fractal_wallpapers.labeling import split as split_module

    resolution = store.resolved()
    drawn = split_module.derive(
        resolution.scored(),
        known=store.registry(),
        seed=args.seed,
        share=args.share,
        pinned=pins.pinned(),
    )
    if args.write:
        members, recipe = split_module.write(drawn)
        print(f"wrote {members} and {recipe}")
    print(json.dumps(drawn.recipe(), indent=2))
    if not args.write:
        print("(dry run - pass --write to ship it)")
    return 0


def add_commands(subcommands) -> None:
    """The labeling rig: register a batch, cut a sheet, serve it, record it, split it."""
    labelling = subcommands.add_parser(
        "label",
        help="collect human verdicts: register, build, sheets, serve, ingest, show, split",
        description=(
            "The labeling rig and the store behind it. A batch is registered before it has "
            "rows, a sheet is cut from a walk's ledger or from a batch already stored, the "
            "page is served locally, and what comes back is recorded through the one writer."
        ),
    )
    steps = labelling.add_subparsers(dest="step", required=True)

    registering = steps.add_parser(
        "register",
        help="register a batch's generation method, before it has any rows",
        description=(
            "Say how a population was drawn, while that is still knowable. Two flags decide "
            "whether anything measured on it can be read as a rate about the world: whether "
            "a model score was in the draw, and whether the page anchored the labels to a "
            "head's own verdict. Eval-eligibility follows from the two and is never stored."
        ),
    )
    registering.add_argument("--batch", required=True, help="the name its rows will carry")
    registering.add_argument("--method", required=True, help="how the population was drawn")
    registering.add_argument(
        "--head",
        choices=list(NON_LOCATION_HEADS),
        help="register in a finished-render, location-attribute or gallery-grade store "
        "instead of the location store",
    )
    registering.add_argument(
        "--score-unconditioned",
        action="store_true",
        help="no model score anywhere in the selection (a systematic draw qualifies)",
    )
    registering.add_argument(
        "--anchored",
        action="store_true",
        help="the page serves a head's own verdict prefilled, or orders rows by its score",
    )
    registering.add_argument(
        "--eval-only",
        action="store_true",
        help="bought as an instrument: pinned to the evaluation side and never trainable",
    )
    registering.add_argument("--why", help="the sentence a later reader will need")
    registering.set_defaults(handler=label_register)

    building = steps.add_parser(
        "build",
        help="cut a sheet and render every unit of it",
        description=(
            "One generator, two row sources. A LOCATION sheet asks whether a place is worth "
            "rendering and renders each unit twice — through the canonical colormap, which is "
            "what a head sees, and through the vivid one, which is what a person judges from, "
            "both named maps in the committed library. A FINISHED-RENDER sheet asks whether a "
            "picture is worth keeping and renders each unit once, through its own whole recipe, "
            "at the geometry both corpora were collected at. Either way the suggestions are the "
            "shipped judge's own decode, the page reads good→bad by its score, and the sheet "
            "is a manifest, a row file carrying every unit's whole join, and a page that serves "
            "the file order and never reshuffles."
        ),
    )
    source = building.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--from-ledger", help="a walk ledger; its admitted candidates are the units"
    )
    source.add_argument("--from-batch", help="a batch already in the store, to judge again")
    source.add_argument(
        "--from-plan",
        help="a JSONL of units — the population somebody selected. Finished-render units with "
        "--head, locations without it; either way the selection is the caller's and is "
        "recorded in the batch's registration",
    )
    building.add_argument(
        "--head",
        choices=list(NON_LOCATION_HEADS),
        help="the store a --from-plan sheet is cut for: a finished-render judge, a location "
        "attribute, or the gallery grade",
    )
    building.add_argument(
        "--admitted-only",
        action="store_true",
        help="cut to what the scorer admitted rather than to everything the gates passed; "
        "empty until a head exists, because admission needs a score",
    )
    building.add_argument(
        "--batch",
        required=True,
        help="the registered batch the rows land in, and what the page keys its saved session "
        "on. A plan unit may name its own batch — a revision sheet re-serves rows from several "
        "at once and each keeps its registration — and then this is only the sheet's name",
    )
    building.add_argument("--seed", type=int, default=0, help="the presentation seed (default: 0)")
    building.add_argument("--limit", type=int, help="cut the sheet to this many units")
    building.add_argument("--title", default="", help="what the page calls itself")
    building.add_argument(
        "--resolution",
        nargs=2,
        type=int,
        metavar=("W", "H"),
        default=[1280, 720],
        help="render size (default: 1280 720, what both finished corpora were collected at)",
    )
    building.add_argument("--supersample", type=int, default=2, help="samples per pixel, per axis")
    building.add_argument(
        "--reuse-renders",
        action="store_true",
        help="take a unit's picture off this head's render cache where the cache already holds "
        "that exact spec, instead of rendering it again. The cache names a picture by a digest "
        "of everything the engine is told, so a hit is the same picture",
    )
    building.add_argument(
        "--order-by",
        choices=list(sheets_module.ORDERINGS),
        default="rank",
        help="which reading a FINISHED-RENDER page is ordered good-to-bad by: `rank`, the "
        "head's expected tier over the whole scale (default), or `top`, its last cutpoint "
        "alone — which is what separates rows at the good end of a page, where the "
        "cutpoint below it is saturated",
    )
    building.add_argument(
        "--out-dir",
        default=str(Path("artifacts") / "sheet"),
        help="where the sheet is built (default: artifacts/sheet)",
    )
    scoring_flags(building)
    building.set_defaults(handler=label_build)

    listing_sheets = steps.add_parser(
        "sheets",
        help="list the built sheets, with what each one holds",
        description=(
            "A sheet's directory name is chosen by whoever cut it and does not have to be "
            "the batch inside it, so the only authority on what a directory holds is its own "
            "manifest. This reads them, so that finding a sheet to serve is a command rather "
            "than opening candidates by hand."
        ),
    )
    listing_sheets.add_argument(
        "--under", default="artifacts", help="where to look (default: artifacts)"
    )
    listing_sheets.add_argument(
        "--drops", action="store_true", help="also print where each sheet's labels would land"
    )
    listing_sheets.set_defaults(handler=label_sheets)

    serving = steps.add_parser(
        "serve",
        help="serve a built sheet to a browser on this machine",
        description=(
            "Binds exclusively, so a second launcher fails instead of silently co-hosting the "
            "port and serving half the images out of the wrong directory."
        ),
    )
    serving.add_argument("--sheet", required=True, help="a built sheet directory")
    serving.add_argument("--host", default="127.0.0.1", help="address to bind (default: loopback)")
    serving.add_argument("--port", type=int, default=8010, help="first port to try (default: 8010)")
    serving.set_defaults(handler=label_serve)

    ingesting = steps.add_parser(
        "ingest",
        help="resolve a sheet's export into store rows — the one path into either store",
        description=(
            "The seam between a sheet that lives somewhere untracked and a store that has to "
            "outlive it. Each exported unit is joined to its sheet row here, once, and lands "
            "as a row carrying the whole join — the place for a location, and the place with "
            "the mode, its own settings, its curve, the map, every knob of the palette pass "
            "and the geometry for a finished render. The sheet says which judge it was cut "
            "for and that decides which store it lands in. Only units the page exported become "
            "labels: a suggestion the labeler never reviewed is absent from that file and "
            "cannot reach a store as a verdict. Both counts are checked in both directions, "
            "nothing already stored is written twice, a verdict that changed is a new row "
            "rather than an edit, and the evaluation pin is asserted after the write."
        ),
    )
    ingesting.add_argument(
        "--sheet", required=True, help="a built sheet directory, or a manifest, rows or stem"
    )
    ingesting.add_argument(
        "--labels",
        help="the export to read (default: labels/<head>.<sheet>.json, where this "
        "sheet's page saves)",
    )
    ingesting.add_argument("--labeler", required=True, help="who cast the verdicts")
    ingesting.add_argument("--write", action="store_true", help="append; otherwise print the plan")
    ingesting.set_defaults(handler=label_ingest)

    pinning = steps.add_parser(
        "pin",
        help="reserve part of an attribute sitting's own units as its evaluation side",
        description=(
            "A seeded uniform draw over a plan's units, written to the attribute store's own "
            "`eval_split.jsonl` BEFORE the sitting starts. It exists because `eval_only` is a "
            "flag on a BATCH and a sitting that reserves a fifth of itself has no second batch "
            "to hang it on — putting the reserved units in one would print a different batch "
            "name on their cards and tell the labeler exactly which ones they were. Reserving "
            "is not withholding: the verdicts on these places are collected like any others, "
            "and what the pin forbids is TRAINING on them."
        ),
    )
    pinning.add_argument(
        "--head", required=True, choices=list(ATTRIBUTE_NAMES), help="the attribute store"
    )
    pinning.add_argument("--from-plan", required=True, help="the sitting's plan")
    pinning.add_argument(
        "--batch", required=True, help="the batch a unit that names none falls back to"
    )
    pinning.add_argument("--reserve", type=int, required=True, help="how many units to reserve")
    pinning.add_argument("--seed", type=int, required=True, help="the reservation's seed")
    pinning.add_argument("--write", action="store_true", help="ship it; otherwise print it")
    pinning.set_defaults(handler=label_pin)

    showing = steps.add_parser("show", help="print what the store currently says, resolved")
    showing.set_defaults(handler=label_show)

    splitting = steps.add_parser(
        "split",
        help="re-derive the train/evaluation split, keeping every pin that exists",
        description=(
            "A seeded draw over location groups. A group reaches the evaluation side only if "
            "every location in it is eval-eligible, and a location already pinned there is "
            "never released — re-deriving adds, and only adds."
        ),
    )
    splitting.add_argument("--seed", type=int, default=0, help="the draw's seed (default: 0)")
    splitting.add_argument(
        "--share", type=float, default=0.20, help="target share of locations on the evaluation side"
    )
    splitting.add_argument("--write", action="store_true", help="ship it; otherwise print it")
    splitting.set_defaults(handler=label_split)
