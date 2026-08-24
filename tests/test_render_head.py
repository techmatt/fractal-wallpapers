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
import pathlib

import pytest

from fractal_wallpapers.labeling import finished
from fractal_wallpapers.models import finished_train, render_acceptance, render_train


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
    return render_train.Picture(**fields)


def test_the_forbidden_set_is_the_union_of_both_pins() -> None:
    """The split rule, at its root: a location on EITHER instrument may not train.

    Read off the shipped pins rather than hard-coded, so a store that gains a
    pinned batch tomorrow tightens this test instead of breaking it.
    """
    forbidden = render_train.pinned_everywhere()
    union = set().union(*(set(finished.pinned(kind)) for kind in render_train.KINDS))
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
    recipe = render_train.RECIPE
    for key, value in finished_train.COMMON.items():
        assert recipe[key] == value, f"{key} drifted from what both incumbents train under"
    assert recipe["classes"] == len(finished.SCALE)
    backbones = {finished_train.RECIPES[kind]["backbone"] for kind in render_train.KINDS}
    assert len(backbones) == 2, "the two incumbents used to disagree about exactly this key"
    assert recipe["backbone"] in backbones, "the backbone is one of theirs, not a third thing"
    assert recipe["backbone"] == finished_train.RECIPES["smooth_render"]["backbone"]


def test_the_head_is_told_no_kind() -> None:
    """The whole design, checked where it could quietly stop being true.

    `kind` rides on the Picture so a read can be cut per kind afterwards. The
    training example the loader builds out of one is the picture, its score and
    its index — three things, and the kind is not among them.
    """
    assert "conditioning" in render_train.RECIPE
    assert render_train.RECIPE["conditioning"].startswith("none")
    example = a_picture("p", 3, "strange_render")
    assert example.kind == "strange_render"
    fields = finished_train.Crops.__getitem__.__code__.co_consts
    assert "kind" not in [value for value in fields if isinstance(value, str)]


def test_every_chosen_key_says_what_it_was_and_why() -> None:
    """One head has one backbone and one split. Each of those is a decision with
    a direction, and a decision without a reason beside it is a preference."""
    chosen = render_train.INHERITANCE["chosen"]
    assert chosen
    for entry in chosen:
        assert set(entry) == {"key", "was", "now", "why"}
        assert entry["was"] != entry["now"]
        assert len(entry["why"]) > 60, f"{entry['key']}: the reason is the point of the entry"
    keys = {entry["key"] for entry in chosen}
    assert keys.isdisjoint(render_train.INHERITANCE["identical_to_both_incumbents"])


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
        a_picture("b", 2, "smooth_render", side=render_train.SELECTION),
        a_picture("c", 3, "strange_render", side="eval"),
        a_picture("d", 4, "smooth_render", side=render_train.EXCLUDED),
    ]
    by_side = render_train.sides(pictures)
    assert {name: len(rows) for name, rows in by_side.items()} == {
        "train": 1,
        render_train.SELECTION: 1,
        "eval": 1,
        render_train.EXCLUDED: 1,
    }
    assert len(render_train.of_kind(pictures, "smooth_render")) == 3


def test_the_judge_is_on_the_roster_and_in_the_release() -> None:
    """It was adopted on 2026-08-23 and it is what ships. A roster that still
    named the two superseded heads would make `fetch-weights` demand two assets
    no release carries."""
    from fractal_wallpapers.models.roster import HEADS

    assert render_train.HEAD in HEADS
    manifest = json.loads(
        (render_train.head_dir().parent / "weights.json").read_text(encoding="utf-8")
    )
    assert render_train.HEAD in manifest["heads"]
    assert set(manifest["heads"]) == set(HEADS)
    # And the two it replaced are gone from both. Their label STORES are not,
    # which is what `finished.HEADS` still names.
    for superseded in finished.HEADS:
        assert superseded not in HEADS
        assert superseded not in manifest["heads"]


def test_the_candidate_lives_beside_the_shipped_heads_and_not_inside_one() -> None:
    home = render_train.head_dir()
    for kind in render_train.KINDS:
        assert finished_train.head_dir(kind) not in home.parents
        assert home != finished_train.head_dir(kind)


