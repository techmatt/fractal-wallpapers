"""Selection: top-N per judge, under the slot, supply and look caps."""

from __future__ import annotations

from fractal_wallpapers.curation import floors, selection


def entry(identifier: str, partition: str, group: str, score: float) -> dict:
    return {"id": identifier, "partition": partition, "group": group, "score": score, "row": {}}


def test_top_n_within_a_partition_under_its_slot_budget() -> None:
    pool = [
        entry("a", "mandelbrot", "g1", 0.9),
        entry("b", "mandelbrot", "g2", 0.7),
        entry("c", "mandelbrot", "g3", 0.5),
    ]
    picked, *_ = selection.select(pool, {"mandelbrot": 2})
    assert [e["id"] for e in picked] == ["a", "b"]


def test_a_partition_absent_from_the_allocation_releases_nothing() -> None:
    """The allocation is the authority on which partitions may release at all."""
    pool = [entry("a", "phoenix", "g1", 0.99)]
    picked, *_ = selection.select(pool, {"mandelbrot": 3})
    assert picked == []


def test_the_thin_supply_cap_binds_below_the_slot_budget() -> None:
    pool = [entry(str(i), "mandelbrot", f"g{i}", 0.9 - i / 10) for i in range(4)]
    picked, *_ = selection.select(pool, {"mandelbrot": 3}, caps={"mandelbrot": 1})
    assert len(picked) == 1


def test_one_location_takes_one_seat_across_both_judge_passes() -> None:
    """Two disjoint passes over the same locations seat one wallpaper between them."""
    used: dict = {}
    first = [entry(f"s{i}", "mandelbrot", "one_place", 0.9) for i in range(3)]
    second = [entry(f"t{i}", "mandelbrot", "one_place", 0.9) for i in range(3)]
    picked_a, *_ = selection.select(first, {"mandelbrot": 3}, used=used)
    picked_b, log_b, _ = selection.select(second, {"mandelbrot": 3}, used=used)
    assert len(picked_a) == floors.CLUSTER_CAP == 1
    assert picked_b == []
    assert all(row["skipped"] == selection.LOCATION_SERVED for row in log_b)
    assert all(row["cause"] == "this_run" for row in log_b)


def test_the_guarantee_floors_the_budget_at_one_over_the_supply_cap() -> None:
    pool = [entry("a", "phoenix:classic", "g1", 0.6)]
    picked, log, _ = selection.select(
        pool,
        {"phoenix:classic": 1},
        caps={"phoenix:classic": 0},
        guarantees=["phoenix:classic"],
    )
    assert [e["id"] for e in picked] == ["a"]
    assert log[0]["slot_source"] == "guarantee"


def test_only_the_first_pick_of_an_owed_partition_is_a_guarantee_slot() -> None:
    pool = [entry(str(i), "mandelbrot", f"g{i}", 0.9 - i / 10) for i in range(3)]
    _, log, _fills = selection.select(
        pool, {"mandelbrot": 3}, caps={"mandelbrot": 3}, guarantees=["mandelbrot"]
    )
    sources = [row["slot_source"] for row in log if row["picked"]]
    assert sources == ["guarantee", "mix", "mix"]


def test_the_location_rule_outranks_the_guarantee() -> None:
    """The guarantee buys a slot and the right to spend it, not a second picture of
    a place the collection has already released one of."""
    used = {"one_place": floors.CLUSTER_CAP}
    pool = [entry("a", "phoenix:classic", "one_place", 0.99)]
    picked, log, _ = selection.select(
        pool, {"phoenix:classic": 1}, used=used, guarantees=["phoenix:classic"]
    )
    assert picked == []
    assert log[0]["skipped"] == selection.LOCATION_SERVED


def test_a_failed_render_is_not_eligible_and_is_not_read_as_a_zero() -> None:
    rows = [
        {"attempt": 0, "partition": "mandelbrot", "p_ge3": 0.5, "family": {}, "viewport": {}},
        {"attempt": 1, "partition": "mandelbrot", "p_ge3": None, "family": {}, "viewport": {}},
    ]
    assert [e["id"] for e in selection.entries(rows)] == ["0000"]


def test_two_frames_of_one_look_share_a_group_and_two_places_do_not() -> None:
    """The grouping is the shipped near-duplicate rule the holdout is drawn on."""
    here = {"kind": "mandelbrot"}
    rows = [
        {
            "attempt": 0,
            "partition": "mandelbrot",
            "p_ge3": 0.9,
            "family": here,
            "viewport": {"center_re": "-0.5", "center_im": "0", "width": "0.4"},
        },
        {
            "attempt": 1,
            "partition": "mandelbrot",
            "p_ge3": 0.8,
            "family": here,
            "viewport": {"center_re": "-0.5001", "center_im": "0", "width": "0.4"},
        },
        {
            "attempt": 2,
            "partition": "mandelbrot",
            "p_ge3": 0.7,
            "family": here,
            "viewport": {"center_re": "0.28", "center_im": "0.01", "width": "0.001"},
        },
    ]
    groups = [e["group"] for e in selection.entries(rows)]
    assert groups[0] == groups[1]
    assert groups[2] != groups[0]


