"""The gallery pass: the radius, the floors, the location rule, and pass identity.

Every claim here is one a wrong answer would cost a full-resolution render or a
wallpaper of a place the collection already has. The expensive halves — the
attempt leg and the release leg — are not exercised: what is pinned is the
arithmetic between them, which is where every decision the pass takes is made.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy
import pytest

from fractal_wallpapers.curation import floors, gallery, records, selection


# --------------------------------------------------------------------------- #
# A tiny synthetic pool: unit vectors in a plane, so distances are arithmetic.
# --------------------------------------------------------------------------- #
def unit(angle: float) -> list[float]:
    """A unit vector at `angle` radians, in the first two of four dimensions."""
    return [numpy.cos(angle), numpy.sin(angle), 0.0, 0.0]


def location(key: str, angle: float, partition: str = "mandelbrot") -> dict:
    """One embedded location, spaced by angle so the cosine is `1 - cos(angle)`."""
    return {
        "key": key,
        "partition": partition,
        "family": {"kind": "mandelbrot", "degree": 2},
        # Widths a decade apart and centres far outside each other's frame, so the
        # near-duplicate grouping puts every synthetic location in its own group
        # unless a test deliberately collides two.
        "viewport": {"center_re": str(float(len(key)) + angle), "center_im": "0", "width": "1e-3"},
        "maxiter": 1000,
        "location_p_ge3": 0.9,
        "picture": f"{key}.jpg",
    }


def matrix_of(rows: list[dict], angles: list[float]):
    return numpy.array([unit(angle) for angle in angles], dtype=numpy.float32)


def candidate(
    identifier: str,
    key: str,
    head: str,
    p_ge3: float,
    p_ge4: float = 0.5,
    partition: str = "mandelbrot",
    center: str = "0",
) -> dict:
    """One flat candidate row, in the shape the seating compares."""
    return {
        "candidate": identifier,
        "source": {"run": "run9", "candidate": identifier, "key": None},
        "head": head,
        "partition": partition,
        "key": key,
        "family": {"kind": "mandelbrot", "degree": 2},
        "viewport": {"center_re": center, "center_im": "0", "width": "1e-3"},
        "maxiter": 1000,
        "mode": "smooth",
        "colormap": "viridis",
        "p_ge3": p_ge3,
        "p_ge4": p_ge4,
    }


SMOOTH, STRANGE = "smooth_render", "strange_render"


# --------------------------------------------------------------------------- #
# Step 4: the hard radius.
# --------------------------------------------------------------------------- #
def test_the_hard_radius_refuses_a_point_however_good_it_is() -> None:
    """Quality never buys a seat inside the radius. That is what makes it hard."""
    angles = [0.0, 0.02, 1.0]
    rows = [location(f"k{i}", angle) for i, angle in enumerate(angles)]
    matrix = matrix_of(rows, angles)
    # The best location by a distance is the one 0.02 radians from the first —
    # about 0.0002 cosine distance away, well inside any sane radius.
    quality = [0.5, 0.99, 0.1]
    picks, tally = gallery.choose(range(3), matrix, quality, 3, 0.05, 1.0)
    assert [pick.index for pick in picks] == [1, 2]
    assert tally["refused_by_radius"] == 1


def test_a_partition_that_runs_out_of_eligible_points_returns_fewer() -> None:
    """Not an error and not padding: the pool does not hold that many places."""
    angles = [0.0, 0.001, 0.002]
    rows = [location(f"k{i}", angle) for i, angle in enumerate(angles)]
    picks, tally = gallery.choose(range(3), matrix_of(rows, angles), [1.0] * 3, 3, 0.05, 1.0)
    assert len(picks) == 1
    assert tally["chosen"] == 1
    assert tally["eligible"] == 3


def test_the_first_pick_is_the_strongest_and_the_rest_are_gain_weighted() -> None:
    angles = [0.0, 0.8, 1.6]
    rows = [location(f"k{i}", angle) for i, angle in enumerate(angles)]
    matrix = matrix_of(rows, angles)
    picks, _ = gallery.choose(range(3), matrix, [0.1, 0.9, 0.2], 3, 0.01, 1.0)
    assert picks[0].index == 1  # strongest by quality, with nothing to be far from
    assert picks[0].distance is None
    assert {pick.index for pick in picks} == {0, 1, 2}
    assert all(pick.distance >= 0.01 for pick in picks[1:])


def test_a_zero_quality_weight_is_pure_farthest_point() -> None:
    """gamma of zero takes the judge out of the draw entirely."""
    angles = [0.0, 0.4, 2.4]
    rows = [location(f"k{i}", angle) for i, angle in enumerate(angles)]
    matrix = matrix_of(rows, angles)
    picks, _ = gallery.choose(range(3), matrix, [0.9, 0.9, 0.001], 2, 0.01, 0.0)
    # Second pick is the farthest one, not the second-best one.
    assert picks[1].index == 2


def test_the_retro_table_is_the_nearest_pairs_closest_first() -> None:
    angles = [0.0, 0.5, 1.9]
    rows = [location(f"k{i}", angle) for i, angle in enumerate(angles)]
    matrix = matrix_of(rows, angles)
    picks, _ = gallery.choose(range(3), matrix, [1.0, 1.0, 1.0], 3, 0.01, 1.0)
    table = gallery.retro_table(picks, matrix)
    assert len(table) == 3
    assert table == sorted(table, key=lambda cell: cell["cosine_distance"])


def test_the_neighbourhood_keeps_the_chosen_point_whatever_its_quality() -> None:
    angles = [0.0, 0.05, 0.06, 3.0]
    rows = [location(f"k{i}", angle) for i, angle in enumerate(angles)]
    matrix = matrix_of(rows, angles)
    near = gallery.neighbourhood(0, range(4), matrix, [0.01, 0.9, 0.8, 0.9], 3, 0.05)
    assert near[0] == 0
    assert set(near) == {0, 1, 2}


# --------------------------------------------------------------------------- #
# Step 6: the floors, one wallpaper per location, and unfilled slots.
# --------------------------------------------------------------------------- #
def slot(identifier: str, head: str, keys: list[str], partition: str = "mandelbrot"):
    return gallery.Slot(
        id=identifier, partition=partition, head=head, point=keys[0], locations=list(keys)
    )


def test_both_measured_floors_act_in_the_pass_and_only_one_acts_at_a_release() -> None:
    """The one place a head's cut reads differently at two sites, on purpose."""
    assert set(floors.MEASURED_RELEASE_FLOORS) == {SMOOTH, STRANGE}
    assert set(floors.ACTING_RELEASE_BARS) == {STRANGE}
    assert floors.release_bar(SMOOTH) is None
    assert floors.gallery_floor(SMOOTH).value == floors.SMOOTH_RELEASE_FLOOR.value
    assert floors.gallery_floor(STRANGE).value == floors.STRANGE_RELEASE_BAR.value


