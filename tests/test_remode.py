"""The re-mode leg: what a twin holds, what the population is, and what it refuses.

Everything here is arithmetic over records, like [`test_mine`] and [`test_hunt`]
and for the same reason: away from the second a render takes, the module is a
`replace` on a recipe, a filter over the ledger and a cut into blocks. So there is
a fake ledger and a fake score sidecar, and never a picture.

The two properties worth pinning hardest are the ones that make the leg honest
rather than the ones that make it work. **A twin holds everything but the mode** —
and it holds it by *never naming* the members it carries, so a member added to
`recipes.Recipe` tomorrow is carried without an edit here. And **the frame is the
source row's own**: this leg re-renders a picture that already exists, so a
framing lookup would move it to a different place, and the guard below is aimed at
a future edit that adds one.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers.curation import (
    candidate_ledger,
    headroom,
    mode_policy,
    recipes,
    remode,
)
from fractal_wallpapers.labeling import finished

VIEWPORT = {"centre_re": "-0.5", "centre_im": "0.1", "width": "0.004", "rotation": 0.0}


# --------------------------------------------------------------------------- #
# Material.
# --------------------------------------------------------------------------- #
def a_recipe(mode="exp_smoothing", colormap="magma", mode_params=None, maxiter=8080):
    """One recipe, in the shape a stored row carries it."""
    return recipes.Recipe(
        family={"kind": "mandelbrot", "degree": 2},
        viewport=dict(VIEWPORT),
        maxiter=int(maxiter),
        regime=recipes.CANDIDATE_REGIME,
        mode=mode,
        mode_params=dict(mode_params or {}),
        curve="linear",
        colormap=colormap,
        palette=finished.recipe(mirror=True),
        autolevel=recipes.live_stamp(mode),
        palette_group=f"map:{colormap}",
    )


def a_source(key="k0", place="p0", score=0.9, p_ge3=None, **over):
    """One [`remode.Source`], its own place unless a test says otherwise."""
    return remode.Source(
        key=key,
        location=place,
        partition="mandelbrot",
        mode="exp_smoothing",
        score=float(score),
        p_ge3=float(score if p_ge3 is None else p_ge3),
        recipe=a_recipe(**over).record(),
    )


def a_stored_row(key, place="p0", mode="exp_smoothing", colormap="magma", **over):
    """One ledger row, thinned to the members [`remode.population`] reads."""
    row = {
        "schema": 1,
        "key": key,
        "partition": "mandelbrot",
        "location": {"key": place},
        "recipe": a_recipe(mode=mode, colormap=colormap).record(),
        "at_candidate_regime": True,
        "picture": f"artifacts/curation/mine/m1/pictures/{key}.jpg",
        "rejected": None,
    }
    row.update(over)
    return row


def a_score(key, p_ge4=0.9, p_ge3=None, artifact="live"):
    return {
        "recipe_key": key,
        "judge_artifact": artifact,
        "p_ge4": p_ge4,
        "p_ge3": p_ge4 if p_ge3 is None else p_ge3,
    }


@pytest.fixture
def store(monkeypatch):
    """A fake ledger and sidecar, wired at the two streaming accessors.

    Redirected at `stream`/`stream_scores` and not at the paths, so no test here
    touches this machine's real 275 MB store — `tests/README.md`'s rule about a
    guard that prices data instead of code.
    """

    def wire(rows, scores, present=None):
        monkeypatch.setattr(candidate_ledger, "stream", lambda *_a, **_k: iter(rows))
        monkeypatch.setattr(candidate_ledger, "stream_scores", lambda *_a, **_k: iter(scores))
        monkeypatch.setattr(candidate_ledger, "live_artifact", lambda *_a, **_k: "live")
        monkeypatch.setattr(
            candidate_ledger,
            "present_pictures",
            lambda held=None, *_a, **_k: (
                {str(row["key"]) for row in (held or [])} if present is None else set(present)
            ),
        )

    return wire


# --------------------------------------------------------------------------- #
# The twin.
# --------------------------------------------------------------------------- #
def test_a_twin_holds_every_keyed_member_but_the_mode():
    """The property the whole leg rests on, and it is checked over
    `recipes.KEYED` rather than over a list written here: a member this test
    named one by one would be a member a future addition could slip past."""
    source = a_recipe(mode="exp_smoothing")
    made = remode.twin(source.record(), "smooth")
    moved = {"mode", "mode_params", "autolevel"}
    for member in recipes.KEYED:
        if member in moved:
            continue
        assert getattr(made, member) == getattr(source, member), member
    for member in recipes.CARRIED:
        assert getattr(made, member) == getattr(source, member), member
    assert made.mode == "smooth" and source.mode == "exp_smoothing"
    # And it is a different picture's name, which is the whole reason the leg
    # renders instead of re-labelling.
    assert recipes.key_of(made) != recipes.key_of(source)


def test_a_twin_empties_the_modes_settings_rather_than_carrying_them():
    """`renders.FIELD_IDENTITY` holds `mode_params`, and the target mode's
    settings space is not the source's — so a carried setting would name a
    picture the engine would not draw. It is also what keeps a twin on the
    shared-field path: `colorize._shared_field` sends a candidate with settings
    down the full render, once per map instead of once per place."""
    source = a_recipe(mode="direct_trap_multiply", mode_params={"opacity": 0.4})
    assert source.mode_params == {"opacity": 0.4}
    assert remode.twin(source.record(), "smooth").mode_params == {}


def test_a_twin_re_derives_the_autolevel_stamp_for_the_target_modes_kind():
    """The stamp is the operator's identity and whether the operator applies is a
    function of the mode's KIND. `field` to `field` carries the same value, which
    is the ordinary case; `field` to `direct` has to drop it, because a stamp a
    kind takes no operator for would name a picture the pipeline cannot make."""
    source = a_recipe(mode="exp_smoothing")
    assert source.autolevel is not None, "a field mode takes the operator"
    assert remode.twin(source.record(), "smooth").autolevel == source.autolevel
    # `direct_trap_screen` is a direct trap: a figure over a flat ground, which
    # `autolevel.applies_to` excludes at the site that decides.
    dropped = remode.twin(source.record(), "direct_trap_screen")
    assert dropped.autolevel == recipes.NO_AUTOLEVEL
    assert dropped.autolevel != source.autolevel


def test_a_twins_key_is_recomputable_off_its_own_record():
    """The invariant every ledger row has to hold: `key_of(of_record(...))` is the
    row's own key, so the store's name for a picture is derived and not trusted."""
    made = remode.twin(a_recipe().record(), "smooth")
    assert recipes.key_of(recipes.of_record(made.record())) == recipes.key_of(made)


def test_the_frame_is_the_source_rows_own_and_never_a_framing_lookup():
    """Aimed at a future edit, not at today's code. A framing index answers *where
    should a fresh candidate be drawn*; adopting a refinement here would move the
    frame and make the twin a different picture at a different place, which is the
    one thing this leg must not do."""
    made = remode.twin(a_recipe(maxiter=12345).record(), "smooth")
    assert remode.frame_of(made) == {"viewport": dict(VIEWPORT), "maxiter": 12345}
    assert remode.place_of(made) == {"family": {"kind": "mandelbrot", "degree": 2}}
    # The guard with teeth: neither function calls one. The docstrings mention
    # `hunt.frame_for` to say why they do not, so the reference is stripped before
    # the body is read — otherwise this passes on the prose that explains itself.
    import inspect

    body = inspect.getsource(remode.frame_of) + inspect.getsource(remode.place_of)
    assert "frame_for" not in body.replace("[`hunt.frame_for`]", "")


# --------------------------------------------------------------------------- #
# The population.
# --------------------------------------------------------------------------- #
def test_the_population_is_one_modes_rows_at_that_modes_own_bar(store):
    rows = [a_stored_row(f"e{at}", place=f"p{at}") for at in range(30)]
    rows += [a_stored_row("s0", place="p0", mode="smooth")]
    scores = [a_score(row["key"]) for row in rows]
    store(rows, scores)
    read = remode.population("exp_smoothing", log=lambda *_a: None)
    assert read["from_mode"] == "exp_smoothing"
    assert read["in_mode"] == 30, "the smooth row is not this leg's population"
    assert len(read["clearing"]) == 30
    assert read["ledger_rows"] == 31
    assert read["known"] == {row["key"] for row in rows}


def test_the_population_takes_its_bar_from_headroom_and_falls_back_the_same_way(store):
    """A mode with too few distinct places over `P(>=4)` clears on `P(>=3)`, which
    is `headroom.rule_of`'s answer and not a constant restated in this module."""
    thin = [a_stored_row(f"e{at}", place=f"p{at}") for at in range(headroom.FALLBACK_LOCATIONS - 1)]
    store(thin, [a_score(row["key"], p_ge4=0.9) for row in thin])
    assert remode.population("exp_smoothing", log=lambda *_a: None)["rule"] == (
        headroom.FALLBACK_COLUMN
    )
    wide = [a_stored_row(f"e{at}", place=f"p{at}") for at in range(headroom.FALLBACK_LOCATIONS)]
    store(wide, [a_score(row["key"], p_ge4=0.9) for row in wide])
    read = remode.population("exp_smoothing", log=lambda *_a: None)
    assert read["rule"] == headroom.DEFAULT_COLUMN
    # And the test is `headroom.clears`, so a row under the bar is out. One row
    # MORE than the fallback count, so dropping one still leaves the rule on the
    # default column — the rule is a count of PLACES over the bar, so a pool cut
    # to exactly the count would fall back and this would be measuring that
    # instead.
    plus = wide + [a_stored_row("low", place="plow")]
    store(plus, [a_score(row["key"], p_ge4=0.9 if row["key"] != "low" else 0.1) for row in plus])
    read = remode.population("exp_smoothing", log=lambda *_a: None)
    assert read["rule"] == headroom.DEFAULT_COLUMN
    assert read["in_mode"] == len(plus)
    assert len(read["clearing"]) == len(plus) - 1
    assert "low" not in {source.key for source in read["clearing"]}


