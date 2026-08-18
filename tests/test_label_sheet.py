"""The generator: two row sources, one cut, and what may become a label.

The invariant that does not bend in either mode or either source: **a suggestion
is not a label**. A sheet row carries no verdict, and the only thing that becomes
one is what a person exported from the page.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.labeling import intake, sheets, store

MANDELBROT = {"kind": "mandelbrot"}


def unit(index: int) -> dict:
    return {
        "family": MANDELBROT,
        "viewport": {"center_re": f"0.{index}", "center_im": "0.0", "width": "1.0"},
        "maxiter": 500,
    }


def stub(row, canonical, vivid, resolution, supersample):
    """A renderer that writes the two files and nothing else.

    Injected rather than mocked at the engine boundary: the sheet's job here is
    ordering, naming and recording, and holding the whole suite to a built
    release engine to test that would be a poor trade.
    """
    del row, resolution, supersample
    for path in (canonical, vivid):
        path.write_bytes(b"")
    return {"maxiter": 500}


class Head:
    """A scorer with an opinion, standing in for the head that will arrive."""

    name = "a_head"

    def __init__(self, scores):
        self.scores = scores

    def score(self, unit):
        return self.scores[unit["viewport"]["center_re"]]

    def admits(self, unit, score):
        return True


class Judge:
    """A head with cutpoints, standing in for the shipped location one."""

    name = "location:abcdef012345"

    def __init__(self, vectors):
        self.vectors = vectors

    def read(self, units):
        from fractal_wallpapers.discovery.scoring import Reading

        return [
            Reading(vector[1], vector[2] if len(vector) > 2 else None, None, tuple(vector))
            for vector in (self.vectors[u["viewport"]["center_re"]] for u in units)
        ]


def build(tmp_path, units, scorer=None, seed=0, **kwargs):
    source = sheets.location_source(scorer=scorer, renderer=stub)
    return sheets.build(
        source,
        units,
        directory=tmp_path / "sheet",
        batch="a_batch",
        seed=seed,
        log=lambda _: None,
        **kwargs,
    )


# --------------------------------------------------------------------------- #
# The location source.
# --------------------------------------------------------------------------- #
def test_without_a_head_the_page_is_a_seeded_shuffle(tmp_path) -> None:
    """Not draw order: it arrives in blocks, and a block of one source's material
    drags the bar for as long as it lasts."""
    units = [unit(i) for i in range(20)]
    first = build(tmp_path, units, seed=3)
    second = sheets.build(
        sheets.location_source(renderer=stub),
        units,
        directory=tmp_path / "again",
        batch="a_batch",
        seed=3,
        log=lambda _: None,
    )
    assert first.manifest["order"] == "shuffle"
    places = [row["join"]["viewport"] for row in first.rows]
    assert places == [row["join"]["viewport"] for row in second.rows]
    assert places != [u["viewport"] for u in units]


def test_with_a_head_the_page_is_ordered_good_to_bad(tmp_path) -> None:
    units = [unit(i) for i in range(4)]
    head = Head({"0.0": 0.1, "0.1": 0.9, "0.2": 0.5, "0.3": 0.7})
    sheet = build(tmp_path, units, scorer=head)
    assert sheet.manifest["order"] == "score"
    assert sheet.manifest["scorer"] == "a_head"
    assert [r["suggestion_score"] for r in sheet.rows] == [0.9, 0.7, 0.5, 0.1]


def test_a_head_with_cutpoints_prefills_a_tier_and_surfaces_every_column(tmp_path) -> None:
    """The decode reaches as far as the checkpoint can: one cutpoint cleared is a
    2, all three are a 4, and the columns are the head's own numbers."""
    judge = Judge(
        {
            "0.0": [0.9, 0.8, 0.7],
            "0.1": [0.9, 0.8, 0.2],
            "0.2": [0.9, 0.1, 0.0],
            "0.3": [0.1, 0.0, 0.0],
        }
    )
    sheet = build(tmp_path, [unit(i) for i in range(4)], scorer=judge)
    assert [row["suggestion"] for row in sheet.rows] == [4, 3, 2, 1]
    assert sheet.manifest["suggested_tiers"] == {"1": 1, "2": 1, "3": 1, "4": 1}
    assert sheet.manifest["scorer"] == judge.name
    assert sheet.manifest["suggested_by"] == judge.name
    assert sheet.rows[0]["columns"] == {"p_ge2": 0.9, "p_ge3": 0.8, "p_ge4": 0.7}


