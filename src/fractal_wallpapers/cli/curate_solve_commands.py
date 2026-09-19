"""`curate`'s gallery half: the solve, its record, and the two readings over it.

`solve` is the selection itself — twelve verbs and, at 370 lines of parser, the
largest single registration in the command line, because every constraint the
gallery runs under is a flag and every flag carries its ruling. `growth` and
`headroom` are readings over the same pool that say what another seat would cost
and what the bars leave reachable, and `seat-sheet` draws a recorded gallery for
an eye.

**The shared flag helpers live here** — [`solve_flags_a_record_keeps`],
[`themed_flags`], [`spiral_cap_value`], [`mode_ceiling_value`] and the key-file
readers — because `solve run` and `solve record` are the only two commands that
take them and they must take the SAME ones. `tests/test_nested_verbs.py` holds
that agreement; a helper copied rather than shared is how the two drifted before.

Cut out of `curate_commands` on 2026-09-12 with four sibling families; that
module's docstring carries the reversal and what it cost.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fractal_wallpapers.cli.common import (
    display_path,
    resolve_output,
)


def curate_recorded_solve(args: argparse.Namespace) -> int:
    """Record a solve under a stamp that never moves, browse one, or resolve an ID."""
    from fractal_wallpapers.curation import tentative

    if args.what == "list":
        held = tentative.stamps()
        if not held:
            print("no tentative gallery has been recorded on this machine.")
            return 1
        # **Which records a clone gets is the first thing this has to say.** An
        # unstamped read lands on the newest PUBLISHED stamp, so a reader looking
        # at this list needs to see why the newest line is not always the default
        # — otherwise the answer reads as a bug in `browse`.
        published = set(tentative.published())
        for stamp in held:
            rows = tentative.read_rows(stamp)
            manifest = tentative.read_manifest(stamp)
            mark = "published" if stamp in published else "unpublished"
            print(
                f"{stamp}  {mark:<11} {len(rows):>5} seat(s) of "
                f"{manifest['seats']['asked']}, {display_path(tentative.gallery_dir(stamp))}"
            )
        if len(published) != len(held):
            print(
                f"\n{len(held) - len(published)} unpublished record(s): read by naming the "
                f"stamp, but not tracked and never what an unstamped read means. An "
                f"unpublished record is DISCARDED once what it was made to measure has been "
                f"measured — keeping one needs a reason, and the keep list is a figure's "
                f"citation or the official n=1000 record. Publishing one is Matt's decision "
                f"— `curation.tentative.PUBLISHED` and the negation lines in `.gitignore` "
                f"are the list."
            )
        return 0

    if args.what == "record":
        return _record_a_solve(args)

    if args.what == "k-sweep":
        return _sweep_the_ceiling(args)

    if args.what == "k-sweep-plot":
        return _draw_the_ceiling_sweep(args)

    if args.what == "fulls":
        return curate_solve_fulls(args)

    if args.what == "recipes":
        return curate_solve_recipes(args)

    if args.what == "viewers":
        from fractal_wallpapers.curation import viewers

        try:
            print(display_path(viewers.build(args.stamps)))
        except (viewers.ViewersRefused, tentative.TentativeRefused) as refusal:
            print(refusal)
            return 1
        return 0

    # `browse <stamp>` and `browse --stamp <stamp>` are one command, because a
    # reader who has just seen a stamp printed will type it either way and the
    # cost of not accepting both is a page silently written for a DIFFERENT
    # record — the positional was ignored and the newest one rebuilt.
    named = [part for text in (args.id or ()) for part in str(text).split(",") if part.strip()]
    try:
        if args.what == "browse":
            if len(named) > 1:
                print(f"`browse` writes one record's page; {len(named)} were named.")
                return 1
            if named and args.stamp and named[0] != args.stamp:
                print(f"two different stamps were named: {named[0]} and {args.stamp}.")
                return 1
            named_stamp = args.stamp or (named[0] if named else None)
            if args.spacing:
                print(json.dumps(_spacing_readout(named_stamp), indent=2))
                return 0
            if args.out and args.viewer:
                print("`--out` and `--viewer` name two places; give one.")
                return 1
            if args.viewer:
                out = tentative.viewer_dir() / tentative.PAGE_NAME
                # Which record it is of, said out loud. The viewer path carries no
                # stamp on purpose, so the one thing this command has to print
                # that `browse <stamp>` does not is the stamp it just wrote.
                named_stamp = named_stamp or tentative.latest()
            else:
                out = resolve_output(args.out) if args.out else None
            written = display_path(tentative.page(named_stamp, out=out))
            print(f"{written} — {named_stamp}" if args.viewer else written)
            return 0
        # resolve: a comma list, so one invocation answers a whole figure prompt.
        if not named:
            print("name at least one ID or alias to resolve.")
            return 1
        answers = tentative.resolve(named, stamp=args.stamp)
    except tentative.TentativeRefused as refusal:
        print(refusal)
        return 1
    print(json.dumps(answers, indent=2))
    return 0 if all(held["found"] for held in answers) else 1


def release_workers() -> int:
    """This machine's render pool, off the module that owns the rule."""
    from fractal_wallpapers.curation import release

    return int(release.DEFAULT_WORKERS)


def curate_solve_recipes(args: argparse.Namespace) -> int:
    """Write — or price — the tracked recipe file that makes a record redrawable."""
    from fractal_wallpapers.curation import candidate_ledger, tentative

    try:
        stamp = args.stamp or tentative.latest()
        if not candidate_ledger.rows_path().is_file():
            print(
                f"the candidate ledger is not on this machine "
                f"({display_path(candidate_ledger.rows_path())}), and a recipe file is built "
                f"out of it. Nothing was written."
            )
            return 1
        if args.write:
            path, readout = tentative.write_recipes(stamp)
            print(display_path(path))
        else:
            rows, readout = tentative.build_recipes(stamp)
            readout = {
                **readout,
                "bytes": sum(len(json.dumps(row, ensure_ascii=False)) + 1 for row in rows),
                "wrote": None,
                "would_write": display_path(tentative.recipes_path(stamp)),
            }
    except tentative.TentativeRefused as refusal:
        print(refusal)
        return 1
    print(json.dumps(readout, indent=2))
    return 0 if not readout["not_in_the_ledger"] and not readout["refused"] else 1


def curate_solve_fulls(args: argparse.Namespace) -> int:
    """Find or make every seat of one record at the release geometry."""
    from fractal_wallpapers.curation import candidate_ledger, fulls, tentative

    try:
        stamp = args.stamp or tentative.latest()
        seats = [str(row["key"]) for row in tentative.read_rows(stamp)]
    except tentative.TentativeRefused as refusal:
        print(refusal)
        return 1
    pin_dir = tentative.fulls_dir(stamp)
    resolved = fulls.index(seats, log=lambda line: None, pin_dir=pin_dir)
    missing = [key for key in seats if key not in resolved]
    borrowed = sum(1 for key, path in resolved.items() if Path(path).parent != pin_dir)
    readout = {
        "stamp": stamp,
        "regime": fulls.REGIME.spelled,
        "seats": len(seats),
        "found": len(seats) - len(missing),
        "missing": len(missing),
        "hit_rate": round((len(seats) - len(missing)) / max(1, len(seats)), 4),
        # How many of the found pictures are somebody else's file. A sheet
        # cleanup takes every one of them, which is what `--pin` is for.
        "borrowed_from_elsewhere": borrowed,
    }
    if missing and not args.no_render:
        # **The absence of the ledger is not zero misses.** `stream()` yields
        # nothing when the file is not there, which is right for a reader asking
        # what the pool holds and wrong here: the rows it would have found are
        # the recipes these renders are made of, so an absent store came out as
        # "planned: 0" and exit 0 — a leg reporting success for work it could not
        # even describe.
        ledger = candidate_ledger.rows_path()
        if not ledger.is_file():
            print(
                f"{len(missing)} of {len(seats)} seat(s) have no picture at "
                f"{fulls.REGIME.spelled}, and the recipes to render them are in the candidate "
                f"ledger, which is not on this machine ({display_path(ledger)}). A recipe "
                f"file beside the record would answer this for a clone — `curate solve "
                f"recipes --stamp {stamp}` — and `--no-render` reports the hit rate without "
                f"needing either."
            )
            return 1
        wanted = set(missing)
        rows = [row for row in candidate_ledger.stream() if str(row.get("key")) in wanted]
        readout["render"] = fulls.render(rows, workers=args.workers)
        resolved = fulls.index(seats, log=lambda line: None, pin_dir=pin_dir)
        readout["found_after"] = sum(1 for key in seats if key in resolved)
    if args.pin:
        record = fulls.pin(resolved, pin_dir, log=lambda line: None)
        resolved = record.pop("pinned")
        readout["pin"] = record
    print(display_path(fulls.write_index(resolved)))
    print(json.dumps(readout, indent=2))
    return 0


def _spacing_readout(stamp: str | None) -> dict:
    """What the presentation order bought this record, beside what it replaced.

    `before` is the order the page shipped with — `rank` descending, which was the
    first option in its sort control — and `after` is [`page_order.order`]'s. Both
    are measured by the same function over the same rows, which is the only way the
    pair is a comparison rather than two instruments.

    It writes nothing: a reader asking what the ordering did has not asked for the
    page to be rebuilt, and `browse` with no flag is still how that is asked for.
    """
    from fractal_wallpapers.curation import page_order, tentative

    rows = tentative.read_rows(stamp)
    vectors = page_order.vectors_for(rows)
    # `-1` for an unranked row, which is where the page's own sort puts it, and the
    # index second so the before-order is total rather than dict-ordered.
    shipped = sorted(range(len(rows)), key=lambda at: (-(rows[at].get("rank") or -1), at))
    return {
        "stamp": stamp or tentative.latest(),
        "basis": page_order.basis(vectors),
        "window": page_order.WINDOW,
        "before": page_order.spacing(rows, shipped, vectors),
        "after": page_order.spacing(rows, page_order.order(rows, vectors), vectors),
    }


