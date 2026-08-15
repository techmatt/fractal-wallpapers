"""The bar: how it is calibrated, and the one thing it must not do.

The location head's first bar was broken and had to be fixed before anything
trained: it had been calibrated on the *width* of the interval two control runs
produce, when what a candidate has to survive is its *lower bound*. The same
mistake is available here, so the same check is: a bar that cannot pass the
material it was built from is not a bar about a candidate.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.models import finished_acceptance as acceptance


def test_the_margin_is_the_lower_reach_and_never_below_the_floor() -> None:
    assert acceptance.margin_of(0.0) == acceptance.MATERIAL_FLOOR
    assert acceptance.margin_of(0.001) == acceptance.MATERIAL_FLOOR
    assert acceptance.margin_of(0.0546) == 0.055, "rounded up to half a point of AUC"
    assert acceptance.margin_of(0.0308) == 0.035
    assert acceptance.margin_of(None) == acceptance.MATERIAL_FLOOR


def test_a_tier_is_decoded_by_threshold_and_cannot_skip() -> None:
    assert acceptance.decode([0.1, 0.05, 0.01], 3) == 1
    assert acceptance.decode([0.9, 0.1, 0.05], 3) == 2
    assert acceptance.decode([0.9, 0.8, 0.2], 3) == 3
    assert acceptance.decode([0.9, 0.8, 0.7], 3) == 4
    assert acceptance.decode([0.9, 0.1], 2) == 2


@pytest.mark.parametrize("head", sorted(acceptance.SHEETS))
def test_the_bar_would_not_fail_the_material_it_was_built_from(head: str) -> None:
    """The check the location head's bar needed and did not have.

    Sheet D committed five seeds of one recipe, so the weakest of them is what
    the bar must not fail. Sheet E committed none, so the analogous control is the
    head the adoption replaced: a bar that called *that* materially worse would be
    calling a difference this population had already failed to resolve.
    """
    path = acceptance.prereg_path(head)
    if not path.is_file():
        pytest.skip(f"the {head} bar has not been written on this machine")
    bar = json.loads(path.read_text(encoding="utf-8"))
    floor = bar["arms"]["ordering"]["target"] - bar["arms"]["ordering"]["margin"]

    seeds = bar["yardstick"]["adopted"]["seeds"]
    control = min(seeds) if seeds else bar["yardstick"]["incumbent"]["auc"]
    assert control >= floor, (
        f"{head}: the bar's floor is {floor:.4f} and the control it was calibrated on reads "
        f"{control:.4f}. A bar its own control cannot clear is not a bar about a candidate."
    )


@pytest.mark.parametrize("head", sorted(acceptance.SHEETS))
def test_the_bar_is_about_the_population_this_repository_holds(head: str) -> None:
    """`preregister` refuses unless the two sides hold the same sheet, so a bar
    that exists is a bar whose population was checked. This re-states it from the
    file, which is what a later reader has."""
    path = acceptance.prereg_path(head)
    if not path.is_file():
        pytest.skip(f"the {head} bar has not been written on this machine")
    bar = json.loads(path.read_text(encoding="utf-8"))
    stick = json.loads(acceptance.yardstick_path(head).read_text(encoding="utf-8"))
    assert bar["population"]["rows"] == stick["population"]["rows"]
    ours = {k: v for k, v in bar["population"]["tiers"].items() if v}
    theirs = {k: int(v) for k, v in stick["population"]["tiers"].items() if int(v)}
    assert ours == theirs
    assert bar["population"]["positives"] > 0
    assert 0.0 < bar["population"]["base_rate"] < 1.0, "one class only is not a boundary"


@pytest.mark.parametrize("head", sorted(acceptance.SHEETS))
def test_the_gated_arms_and_the_reported_ones_are_declared_apart(head: str) -> None:
    path = acceptance.prereg_path(head)
    if not path.is_file():
        pytest.skip(f"the {head} bar has not been written on this machine")
    bar = json.loads(path.read_text(encoding="utf-8"))
    gated = {name for name, arm in bar["arms"].items() if arm.get("gated")}
    assert gated == {"ordering", "interface", "calibration"}
    assert bar["arms"]["agreement"]["gated"] is False
    assert bar["arms"]["other_boundaries"]["gated"] is False
    assert len(bar["declared"]) >= 4, "the caveats are the point of writing this first"
