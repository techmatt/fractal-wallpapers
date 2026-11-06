"""`style keep`: a picker's keeps recorded, copied, merged and redrawn when gone."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fractal_wallpapers import engine, style_keeps, styles

LOCATION = {
    "schema": 1,
    "name": "m2_somewhere",
    "family": {"kind": "mandelbrot", "degree": 2},
    "viewport": {"center_re": "-0.5", "center_im": "0", "width": "3"},
    "maxiter": 500,
}


def picker(tmp_path: Path, name: str, keys: dict[str, list[str]], note: str = "") -> Path:
    """A picker on disk: manifest, images, renders sidecar and a saved choices file."""
    folder = tmp_path / name
    (folder / "shortlist").mkdir(parents=True)
    options = []
    renders = []
    for key in ("00_m2_somewhere", "01_m2_somewhere__hsv"):
        image = f"shortlist/{key}.jpg"
        (folder / image).write_bytes(key.encode())
        options.append({"key": key, "image": image, "label": key})
        renders.append(
            {
                "key": key,
                "location": LOCATION,
                "style": "yas",
                "colormap": "hsv" if key.endswith("hsv") else "yas",
                "resolution": [64, 40],
                "supersample": 1,
            }
        )
    # A baseline row reusing the shortlist's first picture under another key.
    options_base = [{"key": "style_00", "image": "shortlist/00_m2_somewhere.jpg"}]
    renders.append({**renders[0], "key": "style_00"})
    manifest = {
        "name": name,
        "rows": [
            {"id": "shortlist", "kind": "many", "options": options},
            {"id": "baseline", "kind": "many", "options": options_base},
        ],
    }
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with (folder / "renders.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in renders:
            handle.write(json.dumps(row) + "\n")
    choices = {
        "name": name,
        "rows": [{"id": rid, "keys": kept, "note": note} for rid, kept in keys.items()],
    }
    path = tmp_path / f"{name}.choices.json"
    path.write_text(json.dumps(choices), encoding="utf-8")
    return path


@pytest.fixture
def places(tmp_path, monkeypatch):
    reference = tmp_path / "ref.jpg"
    reference.write_bytes(b"ref")
    monkeypatch.setattr(styles, "reference_path", lambda document: reference)
    return {"folder": tmp_path / "keeps", "record": tmp_path / "yas.keeps.json"}


def run(choices: Path, places: dict) -> dict:
    return style_keeps.keep(
        "yas",
        choices,
        manifest_path=choices.parent / choices.name.replace(".choices.json", "") / "manifest.json",
        folder=places["folder"],
        record=places["record"],
    )


def test_a_round_records_and_copies_each_kept_picture_once(tmp_path, places):
    choices = picker(
        tmp_path,
        "style_x_r1",
        {"shortlist": ["00_m2_somewhere"], "baseline": ["style_00"]},
        note="the good one",
    )
    done = run(choices, places)
    record = json.loads(places["record"].read_text(encoding="utf-8"))
    assert done["kept"] == 1 and done["copied"] == 1
    (entry,) = record["keeps"]
    assert entry["picked"] == [
        {"row": "shortlist", "key": "00_m2_somewhere"},
        {"row": "baseline", "key": "style_00"},
    ]
    assert entry["note"] == "the good one"
    assert entry["render"]["location"] == LOCATION
    assert entry["render"]["stack"] in record["stacks"]
    assert (places["folder"] / entry["image"]).read_bytes() == b"00_m2_somewhere"
    assert (places["folder"] / "ref.jpg").read_bytes() == b"ref"
    assert "source" not in entry


def test_a_later_round_adds_and_never_drops(tmp_path, places):
    run(picker(tmp_path, "style_x_r1", {"shortlist": ["00_m2_somewhere"]}), places)
    run(picker(tmp_path, "style_x_r2", {"shortlist": ["01_m2_somewhere__hsv"]}), places)
    record = json.loads(places["record"].read_text(encoding="utf-8"))
    assert [entry["id"] for entry in record["keeps"]] == [
        "style_x_r1/shortlist/00_m2_somewhere",
        "style_x_r2/shortlist/01_m2_somewhere__hsv",
    ]


def test_a_gone_picture_is_drawn_again_from_its_record(tmp_path, places, monkeypatch):
    choices = picker(tmp_path, "style_x_r1", {"shortlist": ["01_m2_somewhere__hsv"]})
    (tmp_path / "style_x_r1" / "shortlist" / "01_m2_somewhere__hsv.jpg").unlink()
    specs = []

    def fake(spec):
        specs.append(spec)
        Path(spec["output"]).write_bytes(b"drawn")
        return {}

    monkeypatch.setattr(engine, "render_report", fake)
    done = run(choices, places)
    assert done["drawn"] == 1
    (spec,) = specs
    assert spec["colormap"] == "hsv" and spec["resolution"] == [64, 40]
    assert spec["style"]["name"] == "yas"


def test_a_kept_key_without_a_render_row_refuses(tmp_path, places):
    choices = picker(tmp_path, "style_x_r1", {"shortlist": ["00_m2_somewhere"]})
    (tmp_path / "style_x_r1" / "renders.jsonl").write_text("", encoding="utf-8")
    with pytest.raises(style_keeps.KeepError, match="no render row"):
        run(choices, places)


def test_a_group_pickers_keeps_go_to_the_style_each_row_names():
    choices = {
        "name": "style_group_r1",
        "rows": [
            {"id": "yas/locations", "keys": ["a"]},
            {"id": "ember_rose/locations", "keys": ["b"]},
            {"id": "formulations", "keys": ["c"]},
        ],
    }
    rows = style_keeps.rows_of(choices, "yas")["rows"]
    assert [row["id"] for row in rows] == ["yas/locations", "formulations"]
    assert len(choices["rows"]) == 3, "the caller's choices are left whole"


def test_a_keeps_file_is_not_a_style():
    assert not any(name.endswith(".keeps") for name in styles.names())
