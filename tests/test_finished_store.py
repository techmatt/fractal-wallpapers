"""The finished-render stores: the join, the ceiling, and the pin.

Three properties, and each one is a way a corpus of eight thousand verdicts could
be quietly wrong. A row whose join is short collapses onto another row and takes
a verdict with it. A row scored above its store's ceiling becomes a cutpoint
nothing trained. And a training row on a pinned location spends the only
unanchored reading of that population that exists — silently, because a spent
instrument still produces a number.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.labeling import finished
from fractal_wallpapers.labeling import registry as registry_module


def a_row(head: str = "strange_render", **changes) -> dict:
    fields = {
        "head": head,
        "batch": "mode_sweep",
        "score": 2,
        "family": {"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]},
        "viewport": {"center_re": "0.1", "center_im": "0.2", "width": "0.5"},
        # The mode follows the head, because the store a row may enter is decided
        # by its mode: `smooth` is the smooth judge's whole roster and every other
        # mode is the strange judge's.
        "mode": "smooth" if head == "smooth_render" else "direct_trap_ring",
        "mode_params": {} if head == "smooth_render" else {"opacity": 0.3, "threshold": 0.05},
        "curve": "linear",
        "colormap": "twilight_shifted",
        "recipe_": finished.recipe(),
        "render": {"resolution": [1280, 720], "supersample": 2, "maxiter": 8000},
        "recorded_at": "2026-08-06",
    }
    fields.update(changes)
    return finished.render_row(**fields)


def test_two_pictures_of_one_place_are_two_rows() -> None:
    """The whole reason this is not the location store."""
    first = a_row()
    second = a_row(recipe_=finished.recipe(gamma=0.5))
    third = a_row(mode_params={"opacity": 0.45, "threshold": 0.05})
    fourth = a_row(curve="log")
    keys = {finished.render_key(row) for row in (first, second, third, fourth)}
    assert len(keys) == 4, "two differently-colored pictures collapsed onto one identity"
    assert len({finished.place_of(row) for row in (first, second, third, fourth)}) == 1


def test_a_row_missing_a_knob_of_its_recipe_is_refused() -> None:
    thin = finished.recipe()
    del thin["phase"]
    with pytest.raises(finished.FinishedError, match="render identity"):
        a_row(recipe_=thin)


def test_a_row_missing_its_mode_settings_is_refused() -> None:
    with pytest.raises(finished.FinishedError, match="render identity"):
        a_row(mode_params=None)


def test_one_scale_for_every_head_and_it_is_not_the_shipped_model_s_class_count() -> None:
    """Matt's ratified decision. `strange_render` was *collected* on three tiers
    and its first judge trained on three classes; neither was a ceiling on what a
    person may cast, and a store that had made one would be a store that could
    never have collected the retrain that widened the model."""
    assert finished.tiers("smooth_render") == finished.SCALE
    assert finished.tiers("strange_render") == finished.SCALE
    a_row("smooth_render", score=4)
    a_row("strange_render", score=4)
    for head in finished.HEADS:
        with pytest.raises(finished.FinishedError, match="one scale"):
            a_row(head, score=5)


def test_the_model_s_class_count_is_the_model_s_own_and_lives_on_the_recipe() -> None:
    """The decoupling has a second half: the number moved to the recipe, it did
    not disappear. It is read there, never off the store — which is what let the
    strange head sit at three while its corpus was already collecting 4s, and then
    move to four without the store having to change at all."""
    from fractal_wallpapers.models import finished_train

    for head in finished.HEADS:
        # What a person may cast is the store's, and it does not move with the model.
        assert finished.tiers(head) == finished.SCALE
        assert finished_train.recipe_for(head)["classes"] <= len(finished.SCALE)
    assert finished_train.recipe_for("strange_render")["classes"] == 4
    assert finished_train.recipe_for("smooth_render")["classes"] == 4


def test_a_later_verdict_on_one_picture_wins_and_the_earlier_stays_readable() -> None:
    early = {**a_row(recorded_at="2026-08-06"), "_file": "a.jsonl", "_line": 1}
    late = {**a_row(recorded_at="2026-08-10", score=3), "_file": "b.jsonl", "_line": 1}
    resolution = finished.resolve([late, early])
    assert resolution.n_superseded == 1
    assert [row["score"] for row in resolution.scored()] == [3]


#: The contested render the diagnosis found in `strange_render`: one render key
#: carrying an evaluation row and a training row a second apart. Spelled here as
#: two registrations rather than read off the store, so the guard survives the
#: batches being renamed.
CONTESTED = {
    "an_instrument": registry_module.Registration(
        batch="an_instrument", method="blind", eval_only=True, why="the instrument"
    ),
    "a_training_draw": registry_module.Registration(
        batch="a_training_draw", method="the head's own ranked top", why="train-side"
    ),
}


def a_contested_pair() -> tuple[dict, dict]:
    """The eval row, and a training row one second later on the same render key."""
    evaluation = {
        **a_row(batch="an_instrument", score=2, recorded_at="2026-08-29T23:37:21Z"),
        "_file": "an_instrument.jsonl",
        "_line": 1,
    }
    training = {
        **a_row(batch="a_training_draw", score=3, recorded_at="2026-08-29T23:37:22Z"),
        "_file": "a_training_draw.jsonl",
        "_line": 1,
    }
    assert finished.render_key(evaluation) == finished.render_key(training)
    return evaluation, training


def test_the_evaluation_side_outranks_the_clock_on_a_contested_render() -> None:
    """A place is pinned at the location; a row's side is read off its batch. So a
    training batch writing a second after an eval batch on the same render key used
    to take the render off the evaluation side, with nothing red and no writer
    intending it. `eval_only` outranks the timestamp instead."""
    evaluation, training = a_contested_pair()
    resolution = finished.resolve([evaluation, training], known=CONTESTED)
    assert resolution.n_superseded == 1
    assert [row["batch"] for row in resolution.scored()] == ["an_instrument"]
    assert [row["score"] for row in resolution.scored()] == [2]


def test_two_evaluation_rows_on_one_render_still_resolve_by_the_clock() -> None:
    """The pin outranks the clock between sides, and nowhere else."""
    early = {
        **a_row(batch="an_instrument", score=2, recorded_at="2026-08-29T23:37:21Z"),
        "_file": "an_instrument.jsonl",
        "_line": 1,
    }
    late = {**early, "score": 3, "recorded_at": "2026-08-29T23:37:22Z", "_line": 2}
    resolution = finished.resolve([late, early], known=CONTESTED)
    assert [row["score"] for row in resolution.scored()] == [3]


def test_the_canonical_reader_reads_the_registry_for_itself(tmp_path, monkeypatch) -> None:
    """`resolved` is where every consumer routes, so it is where the rule has to
    hold — a caller is not asked to remember to pass the registrations."""
    monkeypatch.setattr(finished, "repo_root", lambda: tmp_path)
    for registration in CONTESTED.values():
        finished.register("strange_render", registration)
    evaluation, training = a_contested_pair()
    for row in (evaluation, training):
        finished.append("strange_render", [{k: v for k, v in row.items() if k[0] != "_"}])

    scored = finished.resolved("strange_render").scored()
    assert [row["batch"] for row in scored] == ["an_instrument"]


def test_the_pin_is_asserted_on_the_place_not_on_the_picture(tmp_path, monkeypatch) -> None:
    """A re-render of a pinned location under a fresh recipe is still the instrument."""
    monkeypatch.setattr(finished, "repo_root", lambda: tmp_path)
    finished.register(
        "strange_render",
        registry_module.Registration(
            batch="blind_modes", method="blind", eval_only=True, why="the instrument"
        ),
    )
    pinned_row = a_row(batch="blind_modes")
    finished.write_pin("strange_render", [pinned_row], {"schema": 1})
    assert len(finished.pinned("strange_render")) == 1

    # Same place, a completely different picture of it.
    trespasser = a_row(
        batch="mode_sweep", mode="tia", mode_params={}, recipe_=finished.recipe(gamma=2.0)
    )
    assert finished.render_key(trespasser) != finished.render_key(pinned_row)
    with pytest.raises(finished.FinishedError, match="spent the moment it trains"):
        finished.assert_pin_holds("strange_render", [trespasser])


def test_the_pin_passes_when_nothing_touches_it(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(finished, "repo_root", lambda: tmp_path)
    finished.write_pin("smooth_render", [a_row("smooth_render", batch="blind_minibrot")], {})
    elsewhere = a_row("smooth_render", viewport={"center_re": "9", "center_im": "9", "width": "1"})
    assert finished.assert_pin_holds("smooth_render", [elsewhere])["ok"]


def test_a_row_whose_mode_belongs_to_the_other_store_is_refused() -> None:
    """The routing guard, planted from both sides.

    Forty resolved `smooth` rows reached `strange_render` through the
    `rare_palette` batch, where they inflated its per-mode tables and put a
    non-strange mode second-highest in a store that does not answer for it.
    Nothing rewrites those originals; this is what stops the next forty.
    """
    with pytest.raises(finished.FinishedError, match="routed to the smooth_render store"):
        a_row("strange_render", mode="smooth", mode_params={})
    with pytest.raises(finished.FinishedError, match="routed to the strange_render store"):
        a_row("smooth_render", mode="tia", mode_params={})


def test_the_guard_asks_the_router_rather_than_holding_its_own_answer() -> None:
    """Two spellings of one routing rule agree until one of them is edited."""
    from fractal_wallpapers.curation import hunt

    for mode in ("smooth", "tia", "direct_trap_ring", "exp_smoothing"):
        assert finished.routed_to(mode) == hunt.kind_of(mode)


def test_the_guard_bites_at_the_writer_and_not_only_at_the_builder(tmp_path, monkeypatch) -> None:
    """`append` is the other door into a store, and a checked row is checked there
    too — otherwise a row built for one head could be appended to the other."""
    monkeypatch.setattr(finished, "repo_root", lambda: tmp_path)
    finished.register(
        "strange_render", registry_module.Registration(batch="mode_sweep", method="a draw")
    )
    smooth = a_row("smooth_render", batch="mode_sweep")
    with pytest.raises(finished.FinishedError, match="routed to the smooth_render store"):
        finished.append("strange_render", [smooth])


def test_a_batch_with_no_registration_cannot_be_written(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(finished, "repo_root", lambda: tmp_path)
    with pytest.raises(finished.FinishedError, match="no registration"):
        finished.append("strange_render", [a_row()])


def test_the_pin_outranks_what_the_two_flags_imply() -> None:
    """Every blind sheet here is `biased` on the location axis, and is still the
    instrument: the pin is the decision, and eligibility follows it."""
    blind = registry_module.Registration(
        batch="blind_modes", method="blind", score_unconditioned=False, eval_only=True
    )
    assert blind.eval_eligible and blind.side == "eval"
    anchored = registry_module.Registration(
        batch="correction", method="correction", score_unconditioned=True, anchored=True
    )
    assert not anchored.eval_eligible


def test_the_shipped_stores_hold_what_they_say_they_hold() -> None:
    """The stores as they are on disk: every row keyed, and nothing trainable on
    a pinned place."""
    for head in finished.HEADS:
        if not finished.registry_path(head).is_file():
            pytest.skip(f"the {head} store has not been imported on this machine")
        resolution = finished.resolved(head)
        assert resolution.n_unkeyed == 0, f"{head}: rows with no render identity"
        assert resolution.n_rows > 0
        known = finished.registry(head)
        scored = resolution.scored()
        pinned = [r for r in scored if registry_module.lookup(known, r["batch"]).eval_only]
        assert pinned, f"{head}: nothing is pinned to the evaluation side"
        train = [r for r in scored if not registry_module.lookup(known, r["batch"]).eval_only]
        assert finished.assert_pin_holds(head, train)["ok"]
        document = json.loads(finished.split_recipe_path(head).read_text(encoding="utf-8"))
        assert document["eval_only_batches"] == sorted({r["batch"] for r in pinned})
