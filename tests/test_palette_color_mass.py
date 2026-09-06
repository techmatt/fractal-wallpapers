"""The colour-mass map: what it says, and the two ways it could quietly stop saying it.

Rebuilding the map is a pass over 43 MB of experiment log, and the sweep half of
that log is archived off this machine — so what is pinned here is the **committed
record**: its shape, its completeness, and the invariants a reader relies on
without knowing it. The arithmetic behind one row is checked on rows built by
hand, where a mean over two observations is a number the test can state outright.

Two failures this file exists to catch:

* **the guard.** A tracked file over 1 MiB fails `test_history_purity`, and the
  whole reason the map is eighteen files rather than one is that it is 7.77 MB.
  That split is a decision, and a rebuild that quietly rejoined it would be a
  build failure a long way from here. [`SPLIT_BYTES`] is the warning line the
  split is held to, well below the guard so it fires first and with room to act.
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

#: The size at which the per-mode split has stopped being enough. Three quarters
#: of [`GUARD_BYTES`], and sized off measured growth rather than chosen: a file
#: holds exactly one row per drawable palette group, so it grows only when the
#: library does. The `classic-pairs-2026-09` drop put 120 maps in and the largest
#: file, `itinerary.jsonl`, went 425,148 -> 489,002 bytes — **532 bytes a map**.
#: From 489,002 that leaves 297,430 bytes of headroom, **559 maps** or 4.6 drops
#: of that size, where half of `GUARD_BYTES` left 35,286 bytes and 66 maps: half a
#: drop, so the next one would have gone red. It stays a quarter of a mebibyte —
#: 492 maps, four more drops — below the history guard so it still fires first,
#: which is the whole point of naming a second number here.
#:
#: It was `GUARD_BYTES // 2` until 2026-09-06.
SPLIT_BYTES = GUARD_BYTES * 3 // 4


def files() -> list:
    return sorted(color_mass.record_dir().glob("*.jsonl"))


def test_the_map_is_committed_and_every_file_is_well_under_the_history_guard() -> None:
    written = files()
    assert written, f"{color_mass.record_dir()} holds no map"
    for path in written:
        size = path.stat().st_size
        assert size < SPLIT_BYTES, (
            f"{path.name} is {size:,} bytes, over the {SPLIT_BYTES:,}-byte warning line "
            f"below the {GUARD_BYTES:,}-byte per-file history guard. The map splits per "
            f"mode BECAUSE of that guard; a file this size means the split has stopped "
            f"being enough and wants another axis, not a bigger file"
        )


def test_every_palette_group_is_in_every_measured_mode() -> None:
    """A pair absent from the map and a pair with no colour read identically off a
    lookup, so the map is complete by construction over the roster it was measured
    on: the sweep measured the whole grid and the census only ever added to it.

    **The roster is `measured_modes()` and not the engine's.** The map is a
    measurement — a 27,053-render sweep and a census — so a mode added to the
    catalog after it was taken has no rows, and that is not the same failure as a
    hole. `color_mass.UNMEASURED` names those, and the assertions below hold the
    tuple to being exactly right in both directions: an unmeasured mode must have
    no file at all, and a mode measured later has to leave the tuple or this goes
    red. What is *not* relaxed is the grid: over every mode the map claims to
    hold, every palette group is still there.
    """
    from fractal_wallpapers import engine

    table = color_mass.read()
    library = {row["group"] for row in groups.groups()} | {
        f"map:{name}" for name in groups.library()
    }
    named = {group for group, _mode in table}
    assert named <= library, sorted(named - library)[:5]
    modes = {mode for _group, mode in table}
    assert modes == set(color_mass.measured_modes())
    assert len(table) == len(named) * len(modes), "the grid has a hole in it"

    roster = set(engine.production_modes())
    unmeasured = set(color_mass.UNMEASURED)
    assert unmeasured <= roster, sorted(unmeasured - roster)
    assert not unmeasured & set(color_mass.stored_modes()), (
        "a mode named UNMEASURED has a file: it has been swept, so it belongs in the "
        "grid above and not in the exception"
    )
    assert roster - modes == unmeasured, sorted((roster - modes) ^ unmeasured)


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


# --------------------------------------------------------------------------- #
# The draw filter.
# --------------------------------------------------------------------------- #
def test_delivering_takes_any_listed_cell_and_keeps_the_order_it_was_given() -> None:
    """**Any and not all.** A leg listing five thin cells wants the maps that serve
    one of them; the maps that serve all five are almost none, and a pool cut that
    way could not stand up a 32-map neighbourhood for any of them.

    Order is the caller's, so a caller narrowing a pool gets one back in the shape
    it handed over — which is what lets `depth.build_plan` apply this over whatever
    the maps manifest left without re-sorting a pool between two filters.
    """
    pool = groups.library()
    lime = color_mass.delivering(["dark_vivid_lime"], within=pool)
    yellow = color_mass.delivering(["dark_vivid_yellow"], within=pool)
    both = color_mass.delivering(["dark_vivid_lime", "dark_vivid_yellow"], within=pool)
    assert set(both) == set(lime) | set(yellow)
    assert both == [name for name in pool if name in set(both)], "the pool's own order"
    assert len(both) < len(pool), "a filter that keeps everything is not a filter"


def test_delivering_reads_the_cutoff_off_the_dominance_rule_and_tightens_with_it() -> None:
    """The default is `dominance.CELL_LEAD` and not a constant of this module's, so
    "delivers" means "expected to be dominant here" rather than a number somebody
    chose beside one. Raising it can only take maps away."""
    pool = groups.library()
    default = color_mass.delivering(["dark_vivid_yellow"], within=pool)
    named = color_mass.delivering(["dark_vivid_yellow"], cutoff=dominance.CELL_LEAD, within=pool)
    tighter = color_mass.delivering(["dark_vivid_yellow"], cutoff=0.30, within=pool)
    assert default == named
    assert set(tighter) < set(default)


def test_delivering_refuses_a_cell_the_codebook_does_not_hold() -> None:
    """A misspelt cell would narrow a pool nobody chose, and would do it quietly:
    every map would miss the cutoff for a name no row carries and the cut would
    come back empty for a reason that looks like a thin library."""
    with pytest.raises(color_mass.ColorMassError, match="codebook cell"):
        color_mass.delivering(["dark_vivid_limes"])
    with pytest.raises(color_mass.ColorMassError):
        color_mass.delivering([])


def test_delivers_takes_the_carrier_prior_only_where_there_is_no_mass_row() -> None:
    """The two tables answer the same question at different keys and only one of
    them is a measurement of this pipeline, so the prior is a fallback and never an
    overrule. A group with a row reads 0.0 for a cell that row does not carry —
    which is a measured floor, not missing data — and the prior is not consulted."""
    table = {("g1", "smooth"): {"cells": {"dark_vivid_lime": 0.4}}}
    assert color_mass.delivers("dark_vivid_lime", "g1", table, 0.9, ["smooth"]) == 0.4
    assert color_mass.delivers("dark_vivid_yellow", "g1", table, 0.9, ["smooth"]) == 0.0
    assert color_mass.delivers("dark_vivid_lime", "g2", table, 0.9, ["smooth"]) == 0.9
    assert color_mass.delivers("dark_vivid_lime", "g2", table, 0.0, ["smooth"]) == 0.0


def test_delivers_takes_the_max_over_the_modes_and_not_the_mean() -> None:
    """A run's map pool is shared by every arm and every mode in it, so a map is
    offerable when ANY mode the leg may render delivers the cell with it. A mean
    would drop a map that is the library's best answer in one mode because it is
    ordinary in thirteen others."""
    table = {
        ("g1", "smooth"): {"cells": {"dark_vivid_lime": 0.02}},
        ("g1", "stripe"): {"cells": {"dark_vivid_lime": 0.55}},
    }
    assert color_mass.delivers("dark_vivid_lime", "g1", table, 0.0, ["smooth", "stripe"]) == 0.55
    assert color_mass.delivers("dark_vivid_lime", "g1", table, 0.0, ["smooth"]) == 0.02
