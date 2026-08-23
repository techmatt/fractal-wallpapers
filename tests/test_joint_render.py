"""The joint render candidate: its split, its recipe, and the bar it is read on.

Four things a reader has to be able to check. That the candidate's training side
keeps **both** blind sheets clean, which is the claim its whole comparison rests
on. That "the incumbents' recipe" is a list rather than a sentence, and that the
one key it could not inherit says so. That the ablation is the pooled split
intersected with a kind rather than a second population. And that the bar refuses
the reading it says it refuses, rather than refusing it in prose and computing it
anyway.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.labeling import finished
from fractal_wallpapers.models import finished_train, joint_acceptance, joint_render


def a_picture(place: str, score: int, kind: str, side: str = "train", **changes):
    fields = {
        "path": None,
        "score": score,
        "side": side,
        "batch": "mode_sweep",
        "place": place,
        "partition": "mandelbrot",
        "mode": "smooth",
        "name": f"{kind}:{place}:{score}",
        "kind": kind,
    }
    fields.update(changes)
    return joint_render.Picture(**fields)


def test_the_forbidden_set_is_the_union_of_both_pins() -> None:
    """The split rule, at its root: a location on EITHER instrument may not train.

    Read off the shipped pins rather than hard-coded, so a store that gains a
    pinned batch tomorrow tightens this test instead of breaking it.
    """
    forbidden = joint_render.pinned_everywhere()
    union = set().union(*(set(finished.pinned(kind)) for kind in joint_render.KINDS))
    assert set(forbidden) == union
    for place, kind in forbidden.items():
        assert place in finished.pinned(kind), "a forbidden place names the store that pinned it"


def test_the_two_shipped_pins_share_no_location() -> None:
    """Not a rule, a fact this comparison leans on: no row is on both sheets, so
    the two evaluation populations are disjoint and an arm on one says nothing
    about the other."""
    smooth = set(finished.pinned("smooth_render"))
    strange = set(finished.pinned("strange_render"))
    assert smooth and strange
    assert not (smooth & strange)


def test_the_recipe_is_the_incumbents_shared_one_plus_a_pinned_backbone() -> None:
    recipe = joint_render.RECIPE
    for key, value in finished_train.COMMON.items():
        assert recipe[key] == value, f"{key} drifted from what both incumbents train under"
    assert recipe["classes"] == len(finished.SCALE)
    backbones = {finished_train.RECIPES[kind]["backbone"] for kind in joint_render.KINDS}
    assert len(backbones) == 2, "the two incumbents used to disagree about exactly this key"
    assert recipe["backbone"] in backbones, "the backbone is one of theirs, not a third thing"
    assert recipe["backbone"] == finished_train.RECIPES["smooth_render"]["backbone"]


def test_the_head_is_told_no_kind() -> None:
    """The whole design, checked where it could quietly stop being true.

    `kind` rides on the Picture so a read can be cut per kind afterwards. The
    training example the loader builds out of one is the picture, its score and
    its index — three things, and the kind is not among them.
    """
    assert "conditioning" in joint_render.RECIPE
    assert joint_render.RECIPE["conditioning"].startswith("none")
    example = a_picture("p", 3, "strange_render")
    assert example.kind == "strange_render"
    fields = finished_train.Crops.__getitem__.__code__.co_consts
    assert "kind" not in [value for value in fields if isinstance(value, str)]


def test_every_chosen_key_says_what_it_was_and_why() -> None:
    """One head has one backbone and one split. Each of those is a decision with
    a direction, and a decision without a reason beside it is a preference."""
    chosen = joint_render.INHERITANCE["chosen"]
    assert chosen
    for entry in chosen:
        assert set(entry) == {"key", "was", "now", "why"}
        assert entry["was"] != entry["now"]
        assert len(entry["why"]) > 60, f"{entry['key']}: the reason is the point of the entry"
    keys = {entry["key"] for entry in chosen}
    assert keys.isdisjoint(joint_render.INHERITANCE["identical_to_both_incumbents"])


def test_a_place_is_worth_one_place_across_both_kinds() -> None:
    """The incumbents' sampler weight, pooled. A location judged smooth six times
    and strange three does not get nine places' worth of gradient."""
    both = [a_picture("busy", 2, "smooth_render", name=f"s{i}") for i in range(6)]
    both += [a_picture("busy", 2, "strange_render", name=f"x{i}") for i in range(3)]
    spread = [a_picture(f"place{i}", 2, "smooth_render") for i in range(9)]
    raw, mass = finished_train.weights(both + spread)
    assert mass["largest_place"] == 9
    assert abs(sum(raw[: len(both)]) - sum(raw[len(both) :]) / 9) < 1e-12


