"""The gallery-grade store: three separations, and each one asserted.

This corpus is 1..4 about finished pictures and so is `smooth_render`, and the
two mean different things: over there a 1 is "this does not work", here it is "I
am genuinely surprised this cleared the bar". A number that plausibly reads as
another store's is worse than one that obviously does not, so what is pinned here
is the machinery that keeps them apart — the store is not a finished head, its
rows carry no `score`, and no batch of it can ever be an evaluation instrument.
"""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path

import pytest

from fractal_wallpapers.labeling import finished, gallery_grade, intake, sheets
from fractal_wallpapers.labeling import registry as registry_module

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The one module allowed to know where this store's records live.
STORE_MODULE = "src/fractal_wallpapers/labeling/gallery_grade.py"


def a_row(**changes) -> dict:
    fields = {
        "batch": "a_batch",
        "grade": 3,
        "family": {"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]},
        "viewport": {"center_re": "0.1", "center_im": "0.2", "width": "0.5"},
        "mode": "threads",
        "mode_params": {},
        "curve": "linear",
        "colormap": "twilight_shifted",
        "recipe_": finished.recipe(mirror=True),
        "render": {
            "resolution": [1280, 720],
            "supersample": 2,
            "maxiter": 8000,
            "filter": "lanczos3",
        },
        "recorded_at": "2026-09-06T00:00:00Z",
    }
    fields.update(changes)
    return gallery_grade.grade_row(**fields)


def registered(tmp_path, monkeypatch, batch: str = "a_batch") -> dict:
    """A tmp store with one registered batch, and its registry."""
    monkeypatch.setattr(gallery_grade, "repo_root", lambda: tmp_path)
    gallery_grade.register(
        registry_module.Registration(
            batch=batch, method="the seats of one tentative record, and rows it refused"
        )
    )
    return gallery_grade.registry()


# --------------------------------------------------------------------------- #
# One — it is not a finished head, and no reader can name it as one.
# --------------------------------------------------------------------------- #
def test_the_store_is_not_one_of_the_finished_heads() -> None:
    assert gallery_grade.NAME not in finished.HEADS
    with pytest.raises(finished.FinishedError, match="unknown head"):
        finished.head_of(gallery_grade.NAME)


def test_the_finished_trainers_population_cannot_name_this_store() -> None:
    """The pooling this store exists to be impossible, asserted at the door.

    `finished_train.population` calls `finished.head_of` on its own first line, so
    a retrain that named this store dies before it reads a row — which is the
    difference that matters, because a retrain that ingested these rows would be
    fitting one head to two incompatible definitions of the same four numbers and
    nothing about the result would look wrong.
    """
    from fractal_wallpapers.models import finished_train

    with pytest.raises(finished.FinishedError, match="unknown head"):
        finished_train.population(gallery_grade.NAME)


def test_the_store_lives_beside_the_finished_ones_and_not_inside_them() -> None:
    assert gallery_grade.store_dir().name == gallery_grade.NAME
    assert gallery_grade.store_dir().parent.name == "data"
    for head in finished.HEADS:
        assert gallery_grade.store_dir() != finished.store_dir(head)


# --------------------------------------------------------------------------- #
# Two — the absent `score`.
# --------------------------------------------------------------------------- #
def test_a_row_carries_a_grade_and_never_a_score() -> None:
    """The whole protection, and it is an absence rather than a check downstream."""
    assert "score" not in a_row()
    assert a_row()["grade"] == 3


def test_a_row_carrying_a_score_is_refused_at_the_writer() -> None:
    with pytest.raises(gallery_grade.GradeRefused, match="carries a `score`"):
        a_row(score=3)


def test_a_grade_outside_the_scale_is_refused() -> None:
    with pytest.raises(gallery_grade.GradeRefused, match="not one of"):
        a_row(grade=5)
    assert a_row(grade=None)["grade"] is None


def test_a_row_with_no_render_identity_is_refused() -> None:
    """A partial palette pass is a picture nobody can rebuild.

    The place is the other half and is refused a level down, by
    `supply.location.location_key`, which raises on a family no partition claims
    rather than returning None — so a broken place never reaches this check at all.
    """
    with pytest.raises(gallery_grade.GradeRefused, match="no render identity"):
        a_row(recipe_={"gamma": 1.0})
    with pytest.raises(gallery_grade.GradeRefused, match="no render identity"):
        a_row(mode=None)


def test_the_key_is_the_finished_stores_key_and_not_a_second_spelling() -> None:
    """A picture is one picture across every corpus that judges pictures."""
    row = a_row()
    assert gallery_grade.render_key(row) == finished.render_key(row)
    assert gallery_grade.place_of(row) == finished.place_of(row)


def test_two_colorings_of_one_place_are_two_verdicts() -> None:
    """Unlike an attribute, and like a finished render: the unit is the picture.

    A place carries a dozen pictures and the differences between them are exactly
    what this head has to learn, so a second map at one place is a second row and
    never a revision of the first.
    """
    mine = a_row()
    theirs = a_row(colormap="viridis")
    assert gallery_grade.place_of(mine) == gallery_grade.place_of(theirs)
    resolution = gallery_grade.resolve([mine, theirs])
    assert len(resolution.current) == 2
    assert resolution.n_superseded == 0


def test_the_same_picture_twice_resolves_latest_wins() -> None:
    first = a_row(grade=2, recorded_at="2026-09-06T00:00:00Z")
    second = a_row(grade=4, recorded_at="2026-09-06T01:00:00Z")
    resolution = gallery_grade.resolve([second, first])
    assert resolution.n_superseded == 1
    assert [row["grade"] for row in resolution.graded()] == [4]


# --------------------------------------------------------------------------- #
# Three — no batch here is ever an instrument.
# --------------------------------------------------------------------------- #
def test_a_registration_claiming_a_side_is_refused(tmp_path, monkeypatch) -> None:
    """Both flags `eval_eligible` is derived from, refused at the writer.

    Refused rather than coerced: a registration is the answer to how a population
    was drawn, and silently rewriting one would leave the file saying something
    nobody typed.
    """
    monkeypatch.setattr(gallery_grade, "repo_root", lambda: tmp_path)
    for flag in ("score_unconditioned", "eval_only"):
        with pytest.raises(gallery_grade.GradeRefused, match=flag):
            gallery_grade.register(
                registry_module.Registration(batch="b", method="m", **{flag: True})
            )
    assert not gallery_grade.registry_path().is_file(), "nothing was written"


def test_an_anchored_registration_is_fine_and_still_not_eligible(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(gallery_grade, "repo_root", lambda: tmp_path)
    gallery_grade.register(registry_module.Registration(batch="b", method="m", anchored=True))
    assert gallery_grade.registry()["b"].eval_eligible is False
    assert gallery_grade.eval_eligible() == []


def test_eligibility_is_read_off_the_file_and_not_restated(tmp_path, monkeypatch) -> None:
    """`eval_eligible()` reads the standing registrations rather than repeating the rule.

    So a row that reached the registry some other way — a hand edit, an older
    writer — is *reported* rather than assumed away. The refusal above is the
    writer's; this is the reading.
    """
    registered(tmp_path, monkeypatch)
    assert gallery_grade.eval_eligible() == []
    with gallery_grade.registry_path().open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(
                {
                    "schema": registry_module.SCHEMA,
                    "batch": "smuggled",
                    "method": "written past the writer",
                    "score_unconditioned": True,
                    "anchored": False,
                    "eval_only": False,
                }
            )
            + "\n"
        )
    assert gallery_grade.eval_eligible() == ["smuggled"]


# --------------------------------------------------------------------------- #
# The writer.
# --------------------------------------------------------------------------- #
def test_a_batch_with_no_registration_cannot_be_written(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(gallery_grade, "repo_root", lambda: tmp_path)
    with pytest.raises(gallery_grade.GradeRefused, match="no registration"):
        gallery_grade.append([a_row()])


def test_one_call_writes_one_batch(tmp_path, monkeypatch) -> None:
    known = registered(tmp_path, monkeypatch)
    with pytest.raises(gallery_grade.GradeRefused, match="one batch"):
        gallery_grade.append([a_row(), a_row(batch="other")], known=known)


def test_nothing_half_written_when_one_row_is_bad(tmp_path, monkeypatch) -> None:
    known = registered(tmp_path, monkeypatch)
    with pytest.raises(gallery_grade.GradeRefused):
        gallery_grade.append([a_row(), {**a_row(), "grade": 9}], known=known)
    assert not gallery_grade.batch_path("a_batch").is_file()


def test_rows_written_read_back_through_the_one_reader(tmp_path, monkeypatch) -> None:
    known = registered(tmp_path, monkeypatch)
    gallery_grade.append([a_row(), a_row(colormap="viridis", grade=1)], known=known)
    summary = gallery_grade.resolved().summary()
    assert summary["rows"] == summary["renders"] == summary["graded"] == 2
    assert summary["locations"] == 1
    assert summary["grades"] == {"1": 1, "3": 1}
    assert summary["unkeyed"] == 0


# --------------------------------------------------------------------------- #
# The ingest seam.
# --------------------------------------------------------------------------- #
def test_the_seam_records_a_grade_and_the_quality_stores_keep_their_score() -> None:
    records = intake.records_for(gallery_grade.NAME)
    assert records.verdict_key == "grade"
    assert records.tiers == (1, 2, 3, 4)
    assert records.join_keys == intake.FINISHED_JOIN_KEYS
    for head in ("location", *finished.HEADS):
        assert intake.records_for(head).verdict_key == "score"


def test_the_seam_asserts_no_pin_and_says_why() -> None:
    """There is no side to protect, which is not the attribute store's answer.

    Over there the reservation is intra-batch and asserted against a split
    somewhere else. Here there is no reservation anywhere, so the report says the
    question does not arise and carries the reading that proves it.
    """
    records = intake.records_for(gallery_grade.NAME)
    report = records.assert_pin([])
    assert report["ok"] and report["pinned_locations"] == 0
    assert "no evaluation side" in report["asserted"]
    assert report["eval_eligible_batches"] == []
    assert records.pinned_place is None


def test_an_unknown_head_names_this_store_among_the_ones_it_could_have_meant() -> None:
    with pytest.raises(intake.IntakeError, match=gallery_grade.NAME):
        intake.records_for("gallery_grades")


# --------------------------------------------------------------------------- #
# The page is blind, and the sheet says what its numbers meant.
# --------------------------------------------------------------------------- #
def test_the_source_prefills_nothing_and_orders_by_nothing() -> None:
    source = sheets.gallery_grade_source()
    assert source.head == gallery_grade.NAME
    assert source.kind == "gallery_grade"
    assert source.tiers == (1, 2, 3, 4)
    assert source.order([{"section": ""}] * 4, 0)[1] == "shuffle"


def test_the_page_is_told_there_is_no_prefill_because_its_default_says_otherwise() -> None:
    """Unset, `page.html` prints "the suggestion is a head's own decode".

    On a sheet with no suggestion at all that is a sentence about a thing that is
    not there, which is exactly the confusion `prefill_note` was added for.
    """
    note = sheets.gallery_grade_source().prefill_note
    assert note and "nothing here is prefilled" in note


def test_the_source_ships_its_own_words_because_the_page_default_is_another_scale() -> None:
    """The page's default words are the quality scale's, and a 1 here is not that 1."""
    words = sheets.gallery_grade_source().words
    assert words == gallery_grade.words()
    assert set(words) == {"1", "2", "3", "4"}
    assert words["1"] != "does not work"


def test_the_rubric_carries_all_four_meanings_verbatim() -> None:
    """No anchor sheet exists for this scale, so the first sitting creates the anchors.

    The sentences a labeler is asked in are therefore the store's own constants
    rather than a paraphrase of them, and the rubric goes onto the manifest — so a
    sheet on disk says what its ones and fours meant a year later.
    """
    for meaning in gallery_grade.MEANINGS:
        assert meaning in gallery_grade.RUBRIC
        assert meaning in sheets.gallery_grade_source().rubric


def test_the_sheet_row_carries_the_reading_and_the_draw_and_shows_neither(tmp_path) -> None:
    """The two keys the page does not render, and the three fields that it does.

    `columns`, `facts` and a picture caption are what a card shows, and all three
    are empty on purpose: a caption naming the mode and the map is a stratum a
    labeler can read off the card, and the judge's cutpoints under it are the
    order this head exists to replace in another shape. The judge still reads
    every picture, and its reading lands under `reading`, which `page.html` has
    never heard of.
    """
    unit = {
        "family": {"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]},
        "viewport": {"center_re": "0.1", "center_im": "0.2", "width": "0.5"},
        "maxiter": 8000,
        "mode": "threads",
        "mode_params": {},
        "curve": "linear",
        "colormap": "twilight_shifted",
        "recipe": dict(finished.recipe(mirror=True)),
        "seated": False,
        "refusal": "location",
        "pre_stamp": False,
        "leveled": None,
    }
    made: list[Path] = []

    def render(join, output, colormaps=None):
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"not a picture")
        made.append(output)

    source = sheets.gallery_grade_source(renderer=render, scores=([[1.0, 0.9, 0.5]], 4))
    monkeyed = sheets.thumbnail
    try:
        sheets.thumbnail = lambda picture, out: out
        sheet = sheets.build(source, [unit], tmp_path, batch="b", seed=0, log=lambda *_a: None)
    finally:
        sheets.thumbnail = monkeyed

    row = sheet.rows[0]
    assert row["facts"] == [] and row["columns"] == {}
    assert row["pictures"][0]["caption"] == ""
    assert row["suggestion"] is None and row["suggestion_score"] is None
    assert row["reading"] == {"p_ge2": 1.0, "p_ge3": 0.9, "p_ge4": 0.5}
    assert row["drawn_as"] == {
        "seated": False,
        "refusal": "location",
        "pre_stamp": False,
        "leveled": False,
    }
    assert sheet.manifest["scorer"] == "none"
    assert sheet.manifest["suggested_by"] == "none"
    assert sheet.manifest["suggested_tiers"] == {}
    assert sheet.manifest["order"] == "shuffle"
    assert made, "the unit was rendered"

    # And the seam puts all of it on the store row, where nothing else can.
    read_back = intake.read_sheet(tmp_path)
    made_row = intake.records_for(gallery_grade.NAME).row_of(read_back, "u0001", 4, "matt", None)
    assert made_row["grade"] == 4
    assert made_row["seated"] is False
    assert made_row["refusal"] == "location"
    assert made_row["pre_stamp"] is False
    assert made_row["leveled"] is False
    assert made_row["reading"] == row["reading"]
    assert "score" not in made_row


# --------------------------------------------------------------------------- #
# The correction page: the fine head's own decode, and never the render judge's.
# --------------------------------------------------------------------------- #
def a_unit(**changes) -> dict:
    """One gallery-grade plan unit, the shape [`sheets.units_from_plan`] reads."""
    unit = {
        "family": {"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]},
        "viewport": {"center_re": "0.1", "center_im": "0.2", "width": "0.5"},
        "maxiter": 8000,
        "mode": "threads",
        "mode_params": {},
        "curve": "linear",
        "colormap": "twilight_shifted",
        "recipe": dict(finished.recipe(mirror=True)),
        "seated": False,
        "refusal": "location",
        "pre_stamp": False,
        "leveled": None,
    }
    unit.update(changes)
    return unit


def a_grade_sheet(tmp_path, units: list[dict], prefilled: bool, seed: int = 0):
    """Build a gallery-grade sheet over `units`, rendering nothing real."""

    def render(join, output, colormaps=None):
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"not a picture")

    reading = ([[1.0, 0.9, 0.5]] * len(units), 4)
    source = sheets.gallery_grade_source(renderer=render, scores=reading, prefilled=prefilled)
    monkeyed = sheets.thumbnail
    try:
        sheets.thumbnail = lambda picture, out: out
        return sheets.build(source, units, tmp_path, batch="b", seed=seed, log=lambda *_a: None)
    finally:
        sheets.thumbnail = monkeyed


def test_a_correction_page_prefills_the_fine_heads_decode_and_reads_good_to_bad(
    tmp_path,
) -> None:
    """The two bullets `prefilled` turns over, and the two it does not.

    The prefill comes off the PLAN — the fine head reads a candidate at 640x360
    and this page serves 1280x720, so nothing re-reads it here — and the order is
    that head's expected grade. What does not move is the card: no facts, no
    caption, no `columns`, because a stratum a labeler can read off a card is the
    thing this store's blindness was ever about.
    """
    units = [
        a_unit(colormap="twilight_shifted", suggestion=2, suggestion_score=2.1),
        a_unit(colormap="magma", suggestion=4, suggestion_score=3.8),
        a_unit(colormap="viridis", suggestion=3, suggestion_score=3.0),
    ]
    sheet = a_grade_sheet(tmp_path, units, prefilled=True)

    assert [row["suggestion"] for row in sheet.rows] == [4, 3, 2]
    assert [row["suggestion_score"] for row in sheet.rows] == [3.8, 3.0, 2.1]
    assert [row["join"]["colormap"] for row in sheet.rows] == [
        "magma",
        "viridis",
        "twilight_shifted",
    ]
    assert sheet.manifest["order"] == "fine grade"
    assert sheet.manifest["scorer"] == "plan"
    assert sheet.manifest["suggested_by"] == "plan"
    assert sheet.manifest["suggested_tiers"] == {"2": 1, "3": 1, "4": 1}
    # The card is untouched, which is the half of the blindness that stands.
    for row in sheet.rows:
        assert row["facts"] == [] and row["columns"] == {}
        assert row["pictures"][0]["caption"] == ""
        assert row["reading"] == {"p_ge2": 1.0, "p_ge3": 0.9, "p_ge4": 0.5}


def test_a_row_the_fine_head_cannot_read_carries_no_prefill_and_sorts_last(tmp_path) -> None:
    """`solve.at_fine_bar`'s rule for this same column, arriving at the page.

    The fine head is defined over rows clearing the render bar, so a row it has
    no output for gets no suggestion rather than a guessed one — and it sits
    after every row the head could read, which is also what stops the sweep
    turning a gap into a tier.
    """
    units = [
        a_unit(colormap="magma"),
        a_unit(colormap="viridis", suggestion=1, suggestion_score=1.2),
        a_unit(colormap="twilight_shifted", suggestion=4, suggestion_score=3.9),
    ]
    sheet = a_grade_sheet(tmp_path, units, prefilled=True)

    assert [row["suggestion"] for row in sheet.rows] == [4, 1, None]
    assert sheet.rows[-1]["join"]["colormap"] == "magma"
    assert sheet.rows[-1]["suggestion_score"] is None
    assert "no output for" in sheet.manifest["prefill_note"]


def test_the_page_is_told_the_prefill_is_this_stores_head_at_another_geometry(tmp_path) -> None:
    """`page.html`'s two defaults are both wrong here, and each is wrong its own way.

    Unset, the page says *a head's own decode*, which does not say which head or
    that it read a different picture; and with `suggested_by` reading `plan` it
    says *the verdict this row already carries*, which is an incumbent label
    nobody in this store has cast.
    """
    note = sheets.GRADE_CORRECTION_NOTE
    assert "FINE head" in note and "640x360" in note
    sheet = a_grade_sheet(tmp_path, [a_unit(suggestion=3, suggestion_score=3.0)], prefilled=True)
    assert sheet.manifest["prefill_note"] == note
    assert sheet.manifest["suggested_by"] == "plan"


def test_a_page_asked_for_prefilled_and_handed_none_is_refused(tmp_path) -> None:
    """Otherwise it serves a blind sheet under a correction sheet's manifest."""
    with pytest.raises(sheets.SheetError, match="not one plan unit states a suggestion"):
        a_grade_sheet(tmp_path, [a_unit(), a_unit(colormap="magma")], prefilled=True)


def test_the_gap_the_shared_rule_refuses_needs_a_reason_to_be_allowed() -> None:
    """`stated_suggestions` is one rule for every source, and `gaps` is the door.

    Without a reason the mix is refused, which is what keeps a page from meaning
    an incumbent verdict on one row and a decode on the next.
    """
    units = [{"suggestion": 3}, {"suggestion": None}]
    with pytest.raises(sheets.SheetError, match="all of them or none"):
        sheets.stated_suggestions(units, gallery_grade.tiers())
    assert sheets.stated_suggestions(units, gallery_grade.tiers(), gaps="because") == [3, None]


def test_the_default_is_still_blind_and_the_cli_reads_the_plan_for_the_answer() -> None:
    """No flag decides this; the plan does, and `label build` asks it the one way."""
    source = sheets.gallery_grade_source()
    assert source.prefill_note == sheets.GRADE_BLIND_NOTE
    assert source.order([{"section": ""}] * 4, 0)[1] == "shuffle"
    body = (REPO_ROOT / "src/fractal_wallpapers/cli/label_commands.py").read_text(encoding="utf-8")
    assert 'prefilled=any(unit.get("suggestion") is not None for unit in units)' in body


def test_a_drop_ingests_end_to_end_and_the_store_reads_it_back(tmp_path, monkeypatch) -> None:
    """The whole seam, because a store nothing can ingest into is a store with no use.

    `intake.run` checks both counts in both directions, refuses an unregistered
    batch, asserts the pin before writing and re-reads the store afterwards to
    confirm it now says what the export said. All of that is written once for
    every store, so what this proves is that this store's `Records` satisfies it —
    including the verdict field, which is `grade` and not `score`.
    """
    sheet_dir = tmp_path / "sheet"
    unit = {
        "family": {"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]},
        "viewport": {"center_re": "0.1", "center_im": "0.2", "width": "0.5"},
        "maxiter": 8000,
        "mode": "threads",
        "mode_params": {},
        "curve": "linear",
        "colormap": "twilight_shifted",
        "recipe": dict(finished.recipe(mirror=True)),
        "seated": True,
        "refusal": None,
        "pre_stamp": False,
        "leveled": None,
    }

    def render(join, output, colormaps=None):
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"not a picture")

    source = sheets.gallery_grade_source(renderer=render, scores=([[1.0, 0.9, 0.5]], 4))
    monkeypatch.setattr(sheets, "thumbnail", lambda picture, out: out)
    sheets.build(source, [unit], sheet_dir, batch="a_batch", seed=0, log=lambda *_a: None)

    drop = tmp_path / "gallery_grade.a_batch.json"
    drop.write_text(json.dumps({"u0001": {"score": 4}}), encoding="utf-8")

    monkeypatch.setattr(gallery_grade, "repo_root", lambda: tmp_path)
    with pytest.raises(intake.IntakeError, match="no registration"):
        intake.run(sheet=sheet_dir, labels=drop, labeler="matt", write=True)

    registered(tmp_path, monkeypatch)
    report = intake.run(sheet=sheet_dir, labels=drop, labeler="matt", write=True)
    assert report["head"] == gallery_grade.NAME
    assert report["written"] == 1
    assert report["verdicts"] == {"1": 0, "2": 0, "3": 0, "4": 1}
    assert report["by batch"]["a_batch"]["side"] == "train"

    stored = gallery_grade.resolved().graded()
    assert len(stored) == 1
    assert stored[0]["grade"] == 4 and "score" not in stored[0]
    assert stored[0]["seated"] is True and stored[0]["refusal"] is None
    assert stored[0]["reading"] == {"p_ge2": 1.0, "p_ge3": 0.9, "p_ge4": 0.5}
    assert stored[0]["labeler"] == "matt"

    # And re-running it is a no-op, which is why a labeler ever re-runs it.
    again = intake.run(sheet=sheet_dir, labels=drop, labeler="matt", write=True)
    assert again["rows"]["to write"] == 0 and again["written"] == 0


# --------------------------------------------------------------------------- #
# The choke point.
# --------------------------------------------------------------------------- #
def tracked_sources() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "src"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [name for name in result.stdout.split("\0") if name.endswith(".py")]


def addresses_the_records(source: str, segment: str) -> bool:
    """Whether this source builds a path through the store's own name.

    The reading `tests/test_attribute_store.py` takes, and for the same reason:
    path building off the syntax tree, never the word, so prose about the store in
    a docstring is not a second reader of it.
    """

    def joined(node) -> bool:
        return isinstance(node, ast.Constant) and node.value == segment

    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.BinOp)
            and isinstance(node.op, ast.Div)
            and (joined(node.left) or joined(node.right))
        ):
            return True
        if isinstance(node, ast.Call):
            for argument in node.args:
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                    spelled = argument.value.replace("\\", "/")
                    if f"/{segment}/" in spelled or spelled.endswith(f"/{segment}"):
                        return True
    return False


@pytest.mark.slow
def test_only_the_store_addresses_the_gallery_grade_records() -> None:
    offenders = sorted(
        name
        for name in tracked_sources()
        if name.replace("\\", "/") != STORE_MODULE
        and addresses_the_records(
            (REPO_ROOT / name).read_text(encoding="utf-8"), gallery_grade.NAME
        )
    )
    assert not offenders, (
        f"these modules address the {gallery_grade.NAME} store's directory themselves instead "
        f"of going through {STORE_MODULE}: {offenders}. A second reader is a second answer to "
        "what the corpus says."
    )


# --------------------------------------------------------------------------- #
# The live store.
# --------------------------------------------------------------------------- #
def test_the_tracked_store_reads_back_and_holds_no_instrument() -> None:
    """Whatever is on disk today, read through the one reader, keys and resolves."""
    resolution = gallery_grade.resolved()
    assert resolution.n_unkeyed == 0, "a tracked row carries no render identity"
    assert gallery_grade.eval_eligible() == []
    for registration in gallery_grade.registry().values():
        assert not registration.score_unconditioned
        assert not registration.eval_only
