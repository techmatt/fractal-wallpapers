"""Styles: every file reads, a spec carries the stack, and the engine draws one."""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers import cli, engine, styles

try:
    ENGINE = engine.engine_path()
except FileNotFoundError:
    ENGINE = None

needs_engine = pytest.mark.skipif(ENGINE is None, reason="the engine is not built")

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
    assert "floating_on_dreams" in styles.names()


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


def test_an_unknown_style_is_refused():
    with pytest.raises(styles.StyleError, match="no style"):
        styles.load("not_a_style")


def test_the_cli_parses_a_style_render():
    args = cli.build_parser().parse_args(
        ["style", "render", "floating_on_dreams", "--location", "x.json", "--colormap", "hsv"]
    )
    assert args.handler is cli.style
    assert args.what == "render" and args.resolution == [2560, 1600]


@needs_engine
def test_the_engine_draws_a_style_and_reports_it(tmp_path):
    document = styles.load("floating_on_dreams")
    output = tmp_path / "style.png"
    report = engine.render_report(styles.spec_of(dict(LOCATION), document, output))
    assert output.is_file()
    assert report["style"]["name"] == "floating_on_dreams"
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
