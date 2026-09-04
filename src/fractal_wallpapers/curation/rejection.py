"""Taking a released row back, after the run, without losing what the run did.

A release path can be wrong in a way no head and no test catches, and the thing
that catches it is a person at a sheet. When that happens the run's own records
must not be quietly rewritten to look like the run had known better: `run2`
released eleven strange rows below the strange head's 0.50, the head had been
right about every one of them, and the defect was the release path padding
strange slots out of thin passing supply. Deleting the rows would delete the
evidence of the defect along with them.

So a rejection is **added**, never written over:

* `verdict` stays `released`. That is what the run decided, and it stays true.
* a `rejected` block says who, when, why, and against which bar and artifact.
* the scores are untouched. Nothing here reads them; nothing here changes them.
* [`records.served`] — released minus rejected — is what every listing reads,
  so the row stops being served the moment the block lands, everywhere at once.

## The retroactive pass applies today's acting bars to yesterday's release

[`apply`] is not "reject these eleven rows". It is "this run was released before
this head's cut acted; apply it now", which is a rule rather than a list, and the
eleven rows fall out of it. That matters twice: the same command settles any other
run released under the old stance, and re-running it on a settled one changes
nothing, because the rule has already been applied and produces the same block
byte for byte.

Only heads whose cut **acts** are considered. A smooth row below the smooth
advisory is not touched by this and must not be: the advisory annotates, and the
below-advisory smooth rows belong to a mix-ratio decision nobody has taken.

## A ruling that keeps a row in service is written down, or it is not a ruling

The rule above is idempotent and it is live: it reads the bar at the moment it
runs, so it will find the same rows again every time it is asked. That is what
makes an *unwritten* exception dangerous rather than merely undocumented — four
run8h rows sit below the strange bar and stay served on Matt's reading of the
sheet, and until 2026-08-22 nothing encoded that. The next `curate reject --run
run8h` would have taken them out of service, correctly by the rule and against
the decision, with no line anywhere saying a decision had been made.

So [`exceptions`] is a tracked record — keys, the ruling's date, who took it and
why — and [`below_acting_bar`] passes over the rows it names. It is deliberately
per *row* and not per run or per head: an exception that named a run would go on
excusing rows that run has not made yet, and one that named a head would be the
bar being retired by the back door.

## The second rule that takes a row back is a comparison, not a measurement

One wallpaper per location acts at selection from 2026-08-22 and cannot reach
backwards, so the collection it began on was already holding second and third
pictures of places it had. [`retire_repeats`] applies the rule to what is
already there: each near-duplicate group keeps its best reading and the rest are
stamped `location_served`.

It is a *separate* pass from [`apply`] and deliberately not a mode of it. `apply`
reads the bars live, and every row it would touch is a row whose score fails a
cut — including the four run8h rows a ruling holds in service, which it must go
on excusing. This rule compares two rows to each other and does not read a bar at
all, so a row can be perfectly good and still lose its place to a better reading
of the same place. The two answer different questions and a row can be taken back
by either.

The bar ruling does not carry over, and it is not being reversed when it does not.
A ruling says a named row stays in service *below the bar*; whether the collection
holds two pictures of that row's location is not a question it was asked. Where a
retirement lands on an excused row the pass names it in the report rather than
skipping it — the alternative is a location rule with a silent exception list it
never agreed to.
"""

from __future__ import annotations

import json
from pathlib import Path

from fractal_wallpapers.curation import (
    floors,
    records,
    run_layout,
    selection,
    served_locations,
    sheet,
)
from fractal_wallpapers.paths import repo_root

#: The slug a retroactive bar rejection records. One value, because there is one
#: rule here; a rejection taken for any other cause is a different verdict and
#: would want its own.
BELOW_ACTING_BAR = "below_acting_bar"

#: The slug a retirement under the one-wallpaper-per-location rule records. The
#: same spelling [`selection`] refuses a live candidate with, because a person
#: reading a refused candidate and a retired wallpaper is reading one rule.
LOCATION_SERVED = selection.LOCATION_SERVED

