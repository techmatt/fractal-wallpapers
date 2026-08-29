"""The mode policy: one table, and the places that are held to reading it.

The table itself is arithmetic and belongs in the fast lane. What is worth
pinning hardest is not any one mode's weight — that is a decision and decisions
move — but the two properties the table exists for: that it and the engine's
catalog describe the same roster, and that a weight of 0 is honoured at *every*
place a mode is drawn or seated rather than at the one leg that used to hold the
old constants.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers import engine
from fractal_wallpapers.curation import mode_policy


def engine_is_built() -> bool:
    try:
        engine.engine_path()
    except FileNotFoundError:
        return False
    return True


needs_engine = pytest.mark.skipif(
    not engine_is_built(),
    reason="the engine is not built: cargo build --release --manifest-path engine/Cargo.toml",
)


# --------------------------------------------------------------------------- #
# The table.
# --------------------------------------------------------------------------- #
def test_every_weight_is_one_of_the_three():
    assert set(mode_policy.MODE_POLICY.values()) <= set(mode_policy.WEIGHTS)


def test_a_mode_nobody_has_ruled_on_is_refused_rather_than_given_a_weight():
    """The default that is not there on purpose: a mode arriving in the engine's
    catalog has no standing, and quietly reading it as normal is how a table meant
    to be exhaustive stops being read."""
    with pytest.raises(mode_policy.PolicyRefused, match="no weight"):
        mode_policy.weight_of("a_mode_that_does_not_exist")


def test_is_accepted_answers_without_raising_and_without_crossing_to_the_engine():
    """[`solve.pool`] asks this once a ledger row over a quarter of a million of
    them, so it must be cheap, and an unnamed mode there is a row that is not
    gallery material rather than a crash."""
    assert mode_policy.is_accepted("smooth") is True
    assert mode_policy.is_accepted("trap_circle") is False
    assert mode_policy.is_accepted("a_mode_that_does_not_exist") is False
    assert mode_policy.is_accepted(None) is False


@needs_engine
def test_the_table_and_the_catalog_describe_the_same_roster():
    read = mode_policy.check()
    assert read["production"] == len(mode_policy.MODE_POLICY)
    assert len(read["accepted"]) + len(read["niche"]) == read["production"]


@needs_engine
def test_the_engines_own_niche_tier_never_appears_in_the_table():
    """Two layers, one word, and the table exists so a standing is not written in
    both. `de` is the engine's — what the corpora were collected over — and it
    carries no weight here."""
    catalog = {mode["name"]: mode for mode in engine.modes()}
    tiered = {name for name, mode in catalog.items() if mode["tier"] == engine.NICHE}
    assert tiered, "there is nothing to exclude, so this proves nothing"
    assert not tiered & set(mode_policy.MODE_POLICY)


@needs_engine
def test_accepted_and_niche_are_disjoint_and_come_back_in_catalog_order():
    order = engine.production_modes()
    accepted, niche = mode_policy.accepted(), mode_policy.niche()
    assert not set(accepted) & set(niche)
    assert accepted == [name for name in order if name in set(accepted)]
    assert niche == [name for name in order if name in set(niche)]


# --------------------------------------------------------------------------- #
# What reads it.
# --------------------------------------------------------------------------- #
@needs_engine
def test_no_wired_roster_offers_a_niche_mode():
    """The point of the table. The old constants were read by one leg; a mode
    weighted 0 has to be out of the mode draw, out of both mining rosters, out of
    the depth roster and out of the mode floors — or a standing is a footnote
    again."""
    from fractal_wallpapers.curation import budget, colorize, depth, mine

    out = set(mode_policy.niche())
    assert out, "there is nothing to exclude, so this proves nothing"
    rosters = {
        "the smooth draw": colorize.modes_for(budget.SMOOTH),
        "the strange draw": colorize.modes_for(budget.STRANGE),
        "the mine": mine._accepted_modes(),
        "the depth roster": depth.field_modes(),
    }
    for where, roster in rosters.items():
        assert not out & set(roster), f"{where} can still draw {out & set(roster)}"


@needs_engine
def test_a_niche_mode_still_resolves_and_keeps_its_kind():
    """Nothing is deleted. A niche mode renders by name, its coloring is in the
    catalog, and a verdict already exported on one still has a mode to join to."""
    from fractal_wallpapers.curation import colorize

    catalog = {mode["name"]: mode for mode in engine.modes()}
    for name in mode_policy.niche():
        assert catalog[name]["coloring"]
        assert catalog[name]["tier"] == engine.PRODUCTION
        assert colorize.kind_of(name) in ("field", "composite", "modulate", "direct")


@needs_engine
def test_the_gallery_pool_refuses_a_niche_mode_and_counts_the_refusal():
    """Gallery emission, at the one pool both the greedy and the solver read.
    Counted rather than silently dropped: a refusal nobody can see is a policy
    nobody can audit."""
    from fractal_wallpapers.curation import solve

    niche = mode_policy.niche()[0]
    rows = [_ledger_row("mp_keep", "smooth"), _ledger_row("mp_drop", niche)]
    # The sidecar is keyed on the artifact and the pool joins on one, so a fixture
    # that left it off would be testing a join that cannot happen.
    scores = [
        {
            "recipe_key": key,
            "p_ge4": 0.9,
            "p_ge3": 0.95,
            "head": "strange_render",
            "judge_artifact": "judge-under-test",
        }
        for key in ("mp_keep", "mp_drop")
    ]
    candidates, refused = solve.pool(
        rows=rows, scores=scores, artifact="judge-under-test", log=lambda *_: None
    )
    assert [candidate.key for candidate in candidates] == ["mp_keep"]
    assert refused["niche_mode"] == 1


def _ledger_row(key: str, mode: str) -> dict:
    """One ledger row shaped as [`solve.pool`] reads it, with its picture planted.

    Existence is all the pool asks of the picture, so the planted file is empty —
    and it has to be planted, or both rows would be refused for a reason that is
    not the one under test.
    """
    from fractal_wallpapers import paths

    made = paths.hot_root() / f"{key}.jpg"
    made.parent.mkdir(parents=True, exist_ok=True)
    made.touch()
    return {
        "key": key,
        "recipe_key": key,
        "location": {"key": f"place_{key}"},
        "partition": "mandelbrot",
        "recipe": {"mode": mode},
        "palette_group": f"map:{key}",
        "colour": {"cells": ["dark_vivid_blue"], "families": ["blue"]},
        "picture": f"artifacts/{key}.jpg",
        "at_candidate_regime": True,
        "rejected": None,
    }
