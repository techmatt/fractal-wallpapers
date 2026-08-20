"""Which candidates take the release's slots. One rule, three caps, and one bar.

Top-N by the judge's own score, per partition, under three limits: the partition's
slot allocation, the thin-supply emit cap, and at most [`floors.CLUSTER_CAP`]
picks from one near-duplicate group per run. Nothing else discounts a candidate.

## The bar, where a head has one, is a floor under all three

A head with an acting release bar ([`floors.release_bar`]) offers only the rows
that clear it. The three caps are ceilings on how many a partition may seat; the
bar is the one thing here that says a particular row may not be seated *at all*,
and it outranks the guarantee for the same reason the look cap does — the
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

"No more than two of one look" needs a definition of *one look*, and there is a
shipped one: `labeling.groups`, the connected components of "these two frames
would leak into each other" — same plane exactly, seed constants within a
tolerance, overlapping frames. It is the rule the train/evaluation split is drawn
on, so a release cannot ship two pictures of what the holdout calls one location.

That is deliberately *geometric* rather than perceptual. The source's grouping ran
a CLIP embedding over a grayscale render of every candidate, which is a second
model, a second cache and a second thing to keep in step with a checkpoint; the
grouping this repository ships needs neither, is exact, and is already the
authority on what two pictures being the same picture means here.

**One counter across both passes.** The cap is per *run*: two disjoint head passes
over the same locations would otherwise each be free to take two pictures of one
look, and a release of four could be two looks.

## The cluster cap outranks the guarantee

A guaranteed partition whose only candidates sit in groups the run has already
filled ships nothing and short-fills. The guarantee buys a slot and the right to
spend it, not a second picture of a look already taken.
"""

from __future__ import annotations

from fractal_wallpapers.curation import floors

#: Why a slot the allocation planned was not seated, in the order the reasons are
#: read. One slug per unfilled partition, chosen by the first cause that applies
#: — the counts beside it in the fill record carry the rest, so nothing is lost
#: by naming only the binding one.
UNFILLED_REASONS = {
    "below_bar": "no remaining candidate cleared the head's acting release bar",
    "cluster_cap": "every remaining candidate was a third picture of a look already taken",
    "no_candidates": "the partition ran out of scored candidates",
    "supply_cap": "the thin-supply cap: fewer than four passing candidates per slot",
}


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


def entries(rows: list[dict]) -> list[dict]:
    """Candidate rows as the selector reads them: id, partition, group, score.

    Only rows that were actually scored are eligible. A failed render is a
    recorded row with a reason and no score, and a selector that read its absent
    score as a zero would rank a crash against a wallpaper.
    """
    scored = [row for row in rows if row.get("p_ge3") is not None]
    tags = groups_of(scored)
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


def select(
    candidates: list[dict],
    slots: dict,
    caps: dict | None = None,
    used: dict | None = None,
    cluster_cap: int = floors.CLUSTER_CAP,
    guarantees=(),
    bar=None,
) -> tuple[list[dict], list[dict], dict]:
    """`(selected, log, fills)` — top-N per partition under the caps and the bar.

    `slots`       `{partition: n}`, this pass's allocation. A partition absent
                  from it gets nothing: the allocation is the authority on which
                  partitions may release at all.
    `caps`        `{partition: n}`, the thin-supply cap. A partition absent is
                  **uncapped**, which is the honest default for a caller with no
                  supply census; the driver always passes one.
    `used`        a `{group: count}` carried **across** calls, so the cap is per
                  run rather than per pass. Mutated in place.
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
            skipped = None
            if bar is not None and not bar.acts(entry["score"]):
                # Below the bar is not "beaten by a better row": it is not
                # eligible for a slot at all, and the pool is score-ordered, so
                # nothing under it is either. Logged one row each anyway, because
                # the record of what a bar removed is the only way to ask later
                # what it bought.
                skipped, below = "below_bar", below + 1
            elif used.get(group, 0) >= cluster_cap:
                skipped, capped = "cluster_cap", capped + 1
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
            reason = "below_bar" if below else "cluster_cap" if capped else "no_candidates"
        else:
            reason = "supply_cap"
    return {
        "planned": allotted,
        "budget": budget,
        "eligible": eligible,
        "seated": taken,
        "unfilled": unfilled,
        "below_bar": below,
        "cluster_cap": capped,
        "reason": reason,
        "why": UNFILLED_REASONS[reason] if reason else None,
    }


__all__ = ["UNFILLED_REASONS", "entries", "groups_of", "select"]