def test_the_population_counts_the_five_exclusions_apart(store):
    """`solve.pool`'s exclusions, and counted apart because they are different
    facts about a row: one was rejected by a person, one carries a score read at
    another geometry, one was never drawn, one was drawn and swept."""
    rows = [
        a_stored_row("keep", place="p0"),
        a_stored_row("rejected", place="p1", rejected={"why": "a person said no"}),
        a_stored_row("off_regime", place="p2", at_candidate_regime=False),
        a_stored_row("no_picture", place="p3", picture=None),
        a_stored_row("no_score", place="p4"),
        a_stored_row("swept", place="p5"),
    ]
    scores = [a_score(key) for key in ("keep", "rejected", "off_regime", "no_picture", "swept")]
    store(rows, scores, present={"keep", "rejected", "off_regime", "no_score"})
    read = remode.population("exp_smoothing", log=lambda *_a: None)
    assert read["refused"] == {
        "rejected": 1,
        "off_regime": 1,
        "no_picture": 1,
        "no_score": 1,
        "picture_absent": 1,
    }
    assert [source.key for source in read["clearing"]] == ["keep"]


def test_a_reading_on_another_judge_is_no_reading_at_all(store):
    """The sidecar is keyed on (recipe, artifact, regime) because a number is
    comparable only inside that triple. A row read by an old judge has no score
    on the live one, which is different from — and more honest than — having an
    old one."""
    rows = [a_stored_row("stale", place="p0")]
    store(rows, [a_score("stale", artifact="an_older_judge")])
    read = remode.population("exp_smoothing", log=lambda *_a: None)
    assert read["refused"]["no_score"] == 1 and read["clearing"] == []