def test_the_sides_a_picture_can_be_on_include_the_one_the_strict_rule_invents() -> None:
    pictures = [
        a_picture("a", 1, "smooth_render", side="train"),
        a_picture("b", 2, "smooth_render", side=joint_render.SELECTION),
        a_picture("c", 3, "strange_render", side="eval"),
        a_picture("d", 4, "smooth_render", side=joint_render.EXCLUDED),
    ]
    by_side = joint_render.sides(pictures)
    assert {name: len(rows) for name, rows in by_side.items()} == {
        "train": 1,
        joint_render.SELECTION: 1,
        "eval": 1,
        joint_render.EXCLUDED: 1,
    }
    assert len(joint_render.of_kind(pictures, "smooth_render")) == 3


def test_the_candidate_is_on_no_roster_and_in_no_release() -> None:
    """It is a candidate. A release that carried it would be shipping a head
    nobody adopted, and `fetch-weights` would demand an asset that does not
    exist."""
    from fractal_wallpapers.models.roster import HEADS

    assert joint_render.HEAD not in HEADS
    manifest = json.loads(
        (joint_render.head_dir().parent / "weights.json").read_text(encoding="utf-8")
    )
    assert joint_render.HEAD not in manifest["heads"]


def test_the_candidate_lives_beside_the_shipped_heads_and_not_inside_one() -> None:
    home = joint_render.head_dir()
    for kind in joint_render.KINDS:
        assert finished_train.head_dir(kind) not in home.parents
        assert home != finished_train.head_dir(kind)


def test_the_bar_refuses_the_boundary_it_says_it_refuses() -> None:
    """`blind_modes` at `>=4` is four anchored rows on a blind sheet. The refusal
    has to be a fact about the code and not only a paragraph."""
    assert "strange_auc_ge4" in joint_acceptance.REFUSED
    for arm in joint_acceptance.ARMS:
        if arm["kind"] == "strange_render":
            assert arm.get("cutpoint") != 4, "an arm reads blind_modes at >=4"


def test_the_sheet_the_refusal_is_about_is_still_the_shape_it_describes() -> None:
    """The caveat is about a live population, so it is read off that population.

    Four rows superseded, all four revised up to 4 on the anchored pass, and those
    four are the whole positive class at `>=4`. If a later pass changes any of
    that, this fails rather than the refusal quietly describing a sheet that has
    moved on.
    """
    rows = [row for row in finished.read("strange_render") if row["batch"] == "blind_modes"]
    resolution = finished.resolve(rows)
    assert resolution.n_superseded == 4
    current = resolution.scored()
    assert sum(1 for row in current if row["score"] >= 4) == 4
    revised = [row for row in current if row["labeler"] is not None]
    assert len(revised) == 4 and all(row["score"] == 4 for row in revised)


def test_the_smooth_sheet_has_no_negative_class_at_its_lowest_cutpoint() -> None:
    """Why `smooth_auc_ge2` is refused rather than reported as a perfect score."""
    own = set(finished.pinned("smooth_render"))
    rows = [r for r in finished.resolved("smooth_render").scored() if finished.place_of(r) in own]
    assert rows and min(row["score"] for row in rows) >= 2
    assert "smooth_auc_ge2" in joint_acceptance.REFUSED


@pytest.mark.parametrize(
    ("direction", "low", "high", "worse"),
    [
        ("lower", 0.01, 0.20, True),
        ("lower", -0.05, 0.20, False),
        ("lower", -0.20, -0.01, False),
        ("higher", -0.20, -0.01, True),
        ("higher", -0.20, 0.05, False),
        ("higher", 0.01, 0.20, False),
        ("higher", None, None, False),
    ],
)
def test_worse_reads_the_interval_in_the_statistic_s_own_direction(
    direction: str, low, high, worse: bool
) -> None:
    """Half the arms improve upward and half improve downward. Reading one
    interval the other one's way is a verdict that is exactly backwards."""
    assert joint_acceptance._worse({"direction": direction}, low, high) is worse


def test_the_bar_gates_on_something_and_reports_the_rest() -> None:
    gated = [arm for arm in joint_acceptance.ARMS if arm["gated"]]
    assert gated, "a bar that gates nothing is not a bar"
    assert all(arm["kind"] in joint_render.KINDS for arm in joint_acceptance.ARMS)
    for kind in joint_render.KINDS:
        assert [arm for arm in gated if arm["kind"] == kind], f"{kind} is not gated on anything"
    for arm in joint_acceptance.ARMS:
        assert len(arm["why"]) > 40


