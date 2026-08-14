"""The tracked seed pools, and the invariants a later edit could break.

The `c`-spacing floor is checked here against the shipped file rather than
against a fixture, because the shipped file is what a run loads. A pool that has
quietly saturated its own spacing is indistinguishable from a healthy one until
a run comes back with nothing new in it.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.discovery import pools


def test_the_julia_pool_clears_its_own_spacing_floor() -> None:
    """The one property the pool has, and the one an edit would break silently.

    The floor is a tolerance chosen against pool cost, not a point where the
    looks stop being similar: measured at a fixed viewport across five decades
    of separation, the near-duplicate rate falls smoothly the whole way and
    there is no knee to read a floor off. What it buys is a stated rate at the
    bottom of the admitted band, not a guarantee of distinctness.
    """
    seeds = pools.julia_pool()
    assert len(seeds) == 209
    closest = pools.closest_pair([(float(s.c[0]), float(s.c[1])) for s in seeds])
    assert closest >= pools.C_SPACING_FLOOR
    assert closest < 2 * pools.C_SPACING_FLOOR, (
        "the pool sits at its floor; a much larger gap would mean the floor is "
        "not what thinned it and this check is not testing what it says"
    )


def test_a_pool_under_the_floor_is_refused_rather_than_thinned(tmp_path) -> None:
    """Verified, not enforced: thinning here would leave the file on disk and
    the pool in memory as different objects, and the file is the artifact."""
    path = tmp_path / "pool.jsonl"
    path.write_text(
        "\n".join(
            json.dumps({"schema": 1, "id": f"j{i}", "c": [str(i * 1e-3), "0"], "channel": "x"})
            for i in range(3)
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="c-spacing floor"):
        pools.julia_pool(path)


def test_a_julia_seed_is_a_parameter_and_carries_its_own_family() -> None:
    """The pool seeds *roots*, and a Julia root is a `c` — the viewport comes
    from the walk. Two views at one viewport with different `c` are different
    fractals, so the family has to ride with the seed."""
    seed = pools.julia_pool()[0]
    family = seed.family()
    assert family["kind"] == "julia" and family["degree"] == 2
    assert family["c"] == [seed.c[0], seed.c[1]]
    assert all(isinstance(part, str) for part in family["c"]), "coordinates stay strings"


def test_every_julia_channel_is_provenance_and_nothing_selects_on_it() -> None:
    channels = {seed.channel for seed in pools.julia_pool()}
    assert channels == {"ranked_harvest", "cheap_harvest", "near_minibrot", "near_boundary"}


def test_a_phoenix_seed_is_the_whole_parameter_point() -> None:
    """All six numbers, and this is not bookkeeping: the recurrence carries
    `z₋₁` forward, so any non-zero value moves pixels, and a pool that recorded
    only `c` would be a pool of different fractals under one name."""
    seeds = pools.phoenix_pool()
    assert len(seeds) == 96
    family = seeds[0].family()
    assert family["kind"] == "phoenix"
    assert {"c", "p", "z_prev"} <= set(family)
    assert any(seed.z_prev != ("0", "0") for seed in seeds), "z₋₁ is a live axis"
    assert any(float(seed.p[1]) != 0.0 for seed in seeds), "p is complex here"


def test_the_real_p_sub_mode_is_not_the_classic_point() -> None:
    """The flag records how a seed was *drawn* — `p` real, no displacement off
    the stability curve, `z₋₁` zero — and it is *not* the classic pinned
    instance. Conflating the two reads a handful of ordinary seeds as a named
    location, which is exactly the mistake the name is chosen to prevent: `c`
    still comes from the closed form at a complex phase, so these seeds are not
    even on the real axis."""
    flagged = [seed for seed in pools.phoenix_pool() if seed.real_p_mode]
    assert flagged, "the sub-mode is present in the pool"
    for seed in flagged:
        assert float(seed.p[1]) == 0.0, "p is real"
        assert float(seed.offset) == 0.0, "and sits exactly on the curve"
        assert (float(seed.z_prev[0]), float(seed.z_prev[1])) == (0.0, 0.0)
        assert (float(seed.c[0]), float(seed.c[1])) != (0.5667, 0.0), "not the classic point"
    assert any(float(seed.c[1]) != 0.0 for seed in flagged), "and c is complex"


def test_the_branches_are_the_two_the_labels_kept() -> None:
    """Cardioid and period-2 only. The root branch was drawn, labeled, and
    measured dead to a human eye, so it is not in the shipped pool."""
    branches = {seed.branch for seed in pools.phoenix_pool()}
    assert branches == {"cardioid", "period2"}


def test_a_row_of_the_wrong_schema_is_refused(tmp_path) -> None:
    path = tmp_path / "rows.jsonl"
    path.write_text(json.dumps({"schema": 2, "id": "x"}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="schema"):
        pools.read_rows(path)


def test_a_seed_file_row_carries_a_whole_location(tmp_path) -> None:
    """A c-plane root is a *place*, not a parameter, so the family and the view
    are on one line and a row never needs a second file to mean anything."""
    path = tmp_path / "seeds.jsonl"
    path.write_text(
        json.dumps(
            {
                "schema": 1,
                "family": {"kind": "mandelbrot"},
                "viewport": {"center_re": "-0.75", "center_im": "0.1", "width": "0.2"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    assert pools.read_seed_file(path)[0]["family"]["kind"] == "mandelbrot"

    path.write_text(json.dumps({"schema": 1, "viewport": {}}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="family"):
        pools.read_seed_file(path)
