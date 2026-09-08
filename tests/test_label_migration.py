"""Staging the judged recipes at candidate geometry.

Three things here and they fail differently.

**The derivation** is the whole claim of the leg: the same recipe, with the
geometry changed and nothing else. What is pinned is the "nothing else" — every
keyed member but the regime comes back identical to the label row's, the regime
comes back as `recipes.CANDIDATE_REGIME` whatever the row said, and the key is a
function of that and therefore recomputable. A derivation that quietly spent the
candidate path's own curve or palette would produce a *different* picture under a
name that says it is the judged one, so those are asserted member by member.

**The override door** is the change this leg needed in shipped code, and its
danger is the field cache: a dumped field is named for its curve and `recolored`
pins the palette to the plain recipe, so a recolour under an override would be
the plain picture wearing the override's name. `render` refuses the pair rather
than serving it, and that refusal is what is pinned.

**Everything else is arithmetic** — the store's paths, the shape of a
distribution, the sort the page is in — and can only be wrong about counting.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.curation import colorize, label_migration, recipes


def quiet(*_args, **_rest) -> None:
    """A `log` that says nothing."""


def label_row(**over) -> dict:
    """One finished-render row, in the shape both stores hold.

    Deliberately **not** a plain candidate recipe: a `log` curve and two palette
    knobs the candidate path never sets, because that is the half of the corpora
    the derivation exists for and a fixture that used the defaults would pass
    while the override was dropped on the floor.
    """
    row = {
        "schema": 1,
        "batch": "a_batch",
        "recorded_at": "2026-09-01T00:00:00",
        "labeler": None,
        "origin": "human",
        "score": 4,
        "family": {"kind": "multibrot", "degree": 3},
        "viewport": {"center_re": "-0.5", "center_im": "0.6", "width": "1e-05"},
        "mode": "smooth",
        "mode_params": {},
        "curve": "log",
        "colormap": "cmr.voltage",
        "recipe": {
            "gamma": 0.75,
            "cycles": 2.0,
            "phase": 0.0,
            "reverse": False,
            "mirror": True,
            "transfer": {"kind": "value"},
            "rolloff": {"kind": "none"},
        },
        "render": {"resolution": [1280, 720], "supersample": 2, "maxiter": 4096},
        "partition": "multibrot3",
    }
    row.update(over)
    return row


# --------------------------------------------------------------------------- #
# The derivation.
# --------------------------------------------------------------------------- #
def test_the_derived_recipe_moves_the_geometry_and_nothing_else():
    row = label_row()
    derived = label_migration.recipe_of(row, None, {})
    assert derived.regime == recipes.CANDIDATE_REGIME
    assert derived.regime.spelled == "640x360ss2"
    # Every other keyed member is the row's own, member by member.
    assert derived.family == row["family"]
    assert derived.viewport == row["viewport"]
    assert derived.maxiter == row["render"]["maxiter"]
    assert derived.mode == row["mode"]
    assert derived.mode_params == row["mode_params"]
    assert derived.curve == row["curve"] == "log"
    assert derived.colormap == row["colormap"]
    assert derived.palette == row["recipe"]


def test_the_derived_recipe_does_not_take_the_candidate_paths_curve_or_palette():
    """The failure the override exists to prevent, stated as its own guard.

    A derivation that spent `colorize.CURVE` and the plain recipe would hand back
    a recipe for a picture nobody judged, keyed under a name that says otherwise.
    """
    derived = label_migration.recipe_of(label_row(), None, {})
    assert derived.curve != colorize.CURVE
    assert derived.palette != colorize._plain_recipe(True)


def test_the_derived_key_is_recomputable_from_the_stored_recipe():
    derived = label_migration.recipe_of(label_row(), None, {})
    key = recipes.key_of(derived)
    assert key == recipes.key_of(recipes.of_record(derived.record()))


def test_the_label_regime_never_reaches_the_derived_key():
    """Two rows differing only in the geometry they were judged at derive one key."""
    at_label = label_migration.recipe_of(label_row(), None, {})
    elsewhere = label_migration.recipe_of(
        label_row(render={"resolution": [1920, 1080], "supersample": 3, "maxiter": 4096}),
        None,
        {},
    )
    assert recipes.key_of(at_label) == recipes.key_of(elsewhere)


def test_a_different_maxiter_is_a_different_picture():
    """maxiter is geometry-adjacent and is NOT normalized: it decides pixels."""
    mine = label_migration.recipe_of(label_row(), None, {})
    deeper = label_migration.recipe_of(
        label_row(render={"resolution": [1280, 720], "supersample": 2, "maxiter": 8192}), None, {}
    )
    assert recipes.key_of(mine) != recipes.key_of(deeper)


def test_the_place_is_spelled_the_way_every_store_here_spells_one():
    derived = label_migration.recipe_of(label_row(), None, {})
    place = label_migration._location_of(derived)
    assert isinstance(place, str)
    assert json.loads(place)[0] == "multibrot3"


# --------------------------------------------------------------------------- #
# The override door.
# --------------------------------------------------------------------------- #
def test_render_row_spends_the_candidate_default_unless_asked():
    plain = colorize.render_row(
        {"family": {}, "viewport": {}, "maxiter": 8},
        "smooth",
        "cmr.voltage",
        set(),
        render={"resolution": [8, 8], "supersample": 1, "maxiter": 8},
    )
    assert plain["curve"] == colorize.CURVE
    assert plain["recipe"] == colorize._plain_recipe(True)


def test_render_row_takes_the_override_when_it_is_given():
    palette = {
        "gamma": 0.5,
        "cycles": 3.0,
        "phase": 0.25,
        "reverse": True,
        "mirror": False,
        "transfer": {"kind": "value"},
        "rolloff": {"kind": "none"},
    }
    overridden = colorize.render_row(
        {"family": {}, "viewport": {}, "maxiter": 8},
        "smooth",
        "cmr.voltage",
        set(),
        render={"resolution": [8, 8], "supersample": 1, "maxiter": 8},
        curve="log",
        palette=palette,
    )
    assert overridden["curve"] == "log"
    assert overridden["recipe"] == palette


def test_an_override_refuses_the_field_cache(tmp_path):
    """The one way the override could make a wrong picture, refused before any engine.

    A dumped field is named for its curve and `recolored` pins the palette, so a
    recolour under an override is the plain picture under the override's name.
    """
    with pytest.raises(RuntimeError, match="field cache"):
        colorize.render(
            {"family": {}, "viewport": {}, "maxiter": 8},
            "smooth",
            "cmr.voltage",
            set(),
            tmp_path / "out.jpg",
            fields=tmp_path / "fields",
            curve="log",
        )


# --------------------------------------------------------------------------- #
# The store, and the arithmetic over it.
# --------------------------------------------------------------------------- #
def test_a_relative_store_lands_under_the_checkout(tmp_path):
    from fractal_wallpapers.paths import repo_root

    assert label_migration.store_root("scratch/somewhere") == repo_root() / "scratch/somewhere"
    assert label_migration.store_root(tmp_path) == tmp_path


def test_the_default_store_is_under_the_ignored_tree():
    """`scratch/` and never `artifacts/`: nothing in the pipeline may find these rows."""
    assert label_migration.DEFAULT_STORE.parts[0] == "scratch"


def test_a_stage_that_has_not_run_refuses_by_name(tmp_path):
    with pytest.raises(label_migration.MigrationError, match="run the stage that writes it"):
        label_migration.readout(tmp_path, log=quiet)


def test_the_shape_of_a_distribution_is_its_own_arithmetic():
    read = label_migration._quantiles([0.0, 0.25, 0.5, 0.75, 1.0])
    assert read["n"] == 5
    assert read["min"] == 0.0
    assert read["max"] == 1.0
    assert read["median"] == 0.5
    assert read["mean"] == 0.5


def test_an_empty_column_says_so_rather_than_averaging_nothing():
    assert label_migration._quantiles([]) == {"n": 0}


def test_the_partition_is_taken_from_whichever_verdict_carries_one():
    assert label_migration._partition_of([{"partition": None}, {"partition": "julia"}]) == "julia"
    assert label_migration._partition_of([{"partition": None}]) is None


def test_the_page_writes_both_sides_at_one_width():
    """Otherwise the pair is a comparison of two sizes wearing one caption."""
    assert label_migration.PAGE_WIDTH == 640


# --------------------------------------------------------------------------- #
# Expressibility: which judged recipes the candidate path could produce at all.
# --------------------------------------------------------------------------- #
def _derived(key: str, plain: bool, head: str, score: int, **recipe) -> dict:
    """One `recipes.jsonl` row, thinned to what [`expressibility`] reads."""
    palette = dict(finished_recipe())
    palette.update(recipe.pop("palette", {}))
    return {
        "key": key,
        "plain_candidate_recipe": plain,
        "recipe": {
            "colormap": recipe.pop("colormap", "not_a_cyclic_map"),
            "curve": recipe.pop("curve", colorize.CURVE),
            "palette": palette,
        },
        "labels": [{"head": head, "score": score}],
    }


def finished_recipe() -> dict:
    """The plain candidate palette for a map production folds."""
    from fractal_wallpapers.labeling import finished

    return finished.recipe(mirror=True)


def test_expressibility_counts_verdicts_by_class_and_by_store():
    read = label_migration.expressibility(
        {
            "a": _derived("a", True, "smooth_render", 4),
            "b": _derived("b", False, "smooth_render", 4, palette={"gamma": 0.5}),
            "c": _derived("c", False, "strange_render", 2, palette={"gamma": 0.5}),
        },
        cyclic=set(),
        log=quiet,
    )
    assert read["expressible"] == 1
    assert read["not_expressible"] == 2
    assert read["by_label_class"]["smooth_render/4"] == {"expressible": 1, "not_expressible": 1}
    assert read["by_store"]["strange_render"] == {"expressible": 0, "not_expressible": 1}


def test_the_label_4_count_is_reported_per_store_and_summed():
    read = label_migration.expressibility(
        {
            "a": _derived("a", False, "smooth_render", 4, palette={"gamma": 0.5}),
            "b": _derived("b", False, "strange_render", 4, palette={"gamma": 0.5}),
            "c": _derived("c", False, "strange_render", 3, palette={"gamma": 0.5}),
        },
        cyclic=set(),
        log=quiet,
    )
    held = read["label_4_the_candidate_path_cannot_produce"]
    assert held == {"smooth_render": 1, "strange_render": 1, "total": 2}


def test_the_three_causes_are_exclusive_and_add_to_the_set():
    """A recipe outside on both counts is `both` and is not counted twice."""
    read = label_migration.expressibility(
        {
            "knobs": _derived("knobs", False, "smooth_render", 3, palette={"gamma": 0.5}),
            "curve": _derived("curve", False, "smooth_render", 3, curve="log"),
            "both": _derived(
                "both", False, "smooth_render", 3, curve="log", palette={"gamma": 0.5}
            ),
        },
        cyclic=set(),
        log=quiet,
    )
    causes = read["what_puts_a_recipe_outside"]
    assert causes == {
        label_migration.PALETTE_ONLY: 1,
        label_migration.CURVE_ONLY: 1,
        label_migration.BOTH: 1,
    }
    assert sum(causes.values()) == read["not_expressible"]


def test_a_continuous_knob_is_a_distribution_and_a_discrete_one_is_a_count():
    """`gamma spreads over a continuum` and `transfer takes four values` are
    different findings, and one shape cannot state both."""
    read = label_migration.expressibility(
        {
            "a": _derived("a", False, "smooth_render", 3, palette={"gamma": 0.25}),
            "b": _derived("b", False, "smooth_render", 3, palette={"gamma": 0.75}),
            "c": _derived("c", False, "smooth_render", 3, palette={"reverse": True}),
        },
        cyclic=set(),
        log=quiet,
    )
    gamma = read["palette_knobs"]["gamma"]
    assert gamma["recipes"] == 2
    assert gamma["distribution"]["min"] == 0.25
    assert gamma["distribution"]["max"] == 0.75
    assert "distribution" not in read["palette_knobs"]["reverse"]
    assert read["palette_knobs"]["reverse"]["most_used"] == {"true": 1}


def test_a_knob_nothing_moved_is_absent_rather_than_zero():
    read = label_migration.expressibility(
        {"a": _derived("a", False, "smooth_render", 3, palette={"gamma": 0.5})},
        cyclic=set(),
        log=quiet,
    )
    assert set(read["palette_knobs"]) == {"gamma"}


def test_a_seat_at_a_plain_recipe_reads_as_expressible():
    """The control on the cross-tab: every seat is a ledger row and every ledger
    row was drawn by a leg spending the candidate path's own curve and palette."""
    plain = finished_recipe()
    read = label_migration.seat_expressibility(
        "a_stamp",
        ["seated", "moved"],
        [
            {
                "key": "seated",
                "recipe": {"colormap": "m", "curve": colorize.CURVE, "palette": plain},
            },
            {
                "key": "moved",
                "recipe": {
                    "colormap": "m",
                    "curve": "log",
                    "palette": plain,
                },
            },
        ],
        cyclic=set(),
        log=quiet,
    )
    assert read["expressible"] == 1
    assert read["not_expressible"] == 1
    assert read["the_ones_that_are_not"][0]["key"] == "moved"