# --------------------------------------------------------------------------- #
# The plan.
# --------------------------------------------------------------------------- #
def test_the_plan_skips_a_twin_the_ledger_already_holds_and_counts_it():
    """Resolved in the parent so the skip count is exact up front, rather than
    three workers racing to discover the same key."""
    sources = [a_source("a", colormap="magma"), a_source("b", colormap="viridis")]
    already = recipes.key_of(remode.twin(sources[0].recipe, "smooth"))
    units, shape = remode.plan_of(sources, "smooth", {already})
    assert shape["already_in_ledger"] == 1
    assert [key for _u, _s, _r, key in units] == [
        recipes.key_of(remode.twin(sources[1].recipe, "smooth"))
    ]


def test_the_plan_numbers_k_per_location_and_not_across_the_leg():
    """`k` is which twin at its own place this was, the same thing a mine's `k`
    counts — a reader correcting a winner's-curse estimate needs the per-place
    index and never a leg-wide counter."""
    sources = [
        a_source("a", place="p0", colormap="magma"),
        a_source("b", place="p0", colormap="viridis"),
        a_source("c", place="p1", colormap="magma"),
    ]
    units, shape = remode.plan_of(sources, "smooth", set())
    assert [unit.k for unit, *_rest in units] == [1, 2, 1]
    assert shape["source_locations"] == shape["twin_locations"] == 2
    assert {unit.mode for unit, *_rest in units} == {"smooth"}
    # The source mode rides on `band`, which is the mine's word for the prior a
    # draw was taken under — so a mine's readouts read this leg unedited.
    assert {unit.band for unit, *_rest in units} == {"exp_smoothing"}
    assert {unit.arm for unit, *_rest in units} == {remode.UNIT}


