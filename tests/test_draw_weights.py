"""The standing draw-weight table, and the turn arithmetic three draws now share.

The property worth pinning hardest: **a fraction has to act**. Every site that
weighted a partition draw did the arithmetic as `int(round(weight))`, which turns
0.25 into either zero turns — the partition gone, which the rule forbids — or one
turn, which is no lean at all. So the tests here are mostly about 0.25.
"""

from __future__ import annotations

from fractal_wallpapers.curation import draw_weights
from fractal_wallpapers.supply import partitions, release_mix

EVERY = list(partitions.ALL_PARTITIONS)


def test_the_table_names_every_registered_partition_and_only_downweights_the_two():
    table = draw_weights.table()
    assert set(table) == set(EVERY), "a table that answers for some partitions is a trap"
    assert table["phoenix"] == 0.25
    assert table[partitions.CLASSIC_PHOENIX] == 0.25
    assert {name: weight for name, weight in table.items() if weight != 1.0} == {
        "phoenix": 0.25,
        partitions.CLASSIC_PHOENIX: 0.25,
    }


def test_no_default_weight_is_zero():
    """A partition that should get none of the release is RETIRED from the
    registry, never zeroed — the rule `release_mix.json` states for its ratios,
    and the reason this table holds a quarter rather than a nought."""
    assert all(weight > 0.0 for weight in draw_weights.table().values())


def test_an_override_is_merged_over_the_table_and_not_a_replacement():
    table = draw_weights.table({partitions.CLASSIC_PHOENIX: 1.0})
    assert table[partitions.CLASSIC_PHOENIX] == 1.0, "an aimed leg draws it at full weight"
    assert table["phoenix"] == 0.25, "and says nothing about the partition it did not name"
    assert draw_weights.table({"mandelbrot": 3})["phoenix"] == 0.25, (
        "a leg leaning toward the release mix must not silently re-inflate the pinned plane"
    )


def test_a_quarter_weight_is_a_quarter_of_the_turns_and_never_none():
    turns = draw_weights.turns_of(["mandelbrot", "phoenix"], draw_weights.table())
    assert turns == {"mandelbrot": 4, "phoenix": 1}


def test_an_integer_table_comes_out_as_the_turns_it_always_was():
    """The scaling only acts where it is needed, so every work order this project
    has already passed draws exactly what it drew."""
    assert draw_weights.turns_of("abcd", {"a": 19, "b": 6, "c": 5, "d": 4}) == {
        "a": 19,
        "b": 6,
        "c": 5,
        "d": 4,
    }


def test_an_unweighted_round_is_one_turn_each_in_name_order():
    assert draw_weights.order(["b", "a", "c"], None) == ["a", "b", "c"]
    assert draw_weights.order(["b", "a"], {}) == ["a", "b"]


def test_every_prefix_of_a_round_leans_the_way_the_whole_round_does():
    """A production leg is clock-bound and truncates, so a lean that only acts
    over a whole round is a lean that never acts."""
    round_ = draw_weights.order(["mandelbrot", "phoenix"], draw_weights.table())
    for cut in (2, 3, 4, len(round_)):
        head = round_[:cut]
        assert head.count("mandelbrot") > head.count("phoenix"), head
    assert "phoenix" in round_, "and a lean is never a gate"


def test_a_zero_weight_is_out_of_the_draw_and_still_holds_the_floor_at_an_interleave():
    names = ["mandelbrot", "phoenix"]
    assert draw_weights.turns_of(names, {"phoenix": 0})["phoenix"] == 0
    assert "phoenix" not in draw_weights.order(names, {"phoenix": 0})
    # At the interleave the places are already drawn, and dropping a partition
    # the draw kept would starve one the leg meant to buy.
    assert draw_weights.turns_of(names, {"phoenix": 0}, floor=1)["phoenix"] == 1


def test_a_negative_weight_reads_as_zero_rather_than_refusing_the_leg():
    assert draw_weights.turns_of(["a"], {"a": -3.0}) == {"a": 0}


def test_a_table_of_zeros_leaves_every_name_at_the_floor_it_was_given():
    assert draw_weights.turns_of(["a", "b"], {"a": 0, "b": 0}) == {"a": 0, "b": 0}
    assert draw_weights.turns_of(["a", "b"], {"a": 0, "b": 0}, floor=1) == {"a": 1, "b": 1}


def test_a_round_is_bounded_however_small_a_weight_is():
    turns = draw_weights.turns_of(["a", "b"], {"a": 1.0, "b": 0.001})
    assert max(turns.values()) <= draw_weights.MAX_TURNS
    assert turns["b"] == 1, "and the small one keeps its turn"


def test_a_partition_that_drew_nothing_is_a_zero_and_never_an_absence():
    tally = draw_weights.tallied(["mandelbrot", "phoenix"], {"mandelbrot": 12})
    assert tally == {"mandelbrot": 12, "phoenix": 0}


def test_the_draw_weight_and_the_release_ratio_are_different_axes():
    """Both are declared and neither derives the other: one says how much of a
    RELEASE a family is owed, the other how much of a DRAW it is worth given what
    it costs to render. `phoenix:classic` sits at 0.2 in one and 0.25 in the
    other, and a reader who took them for one number would be wrong twice."""
    assert (
        release_mix.ratio_of(partitions.CLASSIC_PHOENIX)
        != draw_weights.table()[partitions.CLASSIC_PHOENIX]
    )
