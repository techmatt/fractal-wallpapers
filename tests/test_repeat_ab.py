"""The A/B repeat sitting: the comparative scale, the pair, and the fixed side order.

Five ways this could be quietly wrong, and each has a guard here. A comparative
`3` written where a quality reader can find it reads as tier 3. A variant that
digests to its baseline's key is one picture beside itself. A tile whose halves
are swapped reports the opposite result with nothing looking broken. A page
prefilled or ordered by a head imports the error the sitting exists to avoid. And
a plan that names one half leaves the sheet deriving the other.
"""

from __future__ import annotations

import json

import pytest
from PIL import Image

from fractal_wallpapers.curation import repeat_ab, repetition
from fractal_wallpapers.labeling import attributes, finished, intake, sheets
from fractal_wallpapers.labeling import registry as registry_module

MANDELBROT = {"kind": "mandelbrot", "degree": 2}

PALETTE = {
    "gamma": 1.0,
    "cycles": 1.0,
    "phase": 0.0,
    "reverse": False,
    "mirror": False,
    "transfer": {"kind": "value"},
    "rolloff": {"kind": "none"},
}


def stored_recipe(index: int = 0) -> dict:
    """One candidate-ledger recipe block, in the shape `recipes.of_record` reads."""
    return {
        "schema": 1,
        "family": MANDELBROT,
        "viewport": {"center_re": f"0.{index}", "center_im": "0.0", "width": "1.0"},
        "maxiter": 800,
        "regime": "640x360ss2",
        "mode": "smooth",
        "mode_params": {},
        "curve": "linear",
        "colormap": sheets.CANONICAL_COLORMAP,
        "palette_group": "a_group",
        "palette": dict(PALETTE),
        "autolevel": None,
    }


def baseline(index: int = 0, folded: bool = False) -> repeat_ab.Baseline:
    return repeat_ab.Baseline(
        key=f"key{index:04d}",
        location=f"place{index:04d}",
        partition="mandelbrot",
        mode="smooth",
        colormap=sheets.CANONICAL_COLORMAP,
        folded=folded,
        picture=f"artifacts/curation/hunt/a_run/pictures/{index:05d}.jpg",
        p_fine=0.1 + index / 1000,
        p_ge4=0.8,
        p_ge3=0.99,
        recipe=stored_recipe(index),
    )


# --------------------------------------------------------------------------- #
# The scale, and the one thing it may never become.
# --------------------------------------------------------------------------- #
def test_the_scale_is_three_comparative_classes_and_not_a_tier() -> None:
    held = attributes.attribute("repeat_ab")
    assert held.classes == ("repeat_worse", "neutral", "repeat_better")
    assert held.tiers == (1, 2, 3)
    assert held.paired, "the unit here is two renders, and the sheet picks itself off this"
    # The two scales are not the same length and are not the same question. A
    # reader that pooled them would be adding a comparison to a tier.
    assert held.tiers != finished.tiers("smooth_render")


def test_a_verdict_from_here_cannot_carry_a_score() -> None:
    """The structural guard, which is why this store could be declared rather than built."""
    row = attributes.attribute_row(
        name="repeat_ab",
        batch="a_sitting",
        verdict="repeat_better",
        family=MANDELBROT,
        viewport={"center_re": "0.1", "center_im": "0.0", "width": "1.0"},
    )
    assert "score" not in row and row["class"] == "repeat_better"
    with pytest.raises(attributes.AttributeRefused, match="pooled with a quality corpus"):
        attributes.check("repeat_ab", {**row, "score": 3})


def test_the_neutral_class_is_the_middle_one_the_plan_prefills() -> None:
    """`2` is neutral on the page and in the store, and the plan states exactly it."""
    units, _shape = repeat_ab.plan_of([baseline(0)])
    ordinal = units[0]["suggestion"]
    assert ordinal == 2
    assert attributes.class_of("repeat_ab", ordinal) == "neutral"


