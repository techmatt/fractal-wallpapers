"""What changes hands when the seating order changes: two solves, one pool, one page.

A table saying an arm reads 0.68 where the incumbent reads 0.54 is a claim about
a statistic. Whether the seats that statistic moves are seats a person would
rather have is a different question, and only pictures answer it. This module
asks it the narrowest way there is: solve the same pool twice, once under the
shipped [`rank_key`] and once under the cascade, and lay out **only the rows
where the two disagree**.

## It decides nothing and ingests nowhere

No row here enters a store, no verdict is collected, nothing is pinned, and the
page is not a label instrument — it carries its captions in the open precisely so
that it cannot be mistaken for one. A blind sheet is how this project asks a
person for a *verdict*; this is how it shows them a *diff*.

⚠ **It uses the ledger's stored 640x360 pictures and renders nothing**, which is
a deliberate departure from the rule that a sheet is drawn fresh. Matt's call of
2026-09-06, for this sheet alone: the pictures are here to say what changed hands
and a re-render at release geometry would cost an hour to answer a question about
the ordering rather than about the pixels.

## Arriving and departing are one page and not two

A seat the cascade takes is only interesting beside the seat it took it from, so
both halves are on one page in **one order** — the fine head's, good to bad —
rather than in two grids a reader has to hold side by side. The mark on each card
says which direction it moved.

## The cap is a sample and says so

At most [`CAP`] cards, because a page of a thousand thumbnails is a page nobody
scrolls. If more rows differ, the sample is taken **evenly across the fine head's
score range** rather than off the top — the top of the order is the part both
keys mostly agree about, and a sample from there would show the least of what
changed. The true count is on the page and in the record.
"""

from __future__ import annotations

import json
from pathlib import Path

from fractal_wallpapers.paths import under

#: The schema every record here carries.
SCHEMA = 1

#: The subtree this leg's page and readout land in.
UNIT = "seat_sheet"

#: At most this many cards on the page. A hundred and fifty is what a person
#: scrolls in one sitting, and it is the size the four-arm before/after sheet
#: that adopted the shipped key ran at.
CAP = 150

#: How wide a thumbnail is drawn. [`curation.sheet`]'s, so two pages of this
#: project's pictures are the same size on screen.
THUMBNAIL_WIDTH = 320


class SeatSheetError(RuntimeError):
    """A diff that cannot be taken on what is here."""


def root() -> Path:
    return under("curation", UNIT)


def page_path(name: str) -> Path:
    return root() / str(name) / "sheet.html"


def record_path(name: str) -> Path:
    return root() / str(name) / "diff.json"


def seats_of(record: dict) -> dict:
    """`{candidate key: the seated row}` out of one solve record."""
    return {str(row["key"]): row for row in (record.get("seated") or [])}


def difference(incumbent: dict, candidate: dict) -> dict:
    """`{arriving, departing, kept, places}` between two solves of one pool.

    Keyed on the candidate rather than on the seat number, because the seat
    numbers renumber themselves under any reordering and a diff taken on them
    would call every row changed.

    **A changed seat is one of two quite different things and the row says
    which.** Either the two keys seat the same *place* and disagree about which
    candidate there deserves it, or one of them seats the place and the other
    does not — the gallery going somewhere else entirely. On 2026-09-07 the
    shipped pair split 166 of 827 the first way and 661 the second, so four
    fifths of the churn was places rather than candidates, and a page that did
    not distinguish them showed one number where there were two.
    """
    before, after = seats_of(incumbent), seats_of(candidate)
    was = {str(row.get("location")) for row in before.values()}
    now = {str(row.get("location")) for row in after.values()}
    shared = was & now

    def marked(row: dict) -> dict:
        return {**row, "place_seated": "both" if str(row.get("location")) in shared else "one"}

    arriving = [marked(after[key]) for key in after if key not in before]
    departing = [marked(before[key]) for key in before if key not in after]
    return {
        "arriving": arriving,
        "departing": departing,
        "kept": len(set(before) & set(after)),
        "before": len(before),
        "after": len(after),
        "places": {
            "before": len(was),
            "after": len(now),
            "shared": len(shared),
            "changed_at_a_shared_place": sum(
                1 for row in arriving + departing if row["place_seated"] == "both"
            ),
            "changed_because_the_place_moved": sum(
                1 for row in arriving + departing if row["place_seated"] == "one"
            ),
        },
    }


def sampled(rows: list[dict], cap: int = CAP) -> tuple[list[dict], dict]:
    """At most `cap` rows, taken evenly across the fine head's score range.

    `fine_score` is the fine head's own `P(>=4)`, which is what the cascade orders
    on. Evenly across the **range** and not off the top: the two keys mostly agree
    about the very best rows, so a top slice of a diff is the part of it with
    least to show. Sorted good to bad on the way out either way.
    """
    ordered = sorted(rows, key=lambda row: (-float(row.get("fine_score") or 0.0), row["key"]))
    if len(ordered) <= cap:
        return ordered, {"of": len(ordered), "shown": len(ordered), "sampled": False}
    step = len(ordered) / float(cap)
    taken = [ordered[min(len(ordered) - 1, int(index * step))] for index in range(cap)]
    return taken, {
        "of": len(ordered),
        "shown": len(taken),
        "sampled": True,
        "rule": "every nth row of the fine head's own order, so the whole range is represented",
    }


