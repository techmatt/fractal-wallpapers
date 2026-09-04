"""What the pool already holds, over the axes a constraint acts on.

Read-only arithmetic over the rows: the population, the locations, the fill per
mode and colour cell, and [`feasibility`] — whether a solve at `n` can be
satisfied at all before anybody spends an hour finding out.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fractal_wallpapers.curation.candidate_ledger import store
from fractal_wallpapers.curation.candidate_ledger.store import (
    FIRST_SOLVE,
    SCHEMA,
    LedgerError,
)


def census(rows=None, n: int = FIRST_SOLVE, log=print) -> dict:
    """What the ledger holds, over the axes a constraint acts on. Decides nothing.

    Location x colour cell x mode x palette group, with the partition riding on
    the location because that is where it is already recorded. Every axis reports
    its fill **and its empties**: a solver's question is never how much material
    there is, it is which of its constraints has nothing to satisfy it with.
    """
    from fractal_wallpapers.curation import mode_policy
    from fractal_wallpapers.palettes import dominance

    stored = store.read() if rows is None else list(rows)
    if not stored:
        raise LedgerError(
            "the ledger is empty, so there is nothing to take a census over. Run "
            "`fractal-wallpapers curate candidate-ledger backfill` first."
        )
    log(f"[census] {len(stored):,} rows")
    return {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "population": _population(stored),
        "locations": _locations(stored),
        "cells": _fill(stored, dominance.cells(), _cells_of),
        "families": _fill(stored, dominance.families(), _families_of),
        # The mode a row COUNTS as, not the mode it was drawn in: a modulate whose
        # texture said nothing is the smooth field spent by rank bit for bit, and a
        # census that counted it as `itinerary` would be reporting a fill the
        # gallery cannot spend. See [`mode_policy.routed_mode`].
        "modes": _fill(stored, _production_modes(), lambda row: [mode_policy.routed_mode_of(row)]),
        "groups": _fill(
            stored, _drawable_groups(), lambda row: [(row["recipe"] or {})["palette_group"]]
        ),
        "feasibility": feasibility(stored, n=n, log=log),
    }


def _population(stored: list) -> dict:
    runs: dict = {}
    partitions: dict = {}
    for stamped in stored:
        run = str((stamped.get("provenance") or {}).get("run"))
        runs[run] = runs.get(run, 0) + 1
        partition = str(stamped.get("partition"))
        partitions[partition] = partitions.get(partition, 0) + 1
    return {
        "recipes": len(stored),
        "with_picture": sum(1 for stamped in stored if stamped.get("picture")),
        "recipe_only": sum(1 for stamped in stored if not stamped.get("picture")),
        "off_regime": sum(1 for stamped in stored if not stamped.get("at_candidate_regime")),
        # Rows whose modulate texture said nothing, so they are counted as
        # `smooth` on the modes axis above and seated on the smooth side.
        "texture_flat": sum(1 for stamped in stored if stamped.get("texture_flat")),
        "rejected": sum(1 for stamped in stored if stamped.get("rejected")),
        "no_colour": sum(1 for stamped in stored if not stamped.get("colour")),
        "duplicate_renders": sum(
            len((stamped.get("provenance") or {}).get("also_rendered") or []) for stamped in stored
        ),
        "by_run": dict(sorted(runs.items())),
        "by_partition": dict(sorted(partitions.items())),
    }


def _locations(stored: list) -> dict:
    """How many places the ledger stands on, and how deep it stands on each."""
    per: dict = {}
    per_partition: dict = {}
    for stamped in stored:
        key = str((stamped.get("location") or {}).get("key"))
        per[key] = per.get(key, 0) + 1
        per_partition.setdefault(str(stamped.get("partition")), set()).add(key)
    depths = sorted(per.values())
    moved = sum(1 for stamped in stored if not (stamped.get("location") or {}).get("agrees"))
    return {
        "locations": len(per),
        "recipes_per_location": _spread(depths),
        "at_one_recipe": sum(1 for depth in depths if depth == 1),
        "locations_by_partition": {name: len(keys) for name, keys in sorted(per_partition.items())},
        "rows_whose_key_is_not_their_frame": moved,
    }


def _spread(values: list) -> dict:
    """Min, the quartiles, p90 and max of an already-sorted list of counts."""
    if not values:
        return {}

    def at(share: float):
        return values[min(len(values) - 1, int(share * len(values)))]

    return {
        "min": values[0],
        "p25": at(0.25),
        "median": at(0.5),
        "p75": at(0.75),
        "p90": at(0.90),
        "max": values[-1],
        "mean": round(sum(values) / len(values), 2),
    }


def _cells_of(stored: dict) -> list:
    return list((stored.get("colour") or {}).get("cells") or [])


def _families_of(stored: dict) -> list:
    return list((stored.get("colour") or {}).get("families") or [])


def _fill(stored: list, axis, values_of) -> dict:
    """One axis: how many recipes and how many locations reach each of its values.

    Both counts, because they answer different questions. A cell fifty recipes
    carry at one location is a cell the one-wallpaper-per-location rule can only
    seat once, however many recipes stand behind it.
    """
    recipes_at = {name: 0 for name in axis}
    locations_at: dict = {name: set() for name in axis}
    unlisted: dict = {}
    none = 0
    for stamped in stored:
        values = values_of(stamped)
        if not values:
            none += 1
        for value in values:
            if value in recipes_at:
                recipes_at[value] += 1
                locations_at[value].add(str((stamped.get("location") or {}).get("key")))
            else:
                unlisted[value] = unlisted.get(value, 0) + 1
    ranked = sorted(recipes_at.items(), key=lambda item: (-item[1], item[0]))
    return {
        "axis": len(axis),
        "held": sum(1 for name in axis if recipes_at[name]),
        "empty": [name for name in axis if not recipes_at[name]],
        "recipes_carrying_none": none,
        "recipes": dict(ranked),
        "locations": {name: len(locations_at[name]) for name, _count in ranked},
        "not_on_the_axis": dict(sorted(unlisted.items())),
    }


def _production_modes() -> tuple:
    """Every mode a candidate row can be *in*, off the engine's own tiers.

    The census axis, and deliberately wider than [`_accepted_modes`]: a mode ruled
    niche keeps every row it ever made, and a census that stopped counting them
    would report the ledger shrinking on the day of a policy decision.
    """
    from fractal_wallpapers import engine

    return tuple(engine.production_modes())


def _accepted_modes() -> tuple:
    """Every mode a gallery may seat: what a mode floor is asked of."""
    from fractal_wallpapers.curation import mode_policy

    return tuple(mode_policy.accepted())


def _drawable_groups() -> tuple:
    """Every palette group the colorizer's pool can reach, through the group table.

    The pool is already one map per group — a pass records that as
    `palette_pool.collapsed` — so this is the pool's own size. Derived rather than
    assumed, because a group table that stopped collapsing would make the two
    differ and the census would go on reporting the wrong denominator.
    """
    from fractal_wallpapers.curation import colorize
    from fractal_wallpapers.palettes import groups as groups_module

    table = groups_module.member_groups()
    return tuple(sorted({groups_module.group_of(name, table) for name in colorize.pool(0)}))


def feasibility(stored: list, n: int = FIRST_SOLVE, log=print) -> dict:
    """Which of a trivial first solve's constraints could bind, on what we hold.

    Each entry says what the constraint needs, what the ledger offers, and whether
    the second is short of the first. Nothing here is a solve, and every entry
    says which kind of read it is: a constraint that cannot bind on the marginals
    can still bind jointly.
    """
    from fractal_wallpapers.curation import ceiling as ceiling_module
    from fractal_wallpapers.palettes import dominance

    locations = {str((row.get("location") or {}).get("key")) for row in stored}
    groups = {str((row.get("recipe") or {}).get("palette_group")) for row in stored}
    cell_allowance = int(ceiling_module.K * ceiling_module.CELL_SHARE * n) + 1
    family_allowance = int(ceiling_module.K * ceiling_module.FAMILY_SHARE * n) + 1
    cells_held = {name for row in stored for name in _cells_of(row)}
    families_held = {name for row in stored for name in _families_of(row)}
    colourless = sum(1 for row in stored if not _cells_of(row))
    return {
        "n": n,
        "one_wallpaper_per_location": {
            "needs": n,
            "holds": len(locations),
            "binds": len(locations) < n,
            "read": "marginal",
        },
        "distinct_places": _distinct_read(locations, n, log=log),
        "group_cap": {
            "cap": ceiling_module.GROUP_CAP,
            "needs": n,
            "holds": len(groups),
            "of_drawable": len(_drawable_groups()),
            "binds": len(groups) < n,
            "read": "marginal, and the loosest form of the cap: a second seat in a group "
            "is allowed when its pixel cloud is more than tau_group from every picture "
            "that group already seated",
        },
        "colour_ceiling": {
            "k": ceiling_module.K,
            "cell_allowance": cell_allowance,
            "family_allowance": family_allowance,
            "cells_held": len(cells_held),
            "cells_needed": -(-n // max(1, cell_allowance)),
            "families_held": len(families_held),
            "families_needed": -(-n // max(1, family_allowance)),
            "recipes_with_no_dominant_cell": colourless,
            "binds_on_cells": len(cells_held) < -(-n // max(1, cell_allowance)),
            "binds_on_families": len(families_held) < -(-n // max(1, family_allowance)),
            "note": "only a candidate DOMINANT in an over-allowance colour is refused, so "
            f"the {colourless:,} recipes dominant in no cell cannot be refused by it at all",
            "rule": dominance.RULE,
            "read": "marginal — the allowance is per seat and the walk is path-dependent",
        },
        "mode_floors": {
            "acts": "soft",
            # The floor is asked of the modes a gallery may seat, which is
            # [`curation.mode_policy.accepted`] and not the whole production
            # roster. The `modes` axis above stays at the full roster on purpose:
            # a niche mode keeps its rows and a census of the ledger counts them.
            "modes": len(_accepted_modes()),
            "modes_held": sum(1 for name in _accepted_modes() if _mode_count(stored, name)),
            "binds": False,
        },
    }


def _mode_count(stored: list, mode: str) -> int:
    return sum(1 for row in stored if (row.get("recipe") or {}).get("mode") == mode)


def _distinct_read(locations: set, n: int, log=print) -> dict:
    """Whether the ledger holds `n` places the pre-selection would call different.

    The rule itself and not an estimate: [`distinct.suppress`] at
    [`distinct.PRESELECT_RADIUS`] over the neutral descriptors, which is the walk
    a solve's pool is actually built through. It used to be the retired gallery
    pass's quality-weighted draw at its own wider radius, which asked about a rule
    nothing runs any more — a necessary condition has to be a condition of the
    program that will be solved.

    **The order is by key**, and that is a statement rather than a default. The
    walk keeps whichever of a near-cluster it is offered first, so an order
    changes *which* place survives but not how many do, and a census has no score
    to offer them by — it is a read over the whole ledger and a rank would have to
    pick a judge. [`distinct.preselect`] does have one and orders by it.
    """
    from fractal_wallpapers.curation import distinct, embeddings

    stored = embeddings.read()
    if not stored:
        return {
            "radius": distinct.PRESELECT_RADIUS,
            "embedded": 0,
            "read": "no embedding store",
        }
    embedded = {str(row["key"]) for row in stored}
    log(f"[census] {len(locations & embedded):,}/{len(locations):,} ledger locations are embedded")
    walk = distinct.suppress(sorted(locations), rows=stored)
    return {
        "radius": distinct.PRESELECT_RADIUS,
        "metric": distinct.METRIC,
        "embedded": len(locations & embedded),
        "unembedded": len(walk["unembedded"]),
        "needs": n,
        "distinct": len(walk["kept"]),
        "binds": len(walk["kept"]) < n,
        "refused_as_the_same_place": len(walk["refused"]),
        "read": "the pre-selection itself, over the ledger's places in key order",
    }
