"""The per-candidate price, split by band, and the average that carries forward.

One number a partition is the thing this file exists to prevent.
`TIDY_render_cv_and_two_reads` measured `phoenix:classic` at 17-31 s a candidate
on the deep breadth arms and 1.2-1.5 s in the near band — one plane, one weight,
an order of magnitude apart — so a price that forgets which arm it came from
mis-sizes the next leg by that much, silently, because every number involved is a
plausible number of seconds.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.curation import draw_weights, hunt


def test_the_price_keeps_bands_apart():
    price = hunt.Price()
    for _ in range(5):
        price.add("phoenix:classic", 1.5, band="near_band")
        price.add("phoenix:classic", 30.0, band="ranked_bands")
    table = price.table()["phoenix:classic"]
    assert table["candidates"] == 10, "the pooled block still counts every candidate"
    assert table["bands"]["near_band"]["mean"] == pytest.approx(1.5)
    assert table["bands"]["ranked_bands"]["mean"] == pytest.approx(30.0)
    assert price.banded("near_band")["phoenix:classic"] == pytest.approx(1.5)
    assert price.banded("ranked_bands")["phoenix:classic"] == pytest.approx(30.0)


def test_the_ema_walks_toward_what_the_leg_is_actually_seeing():
    """Seeded from the last leg, then moved by this one's own candidates.

    The seed is a guess about this machine on this day and `pc20m` measured that
    guess wrong by 52% six hours later, so the average has to be able to leave it.
    """
    price = hunt.Price(seeded={("phoenix:classic", "near_band"): 30.0})
    assert price.ema[("phoenix:classic", "near_band")] == 30.0
    for _ in range(40):
        price.add("phoenix:classic", 1.5, band="near_band")
    landed = price.ema[("phoenix:classic", "near_band")]
    assert 1.5 < landed < 30.0, "an EMA moves toward the new reading without jumping to it"
    assert landed < 3.0, (
        f"forty candidates at 1.5 s and the average is still {landed:.2f} — at "
        f"alpha={hunt.EMA_ALPHA} it has a memory of about ten and should have arrived"
    )
    assert price.seeded[("phoenix:classic", "near_band")] == 30.0, (
        "what the leg inherited is kept apart from where it ended, or a record cannot "
        "say whether the seed was any good"
    )


def test_one_candidate_prices_a_cell_that_was_never_seeded():
    price = hunt.Price()
    price.add("mandelbrot", 0.4, band="flat")
    assert price.ema[("mandelbrot", "flat")] == pytest.approx(0.4)
    assert ("mandelbrot", "flat") not in price.seeded


def test_a_breadth_leg_never_inherits_a_near_band_price(tmp_path, monkeypatch):
    """The addendum's pin, and the reason `recorded_prices` takes a band at all.

    Two legs on disk: the newer one priced only the near band, the older one only
    a breadth arm. A breadth draw asking for its own price has to walk PAST the
    newer leg rather than take the number that happens to be most recent.
    """
    root = tmp_path / "curation" / "depth"
    for name, band, seconds, when in (
        ("older_breadth", "ranked_bands", 30.0, 1_000),
        ("newer_near", "near_band", 1.5, 2_000),
    ):
        directory = root / name
        directory.mkdir(parents=True)
        (directory / "depth.json").write_text(json.dumps({"price": {}}), encoding="utf-8")
        (directory / "sequence.jsonl").write_text(
            json.dumps({"arm": band, "partition": "phoenix:classic", "seconds": seconds}) + "\n",
            encoding="utf-8",
        )
        for path in (directory / "depth.json", directory / "sequence.jsonl"):
            import os

            os.utime(path, (when, when))

    monkeypatch.setattr(hunt, "under", lambda *parts: tmp_path.joinpath(*parts))
    hunt.forget_recorded_prices()
    monkeypatch.setattr(hunt, "under", lambda *parts: tmp_path.joinpath(*parts))

    near, from_near = hunt.recorded_prices("near_band")
    assert near["phoenix:classic"] == pytest.approx(1.5)
    assert from_near["leg"] == "newer_near"

    breadth, from_breadth = hunt.recorded_prices("ranked_bands")
    assert breadth["phoenix:classic"] == pytest.approx(30.0), (
        "a breadth leg took the near band's 1.5 s — which is the exact mistake that "
        "would ask for twenty times the turns the ruling wants"
    )
    assert from_breadth["leg"] == "older_breadth", "it has to walk past the newer leg"
    hunt.forget_recorded_prices()


def test_a_band_nothing_has_priced_falls_back_and_says_so(tmp_path, monkeypatch):
    monkeypatch.setattr(hunt, "under", lambda *parts: tmp_path.joinpath(*parts))
    hunt.forget_recorded_prices()
    names = ["a", "b", "phoenix", "phoenix:classic"]
    tables, working = draw_weights.by_band(names, ["ranked_bands"], log=lambda *a: None)
    assert working["ranked_bands"]["converted"] is False
    assert tables["ranked_bands"] == draw_weights.table(), (
        "an unpriced band draws under the standing turn weights rather than under a "
        "conversion against a price nobody has taken"
    )
    hunt.forget_recorded_prices()