def test_the_bar_refuses_the_boundary_it_says_it_refuses() -> None:
    """`blind_modes` at `>=4` is four anchored rows on a blind sheet. The refusal
    has to be a fact about the code and not only a paragraph."""
    assert "strange_auc_ge4" in render_acceptance.REFUSED
    for arm in render_acceptance.ARMS:
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
    assert "smooth_auc_ge2" in render_acceptance.REFUSED


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
    assert render_acceptance._worse({"direction": direction}, low, high) is worse


def test_the_bar_gates_on_something_and_reports_the_rest() -> None:
    gated = [arm for arm in render_acceptance.ARMS if arm["gated"]]
    assert gated, "a bar that gates nothing is not a bar"
    assert all(arm["kind"] in render_train.KINDS for arm in render_acceptance.ARMS)
    for kind in render_train.KINDS:
        assert [arm for arm in gated if arm["kind"] == kind], f"{kind} is not gated on anything"
    for arm in render_acceptance.ARMS:
        assert len(arm["why"]) > 40


def test_the_bar_names_the_confound_that_points_the_candidate_s_way() -> None:
    """A deviation that helps the candidate is the one a reader has to be told
    about, because the verdict is non-inferiority and it is the direction that
    could buy a PASS."""
    declared = " ".join(render_acceptance.bar()["declared"])
    assert "never saw" in declared
    assert render_acceptance.bar()["rule"].startswith("NON-INFERIORITY")


def test_the_incumbents_are_the_runs_the_superseded_heads_served_from() -> None:
    """The bar was read against the two heads that served when it was registered.
    They no longer ship, so the manifest cannot answer for them any more and the
    check moves to the record each of them left behind."""
    for kind, entry in render_acceptance.INCUMBENTS.items():
        assert entry["shipped"] in entry["band"]
        directory = finished_train.head_dir(kind, entry["shipped"])
        assert (directory / "scores.jsonl").is_file(), (
            f"{kind} is gated against a run with no committed read of its own sheet"
        )


@pytest.mark.parametrize("kind", sorted(render_train.KINDS))
def test_the_strict_split_keeps_both_sheets_clean(kind: str, shipped_render_cache) -> None:
    """The claim the whole comparison rests on, checked on the split that is built.

    Needs the render caches, because a picture with no file is not a training
    unit and `population` refuses rather than skipping it.
    """
    from fractal_wallpapers.models import renders

    for name in render_train.KINDS:
        if not renders.crop_dir(name).is_dir() or not renders.plan_path(name).is_file():
            pytest.skip("a render cache has not been built on this machine")
        if shipped_render_cache.missing(name):
            pytest.skip("a render cache is incomplete on this machine")

    pictures, record = render_train.population()
    by_side = render_train.sides(pictures)
    forbidden = {repr(place) for place in render_train.pinned_everywhere()}

    for side in ("train", render_train.SELECTION):
        trespassing = [p for p in by_side[side] if p.place in forbidden]
        assert not trespassing, f"{side} touches a location pinned to a blind sheet"
    own = {repr(place) for place in finished.pinned(kind)}
    assert {p.place for p in render_train.of_kind(by_side["eval"], kind)} <= own
    # A place's pictures may not straddle the training side and the slice, in
    # either kind: the draw is over pooled places for exactly that reason.
    training = {p.place for p in by_side["train"]}
    chosen = {p.place for p in by_side[render_train.SELECTION]}
    assert training.isdisjoint(chosen)
    assert record["selection"]["share"] == render_train.SELECTION_SHARE
    assert record["excluded_pictures"] == len(by_side[render_train.EXCLUDED])


