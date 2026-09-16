"""`curate`'s supply half: the ledgers, the sidecars, and the candidate pool.

Everything here answers a question about what the pool HOLDS rather than about
which of it ships. Three shapes, and the file is in registration order:

* **The read.** `score` puts the bound harvest ledgers through the location head
  into the sidecar this stage owns, `rescore` and `redraw` re-read it, `embed`,
  `spiral-scores`, `neighbours` and `reach` derive over it, and `plan` and `run`
  drive the whole path.
* **The durables.** `sidecar`, `amendments`, `frames`, `embeddings` and
  `candidate-ledger` each carry a record/check/restore trio through
  [`common.keeping_verbs`], because each names a file under the regenerable tree
  that the checkout cannot regenerate.
* **The pool itself.** `candidate-ledger` is the big one: fifteen verbs over the
  ledger a hundred million rows of mining wrote, including the orphan sweep and
  the seat ratchet.

Cut out of `curate_commands` on 2026-09-12 with four sibling families; that
module's docstring carries the reversal and what it cost.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fractal_wallpapers.cli.common import (
    declared_ledgers,
    device_flag,
    display_path,
    keeping_verbs,
    ledger_flags,
    resolve_output,
    write_tracked_json,
)


def curate_score(args: argparse.Namespace) -> int:
    """Read the harvest ledgers through the location head, into curation's sidecar."""
    from fractal_wallpapers.curation import binding, intake

    try:
        report = intake.score(
            declared_ledgers(args),
            device=args.device,
            limit=args.limit,
            keys=intake.read_keys(resolve_output(args.key_file)) if args.key_file else None,
            unscored=args.unscored,
            opened=args.opened,
            graded=args.graded,
        )
    except (binding.Unbound, intake.IntakeError) as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    return 0


def curate_sidecar(args: argparse.Namespace) -> int:
    """Record, check or restore the supply sidecar against its tracked manifest."""
    from fractal_wallpapers.curation import durability, durables

    durable = durables.sidecar()
    doing = {
        "save": lambda: durability.save(durable),
        "check": lambda: durability.check(durable),
        "restore": lambda: durability.restore(durable, force=args.force),
    }[args.what]
    try:
        report = doing()
    except durability.DurableLost as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    # `check` is the one that answers a yes/no question, so it is the one with an
    # exit code worth reading. A short or missing sidecar is a build failure.
    if args.what == "check" and report.get("verdict") in {"short", "missing"}:
        return 1
    return 0


def curate_amendments(args: argparse.Namespace) -> int:
    """Record, check or restore the score amendment against its tracked manifest."""
    from fractal_wallpapers.curation import amend, durability

    durable = amend.durable()
    doing = {
        "save": lambda: durability.save(durable),
        "check": lambda: durability.check(durable),
        "restore": lambda: durability.restore(durable, force=args.force),
    }[args.what]
    try:
        report = doing()
    except durability.DurableLost as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    if args.what == "check" and report.get("verdict") in {"short", "missing"}:
        return 1
    return 0


def curate_frames(args: argparse.Namespace) -> int:
    """Record, check or restore the hunt frame index against its tracked manifest."""
    from fractal_wallpapers.curation import durability, hunt

    durable = hunt.frames_durable()
    doing = {
        "save": lambda: durability.save(durable),
        "check": lambda: durability.check(durable),
        "restore": lambda: durability.restore(durable, force=args.force),
    }[args.what]
    try:
        report = doing()
    except durability.DurableLost as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    if args.what == "check" and report.get("verdict") in {"short", "missing"}:
        return 1
    return 0


def curate_mass_sweep_extend(args: argparse.Namespace) -> int:
    """Render the panel for every drawable map with no colour-mass row, and append it."""
    from fractal_wallpapers import paths
    from fractal_wallpapers.curation import mode_policy
    from fractal_wallpapers.palettes import color_mass, mass_sweep

    maps = mass_sweep.unmeasured_maps() if not args.maps else list(args.maps)
    modes = list(args.modes) if args.modes else list(mode_policy.accepted())
    print(f"[mass-sweep] {len(maps)} map(s) with no row, {len(modes)} mode(s) offered")
    if not maps:
        print("[mass-sweep] nothing to measure; every drawable map has a row")
        return 0
    workdir = Path(args.workdir) if args.workdir else paths.under("curation", "palette_mass_sweep")
    try:
        rows, report = mass_sweep.run(
            maps,
            modes,
            workdir=Path(workdir) / "extend",
            workers=args.workers,
            budget=args.budget,
        )
        if report["modes_left"] and not args.partial:
            # The map is complete over its roster by construction and
            # `test_palette_color_mass` asserts it — every group in every measured
            # mode. A budget that cut the tail of the roster would put the new
            # groups in some files and not others, which is exactly that hole. So
            # a short run reports its prices and writes nothing.
            print(
                f"[mass-sweep] stopped with {len(report['modes_left'])} mode(s) unmeasured "
                f"({', '.join(report['modes_left'])}); appending would leave the grid with a "
                f"hole. Nothing written. --partial says do it anyway."
            )
            args.dry_run = True
        if not args.dry_run:
            report["log"] = mass_sweep.append(rows)
            report["saved"] = color_mass.save_sweep_log(log=lambda _line: None)
    except (mass_sweep.MassSweepError, color_mass.ColorMassError, OSError) as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    return 0


def curate_mass_sweep(args: argparse.Namespace) -> int:
    """Record, check or restore the colour-mass sweep log against its tracked manifest."""
    from fractal_wallpapers.curation import durability
    from fractal_wallpapers.palettes import color_mass

    doing = {
        "save": lambda: color_mass.save_sweep_log(),
        "check": lambda: color_mass.check_sweep_log(),
        "restore": lambda: color_mass.restore_sweep_log(force=args.force),
    }[args.what]
    try:
        report = doing()
    except durability.DurableLost as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    # `missing` is not a failure here the way it is for the sidecar: the log is
    # archived on purpose and a checkout with no local copy is the resting state.
    # `short` still is — a truncated log would cut a different map.
    if args.what == "check" and report.get("verdict") == "short":
        return 1
    return 0


def curate_redraw(args: argparse.Namespace) -> int:
    """Re-render every stale location view and amend the score read off it."""
    from fractal_wallpapers import engine_fingerprint
    from fractal_wallpapers.curation import amend

    try:
        report = amend.refresh(device=args.device, limit=args.limit, resume=not args.no_resume)
    except (amend.AmendError, engine_fingerprint.FingerprintError) as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    return 0


def curate_embed(args: argparse.Namespace) -> int:
    """Embed every admitted location the neutral-render store does not hold yet."""
    from fractal_wallpapers.curation import embeddings, neutral

    try:
        report = embeddings.build(
            limit=args.limit,
            device=args.device,
            sample=args.sample,
            seed=args.seed,
            unit_seconds=args.unit_seconds,
        )
    except (embeddings.StoreRefused, neutral.NeutralError) as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    # A store short of its population is a gallery pass that silently cannot
    # choose the locations it is missing, so the count is the exit code.
    return 0 if report["complete"] else 1


