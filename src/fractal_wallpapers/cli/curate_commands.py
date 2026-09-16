"""`curate`: the `curate` parser itself, and the verbs no family claimed.

## The cut, and the decision it reverses

This module argued against being split, and the argument was good for as long as
the answer was three files cut along `curation/`'s own doc taxonomy: **registration
order is `--help`**, `argparse` prints the verbs in the order they are added, and
`README.md`'s, `GALLERY.md`'s and `LEGS.md`'s verbs are not contiguous in that
order — nine store verbs sit inside the legs' run alone. A doc-aligned cut cost
either a reordered surface or an `add_commands` faking the old order out of three
modules' registrations, and neither was worth a smaller file.

**What changed is the size, not the argument.** The file reached 6,354 lines and
forty-eight verbs, 28% of it argparse `help=` prose, and `curate` stopped being
one command group under any reading: it is the ledger, the solve, the votes, the
legs and the colour census wearing one hat. So the cut landed on 2026-09-12 along
the **noun** rather than along the docs, which is contiguous almost everywhere —
and the price the old argument named was paid deliberately: `curate --help` now
lists its verbs **grouped by family** instead of in the order they accreted.
`seat-sheet` moved up beside `solve`, `retention` down beside the legs, and
`autolevel` up beside `colors`. Nothing pins that order (`test_nested_verbs.py`
pins each group's verbs against `SURFACE`, which is per group and by set at the
top level), and grouping by noun is the reason the cut was worth making: the
session that found `--no-render` on `solve run` and not on `solve record` spent
four `--help` invocations doing it.

## What is here

The `curate` parser and `steps` themselves, the five `add_steps` calls in the
order they register, and the nine verbs no family claimed: `reject`, `pool-draw`,
`below-bar`, `repeats`, `retire-repeats`, `parity`, `replay`, `label-migration`
and `label-fate`. They stay because each is the only verb of its kind — a
one-verb family per noun would be five more modules to hold eleven handlers.

The families are [`curate_ledger_commands`], [`curate_solve_commands`],
[`curate_votes_commands`], [`curate_mine_commands`] and
[`curate_colors_commands`]. Each is a module the package must resolve handler
names through, so each is named in `cli/__init__.FAMILIES` as well — `GROUPS` is
the list of modules that register a TOP-LEVEL command and a family registers
none.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fractal_wallpapers.cli.common import (
    device_flag,
    resolve_output,
)
from fractal_wallpapers.curation import label_fate as label_fate_module
from fractal_wallpapers.curation import label_migration as label_migration_module


def _kept_classes(args: argparse.Namespace) -> tuple:
    """The human verdict classes a staging verb acts on, off `--classes`."""
    named = getattr(args, "classes", None)
    return label_migration_module.KEPT_CLASSES if not named else tuple(named)


def _population_flag(parser) -> None:
    """`--classes` on one staging verb.

    On `render`, `readout` and `page` and not on `score`: the score stage reads
    whichever rows the render stage staged, so a second spelling of the population
    there is a second answer to what the leg is about.
    """
    parser.add_argument(
        "--classes",
        type=int,
        nargs="+",
        metavar="N",
        help=f"the human verdict classes to act on (default "
        f"{' '.join(str(name) for name in label_migration_module.KEPT_CLASSES)}; a key "
        f"carrying two verdicts is in if either is named)",
    )


def _staging_store(parser) -> None:
    """`--store` on one staging verb.

    On each verb and not on the group, because the group's verb is required: a
    flag declared only above it would have to be typed before the verb, which is
    not how any other verb in this file reads. `census` does not take it — it is a
    census of the pool and writes into no staging store at all.
    """
    parser.add_argument(
        "--store",
        metavar="PATH",
        default=str(label_migration_module.DEFAULT_STORE),
        help=f"the staging store this run owns, under the checkout unless absolute "
        f"(default {label_migration_module.DEFAULT_STORE.as_posix()})",
    )


def curate_label_fate(args: argparse.Namespace) -> int:
    """What became of every wallpaper a person graded 4, one rung at a time."""
    from fractal_wallpapers.curation import label_fate

    store = getattr(args, "store", None)
    doing = {
        "keys": lambda: label_fate.keys(store),
        "population": lambda: label_fate.population(store),
        "fates": lambda: label_fate.fates(args.stamp, store),
        "competitors": lambda: label_fate.competitors(args.stamp, store),
        "render": lambda: label_fate.render(store, workers=args.workers),
        "page": lambda: label_fate.page(
            store,
            migration_store=args.migration_store,
            repaired_seats_of=args.repaired_seats_of,
            against=args.against,
        ),
    }[args.what]
    try:
        report = doing()
    except (label_fate.FateRefused, OSError) as refusal:
        print(refusal)
        return 1
    if getattr(args, "out", None):
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(f"{out}")
        return 0
    print(json.dumps(report, indent=2))
    return 0


def curate_label_migration(args: argparse.Namespace) -> int:
    """Stage the judged recipes at candidate geometry, score them, and read them out."""
    from fractal_wallpapers.curation import label_migration

    store = getattr(args, "store", None)
    doing = {
        "census": lambda: label_migration.census(),
        "derive": lambda: label_migration.derive(store),
        "render": lambda: label_migration.render(
            store, limit=args.limit, workers=args.workers, classes=_kept_classes(args)
        ),
        "score": lambda: label_migration.score(store, device=args.device, batch=args.batch),
        "readout": lambda: label_migration.readout(
            store, stamp=args.stamp, classes=_kept_classes(args)
        ),
        "page": lambda: label_migration.page(store, classes=_kept_classes(args)),
        "merge": lambda: label_migration.merge(store),
    }[args.what]
    try:
        report = doing()
    except (label_migration.MigrationError, OSError) as refusal:
        print(refusal)
        return 1
    if getattr(args, "out", None):
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(f"{out}")
        return 0
    print(json.dumps(report, indent=2))
    return 0


def curate_reject(args: argparse.Namespace) -> int:
    """Apply today's acting release bars to a run that was released before they acted."""
    from fractal_wallpapers.curation import floors, records, rejection

    if args.ephemeral:
        records.use(records.scratch_root(args.run))
    try:
        report = rejection.apply(
            args.run, rejector=args.rejector, date=args.date, dry_run=args.dry_run
        )
    except (rejection.RejectionRefused, floors.HeadStampMismatch) as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    return 0


