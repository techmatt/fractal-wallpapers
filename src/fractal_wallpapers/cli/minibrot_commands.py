"""`minibrots probe` and `minibrots census`: what a frame holds, and how many do.

The command surface over [`fractal_wallpapers.discovery.minibrot`]. `probe` is one
frame — a link, or coordinates — and prints the atom it sits on. `census` is a
population, cheapest first: the seats of the kept records, the frames a human has
judged, then the whole parameter-plane pool.

The three populations are named rather than taken as a file because each is a
*join* this repository already knows how to make and a list nobody should have to
keep: the records come off [`curation.tentative.kept`], the verdicts off the
location label store, and the pool off the candidate ledger. A caller who wants
some other population hands one in with `--locations`.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path

#: The three named populations, cheapest first — the census's own running order.
POPULATIONS = ("records", "verdicts", "pool")


def _plane_rows(rows):
    """`{location key: (partition, re, im, width)}` for the parameter planes only."""
    from fractal_wallpapers.discovery import minibrot

    held: dict[str, tuple] = {}
    for partition, location, center_re, center_im, width in rows:
        if partition not in minibrot.PLANES or not location:
            continue
        held.setdefault(str(location), (partition, center_re, center_im, width))
    return held


def _from_the_pool():
    """Every parameter-plane location the candidate ledger holds."""
    from fractal_wallpapers.curation import candidate_ledger

    def rows():
        for row in candidate_ledger.stream():
            recipe = row.get("recipe") or {}
            viewport = recipe.get("viewport") or {}
            yield (
                row.get("partition"),
                (row.get("location") or {}).get("key"),
                viewport.get("center_re"),
                viewport.get("center_im"),
                viewport.get("width"),
            )

    return _plane_rows(rows())


def _from_the_records():
    """Every location seated in a kept tentative record, with the records it sits in."""
    from fractal_wallpapers.curation import tentative

    seats: dict[str, set[str]] = {}
    rows = []
    for stamp in tentative.kept():
        name = tentative.read_manifest(stamp)["solve"]["name"]
        for row in tentative.read_rows(stamp):
            location = row.get("location")
            if not location:
                continue
            held = json.loads(location)
            rows.append((row.get("partition"), location, held[3], held[4], held[5]))
            seats.setdefault(str(location), set()).add(name)
    return _plane_rows(rows), {key: sorted(names) for key, names in seats.items()}


def _from_the_verdicts():
    """Every parameter-plane frame the location label store carries a verdict on."""
    from fractal_wallpapers.labeling import store

    rows = []
    verdicts: dict[str, int] = {}
    for key, row in store.resolved().current.items():
        # `key[0]` is already the partition — the label store keys on the same
        # tuple the pool's `location.key` is the JSON of, so the two join as
        # strings and nothing here re-derives a partition from a family record.
        location = json.dumps([key[0], key[1], list(key[2]), key[3], key[4], key[5]])
        rows.append((key[0], location, key[3], key[4], key[5]))
        verdicts[location] = int(row.get("score") or 0)
    return _plane_rows(rows), verdicts


def _skipped(paths) -> set[str]:
    """Every location a prior census output already carries a row for.

    The three populations overlap — a seated location is a pool location and most
    are labelled — so the pool pass is handed the earlier passes' outputs and
    probes the remainder. The union of the files is the census; this is what stops
    the expensive pass re-paying for the cheap ones.
    """
    held: set[str] = set()
    for path in paths or ():
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                held.add(str(json.loads(line)["location"]))
    return held


def _decade_order(item) -> int:
    """Sort key for a [`minibrot.ratio_decade`] bin name, `n/a` last."""
    name = item[0]
    return int(name[2:]) if name.startswith("1e") else 1 << 30


def _summary(found: list[dict], reading: str) -> dict:
    """The counts a census pass reports: how many, in band, enclosed, and where."""
    from fractal_wallpapers.discovery import minibrot

    report: dict = {
        "probed": len(found),
        "refused": dict(Counter(row["refused"] for row in found if "refused" in row).most_common()),
    }
    if reading in ("both", "band"):
        bands = Counter(row["band"] for row in found if "band" in row)
        # In the bins' own order and not the string order, which puts 16-32
        # between 1-2 and 2-4 and makes a distribution unreadable as one.
        ordered = [minibrot.band_of(edge) for edge in (0.5, *minibrot.BANDS)]
        report.update(
            {
                "with_a_nucleus": sum(1 for row in found if "period" in row),
                "in_frame": sum(1 for row in found if row.get("in_frame")),
                "band": f"{minibrot.FRAME_MIN:g}-{minibrot.FRAME_MAX:g} atom sizes",
                "by_band": {name: bands[name] for name in ordered},
                "in_frame_by_partition": dict(
                    Counter(row["partition"] for row in found if row.get("in_frame")).most_common()
                ),
            }
        )
    if reading in ("both", "enclosing"):
        decades = Counter(row["ratio_decade"] for row in found if "ratio_decade" in row)
        report.update(
            {
                "enclosed": sum(1 for row in found if row.get("enclosed")),
                "enclose_k": minibrot.ENCLOSE_K,
                "by_enclosing_period": dict(
                    Counter(
                        row["enclosing_period"] for row in found if "enclosing_period" in row
                    ).most_common(12)
                ),
                # Numerically and not by the key string, which files 1e10 between
                # 1e1 and 1e2 and makes a distribution unreadable as one. `n/a`
                # cannot arrive on an enclosed row — the ratio is at least 1 by
                # construction — and is sorted rather than assumed away.
                "by_ratio_decade": dict(sorted(decades.items(), key=_decade_order)),
                "enclosed_by_partition": dict(
                    Counter(row["partition"] for row in found if row.get("enclosed")).most_common()
                ),
            }
        )
    return report


def minibrots(args: argparse.Namespace) -> int:
    """`minibrots probe` and `minibrots census`, dispatching on the verb."""
    if args.what == "probe":
        return _probe(args)
    return _census(args)


def _probe(args: argparse.Namespace) -> int:
    from fractal_wallpapers.curation import pins
    from fractal_wallpapers.discovery import minibrot

    if args.link:
        try:
            view = pins.parse(args.link)
        except pins.PinsRefused as refusal:
            print(refusal)
            return 1
        family = view["family"]
        if family.startswith("julia") or family.startswith("phoenix"):
            print(f"{minibrot.NOT_A_PLANE}: {family}")
            return 1
        partition = family
        center_re, center_im, width = view["x"], view["y"], view["w"]
    else:
        partition = args.partition
        center_re, center_im, width = args.center_re, args.center_im, args.width
    degree = minibrot.degree_of(partition)
    if degree is None:
        print(f"{minibrot.NOT_A_PLANE}: {partition}")
        return 1
    held = minibrot.scan(center_re, center_im, degree)
    record, cost = minibrot.probe(center_re, center_im, width, degree, held=held)
    around, enclose_cost = minibrot.enclosing(center_re, center_im, width, degree, held=held)
    print(
        json.dumps(
            {
                "partition": partition,
                "atom": record,
                "cost": cost,
                "chain": held.chain[:16],
                "enclosing": around,
                "enclosing_cost": enclose_cost,
            },
            indent=2,
        )
    )
    return 0 if record is not None or around is not None else 1


def _census(args: argparse.Namespace) -> int:
    import time

    from fractal_wallpapers.cli.common import resolve_output
    from fractal_wallpapers.discovery import minibrot

    seats: dict[str, list[str]] = {}
    verdicts: dict[str, int] = {}
    if args.locations:
        rows = [json.loads(line) for line in Path(args.locations).read_text("utf-8").splitlines()]
        held = _plane_rows(
            (row["partition"], row["location"], row["center_re"], row["center_im"], row["width"])
            for row in rows
        )
    elif args.population == "records":
        held, seats = _from_the_records()
    elif args.population == "verdicts":
        held, verdicts = _from_the_verdicts()
    else:
        held = _from_the_pool()
    already = _skipped(args.skip)
    dropped = sum(1 for key in held if key in already)
    # A seeded shuffle and not the key order, so a pass the budget cuts short is a
    # uniform SAMPLE of its population rather than a lexicographic prefix — which
    # on this population is a prefix in the real part of the centre and therefore
    # a prefix in where on the plane the frames are.
    keys = sorted(key for key in held if key not in already)
    random.Random(args.seed).shuffle(keys)
    if args.limit:
        keys = keys[: args.limit]
    print(
        f"[census] {len(keys):,} parameter-plane location(s) to probe"
        + (f", {dropped:,} already read" if dropped else "")
    )

    tasks = [(key, *held[key], args.reading) for key in keys]
    started = time.time()
    found: list[dict] = []
    out = resolve_output(args.out) if args.out else None
    handle = out.open("w", encoding="utf-8", newline="\n") if out else None
    try:
        for row in minibrot.census(tasks, workers=args.workers, budget=args.budget):
            if row["location"] in seats:
                row["records"] = seats[row["location"]]
            if row["location"] in verdicts:
                row["verdict"] = verdicts[row["location"]]
            found.append(row)
            if handle is not None:
                handle.write(json.dumps(row, separators=(",", ":")) + "\n")
            if len(found) % 500 == 0:
                rate = len(found) / max(time.time() - started, 1e-9)
                print(f"[census] {len(found):,}/{len(tasks):,} at {rate:.1f}/s", flush=True)
    finally:
        if handle is not None:
            handle.close()
    report = {
        "population": args.population if not args.locations else str(args.locations),
        "asked": len(tasks),
        "seconds": round(time.time() - started, 1),
        "reading": args.reading,
        **_summary(found, args.reading),
    }
    print(json.dumps(report, indent=2))
    return 0


def add_commands(subcommands) -> None:
    """Register `minibrots` and its two verbs."""
    from fractal_wallpapers.curation import release
    from fractal_wallpapers.discovery import minibrot

    group = subcommands.add_parser(
        "minibrots",
        help="is there a minibrot in this frame, and how many frames hold one",
        description=(
            f"Two readings of one frame. (a) it HOLDS a minibrot: its width is between "
            f"{minibrot.FRAME_MIN:g} and {minibrot.FRAME_MAX:g} atom sizes and the nucleus "
            f"lands within {minibrot.NEAR_MULTIPLE:g} frame width(s) of centre. (c) it IS "
            f"decoration of one: a copy of period q > 1 whose atom is at least the frame's "
            f"width and whose nucleus is within {minibrot.ENCLOSE_K:g} of that copy's own "
            f"atom sizes encloses it. Parameter planes only: a julia or phoenix view has no "
            f"embedded copy of the set to find."
        ),
    )
    verbs = group.add_subparsers(dest="what", required=True)

    one = verbs.add_parser(
        "probe",
        help="the atom one frame sits on",
        description=(
            "One frame, named by an explorer link or by coordinates. Prints the atom's "
            "period, its linear scale, the frame's width in atom sizes and what the solve "
            "cost, or the refusal where there is no atom near the centre."
        ),
    )
    one.add_argument("--link", help="an explorer link; its plane, centre and width are read")
    one.add_argument("--center-re", help="frame centre, real part, as a decimal string")
    one.add_argument("--center-im", help="frame centre, imaginary part, as a decimal string")
    one.add_argument("--width", help="frame width, as a decimal string")
    one.add_argument(
        "--partition",
        default=minibrot.PLANES[0],
        choices=minibrot.PLANES,
        help=f"which parameter plane the coordinates are on (default: {minibrot.PLANES[0]})",
    )

    many = verbs.add_parser(
        "census",
        help="probe a population and report the distribution",
        description=(
            "Three named populations, cheapest first: `records` is every location seated in "
            "a kept tentative record, `verdicts` every frame the location label store holds "
            "a human class on, and `pool` every parameter-plane location in the candidate "
            "ledger. Hand in your own with --locations."
        ),
    )
    many.add_argument(
        "--population",
        default=POPULATIONS[0],
        choices=POPULATIONS,
        help=f"which population to probe (default: {POPULATIONS[0]}) — they are listed "
        f"cheapest first and each is a join this repository already makes",
    )
    many.add_argument(
        "--locations",
        help="a JSONL file of {partition, location, center_re, center_im, width} to probe "
        "instead of a named population",
    )
    many.add_argument(
        "--reading",
        default=minibrot.READINGS[0],
        choices=minibrot.READINGS,
        help=f"which criteria to take (default: {minibrot.READINGS[0]}) — `band` is (a), the "
        f"atom this frame HOLDS, `enclosing` is (c), the copy this frame is DECORATION OF, and "
        f"`both` shares one orbit scan between them. (c) is much the cheaper of the two",
    )
    many.add_argument("--out", help="write one JSONL row per probe here")
    many.add_argument(
        "--workers",
        type=int,
        default=release.DEFAULT_WORKERS,
        help=f"probe processes, at below-normal priority (default: {release.DEFAULT_WORKERS}) "
        f"— this leg drives no engine, but it saturates its workers for the whole pass and "
        f"the desktop has to stay usable through it",
    )
    many.add_argument(
        "--budget",
        type=float,
        default=None,
        help="wall seconds after which the pass stops handing out work and reports how far "
        "it got. Unset runs the whole population",
    )
    many.add_argument(
        "--skip",
        action="append",
        default=None,
        help="a prior census output whose locations this pass leaves alone; repeatable. The "
        "three populations overlap, so the pool pass is handed the two cheap ones' files "
        "and the union of the outputs is the census",
    )
    many.add_argument(
        "--limit",
        type=int,
        default=None,
        help="probe only the first N locations of the shuffled order, which is a sample of "
        "the population and not a region of the plane",
    )
    many.add_argument(
        "--seed",
        type=int,
        default=0,
        help="the seed the probe order is shuffled under (default: 0). The order is shuffled "
        "rather than sorted so that a pass --budget cuts short is a uniform sample of its "
        "population; sorted by key it would be a prefix in the centre's real part",
    )
    group.set_defaults(handler=minibrots)