def test_a_seat_with_no_ledger_row_is_counted_apart_from_one_outside():
    read = label_migration.seat_expressibility("a_stamp", ["gone"], [], cyclic=set(), log=quiet)
    assert read["no_ledger_row"] == 1
    assert read["not_expressible"] == 0


# --------------------------------------------------------------------------- #
# The population: human classes 3 and 4, Matt's ruling of 2026-09-08.
# --------------------------------------------------------------------------- #
def test_the_population_is_the_two_top_human_classes():
    assert label_migration.KEPT_CLASSES == (3, 4)


def test_a_low_verdict_is_outside_and_a_high_one_is_in():
    assert not label_migration.in_population({"labels": [{"score": 1}]})
    assert not label_migration.in_population({"labels": [{"score": 2}]})
    assert label_migration.in_population({"labels": [{"score": 3}]})
    assert label_migration.in_population({"labels": [{"score": 4}]})


def test_any_verdict_qualifies_a_key_carrying_two():
    """A crossover key is the SAME PIXELS judged in both stores, so dropping it for
    its other verdict would drop a picture somebody called a 4."""
    both_ways = {"labels": [{"score": 1}, {"score": 4}]}
    assert label_migration.in_population(both_ways)
    assert label_migration.in_population({"labels": [{"score": 4}, {"score": 1}]})