def test_a_head_with_no_measured_floor_cannot_fill_a_gallery_slot() -> None:
    with pytest.raises(ValueError, match="no release floor has been measured"):
        floors.gallery_floor("a_head_nobody_fit")


def test_each_floor_acts_on_its_own_head_and_neither_reaches_the_other() -> None:
    """A smooth candidate at 0.4 seats; a strange one at 0.4 does not, and the
    numbers are never compared to each other."""
    smooth_floor = floors.gallery_floor(SMOOTH).value
    strange_floor = floors.gallery_floor(STRANGE).value
    assert smooth_floor < 0.4 < strange_floor
    slots = [slot("0000", SMOOTH, ["a"]), slot("0001", STRANGE, ["b"])]
    gallery.seat(
        slots,
        [
            candidate("s", "a", SMOOTH, 0.4, center="0"),
            candidate("t", "b", STRANGE, 0.4, center="90"),
        ],
        log=lambda _line: None,
    )
    assert slots[0].seated is not None
    assert slots[1].seated is None
    assert slots[1].unfilled == "below_bar"
    assert slots[1].fill["below_floor"] == 1


def test_a_slot_with_nothing_above_the_floor_is_unfilled_and_never_padded() -> None:
    slots = [slot("0000", STRANGE, ["a"])]
    report = gallery.seat(
        slots,
        [candidate(str(i), "a", STRANGE, 0.1 + i / 100) for i in range(5)],
        log=lambda _line: None,
    )
    assert slots[0].seated is None
    assert slots[0].unfilled == "below_bar"
    assert slots[0].fill["why"] == selection.UNFILLED_REASONS["below_bar"]
    assert report["filled"] == 0
    assert report["unfilled"] == 1


