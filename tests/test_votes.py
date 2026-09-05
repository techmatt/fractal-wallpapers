"""The voting kit: what a friend receives, and where its pictures came from.

Three claims, and the third is the one that needed a test written for it.

**The folder is complete.** Two JPEGs per seat, a page, a paragraph, a zip — a
kit missing any of them is a kit somebody cannot open or cannot send back.

**The page carries the join.** The seat list is embedded, it parses, and it is
the record's own keys in the record's own order, because a filename carries the
seat's *position* and the export carries the *recipe key* — an export whose keys
did not come from the record would be a label file that joins to nothing.

**The thumbnails came from the full renders.** The stored 640x360 candidate is
the obvious thing to downscale and it is the wrong picture: another size, another
autolevel curve. So the fixture's rows name candidate pictures that **do not
exist on this disk at all**, and the full render carries a two-tone pattern the
thumbnail is then checked for. A kit built off the candidates could not be built
here, and one built off the wrong half of the render would not carry the pattern.

Nothing here renders. [`votes.render_fulls`] is the seam and it is replaced with
a stub that writes a picture and calls the same `arrived` callback in the same
place, so the encode, the downscale, the page and the zip are all exercised.
"""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

import pytest

from fractal_wallpapers.curation import tentative, votes

#: Three seats, so `--limit 2` is a real cut rather than the whole record.
KEYS = ("aaaa0000bbbb1111", "cccc2222dddd3333", "eeee4444ffff5555")

#: What the stub renders: the left half one colour and the right half another, at
#: the frame a kit ships. A downscale of this keeps both halves; a crop, a
#: candidate, or a picture built from anything else does not.
LEFT, RIGHT = (200, 30, 40), (30, 60, 200)


@pytest.fixture
def store(tmp_path, monkeypatch):
    """The regenerable tree in `tmp_path`, and a synthetic record inside it.

    The tier redirect and not a patch of `tentative.gallery_dir`, for
    `tests/test_tentative`'s reason: one accessor moved is a path that reads past
    the redirect into this machine's real records.
    """
    from fractal_wallpapers import paths

    monkeypatch.setenv(paths.HOT_ROOT_VARIABLE, str(tmp_path / "artifacts"))
    (tmp_path / "artifacts").mkdir()
    monkeypatch.setattr(tentative, "published", tentative.stamps)
    stamp = "20260101T000000Z"
    directory = tentative.gallery_dir(stamp)
    directory.mkdir(parents=True)
    rows = [
        {
            "schema": 1,
            "seat": index,
            "key": key,
            "alias": key[:8],
            "mode": "smooth",
            "mode_params": {},
            "partition": "mandelbrot",
            # A path under the redirected tree that nothing ever writes: a kit
            # that reached for a candidate would fail here rather than quietly
            # ship the wrong picture.
            "picture": f"artifacts/curation/depth/nowhere/pictures/{key}.jpg",
        }
        for index, key in enumerate(KEYS)
    ]
    tentative.rows_path(stamp).write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8", newline="\n"
    )
    return stamp