def test_a_scorer_that_only_ranks_orders_the_page_and_suggests_nothing(tmp_path) -> None:
    """A rank is not a tier. The old location page was this, and it is what a
    judge without cutpoints still gets."""
    head = Head({"0.0": 0.1, "0.1": 0.9})
    sheet = build(tmp_path, [unit(0), unit(1)], scorer=head)
    assert [row["suggestion"] for row in sheet.rows] == [None, None]
    assert [row["columns"] for row in sheet.rows] == [{}, {}]
    assert sheet.manifest["order"] == "score"


def test_sections_lead_in_plan_order_and_each_reads_good_to_bad(tmp_path) -> None:
    """Anchor rows first, and the head's order inside every section — so a sweep
    from a chosen row cannot reach back over the rows that set the scale."""
    judge = Judge({"0.0": [0.2, 0.1, 0.0], "0.1": [0.9, 0.9, 0.9], "0.2": [0.9, 0.5, 0.1]})
    units = [
        {**unit(0), "section": "the 4 bar"},
        {**unit(1), "section": "the draw"},
        {**unit(2), "section": "the draw"},
    ]
    sheet = build(tmp_path, units, scorer=judge)
    assert sheet.manifest["order"] == "sections"
    assert [row["section"] for row in sheet.rows] == ["the 4 bar", "the draw", "the draw"]
    assert [row["join"]["viewport"]["center_re"] for row in sheet.rows] == ["0.0", "0.1", "0.2"]
    assert sheet.manifest["sections"] == {"the 4 bar": 1, "the draw": 2}


def test_a_location_plan_may_prefill_the_incumbent_verdict(tmp_path) -> None:
    """One rule, both sources: a stated suggestion is the verdict a row already
    carries, and a page states all of them or none."""
    judge = Judge({"0.0": [0.2, 0.1, 0.0], "0.1": [0.9, 0.9, 0.2]})
    units = [{**unit(0), "suggestion": 4}, {**unit(1), "suggestion": 1}]
    sheet = build(tmp_path, units, scorer=judge)
    assert [row["suggestion"] for row in sheet.rows] == [1, 4]
    assert sheet.manifest["suggested_by"] == "plan"
    with pytest.raises(sheets.SheetError, match="all of them or none"):
        build(tmp_path / "mixed", [{**unit(0), "suggestion": 4}, unit(1)], scorer=judge)
    with pytest.raises(sheets.SheetError, match="not one of"):
        build(tmp_path / "off", [{**unit(0), "suggestion": 7}], scorer=judge)


def test_a_location_plan_row_keeps_the_batch_it_was_drawn_from(tmp_path) -> None:
    units = [{**unit(0), "batch": "top_tier_anchor"}, unit(1)]
    sheet = build(tmp_path, units)
    assert {row["batch"] for row in sheet.rows} == {"top_tier_anchor", "a_batch"}
    assert sheet.manifest["batches"] == {"a_batch": 1, "top_tier_anchor": 1}


def test_the_unit_id_is_assigned_after_the_order_is_fixed(tmp_path) -> None:
    """So the id encodes the page position and nothing else — not the draw, not
    the score, not the fate."""
    sheet = build(tmp_path, [unit(i) for i in range(5)])
    assert [r["unit"] for r in sheet.rows] == ["u0001", "u0002", "u0003", "u0004", "u0005"]


def test_a_picture_is_named_for_the_build_so_re_ordering_costs_no_render(tmp_path) -> None:
    """The id moves when the order does; the file does not. That is what makes a
    long cut resumable."""
    head = Head({"0.0": 0.1, "0.1": 0.9})
    sheet = build(tmp_path, [unit(0), unit(1)], scorer=head)
    assert sheet.rows[0]["unit"] == "u0001"
    assert sheet.rows[0]["pictures"][0]["path"] == "vivid/cut0001.png"
    assert (sheet.directory / "vivid" / "cut0000.png").exists()
    assert (sheet.directory / "vivid" / "cut0001.png").exists()
    # The id and the render number are different numbers for the same unit, so no
    # picture answers to the id: `u0001` cannot reach a file by having its `u` cut off.
    assert not (sheet.directory / "vivid" / "0001.png").exists()


