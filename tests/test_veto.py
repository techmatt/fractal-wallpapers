"""The veto: a human `1` at the fine level, and the four ways it could go wrong.

Every other refusal in this project is a reading of a number and comes back when
the number moves. This one is permanent, so what is pinned here is the four
properties that keep it from reaching further than a person meant:

* only a **human** label vetoes — a rule-written row or a model score does not;
* the store's **latest-wins** answer is the veto's, so a 1 can be taken back;
* it is **row-level** — the exact candidate, never the place, the mode or the map;
* a **synthetic pool** reads no store, which is what keeps a guard's three rows
  from being swept against this machine's real corpus.

The fifth is the sheet's and it is the one that matters most: a rejection pass
must not be able to manufacture a verdict for a tile nobody marked.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fractal_wallpapers import paths
from fractal_wallpapers.curation import solve, veto
from fractal_wallpapers.labeling import finished, gallery_grade, sheets, store

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The judge the pool fixtures are read on. [`solve.pool`] joins the sidecar on
#: one artifact, so a fixture that left it off would test a join that cannot
#: happen.
ARTIFACT = "judge-under-test"


def quiet(*_args, **_rest) -> None:
    """A `log` that says nothing."""


# --------------------------------------------------------------------------- #
# One picture, spelled the two ways the join has to cross.
# --------------------------------------------------------------------------- #
def a_recipe(colormap: str = "twilight_shifted", mode: str = "smooth", **changes) -> dict:
    """The recipe half of one picture, in the shape a LEDGER row carries it."""
    recipe = {
        "family": {"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]},
        "viewport": {"center_re": "0.1", "center_im": "0.2", "width": "0.5"},
        "mode": mode,
        "mode_params": {},
        "curve": "linear",
        "colormap": colormap,
        "palette": finished.recipe(),
        "maxiter": 8000,
    }
    recipe.update(changes)
    return recipe


def a_label(recipe: dict, grade: int = 1, origin: str = store.HUMAN, **changes) -> dict:
    """The same picture as a GALLERY-GRADE row, off the same recipe dictionary.

    Built from the ledger shape rather than restated, so a test that says *these
    two are one picture* is saying it about one set of values. A test that typed
    the join twice would pass on its own typo.
    """
    fields = {
        "batch": "a_batch",
        "grade": grade,
        "origin": origin,
        "family": recipe["family"],
        "viewport": recipe["viewport"],
        "mode": recipe["mode"],
        "mode_params": recipe["mode_params"],
        "curve": recipe["curve"],
        "colormap": recipe["colormap"],
        "recipe_": recipe["palette"],
        "render": {
            "resolution": [1280, 720],
            "supersample": 2,
            "maxiter": 8000,
            "filter": "lanczos3",
        },
        "recorded_at": "2026-09-14T00:00:00Z",
    }
    fields.update(changes)
    return gallery_grade.grade_row(**fields)


@pytest.fixture(autouse=True)
def artifacts_on_disk(tmp_path, monkeypatch):
    """A hot root a fixture can plant a picture in — [`solve.pool`] opens the file."""
    root = tmp_path / "artifacts"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv(paths.HOT_ROOT_VARIABLE, str(root))
    return root


def ledger_row(key: str, recipe: dict, **overrides) -> dict:
    """One ledger row around a recipe, with its picture planted."""
    made = paths.hot_root() / f"{key}.jpg"
    made.parent.mkdir(parents=True, exist_ok=True)
    made.touch()
    row = {
        "key": key,
        "partition": "julia:mandelbrot",
        "location": {"key": f"place-{key}"},
        "recipe": recipe,
        "at_candidate_regime": True,
        "colour": {"cells": ["dark_vivid_blue"], "families": ["blue"]},
        "picture": f"artifacts/{key}.jpg",
        "rejected": None,
    }
    row.update(overrides)
    return row


def score_row(key: str, p_ge4: float = 0.9) -> dict:
    return {
        "recipe_key": key,
        "p_ge4": p_ge4,
        "p_ge3": 0.99,
        "head": "smooth_render",
        "judge_artifact": ARTIFACT,
    }


# --------------------------------------------------------------------------- #
# What vetoes, and what does not.
# --------------------------------------------------------------------------- #
def test_a_human_one_vetoes_and_a_rules_one_does_not() -> None:
    """A verdict a rule wrote is a derivation this project can run again.

    A person's is not, which is the whole reason the label store keeps the two
    origins apart — and a veto derived from a rule would be a permanent exclusion
    nobody chose, reachable by editing a threshold.
    """
    human = a_recipe(colormap="human_map")
    ruled = a_recipe(colormap="ruled_map")
    vetoed = veto.render_keys(
        [a_label(human), a_label(ruled, origin=f"{store.RULE_PREFIX}interior")]
    )
    assert gallery_grade.render_key(a_label(human)) in vetoed
    assert gallery_grade.render_key(a_label(ruled)) not in vetoed


def test_only_the_lowest_ordinal_vetoes() -> None:
    """A 2 is *just above the bar* and is a keeper. The veto reads the store's own 1."""
    graded = [a_recipe(colormap=f"map_{grade}") for grade in gallery_grade.SCALE]
    vetoed = veto.render_keys(
        [
            a_label(recipe, grade=grade)
            for recipe, grade in zip(graded, gallery_grade.SCALE, strict=True)
        ]
    )
    assert {key[4] for key in vetoed} == {"map_1"}
    assert gallery_grade.SCALE[0] == veto.VETO_GRADE


