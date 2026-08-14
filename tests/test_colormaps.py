"""The tracked colormaps are data the renderer trusts, so it is checked here.

A malformed colormap does not crash a render; it produces a picture that is
subtly wrong in a way nobody notices until it is in the corpus. These are the
properties the engine's loader assumes and does not re-verify per lookup.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.paths import colormap_dir

COLORMAP_FILES = sorted(colormap_dir().glob("*.json"))


def test_there_are_colormaps_to_render_with() -> None:
    assert COLORMAP_FILES, "no colormaps under data/palettes"


@pytest.mark.parametrize("path", COLORMAP_FILES, ids=lambda p: p.stem)
def test_a_colormap_is_well_formed(path) -> None:
    colormap = json.loads(path.read_text(encoding="utf-8"))

    assert colormap["schema"] == 1
    assert colormap["name"] == path.stem, "a colormap's name is its filename"
    assert colormap["kind"] in ("cyclic", "sequential")
    assert colormap["source"].strip(), "a colormap says where it came from"

    stops = colormap["stops"]
    assert len(stops) >= 2, "a gradient needs two ends"

    positions = [position for position, _ in stops]
    assert positions == sorted(positions), "stops are in order"
    assert positions[0] == 0.0 and positions[-1] == 1.0, "stops span the whole range"
    assert len(set(positions)) == len(positions), "no two stops share a position"

    for _, rgb in stops:
        assert len(rgb) == 3
        assert all(isinstance(channel, int) and 0 <= channel <= 255 for channel in rgb)

    if colormap["kind"] == "cyclic":
        assert stops[0][1] == stops[-1][1], "a cyclic map closes on the color it opened with"