def _record_a_solve(args: argparse.Namespace) -> int:
    """The production solve, run once and recorded under a stamp that never moves."""
    from fractal_wallpapers.curation import solve, tentative
    from fractal_wallpapers.curation import targets as targets_module

    # `solve.pool` and not `headroom.population`, for `curate solve run`'s reason:
    # the two build the same candidate list — `population` IS `solve.pool` plus a
    # per-mode render-cost table read off every ledger row — and this handler has
    # never looked at that table. Streaming instead is 5.1 s and one fewer
    # whole-ledger copy.
    if args.collection and args.themed:
        print(
            "--collection names a hue family or a mode and --themed names one of the 48 "
            "codebook cells; they are two different galleries. Name one."
        )
        return 1
    # **The table first, `--n` over it, `RECORDED_SEATS` under both.** A collection
    # the table has no target for is refused by `seats_for` rather than recorded at
    # a thousand seats nobody chose — see `curation.targets`.
    if args.n is not None:
        seats = int(args.n)
    elif args.collection:
        seats = targets_module.seats_for(args.collection)
    else:
        seats = tentative.RECORDED_SEATS
    # A themed record reaches the same two demands `curate solve run --themed`
    # reaches, through the same helper. Unthemed, both are `None` and every
    # constant below is the one an unthemed record has always carried, so a
    # record taken before the themed pass could reach this verb is unchanged.
    targets, floor = ({}, None) if not args.themed else themed_demands(args.themed, seats)
    shape: dict = {}
    try:
        explain = keys_to_explain(args)
        forced = keys_to_force(args)
    except FileNotFoundError as refusal:
        print(refusal)
        return 1
    candidates, refused = solve.pool()
    if args.collection:
        candidates, held = targets_module.pool_for(candidates, args.collection)
        shape = collection_pass(args.collection, seats)
        targets, floor = shape["targets"], shape["floor"]
        print(
            f"[collection] {args.collection}: "
            f"{targets_module.kind_of(args.collection)}, {held:,} row(s), {seats} seat(s)"
        )
    try:
        # ONE column, resolved before the order and handed to both. The order is
        # resolved out here rather than inside `solve` — see `curate solve run` —
        # so the forcing has to reach the two of them through one object or the
        # cascade would rank a pool the bar had already narrowed differently.
        fine = solve.fine_column(forced)
        order, coverage = solve.ranking_for(candidates, args.key, fine=fine)
        record = solve.solve(
            candidates,
            n=seats,
            rule=shape.get("rule"),
            targets=targets,
            floor=floor,
            fine_bar=args.fine_bar,
            fine=fine,
            forced=forced,
            fold=args.fold,
            order=order,
            coverage=coverage,
            key=args.key,
            swap=not args.no_swap,
            seconds=args.swap_seconds,
            spiral_cap=args.spiral_cap,
            mode_ceilings=(
                shape["mode_ceilings"]
                if "mode_ceilings" in shape
                else mode_ceilings_named(args.mode_ceiling)
            ),
            cell_floor=args.cell_floor == "on",
            theme=shape.get("theme") or args.themed,
            geometry_radius=args.themed_radius,
            themed_cap=args.themed_cap,
            augment_chains=args.augment == "on",
            augment_depth=args.augment_depth,
            augment_seconds=args.augment_seconds,
            explain=explain,
        )
    except solve.SolveRefused as refusal:
        print(refusal)
        return 1
    # One stamp for both halves: the solve record's directory carries the same
    # name as the tentative folder, so successive records at the same `n` coexist
    # instead of the second overwriting the first's decision. The manifest's
    # `record` path is derived from this name, so it keeps pointing at the solve
    # that chose those seats.
    stamp = tentative.stamp_now()
    name = args.solve_name or f"tentative_n{seats}_{stamp}"
    # Both halves inside the one `try`: a `--solve-name` that already exists is
    # refused by `write_record` now, and a refusal a caller reads as a traceback
    # is a refusal that looks like a crash.
    try:
        print(f"{display_path(solve.write_record(name, record))}")
        directory = tentative.write(
            record, candidates=candidates, solve_name=name, pool_refused=refused, stamp=stamp
        )
    except (solve.SolveRefused, tentative.TentativeRefused) as refusal:
        print(refusal)
        return 1
    stamp = directory.name
    print(f"{display_path(tentative.page(stamp))}")
    manifest = tentative.read_manifest(stamp)
    print(json.dumps({"stamp": stamp, **manifest["seats"], "counts": manifest["counts"]}, indent=2))
    return 0


def _sweep_the_ceiling(args: argparse.Namespace) -> int:
    """One recorded seating per colour-ceiling `K`, so the trade can be looked at."""
    from fractal_wallpapers.curation import k_sweep, solve, tentative

    try:
        held = k_sweep.sweep(rungs=args.k or k_sweep.RUNGS, n=args.n, control=args.control)
    except (solve.SolveRefused, tentative.TentativeRefused) as refusal:
        print(refusal)
        return 1
    # The tables are on disk and were printed as lines while the sweep ran; what
    # is worth restating is where each rung landed and whether the control held.
    print(json.dumps({key: held[key] for key in ("stamp", "n", "k", "readings")}, indent=2))
    if held.get("control_check") is not None:
        print(json.dumps(held["control_check"], indent=2))
        return 0 if held["control_check"]["same_seat_order"] else 1
    return 0


def _draw_the_ceiling_sweep(args: argparse.Namespace) -> int:
    """The two per-cell figures off a sweep already taken. Renders nothing again."""
    from fractal_wallpapers.curation import k_sweep_plot

    if not args.stamp:
        print("name a sweep's stamp to draw — the one `k-sweep` printed when it finished.")
        return 1
    try:
        print(f"{display_path(k_sweep_plot.plot(args.stamp))}")
    except k_sweep_plot.PlotRefused as refusal:
        print(refusal)
        return 1
    return 0


def curate_solve(args: argparse.Namespace) -> int:
    """Choose the gallery, or record one: a stratified view, a greedy seed, and swaps."""
    from fractal_wallpapers.curation import candidate_ledger, ceiling, solve
    from fractal_wallpapers.curation import release as release_module
    from fractal_wallpapers.curation import targets as targets_module

    if args.what != "run":
        # A flag `run` reads and this verb does not is refused BY THE PARSER, at
        # the verb: each of the five is its own subparser and carries only what
        # its handler reads. This used to be a list of run-only flags compared
        # against a bare re-parse of the same verb, which was the same rule
        # enforced a step too late — after argparse had already accepted the line.
        return curate_recorded_solve(args)
    if args.collection and args.themed:
        print(
            "--collection names a hue family or a mode and --themed names one of the 48 "
            "codebook cells; they are two different galleries. Name one."
        )
        return 1
    # **The table, and `--n` still wins.** `seats_for` refuses a collection it has
    # no target for rather than seating a plausible number — see
    # `curation.targets`.
    if args.n is None and args.collection:
        args.n = targets_module.seats_for(args.collection)
    if args.n is None:
        args.n = candidate_ledger.FIRST_SOLVE

    try:
        targets = dict(ceiling.parse_target(text) for text in (args.target or ()))
    except ceiling.TargetRefused as refusal:
        print(refusal)
        return 1
    flat_floor = args.flat_floor
    if args.themed:
        # A themed gallery is one decision spelled in four places (→
        # solver_design, §Themed), so naming the cell asks for all of it. The two
        # a caller could set alone are DEFAULTS here and never overrides: a themed
        # pass that names its own target or its own floor keeps the one it named.
        # [`themed_demands`] is where both live, because `curate solve record`
        # reaches the same two and a second spelling would be a second gallery.
        wanted, _floor = themed_demands(args.themed, args.n)
        if not targets:
            targets = wanted
        if args.mode_floor is None:
            flat_floor = True
    floor = args.mode_floor
    if flat_floor:
        if floor is not None:
            print("--flat-floor and --mode-floor are two different floors; name one.")
            return 1
        # The way OFF. Unflagged, `solve.solve` takes the per-mode floor rule; this
        # puts back the flat floor every gallery before the flip was seated under.
        floor = solve.mode_floor(args.n)

    # `solve.pool` and not `headroom.population`: the two build the same candidate
    # list, but `population` materialises every ledger row to read a per-mode render
    # cost off it, and this handler has never looked at that table. Streaming instead
    # is 5.1 s over the store of 2026-09-02 and one fewer whole-ledger copy in a
    # process that is already the pool-holding one.
    try:
        explain = keys_to_explain(args)
        forced = keys_to_force(args)
    except FileNotFoundError as refusal:
        print(refusal)
        return 1

    candidates, _refused = solve.pool()
    shape: dict = {}
    if args.collection:
        # The pool is narrowed BEFORE the rank order is resolved for a mode pass
        # and spliced before it for a family one, so the cascade ranks the pool
        # the pass actually seats from. `ranking_for` reads the whole pool either
        # way — a family splice leaves every row in it — so the order below is
        # the same order an unnarrowed pass would take.
        candidates, held = targets_module.pool_for(candidates, args.collection)
        shape = collection_pass(args.collection, args.n)
        # **Defaults and not overrides**, the contract `--themed` is already
        # documented under at `GALLERY.md`'s *`--themed <cell>` is the whole themed
        # leg*. This clobbered both unconditionally until 2026-09-17, so
        # `--mode-floor` and `--target` were accepted by the parser and silently
        # discarded on a collection pass — which reads as a measurement of the
        # floor it named rather than of the one it got, and is how the flat floor
        # went unquestioned for as long as it did.
        targets = targets or shape["targets"]
        if args.mode_floor is None and not args.flat_floor:
            floor = shape["floor"]
        print(
            f"[collection] {args.collection}: "
            f"{targets_module.kind_of(args.collection)}, {held:,} row(s), {args.n} seat(s)"
        )
    try:
        fine = solve.fine_column(forced)
        order, coverage = solve.ranking_for(candidates, args.key, fine=fine)
        if coverage is not None:
            print(json.dumps(coverage, indent=2))
        record = solve.solve(
            candidates,
            n=args.n,
            rule=shape.get("rule"),
            targets=targets,
            floor=floor,
            locations=args.locations,
            fine_bar=args.fine_bar,
            fine=fine,
            forced=forced,
            radius=None if args.no_preselection else args.neutral_radius,
            fold=args.fold,
            diversity=not args.no_diversity,
            group_cap=args.group_cap,
            key=args.key,
            order=order,
            coverage=coverage,
            allow_unranked=args.allow_unranked,
            theme=shape.get("theme") or args.themed,
            geometry_radius=args.themed_radius,
            themed_cap=args.themed_cap,
            rows_per_seat=args.rows_per_seat,
            draw_seed=args.draw_seed,
            spiral_cap=args.spiral_cap,
            mode_ceilings=(
                shape["mode_ceilings"]
                if "mode_ceilings" in shape
                else mode_ceilings_named(args.mode_ceiling)
            ),
            cell_floor=args.cell_floor == "on",
            swap=not args.no_swap,
            seconds=args.swap_seconds,
            augment_chains=args.augment == "on",
            augment_depth=args.augment_depth,
            augment_seconds=args.augment_seconds,
            explain=explain,
        )
    except solve.SolveRefused as refusal:
        print(refusal)
        return 1
    name = args.name or f"n{args.n}"
    # `over=True` on both writes here, and only here. A `run` is a leg and its
    # directory is a working name — `--name` is documented as rewritten every
    # time, and the second write below is this same record gaining its rendered
    # pictures. A `record` is the other thing and takes the refusal.
    path = solve.write_record(name, record, over=True)
    print(f"{path}")
    if not args.no_render:
        regime = release_module.regime_of(args.release_regime)
        made = solve.render_seats(name, record, workers=args.workers, regime=regime)
        path = solve.write_record(name, record, over=True)
        print(json.dumps({**made, "timings": f"{len(made['timings'])} row(s), not restated"}))
        print(json.dumps(solve.autolevel_rate(record), indent=2))
    if not args.no_sheet:
        sheet = None if args.sheet_out is None else resolve_output(args.sheet_out)
        print(f"{solve.contact_sheet(name, record, rejected=record['samples'], output=sheet)}")
    modes = record["shortfalls"]["modes"]
    print(
        f"{record['filled']} of {args.n} seat(s) in {record['seconds']}s; "
        f"{modes['represented']} of {modes['of']} mode(s) represented, at a floor "
        f"{'of ' + str(modes['floor']) if modes['floor'] is not None else 'set per mode'}"
        f"; palette-group cap {record['config']['ceiling']['group_cap']} "
        f"({record['config']['ceiling']['group_cap_rule']}), sorted on "
        f"{record['config']['sort_key']}"
    )
    print(json.dumps(record["objective"]["final"], indent=2))
    print(json.dumps(record["rejection"]["reasons"], indent=2))
    return 0