def test_a_row_the_grouping_cannot_place_gets_its_own_look() -> None:
    """Unplaceable is not a look, and lumping them together would let one bad row
    cap the rest."""
    rows = [
        {"attempt": i, "partition": "mandelbrot", "p_ge3": 0.9, "family": None, "viewport": None}
        for i in range(3)
    ]
    groups = [e["group"] for e in selection.entries(rows)]
    assert len(set(groups)) == 3


def test_the_log_carries_a_reason_for_every_row_it_did_not_pick() -> None:
    used = {"one_place": floors.CLUSTER_CAP}
    pool = [entry("a", "mandelbrot", "one_place", 0.9), entry("b", "mandelbrot", "g2", 0.8)]
    picked, log, _ = selection.select(pool, {"mandelbrot": 1}, used=used)
    assert [e["id"] for e in picked] == ["b"]
    assert {row["id"]: row["skipped"] for row in log} == {
        "a": selection.LOCATION_SERVED,
        "b": None,
    }


# --------------------------------------------------------------------------- #
# One wallpaper per location, collection-wide (Matt, 2026-08-22).
# --------------------------------------------------------------------------- #
def test_a_place_an_earlier_run_served_is_refused_and_says_which_side() -> None:
    """The cross-run half: nothing in this run has taken the seat, and it is still
    refused, because the collection already holds a wallpaper of the place."""
    pool = [entry("a", "mandelbrot", "g1", 0.99), entry("b", "mandelbrot", "g2", 0.98)]
    picked, log, fills = selection.select(pool, {"mandelbrot": 2}, served={"g1"})
    assert [e["id"] for e in picked] == ["b"]
    refused = next(row for row in log if row["id"] == "a")
    assert (refused["skipped"], refused["cause"]) == (selection.LOCATION_SERVED, "prior_run")
    assert fills["mandelbrot"]["location_served"] == 1


def test_the_higher_ranked_seat_keeps_the_place_and_the_weaker_one_is_refused() -> None:
    """Score order decides, so the row refused is always the weaker reading."""
    pool = [entry("strong", "mandelbrot", "g1", 0.99), entry("weak", "mandelbrot", "g1", 0.10)]
    picked, log, _ = selection.select(pool, {"mandelbrot": 2})
    assert [e["id"] for e in picked] == ["strong"]
    assert next(row for row in log if row["id"] == "weak")["cause"] == "this_run"


def test_one_grouping_over_both_heads_makes_their_tags_comparable() -> None:
    """Grouped separately, `group#0` in one pass and `group#0` in the other are
    unrelated labels — and the counter under them is then sharing a dictionary
    rather than a rule."""
    here = {"kind": "mandelbrot"}
    frame = {"center_re": "-0.5", "center_im": "0", "width": "0.4"}
    elsewhere = {"center_re": "0.28", "center_im": "0.01", "width": "0.001"}

    def row(attempt: int, score: float, viewport: dict) -> dict:
        return {
            "attempt": attempt,
            "partition": "mandelbrot",
            "p_ge3": score,
            "family": here,
            "viewport": viewport,
        }

    smooth = [row(0, 0.9, elsewhere)]
    strange = [row(1, 0.8, frame)]
    apart = {
        head: [e["group"] for e in selection.entries(rows)]
        for head, rows in (("smooth", smooth), ("strange", strange))
    }
    assert apart["smooth"] == apart["strange"]  # the collision this rule cannot tolerate
    together, served = selection.grouped({"smooth": smooth, "strange": strange})
    assert together["smooth"][0]["group"] != together["strange"][0]["group"]
    assert served == set()


def test_the_served_index_comes_back_as_tags_in_the_candidates_own_grouping() -> None:
    here = {"kind": "mandelbrot"}
    frame = {"center_re": "-0.5", "center_im": "0", "width": "0.4"}
    served = [{"family": here, "viewport": frame}]
    rows = [
        {
            "attempt": 0,
            "partition": "mandelbrot",
            "p_ge3": 0.9,
            "family": here,
            "viewport": frame,
        }
    ]
    entries_by_head, already = selection.grouped({"smooth": rows}, served)
    assert entries_by_head["smooth"][0]["group"] in already
