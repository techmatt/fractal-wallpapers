"""Which candidates take the release's slots. One rule, and three caps on it.

Top-N by the judge's own score, per partition, under three limits: the partition's
slot allocation, the thin-supply emit cap, and at most [`floors.CLUSTER_CAP`]
picks from one near-duplicate group per run. Nothing else discounts a candidate.

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
) -> tuple[list[dict], list[dict]]:
    """`(selected, log)` — top-N per partition under the slot, supply and group caps.

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

    `selected` comes out partition-major, each partition's picks best first; the
    log carries one row per pick *and* per group-cap skip, so a thin or lopsided
    release is diagnosable from the log alone.
    """
    used = {} if used is None else used
    caps = {} if caps is None else caps
    owed = set(guarantees)
    by_partition: dict[str, list[dict]] = {}
    for entry in candidates:
        by_partition.setdefault(entry["partition"], []).append(entry)

    selected: list[dict] = []
    log: list[dict] = []
    for partition in slots:
        allotted = int(slots.get(partition, 0))
        budget = min(allotted, int(caps[partition])) if partition in caps else allotted
        guaranteed = partition in owed and allotted >= 1
        if guaranteed:
            budget = max(budget, 1)
        pool = sorted(
            by_partition.get(partition, []), key=lambda e: (-float(e["score"]), str(e["id"]))
        )
        taken = 0
        for rank, entry in enumerate(pool):
            if taken >= budget:
                break
            group = entry["group"]
            if used.get(group, 0) >= cluster_cap:
                log.append(
                    {
                        "id": entry["id"],
                        "partition": partition,
                        "group": group,
                        "rank": rank,
                        "score": round(float(entry["score"]), 6),
                        "picked": False,
                        "skipped": "cluster_cap",
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
                }
            )
            taken += 1
    return selected, log


__all__ = ["entries", "groups_of", "select"]
