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


def test_the_look_cap_holds_across_both_judge_passes() -> None:
    """Two disjoint passes over the same locations must not each take two of a look."""
    used: dict = {}
    first = [entry(f"s{i}", "mandelbrot", "one_look", 0.9) for i in range(3)]
    second = [entry(f"t{i}", "mandelbrot", "one_look", 0.9) for i in range(3)]
    picked_a, *_ = selection.select(first, {"mandelbrot": 3}, used=used)
    picked_b, log_b, _ = selection.select(second, {"mandelbrot": 3}, used=used)
    assert len(picked_a) == floors.CLUSTER_CAP
    assert picked_b == []
    assert all(row["skipped"] == "cluster_cap" for row in log_b)


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


def test_the_look_cap_outranks_the_guarantee() -> None:
    """The guarantee buys a slot and the right to spend it, not a third picture of
    a look the release has already taken twice."""
    used = {"one_look": floors.CLUSTER_CAP}
    pool = [entry("a", "phoenix:classic", "one_look", 0.99)]
    picked, log, _ = selection.select(
        pool, {"phoenix:classic": 1}, used=used, guarantees=["phoenix:classic"]
    )
    assert picked == []
    assert log[0]["skipped"] == "cluster_cap"


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
    used = {"one_look": floors.CLUSTER_CAP}
    pool = [entry("a", "mandelbrot", "one_look", 0.9), entry("b", "mandelbrot", "g2", 0.8)]
    picked, log, _ = selection.select(pool, {"mandelbrot": 1}, used=used)
    assert [e["id"] for e in picked] == ["b"]
    assert {row["id"]: row["skipped"] for row in log} == {"a": "cluster_cap", "b": None}
