"""The cascade order, and the diff sheet that shows what it moves.

Two things here and they fail differently.

**The cascade** is a seating order and therefore a thing that can quietly ruin a
gallery. Its whole claim is that it changes the order *above* the bar and nothing
at all below it, so what is pinned is the "nothing at all": the below-bar half
comes back identical, an above-bar row the head has no reading for keeps the
shipped key's value rather than jumping ahead of rows that were read, and every
above-bar row still outranks every below-bar one however the two scales happen to
land. It is **the default since 2026-09-07** and that is asserted too, along with
the two keys it did not retire: adoption moved one constant and the alternatives
stayed typeable.

**The sheet** decides nothing, so it can only be wrong about arithmetic: which
rows differ, and which of them a cap keeps.
"""

from __future__ import annotations

import pytest
from tests.test_headroom import candidate

from fractal_wallpapers.curation import seat_sheet, solve


def quiet(*_args, **_rest) -> None:
    """A `log` that says nothing."""


def _trainer():
    """The module `solve.cascade_order` reads the fine head's column through.

    Patched rather than written to disk: what these tests are about is what the
    order does with a reading, and putting a real file under the regenerable tree
    would make them a test of this machine's store.
    """
    from fractal_wallpapers.models import gallery_grade_train

    return gallery_grade_train


def pool(above: int = 4, below: int = 3) -> list:
    """`above` candidates over the bar and `below` under it, all distinct places."""
    over = [candidate(f"hi{index}", score=0.90 - index * 0.01) for index in range(above)]
    under = [candidate(f"lo{index}", score=0.40 - index * 0.01) for index in range(below)]
    return over + under


def readings(keys, p_ge4) -> dict:
    """The fine head's column, by the name the cascade reads it under.

    `p_ge4` and not `rank_score`: the head's bar is stated on AUC(>=4), which is
    read on this column, and the two order a real pool at Spearman 0.92 rather
    than identically — so ranking on the sum would seat on a quantity nothing
    gated.
    """
    return {str(key): {"p_ge4": float(p_ge4(key))} for key in keys}


# --------------------------------------------------------------------------- #
# The cascade.
# --------------------------------------------------------------------------- #
def test_the_cascade_is_the_default_and_neither_alternative_was_retired() -> None:
    """Adopted on 2026-09-07, Matt's ruling, and adoption is one constant.

    The other half of the pin is what the flip did NOT do: `rank-key` is the order
    every gallery between 2026-08-28 and the flip was seated in and is still what
    retention ranks on, and `p_ge4` is what everything before that ran. A record
    naming either has to stay re-runnable, so both stay in [`solve.KEYS`].

    **Deprecating `rank-key` on 2026-09-08 did not change that.** What it changed
    is [`solve.OFFERED_KEYS`] — what a NEW solve may name — and the two lists
    being different is the whole content of "readable but not offered".
    """
    assert solve.DEFAULT_KEY == solve.CASCADE_KEY
    assert set(solve.KEYS) == {solve.CASCADE_KEY, solve.RANK_KEY, solve.JUDGE_KEY}
    assert set(solve.OFFERED_KEYS) == {solve.CASCADE_KEY, solve.JUDGE_KEY}
    assert solve.RANK_KEY not in solve.OFFERED_KEYS


def test_a_record_seated_on_the_deprecated_key_still_resolves_its_order() -> None:
    """The 62 stamps taken before 2026-09-08 name `rank-key`, and a deprecation
    that made them unreplayable would be a deletion wearing another word."""
    assert solve.RANK_KEY in solve.KEYS
    assert solve.ordered_by({"a": 1.0}, key=solve.RANK_KEY) == "rank_key"