#: The tracked rulings that keep a named row in service below an acting bar.
#: One row per excused release row, carrying the key it excuses, the bar it sits
#: under, the score, and who ruled it when and why.
EXCEPTIONS_NAME = "bar_exceptions.jsonl"


def exceptions_path() -> Path:
    """Where the rulings live. Tracked, and never the ephemeral record root.

    Deliberately not under [`records.root()`]: a rehearsal redirects the whole
    record store under `scratch/`, and a ruling that moved with it would stop
    applying exactly when a rehearsal was checking whether it did.
    """
    return repo_root() / "data" / "curation" / EXCEPTIONS_NAME


def exceptions() -> dict:
    """`{key: ruling}` for every row a ruling keeps in service. Empty is normal.

    Keyed on the release record's own `run|stage|candidate`, so an exception
    cannot drift onto a different row than the one it was written for, and a run
    renamed loses its exceptions loudly rather than silently excusing a stranger.
    """
    path = exceptions_path()
    if not path.is_file():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            out[str(row["key"])] = row
    return out


class RejectionRefused(RuntimeError):
    """A rejection pass cannot run as asked, and guessing would cost records."""


def note_for(bar: floors.Bar, score) -> str:
    """The sentence a rejected row carries: what it failed and by how much."""
    return (
        f"P(>=3) {float(score):.4f} is below the {bar.head} release bar at {bar.value:g}, which "
        f"ACTS at release selection. This row was seated by a release path that padded the "
        f"head's slots from thin passing supply; that path no longer exists and the slot would "
        f"now go unfilled. {bar.basis}"
    )


def below_acting_bar(rows) -> list[tuple[dict, floors.Bar]]:
    """`(row, bar)` for every served row whose head's acting bar it does not clear.

    Reads the *served* set rather than every released row, so a row an earlier
    pass already took back is not offered a second time and the pass converges.
    A row on an ungated head, or one with no score, is not here: a bar that acts
    seats nothing without a score, but it also never seated this row, and
    inventing a rejection for a record that predates the scoring would be a
    verdict nobody took.

    Rows named in [`exceptions`] are not here either. They still fail the bar and
    the record still says so; what the ruling settles is whether failing it takes
    them out of service, and that is a decision rather than a comparison.
    """
    excused = exceptions()
    out = []
    for row in records.served(rows):
        head = records.kind_of(row) or None
        score = records.live_reading(row).get("p_ge3")
        if head is None or score is None:
            continue
        if str(row.get("key")) in excused:
            continue
        bar = floors.release_bar(head)
        if bar is not None and not bar.acts(score):
            out.append((row, bar))
    return out