def test_a_one_taken_back_is_not_a_veto_any_more() -> None:
    """Latest-wins is the store's rule and it is the veto's.

    The alternative — any 1 ever cast — would make this the one thing in the
    project a person cannot undo, and undoing it would mean editing an
    append-only store.
    """
    recipe = a_recipe()
    early, late = "2026-09-01T00:00:00Z", "2026-09-02T00:00:00Z"

    def cast(first: int, second: int) -> dict:
        return veto.render_keys(
            [
                a_label(recipe, grade=first, recorded_at=early),
                a_label(recipe, grade=second, recorded_at=late),
            ]
        )

    assert cast(1, 3) == {}
    # The clock and not the file order: `resolve` sorts on `recorded_at`, so the
    # two verdicts have to swap TIMES rather than positions for this to be a test
    # of latest-wins at all.
    assert cast(3, 1) != {}


def test_the_veto_is_the_row_and_not_the_place_the_mode_or_the_map() -> None:
    """A neighbouring palette at the same location is a different picture.

    That is the gallery-grade store's whole estimand — two rows of one place can
    be a 1 and a 4 — so a veto that reached the place would throw away the axis
    the corpus exists to read.
    """
    bad = a_recipe(colormap="the_bad_one")
    siblings = {
        "same place, another map": a_recipe(colormap="another_map"),
        "same map, another mode": a_recipe(colormap="the_bad_one", mode="stripe"),
        "same everything, another frame": a_recipe(
            colormap="the_bad_one",
            viewport={"center_re": "0.9", "center_im": "0.2", "width": "0.5"},
        ),
    }
    vetoed = veto.render_keys([a_label(bad)])
    assert veto.refuses(ledger_row("bad", bad), vetoed)
    for what, recipe in siblings.items():
        assert not veto.refuses(ledger_row("sibling", recipe), vetoed), what


# --------------------------------------------------------------------------- #
# Where it acts: one door, and one that stays shut for a synthetic pool.
# --------------------------------------------------------------------------- #
def test_the_pool_refuses_a_vetoed_row_and_counts_it_apart() -> None:
    """`vetoed` is its own counter beside `rejected` and not folded into it.

    They are two different acts — a rejection travels on the ledger row, a veto is
    derived from the label store — and a pool that reported one number could not
    say which had grown.
    """
    bad, good = a_recipe(colormap="the_bad_one"), a_recipe(colormap="a_good_one")
    rows = [ledger_row("bad", bad), ledger_row("good", good)]
    candidates, refused = solve.pool(
        rows=rows,
        scores=[score_row("bad"), score_row("good")],
        artifact=ARTIFACT,
        vetoed=veto.render_keys([a_label(bad)]),
        log=quiet,
    )
    assert [candidate.key for candidate in candidates] == ["good"]
    assert refused["vetoed"] == 1
    assert refused["rejected"] == 0


