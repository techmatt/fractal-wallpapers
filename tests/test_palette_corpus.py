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


@pytest.fixture(scope="module")
def rows():
    if not palette_corpus.row_dir().is_dir():
        pytest.skip("the distillation corpus has not been built")
    return palette_corpus.read()


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

    def test_a_set_holds_one_place_and_no_map_twice(self, rows) -> None:
        for entry in palette_corpus.grouped(rows):
            assert len(set(entry["candidates"])) == len(entry["candidates"])
            places = {location_key(row["family"], row["viewport"]) for row in entry["rows"]}
            assert len(places) == 1

    def test_no_location_is_on_both_sides_of_the_split(self, rows) -> None:
        sides: dict[str, set] = {}
        for row in rows:
            sides.setdefault(repr(location_key(row["family"], row["viewport"])), set()).add(
                row["side"]
            )
        assert all(len(seen) == 1 for seen in sides.values())

    def test_the_split_record_matches_the_rows(self, rows) -> None:
        import json

        document = json.loads(palette_corpus.split_path().read_text(encoding="utf-8"))
        held = {row["set"] for row in rows if row["side"] == "holdout"}
        assert document["sets"]["holdout"] == len(held)

    def test_every_location_cleared_the_floor(self, rows) -> None:
        assert min(row["location_score"] for row in rows) >= palette_corpus.FLOOR

    def test_no_tracked_row_file_is_large_enough_to_worry_the_history_rule(self) -> None:
        """The corpus is sharded by partition so no single file approaches the
        one-mebibyte tracked-file limit."""
        for path in palette_corpus.row_dir().glob("*.jsonl"):
            assert path.stat().st_size < 1024 * 1024, path
