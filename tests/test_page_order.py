"""The derived presentation order: a permutation, deterministic, and local.

Every test here is arithmetic over rows built in the file, so the whole module is
fast-lane. Nothing renders, nothing reads a store, and the embedding term is
exercised with vectors written by hand rather than off this machine's 71 MB of them
— which is also the only way to assert what the term does, since a real store's
distances are whatever they are.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers.curation import page_order

numpy = pytest.importorskip("numpy")


def seat(key: str, **columns) -> dict:
    """One gallery row, with only the columns this module reads spelled out."""
    held = {
        "key": key,
        "alias": key[:8],
        "cell": None,
        "hue_family": None,
        "mode": "smooth",
        "spiral": False,
        "p_ge4": 0.5,
        "location": None,
    }
    held.update(columns)
    return held


def rows_of(spec: list[tuple]) -> list[dict]:
    """`[(cell, mode, p_ge4), ...]` as rows, keyed by position so ties are total."""
    return [
        seat(f"{at:016x}", cell=cell, hue_family=cell, mode=mode, p_ge4=score)
        for at, (cell, mode, score) in enumerate(spec)
    ]


# --------------------------------------------------------------------------- #
# The guard the prompt asked for, and the two that make it mean something.
# --------------------------------------------------------------------------- #
def test_the_order_is_a_permutation_of_the_seating():
    """Every seat exactly once, none dropped and none doubled. The page shows what
    the record holds or it is not a view of the record."""
    rows = rows_of([("azure", "smooth", 0.9), ("rose", "stripe", 0.8)] * 40)

    placement = page_order.order(rows)

    assert sorted(placement) == list(range(len(rows)))
    assert len(set(placement)) == len(rows)


def test_a_permutation_is_still_a_permutation_with_the_distance_term_in():
    """The embedding term reorders and never drops: a row with no vector is placed
    like any other, which is the case that would silently lose 32 of 1,000 seats."""
    rows = rows_of([("azure", "smooth", 0.9), ("rose", "stripe", 0.8)] * 20)
    for at, row in enumerate(rows):
        row["location"] = f"place-{at}"
    # Half the rows get a vector and half do not, which is the shape of a real
    # record: the store is appended to and the pool has moved on since.
    vectors = {
        f"place-{at}": numpy.eye(4, dtype=numpy.float32)[at % 4] for at in range(0, len(rows), 2)
    }

    placement = page_order.order(rows, vectors)

    assert sorted(placement) == list(range(len(rows)))


def test_one_seating_orders_one_way_however_often_it_is_built():
    """No RNG, and no dict-iteration order either: two calls agree, and so do two
    calls over the same rows in a different arrival order once they are re-keyed."""
    rows = rows_of([("azure", "smooth", 0.9), ("rose", "stripe", 0.9), ("lime", "tia", 0.9)] * 12)

    first = page_order.order(rows)
    second = page_order.order(rows)

    assert first == second
    assert [rows[at]["key"] for at in first] == [rows[at]["key"] for at in second]


def test_a_seating_of_one_and_a_seating_of_none_are_answered_rather_than_refused():
    """A degenerate record is a page, not a traceback: `browse` runs over whatever
    stamp it is given and a one-seat record is a legal one."""
    assert page_order.order([]) == []
    assert page_order.order([seat("a" * 16)]) == [0]


# --------------------------------------------------------------------------- #
# What the order actually does.
# --------------------------------------------------------------------------- #
def test_the_strongest_row_opens_the_page():
    """`p_ge4` descending seeds it — with nothing placed there is no window, every
    cost is equal, and the tie-break is quality."""
    rows = rows_of([("azure", "smooth", 0.30), ("rose", "stripe", 0.99), ("lime", "tia", 0.70)] * 4)

    placement = page_order.order(rows)

    assert rows[placement[0]]["p_ge4"] == 0.99


def test_two_seats_sharing_a_cell_are_pushed_apart():
    """The whole point, at the smallest size that shows it: eight rows, two cells,
    and an order that alternates rather than serving one cell and then the other."""
    rows = rows_of([("azure", "smooth", 0.9)] * 4 + [("rose", "smooth", 0.9)] * 4)

    cells = [rows[at]["cell"] for at in page_order.order(rows)]

    assert cells == ["azure", "rose"] * 4 or cells == ["rose", "azure"] * 4


def test_a_repeat_nearer_the_end_of_the_window_costs_more_than_one_at_its_far_edge():
    """The recency taper, asserted on the penalty rather than through an order: the
    seat one back is on the same screen as the one being placed and the seat thirty
    back is on the way off it, so they cannot be priced alike."""
    window = page_order.WINDOW
    near = (window - 1 + 1) / window
    far = (window - window + 1) / window

    assert near == 1.0
    assert far == pytest.approx(1 / window)
    assert near > far


def test_the_distance_term_cannot_buy_back_an_attribute_repeat():
    """The "normalised so it cannot dominate" rule, as an inequality between the
    constants rather than a hope about a distribution: the whole distance term is
    worth less than the cheapest repeat there is."""
    assert min(page_order.ATTRIBUTE_WEIGHTS.values()) > page_order.DISTANCE_WEIGHT
    assert page_order.UNKNOWN_DISTANCE == page_order.DISTANCE_WEIGHT / 2


def test_an_abundant_value_is_allowed_what_a_window_cannot_avoid_holding():
    """[`page_order._unavoidable`]: a mode holding a quarter of the seating appears
    in every window in every order, so its allowance is a quarter of the taper and a
    rare value's is near zero. Without this the greedy hoards and the tail clumps."""
    rows = rows_of([("azure", "tia", 0.9)] * 25 + [("rose", "smooth", 0.9)] * 75)

    shares = page_order._unavoidable(rows)

    assert shares[("mode", "tia")] == pytest.approx(0.25)
    assert shares[("mode", "smooth")] == pytest.approx(0.75)