def apply(
    run: str,
    rejector: str,
    date: str,
    dry_run: bool = False,
    log=print,
) -> dict:
    """Apply today's acting release bars to a run released before they acted.

    Stamps every served row that fails its head's bar, rewrites the run's release
    records, and redraws the run's sheet off them so the rejected rows stop
    appearing as released. Returns what it did.

    Idempotent in both halves. The stamp is a pure function of the row, the bar
    and the two arguments, so a second pass with the same arguments finds nothing
    left to reject and rewrites identical bytes; the sheet is redrawn from the
    records either way, which is what makes *that* half idempotent rather than
    merely usually-unchanged.
    """
    rows = records.read_decisions(records.RELEASE, run)
    if not rows:
        raise RejectionRefused(
            f"run {run!r} has no release records in {records.root()}. Point the record root at "
            f"the store the run wrote, or check the run name."
        )
    failing = below_acting_bar(rows)
    stamped = []
    for row, bar in failing:
        score = records.live_reading(row)["p_ge3"]
        stamped.append(
            {
                **row,
                "rejected": records.rejection(
                    rejector=rejector,
                    date=date,
                    reason=BELOW_ACTING_BAR,
                    note=note_for(bar, score),
                    bar={"name": bar.name, "value": bar.value, "head_sha256": bar.stamp},
                ),
            }
        )
        log(
            f"[reject] {run} {row['candidate']} {bar.head} P(>=3) {float(score):.4f} "
            f"< {bar.value:g} — rejected by {rejector} ({date})"
        )

    excused = [
        row["candidate"] for row in records.served(rows) if str(row.get("key")) in exceptions()
    ]
    if excused:
        log(
            f"[reject] {len(excused)} row(s) held in service by a tracked ruling: "
            + ", ".join(sorted(excused))
        )
    report = {
        "run": run,
        "rejector": rejector,
        "date": date,
        "dry_run": bool(dry_run),
        "release_rows": len(rows),
        # Named, not just counted. A pass that quietly skipped four rows and a
        # pass that had nothing to skip print the same line otherwise, and which
        # one this was is the only thing anybody reads this report to find out.
        "excused_by_ruling": sorted(excused),
        "newly_rejected": [row["candidate"] for row in stamped],
        "rejected_total": sum(1 for row in rows if records.is_rejected(row)) + len(stamped),
        "served": len(records.served(rows)) - len(stamped),
        "by_head": _by_head(rows, {row["candidate"] for row in stamped}),
    }
    if dry_run:
        log(f"[reject] --dry-run: {len(stamped)} row(s) would be rejected, nothing written")
        return report

    path, _, _ = records.write_decisions(records.RELEASE, run, stamped)
    report["records"] = str(path)
    report["sheet"] = str(redraw(run, log=log))
    log(
        f"[reject] {run}: {len(stamped)} newly rejected, {report['rejected_total']} rejected in "
        f"all, {report['served']} row(s) served"
    )
    return report


def _run_order() -> dict:
    """Each run's place in the store's own ordering of run age, oldest first.

    [`records.run_records`] is the ordering this project already trusts for "which
    run is more recent" — the `finished` stamp where a record has one, and older
    than everything stamped where it does not. A run with no record at all is not
    in here, and [`_best_first`] reads a missing run as older than every recorded
    one rather than inventing a position for it.
    """
    return {path.stem: place for place, path in enumerate(records.run_records())}


def _best_first(order: dict):
    """Rank one location's wallpapers: the survivor first, then what it beat.

    The score is `P(>=3)` **on the row's own head's scale, uncompared**. The two
    finished-render judges are calibrated separately and a cross-scale adjustment
    would be a number nobody has measured; Matt's ruling is that at this size —
    twenty-seven groups, one of them a tie — it does not change which pictures the
    collection keeps, and an invented conversion factor would.

    Ties go to the **later run**, which is the reading taken against the more
    recent supply and the more recent heads. A row with no score at all sorts
    last: it is not a zero, and the only way it survives is by being alone, which
    is the one case where nothing was compared.
    """

    def rank(entry: dict) -> tuple:
        score = entry.get("p_ge3")
        return (
            score is None,
            -float(score or 0.0),
            -order.get(str(entry.get("run")), -1),
            str(entry.get("key")),
        )

    return rank


def _reading(entry: dict) -> str:
    """One row's score as this pass prints it, or the absence of one."""
    score = entry.get("p_ge3")
    return "no score" if score is None else f"P(>=3) {float(score):.4f}"


def location_note(survivor: dict) -> str:
    """The sentence a retired row carries: which row keeps this place, and how it read."""
    return (
        f"The collection releases one wallpaper per location and this location is served by "
        f"{survivor.get('key')} — {survivor.get('head')} {_reading(survivor)}, the highest "
        f"reading of this place on its own head's scale. This row was seated when the look cap "
        f"was two pictures per run, which let one place be released twice inside a run and "
        f"again by the next one. It is a second picture of a place the collection has, not a "
        f"bad picture: the verdict and the scores are untouched and nothing is deleted."
    )


