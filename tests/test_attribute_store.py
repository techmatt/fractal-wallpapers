"""The location-attribute stores: the absent field, the key, and the intra-batch pin.

Four properties, and each is a way a corpus of attribute verdicts could be quietly
wrong. A row carrying a `score` is a row that reads as a tier the day somebody
pools the stores by field name. A row keyed on the picture rather than the place
would let one location hold a dozen contradictory answers to a question about the
location. A pin asserted at ingest would refuse the very drop the reservation was
made to collect. And an ordinal that reached a store would be a number in a store
that holds no numbers.
"""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path

import pytest

from fractal_wallpapers.labeling import attributes, intake, sheets
from fractal_wallpapers.labeling import registry as registry_module

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The one module allowed to know where an attribute store's records live.
STORE_MODULE = "src/fractal_wallpapers/labeling/attributes.py"


def a_row(**changes) -> dict:
    fields = {
        "name": "spiral",
        "batch": "a_batch",
        "verdict": "spiral",
        "family": {"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]},
        "viewport": {"center_re": "0.1", "center_im": "0.2", "width": "0.5"},
        "render": {
            "mode": "threads",
            "mode_params": {},
            "curve": "linear",
            "colormap": "twilight_shifted",
            "recipe": {"gamma": 1.0, "mirror": True},
            "resolution": [1280, 720],
            "supersample": 2,
            "maxiter": 8000,
        },
        "recorded_at": "2026-09-03T00:00:00Z",
    }
    fields.update(changes)
    return attributes.attribute_row(**fields)


def registered(tmp_path, monkeypatch, batch: str = "a_batch") -> dict:
    """A tmp store with one registered batch, and its registry."""
    monkeypatch.setattr(attributes, "repo_root", lambda: tmp_path)
    attributes.register(
        "spiral",
        registry_module.Registration(batch=batch, method="a seeded uniform draw over the pool"),
    )
    return attributes.registry("spiral")


# --------------------------------------------------------------------------- #
# The absent field.
# --------------------------------------------------------------------------- #
def test_a_row_never_carries_a_score() -> None:
    """The whole protection, and it is an absence rather than a check downstream."""
    assert "score" not in a_row()
    assert a_row()["class"] == "spiral"


def test_a_row_carrying_a_score_is_refused_at_the_writer() -> None:
    with pytest.raises(attributes.AttributeRefused, match="pooled with a quality corpus"):
        attributes.check("spiral", {**a_row(), "score": 2})


def test_a_class_outside_the_attribute_is_refused() -> None:
    with pytest.raises(attributes.AttributeRefused, match="is not one of"):
        a_row(verdict="probably_a_spiral")


def test_a_row_with_no_place_is_refused() -> None:
    with pytest.raises(attributes.AttributeRefused, match="no location identity"):
        a_row(viewport={"center_re": "0.1"})


# --------------------------------------------------------------------------- #
# The ordinal-to-class map.
# --------------------------------------------------------------------------- #
def test_the_page_casts_ordinals_and_the_store_records_classes() -> None:
    assert attributes.class_of("spiral", 1) == "spiral"
    assert attributes.class_of("spiral", 2) == "not_spiral"
    assert attributes.SPIRAL.tiers == (1, 2)


def test_an_ordinal_the_page_has_no_button_for_is_refused() -> None:
    for bad in (0, 3, True):
        with pytest.raises(attributes.AttributeRefused):
            attributes.class_of("spiral", bad)


def test_the_map_runs_one_way_only() -> None:
    """A caller holding a class and wanting a number is about to write one down."""
    assert not hasattr(attributes, "ordinal_of")


# --------------------------------------------------------------------------- #
# The key is the place, not the picture.
# --------------------------------------------------------------------------- #
def test_two_colorings_of_one_place_are_one_verdict(tmp_path, monkeypatch) -> None:
    """The whole reason this is not a finished-render store.

    Over there a place holds a dozen genuinely different verdicts, one per
    picture. Here a second sitting that happened to draw the same place under a
    different map is a second opinion about the same *place*, and the later one
    stands.
    """
    known = registered(tmp_path, monkeypatch)
    first = a_row(recorded_at="2026-09-01T00:00:00Z")
    second = a_row(
        verdict="not_spiral",
        recorded_at="2026-09-02T00:00:00Z",
        render={**a_row()["render"], "colormap": "inferno"},
    )
    assert attributes.place_of(first) == attributes.place_of(second)
    attributes.append("spiral", [first, second], known=known)
    resolution = attributes.resolved("spiral")
    assert resolution.n_rows == 2
    assert len(resolution.current) == 1
    assert resolution.n_superseded == 1
    assert resolution.counts() == {"not_spiral": 1}


def test_an_original_is_never_modified(tmp_path, monkeypatch) -> None:
    known = registered(tmp_path, monkeypatch)
    attributes.append("spiral", [a_row(recorded_at="2026-09-01T00:00:00Z")], known=known)
    attributes.append(
        "spiral",
        [a_row(verdict="not_spiral", recorded_at="2026-09-02T00:00:00Z")],
        known=known,
    )
    lines = attributes.batch_path("spiral", "a_batch").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["class"] for line in lines] == ["spiral", "not_spiral"]


