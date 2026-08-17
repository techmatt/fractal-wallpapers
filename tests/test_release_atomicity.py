"""A killed release row must not look finished.

The first production run shipped four wallpapers whose record was wrong, and
every number it printed balanced. The autolevel path is **two** full-resolution
renders to one path, the unit deadline is one budget spent by both of them, and
the kill landed on the second: base render on disk, decodable, no operator pass.
`resumable()` asked only whether the file decoded, so the resume counted all four
as finished and reconciled `28 planned = 28 resumed + 0 made`.

Two fixes, and each of them alone would have caught it:

* nothing exists at the final path until the row is complete — the render lands
  on a temporary and is renamed;
* a resume trusts the leg's own completion record, not a file on disk.

These pin both, and then pin the two of them together on a simulated kill.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.curation import colorize, release


# --------------------------------------------------------------------------- #
# nothing at the final path until the row is complete
# --------------------------------------------------------------------------- #
def _stub_engine(monkeypatch, calls: list, fail_on: int | None = None):
    """An engine that writes bytes to whatever `output` names, and can die."""

    def run(subcommand, spec=None, log=None):
        calls.append(spec["output"])
        if fail_on is not None and len(calls) == fail_on:
            raise RuntimeError("killed: past the deadline")
        from pathlib import Path

        Path(spec["output"]).parent.mkdir(parents=True, exist_ok=True)
        Path(spec["output"]).write_bytes(f"render {len(calls)}".encode())
        return {"output": spec["output"]}

    monkeypatch.setattr(colorize.engine, "run", run)
    return run


def _no_level(monkeypatch):
    monkeypatch.setattr(colorize, "kind_of", lambda mode: "direct")


ROW = {"family": {"kind": "mandelbrot"}, "viewport": {}, "maxiter": 100}


def _spec_of(monkeypatch):
    from fractal_wallpapers.models import renders

    monkeypatch.setattr(
        renders, "spec_of", lambda recipe, output: {"output": str(output), "recipe": recipe}
    )
    monkeypatch.setattr(colorize, "render_row", lambda *a, **k: {"recipe": {"mirror": False}})


def test_the_render_lands_on_a_temporary_and_is_renamed_into_place(tmp_path, monkeypatch) -> None:
    calls: list = []
    _spec_of(monkeypatch)
    _stub_engine(monkeypatch, calls)
    _no_level(monkeypatch)

    output = tmp_path / "0000.png"
    picture, stamp = colorize.render(ROW, "orbit_trap", "x", set(), output)

    assert picture == output and output.is_file() and stamp is None
    assert calls == [str(colorize.writing_path(output))], "the engine wrote the final path"
    assert not colorize.writing_path(output).exists(), "the temporary outlived the rename"


def test_a_render_that_dies_leaves_nothing_at_the_final_path(tmp_path, monkeypatch) -> None:
    """The whole defect in one assertion: a killed row must not leave a picture a
    resume can mistake for a finished one."""
    calls: list = []
    _spec_of(monkeypatch)
    _stub_engine(monkeypatch, calls, fail_on=1)
    _no_level(monkeypatch)

    output = tmp_path / "0000.png"
    with pytest.raises(RuntimeError, match="killed"):
        colorize.render(ROW, "orbit_trap", "x", set(), output)
    assert not output.exists()


def test_a_kill_on_the_operator_s_re_render_leaves_nothing_either(tmp_path, monkeypatch) -> None:
    """The exact shape of the run8h loss: the base render succeeded, the second
    one did not, and the path they share held a picture that was never the row."""
    calls: list = []
    _spec_of(monkeypatch)
    _stub_engine(monkeypatch, calls, fail_on=2)
    monkeypatch.setattr(colorize, "kind_of", lambda mode: "field")
    maps = tmp_path / "maps"
    maps.mkdir()
    (maps / "x.json").write_text(
        json.dumps({"schema": 1, "name": "x", "kind": "linear", "stops": [[0.0, [0, 0, 0]]]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(colorize, "_colormap_dir", lambda: maps)

    def maybe_level(base, colormap, rerender, record=None):
        return colorize.autolevel.Leveled(rerender([[0.0, [1, 1, 1]]]), {"acted": True})

    monkeypatch.setattr(colorize.autolevel, "maybe_level", maybe_level)
    monkeypatch.setattr(colorize.autolevel, "overriding_colormap", lambda *a, **k: tmp_path / "map")

    output = tmp_path / "0000.png"
    with pytest.raises(RuntimeError, match="killed"):
        colorize.render(ROW, "smooth", "x", set(), output)
    assert len(calls) == 2, "the operator's re-render never ran"
    assert not output.exists(), "a killed row left a picture at the final path"


def test_abandoned_temporaries_are_swept_and_finished_pictures_are_not(tmp_path) -> None:
    (tmp_path / "0000.png").write_bytes(b"finished")
    colorize.writing_path(tmp_path / "0001.png").write_bytes(b"half")
    (tmp_path / "nested").mkdir()
    colorize.writing_path(tmp_path / "nested" / "0002.jpg").write_bytes(b"half")

    assert colorize.sweep_writing(tmp_path) == 2
    assert (tmp_path / "0000.png").is_file()
    assert not colorize.writing_path(tmp_path / "0001.png").exists()


def test_a_temporary_keeps_the_extension_the_engine_chooses_its_format_from() -> None:
    """`0000.png.writing` would have been written as a JPEG."""
    from pathlib import Path

    assert colorize.writing_path(Path("a/0000.png")).suffix == ".png"
    assert colorize.writing_path(Path("a/0000.jpg")).suffix == ".jpg"


# --------------------------------------------------------------------------- #
# a resume trusts the record, not the file
# --------------------------------------------------------------------------- #
def _timing(directory, rows) -> None:
    release.timing_path(directory).write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8", newline="\n"
    )


def test_only_a_row_the_parent_recorded_as_finished_counts_as_done(tmp_path) -> None:
    _timing(
        tmp_path,
        [
            {"id": "0000", "ok": True, "seconds": 1.0},
            {"id": "0001", "ok": False, "seconds": 96.3},
        ],
    )
    assert release.completed(tmp_path) == {"0000"}


def test_a_row_made_again_after_a_kill_is_read_from_its_last_record(tmp_path) -> None:
    """A killed row has two timing rows and only the second describes the picture
    that exists."""
    _timing(tmp_path, [{"id": "0000", "ok": False}, {"id": "0000", "ok": True}])
    assert release.completed(tmp_path) == {"0000"}
    _timing(tmp_path, [{"id": "0000", "ok": True}, {"id": "0000", "ok": False}])
    assert release.completed(tmp_path) == set()


def test_a_torn_last_timing_line_is_skipped_rather_than_fatal(tmp_path) -> None:
    release.timing_path(tmp_path).write_text(
        json.dumps({"id": "0000", "ok": True}) + '\n{"id": "0001", "ok": tr',
        encoding="utf-8",
        newline="\n",
    )
    assert release.completed(tmp_path) == {"0000"}


def test_a_decodable_picture_with_no_completion_record_is_remade(tmp_path) -> None:
    """The four rows, exactly: a readable PNG that the record never called done."""
    from PIL import Image

    picture = tmp_path / "0086.png"
    Image.new("RGB", (4, 4)).save(picture)
    assert release.decodable(picture) is True
    assert release.resumable("0086", picture, release.completed(tmp_path)) is False

    _timing(tmp_path, [{"id": "0086", "ok": True}])
    assert release.resumable("0086", picture, release.completed(tmp_path)) is True


def test_a_recorded_row_whose_picture_went_missing_is_remade(tmp_path) -> None:
    """Both halves, and each catches what the other cannot."""
    _timing(tmp_path, [{"id": "0000", "ok": True}])
    assert release.resumable("0000", tmp_path / "0000.png", release.completed(tmp_path)) is False


def test_a_run_that_never_released_has_nothing_to_resume(tmp_path) -> None:
    assert release.completed(tmp_path) == set()
