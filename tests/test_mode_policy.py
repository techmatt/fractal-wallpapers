"""The mode policy: one table, and the places that are held to reading it.

The table itself is arithmetic and belongs in the fast lane. What is worth
pinning hardest is not any one mode's weight — that is a decision and decisions
move — but the two properties the table exists for: that it and the engine's
catalog describe the same roster, and that a weight of 0 is honoured at *every*
place a mode is drawn or seated rather than at the one leg that used to hold the
old constants.
"""

from __future__ import annotations

from pathlib import Path

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


# --------------------------------------------------------------------------- #
# The seat floors. Built, and nothing enables them.
# --------------------------------------------------------------------------- #
def test_the_seat_share_is_its_own_knob_and_not_the_mining_one(monkeypatch):
    """One name for two stages is the confusion this repository keeps paying for.

    The two carry the same number today and answer different questions — how a
    release's mining slots split between the heads, against how many of a
    gallery's seats the strange side is meant to hold. They are free to move
    apart, so neither may be defined as the other, and moving one must not move
    the other.
    """
    from fractal_wallpapers.curation import run

    assert mode_policy.STRANGE_SEAT_SHARE == 0.60
    monkeypatch.setattr(run, "STRANGE_SHARE", 0.05)
    assert mode_policy.STRANGE_SEAT_SHARE == 0.60
    assert mode_policy.strange_seats(1000) == 600


@needs_engine
def test_the_floors_sum_to_half_the_strange_budget():
    """The whole construction: half the budget floored, half left to spend.

    Largest remainder is what makes the sum exact. Truncating each mode's half
    would lose a seat per mode with a remainder, which over thirteen modes is
    most of them.
    """
    for n in (100, 150, 500, 999, 1000):
        budget = mode_policy.strange_seats(n)
        assert sum(mode_policy.seat_floors(n).values()) == (budget + 1) // 2


@needs_engine
def test_a_promoted_mode_is_floored_at_twice_a_normal_one():
    """What makes the weights load-bearing: `2 * promoted + 1 * normal`."""
    floors = mode_policy.seat_floors(1000)
    promoted = {name for name in mode_policy.promoted()} & set(floors)
    normal = set(floors) - promoted
    assert promoted and normal
    assert len({floors[name] for name in promoted}) == 1
    assert len({floors[name] for name in normal}) == 1
    assert next(iter(floors[name] for name in promoted)) == 2 * next(
        iter(floors[name] for name in normal)
    )


@needs_engine
def test_no_mode_gets_a_bare_one_by_exception():
    """`direct_trap_multiply` included. A floor that special-cases somebody is a
    table pretending to be a rule."""
    floors = mode_policy.seat_floors(1000)
    assert "direct_trap_multiply" in floors
    normal = [name for name in floors if mode_policy.weight_of(name) == mode_policy.NORMAL]
    assert floors["direct_trap_multiply"] == floors[normal[0]]
    assert set(floors.values()) != {1}


@needs_engine
def test_smooth_is_not_in_the_floors_because_the_smooth_side_is_one_mode():
    """Read off the colouring split rather than asserted here, which is the point."""
    from fractal_wallpapers.curation import budget, colorize

    assert colorize.modes_for(budget.SMOOTH) == [colorize.SMOOTH_MODE]
    assert colorize.SMOOTH_MODE not in mode_policy.seat_floors(1000)
    assert set(mode_policy.strange_modes()) == set(mode_policy.accepted()) - {colorize.SMOOTH_MODE}


@needs_engine
def test_a_gallery_too_small_to_floor_anything_asks_for_nothing():
    """Zero is a real answer, the same way [`solve.mode_floor`]'s is."""
    assert set(mode_policy.seat_floors(0).values()) == {0}
    assert sum(mode_policy.seat_floors(1).values()) == 1


@needs_engine
def test_the_floors_are_a_pure_function_of_n():
    """Ties are broken by weight then by name, so two readers get one answer."""
    assert mode_policy.seat_floors(150) == mode_policy.seat_floors(150)
    assert mode_policy.seat_floors(150) != mode_policy.seat_floors(200)


@needs_engine
def test_the_floor_rule_is_reachable_only_by_naming_it():
    """It still ships inert, and there is now exactly one way to turn it on.

    This was `test_nothing_that_ships_calls_the_floor_rule_yet` and it was a
    stronger statement than the fact it defended: nothing shipped *reached* the
    rule at all. `curate seat --seat-floors` reaches it now, because the rule
    cannot be measured against a baseline gallery without a leg that seats under
    it. What must stay true is what always mattered — **no unflagged seating
    builds a gallery under it** — so that is what is asserted here, on the parser
    rather than on a grep.

    The grep half is kept and narrowed: `cli.py` is the one shipped file allowed
    to name the rule, so a second leg quietly adopting it is still a red.
    """
    import subprocess

    root = Path(__file__).resolve().parents[1]
    found = subprocess.run(
        ["git", "grep", "-l", "seat_floors(", "--", "src/**/*.py"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    reached = {line for line in found.stdout.split() if line}
    assert reached <= {
        "src/fractal_wallpapers/curation/mode_policy.py",
        "src/fractal_wallpapers/cli.py",
    }, f"a leg other than `curate seat` reaches the floor rule: {sorted(reached)}"

    from fractal_wallpapers import cli

    parser = cli.build_parser()
    plain = parser.parse_args(["curate", "seat", "--n", "150"])
    assert plain.seat_floors is False, "an unflagged seating must take the flat floor"
    assert plain.mode_floor is None
    named = parser.parse_args(["curate", "seat", "--n", "150", "--seat-floors"])
    assert named.seat_floors is True