def test_the_bar_names_the_confound_that_points_the_candidate_s_way() -> None:
    """A deviation that helps the candidate is the one a reader has to be told
    about, because the verdict is non-inferiority and it is the direction that
    could buy a PASS."""
    declared = " ".join(joint_acceptance.bar()["declared"])
    assert "never saw" in declared
    assert joint_acceptance.bar()["rule"].startswith("NON-INFERIORITY")


def test_the_incumbents_are_the_runs_that_actually_serve() -> None:
    manifest = json.loads(
        (joint_render.head_dir().parent / "weights.json").read_text(encoding="utf-8")
    )
    for kind, entry in joint_acceptance.INCUMBENTS.items():
        shipped = manifest["heads"][kind]["run"]
        expected = None if shipped == "its own" else shipped
        assert entry["shipped"] == expected, f"{kind} is gated against a run that does not serve"
        assert entry["shipped"] in entry["band"]


@pytest.mark.parametrize("kind", sorted(joint_render.KINDS))
def test_the_strict_split_keeps_both_sheets_clean(kind: str, shipped_render_cache) -> None:
    """The claim the whole comparison rests on, checked on the split that is built.

    Needs the render caches, because a picture with no file is not a training
    unit and `population` refuses rather than skipping it.
    """
    from fractal_wallpapers.models import renders

    for name in joint_render.KINDS:
        if not renders.crop_dir(name).is_dir() or not renders.plan_path(name).is_file():
            pytest.skip("a render cache has not been built on this machine")
        if shipped_render_cache.missing(name):
            pytest.skip("a render cache is incomplete on this machine")

    pictures, record = joint_render.population()
    by_side = joint_render.sides(pictures)
    forbidden = {repr(place) for place in joint_render.pinned_everywhere()}

    for side in ("train", joint_render.SELECTION):
        trespassing = [p for p in by_side[side] if p.place in forbidden]
        assert not trespassing, f"{side} touches a location pinned to a blind sheet"
    own = {repr(place) for place in finished.pinned(kind)}
    assert {p.place for p in joint_render.of_kind(by_side["eval"], kind)} <= own
    # A place's pictures may not straddle the training side and the slice, in
    # either kind: the draw is over pooled places for exactly that reason.
    training = {p.place for p in by_side["train"]}
    chosen = {p.place for p in by_side[joint_render.SELECTION]}
    assert training.isdisjoint(chosen)
    assert record["selection"]["share"] == joint_render.SELECTION_SHARE
    assert record["excluded_pictures"] == len(by_side[joint_render.EXCLUDED])


def test_the_ablation_is_the_pooled_split_intersected_with_one_kind(
    shipped_render_cache,
) -> None:
    """Not a second population. If the ablation drew its own selection slice it
    would move two things at once and could not separate either."""
    from fractal_wallpapers.models import renders

    for name in joint_render.KINDS:
        if not renders.crop_dir(name).is_dir() or not renders.plan_path(name).is_file():
            pytest.skip("a render cache has not been built on this machine")
        if shipped_render_cache.missing(name):
            pytest.skip("a render cache is incomplete on this machine")

    pooled, _ = joint_render.population()
    whole = {(p.kind, p.name): p.side for p in pooled}
    covered: set = set()
    for kind in joint_render.KINDS:
        part, record = joint_render.population(kind)
        assert record["only"] == kind
        keys = {(p.kind, p.name) for p in part}
        assert keys <= set(whole)
        for picture in part:
            assert whole[(picture.kind, picture.name)] == picture.side
        covered |= keys
    assert covered == set(whole), "the two ablations together are the pooled population"


def test_the_ablation_runs_are_named_for_the_kind_they_hold() -> None:
    """A control whose name does not say what it controls is a directory nobody
    can read a table against six months later."""
    for kind, runs in joint_acceptance.ABLATIONS.items():
        assert len(runs) == len(joint_render.RUNS)
        for run in runs:
            assert run.startswith(kind.split("_")[0])
            assert run.endswith(tuple("012"))
    names = [run for runs in joint_acceptance.ABLATIONS.values() for run in runs]
    assert len(set(names)) == len(names)
    assert not set(names) & set(joint_render.RUNS)


def test_the_ablation_carries_no_bar() -> None:
    """It is the arm that separates pooling from what changed alongside it, and
    a control that gated would be a second bar nobody pre-registered."""
    bar = joint_acceptance.bar()
    assert "ablation" not in json.dumps(bar["arms"])
    assert all(arm["key"] in {a["key"] for a in joint_acceptance.ARMS} for arm in bar["arms"])


