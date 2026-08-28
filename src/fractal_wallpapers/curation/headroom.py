"""What the selection constraints ask for, what the ledger holds, and what a shortfall costs.

Before another leg spends hours making candidates, somebody has to answer which
selection constraints the pool **cannot** satisfy and how expensive each shortfall
is to buy. That answer has to come from arithmetic over the ledger and never from
an optimizer: a solve that runs for twenty minutes and reports "there are no light
greens at all" spent twenty minutes on a fact one pass over the rows already knew.

So this module is O(rows) necessary conditions and nothing else. It decides
nothing, seats nothing, and opens no picture. It is the **upper bound** half of
the pair [`curation.seating`] completes: a census says what could not possibly be
seated, a greedy says what a trivial rule actually seats, and the gap between the
two is the only place exact optimization can buy anything. Close together, the
answer is known and the money goes on making more candidates. Far apart, the gap
is what a solver is for.

## Necessary conditions are the only infeasibility claims allowed

Every row here is of the form "there are `s` distinct locations that could satisfy
this and the constraint needs `r` of them". When `s < r` the program provably
cannot be filled — no ordering, no objective and no solver changes it. That is the
only claim in this file. The reverse is **not** stated anywhere: a constraint with
slack can still be infeasible jointly with another, and this module never says a
selection is possible.

## Counts are distinct locations, never rows

One wallpaper per location is absolute, so a cell fifty recipes carry at one place
is a cell a gallery can seat exactly once. Every supply figure below is a count of
distinct `location.key`, and the row counts sit beside them only to say how deep
the pool stands on each place.

## The bars a row has to clear, per mode

A candidate is only supply if it is worth seating, and what "worth seating" means
is a bar on the ledger's own score column. The default is [`solve.Q4_BAR`] on raw
`P(>=4)`. Eleven of the eighteen production modes have fewer than
[`FALLBACK_LOCATIONS`] distinct locations clearing that, so for those the census
falls back to [`FALLBACK_BAR`] on `P(>=3)` and **says which rule each mode landed
on**. A mode censused under a lower bar is not comparable to one censused under
the default, and a table that did not name the rule per mode would silently mix
them.

Both bars are flags on the arithmetic and neither is a measured crossover. The
one measured release bar this project acts on is `P(>=3) >= 0.575`
([`floors.STRANGE_RELEASE_BAR`]), which is *above* the fallback here; the smooth
kind's measured floor is 0.540 and gates nothing. Nothing in this module
re-scores at shipping geometry, and no per-mode crossover fitted at label geometry
is transported onto the candidate column.

## What "one more" costs

Slack is not the whole answer, because headroom is not equally purchasable. A cell
three locations short of its allowance is a work order only if three more can be
bought for an affordable number of renders, and the ledger already knows the rate:
it holds every candidate this project has ever rendered, and every row a hunt or a
mine wrote carries the seconds it took. So each constraint reports

```text
renders per win = renders on record / distinct clearing locations satisfying it
seconds per win = renders per win * the realized render cost of the modes that won
```

which is the **unconditioned** rate — the rate at which this project's whole
render history happened to produce a location satisfying that constraint, not the
rate an aimed leg would get. An aimed leg beats it, and by how much is a
measurement the conditioned arms make rather than something to assume here. It is
stated on every row for that reason.
"""

from __future__ import annotations

import statistics
from datetime import UTC, datetime

from fractal_wallpapers.curation import candidate_ledger, ceiling, floors, solve

#: The schema every record this module writes carries.
SCHEMA = 1

#: The subtree a census lands in, under the regenerable tree.
UNIT = "headroom"

#: Where the census is taken, in seats. `20` is [`candidate_ledger.FIRST_SOLVE`],
#: the trivial gallery everything else is read against; the three above it are the
#: sizes this project would ship at. Only the first is exercised by a seating
#: today and the whole curve is reported anyway, because it is arithmetic over
#: rows already in hand and the shape of the curve is the finding — a constraint
#: that has slack at 20 and is short at 150 is a mine instruction with a date on
#: it.
LADDER = (20, 150, 500, 1000)