def test_a_pool_built_from_handed_in_rows_reads_no_label_store() -> None:
    """The isolation rule, and it is [`solve.pool`]'s `spirals` argument's.

    A store reached unconditionally from production code is a store a guard's
    fixture cannot redirect, and every test in this file that built three rows in
    `tmp_path` would sweep this machine's real corpus instead — at 0.14 s a call,
    growing with the corpus. A caller that hands its own rows is building its own
    pool, and a pool of synthetic recipes has nothing in the real store to find.
    """
    recipe = a_recipe()
    read: list[int] = []

    def refuse() -> dict:
        read.append(1)
        raise AssertionError("the label store was read for a pool the caller handed rows to")

    import unittest.mock

    with unittest.mock.patch.object(veto, "render_keys", refuse):
        candidates, refused = solve.pool(
            rows=[ledger_row("a", recipe)],
            scores=[score_row("a")],
            artifact=ARTIFACT,
            log=quiet,
        )
    assert not read
    assert [candidate.key for candidate in candidates] == ["a"]
    assert refused["vetoed"] == 0


def test_the_census_hands_the_veto_through_when_it_reads_the_ledger_itself() -> None:
    """[`headroom.population`] is [`solve.pool`]'s population BY DEFINITION.

    It always hands its own `rows`, so the rule above would leave it counting
    headroom a solve cannot reach — which is exactly the wrong pool the function's
    own docstring refuses to census. The line that fixes it is easy to lose in a
    refactor and impossible to notice without this.
    """
    source = (REPO_ROOT / "src" / "fractal_wallpapers" / "curation" / "headroom.py").read_text(
        encoding="utf-8"
    )
    assert "vetoed = set(veto_module.render_keys()) if rows is None else None" in source
    assert "vetoed=vetoed" in source


def test_a_vetoed_row_still_trains_the_head_it_was_cast_for() -> None:
    """The veto is a CONSUMER of labels and never a filter on them.

    A `1` is the most informative row the fine head has — it is the case the head
    got wrong badly enough for a person to say so — and a training population that
    dropped the vetoed rows would be a head fitted on its own successes. The two
    directions are unrelated and must stay so, which is enforceable in exactly one
    place: nothing under `models/` may reach this module. If a fit ever needs to
    know, it is a different question and gets a different name.
    """
    models = REPO_ROOT / "src" / "fractal_wallpapers" / "models"
    reaching = sorted(
        path.name
        for path in models.glob("*.py")
        if "curation import veto" in path.read_text(encoding="utf-8")
        or "curation.veto" in path.read_text(encoding="utf-8")
    )
    assert not reaching, (
        f"{reaching} reaches `curation.veto`. A vetoed row is an ordinary human label on the "
        f"ordinary path and trains exactly as any other does; a fit that filtered on the veto "
        f"would be fitted on its own successes"
    )


# --------------------------------------------------------------------------- #
# The rejection sheet: an unmarked tile is not a label.
# --------------------------------------------------------------------------- #
def test_a_rejection_sheet_turns_the_sweep_off() -> None:
    """THE property. The sweep is the one gesture that casts for a row nobody read.

    Every other path already refuses — the page exports only what was acted on,
    and [`labeling.intake.read_export`] drops a null — so one click on a
    thousand-tile gallery sheet is the whole exposure: nine hundred manufactured
    positives, `origin: human`, indistinguishable from labels a person cast.
    """
    correction = sheets.gallery_grade_source(prefilled=True)
    rejection = sheets.gallery_grade_source(prefilled=True, rejection=True)
    assert correction.sweep is True
    assert rejection.sweep is False


def test_a_rejection_page_says_what_it_is_rather_than_looking_like_a_correction() -> None:
    """A page identical to a correction page is one a labeler sweeps out of habit."""
    note = sheets.gallery_grade_source(prefilled=True, rejection=True).prefill_note
    assert note == sheets.GRADE_REJECTION_NOTE
    assert "NOT a label" in note
    assert "no sweep" in note


def test_a_blind_rejection_sheet_is_refused() -> None:
    """A rejection pass is a correction page whose population is not being reviewed.

    Blind, it would ask a person to walk a thousand shuffled tiles with nothing
    saying which end is worth their attention.
    """
    with pytest.raises(sheets.SheetError, match="prefilled and score-ordered"):
        sheets.gallery_grade_source(prefilled=False, rejection=True)