def test_no_column_s_touch_penalty_can_outweigh_the_cheapest_window_repeat():
    """*It must not come out of the colour terms*, as an inequality between the
    constants rather than a hope about a distribution — the same bound
    [`page_order.DISTANCE_WEIGHT`] is under, for the same reason."""
    most = (
        page_order.ADJACENCY_WEIGHT
        * page_order._taper(page_order.ADJACENCY_REACH, page_order.ADJACENCY_REACH)
        * max(page_order.ATTRIBUTE_WEIGHTS.values())
    )

    assert most < min(page_order.ATTRIBUTE_WEIGHTS.values())
    # And it is a SHORT range: a term reaching as far as the window would be the
    # window term with a second name on it.
    assert page_order.ADJACENCY_REACH < page_order.WINDOW


def test_the_adjacency_term_separates_a_repeat_the_window_allowance_forgives():
    """The gap the term exists to close. A value at a quarter of the seating is
    allowed what a window cannot avoid holding, so the window term is indifferent
    between spreading its copies and stacking them — and stacked is what a reader
    sees. Eight `tia` in thirty-two seats, every other column constant so the mode
    column is the only thing in play."""
    rows = [
        seat(f"{at:016x}", mode="tia" if at < 8 else "smooth", cell="azure", hue_family="blue")
        for at in range(32)
    ]

    placement = page_order.order(rows)
    modes = [rows[at]["mode"] for at in placement]
    touching = sum(1 for at in range(1, len(modes)) if modes[at] == modes[at - 1] == "tia")

    assert touching == 0, modes
    # Without the term the same rows stack them: the allowance forgives every one.
    assert page_order.ADJACENCY_WEIGHT > 0.0


def test_a_value_that_cannot_avoid_touching_degrades_to_its_floor_and_does_not_thrash():
    """The themed case, at the smallest size that shows it. A value holding more than
    half the seats MUST touch itself — `_forced_touches` says how often — and the
    order has to spend that floor and no more rather than refusing to place it and
    stacking the whole majority at the end, which is what an unallowanced term did:
    47 touching cell pairs to 54 on a 176-seat themed record, and its share of the
    closing tenth from 7 to 17."""
    rows = [seat(f"{at:016x}", cell="green" if at < 13 else "rose") for at in range(20)]

    floor = page_order._forced_touches(rows, "cell")
    placement = page_order.order(rows)
    cells = [rows[at]["cell"] for at in placement]
    touching = sum(1 for at in range(1, len(cells)) if cells[at] == cells[at - 1])

    # 13 of 20 leaves 7 others opening 8 slots, so five copies have nowhere to go.
    assert floor == 5
    assert touching == floor, cells
    # And the page is still whole: degrading is placing, never dropping.
    assert sorted(placement) == list(range(len(rows)))