def test_a_key_with_no_verdict_at_all_is_outside():
    assert not label_migration.in_population({"labels": []})
    assert not label_migration.in_population({})


def test_the_population_is_a_parameter_and_not_a_constant():
    """`--classes` has to be able to widen it back, or the trim is irreversible."""
    row = {"labels": [{"score": 2}]}
    assert not label_migration.in_population(row)
    assert label_migration.in_population(row, classes=(1, 2, 3, 4))


# --------------------------------------------------------------------------- #
# merge: the subtree, the leg name, and what is NOT submitted.
# --------------------------------------------------------------------------- #
def test_the_merged_pictures_are_reachable_by_the_orphan_sweep():
    """Not a spelling check. `candidate_ledger.orphans` enumerates `POOL_SUBTREES`
    and looks at `<subtree>/<leg>/pictures` and no other shape, so a merged picture
    outside that has a ledger row and nothing in the project able to find it
    again."""
    from fractal_wallpapers.curation import candidate_ledger

    assert label_migration.POOL_SUBTREE in candidate_ledger.POOL_SUBTREES
    where = label_migration.merged_pictures_dir("scratch/label_migration_demo")
    assert where.name == candidate_ledger.PICTURES_NAME
    assert where.parent.name == "label_migration_demo"
    assert where.parent.parent.name == label_migration.POOL_SUBTREE