def test_the_page_refuses_the_sweep_and_does_not_merely_hide_it() -> None:
    """Both halves, because hiding a control is a statement about one page.

    Refusing the act is a statement about the sheet, and the two are not the same
    guarantee: a cached page, a stale tab or a console is enough to reach a hidden
    button. `!== false` is the third assertion — every sheet cut before the key
    existed is a correction sheet and keeps its sweep.
    """
    page = (REPO_ROOT / "src" / "fractal_wallpapers" / "labeling" / "page.html").read_text(
        encoding="utf-8"
    )
    assert 'el("sweep").hidden = MANIFEST.sweep === false' in page
    assert "if (MANIFEST.sweep === false) {" in page
    assert page.count("MANIFEST.sweep === false") == 2


def test_the_manifest_says_whether_the_sweep_is_there_on_every_sheet(tmp_path) -> None:
    """Written always and not only when it is off.

    A sheet cut for a rejection pass and a sheet cut before the flag existed are
    different sheets, and a key that appears only sometimes is the one a reader
    misses.
    """
    built = _built(tmp_path, rejection=True)
    assert built.manifest["sweep"] is False
    assert _built(tmp_path / "other", rejection=False).manifest["sweep"] is True


def test_a_rejection_sheet_still_casts_the_whole_scale(tmp_path) -> None:
    """A deliberate 2 is a real verdict and the store wants it.

    What the mode forbids is casting for rows nobody looked at, which is a
    different act from casting a tier that is not 1. Narrowing the page to one
    button would throw away information a labeler was willing to give.
    """
    assert _built(tmp_path, rejection=True).manifest["tiers"] == list(gallery_grade.tiers())


def _built(directory: Path, rejection: bool):
    """One two-unit gallery-grade sheet, rendered by a stub rather than the engine."""
    units = [
        {
            "family": {"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]},
            "viewport": {"center_re": "0.1", "center_im": f"0.{index}", "width": "0.5"},
            "maxiter": 8000,
            "mode": "smooth",
            "mode_params": {},
            "curve": "linear",
            "colormap": "twilight_shifted",
            "recipe": finished.recipe(),
            "suggestion": 4,
            "suggestion_score": 3.5 - index,
            "batch": "a_batch",
        }
        for index in (1, 2)
    ]
    source = sheets.gallery_grade_source(
        renderer=_plant,
        scores=([[0.9, 0.8, 0.7]] * len(units), 4),
        prefilled=True,
        rejection=rejection,
    )
    return sheets.build(source, units, directory=Path(directory), batch="a_batch", log=quiet)


def _plant(_join, output: Path, _colormaps=None) -> None:
    """A renderer that writes a real 8x8 JPEG, because the cut takes a thumbnail."""
    from PIL import Image

    output.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), (30, 40, 50)).save(output, "JPEG")


# --------------------------------------------------------------------------- #
# The plan, and the readouts over a record.
# --------------------------------------------------------------------------- #
def test_a_rejection_plan_keeps_the_seats_that_already_carry_a_verdict(tmp_path) -> None:
    """The store is latest-wins, so a second pass has to be able to change its mind.

    A plan that dropped the graded seats would make the sheet a one-way ratchet:
    a picture rejected in error could never be un-rejected from the pass that
    rejects, which is the only pass anybody runs over a gallery.
    """
    import unittest.mock

    from fractal_wallpapers.curation import candidate_ledger, tentative

    recipes = {key: a_recipe(colormap=f"map_{key}") for key in ("seat_a", "seat_b")}
    rows = [ledger_row(key, recipe) for key, recipe in recipes.items()]
    seats = [
        {"key": key, "seat": index, "p_ge4": 0.9, "rank": 2.0, "seated_for": "general_pool"}
        for index, key in enumerate(recipes)
    ]
    with (
        unittest.mock.patch.object(tentative, "read_rows", lambda _stamp: seats),
        unittest.mock.patch.object(candidate_ledger, "stream", lambda: iter(rows)),
    ):
        units, record = veto.plan("a_stamp", fine={}, log=quiet)
    assert record["units"] == 2
    assert [unit["colormap"] for unit in units] == ["map_seat_a", "map_seat_b"]
    # No decode anywhere, so no prefill anywhere — and `None` and not a zero.
    assert {unit["suggestion"] for unit in units} == {None}
    assert {unit["suggestion_score"] for unit in units} == {None}
    assert all(unit["seated"] is True and unit["refusal"] is None for unit in units)