def curate_growth(args: argparse.Namespace) -> int:
    """What N candidates' worth of mining buys, at gallery size n."""
    from fractal_wallpapers.curation import growth

    if args.what == "plot":
        from fractal_wallpapers.curation import growth_plot

        if not args.stamp:
            held = growth.stamps()
            print("name a stamped run to draw. On this machine: " + (", ".join(held) or "none"))
            return 1
        try:
            print(f"{display_path(growth_plot.plot(args.stamp))}")
        except (growth.GrowthRefused, growth_plot.PlotRefused) as refusal:
            print(refusal)
            return 1
        return 0
    stamp = args.name or growth.stamp_now()
    try:
        # The folder is claimed FIRST and each cell is appended as it lands, so a
        # sweep of hours that dies at cell fifteen leaves the fourteen it measured.
        # The manifest is written last and is what says the run finished.
        directory = growth.start_run(stamp)
        rows, manifest = growth.sweep(
            stamp=stamp,
            denominators=tuple(args.fraction) if args.fraction else growth.DENOMINATORS,
            sizes=tuple(args.n) if args.n else growth.SIZES,
            seeds=tuple(args.seed) if args.seed else growth.SEEDS,
            swap_seconds=args.swap_seconds,
            sink=lambda held: growth.append_rows(directory, held),
        )
        growth.write_manifest(directory, manifest)
    except growth.GrowthRefused as refusal:
        print(refusal)
        return 1
    print(f"{display_path(directory)}")
    print(json.dumps(manifest["pool"], indent=2))
    for row in rows:
        print(
            f"{row['rung']:>5} seed={row['seed']} n={row['n']:>5}: "
            f"{row['filled']:>5} seat(s), "
            f"{'-' if row['fill'] is None else format(row['fill'], '.1%'):>6}, "
            f"{row['floors_met']}/{row['floors_in_the_roster']} floor(s), "
            f"lift {row['selection_lift']}, {row['solve_seconds']}s"
        )
    return 0


def curate_headroom(args: argparse.Namespace) -> int:
    """Census the ledger's headroom: what each constraint needs, holds, and costs."""
    from fractal_wallpapers.curation import headroom

    candidates, costs, refused = headroom.population()
    if args.bars:
        # Before the ladder and before the pre-selection, because neither reads the
        # bars and both cost minutes. The pool `headroom.population` hands back is
        # already the population `solve` starts from, so this is the clearing set
        # exactly as a seating would see it.
        #
        # The pool scores are read HERE and handed in: `headroom` is arithmetic over
        # what it is given, and `clearing` and `census` call `bars` on every census
        # without wanting the column.
        from fractal_wallpapers.models import gallery_grade_train

        read = headroom.bars(candidates, fine=gallery_grade_train.read_pool_scores())
        print(json.dumps({**read, "pool": {"refused": refused}}, indent=2))
        return 0
    ladder = tuple(args.n) if args.n else headroom.LADDER
    radius = None if args.no_preselection else args.neutral_radius
    swept = None
    if args.twin_from:
        swept = json.loads(Path(args.twin_from).read_text(encoding="utf-8"))
    elif args.twin:
        swept = _twin_sweep(candidates, radius)
        held = headroom.write_sweep(args.name, swept)
        print(f"{held}")
    # Unset is the per-mode floor rule both gallery legs take, so an unflagged
    # census bounds the gallery an unflagged seating would build. `--flat-floor`
    # is the way off it, at every rung rather than as one number.
    record = headroom.census(
        candidates,
        ladder=ladder,
        costs=costs,
        radius=radius,
        twins=swept,
        floor=headroom.FLAT if args.flat_floor else None,
    )
    record["pool"] = {"refused": refused}
    path = headroom.write_record(args.name, record)
    print(f"{path}")
    print(json.dumps(record["twin_constraint"], indent=2))
    for size, block in record["curve"].items():
        short = [name for name, held in block["blocks"].items() if held["short"]]
        print(
            f"n={size:>5}  {len(block['flagged'])} flagged; "
            f"{'short: ' + ', '.join(short) if short else 'nothing provably short'}"
        )
    return 0


def _twin_sweep(candidates, radius) -> dict:
    """Every twin pair among the census population, exactly. Minutes, and opt-in.

    One picture per place — that place's strongest clearing candidate — because
    the twin relation the census bounds is a relation between places, and a place
    is represented by the picture a seating would reach for first.
    """
    from fractal_wallpapers.curation import distinct, headroom, signatures
    from fractal_wallpapers.paths import Tiers, rehome

    kept = headroom.clearing(candidates)
    if radius is not None:
        # `distinct.DELETE`, for `headroom.headroom`'s reason: this sweep is over
        # one picture per PLACE and the destructive walk's kept set is exactly one
        # representative per cluster.
        kept, _record = distinct.preselect(kept, radius=float(radius), fold=distinct.DELETE)
    best: dict = {}
    for candidate in sorted(kept, key=lambda held: (-held.score, held.key)):
        best.setdefault(candidate.location, candidate)

    # The tiers once, not once a place: [`fractal_wallpapers.paths.rehome`] is
    # 246x dearer resolving them per call, and this is asked over the whole pool.
    tiers = Tiers.current()

    def picture_of(key):
        held = best.get(key)
        if held is None:
            return None
        where = Path(rehome(held.picture, tiers))
        return where if where.is_file() else None

    # The sidecar holds exactly the vector this sweep builds, keyed on the RECIPE;
    # the sweep is keyed on the place, and `best` is the map between them.
    held_signatures = signatures.for_candidates(best.values())

    def reduced_for(key):
        candidate = best.get(key)
        return None if candidate is None else held_signatures.get(str(candidate.key))

    keys, matrix = distinct.matrix_for(sorted(best))
    return distinct.twins(keys, matrix, picture_of, reduced_for=reduced_for)


#: What `--spiral-cap` takes to mean **no cap at all**, beside a share.
#:
#: Needed because the default moved. While `solve.DEFAULT_SPIRAL_CAP` was `None`
#: an uncapped pass was spelled by saying nothing, and `type=float` was enough;
#: now that a tenth runs unasked, the other answer has to be typeable or it
#: becomes unreachable from the command line — which would strand the incumbent
#: gallery, the one invocation `curation/GALLERY.md` pins as having solved without
#: a cap. Two spellings and not one because a reader will reach for either.
NO_SPIRAL_CAP = ("none", "off")


def spiral_cap_value(text: str):
    """`--spiral-cap`'s argument: a share, or a word meaning there is no cap.

    **`0` is not the spelling for no cap and must not become one.** A cap of zero
    is a gallery that may seat no spiral location at all, which is a third
    answer — the cap runs, its allowance is zero, and the `spiral` refusal column
    fills up. Keeping the three apart is the whole reason this is a converter
    rather than a float with a sentinel.
    """
    held = str(text).strip().lower()
    if held in NO_SPIRAL_CAP:
        return None
    try:
        share = float(held)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"{text!r} is neither a share nor {' nor '.join(NO_SPIRAL_CAP)}"
        ) from None
    if share < 0:
        raise argparse.ArgumentTypeError(
            f"{share:g} is not a share. A cap below zero refuses every candidate the rule "
            f"reaches; `0` is the spelling for a gallery that may seat no spiral, and "
            f"`{NO_SPIRAL_CAP[0]}` is the spelling for no cap at all"
        )
    return share


#: What `--mode-ceiling` takes to mean **no per-mode ceiling at all**.
#:
#: The same two spellings [`NO_SPIRAL_CAP`] takes, and for the same reason: a
#: ceiling runs unasked, so the way back to a pass with none has to be typeable or
#: the counterfactual arm of every read of this rule is unreachable from the
#: command line. Unlike the spiral cap there is no third answer to keep apart — an
#: empty mapping IS no ceiling, and `MODE=0` is a mode that may take no seat.
NO_MODE_CEILING = ("none", "off")


def mode_ceiling_value(text: str):
    """`--mode-ceiling`'s argument: `MODE=SHARE`, or a word meaning no ceiling.

    Returns `None` for the word and `(mode, share)` for a pair;
    [`mode_ceilings_named`] folds a repeated flag's answers into the mapping the
    solve takes. Refuses here rather than at the seat, [`ceiling.parse_target`]'s
    argument: a misspelt mode name is a ceiling that can never bind, and a pass
    that discovered it at seat 900 would report a guard as having held when the
    guard was never on the mode anybody meant.
    """
    from fractal_wallpapers.curation import mode_policy

    held = str(text).strip().lower()
    if held in NO_MODE_CEILING:
        return None
    mode, sep, share = str(text).partition("=")
    mode = mode.strip()
    if not sep:
        raise argparse.ArgumentTypeError(
            f"--mode-ceiling wants MODE=SHARE or {' or '.join(NO_MODE_CEILING)}, not {text!r}"
        )
    if not mode_policy.is_accepted(mode):
        raise argparse.ArgumentTypeError(
            f"{mode!r} is not a mode a gallery may seat. A ceiling on one would never "
            "bind, and would read on the record as a guard that held. One of: "
            + ", ".join(
                sorted(name for name in mode_policy.MODE_POLICY if mode_policy.is_accepted(name))
            )
        )
    try:
        value = float(share)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"{share!r} is not a share, in --mode-ceiling {text!r}"
        ) from None
    if value < 0:
        raise argparse.ArgumentTypeError(
            f"{value:g} is not a share. A ceiling below zero refuses every candidate of "
            f"that mode; `{mode}=0` is the spelling for a mode that may take no seat, and "
            f"`{NO_MODE_CEILING[0]}` is the spelling for no ceiling at all"
        )
    return mode, value


def _default_mode_ceilings() -> dict:
    """[`solve.DEFAULT_MODE_CEILINGS`], imported late so building the parser does
    not pull the solve in. Named apart because the help text and the folder both
    want it and neither may hold its own copy."""
    from fractal_wallpapers.curation import solve as solve_module

    return dict(solve_module.DEFAULT_MODE_CEILINGS)


def mode_ceilings_named(named) -> dict:
    """A repeated `--mode-ceiling` folded onto [`solve.DEFAULT_MODE_CEILINGS`].

    Left to right, and the default is where it starts: naming one mode adds to the
    shipped ceiling rather than replacing it, and `none` clears everything to its
    left. So `--mode-ceiling none` is the uncapped arm of a counterfactual,
    `--mode-ceiling threads=0.15` tightens the shipped one, and
    `--mode-ceiling none --mode-ceiling smooth=0.5` is a pass that caps one other
    mode and nothing else.
    """
    held = _default_mode_ceilings()
    for value in named or ():
        if value is None:
            held.clear()
        else:
            mode, share = value
            held[mode] = share
    return held