def test_the_leg_name_is_the_stores_own_name():
    """One name for the two halves: a ledger row's `provenance.run` names the store
    it came from, and the store's pictures sit under that same name in the pool. A
    leg name a caller chose would join back to nothing."""
    assert label_migration.leg_of("scratch/label_migration_0908") == "label_migration_0908"
    assert label_migration.leg_of(None) == label_migration.DEFAULT_STORE.name


def test_a_merge_with_nothing_scored_refuses_by_name(tmp_path):
    """The score stage's file is what a merge submits, and an empty store is a
    caller who has not run it — not an empty merge."""
    (tmp_path / label_migration.RECIPES_NAME).write_text("", encoding="utf-8")
    (tmp_path / label_migration.RENDERS_NAME).write_text("", encoding="utf-8")
    (tmp_path / label_migration.SCORES_NAME).write_text("", encoding="utf-8")
    with pytest.raises(label_migration.MigrationError, match="score stage"):
        label_migration.merge(tmp_path, log=quiet)


def test_the_build_is_unknown_where_nothing_says_which_one_drew_the_pictures(tmp_path):
    """The staging store keeps no fingerprint, so the readout's is the only evidence.
    Absent, it is `UNKNOWN_ENGINE` and never the live build — the whole backfilled
    pool carries that answer honestly and a guess here would not."""
    from fractal_wallpapers.curation import candidate_ledger

    build, why = label_migration._build_for(tmp_path)
    assert build == candidate_ledger.UNKNOWN_ENGINE
    assert label_migration.READOUT_NAME in why


