"""Guard: the colour codebook is an instrument, so its calibration is pinned.

A census reports "dark green never appears" or "orange dies at the floor", and
both readings are only as trustworthy as the fifty-two places the colours were
sorted into. Every number this file asserts was *declared before* the sweep that
fixed `SIGMA` and is repeated in the module docstring; a change that moves one of
them changes what every stored share vector means, so it should be a decision and
not a surprise.

The two failures these tests exist to catch both actually happened while the
codebook was being built:

* a fixed vivid chroma put seven of the twelve dark-vivid swatches outside sRGB,
  dark green among them, so the census would have reported the library's own
  fortyish dark-green maps as absent;
* neutrals placed at lightnesses between the tone levels sent a pure mid-grey to
  dark muted cyan, so every achromatic wallpaper in the pool would have donated a
  quarter of its mass to cyan and teal.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.palettes import codebook, space

numpy = pytest.importorskip("numpy")


def lab_of(swatch: dict):
    return numpy.asarray(swatch["lab"], dtype=numpy.float64).reshape(1, 3)


# --------------------------------------------------------------------------- #
# The shape of the codebook.
# --------------------------------------------------------------------------- #
def test_the_codebook_is_fifty_two_uniquely_named_places() -> None:
    swatches = codebook.swatches()
    assert len(swatches) == 52
    assert len(codebook.HUES) * len(codebook.TONES) * len(codebook.CHROMA_TARGETS) == 48
    assert len(codebook.NEUTRALS) == 4
    names = codebook.names()
    assert len(set(names)) == 52
    assert sum(1 for entry in swatches if entry["kind"] == "neutral") == 4


def test_the_order_is_the_hues_then_the_neutrals_and_it_never_moves() -> None:
    """A share vector persisted under one order and read under another is silently
    wrong, so the order is part of the artifact's contract."""
    kinds = [entry["kind"] for entry in codebook.swatches()]
    assert kinds == ["hue"] * 48 + ["neutral"] * 4
    assert codebook.names()[:2] == ("dark_muted_rose", "dark_vivid_rose")
    assert codebook.names()[-4:] == ("black", "dark_gray", "light_gray", "white")


def test_every_swatch_is_a_colour_sRGB_can_actually_show() -> None:
    """The failure a fixed vivid chroma caused: an out-of-gamut swatch is a bucket
    no pixel can ever land in, and a census through one reports a colour as absent
    when what is absent is the swatch."""
    for entry in codebook.swatches():
        lab = numpy.asarray(entry["lab"], dtype=numpy.float64)
        assert numpy.linalg.norm(space.oklab(space.srgb(lab)) - lab) < 0.004, entry["swatch"]


def test_the_gamut_limited_swatches_are_marked_and_are_the_dark_cool_ones() -> None:
    limited = {entry["swatch"] for entry in codebook.swatches() if entry["gamut_limited"]}
    assert limited, "some swatch must be gamut-limited or the targets are meaningless"
    for name in ("dark_vivid_teal", "dark_vivid_cyan", "dark_vivid_yellow"):
        assert name in limited


# --------------------------------------------------------------------------- #
# The three pre-registered calibration checks.
# --------------------------------------------------------------------------- #
def test_a_pure_swatch_dominates_its_own_cell() -> None:
    """All fifty-two, so the dominant swatch of a single-colour picture is that
    colour. This is what makes `dominant` a name rather than a nearest guess."""
    for index, entry in enumerate(codebook.swatches()):
        read = codebook.census(lab_of(entry))
        assert read["dominant"] == entry["swatch"]
        assert codebook.shares(lab_of(entry)).argmax() == index


def test_a_neutral_grey_stays_neutral_at_every_lightness() -> None:
    """The check that rejected the first codebook. Below 0.99 and achromatic
    wallpapers start manufacturing hue findings."""
    neutral = [
        index for index, entry in enumerate(codebook.swatches()) if entry["kind"] == "neutral"
    ]
    for lightness in numpy.linspace(0.05, 0.98, 40):
        share = codebook.shares(numpy.array([[lightness, 0.0, 0.0]]))
        assert share[neutral].sum() >= 0.99, f"grey at L={lightness:.3f} leaked out of the neutrals"


def test_the_assignment_is_soft_without_collapsing_to_nearest() -> None:
    """Median self-share 0.81 as calibrated: high enough that a cell means
    something, short enough that a gradient crossing a boundary does not show as
    two hard blocks."""
    selves = [
        float(codebook.shares(lab_of(entry))[index])
        for index, entry in enumerate(codebook.swatches())
    ]
    assert 0.75 <= float(numpy.median(selves)) <= 0.90
    assert min(selves) > 0.40


def test_the_width_and_the_thresholds_are_the_declared_ones() -> None:
    assert codebook.SIGMA == 0.015
    assert codebook.SHARE_THRESHOLDS == (0.10, 0.25)
    assert codebook.SMALL_SHARE == 0.05
    assert codebook.CENSUS_SIZE == (160, 90)


# --------------------------------------------------------------------------- #
# What the codebook cannot separate, reported rather than hidden.
# --------------------------------------------------------------------------- #
def test_the_unresolvable_pairs_are_the_dark_cool_muted_vivid_ones() -> None:
    """sRGB has almost no chroma at L=0.40 for these hues, so their muted and vivid
    swatches sit inside the assignment's own resolution. A reader of those cells
    has to be told, which is why `closest_pairs` is in the persisted document."""
    closest = {frozenset((one, other)) for _distance, one, other in codebook.closest_pairs(3)}
    for hue in ("cyan", "teal", "yellow"):
        assert frozenset((f"dark_muted_{hue}", f"dark_vivid_{hue}")) in closest


