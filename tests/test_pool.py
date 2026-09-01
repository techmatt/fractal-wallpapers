"""The pool: which ledger rows the gallery leg may seat at all, and the bound.

Two things that are [`curation.solve`]'s and are not the choosing. The pool is the
projection from a ledger row to a [`solve.Candidate`], and its five exclusions are
each a fact about the row rather than a quality bar — the bars are
[`curation.headroom`]'s and they are the pool *definition*, one layer up. The bound
is [`curation.rules.BOUND`], the sound lower bound the diversity rule prunes with,
and it is here because a prune is only as good as its soundness argument and this
project has shipped one whose premise was false.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers import paths
from fractal_wallpapers.curation import rules, solve


@pytest.fixture(autouse=True)
def artifacts_on_disk(tmp_path, monkeypatch):
    """A hot root these fixtures can actually plant a picture in.

    [`solve.pool`] asks whether a row's picture is **on disk**, not whether the row
    names one, so a fixture that only names a path is a fixture the pool refuses.
    Planting is what makes the exclusion testable in both directions.
    """
    root = tmp_path / "artifacts"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv(paths.HOT_ROOT_VARIABLE, str(root))
    return root


def ledger_row(key, on_disk: bool = True, **overrides):
    """One ledger row, with its picture planted unless `on_disk` is False.

    Existence is all [`solve.pool`] asks, so the planted file is empty.
    """
    named = f"artifacts/{key}.jpg"
    if on_disk:
        made = paths.hot_root() / f"{key}.jpg"
        made.parent.mkdir(parents=True, exist_ok=True)
        made.touch()
    row = {
        "key": key,
        "partition": "mandelbrot",
        "location": {"key": f"place-{key}"},
        "recipe": {"mode": "smooth"},
        "palette_group": "map:one",
        "at_candidate_regime": True,
        "colour": {"cells": ["dark_vivid_blue"], "families": ["blue"]},
        "picture": named,
        "rejected": None,
    }
    row.update(overrides)
    return row


#: The judge these fixtures are read on. The sidecar is keyed on the artifact and
#: [`solve.pool`] joins on one, so a fixture that left it off would be testing a
#: join that cannot happen.
ARTIFACT = "judge-under-test"


def score_row(key, p_ge4=0.9, artifact=ARTIFACT):
    return {
        "recipe_key": key,
        "p_ge4": p_ge4,
        "p_ge3": 0.99,
        "head": "smooth_render",
        "judge_artifact": artifact,
    }


def quiet(*_args, **_rest) -> None:
    """A `log` that says nothing."""


# --------------------------------------------------------------------------- #
# The five exclusions.
# --------------------------------------------------------------------------- #
def test_pool_refuses_a_rejected_row_and_says_so():
    """A person's rejection travels on the ledger row so the leg honours it."""
    rows = [ledger_row("a"), ledger_row("b", rejected={"by": "matt"})]
    scores = [score_row("a"), score_row("b")]
    candidates, refused = solve.pool(rows=rows, scores=scores, artifact=ARTIFACT, log=quiet)
    assert [c.key for c in candidates] == ["a"]
    assert refused["rejected"] == 1


@pytest.mark.parametrize(
    ("overrides", "counter"),
    [
        ({"at_candidate_regime": False}, "off_regime"),
        ({"picture": None}, "no_picture"),
        ({"on_disk": False}, "picture_absent"),
    ],
)
def test_pool_refuses_what_no_rule_could_evaluate(overrides, counter):
    """PLANTED, for `picture_absent`: the row names a JPEG that is not there.

    `curate retention` drops pictures and never rows, so this is permanent,
    expected state over about a quarter of the ledger — and until 2026-08-28 every
    one of those rows was admitted and then seated untested, because the diversity
    rule is the only thing that opens a picture and it admitted what it could not
    read. Named apart from `no_picture`: never drawn and drawn-then-swept are
    different facts, and only the second grows.
    """
    rows = [ledger_row("a"), ledger_row("b", **overrides)]
    candidates, refused = solve.pool(
        rows=rows, scores=[score_row("a"), score_row("b")], artifact=ARTIFACT, log=quiet
    )
    assert [c.key for c in candidates] == ["a"]
    assert refused[counter] == 1


def test_pool_refuses_a_row_with_no_score_apart_from_the_others():
    """Nothing to rank it by is a different fact from losing on the rank."""
    rows = [ledger_row("a"), ledger_row("b")]
    candidates, refused = solve.pool(
        rows=rows, scores=[score_row("a")], artifact=ARTIFACT, log=quiet
    )
    assert [c.key for c in candidates] == ["a"]
    assert refused["no_score"] == 1


def test_pool_comes_back_strongest_first():
    rows = [ledger_row("a"), ledger_row("b"), ledger_row("c")]
    scores = [score_row("a", 0.2), score_row("b", 0.9), score_row("c", 0.5)]
    candidates, _refused = solve.pool(rows=rows, scores=scores, artifact=ARTIFACT, log=quiet)
    assert [c.key for c in candidates] == ["b", "c", "a"]


