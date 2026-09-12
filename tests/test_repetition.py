"""The repeat batch: what the pair holds, what the draw is, and what the card says.

Arithmetic over records, like [`test_remode`] and for its reason: away from the
render the module is a filter over the ledger, a seeded draw and a `dict` per
tile. So there is a fake ledger and a fake sidecar, and never a picture.

Three properties are worth pinning hardest, and none of them is *it works*.

**The pair differs in the traversal and in nothing else**, and it is provable
rather than promised — `plan_of` re-derives each control's own key through the
call that made it and drops a control that does not reproduce. **The card prints
the traversal count and not `cycles`**, which are different numbers on a folded
map and the same on a cyclic one. And **nothing gates**: a bar of any kind here
would select the repeats the current heads already tolerate, which is the sample
the sitting exists to avoid.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers.curation import candidate_ledger, colorize, recipes, repetition
from fractal_wallpapers.labeling import finished

VIEWPORT = {"centre_re": "-0.5", "centre_im": "0.1", "width": "0.004", "rotation": 0.0}

#: A cyclic map and a sequential one, named rather than drawn — a map that
#: changed kind under these tests would make them pass for the wrong reason, and
#: `test_the_named_maps_are_still_the_kinds_these_tests_need` is the pin.
A_CYCLIC_MAP = "twilight_shifted"
A_FOLDED_MAP = "cubehelix"


# --------------------------------------------------------------------------- #
# Material.
# --------------------------------------------------------------------------- #
def a_recipe(mode="smooth", colormap=A_CYCLIC_MAP, cycles=1.0, phase=0.0, mode_params=None):
    return recipes.Recipe(
        family={"kind": "mandelbrot", "degree": 2},
        viewport=dict(VIEWPORT),
        maxiter=8080,
        regime=recipes.CANDIDATE_REGIME,
        mode=mode,
        mode_params=dict(mode_params or {}),
        curve=colorize.CURVE,
        colormap=colormap,
        palette=finished.recipe(
            mirror=colormap == A_FOLDED_MAP, cycles=float(cycles), phase=float(phase)
        ),
        autolevel=recipes.live_stamp(mode),
        palette_group=f"map:{colormap}",
    )


def a_row(key, place="p0", **over):
    row = {
        "schema": 1,
        "key": key,
        "partition": "mandelbrot",
        "location": {"key": place},
        "recipe": a_recipe(**{k: v for k, v in over.items() if k in _RECIPE_KNOBS}).record(),
        "at_candidate_regime": True,
        "picture": f"artifacts/curation/mine/m1/pictures/{key}.jpg",
        "rejected": None,
    }
    row.update({k: v for k, v in over.items() if k not in _RECIPE_KNOBS})
    return row


_RECIPE_KNOBS = {"mode", "colormap", "cycles", "phase", "mode_params"}


def a_score(key, p_ge4=0.9, artifact="live"):
    return {"recipe_key": key, "judge_artifact": artifact, "p_ge4": p_ge4, "p_ge3": p_ge4}


def a_control(key="k0", place="p0", folded=False, p_fine=0.5, **over):
    colormap = A_FOLDED_MAP if folded else A_CYCLIC_MAP
    return repetition.Control(
        key=key,
        location=place,
        partition="mandelbrot",
        mode=over.pop("mode", "smooth"),
        colormap=colormap,
        folded=folded,
        picture=f"artifacts/curation/mine/m1/pictures/{key}.jpg",
        p_ge4=0.9,
        p_ge3=0.95,
        p_fine=p_fine,
        recipe=a_recipe(colormap=colormap, **over).record(),
    )


@pytest.fixture(autouse=True)
def _one_read_of_the_cyclic_set(monkeypatch, shipped_cyclic_maps):
    """The tracked cyclic set, read once for the file rather than once per test.

    Every recipe built here resolves the fold off the map's kind, and that read
    parses the whole colormap library — see [`conftest.shipped_cyclic_maps`] for
    the measurement. The answer is the real one; what changes is how often the
    disk is asked for it.
    """
    monkeypatch.setattr(colorize, "cyclic", lambda: set(shipped_cyclic_maps))


@pytest.fixture
def store(monkeypatch):
    """A fake ledger and sidecar, wired at the two streaming accessors.

    [`test_remode.store`]'s arrangement and its reason: redirected at `stream` and
    `stream_scores` rather than at the paths, so nothing here reads this machine's
    real store.
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
        monkeypatch.setattr(repetition, "_fine_column", lambda *_a, **_k: {})

    return wire