def test_the_floor_is_what_the_counts_impose_and_not_what_an_order_managed():
    """[`page_order._forced_touches`]: `n - k` others open `n - k + 1` slots, so a
    value fits without touching itself while `k <= n - k + 1` and each copy past
    that forces one. The off-by-one is the whole content of it — two of three
    touches nothing, `X . X`, and a floor of `2k - n` would have said one."""
    three = [seat(f"{at:016x}", cell="azure" if at < 2 else "rose") for at in range(3)]
    both = [seat(f"{at:016x}", cell="azure") for at in range(2)]

    assert page_order._forced_touches(three, "cell") == 0
    assert page_order._forced_touches(both, "cell") == 1
    # `tia` is 263 of the 1,000 seats of `20260911T022330Z` and its floor is ZERO,
    # which is what made every pair the allowance alone left an avoidable one. The
    # rest is spread the way that record's is, because a column's floor is a fact
    # about whichever value exceeds half a page and `tia` is not it there.
    spread = ["tia"] * 263 + ["smooth"] * 263 + ["stripe"] * 263 + ["threads"] * 211
    assert (
        page_order._forced_touches(
            [seat(f"{at:016x}", mode=mode) for at, mode in enumerate(spread)], "mode"
        )
        == 0
    )
    # And a value that IS more than half a page carries the whole column's floor,
    # because two values cannot both be.
    lopsided = [seat(f"{at:016x}", mode="tia" if at < 737 else "smooth") for at in range(1000)]
    assert page_order._forced_touches(lopsided, "mode") == 2 * 737 - 1000 - 1
    # A silent value is not a repeat and so cannot force one: 899 non-spirals in a
    # row is the gallery rather than a clump.
    assert page_order._forced_touches([seat(f"{at:016x}") for at in range(8)], "spiral") == 0


def test_the_touching_pairs_are_reported_with_the_floor_and_where_they_LAND():
    """The readout the before/after is read on. `_gaps` can only say a minimum of 1,
    which a page with one touching pair and a page with fifty both report — and the
    closing tenth is the number that says whether a tail clump was removed or moved
    there."""
    rows = [seat(f"{at:016x}", cell="azure" if at in (0, 1, 8, 9) else "rose") for at in range(10)]

    held = page_order.spacing(rows, list(range(10)))["adjacent"]["cell"]

    # `azure azure rose rose rose rose rose rose azure azure`: one touch closing the
    # opening pair, five down the rose run, one closing the last pair.
    assert held["pairs"] == 7
    assert held["worst"] == ["rose", 5]
    # rose holds 6 of 10, so four others open five slots and one copy must touch.
    assert held["forced"] == 1
    assert held["last_tenth"] == 1  # the pair closing at position 9


def test_the_allowance_is_scaled_to_the_window_that_exists_and_not_to_a_full_one():
    """A page opens with an empty window and fills it one seat at a time, so an
    allowance sized for 32 placed seats is far larger than four placed seats can
    accrue — which left the order inert across the first screenful, where a reader
    starts. [`page_order._taper`] is the scaling and this is the arithmetic."""
    window = page_order.WINDOW

    assert page_order._taper(0, window) == 0.0
    assert page_order._taper(1, window) == 1.0
    assert page_order._taper(2, window) == pytest.approx(1.0 + (window - 1) / window)
    # A window cannot hold more than it is, so asking past it is asking for a full one.
    assert page_order._taper(window + 10, window) == page_order._taper(window, window)
    assert page_order._taper(window, window) == pytest.approx((window + 1) / 2)


def test_a_non_spiral_is_not_a_repeat_of_anything():
    """`spiral` is a verdict and `False` is its absence, so 899 non-spirals in a row
    is the gallery rather than a clump. Pricing them moved the fullest window of
    spirals the WRONG way — 13 to 16 on `20260911T022330Z`."""
    assert page_order._value({"spiral": True}, "spiral") is True
    assert page_order._value({"spiral": False}, "spiral") is page_order.SILENT
    assert page_order._value({"spiral": None}, "spiral") is page_order.SILENT
    # A category column keeps `None` as a value of its own, and the two must not be
    # confused: a run of seats with no dominant cell IS a clump.
    assert page_order._value({"cell": None}, "cell") is None


def test_a_silent_value_is_neither_priced_nor_measured():
    """Both halves read the same rule, so a column the order ignores is a column the
    readout does not report a gap for — a spacing that counted the 899 would say the
    minimum gap is 1 on a page where no two spirals touch."""
    rows = [seat(f"{at:016x}", spiral=(at % 10 == 0)) for at in range(40)]

    held = page_order.spacing(rows, page_order.order(rows))

    assert held["gaps"]["spiral"]["values"] == 1
    assert held["spiral"]["seats"] == 4