def test_an_empty_ledger_refuses_rather_than_choosing_nothing():
    with pytest.raises(solve.SolveRefused, match="backfill"):
        solve.pool(rows=[], scores=[], log=quiet)


def test_the_strongest_locations_are_offered_first_and_none_is_a_truncation():
    rows = [ledger_row("strong"), ledger_row("middle"), ledger_row("weak")]
    scores = [score_row("strong", 0.9), score_row("middle", 0.5), score_row("weak", 0.1)]
    candidates, _refused = solve.pool(rows=rows, scores=scores, artifact=ARTIFACT, log=quiet)
    assert solve.strongest_locations(candidates, 2) == ["place-strong", "place-middle"]
    assert len(solve.strongest_locations(candidates, None)) == 3
    kept = solve.within(candidates, {"place-strong"})
    assert [c.key for c in kept] == ["strong"]


# --------------------------------------------------------------------------- #
# The bound, and what it is allowed to settle.
# --------------------------------------------------------------------------- #
def signature_pair(seed):
    """Two signatures shaped the way the metric makes them, from a seeded draw."""
    import numpy

    from fractal_wallpapers.palettes import groups

    rng = numpy.random.default_rng(seed)
    size = groups.QUANTILES * groups.DIRECTIONS
    return (
        numpy.sort(rng.normal(size=size).astype(numpy.float32)),
        numpy.sort(rng.normal(0.3, 1.4, size=size).astype(numpy.float32)),
    )


@pytest.mark.parametrize("seed", range(6))
def test_the_bound_never_exceeds_the_distance_it_bounds(seed) -> None:
    """The whole claim. A prune whose premise is false is what this replaced, and
    the premise here is the triangle inequality and nothing weaker."""
    import numpy

    from fractal_wallpapers.palettes import pixel_clouds

    one, other = signature_pair(seed)
    exact = pixel_clouds.distance(one, other)
    bound = float(
        numpy.abs(rules.reduce_signature(one) - rules.reduce_signature(other)).sum(
            dtype=numpy.float64
        )
        / rules.bound_width()
    )
    assert bound <= exact + 1e-9
    assert bound > 0.5 * exact, "and it is not so slack as to settle nothing"


def test_the_bound_at_one_block_is_the_distance_between_the_mean_colours() -> None:
    """Which is what the design predicted the metric would admit. Four blocks is
    that statement per band of the cloud; one block is the statement itself."""
    from fractal_wallpapers.palettes import groups

    one, _other = signature_pair(0)
    grid = one.reshape(groups.QUANTILES, groups.DIRECTIONS)
    assert rules.reduce_signature(one).mean(axis=0) == pytest.approx(grid.mean(axis=0), abs=1e-5)


def test_the_bounds_denominator_has_one_spelling() -> None:
    """Two spellings of a denominator is how a screen and a metric stop being
    comparable while every line of both still reads correctly."""
    from fractal_wallpapers.palettes import groups

    assert rules.bound_width() == groups.DIRECTIONS * rules.BOUND_BLOCKS


# --------------------------------------------------------------------------- #
# The constants this leg stands on.
# --------------------------------------------------------------------------- #
def test_the_q4_bar_is_the_advisory_and_says_it_is_not_a_crossover():
    from fractal_wallpapers.curation import floors

    assert solve.Q4_BAR == floors.RELEASE_ADVISORY
    assert "NOT a measured crossover" in solve.Q4_BASIS


def test_the_flat_mode_floor_scales_with_the_gallery_and_is_zero_below_a_hundred():
    assert solve.mode_floor(20) == 0
    assert solve.mode_floor(150) == 1
    assert solve.mode_floor(1000) == 10
    assert solve.SEATS_PER_MODE_FLOOR == 100


def test_the_rule_the_leg_builds_carries_the_allowance_arithmetic():
    from fractal_wallpapers.curation import ceiling

    rule = solve.rule_for({"dark_vivid_lime": 0.2})
    assert rule.targets == {"dark_vivid_lime": 0.2}
    assert rule.allowed("dark_vivid_lime", 100) == ceiling.Rule(
        targets={"dark_vivid_lime": 0.2}
    ).allowed("dark_vivid_lime", 100)


def test_a_record_round_trips_through_its_own_directory(tmp_path, monkeypatch):
    monkeypatch.setenv(paths.HOT_ROOT_VARIABLE, str(tmp_path))
    written = solve.write_record("pilot", {"schema": solve.SCHEMA, "filled": 1})
    assert written.name == "solve.json"
    assert solve.read_record("pilot")["schema"] == solve.SCHEMA
    with pytest.raises(solve.SolveRefused, match="no record"):
        solve.read_record("never-run")