def test_adopting_the_cascade_left_retention_ranking_on_the_shipped_key() -> None:
    """★ Seating only, and this is where that claim would break silently.

    `_prune_ranks` decides what the ledger keeps, and it reads
    [`curation.rank_key`] itself rather than [`solve.DEFAULT_KEY`] — so the flip
    could not reach it. A prune that started ranking on a head fitted above the
    gate would be throwing away the below-bar material the head has never seen.
    """
    import inspect

    from fractal_wallpapers.curation.candidate_ledger import sweep

    source = inspect.getsource(sweep._prune_ranks)
    assert "rank_key" in source
    assert "DEFAULT_KEY" not in source and "cascade" not in source


def test_below_the_bar_the_order_is_handed_back_untouched(monkeypatch) -> None:
    """★ The claim that makes it a cascade rather than a fourth column.

    The head's output is undefined on a row that never cleared the gate, so if
    one below-bar value moved, this would be a pool-wide ranker fitted on a
    population it has never seen the like of.
    """
    candidates = pool()
    order = {c.key: 0.5 for c in candidates}
    monkeypatch.setattr(
        _trainer(),
        "read_pool_scores",
        lambda *_a, **_k: readings([c.key for c in candidates], lambda key: 0.8),
    )
    out, record = solve.cascade_order(candidates, order, {"key": "rank-key"}, log=quiet)
    for held in candidates:
        if not held.above_bar:
            assert out[held.key] == order[held.key], held.key
    assert record["cascade"]["below_bar"] == 3
    assert record["cascade"]["lifted"] == 4


def test_every_above_bar_row_outranks_every_below_bar_row(monkeypatch) -> None:
    """The two stages are not on one scale, so they are separated by a constant.

    The worst row the head likes still beats the best row the shipped key does,
    which is what "the cascade decides the top" means — and a rank key value of
    0.99 below the bar must not overtake a fine P(>=4) of 0.0 above it.
    """
    candidates = pool()
    order = {c.key: 0.99 for c in candidates}
    monkeypatch.setattr(
        _trainer(),
        "read_pool_scores",
        lambda *_a, **_k: readings([c.key for c in candidates], lambda key: 0.0),
    )
    out, _record = solve.cascade_order(candidates, order, {}, log=quiet)
    over = [out[c.key] for c in candidates if c.above_bar]
    under = [out[c.key] for c in candidates if not c.above_bar]
    assert min(over) > max(under)


def test_an_above_bar_row_the_head_never_read_keeps_the_shipped_key_s_value(monkeypatch) -> None:
    """The conservative direction, and the one that makes a partial reading safe.

    It falls behind every row the head could read rather than ahead of them, so a
    pool this head has only partly been run over degrades to the shipped key
    rather than to noise.
    """
    candidates = pool()
    order = {c.key: 0.7 for c in candidates}
    seen = [c.key for c in candidates if c.above_bar][:-1]
    monkeypatch.setattr(
        _trainer(), "read_pool_scores", lambda *_a, **_k: readings(seen, lambda key: 0.5)
    )
    out, record = solve.cascade_order(candidates, order, {}, log=quiet)
    missed = [c for c in candidates if c.above_bar and c.key not in seen][0]
    assert out[missed.key] == 0.7
    assert record["cascade"]["above_bar_unread"] == 1
    assert out[missed.key] < min(out[key] for key in seen)


def test_the_cascade_refuses_rather_than_seating_on_a_pool_it_never_read(monkeypatch) -> None:
    """A missing column is a seating that would silently be the shipped key under
    a record saying it was the cascade."""
    monkeypatch.setattr(_trainer(), "read_pool_scores", lambda *_a, **_k: {})
    with pytest.raises(solve.SolveRefused) as refused:
        solve.cascade_order(pool(), {}, {}, log=quiet)
    assert "score-pool" in str(refused.value)


def test_the_order_inside_the_top_is_the_head_s_and_not_the_key_s(monkeypatch) -> None:
    candidates = pool(above=3, below=0)
    # The shipped key likes them in one order; the head likes the reverse.
    order = {c.key: 0.1 * (index + 1) for index, c in enumerate(candidates)}
    monkeypatch.setattr(
        _trainer(),
        "read_pool_scores",
        lambda *_a, **_k: readings(
            [c.key for c in candidates], lambda key: 1.0 - 0.1 * int(str(key)[-1])
        ),
    )
    out, _record = solve.cascade_order(candidates, order, {}, log=quiet)
    assert [c.key for c in sorted(candidates, key=lambda c: -out[c.key])] == [
        "hi0",
        "hi1",
        "hi2",
    ]


