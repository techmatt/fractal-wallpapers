"""`style sheet`: finished pictures as one labelled contact sheet, each keeping its aspect."""

from __future__ import annotations

import pytest

from fractal_wallpapers import style_sheet

Image = pytest.importorskip("PIL.Image")


def picture(path, size, colour=(200, 40, 40)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, colour).save(path)
    return path


def test_a_folder_gives_its_pictures_by_name_and_a_manifest_its_lines(tmp_path):
    picture(tmp_path / "drafts" / "b.png", (32, 20))
    picture(tmp_path / "drafts" / "a.png", (32, 20))
    (tmp_path / "drafts" / "renders.jsonl").write_text("{}\n", encoding="utf-8")
    manifest = tmp_path / "list.txt"
    manifest.write_text("drafts/b.png\n\n", encoding="utf-8")
    found = style_sheet.pictures_of([tmp_path / "drafts", manifest])
    assert [path.name for path in found] == ["a.png", "b.png", "b.png"]
    with pytest.raises(style_sheet.SheetError, match="no picture"):
        style_sheet.pictures_of([tmp_path / "missing.png"])
    # A mistyped manifest is the same refusal, once a FileNotFoundError traceback.
    with pytest.raises(style_sheet.SheetError, match="no picture"):
        style_sheet.pictures_of([tmp_path / "missing.txt"])


def test_tiles_keep_their_aspect_and_rows_take_the_tallest(tmp_path):
    wide = picture(tmp_path / "a" / "wide.png", (64, 40))
    square = picture(tmp_path / "a" / "square.png", (40, 40))
    third = picture(tmp_path / "b" / "third.png", (64, 40))
    out = tmp_path / "sheet.png"
    done = style_sheet.contact_sheet([wide, square, third], out, columns=2, width=32)
    assert (done["columns"], done["rows"]) == (2, 2)
    with Image.open(out) as sheet:
        assert sheet.size == (64, 64)  # rows as tall as the square tile, 32
        assert sheet.getpixel((48, 30)) != (0, 0, 0)  # the square reaches its row's foot
        assert sheet.getpixel((16, 18)) != (0, 0, 0)  # the wide tile is 20 tall, not squashed
        assert sheet.getpixel((16, 26)) == (0, 0, 0)  # and below it is the ground


def test_a_long_label_is_elided_in_the_middle_to_fit_its_tile():
    width = len  # one pixel a character
    assert style_sheet.fitted("short/name", 20, width) == "short/name"
    long = "locations/05_multibrot3_f95d4b63_copper_arms"
    fitted = style_sheet.fitted(long, 20, width)
    assert len(fitted) <= 20 and "…" in fitted
    assert fitted.startswith("locat") and fitted.endswith("arms")


def test_a_crop_leaving_the_picture_is_refused(tmp_path):
    one = picture(tmp_path / "one.png", (40, 25))
    with pytest.raises(style_sheet.SheetError, match="leaves"):
        style_sheet.contact_sheet([one], tmp_path / "s.png", crop=(30, 0, 20, 10))
    done = style_sheet.contact_sheet([one], tmp_path / "s.jpg", width=20, crop=(0, 0, 20, 10))
    assert done["height"] == 10 and (tmp_path / "s.jpg").is_file()