def test_the_named_maps_are_still_the_kinds_these_tests_need() -> None:
    cyclic = colorize.cyclic()
    assert A_CYCLIC_MAP in cyclic
    assert A_FOLDED_MAP not in cyclic


# --------------------------------------------------------------------------- #
# The traversal count, which is the number the card prints.
# --------------------------------------------------------------------------- #
def test_a_folded_map_is_walked_twice_per_cycle_and_a_cyclic_one_once() -> None:
    """`cycles` and the traversal count are the same number on a cyclic map and
    different numbers on a folded one, which is the whole reason the card prints
    this rather than the value the row records."""
    assert repetition.traversals(1.0, folded=False) == 1.0
    assert repetition.traversals(2.0, folded=False) == 2.0
    assert repetition.traversals(3.0, folded=False) == 3.0
    assert repetition.traversals(1.0, folded=True) == 2.0
    assert repetition.traversals(2.0, folded=True) == 4.0


def test_the_folded_arms_one_rung_is_four_passes_of_the_base_ramp() -> None:
    """Which is why it is the smallest rung that means anything there: a folded
    map at cycles 1 is already an out-and-back."""
    assert repetition.FOLDED_RUNGS == (2.0,)
    assert repetition.traversals(repetition.FOLDED_RUNGS[0], folded=True) == 4.0


# --------------------------------------------------------------------------- #
# The population, and the five exclusions that are about pairing.
# --------------------------------------------------------------------------- #
def test_the_population_applies_no_bar_of_any_kind(store) -> None:
    """The one property this leg cannot trade: a bar would select the repeats the
    current heads already tolerate, which is the sample it exists to avoid."""
    rows = [a_row(f"k{index}", place=f"p{index}") for index in range(5)]
    store(rows, [a_score(f"k{index}", p_ge4=index / 100) for index in range(5)])
    world = repetition.population(log=lambda _m: None)
    assert len(world["controls"]) == 5
    # Including the one the render judge scores at 0.00, which every other draw
    # in this project would have cut before building a candidate out of it.
    assert min(control.p_ge4 for control in world["controls"]) == 0.0


def test_the_population_counts_its_exclusions_apart(store) -> None:
    rows = [
        a_row("keep", place="p0"),
        a_row("trap", place="p1", mode="direct_trap_ring"),
        a_row("repeated", place="p2", cycles=2.0),
        a_row("rotated", place="p3", phase=0.25),
        a_row("rejected", place="p4", rejected={"by": "matt"}),
        a_row("offregime", place="p5", at_candidate_regime=False),
        a_row("nopicture", place="p6", picture=None),
    ]
    store(rows, [a_score(row["key"]) for row in rows])
    world = repetition.population(log=lambda _m: None)
    assert [control.key for control in world["controls"]] == ["keep"]
    assert world["refused"] == {
        "direct_trap": 1,
        "already_repeated": 1,
        "rotated": 1,
        "off_regime": 1,
        "rejected": 1,
        "no_picture": 1,
        "picture_absent": 0,
        "no_score": 0,
    }
    # `known` is every key the store holds, the excluded ones included: it is what
    # the plan dedupes against and a repeat can land on a row this leg refused.
    assert world["known"] == {row["key"] for row in rows}


def test_a_rotated_row_is_not_a_control(store) -> None:
    """1,713 of the store's 2,262 repeat rows carry a rotation too, so a batch
    that took rotated controls would confound this axis with the one
    `curate rotate` just measured and answer neither."""
    store([a_row("spun", phase=0.5)], [a_score("spun")])
    world = repetition.population(log=lambda _m: None)
    assert world["controls"] == []
    assert world["refused"]["rotated"] == 1