def curate_pool_draw(args: argparse.Namespace) -> int:
    """Draw a uniform sample of the pool's locations and write a labeling plan."""
    from fractal_wallpapers.curation import pool_draw

    try:
        record = pool_draw.draw(
            n=args.n,
            seed=args.seed,
            directory=resolve_output(args.out),
            like=args.like or (),
            gallery=resolve_output(args.gallery) if args.gallery else None,
        )
    except pool_draw.DrawRefused as refusal:
        print(refusal)
        return 1
    print(json.dumps(record, indent=2))
    return 0


def curate_below_bar(args: argparse.Namespace) -> int:
    """Draw the glance sheet of every served wallpaper an acting bar would take back.

    Report only, and the read to take before `curate reject`: the same rule, the
    same rows, laid out as pictures for the one judgement no head is asked for.
    """
    from fractal_wallpapers.curation import below_bar, records

    if args.ephemeral:
        records.use(records.scratch_root("below_bar"))
    try:
        report = below_bar.write(
            path=Path(args.out) if args.out else None,
            exclude=args.exclude or (),
            reason=args.exclude_reason,
        )
    except ValueError as refusal:
        print(refusal)
        return 1
    print(
        f"{report['below_bar']} served row(s) below an acting bar, {report['shown']} on the "
        f"sheet, {len(report['held_by_ruling'])} held in service by a ruling — "
        f"{report['sheet']}"
    )
    print(json.dumps(report, indent=2))
    return 0


