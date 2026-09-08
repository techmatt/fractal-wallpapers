"""The ratchet: what it forgives, and what it will not.

The guard this replaced was a floor — `>=` a number somebody measured — under a
store that deletes rows on purpose, so it went red at the first prune and the only
edits available were to repoint it (which asserts nothing) or to delete it. What
stands in its place has to do two things that a floor cannot, and every test here
is one of them:

* **forgive a loss a transaction wrote down**, so the ordinary working of the
  retention rule is not a failure; and
* **catch a loss nothing wrote down**, which is the whole property the floor was
  there for and the one a repointed constant gives up.

Arithmetic over a small file, so all of it is in the fast lane. The scan it holds
is in `tests/test_leveled_identity.py` and it is slow for its own reason — it
reads the store, not this.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.curation.candidate_ledger import ratchet


@pytest.fixture
def log(tmp_path):
    """A ratchet log of this test's own. Absent until something writes it."""
    return tmp_path / ratchet.LOG_NAME


def marks(counts, log, why="a test", when="2026-01-01"):
    return ratchet.advance(counts, why=why, when=when, path=log)


def loses(counts, log, why="a test", when="2026-01-01"):
    return ratchet.record_loss(counts, why=why, when=when, path=log)


def reconciles(found: dict, log) -> bool:
    """The invariant the census asserts, as one expression. Every counter, or none."""
    standing = ratchet.reading(log)
    return all(
        found[name] + standing["deleted"][name] >= standing["mark"][name]
        for name in standing["mark"]
    )


# --------------------------------------------------------------------------- #
# The classification, which the census reads too.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("picture", "key", "shape"),
    [
        # A stem that is the row's own key is the recipe-key shape, whatever else
        # the path holds.
        ("artifacts/curation/depth/leg/pictures/abcd.jpg", "abcd", ratchet.RECIPE_KEY),
        # An attempt index is not its row's key, and the key here CONTAINS it —
        # which is what a classification built on `in` rather than on `==` gets
        # wrong.
        ("artifacts/curation/runs/leg/pictures/0042.jpg", "runs|0042", ratchet.RUN_INDEX),
        # A stem that is a prefix of the key, and a key that is a prefix of it.
        ("artifacts/curation/depth/leg/pictures/abc.jpg", "abcd", ratchet.RUN_INDEX),
        ("artifacts/curation/depth/leg/pictures/abcd.jpg", "abc", ratchet.RUN_INDEX),
        # A dotted stem: `stem` takes the last suffix off and no more.
        ("artifacts/curation/depth/leg/pictures/a.b.c.jpg", "a.b.c", ratchet.RECIPE_KEY),
        # Recorded by a Windows run, classified on either platform. This is the
        # case a `PurePosixPath` with no normalisation reads as ONE component.
        ("artifacts\\curation\\depth\\leg\\pictures\\abcd.jpg", "abcd", ratchet.RECIPE_KEY),
        # A key that is not a string, which is what a row carries when the key is
        # an integer index.
        ("artifacts/curation/runs/leg/pictures/17.jpg", 17, ratchet.RECIPE_KEY),
    ],
)
def test_a_picture_is_named_by_its_key_or_by_an_index_and_nothing_else(picture, key, shape):
    assert ratchet.shape_of(picture, key) == shape


def test_the_counters_split_the_rows_and_a_row_with_no_picture_joins_neither():
    """`rows` counts every row; the two shapes count the ones there is a stem for.

    The census asserts no row names an absent picture, so in a healthy store the
    shapes sum to the rows. This counts what it is given rather than what should
    be true, which is what makes the census's assertion worth making."""
    found = ratchet.counts_of(
        [
            ("abcd", "artifacts/curation/depth/leg/pictures/abcd.jpg"),
            ("efgh", "artifacts/curation/depth/leg/pictures/efgh.jpg"),
            ("runs|0001", "artifacts/curation/runs/leg/pictures/0001.jpg"),
            ("nameless", None),
        ]
    )
    assert found == {"rows": 4, "recipe_key_named": 2, "run_index_named": 1}
    assert set(found) == set(ratchet.COUNTERS)


# --------------------------------------------------------------------------- #
# The mark.
# --------------------------------------------------------------------------- #
def test_an_absent_log_marks_nothing_rather_than_raising(log):
    """A checkout that has never pruned is a state, and the census refuses it by
    name — an unmarked counter is a counter with no guard on it, which is a
    louder and more specific failure than a missing file would be."""
    assert ratchet.entries(log) == []
    assert ratchet.reading(log) == {
        "mark": {},
        "deleted": dict.fromkeys(ratchet.COUNTERS, 0),
        "marked_at": {},
    }


def test_the_mark_advances_on_growth_and_stands_still_on_loss(log):
    """The ratchet's whole shape in one test: up, never down."""
    marks({"rows": 100}, log)
    assert ratchet.reading(log)["mark"]["rows"] == 100

    assert marks({"rows": 90}, log) is None, "a smaller store must not lower the mark"
    assert ratchet.reading(log)["mark"]["rows"] == 100

    assert marks({"rows": 100}, log) is None, "an unchanged store writes no row"
    grown = marks({"rows": 140}, log)
    assert grown["counts"] == {"rows": 140}
    assert ratchet.reading(log)["mark"]["rows"] == 140


