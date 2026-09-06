"""One n=1000 seating per colour-ceiling `K`, so the trade can be looked at.

[`ceiling.K`] is the headroom a colour gets over its target rate before the ceiling
refuses a candidate dominant in it, and the allowance it produces is
[`ceiling.Rule.allowed`] — `floor(K * t * n) + 1`. Moving it is a taste decision
that has to be taken off pictures, and this is the leg that makes the pictures:
one solve per `K` over one pool, everything else held.

## Why this exists rather than a `--k` flag

There is no `--k` on `curate solve run` or `curate solve record`, and there should
not be: `K` is a shipped constant, not a per-pass setting, and a record taken under
a `K` nobody set would be a gallery that cannot be reproduced from the constant.
What this leg writes instead is a **counterfactual**, named as one — each rung's
solve record is `sweepK_k<K>_n<n>_<stamp>` — and **no default moves**.
[`solve.solve`]'s `rule` parameter is the override path, it already existed, and
this passes [`ceiling.Rule`] with a `k` rather than editing the module constant.

## What is held, and what is not

Everything but `K` is what [`cli.curate_commands`]'s `curate solve record` passes,
so a rung at the shipped `K` reproduces the record a `curate solve record` at that
`n` would have written — the `K = 2` rung of 2026-09-06 came back bit-identical to
`20260906T133236Z`, the same 1,000 keys in the same seat order with the same
objective and the same refusal table, and that reproduction is the check that makes
the other rungs worth reading. **Run the shipped `K` as a rung and check it**; a
control that misses is itself the finding.

The pool and the ranking are resolved **once** and shared across the rungs, which
is sound because [`solve.Candidate`] is `@dataclass(frozen=True)`: a rung cannot
leave a mark on the next one's pool. It also makes the leg one pool-holding process
rather than four, which is the rule this machine has.

## The records are the evidence and the tables are the finding

Both come out of one command. [`sweep`] writes a solve record and a tentative
gallery per rung, then [`readings`] reads its own output back and writes the
tables to [`readings_path`] — seats per cell against the allowance, the muted and
vivid shares, seats by mode against the floors, the refusal table, the distinct
maps, and how much of the gallery turned over against the first rung.

They are here rather than in a script beside the records because the tables are
what a `K` gets set off, and the first time this ran they were made by a driver
in `scratch/` — a directory defined as disposable. The records were then deleted
and the maker of the committed tables went with them, which is how a number that
cannot be taken again ends up in a tracked document.

⚠ **The two cell tables answer different questions.** [`cell_counts`] is over
*membership* — every cell a seat is dominant in — because that is what the
ceiling counts; a table over each seat's leading cell shows no cell at its
allowance at all. [`tones`] reports both and says which is which.

## What it found the first time

`curation/MEASUREMENTS.md`'s *What the colour ceiling costs at n=1000*: the worst
seat nearly doubles between `K = 2` and `K = 2.5` while every rung still fills, all
of the growth is muted, and the cells that were short at `K = 2` end **shorter**,
because the headroom is spent where the supply is. The refusal table says nothing
else takes over — `cell_allowance` is still the top refusal at 2.5.

⚠ **Read the allowance off [`ceiling.Rule.allowed`] and not off the formula.** The
product is taken in binary floating point, so `K = 2.4` at `n = 1000` allows **50**
where the arithmetic on paper says 51. This leg prints the allowance per rung for
exactly that reason.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

from fractal_wallpapers.curation import ceiling, solve, tentative

#: The rungs the 2026-09-06 sweep ran, and the default set.
#:
#: The first is the **shipped** `K` and is the control: it reproduces the record a
#: `curate solve record` at the same `n` writes, and nothing above it is worth
#: reading until it does. The other three are the loosenings Matt asked to see.
RUNGS: tuple[float, ...] = (2.0, 2.25, 2.4, 2.5)

#: The seat count a rung is taken at. [`tentative.RECORDED_SEATS`] and not a second
#: opinion about it: a counterfactual read at a size no record is kept at would not
#: be comparable with the record it is a counterfactual on.
SEATS = tentative.RECORDED_SEATS


def tag_of(k: float) -> str:
    """`2.25` as `2p25` — a `K` as a directory name. No dot, because a solve record
    is a directory and a dot in one reads as an extension."""
    return f"{float(k):g}".replace(".", "p")


def name_of(k: float, n: int, stamp: str) -> str:
    """What a rung's solve record is called. **Obviously a sweep**: these are
    disposable counterfactuals and the store holds a hundred real ones."""
    return f"sweepK_k{tag_of(k)}_n{int(n)}_{stamp}"


def allowance(k: float, n: int) -> int:
    """The per-cell allowance one rung runs under, asked of the rule that applies it.

    Asked and never computed here — see the module note on the float. The cell is
    any untargeted one, since this leg carries no target and they all share
    [`ceiling.CELL_SHARE`].
    """
    return ceiling.Rule(k=k).allowed("dark_vivid_blue", int(n))


# --------------------------------------------------------------------------- #
# The readings.
# --------------------------------------------------------------------------- #
def cell_counts(rows) -> dict:
    """`{cell: seats}` over **membership** and never the leading cell.

    The allowance counts a seat in every cell it is dominant in — that is what
    [`rules.State.counted_refusal`] walks — so a table read off `row["cell"]`
    would be answering a different question from the one the ceiling asks, and
    would show no cell at its allowance at all. The two totals differ by about
    two to one at n=1000: 1,904 memberships over 1,000 seats at `K = 2`.
    """
    tally: dict = {}
    for row in rows:
        for cell in row["cells"]:
            tally[cell] = tally.get(cell, 0) + 1
    return tally


def tone_of(cell) -> str:
    """`vivid`, `muted`, or `none` for a seat with no chromatic cell at all."""
    if not cell:
        return "none"
    if "_vivid_" in str(cell):
        return "vivid"
    return "muted" if "_muted_" in str(cell) else "none"


def tones(rows) -> dict:
    """Both tone readings, because they answer different questions and disagree.

    `leading` is over each seat's first cell, so it partitions the seats and is
    *the gallery's own share* — what a person looking at the page sees. `dominant`
    is over memberships, which is the quantity the ceiling acts on. The 2026-09-06
    sweep moves them differently: memberships gain 121 muted and lose 4 vivid,
    while the leading split moves 39 seats, so quoting one as the other overstates
    or understates the trade depending which way round it is done.
    """
    leading = {"vivid": 0, "muted": 0, "none": 0}
    for row in rows:
        leading[tone_of(row.get("cell"))] += 1
    dominant = {"vivid": 0, "muted": 0, "none": 0}
    for cell, held in cell_counts(rows).items():
        dominant[tone_of(cell)] += held
    return {"leading": leading, "dominant": dominant}


def families_of(rows) -> dict:
    """`{hue family: seats}`, membership again and for the same reason."""
    tally: dict = {}
    for row in rows:
        for family in row["families"]:
            tally[family] = tally.get(family, 0) + 1
    return tally


def reading_of(block: dict, control_rows=None) -> dict:
    """One rung's tables, off the two records it wrote. Nothing is re-solved.

    `control_rows` is the first rung's seats, so every rung can say how much of
    the gallery turned over against the shipped `K`. The first rung's own reading
    passes `None` and reports no turnover, which is the honest answer rather than
    a row of zeroes that looks like a measurement.
    """
    rows = tentative.read_rows(block["stamp"])
    record = solve.read_record(block["solve_name"])
    held = int(block["allowance"])
    tally = cell_counts(rows)
    modes = record["shortfalls"]["modes"]["per_mode"]
    groups: dict = {}
    for seat in record["seated"]:
        groups[seat["palette_group"]] = groups.get(seat["palette_group"], 0) + 1
    keys = {row["key"] for row in rows}
    out = {
        "k": block["k"],
        "allowance": held,
        "stamp": block["stamp"],
        "solve_name": block["solve_name"],
        "page": block["page"],
        "filled": record["filled"],
        "seconds": record["seconds"],
        "objective": record["objective"]["final"],
        "cells": {
            "counts": dict(sorted(tally.items())),
            "memberships": sum(tally.values()),
            "pinned": sum(1 for seats in tally.values() if seats >= held),
            "over": sum(1 for seats in tally.values() if seats > held),
            "short": [
                {"cell": cell, "seats": seats}
                for seats, cell in sorted(
                    (seats, cell) for cell, seats in tally.items() if seats < held
                )
            ],
        },
        "tones": tones(rows),
        "families": {
            "allowance": ceiling.Rule(k=block["k"]).allowed("blue", int(block["n"])),
            "counts": dict(sorted(families_of(rows).items())),
        },
        "modes": {
            name: {"floor": seen["floor"], "seated": seen["seated"]}
            for name, seen in sorted(modes.items())
        },
        "modes_on_their_floor": sorted(
            name for name, seen in modes.items() if seen["seated"] == seen["floor"]
        ),
        "refusals": record["rules"]["refusals_while_choosing"],
        "rejection_reasons": record["rejection"]["reasons"],
        "maps": {
            "distinct": len(groups),
            "cap": record["rules"]["group_cap"],
            "busiest": sorted(groups.items(), key=lambda item: (-item[1], item[0]))[:5],
        },
    }
    if control_rows is None:
        out["turnover_against_the_control"] = None
    else:
        base = {row["key"] for row in control_rows}
        out["turnover_against_the_control"] = {
            "differing_seats": len(keys - base),
            "shared": len(keys & base),
        }
    return out


def readings(blocks, control: str | None = None, log=print) -> dict:
    """Every rung's tables, plus the control check where a stamp is named.

    `control` is an earlier record's stamp the **first** rung claims to reproduce.
    Named rather than found, because "the newest n=1000 record" is not a claim
    about anything — the check is only worth taking against a record somebody
    decided this sweep is a counterfactual on. Where it is named, the answer is a
    seat-for-seat comparison and not a summary: two galleries with the same
    objective and different seats are two different galleries.
    """
    out: dict = {"control_record": control, "rungs": []}
    first = tentative.read_rows(blocks[0]["stamp"]) if blocks else []
    for at, block in enumerate(blocks):
        out["rungs"].append(reading_of(block, control_rows=None if at == 0 else first))
    if control:
        theirs = [row["key"] for row in tentative.read_rows(control)]
        ours = [row["key"] for row in first]
        record = solve.read_record(blocks[0]["solve_name"])
        theirs_record = solve.read_record(tentative.read_manifest(control)["solve"]["name"])
        out["control_check"] = {
            "same_seat_set": set(theirs) == set(ours),
            "same_seat_order": theirs == ours,
            "shared": len(set(theirs) & set(ours)),
            "their_objective": theirs_record["objective"]["final"],
            "our_objective": record["objective"]["final"],
            "their_refusals": theirs_record["rules"]["refusals_while_choosing"],
            "our_refusals": record["rules"]["refusals_while_choosing"],
        }
        verdict = "reproduces" if out["control_check"]["same_seat_order"] else "DOES NOT match"
        log(f"[k-sweep] the K={blocks[0]['k']:g} rung {verdict} {control}")
    return out


def readings_path(stamp: str, n: int) -> Path:
    """Where a sweep's tables land: a solve directory of the sweep's own.

    Beside the rungs and under the same `sweepK_` prefix on purpose — deleting a
    whole sweep is then one glob over `artifacts/curation/solve/`, which is what
    the 2026-09-06 tidy-up had to do by hand across two directories.
    """
    return solve.solve_dir(f"sweepK_n{int(n)}_{stamp}") / "readings.json"


def write_readings(held: dict, stamp: str, n: int) -> Path:
    path = readings_path(stamp, n)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(held, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def summarise(held: dict, log=print) -> None:
    """The tables as lines, because a sweep is read at the terminal before the file."""
    for block in held["rungs"]:
        turnover = block["turnover_against_the_control"]
        log(
            f"\n[k-sweep] K={block['k']:g} allowance {block['allowance']} "
            f"{block['stamp']}\n"
            f"  filled {block['filled']} in {block['seconds']}s; "
            f"worst {block['objective']['worst']} sum {block['objective']['sum']}\n"
            f"  cells: {block['cells']['pinned']} pinned, "
            f"{len(block['cells']['short'])} short, {block['cells']['over']} over, "
            f"{block['cells']['memberships']} memberships\n"
            f"  tone leading {block['tones']['leading']}; "
            f"dominant {block['tones']['dominant']}\n"
            f"  maps: {block['maps']['distinct']} distinct under a cap of "
            f"{block['maps']['cap']}, busiest {block['maps']['busiest'][:3]}\n"
            f"  on their floor: {block['modes_on_their_floor']}\n"
            f"  turnover: {'the control' if turnover is None else turnover}\n"
            f"  refusals: {block['refusals']}\n"
            f"  short cells: "
            f"{[(row['cell'], row['seats']) for row in block['cells']['short']]}"
        )


# --------------------------------------------------------------------------- #
# The sweep.
# --------------------------------------------------------------------------- #
def sweep(rungs=RUNGS, n: int = SEATS, control: str | None = None, log=print) -> dict:
    """One recorded seating per `K`, and the tables off them. **One command.**

    Each rung writes both halves under one stamp, exactly as `curate solve record`
    does: the solve record under [`name_of`] and the tentative gallery under the
    stamp, with its page. Every rung is **unpublished** — a tentative record is
    published only when Matt names it — and every one holds prune protection
    through [`tentative.protected_keys`] until its folder is deleted, published or
    not. A sweep is disposable and this is the thing to remember about deleting it.

    Then [`readings`] over what was written, into [`readings_path`]. The tables
    are here and not in a scratch script because they are what the sweep is *for*
    — the records are the evidence and the tables are the finding, and a finding
    whose maker gets wiped is a finding nobody can take again.
    """
    started = time.monotonic()
    ks = [float(k) for k in rungs]
    # The sweep's own stamp, taken before any rung's. Each rung stamps itself, so
    # this is the only name that says which rungs were one sweep.
    sweep_stamp = tentative.stamp_now()
    log(f"[k-sweep] allowance at n={n}: " + ", ".join(f"K={k:g} -> {allowance(k, n)}" for k in ks))

    candidates, refused = solve.pool(log=log)
    order, coverage = solve.ranking_for(candidates, solve.DEFAULT_KEY, log=log)
    log(f"[k-sweep] pool and ranking in {time.monotonic() - started:.1f}s")

    out: list[dict] = []
    for k in ks:
        at = time.monotonic()
        rule = ceiling.Rule(targets={}, k=k)
        log(f"[k-sweep] === K={k:g} (allowance {allowance(k, n)}) ===")
        record = solve.solve(
            candidates,
            n=int(n),
            rule=rule,
            order=order,
            coverage=coverage,
            key=solve.DEFAULT_KEY,
            spiral_cap=solve.DEFAULT_SPIRAL_CAP,
            mode_ceilings=dict(solve.DEFAULT_MODE_CEILINGS),
            augment_chains=solve.DEFAULT_AUGMENT,
            log=log,
        )
        stamp = tentative.stamp_now()
        name = name_of(k, n, stamp)
        log(f"[k-sweep] {solve.write_record(name, record)}")
        tentative.write(
            record,
            candidates=candidates,
            solve_name=name,
            pool_refused=refused,
            stamp=stamp,
            log=log,
        )
        page = tentative.page(stamp, log=log)
        out.append(
            {
                "k": k,
                "allowance": allowance(k, n),
                "n": int(n),
                "stamp": stamp,
                "solve_name": name,
                "page": str(page),
                "filled": record["filled"],
                "objective": record["objective"]["final"],
                "refusals": record["rules"]["refusals_while_choosing"],
                "seconds": round(time.monotonic() - at, 2),
            }
        )
        log(f"[k-sweep] {page}")

    held = readings(out, control=control, log=log)
    held["taken_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    held["stamp"] = sweep_stamp
    held["n"] = int(n)
    held["k"] = ks
    summarise(held, log=log)
    held["readings"] = str(write_readings(held, sweep_stamp, n))
    log(f"[k-sweep] {held['readings']}")
    log(f"[k-sweep] {len(out)} rung(s) in {time.monotonic() - started:.1f}s")
    return held


__all__ = [
    "RUNGS",
    "SEATS",
    "allowance",
    "cell_counts",
    "families_of",
    "name_of",
    "reading_of",
    "readings",
    "readings_path",
    "summarise",
    "sweep",
    "tag_of",
    "tone_of",
    "tones",
    "write_readings",
]
