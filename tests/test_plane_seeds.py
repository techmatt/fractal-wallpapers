"""The parameter planes' seed pool: what it holds, and what refuses it.

The pool is the only channel four of the ten partitions have. When the first
production run ran without one, `has_channel` was false for all four, they could
never be refilled, and the harvest stalled with 65.6% of its intended clock
unspendable. So these are mostly checks that the shipped file is still a pool —
run on every commit, off the tracked bytes, without re-deriving anything.

The derivation itself is a quarter of an hour of Newton and is a command
(`derive-plane-seeds`) rather than a test.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.discovery import nucleus, plane_seeds, pools
from fractal_wallpapers.supply.partitions import partition_of_family


def shipped() -> list[dict]:
    if not plane_seeds.pool_path().is_file():
        pytest.skip("the plane seed pool has not been derived on this machine")
    return pools.plane_pool()


# --------------------------------------------------------------------------- #
# the shipped pool
# --------------------------------------------------------------------------- #
def test_the_pool_covers_every_partition_that_has_no_other_channel() -> None:
    """Four partitions, four channels. A pool missing one is a partition that can
    never be refilled, which is invisible until a run comes back empty."""
    covered = {partition_of_family(row["family"]) for row in shipped()}
    assert covered == {name for name, _family, _degree in plane_seeds.FAMILIES}


def test_every_family_keeps_a_home_view_to_stand_on() -> None:
    """A family whose every atom was refused still has one place to start."""
    homes = {
        partition_of_family(row["family"])
        for row in shipped()
        if row["provenance"]["channel"] == "home_view"
    }
    assert homes == {name for name, _family, _degree in plane_seeds.FAMILIES}
    for row in shipped():
        if row["provenance"]["channel"] == "home_view":
            assert "viewport" not in row, "the home view is the engine's, never a literal here"


def test_the_six_a_person_chose_are_carried_as_data() -> None:
    """They are not derivable from anything, and a pool that needs an untracked
    file to be rebuilt is not a tracked pool."""
    hand = [row for row in shipped() if row["provenance"]["channel"] == "hand_picked"]
    assert [row["id"] for row in hand] == [entry[0] for entry in plane_seeds.HAND_PICKED]


def test_every_solved_root_is_a_frame_the_walk_can_move_inside() -> None:
    """The bound is on what the solver emits. A hand-picked frame is somebody's
    judgement about where to look and the procedure has no standing to refuse
    it — one of the six sits just outside, and always has."""
    outside = []
    for row in shipped():
        view = row.get("viewport")
        if view is None:
            continue
        width = float(view["width"])
        assert width > 0
        if row["provenance"]["channel"] == plane_seeds.SOLVED:
            assert plane_seeds.WIDTH_MIN <= width <= plane_seeds.WIDTH_MAX
        elif not (plane_seeds.WIDTH_MIN <= width <= plane_seeds.WIDTH_MAX):
            outside.append(row["id"])
    assert outside == ["m05"], "an unexpected root sits outside the solver's frame bound"


def test_every_solved_root_clears_the_same_headroom_the_operators_ask_for() -> None:
    """One number, one meaning: a root the reframing operators would refuse to
    deploy at is not a root worth seeding from."""
    for row in shipped():
        margin = row["provenance"].get("f64_margin_decades")
        if margin is not None:
            assert margin >= nucleus.MARGIN_MIN_DECADES


def test_the_pool_spreads_over_periods_rather_than_over_one() -> None:
    """Five hundred copies of one period is one place, not five hundred."""
    by_partition: dict[str, set] = {}
    for row in shipped():
        period = row["provenance"].get("period")
        if period is not None:
            by_partition.setdefault(partition_of_family(row["family"]), set()).add(period)
    assert by_partition, "no solved root recorded the period it came from"
    for partition, periods in sorted(by_partition.items()):
        assert len(periods) >= 10, f"{partition} spans only {len(periods)} period(s)"


# --------------------------------------------------------------------------- #
# what the reader refuses
# --------------------------------------------------------------------------- #
def _write(tmp_path, rows) -> object:
    path = tmp_path / "pool.jsonl"
    path.write_text(plane_seeds.render(rows), encoding="utf-8", newline="\n")
    return path


def test_a_root_framed_outside_the_walkable_range_is_refused(tmp_path) -> None:
    """The one property a later edit could silently break, checked at load."""
    row = {
        "schema": 1,
        "id": "wide",
        "family": {"kind": "mandelbrot"},
        "viewport": {"center_re": "0", "center_im": "0", "width": "4.0"},
        "provenance": {"channel": plane_seeds.SOLVED},
    }
    with pytest.raises(plane_seeds.PlaneSeedError, match="outside"):
        plane_seeds.read(_write(tmp_path, [row]))


def test_two_rows_under_one_id_are_refused(tmp_path) -> None:
    """The refill cursor addresses entries by position and provenance by id: two
    rows under one id is a root nobody can attribute."""
    row = {"schema": 1, "id": "same", "family": {"kind": "mandelbrot"}}
    with pytest.raises(plane_seeds.PlaneSeedError, match="duplicate"):
        plane_seeds.read(_write(tmp_path, [row, dict(row)]))


def test_a_row_with_no_family_is_refused(tmp_path) -> None:
    with pytest.raises(plane_seeds.PlaneSeedError, match="id and a family"):
        plane_seeds.read(_write(tmp_path, [{"schema": 1, "id": "bare"}]))


def test_a_missing_pool_says_how_to_make_one(tmp_path) -> None:
    with pytest.raises(plane_seeds.PlaneSeedError, match="derive-plane-seeds"):
        plane_seeds.read(tmp_path / "absent.jsonl")


# --------------------------------------------------------------------------- #
# the derivation's own arithmetic
# --------------------------------------------------------------------------- #
def test_the_grid_is_the_home_frame_at_sixteen_by_nine() -> None:
    assert plane_seeds.rows_of(340) == 191
    assert plane_seeds.rows_of(1) == 1
    view = {"center_re": "0.0", "center_im": "0.0", "width": "2.0"}
    points = list(plane_seeds.grid(view, 2))
    assert len(points) == 2 * plane_seeds.rows_of(2)
    assert all(abs(point.real) <= 1.0 for point in points)


def test_the_keep_round_robins_periods_before_it_ranks_on_margin() -> None:
    """Otherwise the keep clusters on whichever period the grid resolved best."""
    found = [
        {"period": 3, "f64_margin_decades": 9.0},
        {"period": 3, "f64_margin_decades": 8.0},
        {"period": 3, "f64_margin_decades": 7.0},
        {"period": 5, "f64_margin_decades": 2.0},
    ]
    kept = plane_seeds._spread(found, 3)
    assert [row["period"] for row in kept] == [3, 5, 3]
    assert [row["f64_margin_decades"] for row in kept] == [9.0, 2.0, 8.0]


def test_verify_is_an_equality_and_names_what_moved(tmp_path) -> None:
    """The pool's only real claim is that this procedure still produces it, so
    the comparison is exact and a mismatch is attributable to a row."""
    rows = [
        {"schema": 1, "id": "a", "family": {"kind": "mandelbrot"}},
        {"schema": 1, "id": "b", "family": {"kind": "mandelbrot"}},
    ]
    path = _write(tmp_path, rows)
    assert plane_seeds.verify(rows, path)["held"] is True

    moved = [rows[0], {**rows[1], "family": {"kind": "multibrot", "degree": 3}}]
    verdict = plane_seeds.verify(moved, path)
    assert verdict["held"] is False
    assert verdict["mismatched"] == ["b"]


def test_verify_on_a_pool_that_does_not_exist_is_a_refusal_not_a_pass(tmp_path) -> None:
    verdict = plane_seeds.verify([{"schema": 1, "id": "a"}], tmp_path / "absent.jsonl")
    assert verdict["held"] is False


def test_the_pool_is_the_bytes_the_deriver_writes() -> None:
    """Rendered once, so a hand edit and a regeneration cannot both be 'the pool'."""
    if not plane_seeds.pool_path().is_file():
        pytest.skip("the plane seed pool has not been derived on this machine")
    text = plane_seeds.pool_path().read_text(encoding="utf-8")
    rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    assert plane_seeds.render(rows) == text
