"""The colour-mass map: what it says, and the two ways it could quietly stop saying it.

Rebuilding the map is a pass over 43 MB of experiment log, and the sweep half of
that log is archived off this machine — so what is pinned here is the **committed
record**: its shape, its completeness, and the invariants a reader relies on
without knowing it. The arithmetic behind one row is checked on rows built by
hand, where a mean over two observations is a number the test can state outright.

Two failures this file exists to catch:

* **the guard.** A tracked file over 1 MiB fails `test_history_purity`, and the
  whole reason the map is eighteen files rather than one is that it is nearly
  seven megabytes. That split is a decision, and a rebuild that quietly rejoined
  it would be a build failure a long way from here.
* **a silent hole.** The map is complete — every palette group in every production
  mode — and a row missing from it reads exactly like a pair with no colour.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.palettes import color_mass, dominance, groups

#: The 1 MiB per-file cap `tests/test_history_purity.py` holds every tracked file
#: to. Named here too, because the map's split into one file per mode is a
#: response to it and a rejoin would be caught first by the guard and only then
#: understood.
GUARD_BYTES = 1 << 20


def files() -> list:
    return sorted(color_mass.record_dir().glob("*.jsonl"))


def test_the_map_is_committed_and_every_file_is_well_under_the_history_guard() -> None:
    written = files()
    assert written, f"{color_mass.record_dir()} holds no map"
    for path in written:
        size = path.stat().st_size
        assert size < GUARD_BYTES // 2, (
            f"{path.name} is {size:,} bytes, over half the {GUARD_BYTES:,}-byte per-file "
            f"guard. The map splits per mode BECAUSE of that guard; a file this size means "
            f"the split has stopped being enough and wants another axis, not a bigger file"
        )


def test_every_palette_group_is_in_every_production_mode() -> None:
    """A pair absent from the map and a pair with no colour read identically off a
    lookup, so the map is complete by construction: the sweep measured the whole
    grid and the census only ever added to it."""
    from fractal_wallpapers import engine

    table = color_mass.read()
    library = {row["group"] for row in groups.groups()} | {
        f"map:{name}" for name in groups.library()
    }
    named = {group for group, _mode in table}
    assert named <= library, sorted(named - library)[:5]
    modes = {mode for _group, mode in table}
    assert modes == set(engine.production_modes())
    assert len(table) == len(named) * len(modes), "the grid has a hole in it"


def test_the_noisy_modes_are_flagged_and_kept() -> None:
    """`gaussian_int` and three of the direct traps average colour AFTER the
    colormap lookup, so their pictures are not lookups into their own maps. They
    are marked so a reader can down-weight them — and they are NOT dropped, because
    what they read is what the pipeline really produces."""
    table = color_mass.read()
    flagged = {mode for (_group, mode), row in table.items() if row["noisy"]}
    assert flagged == set(color_mass.NOISY_MODES)
    for mode in color_mass.NOISY_MODES:
        assert any(mode == name for _group, name in table), f"{mode} was dropped rather than marked"


def test_every_row_carries_its_evidence_and_its_operator() -> None:
    """The three columns a reader has to have: how many renders stand behind the
    means, how many of them autolevel acted on, and how many of them made no
    colour at all. Autolevel matters because it rewrites the map's stops — one
    pair reads teal 0.002 unlevelled and 0.266 levelled — so a mean whose evidence
    is all levelled is a different prediction from one whose evidence is not."""
    for path in files():
        _method, pairs = color_mass.read_mode(path.stem)
        for row in pairs:
            seen = color_mass.observations(row)
            assert seen > 0, f"{row['group']} x {row['mode']} has a mean over nothing"
            assert set(row["observations"]) == set(color_mass.SOURCES)
            assert 0 <= row["autolevel"]["acted"] <= seen
            assert 0 <= row["autolevel"]["unrecorded"] <= seen
            assert 0 <= row["colourless"] <= seen


def test_the_shares_are_of_the_colour_and_never_sum_over_one() -> None:
    """Neutrals are out of the numerator and the denominator, so a row's cells are
    shares of the picture's COLOUR. The stored cells sum to at most 1 and the
    residual is what the sparsity floor dropped — which is what lets a reader
    recover it as `1 - sum` instead of having to know the rule."""
    names = set(dominance.cells())
    for path in files():
        method, pairs = color_mass.read_mode(path.stem)
        assert method["stored_floor"] == color_mass.STORED_FLOOR
        for row in pairs:
            assert set(row["cells"]) <= names, sorted(set(row["cells"]) - names)[:3]
            assert all(value >= color_mass.STORED_FLOOR for value in row["cells"].values())
            # The underlying means sum to at most 1 exactly; each stored cell is
            # rounded to four places, so the file may read up to half a unit in the
            # last place per cell above it. Anything past that is not rounding.
            assert sum(row["cells"].values()) <= 1.0 + 5e-5 * len(row["cells"])


def test_a_cell_the_floor_dropped_reads_as_the_number_it_is() -> None:
    """Absent is not missing. A caller asking for a cell that fell under the floor
    gets a share, because the alternative is every reader knowing the storage rule."""
    row = {"cells": {"dark_vivid_red": 0.5}}
    assert color_mass.share_of(row, "dark_vivid_red") == 0.5
    assert color_mass.share_of(row, "dark_vivid_green") == 0.0


# --------------------------------------------------------------------------- #
# The arithmetic, on rows small enough to state the answer for.
# --------------------------------------------------------------------------- #
def written(tmp_path, census: list[dict], sweep: list[dict]):
    census_path = tmp_path / "observations.jsonl"
    sweep_path = tmp_path / "rows.jsonl"
    census_path.write_text(
        "".join(json.dumps(row) + "\n" for row in census), encoding="utf-8", newline="\n"
    )
    sweep_path.write_text(
        "".join(json.dumps(row) + "\n" for row in sweep), encoding="utf-8", newline="\n"
    )
    return census_path, sweep_path


def test_the_two_sources_are_pooled_by_observation_and_counted_apart(tmp_path, monkeypatch) -> None:
    """One mean over both measurements — they are readings of the same quantity —
    but the counts stay apart, because they are two populations: the census is
    where the palette head chose to go and the sweep is a seeded two-location
    panel over the grid it never visited."""
    monkeypatch.setattr(color_mass, "_levelled_by_picture", dict)
    census, sweep = written(
        tmp_path,
        [{"group": "m01", "mode": "smooth", "picture": "a.jpg", "cells": {"dark_vivid_red": 1.0}}],
        [
            {
                "kind": "render",
                "group": "m01",
                "mode": "smooth",
                "leveled": True,
                "shares": {"dark_vivid_red": 0.25, "dark_vivid_blue": 0.25, "black": 0.5},
            }
        ],
    )
    table, counts = color_mass.tally(census, sweep, log=lambda *_: None)
    assert counts == {"census": 1, "sweep": 1, "colourless": 0, "unrecorded": 1}
    rows, _price = color_mass.rows_for("smooth", table, floor=0.0)
    (row,) = rows
    assert row["observations"] == {"census": 1, "sweep": 1}
    assert row["autolevel"] == {"acted": 1, "unrecorded": 1}
    # The sweep row is half neutral, and neutrals leave both halves of the ratio:
    # its chromatic mass is 0.5 red and 0.5 blue, not 0.25 and 0.25.
    assert row["cells"] == {"dark_vivid_red": 0.75, "dark_vivid_blue": 0.25}


def test_a_render_that_made_no_colour_is_in_the_denominator(tmp_path, monkeypatch) -> None:
    """The honest arithmetic: the render happened and produced no chromatic pixel,
    so it belongs in `n`. 1,576 of the sweep's renders and 217 of the census's are
    in that position, and dropping them would report a pair as more colourful than
    it is."""
    monkeypatch.setattr(color_mass, "_levelled_by_picture", dict)
    census, sweep = written(
        tmp_path,
        [{"group": "m01", "mode": "smooth", "picture": "a.jpg", "cells": {"dark_vivid_red": 1.0}}],
        [
            {
                "kind": "render",
                "group": "m01",
                "mode": "smooth",
                "leveled": False,
                "shares": {"black": 1.0},
            }
        ],
    )
    table, counts = color_mass.tally(census, sweep, log=lambda *_: None)
    assert counts["colourless"] == 1
    rows, _price = color_mass.rows_for("smooth", table, floor=0.0)
    (row,) = rows
    assert row["colourless"] == 1
    assert row["cells"] == {"dark_vivid_red": 0.5}, "a colourless render was dropped from n"


def test_a_failed_sweep_render_refuses_rather_than_leaving_a_hole(tmp_path, monkeypatch) -> None:
    """The sweep reported zero failures over 13,020 pairs. A map cut over a log
    that has some would carry a pair whose mean stands on fewer renders than its
    `n` claims, with nothing on the row saying so."""
    monkeypatch.setattr(color_mass, "_levelled_by_picture", dict)
    census, sweep = written(
        tmp_path,
        [],
        [
            {
                "kind": "render",
                "group": "m01",
                "mode": "smooth",
                "error": "engine died",
                "shares": {},
            }
        ],
    )
    with pytest.raises(color_mass.ColorMassError, match="failed render"):
        color_mass.tally(census, sweep, log=lambda *_: None)