def test_a_slot_with_no_candidate_at_all_says_so_rather_than_below_the_floor() -> None:
    slots = [slot("0000", STRANGE, ["nobody"])]
    gallery.seat(slots, [], log=lambda _line: None)
    assert slots[0].unfilled == "no_candidates"


def test_one_wallpaper_per_location_across_the_whole_pass() -> None:
    """Two slots wanting one place seat one wallpaper between them, and the
    higher-ranked slot keeps it."""
    slots = [slot("0000", SMOOTH, ["a"]), slot("0001", SMOOTH, ["a"], partition="phoenix")]
    report = gallery.seat(
        slots,
        [
            candidate("weak", "a", SMOOTH, 0.9, p_ge4=0.2),
            candidate("strong", "a", SMOOTH, 0.9, p_ge4=0.9),
        ],
        log=lambda _line: None,
    )
    assert floors.CLUSTER_CAP == 1
    seated = [s for s in slots if s.seated]
    assert len(seated) == 1
    assert seated[0].seated["candidate"] == "strong"
    empty = [s for s in slots if not s.seated][0]
    assert empty.unfilled == selection.LOCATION_SERVED
    assert report["filled"] == 1


def test_ranking_is_p_ge4_first_and_p_ge3_only_breaks_the_tie() -> None:
    ordered = sorted(
        [
            candidate("a", "k", SMOOTH, 0.99, p_ge4=0.10),
            candidate("b", "k", SMOOTH, 0.40, p_ge4=0.80),
            candidate("c", "k", SMOOTH, 0.90, p_ge4=0.80),
        ],
        key=gallery.rank_key,
    )
    assert [row["candidate"] for row in ordered] == ["c", "b", "a"]


def test_a_candidate_with_no_fourth_class_sorts_below_one_that_has_it() -> None:
    """Three-class rows exist in the pool; they are not read as a zero."""
    rows = sorted(
        [
            candidate("old", "k", STRANGE, 0.99, p_ge4=None),
            candidate("new", "k", STRANGE, 0.70, p_ge4=0.01),
        ],
        key=gallery.rank_key,
    )
    assert [row["candidate"] for row in rows] == ["new", "old"]


# --------------------------------------------------------------------------- #
# Steps 1 and 2: slots and the head split.
# --------------------------------------------------------------------------- #
def test_the_head_split_is_taken_per_partition() -> None:
    assert gallery.head_split(5, 0.6) == {SMOOTH: 2, STRANGE: 3}
    assert gallery.head_split(1, 0.6) == {SMOOTH: 0, STRANGE: 1}


def test_the_head_order_holds_both_heads_near_their_share_at_every_prefix() -> None:
    order = gallery.head_order({SMOOTH: 2, STRANGE: 3})
    assert sorted(order) == sorted([SMOOTH] * 2 + [STRANGE] * 3)
    assert order[0] == STRANGE
    assert order.count(SMOOTH) == 2


def test_the_pool_wide_denominator_is_every_embedded_location() -> None:
    rows = [location("a", 0.0), location("b", 1.0), location("c", 2.0, "phoenix")]
    assert gallery.population(rows) == {"mandelbrot": 2, "phoenix": 1}


