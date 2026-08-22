"""Which candidates take the release's slots. One rule, three caps, and one bar.

Top-N by the judge's own score, per partition, under three limits: the partition's
slot allocation, the thin-supply emit cap, and **one wallpaper per location for
the whole collection**. Nothing else discounts a candidate.

## The bar, where a head has one, is a floor under all three

A head with an acting release bar ([`floors.release_bar`]) offers only the rows
that clear it. The three caps are ceilings on how many a partition may seat; the
bar is the one thing here that says a particular row may not be seated *at all*,
and it outranks the guarantee for the same reason the location rule does — the
guarantee buys a slot and the right to spend it, not the right to spend it on
something the head calls a failure.

**A slot with nothing to seat goes unfilled.** It is not handed to another
partition, not filled from below the bar, and not filled by relaxing a cap: the
release target is a cap and not a quota. That is why [`select`] returns a third
value. A short release has to be attributable to the partition and the reason
that shortened it, and "six planned, two seated" with no third column is exactly
the number that gets read as thin supply when it was a bar.

## The two judges are never compared in one step

A score is a probability on **one head's** train-prior-calibrated scale, and the
two finished-render judges do not share one. A single pass over both shuts the
smaller-scaled head out entirely — the source project lost eighty-two
release-eligible strange candidates to smooth exactly that way, in the release it
had already shipped. So this function takes one head's entries per call and the
caller runs it twice; the head budget is decided outside, by [`budget`].

## The diversity rule is the near-duplicate grouping this repository already has

"One wallpaper per location" needs a definition of *one location*, and there is a
shipped one: `labeling.groups`, the connected components of "these two frames
would leak into each other" — same plane exactly, seed constants within a
tolerance, overlapping frames. It is the rule the train/evaluation split is drawn
on, so a release cannot ship two pictures of what the holdout calls one location.

That is deliberately *geometric* rather than perceptual. The source's grouping ran
a CLIP embedding over a grayscale render of every candidate, which is a second
model, a second cache and a second thing to keep in step with a checkpoint; the
grouping this repository ships needs neither, is exact, and is already the
authority on what two pictures being the same picture means here.

## The cap is one, and its scope is the collection

Both halves were widened on 2026-08-22 by Matt's ruling, and neither half was a
tuning decision:

* [`floors.CLUSTER_CAP`] is **1**. Two colorings of one frame are two wallpapers
  of one place, and a collection is a set of places.
* the scope is the collection and not one run. A candidate whose group already
  holds a served wallpaper is refused `location_served`, whether that wallpaper
  came from `served` — the index of what the collection has already released — or
  from a higher-ranked seat in this pass. **Higher-ranked keeps**: the pool is
  score ordered and the counter is checked as each seat is taken, so the row that
  is refused is always the weaker of the two on its own head's scale.

`served` is an argument rather than something this module reads, and who passes
it is the split between curation's two phases. A **run** does not: it is the pool
phase, it accumulates candidates and keeps a small diagnostic release, and a run
that refused a place because an earlier run released it was casting one run's
seats as a veto on the next run's coverage. The global pass over the accumulated
pool passes it, because that is the pass with the population to decide coverage
with.

**One grouping over everything, computed once** ([`grouped`]). A group id is a
position in a connected-components labelling and means nothing outside the call
that made it, so the two heads' pools and the served index have to be grouped
*together* or their tags are not comparable — which is also what makes the cap
apply to the union of the two heads' seats rather than to each of them.

Both heads still attempt every location; the second seat for one is now always
refused, so what the second attempt buys is the better of the two heads' readings
rather than a second wallpaper. Sizing the attempt plan against that is a separate
question and has not been taken.

## The rule outranks the guarantee

A guaranteed partition whose only candidates are places the collection already has
ships nothing and short-fills. The guarantee buys a slot and the right to spend it,
not a second picture of a place already taken.
"""

from __future__ import annotations

from fractal_wallpapers.curation import floors

#: Why a slot the allocation planned was not seated, in the order the reasons are
#: read. One slug per unfilled partition, chosen by the first cause that applies
#: — the counts beside it in the fill record carry the rest, so nothing is lost
#: by naming only the binding one.
UNFILLED_REASONS = {
    "below_bar": "no remaining candidate cleared the head's acting release bar",
    "location_served": "every remaining candidate was a place the collection has already served",
    "no_candidates": "the partition ran out of scored candidates",
    "supply_cap": "the thin-supply cap: fewer than four passing candidates per slot",
}