def test_a_mark_row_names_only_the_counters_that_actually_grew(log):
    """One transaction, one row, and the row is not the whole census.

    This is what makes the per-counter reset below safe. A mark row that restated
    every counter would announce an advance for counters that stood still, and
    [`ratchet.reading`] would zero their accounted deletions on the strength of
    it."""
    marks({"rows": 100, "run_index_named": 20}, log)
    grown = marks({"rows": 130, "run_index_named": 20}, log)
    assert grown["counts"] == {"rows": 130}


# --------------------------------------------------------------------------- #
# The deletions, and what a reset may and may not throw away.
# --------------------------------------------------------------------------- #
def test_a_recorded_loss_is_forgiven_and_an_unrecorded_one_is_not(log):
    """The two halves of the invariant, against one mark.

    A store at 100 that lost 10 reconciles when a transaction said it took 10, and
    does not when it said it took 9. That difference is the entire guard: the
    floor this replaced could not tell those two stores apart, because both of
    them are simply *under the number*."""
    marks({"rows": 100}, log)
    loses({"rows": 10}, log)
    assert reconciles({"rows": 90}, log)
    assert not reconciles({"rows": 89}, log), "a row went that no transaction accounted for"

    # Growth on top of an accounted loss is still fine: the invariant is `>=`, and
    # a store climbing back toward its mark has nothing to explain.
    assert reconciles({"rows": 95}, log)


def test_nothing_taken_writes_no_row(log):
    """A prune that dropped nothing has nothing to account for, and a row of
    zeroes per merge would be the whole growth of this file."""
    marks({"rows": 100}, log)
    assert loses({"rows": 0, "run_index_named": 0}, log) is None
    assert [row["event"] for row in ratchet.entries(log)] == [ratchet.MARK]


def test_an_advance_zeroes_that_counters_deletions_and_leaves_the_others_alone(log):
    """**The reason the reading is per counter**, and the shape of this store on
    2026-09-07: `rows` climbing past its mark while `run_index_named` sat 22 below
    its own, with all 22 accounted for.

    Reset together, the advance on `rows` would have thrown away the 22 that
    explain `run_index_named`, and a counter that lost nothing new would have read
    short against a mark it never reached again — a false red, produced by the
    guard's own bookkeeping."""
    marks({"rows": 100, "run_index_named": 20}, log)
    loses({"rows": 4, "run_index_named": 6}, log)
    marks({"rows": 130}, log)

    standing = ratchet.reading(log)
    assert standing["mark"] == {"rows": 130, "run_index_named": 20}
    assert standing["deleted"]["rows"] == 0, "the mark moved past them, so they are history"
    assert standing["deleted"]["run_index_named"] == 6, "these still explain a counter"
    assert reconciles({"rows": 130, "run_index_named": 14, "recipe_key_named": 0}, log)


def test_deletions_after_one_mark_accumulate_across_transactions(log):
    """Several prunes between two marks, and the census forgives their sum."""
    marks({"rows": 100}, log)
    for _ in range(3):
        loses({"rows": 5}, log)
    assert ratchet.reading(log)["deleted"]["rows"] == 15
    assert reconciles({"rows": 85}, log)
    assert not reconciles({"rows": 84}, log)


def test_the_marked_at_says_which_reading_a_counter_is_held_to(log):
    """A shortfall names a date, so the reader knows which census they are arguing
    with rather than only that they are under a number."""
    marks({"rows": 100}, log, when="2026-01-01")
    marks({"rows": 120}, log, when="2026-02-02")
    assert ratchet.reading(log)["marked_at"]["rows"] == "2026-02-02"


# --------------------------------------------------------------------------- #
# The file itself.
# --------------------------------------------------------------------------- #
def test_the_log_is_lf_jsonl_carrying_a_schema_from_the_first_row(log):
    """The store convention, and the line-ending rule this repository's Windows
    runs exist to not break. `git status` cannot see CRLF drift under
    `* text=auto eol=lf`, so it is asserted on the bytes."""
    marks({"rows": 100}, log)
    loses({"rows": 3}, log, why="prune")
    raw = log.read_bytes()
    assert b"\r\n" not in raw
    lines = raw.decode("utf-8").splitlines()
    assert len(lines) == 2
    for line in lines:
        row = json.loads(line)
        assert row["schema"] == ratchet.LOG_SCHEMA
        assert row["event"] in {ratchet.MARK, ratchet.DELETED}
        assert row["why"] and row["at"]


def test_a_reconciliation_carries_its_note_and_an_ordinary_loss_does_not(log):
    """A loss with no transaction behind it has to say so in the row itself.

    The 22 `run_index_named` rows that went before anything recorded a deletion
    are entered once, with the sentence explaining that they cannot be
    reconstructed. A prune's own row needs no note — `why` is the whole story."""
    marks({"rows": 100}, log)
    plain = loses({"rows": 2}, log, why="prune")
    assert "note" not in plain
    entered = ratchet.record_loss(
        {"rows": 5}, why="reconciliation", when="2026-01-02", note="predates the ratchet", path=log
    )
    assert entered["note"] == "predates the ratchet"