def test_a_sheet_row_carries_no_verdict(tmp_path) -> None:
    sheet = build(tmp_path, [unit(0)])
    assert "score" not in sheet.rows[0]
    assert sheet.rows[0]["suggestion"] is None


def test_both_companions_are_rendered_from_the_committed_library(tmp_path) -> None:
    sheet = build(tmp_path, [unit(0)])
    assert (sheet.directory / "canonical" / "cut0000.png").exists()
    assert (sheet.directory / "vivid" / "cut0000.png").exists()
    assert sheet.rows[0]["join"]["render"]["colormap"] == sheets.CANONICAL_COLORMAP
    assert sheet.rows[0]["join"]["judged_from"] == sheets.VIVID_COLORMAP
    captions = [picture["caption"] for picture in sheet.rows[0]["pictures"]]
    assert captions == [
        f"judge from · {sheets.VIVID_COLORMAP}",
        f"stored against · {sheets.CANONICAL_COLORMAP}",
    ]


def test_a_colormap_outside_the_library_is_refused() -> None:
    with pytest.raises(sheets.SheetError, match="committed library"):
        sheets.colormap("a_map_that_was_never_committed")


def test_an_empty_sheet_is_refused(tmp_path) -> None:
    with pytest.raises(sheets.SheetError, match="nothing to judge"):
        build(tmp_path, [])


def test_a_sheet_reads_back_as_it_was_written(tmp_path) -> None:
    sheet = build(tmp_path, [unit(i) for i in range(3)])
    again = sheets.read(sheet.directory)
    assert again.manifest == sheet.manifest
    assert again.rows == sheet.rows


# --------------------------------------------------------------------------- #
# One shape, both sources.
# --------------------------------------------------------------------------- #
def test_a_sheet_hands_over_the_whole_join_its_store_keys_on(tmp_path) -> None:
    """The generator writes what the one ingest path reads, so the two cannot
    drift into two answers about what a sheet row is."""
    sheet = build(tmp_path, [unit(0)])
    read = intake.read_sheet(sheet.directory)
    assert read.head == sheets.LOCATION_HEAD
    assert set(intake.LOCATION_JOIN_KEYS) <= set(read.rows[0]["join"])


def test_the_manifest_says_which_source_cut_it_and_on_what_scale(tmp_path) -> None:
    sheet = build(tmp_path, [unit(0)])
    assert sheet.manifest["kind"] == "location"
    assert sheet.manifest["head"] == sheets.LOCATION_HEAD
    assert sheet.manifest["tiers"] == list(store.SCORES)
    assert sheet.manifest["rubric"]


def test_a_finished_sheet_is_cast_on_the_same_scale_as_every_other(tmp_path) -> None:
    """Matt's decision: one scale, every head. The shipped strange judge still
    decodes to at most a 3, and that is the model's number, not the page's."""
    source = sheets.finished_source("strange_render", scores=([], 3))
    assert list(source.tiers) == [1, 2, 3, 4]
    assert source.head == "strange_render"


# --------------------------------------------------------------------------- #
# The populations.
# --------------------------------------------------------------------------- #
def test_units_come_off_a_walk_ledger_through_the_supply_reader(tmp_path) -> None:
    ledger = tmp_path / "walk.jsonl"
    rows = [
        {
            "schema": 1,
            "kind": "candidate",
            "fate": "survived",
            "score": 0.9,
            "family": MANDELBROT,
            "viewport": {"center_re": "0.1", "center_im": "0.0", "width": "1.0"},
            "maxiter": 800,
        },
        {
            "schema": 1,
            "kind": "candidate",
            "fate": "interior_cap",
            "score": None,
            "family": MANDELBROT,
            "viewport": {"center_re": "0.2", "center_im": "0.0", "width": "1.0"},
        },
    ]
    ledger.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    units = sheets.units_from_ledger(ledger)
    assert len(units) == 1
    assert units[0]["maxiter"] == 800