# --------------------------------------------------------------------------- #
# The pair.
# --------------------------------------------------------------------------- #
def test_the_variant_moves_the_traversal_and_the_key_and_nothing_else() -> None:
    recipe = stored_recipe()
    palette, key = repeat_ab.variant_of(recipe)
    assert palette["cycles"] == repeat_ab.CYCLES
    assert {name: value for name, value in palette.items() if name != "cycles"} == {
        name: value for name, value in PALETTE.items() if name != "cycles"
    }
    from fractal_wallpapers.curation import recipes

    assert key != recipes.key_of(recipes.of_record(recipe)), "the key did not move"


def test_the_rung_is_two_and_it_is_two_doses() -> None:
    """A cyclic map at cycles 2 is 2x the ramp; a folded one is 4x, and the card says so."""
    assert repeat_ab.CYCLES == 2.0
    assert repeat_ab.PHASE == 0.0
    assert repetition.traversals(repeat_ab.CYCLES, False) == 2.0
    assert repetition.traversals(repeat_ab.CYCLES, True) == 4.0
    cyclic, _shape = repeat_ab.plan_of([baseline(0, folded=False)])
    folded, _shape = repeat_ab.plan_of([baseline(1, folded=True)])
    assert cyclic[0]["selected_on"]["traversals"] == 2.0
    assert folded[0]["selected_on"]["traversals"] == 4.0
    assert "4x the gradient" in folded[0]["facts"][0], "the card prints the TRUE count"


def test_a_plan_unit_states_both_halves_and_names_both_keys() -> None:
    units, shape = repeat_ab.plan_of([baseline(index) for index in range(3)])
    assert shape["units"] == 3 and shape["distinct_variant_keys"] == 3
    for unit in units:
        assert unit["recipe"]["cycles"] == 1.0
        assert unit["variant_recipe"]["cycles"] == repeat_ab.CYCLES
        assert unit["selected_on"]["candidate"] and unit["selected_on"]["variant"]
        assert unit["selected_on"]["phase"] == 0.0


def test_the_draw_is_seeded_and_takes_one_unit_a_location() -> None:
    world = {"baselines": [baseline(index % 5) for index in range(20)]}
    first, shape = repeat_ab.draw(world, units=4, seed=3)
    again, _shape = repeat_ab.draw(world, units=4, seed=3)
    other, _shape = repeat_ab.draw(world, units=4, seed=4)
    assert [one.key for one in first] == [one.key for one in again]
    assert len({one.location for one in first}) == len(first) == 4
    assert shape["eligible_locations"] == 5
    assert [one.location for one in first] != [one.location for one in other]


# --------------------------------------------------------------------------- #
# The composite.
# --------------------------------------------------------------------------- #
def two_pictures(tmp_path) -> tuple:
    left = tmp_path / "left.jpg"
    right = tmp_path / "right.jpg"
    Image.new("RGB", (40, 20), (10, 20, 30)).save(left, "JPEG")
    Image.new("RGB", (40, 20), (200, 100, 50)).save(right, "JPEG")
    return left, right


def test_a_tile_is_two_equal_halves_with_one_separator_between_them(tmp_path) -> None:
    left, right = two_pictures(tmp_path)
    tile = sheets.composite(left, right, tmp_path / "full.jpg")
    with Image.open(tile) as opened:
        assert opened.size == (40 + sheets.SEPARATOR_WIDTH + 40, 20)
        # The baseline is on the LEFT, always. Read off the pixels rather than
        # off the caller's argument order, because that order is the one thing a
        # later reader cannot recover from the picture.
        assert opened.getpixel((5, 10))[0] < opened.getpixel((80, 10))[0]
        # JPEG, so the bar is the colour to within the encoder rather than exactly.
        assert opened.getpixel((42, 10)) == pytest.approx(sheets.SEPARATOR_COLOUR, abs=4)