#: The one refusal slug for the one-wallpaper-per-location rule, whichever side
#: of it a candidate fell on. The `cause` beside it on the log row separates a
#: place an earlier run served from a place this run just seated — the same
#: refusal for a person reading a sheet, two different facts for a readout asking
#: what the ruling cost.
LOCATION_SERVED = "location_served"


def groups_of(rows: list[dict]) -> list:
    """The near-duplicate group of each row, through the shipped grouping.

    A row the grouping cannot place — no location identity — gets its own group
    rather than sharing one, because "unplaceable" is not a look and lumping them
    together would let one bad row cap the rest.
    """
    from fractal_wallpapers.labeling import groups as group_module

    grouping = group_module.assign(rows)
    out, spare = [], grouping.size()
    for group in grouping.of_row:
        if group is None:
            out.append(f"unplaced#{spare}")
            spare += 1
        else:
            out.append(f"group#{group}")
    return out


def scored_rows(rows: list[dict]) -> list[dict]:
    """The rows a selector may look at.

    Only rows that were actually scored are eligible. A failed render is a
    recorded row with a reason and no score, and a selector that read its absent
    score as a zero would rank a crash against a wallpaper.
    """
    return [row for row in rows if row.get("p_ge3") is not None]


def entries(rows: list[dict], tags: list | None = None) -> list[dict]:
    """Candidate rows as the selector reads them: id, partition, group, score.

    `tags` is the grouping's answer for these rows when it was taken over a wider
    population — see [`grouped`], which is how the run calls this. Omitting it
    groups these rows alone, which is right for a caller that has only these and
    wrong for anything comparing tags across two calls.
    """
    scored = scored_rows(rows)
    tags = groups_of(scored) if tags is None else list(tags)
    return [
        {
            "id": f"{row['attempt']:04d}",
            "partition": row["partition"],
            "group": tag,
            "score": float(row["p_ge3"]),
            "row": row,
        }
        for row, tag in zip(scored, tags, strict=True)
    ]


def grouped(by_head: dict, served=()) -> tuple[dict, set]:
    """`(entries per head, the tags already holding a served wallpaper)`.

    **One grouping over everything**, which is the only way the tags mean the
    same thing in three places that have to agree: the smooth pass, the strange
    pass, and the collection's served index. A group id is a position in a
    connected-components labelling — group ids from two calls are unrelated — so
    a run that grouped each head separately and then shared a counter between
    them was sharing a dictionary and not a rule.

    The served locations go in first and their tags come back out as the refusal
    set. They are grouped *with* the candidates rather than tested against them
    pairwise because a group is a connected component: a candidate can reach a
    served location through an intermediate neither of them neighbours, and a
    pairwise test would seat it.
    """
    served = list(served)
    scored = {head: scored_rows(rows) for head, rows in by_head.items()}
    order = sorted(scored)
    tags = groups_of(served + [row for head in order for row in scored[head]])
    already = set(tags[: len(served)])
    out, at = {}, len(served)
    for head in order:
        count = len(scored[head])
        out[head] = entries(scored[head], tags[at : at + count])
        at += count
    return out, already


