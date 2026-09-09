"""`--forced`: a set of rows lifted to the top of the fine column before the bar.

**Staged and off by default**, so the first thing pinned here is the "off": a
pass that forces nothing reads the store's own column, object for object, and
every record it writes says `forced: 0`. A staged lever that quietly moved the
shipped gallery would be worse than no lever.

The rest is the three claims the mechanism makes, and each fails differently:

* **It acts at load.** The lift is in the column before `at_fine_bar` reads it,
  before the fold walks it and before the cascade lays its own stage on top — so
  a forced row below the fine bar clears it, and a forced row at a folded place
  becomes its cluster's survivor. A boost applied at any later door would arrive
  at a row already dropped, or already folded away.
* **It is order-preserving.** `1 + p_fine` and never a flat constant: the forced
  set keeps its own order among itself, which is the comparison a forced pass
  exists to observe when several forced rows compete inside one colour cell.
* **It forces an offer and never a seat.** Every rule still applies, and a forced
  row the one-seat rule or an allowance refuses is refused.
"""

from __future__ import annotations

import pytest
from tests.test_headroom import candidate

from fractal_wallpapers.curation import distinct, solve


def quiet(*_args, **_rest) -> None:
    """A `log` that says nothing."""


@pytest.fixture(autouse=True)
def no_neutral_store(monkeypatch):
    """No place here is in the real embedding store, and sweeping it to learn that
    is half a second a test. See `test_solve.py`'s fixture of the same name."""
    from fractal_wallpapers.curation import embeddings

    monkeypatch.setattr(embeddings, "read", lambda *_args, **_rest: [])


def column(rows: dict, monkeypatch) -> None:
    """Stand in for `gallery-grade score-pool`'s output: `{key: p_fine(>=4)}`.

    Patched over [`distinct.fine_scores`], which is the one door a solve reads
    the fine column through — see [`solve.fine_column`]. A key absent from `rows`
    is a row the head has no reading for.
    """
    from fractal_wallpapers.models import gallery_grade_train

    monkeypatch.setattr(
        distinct,
        "fine_scores",
        lambda scores=None: {str(name): float(value) for name, value in (scores or rows).items()},
    )
    monkeypatch.setattr(
        gallery_grade_train,
        "read_pool_scores",
        lambda *_a, **_k: {str(name): {"p_ge4": float(value)} for name, value in rows.items()},
    )


# --------------------------------------------------------------------------- #
# Off by default.
# --------------------------------------------------------------------------- #
def test_a_pass_that_forces_nothing_reads_the_store_s_own_column(monkeypatch) -> None:
    """★ The staging claim. Not merely equal values — the SAME object, because a
    copy is where a lift could be applied to a pass that asked for none."""
    column({"a": 0.9, "b": 0.4}, monkeypatch)
    store = distinct.fine_scores(None)
    for asked in (None, (), []):
        held = solve.fine_column(asked, log=quiet)
        assert held.read == store
        assert held.forced == frozenset()
        assert held.asked == frozenset()
        assert held.record["asked"] == 0
        assert held.record["lifted"] == 0


def test_the_record_says_a_pass_forced_nothing_rather_than_staying_silent(monkeypatch) -> None:
    """A missing field would put a reader of an old record back on the date, which
    is the defect the cascade flip cost a hand-check of sixty-two stamps for."""
    column({"a": 0.9}, monkeypatch)
    record = solve.solve([candidate("a")], n=5, radius=None, key=solve.JUDGE_KEY, log=quiet)
    assert record["config"]["forced"] == 0
    assert record["config"]["forced_default"] == 0
    assert record["forced"]["asked"] == 0
    assert record["fine_bar"]["forced_over_the_bar"] == 0


# --------------------------------------------------------------------------- #
# The lift itself.
# --------------------------------------------------------------------------- #
def test_the_lift_is_order_preserving_and_never_flat(monkeypatch) -> None:
    """★ A flat constant would tie every forced row, and the tie-break inside one
    colour cell is exactly what a forced run is watching."""
    column({"a": 0.90, "b": 0.60, "c": 0.30}, monkeypatch)
    held = solve.fine_column({"a", "b", "c"}, log=quiet).read
    assert held["a"] == pytest.approx(1.90)
    assert held["b"] == pytest.approx(1.60)
    assert held["c"] == pytest.approx(1.30)
    assert held["a"] > held["b"] > held["c"]


def test_every_forced_row_sorts_above_every_unforced_one(monkeypatch) -> None:
    """The bands are a clean `FORCED_LIFT` apart, so the weakest forced row still
    beats the strongest unforced one — which is what "forced" has to mean."""
    column({"weak": 0.001, "strong": 0.999}, monkeypatch)
    held = solve.fine_column({"weak"}, log=quiet).read
    assert held["weak"] > held["strong"]
    assert held["weak"] - 0.001 == pytest.approx(solve.FORCED_LIFT)


def test_a_forced_key_the_head_never_read_is_not_lifted_and_is_counted(monkeypatch) -> None:
    """Unknown never outranks measured — the ruling `cascade_order` and
    `distinct.offered_at` both already take. There is nothing to lift, and
    inventing a reading is the one thing neither of them will do."""
    column({"read": 0.7}, monkeypatch)
    held = solve.fine_column({"read", "unread"}, log=quiet)
    assert "unread" not in held.read
    assert held.forced == frozenset({"read"})
    assert held.asked == frozenset({"read", "unread"})
    assert held.record["unread"] == 1
    assert held.record["lifted"] == 1