def test_two_halves_of_different_sizes_are_refused(tmp_path) -> None:
    left, right = two_pictures(tmp_path)
    Image.new("RGB", (30, 20), (0, 0, 0)).save(right, "JPEG")
    with pytest.raises(sheets.SheetError, match="asking about a resample"):
        sheets.composite(left, right, tmp_path / "full.jpg")


# --------------------------------------------------------------------------- #
# The sheet.
# --------------------------------------------------------------------------- #
def half_stub(join, output, leveled=None):
    """A renderer whose picture depends on the recipe, so the halves differ."""
    del leveled
    output.parent.mkdir(parents=True, exist_ok=True)
    shade = int(40 * float(join["recipe"]["cycles"]))
    Image.new("RGB", (16, 9), (shade, shade, shade)).save(output, "JPEG")


def a_unit(index: int, **extra) -> dict:
    return {
        "family": MANDELBROT,
        "viewport": {"center_re": f"0.{index}", "center_im": "0.0", "width": "1.0"},
        "maxiter": 500,
        "mode": "smooth",
        "mode_params": {},
        "curve": "linear",
        "colormap": sheets.CANONICAL_COLORMAP,
        "recipe": dict(PALETTE),
        "variant_recipe": {**PALETTE, "cycles": 2.0},
        "suggestion": 2,
        **extra,
    }


def a_sheet(tmp_path, units, **kwargs):
    scores = ([[0.9, 0.6, 0.2]] * len(units), [[0.9, 0.5, 0.1]] * len(units))
    source = sheets.comparison_source(
        "repeat_ab", renderer=half_stub, scores=kwargs.pop("scores", scores), **kwargs
    )
    return sheets.build(
        source,
        units,
        directory=tmp_path / "sheet",
        batch="a_sitting",
        seed=7,
        log=lambda _: None,
    )


def test_the_sheet_says_what_its_ordinals_mean_and_which_side_is_which(tmp_path) -> None:
    sheet = a_sheet(tmp_path, [a_unit(index) for index in range(4)])
    assert sheet.manifest["kind"] == "comparison"
    assert sheet.manifest["head"] == "repeat_ab"
    assert sheet.manifest["tiers"] == [1, 2, 3]
    assert sheet.manifest["classes"] == ["repeat_worse", "neutral", "repeat_better"]
    assert sheet.manifest["words"]["3"] == "the repeat is better"
    # The one fact a reader cannot recover from the pictures a month later.
    assert sheet.manifest["render"]["sides"] == {"left": "baseline", "right": "variant"}
    assert sheet.manifest["scorer"] == "none"
    assert "not a head's decode" in sheet.manifest["prefill_note"]


def test_the_page_is_shuffled_prefilled_neutral_and_carries_no_column(tmp_path) -> None:
    sheet = a_sheet(tmp_path, [a_unit(index) for index in range(10)])
    assert sheet.manifest["order"] == "shuffle"
    assert sheet.manifest["suggested_by"] == "plan"
    assert all(row["suggestion"] == 2 for row in sheet.rows)
    # No head ordered it and no head's opinion reaches the card.
    assert all(row["suggestion_score"] is None for row in sheet.rows)
    assert all(row["columns"] == {} for row in sheet.rows)
    frames = [row["join"]["viewport"]["center_re"] for row in sheet.rows]
    assert frames != [f"0.{index}" for index in range(10)], "the plan's own order was served"


def test_both_halves_are_read_and_the_readings_never_reach_the_page(tmp_path) -> None:
    sheet = a_sheet(tmp_path, [a_unit(index) for index in range(3)])
    for row in sheet.rows:
        assert row["reading"]["baseline"]["p_ge4"] == pytest.approx(0.2)
        assert row["reading"]["variant"]["p_ge4"] == pytest.approx(0.1)
        assert row["reading"]["read_at"]["resolution"] == list(sheets.LABEL_RESOLUTION)
    # `columns` is what the page prints; `reading` is a key it has never heard of.
    assert all(row["columns"] == {} for row in sheet.rows)