def test_the_ablation_is_the_pooled_split_intersected_with_one_kind(
    shipped_render_cache,
) -> None:
    """Not a second population. If the ablation drew its own selection slice it
    would move two things at once and could not separate either."""
    from fractal_wallpapers.models import renders

    for name in render_train.KINDS:
        if not renders.crop_dir(name).is_dir() or not renders.plan_path(name).is_file():
            pytest.skip("a render cache has not been built on this machine")
        if shipped_render_cache.missing(name):
            pytest.skip("a render cache is incomplete on this machine")

    pooled, _ = render_train.population()
    whole = {(p.kind, p.name): p.side for p in pooled}
    covered: set = set()
    for kind in render_train.KINDS:
        part, record = render_train.population(kind)
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
    for kind, runs in render_acceptance.ABLATIONS.items():
        assert len(runs) == len(render_train.RUNS)
        for run in runs:
            assert run.startswith(kind.split("_")[0])
            assert run.endswith(tuple("012"))
    names = [run for runs in render_acceptance.ABLATIONS.values() for run in runs]
    assert len(set(names)) == len(names)
    assert not set(names) & set(render_train.RUNS)


def test_the_ablation_carries_no_bar() -> None:
    """It is the arm that separates pooling from what changed alongside it, and
    a control that gated would be a second bar nobody pre-registered."""
    bar = render_acceptance.bar()
    assert "ablation" not in json.dumps(bar["arms"])
    assert all(arm["key"] in {a["key"] for a in render_acceptance.ARMS} for arm in bar["arms"])


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
    assert "scale" not in {arm["statistic"] for arm in render_acceptance.ARMS}


def test_the_wide_classifier_is_exactly_one_head_per_kind() -> None:
    """A CORN head over K tiers emits K-1 logits, so two of them want twice that.
    `head.build` counts in tiers rather than logits, which is the off-by-one this
    pins."""
    for classes in (3, 4, 5):
        single = render_train.classifier_width(classes, per_kind=False)
        both = render_train.classifier_width(classes, per_kind=True)
        assert single == classes
        assert both - 1 == (classes - 1) * len(render_train.KINDS)


def test_each_row_reads_its_own_kind_s_cutpoints() -> None:
    torch = pytest.importorskip("torch")

    logits = torch.arange(12, dtype=torch.float).view(2, 6)
    kinds = torch.tensor([0, 1])
    picked = render_train.cutpoints_of(logits, kinds, 4, per_kind=True)
    assert picked.tolist() == [[0.0, 1.0, 2.0], [9.0, 10.0, 11.0]]
    # The single head has one set and gives it to everybody, kind or no kind.
    narrow = logits[:, :3]
    assert torch.equal(render_train.cutpoints_of(narrow, None, 4, per_kind=False), narrow)