# --------------------------------------------------------------------------- #
# The draw.
# --------------------------------------------------------------------------- #
def a_world(folded=40, cyclic=200):
    controls = [
        a_control(key=f"f{index}", place=f"fp{index}", folded=True) for index in range(folded)
    ] + [a_control(key=f"c{index}", place=f"cp{index}", folded=False) for index in range(cyclic)]
    return {"controls": controls, "known": set()}


def test_the_folded_arm_gets_its_own_share_and_not_the_pools() -> None:
    """Sequential maps are 15.3% of the library and thinner above any bar, so
    letting the pool decide would put a handful of them on a 250-tile page."""
    pairs, shape = repetition.draw(a_world(), tiles=250, seed=1)
    assert shape["pairs"] == 125
    assert shape["tiles"] == 250
    assert shape["folded_pairs"] == 40
    assert shape["cyclic_pairs"] == 85
    assert shape["folded_share_drawn"] == 0.32
    assert shape["folded_share_in_the_library"] == 0.1528
    assert sum(1 for pair in pairs if pair.control.folded) == 40


def test_the_cyclic_rungs_are_dealt_evenly_rather_than_sampled() -> None:
    """A multinomial over two rungs at n=85 lands eight apart about a third of the
    time, and a rung comparison is what the page is for."""
    pairs, shape = repetition.draw(a_world(), tiles=250, seed=7)
    counts = shape["by_arm_and_rung"]
    assert counts["folded"] == {"2": 40}
    assert sorted(counts["cyclic"].values()) == [42, 43]
    assert {pair.rung for pair in pairs if pair.control.folded} == {2.0}
    assert {pair.rung for pair in pairs if not pair.control.folded} == {2.0, 3.0}


def test_the_draw_takes_one_pair_a_location() -> None:
    """No place may carry the page, so a location is drawn once whichever arm it
    lands in and the two arms never share one."""
    pairs, _shape = repetition.draw(a_world(), tiles=250, seed=3)
    places = [pair.control.location for pair in pairs]
    assert len(places) == len(set(places))


def test_the_same_seed_draws_the_same_batch() -> None:
    first, _ = repetition.draw(a_world(), tiles=60, seed=11)
    second, _ = repetition.draw(a_world(), tiles=60, seed=11)
    other, _ = repetition.draw(a_world(), tiles=60, seed=12)
    assert [pair.control.key for pair in first] == [pair.control.key for pair in second]
    assert [pair.rung for pair in first] == [pair.rung for pair in second]
    assert [pair.control.key for pair in first] != [pair.control.key for pair in other]


def test_a_thin_folded_arm_is_reported_short_rather_than_topped_up_from_the_other() -> None:
    """The share is a claim about what the page holds. Filling it with cyclic
    pairs would leave the record saying 32% of a sample that has none."""
    pairs, shape = repetition.draw(a_world(folded=5, cyclic=200), tiles=250, seed=1)
    assert shape["folded_pairs"] == 5
    assert shape["cyclic_pairs"] == 120
    assert shape["folded_share_drawn"] == 0.04
    assert sum(1 for pair in pairs if pair.control.folded) == 5


# --------------------------------------------------------------------------- #
# The plan: the pair is matched, and it is checked rather than promised.
# --------------------------------------------------------------------------- #
class _Maker:
    """[`hunt.Maker`]'s two members the plan uses, with no judge and no band."""

    def __init__(self, cyclic=None):
        self.cyclic = colorize.cyclic() if cyclic is None else set(cyclic)

    def recipe_for(self, plan, place, frame):
        from fractal_wallpapers.palettes import groups as groups_module

        drawn = dict(getattr(plan, "palette", None) or {})
        return recipes.Recipe(
            family=place["family"],
            viewport=frame["viewport"],
            maxiter=int(frame["maxiter"]),
            regime=recipes.CANDIDATE_REGIME,
            mode=plan.mode,
            mode_params=dict(plan.mode_params or {}),
            curve=colorize.CURVE,
            colormap=plan.colormap,
            palette=finished.recipe(mirror=plan.colormap not in self.cyclic, **drawn),
            autolevel=recipes.live_stamp(plan.mode),
            palette_group=groups_module.group_of(plan.colormap, {}),
        )