def test_a_tile_is_one_picture_and_its_left_half_is_the_baseline(tmp_path) -> None:
    sheet = a_sheet(tmp_path, [a_unit(0)])
    row = sheet.rows[0]
    assert len(row["pictures"]) == 1 and row["pictures"][0]["caption"] == ""
    with Image.open(sheet.directory / row["pictures"][0]["path"]) as tile:
        assert tile.size == (16 + sheets.SEPARATOR_WIDTH + 16, 9)
        # The stub shades by `cycles`, so the darker half is the 1x one.
        assert tile.getpixel((4, 4))[0] < tile.getpixel((28, 4))[0]
    assert row["join"]["recipe"]["cycles"] == 1.0, "the row's join is the BASELINE half"


def test_a_unit_that_states_one_half_is_refused(tmp_path) -> None:
    unit = a_unit(0)
    unit.pop("variant_recipe")
    with pytest.raises(sheets.SheetError, match="names no variant_recipe"):
        a_sheet(tmp_path, [unit])


def test_two_halves_carrying_one_palette_are_refused(tmp_path) -> None:
    with pytest.raises(sheets.SheetError, match="one picture beside itself"):
        a_sheet(tmp_path, [a_unit(0, variant_recipe=dict(PALETTE))])


def test_a_unit_with_no_prefill_is_refused(tmp_path) -> None:
    """An empty box that meant something different from its neighbour's is worse
    than no prefill at all."""
    unit = a_unit(0)
    unit.pop("suggestion")
    with pytest.raises(sheets.SheetError, match="states all of them or none"):
        a_sheet(tmp_path, [unit, a_unit(1)])


def test_an_unpaired_attribute_cannot_be_cut_as_a_comparison() -> None:
    with pytest.raises(sheets.SheetError, match="not a paired attribute"):
        sheets.comparison_source("spiral")


# --------------------------------------------------------------------------- #
# The seam: a page of numbers becomes a store of classes.
# --------------------------------------------------------------------------- #
def test_a_comparison_sheet_ingests_as_classes_carrying_both_keys(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(attributes, "repo_root", lambda: tmp_path / "store")
    attributes.register(
        "repeat_ab",
        registry_module.Registration(batch="a_sitting", method="a draw, for a test"),
    )
    units = [
        a_unit(
            index,
            selected_on={
                "candidate": f"base{index}",
                "variant": f"var{index}",
                "cycles": 2.0,
                "traversals": 2.0,
            },
        )
        for index in range(3)
    ]
    sheet = a_sheet(tmp_path, units)
    export = tmp_path / "drop.json"
    export.write_text(
        json.dumps({"u0001": {"score": 1}, "u0002": {"score": 2}, "u0003": {"score": 3}}),
        encoding="utf-8",
    )
    report = intake.run(sheet=sheet.directory, labels=export, labeler="matt", write=True)
    assert report["written"] == 3
    assert report["verdicts"] == {"repeat_worse": 1, "neutral": 1, "repeat_better": 1}
    stored = attributes.resolved("repeat_ab").cast()
    assert len(stored) == 3
    assert all("score" not in row for row in stored), "an ordinal reached the store"
    for row in stored:
        # The baseline whole, both keys, and the judge's reading of each half.
        assert row["render"]["recipe"]["cycles"] == 1.0
        assert row["selected_on"]["candidate"] and row["selected_on"]["variant"]
        assert set(row["reading"]) == {"baseline", "variant", "read_at"}


def test_a_four_on_a_three_button_page_is_refused(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(attributes, "repo_root", lambda: tmp_path / "store")
    attributes.register(
        "repeat_ab",
        registry_module.Registration(batch="a_sitting", method="a draw, for a test"),
    )
    sheet = a_sheet(tmp_path, [a_unit(0)])
    export = tmp_path / "drop.json"
    export.write_text(json.dumps({"u0001": {"score": 4}}), encoding="utf-8")
    with pytest.raises(intake.IntakeError, match=r"casts \[1, 2, 3\]"):
        intake.run(sheet=sheet.directory, labels=export, labeler="matt", write=True)