#: The bar a row clears at by default: raw `P(>=4)`, at [`solve.Q4_BAR`].
#:
#: Not restated as a number. It is the same bar the solver's first objective
#: stage counts against, and a census taken at one height against a solve taken at
#: another would report headroom the solve cannot reach.
DEFAULT_BAR = solve.Q4_BAR

#: The column the default bar is on. Spelled out because one head emits three
#: cutpoints and a count says nothing without naming which one it counted.
DEFAULT_COLUMN = "p_ge4"

#: The bar a **thin** mode clears at instead: `P(>=3)`, at
#: [`floors.RELEASE_ADVISORY`].
#:
#: The same height as the default and a different cutpoint, which is the whole of
#: the fallback: the fourth class is where a judge trained on four classes is
#: least sure, and a mode with three locations above it has no supply to census
#: rather than no quality. It is **below** both measured release heights
#: ([`floors.MEASURED_RELEASE_FLOORS`], 0.575 and 0.540) and is a flag on this
#: arithmetic rather than a bar anybody fitted.
FALLBACK_BAR = floors.RELEASE_ADVISORY
FALLBACK_COLUMN = "p_ge3"

#: How many distinct locations a mode has to clear the default bar with before
#: the fallback applies. **25**, which is the same number [`THIN`] flags a
#: constraint at: a mode that cannot field twenty-five distinct places is a mode
#: whose census would be a report about four pictures.
FALLBACK_LOCATIONS = 25

#: Below this many distinct locations a constraint is flagged however much slack
#: the arithmetic says it has. A constraint with twenty-four members can be
#: satisfied and cannot be satisfied *twice* under any of the pairwise rules, and
#: the flag is the list of things to go and make.
THIN = 25

#: What a block's rows are. `demand` is a row that can only fall short (a floor);
#: `cap` a row that can only be exceeded (an allowance); `cover` the derived
#: condition that the caps between them can hold `n` seats at all.
DEMAND, CAP, COVER = "demand", "cap", "cover"


class HeadroomError(RuntimeError):
    """The census cannot be taken."""


# --------------------------------------------------------------------------- #
# The population.
# --------------------------------------------------------------------------- #
def population(rows=None, scores=None, log=print) -> tuple:
    """`(candidates, per-mode render cost, what the pool refused)`.

    The candidates are [`solve.pool`]'s and not a second opinion about which rows
    are eligible: a census of headroom a solve cannot reach is a census of the
    wrong pool. The cost table is read off the same rows in the same pass, because
    the seconds a candidate took live on the ledger row and not on the thinned
    [`solve.Candidate`].
    """
    stored = candidate_ledger.read() if rows is None else list(rows)
    read = candidate_ledger.read_scores() if scores is None else list(scores)
    candidates, refused = solve.pool(rows=stored, scores=read, log=log)
    return candidates, render_cost(stored), refused


def render_cost(rows) -> dict:
    """`{mode: what one candidate cost}` off the seconds a leg stamped on its rows.

    The **median** is what a marginal cost is estimated with. These distributions
    have long right tails — every mode's p90 is two to five times its median,
    because a location deep in the set takes as long as the iteration count says —
    and a mean over a tail like that prices the exception.

    A row written before the stamp existed carries no seconds and is simply not in
    the denominator. Modes are reported with their sample size for that reason: a
    cost read off three hundred rows and one read off twenty-five thousand are
    different qualities of number.
    """
    seen: dict = {}
    for row in rows:
        held = (row.get("hunt") or {}).get("seconds")
        if held is None:
            continue
        seen.setdefault(str((row.get("recipe") or {}).get("mode")), []).append(float(held))
    out = {}
    for mode, values in sorted(seen.items()):
        values.sort()
        out[mode] = {
            "rows": len(values),
            "median": round(statistics.median(values), 4),
            "mean": round(statistics.fmean(values), 4),
            "p90": round(values[min(len(values) - 1, int(0.9 * len(values)))], 4),
        }
    return out