# --------------------------------------------------------------------------- #
# Pass identity.
# --------------------------------------------------------------------------- #
@pytest.fixture
def record_root(tmp_path, monkeypatch):
    """Every record this process writes, redirected under `tmp_path`."""
    monkeypatch.setattr(records, "_ROOT", (tmp_path / "curation").resolve())
    return tmp_path / "curation"


def test_two_passes_leave_two_records_and_the_first_is_untouched(record_root) -> None:
    first = gallery.write_pass("gallery1", {"schema": 1, "pass": "gallery1", "seating": {}})
    before = first.read_text(encoding="utf-8")
    second = gallery.write_pass("gallery2", {"schema": 1, "pass": "gallery2", "seating": {}})
    assert first != second
    assert first.read_text(encoding="utf-8") == before
    assert json.loads(second.read_text(encoding="utf-8"))["pass"] == "gallery2"
    assert gallery.passes() == ["gallery1", "gallery2"]


def test_a_pass_record_lives_beside_the_runs_and_not_among_them(record_root) -> None:
    """A pass books no clock and measures no release rate, so it writes no run row."""
    gallery.write_pass("gallery1", {"schema": 1, "pass": "gallery1"})
    assert gallery.record_path("gallery1").parent.name == "gallery"
    assert not (record_root / "runs").exists()
    assert not (record_root / "runs.jsonl").exists()


def test_the_next_pass_id_is_the_next_unused_ordinal(record_root) -> None:
    assert gallery.next_pass_id() == "gallery1"
    gallery.write_pass("gallery1", {"schema": 1})
    assert gallery.next_pass_id() == "gallery2"
    gallery.write_pass("gallery7", {"schema": 1})
    assert gallery.next_pass_id() == "gallery8"


def test_a_pass_stamps_its_release_rows_with_the_gallery_collection(record_root) -> None:
    slots = [slot("0000", SMOOTH, ["a"])]
    gallery.seat(slots, [candidate("0000", "a", SMOOTH, 0.9, p_ge4=0.9)], log=lambda _l: None)
    slots[0].seated["release_picture"] = "release/0000.png"
    attempt = {
        "attempt": 0,
        "head": SMOOTH,
        "partition": "mandelbrot",
        "key": "a",
        "family": {"kind": "mandelbrot", "degree": 2},
        "viewport": {"center_re": "0", "center_im": "0", "width": "1e-3"},
        "maxiter": 1000,
        "mode": "smooth",
        "colormap": "viridis",
        "p_ge3": 0.9,
        "p_ge4": 0.9,
        "picture": "pictures/0000.jpg",
    }
    # The seated candidate carries the same id as the attempt, so the pass writes
    # one row for it rather than two.
    slots[0].seated["candidate"] = "0000"
    written = gallery.write_records("gallery1", slots, [attempt], ["mandelbrot"], lambda _l: None)
    assert written["release_rows"] == 1
    rows = records.read_decisions(records.RELEASE, "gallery1")
    assert [row["collection"] for row in rows] == [records.GALLERY]
    assert rows[0]["verdict"] == records.RELEASED
    assert rows[0]["slot"]["pass"] == "gallery1"
    assert rows[0]["slot_source"] == "guarantee"


# --------------------------------------------------------------------------- #
# The naming rule, at the one place a new module could reintroduce a retired name.
# --------------------------------------------------------------------------- #
def test_the_gallery_pass_carries_none_of_the_retired_vocabulary() -> None:
    """`test_banned_vocabulary` covers the tree; this says it out loud where the
    rename actually happened — the design this module is built from was called
    something else until 2026-08-22."""
    banned = re.compile(r"(?<![a-z])emissio[n](?![a-z])", re.IGNORECASE)
    for path in (
        Path("src/fractal_wallpapers/curation/gallery.py"),
        Path("src/fractal_wallpapers/curation/floors.py"),
        Path("src/fractal_wallpapers/cli.py"),
    ):
        assert not banned.search(path.read_text(encoding="utf-8")), path
