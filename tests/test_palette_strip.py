"""A map's gradient as a picture, and the fold that decides which gradient it is.

The strip exists to be looked at in an article, so the thing worth testing is not
that it produced bytes — it is that the bytes came from the engine's own bake and
that the fold matches the rule everything else in this repository colours by.
"""

from __future__ import annotations

import json
import struct

import pytest

from fractal_wallpapers import engine
from fractal_wallpapers.palettes import strip
from fractal_wallpapers.paths import colormap_dir

pytestmark = pytest.mark.skipif(
    not engine.engine_path().is_file(),
    reason="the strip is drawn by the engine; build it in release first",
)


def test_the_ramp_runs_end_to_end_in_every_row() -> None:
    """A strip is a gradient, not a picture of one: every row is the same sweep,
    and the last column is exactly the colour the map closes on."""
    values = struct.unpack("<12f", strip.ramp(4, 3))
    assert values[:4] == pytest.approx((0.0, 1 / 3, 2 / 3, 1.0))
    assert values[4:8] == values[:4] == values[8:]
    with pytest.raises(strip.StripError):
        strip.ramp(1, 1)


@pytest.mark.slow
def test_the_fold_follows_the_map_and_a_caller_may_override_it() -> None:
    """The rule is `palette_sets.recipe_for`'s and this only reads it: a sequential
    map folds, a cyclic one does not, and either can be asked for by hand."""
    assert strip.mirror_for("viridis") is True
    assert strip.mirror_for("twilight_shifted") is False
    assert strip.mirror_for("viridis", override=False) is False
    assert strip.mirror_for("twilight_shifted", override=True) is True


@pytest.mark.slow
def test_a_folded_strip_is_symmetric_and_an_unfolded_one_is_not(tmp_path) -> None:
    """The whole content of `mirror`: out and back, so the two ends meet. Read off
    the picture the engine made rather than off the recipe that asked for it."""
    image = pytest.importorskip("PIL.Image", reason="reading the strip back needs pillow")

    folded = tmp_path / "folded.png"
    flat = tmp_path / "flat.png"
    assert strip.draw("viridis", folded, width=256, height=4)["mirror"] is True
    assert strip.draw("viridis", flat, width=256, height=4, mirror=False)["mirror"] is False

    def mirrored_gap(path) -> float:
        """Mean channel difference between the strip and its own reflection.

        A mean rather than a maximum: the fold is exact in the gradient and the
        picture is 8-bit, so a column or two lands a level or three off its
        partner. What tells the two pictures apart is not a single column.
        """
        with image.open(path) as opened:
            pixels = opened.convert("RGB").load()
        # The outer half percent is the end colour held flat by the coloring's
        # own percentile clip, so the reflection is measured inside it.
        margin = 4
        gaps = [
            abs(one - other)
            for column in range(margin, 256 - margin)
            for one, other in zip(pixels[column, 0], pixels[255 - column, 0], strict=True)
        ]
        return sum(gaps) / len(gaps)

    assert mirrored_gap(folded) < 1.0
    assert mirrored_gap(flat) > 40.0


def test_the_record_describes_the_field_the_engine_is_handed(tmp_path) -> None:
    """The engine refuses a record whose dtype or layout it cannot read, and that
    refusal is what stops a field being read as a picture. The record this module
    writes has to be one the engine round-trips."""
    field = tmp_path / "ramp.f32"
    written = strip.record("viridis", 8, 2, field.name)
    field.write_bytes(strip.ramp(8, 2))
    field.with_suffix(".json").write_text(json.dumps(written), encoding="utf-8", newline="\n")
    report = engine.recolor(
        {
            "schema": 1,
            "field": str(field),
            "colormap": "viridis",
            "colormap_dir": str(colormap_dir()),
            "output": str(tmp_path / "out.png"),
        }
    )
    assert report["resolution"] == [8, 2]
    assert report["colormap"] == "viridis"


def test_a_manifest_is_a_list_of_names_and_says_so(tmp_path) -> None:
    """A batch subcommand takes a manifest because a Windows command line
    overflows long before the batch does. What it carries here is names."""
    manifest = tmp_path / "names.txt"
    manifest.write_text(
        "# the two the tile floor reserves\nviridis\n\n  twilight_shifted  # canonical\n",
        encoding="utf-8",
    )
    assert strip.names_from(manifest) == ["viridis", "twilight_shifted"]


def test_a_map_this_repository_does_not_hold_is_refused(tmp_path) -> None:
    """No map, no gradient — and a refusal rather than an empty picture."""
    with pytest.raises(strip.StripError):
        strip.draw("a map nobody has", tmp_path / "nope.png")
