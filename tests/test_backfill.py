"""The sidecar that gives a curve back to a seat whose leg never wrote one down.

Every claim here is about *honesty* rather than about the arithmetic. A
backfilled curve is a re-derivation and not a recovery — the base render it came
off was made months after the picture — so what these guard is that a row says
which it is, that the sidecar never edits the record it amends, and that where
the seat's own levelled colormap survived the two are actually compared.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.coloring import autolevel
from fractal_wallpapers.curation import backfill

BANDS = {"black_pt": (0.0, 0.30), "white_pt": (0.86, 0.99), "mid": (0.26, 0.74)}

numpy = pytest.importorskip("numpy")


def stats(black=0.1, white=0.95, mid=0.5) -> dict:
    return {"black_pt": black, "black_pt_all": black, "white_pt": white, "mid": mid}


def ramp(count: int = 8) -> list:
    draw = numpy.linspace(0.0, 1.0, count)
    colours = numpy.stack([(draw * 255), (255 - draw * 200), numpy.full(count, 90.0)], axis=-1)
    return [[float(p), [int(v) for v in row]] for p, row in zip(draw, colours, strict=True)]


def acting_stamp() -> dict:
    curve = autolevel.derive_curve(stats(black=0.45, white=0.60, mid=0.55), BANDS)
    stops, capped = autolevel.curved_stops(ramp(), curve)
    return autolevel.make_stamp({}, curve, stats(), capped, len(stops), acted=True)


def test_a_backfilled_row_says_it_is_a_re_derivation_and_not_a_record():
    """`provenance.curve` is neither `derived` nor `borrowed`: a curve derived from
    a base render made long after the picture is a reconstruction, and a reader
    that could not tell it from the original would be reading one as the other."""
    row = backfill.row("abc123", acting_stamp(), backfill.AGREES, {"record": "R"})
    assert row["autolevel"]["provenance"]["curve"] == backfill.REDERIVED
    assert row["autolevel"]["provenance"]["curve"] != autolevel.DERIVED
    assert row["autolevel"]["provenance"]["from"] == {"record": "R"}


def test_the_source_stamp_is_not_edited_in_place():
    """The stamp handed in belongs to whoever made it. A row that mutated it would
    put a `rederived` provenance on the caller's own object."""
    made = acting_stamp()
    backfill.row("abc123", made, backfill.AGREES, {})
    assert "provenance" not in made or made["provenance"]["curve"] == autolevel.DERIVED


def test_the_sidecar_appends_and_the_later_row_for_a_key_wins(tmp_path):
    """Append-only, so an interrupted leg keeps what it did, and a second backfill
    of one key is two rows with neither hiding the other on disk."""
    where = tmp_path / "autolevel_backfill.jsonl"
    backfill.append([backfill.row("k", acting_stamp(), backfill.AGREES, {"n": 1})], where)
    backfill.append([backfill.row("k", acting_stamp(), backfill.DIFFERS, {"n": 2})], where)
    assert len(backfill.rows(where)) == 2
    assert backfill.read(where)["k"]["source"]["n"] == 2


def test_a_row_of_another_schema_refuses_rather_than_being_read_as_this_one(tmp_path):
    where = tmp_path / "autolevel_backfill.jsonl"
    where.write_text(json.dumps({"schema": 99, "key": "k"}) + "\n", encoding="utf-8", newline="\n")
    with pytest.raises(backfill.BackfillError, match="schema"):
        backfill.rows(where)


def test_an_absent_sidecar_reads_as_nothing_rather_than_refusing(tmp_path):
    assert backfill.read(tmp_path / "not_here.jsonl") == {}


def test_the_shipped_ramp_is_found_beside_the_picture_by_its_own_stem(tmp_path):
    """Every site that writes one names it for the picture's stem, so it is found
    from the picture's path and nothing has to remember where a leg put it."""
    picture = tmp_path / "pictures" / "abc123.jpg"
    picture.parent.mkdir(parents=True)
    picture.write_bytes(b"x")
    leveled = picture.parent / "abc123.leveled"
    leveled.mkdir()
    (leveled / "magma.json").write_text(json.dumps({"stops": ramp()}), encoding="utf-8")
    assert backfill.shipped_stops(picture, "magma") == ramp()
    assert backfill.shipped_stops(picture, "viridis") is None
    assert backfill.shipped_stops(None, "magma") is None


def test_a_re_derived_curve_that_rebuilds_the_shipped_ramp_agrees():
    made = acting_stamp()
    shipped = autolevel.stops_from_stamp(made, ramp())
    assert backfill.agreement(made, shipped, ramp()) == backfill.AGREES


def test_a_re_derived_curve_that_rebuilds_a_different_ramp_differs():
    made = acting_stamp()
    shipped = autolevel.stops_from_stamp(made, ramp())
    moved = [[position, [0, 0, 0]] for position, _ in shipped]
    assert backfill.agreement(made, moved, ramp()) == backfill.DIFFERS


def test_a_seat_whose_levelled_colormap_was_swept_is_unchecked_and_says_so():
    """Not `agrees` by default. A backfill nothing could be compared against is
    exactly the row a reader needs to treat with more care, not less."""
    assert backfill.agreement(acting_stamp(), None, ramp()) == backfill.NO_RAMP


def test_a_re_derivation_that_says_in_band_over_a_ramp_that_shipped_is_the_sharpest_difference():
    """The row shipped a curved ramp and the re-derivation says it should not
    have. Reading that as `no_ramp` — there is no rebuilt list to compare — would
    hide the one disagreement that says the re-derivation landed somewhere else
    entirely."""
    in_band = autolevel.make_stamp({}, autolevel.derive_curve(stats(), BANDS), stats(), 0, 0, False)
    assert backfill.agreement(in_band, ramp(), ramp()) == backfill.DIFFERS


def test_the_wanted_list_skips_the_modes_the_operator_never_acts_on():
    """A direct trap carries no autolevel identity at all, so there is no curve to
    want and a backfill that rendered one would be spending an engine on a
    question nobody asked."""
    rows = {
        "direct": {"recipe": {"autolevel": None}, "provenance": {"run": "r"}},
        "field": {"recipe": {"autolevel": {"band_sha256": "x"}}, "provenance": {"run": "r"}},
    }
    assert backfill._wanted(rows, {}) == ["field"]


def test_the_wanted_list_skips_a_seat_that_already_has_a_curve_on_a_run_record():
    rows = {"field": {"recipe": {"autolevel": {"band_sha256": "x"}}, "provenance": {"run": "r"}}}
    assert backfill._wanted(rows, {"field": {"curve": {}}}) == []