def a_pair(control, rung=2.0, name="p0000"):
    return repetition.Pair(control=control, rung=float(rung), pair=name)


def keyed(control):
    """The key a control's own recipe digests to, as the store would hold it."""
    return recipes.key_of(recipes.of_record(control.recipe))


def test_the_repeat_differs_from_its_control_in_the_traversal_and_nothing_else() -> None:
    """Checked over `recipes.KEYED` rather than over a list written here, so a
    member added to `Recipe` tomorrow is covered without an edit."""
    control = a_control()
    control = repetition.Control(**{**control.__dict__, "key": keyed(control)})
    units, shape = repetition.plan_of(
        _Maker(), [a_pair(control, rung=3.0)], set(), log=lambda _m: None
    )
    assert shape["controls_that_did_not_reproduce"] == 0
    _unit, _pair, _place, _frame, _key, twin = units[0]
    mine_side = recipes.of_record(control.recipe)
    for member in recipes.KEYED:
        if member == "palette":
            continue
        assert getattr(twin, member) == getattr(mine_side, member), member
    assert twin.palette == {**mine_side.palette, "cycles": 3.0}


def test_a_control_whose_key_does_not_reproduce_is_dropped_and_counted() -> None:
    """It means the row was made by some other path — a `label_migration` recipe
    carries knobs the candidate path never spends — so its repeat would differ in
    the traversal AND in whatever else that path moved."""
    good = a_control(key="k0", place="p0")
    good = repetition.Control(**{**good.__dict__, "key": keyed(good)})
    stray = a_control(key="not-the-key-this-recipe-digests-to", place="p1")
    units, shape = repetition.plan_of(
        _Maker(), [a_pair(good), a_pair(stray, name="p0001")], set(), log=lambda _m: None
    )
    assert len(units) == 1
    assert shape["controls_that_did_not_reproduce"] == 1
    assert shape["the_ones_that_did_not_reproduce"] == [stray.key]


def test_a_repeat_the_ledger_already_holds_is_not_rendered_and_stays_on_the_page() -> None:
    """2,262 rows already carry a traversal, so a draw landing on one is a tile
    this leg gets free rather than a pair it loses."""
    control = a_control()
    control = repetition.Control(**{**control.__dict__, "key": keyed(control)})
    pair = a_pair(control)
    units, shape = repetition.plan_of(_Maker(), [pair], set(), log=lambda _m: None)
    key = shape["repeat_keys"][pair.pair]
    assert len(units) == 1

    units, shape = repetition.plan_of(_Maker(), [pair], {key}, log=lambda _m: None)
    assert units == []
    assert shape["repeats_already_in_ledger"] == 1
    # Still keyed, so the sheet can still put both tiles on the page.
    assert shape["repeat_keys"][pair.pair] == key


def test_a_folded_control_keeps_its_fold_through_the_repeat() -> None:
    """`mirror` is the map's bake and not a knob a draw turns — `hunt.Maker`
    refuses an intention that names it — so the repeat is folded because its map
    is, on both sides of the pair."""
    control = a_control(folded=True)
    control = repetition.Control(**{**control.__dict__, "key": keyed(control)})
    units, _shape = repetition.plan_of(_Maker(), [a_pair(control)], set(), log=lambda _m: None)
    _unit, _pair, _place, _frame, _key, twin = units[0]
    assert twin.palette["mirror"] is True
    assert twin.palette["cycles"] == 2.0
    assert twin.colormap == A_FOLDED_MAP


