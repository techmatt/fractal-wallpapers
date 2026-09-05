"""`curate`: the candidate pool, the solver, and everything read over them.

## Why this is one file of 3,800 lines and not three

Asked again once `curation/`'s README had been split into a taxonomy this could
have borrowed — the stores (`README.md`), the gallery (`GALLERY.md`), the legs that
drive the render pool (`LEGS.md`) — and the answer is still no, for a mechanical
reason rather than a taste one.

**Registration order is `--help`.** `argparse` prints the 42 verbs in the order
they are added, in the usage line and again in the body, so moving one to sit
beside its kin changes the surface. A three-way cut therefore has to be contiguous
in registration order already, and it is not: `LEGS.md`'s verbs are `hunt`,
`mine`, `depth`, `shrinkage`, `remode` (26-30), then `pool-draw` (33), then
`manufacture` (41). Nine store verbs sit inside those gaps — `retention` and
`reject` between `remode` and `pool-draw`, and `below-bar`, `repeats`,
`retire-repeats`, `parity`, `replay`, `colors`, `coverage` between `pool-draw`
and `manufacture`. `README.md`'s own verbs are 1-18 and would split into three
runs for the same reason.

Only `GALLERY.md`'s block is clean (`solve`, `growth`, `headroom`, `flatness`,
`rank-key`, `distinct`, 19-25, with `signatures` at 23 the one genuinely arguable
verb — it is a durable sidecar by kind and a gallery instrument by use).

So the cut costs a reordered `--help` or an `add_commands` that interleaves three
modules' registrations to fake the old order, and neither is worth a smaller file.
`modes_commands.py` is the precedent going the other way: it is 30 lines and its
own module *because* it sits alone between two groups. A decision, not a fix.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import NamedTuple

from fractal_wallpapers.cli.common import (
    declared_ledgers,
    device_flag,
    display_path,
    ledger_flags,
    resolve_output,
    write_tracked_json,
)
from fractal_wallpapers.curation import manufacture as manufacture_module
from fractal_wallpapers.paths import (
    repo_root,
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


def curate_gallery_store(args: argparse.Namespace) -> int:
    """Record, check or restore one pass's attempt store against its tracked manifest."""
    from fractal_wallpapers.curation import durability, gallery_store

    doing = {
        "save": lambda: gallery_store.save(args.pass_id),
        "check": lambda: gallery_store.check(args.pass_id),
        "restore": lambda: gallery_store.restore(args.pass_id, force=args.force),
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


def curate_candidate_ledger(args: argparse.Namespace) -> int:
    """Backfill the candidate ledger, census it, or keep its two files durable."""
    from fractal_wallpapers.curation import candidate_ledger, durability

    doing = {
        "backfill": lambda: candidate_ledger.backfill(recolour=args.recolour),
        "census": lambda: candidate_ledger.census(n=args.n),
        "save": candidate_ledger.save,
        "check": candidate_ledger.check,
        "orphans": lambda: candidate_ledger.orphans(
            apply=args.apply, unmerged=orphan_unmerged(args)
        ),
        "pictures": candidate_ledger.picture_census,
        "prune": lambda: candidate_ledger.prune(keep=args.keep, apply=not args.dry_run),
        "re-render": lambda: candidate_ledger.re_render(limit=args.limit, workers=args.workers),
        "score": lambda: candidate_ledger.rescore(limit=args.limit),
        "restore": lambda: candidate_ledger.restore(force=args.force),
    }[args.what]
    try:
        report = doing()
    except (candidate_ledger.LedgerError, durability.DurableLost) as refusal:
        print(refusal)
        return 1
    if args.what == "census" and args.out:
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
                f"\n{len(held) - len(published)} unpublished record(s): kept and read by "
                f"naming the stamp, but not tracked and never what an unstamped read means. "
                f"Publishing one is Matt's decision — `curation.tentative.PUBLISHED` and the "
                f"negation lines in `.gitignore` are the list."
            )
        return 0

    if args.what == "record":
        return _record_a_solve(args)

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
            print(f"{display_path(tentative.page(args.stamp or (named[0] if named else None)))}")
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