def test_one_kind_s_examples_never_touch_the_other_kind_s_last_layer() -> None:
    """THE claim the variant rests on: a wide `Linear` is two independent heads.

    If it were not — if the two shared a parameter anywhere — then training would
    be one head wearing two names and the whole comparison would be measuring
    something else. Rows of a linear map do not interact, and this is that fact
    asserted rather than assumed.
    """
    torch = pytest.importorskip("torch")

    layer = torch.nn.Linear(4, (4 - 1) * len(render_train.KINDS))
    features = torch.randn(3, 4)
    only_the_first_kind = torch.zeros(3, dtype=torch.long)
    render_train.cutpoints_of(
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
    assert render_train.VARIANTS
    for name, entry in render_train.VARIANTS.items():
        assert entry["runs"], f"{name} names no run"
        assert len(entry["what"]) > 60, f"{name}: a variant says what it moved"
        assert not set(entry["runs"]) & set(render_train.RUNS)
    assert set(render_train.VARIANT_RUNS) == {
        run for entry in render_train.VARIANTS.values() for run in entry["runs"]
    }
    assert render_train.VARIANTS["two_head"]["runs"] == render_train.TWO_HEAD_RUNS
    # And the registered candidate is still the unconditioned one.
    assert render_train.RECIPE["conditioning"].startswith("none")


def test_every_candidate_takes_one_of_the_two_incumbents_backbones() -> None:
    """The backbone is the one value a joint head cannot inherit, because the two
    incumbents disagree about it. A candidate has to take one of theirs — a third
    one nobody trained under would make the comparison a different experiment."""
    theirs = {finished_train.RECIPES[kind]["backbone"] for kind in render_train.KINDS}
    assert len(theirs) == 2, "the incumbents used to disagree about exactly this key"
    for name, entry in render_train.CANDIDATES.items():
        assert entry["backbone"] in theirs, f"{name} trains at a backbone neither ships"
    # And between them the registered candidates have asked both.
    assert {e["backbone"] for e in render_train.CANDIDATES.values()} == theirs


def test_both_arms_weight_a_row_identically_whatever_kind_it_is() -> None:
    """ARM C, as a guard. The failure it forecloses: if the shared arm took one
    mean over the pooled batch while the split arm took a mean PER KIND and summed
    them, the rarer kind's head would carry an effective weight of
    `n_pooled / n_kind` — about 2.6x for strange — and the two arms would differ in
    learning rate rather than in architecture. Every comparison between them would
    then be measuring the wrong thing, silently.

    Checked at the derivative, which is where the normalization actually lives:
    `dL/dz` for a row is `(sigmoid(z) - target) / (tasks * |subset|)`, and that
    denominator has to be the POOLED subset for every row of either kind.
    """
    torch = pytest.importorskip("torch")

    from fractal_wallpapers.models import head

    torch.manual_seed(0)
    width, classes = 3, 4
    kinds = torch.tensor([0] * 24 + [1] * 8)
    labels = torch.randint(1, classes + 1, (len(kinds),))
    layer = torch.nn.Linear(8, width * len(render_train.KINDS))
    logits = render_train.cutpoints_of(layer(torch.randn(len(kinds), 8)), kinds, classes, True)
    (gradient,) = torch.autograd.grad(head.loss_of(logits, labels, classes), logits)

    ranks = labels - 1
    for cutpoint in range(width):
        subset = ranks > (cutpoint - 1)
        size = int(subset.sum())
        if size == 0:
            continue
        target = (ranks[subset] > cutpoint).float()
        residual = torch.sigmoid(logits[subset, cutpoint].detach()) - target
        coefficient = gradient[subset, cutpoint] / residual
        expected = torch.full_like(coefficient, 1.0 / (width * size))
        assert torch.allclose(coefficient, expected, atol=1e-6), (
            f"cutpoint {cutpoint}: a row's weight is not 1/(tasks * pooled subset). "
            f"Some kind is being up- or down-weighted relative to the other arm."
        )


def test_the_shared_and_split_arms_reach_one_loss_through_one_line() -> None:
    """The parity above is only durable because there is one call site. A second
    one — a per-kind loss added up somewhere — is how it would come back."""
    source = pathlib.Path(render_train.__file__).read_text(encoding="utf-8")
    assert source.count("head.loss_of(") == 1, (
        "more than one loss call site in the trainer: the two arms are no longer "
        "guaranteed to aggregate the same way"
    )


def test_a_gap_splits_into_a_scale_half_and_an_order_half_that_add_back_up() -> None:
    """`scale_or_order` claims a decomposition. A decomposition that does not sum
    to the thing it decomposes is two unrelated numbers wearing one name."""
    import numpy

    from fractal_wallpapers.models.release_floor import isotonic

    generator = numpy.random.default_rng(0)
    truth = (generator.random(300) < 0.4).astype(float)
    probability = numpy.clip(0.35 * truth + generator.random(300) * 0.5, 1e-6, 1 - 1e-6)

    def entropy(t, p):
        p = numpy.clip(p, 1e-7, 1.0 - 1e-7)
        return float(-(t * numpy.log(p) + (1.0 - t) * numpy.log(1.0 - p)).mean())

    curve = dict(isotonic(list(zip(map(float, probability), map(float, truth), strict=True))))
    order = entropy(truth, numpy.array([curve[float(v)] for v in probability]))
    raw = entropy(truth, probability)
    assert order <= raw + 1e-12, "recalibrating on the sheet cannot make the loss worse"
    assert abs(order + (raw - order) - raw) < 1e-12


def test_each_candidate_owns_its_own_bar_and_record() -> None:
    """A superseded candidate's read stays exactly as it was read. Two candidates
    sharing one file would mean the second question overwrote the first answer."""
    paths = {name: render_acceptance.bar_path(name) for name in render_train.CANDIDATES}
    assert len(set(paths.values())) == len(paths), "two candidates share a bar file"
    records = {name: render_acceptance.comparison_path(name) for name in render_train.CANDIDATES}
    assert len(set(records.values())) == len(records)
    # The first candidate keeps the plain names it was registered under.
    assert render_acceptance.bar_path("medium").name == "bar.json"
    assert render_acceptance.comparison_path("medium").name == "comparison.json"
    assert render_train.CURRENT in render_train.CANDIDATES


def test_a_bar_is_never_rewritten_once_it_exists() -> None:
    for name in render_train.CANDIDATES:
        if render_acceptance.bar_path(name).is_file():
            with pytest.raises(render_acceptance.ComparisonError, match="not a bar"):
                render_acceptance.write_bar(name)


def test_every_variant_names_the_candidate_it_varies() -> None:
    """A variant read against nothing is a number with no comparison in it."""
    for name, entry in render_train.VARIANTS.items():
        assert entry["against"] in render_train.CANDIDATES, f"{name} varies no known candidate"
        assert entry["backbone"] == render_train.CANDIDATES[entry["against"]]["backbone"], (
            f"{name} and the candidate it is compared against differ in the backbone too, "
            f"so the comparison would move two things at once"
        )


def test_the_per_seed_conjunction_reports_how_many_chances_it_takes() -> None:
    """The strict reading runs one test per gated arm per seed. That is a lot of
    one-sided 2.5% tests, and a candidate that is exactly non-inferior everywhere
    still trips one a third of the time — so the number of chances is reported
    beside the verdict rather than left for a reader to work out."""
    band = {
        "verdict": "NOT_RESOLVED",
        "ours": 0.5,
        "theirs": 0.5,
        "delta": 0.0,
        "ci": [-0.1, 0.1],
    }
    arms = [
        {"key": f"arm{i}", "gated": True, "band": band, "per_seed": dict.fromkeys("abc", band)}
        for i in range(5)
    ]
    out = render_acceptance._multiplicity(arms, ["a", "b", "c"])
    assert out["per_seed_tests"] == 15
    assert out["band_only_verdict"] == "PASS"
    assert not out["crossed_per_seed"] and not out["crossed_on_the_band"]
    assert 0.30 < out["chance_of_a_crossing_if_exactly_non_inferior"] < 0.33

    # One seed of one arm crossing is a FAIL under the conjunction and not on the band.
    arms[2]["per_seed"]["c"] = {**band, "verdict": "WORSE"}
    out = render_acceptance._multiplicity(arms, ["a", "b", "c"])
    assert out["crossed_per_seed"] == ["arm2:c"]
    assert out["band_only_verdict"] == "PASS", "the band is unaffected by one seed"


def test_blind_modes_is_blind_at_the_boundary_it_gates_on() -> None:
    """The anchored pass moved four rows from 3 to 4. That contaminates `>=4`,
    which is refused — but it moved them WITHIN the `>=3` class, so the `>=3`
    positive set is identical before and after and gating there is sound.

    Worth a guard because the two facts look alike and the wrong one would either
    throw away a legitimate arm or read a contaminated one.
    """
    from fractal_wallpapers.labeling import store

    rows = [row for row in finished.read("strange_render") if row["batch"] == "blind_modes"]
    blind: dict = {}
    for row in sorted(rows, key=store.order_of):
        blind.setdefault(finished.render_key(row), row)
    current = finished.resolve(rows).current

    at_least_three = [{k for k, v in side.items() if v["score"] >= 3} for side in (blind, current)]
    assert at_least_three[0] == at_least_three[1], "the anchored pass moved the >=3 boundary"
    assert len(at_least_three[0]) == 6

    at_least_four = [{k for k, v in side.items() if v["score"] >= 4} for side in (blind, current)]
    assert not at_least_four[0] and len(at_least_four[1]) == 4, (
        "the >=4 positives should be entirely a product of the anchored pass, "
        "which is why that boundary is refused"
    )


# --------------------------------------------------------------------------- #
# Which head a candidate is gated against.
# --------------------------------------------------------------------------- #
def test_a_candidate_without_an_incumbent_is_gated_against_the_per_kind_pair() -> None:
    """The design study's reading, unchanged. Both of its candidates predate any
    joint head shipping, and a superseded read has to stay exactly as it was read."""
    for name in ("medium", "small_backbone"):
        against = render_acceptance.incumbent_of(name)
        assert against["source"] == render_acceptance.PER_KIND
        assert against["per_kind"] == {
            kind: dict(row) for kind, row in render_acceptance.INCUMBENTS.items()
        }


def test_a_retrain_is_gated_against_the_shipped_joint_band() -> None:
    """A retrain's incumbent is the head it would replace, and once a joint head
    ships that is no longer the pair it replaced."""
    against = render_acceptance.incumbent_of("enlarged_corpus")
    assert against["source"] == render_acceptance.JOINT
    assert against["candidate"] == "small_backbone"
    band = render_train.CANDIDATES["small_backbone"]["runs"]
    for kind in render_train.KINDS:
        assert against["per_kind"][kind]["band"] == band
        assert against["per_kind"][kind]["shipped"] == band[0]


def test_an_incumbent_that_names_no_registered_candidate_is_refused() -> None:
    entry = dict(render_train.CANDIDATES["enlarged_corpus"], incumbent="a_head_nobody_trained")
    saved = render_train.CANDIDATES["enlarged_corpus"]
    render_train.CANDIDATES["enlarged_corpus"] = entry
    try:
        with pytest.raises(render_acceptance.ComparisonError):
            render_acceptance.incumbent_of("enlarged_corpus")
    finally:
        render_train.CANDIDATES["enlarged_corpus"] = saved


def test_the_retrains_bar_reads_the_band_and_says_so() -> None:
    """Matt's standing ruling of 2026-08-23. The per-seed conjunction is still
    computed and still reported; it gates nothing."""
    declared = render_acceptance.bar("enlarged_corpus")
    assert declared["reading"] == "band"
    assert "band" in declared["verdicts"]["PASS"]
    assert "seed" not in declared["verdicts"]["PASS"]
    assert render_acceptance.bar("small_backbone")["reading"] == "band and every seed"


def test_the_retrains_bar_declares_the_scale_shift_before_it_has_a_number() -> None:
    """The one thing a corpus-growth retrain is guaranteed to do, said out loud
    in the bar rather than explained in the report afterwards."""
    declared = render_acceptance.bar("enlarged_corpus")
    said = " ".join(declared["declared"]).lower()
    assert "scale" in said and "expected" in said
    assert "no number" in said, "the rare-colour motivation must be declared unmeasurable"


def test_every_shipped_bar_carries_the_fields_the_read_takes_from_it() -> None:
    """A bar is never rewritten, so `read` fills a missing field from the roster and
    the older documents are genuinely short of some. What it may NOT do is invent one
    of these: the rule, how significance was decided, and what adoption is not."""
    for name in render_train.CANDIDATES:
        path = render_acceptance.bar_path(name)
        if not path.is_file():
            continue
        declared = json.loads(path.read_text(encoding="utf-8"))
        for key in ("rule", "significance", "adoption", "arms", "refused", "incumbents"):
            assert declared.get(key), f"{name}: its bar carries no {key}"


def test_the_retrains_bar_is_reproducible_from_the_module_that_wrote_it() -> None:
    """The newest bar, exactly. The two older ones predate fields this module now
    writes and are exempt by the rule that a bar is never rewritten; this one was
    written by the code as it stands and must still come out of it unchanged."""
    path = render_acceptance.bar_path("enlarged_corpus")
    if not path.is_file():
        pytest.skip("the retrain's bar has not been written on this machine")
    written = json.loads(path.read_text(encoding="utf-8"))
    assert written == json.loads(json.dumps(render_acceptance.bar("enlarged_corpus")))


def test_a_named_run_trains_at_its_band_s_declared_backbone_and_not_the_module_s() -> None:
    """The defect of 2026-08-24, as a guard. `RECIPE["backbone"]` is the FIRST
    candidate's medium and every band since has re-asked that one value in its own
    declaration — so a launch that read the module default instead of the band trained
    a design no bar had been written about. Three `enlarged_corpus` runs did, and
    nothing downstream could see it: `config.json`, the checkpoint's own config and
    `head audit` all agreed with each other and with the wrong value."""
    for name, entry in render_train.CANDIDATES.items():
        for run in entry["runs"]:
            assert render_train.declared_backbone(run) == entry["backbone"], (
                f"{run} resolves to a backbone its {name} band does not declare"
            )
    # The one that bit: the newest band's value is NOT the module's pinned default.
    assert (
        render_train.declared_backbone("enlarged_corpus_seed0") != render_train.RECIPE["backbone"]
    ), "this guard is only worth anything while the two actually differ"
    # A run no band claims stays free: nothing has written a bar about it.
    assert render_train.declared_backbone("some_scratch_run") is None


def test_a_launch_at_a_backbone_the_band_does_not_declare_is_refused() -> None:
    """`--backbone` may re-ask the value under a run name nobody has written a bar
    about. It may not quietly retarget a band: the bar names the design and a band
    trained at another backbone cannot answer it."""
    with pytest.raises(render_train.TrainingError) as refusal:
        render_train.check_declared_backbone(
            "enlarged_corpus_seed1", {"backbone": render_train.RECIPE["backbone"]}
        )
    said = str(refusal.value)
    assert "enlarged_corpus" in said and render_train.RECIPE["backbone"] in said
    # The declared value passes, and an unclaimed run name is not checked at all.
    render_train.check_declared_backbone(
        "enlarged_corpus_seed1",
        {"backbone": render_train.CANDIDATES["enlarged_corpus"]["backbone"]},
    )
    render_train.check_declared_backbone("some_scratch_run", {"backbone": "anything_at_all"})


def test_a_planted_mismatch_between_a_written_run_and_its_band_fails(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The half that sees it AFTER the hours are spent. A run records the recipe it
    ran, so nothing inside its directory can say the band was supposed to be something
    else — only the declaration can, and this is where a written band is held to it."""
    # Only where a run's config is READ: the bar still comes off the tracked file,
    # because what is being checked is that the read refuses on the declaration and
    # not on something incidental about a temporary directory.
    monkeypatch.setattr(render_train, "config_path", lambda run=None: tmp_path / f"{run}.json")
    band = "enlarged_corpus"
    runs = render_train.CANDIDATES[band]["runs"]
    declared = render_train.CANDIDATES[band]["backbone"]
    for run in runs:
        render_train.config_path(run).write_text(
            json.dumps({"backbone": declared}), encoding="utf-8", newline="\n"
        )
    # As declared: nothing to say.
    render_train.check_written_backbone(runs)

    # Now plant the mismatch on one seed, exactly as the mis-launch wrote it.
    render_train.config_path(runs[1]).write_text(
        json.dumps({"backbone": render_train.RECIPE["backbone"]}), encoding="utf-8", newline="\n"
    )
    with pytest.raises(render_train.TrainingError) as refusal:
        render_train.check_written_backbone(runs)
    said = str(refusal.value)
    assert runs[1] in said and band in said and declared in said

    # And the acceptance read refuses on it rather than reporting a band that is not
    # the design its bar was written about.
    with pytest.raises(render_acceptance.ComparisonError) as refused:
        render_acceptance.read(candidate=band)
    assert "backbone their band declares" in str(refused.value), (
        "it must refuse on the declaration, not later on a missing score file"
    )


def test_the_mislaunched_runs_are_out_of_every_band_and_say_what_they_are() -> None:
    """They trained, they cost hours, and they answer no bar. Kept and named rather
    than deleted — but out of the band, so no read can pair them against it."""
    claimed = {run for entry in render_train.CANDIDATES.values() for run in entry["runs"]}
    claimed |= {run for entry in render_train.VARIANTS.values() for run in entry["runs"]}
    for run, entry in render_train.MISLAUNCHED.items():
        assert run not in claimed, f"{run} is a mis-launch and still sits inside a band"
        assert render_train.declared_for(run) is None
        assert entry["launched_as"] in claimed, "it was launched under a name a band does claim"
    assert "--backbone" in render_train.MISLAUNCH_BASIS
