"""Guard: the coverage read counts pixels, under the fold production really uses.

The whole point of this module is that it disagrees with the ramp census, so the
things worth pinning are the places where it could quietly stop disagreeing:

* the **statistic**. A map counts for a swatch when *one* panel cell shows it, so
  the aggregation is a max over cells and never a mean. A mean would let a colour
  fifteen cells cannot show cancel the one that can, which is the opposite of the
  question.
* the **fold**. Production folds a sequential map and never folds a cyclic one. A
  swatch reachable only with the fold off is a picture this pipeline does not
  make, and counting it in the main table would report a capability that is not
  there.
* the **panel's job**. It is selected on field shape, not drawn: every probeable
  mode present, and the hardest end-decile pile-ups taken by construction. A
  selection that lost the pile-ups would be an instrument that cannot see the
  failure it exists to find.
* the **two estimands**. Capability and realized supply are different quantities
  over different populations, and every threshold column has to appear in both or
  a reader will difference two tables that do not line up.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.curation import palette_coverage as coverage
from fractal_wallpapers.palettes import codebook

pytest.importorskip("numpy")


def row(cell: str, colormap: str, shares: dict, fold: str = "production") -> dict:
    """One probe row, holding only what the tables read off it."""
    return {
        "schema": coverage.SCHEMA,
        "cell": cell,
        "mode": "smooth",
        "kind": "smooth",
        "partition": "mandelbrot",
        "colormap": colormap,
        "fold": fold,
        "mirror": fold == "production",
        "shares": shares,
        "dominant": max(shares, key=shares.get) if shares else "black",
    }


def measured(cell: str, mode: str, partition: str, end_mass: float) -> dict:
    """One measured candidate cell, holding only what `choose` selects on."""
    return {
        "cell": cell,
        "mode": mode,
        "partition": partition,
        "shape": {"end_mass": end_mass},
    }


# --------------------------------------------------------------------------- #
# The statistic.
# --------------------------------------------------------------------------- #
def test_a_map_counts_on_its_best_cell_and_not_on_the_panel_average() -> None:
    """One cell showing the colour is the definition. Averaging over sixteen cells
    would report a map that can make the picture as a map that cannot."""
    rows = [
        row("a", "one", {"dark_muted_teal": 0.30}),
        *[row(f"c{index}", "one", {"dark_muted_teal": 0.0}) for index in range(15)],
    ]
    best = coverage.reach(rows)
    assert best["one"]["dark_muted_teal"] == pytest.approx(0.30)
    table = coverage.counts(best, ["one"])["swatches"]["dark_muted_teal"]
    assert [table[f"at_{int(t * 100)}pct"] for t in coverage.THRESHOLDS] == [1, 1, 1, 1]


def test_the_thresholds_nest_so_a_count_can_never_rise_with_the_bar() -> None:
    """Four columns of one table, not four tables. A swatch clearing 20% cleared 5%."""
    rows = [
        row("a", name, {"light_muted_lime": share})
        for name, share in (("one", 0.04), ("two", 0.07), ("three", 0.12), ("four", 0.22))
    ]
    table = coverage.counts(coverage.reach(rows))["swatches"]["light_muted_lime"]
    counted = [table[f"at_{int(t * 100)}pct"] for t in coverage.THRESHOLDS]
    assert counted == [3, 2, 1, 1]
    assert counted == sorted(counted, reverse=True)


def test_every_swatch_gets_a_row_including_the_ones_no_map_reaches() -> None:
    """The subject is the holes: a swatch omitted for counting zero is the finding."""
    table = coverage.counts(coverage.reach([row("a", "one", {"black": 0.9})]))
    assert set(table["swatches"]) == set(codebook.names())
    assert len(table["swatches"]) == 52


def test_a_population_the_rows_never_mention_counts_as_zero_rather_than_vanishing() -> None:
    """The pre-existing-library column is the same table over a named subset, so a
    map with no row has to be a zero in it and not a shorter denominator."""
    best = coverage.reach([row("a", "new", {"dark_vivid_teal": 0.4})])
    prior = coverage.counts(best, ["old", "older"])
    assert prior["maps"] == 2
    assert prior["swatches"]["dark_vivid_teal"]["at_20pct"] == 0


# --------------------------------------------------------------------------- #
# The fold.
# --------------------------------------------------------------------------- #
def test_a_swatch_reached_only_with_the_fold_off_is_named_and_not_counted() -> None:
    """Production folds a sequential map. A colour that needs the fold off is a
    capability of a picture nothing here makes."""
    rows = [
        row("a", "seq", {"dark_muted_cyan": 0.02}, fold="production"),
        row("a", "seq", {"dark_muted_cyan": 0.18}, fold="unfolded"),
    ]
    table = coverage.counts(coverage.reach(rows))["swatches"]["dark_muted_cyan"]
    assert table["at_15pct"] == 0
    false = coverage.false_capabilities(rows)
    assert [(entry["colormap"], entry["swatch"], entry["thresholds"]) for entry in false] == [
        ("seq", "dark_muted_cyan", [5, 10, 15])
    ]


def test_a_swatch_the_fold_does_not_change_is_not_a_false_capability() -> None:
    """Only the thresholds the fold decides are reported, or the list would be
    every sequential map against every swatch it carries."""
    rows = [
        row("a", "seq", {"light_muted_rose": 0.30}, fold="production"),
        row("a", "seq", {"light_muted_rose": 0.31}, fold="unfolded"),
    ]
    assert coverage.false_capabilities(rows) == []


def test_a_cyclic_map_is_probed_once_because_folding_it_is_refused() -> None:
    """The engine will not halve a cycle that closes, so the counterfactual does
    not exist for a cyclic map and asking for it would be an error, not a row."""
    assert coverage._folds("closes", {"closes"}) == [("production", False)]
    assert coverage._folds("seams", {"closes"}) == [("production", True), ("unfolded", False)]


# --------------------------------------------------------------------------- #
# The panel.
# --------------------------------------------------------------------------- #
def test_the_panel_keeps_the_two_hardest_pile_ups_whatever_else_it_takes() -> None:
    """Those cells are where a mirrored ramp strands its far half. A panel that
    selected them away would overstate every count it reports."""
    cells = [measured(f"c{index}", "smooth", f"p{index}", index / 40.0) for index in range(40)]
    chosen = coverage.choose(cells, cells=coverage.PANEL_CELLS)
    names = {cell["cell"] for cell in chosen}
    assert {"c39", "c38"} <= names
    assert len(chosen) == coverage.PANEL_CELLS


def test_the_panel_holds_every_probeable_mode_even_a_rare_one() -> None:
    """A mode missing outright is a field shape the read never saw, and the count
    it would have raised is indistinguishable from a colour nothing carries."""
    cells = [measured(f"s{index}", "smooth", f"p{index}", 0.5) for index in range(30)]
    cells.append(measured("rare", "trap_circle", "phoenix", 0.01))
    chosen = coverage.choose(cells, cells=6)
    assert "trap_circle" in {cell["mode"] for cell in chosen}


def test_only_the_modes_with_one_scalar_field_behind_them_are_probeable() -> None:
    """A composite, a modulate and a direct trap have no field to dump, so a panel
    naming one would be a run of engine refusals rather than a wider read."""
    from fractal_wallpapers import engine

    kinds = {entry["name"]: entry["coloring"]["kind"] for entry in engine.modes()}
    probeable = coverage.probeable_modes()
    assert probeable
    assert all(kinds[name] == "field" for name in probeable)
    assert set(probeable) <= set(engine.production_modes())


# --------------------------------------------------------------------------- #
# The field descriptor, which is what the panel is selected on.
# --------------------------------------------------------------------------- #
def test_a_field_piled_at_one_end_reads_as_piled_and_a_flat_one_does_not(tmp_path) -> None:
    """The descriptor is the selection, so it has to separate the two shapes the
    panel is required to span."""
    import numpy

    def shape_of(values, transform: str = "linear") -> dict:
        field = tmp_path / f"{transform}_{len(values)}.f32"
        numpy.asarray(values, dtype="<f4").tofile(field)
        record = field.with_suffix(".json")
        record.write_text(
            json.dumps({"transform": transform, "field_file": field.name}), encoding="utf-8"
        )
        return coverage.field_shape(record)

    flat = shape_of(numpy.linspace(0.0, 1.0, 10_000))
    piled = shape_of(numpy.concatenate([numpy.zeros(9_000), numpy.linspace(0.0, 1.0, 1_000)]))
    assert flat["end_mass"] < 0.15
    assert piled["end_mass"] > 0.85
    assert piled["spread_bits"] < flat["spread_bits"]


def test_the_interior_is_counted_apart_because_it_takes_black_not_a_gradient_place(
    tmp_path,
) -> None:
    """A frame that is half interior has half as many pixels available to carry any
    colour. Those samples have no field value to stretch, so they are reported as
    their own fraction and the deciles are shares of what is left."""
    import numpy

    values = numpy.concatenate([numpy.full(500, numpy.nan), numpy.linspace(0.0, 1.0, 500)])
    field = tmp_path / "half_interior.f32"
    numpy.asarray(values, dtype="<f4").tofile(field)
    record = field.with_suffix(".json")
    record.write_text(
        json.dumps({"transform": "linear", "field_file": field.name}), encoding="utf-8"
    )
    shape = coverage.field_shape(record)
    assert shape["interior_fraction"] == pytest.approx(0.5)
    assert sum(shape["deciles"]) == pytest.approx(1.0, abs=1e-6)


# --------------------------------------------------------------------------- #
# The two estimands.
# --------------------------------------------------------------------------- #
def test_both_reads_carry_the_same_threshold_columns_so_they_can_be_read_side_by_side() -> None:
    """They are never pooled, but they are printed next to each other, and a column
    present in one table and absent from the other invites a difference nobody can
    take."""
    columns = {f"at_{int(threshold * 100)}pct" for threshold in coverage.THRESHOLDS}
    best = coverage.reach([row("a", "one", {"black": 0.5})])
    assert set(coverage.counts(best)["swatches"]["black"]) == columns


def test_the_thresholds_are_finer_than_the_censuss_because_the_bar_is_not_set_yet() -> None:
    """The census asks present-or-dominant of a ramp. This read exists to find where
    the bar should go, which needs the rungs below the one that already exists."""
    assert coverage.THRESHOLDS == (0.05, 0.10, 0.15, 0.20)
    assert min(coverage.THRESHOLDS) < min(codebook.SHARE_THRESHOLDS)
    assert len(coverage.THRESHOLDS) == 4


# --------------------------------------------------------------------------- #
# The by-swatch sheet: order, gaps, and the cut it takes.
# --------------------------------------------------------------------------- #
def readout_of(counts: dict, floor: int = 250) -> dict:
    """A coverage readout holding only what the sheet's ordering reads.

    Every swatch the caller does not name sits at `floor`, so the named ones are
    ordered against a populated table rather than against forty-nine zeroes.
    """
    swatches = {
        name: {f"at_{int(t * 100)}pct": floor for t in coverage.THRESHOLDS}
        for name in codebook.names()
    }
    for name, cells in counts.items():
        swatches[name].update(cells)
    return {"capability": {"all": {"maps": 901, "swatches": swatches}}}


def test_the_sheet_is_ordered_by_the_pixel_count_and_never_by_the_ramp() -> None:
    """The two disagree hard enough to invert the order — the muted tiers read four
    to five times thinner on a ramp than they are on a picture. A page about pixel
    scarcity sorted the other way would put its abundant half at the top."""
    order = coverage.scarcity_order(
        readout_of(
            {
                "black": {"at_10pct": 500},
                "dark_vivid_lime": {"at_10pct": 38},
                "light_muted_rose": {"at_10pct": 151},
            }
        )
    )
    assert len(order) == 52
    assert order[0] == "dark_vivid_lime"
    assert order[-1] == "black"
    assert order.index("dark_vivid_lime") < order.index("light_muted_rose") < order.index("black")


def test_a_tie_at_the_ten_percent_rung_is_broken_by_the_rung_below_it() -> None:
    """Two swatches level at 10% are not equally scarce if one of them is also
    absent at 5%, and the eye scrolling the page should meet the scarcer one first."""
    order = coverage.scarcity_order(
        readout_of(
            {
                "dark_vivid_teal": {"at_10pct": 40, "at_5pct": 90},
                "dark_vivid_lime": {"at_10pct": 40, "at_5pct": 45},
            }
        )
    )
    assert order.index("dark_vivid_lime") < order.index("dark_vivid_teal")


def test_an_empty_band_says_which_of_the_two_things_it_is() -> None:
    """Nothing reaches the rung, or everything that reaches it clears the next one
    too. Those are opposite findings and a blank cell is both of them."""
    absent = coverage._gap_note("&ge;20%", 0)
    abundant = coverage._gap_note("&ge;5%", 436)
    assert "no map on the panel reaches" in absent
    assert "436 maps" in abundant and "clear it too" in abundant
    assert absent != abundant


def test_the_carrier_list_marks_the_drop_and_says_what_it_cut() -> None:
    """A silent truncation reads as `these are the maps`. `black` is reached at 20%
    by four hundred of them and the page has to say so rather than show twelve."""
    best = {f"map{index}": {"black": 0.9 - index / 1000.0} for index in range(30)}
    cell = coverage._carriers_cell(best, {"map0": "a-drop"}, "black", 0.20)
    assert "class='drop'>map0" in cell
    assert "class='old'>map1" in cell
    assert f"+{30 - coverage.CARRIERS_LISTED} more, not listed" in cell


def test_a_rung_nothing_reaches_says_so_in_the_carrier_list_too() -> None:
    """An empty list and a missing list are the same characters on a page."""
    assert "no map" in coverage._carriers_cell({"one": {"black": 0.1}}, {}, "black", 0.20)


def test_a_tile_is_named_by_what_it_shows_so_two_sheets_share_the_file() -> None:
    """The by-swatch sheet and the contact sheet pick the same weakest example for
    the swatches they both cover, and the second one should cost nothing."""
    entry = row("smooth_phoenix_2ed6828c1f", "Reed Walk", {"dark_vivid_lime": 0.15})
    name = coverage._tile_name("dark_vivid_lime", 0.15, entry)
    assert name == "dark_vivid_lime_15_smooth_phoenix_2ed6828c1f_Reed-Walk.jpg"
    assert name == coverage._tile_name("dark_vivid_lime", 0.15, dict(entry))
