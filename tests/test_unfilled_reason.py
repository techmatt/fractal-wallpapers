"""What an empty seat says emptied it, and whether the record can be believed.

The field a reader trusts when deciding whether under-fill is a **supply** problem
or a **colour** problem, and those have opposite remedies: one is answered by
lowering a floor or drawing more points, the other by loosening the ceiling. A
seat that names the floor when the floor was not what stopped it sends the reader
to the wrong one, which is what happened once already and is what
[`selection.binding_reason`] exists to stop.

**The seating that wrote these counters is gone** — it went with the pre-solver
gallery pass on 2026-08-28 — and the four passes' slot rows are still in the
history and still read. So what is pinned here is the reader and not the writer:
the defect off the record that produced it, and that the reader's whole range is
in the vocabulary. The four tests that drove a seating into each state went with
the seating; the states themselves are stated below out of the tracked row's own
counts, which is what a reader of those rows has to work from anyway.
"""

from __future__ import annotations

import json

from fractal_wallpapers.curation import records, selection

#: The pass whose record the defect was found on. History, and the only pass
#: whose slot rows this file reads.
PASS = "gallery4"

#: The seat that recorded the wrong constraint, and the file it is recorded in.
SEAT, SEAT_PARTITION = "0153", "julia_mandelbrot"


def reason_of(fill: dict) -> str:
    """The binding reason off one tracked slot row's own four counters.

    A row from a pass seated with no ceiling carries no ceiling block at all, and
    that reads as two zeroes rather than as a missing count: no colour rule turned
    anything away because there was no colour rule.
    """
    ceiling = fill.get("ceiling") or {}
    return selection.binding_reason(
        fill["below_floor"],
        fill["location_served"],
        ceiling.get("refused", 0),
        ceiling.get("withheld", 0),
    )


# --------------------------------------------------------------------------- #
# 1. The defect, off the record that produced it.
# --------------------------------------------------------------------------- #
def test_the_one_empty_seat_on_the_tracked_pass_names_the_location_rule() -> None:
    """It recorded `below_bar` while its best candidate sat 0.31 over the floor.

    Read off the tracked slot row and not re-derived: every count the reason is
    chosen from is on the record, so the true one is recoverable without seating
    anything again. The claim is not that the floor turned nothing away — 27 of
    its 30 candidates were under it — but that the three which cleared it were
    stopped by the one-wallpaper-per-location rule, and lowering the floor would
    not have seated any of them.
    """
    path = records.root() / "gallery" / PASS / f"{SEAT_PARTITION}.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    row = next(entry for entry in rows if entry["id"] == SEAT)
    fill = row["fill"]

    assert row["seated"] is None, "the seat this test is about is the empty one"
    assert fill["best"]["p_ge3"] > fill["floor"]["value"], "its best candidate cleared the floor"
    assert fill["ceiling"]["refused"] == 0, "and the colour ceiling refused nothing here"
    assert fill["below_floor"] + fill["location_served"] == fill["eligible"], "all 30 accounted"
    assert fill["location_served"] > 0, "the floor-clearers were turned away by the location rule"

    assert row["unfilled"] == "below_bar", "what the pass wrote"
    assert reason_of(fill) == selection.LOCATION_SERVED, "what actually bound it"


def test_every_empty_seat_in_the_history_is_re_readable_from_its_own_counts() -> None:
    """The reader works over every slot row on record, not only the one defect.

    A row whose counters do not partition the candidates it saw is a row nothing
    can re-read, and that would make the check above a fact about one seat rather
    than a property of the store.
    """
    empty = 0
    for directory in sorted((records.root() / "gallery").iterdir()):
        for path in sorted(directory.glob("*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("seated") is not None or not row.get("fill"):
                    continue
                empty += 1
                assert reason_of(row["fill"]) in selection.UNFILLED_REASONS
    assert empty, "the history holds no empty seat, so this proves nothing"


# --------------------------------------------------------------------------- #
# 2. The vocabulary.
# --------------------------------------------------------------------------- #
def test_the_deepest_rule_a_candidate_reached_is_the_one_named() -> None:
    """The whole rule, stated over the four counters it reads.

    `withheld` is the ceiling acting *before* the floor, so it is outside the
    depth order and cannot be the deepest anything reached: beside another rule's
    refusals it makes the seat `mixed`, and alone it is the ceiling.
    """
    assert selection.binding_reason(0, 0, 0, 0) == "no_candidates"
    assert selection.binding_reason(27, 0, 0, 0) == "below_bar"
    assert selection.binding_reason(27, 3, 0, 0) == selection.LOCATION_SERVED, "the defect"
    assert selection.binding_reason(27, 3, 1, 0) == "ceiling", "deeper still"
    assert selection.binding_reason(0, 0, 0, 3) == "ceiling", "held back and nothing else acted"
    assert selection.binding_reason(1, 0, 0, 3) == "mixed", "no single rule accounts for it"
    assert selection.binding_reason(0, 1, 0, 3) == "mixed"


def test_every_reason_a_seat_can_record_is_in_the_vocabulary() -> None:
    """The slug is a key into the descriptions, so an unlisted one is a KeyError."""
    seen = {
        selection.binding_reason(below, capped, refused, withheld)
        for below in (0, 1)
        for capped in (0, 1)
        for refused in (0, 1)
        for withheld in (0, 1)
    }
    assert seen == {"below_bar", "location_served", "ceiling", "mixed", "no_candidates"}
    assert seen <= set(selection.UNFILLED_REASONS)
