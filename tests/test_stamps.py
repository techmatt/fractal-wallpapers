"""Finding the curve a later render inherits, and refusing the ones it must not.

`curation.stamps` is the join between a recipe key and the whole autolevel stamp
the leg that made it wrote down. The reduced stamp in the key carries the
operator, the switch and the band and never the curve — deliberately — so the
curve has to be found again, and these are the guards on where it is looked for
and what is declined.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.coloring import autolevel
from fractal_wallpapers.curation import stamps

BAND = "49d4f43b200904c5967df788308834be163698081d85802df978554261aa63a1"


def stamp(acted: bool = True, band: str = BAND, curve: dict | None = None) -> dict:
    """One whole stamp as a sequence row carries it."""
    return {
        "operator": autolevel.OPERATOR,
        "switch": "on",
        "acted": acted,
        "band": {"sha256": band},
        "curve": {"applies": True, "identity": not acted} if curve is None else curve,
        "measured": {"black_pt": 0.4},
    }


def ledger_row(run: str = "armA1_0906", band: str = BAND) -> dict:
    return {
        "key": "abc123",
        "recipe": {"colormap": "magma", "autolevel": {"band_sha256": band}},
        "provenance": {"run": run, "candidate": "00001"},
    }


def write_sequence(tmp_path, run: str, rows: list[dict]):
    """One leg's sequence file, in the store layout `sequence_paths` looks in."""
    where = tmp_path / "curation" / "depth" / run
    where.mkdir(parents=True, exist_ok=True)
    path = where / "sequence.jsonl"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
    return path


@pytest.fixture
def store(tmp_path, monkeypatch):
    """The artifact tier redirected at its root, never per accessor."""
    monkeypatch.setattr(stamps, "under", lambda *parts: tmp_path.joinpath(*parts))
    return tmp_path


def test_a_run_that_wrote_its_curve_down_lends_it(store):
    write_sequence(store, "armA1_0906", [{"key": "abc123", "autolevel": stamp()}])
    found = stamps.for_rows({"abc123": ledger_row()})
    assert found["abc123"]["curve"] == {"applies": True, "identity": False}


def test_a_leg_that_wrote_no_sequence_lends_nothing(store):
    """A mine leg is this. `mine.make` returns the whole stamp, the leg counts
    `autolevel_acted` off it and drops it, so a mine-sourced candidate that acted
    is `acted_unrecoverable` the day it is made — not a backlog of old rows."""
    assert stamps.for_rows({"abc123": ledger_row(run="mine1")}) == {}


def test_only_the_wanted_keys_come_back_however_long_the_sequence_is(store):
    """The read is grouped by run and streams each sequence once, keeping the keys
    asked for. The largest of these files is 99.5 MiB and a per-row lookup would
    open one of them per seat."""
    write_sequence(
        store,
        "armA1_0906",
        [{"key": f"k{n:04d}", "autolevel": stamp()} for n in range(50)],
    )
    rows = {"k0007": {**ledger_row(), "key": "k0007"}}
    found = stamps.for_rows(rows)
    assert set(found) == {"k0007"}


def test_the_last_row_for_a_key_wins(store):
    """A re-render inside one leg replaces the stamp of the render it replaced.
    There is one picture on disk and the later row is its row."""
    write_sequence(
        store,
        "armA1_0906",
        [
            {"key": "abc123", "autolevel": stamp(curve={"applies": True, "mark": "first"})},
            {"key": "abc123", "autolevel": stamp(curve={"applies": True, "mark": "second"})},
        ],
    )
    assert stamps.for_rows({"abc123": ledger_row()})["abc123"]["curve"]["mark"] == "second"


def test_the_backfill_overlay_is_preferred_and_costs_no_read(store):
    """An amended row is answered without opening the leg's sequence at all, and
    it wins where both exist: a backfill is a deliberate correction."""
    write_sequence(store, "armA1_0906", [{"key": "abc123", "autolevel": stamp()}])
    amended = {"abc123": {"autolevel": stamp(curve={"applies": True, "mark": "amended"})}}
    found = stamps.for_rows({"abc123": ledger_row()}, amended)
    assert found["abc123"]["curve"]["mark"] == "amended"


def test_a_curve_from_a_different_band_refuses_rather_than_being_lent():
    """A recipe key carries the band's sha256, so a stamp naming another band is a
    stamp for a different picture. Lending its curve would ship a wallpaper
    levelled onto a band its own key says it was not."""
    with pytest.raises(stamps.StampError, match="different picture"):
        stamps.borrowed_for("abc123", stamp(band="0" * 64), ledger_row())


def test_a_row_with_no_curve_inherits_nothing_and_that_is_not_an_error():
    """`acted_unrecoverable` is a fact about the store rather than a fault, and the
    render it is about still has to be made — deciding for itself, as it always
    did."""
    assert stamps.borrowed_for("abc123", None, ledger_row()) is None
    assert stamps.borrowed_for("abc123", {"acted": True}, ledger_row()) is None


def test_what_the_source_said_about_its_own_curve_travels_with_it():
    """Without this a release that inherited a re-derivation would look exactly
    like one that inherited the curve its candidate actually shipped, and only the
    second of those is a record."""
    rederived = {**stamp(), "provenance": {"curve": "rederived", "from": {"record": "R"}}}
    borrowed = stamps.borrowed_for("abc123", rederived, ledger_row())
    assert borrowed["from"]["was"] == "rederived"
    assert borrowed["from"]["key"] == "abc123"


def test_for_release_answers_only_the_seats_it_found_a_curve_for(store):
    write_sequence(store, "armA1_0906", [{"key": "abc123", "autolevel": stamp()}])
    rows = {"abc123": ledger_row(), "nothing": ledger_row(run="mine1")}
    rows["nothing"]["key"] = "nothing"
    out = stamps.for_release(rows)
    assert set(out) == {"abc123"}
    assert out["abc123"]["curve"]["applies"] is True


def test_the_overlay_answers_only_the_batch_it_was_asked_about(store):
    """The sidecar holds every seat ever backfilled and a caller asked about a few.

    Iterating the overlay instead of the batch returned a curve for every
    backfilled seat in the store — 299 answers to a question about 40 — which is
    harmless at a lookup and makes "how many of these inherit one" unanswerable,
    which is how it was found.
    """
    amended = {
        "abc123": {"autolevel": stamp()},
        "somebody_elses_seat": {"autolevel": stamp()},
    }
    assert set(stamps.for_rows({"abc123": ledger_row()}, amended)) == {"abc123"}
