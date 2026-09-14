"""The release-geometry picture of a seat: found where one exists, made where it does not.

The failure these guard against is the quiet one. A gather that matched loosely
would hand the viewer a picture of the right recipe at the wrong frame and nothing
on the page would say so, and a gather that matched nothing would silently re-render
a record that already had its pictures — four hundred engine legs to make files
that were already on disk.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fractal_wallpapers.curation import fulls, release

OTHER = release.Regime((640, 360), 2)


@pytest.fixture
def tier(tmp_path, monkeypatch):
    """The regenerable tree in `tmp_path`, so nothing here reads Matt's sheets."""
    from fractal_wallpapers import paths

    monkeypatch.setenv(paths.HOT_ROOT_VARIABLE, str(tmp_path / "artifacts"))
    (tmp_path / "artifacts").mkdir()
    return tmp_path / "artifacts"


def a_sheet(tier: Path, name: str, rows, under_sheet: bool = True) -> Path:
    """A built sheet, in whichever of the two shapes a cut can land in."""
    directory = (tier / "sheet" / name) if under_sheet else (tier / name)
    (directory / "full").mkdir(parents=True, exist_ok=True)
    lines = []
    for index, (key, regime) in enumerate(rows, start=1):
        picture = f"full/cut{index:04d}.jpg"
        (directory / picture).write_bytes(b"not really a jpeg")
        lines.append(
            json.dumps(
                {
                    "unit": f"u{index:04d}",
                    "join": {
                        "render": {
                            "resolution": list(regime.resolution),
                            "supersample": regime.supersample,
                            "maxiter": 8000,
                        }
                    },
                    "pictures": [{"path": picture, "caption": ""}],
                    "selected_on": {"candidate": key},
                }
            )
        )
    (directory / "sheet.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return directory


def test_a_sheet_row_at_the_regime_is_found_and_one_at_another_frame_is_not(tier) -> None:
    """The match is the recipe key AND the regime, exact. A seat whose only
    picture is at the candidate frame is a MISS — handing it back would put a
    640x360 picture behind a control that says `1280x720ss2`."""
    a_sheet(tier, "a_cut", [("k_full", fulls.REGIME), ("k_small", OTHER)])

    found = fulls.gather(log=lambda _line: None)

    assert set(found) == {"k_full"}
    assert found["k_full"].name == "cut0001.jpg"


def test_both_places_a_built_sheet_can_live_are_read(tier) -> None:
    """`label build` writes under `artifacts/sheet/`; the one-off cuts that
    predate it wrote under `artifacts/`. Their pictures are real pictures."""
    a_sheet(tier, "newer", [("k_new", fulls.REGIME)])
    a_sheet(tier, "older", [("k_old", fulls.REGIME)], under_sheet=False)

    assert set(fulls.gather(log=lambda _line: None)) == {"k_new", "k_old"}


def test_a_row_missing_its_candidate_key_or_its_picture_is_skipped(tier) -> None:
    """Both are required: a row with no key cannot be matched to a seat, and a
    row naming a file that is not there would index a broken href."""
    directory = a_sheet(tier, "a_cut", [("k_here", fulls.REGIME), ("k_gone", fulls.REGIME)])
    (directory / "full" / "cut0002.jpg").unlink()
    rows = (directory / "sheet.jsonl").read_text(encoding="utf-8").splitlines()
    unkeyed = json.loads(rows[0])
    unkeyed["selected_on"] = {}
    unkeyed["pictures"][0]["path"] = "full/cut0001.jpg"
    (directory / "sheet.jsonl").write_text(
        "\n".join([json.dumps(unkeyed), rows[1]]) + "\n", encoding="utf-8"
    )

    assert fulls.gather(log=lambda _line: None) == {}


def test_what_this_module_made_wins_over_what_it_gathered(tier) -> None:
    """A gathered picture is somebody else's file under somebody else's sweep."""
    a_sheet(tier, "a_cut", [("k0", fulls.REGIME)])
    mine = fulls.store_dir() / "pictures" / "k0.jpg"
    mine.parent.mkdir(parents=True, exist_ok=True)
    mine.write_bytes(b"mine")

    resolved = fulls.index(["k0"], log=lambda _line: None)

    assert resolved["k0"] == mine


def test_the_index_answers_only_for_the_keys_it_was_asked_about(tier) -> None:
    """A record's viewer wants that record's seats; the sheets hold thousands."""
    a_sheet(tier, "a_cut", [("k0", fulls.REGIME), ("k1", fulls.REGIME)])

    assert set(fulls.index(["k1"], log=lambda _line: None)) == {"k1"}


def test_the_index_is_written_beside_the_pictures_and_names_its_regime(tier) -> None:
    a_sheet(tier, "a_cut", [("k0", fulls.REGIME)])

    path = fulls.write_index(fulls.index(["k0"], log=lambda _line: None))
    document = json.loads(path.read_text(encoding="utf-8"))

    assert document["regime"] == fulls.REGIME.spelled == "1280x720ss2"
    assert set(document["pictures"]) == {"k0"}
    assert path == fulls.index_path()


def test_the_regime_is_the_release_one_and_not_a_second_spelling_of_it() -> None:
    """The picture a person decides on is the picture the release leg would ship.
    Two spellings of that would be two geometries, one of which nobody chose."""
    assert fulls.REGIME is release.RELEASE_REGIME


def test_a_row_with_no_recipe_is_refused_rather_than_rendered_as_something_else(tier) -> None:
    with pytest.raises(fulls.FullsRefused, match="no recipe"):
        fulls.render([{"key": "k0"}], log=lambda _line: None)


# --------------------------------------------------------------------------- #
# Pinning: a published record cannot be taken by somebody else's cleanup.
# --------------------------------------------------------------------------- #
def test_pinning_gives_the_record_its_own_name_for_a_borrowed_picture(tier) -> None:
    """The failure this closes, measured on 2026-09-14: 923 of the published
    record's 1,000 fulls resolved to labelling sheets and 895 of those to ONE
    sheet, `gallery_rejection_20260914`. Deleting a spent sheet is ordinary
    housekeeping, and doing it would have taken nine tenths of the published
    gallery's full-resolution pictures with it, silently."""
    directory = a_sheet(tier, "a_cut", [("k0", fulls.REGIME), ("k1", fulls.REGIME)])
    resolved = fulls.index(["k0", "k1"], log=lambda _line: None)
    pin_dir = tier / "curation" / "tentative" / "20260914T000000Z" / "fulls"

    record = fulls.pin(resolved, pin_dir, log=lambda _line: None)

    assert record["linked"] + record["copied"] == 2
    assert not record["failed"]
    import shutil

    shutil.rmtree(directory)
    after = fulls.pinned(pin_dir)
    assert set(after) == {"k0", "k1"}
    assert all(path.read_bytes() == b"not really a jpeg" for path in after.values())


def test_a_hard_link_costs_no_bytes_and_a_copy_says_that_it_did(tier) -> None:
    """The readout is what tells a caller which it paid for. On one volume every
    seat is a second directory entry for bytes that already exist — the published
    record's thousand pinned for `bytes_copied: 0` — and the fallback across
    volumes is a real copy that has to be visible as one."""
    a_sheet(tier, "a_cut", [("k0", fulls.REGIME)])
    resolved = fulls.index(["k0"], log=lambda _line: None)

    record = fulls.pin(resolved, tier / "pinned", log=lambda _line: None)

    assert record["copied"] == record["bytes_copied"] == 0 or record["copied"] == 1
    assert record["linked"] + record["copied"] == 1


def test_an_already_pinned_seat_is_left_alone(tier) -> None:
    """A re-pin must not silently repoint the record at whatever the gather
    resolves to TODAY. The whole reason to pin is that the gather's answer
    moves."""
    a_sheet(tier, "a_cut", [("k0", fulls.REGIME)])
    resolved = fulls.index(["k0"], log=lambda _line: None)
    pin_dir = tier / "pinned"
    fulls.pin(resolved, pin_dir, log=lambda _line: None)

    again = fulls.pin(resolved, pin_dir, log=lambda _line: None)

    assert again["already_pinned"] == 1
    assert again["linked"] == again["copied"] == 0


def test_the_records_own_copy_wins_over_the_sheets(tier) -> None:
    """Weakest first: a gathered picture is somebody else's file under somebody
    else's sweep, one this module made was made for this, and one the record
    pinned is the only one a sheet cleanup cannot reach."""
    a_sheet(tier, "a_cut", [("k0", fulls.REGIME)])
    pin_dir = tier / "pinned"
    pin_dir.mkdir(parents=True)
    (pin_dir / "k0.jpg").write_bytes(b"the record's own")

    resolved = fulls.index(["k0"], log=lambda _line: None, pin_dir=pin_dir)

    assert resolved["k0"] == pin_dir / "k0.jpg"
