"""Seat a gallery off the ledger with a trivial greedy, and keep every refusal.

The other half of [`curation.headroom`]. A census is an upper bound — it says what
could not possibly be seated. This is a **lower bound**: the simplest rule that
fills seats, run so that the gap between the two is visible. Close together and
the answer is known; far apart and that gap is the size of the prize an exact
solve is competing for, which is usually the signal to go and make more candidates
instead.

It only chooses. It proposes nothing, renders nothing, and opens no picture: every
reading it needs — the colour, the palette group, the mode, the score — is already
on the ledger row, so a [`ceiling.Lens`] here is a **lookup** and never a second
derivation. Nothing here re-decodes a JPEG to be told what the row already says.

## Fill by scarcity, not by score

Ordering by score alone converts satisfiable problems into apparent infeasibility.
At `n = 20` the mode floors alone ask for eighteen of the twenty seats, and eleven
of those eighteen modes can field only a handful of places between them — so a
walk down the ranked list spends its first seats on `smooth` and `exp_smoothing`,
which have thousands of candidates each, and then reports that fifteen modes could
not be seated. Every one of them could have been.

So the mandated constraints are seated **from their own subpools first, scarcest
first**, and only what is left over is drawn from the general pool by score. The
order is a fact about supply and not a preference: a mode with three eligible
places is seated before a mode with eight hundred because the three can only be
spent one way.

## One rule is hard and every other is soft

**One wallpaper per location** is absolute — it is the identity of the thing being
chosen, not a preference about it. Everything else records a shortfall and carries
on: the cell and family allowances, the mode floors, the palette-group cap. There
is no fallback leg, no least-violating rescue and no padding. An unfilled seat is
the honest output, and it is the number the census is a bound on.

The pairwise diversity radius is deliberately **not** here, and after
[`curation.distinct`]'s premise check that is a gap rather than a design. Moving
it to pool construction over the neutral descriptors was the plan; the measurement
says the two metrics are near-orthogonal, so nothing in a neutral pre-filter
substitutes for it. Until the rule is placed somewhere a seating from this module
is a lower bound on a program **without** it — measured at n=20, the twenty seated
hold no pair under [`ceiling.TAU`] and two under [`solve.RADIUS`] — and the record
says so rather than leaving a reader to assume the rule was applied.

## A greedy shortfall is not infeasibility

Every unseated candidate is recorded with the rule that refused it, aggregated by
cell, family, mode and partition, and that aggregate is the product — it is the
"what do we make next" answer. But a shortfall here means *this greedy did not find
it* and never *the pool does not hold it*. The only infeasibility claims this
project makes are [`curation.headroom`]'s necessary conditions, and the record
carries both so the two are read together.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fractal_wallpapers.curation import candidate_ledger, ceiling, headroom, solve

#: The schema every record this module writes carries.
SCHEMA = 1

#: The subtree a seating's record and its sheet land in.
UNIT = "seat"

#: How many of the refused the contact sheet shows beside the seated, per rule.
#: Enough that a rule's refusals are a sample rather than an anecdote, few enough
#: that the page is one page.
SHOWN = 6

#: The rules, in the order the greedy applies them. The first to fail names the
#: refusal, which is what makes the rejection ledger a partition of the pool
#: rather than a tally that double-counts.
#:
#: `location` is hard. The three after it are soft: a candidate that fails one is
#: passed over while a seat is still being chosen, and the shortfall is recorded —
#: but nothing is ever seated by relaxing a rule it failed, so a soft rule that
#: nothing can satisfy leaves the seat empty.
RULES = ("location", "group_cap", "cell_allowance", "family_allowance")

#: What a candidate that broke no rule and simply lost is recorded as. It is a far
#: weaker statement than any of [`RULES`] and is kept apart for that reason: a
#: mine aimed at this population would be aimed at nothing.
UNSEATED = "the_greedy_had_no_seat_left"

#: What a candidate below its own mode's bar is recorded as. Not a refusal by any
#: selection rule — it never entered the population the seating chooses from.
BELOW_BAR = "below_its_mode_bar"


class SeatingRefused(RuntimeError):
    """The seating cannot be run."""


# --------------------------------------------------------------------------- #
# The lens, off the rows.
# --------------------------------------------------------------------------- #
def lens_for(rows=None) -> ceiling.Lens:
    """A [`ceiling.Lens`] that reads the ledger and never a picture.

    [`ceiling.Lens.reading`] decodes a JPEG unless it is handed a `stored_of`, and
    every ledger row already carries the reading in its `colour` block — so a
    seating driven off the ledger would otherwise spend a decode per candidate to
    be told what the row says. [`candidate_ledger.reading_source`] is that lookup,
    built over the whole store once however many candidates are tested.

    The pixel-cloud half is left unwired on purpose: nothing in this seating is a
    pairwise rule, so a cloud would be half a mebibyte made to answer no question.
    A caller that wants the twin check as a **residual** over the small surviving
    set builds a lens with a real `render_of` and pays for the survivors only.
    """
    return ceiling.Lens(
        render_of=lambda candidate: None,
        group_of=lambda candidate: str(candidate.get("palette_group")),
        stored_of=candidate_ledger.reading_source(rows),
    )


# --------------------------------------------------------------------------- #
# The seating.
# --------------------------------------------------------------------------- #
class Seats:
    """What has been seated, and the three soft tests read off it.

    Holds counts and never pictures. Each test answers "would seating this break
    the rule", so the caller can ask before it commits and record the answer when
    it does not.
    """

    def __init__(self, rule: ceiling.Rule, n: int):
        self.rule = rule
        self.n = int(n)
        self.chosen: list = []
        self.places: set = set()
        self.cells: dict = {}
        self.families: dict = {}
        self.groups: dict = {}
        self.modes: dict = {}
        #: `{rule: how many times it was the reason}`, over every candidate tested.
        self.refusals: dict = {name: 0 for name in RULES}

    def refuses(self, candidate) -> str | None:
        """The first rule this candidate fails, or `None`. [`RULES`] order."""
        if candidate.location in self.places:
            return "location"
        if self.groups.get(candidate.group, 0) >= self.rule.group_cap:
            return "group_cap"
        for cell in candidate.cells:
            if self.cells.get(cell, 0) + 1 > self.rule.allowed(cell, self.n):
                return "cell_allowance"
        for family in candidate.families:
            if self.families.get(family, 0) + 1 > self.rule.allowed(family, self.n):
                return "family_allowance"
        return None

    def seat(self, candidate, why: str) -> dict:
        """Seat one candidate. The caller has already asked [`refuses`]."""
        self.chosen.append((candidate, why))
        self.places.add(candidate.location)
        self.groups[candidate.group] = self.groups.get(candidate.group, 0) + 1
        self.modes[candidate.mode] = self.modes.get(candidate.mode, 0) + 1
        for cell in candidate.cells:
            self.cells[cell] = self.cells.get(cell, 0) + 1
        for family in candidate.families:
            self.families[family] = self.families.get(family, 0) + 1
        return {"key": candidate.key, "seated_for": why}

    @property
    def full(self) -> bool:
        return len(self.chosen) >= self.n


def scarcity(kept, modes) -> list:
    """The mandated constraints, scarcest first. `[(mode, its subpool)]`.

    The only mandate the **default** target vector produces is the mode floor:
    every production mode wants one seat, and no colour cell is demanded because
    no `--target` is set. So the order is by how many distinct locations each mode
    can field, ascending — a mode with three is spent before a mode with eight
    hundred, because the three can only be spent one way.

    A mode with nothing at all is kept in the list rather than dropped, so the
    record says it was asked for and could not be met.
    """
    by_mode: dict = {name: [] for name in modes}
    for candidate in kept:
        if candidate.mode in by_mode:
            by_mode[candidate.mode].append(candidate)
    ranked = sorted(
        by_mode.items(),
        key=lambda item: (len({c.location for c in item[1]}), item[0]),
    )
    return [(name, sorted(members, key=lambda c: (-c.score, c.key))) for name, members in ranked]


def seat(
    candidates,
    n: int = candidate_ledger.FIRST_SOLVE,
    rule: ceiling.Rule | None = None,
    log=print,
) -> dict:
    """Fill `n` seats by scarcity then by score, and keep every refusal.

    Two legs over one [`Seats`]. The first walks the mandated constraints in
    scarcity order and takes each one's best candidate that nothing refuses; the
    second walks whatever is left of the ranked pool. A candidate refused in the
    first leg is offered again in the second, because the state it was refused
    against has moved on.
    """
    from fractal_wallpapers import engine

    modes = list(engine.production_modes())
    rule = solve.rule_for() if rule is None else rule
    table = headroom.bars(candidates)
    kept = headroom.clearing(candidates, table)
    kept.sort(key=lambda candidate: (-candidate.score, candidate.key))
    seats = Seats(rule, n)
    #: `{key: the rule that refused it, the last time it was offered}`.
    refused: dict = {}
    log(f"[seat] {len(kept):,} of {len(candidates):,} candidates clear their mode's bar")

    mandated = scarcity(kept, modes)
    picked: set = set()
    for mode, members in mandated:
        if seats.full:
            break
        if seats.modes.get(mode, 0) >= solve.MODE_FLOOR:
            continue
        for candidate in members:
            why = seats.refuses(candidate)
            if why is None:
                seats.seat(candidate, f"mode_floor:{mode}")
                picked.add(candidate.key)
                refused.pop(candidate.key, None)
                break
            refused[candidate.key] = why
            seats.refusals[why] += 1

    for candidate in kept:
        if seats.full:
            break
        if candidate.key in picked:
            continue
        why = seats.refuses(candidate)
        if why is None:
            seats.seat(candidate, "general_pool")
            picked.add(candidate.key)
            refused.pop(candidate.key, None)
        else:
            refused[candidate.key] = why
            seats.refusals[why] += 1

    # Everything the walk never reached, because the seats ran out. Recorded as
    # its own thing and never as a refusal: no rule acted on it.
    for candidate in kept:
        if candidate.key not in picked and candidate.key not in refused:
            refused[candidate.key] = UNSEATED
    for candidate in candidates:
        if candidate.key not in picked and candidate.key not in refused:
            refused[candidate.key] = BELOW_BAR

    record = {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "config": _config(n, rule, modes, table),
        "population": {
            "candidates": len(candidates),
            "clearing": len(kept),
            "locations": len({c.location for c in candidates}),
            "clearing_locations": len({c.location for c in kept}),
        },
        "filled": len(seats.chosen),
        "unfilled": n - len(seats.chosen),
        "seated": [_seated(candidate, why) for candidate, why in seats.chosen],
        "shortfalls": _shortfalls(seats, rule, modes, n),
        "rejection": rejection(candidates, refused, log=log),
        "samples": samples(candidates, refused),
    }
    log(
        f"[seat] {record['filled']} of {n} seat(s); "
        f"{record['shortfalls']['modes']['missing_count']} mode(s) unseated"
    )
    return record


def _config(n: int, rule: ceiling.Rule, modes: list, table: dict) -> dict:
    return {
        "n": n,
        "hard": ["one wallpaper per location"],
        "soft": [
            "the palette group cap",
            "the per-cell allowance",
            "the per-family allowance",
            "the mode floors",
        ],
        "order": "the mandated constraints from their own subpools, scarcest first; then "
        "the general pool by score",
        "rules": list(RULES),
        "no_fallback": "nothing is seated by relaxing a rule it failed, and no seat is "
        "padded. Unfilled beats padded",
        "pairwise": "NOT applied, and nothing here reads a pixel cloud. Moving the "
        "diversity radius to pool construction over the neutral descriptors was the plan; "
        "the premise check refutes it (6,720 twin pairs at a median neutral distance of "
        "0.226, a radius of 0.10 removing 413 of them), so the rule is unplaced and these "
        "seats are a bound on a program WITHOUT it",
        "bars": {name: block["rule"] for name, block in sorted(table["modes"].items())},
        "ceiling": {
            "k": rule.k,
            "cell_share": ceiling.CELL_SHARE,
            "family_share": ceiling.FAMILY_SHARE,
            "allowance": "floor(k * t * n) + 1",
            "group_cap": rule.group_cap,
            "tau_group": rule.tau_group,
            "targets": dict(sorted(rule.targets.items())),
        },
        "mode_floor": solve.MODE_FLOOR,
        "modes": modes,
    }


def _seated(candidate, why: str) -> dict:
    return {
        "key": candidate.key,
        "seated_for": why,
        "location": candidate.location,
        "partition": candidate.partition,
        "mode": candidate.mode,
        "kind": candidate.kind,
        "palette_group": candidate.group,
        "cells": list(candidate.cells),
        "families": list(candidate.families),
        "p_ge4": round(candidate.score, 6),
        "p_ge3": round(candidate.p_ge3, 6),
        "picture": candidate.picture,
    }


def _shortfalls(seats: Seats, rule: ceiling.Rule, modes: list, n: int) -> dict:
    """Every soft rule's shortfall, recorded rather than repaired."""
    missing = [name for name in modes if seats.modes.get(name, 0) < solve.MODE_FLOOR]
    return {
        "seats": {"asked": n, "filled": len(seats.chosen), "unfilled": n - len(seats.chosen)},
        "modes": {
            "floor": solve.MODE_FLOOR,
            "held": len(modes) - len(missing),
            "of": len(modes),
            "missing": missing,
            "missing_count": len(missing),
            "counts": dict(sorted(seats.modes.items(), key=lambda item: -item[1])),
        },
        "cells": {
            "held": len(seats.cells),
            "over_allowance": {
                cell: count
                for cell, count in sorted(seats.cells.items())
                if count > rule.allowed(cell, n)
            },
            "counts": dict(sorted(seats.cells.items(), key=lambda item: -item[1])),
        },
        "families": {
            "held": len(seats.families),
            "over_allowance": {
                family: count
                for family, count in sorted(seats.families.items())
                if count > rule.allowed(family, n)
            },
            "counts": dict(sorted(seats.families.items(), key=lambda item: -item[1])),
        },
        "groups": {
            "held": len(seats.groups),
            "cap": rule.group_cap,
            "over_cap": {
                group: count
                for group, count in sorted(seats.groups.items())
                if count > rule.group_cap
            },
        },
        "refusals_while_seating": dict(sorted(seats.refusals.items(), key=lambda i: -i[1])),
        "read": "a greedy shortfall is `this walk did not find it`, never `the pool does "
        "not hold it`. The only infeasibility claims are the census's necessary conditions",
    }