def _cost_of(costs: dict, mode: str) -> float | None:
    held = costs.get(str(mode))
    return None if held is None else float(held["median"])


def _mixed_cost(costs: dict, candidates) -> float | None:
    """The render cost of a set of winners: their modes' medians, mixed as they are.

    A cell is delivered by whichever modes happened to deliver it, and those run
    from 0.20 s a render to 1.42; pricing one at the pool's overall median would
    under-price a cell only the slow modes reach. So the mix is the winners' own.
    """
    prices = [_cost_of(costs, candidate.mode) for candidate in candidates]
    prices = [price for price in prices if price is not None]
    return None if not prices else round(statistics.fmean(prices), 4)


# --------------------------------------------------------------------------- #
# The bars, per mode.
# --------------------------------------------------------------------------- #
def bars(candidates) -> dict:
    """Which rule each production mode's rows clear under, and the counts behind it.

    The default bar on `P(>=4)` unless fewer than [`FALLBACK_LOCATIONS`] distinct
    locations clear it, in which case that mode's rows clear on `P(>=3)` instead.
    Both counts are reported for every mode whichever rule it landed on, so a
    reader can see how far a fallback mode is from the default and whether the
    fallback bought it anything at all.
    """
    from fractal_wallpapers import engine

    modes = list(engine.production_modes())
    held: dict = {name: [] for name in modes}
    off_roster: dict = {}
    for candidate in candidates:
        if candidate.mode in held:
            held[candidate.mode].append(candidate)
        else:
            off_roster[candidate.mode] = off_roster.get(candidate.mode, 0) + 1
    out: dict = {}
    for mode in modes:
        mine = held[mode]
        above4 = [c for c in mine if c.score >= DEFAULT_BAR]
        above3 = [c for c in mine if c.p_ge3 >= FALLBACK_BAR]
        places4 = {c.location for c in above4}
        places3 = {c.location for c in above3}
        rule = DEFAULT_COLUMN if len(places4) >= FALLBACK_LOCATIONS else FALLBACK_COLUMN
        clearing = above4 if rule == DEFAULT_COLUMN else above3
        out[mode] = {
            "rule": rule,
            "bar": DEFAULT_BAR if rule == DEFAULT_COLUMN else FALLBACK_BAR,
            "rows": len(mine),
            "locations": len({c.location for c in mine}),
            "q4_rows": len(above4),
            "q4_locations": len(places4),
            "q3_rows": len(above3),
            "q3_locations": len(places3),
            "clearing_rows": len(clearing),
            "clearing_locations": len({c.location for c in clearing}),
            "thin": len({c.location for c in clearing}) < THIN,
        }
    return {
        "default": {"column": DEFAULT_COLUMN, "at": DEFAULT_BAR, "from": "solve.Q4_BAR"},
        "fallback": {
            "column": FALLBACK_COLUMN,
            "at": FALLBACK_BAR,
            "from": "floors.RELEASE_ADVISORY",
            "applies_below": FALLBACK_LOCATIONS,
        },
        "provisional": (
            "candidate-column bars, both of them flags. Nothing here re-scores at shipping "
            "geometry and no crossover fitted at label geometry is transported onto this "
            "column. The one ACTING release bar is P(>=3) >= "
            f"{floors.STRANGE_RELEASE_BAR.value} on strange_render, which is above the "
            "fallback used here."
        ),
        "on_default": [name for name in modes if out[name]["rule"] == DEFAULT_COLUMN],
        "on_fallback": [name for name in modes if out[name]["rule"] == FALLBACK_COLUMN],
        "still_thin": [name for name in modes if out[name]["thin"]],
        "off_roster": dict(sorted(off_roster.items())),
        "modes": out,
    }


