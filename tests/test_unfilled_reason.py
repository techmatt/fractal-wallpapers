"""What an empty seat says emptied it, and whether the record can be believed.

The field a reader trusts when deciding whether under-fill is a **supply** problem
or a **colour** problem, and those have opposite remedies: one is answered by
lowering a floor or drawing more points, the other by loosening the ceiling. A
seat that names the floor when the floor was not what stopped it sends the reader
to the wrong one, which is what happened once already and is what
[`gallery.binding_reason`] exists to stop.

The candidates here are **real released rows off the tracked store**, adapted the
way a pass adapts them, so the scores the floor acts on are scores a head actually
produced over pictures that shipped. The colour side is stated rather than
measured — the pictures themselves are not in the history — which is the same
split `tests/test_curation_ceiling.py` makes and for the same reason.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.curation import ceiling, floors, gallery, records, selection
from test_curation_ceiling import Eyes, quiet, red

#: The pass whose record the defect was found on, and the pass these candidates
#: are read out of. Two separate uses of one name: the first is history and the
#: second is only "a tracked pass with released rows in it".
PASS = "gallery4"
STRANGE = "strange_render"

#: The seat that recorded the wrong constraint, and the file it is recorded in.
SEAT, SEAT_PARTITION = "0153", "julia_mandelbrot"


def released(partition: str) -> list[dict]:
    """One partition's released rows, as the flat candidate rows a seat compares."""
    path = records.root() / "release" / PASS / f"{partition}.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    out = [gallery.candidate_of_pool_row(row) for row in rows]
    return [row for row in out if row["head"] == STRANGE and row.get("p_ge3") is not None]


@pytest.fixture(scope="module")
def shipped() -> list[dict]:
    """Four real strange-head candidates, each at its own place, each over the floor."""
    floor = floors.gallery_floor(STRANGE)
    pool = [row for row in released("mandelbrot") if floor.acts(row["p_ge3"])][:4]
    assert len(pool) == 4, "the tracked pass has fewer released rows than this test reads"
    return pool


def one_group(pool: list[dict]) -> Eyes:
    """A lens under which every one of these candidates is the same look.

    One palette group and one pixel cloud, so the group cap refuses everything
    after the first seat and the exemption distance cannot rescue any of it.
    """
    names = [str(row["candidate"]) for row in pool]
    return Eyes(
        colours=dict.fromkeys(names, red()),
        clouds=dict.fromkeys(names, 0.0),
        palettes=dict.fromkeys(names, "m01"),
    )


def seats(pool: list[dict], first: int = 1) -> list:
    """`first` slots on the leading candidates, then one slot on all the rest.

    One partition throughout, so [`gallery._seat_order`] leaves them in list order
    and the last slot is the one that meets a state the others left behind.
    """
    out = []
    for index, row in enumerate(pool[:first]):
        slot = gallery.Slot(
            id=f"{index:04d}", partition="mandelbrot", head=STRANGE, point=row["key"]
        )
        slot.locations = [row["key"]]
        out.append(slot)
    last = gallery.Slot(
        id=f"{first:04d}", partition="mandelbrot", head=STRANGE, point=pool[first]["key"]
    )
    last.locations = [row["key"] for row in pool[first:]]
    return [*out, last]


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
    assert (
        gallery.binding_reason(
            fill["below_floor"], fill["location_served"], fill["ceiling"]["refused"], 0
        )
        == selection.LOCATION_SERVED
    ), "what actually bound it"


# --------------------------------------------------------------------------- #
# 2. The constraints, told apart.
# --------------------------------------------------------------------------- #
def test_a_seat_whose_floor_clearers_were_all_refused_by_the_ceiling_names_the_ceiling(
    shipped,
) -> None:
    """The counts come off a real seating; the expected reason is written out.

    The seat has to be driven to the state first — three candidates over the
    floor, at three unserved places, every one refused — because a reason rule fed
    numbers somebody chose proves only that the numbers were chosen to fit.
    """
    slots = seats(shipped)
    gallery.seat(slots, list(shipped), log=quiet, rule=ceiling.Rule(one_group(shipped)))
    fill = slots[1].fill

    assert fill["below_floor"] == 0, "nothing this seat saw was under the floor"
    assert fill["location_served"] == 0, "and no place of its was already served"
    assert fill["ceiling"]["refused"] == 3, "every candidate it had, refused by the ceiling"
    assert fill["ceiling"]["refused_by"] == {"group": 3}, "and the record names which test"

    assert (
        gallery.binding_reason(
            fill["below_floor"], fill["location_served"], fill["ceiling"]["refused"], 0
        )
        == "ceiling"
    )


