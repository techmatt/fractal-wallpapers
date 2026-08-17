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
"""

from __future__ import annotations

import json
from pathlib import Path

from fractal_wallpapers.curation import floors, records, sheet
from fractal_wallpapers.curation import run as run_module

#: The slug a retroactive bar rejection records. One value, because there is one
#: rule here; a rejection taken for any other cause is a different verdict and
#: would want its own.
BELOW_ACTING_BAR = "below_acting_bar"


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
    """
    out = []
    for row in records.served(rows):
        head = (row.get("scores") or {}).get("head")
        score = (row.get("scores") or {}).get("p_ge3")
        if head is None or score is None:
            continue
        bar = floors.release_bar(head)
        if bar is not None and not bar.seats(score):
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
        score = row["scores"]["p_ge3"]
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

    report = {
        "run": run,
        "rejector": rejector,
        "date": date,
        "dry_run": bool(dry_run),
        "release_rows": len(rows),
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


def redraw(run: str, log=print) -> Path:
    """Redraw a run's release sheet off its records as they now stand.

    The sheet is the release's derived view, it lives in the untracked run
    directory, and it is regenerated rather than patched — a page edited to drop
    a row is a page that can disagree with the record it came from.
    """
    directory = run_module.run_dir(run)
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
        "look cap": floors.CLUSTER_CAP,
        "junk floor": floors.JUNK_FLOOR,
        "good floor": floors.GOOD_FLOOR,
    }
    for head, value in sorted(floors.ACTING_RELEASE_BARS.items()):
        summary[f"{head} bar"] = f"{value:g} (acting)"
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
    "RejectionRefused",
    "apply",
    "below_acting_bar",
    "note_for",
    "redraw",
]