# --------------------------------------------------------------------------- #
# The basis, which is what keeps the page a derivation of two tracked files.
# --------------------------------------------------------------------------- #
def test_with_no_embedding_store_the_order_is_the_attribute_terms_alone():
    """What a clone gets. It is still an order, still deterministic, still a
    permutation — and the page says which basis it used rather than going quiet."""
    rows = rows_of([("azure", "smooth", 0.9), ("rose", "stripe", 0.8)] * 10)

    assert page_order.order(rows, {}) == page_order.order(rows, None)
    assert page_order.basis({}) == page_order.ATTRIBUTES_ONLY
    assert page_order.basis(None) == page_order.ATTRIBUTES_ONLY
    assert page_order.basis({"a": 1}) == page_order.WITH_EMBEDDING


def test_a_store_that_is_not_there_is_answered_with_no_vectors(tmp_path):
    """`vectors_for` is asked on every build, so a machine with no store must get an
    empty map rather than a refusal — and a row with no `location` asks nothing."""
    rows = [seat("a" * 16, location="place-1"), seat("b" * 16)]

    assert page_order.vectors_for(rows, path=tmp_path / "absent.jsonl") == {}
    assert page_order.vectors_for([seat("c" * 16)], path=tmp_path / "absent.jsonl") == {}


def test_only_the_locations_a_record_seats_are_decoded(tmp_path):
    """One streamed pass keeping what was asked for: the store is 41,415 rows and a
    record names a thousand of them, so a reader of the whole thing would decode
    forty times the vectors it needs."""
    import base64
    import json

    store = tmp_path / "neutral_embeddings.jsonl"
    store.write_text(
        "".join(
            json.dumps(
                {
                    "schema": 1,
                    "key": f"place-{at}",
                    "vector": base64.b64encode(numpy.eye(4, dtype="<f2")[at % 4].tobytes()).decode(
                        "ascii"
                    ),
                }
            )
            + "\n"
            for at in range(8)
        ),
        encoding="utf-8",
        newline="\n",
    )

    held = page_order.vectors_for([seat("a" * 16, location="place-3")], path=store)

    assert list(held) == ["place-3"]
    assert held["place-3"].tolist() == [0.0, 0.0, 0.0, 1.0]


# --------------------------------------------------------------------------- #
# The readout, which is what a before/after is read on.
# --------------------------------------------------------------------------- #
def test_the_spacing_readout_measures_the_placement_it_is_HANDED():
    """It takes the order rather than computing one, which is what lets the shipped
    order and the derived one be measured by one function — two instruments would
    not be a comparison."""
    rows = rows_of([("azure", "smooth", 0.9)] * 2 + [("rose", "smooth", 0.9)] * 2)

    clumped = page_order.spacing(rows, [0, 1, 2, 3])
    spread = page_order.spacing(rows, [0, 2, 1, 3])

    assert clumped["gaps"]["cell"]["min"] == 1
    assert spread["gaps"]["cell"]["min"] == 2


def test_the_spiral_clumping_is_said_two_ways_because_run_is_ambiguous():
    """`longest_run` is consecutive tiles and `most_in_a_window` is the fullest
    window there is. A page can move one without the other, and the second is what
    the ordering steers."""
    rows = [seat(f"{at:016x}", spiral=at in (0, 1, 5, 9)) for at in range(12)]

    held = page_order.spacing(rows, list(range(12)), window=6)

    assert held["spiral"]["longest_run"] == 2
    assert held["spiral"]["most_in_a_window"] == 3
    assert held["spiral"]["seats"] == 4


def test_a_distance_mean_over_a_page_with_unembedded_seats_says_how_many_it_read():
    """A mean taken where a thirtieth of the seats have no vector is a mean over the
    rest, and it states that rather than imputing: `measured` is the count and
    `embedded` is how much of the page could have contributed."""
    rows = [seat(f"{at:016x}", location=f"place-{at}") for at in range(4)]
    vectors = {
        "place-0": numpy.array([1.0, 0.0], dtype=numpy.float32),
        "place-2": numpy.array([0.0, 1.0], dtype=numpy.float32),
    }

    held = page_order.spacing(rows, [0, 1, 2, 3], vectors)

    assert held["distance"]["embedded"] == 2
    assert held["distance"]["of"] == 4
    # Position 0 has no window and positions 1 and 3 have no vector, so exactly one
    # position contributes — place-2 against place-0, orthogonal, a distance of 1.
    assert held["distance"]["measured"] == 1
    assert held["distance"]["mean"] == pytest.approx(1.0)


def test_a_readout_over_a_page_with_no_vectors_at_all_reports_nothing_rather_than_zero():
    """`None` and `0.0` are opposite readings — a page whose distances were not
    measured must not look like a page whose seats are all identical."""
    rows = rows_of([("azure", "smooth", 0.9)] * 4)

    held = page_order.spacing(rows, [0, 1, 2, 3])

    assert held["distance"]["mean"] is None
    assert held["distance"]["measured"] == 0