def clearing(candidates, table: dict | None = None) -> list:
    """Every candidate that clears its own mode's bar. The census's whole population."""
    read = bars(candidates) if table is None else table
    keep = []
    for candidate in candidates:
        rule = (read["modes"].get(candidate.mode) or {}).get("rule")
        column = candidate.score if rule == DEFAULT_COLUMN else candidate.p_ge3
        bar = DEFAULT_BAR if rule == DEFAULT_COLUMN else FALLBACK_BAR
        if rule is not None and column >= bar:
            keep.append(candidate)
    return keep


# --------------------------------------------------------------------------- #
# The census.
# --------------------------------------------------------------------------- #
def _places(candidates) -> set:
    return {candidate.location for candidate in candidates}


def _row(
    *,
    about: str,
    kind: str,
    needs: int,
    members: list,
    costs: dict,
    renders: int,
    note: str = "",
) -> dict:
    """One constraint's line: what it needs, what the pool has, and what more costs."""
    places = _places(members)
    supply = len(places)
    win_rate = supply / renders if renders else 0.0
    per_win = None if not supply else round(renders / supply, 1)
    price = _mixed_cost(costs, members)
    return {
        "about": about,
        "kind": kind,
        "needs": int(needs),
        "supply": supply,
        "rows": len(members),
        "slack": supply - int(needs),
        "short": supply < int(needs),
        "thin": supply < THIN,
        "win_rate": round(win_rate, 6),
        "renders_per_win": per_win,
        "render_seconds": price,
        "seconds_per_win": None if per_win is None or price is None else round(per_win * price, 1),
        **({"note": note} if note else {}),
    }


def census(candidates, ladder=LADDER, costs: dict | None = None, log=print) -> dict:
    """The whole curve: every constraint at every `n` of `ladder`. No solver.

    Runs the bars once, restricts to the clearing population once, and then walks
    the ladder over counts already tallied — so the whole curve costs what one
    rung costs, which is why it is reported even though one rung is exercised.
    """
    costs = {} if costs is None else costs
    table = bars(candidates)
    kept = clearing(candidates, table)
    renders = len(candidates)
    log(f"[headroom] {len(kept):,} of {len(candidates):,} candidates clear their mode's bar")
    by_cell: dict = {}
    by_family: dict = {}
    by_mode: dict = {}
    by_group: dict = {}
    colourless: list = []
    renders_by_mode: dict = {}
    for candidate in candidates:
        renders_by_mode[candidate.mode] = renders_by_mode.get(candidate.mode, 0) + 1
    for candidate in kept:
        for cell in candidate.cells:
            by_cell.setdefault(cell, []).append(candidate)
        for family in candidate.families:
            by_family.setdefault(family, []).append(candidate)
        by_mode.setdefault(candidate.mode, []).append(candidate)
        by_group.setdefault(candidate.group, []).append(candidate)
        if not candidate.cells:
            colourless.append(candidate)
    rule = solve.rule_for()
    return {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reads": "necessary conditions only. A short row is provable infeasibility; a row "
        "with slack is NOT a claim that the selection is possible, jointly or at all",
        "bars": table,
        "population": {
            "candidates": len(candidates),
            "clearing": len(kept),
            "locations": len(_places(candidates)),
            "clearing_locations": len(_places(kept)),
            "dominant_in_no_cell": len(_places(colourless)),
            "cells_held": len(by_cell),
            "families_held": len(by_family),
            "modes_held": len(by_mode),
            "groups_held": len(by_group),
        },
        "render_cost": costs,
        "estimator": (
            "renders per win = every render on record / the distinct clearing locations "
            "satisfying the constraint; seconds per win = that times the median realized "
            "`hunt.seconds` of the modes that won, mixed as they won. UNCONDITIONED: it is "
            "the rate this project's whole render history happened to produce one at, not "
            "the rate an aimed leg gets. A mode row uses that mode's own renders and its "
            "own cost. Wall clock is a third of this — the render pool is three workers."
        ),
        "curve": {
            str(size): _at(
                size,
                kept=kept,
                rule=rule,
                costs=costs,
                renders=renders,
                by_cell=by_cell,
                by_family=by_family,
                by_mode=by_mode,
                by_group=by_group,
                colourless=colourless,
                renders_by_mode=renders_by_mode,
            )
            for size in ladder
        },
    }