def test_the_fallback_is_why_that_seat_is_not_empty_and_so_never_records_it(shipped) -> None:
    """A refusal cannot leave a seat empty while the least-violating fallback stands.

    So the `ceiling` branch above is unreachable through a seating today, and the
    reason it is written anyway is that the fallback is a policy: the colours are
    advisory exactly once, at the seat of last resort. Pinned rather than
    commented, so the day that moves the suite says which claim moved with it.
    """
    slots = seats(shipped)
    report = gallery.seat(slots, list(shipped), log=quiet, rule=ceiling.Rule(one_group(shipped)))
    assert slots[1].seated is not None, "seated by the fallback, not by clearing anything"
    assert slots[1].unfilled is None
    assert len(report["ceiling"]["fallbacks"]) == 1


def test_a_mandate_that_holds_back_the_pool_says_so_and_will_not_name_one_rule(shipped) -> None:
    """The ceiling acting BEFORE the floor, which is the reachable colour bind.

    A cell the pass owes and cannot reach narrows the seat's sequence to that
    cell's carriers ([`ceiling.State.steer`]), and a candidate dropped there is
    never tested by anything. Where the survivors then fall under the floor,
    neither rule accounts for the seat on its own: the record says `mixed` and
    leaves the counts to say the rest.
    """
    names = [str(row["candidate"]) for row in shipped]
    carrier, *rest = names
    eyes = Eyes(
        colours={carrier: {"dark_vivid_green": 1.0}, **dict.fromkeys(rest, red())},
        clouds=dict.fromkeys(names, 0.0),
        palettes={name: f"m{index:02d}" for index, name in enumerate(names)},
    )
    # The one candidate the mandate lets through is the one under the floor, so
    # the seat empties on the floor while the ceiling is what removed the rest.
    pool = [{**shipped[0], "p_ge3": 0.1}, *shipped[1:]]
    rule = ceiling.Rule(eyes, targets={"dark_vivid_green": 1.0})
    slot = gallery.Slot(id="0000", partition="mandelbrot", head=STRANGE, point=pool[0]["key"])
    slot.locations = [row["key"] for row in pool]

    gallery.seat([slot], pool, log=quiet, rule=rule)
    assert slot.seated is None
    assert slot.fill["eligible"] == 4
    assert slot.fill["below_floor"] == 1, "the only candidate the mandate admitted"
    assert slot.fill["ceiling"]["withheld"] == 3, "and the three it did not"
    assert slot.fill["ceiling"]["refused"] == 0, "none of which any test ever saw"
    assert slot.unfilled == "mixed"
    assert slot.fill["why"] == selection.UNFILLED_REASONS["mixed"]


def test_the_reasons_that_were_right_before_are_still_what_they_were(shipped) -> None:
    """Nothing under the floor, no place taken, no ceiling: the old three, unmoved."""
    floor = floors.gallery_floor(STRANGE)
    under = [{**row, "p_ge3": floor.value - 0.01} for row in shipped]
    empty = gallery.Slot(id="0000", partition="mandelbrot", head=STRANGE, point=under[0]["key"])
    empty.locations = [row["key"] for row in under]
    gallery.seat([empty], under, log=quiet)
    assert empty.unfilled == "below_bar"

    nowhere = gallery.Slot(id="0000", partition="mandelbrot", head=STRANGE, point="nobody")
    nowhere.locations = ["nobody"]
    gallery.seat([nowhere], list(shipped), log=quiet)
    assert nowhere.unfilled == "no_candidates"

    slots = seats(shipped, first=3)
    slots[3].locations = [row["key"] for row in shipped[:3]]
    gallery.seat(slots, list(shipped), log=quiet)
    assert slots[3].unfilled == selection.LOCATION_SERVED


def test_every_reason_a_seat_can_record_is_in_the_vocabulary() -> None:
    """The slug is a key into the descriptions, so an unlisted one is a KeyError."""
    seen = {
        gallery.binding_reason(below, capped, refused, withheld)
        for below in (0, 1)
        for capped in (0, 1)
        for refused in (0, 1)
        for withheld in (0, 1)
    }
    assert seen == {"below_bar", "location_served", "ceiling", "mixed", "no_candidates"}
    assert seen <= set(selection.UNFILLED_REASONS)