# --------------------------------------------------------------------------- #
# It acts at load, which is the only placement that matters.
# --------------------------------------------------------------------------- #
def test_a_forced_row_below_the_fine_bar_clears_it(monkeypatch) -> None:
    """★ The whole reason the lift is applied at load. A boost applied after the
    bar would arrive at a row already dropped from the pool, and nothing
    downstream would ever see it."""
    column({"low": 0.10, "high": 0.90}, monkeypatch)
    pool = [candidate("low", score=0.9), candidate("high", score=0.9)]
    plain = solve.at_fine_bar(pool, 0.5, log=quiet)[0]
    assert {held.key for held in plain} == {"high"}
    forced = solve.fine_column({"low"}, log=quiet)
    kept, reading = solve.at_fine_bar(pool, 0.5, fine=forced, log=quiet)
    assert {held.key for held in kept} == {"low", "high"}
    assert reading["forced_over_the_bar"] == 1


def test_a_forced_row_is_its_cluster_s_survivor(monkeypatch) -> None:
    """The fold picks each cluster's strongest candidate on this same column, so
    forcing has to reach it — otherwise a forced row loses its place before a seat
    exists and every rule downstream is asked about the wrong row."""
    from tests.test_solve import store_of

    rows = store_of({"a": 0.0, "b": 0.001})
    pool = [candidate("a", score=0.10), candidate("b", score=0.99)]
    plain = distinct.preselect(
        pool, rows=rows, fine={"a": 0.10, "b": 0.99}, fold=distinct.DELETE, log=quiet
    )
    assert {held.key for held in plain[0]} == {"b"}
    column({"a": 0.10, "b": 0.99}, monkeypatch)
    lifted = solve.fine_column({"a"}, log=quiet).read
    kept, _record = distinct.preselect(
        pool, rows=rows, fine=lifted, fold=distinct.DELETE, log=quiet
    )
    assert {held.key for held in kept} == {"a"}


def test_the_cascade_lays_its_own_stage_over_a_forced_row(monkeypatch) -> None:
    """Forced rows sit a clean band above the read rows, which sit a clean band
    above the below-bar half — three storeys, each `1.0` wide, none interleaved."""
    column({"hi": 0.8, "mid": 0.6}, monkeypatch)
    pool = [candidate("hi", score=0.9), candidate("mid", score=0.9), candidate("lo", score=0.1)]
    order = {held.key: 0.5 for held in pool}
    forced = solve.fine_column({"mid"}, log=quiet)
    out, record = solve.cascade_order(pool, order, {}, fine=forced, log=quiet)
    assert out["lo"] == 0.5
    assert out["hi"] == pytest.approx(1.8)
    assert out["mid"] == pytest.approx(2.6)
    assert out["mid"] > out["hi"] > out["lo"]
    assert record["cascade"]["forced"] == 1


def test_a_forced_row_is_lifted_whatever_the_coarse_bar_says(monkeypatch) -> None:
    """`score_pool` reads only the above-bar rows, so on a real store the clause
    cannot fire — it is written because "forced" must not mean "forced unless"."""
    column({"under": 0.4}, monkeypatch)
    under = candidate("under", score=solve.Q4_BAR - 0.1)
    assert not under.above_bar
    forced = solve.fine_column({"under"}, log=quiet)
    out, record = solve.cascade_order([under], {"under": 0.5}, {}, fine=forced, log=quiet)
    assert out["under"] == pytest.approx(1.0 + 1.0 + 0.4)
    assert record["cascade"]["forced"] == 1
    assert record["cascade"]["below_bar"] == 0


# --------------------------------------------------------------------------- #
# An offer and never a seat.
# --------------------------------------------------------------------------- #
def test_forcing_offers_a_row_first_and_the_rules_still_refuse_it(monkeypatch) -> None:
    """★ The claim a forced record is read under. Two rows at one place: forcing
    the weaker one makes it the offer, and the one-seat rule still allows exactly
    one of them — so the reading a forced pass gives is which rule bit, not a
    seat count that went up by the size of the forced set."""
    column({"weak": 0.10, "strong": 0.99}, monkeypatch)
    pool = [
        candidate("weak", location="here", score=0.9),
        candidate("strong", location="here", score=0.9),
    ]
    forced = solve.fine_column({"weak"}, log=quiet)
    record = solve.solve(
        pool,
        n=5,
        radius=None,
        fine=forced,
        forced={"weak"},
        diversity=False,
        explain={"weak", "strong"},
        log=quiet,
    )
    assert [seat["key"] for seat in record["seated"]] == ["weak"]
    assert record["rejection"]["explained"]["strong"] == "location"
    assert record["config"]["forced"] == 1


def test_a_column_that_forced_a_different_set_is_refused(monkeypatch) -> None:
    """The caller that resolves the order itself hands the same column to both, and
    two columns is how a pass ranks a pool its bar narrowed under other rules."""
    column({"a": 0.9, "b": 0.9}, monkeypatch)
    with pytest.raises(solve.SolveRefused) as refused:
        solve.solve(
            [candidate("a")],
            n=5,
            radius=None,
            fine=solve.fine_column({"a"}, log=quiet),
            forced={"b"},
            log=quiet,
        )
    assert "hand it to both" in str(refused.value)
