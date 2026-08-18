"""The seam: a page's export, a sheet that will be swept, and rows that outlive both.

Everything a label means has to be in the row by the time this step finishes.
The sheet directory is untracked and disposable by design, so the failure these
tests exist to prevent is the quiet one — an ingest that succeeds, a scratch
directory that gets cleared a week later, and a corpus of verdicts about pictures
nobody can rebuild.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fractal_wallpapers.labeling import finished, intake, store
from fractal_wallpapers.labeling import registry as registry_module

HEAD = "smooth_render"


@pytest.fixture
def head_store(tmp_path, monkeypatch):
    """An empty finished-render store, and the package pointed at it."""
    directory = tmp_path / "store"
    monkeypatch.setattr(finished, "store_dir", lambda head: directory / finished.head_of(head))
    finished.register(
        HEAD,
        registry_module.Registration(
            batch="a_batch", method="a draw, for a test", anchored=True, why="a test"
        ),
    )
    return directory


@pytest.fixture
def drop(tmp_path, monkeypatch):
    """An empty export drop, addressed the way the rig addresses it."""
    directory = tmp_path / "labels"
    monkeypatch.setattr(store, "export_dir", lambda: directory)
    return directory


def a_join(**changes) -> dict:
    join = {
        "family": {"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]},
        "viewport": {"center_re": "0.1", "center_im": "0.2", "width": "0.5"},
        "mode": "smooth",
        "mode_params": {},
        "curve": "linear",
        "colormap": "twilight_shifted",
        "recipe": finished.recipe(),
        "render": {"resolution": [1280, 720], "supersample": 2, "maxiter": 8000},
        "partition": "julia:mandelbrot",
    }
    join.update(changes)
    return join


def a_sheet(directory, units: int = 3, head: str = HEAD, batch: str = "a_batch"):
    """Write a sheet the way a generator writes one, and return its stem."""
    stem = directory / "a_sheet"
    rows = [
        {
            "unit": f"u{index:04d}",
            "batch": batch,
            "suggestion": 2,
            "join": a_join(
                viewport={"center_re": f"0.{index}", "center_im": "0.2", "width": "0.5"}
            ),
        }
        for index in range(1, units + 1)
    ]
    stem.with_suffix(".json").write_text(
        json.dumps({"schema": 1, "head": head, "units": units, "sheet": "a_sheet"}),
        encoding="utf-8",
    )
    stem.with_suffix(".jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )
    return stem


def an_export(directory, verdicts: dict) -> Path:
    path = directory / "export.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({unit: {"score": score, "revealed": 0} for unit, score in verdicts.items()}),
        encoding="utf-8",
    )
    return path


# --------------------------------------------------------------------------- #
# The row is self-contained, or it does not get written.
# --------------------------------------------------------------------------- #
def test_a_stored_row_needs_nothing_from_the_sheet_it_came_from(tmp_path, head_store) -> None:
    """The whole point: the sheet is deleted and the store still says everything."""
    stem = a_sheet(tmp_path)
    labels = an_export(tmp_path, {"u0001": 3, "u0002": 1})
    intake.run(sheet=stem, labels=labels, labeler="matt", write=True)

    stem.with_suffix(".json").unlink()
    stem.with_suffix(".jsonl").unlink()
    labels.unlink()

    resolution = finished.resolved(HEAD)
    assert resolution.n_unkeyed == 0
    assert {row["score"] for row in resolution.scored()} == {1, 3}
    for row in resolution.scored():
        assert finished.render_key(row) is not None
        assert row["family"] and row["viewport"] and row["recipe"] and row["render"]


def test_a_sheet_row_missing_part_of_the_join_is_refused_before_anything_is_written(
    tmp_path, head_store
) -> None:
    stem = a_sheet(tmp_path)
    rows = [
        json.loads(line)
        for line in stem.with_suffix(".jsonl").read_text(encoding="utf-8").splitlines()
    ]
    del rows[1]["join"]["recipe"]
    stem.with_suffix(".jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )
    with pytest.raises(intake.IntakeError, match="recipe"):
        intake.run(
            sheet=stem,
            labels=an_export(tmp_path, {"u0001": 3}),
            labeler="matt",
            write=True,
        )
    assert finished.resolved(HEAD).n_rows == 0


def test_a_row_whose_partition_disagrees_with_its_family_is_refused(tmp_path, head_store) -> None:
    """Two answers to what a row is, and the label on top is the one that is wrong."""
    stem = a_sheet(tmp_path)
    rows = [
        json.loads(line)
        for line in stem.with_suffix(".jsonl").read_text(encoding="utf-8").splitlines()
    ]
    rows[0]["join"]["partition"] = "phoenix"
    stem.with_suffix(".jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )
    with pytest.raises(intake.IntakeError, match="partition"):
        intake.run(sheet=stem, labels=an_export(tmp_path, {"u0001": 3}), labeler="matt", write=True)


def test_the_unit_id_travels_as_provenance_and_keys_nothing(tmp_path, head_store) -> None:
    stem = a_sheet(tmp_path)
    intake.run(sheet=stem, labels=an_export(tmp_path, {"u0001": 3}), labeler="matt", write=True)
    row = finished.resolved(HEAD).scored()[0]
    assert row["unit"] == "u0001" and row["sheet"] == "a_sheet" and row["suggested"] == 2
    stripped = {key: value for key, value in row.items() if key not in ("unit", "sheet")}
    assert finished.render_key(stripped) == finished.render_key(row)


# --------------------------------------------------------------------------- #
# Counted, both ways.
# --------------------------------------------------------------------------- #
def test_only_units_a_person_acted_on_become_rows(tmp_path, head_store) -> None:
    stem = a_sheet(tmp_path, units=5)
    report = intake.run(
        sheet=stem, labels=an_export(tmp_path, {"u0002": 4}), labeler="matt", write=True
    )
    assert report["units"] == {"on the sheet": 5, "exported": 1, "not acted on": 4}
    assert report["written"] == 1
    assert finished.resolved(HEAD).n_rows == 1


def test_an_export_naming_a_unit_the_sheet_does_not_hold_is_refused(tmp_path, head_store) -> None:
    stem = a_sheet(tmp_path)
    with pytest.raises(intake.IntakeError, match="not on this sheet"):
        intake.run(
            sheet=stem,
            labels=an_export(tmp_path, {"u0001": 3, "u0099": 2}),
            labeler="matt",
            write=True,
        )
    assert finished.resolved(HEAD).n_rows == 0


def test_a_sheet_that_miscounts_itself_is_refused(tmp_path, head_store) -> None:
    stem = a_sheet(tmp_path, units=3)
    manifest = json.loads(stem.with_suffix(".json").read_text(encoding="utf-8"))
    manifest["units"] = 4
    stem.with_suffix(".json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(intake.IntakeError, match="units"):
        intake.read_sheet(stem)


def test_the_store_takes_the_corpus_scale_and_not_the_shipped_model_s(tmp_path, head_store) -> None:
    """Matt's ratified decision: 1..4 for every head, `strange_render` included.

    The strange judge trained on three classes for a generation and could not
    suggest a 4; that is the model's own config and it is not the store's ceiling.
    A store that refused the tier would be a store that can never collect the
    retrain — and this corpus collected exactly that.
    """
    stem = a_sheet(tmp_path, head="strange_render")
    finished.register(
        "strange_render",
        registry_module.Registration(batch="a_batch", method="a draw, for a test"),
    )
    report = intake.run(
        sheet=stem, labels=an_export(tmp_path, {"u0001": 4}), labeler="matt", write=True
    )
    assert report["written"] == 1
    assert report["tiers"] == {"1": 0, "2": 0, "3": 0, "4": 1}
    assert [row["score"] for row in finished.resolved("strange_render").scored()] == [4]


def test_the_writer_itself_takes_a_four_for_the_strange_head(tmp_path, head_store) -> None:
    """The plainest statement of the same decision, at the writer."""
    join = a_join()
    join.pop("partition")
    row = finished.render_row(
        head="strange_render", batch="a_batch", score=4, recipe_=join.pop("recipe"), **join
    )
    assert row["score"] == 4
    assert finished.tiers("strange_render") == (1, 2, 3, 4)


def test_a_score_off_the_scale_entirely_is_still_refused(tmp_path, head_store) -> None:
    stem = a_sheet(tmp_path)
    with pytest.raises(finished.FinishedError, match="one scale"):
        intake.run(sheet=stem, labels=an_export(tmp_path, {"u0001": 5}), labeler="matt", write=True)


# --------------------------------------------------------------------------- #
# Idempotent, and append-only.
# --------------------------------------------------------------------------- #
def test_a_second_ingest_of_the_same_export_writes_nothing(tmp_path, head_store) -> None:
    stem = a_sheet(tmp_path)
    labels = an_export(tmp_path, {"u0001": 3, "u0002": 1, "u0003": 2})
    first = intake.run(sheet=stem, labels=labels, labeler="matt", write=True)
    path = finished.batch_path(HEAD, "a_batch")
    written = path.read_bytes()

    second = intake.run(sheet=stem, labels=labels, labeler="matt", write=True)
    assert first["written"] == 3
    assert second["written"] == 0
    assert second["rows"]["already stored"] == 3
    assert path.read_bytes() == written, "a repeated ingest touched the file"


def test_a_changed_verdict_appends_and_the_original_stays_readable(tmp_path, head_store) -> None:
    stem = a_sheet(tmp_path)
    intake.run(
        sheet=stem,
        labels=an_export(tmp_path, {"u0001": 2}),
        labeler="matt",
        write=True,
    )
    path = finished.batch_path(HEAD, "a_batch")
    original = path.read_bytes()

    report = intake.run(
        sheet=stem,
        labels=an_export(tmp_path, {"u0001": 4}),
        labeler="matt",
        write=True,
    )
    assert report["rows"]["revised"] == 1 and report["written"] == 1
    assert path.read_bytes().startswith(original), "the original row was rewritten, not overlaid"
    assert finished.resolved(HEAD).n_rows == 2
    assert [row["score"] for row in finished.resolved(HEAD).scored()] == [4]


def test_a_dry_run_writes_nothing_and_says_what_it_would(tmp_path, head_store) -> None:
    stem = a_sheet(tmp_path)
    report = intake.run(sheet=stem, labels=an_export(tmp_path, {"u0001": 3}), labeler="matt")
    assert report["written"] == 0 and report["rows"]["to write"] == 1
    assert finished.resolved(HEAD).n_rows == 0


def test_an_unregistered_batch_cannot_be_ingested(tmp_path, head_store) -> None:
    """Registration is answerable while the population is drawn and from memory after."""
    stem = a_sheet(tmp_path, batch="nobody_registered_this")
    with pytest.raises(intake.IntakeError, match="no registration"):
        intake.run(sheet=stem, labels=an_export(tmp_path, {"u0001": 3}), labeler="matt", write=True)


def test_the_registration_flags_reach_the_report_from_the_registry(tmp_path, head_store) -> None:
    """A row carries no flags; the batch does, and the side is read off it."""
    stem = a_sheet(tmp_path)
    report = intake.run(sheet=stem, labels=an_export(tmp_path, {"u0001": 3}), labeler="matt")
    assert report["by batch"]["a_batch"] == {
        "rows": 1,
        "anchored": True,
        "eval_only": False,
        "score_unconditioned": False,
        "side": "train",
    }


# --------------------------------------------------------------------------- #
# One path, both stores.
# --------------------------------------------------------------------------- #
def a_location_sheet(directory, units: int = 3, batch: str = "a_batch"):
    """A location sheet, in the shape the generator writes one."""
    stem = directory / "a_location_sheet"
    rows = [
        {
            "unit": f"u{index:04d}",
            "batch": batch,
            "suggestion": None,
            "join": {
                "family": {"kind": "mandelbrot"},
                "viewport": {"center_re": f"0.{index}", "center_im": "0.2", "width": "0.5"},
                "render": {"resolution": [1280, 720], "supersample": 2, "maxiter": 500},
                "judged_from": "blue_orange",
            },
        }
        for index in range(1, units + 1)
    ]
    stem.with_suffix(".json").write_text(
        json.dumps({"schema": 1, "head": "location", "units": units, "sheet": "a_location_sheet"}),
        encoding="utf-8",
    )
    stem.with_suffix(".jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )
    return stem


def test_the_sheet_s_head_decides_which_store_it_lands_in(tmp_path, store_dir, registered) -> None:
    """One step, two stores. The location half used to be a second path that had
    none of the checks below it; it is the same path now."""
    registered("a_batch")
    stem = a_location_sheet(tmp_path)
    report = intake.run(
        sheet=stem, labels=an_export(tmp_path, {"u0001": 3, "u0002": 1}), labeler="matt", write=True
    )
    assert report["head"] == "location"
    assert report["written"] == 2
    assert store.resolved().summary()["scored"] == 2
    assert report["pin"]["ok"]


def test_a_location_ingest_is_counted_and_idempotent_like_the_other(
    tmp_path, store_dir, registered
) -> None:
    """The §2 guarantees were absent from `record` and are not optional now."""
    registered("a_batch")
    stem = a_location_sheet(tmp_path)
    labels = an_export(tmp_path, {"u0001": 3, "u0002": 1, "u0003": 2})
    first = intake.run(sheet=stem, labels=labels, labeler="matt", write=True)
    written = store.batch_path("a_batch").read_bytes()

    second = intake.run(sheet=stem, labels=labels, labeler="matt", write=True)
    assert first["written"] == 3
    assert second["written"] == 0 and second["rows"]["already stored"] == 3
    assert store.batch_path("a_batch").read_bytes() == written


def test_a_location_verdict_that_changed_appends(tmp_path, store_dir, registered) -> None:
    registered("a_batch")
    stem = a_location_sheet(tmp_path)
    intake.run(sheet=stem, labels=an_export(tmp_path, {"u0001": 2}), labeler="matt", write=True)
    report = intake.run(
        sheet=stem, labels=an_export(tmp_path, {"u0001": 4}), labeler="matt", write=True
    )
    assert report["rows"]["revised"] == 1
    assert store.resolved().n_rows == 2
    assert [row["score"] for row in store.resolved().scored()] == [4]


def test_a_location_sheet_short_of_its_join_is_refused(tmp_path, store_dir, registered) -> None:
    registered("a_batch")
    stem = a_location_sheet(tmp_path)
    rows = [
        json.loads(line)
        for line in stem.with_suffix(".jsonl").read_text(encoding="utf-8").splitlines()
    ]
    del rows[0]["join"]["viewport"]
    stem.with_suffix(".jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )
    with pytest.raises(intake.IntakeError, match="viewport"):
        intake.run(sheet=stem, labels=an_export(tmp_path, {"u0001": 3}), labeler="matt", write=True)
    assert store.resolved().n_rows == 0


def test_a_sheet_cut_for_no_known_judge_is_refused(tmp_path) -> None:
    stem = a_sheet(tmp_path, head="not_a_head")
    with pytest.raises(intake.IntakeError, match="unknown head"):
        intake.read_sheet(stem)


def test_a_sheet_directory_and_a_stem_are_both_read(tmp_path, head_store) -> None:
    """A cut sheet is a directory; a one-off writes a stem. An open session is not
    rebuilt into a new shape just to be ingested."""
    directory = tmp_path / "cut"
    directory.mkdir()
    stem = a_sheet(tmp_path)
    manifest = json.loads(stem.with_suffix(".json").read_text(encoding="utf-8"))
    del manifest["sheet"]  # a cut sheet is named by its directory, not by a field
    (directory / "sheet.json").write_text(json.dumps(manifest), encoding="utf-8")
    (directory / "sheet.jsonl").write_text(
        stem.with_suffix(".jsonl").read_text(encoding="utf-8"), encoding="utf-8"
    )
    assert intake.read_sheet(directory).name == "cut"
    assert intake.read_sheet(stem).name == "a_sheet"


# --------------------------------------------------------------------------- #
# The drop.
# --------------------------------------------------------------------------- #
def test_the_drop_is_named_for_the_head(drop) -> None:
    assert store.export_path("smooth_render") == drop / "smooth_render.json"
    assert store.export_path("location") == drop / "location.json"
    with pytest.raises(store.LabelError):
        store.export_path("../escape")


def test_a_save_that_would_drop_a_unit_is_refused(drop) -> None:
    """A page exports everything it holds; a shorter one is a page that lost its state."""
    intake.write_export(HEAD, {"u0001": {"score": 3}, "u0002": {"score": 1}})
    held = store.export_path(HEAD).read_bytes()
    with pytest.raises(intake.IntakeError, match="already carries"):
        intake.write_export(HEAD, {"u0001": {"score": 3}})
    assert store.export_path(HEAD).read_bytes() == held


def test_a_save_that_changes_a_verdict_is_allowed(drop) -> None:
    intake.write_export(HEAD, {"u0001": {"score": 3}})
    intake.write_export(HEAD, {"u0001": {"score": 1}, "u0002": {"score": 4}})
    assert intake.read_export(store.export_path(HEAD)) == {"u0001": 1, "u0002": 4}


def test_the_drop_is_written_whole_or_not_at_all(drop) -> None:
    """Renamed into place, so a killed save leaves the last good file rather than half of one."""
    intake.write_export(HEAD, {"u0001": {"score": 3}})
    assert not list(drop.glob("*.writing*")), "a temporary survived the save"


def test_both_shapes_of_export_are_read_and_a_withdrawn_verdict_is_not(tmp_path) -> None:
    path = tmp_path / "export.json"
    path.write_text(
        json.dumps({"u0001": {"score": 3, "revealed": 0}, "u0002": 2, "u0003": None}),
        encoding="utf-8",
    )
    assert intake.read_export(path) == {"u0001": 3, "u0002": 2}