def test_a_batch_with_no_registration_cannot_be_written(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(attributes, "repo_root", lambda: tmp_path)
    with pytest.raises(attributes.AttributeRefused, match="no registration"):
        attributes.append("spiral", [a_row()])


def test_nothing_half_written_when_one_row_is_bad(tmp_path, monkeypatch) -> None:
    known = registered(tmp_path, monkeypatch)
    with pytest.raises(attributes.AttributeRefused):
        attributes.append("spiral", [a_row(), {**a_row(), "score": 3}], known=known)
    assert not attributes.batch_path("spiral", "a_batch").exists()


# --------------------------------------------------------------------------- #
# The pin, and the one place it is deliberately not asserted.
# --------------------------------------------------------------------------- #
def test_the_pin_is_written_before_a_verdict_exists(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(attributes, "repo_root", lambda: tmp_path)
    unit = {"batch": "a_batch", "family": a_row()["family"], "viewport": a_row()["viewport"]}
    attributes.write_pin("spiral", [attributes.pin_row(unit)], {"schema": 1, "reserved": 1})
    assert list(attributes.pinned("spiral")) == [attributes.place_of(a_row())]
    assert attributes.resolved("spiral").n_rows == 0, "the pin needed no verdicts to exist"


def test_a_training_row_on_a_reserved_place_is_refused(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(attributes, "repo_root", lambda: tmp_path)
    unit = {"batch": "a_batch", "family": a_row()["family"], "viewport": a_row()["viewport"]}
    attributes.write_pin("spiral", [attributes.pin_row(unit)], {"schema": 1})
    with pytest.raises(attributes.AttributeRefused, match="reserved to the spiral"):
        attributes.assert_pin_holds("spiral", [a_row()])


def test_the_pin_holds_when_nothing_touches_it(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(attributes, "repo_root", lambda: tmp_path)
    unit = {"batch": "a_batch", "family": a_row()["family"], "viewport": a_row()["viewport"]}
    attributes.write_pin("spiral", [attributes.pin_row(unit)], {"schema": 1})
    elsewhere = a_row(viewport={"center_re": "9.5", "center_im": "9.5", "width": "0.5"})
    assert attributes.assert_pin_holds("spiral", [elsewhere])["ok"]


def test_ingest_does_not_assert_the_pin(tmp_path, monkeypatch) -> None:
    """The reservation is intra-batch, so the drop it collects sits on it by design.

    A finished store's evaluation side is a whole batch cut blind, and a row from
    any other batch at one of its places is a trespass worth refusing. Here one
    batch holds both sides: a hundred of the sitting's own five hundred units are
    reserved, every one of them lands under the sitting's own batch, and a pin
    asserted at ingest would refuse the drop it exists to collect.
    """
    monkeypatch.setattr(attributes, "repo_root", lambda: tmp_path)
    unit = {"batch": "a_batch", "family": a_row()["family"], "viewport": a_row()["viewport"]}
    attributes.write_pin("spiral", [attributes.pin_row(unit)], {"schema": 1})
    records = intake.records_for("spiral")
    report = records.assert_pin([a_row()])
    assert report["ok"] and report["pinned_locations"] == 1
    assert "not at ingest" in report["asserted"]
    assert records.pinned_place is None


# --------------------------------------------------------------------------- #
# What the ingest seam does with a number.
# --------------------------------------------------------------------------- #
def test_the_ingest_seam_records_a_class_and_not_a_tier() -> None:
    records = intake.records_for("spiral")
    assert records.verdict_key == "class"
    assert records.tiers == (1, 2)
    assert [records.verdict_of(tier) for tier in records.tiers] == ["spiral", "not_spiral"]


def test_the_quality_stores_keep_their_own_field() -> None:
    for head in ("location", "smooth_render", "strange_render"):
        records = intake.records_for(head)
        assert records.verdict_key == "score"
        assert [records.verdict_of(tier) for tier in records.tiers] == list(records.tiers)


def test_an_unknown_head_names_every_store_it_could_have_meant() -> None:
    with pytest.raises(intake.IntakeError, match="spiral"):
        intake.records_for("spirals")


# --------------------------------------------------------------------------- #
# The page and the store agree about what the buttons mean.
# --------------------------------------------------------------------------- #
def test_the_sheet_carries_the_classes_its_ordinals_stand_for() -> None:
    """A drop is numbers, so the manifest has to say what the numbers were.

    Without this a sheet on disk is a page of ones and twos whose meaning lives
    only in whichever version of this module reads it next.
    """
    source = sheets.attribute_source("spiral")
    assert source.tiers == (1, 2)
    assert source.classes == ("spiral", "not_spiral")
    assert source.words == {"1": "spiral", "2": "not a spiral"}
    assert source.head == "spiral"
    assert source.kind == "attribute"


def test_the_attribute_page_says_what_its_prefill_is() -> None:
    """The page knows two kinds of prefill and this is a third."""
    note = sheets.attribute_source("spiral").prefill_note
    assert note and "not a tier" in note


def test_a_quality_source_ships_no_words_and_keeps_the_page_default() -> None:
    assert sheets.location_source().words == {}
    assert sheets.location_source().prefill_note == ""


def test_the_page_reads_the_manifest_for_its_buttons() -> None:
    """The one line in `page.html` this arrangement rests on."""
    page = (REPO_ROOT / "src/fractal_wallpapers/labeling/page.html").read_text(encoding="utf-8")
    assert "WORD = MANIFEST.words || QUALITY_WORD" in page
    assert "MANIFEST.prefill_note" in page


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
    """Whether this source builds a path through an attribute store's own name.

    The same reading `tests/test_label_store.py` takes of `data/labels`: path
    building off the syntax tree, never the word. Prose about the spiral store in
    a docstring is not a second reader of it, and neither is a report key.
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
def test_only_the_store_addresses_an_attribute_store() -> None:
    # The sources are listed once and parsed once per attribute: a guard that
    # re-ran `git ls-files` per store would cost a subprocess for every name.
    sources = {
        name: (REPO_ROOT / name).read_text(encoding="utf-8")
        for name in tracked_sources()
        if name.replace("\\", "/") != STORE_MODULE
    }
    offenders = sorted(
        {
            name
            for segment in attributes.NAMES
            for name, source in sources.items()
            if addresses_the_records(source, segment)
        }
    )
    assert not offenders, (
        f"these modules address an attribute store's directory themselves instead of going "
        f"through {STORE_MODULE}: {offenders}. A second reader is a second answer to what the "
        "corpus says."
    )


def test_the_choke_point_guard_would_actually_catch_something() -> None:
    assert addresses_the_records('path = repo_root() / "data" / "spiral" / "rows"', "spiral")
    assert addresses_the_records('path = Path("data/spiral")', "spiral")
    assert not addresses_the_records('"""Prose about data/spiral is not a reader."""', "spiral")
    assert not addresses_the_records('report = {"spiral": len(rows)}', "spiral")


# --------------------------------------------------------------------------- #
# The live store.
# --------------------------------------------------------------------------- #
def test_the_tracked_spiral_store_reads_back() -> None:
    """Whatever is on disk today, read through the one reader, keys and resolves."""
    resolution = attributes.resolved("spiral")
    assert resolution.n_unkeyed == 0, "a tracked row carries no location identity"
    assert set(resolution.counts()) <= set(attributes.classes("spiral"))


def test_the_tracked_reservation_is_a_fifth_of_its_sitting() -> None:
    """The pin the probe will be measured on, checked as data rather than as intent."""
    recipe = attributes.split_recipe_path("spiral")
    if not recipe.is_file():
        pytest.skip("no reservation has been drawn yet")
    document = json.loads(recipe.read_text(encoding="utf-8"))
    held = attributes.pinned("spiral")
    assert len(held) == document["reserved"], "the pin file and its recipe disagree"
    assert document["realized_eval_share"] == pytest.approx(
        document["reserved"] / document["units"], abs=1e-4
    )
