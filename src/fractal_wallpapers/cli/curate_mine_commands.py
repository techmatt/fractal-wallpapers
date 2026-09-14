"""`curate`'s legs: the fourteen verbs that drive the render pool.

A leg makes pictures. That is what these have in common and why they are one
module: each of them plans a batch, renders it three-wide at below-normal
priority through [`engine.run`], and merges what it made into the pool — so each
carries the same `--workers`, `--seed` and `--limit` shape, and the shared draw
helpers ([`depth_leg_flags`], [`mine_draw_flags`], [`hunt_draw_flags`],
[`SWEEP_WORKERS`], [`SWEEP_EVERY_ROW`]) are the reason the shape stays one shape.

`hunt` and `mine` find candidates; `depth`, `rotate`, `remode`, `repetition`,
`repeat-ab` and `shrinkage` ask an axis nothing has asked yet; `flatness`,
`signatures`, `rank-key`, `distinct` and `retention` sweep the pool and report.
`phase-response` is the one that touches neither — it renders a stated panel to
measure what an axis *does*, holds no pool and merges nothing.
[`curation/LEGS.md`] is the reference for what each one costs.

Cut out of `curate_commands` on 2026-09-12 with four sibling families; that
module's docstring carries the reversal and what it cost.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import NamedTuple

from fractal_wallpapers.cli.common import (
    device_flag,
    display_path,
    keeping_verbs,
    resolve_output,
)
from fractal_wallpapers.curation import repetition as repetition_module


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
    from fractal_wallpapers.paths import Tiers, rehome

    # `solve.pool` and not `headroom.population` — see `curate solve record`.
    candidates, _ = solve.pool()
    kept = headroom.clearing(candidates)
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


def curate_phase_response(args):
    """Measure what `Palette.phase` moves, mode by mode, off the pixels."""
    from fractal_wallpapers import engine
    from fractal_wallpapers.curation import phase_response

    try:
        if args.what == "read":
            rows, record = phase_response.read(args.name)
        else:
            modes = args.modes or engine.production_modes()
            phases = tuple(args.phases) if args.phases else phase_response.PHASES
            panel = phase_response.places(args.places, seed=args.seed)
            library = phase_response.maps(args.maps, seed=args.seed)
            print(f"panel   {', '.join(place['partition'] for place in panel)}")
            print(f"maps    {', '.join(library)}")
            print(f"phases  {', '.join(f'{phase:g}' for phase in phases)}")
            rows, report = phase_response.run(
                modes,
                panel,
                library,
                phase_response.pass_dir(args.name),
                phases=phases,
                workers=args.workers,
                budget=args.budget,
            )
            report["seed"] = args.seed
            record = phase_response.write(args.name, rows, report)
    except phase_response.PhaseResponseRefused as refusal:
        print(refusal)
        return 1

    summary = phase_response.summarise(rows)
    checked = phase_response.control(rows)
    print()
    # ASCII, and the delta is spelled out: this prints to a Windows console whose
    # default code page is cp1252, where a bare U+0394 is a UnicodeEncodeError and
    # not a mojibake — the whole command dies after the renders are paid for.
    print(f"{'mode':24} {'kind':10} {'mean dE':>9} {'p99':>8} {'moved':>7} {'map low/high':>17}")
    for entry in summary:
        print(
            f"{entry['mode']:24} {entry['mode_kind']:10} {entry['mean']:9.5f} "
            f"{entry['p99']:8.5f} {entry['moved']:7.3f} "
            f"{entry['map_low']:8.5f}/{entry['map_high']:8.5f}"
        )
    print()
    print(json.dumps({"control": checked, "split": phase_response.split(summary)}, indent=2))
    print(f"\nrecord {display_path(phase_response.record_path(record['name']))}")
    # The control is the harness and not a column: a trap that moved means the
    # palette pass reached a picture it cannot reach, and then no row above is a
    # reading of the axis. Reported and then refused, so nothing downstream takes
    # the table as sound.
    if not checked["passed"]:
        print(
            f"\nCONTROL FAILED: {checked['identical']} of {checked['cells']} direct-trap cells "
            f"came back byte-identical. The axis cannot reach a trap figure, so the harness is "
            f"wrong and the table above means nothing."
        )
        return 1
    return 0


def curate_rotate(args):
    """Price the passing set, rotate it, or put the decisions in the store."""
    from fractal_wallpapers.curation import rotation

    try:
        if args.what == "merge":
            print(json.dumps(rotation.merge(args.name, apply=not args.dry_run), indent=2))
            return 0
        if args.what == "read":
            record = rotation.read(args.name)
            print(json.dumps({**record.get("population", {}), **record["counts"]}, indent=2))
            return 0
        if args.what == "mine":
            from fractal_wallpapers.curation import depth as depth_module

            record = rotation.mine(
                args.name,
                seed=args.seed,
                rate=args.rate,
                budget=args.budget,
                width=args.width,
                rotations=args.rotations,
                roster=args.modes,
                shares=json.loads(args.shares) if args.shares else None,
                plan_budget=args.plan_budget,
                from_block=args.from_block,
                workers=args.workers,
                device=args.device,
                chunk=args.chunk,
                # The draw-shaping flags, read the way `curate depth run` reads
                # them: a manifest through `depth.read_places`, the weights as
                # JSON, and `None` left as `None` so `build_plan` keeps its own
                # defaults rather than being handed an empty narrowing.
                cell=args.cell,
                bands=args.bands,
                top_bands=args.top_bands,
                band_weights=json.loads(args.band_weights) if args.band_weights else None,
                partition_weights=(
                    json.loads(args.partition_weights) if args.partition_weights else None
                ),
                draw_maps=depth_module.read_maps(args.draw_maps) if args.draw_maps else None,
                draw_cells=args.draw_cells,
                draw_cutoff=args.draw_cutoff,
                floor_modes=args.floor_modes,
                floor_untried=args.floor_untried,
                floor_places=(
                    depth_module.read_places(args.floor_places) if args.floor_places else None
                ),
                near_named=(
                    depth_module.read_places(args.near_places) if args.near_places else None
                ),
                floor_seats=args.floor_seats,
                floor_width=args.floor_width,
            )
            # `resume_from_block` is top-level on the record and is the one figure
            # the next leg has to have, so it is printed with the counts rather
            # than left to a reader of the file.
            print(
                json.dumps(
                    {
                        **record["counts"],
                        "resume_from_block": record["resume_from_block"],
                        **record["budget"],
                    },
                    indent=2,
                )
            )
            print(f"\nrecord {display_path(rotation.record_path(args.name))}")
            return 0
        if args.what == "plan":
            # The plan step renders nothing and holds the pool, which makes it the
            # honest place to read a count before spending hours of engine on it.
            # It resolves no recipe - that needs the group table and the band, and
            # is `run`'s first act - so `rotations` here is what the draw intends
            # rather than what survives the dedupe.
            world = rotation.population(args.bar, owed=args.owed)
            _groups, shape = rotation.plan_of(
                world["sources"], args.seed, world["known"], args.rotations
            )
            print(
                json.dumps(
                    {
                        "ledger_rows": world["ledger_rows"],
                        "passing": world["passing"],
                        "rotatable": len(world["sources"]),
                        "owed_arm": bool(args.owed),
                        "refused": world["refused"],
                        "owed": rotation.owed(world["refused"]),
                        "protected": world["protected"],
                        "plan": shape,
                    },
                    indent=2,
                )
            )
            return 0
        record = rotation.run(
            args.name,
            bar=args.bar,
            seed=args.seed,
            tolerance=args.tolerance,
            rotations=args.rotations,
            budget=args.budget,
            workers=args.workers,
            device=args.device,
            chunk=args.chunk,
            groups=args.groups,
            take_owed=args.owed,
        )
    except rotation.RotationRefused as refusal:
        print(refusal)
        return 1
    print(json.dumps({**record["counts"], **record["budget"]}, indent=2))
    print(f"\nrecord {display_path(rotation.record_path(args.name))}")
    return 0


def curate_repetition(args) -> int:
    """Draw the matched repeat batch, render it, merge it, and cut its sheet plan."""
    from fractal_wallpapers.curation import hunt, repetition

    try:
        if args.what == "merge":
            print(json.dumps(repetition.merge(args.name), indent=2))
            return 0
        if args.what == "read":
            record = repetition.read(args.name)
            print(json.dumps({**record["draw"], **record["counts"]}, indent=2))
            return 0
        if args.what == "sheet":
            print(json.dumps(repetition.sheet_plan(args.name, device=args.device), indent=2))
            return 0
        if args.what == "plan":
            # Renders nothing and HOLDS THE POOL, which is what makes it the
            # honest place to read the draw's composition — and the oversampling
            # ratio — before any engine time is spent. It resolves every key, so
            # `repeats_already_in_ledger` here is exactly what the run will skip.
            world = repetition.population()
            # The plan resolves keys and renders nothing, so this maker never
            # dumps a field and never loads the judge. It is named at the leg's
            # own fields directory all the same — a maker pointed somewhere else
            # would be one whose cache a later `run` could not reuse.
            maker = hunt.Maker(
                args.name,
                device=args.device,
                log=lambda *_a: None,
                fields=repetition.fields_dir(args.name),
            )
            pairs, drawn = repetition.draw(
                world, tiles=args.tiles, seed=args.seed, share=args.folded_share
            )
            _units, shape = repetition.plan_of(maker, pairs, world["known"])
            print(
                json.dumps(
                    {
                        "population": {
                            "ledger_rows": world["ledger_rows"],
                            "controls": len(world["controls"]),
                            "refused": world["refused"],
                            "fine_readings": world["fine_readings"],
                        },
                        "draw": drawn,
                        "plan": {
                            key: value for key, value in shape.items() if key != "repeat_keys"
                        },
                    },
                    indent=2,
                )
            )
            return 0
        record = repetition.run(
            args.name,
            tiles=args.tiles,
            seed=args.seed,
            share=args.folded_share,
            budget=args.budget,
            workers=args.workers,
            device=args.device,
        )
    except repetition.RepetitionRefused as refusal:
        print(refusal)
        return 1
    print(json.dumps({**record["counts"], **record["budget"]}, indent=2))
    print(f"\nrecord {display_path(repetition.record_path(args.name))}")
    return 0


def curate_repeat_ab(args) -> int:
    """Draw the A/B repeat sitting: one composite tile a place, and nothing rendered."""
    from fractal_wallpapers.curation import repeat_ab

    try:
        if args.what == "read":
            record = repeat_ab.read(args.name)
            print(json.dumps({**record["draw"], **record["plan"]}, indent=2))
            return 0
        record = repeat_ab.run(args.name, units=args.units, seed=args.seed, bar=args.bar)
    except repeat_ab.RepeatAbRefused as refusal:
        print(refusal)
        return 1
    print(json.dumps({**record["population"], "draw": record["draw"]}, indent=2))
    print(f"\nplan {display_path(repeat_ab.plan_path(args.name))}")
    print(f"record {display_path(repeat_ab.record_path(args.name))}")
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


def _near_places(args: argparse.Namespace) -> int:
    """Cut the places manifest a near-band arm is handed, by the draw's own rule.

    **The manifest and the draw were two rules and they disagreed.** A manifest
    cut over the ledger — which is how every band arm to date has been cut, by a
    leg rig beside the checkout — names places `depth.near_places` will not stand
    on, and the arm then drops them in silence: `general_leg_0909`'s three bands
    were handed 328, 255 and 236 places and planned **160, 87 and 68**, stopping
    on an empty plan at 41%, 13% and 33% of their clock. The **same 168 places**
    cost all three — an unadmitted place is never drawn on, so its room never falls
    and the next cut names it again — and 166 of them have no supply row at all.
    [`depth.near_manifest`] applies the three tests the draw applies —
    a roster incumbent, the band, the admitted population — and counts the room at
    the pair the draw will actually render into.

    It costs one population read, which is what a leg pays anyway, and `--out`
    writes the file `--near-places` reads.
    """
    from fractal_wallpapers.curation import depth

    rows, census = depth.near_manifest(
        depth.population(),
        roster=args.modes,
        keep=args.keep,
        min_slots=args.min_slots,
    )
    print(json.dumps(census, indent=2))
    if not args.out:
        return 0
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"{display_path(out)}  {len(rows):,} place(s)")
    return 0


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
        if args.what == "near-places":
            return _near_places(args)
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
            "vary_palette": args.vary_palette,
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
    draw_shares.add_argument(
        "--vary-palette",
        action="store_true",
        help="draw each candidate a PHASE and a REPEAT as well as a map — `Palette.phase` "
        f"and `Palette.cycles`, the engine's own knobs for where the gradient's traversal "
        f"starts and how many times it is traversed. repeat "
        f"{', '.join(f'{count} at {share:g}' for count, share in depth_module.PALETTE_REPEATS)}; "
        f"phase exactly 0 at {depth_module.PALETTE_PHASE_HELD:g} and otherwise uniform over "
        "the turn. The direct traps have no field for a traversal to start in and are drawn "
        "bare; every varied shot gets its own phase-0 twin at the same place, mode and map, "
        "which is what makes `does adjusting an existing recipe pay` a matched question. "
        "**No map is derived, written or admitted** — the palette block is part of the "
        "recipe key, so a varied candidate is a new picture beside the plain one",
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
        "mode curation.mode_policy mines - accepted, less the modes ruled out of the mines "
        "and left in the gallery. Narrowing it is how a run at a small width "
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


def add_steps(steps) -> None:
    """The legs: the verbs that plan a batch, render it, and merge it back."""
    from fractal_wallpapers.curation import candidate_ledger as candidate_ledger_module
    from fractal_wallpapers.curation import depth as depth_module
    from fractal_wallpapers.curation import distinct as distinct_module
    from fractal_wallpapers.curation import flatness as flatness_module
    from fractal_wallpapers.curation import hunt as hunt_module
    from fractal_wallpapers.curation import mine as mine_module
    from fractal_wallpapers.curation import phase_response as phase_response_module
    from fractal_wallpapers.curation import remode as remode_module
    from fractal_wallpapers.curation import repeat_ab as repeat_ab_module
    from fractal_wallpapers.curation import rotation as rotation_module
    from fractal_wallpapers.curation import shrinkage as shrinkage_module
    from fractal_wallpapers.curation import signatures as signatures_module
    from fractal_wallpapers.curation import solve as solve_module

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
            "judge at both cutpoints and the flatness column — "
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
    near_manifest = depth_verbs.add_parser(
        "near-places",
        help="cut the places manifest a near-band arm is handed, by the draw's own rule",
        description=(
            "The near band is bounded by ROOM at the incumbent's pair and by what the draw "
            "will stand on, and a manifest cut any other way names places the leg drops in "
            "silence. This applies the three tests `depth.near_places` applies - the place "
            "holds a candidate in a roster mode, its best one is inside [SEATING_BAR, "
            "PRIMED_BAR), and it is in the ADMITTED embedded population - and then counts "
            "free slots at the pair the draw will render into, which is the incumbent's "
            "mode spelled bare. `general_leg_0909`'s three band arms were handed 328, 255 "
            "and 236 places by a cut that asked only the first, planned 160, 87 and 68, and "
            "stopped on an empty plan at 41%, 13% and 33% of their clock; the SAME 168 "
            "places cost all three, 166 of them locations the supply sidecar has never "
            "scored. Costs one population read. --out writes what --near-places reads."
        ),
    )
    near_manifest.add_argument(
        "--out",
        metavar="FILE",
        help="where to write the manifest, best-stocked first. Unsaid, the census is printed "
        "and nothing is written",
    )
    near_manifest.add_argument(
        "--modes",
        nargs="+",
        metavar="MODE",
        help="the incumbent modes the manifest may name. Unsaid, `depth.field_modes()` - the "
        "three shareable modes, NOT the twelve `mode_policy.mined()` holds. The near band "
        "holds its incumbent's mode, so a composite incumbent costs about 175s a location "
        "and measured the arm 6.2x dearer on the twelve-mode roster",
    )
    near_manifest.add_argument(
        "--min-slots",
        type=int,
        default=1,
        metavar="N",
        help="how much room a place must have at its incumbent pair to be named (default 1). "
        "A near-band pass over a pair already at the keep is ranked out as it lands",
    )
    near_manifest.add_argument(
        "--keep",
        type=int,
        default=None,
        metavar="N",
        help="price the room against another retention keep. Unsaid, the standing one",
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

    repeat_ab_step = steps.add_parser(
        "repeat-ab",
        help="the one repetition question still open: on a picture already good at 1x, is "
        "the repeat better? One composite tile a place, the 1x on the left",
        description=(
            "`curate repetition` closed repetition as a general draw — 121 matched pairs, "
            "mean within-pair delta -0.273 tiers, cycles 3 a rout at -0.634. What it could "
            "not answer is what repetition does to a picture that is ALREADY GOOD, because "
            "that page gated on nothing and only 4 of its 121 baselines cleared the fine "
            "bar at all. This draws that page. Every unit is a smooth-routed row above "
            "solve.DEFAULT_FINE_BAR at cycles 1 and phase 0, at the candidate regime, with "
            "its picture on disk and NO human verdict in either finished store — a page "
            "mixing judged rows with unjudged ones is the aug_sweep_A failure and cannot be "
            "repaired afterwards. One unit per location. The rung is cycles 2 and one rung "
            "only, which is a 2x traversal on a cyclic map and 4x on a folded one: the two "
            "arms the ckpt-121 labels did not reject. Phase is held at 0 on both halves. It "
            "RENDERS NOTHING and MERGES NOTHING — the variant is not a candidate, the "
            "verdict keys on the place, and the two halves are rendered once by the sheet. "
            "The verdicts land in the `repeat_ab` attribute store on a three-point "
            "COMPARATIVE scale that is not the 1..4 quality scale and never pools with one. "
            "It HOLDS THE POOL."
        ),
    )
    repeat_ab_step.set_defaults(handler=curate_repeat_ab)
    repeat_ab_verbs = repeat_ab_step.add_subparsers(dest="what", required=True)
    planning_repeat_ab = repeat_ab_verbs.add_parser(
        "plan",
        help="draw the sitting and write its sheet plan, rendering nothing",
        description=(
            "The whole leg: this command writes `plan.jsonl`, and `label build --head "
            "repeat_ab --from-plan <it>` is what renders the tiles. The plan states BOTH "
            "halves whole — the map, the baseline's palette pass and the variant's — and "
            "prefills every unit at the neutral class, because a page whose premise is that "
            "no head can read this axis must not carry a head's opinion into the box the "
            "labeler corrects."
        ),
    )
    reading_repeat_ab = repeat_ab_verbs.add_parser("read", help="a drawn sitting's readout")
    for a_verb in (planning_repeat_ab, reading_repeat_ab):
        a_verb.add_argument(
            "--name",
            required=True,
            help="what to call this sitting. Its plan and its records live under it, and "
            "the other verb names it again",
        )
    planning_repeat_ab.add_argument(
        "--units",
        type=int,
        default=repeat_ab_module.UNITS,
        help=f"composite tiles in the sitting (default {repeat_ab_module.UNITS}). A unit is "
        f"ONE tile carrying two renders, so this is also the number of places drawn and "
        f"twice this many renders",
    )
    planning_repeat_ab.add_argument(
        "--seed", type=int, required=True, help="the draw's seed, recorded with it"
    )
    planning_repeat_ab.add_argument(
        "--bar",
        type=float,
        default=None,
        help=f"the p_fine(>=4) the population is taken above (default "
        f"{solve_module.DEFAULT_FINE_BAR:g}, solve.DEFAULT_FINE_BAR). The selection is "
        f"CONDITIONAL on it and that is the leg: a rate measured here is a rate about "
        f"pictures already good at 1x and a ceiling on any rate about the pool",
    )

    repetition_step = steps.add_parser(
        "repetition",
        help="ask an eye what the heads have never been shown: every repeated traversal "
        "of a gradient beside its own unrepeated twin at the same place, mode and map",
        description=(
            "`Palette.cycles` is how many times a render walks its colormap across the "
            "field, and the pool has almost no opinion about it: 2,262 of 374,186 rows "
            "stand at anything but one and 44 of those are seated, so neither head was "
            "fitted on a population containing the axis and neither head's reading of it "
            "is evidence. This renders a labelling set instead. Every repeated tile sits "
            "beside its own unrepeated twin at the same place, mode, settings, map and "
            "frame, and the match is PROVED rather than promised — the control's own "
            "recipe key is re-derived through the same call that made it and checked "
            "against the store, and a control that does not reproduce is dropped. Phase "
            "is held at 0 on both sides: 1,713 of the store's repeat rows carry a "
            "rotation too, so the axis as the pool holds it is confounded with the one "
            "`curate rotate` just measured. Cyclic maps draw cycles 2 and 3; sequential "
            "maps are baked folded, so their one rung of 2 is FOUR passes of the base "
            "ramp and the card prints the traversal count rather than the cycles value. "
            "The direct traps are excluded — the axis is a byte-for-byte no-op there. It "
            "GATES ON NOTHING: both columns are recorded on every tile and neither "
            "selects one, because the repeats the current heads tolerate are exactly the "
            "wrong sample. Repeats are deliberately oversampled far above any rate "
            "production draws and the ratio is on the record. It HOLDS THE POOL."
        ),
    )
    repetition_step.set_defaults(handler=curate_repetition)
    repetition_verbs = repetition_step.add_subparsers(dest="what", required=True)
    planning_repetition = repetition_verbs.add_parser(
        "plan", help="draw the batch and census it, rendering nothing"
    )
    running_repetition = repetition_verbs.add_parser("run", help="draw, render, read")
    merging_repetition = repetition_verbs.add_parser(
        "merge",
        help="this batch's rows into the candidate pool, through THE door",
        description=(
            "`gallery-grade score-pool` must run afterwards or the merged repeats carry "
            "no p_fine, pool_scores.jsonl being a one-shot file — and p_fine is what the "
            "sheet is ordered in."
        ),
    )
    sheeting_repetition = repetition_verbs.add_parser(
        "sheet",
        help="both tiles of every pair as finished-render sheet plans, split by store",
        description=(
            "One plan per label store, because a mode routes to one of them and a batch's "
            "rows all belong to one. Every unit carries the fine head's reading of the "
            "CANDIDATE as `order_score` — which is what `label build --order-by plan` "
            "reads the page good->bad in — and a card naming whether the tile is the "
            "repeat or the control, the TRUE traversal count, and both columns. The "
            "prefill is left to the render judge's own decode: the fine head's tier is a "
            "gallery grade and this page's scale is not that one."
        ),
    )
    reading_repetition = repetition_verbs.add_parser("read", help="a finished batch's readout")
    # --name first and required on all five, the shape every leg group here has.
    for a_verb in (
        planning_repetition,
        running_repetition,
        merging_repetition,
        reading_repetition,
        sheeting_repetition,
    ):
        a_verb.add_argument(
            "--name",
            required=True,
            help="what to call this batch. Its rows, its pictures, its fields, its draw "
            "and its records live under it, and every other verb names it again",
        )
    # The draw's own knobs are on `plan` and `run` and on neither of the other
    # three: a draw is settled when it is made, and a merge or a sheet that could
    # be handed a different tile count would be one that could disagree with the
    # record it is reading.
    for a_verb in (planning_repetition, running_repetition):
        a_verb.add_argument(
            "--tiles",
            type=int,
            default=repetition_module.TILES,
            help=f"tiles in the sitting, CONTROLS INCLUDED (default "
            f"{repetition_module.TILES}), so half this many pairs",
        )
        a_verb.add_argument(
            "--seed", type=int, required=True, help="the draw's seed, recorded with it"
        )
        a_verb.add_argument(
            "--folded-share",
            type=float,
            default=repetition_module.FOLDED_SHARE,
            help=f"what share of the pairs the sequential arm gets (default "
            f"{repetition_module.FOLDED_SHARE:g}), against its 15.3%% of the library. A "
            f"deliberate over-share, not the pool's own proportion",
        )
    running_repetition.add_argument(
        "--budget",
        type=float,
        default=repetition_module.BUDGET_SECONDS,
        help=f"wall seconds of rendering (default {repetition_module.BUDGET_SECONDS:g})",
    )
    running_repetition.add_argument(
        "--workers",
        type=int,
        default=repetition_module.WORKERS,
        help=f"engines at once (default {repetition_module.WORKERS}, this machine's render pool)",
    )
    device_flag(planning_repetition)
    device_flag(running_repetition)
    # The sheet step RUNS the fine head over every tile, which is the half of
    # "score everything and gate on nothing" the pool's own column cannot do.
    device_flag(sheeting_repetition)

    phase_response_step = steps.add_parser(
        "phase-response",
        help="which production modes Palette.phase actually moves, and by how much, "
        "measured off the pixels rather than off what a head thinks of them",
        description=(
            "A varied mining draw spends phase on every mode that is not a direct trap, so "
            "on a mode the shift cannot move those renders buy nothing. This renders one "
            "recipe at several phases over a small stated panel and reads the pictures: "
            "the share of variants byte-identical to phase 0, and where they are not, the "
            "per-pixel Oklab difference as a mean, a p95, a p99 and the share of the frame "
            "past a just-noticeable 0.02. THE FOUR DIRECT TRAPS ARE THE HARNESS CONTROL - "
            "the axis cannot reach a trap figure, so they must come back byte-identical and "
            "the command FAILS if they do not, because then no other row is a reading of "
            "the axis. Levelling is OFF throughout: the autolevel operator derives its "
            "curve off the picture's own histogram, so a phase shift measured with the "
            "switch on would be phase plus re-levelling. Both a place and a map are varied "
            "- the interior is hard black and outside the map, so how much of a frame the "
            "axis can reach is a property of the place, and mirror is read off a map's kind "
            "so the two kinds are different ramps to traverse. This CHANGES NO DRAW: it "
            "writes rows and a record under artifacts/curation/phase_response/<name> and "
            "reads depth's shares without touching them."
        ),
    )
    phase_response_step.set_defaults(handler=curate_phase_response)
    phase_response_verbs = phase_response_step.add_subparsers(dest="what", required=True)
    running_phase_response = phase_response_verbs.add_parser(
        "run", help="render the grid, read the pixels, write the rows"
    )
    reading_phase_response = phase_response_verbs.add_parser(
        "read", help="a finished pass's table, control and split"
    )
    for a_phase_response in (running_phase_response, reading_phase_response):
        a_phase_response.add_argument(
            "--name", required=True, metavar="NAME", help="the pass's own directory"
        )
    running_phase_response.add_argument(
        "--places",
        type=int,
        default=phase_response_module.DEFAULT_PLACES,
        metavar="COUNT",
        help=f"places drawn from the shallow half of {phase_response_module.PANEL_RUN}, at most "
        f"one a partition (default {phase_response_module.DEFAULT_PLACES})",
    )
    running_phase_response.add_argument(
        "--maps",
        type=int,
        default=phase_response_module.DEFAULT_MAPS,
        metavar="COUNT",
        help=f"maps drawn off the drawable pool, half cyclic and half folded "
        f"(default {phase_response_module.DEFAULT_MAPS})",
    )
    running_phase_response.add_argument(
        "--phases",
        type=float,
        nargs="+",
        metavar="TURNS",
        help="the phases asked beside 0, in turns of the gradient (default "
        + " ".join(f"{phase:g}" for phase in phase_response_module.PHASES)
        + ")",
    )
    running_phase_response.add_argument(
        "--modes",
        nargs="+",
        metavar="MODE",
        help="the roster (default every production mode, which is what the table is of)",
    )
    running_phase_response.add_argument(
        "--seed",
        type=int,
        default=phase_response_module.DEFAULT_SEED,
        metavar="SEED",
        help=f"the seed for the place draw, the map draw and the pool collapse "
        f"(default {phase_response_module.DEFAULT_SEED})",
    )
    running_phase_response.add_argument(
        "--budget",
        type=float,
        metavar="SECONDS",
        help="wall seconds, checked at each phase boundary - a phase is finished or not "
        "started and NO MODE IS EVER CUT, because the table is a per-mode one",
    )
    running_phase_response.add_argument(
        "--workers",
        type=int,
        default=phase_response_module.DEFAULT_WORKERS,
        metavar="COUNT",
        help=f"render workers (default {phase_response_module.DEFAULT_WORKERS}, this "
        f"machine's pool)",
    )

    rotate_step = steps.add_parser(
        "rotate",
        help="ask the phases nothing ever asked: every passing recipe against five "
        "rotations of its own gradient, best of the six, and the row it replaces removed",
        description=(
            "Every recipe in the store was chosen at phase 0 with no alternative on the "
            "table, because Palette.phase was not a member a candidate leg could move "
            "until 2026-09-11 - so the pool is a selected-at-phase-0 population and every "
            "head fitted on it inherits that. This takes the residue back out. Per row six "
            "candidates: the picture it already has, plus five phases drawn uniformly over "
            "the turn with the repeat fixed at 1, scored through the fine head with "
            "p_coarse carried beside and gated on for neither. Best of the six wins; where "
            "it is a rotation clearing the tolerance the rotation is adopted and the row it "
            "replaces comes out of the store with its picture and its levelled colormap. "
            "Two kinds of row are never removed whatever the scores say - a row seated in "
            "ANY recorded gallery, and a row carrying ANY human label - and this honours "
            "the prune rule's other three protections beside them. The unit of work is the "
            "(location, mode) pair, because one dumped field serves every rotation under "
            "it: that is what makes six candidates a row cost about one and a quarter "
            "renders instead of six, and it is also what bounds the coverage to the modes "
            "the engine can dump a field for. The direct traps are excluded outright - the "
            "axis is a byte-for-byte no-op on a trap figure over a flat ground."
        ),
    )
    rotate_step.set_defaults(handler=curate_rotate)
    rotate_verbs = rotate_step.add_subparsers(dest="what", required=True)
    planning_rotate = rotate_verbs.add_parser(
        "plan", help="read the passing set and census it, rendering nothing"
    )
    running_rotate = rotate_verbs.add_parser("run", help="render, read, decide")
    merging_rotate = rotate_verbs.add_parser(
        "merge", help="adopt what won and remove what it replaced"
    )
    reading_rotate = rotate_verbs.add_parser("read", help="a finished pass's readout")
    mining_rotate = rotate_verbs.add_parser(
        "mine",
        help="a standard mining draw where every candidate is the best of five phases",
        description=(
            "What the store arm does to rows that exist, done to rows that do not. A "
            "standard depth draw over mode_policy.mined()'s roster, and the one thing that "
            "differs from a production leg is that each drawn shot becomes a phase-0 "
            "control plus four rotations, all five read through the fine head, and the best "
            "of them merged. The four that lose are recorded with their drawn phases and "
            "both columns and their pictures are freed: merging them would spend the "
            "retention rule's keep on near-duplicates, and recording only the winner would "
            "be the selected-at-one-phase bias again one level up, with nothing beside the "
            "argmax to correct a rate by. Direct traps are drawn bare - the axis is a "
            "no-op on them."
        ),
    )
    # **`mine` names its seams and the other four do not**, because `mine` is the
    # only one of the five past `test_cli.WALL` — it carries the whole draw-shaping
    # surface since 2026-09-13 and twenty-odd flags in one undivided block is a
    # reference nobody reads. The four group names are `curate depth run`'s own, in
    # its order, because they are the same flags doing the same jobs and a reader
    # moving between the two commands should not have to learn a second layout.
    # Every flag goes in a group once there is one: argparse prints a stray
    # optional above the named groups beside `-h`, which reads as belonging with
    # `--help`. `tests/test_cli.py` holds both halves of that.
    rotate_mine_clock = mining_rotate.add_argument_group("the leg and its clock")
    rotate_mine_draws = mining_rotate.add_argument_group("the draws and their shares")
    rotate_mine_width = mining_rotate.add_argument_group("how wide each draw goes")
    rotate_mine_where = mining_rotate.add_argument_group("the modes and places the draws work over")
    rotate_mine_maps = mining_rotate.add_argument_group("the palettes the draws may offer")

    # --name first and required on all five, the shape every leg group here has.
    for a_pass in (
        planning_rotate,
        running_rotate,
        merging_rotate,
        reading_rotate,
        rotate_mine_clock,
    ):
        a_pass.add_argument(
            "--name",
            required=True,
            help="what to call this pass. Its rows, its pictures, its fields, its "
            "decisions and its record live under it, and `merge` names it again",
        )
    # The population flags are on `plan` and `run` and on neither of the other two:
    # a merge reads the files the run already wrote and a read reads its record, so
    # a bar named there would be a flag that could disagree with the pass.
    for a_draw in (planning_rotate, running_rotate):
        a_draw.add_argument(
            "--bar",
            type=float,
            default=None,
            metavar="P_FINE",
            help=f"the fine bar the passing set is taken at (default the shipped "
            f"{solve_module.DEFAULT_FINE_BAR:g}). Rows under it are not this pass's "
            f"clock to spend",
        )
        a_draw.add_argument(
            "--seed",
            type=int,
            default=0,
            help="the draw's seed (default 0). Seeded per ROW off the row's own key, so a "
            "pass that stopped at the clock and a pass re-run over the same population "
            "draw the same phases for the same rows",
        )
        a_draw.add_argument(
            "--rotations",
            type=int,
            default=rotation_module.ROTATIONS,
            metavar="COUNT",
            help=f"phases drawn a row beside the one it has (default "
            f"{rotation_module.ROTATIONS}, so a row is six candidates)",
        )
        a_draw.add_argument(
            "--owed",
            action="store_true",
            help="take the rows a dumpable pass recorded as OWED — the composites and "
            "itinerary, whose coloring has no single scalar field to dump and recolour. "
            "They render at six iteration passes a row against a dumpable row's one, "
            "which is the whole of what the flag buys and the whole of what it costs. "
            "The direct traps stay refused: phase is a no-op on a trap figure",
        )
    running_rotate.add_argument(
        "--tolerance",
        type=float,
        default=rotation_module.TOLERANCE,
        metavar="FACTOR",
        help=f"a winning rotation is adopted where it reads at least this times the "
        f"incumbent's STORED fine column (default {rotation_module.TOLERANCE:g}). Relative "
        f"because p_fine spans orders of magnitude down the pool",
    )
    running_rotate.add_argument(
        "--budget",
        type=float,
        default=3600.0,
        metavar="SECONDS",
        help="wall seconds of RENDERING (default 3600). The ledger read and the guard "
        "resolution sit outside it, and what it truncates is whole chunks",
    )
    running_rotate.add_argument(
        "--chunk",
        type=int,
        default=rotation_module.CHUNK_GROUPS,
        metavar="GROUPS",
        help=f"(location, mode) groups rendered before the pass stops to read what it made "
        f"(default {rotation_module.CHUNK_GROUPS}). It is the interruption point: every "
        f"picture of a finished chunk is either adopted or unlinked",
    )
    running_rotate.add_argument(
        "--groups",
        type=int,
        default=None,
        metavar="COUNT",
        help="render only this many whole groups. For a smoke, and whole groups because a "
        "dump pays for itself only across the rotations that follow it",
    )
    running_rotate.add_argument(
        "--workers",
        type=int,
        default=rotation_module.WORKERS,
        metavar="COUNT",
        help=f"render workers (default {rotation_module.WORKERS}, this machine's pool)",
    )
    device_flag(running_rotate)
    rotate_mine_clock.add_argument(
        "--budget",
        type=float,
        default=3600.0,
        metavar="SECONDS",
        help="wall seconds of RENDERING (default 3600). The population read and the plan "
        "sit outside it, and what it truncates is whole chunks of location blocks",
    )
    rotate_mine_clock.add_argument(
        "--plan-budget",
        type=float,
        default=None,
        metavar="SECONDS",
        help="the budget the PLAN is sized off, where that is not the clock this leg has "
        "(default: --budget). A RESUMED leg says both — this rebuilds the first leg's "
        "block plan exactly, so its block N is this leg's block N, and --budget is only "
        "what is left to spend on it",
    )
    rotate_mine_clock.add_argument(
        "--from-block",
        type=int,
        default=0,
        metavar="INDEX",
        help="skip this many whole blocks of the plan, so a second leg continues the first "
        "rather than re-drawing it. Pass the first leg's `resume_from_block` and NEVER its "
        "`blocks_done`, which counts the blocks handed to the render pool and not the ones "
        "that came back. An index above what this plan has actually rendered is refused at "
        "start-up, because skipping a rendered block throws that work away with nothing in "
        "the store to say so: each shot's four losers are freed rather than merged, and a "
        "shot whose control never merged comes back as a best-of-FOUR under the same name",
    )
    rotate_mine_clock.add_argument(
        "--rate",
        type=float,
        default=rotation_module.MINE_RATE,
        metavar="SECONDS",
        help=f"engine seconds a SHOT the plan is sized off (default "
        f"{rotation_module.MINE_RATE:g}, a deliberate under-estimate). The surplus of a "
        f"plan is never started, so clock-bound is the correct way for a leg to end",
    )
    rotate_mine_width.add_argument(
        "--width",
        type=int,
        default=rotation_module.MINE_WIDTH,
        metavar="MAPS",
        help=f"maps a location (default {rotation_module.MINE_WIDTH}). Over twelve modes "
        f"that is one map a (location, mode), and a best-of-five merges one row - so a "
        f"pair takes one against a keep of {candidate_ledger_module.RETAIN_PER_PAIR}",
    )
    rotate_mine_width.add_argument(
        "--rotations",
        type=int,
        default=rotation_module.MINE_ROTATIONS,
        metavar="COUNT",
        help=f"phases drawn a shot beside its phase-0 control (default "
        f"{rotation_module.MINE_ROTATIONS}, so a shot is five candidates)",
    )
    rotate_mine_clock.add_argument(
        "--seed",
        type=int,
        default=0,
        help="the draw's seed (default 0), for the plan and for the phases both",
    )
    rotate_mine_where.add_argument(
        "--modes",
        nargs="+",
        default=None,
        metavar="MODE",
        help="the roster (default mode_policy.mined(), the policy's own). Named because "
        "`curate depth`'s default roster is the three SHAREABLE modes and not the twelve",
    )
    rotate_mine_draws.add_argument(
        "--shares",
        default=None,
        metavar="JSON",
        help=f"how the plan is split between the draws, spelled WHOLE - build_plan merges "
        f"what it is given over depth.SHARES, so naming one entry leaves the rest on their "
        f"defaults. Default {json.dumps(rotation_module.MINE_SHARES)}",
    )
    # **The draw-shaping flags `curate depth run` has, on this leg too.** This is a
    # standard depth draw whose shots are best-of-five, so a draw `depth run` can
    # aim, this has to be able to aim: without them the rotation search was
    # available only on the draws nobody narrows, and a leg wanting rotations at a
    # named population or an aimed cell had to give up one or the other. Spelled
    # out here rather than shared with `depth run`'s parser because the two help
    # texts differ in what they say about the shot: a width here is maps a
    # location and every one of them becomes five candidates.
    rotate_mine_where.add_argument(
        "--floor-places",
        metavar="FILE",
        help='a places MANIFEST - a JSONL of {"schema": 1, "key": ...} rows - naming '
        "the locations the mode-floor draw may stand on. It is ALSO the seating bar's "
        "set: a named place is drawn whatever its best candidate reads, which is how a "
        "place carrying a human q3/q4 verdict and an under-bar field score is reached. "
        "Needs a mode_floor share in --shares",
    )
    rotate_mine_where.add_argument(
        "--near-places",
        metavar="FILE",
        help="the same manifest shape, naming the locations the NEAR-BAND draw may "
        "stand on. Needs a near_band share in --shares",
    )
    rotate_mine_where.add_argument(
        "--floor-untried",
        nargs="*",
        default=None,
        metavar="MODE",
        help="narrow the mode-floor draw's population to opened locations with NO "
        "attempt in any of these modes. Given with no mode named, the dear half of "
        "the roster",
    )
    rotate_mine_where.add_argument(
        "--floor-modes",
        nargs="+",
        default=None,
        metavar="MODE",
        help="the modes the mode-floor draw serves. Unsaid, every mode the ledger says "
        "is short of --floor-seats seats today, worst first",
    )
    rotate_mine_where.add_argument(
        "--floor-seats",
        type=int,
        default=10,
        metavar="COUNT",
        help="how many distinct locations over the seating bar a mode needs before it "
        "is no longer short (default 10)",
    )
    rotate_mine_width.add_argument(
        "--floor-width",
        type=int,
        default=None,
        metavar="COUNT",
        help=f"palettes per (proven location, mode) in the mode-floor draw (default "
        f"{depth_module.FLOOR_WIDTH})",
    )
    rotate_mine_maps.add_argument(
        "--cell",
        nargs="+",
        default=None,
        metavar="CELL",
        help="the codebook cell or cells the CONDITIONED draw aims its palette ask at. "
        "Needs a conditioned share in --shares",
    )
    rotate_mine_maps.add_argument(
        "--draw-cells",
        nargs="+",
        default=None,
        metavar="CELL",
        help="codebook cells the palettes EVERY draw here offers must be expected to "
        "deliver. A draw filter and nothing else: it re-marks no map and writes nothing "
        "back to the tracked colour records",
    )
    rotate_mine_maps.add_argument(
        "--draw-cutoff",
        type=float,
        default=None,
        metavar="SHARE",
        help="the share of a picture's colour a map's group must be expected to put in "
        "a listed cell for --draw-cells to keep it",
    )
    rotate_mine_maps.add_argument(
        "--draw-maps",
        metavar="FILE",
        help='a maps MANIFEST - a JSONL of {"schema": 1, "map": ...} rows - naming the '
        "colormaps every draw here may offer",
    )
    rotate_mine_draws.add_argument(
        "--bands",
        type=int,
        default=None,
        metavar="COUNT",
        help=f"how many equal-count bands the head's rank range inside one partition is "
        f"cut into (default {depth_module.RANK_BANDS})",
    )
    rotate_mine_draws.add_argument(
        "--top-bands",
        type=int,
        default=None,
        metavar="COUNT",
        help="restrict the FLAT and CONDITIONED draws to the strongest COUNT rank bands. "
        "Unsaid, they draw over the whole range",
    )
    rotate_mine_draws.add_argument(
        "--band-weights",
        default=None,
        metavar="JSON",
        help="how many turns a round each rank band gets in the ranked draw, as JSON",
    )
    rotate_mine_draws.add_argument(
        "--partition-weights",
        default=None,
        metavar="JSON",
        help="what share of the breadth draw each PARTITION gets, as JSON. MERGED OVER "
        "the standing table in curation.draw_weights rather than replacing it",
    )
    rotate_mine_clock.add_argument(
        "--chunk",
        type=int,
        default=rotation_module.CHUNK_GROUPS,
        metavar="BLOCKS",
        help=f"location blocks rendered before the leg stops to read what it made "
        f"(default {rotation_module.CHUNK_GROUPS})",
    )
    rotate_mine_clock.add_argument(
        "--workers",
        type=int,
        default=rotation_module.WORKERS,
        metavar="COUNT",
        help=f"render workers (default {rotation_module.WORKERS}, this machine's pool)",
    )
    device_flag(rotate_mine_clock)
    merging_rotate.add_argument(
        "--dry-run",
        action="store_true",
        help="decide and touch nothing: no upsert, no removal, no prune",
    )

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
