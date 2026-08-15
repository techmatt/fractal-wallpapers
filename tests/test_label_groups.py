"""Location groups, and the sweep that once collapsed into one of them.

The regression this file exists for: a family swept at a fixed frame, varying a
constant the grouping does not read, folds its whole sweep into a single group —
and a holdout drawn on those groups has one of it. It happened to a five-hundred
row phoenix parameter sweep, and it is available to any family with more than one
constant.
"""

from __future__ import annotations

from fractal_wallpapers.labeling import groups


def row(family: dict, center_re="0.0", center_im="0.0", width="1.0") -> dict:
    return {
        "family": family,
        "viewport": {"center_re": center_re, "center_im": center_im, "width": width},
    }


def phoenix(c=("0.5667", "0.0"), p=("-0.5", "0.0"), z=("0.0", "0.0")) -> dict:
    return {"kind": "phoenix", "c": list(c), "p": list(p), "z_prev": list(z)}


def test_a_sweep_at_one_frame_is_not_one_group() -> None:
    """Twenty phoenix points sharing a seed and a frame, differing only in `p`.
    Grouped on the seed alone they are one group; grouped on the exact non-`c`
    axes they are twenty, which is the whole difference between a family that can
    be held out and one that cannot."""
    rows = [row(phoenix(p=(f"-0.5{i:02d}", "0.0"))) for i in range(20)]
    assert groups.assign(rows).size() == 20


def test_the_same_sweep_varying_the_slice_coordinate_also_separates() -> None:
    """`z₋₁` is carried forward by the recurrence, so a different one is a
    different fractal — and it is exactly the axis a `c`-only rule cannot see."""
    rows = [row(phoenix(z=(f"0.0{i}", "0.0"))) for i in range(8)]
    assert groups.assign(rows).size() == 8


def test_one_plane_at_overlapping_frames_is_one_group() -> None:
    rows = [row(phoenix()), row(phoenix(), center_re="0.1", width="1.2")]
    assert groups.assign(rows).size() == 1


def test_frames_a_long_way_apart_are_not_neighbours() -> None:
    rows = [row({"kind": "mandelbrot"}), row({"kind": "mandelbrot"}, center_re="9.0")]
    assert groups.assign(rows).size() == 2


def test_frames_at_different_scales_are_not_neighbours() -> None:
    rows = [row({"kind": "mandelbrot"}), row({"kind": "mandelbrot"}, width="4.0")]
    assert groups.assign(rows).size() == 2


def test_a_ladder_of_near_seeds_at_one_frame_is_one_group() -> None:
    """The mirror failure. A `c` ladder produces neighbours differing in the
    eighth decimal place; on an exact-`c` rule each would be its own group and
    near-identical pictures would land on opposite sides of the holdout."""
    rows = [row({"kind": "julia", "degree": 2, "c": [f"-0.400000{i}", "0.6"]}) for i in range(1, 6)]
    assert groups.assign(rows).size() == 1


def test_seeds_further_apart_than_the_tolerance_are_separate_groups() -> None:
    rows = [
        row({"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]}),
        row({"kind": "julia", "degree": 2, "c": ["-0.5", "0.6"]}),
    ]
    assert groups.assign(rows).size() == 2


def test_degree_separates_planes() -> None:
    rows = [
        row({"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]}),
        row({"kind": "julia", "degree": 3, "c": ["-0.4", "0.6"]}),
    ]
    assert groups.assign(rows).size() == 2


def test_a_row_with_no_location_is_counted_and_not_grouped() -> None:
    grouping = groups.assign([row({"kind": "mandelbrot"}), {"family": {"kind": "mandelbrot"}}])
    assert grouping.n_unplaced == 1
    assert grouping.size() == 1
    assert grouping.of_row[1] is None


def test_groups_are_transitive_along_a_chain() -> None:
    """Neighbourhood is a relation; a group is its connected component. Three
    frames each overlapping the next are one group even though the ends do not
    overlap each other."""
    rows = [
        row({"kind": "mandelbrot"}, center_re="0.0"),
        row({"kind": "mandelbrot"}, center_re="0.4"),
        row({"kind": "mandelbrot"}, center_re="0.8"),
    ]
    assert groups.assign(rows).size() == 1


def test_two_spellings_of_one_constant_are_one_plane() -> None:
    assert groups.plane_of(phoenix(p=("-0.50", "0"))) == groups.plane_of(phoenix(p=("-0.5", "0.0")))