# --------------------------------------------------------------------------- #
# The diff.
# --------------------------------------------------------------------------- #
def solved(keys) -> dict:
    return {"seated": [{"key": str(key), "picture": ""} for key in keys]}


def seated_at(pairs) -> dict:
    """`(candidate, place)` pairs, for the half of the diff that is about places."""
    return {"seated": [{"key": str(key), "location": str(place)} for key, place in pairs]}


def test_the_diff_is_keyed_on_the_candidate_and_never_on_the_seat_number() -> None:
    """Seat numbers renumber under any reordering, so a diff taken on them would
    call every row changed and say nothing."""
    diff = seat_sheet.difference(solved(["a", "b", "c"]), solved(["c", "b", "d"]))
    assert {row["key"] for row in diff["arriving"]} == {"d"}
    assert {row["key"] for row in diff["departing"]} == {"a"}
    assert diff["kept"] == 2
    assert (diff["before"], diff["after"]) == (3, 3)


def test_two_solves_that_seated_the_same_rows_have_no_diff_at_all() -> None:
    diff = seat_sheet.difference(solved(["a", "b"]), solved(["b", "a"]))
    assert not diff["arriving"] and not diff["departing"] and diff["kept"] == 2
    with pytest.raises(seat_sheet.SeatSheetError):
        seat_sheet.build("nothing-moved", diff, log=quiet)


def test_a_changed_seat_says_whether_its_PLACE_moved_or_only_its_candidate() -> None:
    """★ Two quite different things wear the same badge until the row says which.

    `p1` is seated by both keys and they disagree about the candidate there; `p2`
    leaves the gallery and `p3` joins it. A count of changed seats reads 4 either
    way, and only the split says that one of those changes is a swap and two are
    the gallery going somewhere else.
    """
    diff = seat_sheet.difference(
        seated_at([("a", "p1"), ("b", "p2")]),
        seated_at([("c", "p1"), ("d", "p3")]),
    )
    moved = {row["key"]: row["place_seated"] for row in diff["arriving"] + diff["departing"]}
    assert moved == {"c": "both", "d": "one", "a": "both", "b": "one"}
    assert diff["places"] == {
        "before": 2,
        "after": 2,
        "shared": 1,
        "changed_at_a_shared_place": 2,
        "changed_because_the_place_moved": 2,
    }


def test_under_the_cap_every_row_is_shown_good_to_bad() -> None:
    rows = [{"key": f"k{index}", "fine_score": index / 10.0} for index in range(20)]
    shown, sampling = seat_sheet.sampled(rows, cap=50)
    assert sampling == {"of": 20, "shown": 20, "sampled": False}
    assert [row["key"] for row in shown[:2]] == ["k19", "k18"]


def test_over_the_cap_the_sample_spans_the_range_rather_than_taking_the_top() -> None:
    """★ The top of a diff is the part the two keys mostly agree about.

    A `[:cap]` slice would show the least of what changed, so the sample is every
    nth row of the head's own order — and the pin is that the worst row survives
    it.
    """
    rows = [{"key": f"k{index:03d}", "fine_score": index / 1000.0} for index in range(1000)]
    shown, sampling = seat_sheet.sampled(rows, cap=10)
    assert sampling["of"] == 1000 and sampling["shown"] == 10 and sampling["sampled"]
    scores = [row["fine_score"] for row in shown]
    assert scores == sorted(scores, reverse=True)
    assert scores[0] > 0.99 and scores[-1] < 0.11, scores


def test_the_cap_is_the_sheet_s_own_constant_and_the_page_says_the_true_count() -> None:
    assert seat_sheet.CAP == 150
