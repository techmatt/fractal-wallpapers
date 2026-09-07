"""What an empty seat says emptied it, and whether the record can be believed.

The field a reader trusts when deciding whether under-fill is a **supply** problem
or a **colour** problem, and those have opposite remedies: one is answered by
lowering a floor or drawing more points, the other by loosening the ceiling. A
seat that names the floor when the floor was not what stopped it sends the reader
to the wrong one, which is what happened once already and is what
[`selection.binding_reason`] exists to stop.

**The seating that wrote these counters is gone** — it went with the pre-solver
gallery pass on 2026-08-28 — and **the slot rows it wrote went on 2026-09-06**,
with the rest of the four passes' store. So what is pinned here is the reader and
not the writer: the defect off the counts that produced it, and that the reader's
whole range is in the vocabulary. The four tests that drove a seating into each
state went with the seating; the states themselves are stated below out of the
counts, which is what a reader of those rows had to work from anyway.

**The population is carried here as data, and that is a faithful stand-in rather
than a weakening.** Nine empty seats over four passes is the whole of it, nothing
can write a tenth, and every count `binding_reason` reads is in the table — so the
guard runs over exactly the population it ran over when the rows were on disk.
"""

from __future__ import annotations

from fractal_wallpapers.curation import selection

#: The pass whose record the defect was found on, and the seat. History.
PASS, SEAT = "gallery4", "0153"

#: **Every empty seat the four retired gallery passes recorded**, read out of
#: `data/curation/gallery/<pass>/<partition>.jsonl` before that store was deleted:
#: `(pass, seat, below_floor, location_served, refused, withheld, unfilled)`. The
#: first four are what [`selection.binding_reason`] reads; the last is what the
#: pass itself wrote, which is the thing the defect is a disagreement with.
EMPTY_SEATS = (
    ("gallery1", "0008", 18, 0, 0, 0, "below_bar"),
    ("gallery1", "0011", 22, 0, 0, 0, "below_bar"),
    ("gallery1", "0017", 18, 0, 0, 0, "below_bar"),
    ("gallery1", "0021", 18, 0, 0, 0, "below_bar"),
    ("gallery1", "0026", 6, 0, 0, 0, "below_bar"),
    ("gallery1", "0028", 20, 0, 0, 0, "below_bar"),
    ("gallery1", "0043", 6, 0, 0, 0, "below_bar"),
    ("gallery1", "0046", 20, 0, 0, 0, "below_bar"),
    ("gallery4", "0153", 27, 3, 0, 0, "below_bar"),
)

#: The defect seat's own arithmetic, off the same row: how many candidates it saw,
#: the acting floor, and what its best candidate read against that floor.
DEFECT_ELIGIBLE = 30
DEFECT_FLOOR = 0.575
DEFECT_BEST_P_GE3 = 0.881260189693845


def reason_of(seat: tuple) -> str:
    """The binding reason off one slot row's own four counters.

    A row from a pass seated with no ceiling carried no ceiling block at all, and
    that reads as two zeroes rather than as a missing count: no colour rule turned
    anything away because there was no colour rule. That is why the table's last
    two columns are zero throughout and not absent.
    """
    _pass, _seat, below, served, refused, withheld = seat[:6]
    return selection.binding_reason(below, served, refused, withheld)


# --------------------------------------------------------------------------- #
# 1. The defect, off the record that produced it.
# --------------------------------------------------------------------------- #
def test_the_one_empty_seat_on_the_tracked_pass_names_the_location_rule() -> None:
    """It recorded `below_bar` while its best candidate sat 0.31 over the floor.

    Read off the counts the slot row carried and not re-derived: every count the
    reason is chosen from was on the record, so the true one is recoverable without
    seating anything again. The claim is not that the floor turned nothing away —
    27 of its 30 candidates were under it — but that the three which cleared it
    were stopped by the one-wallpaper-per-location rule, and lowering the floor
    would not have seated any of them.
    """
    seat = next(row for row in EMPTY_SEATS if (row[0], row[1]) == (PASS, SEAT))
    _pass, _seat, below, served, refused, withheld, wrote = seat

    assert DEFECT_BEST_P_GE3 > DEFECT_FLOOR, "its best candidate cleared the floor"
    assert refused == 0 and withheld == 0, "and the colour ceiling refused nothing here"
    assert below + served == DEFECT_ELIGIBLE, "all 30 accounted"
    assert served > 0, "the floor-clearers were turned away by the location rule"

    assert wrote == "below_bar", "what the pass wrote"
    assert reason_of(seat) == selection.LOCATION_SERVED, "what actually bound it"


def test_every_empty_seat_in_the_history_is_re_readable_from_its_own_counts() -> None:
    """The reader works over every slot row on record, not only the one defect.

    A row whose counters do not partition the candidates it saw is a row nothing
    can re-read, and that would make the check above a fact about one seat rather
    than a property of the record.
    """
    assert len(EMPTY_SEATS) == 9, "the whole population, and it cannot grow"
    for seat in EMPTY_SEATS:
        assert reason_of(seat) in selection.UNFILLED_REASONS, seat
    # Eight of the nine really were the floor and only the defect was not, which
    # is what makes the defect a defect rather than the normal case.
    disagree = [seat for seat in EMPTY_SEATS if reason_of(seat) != seat[6]]
    assert [(seat[0], seat[1]) for seat in disagree] == [(PASS, SEAT)]


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