def curate_repeats(args: argparse.Namespace) -> int:
    """List every location the collection has served more than one wallpaper of.

    Report only. The one-wallpaper-per-location rule acts at selection from
    2026-08-22 and cannot reach backwards: these are the pairs the collection
    accumulated while the rule was per-run and at two. `retire-repeats` is what
    settles them, and this is the read to take before and after it.
    """
    from fractal_wallpapers.curation import served_locations

    index = served_locations.build()
    rows = served_locations.repeats(index)
    extra = sum(len(cell["served"]) - 1 for cell in rows)
    print(
        f"{index.summary()['served_rows']} served wallpaper(s), {len(rows)} location(s) "
        f"holding more than one, {extra} wallpaper(s) over the one-per-location rule"
    )
    print(json.dumps(rows, indent=2))
    return 0


def curate_retire_repeats(args: argparse.Namespace) -> int:
    """Retire every wallpaper past the best one at a location, inside each collection."""
    from fractal_wallpapers.curation import records, rejection

    if args.ephemeral:
        records.use(records.scratch_root("retire_repeats"))
    try:
        report = rejection.retire_repeats(
            rejector=args.rejector, date=args.date, dry_run=args.dry_run
        )
    except rejection.RejectionRefused as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    # The pass exists to leave the collection one-per-location. A run of it that
    # wrote rejections and left a group standing has done half a decision, and
    # saying so in the exit code is what stops the next step reading the report
    # as the rule being settled.
    return 0 if report["groups_remaining"] in (0, None) else 1


def curate_parity(args: argparse.Namespace) -> int:
    """Render a real release plan both ways and compare the bytes."""
    from fractal_wallpapers.curation import checks, records

    if args.ephemeral:
        records.use(records.scratch_root(args.run))
    try:
        report = checks.parity(args.run, rows=args.rows, workers=args.workers)
    except checks.CheckError as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    return 0 if report["held"] else 1


def curate_replay(args: argparse.Namespace) -> int:
    """Re-derive every released picture from its own record and compare the bytes."""
    from fractal_wallpapers.curation import checks, records

    if args.ephemeral:
        records.use(records.scratch_root(args.run))
    try:
        report = checks.replay(args.run)
    except (checks.CheckError, FileNotFoundError) as refusal:
        print(refusal)
        return 1
    print(json.dumps({key: report[key] for key in report if key != "detail"}, indent=2))
    for row in report["detail"]:
        print(f"  {row['candidate']}: {row.get('arm', 'no picture')} -> {row['verdict']}")
    return 0 if report["held"] else 1