def _card(row: dict) -> str:
    from fractal_wallpapers.curation import sheet
    from fractal_wallpapers.paths import Tiers, rehome

    picture = rehome(str(row.get("picture") or ""), Tiers.current())
    source = "" if picture is None else sheet.thumbnail(picture, THUMBNAIL_WIDTH)
    moved = row["moved"]
    place = str(row.get("place_seated") or "both")
    facts = [
        f"{row.get('mode') or '?'} &middot; {row.get('cell') or 'no cell'}",
        f'place <span class="place {place}">seated by '
        + ("both keys" if place == "both" else "one key only")
        + "</span>",
        f"fine P(&ge;4) {_number(row.get('fine_score'))}"
        f" &middot; judge p_ge4 {_number(row.get('p_ge4'))}",
        f"rank key {_number(row.get('rank_key'))}",
        f"<span class=key>{row['key']}</span>",
    ]
    return (
        f'<figure class="card {moved}">'
        + (
            f'<img loading="lazy" src="{source}">'
            if source
            else '<div class="gone">no picture</div>'
        )
        + f'<figcaption><span class="badge {moved}">{moved}</span>'
        + "".join(f"<span>{fact}</span>" for fact in facts)
        + "</figcaption></figure>"
    )


def _number(value) -> str:
    return "—" if value is None else f"{float(value):.4f}"


PAGE = """<!doctype html>
<meta charset="utf-8"><title>seats the cascade moves &mdash; {name}</title>
<style>
 body {{ font: 13px/1.45 system-ui, sans-serif; margin: 1.5rem;
         background: #14161a; color: #dfe3e8; }}
 h1 {{ font-size: 1.15rem; margin: 0 0 .35rem; }}
 .lede {{ max-width: 62rem; color: #9aa4b1; margin: 0 0 1.25rem; }}
 .lede b {{ color: #dfe3e8; }}
 .grid {{ display: grid; gap: 1rem; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); }}
 figure {{ margin: 0; background: #1c1f26; border-radius: 6px; overflow: hidden;
           border: 2px solid transparent; }}
 figure.arriving {{ border-color: #3f8f5c; }}
 figure.departing {{ border-color: #96434a; }}
 img {{ display: block; width: 100%; }}
 .gone {{ padding: 3rem 1rem; text-align: center; color: #6b7480; }}
 figcaption {{ display: flex; flex-direction: column; gap: .15rem; padding: .5rem .6rem .6rem; }}
 .badge {{ align-self: flex-start; font-weight: 600; letter-spacing: .03em;
           text-transform: uppercase; font-size: .7rem; padding: .1rem .4rem;
           border-radius: 3px; margin-bottom: .2rem; }}
 .badge.arriving {{ background: #3f8f5c; color: #0b1410; }}
 .badge.departing {{ background: #96434a; color: #1a0c0d; }}
 .key {{ font-family: ui-monospace, monospace; color: #6b7480; font-size: .72rem; }}
 .place.both {{ color: #d8b45a; }}
 .place.one {{ color: #7fa8d8; }}
</style>
<h1>Seats the cascade moves &mdash; {name}</h1>
<p class="lede">{lede}</p>
<div class="grid">{cards}</div>
"""


def build(name: str, diff: dict, cap: int = CAP, log=print) -> tuple[Path, dict]:
    """Write the page and its readout. Returns `(page, record)`."""
    rows = [{**row, "moved": "arriving"} for row in diff["arriving"]] + [
        {**row, "moved": "departing"} for row in diff["departing"]
    ]
    if not rows:
        raise SeatSheetError(
            "the two keys seated exactly the same candidates, so there is no diff to show. "
            "That is a finding and not a failure — record it rather than building a page."
        )
    shown, sampling = sampled(rows, cap)
    places = diff.get("places") or {}
    lede = (
        f"<b>{diff['before']}</b> seats under the shipped rank key, <b>{diff['after']}</b> under "
        f"the cascade, <b>{diff['kept']}</b> of them the same candidate. "
        f"<b>{len(diff['arriving'])}</b> arrive and <b>{len(diff['departing'])}</b> depart"
        + (
            f", of which <b>{places['changed_at_a_shared_place']}</b> sit at a place both keys "
            f"seat and <b>{places['changed_because_the_place_moved']}</b> are the gallery going "
            f"somewhere else ({places['shared']} places shared)"
            if places
            else ""
        )
        + f". <b>{sampling['shown']}</b> of those {sampling['of']} are on this page"
        + (", sampled evenly across the fine head's score range" if sampling["sampled"] else "")
        + ". Sorted good to bad by the fine head. Pictures are the ledger's stored 640&times;360 "
        "candidates &mdash; nothing was re-rendered, and this page ingests nowhere."
    )
    page = PAGE.format(name=name, lede=lede, cards="".join(_card(row) for row in shown))
    where = page_path(name)
    where.parent.mkdir(parents=True, exist_ok=True)
    where.write_text(page, encoding="utf-8", newline="\n")

    record = {
        "schema": SCHEMA,
        "name": str(name),
        "seats": {"before": diff["before"], "after": diff["after"], "kept": diff["kept"]},
        # The other half of the churn, and the one a seat count hides: whether a
        # changed seat is a different candidate at a place both keys hold, or a
        # place one of them does not hold at all.
        "places": places,
        "changed": len(diff["arriving"]) + len(diff["departing"]),
        "arriving": len(diff["arriving"]),
        "departing": len(diff["departing"]),
        "sheet": sampling,
        "page": str(where),
        "is": (
            "a diff for a person to look at. No row enters a store, nothing is pinned, and "
            "this is not a label instrument — the captions are open for that reason"
        ),
    }
    record_path(name).write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    log(
        f"[seat-sheet] {record['changed']} seat(s) differ "
        f"({record['arriving']} in, {record['departing']} out); {sampling['shown']} on the page"
    )
    return where, record


__all__ = [
    "CAP",
    "SCHEMA",
    "THUMBNAIL_WIDTH",
    "UNIT",
    "SeatSheetError",
    "build",
    "difference",
    "page_path",
    "record_path",
    "root",
    "sampled",
    "seats_of",
]