# --------------------------------------------------------------------------- #
# The card.
# --------------------------------------------------------------------------- #
def test_an_unread_column_is_a_word_on_the_card_and_never_a_zero() -> None:
    """A number on a card is a claim. A defaulted zero under a repeat the pool
    scores well would have the page arguing the opposite of the truth at exactly
    the tile the sitting is about."""
    assert repetition._spell(None) == "—"
    assert repetition._spell(0.0) == "0"
    assert repetition._spell(0.123456) == "0.1235"


def test_the_card_keeps_four_SIGNIFICANT_figures_and_not_four_decimals() -> None:
    """`p_coarse` has a median of 0.0025 over this population, so `.4f` printed
    0.0000 under most of the batch — and under both halves of a pair whose two
    readings differ by a factor of ten, which is the comparison the card is for."""
    assert repetition._spell(0.002475) == "0.002475"
    assert repetition._spell(0.0002475) == "0.0002475"
    assert repetition._spell(0.8140) == "0.814"


def test_the_card_prints_the_traversal_count_and_names_the_arm() -> None:
    line = repetition.CARD.format(
        which="repeat", traversals=repetition.traversals(2.0, True), fine="0.4000", coarse="—"
    )
    assert line == "repeat · 4x · p_fine 0.4000 · p_coarse —"


# --------------------------------------------------------------------------- #
# The readings a card prints come off the shape a score row really has.
# --------------------------------------------------------------------------- #
def test_the_repeats_readings_come_off_the_score_rows_top_level(tmp_path, monkeypatch) -> None:
    """`candidate_ledger.score_row` spreads the judge's columns at the top level.

    Reading them from a nested `read` block returned None for every repeat and
    defaulted the card to 0.0000 under all 123 of `repeat_ckpt120`'s pairs —
    which is the false number `repeat_readings`' second pass exists to prevent,
    arrived at from the other side. A page that prints a defaulted zero under the
    exact tile a sitting is about argues the opposite of the truth.
    """
    monkeypatch.setattr(repetition, "repetition_dir", lambda name: tmp_path / str(name))
    row = candidate_ledger.score_row(
        key="k0",
        artifact="live",
        regime="640x360ss2",
        head="strange",
        read={"p_ge2": 0.8, "p_ge3": 0.35, "p_ge4": 0.002475, "rank_score": 0.1},
        source={"run": "a_leg", "candidate": "00001"},
    )
    path = repetition.scores_path("a_batch")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(__import__("json").dumps(row) + "\n", encoding="utf-8", newline="\n")

    readings = repetition.repeat_readings("a_batch", {"k0"}, log=lambda _m: None)
    assert readings["k0"] == {"p_ge4": 0.002475, "p_ge3": 0.35}
    assert repetition._spell(readings["k0"]["p_ge4"]) == "0.002475"


def test_a_score_row_with_no_columns_is_refused_rather_than_defaulted(tmp_path, monkeypatch):
    monkeypatch.setattr(repetition, "repetition_dir", lambda name: tmp_path / str(name))
    path = repetition.scores_path("a_batch")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"recipe_key": "k0", "read": {"p_ge4": 0.5}}\n', encoding="utf-8")
    with pytest.raises(repetition.RepetitionRefused, match="p_ge4"):
        repetition.repeat_readings("a_batch", {"k0"}, log=lambda _m: None)


# --------------------------------------------------------------------------- #
# The sweep has to be able to reach this leg's pictures.
# --------------------------------------------------------------------------- #
def test_this_legs_subtree_is_one_the_orphan_sweep_walks() -> None:
    """A picture with no ledger row is garbage and there is a sweep for it —
    `curate candidate-ledger orphans` — and it looks at `<subtree>/<leg>/pictures`
    for the subtrees named here and nowhere else. This leg merges through the
    ordinary door, and the door PRUNES, so some of what it renders is deleted in
    the same act that admits it: a batch killed between its render and its merge
    leaves 125 pictures named by nothing."""
    assert repetition.UNIT in candidate_ledger.POOL_SUBTREES
    assert repetition.pictures_dir("a_batch").name == candidate_ledger.PICTURES_NAME
    assert repetition.pictures_dir("a_batch").parent.parent.name == repetition.UNIT