@pytest.mark.parametrize(
    ("reading", "expected"),
    [
        ({"p_ge2": 0.9, "p_ge3": 0.9, "p_ge4": 0.9, "rank_score": 3.7}, (4, 3.7)),
        ({"p_ge2": 0.9, "p_ge3": 0.9, "p_ge4": 0.1, "rank_score": 2.9}, (3, 2.9)),
        ({"p_ge2": 0.9, "p_ge3": 0.1, "p_ge4": 0.1, "rank_score": 2.1}, (2, 2.1)),
        ({"p_ge2": 0.1, "p_ge3": 0.1, "p_ge4": 0.1, "rank_score": 1.3}, (1, 1.3)),
        ({}, (None, None)),
    ],
)
def test_a_prefill_is_the_highest_tier_the_column_puts_at_even_odds(reading, expected) -> None:
    """The decode `gallery_top_20260910`'s own sheet read this column with.

    It needs no threshold anybody fitted, which is the argument for it: a CORN
    head emits one probability per cutpoint and the ordinal they agree on is the
    last one that clears even odds. An unread row gets `None` and never a 1 — the
    fine head is defined over rows clearing the render bar and has no opinion
    anywhere else, and a 1 there would be a veto suggested by nobody.
    """
    assert veto._decoded(reading) == expected


def test_a_readout_over_a_record_breaks_the_vetoed_seats_out_by_every_axis() -> None:
    """Mode, family, colour cell, hue family and map.

    A systematic pocket of bad pictures — one mode, one map, one cell — is the
    thing worth finding in a rejection, and a bare count cannot show it.
    """
    import unittest.mock

    from fractal_wallpapers.curation import candidate_ledger, tentative

    bad, good = a_recipe(colormap="the_bad_one"), a_recipe(colormap="a_good_one")
    rows = [ledger_row("bad", bad), ledger_row("good", good)]
    seats = [
        {
            "key": key,
            "seat": index,
            "alias": key,
            "mode": "smooth",
            "partition": "julia:mandelbrot",
            "cell": "dark_vivid_blue",
            "hue_family": "blue",
            "p_ge4": 0.9,
            "picture": f"artifacts/{key}.jpg",
        }
        for index, key in enumerate(("bad", "good"))
    ]
    with (
        unittest.mock.patch.object(tentative, "read_rows", lambda _stamp: seats),
        unittest.mock.patch.object(candidate_ledger, "stream", lambda: iter(rows)),
    ):
        readout = veto.seats("a_stamp", veto=veto.render_keys([a_label(bad)]), log=quiet)
    assert readout["seats"] == 2
    assert readout["vetoed"] == 1
    assert [row["key"] for row in readout["rows"]] == ["bad"]
    assert readout["by_mode"] == {"smooth": 1}
    assert readout["by_colormap"] == {"the_bad_one": 1}
    assert readout["by_cell"] == {"dark_vivid_blue": 1}
    assert readout["by_hue_family"] == {"blue": 1}
    assert readout["by_partition"] == {"julia:mandelbrot": 1}


def test_a_page_of_no_vetoed_seats_is_a_reading_and_not_a_page() -> None:
    """Zero is an answer. A page of nothing is a file somebody has to interpret."""
    with pytest.raises(veto.VetoRefused, match="nothing to show"):
        veto.page({"stamp": "a_stamp", "seats": 10, "vetoed": 0, "rows": []}, Path("nowhere.html"))


def test_the_record_a_readout_writes_says_the_record_is_not_rewritten() -> None:
    """The one sentence a reader of this file a year from now needs.

    A stamp seated before a label was cast still holds that seat — the veto reads
    forward into the next solve and never backwards into a record on disk — and a
    readout whose `vetoed` count was mistaken for a repair would be a person
    believing a gallery had already changed.
    """
    import unittest.mock

    from fractal_wallpapers.curation import candidate_ledger, tentative

    recipe = a_recipe()
    with (
        unittest.mock.patch.object(
            tentative, "read_rows", lambda _stamp: [{"key": "a", "seat": 0}]
        ),
        unittest.mock.patch.object(
            candidate_ledger, "stream", lambda: iter([ledger_row("a", recipe)])
        ),
    ):
        readout = veto.seats("a_stamp", veto={}, log=quiet)
    assert "NOT rewritten" in readout["is"]
    assert json.loads(json.dumps(readout))["vetoed"] == 0