def test_a_readout_naming_another_build_does_not_stamp_the_live_one(tmp_path):
    (tmp_path / label_migration.READOUT_NAME).write_text(
        json.dumps({"byte_identity": {"live_engine": "not_this_box"}}), encoding="utf-8"
    )
    from fractal_wallpapers.curation import candidate_ledger

    build, why = label_migration._build_for(tmp_path)
    assert build == candidate_ledger.UNKNOWN_ENGINE
    assert "not_this_box" in why


# --------------------------------------------------------------------------- #
# p_fine by expressibility: the cross-tab the readout was missing.
# --------------------------------------------------------------------------- #
def _fine(value: float) -> dict:
    return {"fine": {"p_ge4": value}, "judge": {"p_ge4": value, "p_ge3": value}}


def test_p_fine_is_split_by_class_and_by_whether_the_path_can_produce_the_recipe():
    derived = {
        "a": _derived("a", True, "smooth_render", 4),
        "b": _derived("b", False, "smooth_render", 4),
        "c": _derived("c", True, "smooth_render", 3),
    }
    read = label_migration.fine_by_expressibility(
        derived, {"a": _fine(0.9), "b": _fine(0.1), "c": _fine(0.5)}, log=quiet
    )
    assert read["smooth_render/4"]["expressible"]["n"] == 1
    assert read["smooth_render/4"]["expressible"]["median"] == pytest.approx(0.9)
    assert read["smooth_render/4"]["not_expressible"]["median"] == pytest.approx(0.1)
    assert read["smooth_render/3"]["expressible"]["n"] == 1
    assert "not_expressible" not in read["smooth_render/3"]
    assert read["all_classes"]["expressible"]["n"] == 2


def test_an_unscored_row_is_left_out_rather_than_counted_at_zero():
    derived = {"a": _derived("a", True, "smooth_render", 4)}
    read = label_migration.fine_by_expressibility(derived, {}, log=quiet)
    assert read["all_classes"]["expressible"]["n"] == 0


def test_a_key_carrying_two_verdicts_is_counted_under_each_class():
    """The crossover pairs are one picture judged in both stores, and a cross-tab
    that counted such a key once would have to choose a class for it."""
    row = _derived("a", True, "smooth_render", 4)
    row["labels"].append({"head": "strange_render", "score": 3})
    read = label_migration.fine_by_expressibility({"a": row}, {"a": _fine(0.7)}, log=quiet)
    assert read["smooth_render/4"]["expressible"]["n"] == 1
    assert read["strange_render/3"]["expressible"]["n"] == 1
    assert read["all_classes"]["expressible"]["n"] == 2
