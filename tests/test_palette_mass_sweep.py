"""The leg that closes a colour-mass hole, and the append it feeds.

Nothing here renders. What a render leg has that a test can hold it to is its
*instrument* — the panel it draws, the maps it claims are unmeasured, the row
shape it writes — and the append that turns those rows into tracked ones, which
is the half that can quietly damage a record that is already committed.

The failure this file exists to catch is a **silent re-cut**. `color_mass.build`
reads both measurements and rewrites every file; the census's own record is not
kept, so a rebuild today would drop 15,681 observations and move all 14,796
existing rows with no error anywhere. [`color_mass.extend`] is the path that
cannot do that, and the test below is the reason to believe it: every row that
was there comes back byte-identical.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.palettes import color_mass, mass_sweep


def test_the_panel_is_the_one_the_tracked_manifest_names() -> None:
    """The manifest owns *where* the map was measured and the module owns *how to
    draw it*, so the two are a pair that can disagree. A row measured at a place
    the manifest does not name would be filed beside rows that were not, and
    nothing downstream could tell — which is why this is a refusal at the door
    rather than a column on the row."""
    from fractal_wallpapers.supply.location import key_text, location_key

    named = json.loads(color_mass.sweep_manifest_path().read_text(encoding="utf-8"))["panel"][
        "keys"
    ]
    places = mass_sweep.panel()
    assert len(places) == len(mass_sweep.PANEL) == len(named)
    for place in places:
        assert place["key"] in named
        assert place["key"] == key_text(location_key(place["family"], place["viewport"]))
        # The cap is derived and not stored: the manifest carries no maxiter, and
        # a constant here would be a second opinion about what the sweep drew.
        assert place["maxiter"] > 0


def test_a_panel_location_the_manifest_does_not_name_is_refused(monkeypatch) -> None:
    moved = [
        {
            "family": {"kind": "mandelbrot", "degree": 2},
            "viewport": {"center_re": "0", "center_im": "0", "width": "3"},
        }
    ]
    monkeypatch.setattr(mass_sweep, "PANEL", tuple(moved))
    with pytest.raises(mass_sweep.MassSweepError, match="panel keys"):
        mass_sweep.panel()


def test_the_unmeasured_maps_are_drawable_and_have_no_row() -> None:
    """The draw pool and not the library. A map production cannot pick is a map
    whose realized colour nothing would read, and measuring it would spend the
    panel on a row with no reader."""
    from fractal_wallpapers.curation import colorize
    from fractal_wallpapers.palettes import groups

    table = color_mass.read()
    measured = {group for group, _mode in table}
    member = groups.member_groups()
    offered = set(colorize.pool(0))
    for name in mass_sweep.unmeasured_maps():
        assert name in offered
        assert groups.group_of(name, member) not in measured


def test_a_row_carries_the_raw_census_the_cut_reduces_itself() -> None:
    """The sweep's rows hold all fifty-two cells, neutrals included, because
    `color_mass.tally` takes the chromatic reduction. A row reduced here would be
    renormalised a second time and every neutral-heavy pair would read as more
    colourful than it is."""
    place = mass_sweep.panel()[0]
    row = mass_sweep.row_of(
        "twilight_shifted",
        "smooth",
        place,
        {"dark_vivid_red": 0.25, "black": 0.75, "white": 0.0},
        mirror=True,
        leveled=True,
        seconds=1.2345,
    )
    assert row["kind"] == mass_sweep.RENDER_ROW
    assert row["schema"] == mass_sweep.SCHEMA
    assert row["error"] is None
    assert row["location"] == place["key"]
    assert row["shares"] == {"dark_vivid_red": 0.25, "black": 0.75}, "a neutral was dropped"
    assert row["seconds"] == 1.234


def _map_of(tmp_path, rows: list[dict], monkeypatch):
    """A one-mode colour-mass map on disk, and the module pointed at it."""
    monkeypatch.setattr(color_mass, "colormap_dir", lambda: tmp_path)
    header = color_mass.method_row(
        "smooth",
        {"pairs": len(rows), "cells_stored": 0, "cells_below_floor": 0, "mass_below_floor": 0.0},
        {"census": {"path": "gone", "observations": 1}},
    )
    color_mass.write_mode("smooth", [header, *rows])
    return color_mass.record_path("smooth")


def test_extend_appends_the_new_group_and_leaves_every_old_row_byte_identical(
    tmp_path, monkeypatch
) -> None:
    """The whole reason this path exists. `build` rewrites every file from both
    measurements and one of them is not kept any more, so the only safe cut is one
    that touches nothing it did not measure."""
    old = {
        "schema": 1,
        "kind": color_mass.PAIR_ROW,
        "group": "m01",
        "mode": "smooth",
        "observations": {"census": 3, "sweep": 2},
        "autolevel": {"acted": 1, "unrecorded": 0},
        "colourless": 0,
        "cells": {"dark_vivid_red": 0.5},
    }
    path = _map_of(tmp_path, [old], monkeypatch)
    sweep = tmp_path / "rows.jsonl"
    sweep.write_text(
        "".join(
            json.dumps(row) + "\n"
            for row in (
                {
                    "kind": "render",
                    "group": "map:new",
                    "mode": "smooth",
                    "leveled": True,
                    "shares": {"dark_vivid_green": 0.5, "black": 0.5},
                },
                # A row for a group that already has one is skipped rather than
                # unioned: its mean stands on a census half that cannot be re-read.
                {
                    "kind": "render",
                    "group": "m01",
                    "mode": "smooth",
                    "leveled": True,
                    "shares": {"dark_vivid_blue": 1.0},
                },
            )
        ),
        encoding="utf-8",
        newline="\n",
    )
    report = color_mass.extend(sweep, log=lambda *_: None)
    assert report["groups"] == 1 and report["pairs"] == 1
    _method, pairs = color_mass.read_mode("smooth")
    kept = {row["group"]: row for row in pairs}
    assert set(kept) == {"m01", "map:new"}
    assert kept["m01"] == old, "an existing row moved"
    assert kept["map:new"]["observations"] == {"census": 0, "sweep": 1}
    assert kept["map:new"]["cells"] == {"dark_vivid_green": 1.0}
    assert path.read_bytes().count(b"\r") == 0, "a tracked file was written with CRLF"


def test_extend_says_on_the_header_what_it_appended_and_when(tmp_path, monkeypatch) -> None:
    """`sources` is the provenance of the *build* and a drop did not change what
    that was cut from, so what is appended goes in a name of its own."""
    _map_of(tmp_path, [], monkeypatch)
    sweep = tmp_path / "rows.jsonl"
    sweep.write_text(
        json.dumps(
            {
                "kind": "render",
                "group": "map:new",
                "mode": "smooth",
                "leveled": False,
                "shares": {"dark_vivid_green": 1.0},
            }
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    color_mass.extend(sweep, log=lambda *_: None)
    method, _pairs = color_mass.read_mode("smooth")
    (entry,) = method["extensions"]
    assert entry["pairs"] == 1 and entry["sweep_observations"] == 1
    assert entry["when"] == color_mass._today()
    assert method["sources"]["census"]["observations"] == 1, "the build's provenance moved"


def test_extend_refuses_a_log_with_nothing_new_in_it(tmp_path, monkeypatch) -> None:
    """A leg that measured only groups the map already holds has measured nothing,
    and a silent no-op there reads as a successful close of a hole that is open."""
    _map_of(tmp_path, [], monkeypatch)
    sweep = tmp_path / "rows.jsonl"
    sweep.write_text("", encoding="utf-8", newline="\n")
    with pytest.raises(color_mass.ColorMassError, match="nothing to append"):
        color_mass.extend(sweep, log=lambda *_: None)
