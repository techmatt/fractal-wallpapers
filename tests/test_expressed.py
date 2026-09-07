"""Guard: the collection's coverage vector, and the identity the budget rests on.

This module's finding is one line of arithmetic, so the things worth pinning are
the places the arithmetic could quietly stop being true:

* the **identity**. `sum(COVERAGE)` over a set of swatches IS the mean number of
  them a picture expresses — the same double sum read down the columns instead of
  across the rows. Every ceiling in the readout is that mean over a count, so a
  drift between the two halves would make a feasibility claim out of a bug.
* the **threshold is a floor, not a boundary**. A swatch on exactly a tenth of
  the pixels is expressed. One comparison written the other way moves the whole
  vector by however many pictures land on the line.
* the **neutrals are reported, never excluded**. They sit near the top and the
  prompt for this measurement asks for them; a helper that filtered them would
  turn "black is in half the pictures" into silence.
* the **population is the verdict, checked**. A `released` row claims a picture
  exists, and the reader tests that claim rather than trusting it — a row whose
  file is gone is a refusal, because a coverage vector short a picture is a
  number nobody can reproduce.
* the **cheap instruments are priced, not assumed**. The 160x90 decode and the
  candidate render are both compared against the shipped PNG, and the screen a
  recolor pass would run is re-derived from real pairs at every height.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers.curation import expressed
from fractal_wallpapers.palettes import codebook

pytest.importorskip("numpy")


def picture(shares: dict, **overrides) -> dict:
    """One censused wallpaper, holding only what the tables read off it."""
    row = {
        "schema": expressed.SCHEMA,
        "key": "run|release|0000",
        "run": "run",
        "candidate": "0000",
        "collection": "diagnostic",
        "rejected": False,
        "kind": "smooth_render",
        "mode": "smooth",
        "mode_kind": "field",
        "shares": shares,
        "census_shares": shares,
        "candidate_shares": shares,
        "resolution": [2560, 1440],
    }
    row.update(overrides)
    return row


# --------------------------------------------------------------------------- #
# The threshold.
# --------------------------------------------------------------------------- #
def test_a_swatch_on_exactly_the_threshold_is_expressed():
    """The comparison is `>=`. A tenth of the pixels is a tenth of the pixels."""
    rows = [picture({"black": expressed.THRESHOLD})]
    assert expressed.coverage(rows)["black"] == 1.0


def test_a_swatch_just_under_the_threshold_is_not():
    rows = [picture({"black": expressed.THRESHOLD - 1e-9})]
    assert expressed.coverage(rows)["black"] == 0.0


def test_every_swatch_appears_in_the_vector_even_at_zero():
    """A missing key is a share of zero, and the vector is all fifty-two either way."""
    table = expressed.coverage([picture({"black": 0.9})])
    assert set(table) == set(codebook.names())
    assert table["dark_vivid_lime"] == 0.0


# --------------------------------------------------------------------------- #
# The identity the whole finding rests on.
# --------------------------------------------------------------------------- #
def test_summed_coverage_is_the_mean_expressed_count():
    """The two halves of the budget are one double sum, read two ways."""
    rows = [
        picture({"black": 0.4, "white": 0.3, "dark_vivid_red": 0.2}),
        picture({"black": 0.6, "white": 0.05}),
        picture({"light_gray": 0.5, "dark_muted_blue": 0.11, "light_vivid_lime": 0.1}),
    ]
    table = expressed.coverage(rows)
    counts = expressed.expressed_counts(rows)
    assert sum(table.values()) == pytest.approx(sum(counts) / len(rows))
    assert expressed.budget(rows)["all"]["sum_coverage"] == pytest.approx(
        expressed.budget(rows)["all"]["distribution"]["mean"], abs=5e-4
    )


def test_the_ceiling_is_the_mean_over_the_swatch_count():
    """A floor of f over k swatches asks for f*k, so no f above mean/k can exist."""
    rows = [picture({"black": 0.5, "white": 0.2}), picture({"black": 0.5, "dark_gray": 0.3})]
    cell = expressed.budget(rows)["all"]
    assert cell["implied_ceiling"] == pytest.approx(
        cell["sum_coverage"] / cell["swatches"], abs=5e-5
    )


def test_the_non_neutral_half_drops_only_the_four_neutrals():
    rows = [picture({"black": 0.5, "dark_vivid_red": 0.2})]
    budget = expressed.budget(rows)
    assert budget["all"]["swatches"] - budget["non_neutral"]["swatches"] == 4
    assert budget["neutrals"] == sorted(expressed.neutrals())
    assert budget["non_neutral"]["sum_coverage"] == pytest.approx(1.0)


def test_the_neutrals_are_reported_in_the_vector():
    """Reported, not excluded: they are the top of the ranking and that is the reading."""
    table = expressed.coverage([picture({"black": 0.5})])
    assert table["black"] == 1.0
    assert set(expressed.neutrals()) <= set(table)


# --------------------------------------------------------------------------- #
# The distribution, and what a floor would have to be true of.
# --------------------------------------------------------------------------- #
def test_the_distribution_keeps_the_whole_histogram():
    """Seven integers over the population; every bar is a sentence about a floor."""
    spread = expressed.distribution([1, 2, 2, 3])
    assert spread["histogram"] == {"1": 1, "2": 2, "3": 1}
    assert spread["min"] == 1 and spread["max"] == 3
    assert spread["mean"] == pytest.approx(2.0)


def test_a_picture_expressing_nothing_non_neutral_is_a_zero_and_not_a_gap():
    rows = [picture({"black": 0.9})]
    achromatic = set(expressed.neutrals())
    names = [name for name in codebook.names() if name not in achromatic]
    assert expressed.expressed_counts(rows, names) == [0]


# --------------------------------------------------------------------------- #
# Thinness.
# --------------------------------------------------------------------------- #
def test_thin_is_a_picture_count_and_never_includes_a_neutral():
    rows = [picture({}) for _ in range(100)]
    table = dict.fromkeys(codebook.names(), 0.0)
    table["black"] = 0.0
    table["light_vivid_lime"] = expressed.THIN_PICTURES / len(rows)
    table["dark_vivid_red"] = (expressed.THIN_PICTURES + 1) / len(rows)
    lean = expressed.thin(table, rows)
    assert "light_vivid_lime" in lean
    assert "dark_vivid_red" not in lean
    assert not set(lean) & set(expressed.neutrals())


def test_thin_is_ordered_thinnest_first():
    rows = [picture({}) for _ in range(100)]
    table = dict.fromkeys(codebook.names(), 1.0)
    table["light_vivid_lime"] = 0.02
    table["dark_vivid_red"] = 0.0
    assert expressed.thin(table, rows) == ["dark_vivid_red", "light_vivid_lime"]


# --------------------------------------------------------------------------- #
# What the cheap instruments cost.
# --------------------------------------------------------------------------- #
def test_agreement_counts_a_threshold_flip_in_both_directions():
    rows = [
        picture({"black": 0.11}, census_shares={"black": 0.09}, candidate_shares={"black": 0.11}),
        picture({"black": 0.09}, census_shares={"black": 0.11}, candidate_shares={"black": 0.09}),
    ]
    read = expressed.agreement(rows)
    assert read["census_decode"]["threshold_cells_flipped"] == 2
    assert read["candidate_geometry"]["threshold_cells_flipped"] == 0
    assert read["census_decode"]["threshold_cells"] == 2 * len(codebook.names())


def test_agreement_prices_the_screen_at_every_height_off_real_pairs():
    """The screen is a reading, not a remembered claim, so it is re-derived here."""
    rows = [
        picture({"black": 0.12}, candidate_shares={"black": 0.075}),
        picture({"black": 0.12}, candidate_shares={"black": 0.055}),
    ]
    misses = expressed.agreement(rows)["screen_misses"]
    assert misses["0.08"] == {"missed": 2, "of": 2}
    assert misses["0.07"] == {"missed": 1, "of": 2}
    assert misses["0.05"] == {"missed": 0, "of": 2}


def test_a_picture_with_no_candidate_render_is_left_out_rather_than_counted_as_agreeing():
    rows = [picture({"black": 0.5}, candidate_shares=None)]
    assert expressed.agreement(rows)["candidate_geometry"]["pictures"] == 0
    assert expressed.agreement(rows)["census_decode"]["pictures"] == 1


# --------------------------------------------------------------------------- #
# The population is the verdict, and the verdict is checked.
# --------------------------------------------------------------------------- #
def test_a_released_row_with_no_picture_is_refused(monkeypatch, tmp_path):
    """A claim worth reading is worth testing: a missing file is a refusal."""
    from fractal_wallpapers.curation import records
    from fractal_wallpapers.curation import run as run_module

    row = {
        "key": "run|release|0000",
        "run": "run",
        "verdict": records.RELEASED,
        "picture": "release\\0000.png",
    }
    monkeypatch.setattr(records, "read_decisions", lambda *a, **k: [row])
    monkeypatch.setattr(run_module, "run_dir", lambda name: tmp_path / name)
    with pytest.raises(expressed.ExpressedError, match="reads `released`"):
        expressed.finished()


def test_an_empty_release_store_is_refused_rather_than_measured(monkeypatch):
    from fractal_wallpapers.curation import records

    monkeypatch.setattr(records, "read_decisions", lambda *a, **k: [])
    with pytest.raises(expressed.ExpressedError, match="no finished wallpaper"):
        expressed.finished()


def test_the_recolor_cost_splits_the_two_populations_and_never_pools_them(monkeypatch):
    """One dump then a sweep per map, against a whole render per map. Two prices."""
    monkeypatch.setattr(expressed, "carriers", lambda swatches: {"dark_vivid_lime": ["a", "b"]})
    rows = [
        picture({}, mode_kind="field"),
        picture({}, mode_kind="composite"),
        picture({}, mode_kind="direct"),
    ]
    cost = expressed.recolor_cost(["dark_vivid_lime"], rows)
    assert cost["carriers_union"] == 2
    assert cost["populations"]["field"]["pictures"] == 1
    assert cost["populations"]["not_field"]["pictures"] == 2
    assert cost["populations"]["not_field"]["by_kind"] == {"composite": 1, "direct": 1}
    assert cost["populations"]["field"]["screen_units"] == 2
    assert cost["populations"]["not_field"]["screen_units"] == 4


# --------------------------------------------------------------------------- #
# The population the census covers, against the one that exists.
# --------------------------------------------------------------------------- #
def readout_document(pictures: int, **overrides) -> dict:
    """The two fields the drift guard reads, and nothing else it does not."""
    document = {
        "schema": expressed.SCHEMA,
        "taken_at": "2026-08-24T05:02:00+00:00",
        "population": {"pictures": pictures},
        "thin": ["dark_muted_lime"],
    }
    document.update(overrides)
    return document


def test_a_census_within_the_factor_is_handed_over_with_what_it_measured():
    read = expressed.check_population(readout_document(400), current=645)
    assert read["census_pictures"] == 400
    assert read["released_now"] == 645
    assert read["drift"] == pytest.approx(645 / 400, abs=1e-4)
    assert read["allowed"] == expressed.POPULATION_DRIFT


def test_a_census_past_the_factor_is_refused_and_never_re_derived():
    """The miss is a refusal. A partition that re-took itself mid-leg would prune
    rows under a set no record names, which is the attribution the prune rests on."""
    with pytest.raises(expressed.ExpressedError, match="past the"):
        expressed.check_population(readout_document(246), current=645)


def test_the_drift_is_a_ratio_either_way():
    """A census over a LARGER population than the store holds is the same fault
    wearing the other sign — a readout pointed at a store that is not this one."""
    with pytest.raises(expressed.ExpressedError, match="past the"):
        expressed.check_population(readout_document(645), current=246)


def test_a_store_with_no_released_row_is_not_a_drift():
    """Nothing to compare against is not a stale census, and it is the shape a
    redirected store has: refusing there would name the wrong fault."""
    read = expressed.check_population(readout_document(246), current=0)
    assert read["drift"] is None
    assert read["released_now"] == 0


def test_reading_the_readout_checks_the_population_it_covers(monkeypatch, tmp_path):
    """The guard is on the accessor and not on one caller, because `thin_cells`
    and `manufacture.targets` are two readers of one policy input."""
    import json

    path = tmp_path / "expressed.json"
    path.write_text(json.dumps(readout_document(246)), encoding="utf-8")
    monkeypatch.setattr(expressed, "readout_path", lambda: path)
    monkeypatch.setattr(expressed, "released_now", lambda: 645)
    with pytest.raises(expressed.ExpressedError, match="past the"):
        expressed.readout()
    monkeypatch.setattr(expressed, "released_now", lambda: 300)
    assert expressed.readout()["thin"] == ["dark_muted_lime"]


def test_released_now_counts_the_verdict_and_not_the_file(monkeypatch):
    """`finished` tests the picture because it is about to read it; this only needs
    the size of the population the census was meant to cover."""
    from fractal_wallpapers.curation import records

    rows = [
        {"verdict": records.RELEASED},
        {"verdict": records.RELEASED},
        {"verdict": records.PASSED_OVER},
        {"verdict": "unrendered"},
    ]
    monkeypatch.setattr(records, "read_decisions", lambda *a, **k: rows)
    assert expressed.released_now() == 2