def test_units_come_off_a_stored_batch_at_its_current_verdict(store_dir, registered) -> None:
    known = registered("a_batch")
    store.append(
        [
            store.label_row(
                batch="a_batch",
                score=2,
                family=MANDELBROT,
                viewport={"center_re": "0.1", "center_im": "0.0", "width": "1.0"},
                render={"maxiter": 900},
            )
        ],
        known=known,
    )
    units = sheets.units_from_batch("a_batch")
    assert len(units) == 1
    assert units[0]["maxiter"] == 900


def test_a_location_plan_unit_short_of_its_cap_is_refused(tmp_path) -> None:
    """The head's view is addressed by a digest the cap is inside, so a unit
    without one is a fresh render of a picture the walk already scored."""
    plan = tmp_path / "plan.jsonl"
    plan.write_text(json.dumps({"family": MANDELBROT}) + "\n", encoding="utf-8")
    with pytest.raises(sheets.SheetError, match="viewport, maxiter"):
        sheets.units_from_location_plan(plan)


def test_a_location_plan_reads_back_the_units_it_holds(tmp_path) -> None:
    plan = tmp_path / "plan.jsonl"
    written = {**unit(3), "section": "the draw", "batch": "a_batch", "facts": ["rung 7"]}
    plan.write_text(json.dumps(written) + "\n", encoding="utf-8")
    assert sheets.units_from_location_plan(plan) == [written]


def test_a_plan_unit_short_of_the_recipe_is_refused_before_a_pixel_is_rendered(tmp_path) -> None:
    """A finished render is a place AND how it was colored. Finding that out at
    the writer, one row at a time, is finding it out after the render bill."""
    plan = tmp_path / "plan.jsonl"
    plan.write_text(json.dumps({"family": MANDELBROT, "maxiter": 500}) + "\n", encoding="utf-8")
    with pytest.raises(sheets.SheetError, match="viewport, mode"):
        sheets.units_from_plan(plan)


def test_a_plan_reads_back_the_units_it_holds(tmp_path) -> None:
    plan = tmp_path / "plan.jsonl"
    written = {
        "family": MANDELBROT,
        "viewport": {"center_re": "0.1", "center_im": "0.0", "width": "1.0"},
        "mode": "threads",
        "maxiter": 800,
        "section": "promotion draw",
    }
    plan.write_text(json.dumps(written) + "\n", encoding="utf-8")
    assert sheets.units_from_plan(plan) == [written]


# --------------------------------------------------------------------------- #
# The revision sheet: a plan that re-serves rows the store already holds.
# --------------------------------------------------------------------------- #
RECIPE = {
    "gamma": 1.25,
    "cycles": 2.0,
    "phase": 0.5,
    "reverse": True,
    "mirror": True,
    "transfer": {"kind": "edge", "weight": 2.0},
    "rolloff": {"kind": "soft_knee", "knee": 0.35},
}


def picture_stub(join, output, leveled=None):
    """A renderer that writes a real (tiny) picture, because thumbnails open it."""
    from PIL import Image

    del join, leveled
    output.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 5), (10, 20, 30)).save(output, "JPEG")


def finished_unit(index: int, **extra) -> dict:
    return {
        "family": MANDELBROT,
        "viewport": {"center_re": f"0.{index}", "center_im": "0.0", "width": "1.0"},
        "mode": "stripe",
        "maxiter": 500,
        "colormap": sheets.CANONICAL_COLORMAP,
        "recipe": dict(RECIPE),
        **extra,
    }


def finished_sheet(tmp_path, units, probabilities=None, **kwargs):
    scores = probabilities or [[0.9, 0.1]] * len(units)
    source = sheets.finished_source(
        "strange_render", renderer=picture_stub, scores=(scores, 3), **kwargs
    )
    return sheets.build(
        source,
        units,
        directory=tmp_path / "sheet",
        batch="a_sheet_name",
        log=lambda _: None,
    )


def test_a_plan_unit_carries_its_own_recipe_into_the_join(tmp_path) -> None:
    """A revision sheet re-serves a picture the store already holds, and a knob
    re-derived from defaults is a different picture and a different identity."""
    sheet = finished_sheet(tmp_path, [finished_unit(0)])
    assert sheet.rows[0]["join"]["recipe"] == RECIPE