@pytest.fixture
def stub_renders(monkeypatch):
    """[`votes.render_fulls`] without an engine, calling `arrived` where it does."""
    from PIL import Image

    def render_fulls(jobs, staging, regime, workers, arrived, log=print):
        staging.mkdir(parents=True, exist_ok=True)
        for job in jobs:
            picture = Image.new("RGB", votes.FRAME, LEFT)
            picture.paste(
                Image.new("RGB", (votes.FRAME[0] // 2, votes.FRAME[1]), RIGHT),
                (votes.FRAME[0] // 2, 0),
            )
            png = staging / f"{job['key']}.png"
            picture.save(png, compress_level=1)
            arrived(job, png)
        return {"regime": regime.spelled, "planned": len(jobs), "made": len(jobs), "failed": []}

    monkeypatch.setattr(votes, "render_fulls", render_fulls)


def built(tmp_path, stamp, **over) -> dict:
    """A two-seat kit in `tmp_path`, with `over` applied to the build."""
    return votes.build(stamp=stamp, out=tmp_path / "kit", limit=2, log=lambda _line: None, **over)


def seat_list(directory: Path) -> list[str]:
    """The keys the page embeds, read back the way a reader would have to."""
    page = (directory / votes.PAGE_NAME).read_text(encoding="utf-8")
    found = re.search(r"^const KEYS = (\[.*\]);$", page, re.MULTILINE)
    assert found, "the page does not embed a seat list"
    return json.loads(found.group(1))


def test_a_kit_is_a_folder_a_friend_can_open_and_a_zip_to_send_it_in(
    tmp_path, store, stub_renders
) -> None:
    manifest = built(tmp_path, store)
    kit = tmp_path / "kit"
    assert sorted(path.name for path in kit.iterdir()) == sorted(
        [votes.PAGE_NAME, votes.READ_ME, votes.FULLS, votes.THUMBS]
    )
    assert sorted(path.name for path in (kit / votes.FULLS).iterdir()) == [
        "s0000.jpg",
        "s0001.jpg",
    ]
    assert sorted(path.name for path in (kit / votes.THUMBS).iterdir()) == [
        "s0000.jpg",
        "s0001.jpg",
    ]
    # The staging tree is not left behind, and it is not in the zip either.
    assert not (kit / votes.STAGING).exists()
    bundle = Path(manifest["zip"])
    assert bundle.is_file()
    with zipfile.ZipFile(bundle) as held:
        names = held.namelist()
    assert f"kit/{votes.PAGE_NAME}" in names
    assert f"kit/{votes.FULLS}/s0000.jpg" in names
    assert not [name for name in names if votes.STAGING in name]


def test_the_page_embeds_the_records_own_keys_in_the_records_own_order(
    tmp_path, store, stub_renders
) -> None:
    """The filename is a position and the export is a recipe key, so the page is
    the only thing that joins the two. A page carrying anything else is a label
    file nothing can ingest."""
    built(tmp_path, store)
    assert seat_list(tmp_path / "kit") == list(KEYS[:2])


def test_a_thumbnail_is_a_downscale_of_the_full_render_and_never_of_the_candidate(
    tmp_path, store, stub_renders
) -> None:
    """The dimensions say it is not the candidate; the pattern says it is not a
    crop, a half, or the other seat's picture."""
    from PIL import Image

    built(tmp_path, store)
    kit = tmp_path / "kit"
    for name in ("s0000.jpg", "s0001.jpg"):
        with Image.open(kit / votes.FULLS / name) as full:
            assert full.size == votes.FRAME
        with Image.open(kit / votes.THUMBS / name) as thumb:
            assert thumb.size == (votes.THUMB_WIDTH, votes.THUMB_WIDTH * 9 // 16)
            left = thumb.convert("RGB").getpixel((thumb.width // 4, thumb.height // 2))
            right = thumb.convert("RGB").getpixel((3 * thumb.width // 4, thumb.height // 2))
        # JPEG at the shipped quality, so this is "much nearer than the other
        # half" rather than an equality on bytes.
        assert abs(left[0] - LEFT[0]) < 25 and abs(left[2] - LEFT[2]) < 25
        assert abs(right[2] - RIGHT[2]) < 25 and abs(right[0] - RIGHT[0]) < 25


def test_the_kit_names_its_encoding_and_the_frame_it_was_rendered_at(
    tmp_path, store, stub_renders
) -> None:
    """A kit that did not say would be a folder of JPEGs nobody could reproduce."""
    manifest = built(tmp_path, store, quality=85, chroma="444", supersample=4)
    assert manifest["encoding"] == {
        "quality": 85,
        "chroma": "444",
        "regime": "2560x1440ss4",
    }
    assert manifest["record"] == store
    assert manifest["viewer"] == votes.VIEWER
    assert manifest["seats"] == 2


def test_a_seat_already_encoded_is_not_rendered_again(tmp_path, store, stub_renders) -> None:
    """The resume unit is the seat's two JPEGs and not the staging PNG, which is
    deleted as it goes — a thousand of those is ten gigabytes."""
    built(tmp_path, store)
    again = built(tmp_path, store)
    assert again["render"]["planned"] == 0


def test_a_chroma_nothing_ships_is_refused_rather_than_passed_to_pillow(tmp_path, store) -> None:
    """Pillow takes an integer here and would take a wrong one silently."""
    with pytest.raises(votes.VotesRefused):
        votes.build(stamp=store, out=tmp_path / "kit", chroma="422", log=lambda _line: None)
