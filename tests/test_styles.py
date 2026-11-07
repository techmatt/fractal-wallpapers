"""Styles: every file reads, a spec carries the stack, and the engine draws one."""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers import cli, engine, styles

needs_engine = pytest.mark.skipif(not engine.is_built(), reason="the engine is not built")

#: A location every style draws something of: a Julia set with a round interior.
LOCATION = {
    "family": {"kind": "julia", "degree": 2, "c": ["-0.123", "0.745"]},
    "viewport": {"center_re": "0", "center_im": "0", "width": "3.2"},
    "maxiter": 400,
    "render": {"resolution": [48, 30], "supersample": 1, "mode": "smooth", "colormap": "x"},
}


@pytest.mark.parametrize("name", styles.names())
def test_every_style_file_reads_and_names_a_map_that_exists(name):
    document = styles.load(name)
    assert document["style"]["layers"], name
    assert (styles.colormap_dir() / f"{document['suggested_colormap']}.json").is_file()


def test_there_is_a_style():
    assert {"floating_on_dreams", "yas", "teal_tunnel"} <= set(styles.names())


def test_the_tonal_check_holds_a_band_and_two_ceilings():
    reference = {"median": 0.36, "p10": 0.2, "p90": 0.6, "white": 0.01, "black": 0.01}
    assert styles.tone_misses(dict(reference), reference) == []
    paler = {**reference, "median": 0.40}
    assert [miss.split()[0] for miss in styles.tone_misses(paler, reference)] == ["median"]
    flooded = {**reference, "white": 0.07, "black": 0.0}
    assert [miss.split()[0] for miss in styles.tone_misses(flooded, reference)] == ["white"]
    hot = {**reference, "p90": 0.71}
    assert [miss.split()[0] for miss in styles.tone_misses(hot, reference)] == ["p90"]


def test_a_draft_too_small_to_check_is_marked_not_passed(tmp_path, capsys):
    from PIL import Image

    from fractal_wallpapers.cli import style_commands

    reference, small = tmp_path / "ref.png", tmp_path / "small.png"
    Image.new("RGB", (1600, 1000), (119, 119, 119)).save(reference)
    Image.new("RGB", (640, 400), (119, 119, 119)).save(small)
    args = cli.build_parser().parse_args(
        ["style", "tones", "yas", str(small), "--reference", str(reference)]
    )
    assert style_commands.check_tones(args) == 1
    out = capsys.readouterr().out
    assert "DRAFT" in out and "1280x800 ss2" in out


def test_the_tonal_check_reads_a_picture(tmp_path):
    from PIL import Image

    path = tmp_path / "grey.png"
    Image.new("RGB", (64, 40), (119, 119, 119)).save(path)
    stats = styles.tones(path, width=32)
    # sRGB 119 is CIE L* 50 to within a hair.
    assert abs(stats["median"] - 0.5) < 0.01 and stats["white"] == stats["black"] == 0.0


def test_the_cli_parses_a_tonal_check():
    args = cli.build_parser().parse_args(["style", "tones", "yas", "a.jpg", "b.jpg"])
    assert args.handler is cli.style
    assert args.what == "tones" and args.pictures == ["a.jpg", "b.jpg"]


def test_a_spec_carries_the_stack_and_drops_the_mode(tmp_path):
    document = styles.load("floating_on_dreams")
    spec = styles.spec_of(dict(LOCATION), document, tmp_path / "x.png", colormap="hsv")
    assert spec["style"] == document["style"]
    assert "mode" not in spec and "coloring" not in spec and "params" not in spec
    assert spec["colormap"] == "hsv"
    assert (
        styles.spec_of(dict(LOCATION), document, tmp_path / "x.png")["colormap"]
        == (document["suggested_colormap"])
    )


def test_a_sequential_map_is_folded_only_when_a_layer_repeats_it(tmp_path):
    document = styles.load("floating_on_dreams")
    assert not styles.is_cyclic("floating_on_dreams")
    once = styles.spec_of(dict(LOCATION), document, tmp_path / "x.png")
    assert "palette" not in once
    repeated = json.loads(json.dumps(document))
    repeated["style"]["layers"][0]["palette"] = {"cycles": 3.0}
    assert styles.spec_of(dict(LOCATION), repeated, tmp_path / "x.png")["palette"] == {
        "mirror": True
    }
    assert "palette" not in styles.spec_of(
        dict(LOCATION), repeated, tmp_path / "x.png", colormap="hsv"
    )


def test_a_location_lays_its_own_twist_and_ring_over_the_style_projection(tmp_path):
    document = styles.load("teal_tunnel")
    own = document["style"]["projection"]["log_polar"]
    row = {**LOCATION, "projection": {"log_polar": {"twist": 0.25, "ring": 4.0}}}
    spec = styles.spec_of(row, document, tmp_path / "x.png")
    merged = spec["style"]["projection"]["log_polar"]
    assert merged == {**own, "twist": 0.25, "ring": 4.0}
    assert document["style"]["projection"]["log_polar"] == own, "the style file is untouched"
    # A straight style draws straight wherever it is drawn.
    straight = styles.load("yas")
    assert "projection" not in styles.spec_of(row, straight, tmp_path / "x.png")["style"]


def test_a_location_record_keeps_its_projection():
    from fractal_wallpapers import locations

    row = {"schema": 1, **LOCATION, "projection": {"log_polar": {"twist": 0.1}}}
    assert locations.record(row)["projection"] == {"log_polar": {"twist": 0.1}}
    assert "projection" not in locations.record({"schema": 1, **LOCATION})