def test_a_partial_recipe_is_refused_rather_than_topped_up(tmp_path) -> None:
    with pytest.raises(sheets.SheetError, match="names no phase"):
        sheets.stated_recipe({key: value for key, value in RECIPE.items() if key != "phase"})


def test_a_stated_recipe_without_a_map_is_refused(tmp_path) -> None:
    unit = finished_unit(0)
    unit.pop("colormap")
    with pytest.raises(sheets.SheetError, match="states a recipe and no colormap"):
        finished_sheet(tmp_path, [unit])


def test_a_plan_may_prefill_the_incumbent_verdict_the_head_cannot_reach(tmp_path) -> None:
    """A head with two cutpoints can never suggest a 4. On a re-judging pass the
    incumbent is the stored label, not the decode."""
    sheet = finished_sheet(tmp_path, [finished_unit(0, suggestion=4)])
    assert sheet.rows[0]["suggestion"] == 4
    assert sheet.manifest["suggested_by"] == "plan"
    assert sheet.manifest["scorer"] == "strange_render"


def test_a_head_prefilled_sheet_still_says_so(tmp_path) -> None:
    sheet = finished_sheet(tmp_path, [finished_unit(0)])
    assert sheet.rows[0]["suggestion"] == 2
    assert sheet.manifest["suggested_by"] == "strange_render"


def test_a_sheet_states_every_suggestion_or_none_of_them(tmp_path) -> None:
    """A page whose prefills mean two different things cannot be read back."""
    units = [finished_unit(0, suggestion=3), finished_unit(1)]
    with pytest.raises(sheets.SheetError, match="all of them or none"):
        finished_sheet(tmp_path, units, probabilities=[[0.9, 0.1], [0.2, 0.1]])


def test_a_suggestion_outside_the_scale_is_refused(tmp_path) -> None:
    with pytest.raises(sheets.SheetError, match="not one of"):
        finished_sheet(tmp_path, [finished_unit(0, suggestion=7)])


def test_a_revision_row_keeps_the_batch_it_was_drawn_from(tmp_path) -> None:
    """The sheet's own name is not a registration, and a row revised under it
    would silently change side, anchoring and draw method."""
    units = [finished_unit(0, batch="mode_sweep"), finished_unit(1, batch="rare_palette")]
    sheet = finished_sheet(tmp_path, units, probabilities=[[0.9, 0.1], [0.2, 0.1]])
    assert {row["batch"] for row in sheet.rows} == {"mode_sweep", "rare_palette"}
    assert sheet.manifest["batch"] == "a_sheet_name"
    assert sheet.manifest["batches"] == {"mode_sweep": 1, "rare_palette": 1}


def test_a_unit_that_names_no_batch_falls_back_to_the_sheet(tmp_path) -> None:
    sheet = finished_sheet(tmp_path, [finished_unit(0)])
    assert sheet.rows[0]["batch"] == "a_sheet_name"


def test_the_render_cache_is_reused_only_on_an_exact_spec(tmp_path, monkeypatch) -> None:
    """The cache names a picture by a digest of everything the engine is told, so
    a hit is the same picture and anything different at all is a miss."""
    from fractal_wallpapers.models import renders

    crops = tmp_path / "crops"
    crops.mkdir()
    monkeypatch.setattr(renders, "crop_dir", lambda head: crops)
    unit = finished_unit(0)
    plain = finished_sheet(tmp_path / "first", [unit], reuse_cache=True)
    assert plain.manifest["cut"] == {"reused_from_cache": 0, "rendered": 1}

    join = plain.rows[0]["join"]
    picture_stub(join, crops / f"{renders.job_name({**join, '_head': 'strange_render'})}.jpg")
    hit = finished_sheet(tmp_path / "second", [unit], reuse_cache=True)
    assert hit.manifest["cut"] == {"reused_from_cache": 1, "rendered": 0}
    missed = finished_sheet(tmp_path / "third", [finished_unit(1)], reuse_cache=True)
    assert missed.manifest["cut"] == {"reused_from_cache": 0, "rendered": 1}
