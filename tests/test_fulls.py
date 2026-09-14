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
