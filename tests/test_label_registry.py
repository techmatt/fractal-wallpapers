"""Batch registration: fail-closed, and eval-eligibility derived from two flags and a pin.

The registry answers one question — may anything measured on this population be
read as a rate about the world? — and it answers it conservatively when nobody
wrote the population down.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.labeling import registry as registry_module
from fractal_wallpapers.labeling import store


def registration(batch="a", **flags) -> registry_module.Registration:
    return registry_module.Registration(batch=batch, method="a draw", **flags)


def test_an_unregistered_batch_fails_closed() -> None:
    found = registry_module.lookup({}, "nobody_registered_this")
    assert not found.score_unconditioned
    assert not found.eval_eligible
    assert found.side == "train"


def test_eligibility_is_derived_from_the_two_flags() -> None:
    assert registration(score_unconditioned=True).eval_eligible
    assert not registration(score_unconditioned=False).eval_eligible


def test_an_anchored_page_is_train_side_however_the_draw_was_made() -> None:
    """A correction page's labels measure agreement with the head that suggested
    them, which is the failure the flag exists to carry: the draw can be perfect
    and the labels still unusable as an instrument."""
    anchored = registration(score_unconditioned=True, anchored=True)
    assert not anchored.eval_eligible
    assert anchored.side == "train"


def test_an_identical_re_registration_is_appended_and_reads_as_a_no_op(store_dir) -> None:
    """Re-running a registration step is how anybody finds out it already ran, so
    the second row is written and the read is unmoved. The two rows differ in
    `registered_at` by construction, which is why that field is not part of the
    claim."""
    store.register(registration("a", score_unconditioned=True))
    store.register(registration("a", score_unconditioned=True))
    lines = store.registry_path().read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert registry_module.eval_eligible(store.registry(), "a")


def test_a_second_registration_that_disagrees_is_refused_at_the_writer(store_dir) -> None:
    """The failure this closes is silent: a batch that changes sides between two
    readings of one file, with nothing red and every number measured on it
    quietly meaning something else. Refused at the write, so the file never holds
    two answers — a read-side guard alone would leave the row on disk and every
    later read raising."""
    store.register(registration("a", score_unconditioned=True))
    with pytest.raises(registry_module.RegistrationContradiction) as refusal:
        store.register(registration("a", score_unconditioned=False))
    said = str(refusal.value)
    assert "-> eval" in said and "-> train" in said
    lines = store.registry_path().read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1, "the contradicting row must not have landed"


def test_a_contradiction_on_the_method_alone_is_still_a_contradiction(store_dir) -> None:
    """The method sentence is the record of how the population was drawn, and it
    is the only record. Two of them is two populations under one name."""
    store.register(registration("a"))
    with pytest.raises(registry_module.RegistrationContradiction, match="already registered"):
        store.register(
            registry_module.Registration(batch="a", method="a completely different draw")
        )


def test_a_file_that_already_holds_two_answers_is_refused_at_the_read(store_dir) -> None:
    """The backstop, for a file somebody edited by hand or a row that predates the
    writer's guard. Both rows are named, by line, because the fix is to decide
    which one is true."""
    store.registry_path().parent.mkdir(parents=True, exist_ok=True)
    store.registry_path().write_text(
        json.dumps(registration("a", score_unconditioned=True).row())
        + "\n"
        + json.dumps(registration("a", score_unconditioned=False).row())
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(registry_module.RegistrationContradiction) as refusal:
        store.registry()
    said = str(refusal.value)
    assert "line 1" in said and "line 2" in said
    assert "-> eval" in said and "-> train" in said


def test_the_rationale_may_be_corrected_without_contradicting_the_claim(store_dir) -> None:
    """`why` sits beside the claim rather than in it: a sentence somebody improved
    is not a second answer about the draw."""
    store.register(registry_module.Registration(batch="a", method="a draw", why="terse"))
    store.register(
        registry_module.Registration(batch="a", method="a draw", why="the fuller reason")
    )
    assert registry_module.lookup(store.registry(), "a").method == "a draw"


def test_a_registration_without_a_method_is_refused(store_dir) -> None:
    with pytest.raises(registry_module.RegistrationError, match="how the population was drawn"):
        store.register(registry_module.Registration(batch="a", method=""))


def test_a_registration_is_stamped_with_when_it_was_made(store_dir) -> None:
    row = store.register(registration("a"))
    assert row["registered_at"]


def test_the_summary_separates_permission_from_anchoring(store_dir) -> None:
    store.register(registration("instrument", score_unconditioned=True))
    store.register(registration("correction", anchored=True))
    summary = registry_module.summary(store.registry())
    assert summary["eval_eligible"] == ["instrument"]
    assert summary["anchored"] == ["correction"]
    assert summary["train_side"] == ["correction"]


def test_a_registration_row_of_the_wrong_schema_raises(store_dir) -> None:
    store.registry_path().parent.mkdir(parents=True, exist_ok=True)
    store.registry_path().write_text('{"schema": 99, "batch": "a"}\n', encoding="utf-8")
    with pytest.raises(registry_module.RegistrationError, match="schema"):
        store.registry()
