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

from fractal_wallpapers import engine, paths
from fractal_wallpapers.curation import mode_policy


@pytest.fixture(autouse=True)
def artifacts_on_disk(tmp_path, monkeypatch):
    """A hot root these fixtures can plant a picture in that is not the real one.

    [`solve.pool`] asks whether a row's picture is **on disk**, so `_ledger_row`
    has to plant one — and without this it planted `mp_keep.jpg` and
    `mp_drop.jpg` into the checkout's own `artifacts/`, where they outlived the
    run. The same fixture `test_solve` uses, for the same reason.
    """
    root = tmp_path / "artifacts"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv(paths.HOT_ROOT_VARIABLE, str(root))
    return root


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
    again.

    **The centered roster is on this list because it once was not.**
    `depth.CENTERED_FIELD` is the only roster in the tree written out by name, and
    until 2026-09-04 it was unioned in after the gate rather than passed through
    it, so `exp_smoothing` would have gone on being drawn by that one arm after
    every other draw had dropped it. A list of rosters that omits the one roster
    that is not derived is the list that proves the least.
    """
    from fractal_wallpapers.curation import budget, colorize, depth, mine

    out = set(mode_policy.niche())
    assert out, "there is nothing to exclude, so this proves nothing"
    rosters = {
        "the smooth draw": colorize.modes_for(budget.SMOOTH),
        "the strange draw": colorize.modes_for(budget.STRANGE),
        "the mine": mine._mined_modes(),
        "the depth roster": depth.field_modes(),
        "the dear half of it": depth.dear_modes(),
        "the centered roster": depth.centered_modes(),
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
    """What makes the weights load-bearing: `2 * promoted + 1 * normal`.

    The gallery size is **derived from the table rather than picked**, and that is
    the whole of what this test learned when `tail_itinerary` arrived. At `n =
    1000` the strange house was 300 seats over a total weight of 20, which divided
    exactly and made every promoted floor the same integer — a coincidence of the
    roster, not the rule. A fourteenth strange mode put the total at 21, largest
    remainder handed six of the seven promoted modes a spare seat, and the test
    read that as the weights having stopped working. Sizing the house at a whole
    multiple of the total weight makes the halves exact for any roster, so what is
    asserted is the ratio and never the arithmetic's luck.
    """
    total = sum(mode_policy.weight_of(name) for name in mode_policy.strange_modes())
    floors = mode_policy.seat_floors(2 * 20 * total, share=1.0)
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
def test_the_floor_rule_is_the_default_and_a_flag_is_what_turns_it_off():
    """The FLIP. This was `test_the_floor_rule_is_reachable_only_by_naming_it`.

    That guard existed to prove the rule shipped inert while it was being
    measured — built, reachable by one flag, and the default nowhere. The ruling
    (ckpt 94) is that the floors ARE the design, so the polarity is reversed and
    the guard with it: an unflagged seating is seated under the rule, and
    `--flat-floor` is the one way back to the flat `floor(n / 100)` every gallery
    before 2026-08-31 was seated under.

    Asserted on the parser and on the record a seating actually writes, because
    "the default" is a claim about what somebody gets by naming nothing, and a
    grep cannot see that.
    """
    from fractal_wallpapers import cli
    from fractal_wallpapers.curation import solve

    parser = cli.build_parser()
    plain = parser.parse_args(["curate", "solve", "run", "--n", "150"])
    assert plain.flat_floor is False, "the floors are the default; nothing turns them on"
    assert plain.mode_floor is None
    assert parser.parse_args(["curate", "solve", "run", "--flat-floor"]).flat_floor is True

    modes = mode_policy.accepted()
    floored = solve.solve([], n=150, key=solve.JUDGE_KEY, log=lambda *_: None)["config"]
    assert floored["mode_floors"] == solve.floors_for(mode_policy.seat_floors(150), modes)
    assert floored["mode_floor"] is None, "the default is per mode and not one number"
    assert floored["mode_floor_artificial"] is False
    assert "THE DEFAULT" in floored["mode_floor_rule"]

    flat = solve.solve(
        [], n=150, floor=solve.mode_floor(150), key=solve.JUDGE_KEY, log=lambda *_: None
    )["config"]
    assert set(flat["mode_floors"].values()) == {solve.mode_floor(150)}
    assert flat["mode_floor_artificial"] is True
    assert "FLAT" in flat["mode_floor_rule"]


@needs_engine
def test_one_leg_is_floored_by_one_rule_and_the_demands_carry_it():
    """There used to be two legs and two copies of this, and a flip that moved only
    one would have left `curate solve` answering a different question in the same
    words. There is one leg now, and the floors reach the objective through
    `solve.demands_for` — a floor of zero is not a demand at all, because a floor
    nothing can fail is not a row on a shortfall block."""
    from fractal_wallpapers.curation import solve

    modes = mode_policy.accepted()
    held = solve.floors_for(mode_policy.seat_floors(150), modes)
    demands = solve.demands_for(held, {})
    assert {demand.of for demand in demands} == set(mode_policy.strange_modes())
    assert all(demand.wanted(150) == held[demand.of] for demand in demands)
    assert "smooth" not in {demand.of for demand in demands}, "its floor is zero"
    assert "THE DEFAULT" in solve.floor_rule(150, None, held, mode_policy.seat_floors(150), modes)


@needs_engine
def test_the_ruled_out_modes_are_the_six_and_the_two_picture_rulings_are_in_them():
    """The rider, so neither ruling is carried by a docstring alone.

    `tail_itinerary` was seated provisionally at 1 to buy itself a contact sheet.
    It got one and Matt ruled it not gallery-worthy — the frequency of address
    changes is too abrupt — so it is 0, out of the draws and out of the gallery,
    with its catalog entry and every picture it has already made untouched.

    `exp_smoothing` is the other one ruled on pictures, and the only mode here
    demoted for being a **duplicate** rather than for being weak: it was the
    strongest weight-1 mode on the tier-4 rate and it is out anyway, because at
    98.7% of a 914-seat gallery it renders the same picture as `smooth` and the
    judge cannot order the two apart. Same treatment as the five: nothing deleted,
    nothing re-keyed, and a leg naming it in `--modes` still draws it.
    """
    for name in ("tail_itinerary", "exp_smoothing"):
        assert mode_policy.weight_of(name) == mode_policy.NICHE
        assert mode_policy.is_accepted(name) is False
        assert name not in mode_policy.seat_floors(1000)
    assert len(mode_policy.niche()) == 6
    assert len(mode_policy.accepted()) == 13
    assert len(mode_policy.strange_modes()) == 12


# --------------------------------------------------------------------------- #
# UNMINED: the second question, and the half of `accepted` that still answers it.
# --------------------------------------------------------------------------- #
def test_the_unmined_ruling_and_what_it_leaves_alone() -> None:
    """`curvature` is out of the mines and in the gallery. Matt's ruling, 2026-09-06.

    The ruling is about **quality** — its pictures are rarely good and the gallery
    only wants a handful — and the whole of it is that no leg buys more. So this
    asserts the standing in both directions at once: gone from `mined`, and every
    other thing an accepted mode has still there. Recording it as a weight of 0
    would have taken the handful away too, which is the mistake this shape exists
    to make impossible.
    """
    assert mode_policy.UNMINED == ("curvature",)
    assert mode_policy.unmined() == ["curvature"]
    assert "curvature" not in mode_policy.mined()
    assert "curvature" in mode_policy.accepted()
    assert mode_policy.is_accepted("curvature") is True
    assert mode_policy.weight_of("curvature") == mode_policy.NORMAL
    assert "curvature" in mode_policy.strange_modes()
    assert mode_policy.seat_floors(200)["curvature"] == 3
    assert mode_policy.seat_floors(1000)["curvature"] == 16


def test_mined_is_accepted_less_the_unmined_and_nothing_else() -> None:
    """Derived, in catalog order, and a partition of `accepted`. A `mined` that
    was its own list is the second table the module exists to prevent."""
    assert set(mode_policy.mined()) | set(mode_policy.unmined()) == set(mode_policy.accepted())
    assert not set(mode_policy.mined()) & set(mode_policy.unmined())
    order = mode_policy.accepted()
    assert mode_policy.mined() == [name for name in order if name in set(mode_policy.mined())]
    assert len(mode_policy.mined()) == 12


@needs_engine
def test_no_mining_roster_can_draw_an_unmined_mode() -> None:
    """The same sweep the niche ruling gets, over the rosters that **buy**.

    The two lists are honoured at different sets of places on purpose, so this is
    a different assertion from the niche one and not a copy of it: a mining roster
    may draw neither, and the seating rosters below still draw an unmined mode.
    """
    from fractal_wallpapers.curation import depth, mine

    out = set(mode_policy.unmined())
    assert out, "there is nothing to exclude, so this proves nothing"
    buying = {
        "the mine": mine._mined_modes(),
        "the depth roster": depth.field_modes(),
        "the dear half of it": depth.dear_modes(),
        "the centered roster": depth.centered_modes(),
    }
    for where, roster in buying.items():
        assert not out & set(roster), f"{where} can still draw {out & set(roster)}"


@needs_engine
def test_an_unmined_mode_is_still_drawn_by_everything_that_seats() -> None:
    """The other half, and the one the niche sweep has no counterpart for.

    `colorize.modes_for` is the two-way split of the roster the seating reads and
    `seat_floors` is computed off it, so an unmined mode leaving it would take the
    gallery's handful with it — which is exactly what the ruling refused.
    """
    from fractal_wallpapers.curation import budget, colorize

    out = set(mode_policy.unmined())
    seating = colorize.modes_for(budget.SMOOTH) + colorize.modes_for(budget.STRANGE)
    assert out <= set(seating), f"{out - set(seating)} left the seating roster"
    assert out <= set(mode_policy.seat_floors(1000))


def test_the_unmined_list_is_checked_against_the_accepted_roster(monkeypatch) -> None:
    """A name in `UNMINED` that is not accepted is a ruling that reads as applied
    and is not — the mode is out of the gallery too, which is the opposite of what
    the list says. `check` refuses rather than ignoring it."""
    monkeypatch.setattr(mode_policy, "UNMINED", ("trap_circle",))
    with pytest.raises(mode_policy.PolicyRefused, match="not accepted modes"):
        mode_policy.check()


def test_the_record_says_which_modes_were_mined_and_which_were_only_seated() -> None:
    """A run's record has to distinguish the two, or a leg read back later cannot
    say whether a mode was absent because nothing drew it or because nothing
    could."""
    read = mode_policy.record()
    assert read["mined"] == mode_policy.mined()
    assert read["unmined"] == mode_policy.unmined()
    assert set(read["mined"]) < set(read["accepted"])