def retire_repeats(
    rejector: str,
    date: str,
    dry_run: bool = False,
    log=print,
) -> dict:
    """Bring the collection to one wallpaper per location, keeping the best of each.

    The rule acts at selection from 2026-08-22 and cannot reach backwards, so this
    is it applied once to what the collection already held. Every near-duplicate
    group with more than one served wallpaper keeps the row [`_best_first`] ranks
    first, and the rest are stamped `location_served` carrying the survivor's key,
    so the comparison is legible from the row alone.

    Reads and writes **one store** — this process's — because it rewrites the rows
    it read. [`served_locations.build`] defaults to the tracked store on purpose,
    which is right for a run asking what the collection holds and wrong here: an
    index over the tracked store feeding writes into a redirected one would stamp
    rows that store does not have.

    **Scoped to one collection at a time**, because that is where the rule acts.
    There are two of them — the runs' `diagnostic` pictures and the gallery
    pass's — and a group holding one of each is two collections agreeing about a
    location rather than one collection holding it twice. The unscoped read finds
    those and is meant to; a pass that retired off it would have taken back
    twenty-seven wallpapers the rule does not reach.

    Idempotent, and not by re-deriving the same answer: a retired row leaves the
    served set, so a second pass finds every group holding one wallpaper and has
    nothing to do. One pass is enough for the same reason — dropping rows can only
    split a connected component, never merge two — so every group is left with
    exactly its survivor.
    """
    index = served_locations.build(under=records.root())
    order = _run_order()
    excused = exceptions()

    groups: list[dict] = []
    retired: dict[str, tuple[dict, dict]] = {}
    for collection, scoped in served_locations.by_collection(index):
        for cell in served_locations.repeats(scoped):
            ranked = sorted(cell["served"], key=_best_first(order))
            survivor, losers = ranked[0], ranked[1:]
            groups.append(
                {
                    "collection": collection,
                    "group": cell["group"],
                    "partition": cell["partition"],
                    "runs": cell["runs"],
                    "survivor": survivor,
                    "retired": losers,
                }
            )
            log(
                f"[retire] {collection} {cell['group']} {cell['partition']}: keeping "
                f"{survivor['key']} ({survivor['head']} {_reading(survivor)}) over "
                + ", ".join(
                    f"{entry['key']} ({entry['head']} {_reading(entry)})" for entry in losers
                )
            )
            for entry in losers:
                retired[str(entry["key"])] = (entry, survivor)

    per_run: dict[str, list[str]] = {}
    for key, (entry, _) in retired.items():
        per_run.setdefault(str(entry["run"]), []).append(key)

    # Named rather than counted, and not skipped. A ruling that holds a row in
    # service settles whether failing a bar takes it out, which is not the
    # question this rule asks — but a row leaving service under a second rule
    # while a tracked ruling names it is exactly what somebody has to be told
    # about rather than left to find.
    ruled = sorted(key for key in retired if key in excused)
    if ruled:
        log(
            f"[retire] {len(ruled)} retired row(s) named by a tracked bar ruling, which settled "
            f"a different question and is not reversed here: " + ", ".join(ruled)
        )

    written: dict[str, str] = {}
    sheets: dict[str, str] = {}
    for run in sorted(per_run):
        rows = records.read_decisions(records.RELEASE, run)
        by_key = {str(row.get("key")): row for row in rows}
        stamped = []
        for key in sorted(per_run[run]):
            row = by_key.get(key)
            if row is None:
                raise RejectionRefused(
                    f"{key!r} is in the served index and not in run {run!r}'s release records "
                    f"under {records.root()}. The index and the records have come apart, and "
                    f"stamping a row this pass cannot see would leave its group uncut."
                )
            _, survivor = retired[key]
            stamped.append(
                {
                    **row,
                    "rejected": records.rejection(
                        rejector=rejector,
                        date=date,
                        reason=LOCATION_SERVED,
                        note=location_note(survivor),
                        bar=None,
                        survivor=str(survivor["key"]),
                    ),
                }
            )
        if dry_run:
            continue
        path, _, _ = records.write_decisions(records.RELEASE, run, stamped)
        written[run] = str(path)
        sheets[run] = str(redraw(run, log=log))

    remaining = None
    if not dry_run:
        settled = served_locations.build(under=records.root())
        remaining = [
            cell
            for _collection, scoped in served_locations.by_collection(settled)
            for cell in served_locations.repeats(scoped)
        ]

    report = {
        "rejector": str(rejector),
        "date": str(date),
        "dry_run": bool(dry_run),
        "rule": {"reason": LOCATION_SERVED, "wallpapers_per_location": floors.CLUSTER_CAP},
        "served_before": len(index),
        "served_after": len(index) - len(retired),
        "groups": groups,
        "retired": sorted(retired),
        "by_run": {run: len(keys) for run, keys in sorted(per_run.items())},
        "held_in_service_by_a_ruling": ruled,
        "groups_remaining": None if remaining is None else len(remaining),
        "records": written,
        "sheets": sheets,
    }
    if dry_run:
        log(
            f"[retire] --dry-run: {len(retired)} wallpaper(s) over {len(groups)} location(s) "
            f"would be retired, nothing written"
        )
        return report
    log(
        f"[retire] {len(retired)} retired across {len(groups)} location(s); "
        f"{report['served_after']} served, {len(remaining or [])} location(s) still holding "
        f"more than one"
    )
    return report