def add_commands(subcommands) -> None:
    """The last stage: harvest supply in, released wallpapers out."""
    from fractal_wallpapers.cli import (
        curate_atlas_commands,
        curate_colors_commands,
        curate_ledger_commands,
        curate_mine_commands,
        curate_solve_commands,
        curate_veto_commands,
        curate_votes_commands,
    )
    from fractal_wallpapers.curation import below_bar as below_bar_module
    from fractal_wallpapers.curation import pool_draw as pool_draw_module

    curating = subcommands.add_parser(
        "curate",
        help="make a release: score the supply, colorize, select, render at full size",
        description=(
            "The end-to-end path. Every step is bound to the ledgers it reads — name them "
            "with --ledger, or name the harvest that wrote them with --harvest; nothing "
            "defaults to all of them. `score` reads the bound ledgers through the location "
            "head into a sidecar this stage owns, upserting one binding's rows without "
            "touching another's and never rewriting a ledger; `plan` prints the offer and "
            "the budget it implies without making a picture; and `run` does the whole thing, "
            "records its binding in its own plan, and records every decision."
        ),
    )
    steps = curating.add_subparsers(dest="step", required=True)

    # The families, in the order they register — which is the `--help` surface.
    curate_ledger_commands.add_steps(steps)
    curate_solve_commands.add_steps(steps)
    curate_votes_commands.add_steps(steps)
    curate_mine_commands.add_steps(steps)
    curate_colors_commands.add_steps(steps)
    curate_veto_commands.add_steps(steps)
    curate_atlas_commands.add_steps(steps)

    rejecting = steps.add_parser(
        "reject",
        help="apply today's acting release bars to a run released before they acted",
        description=(
            "A rule, not a list: every row this run serves whose head has an ACTING release "
            "bar and which does not clear it is stamped rejected — recorded, dated and "
            "attributed, with nothing deleted and no score touched — and the run's sheet is "
            "redrawn so those rows no longer appear as released. Heads whose cut only "
            "annotates are not touched. Idempotent: a second pass with the same arguments "
            "finds nothing left to do and rewrites the same bytes."
        ),
    )
    rejecting.add_argument("--run", required=True, help="the run to apply the bars to")
    rejecting.add_argument(
        "--rejector",
        required=True,
        help="who is taking these rows back — a person, or the named review standing for one. "
        "An unattributed retraction cannot be told from a bug in the release path",
    )
    rejecting.add_argument(
        "--date", required=True, metavar="YYYY-MM-DD", help="the date of the review verdict"
    )
    rejecting.add_argument(
        "--dry-run", action="store_true", help="print what would be rejected and write nothing"
    )
    rejecting.add_argument(
        "--ephemeral", action="store_true", help="read the run's ephemeral record store"
    )
    rejecting.set_defaults(handler=curate_reject)

    drawing_pool = steps.add_parser(
        "pool-draw",
        help="draw a uniform sample of the pool's locations as a labeling plan",
        description=(
            "The unaimed draw. Every other sheet this project cuts is aimed at a band, a "
            "mode or the top of a queue, and those measure a correction; this one measures a "
            "BASE RATE and so cannot be aimed at anything. The population is every location "
            "holding at least one candidate row that clears its own mode's bar in "
            "`headroom.bars`, read fresh — the same set the census counts as supply. Each "
            "drawn location is represented by the best-ranked clearing row a seating pass "
            "would reach first, so the card carries the picture this project would actually "
            "ship from that place. It writes a finished-render sheet plan and the record of "
            "the draw, and it writes nothing into any label store. It HOLDS THE POOL."
        ),
    )
    drawing_pool.add_argument("--n", type=int, required=True, help="how many locations to draw")
    drawing_pool.add_argument(
        "--seed", type=int, required=True, help="the draw's seed, recorded with it"
    )
    drawing_pool.add_argument(
        "--out",
        default=str(Path("artifacts") / "pool_draw"),
        help="where the plan and its record are written (default: artifacts/pool_draw)",
    )
    drawing_pool.add_argument(
        "--like",
        action="append",
        metavar="ALIAS",
        help="a gallery seat whose neutral embedding seeds the page's prefill, repeatable. "
        f"Under {pool_draw_module.MINIMUM_SEEDS} resolving, the sheet ships unprefilled and "
        "the record says which were lost",
    )
    drawing_pool.add_argument(
        "--gallery",
        help="the tentative gallery directory the --like aliases are resolved against",
    )
    drawing_pool.set_defaults(handler=curate_pool_draw)

    glancing = steps.add_parser(
        "below-bar",
        help="draw the glance sheet of every served wallpaper an acting bar would take back",
        description=(
            "The read to take before `reject`, off the same rule and the same rows: every "
            "wallpaper the collection still serves whose KIND has an ACTING release bar it "
            "does not clear, one row each with the picture, the key, the kind, and the "
            "current score against that kind's floor, best score first. Rows a tracked "
            "ruling holds in service are on the page under their own heading and are not "
            "counted with the rest. It decides nothing, rejects nothing, re-renders nothing "
            "and writes nothing but the sheet."
        ),
    )
    glancing.add_argument(
        "--out",
        metavar="PATH",
        help=f"where to write the sheet (default {below_bar_module.DEFAULT_SHEET.as_posix()})",
    )
    glancing.add_argument(
        "--exclude",
        action="append",
        metavar="RUN|STAGE|CANDIDATE",
        help="drop one row from the sheet by its record key, repeatable. Refuses a key that "
        "is not below the bar today, since a sheet quietly a row short cannot be checked",
    )
    glancing.add_argument(
        "--exclude-reason",
        default="",
        metavar="TEXT",
        help="why those rows were dropped, printed on the sheet beside the keys. An "
        "exclusion is a person's call rather than a rule, so the page carries the call",
    )
    glancing.add_argument("--ephemeral", action="store_true", help="read an ephemeral record store")
    glancing.set_defaults(handler=curate_below_bar)

    repeating = steps.add_parser(
        "repeats",
        help="list every location the collection has served more than one wallpaper of",
        description=(
            "A location is released once, collection-wide (curation.floors.CLUSTER_CAP). "
            "That rule acts at selection and cannot reach backwards, so this is the read of "
            "it against what the collection already holds: every near-duplicate group with "
            "more than one served wallpaper in it, with both heads' scores. It decides "
            "nothing, rejects nothing and writes nothing — `retire-repeats` is the pass "
            "that acts on what this lists."
        ),
    )
    repeating.set_defaults(handler=curate_repeats)

    retiring = steps.add_parser(
        "retire-repeats",
        help="retire every wallpaper past the best one at a location",
        description=(
            "One wallpaper per location acts at selection and cannot reach backwards, so "
            "this applies it once to the collection that predates it. It runs inside ONE "
            "collection at a time, which is where the rule acts: a group holding a run's "
            "diagnostic picture and a gallery seat of the same place is two collections "
            "agreeing about a location, not one collection holding it twice. Each "
            "near-duplicate group keeps the highest P(>=3) on its own head's scale — ties "
            "to the later run — and every other wallpaper of that place is stamped "
            "rejected with the reason "
            "`location_served` and the survivor's key on the row. Nothing is deleted, no "
            "score is touched, and no bar is read: a retired row is a second picture of a "
            "place, not a bad picture. Run `repeats` first to read what it will do."
        ),
    )
    retiring.add_argument(
        "--rejector",
        required=True,
        help="who is taking these rows back — a person, or the named review standing for one. "
        "An unattributed retraction cannot be told from a bug in the release path",
    )
    retiring.add_argument(
        "--date", required=True, metavar="YYYY-MM-DD", help="the date of the review verdict"
    )
    retiring.add_argument(
        "--dry-run", action="store_true", help="print what would be retired and write nothing"
    )
    retiring.add_argument(
        "--ephemeral", action="store_true", help="read and write an ephemeral record store"
    )
    retiring.set_defaults(handler=curate_retire_repeats)

    checking = steps.add_parser(
        "parity",
        help="render a real release plan serially and concurrently, and compare the bytes",
        description=(
            "The concurrent pass claims to produce the same file as the serial one, not "
            "merely equivalent output. This is the only way to know."
        ),
    )
    checking.add_argument("--run", required=True, help="the run whose plan to re-render")
    checking.add_argument("--rows", type=int, default=2, help="how many rows (default: 2)")
    checking.add_argument("--workers", type=int, default=3, help="the concurrent arm's workers")
    checking.add_argument(
        "--ephemeral", action="store_true", help="read the run's ephemeral record store"
    )
    checking.set_defaults(handler=curate_parity)

    replaying = steps.add_parser(
        "replay",
        help="re-derive every released picture from its own record and compare the bytes",
        description=(
            "An in-band row is re-rendered with the operator off and must be identical; an "
            "acting row's stop list is rebuilt from its stamp alone — no image, no "
            "re-measurement — and must render identically."
        ),
    )
    replaying.add_argument("--run", required=True, help="the run to replay")
    replaying.add_argument(
        "--ephemeral", action="store_true", help="read the run's ephemeral record store"
    )
    replaying.set_defaults(handler=curate_replay)

    migrating = steps.add_parser(
        "label-migration",
        help="the judged recipes re-expressed at candidate geometry, staged and read out",
        description=(
            "Every row resolving through both finished-render stores carries the whole "
            "recipe of a picture somebody judged, at 1280x720 ss2. This derives the same "
            "recipe at candidate geometry — geometry changed and nothing else — renders it, "
            "and reads it through the shipped render judge and the fine-tier head. It "
            "STAGES: the six reading verbs write nothing into the candidate ledger, its "
            "score sidecar, the fine head's pool scores or either label store. Merging is a "
            "separate act against a separate decision and it is the seventh verb, `merge`. "
            "Every labelling sitting makes new rows, so each stage is resumable and re-uses "
            "every picture already on disk."
        ),
    )
    migrating.set_defaults(handler=curate_label_migration)
    migration_verbs = migrating.add_subparsers(dest="what", required=True)

    fine_census = migration_verbs.add_parser(
        "census",
        help="how much of the ledger the fine head has read, and what the gap costs",
        description=(
            "Read-only, and about the POOL rather than the corpora. Per mode: the rows, the "
            "ones carrying a p_fine reading, and — the question — how many of the unscored "
            "ones clear their own mode's headroom bar and so would be seatable if scored, "
            "split by whether they still have a picture. The record names the code path "
            "that decides who the fine head runs on."
        ),
    )
    fine_census.add_argument("--out", metavar="PATH", help="write the census there")

    deriving = migration_verbs.add_parser(
        "derive",
        help="every resolved label row as a recipe at candidate geometry",
        description=(
            "Both stores, every label class. Renders nothing. Reports how many derived "
            "recipes the candidate ledger already holds, which is the first key-level "
            "overlap figure this project has taken — the two stores have only ever been "
            "compared by place."
        ),
    )
    _staging_store(deriving)
    deriving.add_argument("--out", metavar="PATH", help="write the record there")

    drawing = migration_verbs.add_parser(
        "render",
        help="draw every derived recipe at candidate geometry",
        description=(
            "Each at its OWN recipe['mode'] and never the routed mode. Levelled like any "
            "candidate, and the levelled colormap is kept beside the picture rather than "
            "swept: defining levelling once at eval resolution is a change somebody intends "
            "to make and these curves are its seed. Resumable — a picture on disk is not "
            "made again and its stamp is carried forward."
        ),
    )
    _staging_store(drawing)
    _population_flag(drawing)
    drawing.add_argument("--limit", type=int, help="render only the first this many recipes")
    drawing.add_argument(
        "--workers",
        type=int,
        default=label_migration_module.WORKERS,
        help=f"engines at once (default {label_migration_module.WORKERS}, this machine's "
        f"render pool)",
    )
    drawing.add_argument("--out", metavar="PATH", help="write the record there")

    reading_both = migration_verbs.add_parser(
        "score",
        help="the shipped render judge and the fine head, both at candidate geometry",
        description=(
            "The existing regime and no second one: every staged picture is 640x360 ss2, "
            "which is what the sidecar holds and what both heads are deployed against. "
            "Nothing is scored at label geometry, nothing is written into pool_scores.jsonl "
            "and rerender.rescore is not touched."
        ),
    )
    _staging_store(reading_both)
    device_flag(reading_both)
    reading_both.add_argument(
        "--batch",
        type=int,
        default=label_migration_module.SCORE_BATCH,
        help=f"pictures per forward pass (default {label_migration_module.SCORE_BATCH})",
    )
    reading_both.add_argument("--out", metavar="PATH", help="write the record there")

    reading_out = migration_verbs.add_parser(
        "readout",
        help="the distributions, the bars, the places, and what a prune would cost",
        description=(
            "Per human label class the shape of both columns; the label-4 rows against "
            "their mode's render-judge bar and the fine bar; where the ones clearing both "
            "stand against a recorded gallery; which judged recipes the candidate path "
            "could produce at all, cross-tabbed by class and by store and split by what "
            "puts a recipe outside, with the gallery's own seats as the control; and what "
            "retention.decide would do to them on arrival. It PRICES the merge and does "
            "not make one."
        ),
    )
    _staging_store(reading_out)
    _population_flag(reading_out)
    reading_out.add_argument(
        "--stamp",
        metavar="STAMP",
        help="the recorded gallery to compare places against (default the latest PUBLISHED)",
    )
    reading_out.add_argument("--out", metavar="PATH", help="write the record there")

    paging = migration_verbs.add_parser(
        "page",
        help="one entry per label-4 verdict: the judged picture beside the candidate",
        description=(
            "Self-contained, pictures beside it, both sides written at one width so the "
            "pair is a comparison at one display size. Sorted by p_fine ascending, so the "
            "rows the pipeline likes least come first."
        ),
    )
    _staging_store(paging)
    _population_flag(paging)
    paging.add_argument("--out", metavar="PATH", help="write the record there")

    merging = migration_verbs.add_parser(
        "merge",
        help="this store's scored rows into the candidate pool, through THE door",
        description=(
            "Every scored row is offered and the ones the pool already holds are NOT "
            "submitted: an upsert replaces a stored row outright, so submitting one would "
            "rewrite a row this leg does not own. What is submitted gains a colour reading, "
            "a home under artifacts/curation/label_migration/<store>/pictures — the "
            "pictures MOVE out of the store — and the live engine build where it can "
            "honestly be named. Then curation.candidate_ledger.merge runs: the flatness "
            "sweep, the retention prune and all four manifests. ONE POOL-HOLDING PROCESS "
            "PER BOX. `gallery-grade score-pool` must run afterwards or the merged rows are "
            "unseatable, pool_scores.jsonl being a one-shot file."
        ),
    )
    _staging_store(merging)
    merging.add_argument("--out", metavar="PATH", help="write the record there")

    fate = steps.add_parser(
        "label-fate",
        help="what became of every GALLERY-GRADE wallpaper a person graded 4, one rung at a time",
        description=(
            "The gallery-grade sitting's own 4s, and since `label-migration merge` every "
            "one of those verdicts is a ledger row BY KEY. So the fate of a graded "
            "wallpaper is exact rather than inferred: off the roster, below the coarse "
            "bar, below the fine bar, refused by a named rule, or seated. THE TWO "
            "FINISHED-RENDER CORPORA CAME OFF THIS PAGE ON 2026-09-09: whether a "
            "coarse-store 4 is a gallery-grade 4 is unanswered, so putting the two "
            "populations on one page asked a fate question of rows whose membership was "
            "itself the open question. `keys` runs BEFORE the solve and writes the "
            "manifest `curate solve record --explain-keys` takes; the rest run after it. "
            "The page puts each graded picture beside whatever holds its place, both "
            "drawn fresh at the geometry a person judged at and a wallpaper ships at — "
            "and says once that p_fine is recognition for every row on it, the "
            "population being the fine head's own corpus."
        ),
    )
    fate.set_defaults(handler=curate_label_fate)
    fate_verbs = fate.add_subparsers(dest="what", required=True)

    fate_keys = fate_verbs.add_parser(
        "keys",
        help="the population's ledger keys, one per line, for `solve --explain-keys`",
        description=(
            "Resolves the gallery-grade store and joins each graded row to its ledger "
            "key, which is `selected_on.candidate` and already IS one — the row was drawn "
            "FROM the pool, so there is no derivation to get wrong. `labeler` is not "
            "read: every row in this store carries `matt`. Reads no ledger and takes "
            "seconds; run it before the solve, because the fate of a row that took no seat "
            "exists only inside the pass that refused it."
        ),
    )
    fate_population = fate_verbs.add_parser(
        "population",
        help="the graded rows joined to the ledger, with rungs 0 to 2 decided",
        description=(
            "THE POOL-HOLDING HALF — it streams the ledger for the population's rows and "
            "reads the score sidecar whole, which is why the rungs are decided once here "
            "and the render and the page never open the store again. Rung 0 is five of "
            "`solve.pool`'s six exclusions read off the ROUTED mode — the veto is the sixth "
            "and cannot fire on a population of 4s — rung 1 is solve.Q4_BAR (the "
            "height score-pool stops reading at) and rung 2 is solve.DEFAULT_FINE_BAR. "
            "Rungs 3 and 4 are left unset for `fates`, because only the solve knows them."
        ),
    )
    fate_fates = fate_verbs.add_parser(
        "fates",
        help="a record's `explained` block into rungs 3 and 4, and the seat at each place",
        description=(
            "REFUSES a record with no `rejection.explained` block, and one whose block does "
            "not name every row here: a rung read off the aggregate refusal columns would "
            "be a guess about which of several rules acted first, and the point of doing "
            "this after the merge is that it no longer has to be one. The seat is matched "
            "on the exact location; a place the record does not hold gets none, and the "
            "card says so rather than leaving a gap."
        ),
    )
    fate_fates.add_argument(
        "--stamp", required=True, help="the tentative record whose fates these are"
    )
    fate_competitors = fate_verbs.add_parser(
        "competitors",
        help="the row whose removal would admit each refused one",
        description=(
            "Pairs every refused card with the row that actually beat it, which for a "
            "`cell_allowance` refusal is NOT the seat standing at its place. The definition "
            "is `rules.State.removals` and is not restated here: `requirements` gives one "
            "set of seated keys per rule the candidate fails, one member of every set has "
            "to leave, and `removals` is their intersection. Where that holds more than one "
            "seat the MARGINAL member is shown — the weakest by this pass's own seating "
            "key, which is the seat a 1-swap ejects first. POOL-HOLDING: it rebuilds the "
            "pass's final state from `solve.pool` and the record's own ceiling, and it "
            "REFUSES unless `counted_refusal` reproduces every refusal the record wrote "
            "down. `another_place_is_the_same_place` is left unpaired on purpose — the "
            "place was folded into a neighbour before any seat existed."
        ),
    )
    fate_competitors.add_argument(
        "--stamp", required=True, help="the tentative record these pairings are against"
    )
    fate_render = fate_verbs.add_parser(
        "render",
        help="every graded picture and every seat beside one, at label geometry",
        description=(
            "One pass over both sides, because they are the same render and drawing them "
            "through two paths would put the difference between the paths into the "
            "comparison the page exists to make. Each render is told the row's WHOLE "
            "recipe — mode_params, curve and palette, all three of them recipe-key members "
            "— and inherits its levelling off the candidate's own stamp rather than "
            "re-measuring at the larger size. Three workers below normal; resumable on the "
            "file, so a killed leg costs the rows it was holding."
        ),
    )
    fate_render.add_argument(
        "--workers",
        type=int,
        default=label_fate_module.WORKERS,
        help=f"engines to drive (default {label_fate_module.WORKERS}, this machine's pool)",
    )
    fate_page = fate_verbs.add_parser(
        "page",
        help="one card per wallpaper, p_fine ascending inside each rung",
        description=(
            "Ascending because the head's largest disagreements with a person come first. "
            "Each card is the graded picture beside the seat holding its place, at one "
            "display width, with the human verdict, both scores, the first refusing rule "
            "where there was one, and the place, mode and palette on each side. The legend "
            "carries a count per rung and the three things that make a column mean less "
            "than it looks."
        ),
    )
    fate_page.add_argument(
        "--migration-store",
        metavar="PATH",
        default=None,
        help="a `label-migration` store whose staged scores stand in where production has "
        "none. A row below the coarse bar was never read by the fine head — that is what "
        "the rung MEANS — so the column would otherwise be blank exactly where the "
        "disagreement is largest. Marked as the migration's reading on every card that "
        "uses one, and never mixed into the pool's column",
    )
    fate_page.add_argument(
        "--repaired-seats-of",
        metavar="STAMP",
        default=None,
        help="a recorded gallery whose VARIED seats a repair leg re-rendered through the "
        "fixed path, so they are not flagged. SUPERSEDED and kept: `mine.make` dropped "
        "`mode_params` until 2026-09-08, and the repair that followed was store-wide — all "
        "10,664 rows the pool held, so `label_fate.REPAIRED_STORE_WIDE` turns the flag off "
        "for everything and this narrows nothing. It is still here because the flag has a "
        "switch: a leg found regressing turns it back on, and then scoping a repair to one "
        "record is again a thing somebody does",
    )
    fate_page.add_argument(
        "--against",
        metavar="PATH",
        default=None,
        help="an earlier store of this same leg. The page then says how many of these "
        "wallpapers changed rung between that store's record and this one, and which way "
        "— forward being further along the rungs before something stopped it, so only a "
        "move to SEATED is a wallpaper that now ships. A rung is a fact about a row AND a "
        "record, so this is the only way the page can say a fate changed rather than that "
        "it was rebuilt",
    )
    for verb in (
        fate_keys,
        fate_population,
        fate_fates,
        fate_competitors,
        fate_render,
        fate_page,
    ):
        verb.add_argument(
            "--store",
            metavar="PATH",
            default=str(label_fate_module.DEFAULT_STORE),
            help=f"the store this reading owns, under the checkout unless absolute "
            f"(default {label_fate_module.DEFAULT_STORE.as_posix()})",
        )
        verb.add_argument("--out", metavar="PATH", help="write the record there")