def test_an_unknown_style_is_refused():
    with pytest.raises(styles.StyleError, match="no style"):
        styles.load("not_a_style")


def test_a_sixteen_bit_grey_picture_reads_its_own_lightness(tmp_path):
    """Pillow's own conversion clipped a 16-bit grey picture to white."""
    from PIL import Image

    deep, shallow = tmp_path / "deep.png", tmp_path / "shallow.png"
    Image.new("I;16", (64, 40), 20000).save(deep)
    Image.new("L", (64, 40), round(20000 / 256)).save(shallow)
    assert styles.tones(deep)["median"] == pytest.approx(styles.tones(shallow)["median"])


def test_an_unreadable_reference_is_refused_not_raised(tmp_path, capsys):
    from fractal_wallpapers.cli import style_commands

    broken = tmp_path / "ref.png"
    broken.write_text("not a picture", encoding="utf-8")
    args = cli.build_parser().parse_args(["style", "tones", "yas", "--reference", str(broken)])
    assert style_commands.check_tones(args) == 1
    assert "cannot read the reference" in capsys.readouterr().out


def test_a_manifest_rows_name_is_one_file_name():
    from fractal_wallpapers.cli.style_commands import file_name

    assert file_name("00_a b/c:d_Lilac Vellum.png") == "00_a b_c_d_Lilac Vellum.png"


def test_a_draft_that_does_not_read_is_refused_not_raised(tmp_path):
    """A broken draft once came back as a JSON traceback from `style show` and `render`."""
    garbled = tmp_path / "garbled.json"
    garbled.write_text("{not json", encoding="utf-8")
    with pytest.raises(styles.StyleError, match="does not read"):
        styles.load(str(garbled))
    listed = tmp_path / "listed.json"
    listed.write_text("[]", encoding="utf-8")
    with pytest.raises(styles.StyleError, match="not a style file"):
        styles.load(str(listed))
    with pytest.raises(styles.StyleError, match="no draft style file"):
        styles.load(str(tmp_path / "missing.json"))


def test_a_knob_asked_for_wins_over_the_records_own_projection(tmp_path):
    """`teal_tunnel`'s keeps carry `turns`, which once silenced its `turns` knob."""
    document = styles.load("teal_tunnel")
    row = {**LOCATION, "projection": {"log_polar": {"turns": 8, "twist": 0.1}}}
    plain = styles.spec_of(row, document, tmp_path / "x.png")
    assert plain["style"]["projection"]["log_polar"]["turns"] == 8
    turned = styles.spec_of(row, document, tmp_path / "x.png", knobs={"turns": 3})
    assert turned["style"]["projection"]["log_polar"]["turns"] == 3
    assert turned["style"]["projection"]["log_polar"]["twist"] == 0.1


def test_a_merged_name_holds_its_tones_to_its_own_reference():
    """A palette entry was fitted to its own picture: `style tones crisis_smooth` once read
    `smooth_bands`' reference instead."""
    rows = styles.catalog_rows()
    merged = [
        (row, entry)
        for row in rows
        for entry in row.get("palettes", [])
        if entry.get("was") and entry.get("reference")
    ]
    assert merged, "the catalog holds a merged entry with its own reference"
    for _row, entry in merged:
        document = styles.load(entry["was"])
        assert document["reference"]["image"] == entry["reference"], entry["was"]
    mode = styles.load(merged[0][0]["style"])
    assert mode["reference"]["image"] == merged[0][0]["reference"]


@pytest.mark.parametrize("name", styles.names())
def test_no_public_knob_turns_only_what_a_flat_light_ignores(name):
    """A knob writing only a light's `period` or `bands` where its `rings` is 0 moves no
    pixel: there the normal is the slope alone (`lit_petals`' `petal_depth`, dropped)."""
    document = styles.load(name)
    lights = [layer.get("light") for layer in document["style"]["layers"]]
    for knob in (document.get("public") or {}).get("knobs") or []:
        pointers = [s if isinstance(s, str) else s["path"] for s in knob["set"]]
        places = [place for p in pointers for place in styles.targets(document["style"], p)]
        dead = bool(places) and all(
            key in ("period", "bands")
            and any(node is light for light in lights)
            and node.get("rings", 0.7) == 0
            for node, key in places
        )
        assert not dead, (name, knob["name"])


def test_the_cli_parses_a_style_render():
    args = cli.build_parser().parse_args(
        ["style", "render", "floating_on_dreams", "--location", "x.json", "--colormap", "hsv"]
    )
    assert args.handler is cli.style
    assert args.what == "render" and args.resolution == [2560, 1600]


@needs_engine
@pytest.mark.parametrize("name", styles.names())
def test_the_engine_draws_a_style_and_reports_it(tmp_path, name):
    document = styles.load(name)
    output = tmp_path / "style.png"
    report = engine.render_report(styles.spec_of(dict(LOCATION), document, output))
    assert output.is_file()
    assert report["style"]["name"] == name
    assert "coloring" not in report
    assert 0.0 < report["interior_fraction"] < 1.0


@needs_engine
def test_the_engine_refuses_a_style_beside_a_mode(tmp_path):
    document = styles.load("floating_on_dreams")
    spec = styles.spec_of(dict(LOCATION), document, tmp_path / "x.png")
    spec["mode"] = "smooth"
    with pytest.raises(RuntimeError, match="give it alone"):
        engine.render_report(spec)
    del spec["mode"]
    spec["palette"] = {"cycles": 2.0}
    with pytest.raises(RuntimeError, match="each palette"):
        engine.render_report(spec)
