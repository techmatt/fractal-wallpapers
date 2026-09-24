"""`minibrots probe`, `census` and `examples`: what a frame holds, how many do, and
which ones a writeup should look at.

The command surface over [`fractal_wallpapers.discovery.minibrot`]. `probe` is one
frame — a link, or coordinates — and prints both readings of it. `census` is a
population, cheapest first: the seats of the kept records, the frames a human has
judged, then the whole parameter-plane pool.

The three populations are named rather than taken as a file because each is a
*join* this repository already knows how to make and a list nobody should have to
keep: the records come off [`curation.tentative.kept`], the verdicts off the
location label store, and the pool off the candidate ledger. A caller who wants
some other population hands one in with `--locations`.

`examples` turns a census output into the **example set** a writeup picks figures
from: one row per enclosed place, each carrying its explorer link, its enclosing
copy, the whole solved chain and what the walk, the head and the records say about
it. It re-reads the census's own `chain_table` rather than probing again, so a
different cut costs nothing and the answers cannot drift from the census's. The
output is **not tracked** — see [`minibrot.EXAMPLES_NAME`] for why — and it lands
under the hot tier, which is what survives `scratch/` being wiped.
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
    """`minibrots probe`, `census` and `examples`, dispatching on the verb."""
    if args.what == "probe":
        return _probe(args)
    if args.what == "examples":
        return _examples(args)
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


# --------------------------------------------------------------------------- #
# `examples`: the census output as the set a writeup picks figures from.
# --------------------------------------------------------------------------- #
#: Cuts the summary row reports counts at, whatever the population is kept at.
#:
#: The shipped bound, the one every tuned *frame* clears rather than every tuned
#: frame the pool kept, and the geometric extent of a copy. A writeup quoting "one
#: place in N is inside a copy" has to say which of these it means, and the three
#: differ by an order of magnitude.
REPORTED_CUTS = (1.0, 1.35, 1.5, 2.0)


def _census_output(paths):
    """Every row of every census output named, oldest file first, by place."""
    held: dict[str, dict] = {}
    for path in paths:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                held[str(row["location"])] = row
    return held


def _pool_rows(places: set[str]) -> dict:
    """The pool row each place is *shown* by: its best fine reading, or its first.

    One streamed pass, because the ledger is hundreds of megabytes and this is the
    only thing in this command that touches it. The chosen row is what the example's
    link, mode, palette and picture come from, so the link opens the picture the
    `p_fine` beside it is a reading of.
    """
    from fractal_wallpapers.curation import candidate_ledger
    from fractal_wallpapers.models import gallery_grade_train

    fine = gallery_grade_train.read_pool_scores()
    held: dict[str, dict] = {}
    for row in candidate_ledger.stream():
        place = str((row.get("location") or {}).get("key") or "")
        if place not in places:
            continue
        recipe = row.get("recipe") or {}
        read = fine.get(str(row.get("key")))
        value = float(read["p_ge4"]) if read and read.get("p_ge4") is not None else None
        seen = held.get(place)
        if seen is not None and not (value is not None and (seen["p_fine"] or -1.0) < value):
            continue
        held[place] = {
            "candidate": str(row.get("key")),
            "mode": recipe.get("mode"),
            "colormap": recipe.get("colormap"),
            "phase": float((recipe.get("palette") or {}).get("phase") or 0.0),
            "picture": bool(row.get("picture")),
            "p_fine": value,
            "family": recipe.get("family") or {},
            "maxiter": recipe.get("maxiter"),
        }
    return held


def _walk_rows(places) -> dict:
    """What the walk ledgers say about each place: tuned or not, root kind, depth."""
    from fractal_wallpapers.discovery import minibrot

    index = minibrot.walk_index()
    held: dict[str, dict] = {}
    for place in places:
        parsed = json.loads(place)
        got = minibrot.descent(index, parsed[3], parsed[4], parsed[5])
        if got is None:
            continue
        tuned = bool((got.root_provenance or {}).get("tuned_seed_key"))
        held[place] = {
            "provenance": "tuned" if tuned else "untuned",
            "root_kind": "tuned_descent" if tuned else got.root_source,
            "depth": got.depth,
            "decades": None if got.decades is None else round(got.decades, 2),
        }
    return held


def _seat_names(places) -> dict:
    """`{place: [record, …]}` over the kept records, for the places asked about."""
    from fractal_wallpapers.curation import tentative

    held: dict[str, set] = {}
    for stamp in tentative.kept():
        name = tentative.read_manifest(stamp)["solve"]["name"]
        for row in tentative.read_rows(stamp):
            place = str(row.get("location") or "")
            if place in places:
                held.setdefault(place, set()).add(name)
    return {place: sorted(names) for place, names in held.items()}


def _view_of(place: str, shown: dict) -> dict:
    """The place as [`pins.query_of`] wants it: plane, constants, mode, coordinates."""
    from fractal_wallpapers.curation import pins

    parsed = json.loads(place)
    family = shown.get("family") or {}
    kind = family.get("kind") or str(parsed[0]).split(":")[0]
    return {
        "family": pins.family_of(kind, family.get("degree", parsed[1])),
        "constants": {},
        "mode": shown.get("mode"),
        "x": parsed[3],
        "y": parsed[4],
        "w": parsed[5],
        "palette": shown.get("colormap"),
        "phase": shown.get("phase") or 0.0,
        # The cap the row was drawn at, which the link writes as `n` where it is not the
        # width's — so the example opens the picture its `p_fine` is a reading of.
        "maxiter": shown.get("maxiter"),
    }


def _significant(value, digits: int = 6):
    """`value` at `digits` significant figures. A size is a scale, not an identity."""
    import math

    if not value or not isinstance(value, (int, float)) or not math.isfinite(value):
        return value
    return float(f"{value:.{digits}g}")


def _example_row(place, census, head, groups, solved, shown, walk, records) -> dict:
    """One example: where it is, what encloses it, and what everything else says.

    The place key carries the plane, the centre and the width, and the query carries
    them again because a link has to; nothing else repeats them. `chain` is every
    copy the census solved that is bigger than the frame, each as
    `[period, atom size, distance in its own atom sizes]`, so a **tighter** cut is a
    filter over this list and not another census.
    """
    from fractal_wallpapers.curation import pins

    entry = {
        "schema": 1,
        "place": place,
        "mode": shown.get("mode"),
        "query": pins.query_of(_view_of(place, shown)),
        "q": head["period"],
        "ratio": _significant(head["window_scale"] / float(census["width"])),
        "distance_atoms": round(head["distance_atoms"], 5),
        "chain": [
            [one["period"], _significant(one["window_scale"]), round(one["distance_atoms"], 5)]
            for one in solved
        ],
        "generations": [[member["period"] for member in group] for group in groups],
        "provenance": (walk or {}).get("provenance", "no_walk_row"),
    }
    if shown.get("p_fine") is not None:
        entry["p_fine"] = round(shown["p_fine"], 4)
    if shown.get("candidate"):
        entry["candidate"] = shown["candidate"]
    if shown.get("picture"):
        entry["picture"] = True
    for key in ("root_kind", "depth", "decades"):
        if (walk or {}).get(key) is not None:
            entry[key] = walk[key]
    if records:
        entry["records"] = records
    return entry


def _descent_chains(globs, k: float) -> list[dict]:
    """One `descent_chain` example per tuned walk directory group named.

    A tuned descent is a walk aimed *into* a satellite, so its ledger is the one
    place this repository holds a whole nesting as a sequence of frames somebody
    rendered: the rungs come out as `<run>/views/node<parent>_c<child>.jpg`, which is
    the gate render at each step. The satellite's period and atom size come off the
    root row's own provenance rather than a table here, so a leg that aimed at a
    different satellite reads correctly with no edit.

    The deepest admitted node of each group wins, and its chain is walked back up
    `parent_node_id`. Nothing is probed from a table here — the deepest node is
    usually not a pool row at all — so this is the one place the command solves.
    """
    from fractal_wallpapers.curation import pins
    from fractal_wallpapers.discovery import minibrot
    from fractal_wallpapers.paths import hot_root

    best: dict[str, tuple] = {}
    for pattern in globs:
        for directory in sorted(hot_root().glob(pattern)):
            ledger = directory / "walk.jsonl"
            if not ledger.is_file():
                continue
            root, rows = None, []
            for line in ledger.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("kind") == "root":
                    root = row
                elif row.get("kind") == "candidate" and row.get("node_id") is not None:
                    rows.append(row)
            if root is None or not rows:
                continue
            provenance = root.get("provenance") or {}
            group = str(provenance.get("tuned_satellite") or directory.name)
            deepest = min(rows, key=lambda row: float(row["viewport"]["width"]))
            width = float(deepest["viewport"]["width"])
            if group not in best or width < best[group][0]:
                best[group] = (width, directory.name, root, rows, deepest)

    out = []
    for group in sorted(best):
        _width, run, root, rows, deepest = best[group]
        provenance = root.get("provenance") or {}
        admitted = {row["node_id"]: row for row in rows}
        rungs, node = [], deepest
        while node is not None:
            rungs.append(node)
            node = admitted.get(node.get("parent_node_id"))
        rungs.reverse()
        view = deepest["viewport"]
        record, _cost = minibrot.enclosing(
            view["center_re"], view["center_im"], view["width"], 2, k=k
        )
        out.append(
            {
                "schema": 1,
                "example": "descent_chain",
                "satellite": group,
                "satellite_period": provenance.get("tuned_satellite_period"),
                "satellite_nucleus": provenance.get("tuned_satellite_key"),
                "satellite_atom_size": provenance.get("tuned_abs_lambda"),
                "run": run,
                "seed": provenance.get("tuned_seed_key"),
                "seeded_where": provenance.get("tuned_seed_where"),
                "query": pins.query_of(
                    {
                        "family": pins.family_of(
                            (root.get("family") or {}).get("kind", "mandelbrot"),
                            (root.get("family") or {}).get("degree", 2),
                        ),
                        "constants": {},
                        "mode": None,
                        "x": view["center_re"],
                        "y": view["center_im"],
                        "w": view["width"],
                        "palette": None,
                        "phase": 0.0,
                    }
                ),
                "rungs": [{"depth": "root", "width": (root.get("viewport") or {}).get("width")}]
                + [
                    {
                        "depth": rung.get("depth"),
                        "width": rung["viewport"]["width"],
                        "branch": rung.get("branch"),
                        "placement": rung.get("placement"),
                        "interior_fraction": _significant(rung.get("interior_fraction"), 4),
                        "occupancy": _significant(rung.get("occupancy"), 4),
                        "view": f"{run}/views/node{rung['parent_node_id']}"
                        f"_c{rung['child_index']}.jpg",
                    }
                    for rung in rungs
                ],
                "q": None if record is None else record["period"],
                "ratio": None if record is None else _significant(record["size_over_width"]),
                "chain_periods": None if record is None else record["chain_periods"],
                "generations": None if record is None else record["generations"],
            }
        )
    return out


def _examples_summary(census, cuts, kept_at, rows, chains, walk, shown, seats) -> dict:
    """The header row: what a writeup quotes, and the population it is quoting from."""
    import math
    import statistics
    from collections import defaultdict

    from fractal_wallpapers.curation import pins
    from fractal_wallpapers.discovery import minibrot

    by_k = {}
    for k in cuts:
        enclosed = [place for place, row in census.items() if minibrot.enclosing_at(row, k)]
        tuned = sum(1 for place in enclosed if walk.get(place, {}).get("provenance") == "tuned")
        by_k[f"{k:g}"] = {
            "enclosed": len(enclosed),
            "tuned": tuned,
            "untuned": len(enclosed) - tuned,
            "one_in": round(len(census) / len(enclosed)) if enclosed else None,
        }
    untuned = [row for row in rows if row["provenance"] != "tuned"]
    depths = [row["depth"] for row in untuned if row.get("depth") is not None]
    decades = [row["decades"] for row in untuned if row.get("decades") is not None]
    widths, enclosed_widths = defaultdict(int), defaultdict(int)
    kept_places = {row["place"] for row in rows}
    for place, row in census.items():
        width = float(row["width"])
        name = f"1e{int(math.floor(math.log10(width)))}" if width > 0 else "n/a"
        widths[name] += 1
        if place in kept_places:
            enclosed_widths[name] += 1
    order = sorted(widths, key=lambda name: int(name[2:]) if name.startswith("1e") else 1 << 30)
    return {
        "schema": 1,
        "summary": "minibrots examples",
        # The base once for the file, a query a row — see [`pins.EXPLORER_BASE`].
        "explorer": pins.EXPLORER_BASE,
        "probed": len(census),
        "kept_at_k": kept_at,
        "shipped_k": minibrot.ENCLOSE_K,
        "bulb_slack": minibrot.BULB_SLACK,
        "rows": len(rows),
        "descent_chains": len(chains),
        "by_k": by_k,
        "untuned_with_pool_row": sum(1 for row in untuned if row.get("candidate")),
        "untuned_with_walk_row": len(depths),
        "untuned_no_walk_row": sum(1 for row in untuned if row["provenance"] == "no_walk_row"),
        "seated_anywhere": sum(1 for row in rows if row.get("records")),
        "untuned_median_depth": statistics.median(depths) if depths else None,
        "untuned_median_decades": round(statistics.median(decades), 2) if decades else None,
        "by_ratio_decade": dict(
            sorted(
                Counter(minibrot.ratio_decade(row["ratio"]) for row in rows).items(),
                key=lambda item: int(item[0][2:]) if item[0].startswith("1e") else 1 << 30,
            )
        ),
        "by_width_decade": {name: [enclosed_widths[name], widths[name]] for name in order},
    }


def _examples(args: argparse.Namespace) -> int:
    from fractal_wallpapers.cli.common import resolve_output
    from fractal_wallpapers.curation import pins
    from fractal_wallpapers.discovery import minibrot

    census = _census_output(args.census)
    print(f"[examples] {len(census):,} census row(s) read")
    verdicts = {}
    for place, row in census.items():
        got = minibrot.enclosing_at(row, args.k)
        if got is not None:
            verdicts[place] = got
    print(f"[examples] {len(verdicts):,} enclosed at K={args.k:g}")

    places = set(verdicts)
    shown = _pool_rows(places)
    print(f"[examples] {len(shown):,} have a pool row")
    walk = _walk_rows(places)
    print(f"[examples] {len(walk):,} join to a walk row")
    seats = _seat_names(places)
    # One question to the engine for every width a link below will compare its cap to.
    pins.warm_width_caps(json.loads(place)[5] for place in places if place in shown)

    rows = [
        _example_row(
            place,
            census[place],
            *verdicts[place],
            shown.get(place, {}),
            walk.get(place),
            seats.get(place),
        )
        for place in places
    ]
    # Tuned first and then by the fine head, descending, which puts the places a
    # descent aimed at above the ones a walk stumbled into and the best picture at
    # the top of each. Ties by place, so the file is a function of the census.
    rows.sort(
        key=lambda row: (row["provenance"] != "tuned", -(row.get("p_fine") or -1.0), row["place"])
    )
    chains = _descent_chains(args.descents or (), args.k)
    print(f"[examples] {len(chains)} descent chain(s)")

    cuts = sorted({minibrot.TIGHT_ENCLOSE_K, minibrot.ENCLOSE_K, args.k, *REPORTED_CUTS})
    summary = _examples_summary(census, cuts, args.k, rows, chains, walk, shown, seats)
    out = resolve_output(args.out) if args.out else minibrot.examples_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as handle:
        for row in [summary, *chains, *rows]:
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")
    size = out.stat().st_size
    print(f"[examples] wrote {out} — {len(rows):,} places + {len(chains)} chain(s), {size:,} bytes")
    print(json.dumps(summary["by_k"], indent=2))
    return 0


def add_commands(subcommands) -> None:
    """Register `minibrots` and its three verbs."""
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

    examples = verbs.add_parser(
        "examples",
        help="a census output as the set a writeup picks figures from",
        description=(
            "One row per enclosed place, carrying its explorer link, the copy that encloses "
            "it, the whole solved chain and what the walk, the fine head and the kept records "
            "say about it, under a summary row with the counts at several cuts. It re-reads "
            "the census's own `chain_table` and probes nothing, so the answers cannot drift "
            "from the census's and a different --k costs nothing. The output is NOT tracked: "
            "it is regenerable from a census output by this command."
        ),
    )
    examples.add_argument(
        "--census",
        action="append",
        required=True,
        help="a `census --out` file to read; repeatable, and the union of them is the "
        "population. A place named twice keeps the later file's row",
    )
    examples.add_argument(
        "--k",
        type=float,
        default=2.0,
        help="the cut the population is kept at (default: 2.0, the geometric extent of a "
        f"copy and the {minibrot.ENCLOSE_K:g} the census ships — widest, so nothing a "
        f"writeup might want is dropped). Every row carries each chain entry's "
        f"own distance, so a TIGHTER cut is a filter over the output and never a re-run",
    )
    examples.add_argument(
        "--descents",
        action="append",
        help="a glob under the hot root whose walk ledgers are tuned descents, e.g. "
        "`<leg>_<seed>x<satellite>`; repeatable. Each satellite the glob reaches "
        "contributes one `descent_chain` example — its deepest walk, rung by rung, with "
        "the gate render at each step. Unset writes no chains",
    )
    examples.add_argument(
        "--out",
        help="where to write; unset writes beside the hot tier's other discovery output",
    )
    group.set_defaults(handler=minibrots)
