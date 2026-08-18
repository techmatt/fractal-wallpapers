"""The distillation corpus: the draw, the split, and what the tracked rows say."""

from __future__ import annotations

import pytest

from fractal_wallpapers.models import palette_corpus
from fractal_wallpapers.supply.location import location_key


def test_the_apportionment_is_even_until_a_partition_runs_out() -> None:
    quota = palette_corpus.apportion({"a": 1000, "b": 1000, "c": 1000}, 600)
    assert quota == {"a": 200, "b": 200, "c": 200}


def test_a_thin_partition_gives_what_it_has_and_the_rest_take_the_shortfall() -> None:
    """`phoenix:classic` is the one that binds: its plane is a single pinned
    parameter point, so the corpus holds two dozen places on it and no seed can
    conjure more."""
    quota = palette_corpus.apportion({"a": 1000, "b": 1000, "thin": 24}, 600)
    assert quota["thin"] == 24
    assert sum(quota.values()) == 600
    assert abs(quota["a"] - quota["b"]) <= 1


def test_the_apportionment_stops_at_the_supply_rather_than_looping() -> None:
    quota = palette_corpus.apportion({"a": 5, "b": 5}, 600)
    assert quota == {"a": 5, "b": 5}


def test_the_split_moves_whole_locations() -> None:
    """A place's candidates share one field and differ only in colour, so a split
    that let them straddle would report a held-out loss that is partly a training
    loss."""
    rows = [
        {
            "family": {"kind": "mandelbrot"},
            "viewport": {"center_re": str(index // 2), "center_im": "0", "width": "3.0"},
        }
        for index in range(20)
    ]
    record = palette_corpus.sides(rows, seed=0, share=0.2)
    by_place: dict[str, set] = {}
    for row in rows:
        by_place.setdefault(repr(location_key(row["family"], row["viewport"])), set()).add(
            row["side"]
        )
    assert all(len(seen) == 1 for seen in by_place.values())
    assert record["held_out_locations"] == 2
    assert record["realized_share"] == pytest.approx(0.2)


def test_the_split_reports_what_it_realized_rather_than_what_it_asked_for() -> None:
    rows = [
        {
            "family": {"kind": "mandelbrot"},
            "viewport": {"center_re": str(index), "center_im": "0", "width": "3.0"},
        }
        for index in range(7)
    ]
    record = palette_corpus.sides(rows, seed=0, share=0.2)
    assert record["target_share"] == 0.2
    assert record["realized_share"] != 0.2


def test_a_pinned_location_cannot_be_drawn_back_onto_the_training_side(monkeypatch) -> None:
    """A corpus that grows must not grow into its own held-out side: the epoch
    this head ships at is chosen there, and a location that scored that loss last
    time and teaches the model this time makes the two readings incomparable."""
    rows = [
        {
            "family": {"kind": "mandelbrot"},
            "viewport": {"center_re": str(index), "center_im": "0", "width": "3.0"},
        }
        for index in range(100)
    ]
    pinned = {repr(location_key(row["family"], row["viewport"])) for row in rows[:5]}
    monkeypatch.setattr(palette_corpus, "carried_holdout", lambda: pinned)
    record = palette_corpus.sides(rows, seed=1, share=0.2)
    held = {
        repr(location_key(row["family"], row["viewport"]))
        for row in rows
        if row["side"] == "holdout"
    }
    assert pinned <= held
    assert record["carried_from_earlier_draws"] == 5
    assert record["held_out_locations"] == 20


def test_the_pin_never_shrinks_the_held_out_share_it_was_asked_for(monkeypatch) -> None:
    """More pins than the share asks for is a bigger held-out side, not a
    truncated pin. Dropping one would be dropping the property the pin exists for."""
    rows = [
        {
            "family": {"kind": "mandelbrot"},
            "viewport": {"center_re": str(index), "center_im": "0", "width": "3.0"},
        }
        for index in range(10)
    ]
    everything = {repr(location_key(row["family"], row["viewport"])) for row in rows}
    monkeypatch.setattr(palette_corpus, "carried_holdout", lambda: everything)
    record = palette_corpus.sides(rows, seed=0, share=0.2)
    assert record["held_out_locations"] == 10
    assert all(row["side"] == "holdout" for row in rows)


def test_every_map_anchors_a_set_before_any_map_anchors_two() -> None:
    """A corpus that sampled anchors independently would leave a tail of maps that
    never sat at the centre of a set."""
    pool = [f"map{index:03d}" for index in range(50)]
    assert sorted(palette_corpus.anchors(pool, 50, seed=3)) == pool
    twice = palette_corpus.anchors(pool, 100, seed=3)
    assert sorted(twice) == sorted(pool + pool)
    assert palette_corpus.anchors(pool, 30, seed=3) == twice[:30]


def test_the_temperature_is_read_off_the_corpus_rather_than_chosen() -> None:
    """The teacher's units mean nothing on their own, so a listwise term cannot
    carry a constant temperature and mean the same thing twice."""
    tight = palette_corpus.temperature([[0.0, 1.0, 2.0], [1.0, 2.0, 3.0]])
    loose = palette_corpus.temperature([[0.0, 10.0, 20.0], [10.0, 20.0, 30.0]])
    assert loose == pytest.approx(10 * tight)
    assert tight > 0


@pytest.fixture(scope="module")
def rows(distillation_rows):
    """The tracked corpus, under the name this file's tests read it by."""
    return distillation_rows


@pytest.fixture(scope="module")
def grouped(rows):
    """The corpus folded back into the candidate sets it was drawn as."""
    return palette_corpus.grouped(rows)


@pytest.fixture(scope="module")
def places(rows):
    """One location coordinate per row, in row order.

    Deriving it is a pass over every row of the corpus, and three of the tests
    below are about which side of the split a *place* landed on rather than a row.
    """
    return [repr(location_key(row["family"], row["viewport"])) for row in rows]


class TestTheTrackedCorpus:
    """The machine-labeled rows, held to what they claim about themselves."""

    def test_every_row_says_a_machine_labeled_it(self, rows) -> None:
        """The one thing that must never be ambiguous: none of this is a human
        verdict, and none of it belongs in a store that holds those."""
        assert rows
        assert {row["origin"] for row in rows} == {"teacher"}
        assert all(isinstance(row["score"], float) for row in rows)

    def test_every_row_names_the_teacher_that_cast_it(self, rows) -> None:
        """By the sha256 of the weights, so a corpus can be regenerated rather
        than re-approximated."""
        teachers = {row["teacher"] for row in rows}
        assert len(teachers) == 1
        assert len(teachers.pop()) == 64

    def test_every_row_carries_enough_to_rebuild_its_own_picture(self, rows) -> None:
        from fractal_wallpapers.labeling import finished
        from fractal_wallpapers.models import renders

        for row in rows[:50]:
            assert set(finished.RECIPE_KEYS) <= set(row["recipe"])
            spec = renders.spec_of(row, __import__("pathlib").Path("out.jpg"))
            assert spec["colormap"] == row["colormap"]

    def test_a_set_holds_one_place_and_no_map_twice(self, grouped) -> None:
        for entry in grouped:
            assert len(set(entry["candidates"])) == len(entry["candidates"])
            held = {location_key(row["family"], row["viewport"]) for row in entry["rows"]}
            assert len(held) == 1

    def test_no_location_is_on_both_sides_of_the_split(self, rows, places) -> None:
        sides: dict[str, set] = {}
        for row, place in zip(rows, places, strict=True):
            sides.setdefault(place, set()).add(row["side"])
        assert all(len(seen) == 1 for seen in sides.values())

    def test_the_split_record_matches_the_rows(self, rows) -> None:
        import json

        document = json.loads(palette_corpus.split_path().read_text(encoding="utf-8"))
        held = {row["set"] for row in rows if row["side"] == "holdout"}
        assert document["sets"]["holdout"] == len(held)

    def test_every_location_cleared_the_floor(self, rows) -> None:
        assert min(row["location_score"] for row in rows) >= palette_corpus.FLOOR

    def test_the_hard_sets_really_are_tighter_than_the_uniform_ones(self, rows) -> None:
        """The mix is a declaration and this is the check on it. A hard set is
        meant to be a near-tie by construction; if its members were no nearer each
        other than a uniform draw's, the corpus would be claiming a property it
        does not have."""
        import json

        document = json.loads(palette_corpus.split_path().read_text(encoding="utf-8"))
        kinds = document["mix"]["kinds"]
        assert kinds["hard"]["share"] == pytest.approx(document["mix"]["declared_hard_share"])
        assert (
            kinds["hard"]["palette_distance"]["mean"] < kinds["uniform"]["palette_distance"]["mean"]
        )

    def test_a_hard_set_opens_on_the_anchor_it_was_built_around(self, grouped) -> None:
        from fractal_wallpapers.models import palette_sets
        from fractal_wallpapers.palettes import space

        pool = palette_sets.pool()["pool"]
        hard = [entry for entry in grouped if entry["kind"] == "hard"]
        assert hard
        for entry in hard[:5]:
            anchor = entry["rows"][0]["anchor"]
            assert anchor is not None
            assert set(entry["candidates"]) == set(
                space.neighbourhood(anchor, pool, len(entry["candidates"]))
            )

    def test_no_location_a_previous_draw_held_out_is_being_taught(self, rows, places) -> None:
        """The pin is data, and this is what it is for."""
        pinned = palette_corpus.carried_holdout()
        taught = {place for row, place in zip(rows, places, strict=True) if row["side"] == "train"}
        assert not (pinned & taught)

    def test_the_corpus_is_the_one_thing_the_size_rule_is_widened_for(self) -> None:
        """These files are over a mebibyte and are meant to be. The exemption is
        named and narrow — the corpus directory, nothing else — and it exempts the
        size rule only, so a blob dropped in here still fails the build."""
        from tests.test_history_purity import LARGE_TEXT_ALLOWLIST

        assert any("palette_choice/rows" in prefix for prefix in LARGE_TEXT_ALLOWLIST), (
            "the corpus is over the limit and nothing records that as a decision"
        )
        for path in palette_corpus.row_dir().glob("*.jsonl"):
            assert path.suffix == ".jsonl"
            path.read_text(encoding="utf-8")
