"""Every location the collection has already released a wallpaper of.

The look cap used to be the whole diversity rule: at most two release picks from
one near-duplicate group, **per run**. Both halves of that were wrong, and Matt
ruled on 2026-08-22 that they were:

* *per run* meant a location released in run2 was free to be released again in
  run9, and thirty-two of the hundred and thirty served wallpapers are second and
  third pictures of a place the collection already had.
* *two* meant one run could ship a look twice on purpose. Two colorings of one
  frame are two wallpapers of one place, and a collection is a set of places.

So the rule is now **one released wallpaper per location, collection-wide** —
not in one run, not across runs, not in two modes or two palettes.

## A run does not read this, and that is the split between the two phases

It did, until 2026-08-22. A `curate run` built this index and refused every
candidate whose place an earlier run had released, which made one run's seats a
veto on the next run's coverage — a global decision taken by whichever run
happened to go first, out of the fraction of the pool it had in front of it. The
two phases are separate now: a run **accumulates** candidates and keeps a small
diagnostic release, and what the collection ships is chosen later over the whole
accumulated pool at once. One wallpaper per location is still enforced, and it is
enforced where the population to enforce it over actually exists.

So this index is read by the collection-level passes — `curate repeats`,
`curate retire-repeats`, the rejection path — and by the global selection that
decides what ships. Nothing in `curate run` reads it.

## "Same location" is the grouping this repository already had

`labeling.groups.assign`: same plane digit for digit, seed `c` within
`groups.C_TOLERANCE`, overlapping frames. It is the rule the train/evaluation
split is drawn on, and reusing it means a release cannot ship two pictures of
what the holdout calls one location. **Perceptual similarity is a different
question** — two unrelated places that happen to look alike — and it is not this.

## The index is a set of places, and it has no keys of its own

A group id is a *position in a connected-components labelling*, so it means
nothing outside the call that produced it: `group#3` over one run's candidates
and `group#3` over another's are unrelated. That is the whole reason nothing here
is stored on a row. What this module holds is the served rows' **locations**, and
the question "has this candidate's location been served" is answered by grouping
the candidates and the index *together*, in one call, and asking whether a
candidate's component contains an index member ([`selection.grouped`]).

Grouping them together rather than testing the neighbour predicate pairwise is
not a detail. A group is a connected *component*: a candidate can be joined to a
served location through an intermediate that neither of them is a neighbour of,
and a pairwise test would seat it.

## What counts as served, and what does not

[`records.served`] — released, minus what a review took back, minus rows with no
picture. A rejected row's location is free again, which is the point of
rejecting it; a `passed_over` row was never served and never blocked anything.

**Read out of the tracked store, always**, and not out of this process's record
root. `--ephemeral` redirects everything a rehearsal writes under `scratch/`,
which is what keeps a rehearsal's rows out of a later calibration — but the
collection is not a thing a rehearsal owns, and one that read its own empty root
would seat places the collection already has and produce a release nobody could
compare to a real one. The same reasoning puts the bar exceptions outside the
redirect.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fractal_wallpapers.curation import records


@dataclass(frozen=True)
class ServedLocations:
    """The places already spoken for, and the rows that spoke for them.

    `locations` is what the grouping reads; `rows` is the release records they
    came from, kept so a refusal can name the wallpaper that caused it rather
    than only asserting one exists.
    """

    locations: list = field(default_factory=list)
    rows: list = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.locations)

    def summary(self) -> dict:
        runs: dict = {}
        for row in self.rows:
            runs[row.get("run")] = runs.get(row.get("run"), 0) + 1
        return {"served_rows": len(self.rows), "by_run": dict(sorted(runs.items()))}


def build(exclude_run: str | None = None, under=None) -> ServedLocations:
    """Read the tracked release records into an index of served locations.

    `exclude_run` drops one run's own rows, for a caller asking what the index
    would be *without* a given run in it — what the collection looked like before
    it, or what a global pass would decide if that run's seats were not already
    taken. A name nothing has released under passes harmlessly.

    `under` names a record store other than the tracked one. It is not how a run
    calls this — a run's index is the collection's and the collection is tracked
    — and it is how a test, or anything asking what the index would be over some
    other store, says which store it means.
    """
    tracked = records.read_decisions(
        records.RELEASE, under=records.default_root() if under is None else under
    )
    rows = [
        row
        for row in records.served(tracked)
        if exclude_run is None or row.get("run") != exclude_run
    ]
    return ServedLocations(locations=[dict(row.get("location") or {}) for row in rows], rows=rows)


def repeats(index: ServedLocations | None = None, under=None) -> list[dict]:
    """Every group of the served set holding more than one wallpaper.

    The retro read of the rule against the collection that predates it: what the
    ruling would have refused, laid out so somebody can choose which one of each
    group survives. It decides nothing and rejects nothing.
    """
    from fractal_wallpapers.labeling import groups as group_module

    index = build(under=under) if index is None else index
    grouping = group_module.assign(index.locations)
    out = []
    for group, members in sorted(grouping.members.items()):
        if len(members) < 2:
            continue
        rows = [index.rows[i] for i in members]
        out.append(
            {
                "group": f"group#{group}",
                "partition": (rows[0].get("location") or {}).get("partition"),
                "runs": sorted({str(row.get("run")) for row in rows}),
                "served": [
                    {
                        "key": row.get("key"),
                        "run": row.get("run"),
                        "candidate": row.get("candidate"),
                        "head": (row.get("scores") or {}).get("head"),
                        "p_ge3": (row.get("scores") or {}).get("p_ge3"),
                        "mode": (row.get("recipe") or {}).get("mode"),
                        "colormap": (row.get("recipe") or {}).get("colormap"),
                        "picture": row.get("picture"),
                    }
                    for row in rows
                ],
            }
        )
    return sorted(out, key=lambda cell: (-len(cell["served"]), cell["group"]))


__all__ = ["ServedLocations", "build", "repeats"]