def curate_embeddings(args: argparse.Namespace) -> int:
    """Record, check or restore the embedding store against its tracked manifest."""
    from fractal_wallpapers.curation import durability, embeddings

    which = embeddings.store()
    doing = {
        "save": lambda: durability.save(which),
        "check": lambda: durability.check(which),
        "restore": lambda: durability.restore(which, force=args.force),
    }[args.what]
    try:
        report = doing()
    except durability.DurableLost as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    if args.what == "check" and report.get("verdict") in {"short", "missing"}:
        return 1
    return 0


def curate_spiral_scores(args: argparse.Namespace) -> int:
    """Score every embedded location through the shipped spiral probe, or keep the store."""
    from fractal_wallpapers.curation import durability, spiral_scores

    if args.what == "build":
        try:
            report = spiral_scores.build(limit=args.limit)
        except spiral_scores.StoreRefused as refusal:
            print(refusal)
            return 1
        print(json.dumps(report, indent=2))
        return 0

    which = spiral_scores.store()
    doing = {
        "save": lambda: durability.save(which),
        "check": lambda: durability.check(which),
        "restore": lambda: durability.restore(which, force=args.force),
    }[args.what]
    try:
        report = doing()
    except durability.DurableLost as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    if args.what == "check" and report.get("verdict") in {"short", "missing"}:
        return 1
    return 0


def curate_neighbours(args: argparse.Namespace) -> int:
    """The cheap sanity read: nearest neighbours by cosine, with their pictures."""
    from fractal_wallpapers.curation import embeddings

    try:
        report = embeddings.neighbours(k=args.k, sample=args.sample, seed=args.seed)
    except embeddings.StoreRefused as refusal:
        print(refusal)
        return 1
    print(f"{report['rows']:,} embedded locations; pictures under {report['pictures']}")
    spread = report["background"]
    print(
        f"background cosine over {spread['pairs']:,} random pairs: "
        f"min {spread['min']:.3f}, p01 {spread['p01']:.3f}, median {spread['median']:.3f}, "
        f"p99 {spread['p99']:.3f}, max {spread['max']:.3f}"
    )
    for cell in report["sample"]:
        print(f"\n{cell['partition']:<18} {cell['picture']}  {cell['key']}")
        for near in cell["nearest"]:
            print(
                f"  {near['cosine']:.4f}  {near['partition']:<18} {near['picture']}  {near['key']}"
            )
    return 0