# --------------------------------------------------------------------------- #
# The arithmetic.
# --------------------------------------------------------------------------- #
def test_shares_are_a_distribution() -> None:
    share = codebook.shares(space.oklab(space.spent("twilight_shifted", 256)))
    assert share.shape == (52,)
    assert share.min() >= 0.0
    assert abs(float(share.sum()) - 1.0) < 1e-12


def test_collapsing_duplicate_pixels_is_the_same_arithmetic() -> None:
    """The speed-up is only allowed because it is exact: a colour assigned once and
    weighted by its pixel count is the mean over those pixels."""
    generator = numpy.random.default_rng(0)
    picture = generator.integers(0, 40, size=(90, 160, 3), dtype=numpy.uint8) * 6
    colours, counts = codebook.distinct(picture)
    assert int(counts.sum()) == 90 * 160
    assert len(colours) < 90 * 160, "the fixture must actually hold duplicates"
    whole = codebook.shares(space.oklab(picture))
    collapsed = codebook.shares(space.oklab(colours), counts)
    assert float(numpy.abs(whole - collapsed).max()) < 1e-12


def test_entropy_runs_from_one_cell_to_the_whole_codebook() -> None:
    one = numpy.zeros(52)
    one[7] = 1.0
    assert codebook.entropy_bits(one) == pytest.approx(0.0)
    assert codebook.entropy_bits(numpy.full(52, 1.0 / 52)) == pytest.approx(
        numpy.log2(52), abs=1e-9
    )


def test_a_rollup_conserves_the_share_it_folds() -> None:
    read = codebook.of_ramp("Blues")
    folded = codebook.rollup(read["shares"])
    assert set(folded) == {name for name, _ in codebook.HUES} | {"neutral"}
    assert sum(folded.values()) == pytest.approx(sum(read["shares"].values()), abs=1e-6)


# --------------------------------------------------------------------------- #
# Does it say what a person would say.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("colormap", "family"),
    [("Blues", "blue"), ("Greens", "green"), ("Oranges", "orange"), ("Purples", "purple")],
)
def test_a_map_named_for_a_colour_censuses_as_that_colour(colormap: str, family: str) -> None:
    """The cheapest possible validity check, and the one worth having: matplotlib's
    single-hue ramps are named by people, and the codebook has to agree with them.

    **Within one spoke**, which is the whole of what a twelve-spoke wheel can
    promise. `Blues` really does sit at 236-259 degrees, nearer the azure spoke at
    240 than the blue one at 270 — it is a cyan-leaning ramp and the codebook is
    reading it correctly — and `Oranges` straddles the orange/red boundary the
    same way. A map landing two spokes away would be a genuine fault, and this
    still catches it.
    """
    wheel = [name for name, _degrees in codebook.HUES]
    folded = codebook.rollup(codebook.of_ramp(colormap)["shares"])
    hues = {name: value for name, value in folded.items() if name != "neutral"}
    read = max(hues, key=hues.get)
    at = wheel.index(family)
    adjacent = {wheel[at], wheel[(at + 1) % len(wheel)], wheel[at - 1]}
    assert read in adjacent, f"{colormap} read as {read}, more than one spoke from {family}"


@pytest.mark.slow
def test_the_fold_is_the_maps_own_kind_and_not_a_callers() -> None:
    """`mirror = the map is not cyclic`, the rule `palette_sets.recipe_for` owns.
    A sequential map censused unfolded is a different set of colours."""
    from fractal_wallpapers.models import palette_sets

    cyclic = palette_sets.cyclic()
    assert "Blues" not in cyclic, "the fixture must be a sequential map"

    # A folded ramp is spent out and back, so it is symmetric about its middle and
    # its two ends are the same colour. That is the seam fix, and it is what the
    # census reads because it is what the engine draws.
    folded = space.spent("Blues", 64)
    assert numpy.allclose(folded, folded[::-1], atol=1e-9)

    # A cyclic map is swept once and is not symmetric — otherwise the fold would be
    # unobservable and this test would pass on a census that ignored `kind`.
    wrapped = next(name for name in ("twilight_shifted", "berlin") if name in cyclic)
    swept = space.spent(wrapped, 64)
    assert not numpy.allclose(swept, swept[::-1], atol=1e-9)


# --------------------------------------------------------------------------- #
# The persisted document.
# --------------------------------------------------------------------------- #
def test_the_document_carries_everything_needed_to_reproduce_an_assignment() -> None:
    """A share vector read next year has to be readable under the codebook that
    produced it, so the artifact carries the codebook rather than a version tag."""
    document = codebook.document()
    assert document["space"] == "oklab"
    assert document["assignment"]["sigma"] == codebook.SIGMA
    assert len(document["swatches"]) == 52
    assert document["closest_pairs"]
    json.dumps(document)  # must survive the artifact writer


def test_the_document_states_the_swatch_for_anchor_translation() -> None:
    """The ratified codebook says `anchor`; this repository already means three
    other things by that word, one of them on the very rows a census reads."""
    assert "anchor" in codebook.document()["note"]
    assert "swatch" in codebook.document()["note"]