def _record_a_solve(args: argparse.Namespace) -> int:
    """The production solve, run once and recorded under a stamp that never moves."""
    from fractal_wallpapers.curation import solve, tentative

    # `solve.pool` and not `headroom.population`, for `curate solve run`'s reason:
    # the two build the same candidate list — `population` IS `solve.pool` plus a
    # per-mode render-cost table read off every ledger row — and this handler has
    # never looked at that table. Streaming instead is 5.1 s and one fewer
    # whole-ledger copy.
    seats = args.n if args.n is not None else tentative.RECORDED_SEATS
    candidates, refused = solve.pool()
    try:
        order, coverage = solve.ranking_for(candidates, args.key)
        record = solve.solve(
            candidates,
            n=seats,
            order=order,
            coverage=coverage,
            key=args.key,
            swap=not args.no_swap,
            seconds=args.swap_seconds,
            spiral_cap=args.spiral_cap,
            augment_chains=args.augment == "on",
            augment_depth=args.augment_depth,
            augment_seconds=args.augment_seconds,
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
    print(f"{display_path(solve.write_record(name, record))}")
    try:
        directory = tentative.write(
            record, candidates=candidates, solve_name=name, pool_refused=refused, stamp=stamp
        )
    except tentative.TentativeRefused as refusal:
        print(refusal)
        return 1
    stamp = directory.name
    print(f"{display_path(tentative.page(stamp))}")
    manifest = tentative.read_manifest(stamp)
    print(json.dumps({"stamp": stamp, **manifest["seats"], "counts": manifest["counts"]}, indent=2))
    return 0


def curate_solve(args: argparse.Namespace) -> int:
    """Choose the gallery, or record one: a stratified view, a greedy seed, and swaps."""
    from fractal_wallpapers.curation import candidate_ledger, ceiling, solve
    from fractal_wallpapers.curation import release as release_module

    if args.what != "run":
        # A flag `run` reads and this verb does not is refused BY THE PARSER, at
        # the verb: each of the five is its own subparser and carries only what
        # its handler reads. This used to be a list of run-only flags compared
        # against a bare re-parse of the same verb, which was the same rule
        # enforced a step too late — after argparse had already accepted the line.
        return curate_recorded_solve(args)
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
        if not targets:
            targets = {str(args.themed): 1.0}
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
    explain = None
    if args.explain_seats_of:
        explain = [str(row["key"]) for row in solve.read_record(args.explain_seats_of)["seated"]]
        print(f"[solve] explaining {len(explain):,} seat(s) of {args.explain_seats_of!r} by name")

    candidates, _refused = solve.pool()
    try:
        order, coverage = solve.ranking_for(candidates, args.key)
        if coverage is not None:
            print(json.dumps(coverage, indent=2))
        record = solve.solve(
            candidates,
            n=args.n,
            targets=targets,
            floor=floor,
            locations=args.locations,
            radius=None if args.no_preselection else args.neutral_radius,
            diversity=not args.no_diversity,
            group_cap=args.group_cap,
            key=args.key,
            order=order,
            coverage=coverage,
            allow_unranked=args.allow_unranked,
            theme=args.themed,
            geometry_radius=args.themed_radius,
            themed_cap=args.themed_cap,
            rows_per_seat=args.rows_per_seat,
            draw_seed=args.draw_seed,
            spiral_cap=args.spiral_cap,
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
    path = solve.write_record(name, record)
    print(f"{path}")
    if not args.no_render:
        regime = release_module.regime_of(args.release_regime)
        made = solve.render_seats(name, record, workers=args.workers, regime=regime)
        path = solve.write_record(name, record)
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
    from fractal_wallpapers.paths import rehome

    kept = headroom.clearing(candidates)
    if radius is not None:
        kept, _record = distinct.preselect(kept, radius=float(radius))
    best: dict = {}
    for candidate in sorted(kept, key=lambda held: (-held.score, held.key)):
        best.setdefault(candidate.location, candidate)

    def picture_of(key):
        held = best.get(key)
        if held is None:
            return None
        where = Path(rehome(held.picture))
        return where if where.is_file() else None

    # The sidecar holds exactly the vector this sweep builds, keyed on the RECIPE;
    # the sweep is keyed on the place, and `best` is the map between them.
    held_signatures = signatures.for_candidates(best.values())

    def reduced_for(key):
        candidate = best.get(key)
        return None if candidate is None else held_signatures.get(str(candidate.key))

    keys, matrix = distinct.matrix_for(sorted(best))
    return distinct.twins(keys, matrix, picture_of, reduced_for=reduced_for)


class _PictureOf(NamedTuple):
    """The two fields `flatness.missing` reads, for a population that is not a pool.

    `--all` sweeps every ledger row with a picture rather than the pool, and a
    ledger row is not a [`solve.Candidate`] — it has no score, and rows a person
    rejected have no place in a pool and are still pictures the fit needs read.
    """

    key: str
    picture: str


def curate_flatness(args: argparse.Namespace) -> int:
    """Sweep the dead-space column over the pool, or keep the sidecar it lands in."""
    from fractal_wallpapers.curation import durability, flatness, solve

    if args.what in ("save", "check", "restore"):
        durable = flatness.durable()
        if args.what == "save":
            print(json.dumps(durability.save(durable), indent=2))
            return 0
        if args.what == "check":
            report = durability.check(durable)
            print(json.dumps(report, indent=2))
            return 0 if report["verdict"] in ("ok", "grown", "unrecorded") else 1
        print(json.dumps(durability.restore(durable, force=args.force), indent=2))
        return 0

    if args.all:
        from fractal_wallpapers.curation import candidate_ledger

        rows = candidate_ledger.read()
        present = candidate_ledger.present_pictures(rows)
        candidates = [
            _PictureOf(str(row["key"]), str(row["picture"]))
            for row in rows
            if row.get("picture") and str(row["key"]) in present
        ]
        print(f"[flatness] every ledger row with a picture on disk: {len(candidates):,}")
    else:
        # `solve.pool` and not `headroom.population` — see `curate solve record`.
        candidates, _ = solve.pool()
    if args.what == "coverage":
        print(json.dumps(flatness.coverage(candidates), indent=2))
        return 0
    record = flatness.sweep(candidates, workers=args.workers, recompute=args.recompute)
    print(json.dumps(record, indent=2))
    print(json.dumps(flatness.coverage(candidates), indent=2))
    return 0


def curate_signatures(args: argparse.Namespace) -> int:
    """Sweep the diversity rule's bound signature, or keep the sidecar it lands in."""
    from fractal_wallpapers.curation import durability, headroom, signatures, solve

    # Before the population is built, because the three keeping verbs are about
    # the file on disk and reading the clearing pool to save it would be minutes
    # of work to copy bytes. Same shape as `curate flatness`.
    if args.what in ("save", "check", "restore"):
        durable = signatures.durable()
        if args.what == "save":
            print(json.dumps(durability.save(durable), indent=2))
            return 0
        if args.what == "check":
            report = durability.check(durable)
            print(json.dumps(report, indent=2))
            return 0 if report["verdict"] in ("ok", "grown", "unrecorded") else 1
        print(json.dumps(durability.restore(durable, force=args.force), indent=2))
        return 0

    # `solve.pool` and not `headroom.population` — see `curate solve record`.
    candidates, _ = solve.pool()
    kept = headroom.clearing(candidates)
    print(f"[signatures] the clearing pool: {len(kept):,} candidate(s)")
    if args.what == "coverage":
        print(json.dumps(signatures.coverage(kept), indent=2))
        return 0
    record = signatures.sweep(kept, workers=args.workers, recompute=args.recompute)
    print(json.dumps(record, indent=2))
    print(json.dumps(signatures.coverage(kept), indent=2))
    return 0


def curate_rank_key(args: argparse.Namespace) -> int:
    """Fit the seating's sort key, or print the one that is shipped."""
    from fractal_wallpapers.curation import rank_key

    if args.what == "show":
        document = json.loads(rank_key.artifact_path().read_text(encoding="utf-8"))
        print(json.dumps(document, indent=2))
        return 0
    document = rank_key.fit()
    print(
        json.dumps(
            {
                name: document[name]
                for name in ("coefficients", "standardization", "population", "out_of_fold")
            },
            indent=2,
        )
    )
    return 0


def curate_distinct(args: argparse.Namespace) -> int:
    """The neutral pre-selection read: the join, the distribution, the premise, the sheet."""
    from fractal_wallpapers.curation import distinct, headroom, solve
    from fractal_wallpapers.paths import rehome

    # `solve.pool` and not `headroom.population` — see `curate solve record`.
    candidates, _ = solve.pool()
    kept = headroom.clearing(candidates)
    best: dict = {}
    for candidate in sorted(kept, key=lambda held: (-held.score, held.key)):
        best.setdefault(candidate.location, candidate)

    def picture_of(key):
        held = best.get(key)
        if held is None:
            return None
        where = Path(rehome(held.picture))
        return where if where.is_file() else None

    try:
        record = distinct.read(
            sorted(best),
            picture_of=None if args.no_premise else picture_of,
            pairs=args.premise_pairs,
            sweep=not args.no_sweep,
        )
    except distinct.DistinctRefused as refusal:
        print(refusal)
        return 1
    print(f"{distinct.write_record(args.name, record)}")
    out = resolve_output(args.out) if args.out else distinct.sheet_path(args.name)
    print(f"{distinct.sheet(record, out)}")
    join = record["join"]
    print(
        f"{join['embedded']:,} of {join['asked']:,} pool locations are embedded; "
        f"{join['unembedded']:,} are not"
    )
    print(json.dumps(record["nearest"], indent=2))
    if "pearson" in record["premise"]:
        print(
            f"premise: pearson {record['premise']['pearson']}, "
            f"spearman {record['premise']['spearman']} over "
            f"{record['premise']['pairs']} pair(s)"
        )
    if record["twins"].get("twin_pairs") is not None:
        print(json.dumps(record["twins"]["removed_by_radius"], indent=2))
    return 0


def curate_hunt(args: argparse.Namespace) -> int:
    """Plan a hunt, run one, merge one into the ledger, or rebuild the frame index."""
    from fractal_wallpapers.curation import embeddings as embeddings_module
    from fractal_wallpapers.curation import hunt

    try:
        if args.what == "frames":
            path, rows = hunt.build_frames()
            print(f"{display_path(path)} — {rows:,} frame(s)")
            return 0
        if args.what == "merge":
            print(json.dumps(hunt.merge(args.name), indent=2))
            return 0
        if args.what == "sheet":
            record = json.loads(hunt.record_path(args.name).read_text(encoding="utf-8"))
            print(f"{display_path(hunt.contact_sheet(args.name, record))}")
            return 0
        # Below the three that return, because --work-order is `plan`'s and
        # `run`'s and the other three verbs do not carry it to read.
        try:
            order = dict(_work_order(text) for text in (args.work_order or ()))
        except ValueError as refusal:
            print(refusal)
            return 1
        if args.what == "plan":
            if args.rebuild_frames:
                hunt.frames(rebuild=True)
            pools = hunt.drawable(hunt.scanned(), hunt.opened_locations())
            intended = hunt.plan(
                pools,
                seed=args.seed,
                per_location=args.per_location,
                unconditional=args.unconditional,
                conditioned=args.conditioned,
                cell=args.cell,
                work_order=order,
            )
            print(json.dumps(hunt.shape_of(pools, intended), indent=2))
            return 0
        if args.rebuild_frames:
            hunt.build_frames()
        record = hunt.run(
            args.name,
            seed=args.seed,
            budget=args.budget,
            per_location=args.per_location,
            unconditional=args.unconditional,
            conditioned=args.conditioned,
            cell=args.cell,
            work_order=order,
            device=args.device,
        )
    except (hunt.HuntRefused, embeddings_module.StoreRefused) as refusal:
        print(refusal)
        return 1
    print(f"{display_path(hunt.contact_sheet(args.name, record))}")
    print(json.dumps({k: v for k, v in record.items() if k != "made"}, indent=2))
    return 0


def curate_mine(args: argparse.Namespace) -> int:
    """Plan a mine, run one, or redraw its autopsy sheet."""
    from fractal_wallpapers.curation import mine

    try:
        if args.what == "sheet":
            record = json.loads(mine.record_path(args.name).read_text(encoding="utf-8"))
            print(f"{display_path(mine.contact_sheet(args.name, record))}")
            return 0
        if args.what == "merge":
            print(json.dumps(mine.merge(args.name), indent=2))
            return 0
        if args.what == "bench":
            report = mine.bench(seed=args.seed)
            path = mine.mine_dir(args.name) / "bench.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
            print(json.dumps(report, indent=2))
            print(f"{display_path(path)}")
            return 0
        if args.what == "plan":
            _intended, shape = mine.build_plan(
                mine.population(),
                seed=args.seed,
                rate=args.rate,
                budget=args.budget,
                k=args.k,
                per_location=args.per_location,
            )
            print(json.dumps(shape, indent=2))
            return 0
        record = mine.run(
            args.name,
            seed=args.seed,
            budget=args.budget,
            rate=args.rate,
            k=args.k,
            per_location=args.per_location,
            device=args.device,
        )
    except mine.MineRefused as refusal:
        print(refusal)
        return 1
    except hunt_refused() as refusal:
        print(refusal)
        return 1
    print(f"{display_path(mine.contact_sheet(args.name, record))}")
    print(json.dumps({k: v for k, v in record.items() if k != "made"}, indent=2))
    return 0


def curate_retention(args: argparse.Namespace) -> int:
    """Build the three aggregates the retention rule must not destroy."""
    from fractal_wallpapers.curation import candidate_ledger, colorize, retention

    rows = candidate_ledger.read()
    scores = {
        key: float(row.get("p_ge4") or 0.0)
        for key, row in candidate_ledger.scores_by_recipe().items()
    }
    out = retention.aggregates(rows, scores, retention.pool_stamp(colorize.pool(0)))
    # The rows themselves are tens of thousands of tuple keys and JSON has no
    # tuple, so what is printed is the shape and the sizes; --out writes the
    # whole thing with the keys joined.
    out = {
        **out,
        **{name: _sized(out[name]) for name in ("place_mode", "map_mode", "place_cell")},
    }
    text = json.dumps(out, indent=2)
    print(text)
    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8", newline="\n")
        print(display_path(path))
    return 0


def _sized(block: dict) -> dict:
    """One aggregate as JSON carries it: tuple keys joined, and the count kept."""
    return {
        "pairs": block["pairs"],
        "rows": {
            " | ".join(str(part) for part in key): value for key, value in block["rows"].items()
        },
    }


def curate_shrinkage(args: argparse.Namespace) -> int:
    """Re-read one depth run's winners at label geometry and write both curves."""
    from fractal_wallpapers.curation import candidate_ledger, depth, hunt, shrinkage

    try:
        sequence = depth.read_sequence(args.name)
        # The run's own rows overlay the ledger rather than being read out of it,
        # so a read can be taken before `curate depth merge` and on a run that was
        # killed before it could be merged at all.
        ledger = {str(row["key"]): row for row in candidate_ledger.stream()}
        ledger.update({str(row["key"]): row for row in hunt._read(depth.rows_path(args.name))})
        record = shrinkage.measure(
            args.name,
            sequence,
            ledger,
            bars=(depth.SEATING_BAR, depth.PRIMED_BAR),
            per_arm=args.per_arm,
            seed=args.seed,
            workers=args.workers,
            device=args.device,
        )
    except shrinkage.ShrinkageRefused as refusal:
        print(refusal)
        return 1
    print(json.dumps(record, indent=2))
    return 0


def curate_remode(args: argparse.Namespace) -> int:
    """Read the population, render a retired mode's rows again, merge them, read back."""
    from fractal_wallpapers.curation import remode

    try:
        if args.what == "merge":
            print(json.dumps(remode.merge(args.name), indent=2))
            return 0
        if args.what == "read":
            print(json.dumps(remode.read(args.name)["carry"], indent=2))
            return 0
        if args.what == "plan":
            # The plan step renders nothing and holds the pool, which is what
            # makes it the honest place to verify a count before spending an hour
            # of engine on it. It resolves every twin, so `already_in_ledger` here
            # is exactly what the run would skip.
            world = remode.population(args.from_mode)
            rule = remode.target_rule(args.to_mode)
            units, shape = remode.plan_of(world["clearing"], args.to_mode, world["known"])
            blocks = remode.blocks_of(units)
            readout = {
                "from_mode": args.from_mode,
                "to_mode": args.to_mode,
                "source_rule": world["rule"],
                "target_rule": rule,
                "population": {
                    "ledger_rows": world["ledger_rows"],
                    "in_mode": world["in_mode"],
                    "refused": world["refused"],
                    "clearing": len(world["clearing"]),
                    "clearing_locations": len({source.location for source in world["clearing"]}),
                },
                "plan": shape,
                "location_blocks": len(blocks),
                "by_partition": _remode_partitions(units),
            }
            print(json.dumps(readout, indent=2))
            return 0
        record = remode.run(
            args.name,
            from_mode=args.from_mode,
            to_mode=args.to_mode,
            budget=args.budget,
            workers=args.workers,
            device=args.device,
        )
    except remode.RemodeRefused as refusal:
        print(refusal)
        return 1
    print(json.dumps({**record["counts"], **record["budget"]}, indent=2))
    print(json.dumps(record["carry"], indent=2))
    print(f"\nrecord {display_path(remode.record_path(args.name))}")
    return 0


def _remode_partitions(units: list) -> dict:
    """Twins and places per partition, off a resolved plan.

    On the plan and not only on the record, because it is what a leg is priced
    off: `phoenix:classic` reads 35 s a candidate against `smooth`'s 0.34
    elsewhere (see `curation/MEASUREMENTS.md`), so a count that did not separate
    the planes would size this leg by more than an order of magnitude.
    """
    out: dict = {}
    for unit, _source, _recipe, _key in units:
        cell = out.setdefault(str(unit.partition), {"twins": 0, "locations": set()})
        cell["twins"] += 1
        cell["locations"].add(unit.location)
    return {
        name: {"twins": cell["twins"], "locations": len(cell["locations"])}
        for name, cell in sorted(out.items(), key=lambda item: -item[1]["twins"])
    }


def curate_depth(args: argparse.Namespace) -> int:
    """Plan a depth run, run one, merge it, or redraw its autopsy sheet."""
    from fractal_wallpapers.curation import depth

    try:
        if args.what == "sheet":
            record = json.loads(depth.record_path(args.name).read_text(encoding="utf-8"))
            print(f"{display_path(depth.contact_sheet(args.name, record))}")
            return 0
        if args.what == "merge":
            print(json.dumps(depth.merge(args.name), indent=2))
            return 0
        if args.rate is None:
            print(
                "a depth run is sized off a rate measured at ITS width, and none was given. "
                "Pass --rate the seconds a candidate a short run at this width reported."
            )
            return 1
        knobs = {
            "shares": json.loads(args.shares) if args.shares else None,
            "band_weights": json.loads(args.band_weights) if args.band_weights else None,
            "floor_modes": args.floor_modes,
            "floor_untried": (
                None if args.floor_untried is None else (args.floor_untried or depth.dear_modes())
            ),
            "floor_places": (
                None if args.floor_places is None else depth.read_places(args.floor_places)
            ),
            # `near_named` and not `near_places`: inside `build_plan` a parameter
            # of the flag's own name would shadow the draw it narrows.
            "near_named": (
                None if args.near_places is None else depth.read_places(args.near_places)
            ),
            "draw_maps": (None if args.draw_maps is None else depth.read_maps(args.draw_maps)),
            "draw_cells": args.draw_cells,
            "draw_cutoff": args.draw_cutoff,
            "floor_width": args.floor_width,
            "floor_seats": args.floor_seats,
            "roster": args.modes,
            "cell": args.cell,
            "centered": args.centered,
            "partition_weights": (
                json.loads(args.partition_weights) if args.partition_weights else None
            ),
            "breadth_demoted": (
                depth.BREADTH_DEMOTED if args.breadth_demoted is None else args.breadth_demoted
            ),
            "near_width": args.near_width,
            "top_bands": args.top_bands,
            "workers": args.workers,
        }
        if args.what == "plan":
            _intended, shape = depth.build_plan(
                depth.population(),
                seed=args.seed,
                rate=args.rate,
                budget=args.budget,
                width=args.width,
                bands=args.bands,
                **knobs,
            )
            print(json.dumps(shape, indent=2))
            return 0
        record = depth.run(
            args.name,
            seed=args.seed,
            budget=args.budget,
            rate=args.rate,
            width=args.width,
            bands=args.bands,
            device=args.device,
            **knobs,
        )
    except depth.DepthRefused as refusal:
        print(refusal)
        return 1
    except hunt_refused() as refusal:
        print(refusal)
        return 1
    print(f"{display_path(depth.contact_sheet(args.name, record))}")
    print(json.dumps(record, indent=2))
    return 0


def hunt_refused():
    """[`hunt.HuntRefused`], reached without importing the module at parse time."""
    from fractal_wallpapers.curation import hunt

    return hunt.HuntRefused


def _work_order(text: str) -> tuple:
    """`PARTITION=WEIGHT`, refused rather than guessed at."""
    if "=" not in str(text):
        raise ValueError(f"{text!r} is not PARTITION=WEIGHT, e.g. julia:mandelbrot=19")
    name, _, weight = str(text).partition("=")
    try:
        return name.strip(), int(weight)
    except ValueError as refusal:
        raise ValueError(f"{weight!r} is not a whole number of turns") from refusal


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


def curate_expressed(args: argparse.Namespace) -> int:
    """How much of the codebook the finished collection expresses, and what a floor could ask."""
    from fractal_wallpapers.curation import expressed

    try:
        if args.step_of_expressed in ("census", "all"):
            expressed.census()
        readout = expressed.take() if args.step_of_expressed in ("read", "all") else None
    except expressed.ExpressedError as refusal:
        print(refusal)
        return 1
    if readout is None:
        return 0

    population = readout["population"]
    budget = readout["budget"]
    print(
        f"\npopulation {population['pictures']} finished wallpapers over "
        f"{len(population['runs'])} passes, {population['rejected_afterwards']} since taken back"
    )
    for label in ("all", "non_neutral"):
        cell = budget[label]
        spread = cell["distribution"]
        print(
            f"{label:<12} mean {cell['sum_coverage']:.3f} swatches expressed over "
            f"{cell['swatches']} "
            f"(median {spread['median']:g}, {spread['min']}-{spread['max']}); "
            f"largest uniform floor that fits: {cell['implied_ceiling']:.4f}"
        )
    print("\nthinnest first:")
    for swatch in readout["ranked"][:12]:
        value = readout["coverage"][swatch]
        print(f"  {swatch:<26} {value:.4f}  ({round(value * population['pictures'])})")
    print(f"  ... and {len(readout['ranked']) - 12} more, in the readout")
    census_gap = readout["agreement"]["census_decode"]
    print(
        f"\n160x90 decode moves a swatch by at most "
        f"{census_gap['worst_swatch_move']:.4f} and flips "
        f"{census_gap['threshold_cells_flipped']} of {census_gap['threshold_cells']} cells"
    )
    cost = readout["recolor_cost"]
    print(
        f"recolor pass over {cost['thin_swatches']} thin swatches would put "
        f"{cost['carriers_union']} carrier maps through "
        f"{cost['populations']['field']['pictures']} field pictures and "
        f"{cost['populations']['not_field']['pictures']} that need a re-render"
    )
    print(f"\nexpressed {display_path(expressed.readout_path())}")
    print(f"pictures  {display_path(expressed.pictures_path())}")
    return 0


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


def solve_flags_a_record_keeps(*, demands, search):
    """The four flags `curate solve run` and `curate solve record` both read.

    A record IS a run, taken once and kept, so the flags it accepts are the ones
    it can pass straight through. Written once for [`common.device_flag`]'s
    reason and this one besides: a record that took a flag it did not read would
    not be reproducible from the `run` it claims to be, and the drift would show
    up as two `--help` texts describing one flag two ways.

    Two containers rather than one parser, because `run` groups its help — it
    carries twenty-six flags — and `record` at six does not, so a record hands
    the same parser twice.
    """
    from fractal_wallpapers.curation import augment as augment_module
    from fractal_wallpapers.curation import solve as solve_module

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
    search.add_argument(
        "--key",
        choices=list(solve_module.KEYS),
        default=solve_module.DEFAULT_KEY,
        help="the sort key the pool is walked in AND the quantity the objective is stated "
        "in. `rank-key` is the fitted form in `curate rank-key` — the location head, both "
        "judge cutpoints, the calibration stratum and the flatness column — and is THE "
        "DEFAULT since 2026-08-28, on Matt's acceptance by eye. `p_ge4` is the render judge "
        "alone. IT MOVES THE ORDER AND THE OBJECTIVE AND NOTHING ELSE: every bar, the "
        "clearing rule and the neutral pre-selection still read the judge's own columns",
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


#: `--workers` on the two sidecar sweeps, which read it identically.
SWEEP_WORKERS = (
    "how many processes decode at once (default {count}, the render pool's number and for "
    "the same reason: this should not make the desktop unusable while it runs)"
)

#: `--all` on `curate flatness`, which the group, `sweep` and `coverage` all take.
SWEEP_EVERY_ROW = (
    "sweep every ledger row whose picture is on disk rather than the pool. The pool "
    "excludes a row a person rejected and a row off the candidate regime, and the rank key "
    "has to be FITTED on some of those — a label row is a label row whatever the pool later "
    "did with its recipe"
)


#: `--seed` on `curate mine`, which `plan`, `run` and `bench` all take.
MINE_SEED = "the seed every draw here is taken under (default {seed})"


def depth_leg_flags(parser, *, device: bool):
    """The twenty-four flags that describe a depth leg, in five argument groups.

    `plan` and `run` take all of them and only `run` takes `--device`, on the
    same rule [`hunt_draw_flags`] states: a plan is the run with the rendering
    left out, so a flag the two did not share would be a plan pricing a leg
    nobody can run. Grouped because twenty-five flags in one undivided block is
    a reference nobody reads, and cut by what each group steers: the leg, how
    the budget is split between the four draws, how wide each goes, what it may
    stand on, and what it may colour with.
    """
    from fractal_wallpapers.curation import depth as depth_module
    from fractal_wallpapers.palettes import dominance as dominance_module

    leg = parser.add_argument_group("the leg and its clock")
    draw_shares = parser.add_argument_group("the draws and their shares")
    widths = parser.add_argument_group("how wide each draw goes")
    populations = parser.add_argument_group("the modes and places the draws work over")
    draw_palettes = parser.add_argument_group("the palettes the draws may offer")

    leg.add_argument(
        "--name",
        required=True,
        help="what to call this run. Its rows, its pictures, its sequence and its record "
        "live under it, and `merge` names it again",
    )
    leg.add_argument(
        "--budget",
        type=float,
        default=depth_module.BUDGET_SECONDS,
        metavar="SECONDS",
        help=f"how long the leg may run, in WALL seconds (default "
        f"{int(depth_module.BUDGET_SECONDS)}), however many engines are spending it. "
        "Checked before every candidate, so a wide near-band block stops inside itself",
    )
    leg.add_argument(
        "--rate",
        type=float,
        metavar="SECONDS",
        help="seconds a candidate at this width on ONE engine, which is what sizes the "
        "draws: the plan is `workers * budget / rate`. Required by `plan` and `run`. A rate "
        "carried in from a pass that ran at another width prices another loop, most of a "
        "candidate's cost here being amortised over the width. Read a pilot's "
        "`budget.seconds_per_candidate` — per engine — and never its wall over its count",
    )
    leg.add_argument(
        "--workers",
        type=int,
        default=depth_module.DEFAULT_WORKERS,
        metavar="COUNT",
        help=f"engines this leg renders on (default {depth_module.DEFAULT_WORKERS}, this "
        "machine's render pool). The unit of work is a LOCATION, because one field is "
        "dumped per (location, mode) and cutting per candidate would make three workers "
        "dump the same field. A plan with fewer location blocks than workers runs on "
        "fewer and the record says so",
    )
    draw_shares.add_argument(
        "--seed",
        type=int,
        default=depth_module.DEFAULT_SEED,
        help=f"the seed every draw here is taken under (default {depth_module.DEFAULT_SEED})",
    )
    draw_shares.add_argument(
        "--shares",
        metavar="JSON",
        help='what share of the budget each draw takes, as JSON, e.g. \'{"near_band": 0.3, '
        '"ranked_bands": 0.4, "flat": 0.0, "mode_floor": 0.3}\'. Unsaid, the three measuring '
        "draws take their own shares; the mode-floor and conditioned draws take nothing",
    )
    draw_shares.add_argument(
        "--band-weights",
        metavar="JSON",
        help="how many turns a round each rank band gets in the ranked draw, as JSON keyed "
        'by band name, e.g. \'{"band00": 3, "band09": 0}\'. A band left out gets one turn. '
        "This is how a production run spends what a measuring run learned; a measuring run "
        "leaves it alone and every band draws alike",
    )
    draw_shares.add_argument(
        "--partition-weights",
        metavar="JSON",
        help="what share of the breadth draw each PARTITION gets, as JSON keyed by "
        'partition, e.g. \'{"mandelbrot": 3, "julia:mandelbrot": 3}\'. Fractions are '
        "allowed, and this is MERGED OVER the standing table in curation.draw_weights "
        "(phoenix and phoenix:classic at 0.25, every other partition at 1.0) rather than "
        "replacing it, so a leg says what it is changing. A soft lean and never a floor: "
        "a partition left out keeps its standing weight, nothing is capped, and a "
        "partition is out of the draw only where a weight of 0 is named here",
    )
    draw_shares.add_argument(
        "--bands",
        type=int,
        default=depth_module.RANK_BANDS,
        metavar="COUNT",
        help=f"how many equal-count bands the head's rank range inside one partition is "
        f"cut into (default {depth_module.RANK_BANDS})",
    )
    draw_shares.add_argument(
        "--top-bands",
        type=int,
        default=None,
        metavar="COUNT",
        help="restrict the FLAT and CONDITIONED draws to the strongest COUNT rank bands, so "
        "the two matched arms stand on one stretch of the head's rank axis. Unsaid, they "
        "draw over the whole of it. The ranked draw is never cut: measuring the curve end "
        "to end is its whole job",
    )
    draw_shares.add_argument(
        "--centered",
        choices=list(depth_module.CENTERED_CHOICES),
        default=depth_module.CENTERED_ANY,
        help="what the breadth draws do about the walk ledger's `centered` flag: draw only "
        "centered locations, only the rest, or (default) every drawable location. The flag "
        "lives on the walk-ledger row and neither the embedding store nor the supply "
        "sidecar carries it, so it is joined back at plan time",
    )
    widths.add_argument(
        "--width",
        type=int,
        default=depth_module.WIDTH,
        metavar="COUNT",
        help=f"how many candidates one location is offered (default {depth_module.WIDTH})",
    )
    widths.add_argument(
        "--near-width",
        type=int,
        metavar="COUNT",
        help="how many candidates the NEAR-BAND draw offers one location, where that "
        "differs from --width. It usually does: a near-band location holds its mode and "
        "pays one dump over the whole set where a breadth location pays one per mode, so "
        "the width at which the marginal candidate stops paying is not the same number",
    )
    widths.add_argument(
        "--floor-width",
        type=int,
        default=depth_module.FLOOR_WIDTH,
        metavar="COUNT",
        help=f"palettes per (proven location, mode) in the mode-floor draw (default "
        f"{depth_module.FLOOR_WIDTH})",
    )
    populations.add_argument(
        "--modes",
        metavar="MODE",
        nargs="+",
        help="the modes this run can afford at all — what the breadth draws cycle, and "
        "what a near-band incumbent must be in to enter that draw. An entry is a MODE, or "
        "a mode with its own settings: `direct_trap_multiply@opacity=0.6,threshold=0.2` is "
        "a different recipe key and so a different picture beside the shipped one — nothing "
        "re-keys, nothing re-renders and no label is voided. Settings a mode does not take "
        "are refused at plan time. Unsaid, every shareable "
        "mode curation.mode_policy accepts. Narrowing it is how a run at a small width "
        "keeps the dump amortised: one field is dumped per (location, mode), so six modes "
        "at twelve candidates pays six dumps and three modes pays three. To drop a mode "
        "from breadth alone and keep it on the near band, use --breadth-demoted",
    )
    populations.add_argument(
        "--cell",
        metavar="CELL",
        nargs="+",
        help="the codebook cell or cells the CONDITIONED draw aims its palette ask at, e.g. "
        "dark_vivid_green. The arm is the flat draw with its maps drawn through the "
        "carrier table instead of uniformly, so the flat draw is its control. It is "
        "draw-biased and verdict-measured: the table decides which maps are offered and "
        "nothing else, and what a candidate is dominant in is read off its own render. "
        "Several cells split the arm's places round-robin, one cell each, so a leg sent "
        "at the pool's thinnest colours serves them evenly; a cell the carrier table "
        "cannot serve out of this map pool is dropped and named. "
        "Needs a share — pass --shares with a 'conditioned' entry",
    )
    populations.add_argument(
        "--breadth-demoted",
        metavar="MODE",
        nargs="*",
        help="modes the near band may hold but the two breadth draws do not cycle. Unsaid, "
        "NONE: which modes are worth spending on at all is curation.mode_policy's table, "
        "and this is the one thing a weight cannot say — drop a mode from breadth and keep "
        "its near-band seat. Set it per run, for a mode that pays at depth and not at width",
    )
    populations.add_argument(
        "--floor-modes",
        metavar="MODE",
        nargs="+",
        help="the modes the mode-floor draw serves, each of them a MODE or a mode with its "
        "own settings (`direct_trap_multiply@opacity=0.6,threshold=0.2`). Unsaid, it serves "
        "every mode the ledger says is short of --floor-seats seats today, worst first",
    )
    populations.add_argument(
        "--floor-untried",
        metavar="MODE",
        nargs="*",
        help="narrow the mode-floor draw's population to opened locations with NO attempt "
        "in any of these modes. Given with no mode named, that is every mode a dumped "
        "field cannot serve — the dear half of the roster — which is the opened-but-shallow "
        "population: the field is known good and the dear modes have never been asked",
    )
    populations.add_argument(
        "--floor-places",
        metavar="FILE",
        help='a places MANIFEST — a JSONL of {"schema": 1, "key": ...} rows — naming the '
        "locations the mode-floor draw may stand on. This is the one flag that says WHICH "
        "places: every other draw here picks its own off a rank, a band or a bar. A file "
        "rather than arguments because the population is hundreds of places long. It "
        "narrows the floor draw alone, which is already the draw over opened, proven "
        "locations — and that is what a list somebody read off the ledger always is. Keys "
        "the opened pool does not hold are counted and named",
    )
    populations.add_argument(
        "--near-places",
        metavar="FILE",
        help='a places MANIFEST — the same JSONL of {"schema": 1, "key": ...} rows '
        "--floor-places takes — naming the locations the NEAR-BAND draw may stand on. "
        "Unsaid, the draw takes every place whose best candidate in a roster mode sits "
        "between the two bars, which is a population built out of the whole history of "
        "this pool. Narrowing it is how a leg says `the places this night opened`: a "
        "near-band pass over a place already at the retention keep is ranked out as it "
        "lands, so an unnarrowed pass spends most of its clock on rows the merge drops. "
        "A named place holding no candidate in a mode this run can afford is counted and "
        "named, and a manifest leaving none is refused",
    )
    populations.add_argument(
        "--floor-seats",
        type=int,
        default=10,
        metavar="COUNT",
        help="how many distinct locations over the seating bar a mode needs before it is "
        "no longer short (default 10, which is about N/100 at N=1000)",
    )
    draw_palettes.add_argument(
        "--draw-maps",
        metavar="FILE",
        help='a maps MANIFEST — a JSONL of {"schema": 1, "map": ...} rows — naming the '
        "colormaps every draw here may offer. The palette twin of --floor-places, and a "
        "DRAW FILTER and nothing else: it re-marks no map, folds none, moves no bar and "
        "writes nothing back to the tracked colour records. Unsaid, a run draws the whole "
        "of `colorize.pool`. Narrowing it is how a leg aimed at the colours a seating is "
        "thin in stops spending its palettes on the colours that are already full — and "
        "the narrowed pool still has to hold a 32-map neighbourhood, or the run is "
        "refused. A map the drawable pool has stood down is refused rather than dropped "
        "quietly, because a manifest cut against the library and spent against the pool "
        "is a narrowing nobody can read off the record",
    )
    draw_palettes.add_argument(
        "--draw-cells",
        nargs="+",
        metavar="CELL",
        help="codebook cells the palettes every draw here offers must be expected to "
        "DELIVER. The rule-shaped twin of --draw-maps and it composes with it — both "
        "filters apply — and it is the same DRAW FILTER and nothing else: it re-marks no "
        "map, moves no bar and writes nothing back to the tracked colour records. A map is "
        "kept when its palette group is expected to put at least --draw-cutoff of a "
        "picture's colour in ANY listed cell, read off data/palettes/color_mass/ where "
        "there is a row for the group and off the carrier table where there is not. Unsaid, "
        "every cell, which is the whole of colorize.pool and what a run drew before this "
        "flag existed. The narrowed pool still has to hold a 32-map neighbourhood or the "
        "run is refused. Every row the leg writes is stamped hunt.drawn_cells, because a "
        "colour-narrowed leg is not a base rate",
    )
    draw_palettes.add_argument(
        "--draw-cutoff",
        type=float,
        default=None,
        metavar="SHARE",
        help=f"the share of a picture's colour a map must be expected to put in a "
        f"--draw-cells cell (default {dominance_module.CELL_LEAD}, which is "
        f"palettes.dominance.CELL_LEAD — the share at which a cell LEADS a picture, so the "
        f"default reads as 'expected to be dominant here'). Raising it narrows harder and "
        f"the thinnest cell in this library runs out of the 32-map neighbourhood between "
        f"0.10 and 0.15",
    )
    if device:
        device_flag(leg)


def mine_draw_flags(holder):
    """The five flags that describe a mine's draw, which `plan` and `run` share.

    Same rule as [`hunt_draw_flags`]: a plan is the run with the rendering left
    out, so the two describe the same draw or the plan is pricing another one.
    `bench` takes `--seed` alone, which is why that help string is a constant.
    """
    from fractal_wallpapers.curation import mine as mine_module

    holder.add_argument(
        "--budget",
        type=float,
        default=mine_module.BUDGET_SECONDS,
        metavar="SECONDS",
        help=f"how long the mine may spend RENDERING (default "
        f"{int(mine_module.BUDGET_SECONDS)}). Enforced at the candidate boundary",
    )
    holder.add_argument(
        "--rate",
        type=float,
        metavar="SECONDS",
        help="seconds a candidate, measured on THIS mine's target population, which is "
        "what sizes the arms. Required by `plan` and `run` and by nothing else. Take it "
        "off a short run first and pass the figure that run reported — a rate carried in "
        "from another pass prices another population",
    )
    holder.add_argument(
        "--k",
        type=int,
        default=mine_module.DEEPEN_K,
        metavar="COUNT",
        help=f"how many fresh palettes the DEEPEN arm offers one location (default "
        f"{mine_module.DEEPEN_K}). Wide enough that the marginal clear rate can die",
    )
    holder.add_argument(
        "--per-location",
        type=int,
        default=mine_module.PER_LOCATION,
        metavar="COUNT",
        help=f"how many candidates a breadth arm gives one location (default "
        f"{mine_module.PER_LOCATION}), the same on both so they differ only in the draw",
    )
    holder.add_argument(
        "--seed",
        type=int,
        default=mine_module.DEFAULT_SEED,
        help=MINE_SEED.format(seed=mine_module.DEFAULT_SEED),
    )


def hunt_draw_flags(holder):
    """The seven flags that describe a hunt's draw, which `plan` and `run` share.

    `plan` IS the run with the rendering left out — it prints the shape the
    budget would be spent against — so the two take the same description of what
    to draw and differ in `--budget` and `--device`, which only a run spends.
    One definition so the two cannot drift into describing different draws.
    """
    from fractal_wallpapers.curation import hunt as hunt_module

    holder.add_argument(
        "--unconditional",
        type=int,
        default=0,
        metavar="COUNT",
        help="how many breadth candidates to plan. The budget still decides how many are "
        "made; this is the size of the plan the budget is spent against",
    )
    holder.add_argument(
        "--conditioned",
        type=int,
        default=0,
        metavar="COUNT",
        help="how many candidates to plan against --cell. Needs --cell",
    )
    holder.add_argument(
        "--cell",
        help="the codebook cell the conditioned leg aims at, e.g. dark_vivid_lime. Its maps "
        "are drawn from the tracked carrier table, weighted by mean share",
    )
    holder.add_argument(
        "--work-order",
        action="append",
        default=[],
        metavar="PARTITION=WEIGHT",
        help="how the conditioned leg spreads over the partitions, repeatable — a solve's "
        "shortage list says where the pool's carriers of that colour already stand, and "
        "this is that list. Absent, the leg spreads evenly like the breadth one",
    )
    holder.add_argument(
        "--per-location",
        type=int,
        default=hunt_module.PER_LOCATION,
        metavar="COUNT",
        help=f"how many candidates one location is given (default {hunt_module.PER_LOCATION}). "
        "Shallow on purpose: a gallery seats one wallpaper per location, so a fourth "
        "candidate at a fresh place is worth more than a ninth at a stocked one",
    )
    holder.add_argument(
        "--seed",
        type=int,
        default=hunt_module.DEFAULT_SEED,
        help=f"the seed every draw here is taken under (default {hunt_module.DEFAULT_SEED})",
    )
    holder.add_argument(
        "--rebuild-frames",
        action="store_true",
        help="derive the frame index off the scan record again before planning",
    )


def keeping_verbs(verbs, *, noun: str, force: str, order=("check", "save", "restore")):
    """`check`, `save`, `restore` — the three verbs every durable store shares.

    Seven groups spell them and only the noun and the order move, so they are
    written once here for the reason [`common.device_flag`] gives: a copied
    `add_argument` costs nothing until somebody edits one of them, and then
    `--help` carries a difference that reads like a difference in behaviour.

    A REAL subparser per verb rather than one `choices=` positional, which is
    what every one of them did before: a positional puts the whole group's flags
    on every verb, so `--force` was accepted by `check` and dropped on the floor,
    and `--help` at the group was every verb's flags at once with nothing saying
    which belonged to which.

    Takes the subparsers action rather than the parser, because three of the
    groups register another verb first — `spiral-scores` builds, `flatness` and
    `signatures` sweep — and the registration order is the `--help` surface.
    """
    for name in order:
        if name == "check":
            verbs.add_parser("check", help=f"check the live {noun} against the manifest")
        elif name == "save":
            verbs.add_parser("save", help="save a fresh copy and manifest")
        else:
            restoring = verbs.add_parser(
                "restore", help="restore the archived copy, counted before it is believed"
            )
            restoring.add_argument("--force", action="store_true", help=force)
    return verbs


def add_commands(subcommands) -> None:
    """The last stage: harvest supply in, released wallpapers out."""
    from fractal_wallpapers.curation import below_bar as below_bar_module
    from fractal_wallpapers.curation import budget as budget_module
    from fractal_wallpapers.curation import candidate_ledger as candidate_ledger_module
    from fractal_wallpapers.curation import ceiling as ceiling_module
    from fractal_wallpapers.curation import colors as colors_module
    from fractal_wallpapers.curation import distinct as distinct_module
    from fractal_wallpapers.curation import embeddings as embeddings_module
    from fractal_wallpapers.curation import flatness as flatness_module
    from fractal_wallpapers.curation import growth as growth_module
    from fractal_wallpapers.curation import headroom as headroom_module
    from fractal_wallpapers.curation import hunt as hunt_module
    from fractal_wallpapers.curation import mine as mine_module
    from fractal_wallpapers.curation import pool_draw as pool_draw_module
    from fractal_wallpapers.curation import release as release_module
    from fractal_wallpapers.curation import remode as remode_module
    from fractal_wallpapers.curation import rules as rules_module
    from fractal_wallpapers.curation import run as run_module
    from fractal_wallpapers.curation import shrinkage as shrinkage_module
    from fractal_wallpapers.curation import signatures as signatures_module
    from fractal_wallpapers.curation import solve as solve_module
    from fractal_wallpapers.curation import tentative as tentative_module
    from fractal_wallpapers.curation import view as view_module

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

    reading = ledger_flags(
        steps.add_parser(
            "score",
            help="read the harvest ledgers through the location head",
            description=(
                "Reads each gate-surviving location through the head, at the regime its own "
                "ledger row names: a walk's gate render where the row's recorded digest still "
                "describes it, the deploy view already on disk for the standing stock. No "
                "deploy-geometry render is ever demanded for a row that was not scored at one. "
                "Resumable in both halves: a picture already on disk is not re-made."
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
        help="the colour-mass sweep log's durability: record it, check it, restore it",
        description=(
            "artifacts/curation/palette_mass_sweep/rows.jsonl is the 25.7 MB experiment log "
            "the tracked colour-mass map was cut from: one row per (palette group, mode, "
            "location) with its 48-cell vector, its recipe and whether autolevel acted. It "
            "is insurance rather than a record anything reads — what production reads is "
            "the map under data/palettes/color_mass/ — and it is the only thing that would "
            "let the map be re-cut on other terms. Re-deriving it is 8.7 h of wall over "
            "27,053 renders whose pictures were deleted, so the bytes go to the archive "
            "tier and the history keeps the manifest."
        ),
    )
    mass_sweep.set_defaults(handler=curate_mass_sweep)
    keeping_verbs(
        mass_sweep.add_subparsers(dest="what", required=True),
        noun="log",
        force="overwrite a live log that holds MORE rows than the manifest records",
    )

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
            "this. Exits non-zero when the store does not cover the admitted population."
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

    pass_store = steps.add_parser(
        "gallery-store",
        help="a gallery pass's attempt store: record it, check it, restore it",
        description=(
            "A pass makes locations x heads x draws attempts per slot and each one is a pool "
            "row carrying its whole join — 1,120 rows at n=50 and ten times that at n=500, "
            "at about 3.8 KB a row. They live under the regenerable tree rather than in the "
            "history, so they get what the supply sidecar and the embedding store get: a "
            "copy on the archive tier, a tracked manifest carrying the row count, the bytes, "
            "the sha256 and the population the attempts were made over, and a restore that "
            "counts before it believes."
        ),
    )
    pass_store.set_defaults(handler=curate_gallery_store)
    # Its own three rather than [`keeping_verbs`]: every verb here names a pass,
    # because unlike the five stores that share that helper this one keeps a
    # store per gallery pass rather than a single file.
    pass_verbs = pass_store.add_subparsers(dest="what", required=True)
    for named, purpose in (
        ("check", "check the live store against the manifest"),
        ("save", "save a fresh copy and manifest"),
        ("restore", "restore the archived copy, counted before it is believed"),
    ):
        keeping_a_pass = pass_verbs.add_parser(named, help=purpose)
        keeping_a_pass.add_argument(
            "--pass",
            dest="pass_id",
            required=True,
            help="which pass's store, by id",
        )
        if named == "restore":
            keeping_a_pass.add_argument(
                "--force",
                action="store_true",
                help="overwrite a live store that holds MORE rows than the manifest records. "
                "Those rows are attempts nobody has saved yet",
            )

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
            "leg that HAS merged is decided by the ledger alone; one that has not is "
            "skipped and listed for a person, never swept. It is a dry run unless "
            "`--apply` says otherwise."
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
        f"shipped rank key (default: {candidate_ledger_module.RETAIN_PER_PAIR}). Four "
        "protections keep a row outside the rank whatever it says, and a picture is kept "
        "if and only if its row is",
    )
    pruning.add_argument(
        "--dry-run",
        action="store_true",
        help="read, decide, and touch nothing. THE dry run — there is no second command "
        "that says what a prune would do",
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

    ledger_verbs.add_parser("save", help="save a fresh copy and manifests")

    rejudging = ledger_verbs.add_parser(
        "score", help="read every picture through the judge shipped now"
    )
    rejudging.add_argument(
        "--limit",
        type=int,
        help="stop after this many pictures. What a pilot prices the whole leg off",
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
        help="let the pass reach only this many strongest locations, ranked by their best "
        "candidate. Unset is the whole ledger",
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
    themed.add_argument(
        "--themed",
        metavar="CELL",
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
    themed.add_argument(
        "--themed-cap",
        type=int,
        metavar="SEATS",
        help="the palette-group cap a THEMED pass runs under, overriding the computed "
        f"one. Unset is ceiling.themed_group_cap: ceil({ceiling_module.THEMED_CAP_SHARE} x "
        "n / P), twice the even share across the P palette groups that can field the "
        f"theme, where P counts the groups fielding {ceiling_module.THEMED_CAP_PLACES} or "
        "more distinct PLACES in the themed pool. The main gallery's cap is a share of `n` "
        "alone and was measured as the BINDING rule over a themed pool at every shipping "
        "size, which is why a themed pass gets its own. `--group-cap` still names the "
        "main gallery's rule and a themed pass ignores it. Ignored without `--themed`",
    )
    themed.add_argument(
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
    solve_flags_a_record_keeps(demands=demands, search=search)
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
        "stamp, so successive records at the same N coexist)",
    )
    recording.add_argument(
        "--n",
        type=int,
        default=None,
        help=f"how many wallpapers to seat (default {tentative_module.RECORDED_SEATS}, the "
        f"size a record is kept at, where a `run` reads a leg at "
        f"{candidate_ledger_module.FIRST_SOLVE})",
    )
    solve_flags_a_record_keeps(demands=recording, search=recording)

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

    flatness_step = steps.add_parser(
        "flatness",
        help="the dead-space column, swept over the pool into a sidecar beside the scores",
        description=(
            "Tile each picture into 16-pixel cells, fit a plane to every cell, and count "
            "the cells with nothing left over — a candidate that is mostly dead space is a "
            "candidate with less in it. The plane term is what makes it more than a "
            "variance screen: a smooth ramp across a cell is not detail. It ranks "
            "BACKWARDS on its own (AUC 0.407 smooth / 0.480 strange) and earns its place "
            "on top of the judge on both kinds, which is why it is a column of the fitted "
            "rank key and never a bar. One row per recipe key in a sidecar beside "
            "`scores.jsonl`; NO LEDGER ROW IS EDITED. About 7.5 ms a picture, incremental "
            "— a store already swept costs one read and no decodes."
        ),
    )
    # The VERB IS OPTIONAL here and `sweep` is what a bare `curate flatness`
    # means, so the group carries the sweep's flags as well as `sweep` does:
    # `curate flatness --workers 2` and `curate flatness sweep --workers 2` are
    # both lines somebody types and both have to keep working. The verb's copy
    # takes `default=argparse.SUPPRESS`, which is load-bearing rather than tidy —
    # argparse parses a subparser into its own namespace and then copies the
    # WHOLE of it over the parent's, so a plain re-declaration would put the
    # default back over the value the group had already taken. `--force` is
    # `restore`'s alone and is on no other verb and not on the group.
    flatness_verbs = flatness_step.add_subparsers(dest="what", required=False)
    flatness_step.set_defaults(handler=curate_flatness, what="sweep")
    flatness_step.add_argument(
        "--workers",
        type=int,
        default=flatness_module.WORKERS,
        metavar="N",
        help=SWEEP_WORKERS.format(count=flatness_module.WORKERS),
    )
    flatness_step.add_argument("--all", action="store_true", help=SWEEP_EVERY_ROW)
    flatness_step.add_argument(
        "--recompute",
        action="store_true",
        help="re-read every candidate rather than only the ones with no row yet",
    )

    sweeping_flatness = flatness_verbs.add_parser(
        "sweep", help="read every pool candidate the sidecar does not hold"
    )
    sweeping_flatness.add_argument(
        "--workers",
        type=int,
        default=argparse.SUPPRESS,
        metavar="N",
        help=SWEEP_WORKERS.format(count=flatness_module.WORKERS),
    )
    sweeping_flatness.add_argument(
        "--all", action="store_true", default=argparse.SUPPRESS, help=SWEEP_EVERY_ROW
    )
    sweeping_flatness.add_argument(
        "--recompute",
        action="store_true",
        default=argparse.SUPPRESS,
        help="re-read every candidate rather than only the ones with no row yet",
    )
    covering_flatness = flatness_verbs.add_parser(
        "coverage", help="report how much of the pool the sidecar can answer for"
    )
    covering_flatness.add_argument(
        "--all", action="store_true", default=argparse.SUPPRESS, help=SWEEP_EVERY_ROW
    )
    keeping_verbs(
        flatness_verbs,
        noun="sidecar",
        force="overwrite a live sidecar holding MORE rows than the manifest",
        order=("save", "check", "restore"),
    )

    signatures_step = steps.add_parser(
        "signatures",
        help="the diversity rule's bound signature, swept over the clearing pool into a "
        "sidecar beside the scores",
        description=(
            "The gallery leg screens a candidate against the seated pictures with a sound "
            "lower bound read off a REDUCED pixel-cloud signature — four blocks of "
            "quantiles by 256 directions, 4 KiB against the metric's 128. Making "
            "one costs a JPEG decode, about 16.8 ms, and it was ~100% of the leg before "
            "the prunes. It is the same number every time, so this sweeps it once into a "
            "sidecar and every later solve reads it instead of deriving it. One row per "
            "recipe key; NO LEDGER ROW IS EDITED. Incremental, and a row is stale when the "
            "recipe's picture is not the picture the row was read from — never on a clock."
        ),
    )
    #: `--recompute` here and on `curate flatness` are two different sentences,
    #: which is why they are not one constant: this one is about the reduction.
    recomputing = (
        "re-read every candidate rather than only the ones the sidecar cannot answer for. "
        "What to run after changing anything about the reduction itself"
    )
    # The verb is optional and the group carries the sweep's flags, for the
    # reason `curate flatness` above gives at length.
    signature_verbs = signatures_step.add_subparsers(dest="what", required=False)
    signatures_step.set_defaults(handler=curate_signatures, what="sweep")
    signatures_step.add_argument(
        "--workers",
        type=int,
        default=signatures_module.WORKERS,
        metavar="N",
        help=SWEEP_WORKERS.format(count=signatures_module.WORKERS),
    )
    signatures_step.add_argument("--recompute", action="store_true", help=recomputing)

    sweeping_signatures = signature_verbs.add_parser(
        "sweep", help="read every clearing candidate the sidecar cannot answer for"
    )
    sweeping_signatures.add_argument(
        "--workers",
        type=int,
        default=argparse.SUPPRESS,
        metavar="N",
        help=SWEEP_WORKERS.format(count=signatures_module.WORKERS),
    )
    sweeping_signatures.add_argument(
        "--recompute", action="store_true", default=argparse.SUPPRESS, help=recomputing
    )
    signature_verbs.add_parser(
        "coverage", help="report how much of the pool the sidecar can answer for"
    )
    keeping_verbs(
        signature_verbs,
        noun="sidecar",
        force="overwrite a live sidecar holding MORE rows than the manifest",
        order=("save", "check", "restore"),
    )

    rank_key_step = steps.add_parser(
        "rank-key",
        help="the fitted sort key a seating may rank on instead of the judge alone",
        description=(
            "Fit the form `rank_key_fit` selected — the location head's P(>=4), the render "
            "judge at both cutpoints, the calibration stratum and the flatness column — "
            "over every human label row that joins the candidate ledger, with SHARED "
            "weights over both stores because per-kind bought +0.000 [-.011,+.012] on "
            "smooth. Five folds at 20% grouped on lineage and assigned ONCE over the "
            "pooled corpus, since 96 groups span both stores. It ships two tracked files: "
            "the coefficients with their standardization constants, and EVERY LABEL ROW "
            "THE FIT CONSUMED — the store, the batch, the file and line, the tier, the "
            "lineage group and the fold. A selection rule fit on human labels is a "
            "category no eligibility guard covers, so the record is the guard."
        ),
    )
    # Optional verb, and `fit` is the one that does the work. Neither takes a
    # flag, so there is nothing to carry on the group but the default itself.
    rank_key_verbs = rank_key_step.add_subparsers(dest="what", required=False)
    rank_key_step.set_defaults(handler=curate_rank_key, what="fit")
    rank_key_verbs.add_parser("fit", help="re-fit the key and rewrite both tracked files")
    rank_key_verbs.add_parser("show", help="print the shipped key")

    distinct_step = steps.add_parser(
        "distinct",
        help="the neutral pre-selection read: which places are visibly different places",
        description=(
            "The instrument the pre-selection radius was set off. The join FIRST — how many of "
            "the pool's locations have a neutral descriptor and how many do not, because "
            "a lossy pre-filter is a finding rather than a detail to work around — then "
            "the nearest-neighbour distribution, then the near pairs at each candidate "
            "radius as a sheet. NO RADIUS IS CHOSEN: the sheet is the instrument and the "
            "choice is a person's. The premise the whole decoupling rests on — that far "
            "in the neutral descriptor implies far in the coloured pixels — is MEASURED "
            "against the pixel-cloud metric over a stratified sample, because a "
            "correlated proxy is not a prune and this project has shipped one that was. It "
            "does not hold, which is why there are TWO rules: this radius asks whether two "
            "places are the same place, and the twin test in `seat` asks whether two "
            "pictures are one wallpaper."
        ),
    )
    distinct_step.add_argument(
        "--name",
        default="latest",
        help="what to call this read's output directory (default `latest`)",
    )
    distinct_step.add_argument(
        "--out",
        metavar="PATH",
        help="where the near-pair sheet goes (default beside the record)",
    )
    distinct_step.add_argument(
        "--premise-pairs",
        type=int,
        default=distinct_module.PREMISE_PAIRS,
        metavar="PAIRS",
        help="how many pairs the premise check measures "
        f"(default {distinct_module.PREMISE_PAIRS}). Two pixel-cloud signatures a pair at "
        "about a tenth of a second each, cached per picture",
    )
    distinct_step.add_argument(
        "--no-premise",
        action="store_true",
        help="the join, the distribution and the sheet, and measure no pixel cloud",
    )
    distinct_step.add_argument(
        "--no-sweep",
        action="store_true",
        help="the scatter but not the exact twin sweep. The sweep is one signature per "
        "picture plus the pairs the sound bound cannot settle, which is minutes over a "
        "pool of a thousand places — and it is the half that decides the design",
    )
    distinct_step.set_defaults(handler=curate_distinct)

    hunting = steps.add_parser(
        "hunt",
        help="render candidates into the ledger's two shortages: fresh places, and one colour",
        description=(
            "The proposal side of propose-then-solve, aimed rather than opportunistic. The "
            "UNCONDITIONAL leg buys breadth — locations from the admitted pool that carry no "
            "ledger recipe at all, a shallow spread each, the palette stratified across the "
            "codebook's cells instead of picked by the palette head, whose argmax is what "
            "left the ledger at a quarter as much green as red. The CONDITIONED leg buys one "
            "colour: the maps come from the tracked carrier table for the cell a solve came "
            "up short in and the palette head is never asked, because it is offered those "
            "carriers as often as anything else and takes them at 0.17x the base rate. "
            "Everything renders at the frame the pool-wide refinement scan chose, looked up "
            "rather than recomputed. Rows land as candidates land, so a killed hunt is a "
            "usable partial; `merge` is what folds them into the ledger."
        ),
    )
    hunting.set_defaults(handler=curate_hunt)
    hunt_verbs = hunting.add_subparsers(dest="what", required=True)
    planning_hunt = hunt_verbs.add_parser("plan", help="print the plan and render nothing")
    running_hunt = hunt_verbs.add_parser("run", help="run the hunt")
    merging_hunt = hunt_verbs.add_parser("merge", help="merge a hunt's rows into the ledger")
    hunt_sheet = hunt_verbs.add_parser("sheet", help="redraw a hunt's contact sheet")
    hunt_frames = hunt_verbs.add_parser("frames", help="rebuild the frame index off the scan")
    # --name first on every one of the five, and REQUIRED on every one of the
    # five: it was required by the group before the split, so `curate hunt
    # frames --name h1` is a line that works and a `frames` that had dropped the
    # flag would refuse it. `frames` does not read it, and says so.
    for a_hunt in (planning_hunt, running_hunt, merging_hunt, hunt_sheet, hunt_frames):
        a_hunt.add_argument(
            "--name",
            required=True,
            help="what to call this hunt. Its rows, its pictures and its record live under "
            "it, and `merge` names it again"
            + ("; `frames` names one and reads nothing off it" if a_hunt is hunt_frames else ""),
        )
    hunt_draw_flags(planning_hunt)
    running_hunt.add_argument(
        "--budget",
        type=float,
        default=hunt_module.BUDGET_SECONDS,
        metavar="SECONDS",
        help=f"how long the hunt may spend RENDERING (default {int(hunt_module.BUDGET_SECONDS)}). "
        "Not the wall clock: the frame lookup, the plan and the merge sit outside it. "
        "Enforced at the candidate boundary, so nothing is started that cannot finish",
    )
    hunt_draw_flags(running_hunt)
    device_flag(running_hunt)

    mine_step = steps.add_parser(
        "mine",
        help="price a PRIMED location three ways, and profile what one candidate costs",
        description=(
            "A measurement pass over the unchanged render loop. A location is PRIMED when "
            "it holds at least one candidate the render judge scores at or above the bar, "
            "derived at read time off the score sidecar and stored in no row. Three arms "
            "are woven together so a budget that runs out truncates all of them alike: "
            "DEEPEN adds palettes at a place that already showed something, holding the "
            "frame and the mode, and reports what the k-th palette is worth; "
            "BREADTH-RANKED opens never-opened admitted locations top-down on the location "
            "head's rank WITHIN partition, never pooled across one; BREADTH-FLAT opens "
            "them with no quality conditioning, matched to the ranked arm's per-partition "
            "counts, and is the base rate that says whether the rank bought anything. "
            "Candidates land as candidates land and `merge` folds them into the ledger, "
            "and a stopwatch on each stage lands beside them."
        ),
    )
    mine_step.set_defaults(handler=curate_mine)
    mine_verbs = mine_step.add_subparsers(dest="what", required=True)
    planning_mine = mine_verbs.add_parser("plan", help="print the plan and render nothing")
    running_mine = mine_verbs.add_parser("run", help="run the mine")
    merging_mine = mine_verbs.add_parser("merge", help="merge its rows into the ledger")
    benching = mine_verbs.add_parser(
        "bench", help="price the loop against the cheaper shapes it could have had"
    )
    mine_sheet = mine_verbs.add_parser("sheet", help="redraw the autopsy sheet")
    # --name first and required on all five, as it was on the group before the
    # split; `merge`, `bench` and `sheet` read it and `bench` writes beside it.
    for a_mine in (planning_mine, running_mine, merging_mine, benching, mine_sheet):
        a_mine.add_argument(
            "--name",
            required=True,
            help="what to call this mine. Its rows, its pictures, its profile and its record "
            "live under it, and `merge` names it again",
        )
    mine_draw_flags(planning_mine)
    mine_draw_flags(running_mine)
    device_flag(running_mine)
    benching.add_argument(
        "--seed",
        type=int,
        default=mine_module.DEFAULT_SEED,
        help=MINE_SEED.format(seed=mine_module.DEFAULT_SEED),
    )

    depth_step = steps.add_parser(
        "depth",
        help="buy width at one place, and measure what it buys against the head's rank",
        description=(
            "Forty candidates a location on the modes a dumped field can serve, over three "
            "draws woven together so a budget that runs out truncates all of them alike. "
            "NEAR-BAND deepens a place whose best FIELD candidate already sits between the "
            "two bars, holding the incumbent's mode so only the palette moves. "
            "RANKED-BANDS opens never-opened locations across the WHOLE of the location "
            "head's rank range inside each partition, in equal-count bands, which is the "
            "curve the earlier passes are two points on. FLAT opens them with no quality "
            "conditioning, matched on partition. Every candidate is written to the "
            "sequence file in the order it was made, so a cumulative curve at any width "
            "below the one reached is arithmetic rather than another run. Field modes "
            "only: a composite at this width is about 175s a location."
        ),
    )
    depth_step.set_defaults(handler=curate_depth)
    depth_verbs = depth_step.add_subparsers(dest="what", required=True)
    planning_depth = depth_verbs.add_parser("plan", help="print the plan and render nothing")
    depth_leg_flags(planning_depth, device=False)
    running_depth = depth_verbs.add_parser("run", help="run the leg")
    depth_leg_flags(running_depth, device=True)
    # `merge` and `sheet` name a leg and read nothing else off the plan: --name
    # was required by the group before the split, so both keep taking it.
    for a_leg, purpose in (
        ("merge", "merge its rows into the ledger"),
        ("sheet", "redraw the autopsy sheet"),
    ):
        finished = depth_verbs.add_parser(a_leg, help=purpose)
        finished.add_argument(
            "--name",
            required=True,
            help="what to call this run. Its rows, its pictures, its sequence and its record "
            "live under it, and `merge` names it again",
        )

    shrinkage_step = steps.add_parser(
        "shrinkage",
        help="re-read a candidate set's winner at label geometry, and price the winner's curse",
        description=(
            "A location is PRIMED on the MAXIMUM of k noisy readings, so the prime rate "
            "captures noise as well as quality and does so more the wider the set is. The "
            "calibration sheet measured the noise: across one doubling of geometry P(>=4) "
            "moves by mean -0.009 with sd 0.087. This re-renders the candidate that was "
            "the running best of the first k, at each of a few checkpoints, at label "
            "geometry (1280x720 ss2) through its own recipe, and scores it on the same "
            "shipped artifact. It writes BOTH curves - the raw one every prime count so "
            "far is, and the calibrated one - and never replaces one with the other."
        ),
    )
    shrinkage_step.add_argument(
        "--name",
        required=True,
        help="the depth run to re-read. Its sequence is the input and this read's own "
        "subtree is named for it",
    )
    shrinkage_step.add_argument(
        "--per-arm",
        type=int,
        default=shrinkage_module.PER_ARM,
        metavar="COUNT",
        help=f"how many locations each draw contributes (default {shrinkage_module.PER_ARM}). "
        f"A correction term, not a second experiment",
    )
    shrinkage_step.add_argument(
        "--workers",
        type=int,
        default=shrinkage_module.WORKERS,
        metavar="COUNT",
        help=f"render workers (default {shrinkage_module.WORKERS}). The judge stays in this "
        f"process and runs once over everything they made",
    )
    shrinkage_step.add_argument("--seed", type=int, default=0, help="the sample's seed")
    device_flag(shrinkage_step)
    shrinkage_step.set_defaults(handler=curate_shrinkage)

    remode_step = steps.add_parser(
        "remode",
        help="re-render a retired mode's clearing rows in a mode the project still buys",
        description=(
            "A mode_policy weight of 0 leaves a mode's material standing and takes every "
            "row of it out of solve.pool, so a place whose only clearing candidate was in "
            "that mode stops being a place a gallery can reach - 574 of them when "
            "exp_smoothing was ruled niche. This renders the SAME recipe again with the "
            "mode moved: same frame, same cap, same map, same palette knobs, and the "
            "autolevel stamp re-derived for the target mode's kind. Nothing is re-labelled "
            "and no source row is touched - a recipe key is a digest of the engine spec, so "
            "a row claiming a mode it was not rendered in would name a picture nobody made. "
            "Each twin is judged on its own render by the shipped judge and a twin below "
            "the bar is a row that merged and does not clear. Three counts come out and the "
            "row count is the least interesting: what the retention rule bounds is places "
            "that regain a clearing row, because every twin lands on (location, target "
            "mode) where only three survive ranked within the pair."
        ),
    )
    remode_step.set_defaults(handler=curate_remode)
    remode_verbs = remode_step.add_subparsers(dest="what", required=True)
    planning_remode = remode_verbs.add_parser(
        "plan", help="read the population and price it, rendering nothing"
    )
    running_remode = remode_verbs.add_parser("run", help="render the twins")
    merging_remode = remode_verbs.add_parser("merge", help="merge its rows into the ledger")
    reading_remode = remode_verbs.add_parser("read", help="a finished leg's readout")
    # --name first and required on all four, the shape every leg group here has.
    for a_leg in (planning_remode, running_remode, merging_remode, reading_remode):
        a_leg.add_argument(
            "--name",
            required=True,
            help="what to call this leg. Its rows, its pictures, its fields and its record "
            "live under it, and `merge` names it again",
        )
    # The mode pair is on `plan` and `run` and on neither of the other two: a
    # merge reads the rows the run already wrote, and a read reads its record, so
    # a mode named there would be a flag that could disagree with the leg.
    for a_render in (planning_remode, running_remode):
        a_render.add_argument(
            "--from-mode",
            required=True,
            metavar="MODE",
            help="the mode whose clearing rows get rendered again. Usually one "
            "mode_policy has just weighted 0, which is what strands them",
        )
        a_render.add_argument(
            "--to-mode",
            required=True,
            metavar="MODE",
            help="the mode to render them in. Refused unless mode_policy accepts it - a "
            "twin in a second weight-0 mode would be stranded exactly as its source is",
        )
    running_remode.add_argument(
        "--budget",
        type=float,
        default=remode_module.BUDGET_SECONDS,
        metavar="SECONDS",
        help=f"wall seconds of RENDERING (default {remode_module.BUDGET_SECONDS:.0f}). The "
        f"population read sits outside it, and what it truncates is whole locations",
    )
    running_remode.add_argument(
        "--workers",
        type=int,
        default=remode_module.WORKERS,
        metavar="COUNT",
        help=f"render workers (default {remode_module.WORKERS}, this machine's pool). A plan "
        f"with fewer location blocks than workers runs on one worker a block",
    )
    device_flag(running_remode)

    retention_step = steps.add_parser(
        "retention",
        help="the three aggregates that survive what the retention rule drops",
        description=(
            "At ten million attempts the ledger's rows are about 5 GB and the pictures "
            "they name are about 600 GB, so storage has to scale with the locations "
            "explored and not with the attempts made. The rule keeps the top "
            f"{candidate_ledger_module.RETAIN_PER_PAIR} per (location, mode) ranked WITHIN "
            "the pair by the shipped rank key, plus five protections, and a picture is "
            "kept if and only if its row is. This builds the three counts that dropping "
            "the rest must not destroy: the (location, mode) cursor into the palette draw, "
            "the (colormap, mode) success table, and what each place has been made to look "
            "like. What a prune WOULD do is `curate candidate-ledger prune --dry-run`, "
            "which is the only dry run there is."
        ),
    )
    retention_step.add_argument(
        "--out", metavar="PATH", help="write the JSON here as well as printing it"
    )
    retention_step.set_defaults(handler=curate_retention)

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

    expressing = steps.add_parser(
        "expressed",
        help="how much of the codebook the finished collection expresses, and what a "
        "per-swatch floor could arithmetically ask for",
        description=(
            "COVERAGE(s) is the fraction of finished full-size wallpapers in which at least "
            "a tenth of the pixels are assigned to swatch s, read off the shipped render at "
            "its own resolution rather than off the candidate that stands behind it. Summed "
            "over the fifty-two, COVERAGE is the mean number of swatches a wallpaper "
            "expresses — which is what decides whether a uniform per-swatch floor can exist "
            "at all, since a floor of f across k swatches asks the average picture for f*k "
            "expressed colours. Measurement only: no floor is set and nothing is gated."
        ),
    )
    expressing.add_argument(
        "--step",
        dest="step_of_expressed",
        choices=["all", "census", "read"],
        default="all",
        help="run one step only: census every finished wallpaper, or read the tables off a "
        "census already taken (default: both)",
    )
    expressing.set_defaults(handler=curate_expressed)
