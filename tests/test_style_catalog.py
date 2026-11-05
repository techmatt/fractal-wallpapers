"""The custom-mode catalog, the published modes' public knobs, and the page built from them."""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers import cli, style_catalog, styles


def published():
    """The catalog's published rows."""
    return [row for row in style_catalog.load()["modes"] if row["status"] == "publish"]


def test_the_catalog_holds_its_rows_and_agrees_with_the_styles():
    catalog = style_catalog.load()
    assert style_catalog.check(catalog) == []
    names = [row["style"] for row in catalog["modes"]]
    assert len(names) == len(set(names)) >= 14
    assert {row["status"] for row in catalog["modes"]} <= set(style_catalog.STATUSES)


def test_the_catalog_is_not_a_style():
    assert styles.CATALOG_FILE.removesuffix(".json") not in styles.names()


@pytest.mark.parametrize("row", published(), ids=lambda row: row["style"])
def test_a_published_mode_exposes_knobs_whose_defaults_are_its_stack(row):
    document = styles.load(row["style"])
    knobs = document["public"]["knobs"]
    assert 3 <= len(knobs) <= 5
    assert styles.check_public(document) == []
    assert row["public"]["palette"] == document["suggested_colormap"]


@pytest.mark.parametrize("row", published(), ids=lambda row: row["style"])
def test_every_knob_moves_its_stack_at_either_end(row):
    document = styles.load(row["style"])
    for knob in document["public"]["knobs"]:
        for end in knob["range"]:
            if end == knob["default"]:
                continue
            turned = styles.with_knobs(document, {knob["name"]: end})
            assert turned["style"] != document["style"], (knob["name"], end)
    assert styles.with_knobs(document, {})["style"] == document["style"]


def test_a_knob_writes_every_target_and_refuses_what_it_does_not_offer():
    document = styles.load("gilded_orbs")
    turned = styles.with_knobs(document, {"orb_size": 0.3, "light_angle": 200})
    layers = turned["style"]["layers"]
    assert {layers[i]["channel"]["bubble"]["radius"] for i in range(12, 17)} == {0.3}
    assert {round(layers[i]["channel"]["bubble"]["largest"], 9) for i in range(12, 17)} == {0.25}
    lights = [layer["light"]["azimuth"] for layer in layers if layer["kind"] == "light"]
    assert lights and set(lights) == {200}
    assert document["style"]["layers"][12]["channel"]["bubble"]["radius"] == 0.12
    with pytest.raises(styles.StyleError, match="outside"):
        styles.with_knobs(document, {"orb_size": 0.5})
    with pytest.raises(styles.StyleError, match="no knob"):
        styles.with_knobs(document, {"swirl": 0.2})


def test_a_whole_number_member_stays_whole():
    turned = styles.with_knobs(styles.load("teal_tunnel"), {"turns": 3})
    assert turned["style"]["projection"]["log_polar"]["turns"] == 3
    assert isinstance(turned["style"]["projection"]["log_polar"]["turns"], int)


def test_knob_arguments_parse_and_refuse_a_bad_pair():
    assert styles.parse_knobs(["a=1", "b = 0.5"]) == {"a": 1.0, "b": 0.5}
    for bad in ("a", "a=x", "=1"):
        with pytest.raises(styles.StyleError):
            styles.parse_knobs([bad])


def test_the_cli_parses_a_knob_and_the_gallery():
    parser = cli.build_parser()
    args = parser.parse_args(
        ["style", "render", "yas", "--location", "x.json", "--knob", "swirl=0.4"]
    )
    assert args.knob == ["swirl=0.4"]
    assert parser.parse_args(["style", "gallery", "--out", "x"]).out == "x"


def test_the_gallery_starts_each_toggle_from_the_status(tmp_path, monkeypatch):
    from PIL import Image

    reference = tmp_path / "ref.png"
    Image.new("RGB", (2000, 1250), (40, 60, 90)).save(reference)
    monkeypatch.setattr(styles, "reference_path", lambda document: reference)
    rows = [
        {**row, "show": []}
        for row in style_catalog.load()["modes"]
        if row["style"] in ("yas", "field_lines", "leaf_veins")
    ]
    folder = tmp_path / "page"
    (folder / "img").mkdir(parents=True)
    (folder / "img" / "stale.jpg").write_bytes(b"")
    done = style_catalog.gallery(folder, {"schema": 1, "modes": rows})
    assert (done["shown"], done["discarded"], done["written"]) == (2, 1, 3)
    page = (folder / "index.html").read_text(encoding="utf-8")
    assert json.dumps({"yas": "publish", "field_lines": "drop"}) in page
    assert 'data-id="yas"' in page and "glass-whorl" in page and "Discarded" in page
    assert not (folder / "img" / "stale.jpg").exists()
    with Image.open(folder / "img" / "yas__ref.jpg") as small:
        assert small.width == style_catalog.REFERENCE_WIDTH
    again = style_catalog.gallery(folder, {"schema": 1, "modes": rows})
    assert again["written"] == 0
