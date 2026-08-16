"""The autolevel operator: the identity, the curve, the guards, and the replay."""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.coloring import autolevel
from fractal_wallpapers.palettes import space

numpy = pytest.importorskip("numpy")

BANDS = {"black_pt": (0.0, 0.30), "white_pt": (0.86, 0.99), "mid": (0.26, 0.74)}


def stats(black=0.1, white=0.95, mid=0.5) -> dict:
    return {"black_pt": black, "black_pt_all": black, "white_pt": white, "mid": mid}


def test_in_band_on_all_three_is_the_exact_identity() -> None:
    curve = autolevel.derive_curve(stats(), BANDS)
    assert curve["identity"] is True
    lightness = numpy.linspace(0.0, 1.0, 101)
    moved = autolevel.apply_curve(lightness, curve)
    assert numpy.allclose(moved, lightness)


def test_the_curve_pins_both_ends_however_far_it_moves() -> None:
    """0 stays 0 and 1 stays 1: a true black is never lifted, a true white never dimmed."""
    curve = autolevel.derive_curve(stats(black=0.5, white=0.6, mid=0.55), BANDS)
    assert curve["identity"] is False
    moved = autolevel.apply_curve(numpy.array([0.0, 1.0]), curve)
    assert moved[0] == pytest.approx(0.0)
    assert moved[1] == pytest.approx(1.0)


def test_the_curve_is_monotone() -> None:
    curve = autolevel.derive_curve(stats(black=0.42, white=0.55, mid=0.5), BANDS)
    moved = autolevel.apply_curve(numpy.linspace(0.0, 1.0, 401), curve)
    assert numpy.all(numpy.diff(moved) >= -1e-12)


def test_a_statistic_with_no_band_leaves_that_end_alone() -> None:
    """An absent band is a refusal to say, not a zero — the same shape as the guard."""
    partial = {key: value for key, value in BANDS.items() if key != "black_pt"}
    out_of_band = stats(black=0.6, white=0.95, mid=0.5)
    curve = autolevel.derive_curve(out_of_band, partial)
    assert curve["out_ends"][0] == pytest.approx(0.6)


def test_the_chroma_guard_can_only_turn_a_correction_off() -> None:
    """An unmeasurable black point leaves the dark end where it was."""
    guarded = {**stats(black=0.6), "black_pt": None}
    curve = autolevel.derive_curve(guarded, BANDS)
    assert curve["black_guarded"] is True
    assert curve["out_ends"][0] == pytest.approx(curve["black_pt"])


def test_a_degenerate_range_proposes_no_curve() -> None:
    curve = autolevel.derive_curve(stats(black=0.50, white=0.52, mid=0.51), BANDS)
    assert curve["applies"] is False
    assert "degenerate" in curve["reason"]


def test_the_exponent_is_clamped_both_ways() -> None:
    for mid in (0.05, 0.94):
        curve = autolevel.derive_curve(stats(black=0.01, white=0.99, mid=mid), BANDS)
        assert curve["exponent"] >= 1.0 / autolevel.EXPONENT_CLAMP - 1e-9
        assert curve["exponent"] <= autolevel.EXPONENT_CLAMP + 1e-9


def test_the_direct_trap_family_is_excluded_by_kind() -> None:
    assert autolevel.applies_to("field")
    assert autolevel.applies_to("composite")
    assert not autolevel.applies_to("direct")


def test_the_switch_reads_at_call_time_and_a_typo_reads_as_the_default(monkeypatch) -> None:
    monkeypatch.setenv(autolevel.SWITCH_ENV, "0")
    assert autolevel.enabled() is False
    monkeypatch.setenv(autolevel.SWITCH_ENV, "on")
    assert autolevel.enabled() is True
    monkeypatch.setenv(autolevel.SWITCH_ENV, "maybe")
    assert autolevel.enabled() is autolevel.SWITCH_DEFAULT


