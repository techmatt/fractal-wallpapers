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
`curate retire-repeats`, the rejection path. Nothing in `curate run` reads it.

**The gallery pass does not read it either, and that is not the same exemption.**
A run is excused because it has the wrong population; `curate gallery` has
exactly the right one and is excused because of what a *pass* is. Each pass
chooses the whole gallery at once and **supersedes** the previous one rather than
adding to it, so a pass that refused every place the last pass shipped could not
re-choose its own gallery — and a pass that refused every place a run's
diagnostic release happens to sit on would be handing the collection's best
locations to the ten pictures a night kept to prove its path worked. One
wallpaper per location is enforced inside the pass, over the pass's own seats,
which is the population the gallery is.

## Superseding is enforced here, because "the collection" is defined here

A pass supersedes the previous gallery, and for two passes that was prose with
nothing behind it: both passes' seats were `released`, so both were served and the
collection held two galleries at once. [`current_pass`] is what makes the word
mean something — the newest pass with served seats is the gallery, and an earlier
pass's rows stay released and on record without being served. Nothing is deleted
and nothing is rejected; a rejection means a person took a picture back on its
merits, and being replaced by a later pass is not that.

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


def build(
    exclude_run: str | None = None, under=None, collection: str | None = None
) -> ServedLocations:
    """Read the tracked release records into an index of served locations.

    `exclude_run` drops one run's own rows, for a caller asking what the index
    would be *without* a given run in it — what the collection looked like before
    it, or what a gallery pass would decide if that run's seats were not already
    taken. A name nothing has released under passes harmlessly.

    `collection` narrows it to one of [`records.COLLECTIONS`], and **the rule is
    per collection**. There are two: the runs' `diagnostic` pictures and the
    gallery pass's. A gallery winner standing where a run's diagnostic picture
    already stands is not a repeat — it is the design, stated at the top of this
    module — and an index over both at once answers a question nobody asked.
    `None` is every row, which is what `curate repeats` reads when it wants to see
    the whole store at once.

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
        if (exclude_run is None or row.get("run") != exclude_run)
        and (collection is None or row.get("collection") == collection)
    ]
    rows = [row for row in rows if not _superseded(row, current_pass(rows))]
    return ServedLocations(locations=[dict(row.get("location") or {}) for row in rows], rows=rows)


def _superseded(row: dict, current: str | None) -> bool:
    """Is this row a seat of a gallery pass that a later pass has replaced?"""
    return (
        current is not None
        and row.get("collection") == records.GALLERY
        and str(row.get("run")) != current
    )


def current_pass(rows) -> str | None:
    """The newest gallery pass **with rendered seats**, which is the gallery.

    A pass chooses the whole gallery at once and supersedes the previous one, so
    two passes' seats are two galleries rather than one gallery holding both. The
    older pass's rows stay `released` and stay on record — nothing is deleted, and
    its own pass record still says what it chose out of what — but they are not
    what the collection serves any more.

    **Rendered** is load-bearing and is this function's own test rather than
    something the caller is trusted to have done. `--no-full-size` takes every
    seating decision and spends no release render: those seats are recorded
    `unrendered`, which is a seat with no wallpaper at the end of it. A pass like
    that must never become the collection — it would supersede a gallery that has
    pictures with one that has none — so the rows are put through
    [`records.served`] here, and a pass is only a candidate if something survives
    it. `curate gallery --pass <id>` without the flag later makes the pictures and
    lifts the rows to `released`, and the pass becomes eligible then and not
    before.

    Until a third pass this was invisible: gallery2 ran `--no-full-size`, so only
    one pass had ever rendered its seats. The moment two passes both had
    wallpapers the collection held two galleries at once, and the
    one-wallpaper-per-location rule failed on twenty places — not because either
    pass was wrong, but because nothing said which of them was the gallery.

    Computed AFTER `exclude_run` and off the rows in hand, deliberately: a caller
    asking what the collection looked like without the newest pass should get the
    pass before it, not an empty gallery.
    """
    from fractal_wallpapers.curation import gallery_store

    named = {
        str(row.get("run"))
        for row in records.served(rows)
        if row.get("collection") == records.GALLERY
    }
    ordered = [name for name in gallery_store.passes() if name in named]
    return ordered[-1] if ordered else None


def by_collection(index: ServedLocations) -> list[tuple]:
    """One index per collection the served set holds, in name order.

    The population the one-wallpaper-per-location rule acts over is **one
    collection**, and [`build`] already knows it — but a caller holding a whole
    index has no way to cut it without reading the store a second time. This is
    that cut, off the rows in hand.

    A row whose `collection` is `None` is its own population rather than a member
    of every one: nothing tracked carries that, and folding it into a named
    collection would be this function guessing which.
    """
    seen: dict = {}
    for place, row in enumerate(index.rows):
        seen.setdefault(row.get("collection"), []).append(place)
    return [
        (
            name,
            ServedLocations(
                locations=[index.locations[place] for place in places],
                rows=[index.rows[place] for place in places],
            ),
        )
        for name, places in sorted(seen.items(), key=lambda item: str(item[0]))
    ]


def repeats(
    index: ServedLocations | None = None, under=None, collection: str | None = None
) -> list[dict]:
    """Every group of the served set holding more than one wallpaper.

    The retro read of the rule against the collection that predates it: what the
    ruling would have refused, laid out so somebody can choose which one of each
    group survives. It decides nothing and rejects nothing.

    `collection` is [`build`]'s and means the same thing: the rule acts inside one
    collection, and a group holding a run's diagnostic picture and a gallery
    winner of the same place is two collections agreeing about a location rather
    than one collection holding it twice.
    """
    from fractal_wallpapers.labeling import groups as group_module

    index = build(under=under, collection=collection) if index is None else index
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
                "collections": sorted({str(row.get("collection")) for row in rows}),
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


__all__ = ["ServedLocations", "build", "by_collection", "current_pass", "repeats"]