def select(
    candidates: list[dict],
    slots: dict,
    caps: dict | None = None,
    used: dict | None = None,
    cluster_cap: int = floors.CLUSTER_CAP,
    guarantees=(),
    bar=None,
    served=(),
) -> tuple[list[dict], list[dict], dict]:
    """`(selected, log, fills)` — top-N per partition under the caps and the bar.

    `slots`       `{partition: n}`, this pass's allocation. A partition absent
                  from it gets nothing: the allocation is the authority on which
                  partitions may release at all.
    `caps`        `{partition: n}`, the thin-supply cap. A partition absent is
                  **uncapped**, which is the honest default for a caller with no
                  supply census; the driver always passes one.
    `used`        a `{group: count}` carried **across** calls, so the cap covers
                  the union of both heads' seats rather than each pass on its
                  own. Mutated in place.
    `served`      the group tags the collection has already released a wallpaper
                  of, from [`grouped`]. A candidate in one is refused
                  [`LOCATION_SERVED`] with cause `prior_run`; the same refusal
                  with cause `this_run` is `used` reaching `cluster_cap`.
    `guarantees`  the partitions this pass owes a guaranteed slot. Two effects,
                  both on the first pick only: the budget floors at one, which is
                  the guarantee overriding the thin-supply cap; and that pick's
                  log row is stamped `guarantee` instead of `mix`.
    `bar`         this head's acting release bar ([`floors.Bar`]), or `None` where
                  the head has one that only annotates. `None` is no bar at all
                  and not a bar at zero: the pass picks exactly as it did before
                  any head gated, which is what keeps the ungated head's path
                  unchanged by a decision taken about the other one.

    `selected` comes out partition-major, each partition's picks best first; the
    log carries one row per pick *and* per skip, reason included, so a thin or
    lopsided release is diagnosable from the log alone. `fills` is the slot
    arithmetic per partition — planned, seated, unfilled and why — which the log
    cannot carry because an unfilled slot has no candidate to hang a row on.
    """
    used = {} if used is None else used
    caps = {} if caps is None else caps
    served = set(served)
    owed = set(guarantees)
    by_partition: dict[str, list[dict]] = {}
    for entry in candidates:
        by_partition.setdefault(entry["partition"], []).append(entry)

    selected: list[dict] = []
    log: list[dict] = []
    fills: dict = {}
    for partition in slots:
        allotted = int(slots.get(partition, 0))
        budget = min(allotted, int(caps[partition])) if partition in caps else allotted
        guaranteed = partition in owed and allotted >= 1
        if guaranteed:
            budget = max(budget, 1)
        pool = sorted(
            by_partition.get(partition, []), key=lambda e: (-float(e["score"]), str(e["id"]))
        )
        taken, below, capped = 0, 0, 0
        for rank, entry in enumerate(pool):
            if taken >= budget:
                break
            group = entry["group"]
            skipped, cause = None, None
            if bar is not None and not bar.acts(entry["score"]):
                # Below the bar is not "beaten by a better row": it is not
                # eligible for a slot at all, and the pool is score-ordered, so
                # nothing under it is either. Logged one row each anyway, because
                # the record of what a bar removed is the only way to ask later
                # what it bought.
                skipped, below = "below_bar", below + 1
            elif group in served:
                # An earlier run already released this place. Checked before the
                # counter so the cause is the true one: a candidate refused here
                # would also have been refused by the counter the moment a seat
                # was taken, and reporting that would hide the ruling's real cost.
                skipped, cause, capped = LOCATION_SERVED, "prior_run", capped + 1
            elif used.get(group, 0) >= cluster_cap:
                skipped, cause, capped = LOCATION_SERVED, "this_run", capped + 1
            if skipped is not None:
                log.append(
                    {
                        "id": entry["id"],
                        "partition": partition,
                        "group": group,
                        "rank": rank,
                        "score": round(float(entry["score"]), 6),
                        "picked": False,
                        "skipped": skipped,
                        "cause": cause,
                    }
                )
                continue
            used[group] = used.get(group, 0) + 1
            selected.append(entry)
            log.append(
                {
                    "id": entry["id"],
                    "partition": partition,
                    "group": group,
                    "rank": rank,
                    "score": round(float(entry["score"]), 6),
                    "picked": True,
                    "skipped": None,
                    "cause": None,
                    "slots": allotted,
                    "supply_cap": int(caps[partition]) if partition in caps else None,
                    # Per-slot provenance. The guarantee is one slot, so it is the
                    # first pick of an owed partition; everything after it came
                    # out of the mix. A `not_selected` row has no slot and
                    # therefore no provenance — defaulting it would invent one.
                    "slot_source": "guarantee" if (guaranteed and taken == 0) else "mix",
                    "group_count": used[group],
                    # The bar that let this row sit down, stamped per seat. A
                    # seated row on a gated head must carry the height it cleared
                    # and the artifact that height lives on, or the seat is a
                    # claim nobody can restate once the head moves.
                    "bar": None
                    if bar is None
                    else {"name": bar.name, "value": bar.value, "head_sha256": bar.stamp},
                }
            )
            taken += 1
        if allotted:
            fills[partition] = _fill(allotted, budget, len(pool), taken, below, capped)
    return selected, log, fills


def _fill(allotted: int, budget: int, eligible: int, taken: int, below: int, capped: int) -> dict:
    """One partition's slot arithmetic, and the binding reason it fell short.

    The reason is chosen by precedence rather than reported as a set, because a
    partition that ran out under the bar also ran out of candidates and listing
    both says less than naming the first. Every count that fed the choice is on
    the record beside it.
    """
    unfilled = max(0, allotted - taken)
    reason = None
    if unfilled:
        if taken < budget:
            reason = "below_bar" if below else LOCATION_SERVED if capped else "no_candidates"
        else:
            reason = "supply_cap"
    return {
        "planned": allotted,
        "budget": budget,
        "eligible": eligible,
        "seated": taken,
        "unfilled": unfilled,
        "below_bar": below,
        "location_served": capped,
        "reason": reason,
        "why": UNFILLED_REASONS[reason] if reason else None,
    }


__all__ = [
    "LOCATION_SERVED",
    "UNFILLED_REASONS",
    "entries",
    "grouped",
    "groups_of",
    "scored_rows",
    "select",
]