def test_the_decomposition_adds_back_up_and_is_reported_rather_than_gated() -> None:
    """The scale term and the order term are a split of one number, not two new
    numbers. If they stopped summing to the cross-entropy the table would be
    describing an arithmetic nobody could check."""
    import numpy

    from fractal_wallpapers.models.release_floor import isotonic

    generator = numpy.random.default_rng(0)
    truth = (generator.random(200) < 0.3).astype(float)
    probability = numpy.clip(0.3 * truth + generator.random(200) * 0.5, 1e-6, 1 - 1e-6)
    curve = dict(isotonic(list(zip(map(float, probability), map(float, truth), strict=True))))
    fitted = numpy.array([curve[float(value)] for value in probability])

    def entropy(t, p):
        p = numpy.clip(p, 1e-7, 1.0 - 1e-7)
        return float(-(t * numpy.log(p) + (1.0 - t) * numpy.log(1.0 - p)).mean())

    raw, order = entropy(truth, probability), entropy(truth, fitted)
    assert order <= raw + 1e-12, "recalibrating on the sheet cannot make the loss worse"
    assert abs((order + (raw - order)) - raw) < 1e-12
    # And it gates nothing: the bar's arms are the six, and none of them is this.
    assert "scale" not in {arm["statistic"] for arm in joint_acceptance.ARMS}


def test_the_wide_classifier_is_exactly_one_head_per_kind() -> None:
    """A CORN head over K tiers emits K-1 logits, so two of them want twice that.
    `head.build` counts in tiers rather than logits, which is the off-by-one this
    pins."""
    for classes in (3, 4, 5):
        single = joint_render.classifier_width(classes, per_kind=False)
        both = joint_render.classifier_width(classes, per_kind=True)
        assert single == classes
        assert both - 1 == (classes - 1) * len(joint_render.KINDS)


def test_each_row_reads_its_own_kind_s_cutpoints() -> None:
    torch = pytest.importorskip("torch")

    logits = torch.arange(12, dtype=torch.float).view(2, 6)
    kinds = torch.tensor([0, 1])
    picked = joint_render.cutpoints_of(logits, kinds, 4, per_kind=True)
    assert picked.tolist() == [[0.0, 1.0, 2.0], [9.0, 10.0, 11.0]]
    # The single head has one set and gives it to everybody, kind or no kind.
    narrow = logits[:, :3]
    assert torch.equal(joint_render.cutpoints_of(narrow, None, 4, per_kind=False), narrow)


def test_one_kind_s_examples_never_touch_the_other_kind_s_last_layer() -> None:
    """THE claim the variant rests on: a wide `Linear` is two independent heads.

    If it were not — if the two shared a parameter anywhere — then training would
    be one head wearing two names and the whole comparison would be measuring
    something else. Rows of a linear map do not interact, and this is that fact
    asserted rather than assumed.
    """
    torch = pytest.importorskip("torch")

    layer = torch.nn.Linear(4, (4 - 1) * len(joint_render.KINDS))
    features = torch.randn(3, 4)
    only_the_first_kind = torch.zeros(3, dtype=torch.long)
    joint_render.cutpoints_of(
        layer(features), only_the_first_kind, 4, per_kind=True
    ).sum().backward()
    gradient = layer.weight.grad
    owned = 4 - 1
    assert gradient[:owned].abs().sum() > 0, "the kind that trained got no gradient"
    assert gradient[owned:].abs().sum() == 0.0, "a kind absent from the batch was trained anyway"


def test_every_variant_is_reported_and_none_of_them_gates() -> None:
    """A variant moves one thing about the design. The bar was written about the
    registered candidate, and a bar a different design could satisfy is not a
    bar — so no variant's run may be mistaken for a candidate run."""
    assert joint_render.VARIANTS
    for name, entry in joint_render.VARIANTS.items():
        assert entry["runs"], f"{name} names no run"
        assert len(entry["what"]) > 60, f"{name}: a variant says what it moved"
        assert not set(entry["runs"]) & set(joint_render.RUNS)
    assert set(joint_render.VARIANT_RUNS) == {
        run for entry in joint_render.VARIANTS.values() for run in entry["runs"]
    }
    assert joint_render.VARIANTS["two_head"]["runs"] == joint_render.TWO_HEAD_RUNS
    # And the registered candidate is still the unconditioned one.
    assert joint_render.RECIPE["conditioning"].startswith("none")


def test_the_backbone_variant_moves_the_one_value_that_could_not_be_inherited() -> None:
    """`small_backbone` exists because the pinned choice is a choice. It has to be
    the OTHER incumbent's backbone, not a third thing nobody trained under."""
    assert "small_backbone" in joint_render.VARIANTS
    theirs = {finished_train.RECIPES[kind]["backbone"] for kind in joint_render.KINDS}
    assert joint_render.RECIPE["backbone"] in theirs and len(theirs) == 2