def test_the_off_path_never_calls_the_renderer(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv(autolevel.SWITCH_ENV, "0")
    base = tmp_path / "base.png"
    base.write_bytes(b"not read")

    def refuse(stops):
        raise AssertionError("the off path must not re-render")

    leveled = autolevel.maybe_level(base, {"name": "x", "stops": [], "mirror": False}, refuse)
    assert leveled.image == base
    assert leveled.stamp is None


def stops(count: int = 8) -> list:
    """A ramp with real chroma in it, so the caps have something to act on."""
    draw = numpy.linspace(0.0, 1.0, count)
    colours = numpy.stack([(draw * 255), (255 - draw * 200), numpy.full(count, 90.0)], axis=-1)
    return [[float(p), [int(v) for v in row]] for p, row in zip(draw, colours, strict=True)]


def test_densify_is_the_identity_for_the_palette() -> None:
    """The engine interpolates its stops in Oklab; so does this, so it only refines."""
    ramp = stops()
    positions, lab = autolevel.densify(ramp)
    assert len(positions) == autolevel.DENSIFY * (len(ramp) - 1) + 1
    # Every original stop is reproduced exactly where it was.
    for position, colour in ramp:
        index = min(range(len(positions)), key=lambda i: abs(positions[i] - position))
        assert positions[index] == pytest.approx(position)
        assert numpy.allclose(space.srgb(lab[index]), colour, atol=1e-3)


def test_an_identity_curve_leaves_the_stops_where_they_were() -> None:
    curve = autolevel.derive_curve(stats(), BANDS)
    curved, capped = autolevel.curved_stops(stops(), curve)
    assert capped == 0
    original = {round(p, 9): c for p, c in stops()}
    for position, colour in curved:
        if round(position, 9) in original:
            assert colour == original[round(position, 9)]


def test_the_stamp_replays_the_stop_list_with_no_image() -> None:
    ramp = stops()
    curve = autolevel.derive_curve(stats(black=0.45, white=0.60, mid=0.55), BANDS)
    curved, capped = autolevel.curved_stops(ramp, curve)
    stamp = autolevel.make_stamp({}, curve, stats(), capped, len(curved), acted=True)
    assert autolevel.stops_from_stamp(stamp, ramp) == curved


def test_replaying_an_identity_stamp_is_refused() -> None:
    """There is no curved ramp for an in-band row, and pretending otherwise would
    make "replayed" mean two different things."""
    stamp = autolevel.make_stamp({}, autolevel.derive_curve(stats(), BANDS), stats(), 0, 0, False)
    with pytest.raises(autolevel.AutolevelError):
        autolevel.stops_from_stamp(stamp, stops())


def test_the_gamut_fit_keeps_lightness_rather_than_clipping_channels() -> None:
    """A per-channel clip would move L, which is the one axis the curve controls."""
    impossible = numpy.array([[0.55, 0.35, -0.25]])  # far outside sRGB
    fitted = autolevel.gamut_fit(impossible).astype(float)
    back = space.oklab(fitted)
    assert back[0][0] == pytest.approx(0.55, abs=0.02)


def test_a_neutral_render_measures_a_black_point_and_a_chromatic_one_does_not() -> None:
    grey = numpy.tile(numpy.linspace(0, 255, 256, dtype=numpy.uint8)[:, None, None], (1, 8, 3))
    assert autolevel.tone_stats(grey)["black_pt"] is not None

    saturated = numpy.zeros((64, 64, 3), dtype=numpy.uint8)
    saturated[..., 0] = 200
    assert autolevel.tone_stats(saturated)["black_pt"] is None


def test_the_override_colormap_carries_the_kind_through(tmp_path) -> None:
    """The engine's fold decision is the map's, so it has to ride along unchanged."""
    path = autolevel.overriding_colormap("some_map", stops(), "cyclic", tmp_path)
    written = json.loads(path.read_text(encoding="utf-8"))
    assert path.name == "some_map.json"
    assert written["kind"] == "cyclic"
    assert written["stops"] == stops()


def test_densify_spans_a_real_colormap_end_to_end() -> None:
    """Every tracked map carries an explicit stop at 0 *and* at 1.

    This is the regression the wrap segment was: folding position 1 around to 0
    put two stops on top of each other and left the ramp reaching only as far as
    the second-to-last one — a different palette wearing this one's name, on
    every render the operator acted on.
    """
    ramp = space.ramp("twilight_shifted")
    stops_ = [[float(p), [int(v) for v in c]] for p, c in zip(ramp[0], ramp[1], strict=True)]
    assert stops_[0][0] == 0.0 and stops_[-1][0] == 1.0
    positions, lab = autolevel.densify(stops_)
    assert positions[0] == 0.0
    assert positions[-1] == 1.0
    assert len(positions) == autolevel.DENSIFY * (len(stops_) - 1) + 1
    assert positions == sorted(positions)
    assert numpy.allclose(space.srgb(lab[-1]), stops_[-1][1], atol=1e-3)