def curate_reach(args: argparse.Namespace) -> int:
    """Which judged locations the gallery pass cannot select, and why."""
    from fractal_wallpapers.curation import embeddings, intake

    pool = embeddings.judged_pool()
    report = embeddings.unreachable(pool)
    if args.write:
        where = resolve_output(args.write)
        cell = report["absent_from_the_sidecar"]
        rows = intake.key_manifest(
            {"key": key, "partition": pool.get(key, "")} for key in cell["keys"]
        )
        where.parent.mkdir(parents=True, exist_ok=True)
        with where.open("w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"wrote {len(rows)} unreachable key(s) to {display_path(where)}")
    print(
        f"{report['judged']} judged locations; {report['admitted']} are in the admitted "
        f"population the gallery pass selects over"
    )
    for cause in ("below_the_junk_floor", "absent_from_the_sidecar"):
        cell = report[cause]
        print(f"{cell['count']:>5}  {cause.replace('_', ' ')}")
        if args.keys:
            for key in cell["keys"]:
                print(f"       {pool.get(key, '?'):<18} {key}")
    return 0


def curate_ledgers(args: argparse.Namespace) -> int:
    """Which walk ledger each released row names, and whether it still resolves."""
    from fractal_wallpapers.curation import durability

    report = durability.pool_ledgers()
    for cell in report["ledgers"]:
        where = f"{cell['tier']} tier" if cell["resolves"] else "NOT FOUND"
        print(f"{cell['rows']:>6}  {cell['ledger']:<44}  {where}  {','.join(cell['runs'])}")
    print(
        f"{report['pool_rows']:,} released rows name {report['ledgers_named']} ledger(s); "
        f"{report['ledgers_absent']} do not resolve, holding "
        f"{report['rows_on_absent_ledgers']:,} row(s)"
    )
    if args.write:
        write_tracked_json(durability.provenance_path(), report)
        print(f"wrote {display_path(durability.provenance_path())}")
    return 0


def curate_rescore(args: argparse.Namespace) -> int:
    """Read every candidate the pool holds through today's finished-render heads."""
    from fractal_wallpapers.curation import floors, rescore

    try:
        report = rescore.run(device=args.device)
    except (rescore.RescoreError, floors.HeadStampMismatch) as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    return 0


def curate_re_render(args: argparse.Namespace) -> int:
    """Put back every pool candidate render that is not on disk."""
    from fractal_wallpapers.curation import rescore

    report = rescore.re_render(limit=args.limit, workers=args.workers)
    print(json.dumps(report, indent=2))
    return 1 if report["failed"] or report["refused_count"] else 0


def drawn_modes(args: argparse.Namespace):
    """The mode table this invocation asks for, or `None` for curation's own.

    Only the strange judge's count is on the command line: the smooth judge owns
    one coloring, so a second draw at a location would render the same picture,
    and a table with a knob for it would be a knob nobody may turn.
    """
    from fractal_wallpapers.curation import budget

    if args.strange_modes is None:
        return None
    return {budget.SMOOTH: 1, budget.STRANGE: args.strange_modes}


def curate_plan(args: argparse.Namespace) -> int:
    """Print the offer and the budget it implies, making no picture."""
    from fractal_wallpapers.curation import binding, budget, floors, intake

    try:
        offer, supply = intake.ranked(declared_ledgers(args))
    except (binding.Unbound, intake.IntakeError) as refusal:
        print(refusal)
        return 1
    claims = intake.guaranteed(supply)
    modes = budget.modes_of(drawn_modes(args))
    plan, record = budget.plan(
        offer,
        args.n,
        args.strange_share,
        budget=args.attempts,
        guarantees=claims,
        modes=modes,
    )
    print(
        json.dumps(
            {
                "cuts": floors.summary(modes),
                "supply": supply,
                "lines": intake.supply_lines(supply),
                "release_caps": intake.release_caps(offer),
                "guaranteed": claims,
                "budget": record,
                "attempts": [
                    {"head": a.head, "partition": a.partition, "rank": a.rank} for a in plan
                ],
            },
            indent=2,
        )
    )
    return 0


def curate_run(args: argparse.Namespace) -> int:
    """Make a release: colorize, select, render at full resolution, record it all."""
    from fractal_wallpapers.curation import binding, durability, intake, records
    from fractal_wallpapers.curation import run as run_module
    from fractal_wallpapers.deep import run as deep_run

    try:
        summary = run_module.curate(
            run=args.resume or args.run,
            n=args.n,
            seed=args.seed,
            strange_share=args.strange_share,
            modes=drawn_modes(args),
            attempts=args.attempts,
            workers=args.workers,
            ephemeral=args.ephemeral,
            ledgers=declared_ledgers(args),
            device=args.device,
            skip_release=args.skip_release,
            wall_budget=args.wall_budget,
            ceilings=deep_run.HUNG_CEILING if args.deep else None,
            resume=bool(args.resume),
        )
    except (
        binding.Unbound,
        durability.DurableLost,
        intake.IntakeError,
        records.NotIsolated,
        run_module.RunRefused,
    ) as refusal:
        print(refusal)
        return 1
    print(json.dumps(summary, indent=2))
    # A run that cannot balance its plan against what it made has shipped
    # pictures and lost track of which, and that is a failure whatever the
    # release looks like.
    return 0 if summary["reconciliation"]["holds"] else 1


def orphan_unmerged(args: argparse.Namespace):
    """Which unmerged legs `orphans` was told to sweep: named, all, or none.

    None is the default and is the whole safety of the listing: a leg the ledger
    has never heard of is real work with no row anywhere, and it is swept only
    because somebody read the list and typed its name.
    """
    from fractal_wallpapers.curation import candidate_ledger

    if getattr(args, "include_unmerged", False):
        return candidate_ledger.ALL_UNMERGED
    return tuple(getattr(args, "leg", None) or ())


def _ratchet(census: bool = False) -> dict:
    """What bounds the store from below, and — asked for — whether it still does.

    The log alone is cheap and answers *what is the mark*; `--census` streams the
    rows to answer *does the store still reconcile against it*, which is the
    question `tests/test_leveled_identity.py` asks in the slow lane. Same
    expression either way: the counters come off
    [`candidate_ledger.ratchet.counts_of`], which is also what a prune records
    with, so this cannot drift from what it is reading.
    """
    from fractal_wallpapers.curation.candidate_ledger import ratchet, store

    standing = ratchet.reading()
    record = {
        "schema": ratchet.LOG_SCHEMA,
        "log": display_path(ratchet.log_path()),
        "rows_in_the_log": len(ratchet.entries()),
        **standing,
    }
    if not census:
        return record
    found = ratchet.counts_of((str(row.get("key")), row.get("picture")) for row in store.stream())
    record["store"] = found
    record["reconciles"] = {
        name: found[name] + standing["deleted"][name] - mark
        for name, mark in standing["mark"].items()
    }
    record["unaccounted"] = sorted(name for name, over in record["reconciles"].items() if over < 0)
    return record


def _free_slots(args: argparse.Namespace) -> int:
    """The free-slot census, and the places manifest a near-band leg is cut from.

    **This verb exists because the arithmetic was being done by hand and got done
    exactly backwards once.** `thin2_b_near` was handed the proven near-band
    places *less the ones the floor arms took* — and the floor arms had taken
    every place that HAD a slot, so the subtraction left precisely the pairs
    already at the keep. It made 13,265 rows and the merge kept 39. The rule is
    `free slot AND not taken`, never `not taken` alone, and the free-slot half is
    a subtraction over rows already in hand: [`retention.free_slots`].

    `--out` writes a places manifest in the shape `--near-places` and
    `--floor-places` read, so the population a leg draws is the one this counted
    rather than one somebody re-derived beside it.
    """
    from fractal_wallpapers.curation import candidate_ledger, depth, retention

    wanted = set(args.mode or ())
    rows = candidate_ledger.stream()
    if wanted:
        rows = (row for row in rows if str((row.get("recipe") or {}).get("mode")) in wanted)
    slots = retention.free_slots(rows, keep=args.keep)
    if args.min_slots > 1:
        slots = {pair: count for pair, count in slots.items() if count >= args.min_slots}

    # Per PLACE and not per pair, because that is what a manifest names. A place
    # with room in two of its modes is one line here and two entries above, and
    # reporting the pair count as though it were places is the third of the three
    # ways `curation/README.md` says this phrasing goes wrong.
    by_place: dict = {}
    for (place, _coloring), count in slots.items():
        by_place[place] = by_place.get(place, 0) + count
    report = {
        "schema": retention.SCHEMA,
        "keep": args.keep if args.keep is not None else retention.keep_per_pair(),
        "modes": sorted(wanted) or "every mode the ledger holds",
        "min_slots_per_pair": args.min_slots,
        "pairs_with_room": len(slots),
        "free_slots": sum(slots.values()),
        "places_with_room": len(by_place),
        "unexplored_reading": (
            "a pair under THREE has never had more attempts than it holds; a pair at three "
            "or four may have been pruned there at the old keep of 3. The slots are real "
            "either way — this is about what they are evidence of, not about the arithmetic"
        ),
    }
    print(json.dumps(report, indent=2))
    if not args.out:
        return 0
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # Best-stocked first, so a manifest truncated to fit a budget keeps the places
    # with the most room rather than whichever the dict happened to hold first.
    ordered = sorted(by_place.items(), key=lambda item: (-item[1], item[0]))
    with out.open("w", encoding="utf-8", newline="\n") as handle:
        for place, count in ordered:
            handle.write(
                json.dumps(
                    {"schema": depth.PLACES_SCHEMA, "key": place, "free_slots": count},
                    ensure_ascii=False,
                )
                + "\n"
            )
    print(f"{display_path(out)}  {len(ordered):,} place(s)")
    return 0


def curate_candidate_ledger(args: argparse.Namespace) -> int:
    """Backfill the candidate ledger, census it, or keep its two files durable."""
    from fractal_wallpapers.curation import candidate_ledger, durability

    if args.what == "free-slots":
        return _free_slots(args)
    doing = {
        "backfill": lambda: candidate_ledger.backfill(recolour=args.recolour),
        "bare-varied": lambda: candidate_ledger.bare_varied(
            out=resolve_output(args.out) if args.out else None
        ),
        "census": lambda: candidate_ledger.census(n=args.n),
        "modes": lambda: candidate_ledger.modes(),
        "save": candidate_ledger.save,
        "check": candidate_ledger.check,
        "orphans": lambda: candidate_ledger.orphans(
            apply=args.apply, unmerged=orphan_unmerged(args)
        ),
        "pictures": candidate_ledger.picture_census,
        "prune": lambda: candidate_ledger.prune(keep=args.keep, apply=not args.dry_run),
        "ratchet": lambda: _ratchet(census=args.census),
        "re-render": lambda: candidate_ledger.re_render(
            limit=args.limit,
            workers=args.workers,
            keys=candidate_ledger.read_keys(resolve_output(args.keys)) if args.keys else None,
        ),
        "recolour": lambda: candidate_ledger.recolour(
            limit=args.limit,
            keys=candidate_ledger.read_keys(resolve_output(args.keys)),
        ),
        "score": lambda: candidate_ledger.rescore(
            limit=args.limit,
            keys=candidate_ledger.read_keys(resolve_output(args.keys)) if args.keys else None,
        ),
        "restore": lambda: candidate_ledger.restore(force=args.force),
    }[args.what]
    try:
        report = doing()
    except (candidate_ledger.LedgerError, durability.DurableLost) as refusal:
        print(refusal)
        return 1
    if args.what in {"census", "modes"} and args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(f"{out}")
        return 0
    print(json.dumps(report, indent=2))
    if args.what == "check" and any(
        part.get("verdict") in {"short", "missing"} for part in report.values()
    ):
        return 1
    return 0


def add_steps(steps) -> None:
    """The supply half: the ledgers, the sidecars, and the candidate pool."""
    from fractal_wallpapers.curation import budget as budget_module
    from fractal_wallpapers.curation import candidate_ledger as candidate_ledger_module
    from fractal_wallpapers.curation import embeddings as embeddings_module
    from fractal_wallpapers.curation import run as run_module

    reading = ledger_flags(
        steps.add_parser(
            "score",
            help="read the harvest ledgers through the location head",
            description=(
                "Reads each gate-surviving location through the head, at the regime its own "
                "ledger row names: a walk's gate render where the row's recorded digest still "
                "describes it, the deploy view already on disk for the standing stock. No "
                "deploy-geometry render is ever demanded for a row that was not scored at one. "
                "Resumable in both halves: a picture already on disk is not re-made. "
                "There is no --score-workers here, unlike `harvest`, `reframe` and `walk`, "
                "and that is a decision rather than an omission: what little this renders it "
                "renders in this process, and the fan-out was measured not to pay — 0.88x at "
                "two workers and 1.01x at four over the same views. See supply/README.md's "
                "*`--score-workers` is a flag with almost nothing left to do*."
            ),
        )
    )
    device_flag(reading)
    reading.add_argument("--limit", type=int, help="score only this many locations")
    reading.add_argument(
        "--key-file",
        metavar="PATH",
        help="score only the locations this key manifest names, out of the bound ledgers "
        "(`curate reach --write` writes one). Like --limit it is a partial pass, so it "
        "upserts what it looked at and clears nothing",
    )
    reading.add_argument(
        "--unscored",
        action="store_true",
        help="score only the bound locations the sidecar has NO row for — the backlog. "
        "A partial pass like --limit and --key-file: it upserts what it looked at and "
        "clears nothing, and it reports `outstanding` before --limit truncates. THE "
        "BINDING IS THE CONTROL, not this flag: measured 2026-09-15, the 54 ledgers on "
        "both tiers hold 242,007 gate survivors of which 132,992 have no row, and most "
        "of those sit on smoke, dedup and demo runs that are not standing supply. Name "
        "the ledgers whose locations you mean",
    )
    reading.add_argument(
        "--opened",
        action="store_true",
        help="score the opened locations the sidecar has no row for, off the CANDIDATE "
        "LEDGER rather than a walk binding. A population and not a filter, so it takes no "
        "--ledger, --harvest, --key-file, --limit or --unscored: these places are on no "
        "walk ledger at all. 1,607 of 42,113 opened locations on 2026-09-15, nearly all of "
        "them `curate label-migration merge`'s — a place with a human grade, a picture and "
        "a candidate row, which every draw standing on hunt.scanned stepped over because "
        "the sidecar had nothing to cut. Read at the node regime like all other stock that "
        "states no regime",
    )
    reading.add_argument(
        "--graded",
        action="store_true",
        help="score the human-graded places nothing has ever OPENED, off the three LABEL "
        "STORES. The fifth population and the one behind --opened: a place with a verdict "
        "and no candidate row, so it is on no walk ledger for a binding to reach and on no "
        "candidate ledger for --opened to reach. Takes no --ledger, --harvest, --key-file, "
        "--limit or --unscored, and refuses beside --opened, whose population it overlaps. "
        "3,110 of the 6,202 places at a human verdict >= 3 on 2026-09-16, of which 2,025 "
        "are location-store only — a place and not a picture, so `curate label-migration` "
        "has no recipe to derive and never could have reached them. Until they carry a "
        "sidecar row they are not admitted, `curate embed` gives them no vector, and "
        "`curate hunt --places` refuses a manifest of them outright. Best verdict first, "
        "read at the node regime like all other stock that states no regime",
    )
    reading.set_defaults(handler=curate_score)

    sidecar = steps.add_parser(
        "sidecar",
        help="the supply sidecar's durability: record it, check it, restore it",
        description=(
            "artifacts/curation/supply_scores.jsonl is the head's read of the standing "
            "supply and the one file under the regenerable tree that the checkout cannot "
            "regenerate — the ledgers it reads are under that tree too. It is too big and "
            "too churny to track, so what the history keeps is a manifest: the row count, "
            "the byte count, the sha256 and the per-ledger split. `save` writes a copy to "
            "the archive tier and records it; `check` reads the live file against the "
            "manifest; `restore` brings the copy back, counted before it is believed."
        ),
    )
    sidecar.set_defaults(handler=curate_sidecar)
    keeping_verbs(
        sidecar.add_subparsers(dest="what", required=True),
        noun="file",
        force="overwrite a live sidecar that holds MORE rows than the manifest records. "
        "Those rows are a harvest nobody has saved yet",
    )

    amendments = steps.add_parser(
        "amendments",
        help="the score amendment's durability: record it, check it, restore it",
        description=(
            "artifacts/curation/score_amendments.jsonl is what `curate redraw` writes: one "
            "append-only row per (location, engine build) re-reading a standing seating "
            "score off a view drawn again for it. Every reader of a seating score overlays "
            "it, so losing it does not shrink the supply — it silently puts the supply back "
            "on the numbers the re-read corrected. Rebuilding it is `curate redraw` over "
            "the whole supply, about ninety thousand renders, and only on a machine whose "
            "engine still fingerprints the same. So the bytes go to the archive tier and "
            "the history keeps the manifest: the row count, the byte count, the sha256 and "
            "the per-build split."
        ),
    )
    amendments.set_defaults(handler=curate_amendments)
    keeping_verbs(
        amendments.add_subparsers(dest="what", required=True),
        noun="amendment",
        force="overwrite a live amendment that holds MORE rows than the manifest records. "
        "Those rows are a redraw nobody has saved yet",
    )

    frames = steps.add_parser(
        "frames",
        help="the hunt frame index's durability: record it, check it, restore it",
        description=(
            "artifacts/curation/hunt/frames.jsonl is the frame every mining leg draws a "
            "location at, looked up through `hunt.frame_for`. It was cut from a 97.8 MiB "
            "pool-wide refinement scan that no job in this repository builds and that was "
            "deleted on 2026-09-02, so `curate hunt frames` refuses and there is no rebuild "
            "at any price — this file is the only copy of those frame choices. Losing it is "
            "silent by design: a location it has no row for draws at the frame it already "
            "carries. So the bytes go to the archive tier, the history keeps the manifest, "
            "and `curate run` refuses to start without it."
        ),
    )
    frames.set_defaults(handler=curate_frames)
    keeping_verbs(
        frames.add_subparsers(dest="what", required=True),
        noun="index",
        force="overwrite a live index that holds MORE rows than the manifest records. There "
        "is no job that appends to this file, so that is a state to explain rather than one "
        "to overwrite",
    )

    mass_sweep = steps.add_parser(
        "mass-sweep",
        help="the colour-mass sweep log: extend it, and record, check and restore it",
        description=(
            "artifacts/curation/palette_mass_sweep/rows.jsonl is the 25.7 MB experiment log "
            "the tracked colour-mass map was cut from: one row per (palette group, mode, "
            "location) with its 48-cell vector, its recipe and whether autolevel acted. It "
            "is insurance rather than a record anything reads — what production reads is "
            "the map under data/palettes/color_mass/ — and it is the only thing that would "
            "let the map be re-cut on other terms. Re-deriving the whole of it is 52.1 h of "
            "engine time over 27,053 renders whose pictures were deleted — the sum of its "
            "own rows' `seconds` — so the bytes go to the archive tier and the history "
            "keeps the manifest. `extend` is the one thing that adds to it: the panel "
            "rendered for maps the map has no row for, appended."
        ),
    )
    mass_sweep.set_defaults(handler=curate_mass_sweep)
    sweep_verbs = mass_sweep.add_subparsers(dest="what", required=True)
    keeping_verbs(
        sweep_verbs,
        noun="log",
        force="overwrite a live log that holds MORE rows than the manifest records",
    )
    extending = sweep_verbs.add_parser(
        "extend",
        help="measure the panel for every drawable map the colour-mass map has no row for",
        description=(
            "A colormap drop lands as palette groups with no row, reachable only through "
            "the carrier prior, which is a bound on the ramp rather than a reading of this "
            "pipeline. This renders the two-location panel for those maps over the modes it "
            "is given, appends the rows to the log and re-stamps the manifest; "
            "`fractal-wallpapers palettes color-mass --only-new` is the cut that follows. "
            "Modes are taken in the order given and a mode is finished or not started, so "
            "what a budget cuts is the tail of the roster and never half a column. Priced "
            "off the first sweep's own seconds over both panel locations: the four field "
            "modes 3.0 s a map together, itinerary and the three direct traps 39.9, threads "
            "18.1, and the four big composites 169.3."
        ),
    )
    extending.add_argument(
        # Resolved in the handler, for the reason `palettes color-mass --sweep` is:
        # `mode_policy.accepted()` reads a record, and building a parser must not
        # touch a disk — `--help` would raise before argparse said anything.
        "--modes",
        nargs="+",
        default=None,
        help="the modes to measure, cheapest first (default: every accepted mode)",
    )
    extending.add_argument(
        "--maps", nargs="+", default=None, help="measure these maps instead of every unmeasured one"
    )
    extending.add_argument(
        "--workers", type=int, default=3, help="renders at once (default 3, this box's pool)"
    )
    extending.add_argument(
        "--budget",
        type=float,
        default=None,
        help="wall seconds after which no further mode is started",
    )
    extending.add_argument("--workdir", default=None, help="where fields and pictures are made")
    extending.add_argument(
        "--dry-run", action="store_true", help="render and price it, append nothing"
    )
    extending.add_argument(
        "--partial",
        action="store_true",
        help="append even where the budget left a mode unmeasured, holing the grid",
    )
    extending.set_defaults(handler=curate_mass_sweep_extend)

    redrawing = steps.add_parser(
        "redraw",
        help="re-render every stale location view and amend the score read off it",
        description=(
            "A standing seating score is a reading of a picture, and the sidecar row names "
            "which picture. For tens of thousands of rows that name no longer describes "
            "anything: the view was drawn at a geometry the read no longer uses, under a "
            "recipe whose digest has since moved, or by an engine build nobody wrote down — "
            "and the build is not in the digest, so nothing before this could ask. This "
            "re-renders every stale view at the node regime, reads it through the shipped "
            "location head, and appends the result to an APPEND-ONLY amendment keyed by "
            "(location key, engine fingerprint). The sidecar is never edited. Every reader "
            "of a seating score prefers the amendment from the moment it lands. Serial "
            "(the engine threads inside one render) at about 0.03 s a view, so a whole "
            "supply is the best part of an hour; idempotent and resumable."
        ),
    )
    redrawing.add_argument(
        "--limit",
        type=int,
        help="stop after this many stale locations. A smoke leg, not a scoping flag: the "
        "amendment is append-only, so a limited pass amends a prefix and leaves the rest "
        "stale rather than declaring them current",
    )
    redrawing.add_argument(
        "--no-resume",
        action="store_true",
        help="re-read locations this engine build has already amended. Off by default, "
        "which is what makes an interrupted refresh cheap to finish",
    )
    device_flag(redrawing)
    redrawing.set_defaults(handler=curate_redraw)

    embedding_step = steps.add_parser(
        "embed",
        help="one DINOv2 vector per admitted location, from a neutral render",
        description=(
            "The gallery pass picks locations by how far apart they look, so every location "
            "the judge admits over the junk floor needs one picture that says nothing about "
            "a coloring nobody has chosen yet: the NEUTRAL RENDER, this location's smooth "
            "field through one fixed cyclic map at one fixed small geometry. A frozen DINOv2 "
            "reads a unit vector off it and the vector is kept forever, keyed by the exact "
            "location key. Incremental and idempotent: what is already stored is subtracted "
            "before anything is drawn, so a later harvest's admissions are a second run of "
            "this. Exits non-zero when the store does not cover the admitted population. "
            "NEEDS THE NETWORK THE FIRST TIME ON A MACHINE: the encoder is the only "
            "third-party weight here and is not re-hosted, so it comes from Hugging Face — "
            "84.2 MB into ~/.cache/huggingface, once, pinned to the hub revision "
            "`models/embedding.py` names. Every run after it is local, and "
            "`models.embedding.verify()` hashes what was cached against the pin."
        ),
    )
    device_flag(embedding_step)
    embedding_step.add_argument(
        "--sample",
        type=int,
        help="embed a stratified draw of this many outstanding locations rather than all of "
        "them, spread over the partitions in proportion to their supply. The pilot",
    )
    embedding_step.add_argument(
        "--limit", type=int, help="stop after this many locations; a prefix, not a sample"
    )
    embedding_step.add_argument(
        "--seed",
        type=int,
        default=embeddings_module.SAMPLE_SEED,
        help=f"the seed --sample draws under (default: {embeddings_module.SAMPLE_SEED})",
    )
    embedding_step.add_argument(
        "--unit-seconds",
        type=float,
        default=embeddings_module.UNIT_SECONDS,
        help=f"kill one neutral render that runs past this and carry on "
        f"(default: {embeddings_module.UNIT_SECONDS:g})",
    )
    embedding_step.set_defaults(handler=curate_embed)

    embedding_store = steps.add_parser(
        "embeddings",
        help="the embedding store's durability: record it, check it, restore it",
        description=(
            "The vectors cost a pass of the encoder over every admitted location and their "
            "input lives under the regenerable tree, so the store gets what the supply "
            "sidecar gets: a copy on the archive tier, a tracked manifest carrying the row "
            "count, the bytes, the sha256 and the frozen choices every vector was made "
            "under, and a restore that counts before it believes. The neutral JPEGs are not "
            "copied: every row carries the join its own picture re-renders from."
        ),
    )
    embedding_store.set_defaults(handler=curate_embeddings)
    keeping_verbs(
        embedding_store.add_subparsers(dest="what", required=True),
        noun="store",
        force="overwrite a live store that holds MORE rows than the manifest records. Those "
        "rows are admissions nobody has saved yet",
    )

    spiral_store = steps.add_parser(
        "spiral-scores",
        help="P(spiral) per location: build the store, or record, check and restore it",
        description=(
            "One row per location, keyed on the location key, saying what the shipped "
            "spiral probe makes of the place. `build` is NOT a render leg: the probe reads "
            "DINOv2 over the neutral render and the embedding store already holds that "
            "vector for every admitted location, so scoring one is a 384-column dot product "
            "and the whole store scores in under two seconds. It is also run automatically "
            "at the end of `curate embed`, so a newly admitted location arrives with a "
            "score rather than being drawable before it has one. A location with NO row "
            "here reads as UNKNOWN everywhere and counts toward nothing: unknown is never "
            "not_spiral. The reader is `curate solve --spiral-cap`."
        ),
    )
    spiral_store.set_defaults(handler=curate_spiral_scores)
    # `build` first, then the three keeping verbs, which is the order they
    # registered in before the split and so the order `--help` prints.
    spiral_verbs = spiral_store.add_subparsers(dest="what", required=True)
    building_spirals = spiral_verbs.add_parser(
        "build", help="score every embedded location the store does not hold"
    )
    building_spirals.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="score at most this many outstanding locations",
    )
    spiral_verbs.add_parser("check", help="check the live store against the manifest")
    spiral_verbs.add_parser("save", help="save a fresh copy and manifest")
    restoring_spirals = spiral_verbs.add_parser(
        "restore", help="restore the archived copy, counted before it is believed"
    )
    restoring_spirals.add_argument(
        "--force",
        action="store_true",
        help="overwrite a live store that holds MORE rows than the manifest records. Those "
        "rows are locations nobody has saved yet",
    )

    neighbouring = steps.add_parser(
        "neighbours",
        help="nearest neighbours by cosine in the embedding store, with their pictures",
        description=(
            "The sanity read, and it does not settle anything by itself: it names the "
            "neutral JPEGs of a few random locations and of whatever the store says is "
            "nearest to each, so a person can open them and see whether near means alike."
        ),
    )
    neighbouring.add_argument("-k", type=int, default=3, help="neighbours per row (default: 3)")
    neighbouring.add_argument("--sample", type=int, default=10, help="rows to read (default: 10)")
    neighbouring.add_argument(
        "--seed",
        type=int,
        default=embeddings_module.SAMPLE_SEED,
        help=f"the seed the rows are drawn under (default: {embeddings_module.SAMPLE_SEED})",
    )
    neighbouring.set_defaults(handler=curate_neighbours)

    reaching = steps.add_parser(
        "reach",
        help="which judged locations the gallery pass cannot select, and why",
        description=(
            "The gallery pass selects over the ADMITTED population — every location the "
            "location judge puts over the junk floor — and the accumulated pool is a "
            "different set. A judged location outside the admitted one cannot be chosen, "
            "however good the wallpaper somebody already made of it, and there are two ways "
            "for that to happen: today's head reads it below the junk floor, which is a "
            "judgement, or the supply sidecar has no row for it at all, which is not a "
            "judgement about anything. The second is a location whose ledger was never "
            "scored into the sidecar."
        ),
    )
    reaching.add_argument(
        "--keys", action="store_true", help="print every location key, not only the counts"
    )
    reaching.add_argument(
        "--write",
        metavar="PATH",
        help="write the locations with NO sidecar row at all as a key manifest, which "
        "`curate score --key-file` reads back. The other cause - below the junk floor - is a "
        "judgement and not a gap, so it is never written here",
    )
    reaching.set_defaults(handler=curate_reach)

    naming_ledgers = steps.add_parser(
        "ledgers",
        help="which walk ledger each released row names, and whether it still resolves",
        description=(
            "Provenance, not a repair. A released row carries its whole join and re-renders "
            "from itself, so a row whose ledger has gone is still a wallpaper somebody can "
            "rebuild — what it cannot be is re-OFFERED, because an intake starts from "
            "ledgers. Resolution goes through the same tier funnel every reader uses, so a "
            "ledger that has merely been archived reads as present."
        ),
    )
    naming_ledgers.add_argument(
        "--write",
        action="store_true",
        help="write the tracked provenance record as well as printing it",
    )
    naming_ledgers.set_defaults(handler=curate_ledgers)

    rereading = steps.add_parser(
        "rescore",
        help="read every candidate the pool holds through today's finished-render heads",
        description=(
            "Not `score`, which reads LOCATIONS through the location head over the walk "
            "ledgers. This reads the accumulated pool's own candidate renders — "
            "pictures/NNNN.jpg, 640x360, the picture each gate decision was taken on — "
            "through whichever finished-render head owns each row, at the artifact shipped "
            "now. The run's own scores are left exactly as they are, as that night's "
            "provenance; the reading lands in a `scores_current` block carrying the head "
            "sha. Rows judged by a retired head gain the cutpoints it never had."
        ),
    )
    device_flag(rereading)
    rereading.set_defaults(handler=curate_rescore)

    remaking = steps.add_parser(
        "re-render",
        help="put back every pool candidate render the pool names and the disk does not have",
        description=(
            "The pool's pictures live under the regenerable tree, and `rescore` refuses "
            "outright while one of them is missing — a reading of most of the pool is not a "
            "reading of the pool. This is the repair that refusal points at. Each row's "
            "recipe is rebuilt from the join the row carries, and it is rendered only if "
            "the recipe the RENDER PATH derives digests to the same name: the same pixels, "
            "not similar ones, because every reading the pool holds was taken on the pixels "
            "that used to be there. A row that will not reproduce is recorded and skipped. "
            "Writes no row, no reading and no manifest."
        ),
    )
    remaking.add_argument(
        "--workers",
        type=int,
        default=candidate_ledger_module.RE_RENDER_WORKERS,
        metavar="COUNT",
        help="how many engines to drive at once (default "
        f"{candidate_ledger_module.RE_RENDER_WORKERS}, this machine's render pool). More "
        "than three, or any of them at normal priority, makes the desktop unusable",
    )
    remaking.add_argument(
        "--limit",
        type=int,
        help="stop after this many pictures, taken as WHOLE (location, mode) pairs. What a "
        "pilot prices the whole leg off",
    )
    remaking.set_defaults(handler=curate_re_render)

    def with_shape(parser, defaults=True):
        # A run takes `None` where `plan` takes a number: a resumed run reads its
        # shape back out of its own sidecar, and a flag that defaulted to 6 here
        # could not be told from a flag that asked for 6.
        parser.add_argument(
            "-n",
            type=int,
            default=run_module.DEFAULT_N if defaults else None,
            help=f"release slots to fill (default: {run_module.DEFAULT_N}, or the resumed "
            f"run's own). A run's release is a DIAGNOSTIC — enough pictures to see that the "
            f"path works — and not a claim about what is worth shipping, which is a decision "
            f"over the whole accumulated pool",
        )
        parser.add_argument(
            "--strange-share",
            type=float,
            default=run_module.STRANGE_SHARE if defaults else None,
            help=f"share of the slots the strange judge fills "
            f"(default: {run_module.STRANGE_SHARE:g})",
        )
        parser.add_argument(
            "--strange-modes",
            type=int,
            default=None,
            help=f"modes the strange judge draws at each location it pays for "
            f"(default: {budget_module.MODES_PER_LOCATION[budget_module.STRANGE]}). The "
            f"smooth judge always draws one: the smooth coloring is the only mode it owns "
            f"and a second draw would render the same picture",
        )
        parser.add_argument(
            "--attempts", type=int, help="cap the total colorize attempts; omit for the multiple"
        )
        return parser

    planning = with_shape(
        ledger_flags(
            steps.add_parser(
                "plan",
                help="print the offer and the budget it implies, making nothing",
            )
        )
    )
    planning.set_defaults(handler=curate_plan)

    running = with_shape(
        ledger_flags(
            steps.add_parser(
                "run",
                help="make a release and record every decision",
                description=(
                    "Full resolution is the expensive part — measure one before asking for "
                    "many. Nothing is padded or backfilled: a judge that cannot fill its "
                    "quota under the slot and supply caps, the acting bar, and the "
                    "one-wallpaper-per-location rule ships fewer, and says so. "
                    "A long run wants --wall-budget: it stops cleanly at the last unit it "
                    "can afford rather than finding out afterwards, and --resume continues "
                    "an interrupted one from what it finished."
                ),
            )
        ),
        defaults=False,
    )
    naming = running.add_mutually_exclusive_group(required=True)
    naming.add_argument("--run", help="the name this run's records carry")
    naming.add_argument(
        "--resume",
        metavar="RUN",
        help="continue an interrupted run: its finished attempts and release renders are "
        "skipped, and its shape is read back from its own plan rather than from these flags",
    )
    running.add_argument("--seed", type=int, help="run seed (default: 0)")
    running.add_argument(
        "--wall-budget",
        type=float,
        metavar="SECONDS",
        help="stop cleanly rather than start a unit of work that would overrun this. Covers "
        "the whole run, intake through the last release render",
    )
    running.add_argument(
        "--workers",
        type=int,
        default=3,
        help="worker processes for the full-resolution pass (1 is the serial path)",
    )
    device_flag(running)
    running.add_argument(
        "--ephemeral",
        action="store_true",
        help="redirect the WHOLE record store under scratch/. A rehearsal that writes the "
        "durable store adds rows a later calibration pass cannot tell from a release's",
    )
    running.add_argument(
        "--skip-release",
        action="store_true",
        help="reuse the full-resolution pictures already on disk instead of rendering "
        "(with --resume: the pictures are this run's own, from before it was interrupted)",
    )
    running.add_argument(
        "--deep",
        action="store_true",
        help="hold this run to the deep mode's hung-unit ceilings instead of the shallow "
        "ones. A deep release frame was measured at 607s against a shallow distribution "
        "whose median is 87.8s, and the backstop only ever raises itself off units a run "
        "has FINISHED - so a deep row killed at the shallow colorize ceiling never teaches "
        "the run that its class is slow",
    )
    running.set_defaults(handler=curate_run)

    ledger_store = steps.add_parser(
        "candidate-ledger",
        help="the durable cache of every candidate ever rendered: build it, census it, keep it",
        description=(
            "One row per RECIPE — the frame that was rendered, the mode, the map and every "
            "palette knob, the regime, and the sha256 of the autolevel band the picture was "
            "levelled onto — carrying the location it stands on, the colour it turned out "
            "to be, and where its picture is. It admits everything and filters nothing: a "
            "floor is a reading of a judge and both move, the recipe and the pixels do not. "
            "Scores live in a sidecar keyed on (recipe, judge artifact, regime), so a judge "
            "adoption invalidates scores and nothing else. `backfill` reads the two decision "
            "stores and renders nothing; `census` is the fill over the axes a constraint "
            "acts on, and which of them is thin. `orphans` is the other direction and the "
            "backstop under `prune`: a KILLED leg never reaches `merge`, so its pictures "
            "are on disk with no row ever written for them and no prune can free them. A "
            "leg that HAS merged is decided by every store that names a picture — the "
            "ledger, the two decision stores and the kept gallery attempt rows; one that "
            "has not is skipped and listed for a person, never swept. It is a dry run "
            "unless `--apply` says otherwise."
        ),
    )
    ledger_store.set_defaults(handler=curate_candidate_ledger)
    ledger_verbs = ledger_store.add_subparsers(dest="what", required=True)

    filling = ledger_verbs.add_parser("backfill", help="build the ledger from what already exists")
    filling.add_argument(
        "--recolour",
        action="store_true",
        help="read every picture's colour again instead of carrying the reading already on "
        "record. About twenty milliseconds a picture",
    )

    bare_varied = ledger_verbs.add_parser(
        "bare-varied",
        help="the rows whose stored picture is the bare mode under a varied key",
        description=(
            "Writes a key manifest of every row carrying a non-empty `mode_params` whose "
            "picture was drawn WITHOUT them — the population `mine.make`'s dropped keyword "
            "left in the pool. Their files are not their recipes' pictures and every score "
            "on them is a reading of the wrong file, and nothing looks broken, which is "
            "worse than a missing picture. Which maker drew a row is read off its picture's "
            "path, the only durable place that fact lives: a picture under `hunt` or "
            "`label_migration` is what its key says and is left out. Feed the manifest to "
            "`re-render --keys` and then `score --keys`. Read-only and STREAMS the store, "
            "so it is not a pool-holding process."
        ),
    )
    bare_varied.add_argument(
        "--out",
        metavar="PATH",
        default=None,
        help="write the manifest there (default `bare_varied.jsonl` in the re-render store)",
    )

    censusing = ledger_verbs.add_parser("census", help="take the coverage census")
    censusing.add_argument(
        "--n",
        type=int,
        default=candidate_ledger_module.FIRST_SOLVE,
        help=f"how many wallpapers the feasibility read is taken against "
        f"(default {candidate_ledger_module.FIRST_SOLVE})",
    )
    censusing.add_argument(
        "--out",
        metavar="PATH",
        help="write the census there instead of printing it",
    )

    ledger_verbs.add_parser("check", help="check the live files against their manifests")

    slots = ledger_verbs.add_parser(
        "free-slots",
        help="how much room the retention keep leaves, and the places manifest a leg cuts from",
    )
    slots.add_argument(
        "--keep",
        type=int,
        default=None,
        help=f"count against this keep instead of the shipped "
        f"{candidate_ledger_module.RETAIN_PER_PAIR}. For pricing a change, not for planning "
        f"one: a leg draws against the keep the merge will actually apply",
    )
    slots.add_argument(
        "--mode",
        action="append",
        metavar="MODE",
        help="count only pairs in this colouring mode. Repeatable, and it is what sizes ONE "
        "unit — a mode's free slots are what a floor or near-band unit in that mode can add "
        "prune-free, and the modes are nowhere near alike on that axis",
    )
    slots.add_argument(
        "--min-slots",
        type=int,
        default=1,
        metavar="N",
        help="only pairs with at least this much room (default 1). A width-N unit wants "
        "places that can take N rows, and a place with one slot spends the other N-1 renders "
        "on rows the merge will drop",
    )
    slots.add_argument(
        "--out",
        metavar="PATH",
        help="also write a places manifest there, best-stocked first, in the shape "
        "--near-places and --floor-places read. Cutting the manifest from this count is the "
        "whole point: `thin2_b_near` inferred *free slot* from *not taken by a floor arm*, "
        "which is evidence of the opposite, and spent 13,265 renders to keep 39",
    )

    counting = ledger_verbs.add_parser(
        "modes",
        help="the accepted-recipe count per rendering type, so representation is read "
        "from counts rather than from impression",
        description=(
            "One row per mode in the `routed_mode` spelling — the mode a picture COUNTS "
            "as, so a modulate whose texture said nothing is counted where its pixels "
            "are. Five columns and each is a different question: `rows` is everything the "
            "ledger holds in that mode; `accepted` is what `solve.pool` would let a "
            "seating reach; `above_render_bar` is what clears its own mode's bar under "
            "`headroom.bars`, with the rule (P(>=4) or P(>=3)) printed beside the count "
            "because the two are different columns; `above_fine_bar` is what reads at or "
            "above solve.DEFAULT_FINE_BAR on the fine head, where a row merged since the "
            "last `score-pool` counts as unread; and `human_labeled` is what carries a "
            "verdict a PERSON cast in either finished store, with the wider set retention "
            "protects reported apart. Plus distinct locations and each column's share of "
            "its own total. It DECIDES NOTHING and proposes no roster change. It HOLDS "
            "THE POOL and reads the store twice."
        ),
    )
    counting.add_argument(
        "--out",
        metavar="PATH",
        help="write the table there instead of printing it",
    )
    sweeping = ledger_verbs.add_parser(
        "orphans", help="sweep the pool subtrees for pictures no record names"
    )
    sweeping.add_argument(
        "--apply",
        action="store_true",
        help="actually delete what the sweep found. The default is the dry run, which is "
        "the opposite way round from `prune` and deliberately so — a prune decides about "
        "rows it can see, and this decides about files nothing wrote down. Read the "
        "`unmerged` list first: those legs are skipped either way",
    )
    sweeping.add_argument(
        "--leg",
        action="append",
        metavar="NAME",
        help="also sweep this UNMERGED leg, which the sweep otherwise only lists. "
        "Repeatable, and takes the name as the listing prints it or just its last "
        "component. A named leg is swept under the same rule as a merged one — what the "
        "ledger names is kept, the rest goes — so a killed leg loses everything and a "
        "backfilled `runs` leg loses only the renders nothing decided about",
    )
    sweeping.add_argument(
        "--include-unmerged",
        action="store_true",
        help="sweep every unmerged leg the listing holds, as though each had been named. "
        "The listing stays the default precisely so that this is a sentence somebody typed "
        "after reading it",
    )

    ledger_verbs.add_parser(
        "pictures", help="report which rows name a picture that is no longer on disk"
    )

    pruning = ledger_verbs.add_parser("prune", help="bring the store back to the retention rule")
    pruning.add_argument(
        "--keep",
        type=int,
        default=candidate_ledger_module.RETAIN_PER_PAIR,
        help="how many rows one (location, mode) pair keeps, ranked by the "
        f"shipped rank key (default: {candidate_ledger_module.RETAIN_PER_PAIR}). Five "
        "protections keep a row outside the rank whatever it says, and a picture is kept "
        "if and only if its row is",
    )
    pruning.add_argument(
        "--dry-run",
        action="store_true",
        help="read, decide, and touch nothing. THE dry run — there is no second command "
        "that says what a prune would do",
    )

    ratcheting = ledger_verbs.add_parser(
        "ratchet",
        help="the high-water mark, the deletions recorded since it, and whether they reconcile",
    )
    ratcheting.add_argument(
        "--census",
        action="store_true",
        help="count the live store as well and report the shortfall, if any. A full parse "
        "of the rows — about fifteen seconds — where the default reads only the log",
    )

    remaking_pictures = ledger_verbs.add_parser(
        "re-render", help="put back the pictures the rows still name"
    )
    remaking_pictures.add_argument(
        "--workers",
        type=int,
        default=candidate_ledger_module.RE_RENDER_WORKERS,
        metavar="COUNT",
        help="how many engines to drive at once (default "
        f"{candidate_ledger_module.RE_RENDER_WORKERS}, this machine's render pool). More "
        "than three, or any of them at normal priority, makes the desktop unusable",
    )
    remaking_pictures.add_argument(
        "--limit",
        type=int,
        help="stop after this many pictures. What a pilot prices the whole leg off",
    )
    remaking_pictures.add_argument(
        "--keys",
        metavar="PATH",
        help="a key manifest — one JSON object a line carrying a recipe `key` — naming rows "
        "to render WHETHER OR NOT their picture is on disk. For the one case that needs it: "
        "a stored file that is not its own recipe's picture, which is worse than a missing "
        "one because nothing looks broken",
    )

    ledger_verbs.add_parser("save", help="save a fresh copy and manifests")

    recolouring = ledger_verbs.add_parser(
        "recolour",
        help="re-read every reading taken off the named pictures: colour, flatness, signature",
        description=(
            "The third companion of `re-render --keys` and `score --keys`, and it exists "
            "because a corrected picture invalidates more than its score. THREE readings "
            "come off a picture and all three are re-read here: the colour census on the "
            "ledger row, the flatness column its sidecar holds, and the pixel-cloud "
            "signature. Each is incremental on the recipe key and a re-render keeps both "
            "the key and the path, so each would otherwise go on serving a reading of the "
            "file that used to be there — and flatness feeds `curation.rank_key`, which is "
            "what a seating sorts on. `--keys` is REQUIRED: this is a repair over a named "
            "population and never a sweep. A re-run over unchanged pictures reports "
            "`changed: 0`."
        ),
    )
    recolouring.add_argument(
        "--keys",
        metavar="PATH",
        required=True,
        help="a key manifest naming the rows whose pictures moved. `candidate-ledger "
        "bare-varied` writes one",
    )
    recolouring.add_argument(
        "--limit", type=int, help="stop after this many rows. What a pilot prices the leg off"
    )

    rejudging = ledger_verbs.add_parser(
        "score", help="read every picture through the judge shipped now"
    )
    rejudging.add_argument(
        "--limit",
        type=int,
        help="stop after this many pictures. What a pilot prices the whole leg off",
    )
    rejudging.add_argument(
        "--keys",
        metavar="PATH",
        help="a key manifest naming rows to re-read EVEN WHERE the sidecar already holds a "
        "reading. The companion of `re-render --keys`: a corrected picture carries a "
        "reading of the picture it used to be, and the upsert replaces it in place",
    )

    putting_back = ledger_verbs.add_parser(
        "restore", help="restore the archived copies, counted before they are believed"
    )
    putting_back.add_argument(
        "--force",
        action="store_true",
        help="overwrite live files that hold MORE rows than the manifests record. Those "
        "rows are recipes nobody has saved yet",
    )