def test_an_unreadable_stored_recipe_is_counted_and_never_raised():
    """A stored recipe missing a member names no picture, so it names no twin
    either. One bad row of several thousand is not a reason to render none."""
    broken = a_source("bad")
    broken = remode.Source(**{**broken.__dict__, "recipe": {"mode": "exp_smoothing"}})
    units, shape = remode.plan_of([broken, a_source("good")], "smooth", set())
    assert shape["unresolvable"] == 1 and len(units) == 1


def test_the_plan_is_cut_at_the_location_so_one_field_is_dumped_per_place():
    """One field is dumped per (location, mode) and every map at that pair is a
    recolour of it. A plan cut per candidate would hand one place to three
    workers and pay the dump three times, which comes out slower than serial."""
    sources = [a_source(f"a{at}", place="p0", colormap=f"m{at}") for at in range(4)]
    sources += [a_source("b", place="p1")]
    units, _shape = remode.plan_of(sources, "smooth", set())
    blocks = remode.blocks_of(units)
    assert [len(block) for block in blocks] == [4, 1]
    for block in blocks:
        assert len({unit.location for _at, (unit, *_rest) in block}) == 1


# --------------------------------------------------------------------------- #
# What it refuses.
# --------------------------------------------------------------------------- #
def test_a_target_mode_the_project_has_stopped_buying_is_refused():
    """The whole point of the leg. A twin in a second weight-0 mode would leave
    `solve.pool` exactly the way its source did — for the full render cost."""
    # Any weight-0 mode other than the source, since rendering a mode into
    # itself is refused first and for a different reason.
    niche = [name for name in mode_policy.niche() if name != "exp_smoothing"]
    assert niche, "the ruling this leg exists for put at least one other mode here"
    with pytest.raises(remode.RemodeRefused, match="MODE_POLICY"):
        remode.run("t", from_mode="exp_smoothing", to_mode=niche[0], log=lambda *_a: None)


def test_rendering_a_mode_into_itself_is_refused():
    with pytest.raises(remode.RemodeRefused, match="already in"):
        remode.run("t", from_mode="smooth", to_mode="smooth", log=lambda *_a: None)