def redraw(run: str, log=print) -> Path:
    """Redraw a run's release sheet off its records as they now stand.

    The sheet is the release's derived view, it lives in the untracked run
    directory, and it is regenerated rather than patched — a page edited to drop
    a row is a page that can disagree with the record it came from.
    """
    directory = run_layout.run_dir(run)
    rows = records.read_decisions(records.RELEASE, run)
    page = sheet.from_records(
        run,
        rows,
        _summary(run, rows),
        directory,
        directory / f"release_sheet_{run}.html",
    )
    log(f"[reject] sheet {page}")
    return page


def _summary(run: str, rows) -> dict:
    """The sheet's banner, off the run's own record where there is one.

    The counts a run knew and this pass does not — how many attempts it made, what
    it was asked for — are read back rather than recomputed, and simply absent
    when the run summary is not in the store. A banner that guessed at them would
    be the one part of this page nothing could check.
    """
    stored: dict = {}
    path = records.sinks(run)["run_record"]
    if path.is_file():
        stored = (json.loads(path.read_text(encoding="utf-8")) or {}).get("counts") or {}
    rejected = sum(1 for row in rows if records.is_rejected(row))
    summary = {
        "requested": stored.get("requested", "?"),
        "scored": stored.get("attempts_scored", len(rows)),
        "attempts": stored.get("attempts_made", "?"),
        "released": len(records.served(rows)),
        "rejected after review": rejected,
        "wallpapers per location": floors.CLUSTER_CAP,
        "junk floor": floors.JUNK_FLOOR,
        "good floor": floors.GOOD_FLOOR,
    }
    for head, restated in sorted(floors.ACTING_RELEASE_BARS.items()):
        summary[f"{head} bar"] = (
            f"{restated.value:g} (acting; restated {restated.date} against "
            f"{restated.head_sha256[:12]})"
        )
    return summary


def _by_head(rows, newly: set) -> dict:
    """Served against rejected, per head — the shape of what the pass changed."""
    out: dict = {}
    for row in rows:
        head = (row.get("scores") or {}).get("head")
        if head is None or row.get("verdict") != "released":
            continue
        cell = out.setdefault(head, {"released_by_the_run": 0, "rejected": 0, "served": 0})
        cell["released_by_the_run"] += 1
        gone = records.is_rejected(row) or row["candidate"] in newly
        cell["rejected" if gone else "served"] += 1
    return dict(sorted(out.items()))


__all__ = [
    "BELOW_ACTING_BAR",
    "EXCEPTIONS_NAME",
    "LOCATION_SERVED",
    "RejectionRefused",
    "apply",
    "below_acting_bar",
    "exceptions",
    "exceptions_path",
    "location_note",
    "note_for",
    "redraw",
    "retire_repeats",
]
