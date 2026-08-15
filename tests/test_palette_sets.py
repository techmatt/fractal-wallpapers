"""The vendored candidate sets: how they are rebuilt, and what the tracked ones say."""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.labeling import finished
from fractal_wallpapers.models import palette_sets
from fractal_wallpapers.paths import colormap_dir
from fractal_wallpapers.supply.location import location_key


def test_a_flavour_s_members_keep_library_order_and_stop_at_the_cap() -> None:
    order = [f"map{index:03d}" for index in range(50)]
    flavours = dict.fromkeys(order, "k16:1")
    flavours["map007"] = "special:neutral"
    members = palette_sets.members_of("k16:1", flavours, order)
    assert len(members) == palette_sets.CAP
    assert "map007" not in members
    assert members == [name for name in order if name != "map007"][: palette_sets.CAP]


def test_folding_is_read_off_the_map_and_never_off_the_row() -> None:
    """A sequential map is folded to hide the seam its two ends would show; a
    cyclic one is not. That is a property of the map, so it is not a knob a row
    may set — the same rule the finished-render import applies."""
    cyclic = {"twilight"}
    assert palette_sets.recipe_for("twilight", cyclic)["mirror"] is False
    assert palette_sets.recipe_for("viridis", cyclic)["mirror"] is True


def test_a_candidate_row_is_a_finished_render_row_the_engine_can_read() -> None:
    from fractal_wallpapers.models import renders

    set_row = {
        "family": {"kind": "mandelbrot"},
        "viewport": {"center_re": "0", "center_im": "0", "width": "3.0"},
        "render": {"resolution": [640, 360], "supersample": 2, "maxiter": 1000},
        "mode": "smooth",
        "curve": "linear",
    }
    row = palette_sets.candidate_row(set_row, "viridis", set())
    assert set(finished.RECIPE_KEYS) <= set(row["recipe"])
    spec = renders.spec_of(row, __import__("pathlib").Path("out.jpg"))
    assert spec["colormap"] == "viridis"
    assert spec["coloring"]["kind"] == "field"
    assert spec["resolution"] == [640, 360]


def test_the_canonical_recipe_is_every_knob_at_the_identity() -> None:
    """What a production colorize applies and nothing else. A knob that drifted
    here would make every candidate a different picture from the one the teacher
    was asked about."""
    recipe = palette_sets.recipe_for("twilight", {"twilight"})
    assert recipe["gamma"] == 1.0
    assert recipe["cycles"] == 1.0
    assert recipe["phase"] == 0.0
    assert recipe["reverse"] is False
    assert recipe["transfer"] == {"kind": "value"}
    assert recipe["rolloff"] == {"kind": "none"}


@pytest.fixture(scope="module")
def rows():
    if not palette_sets.sets_path().is_file():
        pytest.skip("the production candidate sets have not been extracted")
    return palette_sets.read()


class TestTheTrackedRecord:
    """The 180 vendored sets, held to what they claim about themselves."""

    def test_every_recorded_winner_is_inside_its_own_candidate_set(self, rows) -> None:
        """The check the extraction refuses to write without. A winner outside its
        own set means the pool, the flavour table or the cap is wrong, and every
        number read on these sets would be about a question nobody asked."""
        assert rows
        for row in rows:
            assert row["chosen"] in row["candidates"], row["set"]

    def test_every_candidate_names_a_map_this_repository_holds(self, rows) -> None:
        """A candidate set naming a map nobody holds is a decision nobody can reproduce."""
        held = {path.stem for path in colormap_dir().glob("*.json")}
        named = {name for row in rows for name in row["candidates"]}
        assert not named - held

    def test_the_pool_holds_every_map_the_sets_name(self, rows) -> None:
        pool = set(palette_sets.pool()["pool"])
        assert not {name for row in rows for name in row["candidates"]} - pool

    def test_no_set_shares_a_location_with_another(self, rows) -> None:
        keys = [location_key(row["family"], row["viewport"]) for row in rows]
        assert len(set(keys)) == len(keys)

    def test_the_sets_are_held_out_of_the_distillation_corpus(self, rows) -> None:
        """The whole point of them: a set the head trained on is not an instrument."""
        from fractal_wallpapers.models import palette_corpus

        if not palette_corpus.row_dir().is_dir():
            pytest.skip("the distillation corpus has not been built")
        taught = {location_key(row["family"], row["viewport"]) for row in palette_corpus.read()}
        assert not taught & palette_sets.places()

    def test_a_row_carries_the_geometry_its_pictures_are_made_at(self, rows) -> None:
        for row in rows:
            assert row["render"]["resolution"] == list(palette_sets.RESOLUTION)
            assert row["render"]["supersample"] == palette_sets.SUPERSAMPLE
            assert row["render"]["maxiter"] > 0

    def test_the_reader_refuses_a_row_from_another_schema(self, tmp_path, rows) -> None:
        path = tmp_path / "candidate_sets.jsonl"
        path.write_text(json.dumps({**rows[0], "schema": 99}) + "\n", encoding="utf-8")
        original = palette_sets.sets_path
        palette_sets.sets_path = lambda: path
        try:
            with pytest.raises(palette_sets.SetsError):
                palette_sets.read()
        finally:
            palette_sets.sets_path = original