def _at(
    n: int,
    *,
    kept,
    rule,
    costs,
    renders,
    by_cell,
    by_family,
    by_mode,
    by_group,
    colourless,
    renders_by_mode,
) -> dict:
    """Every block at one `n`."""
    from fractal_wallpapers import engine
    from fractal_wallpapers.palettes import dominance

    out: dict = {"n": n, "blocks": {}}
    out["blocks"]["one_per_location"] = {
        "kind": DEMAND,
        "needs": n,
        "supply": len(_places(kept)),
        "slack": len(_places(kept)) - n,
        "short": len(_places(kept)) < n,
        "rule": "hard, and the only hard rule in the seating",
        "rows": [],
    }
    out["blocks"]["colour_ceiling_cells"] = _cover(
        n,
        members=by_cell,
        axis=dominance.cells(),
        allowance=lambda name: rule.allowed(name, n),
        spare=colourless,
        costs=costs,
        renders=renders,
        what="cell",
    )
    out["blocks"]["colour_ceiling_families"] = _cover(
        n,
        members=by_family,
        axis=dominance.families(),
        allowance=lambda name: rule.allowed(name, n),
        spare=colourless,
        costs=costs,
        renders=renders,
        what="family",
    )
    out["blocks"]["palette_group_cap"] = _cover(
        n,
        members=by_group,
        axis=sorted(by_group),
        allowance=lambda _name: ceiling.GROUP_CAP,
        spare=[],
        costs=costs,
        renders=renders,
        what="palette group",
        flag_thin=False,
        note=(
            f"the TIGHT form of the cap. A second seat in one group is allowed when its "
            f"pixel cloud is more than {ceiling.TAU_GROUP} from every picture that group "
            "already seated, so the real condition is looser than this by however many "
            "exemptions the pixels grant — which is not knowable without decoding them"
        ),
    )
    modes = list(engine.production_modes())
    out["blocks"]["mode_floors"] = {
        "kind": DEMAND,
        "needs": solve.MODE_FLOOR * len(modes),
        "supply": sum(1 for name in modes if by_mode.get(name)),
        "slack": sum(1 for name in modes if by_mode.get(name)) - solve.MODE_FLOOR * len(modes),
        "short": sum(1 for name in modes if by_mode.get(name)) < solve.MODE_FLOOR * len(modes),
        "rule": f"soft in the solve; {solve.MODE_FLOOR} seat per production mode",
        # The one block whose block-level supply is not a count of locations: it
        # is how many modes can field anything at all, against how many seats the
        # floors ask for between them. The per-mode rows below are in locations
        # like every other row here.
        "supply_counts": "modes with at least one clearing location",
        "fits_in_n": solve.MODE_FLOOR * len(modes) <= n,
        "rows": [
            _row(
                about=name,
                kind=DEMAND,
                needs=solve.MODE_FLOOR,
                members=by_mode.get(name, []),
                costs=costs,
                renders=renders_by_mode.get(name, 0),
                note="renders per win is this mode's own rate: its clearing locations "
                "against every render on record in this mode",
            )
            for name in modes
        ],
        "empty": [name for name in modes if not by_mode.get(name)],
    }
    out["blocks"]["colour_targets"] = {
        "kind": DEMAND,
        "needs": 0,
        "supply": 0,
        "slack": 0,
        "short": False,
        "rule": "the DEFAULT target vector sets no explicit target. Every cell's rate is "
        f"the uniform {round(ceiling.CELL_SHARE, 6)} and every family's "
        f"{round(ceiling.FAMILY_SHARE, 6)}; an explicit `--target` is what makes this "
        "block non-empty, and this pass censuses the default only",
        "rows": [],
    }
    flagged = []
    for name, block in out["blocks"].items():
        if block.get("short"):
            flagged.append({"block": name, "about": "-", "supply": block["supply"]})
        for row in block.get("rows", []):
            if row["short"] or (row["thin"] and block.get("flag_thin", True)):
                flagged.append(
                    {
                        "block": name,
                        "about": row["about"],
                        "supply": row["supply"],
                        "short": row["short"],
                        "thin": row["thin"],
                        "seconds_per_win": row["seconds_per_win"],
                    }
                )
    flagged.sort(key=lambda item: (item["supply"], item["block"], item["about"]))
    out["flagged"] = flagged
    return out


