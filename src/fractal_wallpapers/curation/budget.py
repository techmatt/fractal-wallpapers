"""How many pictures to make, and for whom — budgeted from what the release needs.

The direction of causation is the whole module: **the release budgets the
colorize**, never the other way round. Each of the two finished-render judges is
asked to fill some number of release slots; its attempt budget is
[`floors.ATTEMPT_MULTIPLIER`] times *that*, and the two heads are sized against
their own need rather than against each other.

The failure this replaces is worth naming, because it is invisible in every
report it produces. When colorize volume falls out of a spread over render styles
— one smooth style against fifteen strange ones — the smooth head draws about a
sixteenth of the attempts no matter how many smooth slots the release asked for.
The source project measured it: three smooth candidates out of thirty attempts
against six smooth slots, three of them short-filled, off a supply that held
hundreds of smooth-capable locations. A release starved by an allocation rule
that had no opinion about the release.

## Three levels, in order

1. **Head first.** `attempts = multiplier × that head's slots`. When the total
   budget cannot cover both at full multiple, **both scale down proportionally** —
   never one head starved to keep the other whole, which is the same failure one
   level up. Proportionally and not evenly: an even split levels the head with the
   larger need down to the other, and would be invisible in any run where the two
   happen to ask for the same number.
2. **Partition second, off the seated slots.** Within a head, each partition gets
   the multiple of the slots it is *planned to seat* — the same apportionment the
   release itself will make, made early. Budgeting off the bare mix instead is
   blind to the guarantee: at small `n` the mix zeroes exactly the partitions the
   guarantee exists to seat, so a partition certain to be asked for a picture
   would be budgeted none to find one with.
3. **Rank third.** A partition's attempts are filled in intake rank order, best
   first. A partition with fewer floor-passing locations than attempts short-fills
   and **says so**, which is the whole reason planned is recorded beside realized:
   a thin release is then attributable to supply or to budget at a glance.

## The order of the plan is itself a decision

The attempts come out in largest-deficit order over the `(head, partition)` cells,
so **every prefix** is near-proportional. A run stopped half way through — by a
clock, by a person, by a failure — has spent its half in the planned mix rather
than in whatever order the cells happened to be built in. A colorize loop is a
truncating consumer by construction, and the prefix property is the only one that
survives truncation.
"""

from __future__ import annotations

from dataclasses import dataclass

from fractal_wallpapers.curation import floors
from fractal_wallpapers.supply import apportion

#: The two finished-render judges, in the spelling every record uses. Declared
#: here because this module allocates *between* them, and a misspelled head is a
#: budget that silently goes nowhere.
SMOOTH, STRANGE = "smooth_render", "strange_render"
HEADS = (SMOOTH, STRANGE)


@dataclass(frozen=True)
class Attempt:
    """One planned colorize: a location, and the head whose slots paid for it.

    `head` fixes the **set of modes** the attempt may draw from — the smooth judge
    owns the one smooth coloring, the strange judge owns every other — and does
    not fix the mode. `rank` is the location's position in its partition's ranked
    offer, carried so the realized log can say how deep the budget reached
    without re-deriving the ranking.
    """

    head: str
    partition: str
    key: str
    rank: int


def head_slots(n: int, strange_share: float) -> dict:
    """`{head: release slots}` — the split the attempt budget is sized against.

    The same arithmetic the selection spends, read from here so the two cannot
    disagree about how many slots a head is filling. That disagreement is not
    hypothetical: a budget sized against a different `n` than the selection
    spends is exactly a short-fill nobody can attribute.
    """
    n = max(0, int(n))
    strange = max(0, min(n, int(round(n * float(strange_share)))))
    return {SMOOTH: n - strange, STRANGE: strange}


def scale_to_budget(want: dict, budget: int) -> dict:
    """`want` truncated to `budget`, proportionally. Unchanged when it fits."""
    budget = max(0, int(budget))
    total = sum(int(v) for v in want.values())
    if budget >= total:
        return {k: int(v) for k, v in want.items()}
    out = dict.fromkeys(want, 0)
    for key in apportion.sequence_by_deficit({k: int(v) for k, v in sorted(want.items())}, budget):
        out[key] += 1
    return out