# --------------------------------------------------------------------------- #
# The rejection ledger — the product.
# --------------------------------------------------------------------------- #
def rejection(candidates, refused: dict, log=print) -> dict:
    """For every candidate not seated, which rule killed it, aggregated four ways.

    By cell, by family, by mode and by partition, because those are the four axes
    a leg can be aimed down. A cell whose whole refusal column is `cell_allowance`
    is a cell the gallery is already full of; one whose column is `location` is a
    cell that exists only at places something else already took, and the answer to
    those two is not the same answer.

    Aggregated over **distinct locations** as well as rows, for the reason every
    count in this pair of modules is: a rule that refused four hundred rows at
    twelve places refused twelve wallpapers.
    """
    axes = {
        "cells": lambda candidate: candidate.cells,
        "families": lambda candidate: candidate.families,
        "modes": lambda candidate: (candidate.mode,),
        "partitions": lambda candidate: (candidate.partition,),
    }
    rows: dict = {name: {} for name in axes}
    places: dict = {name: {} for name in axes}
    overall: dict = {}
    for candidate in candidates:
        why = refused.get(candidate.key)
        if why is None:
            continue
        overall[why] = overall.get(why, 0) + 1
        for axis, values_of in axes.items():
            for value in values_of(candidate):
                rows[axis].setdefault(value, {}).setdefault(why, 0)
                rows[axis][value][why] += 1
                places[axis].setdefault(value, {}).setdefault(why, set()).add(candidate.location)
    log(f"[seat] {sum(overall.values()):,} candidates refused; {dict(sorted(overall.items()))}")
    return {
        "reasons": dict(sorted(overall.items(), key=lambda item: -item[1])),
        "by": {
            axis: {
                str(value): {
                    "rows": dict(sorted(reasons.items(), key=lambda item: -item[1])),
                    "locations": {
                        why: len(keys)
                        for why, keys in sorted(
                            places[axis][value].items(), key=lambda item: -len(item[1])
                        )
                    },
                }
                for value, reasons in sorted(rows[axis].items())
            }
            for axis in axes
        },
        "read": "the rule that refused each candidate the LAST time it was offered, in "
        f"{list(RULES)} order. `{UNSEATED}` broke no rule and simply arrived after the "
        f"seats ran out; `{BELOW_BAR}` never entered the population at all",
    }


