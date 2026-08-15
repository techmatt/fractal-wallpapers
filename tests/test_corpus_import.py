"""The import from the source corpus: the adapter, the table, and the fold.

The import itself needs the source repository and cannot run here — it ran once,
and what it produced is tracked. What is tested is everything that decided what
it produced: how one of their render blocks becomes one of our locations, that
the landing table is internally consistent, and that a location several batches
labelled lands on the conservative side of the fold.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers.labeling import corpus_import
from fractal_wallpapers.labeling import registry as registry_module
from fractal_wallpapers.supply.partitions import partition_of_family

VIEW = {"cx": "0.1", "cy": "0.2", "fw": "0.5"}


def render(**extra) -> dict:
    return {**VIEW, "maxiter": 8000, "width": 1280, "height": 720, "ss": 4, **extra}


def test_the_parameter_planes_carry_their_degree_in_a_field() -> None:
    family, viewport, _ = corpus_import.location_of(render(), "multibrot4")
    assert family == {"kind": "multibrot", "degree": 4}
    assert viewport == {"center_re": "0.1", "center_im": "0.2", "width": "0.5"}
    assert partition_of_family(family) == "multibrot4"


def test_a_julia_row_carries_its_seed_and_lands_in_the_dynamical_partition() -> None:
    family, _viewport, _ = corpus_import.location_of(
        render(c_re="-0.4", c_im="0.6"), "julia_multibrot3"
    )
    assert family == {"kind": "julia", "degree": 3, "c": ["-0.4", "0.6"]}
    assert partition_of_family(family) == "julia:multibrot3"


def test_a_julia_row_without_its_seed_is_refused() -> None:
    """Half the location's identity is missing, and no default can supply it."""
    with pytest.raises(corpus_import.CorpusImportError, match="no seed c"):
        corpus_import.location_of(render(), "julia")


def test_a_phoenix_row_naming_no_constants_is_the_pinned_instance() -> None:
    """Absent is not unknown: what the engine renders when told nothing is the
    classic point, so a row that names nothing is a row at that point."""
    family, _viewport, _ = corpus_import.location_of(render(), "phoenix")
    assert family == {"kind": "phoenix"}
    assert partition_of_family(family) == "phoenix:classic"


def test_a_swept_phoenix_row_carries_all_three_parameter_pairs() -> None:
    family, _viewport, _ = corpus_import.location_of(
        render(c_re="0.4", c_im="0.1", p_re="-0.3", p_im="0.0", zm1_re="0.2", zm1_im="0.0"),
        "phoenix",
    )
    assert family["c"] == ["0.4", "0.1"]
    assert family["p"] == ["-0.3", "0.0"]
    assert family["z_prev"] == ["0.2", "0.0"]
    assert partition_of_family(family) == "phoenix"


def test_a_coordinate_written_as_a_number_is_coerced_and_counted() -> None:
    """One batch there wrote its seeds as JSON numbers on every row. A number is
    not a coordinate here, and a silent float would key that batch's locations
    somewhere nothing else can reach."""
    family, _viewport, coerced = corpus_import.location_of(render(c_re=-0.4, c_im=0.6), "julia")
    assert coerced == 2
    assert all(isinstance(part, str) for part in family["c"])


def test_the_crop_axes_do_not_survive_the_fold_onto_a_location() -> None:
    """Palette and composition vary across the crops of one location, and the
    location's verdict is the best of them — so carrying one crop's coloring
    would attach it to a label that is not about that crop."""
    block = corpus_import.render_of(render(palette="RdGy", composition="thirds"))
    assert block == {"resolution": [1280, 720], "supersample": 4, "mode": "smooth", "maxiter": 8000}


def test_an_unknown_source_family_is_refused() -> None:
    with pytest.raises(corpus_import.CorpusImportError, match="unknown source family"):
        corpus_import.location_of(render(), "something_else")


# --------------------------------------------------------------------------- #
# The landing table.
# --------------------------------------------------------------------------- #


def test_every_landing_batch_is_registered_exactly_once() -> None:
    names = [r.batch for r in corpus_import.registrations()]
    assert len(names) == len(set(names))
    assert all(r.method for r in corpus_import.registrations())


def test_the_only_eligible_batches_are_the_unconditioned_ones() -> None:
    eligible = {r.batch for r in corpus_import.registrations() if r.eval_eligible}
    unconditioned = {r.batch for r in corpus_import.registrations() if r.score_unconditioned}
    assert eligible == unconditioned
    assert eligible == {
        "crawl_uniform",
        "descent_base_rate_julia",
        "flat_draw_mandelbrot",
        "parameter_space_uniform",
    }


def test_a_batch_holding_two_populations_registers_twice() -> None:
    """One source batch drew a base rate over the dynamical planes and screened
    rows on the parameter planes. Two generation methods are two registrations,
    or the distinction stops being recoverable from the corpus afterwards."""
    census = "2026-07-17_prospect_run1_baserate_v1"
    assert corpus_import.target(census, "julia:multibrot4").batch == "descent_base_rate_julia"
    assert corpus_import.target(census, "multibrot4").batch == "descent_base_rate_native"
    assert corpus_import.target(census, "julia:multibrot4").score_unconditioned
    assert not corpus_import.target(census, "multibrot4").score_unconditioned


def test_a_source_batch_nobody_mapped_lands_nowhere() -> None:
    assert corpus_import.target("a_batch_from_another_project", "mandelbrot") is None


def test_every_anchored_batch_is_train_side() -> None:
    for entry in corpus_import.registrations():
        if entry.anchored:
            assert not entry.eval_eligible


# --------------------------------------------------------------------------- #
# The fold, for a location several batches labelled.
# --------------------------------------------------------------------------- #


def known(**batches) -> dict:
    return {
        name: registry_module.Registration(
            batch=name, method="a draw", score_unconditioned=unconditioned
        )
        for name, unconditioned in batches.items()
    }


def test_one_biased_contributor_owns_the_location() -> None:
    """Eligibility over a location is an AND over everything that touched it. It
    is carried as the owning batch so the store holds it as one fact on the row
    rather than as a rule every reader has to remember."""
    registry = known(clean=True, biased=False)
    assert corpus_import.owning_batch({"clean", "biased"}, registry) == "biased"


def test_an_all_eligible_location_keeps_an_eligible_owner() -> None:
    registry = known(clean=True, also_clean=True)
    assert corpus_import.owning_batch({"clean", "also_clean"}, registry) == "also_clean"


def test_an_unregistered_contributor_is_biased_and_wins() -> None:
    registry = known(clean=True)
    assert corpus_import.owning_batch({"clean", "unregistered"}, registry) == "unregistered"
