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


def test_a_kept_tile_goes_to_the_mode_that_drew_it_whatever_row_it_sits_in():
    """060 split a choices file by hand to save a molten_flow baseline tile kept in a
    stirred_ink row as a molten_flow keep; the render row now decides."""
    choices = {
        "name": "style_ink_r1",
        "rows": [
            {"id": "ink/formulations", "keys": ["own", "draft", "molten", "smooth"]},
            {"id": "pools/formulations", "keys": ["pool", "molten_2"]},
            {"id": "locations", "keys": ["loc", "lobes"]},
        ],
    }
    renders = {
        "own": {"style": "ink"},
        "draft": {"style": "ink__no_core"},
        "molten": {"style": "molten_flow"},
        "smooth": {"mode": "smooth"},
        "pool": {"style": "pools"},
        "molten_2": {"style": "old_molten"},
        "loc": {"style": "ink"},
        "lobes": {"style": "glossy_lobes"},
    }
    modes = {
        "ink": "ink",
        "pools": "pools",
        "molten_flow": "molten_flow",
        "old_molten": "molten_flow",
        "glossy_lobes": "glossy_lobes",
    }

    def keys(name):
        rows = style_keeps.rows_of(choices, name, renders, modes)["rows"]
        return {row["id"]: row["keys"] for row in rows}

    assert keys("ink") == {"ink/formulations": ["own", "draft", "smooth"], "locations": ["loc"]}
    assert keys("molten_flow") == {
        "ink/formulations": ["molten"],
        "pools/formulations": ["molten_2"],
    }
    assert keys("pools") == {"pools/formulations": ["pool"]}
    assert keys("glossy_lobes") == {"locations": ["lobes"]}
    # what `ink`'s run leaves out is named, so no keep is lost between the two runs
    assert style_keeps.left_to(choices, "ink", renders, modes) == {
        "molten_flow": ["molten"],
        "glossy_lobes": ["lobes"],
    }
    assert style_keeps.left_to(choices, "pools", renders, modes) == {
        "molten_flow": ["molten_2"],
        "ink": ["loc"],
        "glossy_lobes": ["lobes"],
    }


def test_style_keep_leaves_another_modes_tile_to_that_mode(tmp_path, places):
    choices = picker(
        tmp_path, "style_x_r1", {"shortlist": ["00_m2_somewhere"], "baseline": ["style_00"]}
    )
    renders = tmp_path / "style_x_r1" / "renders.jsonl"
    rows = [json.loads(line) for line in renders.read_text(encoding="utf-8").splitlines()]
    rows[-1]["style"] = "molten_flow"
    renders.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    run(choices, places)
    (entry,) = json.loads(places["record"].read_text(encoding="utf-8"))["keeps"]
    assert entry["picked"] == [{"row": "shortlist", "key": "00_m2_somewhere"}]


def test_a_keeps_file_is_not_a_style():
    assert not any(name.endswith(".keeps") for name in styles.names())


def test_a_new_rows_default_palette_is_the_stacks_own(tmp_path):
    """Step 10's `--sync` read the default entry's values off its first keep, often a
    round-one formulation, and wrote a catalog `style_catalog.load` then refused."""
    import copy

    document = styles.load("lit_petals")
    formulation = copy.deepcopy(document["style"])
    formulation["layers"][2]["opacity"] = 0.5
    catalog = tmp_path / "catalog.json"
    catalog.write_text(
        json.dumps({"schema": 1, "modes": [{"style": "lit_petals", "palettes": []}]}),
        encoding="utf-8",
    )
    keeps = [
        {
            "id": "r1/formulations/half_jewels",
            "render": {"style": "lit_petals", "colormap": "lit_petals", "stack": "s1"},
        }
    ]
    added = style_keeps.palettes_from("lit_petals", keeps, {"s1": formulation}, path=catalog)
    assert added == ["lit_petals"]
    row = json.loads(catalog.read_text(encoding="utf-8"))["modes"][0]
    assert row["palettes"][0]["colormap"] == "lit_petals"
    assert row["palettes"][0]["values"] == {}
    assert row["palettes"][0]["keeps"] == ["r1/formulations/half_jewels"]

    # No tile kept in the suggested map: it still heads the set, unkept, and the kept
    # map keeps its tuned values behind it.
    catalog.write_text(
        json.dumps({"schema": 1, "modes": [{"style": "lit_petals", "palettes": []}]}),
        encoding="utf-8",
    )
    elsewhere = [{**keeps[0], "render": {**keeps[0]["render"], "colormap": "magma"}}]
    style_keeps.palettes_from("lit_petals", elsewhere, {"s1": formulation}, path=catalog)
    row = json.loads(catalog.read_text(encoding="utf-8"))["modes"][0]
    assert [entry["colormap"] for entry in row["palettes"]] == ["lit_petals", "magma"]
    assert row["palettes"][0] == {"colormap": "lit_petals", "values": {}, "keeps": []}
    assert row["palettes"][1]["values"]