def samples(candidates, refused: dict, count: int = SHOWN) -> dict:
    """`{rule: the strongest few it refused}` — the visual half of the ledger.

    Strongest first inside each rule, because a refusal of a weak candidate says
    nothing: the question a sheet answers is whether the rule is throwing away
    pictures a person would have kept.
    """
    held: dict = {}
    for candidate in sorted(candidates, key=lambda c: (-c.score, c.key)):
        why = refused.get(candidate.key)
        if why is None:
            continue
        mine = held.setdefault(why, [])
        if len(mine) < int(count):
            mine.append(_seated(candidate, why))
    return held


# --------------------------------------------------------------------------- #
# Where it lands.
# --------------------------------------------------------------------------- #
def seat_dir(name: str):
    from fractal_wallpapers.paths import under

    return under("curation", UNIT, str(name))


def write_record(name: str, record: dict):
    import json

    path = seat_dir(name) / "seat.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def contact_sheet(name: str, record: dict, rejected=None, output=None):
    """The seated, and a sample of the refused with the rule that refused each.

    Both halves for [`solve.contact_sheet`]'s reason: a gallery on its own says
    only what the rule liked. A refusal captioned with the rule that made it is
    the thing a person can disagree with — and here the captions are the *product*,
    because a column of `cell_allowance` and a column of `location` are two
    different instructions to whatever makes candidates next.
    """
    import html
    from pathlib import Path

    from fractal_wallpapers.curation import sheet as sheet_module
    from fractal_wallpapers.paths import rehome

    output = seat_dir(name) / "contact_sheet.html" if output is None else Path(output)
    config = record["config"]
    shortfalls = record["shortfalls"]

    def card(row: dict, caption: str) -> str:
        picture = row.get("picture")
        source = None if not picture else Path(rehome(picture))
        body = (
            f'<img src="{sheet_module.thumbnail(source)}" alt="">'
            if source is not None and source.is_file()
            else '<div class="missing">no picture on disk</div>'
        )
        facts = [
            f"mode <b>{html.escape(str(row.get('mode')))}</b>",
            f"P(&ge;4) {row.get('p_ge4')} &middot; P(&ge;3) {row.get('p_ge3')}",
            f"cells {html.escape(', '.join(row.get('cells') or []) or 'none')}",
            f"group {html.escape(str(row.get('palette_group')))}",
            f"partition {html.escape(str(row.get('partition')))}",
        ]
        return (
            f"<figure><div class='frame'>{body}</div><figcaption>"
            f"<b>{html.escape(caption)}</b><ul>"
            + "".join(f"<li>{fact}</li>" for fact in facts)
            + "</ul></figcaption></figure>"
        )

    lines = [
        "<!doctype html><meta charset='utf-8'>",
        f"<title>seat {html.escape(name)}</title>",
        f"<style>{sheet_module.STYLE}</style>",
        f"<h1>seat {html.escape(name)}</h1>",
        f"<p class='lede'>{record['filled']} of {config['n']} seat(s) filled from "
        f"{record['population']['clearing']:,} clearing candidates over "
        f"{record['population']['clearing_locations']:,} locations. "
        f"{shortfalls['modes']['held']} of {shortfalls['modes']['of']} modes held. "
        "A greedy: fill by scarcity, then by score. Nothing here is optimal and a "
        "shortfall is not infeasibility.</p>",
        f"<h2>Seated ({record['filled']})</h2>",
        "<div class='grid'>"
        + "".join(
            card(row, f"{row['seated_for']} — {row['mode']}") for row in record.get("seated") or []
        )
        + "</div>",
    ]
    for why, sample in sorted((rejected or {}).items()):
        if not sample:
            continue
        lines += [
            f"<h2>Refused by <code>{html.escape(why)}</code> ({len(sample)} shown)</h2>",
            "<div class='grid'>" + "".join(card(row, why) for row in sample) + "</div>",
        ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return output


__all__ = [
    "BELOW_BAR",
    "RULES",
    "SCHEMA",
    "SHOWN",
    "UNIT",
    "UNSEATED",
    "SeatingRefused",
    "Seats",
    "contact_sheet",
    "lens_for",
    "rejection",
    "samples",
    "scarcity",
    "seat",
    "seat_dir",
    "write_record",
]