def themed_flags(container):
    """The three flags that name a THEMED gallery, for `run` and for `record`.

    Written once for [`solve_flags_a_record_keeps`]'s reason: a record IS a run
    taken once and kept, so a themed record has to reach the same decision by the
    same spelling, and two `--help` texts describing one flag two ways is how that
    stops being true. `run` hands its own argument group — it carries twenty-six
    flags and groups them — and `record` at twelve hands the parser itself, which
    is what `tests/test_cli.py`'s *a grouped command leaves no flag behind* wants:
    a command with no named groups keeps none.
    """
    from fractal_wallpapers.curation import ceiling as ceiling_module
    from fractal_wallpapers.curation import headroom as headroom_module
    from fractal_wallpapers.curation import rules as rules_module
    from fractal_wallpapers.palettes import dominance as dominance_module

    container.add_argument(
        "--themed",
        metavar="CELL",
        # A closed list of 48 and therefore `choices`, which exits before any pool
        # is read. `--themed not_a_real_cell` used to be accepted, spend ~40 s
        # loading the whole pool, and then fail on `solve.SolveRefused` — whose
        # message reads *the pool holds none of that*, which is the right sentence
        # for a cell that IS one and is the wrong sentence for a typo.
        # [`dominance.cells`] is stdlib-only for this: see
        # [`codebook.cell_names`], which is what keeps a gamut bisection and numpy
        # out of every `fractal-wallpapers --help`.
        choices=dominance_module.cells(),
        help="choose a THEMED gallery: one dominant colour cell, over a pool of the rows "
        "that cell's dominance block claims, at the RELAXED bar — P(>=3) >= "
        f"{headroom_module.FALLBACK_BAR} for every accepted mode rather than the per-mode "
        "rule, because a single-cell pool is q3-grade material and at the per-mode bars "
        "there is no pool. It also swaps the diversity rule for geometry-only "
        f"distinctness at rules.GEOMETRY_RADIUS ({rules_module.GEOMETRY_RADIUS:g}) in the "
        "neutral descriptor: the pixel-cloud twin test is over a picture's COLOUR cloud, "
        "so a themed pool is a near-duplicate pool under exactly it. Unless you name them "
        "otherwise it also sets `--target CELL=1.0`, without which the cell allowance "
        "refuses the theme at nine seats, and `--flat-floor`",
    )
    container.add_argument(
        "--themed-cap",
        type=int,
        metavar="SEATS",
        help="the palette-group cap a THEMED pass runs under, overriding the computed "
        "one. Unset is ceiling.themed_group_cap: max(1, floor("
        f"{ceiling_module.THEMED_GROUP_CAP_RATE:g} x n)), three times the main gallery's "
        "rate, raised from twice it on 2026-09-12. A "
        "themed pool holds a few dozen palette groups against the whole pool's hundreds, "
        "so the general cap was measured as the BINDING rule over a themed pool at every "
        "shipping size, which is why a themed pass gets its own. It was ceil(2 x n / P) "
        "until 2026-09-05, where P counted the groups fielding "
        f"{ceiling_module.THEMED_CAP_PLACES}+ distinct places — a cap that moved with the "
        "pool, so two themes at one n ran under two caps; P is still measured and recorded "
        "and denominates nothing. `--group-cap` still names the main gallery's rule and a "
        "themed pass ignores it. Ignored without `--themed`",
    )
    container.add_argument(
        "--themed-radius",
        type=float,
        default=rules_module.GEOMETRY_RADIUS,
        metavar="COSINE",
        help=f"the radius the themed diversity rule refuses inside (default "
        f"{rules_module.GEOMETRY_RADIUS:g}). A SETTING and not a law — it was read off the "
        "themed pools' own nearest-neighbour distributions and is the number to move if a "
        "themed gallery reads as repetitive or as needlessly small. Ignored without "
        "`--themed`",
    )


def collection_flag(container) -> None:
    """`--collection`, on the two verbs that seat a gallery.

    One flag and one helper for both, [`themed_flags`]' reason: `run` and
    `record` must take the same flags or a recorded collection and a run one at
    the same size are two different galleries.
    """
    from fractal_wallpapers.curation import targets as targets_module

    container.add_argument(
        "--collection",
        metavar="NAME",
        choices=list(targets_module.collections()),
        help="seat ONE COLLECTION — a hue family or a production mode — at the size "
        "`curation.targets.TARGETS` sets for it. A family pass splices the family name "
        "onto the cells of every row the store calls dominant in it and then runs as an "
        "ordinary themed pass (the relaxed bar, geometry-only distinctness), with the "
        "family's four cells raised out of the colour ceiling's way and no colour demand "
        "stated, at the DEFAULT per-mode floor rule since 2026-09-17 — it took the flat "
        "floor(n / 100) until then, which cost `magenta` a seat. A mode pass narrows the "
        "pool to that ROUTED mode and clears the per-mode "
        "floors and ceilings, which over a single-mode population are a demand nothing can "
        "meet and a cap on the collection itself. The "
        + str(len(targets_module.TARGETS))
        + " targets are: "
        + ", ".join(f"{name} {seats}" for name, seats in targets_module.TARGETS.items())
        + ". `--n` overrides the table; `--themed` names a CELL and refuses beside this",
    )


def collection_pass(collection: str, seats: int) -> dict:
    """The solve arguments one `--collection` pass runs under, as a dict to splat.

    Both verbs read this for [`themed_demands`]' reason. The two kinds differ in
    everything but the table they took their `n` from, so the branch is here and
    not at each call site.

    ## A FAMILY pass takes the default floor rule, Matt's ruling of 2026-09-17

    `None` is [`curation.solve.solve`]'s way of asking for
    [`curation.mode_policy.seat_floors`] — half each accepted strange mode's share
    of the strange seat budget — which is what every other pass in this repository
    runs under. It inherited [`solve.mode_floor`]'s **flat** `floor(n / 100)` from
    the `--themed` path until this ruling, and that is the rule every gallery
    before 2026-08-31 was seated under.

    **The flat floor was costing seats, which is the opposite of what a floor
    reads like it does.** Measured on `magenta` at n = 400 over one pool, the
    seat count is not monotone in the floor and the shipped flat 4 was not its
    best value:

    | floor | seats | shortfall |
    |---|--:|--:|
    | 0 | 396 | 0 |
    | 1 | 395 | 0 |
    | 2 | 395 | 0 |
    | 3 | 399 | 2 |
    | **4 — the flat floor** | **399** | **2** |
    | 5 | 400 | 3 |
    | 6 | 393 | 3 |
    | **`seat_floors(400)` — this** | **400** | **7** |

    A floor is a mandate, and the mandate leg seats scarcest-first from its own
    subpool; that is a better **seed** for the augmenting chain than the ranked
    walk is, so raising the mandate raises the seat count until the mandate stops
    being fillable. `magenta`'s mandate leg seats 16 at floor 2 and 88 here.

    **The shortfall column going the other way is not a regression**, because
    [`solve.solve`]'s objective is lexicographic with **seats first and shortfall
    second** — 400 seats at a shortfall of 7 strictly beats 399 at 2. What the
    larger shortfall records is a demand this pool genuinely cannot meet:
    `magenta` holds **four** `direct_trap_lines` rows above the bar in the whole
    themed pool, so the mode is short at every floor at or above 3 and no leg
    could close it. An unfilled floor beats a padded gallery, and the seating
    records the shortfall rather than repairing it.

    A **mode** pass still floors at 0: over a single-mode population a per-mode
    floor is a demand nothing but that one mode can meet, which is the reason
    already written at `--collection`'s own help.
    """
    from fractal_wallpapers.curation import targets as targets_module

    if targets_module.kind_of(collection) == targets_module.FAMILY:
        return {
            "theme": collection,
            "rule": targets_module.rule_for(collection),
            "targets": {},
            "floor": None,
        }
    return {"theme": None, "rule": None, "targets": {}, "floor": 0, "mode_ceilings": {}}


def themed_demands(theme: str, n: int) -> tuple[dict, int]:
    """The two demands `--themed` sets, as `(targets, floor)`.

    They are DEFAULTS at `run`, which lets a caller name its own `--target` or
    `--mode-floor` and keep it, and they are the whole rule at `record`, which
    carries neither flag. Both callers read them here so a themed record and a
    themed run at one `n` cannot come to two different galleries — which is the
    only claim a record makes about itself.

    The target is `1.0` and not a share: the allowance is
    `floor(k * t * n) + 1`, so at `t = 1.0` it is `2n + 1` and cannot bind, and
    without it the cell's default `1/48` refuses the theme at nine seats.
    """
    from fractal_wallpapers.curation import solve as solve_module

    return {str(theme): 1.0}, solve_module.mode_floor(int(n))


