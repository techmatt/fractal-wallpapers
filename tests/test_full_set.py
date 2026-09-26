"""The full set's driver: its order, its done-ness, its lock, its pause and its encode.

The render itself is `release.render_task` and is guarded where it lives; what is
here is what this driver adds around it, none of which needs the engine.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, JpegImagePlugin

from fractal_wallpapers import process_control
from fractal_wallpapers.curation import embed_link, explorer_link, full_set


def test_a_recipe_seated_twice_renders_once_where_it_is_first_seated() -> None:
    rows = [{"key": key} for key in ("a", "b", "a", "c", "b")]
    assert full_set.render_order(rows) == ["a", "b", "c"]


def test_only_a_finished_jpeg_counts_as_done(tmp_path: Path) -> None:
    (tmp_path / "a.jpg").write_bytes(b"x")
    (tmp_path / full_set.WORK).mkdir()
    (tmp_path / full_set.WORK / "b.jpg").write_bytes(b"x")
    (tmp_path / "c.png").write_bytes(b"x")
    assert full_set.done(tmp_path) == {"a"}


def test_the_gate_declines_once_the_pause_file_exists(tmp_path: Path) -> None:
    gate = full_set.PauseGate(tmp_path / full_set.PAUSE_NAME, 10.0)
    assert gate.may_start() is None and not gate.paused
    full_set.pause(tmp_path)
    assert gate.may_start() and gate.paused
    assert gate.timeout() == 10.0


def test_a_held_directory_names_its_driver_and_a_released_one_names_none(tmp_path: Path) -> None:
    (tmp_path / full_set.PID_NAME).write_text("4321\n", encoding="utf-8")
    assert full_set.running(tmp_path) is None  # no lock file at all
    handle = process_control.hold(tmp_path / full_set.LOCK_NAME)
    try:
        assert full_set.running(tmp_path) == 4321
    finally:
        process_control.let_go(handle)
    assert full_set.running(tmp_path) is None


def test_finish_writes_a_full_chroma_q95_jpeg_carrying_its_link(tmp_path: Path) -> None:
    work = tmp_path / full_set.WORK
    work.mkdir()
    png = work / "k1.png"
    Image.new("RGB", (64, 36), (200, 40, 90)).save(png)
    query = "v=4&m=smooth&x=-0.5&y=0&w=3"
    size = full_set.finish(png, tmp_path, explorer_link.url_of(query))
    final = tmp_path / "k1.jpg"
    assert final.stat().st_size == size
    assert not (work / "k1.jpg").exists()
    with Image.open(final) as image:
        assert JpegImagePlugin.get_sampling(image) == 0  # 4:4:4
    assert embed_link.link_in(final.read_bytes()) == query