def test_a_population_read_for_another_mode_is_refused():
    """A leg rendering one mode's rows, selected under another mode's bar, would
    report a clearing rate about neither."""
    world = {
        "from_mode": "tia",
        "rule": headroom.DEFAULT_COLUMN,
        "clearing": [],
        "known": set(),
        "in_mode": 0,
        "refused": {},
        "ledger_rows": 0,
        "seconds": 0.0,
    }
    with pytest.raises(remode.RemodeRefused, match="was read for"):
        remode.run(
            "t",
            from_mode="exp_smoothing",
            to_mode="smooth",
            world=world,
            rule=headroom.DEFAULT_COLUMN,
            log=lambda *_a: None,
        )


def test_merging_a_leg_that_made_nothing_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(remode, "remode_dir", lambda name: tmp_path / str(name))
    (tmp_path / "t").mkdir()
    with pytest.raises(remode.RemodeRefused, match="nothing to merge"):
        remode.merge("t", log=lambda *_a: None)


# --------------------------------------------------------------------------- #
# The readout.
# --------------------------------------------------------------------------- #
def made_row(key, p_ge4, from_p_ge4, *, place="p0", partition="mandelbrot", rule="p_ge4"):
    clears = remode._clears(p_ge4, p_ge4, rule)
    return {
        "key": key,
        "location": place,
        "partition": partition,
        "p_ge4": p_ge4,
        "p_ge3": p_ge4,
        "from_p_ge4": from_p_ge4,
        "delta": round(p_ge4 - from_p_ge4, 6),
        "clears": clears,
        "crossed": clears != remode._clears(from_p_ge4, from_p_ge4, rule),
        "seconds": 1.0,
        "acted": False,
    }


def test_the_readout_reports_the_crossings_in_both_directions():
    """Both directions, and the upward one is the **assertion** rather than a
    measurement: on a real population every source is in the plan because it
    cleared, so `crossed_up` is zero by construction and a non-zero one means a
    source that did not clear got in. The `gained` row below cannot occur in a
    real leg, which is exactly why the function has to be able to count it."""
    made = [
        made_row("held", 0.90, 0.88),
        made_row("lost", 0.40, 0.60, place="p1"),
        made_row("gained", 0.60, 0.40, place="p2"),
    ]
    read = remode.carry_readout(made)
    assert read["made"] == 3 and read["clearing"] == 2
    assert read["crossed_down"] == 1 and read["crossed_up"] == 1
    assert read["locations"] == 3 and read["clearing_locations"] == 2
    assert read["delta"]["higher"] == 2 and read["delta"]["lower"] == 1
    assert read["by_partition"]["mandelbrot"] == {"made": 3, "clearing": 2, "seconds": 3.0}
    assert remode.carry_readout([]) == {"made": 0}


def test_the_legs_own_clearing_test_is_headrooms(store):
    """`_clears` takes two bare numbers because a twin is judged before any row
    exists for it. It has to be the same answer `headroom.clears` gives, or the
    leg's clearing rate and the pool's population would be two different bars."""
    assert remode._clears(0.5, 0.0, headroom.DEFAULT_COLUMN) is True
    assert remode._clears(0.49, 0.99, headroom.DEFAULT_COLUMN) is False
    assert remode._clears(0.0, 0.5, headroom.FALLBACK_COLUMN) is True
    assert remode._clears(0.99, 0.49, headroom.FALLBACK_COLUMN) is False
    source = a_source(score=0.5)
    assert headroom.clears(source, headroom.DEFAULT_COLUMN) is True
    assert remode._clears(source.score, source.p_ge3, headroom.DEFAULT_COLUMN) is True


# --------------------------------------------------------------------------- #
# The subtree.
# --------------------------------------------------------------------------- #
def test_the_legs_pictures_are_reachable_by_the_orphan_sweep():
    """Not a spelling check. `candidate_ledger.orphans` enumerates
    `POOL_SUBTREES` and no other names, so a leg whose subtree is missing from it
    leaves a killed run's pictures on disk with no row anywhere and nothing in
    the project able to find them."""
    assert remode.UNIT in candidate_ledger.POOL_SUBTREES
    assert remode.pictures_dir("leg").name == candidate_ledger.PICTURES_NAME
    assert remode.pictures_dir("leg").parent.parent.name == remode.UNIT