def _cover(
    n: int,
    *,
    members: dict,
    axis,
    allowance,
    spare,
    costs,
    renders,
    what: str,
    flag_thin: bool = True,
    note: str = "",
) -> dict:
    """A block of caps, plus the covering condition they imply together.

    A cap on its own can never be infeasible — nothing is forced to use it. What
    *is* a necessary condition is that the caps between them can hold `n` seats:
    every seat is dominant in at least one member of the axis or in none of it, so

    ```text
    n <= sum over the axis of min(its allowance, its distinct locations)
         + the locations dominant in nothing on the axis
    ```

    and a pool that fails it cannot fill `n` seats however they are ordered. It is
    a bound and not a construction: a location dominant in three cells is counted
    in all three, so the sum is an over-count and the condition is only ever a
    necessary one. That is the direction that makes it safe.
    """
    rows = []
    usable = 0
    for name in axis:
        mine = members.get(name, [])
        cap = int(allowance(name))
        row = _row(
            about=name,
            kind=CAP,
            needs=cap,
            members=mine,
            costs=costs,
            renders=renders,
            note=note,
        )
        row["cap"] = cap
        row["usable"] = min(cap, row["supply"])
        # A cap cannot be short of its own allowance in the sense a demand can:
        # nothing makes a gallery use it. `short` on these rows means "this cell
        # cannot fill its own allowance", which is the flag a mine reads.
        usable += row["usable"]
        rows.append(row)
    spare_places = len(_places(spare))
    supply = usable + spare_places
    rows.sort(key=lambda row: (row["supply"], row["about"]))
    return {
        "kind": COVER,
        "needs": n,
        "supply": supply,
        "slack": supply - n,
        "short": supply < n,
        "usable_from_the_axis": usable,
        "dominant_in_none": spare_places,
        "rule": f"n <= sum over the axis of min(allowance, distinct locations) + the "
        f"locations dominant in no {what}. An over-count, so it is necessary and never "
        "sufficient",
        "empty": [row["about"] for row in rows if not row["supply"]],
        # An axis whose cap is one member is thin by construction — 752 palette
        # groups mostly hold a handful of places each and always will — so the
        # THIN flag is not raised on it. The rows still carry their own `thin`;
        # what is switched off is calling it a finding.
        "flag_thin": bool(flag_thin),
        "rows": rows,
        **({"note": note} if note else {}),
    }


def write_record(name: str, record: dict):
    """The census as JSON, under the regenerable tree."""
    import json

    from fractal_wallpapers.paths import under

    path = under("curation", UNIT, str(name)) / "census.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


__all__ = [
    "CAP",
    "COVER",
    "DEFAULT_BAR",
    "DEFAULT_COLUMN",
    "DEMAND",
    "FALLBACK_BAR",
    "FALLBACK_COLUMN",
    "FALLBACK_LOCATIONS",
    "LADDER",
    "SCHEMA",
    "THIN",
    "UNIT",
    "HeadroomError",
    "bars",
    "census",
    "clearing",
    "population",
    "render_cost",
    "write_record",
]
