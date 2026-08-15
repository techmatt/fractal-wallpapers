"""Batch registration: fail-closed, and eval-eligibility derived from two flags.

The registry answers one question — may anything measured on this population be
read as a rate about the world? — and it answers it conservatively when nobody
wrote the population down.
"""

from __future__ import annotations

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


def test_a_registration_is_appended_and_the_earlier_one_stays_readable(store_dir) -> None:
    store.register(registration("a", score_unconditioned=True))
    store.register(registration("a", score_unconditioned=False))
    lines = store.registry_path().read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert not registry_module.eval_eligible(store.registry(), "a")


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