def keys_named(path) -> list:
    """The candidate keys one manifest names, in file order and without repeats.

    A FILE and never a list of keys on the command line, because a population runs
    to thousands and a Windows command line does not — the rule this project has
    for every batch. Blank lines and `#` comments are skipped so a manifest can
    say what it is.

    Two flags take one of these — `--explain-keys` and `--forced` — and they read
    it through one function, so a manifest that works for one works for the other
    and the same file can serve both in a single run, which is exactly the shape
    a forced pass wants: force this population, and explain it.
    """
    where = Path(path)
    if not where.is_file():
        raise FileNotFoundError(f"no key manifest at {where}")
    read = [
        line.strip()
        for line in where.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    return list(dict.fromkeys(read))


def keys_to_force(args: argparse.Namespace) -> list | None:
    """The keys `--forced` names, or `None` where nothing was forced.

    `None` and never an empty list: `solve.fine_column` treats them the same, but
    a record saying a pass forced nothing and a record saying a pass was handed an
    empty manifest are the same gallery and it costs nothing to keep the spelling
    honest at one end.
    """
    named = getattr(args, "forced", None)
    if not named:
        return None
    read = keys_named(named)
    print(f"[solve] forcing {len(read):,} key(s) named in {display_path(Path(named))}")
    return read


def keys_to_explain(args: argparse.Namespace) -> list | None:
    """The candidate keys this pass records a fate for, or `None` for no block.

    The union of the two ways of naming a set, because they name different kinds
    of set and a caller can want both: `--explain-seats-of` is *an earlier
    gallery's seats*, which is the before/after question, and `--explain-keys` is
    *any population at all*, which is the question a set defined outside the solve
    asks. `curate solve record` reaches only the second — a record does not take a
    record's name as an argument — so the getattr is the run/record split and not
    defensive coding.

    Order is preserved and duplicates are dropped: the block is one entry per key
    asked about, and asking twice is not two answers.
    """
    from fractal_wallpapers.curation import solve

    named: list = []
    seats_of = getattr(args, "explain_seats_of", None)
    if seats_of:
        named += [str(row["key"]) for row in solve.read_record(seats_of)["seated"]]
        print(f"[solve] explaining {len(named):,} seat(s) of {seats_of!r} by name")
    if getattr(args, "explain_keys", None):
        where = Path(args.explain_keys)
        read = keys_named(where)
        print(f"[solve] explaining {len(read):,} key(s) named in {display_path(where)}")
        named += read
    if not named:
        return None
    return list(dict.fromkeys(named))


def solve_flags_a_record_keeps(*, pool, demands, search):
    """The flags `curate solve run` and `curate solve record` both read.

    A record IS a run, taken once and kept, so the flags it accepts are the ones
    it can pass straight through. Written once for [`common.device_flag`]'s
    reason and this one besides: a record that took a flag it did not read would
    not be reproducible from the `run` it claims to be, and the drift would show
    up as two `--help` texts describing one flag two ways.

    Three containers rather than one parser, because `run` groups its help — it
    carries twenty-seven flags — and `record` does not, so a record hands the
    same parser three times.
    """
    from fractal_wallpapers.curation import augment as augment_module
    from fractal_wallpapers.curation import ceiling as ceiling_module
    from fractal_wallpapers.curation import distinct as distinct_module
    from fractal_wallpapers.curation import solve as solve_module

    pool.add_argument(
        "--fine-bar",
        type=float,
        default=solve_module.DEFAULT_FINE_BAR,
        metavar="SCORE",
        help=f"narrow the pool to the rows the gallery-grade head reads at "
        f"p_fine(>=4) >= SCORE, BEFORE anything else runs — the per-mode bars, the neutral "
        f"pre-selection and the view are all taken over what is left, so a barred pass is a "
        f"whole pass and not a filtered reading of an unbarred one. A row the head has NO "
        f"reading for is excluded, which costs nothing: it has read exactly the clearing "
        f"set. Unsaid, {solve_module.DEFAULT_FINE_BAR:g} runs (Matt's ruling, 2026-09-08); "
        f"it was NO bar until then, so a record on this machine that does not name the flag "
        f"and predates 20260908T144844Z ran unbarred. At 0.50 it keeps a quarter of the "
        f"seatable pool, fills the same thousand seats, raises the sum 1786.5 -> 1876.6 and "
        f"costs a demand shortfall of 0 -> 18. It needs `gallery-grade score-pool` and "
        f"seats NOTHING without it. The value is on every record either way, `null` for a "
        f"pass that ran unbarred",
    )
    pool.add_argument(
        "--forced",
        metavar="PATH",
        help="a MANIFEST of candidate keys, one per line, this pass lifts to the top of "
        "the fine column BEFORE the bar, the neutral pre-selection and the cascade — so a "
        "forced row clears `--fine-bar`, is its cluster's survivor and is offered ahead "
        f"of every unforced row. `solve.FORCED_LIFT` is the lift and it is "
        f"ORDER-PRESERVING, `{solve_module.FORCED_LIFT:g} + p_fine`: the forced set keeps "
        "its own order among itself, so several forced rows competing inside one colour "
        "cell are still ranked against each other rather than tied arbitrarily. It forces "
        "an OFFER and never a seat — one seat per cluster, the twin test, the allowances, "
        "the mode ceilings and the spiral cap all still apply, and a forced row refused by "
        "any of them is the reading this flag exists to give. STAGED and OFF unasked: no "
        "shipped default moves, and `config.forced` is 0 on every record that does not "
        "name it. A FILE and never a list of keys, for `--explain-keys`' reason. Blank "
        "lines and `#` comments are skipped",
    )
    pool.add_argument(
        "--fold",
        choices=list(distinct_module.FOLDS),
        default=distinct_module.FOLD,
        help="what the neutral pre-selection does with a place it folds into another. "
        f"`{distinct_module.POOL}`, THE DEFAULT since 2026-09-09, relabels: the absorbed "
        "place's rows stay in the pool carrying the surviving place's key as their "
        "cluster, and the one-seat-per-location rule reads one seat per CLUSTER — so a "
        "near-duplicate cluster still holds one seat and stops destroying the modes and "
        f"colour cells only its absorbed places hold. `{distinct_module.DELETE}` is the "
        "fold as it shipped before that: the place and every row it carries leave the "
        "pass. It is kept so an older record reproduces and so the two can be compared "
        "over one pool. Ignored under `--no-preselection`, which folds nothing",
    )
    demands.add_argument(
        "--spiral-cap",
        type=spiral_cap_value,
        default=solve_module.DEFAULT_SPIRAL_CAP,
        metavar="SHARE",
        help="cap the share of seats sitting at a location the spiral probe calls a "
        "spiral: at most ceil(SHARE * seats filled), the same spelling a colour target "
        "is stated in. The verdict comes off `curate spiral-scores` at the cut "
        "models/spiral/manifest.json carries, and a location with NO score counts "
        f"toward nothing — unknown is not not_spiral. Unsaid, {solve_module.DEFAULT_SPIRAL_CAP:g} "
        f"runs (Matt's ruling, 2026-09-04; it was NO cap before that, so a record on "
        f"this machine that does not name the flag ran uncapped). "
        f"`{NO_SPIRAL_CAP[0]}` runs no cap at all and is what the incumbent gallery is "
        "spelled with; 1.0 runs the cap and lets it not bind, which is the spelling for "
        "a record that should say so",
    )
    demands.add_argument(
        "--cell-floor",
        choices=("on", "off"),
        default="on" if solve_module.DEFAULT_CELL_FLOOR else "off",
        help="the COLOUR FLOOR: at least floor(kf * t * seats filled) seats dominant in "
        f"each of the 48 chromatic cells — kf = {ceiling_module.KF} against the ceiling's "
        f"k = {ceiling_module.K}, one fair share against three, so 20 of a thousand seats "
        "where the allowance is 63. SOFT, and it is the ceiling's arithmetic with one "
        "number changed and NO + 1: a warm-up belongs to a walk that has to seat its first "
        "row somewhere. It refuses nothing and can never make a pass infeasible — a cell "
        "the pool cannot fill is a row in `shortfalls.cell_floors` and a shortfall on the "
        "objective's tier 2, under the seat count and over the worst seated score. ON "
        "unasked (Matt's ruling, 2026-09-09), so a record that does not name this ran WITH "
        "it; `config.ceiling.kf` is `null` on one that did not. Always off on `--themed`, "
        "a theme being one cell by construction",
    )
    demands.add_argument(
        "--mode-ceiling",
        type=mode_ceiling_value,
        action="append",
        default=None,
        metavar="MODE=SHARE",
        help="cap the share of seats one MODE may take: at most ceil(SHARE * seats "
        "filled), the spiral cap's own arithmetic and the same spelling a colour target "
        "is stated in. REPEATABLE, folded left to right onto the shipped ceiling, and "
        f"`{NO_MODE_CEILING[0]}` clears everything to its left — which is how the "
        "uncapped arm of a counterfactual is spelled. Unsaid, "
        + (
            ", ".join(
                f"{mode} {share:g}" for mode, share in sorted(_default_mode_ceilings().items())
            )
            or "nothing"
        )
        + " runs (Matt's ruling, 2026-09-05; there was NO per-mode ceiling before that, so "
        "a record on this machine that does not name the flag ran without one). It is a "
        "GUARD against a runaway rather than a setting expected to bind — `threads` took "
        "187 of 1,000 seats at 7.5x a pool-mirror on 2026-09-05 — so the reading it gives "
        "is the `mode_ceiling` refusal column, and a zero there is the expected answer",
    )
    search.add_argument(
        "--key",
        choices=list(solve_module.OFFERED_KEYS),
        default=solve_module.DEFAULT_KEY,
        help="the sort key the pool is walked in AND the quantity the objective is stated "
        "in. `cascade` is THE DEFAULT since 2026-09-07, Matt's ruling: above the solve's "
        "own bar it orders on the fine-tier head's P(>=4) — `curate rank-key`'s value plus "
        "one, so the two stages never interleave — and below it hands the rank key's order "
        "straight back. It REFUSES without `gallery-grade score-pool`, rather than falling "
        "back to a key the record would then be wrong about. `p_ge4` is the render judge "
        "alone. `rank-key` is NOT OFFERED HERE since 2026-09-08, Matt's deprecation of it "
        "as a seating key — it is still the fitted form in `curate rank-key`, still what "
        "retention ranks on, still the cascade's own below-bar half, and still resolved for "
        "a record that names it, so the 62 galleries seated on it stay readable. IT MOVES "
        "THE ORDER AND THE OBJECTIVE AND NOTHING ELSE: every bar, the clearing rule and the "
        "neutral pre-selection still read the judge's own columns",
    )
    search.add_argument(
        "--explain-keys",
        metavar="PATH",
        help="a MANIFEST of candidate keys, one per line, whose fate this pass records ONE "
        "AT A TIME into `rejection.explained` — every key named comes back `seated`, `not "
        "in the pool`, or the first rule that refused it. `--explain-seats-of` asks the "
        "same question of an earlier record's seats; this asks it of any set at all, which "
        "is what a population defined outside the solve needs — the wallpapers a person "
        "graded 4, say, which are ledger rows but are nobody's seats. A FILE and never a "
        "list of keys, because a population runs to thousands and a Windows command line "
        "does not. Unioned with `--explain-seats-of` where both are named; blank lines and "
        "`#` comments are skipped",
    )
    search.add_argument(
        "--no-swap",
        action="store_true",
        help="take the greedy seed and stop. The record still carries the objective, so "
        "this is how a before/after on the swap loop alone is taken",
    )
    search.add_argument(
        "--swap-seconds",
        type=float,
        default=None,
        metavar="SECONDS",
        help="a wall budget for the SWAP LOOP alone. The seed always runs to completion, "
        "so what this stops is improvement rather than the answer, and the gallery it "
        "stops on is valid. Unset is until a full pass finds no improving swap",
    )
    search.add_argument(
        "--augment",
        choices=("on", "off"),
        default="on" if solve_module.DEFAULT_AUGMENT else "off",
        help="the augmenting-chain stage: eject one seat, insert TWO in its room. THE ONLY "
        "STAGE THAT RAISES THE SEAT COUNT — a 1-swap conserves it, so tier 1 was frozen at "
        "the greedy seed until this landed. ON unasked (Matt's ruling, 2026-09-04), so a "
        "record that does not name this ran WITH it and is not comparable to one taken "
        "before. It fills the gallery at n=750 and n=1000 on the pool of that day, and it "
        "PAYS for the seats in the three tiers beneath — the swap loop runs again after it "
        "to buy back what it can. `off` is the incumbent leg",
    )
    search.add_argument(
        "--augment-depth",
        type=int,
        choices=(2, 3),
        default=augment_module.DEFAULT_DEPTH,
        help="how long a chain may be: 2 is one ejection and two inserts, 3 is one more "
        f"eject/insert pair. Unasked, {augment_module.DEFAULT_DEPTH}, and that is a "
        "measurement — at n=2000 depth 3 bought 15 seats against depth 2's 294 and spent a "
        "whole second budget doing it, and at the smaller rungs the gallery was already "
        "full before depth 3 was asked anything",
    )
    search.add_argument(
        "--augment-seconds",
        type=float,
        default=augment_module.DEFAULT_SECONDS,
        metavar="SECONDS",
        help="a wall budget for the AUGMENT STAGE alone. The stage is anytime and stops at "
        "a chain boundary, never inside one, so the gallery it stops on is valid. Unasked, "
        f"{augment_module.DEFAULT_SECONDS:g}s: the search exhausts in 1.0s at n=750 and "
        "5.8s at n=1000, so it never binds at the shipping rungs, and n=2000 ran 574s "
        "without exhausting, so there it binds and is meant to",
    )


def _seat_sheet_of_records(args: argparse.Namespace) -> int:
    """The other axis: one rule, two POOLS — a run's own before and after.

    **It holds no pool and solves nothing.** Both seatings already exist as
    recorded galleries, so this reads two stamps and diffs them, which is what
    makes it answerable in seconds after a night rather than being a second pair
    of solves. The `--before`/`--after` pair is therefore NOT a variation on the
    two-key sheet above; it is the same page over a different question, and
    `seat_sheet.RUNS` is the wording that says so on the page itself.

    ⚠ **The two records must be the same n and the same rule** or the diff is
    reading two disagreements at once. Nothing here can check the rule — a record
    carries its config and not its ranking — so the seat counts are compared and
    a mismatch is refused rather than laid out.
    """
    from fractal_wallpapers.curation import seat_sheet, tentative

    if not (args.before and args.after):
        print("--before and --after are one pair; name both stamps")
        return 1
    try:
        before = seat_sheet.of_stamp(args.before)
        after = seat_sheet.of_stamp(args.after)
    except tentative.TentativeRefused as refusal:
        print(refusal)
        return 1
    if len(before["seated"]) != len(after["seated"]):
        print(
            f"--before seats {len(before['seated']):,} and --after seats "
            f"{len(after['seated']):,}. A diff of two gallery SIZES is not a diff of "
            f"what the run moved; solve both at one n"
        )
        return 1

    diff = seat_sheet.difference(before, after)
    # `rank_key` is not on a recorded row and this page does not pretend it is:
    # the caption reads a dash there. `fine_score` is already mapped by `of_stamp`.
    try:
        page, record = seat_sheet.build(args.sheet_name, diff, cap=args.cap, axis=seat_sheet.RUNS)
    except seat_sheet.SeatSheetError as nothing:
        print(nothing)
        return 0
    record = {**record, "before_stamp": str(args.before), "after_stamp": str(args.after)}
    seat_sheet.record_path(args.sheet_name).write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(record, indent=1))
    print(display_path(page))
    return 0