def head_attempts(slots: dict, budget: int | None, multiplier: int | None = None) -> tuple:
    """`(attempts, record)` — the per-head budget, sized against release need.

    `budget` of `None` means uncapped, which is the honest default: the multiple
    *is* the budget unless somebody asked for a smaller run. The record carries
    the want beside the grant, because "the smooth judge got fifteen" and "the
    smooth judge got fifteen because the run was capped at thirty" are different
    facts and only the second one explains a short-fill.
    """
    multiplier = floors.ATTEMPT_MULTIPLIER if multiplier is None else int(multiplier)
    want = {head: max(0, multiplier * int(slots.get(head, 0))) for head in HEADS}
    granted = want if budget is None else scale_to_budget(want, budget)
    return granted, {
        "attempt_multiplier": multiplier,
        "attempt_budget": budget,
        "head_slots": {head: int(slots.get(head, 0)) for head in HEADS},
        "head_want": want,
        "scaled_to_budget": granted != want,
    }


def assign_guarantees(guarantees, slots: dict) -> tuple[dict, list[str]]:
    """`(owed, unplaced)` — which head pays each guaranteed partition its slot.

    The guarantee is one slot across the *whole* release and the two heads are
    planned separately, so somebody has to decide who pays. The key is *fewer
    guarantees placed so far*, so the two heads' mixes are eroded evenly instead
    of one head paying for every one of them, then the head name so the answer is
    a pure function of its inputs.

    A partition no head has room for comes back in `unplaced` rather than raising.
    A budget that aborted here would replace a message the selection can make
    precisely — it knows the candidate counts — with a worse one, and the shortfall
    is recorded either way.
    """
    owed: dict[str, str] = {}
    unplaced: list[str] = []
    placed = dict.fromkeys(HEADS, 0)
    for partition in sorted(set(guarantees)):
        room = [head for head in HEADS if placed[head] < int(slots.get(head, 0))]
        if not room:
            unplaced.append(partition)
            continue
        head = min(room, key=lambda h: (placed[h], h))
        owed[partition] = head
        placed[head] += 1
    return owed, unplaced


def partition_attempts(seated: dict, budget: int, multiplier: int | None = None) -> dict:
    """`{partition: attempts}` — the multiple of each partition's **seated** slots.

    Off the seated slots and not off the mix, and the two are not the same thing
    in the one place it matters. The mix is blind to the guarantee, so at small
    `n` it hands nothing to exactly the partitions that are certain to be asked
    for a picture. Apportioning `4n` directly is also finer-grained than
    apportioning `n` and multiplying, so a partition seated two slots can come out
    budgeted seven attempts where the rule promises eight — the head total is
    right and the per-partition split is not, which is invisible in a banner.

    A supplied partition seated nothing gets no attempts. That is the rule
    stating itself: attempts are budgeted from release need, and a partition with
    no slot has none.
    """
    multiplier = floors.ATTEMPT_MULTIPLIER if multiplier is None else int(multiplier)
    want = {p: max(0, multiplier * int(k)) for p, k in sorted(seated.items())}
    total = sum(want.values())
    budget = max(0, int(budget))
    if total <= budget:
        return want
    out = dict.fromkeys(want, 0)
    for partition in apportion.sequence_by_deficit(want, budget):
        out[partition] += 1
    return out


