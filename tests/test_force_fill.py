"""`--force-fill`: the first look at an early pool, past both quality gates.

Three claims. **Off by default**: a pass that does not ask is the pass it was, and
says `force_fill: false`. **It opens both gates**: rows under the per-mode bar and
under the fine bar seat when nothing better exists. **It keeps distinctness**: two
rows at one place still hold one seat. And the record carries the flag to the
tentative manifest, where a collection publish path refuses it.
"""

from __future__ import annotations

import pytest
from tests.test_forced import column, quiet
from tests.test_headroom import candidate

from fractal_wallpapers.curation import solve, tentative


@pytest.fixture(autouse=True)
def no_neutral_store(monkeypatch):
    """No place here is in the real embedding store; see `test_forced.py`."""
    from fractal_wallpapers.curation import embeddings

    monkeypatch.setattr(embeddings, "read", lambda *_args, **_rest: [])


def weak_pool() -> list:
    """Three places, every row under the per-mode bar and the fine bar, one place twice."""
    return [
        candidate("a", score=0.20),
        candidate("b", score=0.15),
        candidate("c", location="a", score=0.10),
    ]


def test_a_default_pass_on_a_weak_pool_seats_nothing_and_says_it_did_not_force(monkeypatch):
    column({"a": 0.001, "b": 0.001, "c": 0.001}, monkeypatch)
    with pytest.raises(solve.SolveRefused):
        solve.solve(weak_pool(), n=3, radius=None, key=solve.JUDGE_KEY, log=quiet)
    column({"a": 0.9, "b": 0.9, "c": 0.9}, monkeypatch)
    record = solve.solve(weak_pool(), n=3, radius=None, key=solve.JUDGE_KEY, log=quiet)
    assert record["config"]["force_fill"] is False
    assert record["seated"] == [], "every row is under its mode's bar"


def test_a_forced_fill_seats_past_both_bars_and_keeps_one_seat_a_place(monkeypatch):
    column({"a": 0.001, "b": 0.001, "c": 0.001}, monkeypatch)
    record = solve.solve(
        weak_pool(),
        n=3,
        radius=None,
        key=solve.JUDGE_KEY,
        force_fill=True,
        diversity=False,
        log=quiet,
    )
    assert record["config"]["force_fill"] is True
    assert record["config"]["fine_bar"] is None
    assert sorted(seat["key"] for seat in record["seated"]) == ["a", "b"]


def test_a_forced_record_is_refused_by_a_publish_path(tmp_path, monkeypatch):
    monkeypatch.setattr(tentative, "store_root", lambda: tmp_path / "tentative")
    monkeypatch.setattr(
        tentative, "read_manifest", lambda stamp=None: {"solve": {"config": {"force_fill": True}}}
    )
    with pytest.raises(tentative.TentativeRefused) as refused:
        tentative.refuse_forced("20260101T000000Z", "the full set")
    assert "FORCED FILL" in str(refused.value)
    assert tentative.is_forced({"solve": {"config": {}}}) is False