def seat_sheet_cap() -> int:
    """The sheet's cap, read off the module rather than restated in a help string."""
    from fractal_wallpapers.curation import seat_sheet

    return seat_sheet.CAP


def curate_seat_sheet(args: argparse.Namespace) -> int:
    """Solve one pool twice and lay out only the seats the two keys disagree about."""
    from fractal_wallpapers.curation import seat_sheet, solve
    from fractal_wallpapers.models import gallery_grade_train

    if args.before or args.after:
        return _seat_sheet_of_records(args)

    # ONE pool, solved twice. Two pools would be two populations and the diff
    # would carry whatever moved between them as though the key had done it.
    candidates, _refused = solve.pool()
    try:
        incumbent_order, incumbent_coverage = solve.ranking_for(candidates, solve.RANK_KEY)
        cascade_order, cascade_coverage = solve.ranking_for(candidates, solve.CASCADE_KEY)
    except solve.SolveRefused as refusal:
        print(refusal)
        return 1

    def run(order, coverage, key):
        return solve.solve(candidates, n=args.n, order=order, coverage=coverage, key=key)

    print(f"[seat-sheet] solving n={args.n} under {solve.RANK_KEY!r}")
    incumbent = run(incumbent_order, incumbent_coverage, solve.RANK_KEY)
    print(f"[seat-sheet] solving n={args.n} under {solve.CASCADE_KEY!r}")
    candidate = run(cascade_order, cascade_coverage, solve.CASCADE_KEY)

    diff = seat_sheet.difference(incumbent, candidate)
    # The columns the page captions each card with, joined here because this is
    # the one place that holds both orders and the head's own reading at once.
    fine = gallery_grade_train.read_pool_scores()
    for half in ("arriving", "departing"):
        for row in diff[half]:
            read = fine.get(str(row["key"])) or {}
            # `p_ge4` and not `rank_score`: it is the column the cascade orders
            # on and the one the head's bar is stated against, and the two order
            # this pool at Spearman 0.92 rather than identically.
            row["fine_score"] = read.get("p_ge4")
            row["rank_key"] = incumbent_order.get(str(row["key"]))
    try:
        page, record = seat_sheet.build(args.sheet_name, diff, cap=args.cap)
    except seat_sheet.SeatSheetError as nothing:
        print(nothing)
        return 0
    print(json.dumps(record, indent=1))
    print(display_path(page))
    return 0