def plan(
    offer: dict,
    n: int,
    strange_share: float,
    budget: int | None = None,
    guarantees=(),
    multiplier: int | None = None,
) -> tuple[list[Attempt], dict]:
    """`(attempts, record)` — the whole plan, and the record that explains it.

    `offer` is intake's ranked offer, `{partition: [row, ...]}` best first and
    already floor-passing. A partition with an empty offer is not in the supply
    set and gets nothing.

    Realized fills are deliberately **not** here. They are derived from the
    candidate log after the run, because a plan that reports its own execution is
    a hardcoded success waiting to happen: a resumed run, a failed render and a
    location the modes had nothing to offer all diverge from the plan, and only
    the log knows which.
    """
    supply = {p: list(rows) for p, rows in offer.items() if rows}
    slots = head_slots(n, strange_share)
    granted, record = head_attempts(slots, budget, multiplier)
    claims = [p for p in sorted(set(guarantees or ())) if p in supply]
    owed, unplaced = assign_guarantees(claims, slots)

    planned: dict = {}
    short: dict = {}
    cells: dict = {}
    seated: dict = {}
    for head in HEADS:
        mine = {p for p, h in owed.items() if h == head}
        seated[head] = intake_slots(supply, slots[head], mine)
        per_partition = partition_attempts(seated[head], granted[head], multiplier)
        planned[head] = {p: int(k) for p, k in sorted(per_partition.items())}
        take = {p: min(int(k), len(supply.get(p, ()))) for p, k in per_partition.items()}
        short[head] = {p: per_partition[p] - t for p, t in take.items() if per_partition[p] > t}
        for partition, count in sorted(take.items()):
            if count > 0:
                cells[(head, partition)] = count

    order = apportion.sequence_by_deficit(dict(sorted(cells.items())), sum(cells.values()))
    cursor = dict.fromkeys(cells, 0)
    out: list[Attempt] = []
    for cell in order:
        head, partition = cell
        index = cursor[cell]
        cursor[cell] = index + 1
        out.append(
            Attempt(
                head=head,
                partition=partition,
                key=supply[partition][index]["key"],
                rank=index,
            )
        )

    record.update(
        {
            "head_attempts": {head: int(granted[head]) for head in HEADS},
            # The slot projection the attempts were sized against, and the
            # guarantee behind it: "this partition got four attempts" and "it got
            # four because it is guaranteed a slot the mix would not have given
            # it" are different facts, and only the second explains the plan.
            "seated_slots": {
                head: {p: int(k) for p, k in sorted(seated[head].items()) if k} for head in HEADS
            },
            "guaranteed": list(claims),
            "guarantee_head": dict(sorted(owed.items())),
            "guarantee_unplaced": list(unplaced),
            "planned_by_partition": planned,
            "planned": sum(sum(v.values()) for v in planned.values()),
            "supply_short_by_partition": {h: v for h, v in short.items() if v},
            "supply_short": sum(sum(v.values()) for v in short.values()),
            "scheduled": len(out),
            "supply_partitions": {p: len(rows) for p, rows in sorted(supply.items())},
            "prefix_deviation": round(
                apportion.prefix_deviation(order, dict(sorted(cells.items()))), 3
            ),
        }
    )
    return out, record


def intake_slots(supply: dict, n: int, guarantees=()) -> dict:
    """The slots one head is *projected* to seat — the release's own call, made early.

    A projection and not the allocation the release runs: the real one is solved
    again after the colorize, over the partitions that ended up with a scored
    candidate. This is the best estimate available before any picture exists, and
    it is exactly the estimate the attempts have to be sized against.
    """
    from fractal_wallpapers.curation import intake

    return intake.slots(supply.keys(), n, guarantees)


def realized(rows, partition_of=None) -> dict:
    """`{head: {partition: attempts}}`, derived from the candidate log.

    Derived rather than counted into the plan as it executes, for the reason the
    plan's own docstring gives: a record that reports its own execution outlives
    what it records.
    """
    out: dict = {head: {} for head in HEADS}
    for row in rows:
        head = row.get("head")
        partition = partition_of(row) if partition_of else row.get("partition")
        out.setdefault(head, {})
        out[head][partition] = out[head].get(partition, 0) + 1
    return {head: dict(sorted(v.items())) for head, v in out.items()}


def fill_lines(record: dict, realized_fills: dict) -> list[str]:
    """One line per head. The three numbers together are what makes a short-fill
    attributable: want above granted is the budget cap, granted above realized is
    supply or a failed render, and neither with a thin release is a bug.
    """
    lines = []
    for head in HEADS:
        want = (record.get("head_want") or {}).get(head, 0)
        granted = (record.get("head_attempts") or {}).get(head, 0)
        planned = (record.get("planned_by_partition") or {}).get(head, {})
        real = sum((realized_fills or {}).get(head, {}).values())
        line = (
            f"{head}: {record.get('attempt_multiplier')}x"
            f"{(record.get('head_slots') or {}).get(head, 0)} slots = {want} wanted, "
            f"{granted} budgeted, {sum(planned.values())} scheduled, {real} realized"
        )
        thin = (record.get("supply_short_by_partition") or {}).get(head) or {}
        if thin:
            line += f" · supply-short {thin}"
        lines.append(line)
    return lines


__all__ = [
    "HEADS",
    "SMOOTH",
    "STRANGE",
    "Attempt",
    "assign_guarantees",
    "fill_lines",
    "head_attempts",
    "head_slots",
    "intake_slots",
    "partition_attempts",
    "plan",
    "realized",
    "scale_to_budget",
]
