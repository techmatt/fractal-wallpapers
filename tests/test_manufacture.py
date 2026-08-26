"""The manufactured batch: what it aims at, what it draws, and what fills a quota.

The population here is made rather than found, so almost everything worth
guarding is a claim about *construction* — that the recipe is production's, that
a location appears once, that a quota is filled from what was measured on the
picture served rather than from what a map's ramp promised.

Nothing in this file renders. The build legs are the engine's and are exercised
by running them; what is pinned here is every decision taken either side of a
render.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from fractal_wallpapers.curation import manufacture
from fractal_wallpapers.labeling import finished

TARGETS = ("dark_muted_cyan", "dark_vivid_lime", "light_muted_green")


@pytest.fixture
def targets(monkeypatch):
    """A three-swatch codebook, so a quota table fits in an assertion."""
    monkeypatch.setattr(manufacture, "targets", lambda: TARGETS)
    return TARGETS


def screened(**extra) -> dict:
    row = {
        "attempt": 0,
        "kind": manufacture.SMOOTH,
        "arm": "new",
        "batch": manufacture.BATCH,
        "target": TARGETS[0],
        "key": "a_place",
        "family": {"kind": "mandelbrot"},
        "viewport": {"center_re": "0.1", "center_im": "0.0", "width": "1.0"},
        "maxiter": 500,
        "partition": "mandelbrot",
        "tier": manufacture.TIERS[0],
        "location_score": 3,
        "mode": "smooth",
        "colormap": "a_map",
        "mirror": False,
        "picture": "pictures/000000.jpg",
        "share": 0.30,
        "dominant": TARGETS[0],
        "entropy_bits": 2.0,
        "present": 3,
        "scores": {"p_ge2": 0.9, "p_ge3": 0.4, "p_ge4": 0.1, "rank_score": 1.4, "tier": 2},
        "error": None,
    }
    return {**row, **extra}


# --------------------------------------------------------------------------- #
# The recipe, which is the diagnostic's premise.
# --------------------------------------------------------------------------- #
def test_the_batch_draws_no_palette_knob_because_production_draws_none() -> None:
    """The whole hit-rate reading rests on this. A palette free to cycle and
    shift phase could put its colours almost anywhere; production's is pinned at
    the identity, so the only thing that moves across the batch is the fold — and
    that is read off the map rather than sampled."""
    note = manufacture.recipe_note()
    assert note["knobs"] == finished.recipe()
    assert note["sampled"] == []
    assert note["varied"] == ["mirror"]
    assert note["knobs"]["cycles"] == 1.0 and note["knobs"]["phase"] == 0.0


def test_a_unit_is_coloured_exactly_the_way_a_production_candidate_is() -> None:
    """`palette_sets.recipe_for` owns the fold rule, and a second spelling of it
    here would be a batch coloured differently from the pool it is compared to."""
    from fractal_wallpapers.models import palette_sets

    cyclic = {"a_cyclic_map"}
    for name, mirror in (("a_cyclic_map", False), ("a_sequential_map", True)):
        unit = manufacture._unit(screened(colormap=name, mirror=mirror))
        assert unit["recipe"] == palette_sets.recipe_for(name, cyclic)


# --------------------------------------------------------------------------- #
# The quotas.
# --------------------------------------------------------------------------- #
def test_every_kind_owes_the_same_rows_spread_evenly_over_the_targets(targets) -> None:
    quota = manufacture.quotas(rows_per_kind=30)
    for kind in manufacture.KINDS:
        assert sum(sum(arm.values()) for arm in quota[kind].values()) == 30
        assert set(quota[kind]) == set(targets)


def test_about_a_tenth_of_a_kind_is_the_contrast_arm(targets) -> None:
    quota = manufacture.quotas(rows_per_kind=30)
    contrast = sum(arm["contrast"] for arm in quota[manufacture.SMOOTH].values())
    assert contrast == round(30 * manufacture.CONTRAST_SHARE)


def test_a_remainder_that_will_not_divide_is_spread_and_never_zeroes_a_target(targets) -> None:
    """Through the supply engine's own apportionment: a swatch that got nothing
    is a swatch this batch does not manufacture, and that is a decision."""
    quota = manufacture.quotas(rows_per_kind=31)
    rows = [sum(arm.values()) for arm in quota[manufacture.SMOOTH].values()]
    assert sum(rows) == 31
    assert min(rows) > 0
    assert max(rows) - min(rows) <= 1


# --------------------------------------------------------------------------- #
# The mode draw.
# --------------------------------------------------------------------------- #
def test_the_smooth_kind_owns_one_mode_and_the_strange_kind_draws_production_s_two() -> None:
    assert manufacture.modes_of(manufacture.SMOOTH, "a_place", 0) == ["smooth"]
    drawn = manufacture.modes_of("strange_render", "a_place", 0)
    assert len(drawn) == manufacture.STRANGE_MODES
    assert len(set(drawn)) == len(drawn)
    assert "smooth" not in drawn


def test_the_mode_draw_is_the_one_a_run_takes_and_not_a_second_copy_of_it() -> None:
    """Reached through `colorize.modes_drawn_for`, so a change to the roster or
    to the draw reaches this batch instead of leaving it on the old one."""
    from fractal_wallpapers.curation import colorize

    class Plan:
        head = "strange_render"
        modes_drawn = manufacture.STRANGE_MODES
        key = "a_place"

    assert manufacture.modes_of("strange_render", "a_place", 7) == colorize.modes_drawn_for(
        Plan(), 7
    )


# --------------------------------------------------------------------------- #
# The two cuts, and where they are taken.
# --------------------------------------------------------------------------- #
def test_a_row_is_served_only_when_both_cuts_clear_on_the_sheet_render() -> None:
    assert manufacture.serves(screened())
    assert not manufacture.serves(screened(share=0.09))
    assert not manufacture.serves(
        screened(scores={"p_ge2": 0.4, "p_ge3": 0.1, "p_ge4": 0.0, "rank_score": 0.5, "tier": 1})
    )


def test_a_failed_render_is_not_served_and_is_not_a_zero() -> None:
    """A crash and a bad wallpaper must not be the same number: a row with no
    picture carries its error and no score at all."""
    failed = {**screened(), "picture": None, "scores": None, "error": "RuntimeError()"}
    assert not manufacture.serves(failed)
    assert not manufacture._passes_screen(failed)


def test_the_screen_is_generous_on_both_axes_and_the_acting_cut_is_not() -> None:
    """The screen decides what is worth measuring again at four times the pixels.
    Setting it at the acting height would be the acting cut taken at the geometry
    it is deliberately not taken at."""
    assert manufacture.SCREEN_SHARE < manufacture.REACHED
    assert manufacture.CONFIRM_PROBABILITY < manufacture.SCREEN_PROBABILITY
    marginal = screened(
        share=0.07,
        scores={"p_ge2": 0.3, "p_ge3": 0.1, "p_ge4": 0.0, "rank_score": 0.4, "tier": 1},
    )
    assert manufacture._passes_screen(marginal)
    assert not manufacture.serves(marginal)


# --------------------------------------------------------------------------- #
# The selection.
# --------------------------------------------------------------------------- #
def selection(tmp_path, monkeypatch, rows, targets_, rows_per_kind=6):
    monkeypatch.setattr(manufacture, "work_dir", lambda batch=None: tmp_path)
    monkeypatch.setattr(manufacture, "record_dir", lambda batch=None: tmp_path / "record")
    monkeypatch.setattr(manufacture, "targets", lambda: targets_)
    manufacture._write_jsonl(tmp_path / "confirmed.jsonl", rows)
    monkeypatch.setattr(
        manufacture, "confirmed_path", lambda batch=None: tmp_path / "confirmed.jsonl"
    )
    monkeypatch.setattr(
        manufacture, "sheet_plan_path", lambda kind, batch=None: tmp_path / f"{kind}.jsonl"
    )
    return manufacture.select(rows_per_kind=rows_per_kind, log=lambda _: None)


def written_units(tmp_path) -> list[dict]:
    """The smooth sheet's plan, as `label build --from-plan` would read it."""
    text = (tmp_path / "smooth_render.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line]


def offered(count: int, **extra) -> list[dict]:
    return [
        screened(attempt=index, key=f"place_{index}", share=0.5 - index * 0.01, **extra)
        for index in range(count)
    ]


def test_no_more_than_the_cap_of_a_sheet_s_rows_come_through_one_map(tmp_path, monkeypatch) -> None:
    rows = offered(12)
    summary = selection(tmp_path, monkeypatch, rows, (TARGETS[0],), rows_per_kind=12)
    written = [
        json.loads(line) for line in (tmp_path / "smooth_render.jsonl").read_text().splitlines()
    ]
    assert len(written) == manufacture.ROWS_PER_MAP
    assert summary["capped_out"] == 12 - manufacture.ROWS_PER_MAP
    assert summary["rows_per_map"]["distribution"] == {str(manufacture.ROWS_PER_MAP): 1}


def test_a_quota_is_filled_by_what_the_picture_held_and_not_by_what_the_head_thought(
    tmp_path, monkeypatch
) -> None:
    """The tier cut has already removed everything a person would not be asked
    about. Ranking the survivors by the head's own score would enrich the sheet a
    third time, on the axis the sheet exists to correct."""
    rows = [
        screened(
            attempt=0,
            key="dull_colour_great_score",
            share=0.11,
            colormap="one",
            scores={"p_ge2": 1.0, "p_ge3": 0.9, "p_ge4": 0.8, "rank_score": 2.7, "tier": 4},
        ),
        screened(
            attempt=1,
            key="rich_colour_plain_score",
            share=0.60,
            colormap="two",
            scores={"p_ge2": 0.6, "p_ge3": 0.1, "p_ge4": 0.0, "rank_score": 0.7, "tier": 2},
        ),
    ]
    selection(tmp_path, monkeypatch, rows, (TARGETS[0],), rows_per_kind=1)
    written = [
        json.loads(line) for line in (tmp_path / "smooth_render.jsonl").read_text().splitlines()
    ]
    assert [unit["colormap"] for unit in written] == ["two"]


def test_a_cell_that_cannot_be_filled_is_reported_short_rather_than_padded(
    tmp_path, monkeypatch
) -> None:
    summary = selection(tmp_path, monkeypatch, offered(2), (TARGETS[0],), rows_per_kind=6)
    # Five new rows and one contrast row are owed per kind; two new smooth rows
    # were offered and nothing else was, so every other cell is short too.
    assert summary["shortfall"][f"smooth_render/{TARGETS[0]}/new"] == 3
    assert summary["shortfall"][f"strange_render/{TARGETS[0]}/new"] == 5
    assert summary["rows"][manufacture.SMOOTH] == 2


def test_a_selected_row_states_its_whole_recipe_and_its_map(tmp_path, monkeypatch) -> None:
    """A plan unit that let the sheet re-pick either would be a different picture
    from the one both cuts were taken on."""
    from fractal_wallpapers.labeling import sheets

    selection(tmp_path, monkeypatch, offered(1), (TARGETS[0],), rows_per_kind=1)
    units = sheets.units_from_plan(tmp_path / "smooth_render.jsonl")
    assert sheets.stated_recipe(units[0]["recipe"]) == finished.recipe()
    assert units[0]["colormap"] == "a_map"
    assert finished.render_key(units[0]) is not None


def test_every_row_carries_the_manufacture_stamp_and_its_arm(tmp_path, monkeypatch) -> None:
    """The batch name is the stamp, and it is what separates forced supply from
    free supply in a census or a preference read."""
    rows = offered(1) + offered(1, arm="contrast", batch=manufacture.CONTRAST_BATCH)
    rows[1]["attempt"], rows[1]["key"] = 5, "another_place"
    selection(tmp_path, monkeypatch, rows, (TARGETS[0],), rows_per_kind=6)
    units = [
        json.loads(line) for line in (tmp_path / "smooth_render.jsonl").read_text().splitlines()
    ]
    assert {unit["batch"] for unit in units} == {manufacture.BATCH, manufacture.CONTRAST_BATCH}


def test_the_tracked_record_joins_to_the_store_on_the_render_identity(
    tmp_path, monkeypatch
) -> None:
    """A store row carries the place, the recipe and the verdict, and not which
    target this was manufactured for. That lives here, keyed on the identity a
    verdict is cast on."""
    selection(tmp_path, monkeypatch, offered(1), (TARGETS[0],), rows_per_kind=1)
    kept = [
        json.loads(line)
        for line in (tmp_path / "record" / f"{manufacture.SMOOTH}.jsonl").read_text().splitlines()
    ]
    units = [
        json.loads(line) for line in (tmp_path / "smooth_render.jsonl").read_text().splitlines()
    ]
    assert kept[0]["target"] == TARGETS[0]
    assert kept[0]["tier"] == manufacture.TIERS[0]
    assert kept[0]["render_key"] == json.loads(json.dumps(finished.render_key(units[0])))


# --------------------------------------------------------------------------- #
# The diagnostic.
# --------------------------------------------------------------------------- #
def test_the_hit_rate_counts_locations_and_never_attempts(tmp_path, monkeypatch) -> None:
    """The number Matt asked for is the per-LOCATION rate. One location tried
    four ways and reaching the swatch once is a hit, not a quarter of one — the
    map-by-cell count is a different question and answers it differently."""
    rows = [
        screened(attempt=index, key="one_place", share=share)
        for index, share in enumerate((0.01, 0.02, 0.30, 0.03))
    ]
    monkeypatch.setattr(manufacture, "screened_path", lambda batch=None: tmp_path / "s.jsonl")
    manufacture._write_jsonl(tmp_path / "s.jsonl", rows)
    read = manufacture.hit_rate()
    assert read[TARGETS[0]] == {
        "locations": 1,
        "reached": 1,
        "rate": 1.0,
        "attempts": 4,
        "best_share": 0.3,
        "median_share": 0.3,
        "by_arm": {"new": {"locations": 1, "rate": 1.0}},
        "probable_defect": False,
    }


def test_a_swatch_more_than_half_of_whose_locations_fail_is_flagged(tmp_path, monkeypatch) -> None:
    """Matt's rule: a palette that cannot reach a colour on most good places is
    more likely a defect in what was asked for than a fact about the places."""
    rows = [
        screened(attempt=index, key=f"place_{index}", share=share)
        for index, share in enumerate((0.5, 0.01, 0.01, 0.01))
    ]
    monkeypatch.setattr(manufacture, "screened_path", lambda batch=None: tmp_path / "s.jsonl")
    manufacture._write_jsonl(tmp_path / "s.jsonl", rows)
    assert manufacture.hit_rate()[TARGETS[0]]["probable_defect"]


# --------------------------------------------------------------------------- #
# The ordering that makes the whole thing readable afterwards.
# --------------------------------------------------------------------------- #
def test_nothing_is_planned_until_every_batch_is_registered(monkeypatch) -> None:
    """`store.append` refuses an unregistered row, but that is at ingest — after
    the whole build has been paid for. This fails closed before the first pixel."""
    from fractal_wallpapers.labeling import finished as finished_module

    monkeypatch.setattr(finished_module, "registry", lambda head: {})
    with pytest.raises(manufacture.ManufactureError, match="not registered"):
        manufacture.registered()


def test_both_arms_are_train_side_and_neither_is_an_instrument() -> None:
    """Model- and construction-conditioned on every axis: the extension tier is
    ranked on the location head, every map comes off the coverage read, and the
    page prefills the render judge's own decode."""
    from fractal_wallpapers.labeling import registry as registry_module

    for batch, method in manufacture.METHODS.items():
        registration = registry_module.Registration(
            batch=batch, method=method, score_unconditioned=False, anchored=True
        )
        assert registration.side == "train"
        assert not registration.eval_eligible


# --------------------------------------------------------------------------- #
# The counterfactual the diagnostic asks about.
# --------------------------------------------------------------------------- #
def test_the_knob_grid_opens_at_the_recipe_production_actually_uses() -> None:
    """The probe measures what exploring would have bought, so its first cell has
    to be not-exploring. A grid that opened anywhere else would report a gain
    against a baseline no row was ever built at."""
    assert manufacture.KNOB_GRID[0] == (1.0, 0.0)
    identity = finished.recipe()
    assert (identity["cycles"], identity["phase"]) == manufacture.KNOB_GRID[0]
    assert len(set(manufacture.KNOB_GRID)) == len(manufacture.KNOB_GRID)


@pytest.mark.slow
def test_the_probe_says_so_rather_than_returning_a_zero_when_it_can_sweep_nothing(
    tmp_path, monkeypatch
) -> None:
    """Only a cyclic map has these knobs and only a field mode has a dumped field
    to sweep. A probe with neither has no reading, which is not the same as a
    reading of nought."""
    monkeypatch.setattr(manufacture, "work_dir", lambda batch=None: tmp_path)
    monkeypatch.setattr(manufacture, "screened_path", lambda batch=None: tmp_path / "s.jsonl")
    manufacture._write_jsonl(tmp_path / "s.jsonl", [screened(share=0.5)])
    with pytest.raises(manufacture.ManufactureError, match="nothing for the knob probe"):
        manufacture.probe_knobs()


# --------------------------------------------------------------------------- #
# The extension a short quota reaches for.
# --------------------------------------------------------------------------- #
def location(index: int, tier: str = manufacture.TIERS[0]) -> dict:
    return {
        "key": f"spare_{index}",
        "family": {"kind": "mandelbrot"},
        "viewport": {"center_re": f"0.{index}", "center_im": "0.0", "width": "1.0"},
        "maxiter": 500,
        "partition": "mandelbrot",
        "tier": tier,
        "score": 3,
    }


def planned(tmp_path, monkeypatch, shortfall, people, admitted):
    monkeypatch.setattr(manufacture, "work_dir", lambda batch=None: tmp_path)
    monkeypatch.setattr(manufacture, "plan_path", lambda batch=None: tmp_path / "plan.json")
    monkeypatch.setattr(manufacture, "attempts_path", lambda batch=None: tmp_path / "a.jsonl")
    monkeypatch.setattr(manufacture, "targets", lambda: TARGETS)
    monkeypatch.setattr(manufacture, "human_locations", lambda: list(people))
    monkeypatch.setattr(manufacture, "admitted_locations", lambda exclude: list(admitted))
    monkeypatch.setattr(
        manufacture,
        "carriers",
        lambda: ({TARGETS[0]: ["m0", "m1", "m2"]}, {TARGETS[0]: ["lib0", "lib1"]}),
    )
    manufacture._write_json(
        tmp_path / "plan.json",
        {"seed": 0, "locations": {"wanted": 1, "human_q3": 1, "admitted": 0}, "attempts": 1},
    )
    manufacture._write_jsonl(tmp_path / "a.jsonl", [screened(attempt=0, key="already_used")])
    manufacture._write_json(tmp_path / "selection.json", {"shortfall": shortfall})
    return manufacture.top_up(oversample=1.0, log=lambda _: None)


def test_a_short_quota_takes_more_of_the_preferred_tier_before_the_extension(
    tmp_path, monkeypatch
) -> None:
    """A batch that jumped to the admitted supply while labelled keepers sat
    unused would be reporting a tier split about its own draw order."""
    people = [location(index) for index in range(4)]
    admitted = [location(9, manufacture.TIERS[1])]
    planned(tmp_path, monkeypatch, {f"smooth_render/{TARGETS[0]}/new": 2}, people, admitted)
    added = [row for row in manufacture._read_jsonl(tmp_path / "a.jsonl") if row.get("top_up")]
    assert {row["tier"] for row in added} == {manufacture.TIERS[0]}
    assert len({row["key"] for row in added}) == 2


def test_the_extension_is_reached_for_when_the_preferred_tier_runs_out(
    tmp_path, monkeypatch
) -> None:
    people = [location(0)]
    admitted = [location(index, manufacture.TIERS[1]) for index in range(5, 9)]
    planned(tmp_path, monkeypatch, {f"smooth_render/{TARGETS[0]}/new": 3}, people, admitted)
    added = [row for row in manufacture._read_jsonl(tmp_path / "a.jsonl") if row.get("top_up")]
    assert {row["tier"] for row in added} == set(manufacture.TIERS)


def test_a_top_up_appends_and_never_renumbers_an_attempt(tmp_path, monkeypatch) -> None:
    """Every built group's record is keyed on the attempt ids it holds, so a
    renumbering would throw away the whole screen and rebuild it."""
    people = [location(index) for index in range(4)]
    planned(tmp_path, monkeypatch, {f"smooth_render/{TARGETS[0]}/new": 1}, people, [])
    rows = manufacture._read_jsonl(tmp_path / "a.jsonl")
    assert rows[0]["attempt"] == 0 and rows[0]["key"] == "already_used"
    assert [row["attempt"] for row in rows] == list(range(len(rows)))
    assert "already_used" not in {row["key"] for row in rows if row.get("top_up")}


def test_a_plan_with_nothing_short_is_left_exactly_as_it_was(tmp_path, monkeypatch) -> None:
    planned(tmp_path, monkeypatch, {}, [location(0)], [])
    assert len(manufacture._read_jsonl(tmp_path / "a.jsonl")) == 1


# --------------------------------------------------------------------------- #
# The claim only a comparison can settle.
# --------------------------------------------------------------------------- #
def built(tmp_path, monkeypatch, served_picture: bytes, cut_on_picture: bytes, columns=None):
    """A one-row sheet beside the confirm leg that is supposed to have made it."""
    monkeypatch.setattr(manufacture, "work_dir", lambda batch=None: tmp_path / "work")
    monkeypatch.setattr(
        manufacture, "confirmed_path", lambda batch=None: tmp_path / "confirmed.jsonl"
    )
    row = screened(picture="pictures/000000.jpg")
    manufacture._write_jsonl(tmp_path / "confirmed.jsonl", [row])
    made = tmp_path / "work" / "sheet" / "pictures"
    made.mkdir(parents=True)
    (made / "000000.jpg").write_bytes(cut_on_picture)

    sheet = tmp_path / "sheet"
    (sheet / "full").mkdir(parents=True)
    (sheet / "full" / "cut0000.jpg").write_bytes(served_picture)
    (sheet / "sheet.json").write_text("{}", encoding="utf-8")
    unit = manufacture._unit(row)
    join = {
        "family": unit["family"],
        "viewport": unit["viewport"],
        "mode": unit["mode"],
        "mode_params": {},
        "curve": unit["curve"],
        "colormap": unit["colormap"],
        "recipe": unit["recipe"],
    }
    manufacture._write_jsonl(
        sheet / "sheet.jsonl",
        [
            {
                "unit": "u0001",
                "join": join,
                "pictures": [{"path": "full/cut0000.jpg"}],
                "columns": columns if columns is not None else {"p_ge2": 0.9},
            }
        ],
    )
    return manufacture.verify(sheet)


def test_the_sheet_is_proved_to_serve_the_picture_the_cuts_were_taken_on(
    tmp_path, monkeypatch
) -> None:
    held = built(tmp_path, monkeypatch, b"the same bytes", b"the same bytes")
    assert held == {
        "sheet": str(tmp_path / "sheet"),
        "rows": 1,
        "identical": 1,
        "different": 0,
        "unmatched": 0,
        "worst_score_gap": 0.0,
        "held": True,
    }


def test_a_sheet_that_re_rendered_something_else_is_caught_rather_than_trusted(
    tmp_path, monkeypatch
) -> None:
    """The failure this exists for: a unit that lost the levelled colormap's name
    renders through the map as it was before the operator touched it, which is a
    different picture carrying the same join."""
    held = built(tmp_path, monkeypatch, b"unlevelled", b"levelled")
    assert held["different"] == 1 and not held["held"]


def test_the_two_readings_of_the_judge_are_compared_and_not_assumed(tmp_path, monkeypatch) -> None:
    held = built(tmp_path, monkeypatch, b"same", b"same", columns={"p_ge2": 0.5})
    assert held["worst_score_gap"] == pytest.approx(0.4)


def test_a_recolor_states_the_curve_a_render_of_the_same_row_would_force(
    tmp_path, monkeypatch
) -> None:
    """The one defect `verify` caught. A dumped field records the curve it was
    dumped under — the MODE's own — while `renders.coloring_of` writes
    `colorize.CURVE` over the mode's on every render. `trap_circle` names `log`
    and every other production field mode names `linear`, so a recolor that
    inherited the dump's curve produced a different picture from the render of
    the same row, for that one mode and no other."""
    from fractal_wallpapers import engine, paths
    from fractal_wallpapers.coloring import autolevel
    from fractal_wallpapers.curation import colorize
    from fractal_wallpapers.models import renders

    catalog = renders.catalog()
    field_modes = [m for m in engine.production_modes() if catalog[m]["kind"] == "field"]
    named = {catalog[mode]["transform"] for mode in field_modes}
    assert named == {"linear", "log"}, named
    assert [m for m in field_modes if catalog[m]["transform"] != colorize.CURVE] == ["trap_circle"]

    maps = tmp_path / "maps"
    maps.mkdir()
    (maps / "a_map.json").write_text(
        json.dumps({"schema": 1, "name": "a_map", "kind": "sequential", "stops": []}),
        encoding="utf-8",
    )
    monkeypatch.setattr(paths, "colormap_dir", lambda: maps)
    monkeypatch.setattr(autolevel, "enabled", lambda: False)
    seen = []

    def recolor(spec):
        seen.append(spec)
        pathlib.Path(spec["output"]).write_bytes(b"a picture")

    monkeypatch.setattr(engine, "recolor", recolor)

    picture = tmp_path / "out.jpg"
    manufacture._leveled_recolor(tmp_path / "a.f32", "a_map", False, picture, None)
    assert seen and seen[0]["transform"] == colorize.CURVE
    assert picture.read_bytes() == b"a picture"