def add_steps(steps) -> None:
    """The gallery half: the solve, its record, and the readings over it."""
    from fractal_wallpapers.curation import candidate_ledger as candidate_ledger_module
    from fractal_wallpapers.curation import ceiling as ceiling_module
    from fractal_wallpapers.curation import distinct as distinct_module
    from fractal_wallpapers.curation import growth as growth_module
    from fractal_wallpapers.curation import headroom as headroom_module
    from fractal_wallpapers.curation import k_sweep as k_sweep_module
    from fractal_wallpapers.curation import release as release_module
    from fractal_wallpapers.curation import solve as solve_module
    from fractal_wallpapers.curation import tentative as tentative_module
    from fractal_wallpapers.curation import view as view_module

    solving = steps.add_parser(
        "solve",
        help="choose the gallery: a stratified view, a greedy seed, and 1-swap improvement",
        description=(
            "ONE leg, one pool, one command. A per-pass stratified VIEW over the pool above "
            "its per-mode bars — one row per place plus each place's best row per (kind, "
            "mode, cell) stratum, then either the whole stratum or a band-blind slice of it, "
            "never a top-by-score cut. A GREEDY SEED in the seating order this project "
            "already had: the mandated demands from their own subpools scarcest first, then "
            "the ranked walk. Then 1-SWAP IMPROVEMENT — one seat out, one candidate in, "
            "accepted only on strict lexicographic improvement, to exhaustion. ANYTIME: the "
            "gallery is valid from its first seat, so a clock or a Ctrl-C leaves an answer. "
            "The objective is lexicographic and strict: seats filled, then the worst seated "
            "score, then the shortfall against the mode floors and any colour target, then "
            "the sum — all in the FITTED rank key. TWO HARD RULES: one wallpaper per "
            "location, and the diversity rule, which refuses a picture within ceiling.TAU of "
            "one already seated. Everything else is counted with the shortfall recorded: no "
            "fallback leg, no least-violating rescue, unfilled beats padded. The REJECTION "
            "LEDGER is the product. The exact solve this replaced is RETIRED: it was "
            "measured infeasible at n=1000 against a thirty-minute bar. "
            "The seats a record names are a PROTECTION CLASS in `curate "
            "candidate-ledger prune` — an ID that stopped resolving would take its picture "
            "with it, and nothing would notice. The `sweep` and `truncate` experiments went "
            "with the exact solver they were experiments on."
        ),
    )
    solving.set_defaults(handler=curate_solve)
    solve_verbs = solving.add_subparsers(dest="what", required=True)

    running_solve = solve_verbs.add_parser(
        "run",
        help="choose one gallery, render its seats and cut its sheet",
        description=(
            "The solve itself, under whatever this invocation asks for. `run` rewrites "
            "`--name` every time, which is a decision rather than a handle — a solve worth "
            "pointing at later is a `record`."
        ),
    )
    # Seven groups over twenty-six flags. Every flag here is one `run` reads and
    # `record` does not: a record is `run` with nothing changed, which is the
    # whole claim it makes, so a record that took one of these would not be
    # reproducible from the `curate solve run` it names. That used to be a
    # runtime check against a list; it is the parser's now.
    which_record = running_solve.add_argument_group(
        "what to call it",
        "`run` rewrites --name every time; `record` stamps --solve-name and never writes over it",
    )
    pool_size = running_solve.add_argument_group("how big, and how much of the pool it reaches")
    demands = running_solve.add_argument_group(
        "the demands",
        "every one of these is counted with its shortfall recorded: unfilled beats "
        "padded, and no demand is ever met by a fallback leg",
    )
    themed = running_solve.add_argument_group(
        "a themed gallery",
        "one dominant colour cell at the relaxed bar; the other two are ignored without --themed",
    )
    distinctness = running_solve.add_argument_group("the distinctness rules")
    search = running_solve.add_argument_group("the objective and the search")
    release_leg = running_solve.add_argument_group("the release leg and the sheet")

    which_record.add_argument(
        "--name",
        help="what to call this pass's output directory (default `n<N>`). A `record` names "
        "its solve directory with `--solve-name` instead, because it writes two things and "
        "they are stamped together",
    )
    pool_size.add_argument(
        "--n",
        type=int,
        default=None,
        help=f"how many wallpapers to seat (default "
        f"{candidate_ledger_module.FIRST_SOLVE}, the size a leg is read at). A `record` "
        f"seats {tentative_module.RECORDED_SEATS} by default instead, which is the size a "
        f"record is kept at",
    )
    pool_size.add_argument(
        "--locations",
        type=int,
        metavar="COUNT",
        help="let the pass reach only this many strongest CLUSTERS — a kept place plus "
        "every place the neutral pre-selection folded into it — ranked by their best "
        "candidate on the fine head's p_fine where it has read the row and raw P(>=4) "
        "where it has not. Taken after the pre-selection, so it never drops a place whose "
        "cluster sibling survives. Unset is the whole ledger",
    )
    pool_size.add_argument(
        "--rows-per-seat",
        type=int,
        default=view_module.ROWS_PER_SEAT,
        metavar="ROWS",
        help=f"how many view rows each stratum keeps per seat it could contribute "
        f"(default {view_module.ROWS_PER_SEAT}). Larger reaches more of the pool and costs "
        "one pixel-cloud signature a row",
    )
    pool_size.add_argument(
        "--draw-seed",
        type=int,
        default=view_module.DRAW_SEED,
        metavar="SEED",
        help=f"the seed the view's band-blind stride offsets are drawn under (default "
        f"{view_module.DRAW_SEED}). It is on the record either way",
    )
    pool_size.add_argument(
        "--allow-unranked",
        action="store_true",
        help="choose even though the key cannot read every clearing candidate. Unsaid, "
        "that is REFUSED: an unreadable row sorts last and cannot win a seat while a "
        "readable one is left, so a pool holding any is a pass that ignores them silently. "
        "The usual cause is a leg merged before its pictures were swept, and the fix is "
        "`curate flatness sweep`. This flag is for the other case — a picture on disk that "
        "will not decode, which has no reading to take and never will",
    )
    demands.add_argument(
        "--target",
        action="append",
        metavar="CELL=FRACTION",
        help="demand that at least this share of the REALIZED seats be dominant in this "
        "colour cell. A demand and not a row: it is seated from its own subpool by the "
        "scarcity leg, it counts in the third objective tier, and a target the pool cannot "
        "meet is a recorded shortfall rather than a refusal. The target also raises that "
        "cell's and its family's ceiling allowance, so the demand is not refused by the "
        "ceiling it asked for",
    )
    demands.add_argument(
        "--mode-floor",
        type=int,
        metavar="SEATS",
        help="an ARTIFICIAL flat mode floor, one number for every accepted mode. Unset is "
        "the per-mode floor rule, which is the default; `--flat-floor` is the other way "
        f"off it, floor(n / {solve_module.SEATS_PER_MODE_FLOOR}). A record taken under any "
        "of the three says which it was",
    )
    demands.add_argument(
        "--flat-floor",
        action="store_true",
        help="solve under the FLAT mode floor instead of the per-mode rule — "
        f"floor(n / {solve_module.SEATS_PER_MODE_FLOOR}) seats for every accepted mode, "
        "which is what every gallery before 2026-08-31 was seated under. The default is "
        "curation.mode_policy.seat_floors(n): half each accepted strange mode's share of "
        "the strange seat budget. Refuses beside `--mode-floor`, which asks for a "
        "different flat one",
    )
    demands.add_argument(
        "--group-cap",
        choices=list(ceiling_module.GROUP_CAP_RULES),
        default=solve_module.DEFAULT_GROUP_CAP,
        help=f"which palette-group cap to run under. `{ceiling_module.PROPORTIONAL}` is "
        f"max(1, floor({ceiling_module.GROUP_CAP_RATE:g} * n)) — 1 up to n=40, 3 at n=150, "
        f"25 at n=1000 — and is THE DEFAULT since 2026-08-28, the ckpt-88 ruling. "
        f"`{ceiling_module.IDENTITY}` is ceiling.GROUP_CAP = {ceiling_module.GROUP_CAP}, one "
        f"seat a map. It is a COUNT under either rule: the same-group DISTANCE row the exact "
        f"solve carried is retired and not merged",
    )
    themed_flags(themed)
    collection_flag(pool_size)
    distinctness.add_argument(
        "--neutral-radius",
        type=float,
        default=distinct_module.PRESELECT_RADIUS,
        metavar="COSINE",
        help="the neutral pre-selection radius applied at pool construction "
        f"(default {distinct_module.PRESELECT_RADIUS:g}). Geometric distinctness only: it "
        "asks whether two places are the same place, and it is NOT the diversity rule",
    )
    distinctness.add_argument(
        "--no-preselection",
        action="store_true",
        help="choose from the whole clearing pool, with no neutral pre-selection",
    )
    distinctness.add_argument(
        "--no-diversity",
        action="store_true",
        help="choose without the diversity rule, which is the only rule that opens a "
        f"picture. A gallery without it is a bound on a program that does not refuse "
        f"inside {ceiling_module.TAU}, and its record says so",
    )
    solve_flags_a_record_keeps(pool=pool_size, demands=demands, search=search)
    search.add_argument(
        "--explain-seats-of",
        metavar="NAME",
        help="an earlier solve record whose seats this pass explains ONE AT A TIME, into "
        "`rejection.explained`: every key it seated comes back either `seated` or with the "
        "rule that refused it here. The aggregate beside it says which rules cost this pass "
        "its seats; this says what happened to a named picture, which is the question a "
        "before/after sheet asks and the only one the aggregate cannot answer. Named rather "
        "than automatic because the refusal map is one entry per candidate over a hundred "
        "and fifty thousand of them, and a record carrying all of it would be forty times "
        "the size of the one carrying the decisions",
    )
    release_leg.add_argument(
        "--no-render",
        action="store_true",
        help="take every decision and make no release picture. The contact sheet falls "
        "back to each seat's candidate render and says which it is showing",
    )
    release_leg.add_argument(
        "--release-regime",
        default=release_module.RELEASE_REGIME.spelled,
        metavar="WxHssN",
        help=f"the geometry the release leg renders at (default "
        f"{release_module.RELEASE_REGIME.spelled}, which is what every leg that ships a "
        f"wallpaper ships; {release_module.FORMER_RELEASE_REGIME.spelled} is what the "
        f"first three gallery passes shipped at)",
    )
    release_leg.add_argument(
        "--workers",
        type=int,
        default=release_module.DEFAULT_WORKERS,
        help=f"worker processes the release leg renders over (default "
        f"{release_module.DEFAULT_WORKERS}, which is this machine's render pool; each "
        f"spawns below-normal by construction)",
    )
    release_leg.add_argument(
        "--no-sheet",
        action="store_true",
        help="take every decision and build no contact sheet",
    )
    release_leg.add_argument(
        "--sheet-out",
        metavar="PATH",
        help="write the contact sheet there instead of beside the record, which is what a "
        "before/after over several variants wants — one directory of sheets to look at",
    )

    recording = solve_verbs.add_parser(
        "record",
        help="run that same solve once and keep it under a stamp that never moves",
        description=(
            "A RECORD is `run` with nothing changed, which is the whole claim it makes: it "
            "writes the seats under a UTC stamp that is never written over, so a person can "
            "point at a picture and be understood. It writes `gallery.jsonl` (one row per "
            "seat, carrying the ledger recipe key that IS the ID, a short alias, the mode, "
            "the partition, the dominant colour cell and hue family, `centered`, the rank "
            "and P(>=4), the seat order and the stored picture), `manifest.json` beside it, "
            "and a self-contained page. It reads the flags below and no others — every one "
            "`run` carries and this does not is a flag a record could not pass through, so "
            "naming it here is refused rather than dropped on the floor."
        ),
    )
    recording.add_argument(
        "--solve-name",
        help="what to call the solve's own output directory under "
        "artifacts/curation/solve (default `tentative_n<N>_<stamp>`, the record's own "
        "stamp, so successive records at the same N coexist). A name that already "
        "holds a solve record is refused rather than written over",
    )
    recording.add_argument(
        "--n",
        type=int,
        default=None,
        help=f"how many wallpapers to seat (default {tentative_module.RECORDED_SEATS}, the "
        f"size a record is kept at, where a `run` reads a leg at "
        f"{candidate_ledger_module.FIRST_SOLVE})",
    )
    solve_flags_a_record_keeps(pool=recording, demands=recording, search=recording)
    # A THEMED record is the one thing a record could not be. Recording a themed
    # gallery had to go through `run`, which writes a solve record and never a
    # stamp — so a themed gallery could be solved and never kept, and the six
    # themed baselines of 2026-09-05 are what noticed. The three flags are the
    # same three `run` carries, from the same helper.
    themed_flags(recording)
    collection_flag(recording)

    sweeping_k = solve_verbs.add_parser(
        "k-sweep",
        help="one recorded seating per colour-ceiling K, to look at the trade",
        description=(
            "A COUNTERFACTUAL on ceiling.K, which is the headroom a colour gets over its "
            "target rate before the ceiling refuses a candidate dominant in it. One solve "
            "per K over ONE pool, everything else exactly what `record` passes, each rung "
            "kept as a solve record named `sweepK_k<K>_n<N>_<stamp>` and a tentative "
            "gallery with its page. IT MOVES NO DEFAULT: K stays whatever the constant "
            "says, and setting it is a separate act taken off the pictures this writes. "
            "RUN THE SHIPPED K AS A RUNG AND CHECK IT — a rung at the shipped K "
            "reproduces the record `record` writes at the same N, and a control that "
            "misses is itself the finding. Every rung is unpublished and every one holds "
            "prune protection until its folder is deleted, so a sweep nobody is reading "
            "is a sweep to delete."
        ),
    )
    sweeping_k.add_argument(
        "--k",
        type=float,
        action="append",
        metavar="K",
        help="a rung, repeatable. Unsaid, "
        + ", ".join(f"{k:g}" for k in k_sweep_module.RUNGS)
        + " run — the 2026-09-06 set, whose first is the shipped K and therefore the "
        "control. The allowance a K buys is `floor(K * t * n) + 1`, and it is PRINTED per "
        "rung rather than left to be computed: the product is taken in binary floating "
        "point, so K=2.4 at n=1000 allows 50 where the arithmetic on paper says 51",
    )
    sweeping_k.add_argument(
        "--n",
        type=int,
        default=k_sweep_module.SEATS,
        help=f"how many wallpapers each rung seats (default {k_sweep_module.SEATS}, the "
        "size a record is kept at — a counterfactual read at a size no record is kept at "
        "is not comparable with the record it is a counterfactual on)",
    )
    sweeping_k.add_argument(
        "--control",
        metavar="STAMP",
        help="an earlier record's stamp the FIRST rung claims to reproduce, compared seat "
        "for seat: the same keys in the same seat order, the same objective and the same "
        "refusal table. Unsaid, no check is taken — `the newest n=1000 record` is not a "
        "claim about anything, so the record a sweep is a counterfactual ON has to be "
        "named. A first rung that does not reproduce it exits 1, because a control that "
        "misses is itself the finding and the other rungs are not worth reading until it "
        "is understood",
    )

    drawing_k = solve_verbs.add_parser(
        "k-sweep-plot",
        help="draw one K sweep's per-cell figures, off the readings it already wrote",
        description=(
            "TWO PICTURES of a sweep already taken, into `scratch/k_sweep_<stamp>/`: "
            "per-cell membership at every rung with the control beside each arm, and the "
            "same as a difference against the control so a colour that FALLS as the "
            "ceiling loosens reads as a bar below zero rather than as a small one. "
            "Nothing is re-solved and no record is touched — the input is the sweep's own "
            "readings.json. Scratch only and disposable, as `curate growth plot` is: the "
            "durable product of a sweep is its readings and its records."
        ),
    )
    drawing_k.add_argument(
        "stamp",
        nargs="?",
        metavar="STAMP",
        help="the sweep's stamp, which is what `k-sweep` printed when it finished. NOT a "
        "rung's stamp: a rung is one seating and the figures are over all of them",
    )

    filling = solve_verbs.add_parser(
        "fulls",
        help="find or make each of a record's seats at the release geometry, for the viewer",
        description=(
            "The viewer shows the 640x360 candidate, which is the size the judges read and "
            "not the size a person decides at. This finds each seat at 1280x720ss2 — the "
            "release regime, and the geometry the labeling sheets are cut at — and renders "
            "only what it cannot find. The match is the recipe key AND the regime, exact: a "
            "seat whose only picture is at another frame is a miss. Nothing found is copied; "
            "what this leg owns on disk is only the pictures it made. It holds no pool and "
            "reads the ledger once for the recipes of the misses."
        ),
    )
    filling.add_argument("--stamp", help="which record to fill (default the newest)")
    filling.add_argument(
        "--workers",
        type=int,
        default=release_workers(),
        help=f"the render pool for the misses (default {release_workers()}, this machine's rule)",
    )
    filling.add_argument(
        "--no-render",
        action="store_true",
        help="report the hit rate and render nothing, which is how a leg is sized before it runs",
    )
    filling.add_argument(
        "--pin",
        action="store_true",
        help="give every found picture a second name under the RECORD'S OWN directory, so a "
        "sheet cleanup cannot take it. A hard link where the filesystem allows one, which "
        "costs no disk at all; a copy across volumes, and the readout says which it did. "
        "It is what a published record wants: 923 of the published record's 1,000 fulls "
        "were borrowed from labelling sheets on 2026-09-14 and 895 of those from one sheet",
    )

    viewing = solve_verbs.add_parser(
        "viewers",
        help="a viewer per named record under the viewer directory, and `all.html` over them",
        description=(
            "Each record's page, built exactly as `browse` builds it, lands at "
            "`<viewer>/<label>/index.html`: the collection a `targets_<collection>_n…` solve "
            "name says, else `general`, with `_n<seats>` where the size is not the recorded "
            "one. `all.html` beside them links every one with seats against target and the "
            "seated `p_fine` median and q1. Nothing is rendered."
        ),
    )
    viewing.add_argument("stamps", nargs="+", metavar="STAMP", help="the records, one each")

    browsing = solve_verbs.add_parser(
        "browse", help="write a record's page again, off the rows it already holds"
    )
    browsing.add_argument(
        "id",
        nargs="*",
        metavar="STAMP",
        help="the stamp, which `--stamp` also names. A reader who has just seen one printed "
        "will type it either way, and the cost of taking only one spelling is a page "
        "silently written for a DIFFERENT record",
    )
    browsing.add_argument(
        "--stamp",
        help="which record to write again (default the newest)",
    )
    browsing.add_argument(
        "--spacing",
        action="store_true",
        help="print what the PRESENTATION ORDER bought this record, and write no page. "
        "The gap between seats sharing a cell, a mode, a hue family or a spiral verdict, "
        "how many pairs of each TOUCH beside the floor their own counts impose on every "
        "order there is, where those pairs sit in the page, the spiral clumping, and the "
        "within-window embedding distance — each of them under the order the page shipped "
        "with and under the derived one, measured by one function so the pair is a "
        "comparison rather than two instruments",
    )
    browsing.add_argument(
        "--out",
        metavar="PATH",
        help="write the page HERE instead of beside the record's rows, with every "
        "thumbnail resolved relative to where it lands. That is the difference between "
        "this and copying `index.html` afterwards, which points at nothing. The record's "
        "own page is left alone",
    )
    browsing.add_argument(
        "--viewer",
        action="store_true",
        help="write the page to the VIEWER directory — `curation.tentative.viewer_dir()`, "
        "one place with no stamp in its name — instead of beside the record's rows. That is "
        "the path to bookmark: a record's own page names the stamp it is of, and the "
        "official record moves every checkpoint, so a bookmark onto one is a bookmark onto "
        "a superseded gallery. With no stamp named it is the newest PUBLISHED record, which "
        "is what the bookmark is for. `--out` names another place and the two are not given "
        "together",
    )

    listing_recipes = solve_verbs.add_parser(
        "recipes",
        help="what each of a record's seats is MADE of, as a tracked file beside its rows",
        description=(
            "A seat row names the picture that was seated; it does not say what the picture "
            "is. The key is a one-way digest and the recipe behind it lives in the untracked "
            "candidate ledger, so 994 of the published record's 1,000 seats could not be "
            "drawn from tracked data at all — the six that could being an accident of "
            "overlap with a tracked decision store. This writes `recipes.jsonl` beside "
            "`gallery.jsonl`: one {key, recipe} row per seat, 0.68 MiB for a thousand, every "
            "row checked to recompute its own key before it is written. `render --recipe` is "
            "the door that draws one back."
        ),
    )
    listing_recipes.add_argument("--stamp", help="which record (default the newest published)")
    listing_recipes.add_argument(
        "--write",
        action="store_true",
        help="write the file. Without it this reads the ledger and reports what WOULD be "
        "written, which is how a record is checked for redrawability before anything lands",
    )

    resolving = solve_verbs.add_parser(
        "resolve", help="turn an ID or alias back into a row, a recipe and a location"
    )
    resolving.add_argument(
        "id",
        nargs="*",
        help="the IDs or aliases to look up, as arguments or as one comma-separated list, "
        "so one invocation answers a whole figure prompt",
    )
    resolving.add_argument(
        "--stamp",
        help="which record to look them up in (default the newest)",
    )

    solve_verbs.add_parser("list", help="name every record on this machine")

    growing = steps.add_parser(
        "growth",
        help="what N candidates' worth of mining buys, at every gallery size",
        description=(
            "A re-runnable instrument. The history was never snapshotted, so the curve is "
            "read off the pool as it stands: draw a fraction of the VISITS that made it — "
            "a visit is (location, leg), never a row, because drawing rows would be the "
            "same history with the depth arm switched off — and solve the gallery over "
            "what those visits produced. Every rung is solved by production's own "
            "`curate solve run`, at the same bars, floors, allowances and objective; "
            "restricting the pool is the only difference, and the restriction is in "
            "memory and never touches the ledger. A subsample that cannot fill n is a "
            "FINDING, not an error. Each run writes a new stamped folder and overwrites "
            "none, so re-running after each mining leg accumulates a chronological series."
        ),
    )
    growing.set_defaults(handler=curate_growth)
    growth_verbs = growing.add_subparsers(dest="what", required=True)
    sweeping_rungs = growth_verbs.add_parser(
        "run", help="sweep the rungs and write a stamped folder"
    )
    drawing_a_curve = growth_verbs.add_parser(
        "plot", help="draw a finished stamped run into scratch/"
    )
    drawing_a_curve.add_argument(
        "stamp",
        nargs="?",
        help="which stamped run to draw. Unnamed, the stamps this machine holds are printed",
    )
    sweeping_rungs.add_argument(
        "--name",
        help="what to call this run's stamped folder (default: the UTC clock, to the "
        "second). A folder that already exists is refused rather than overwritten",
    )
    sweeping_rungs.add_argument(
        "--fraction",
        type=int,
        action="append",
        metavar="DENOMINATOR",
        help="a rung, named by the DENOMINATOR of the fraction of visits it draws — `8` "
        f"is one visit in eight, `1` is the whole pool (default "
        f"{list(growth_module.DENOMINATORS)})",
    )
    sweeping_rungs.add_argument(
        "--n",
        type=int,
        action="append",
        help=f"a gallery size to solve at (default {list(growth_module.SIZES)}). 2000 comes "
        "back the moment the pool can seat it",
    )
    sweeping_rungs.add_argument(
        "--seed",
        type=int,
        action="append",
        help=f"a draw seed for the rungs below the whole pool (default "
        f"{list(growth_module.SEEDS)}). The whole pool is not drawn and takes none",
    )
    sweeping_rungs.add_argument(
        "--swap-seconds",
        type=float,
        help="a wall budget for each solve's swap loop. Unset is production, which is "
        "unbounded — set it and the rows are no longer comparable with an unbudgeted run",
    )

    headroom_step = steps.add_parser(
        "headroom",
        help="census what each selection constraint needs, what the ledger holds, and "
        "what one more would cost",
        description=(
            "O(rows) necessary conditions over the candidate ledger, at several gallery "
            "sizes. No solver: a slow solve that reports `there are no light greens at "
            "all` spent twenty minutes on a fact one pass over the rows already knew. "
            "Counts are DISTINCT LOCATIONS and never rows, because one wallpaper per "
            "location is absolute. Each row says what it needs at n, what the pool holds, "
            "the slack, and the marginal cost of buying one more — estimated off the "
            "ledger's own realized attempt-to-success rate times the realized per-mode "
            "render cost. A short row is provable infeasibility; a row with slack is NOT "
            "a claim that the selection is possible. The census is taken over the pool the "
            "seating will see, neutral pre-selection included. One block is not arithmetic "
            "and is opt-in: `--twin`."
        ),
    )
    headroom_step.add_argument(
        "--bars",
        action="store_true",
        help="print the per-mode bar table and stop. Which column each accepted mode's "
        "rows clear on, and how many rows and distinct places clear it — `headroom.bars`, "
        "which the census reads anyway and which nothing else could print. No census, no "
        "solver, no neutral pre-selection. What a before-and-after of a re-score is read "
        "off: the clearing set is the population every seating starts from, so a leg that "
        "moved thousands of scores moved this table and the size of the move is the answer",
    )
    headroom_step.add_argument(
        "--n",
        type=int,
        action="append",
        metavar="SEATS",
        help="census at this gallery size; repeatable. Unset is the whole ladder "
        f"({', '.join(str(size) for size in headroom_module.LADDER)})",
    )
    headroom_step.add_argument(
        "--name",
        default="latest",
        help="what to call this census's output directory (default `latest`)",
    )
    headroom_step.add_argument(
        "--neutral-radius",
        type=float,
        default=distinct_module.PRESELECT_RADIUS,
        metavar="COSINE",
        help="the neutral pre-selection the census is taken over "
        f"(default {distinct_module.PRESELECT_RADIUS:g}). A place closer than this to a "
        "place already kept is refused before anything is counted",
    )
    headroom_step.add_argument(
        "--no-preselection",
        action="store_true",
        help="census the whole clearing pool, with no neutral pre-selection. The only way "
        "to read a schema 1 census against this one",
    )
    headroom_step.add_argument(
        "--flat-floor",
        action="store_true",
        help="bound the FLAT mode floor instead of the per-mode rule — "
        f"floor(n / {solve_module.SEATS_PER_MODE_FLOOR}) seats for every accepted mode, at "
        "every rung. The default is curation.mode_policy.seat_floors(n), which is what an "
        "unflagged `curate seat` and an unflagged `curate solve run` are floored by, so an "
        "unflagged census bounds the gallery they would build. The block says which it ran "
        "under",
    )
    headroom_step.add_argument(
        "--twin",
        action="store_true",
        help="also count the twin constraint: every twin pair among the population's "
        "strongest picture per place, found exactly, and the bounds it puts on how many "
        "mutually non-twin places the pool holds. MINUTES — one pixel-cloud signature per "
        "place plus the pairs the sound bound cannot settle — which is why it is opt-in. "
        "The sweep is written beside the census as `twins.json`",
    )
    headroom_step.add_argument(
        "--twin-from",
        metavar="PATH",
        help="count the twin constraint off a sweep already taken — the `twins.json` a "
        "`--twin` run wrote. Re-reading a census at a different ladder is arithmetic and "
        "should not cost the sweep again",
    )
    headroom_step.set_defaults(handler=curate_headroom)

    seating_sheet = steps.add_parser(
        "seat-sheet",
        help="the seats that change hands when the cascade orders the seating instead",
        description=(
            "ONE pool, solved twice — under the shipped rank key and under the cascade — "
            "and a page of only the rows where the two disagree, sorted good to bad by the "
            "fine head and marked arriving or departing. It uses the ledger's STORED "
            "pictures and renders nothing, it ingests nowhere, and it is not a label "
            "instrument: the captions are open so it cannot be read as one."
        ),
    )
    seating_sheet.add_argument(
        "--n", type=int, default=1000, help="gallery size both solves run at (default 1000)"
    )
    seating_sheet.add_argument(
        "--before",
        metavar="STAMP",
        help="diff two RECORDED galleries instead of solving one pool twice: the seating "
        "before something and the seating after it, which is what a mining night's own "
        "before and after are. Holds no pool and solves nothing — both seatings already "
        "exist — so it answers in seconds. Pair it with `--after`; `--n` is then ignored "
        "and the two records must already be the same size",
    )
    seating_sheet.add_argument(
        "--after",
        metavar="STAMP",
        help="the second half of `--before`. The page marks a seat arriving or departing "
        "relative to this one",
    )
    seating_sheet.add_argument(
        "--cap",
        type=int,
        default=seat_sheet_cap(),
        help=f"at most this many cards, sampled evenly across the fine head's score range "
        f"if more differ (default {seat_sheet_cap()})",
    )
    seating_sheet.add_argument(
        "--sheet-name", default="cascade_vs_rank_key", help="what to call this sheet's directory"
    )
    seating_sheet.set_defaults(handler=curate_seat_sheet)
