"""The Python-to-Rust boundary.

The spec-building half runs anywhere. The half that actually renders needs a
built binary, and CI lints and tests before it compiles the crate, so those
tests skip rather than fail when the engine is absent.
"""

from __future__ import annotations

import argparse

import pytest

from fractal_wallpapers import cli, engine

try:
    ENGINE = engine.engine_path()
except FileNotFoundError:
    ENGINE = None

needs_engine = pytest.mark.skipif(ENGINE is None, reason="the engine is not built")


def arguments(**overrides) -> argparse.Namespace:
    """A parsed `render` command line, with overrides applied."""
    parser = cli.build_parser()
    args = parser.parse_args(["render"])
    for key, value in overrides.items():
        setattr(args, key, value)
    return args


def test_the_render_subcommand_is_registered() -> None:
    assert cli.build_parser().parse_args(["render"]).handler is cli.render


def test_a_default_spec_names_a_family_and_a_colormap() -> None:
    spec = cli.render_spec(arguments())
    assert spec["schema"] == 1
    assert spec["family"] == {"kind": "mandelbrot"}
    assert spec["colormap"] == "twilight_shifted"
    assert "viewport" not in spec, "an unspecified view is left for the engine to default"
    assert "maxiter" not in spec, "an unspecified cap is left to the policy"


def test_coordinates_reach_the_spec_as_the_strings_they_were_written_as() -> None:
    written = "0.41041350545462440"
    spec = cli.render_spec(arguments(center_re=written, width="0.5622541254857749"))
    assert spec["viewport"]["center_re"] == written
    assert spec["viewport"]["width"] == "0.5622541254857749"
    assert "center_im" not in spec["viewport"]


def test_each_family_carries_its_own_constants() -> None:
    julia = cli.render_spec(arguments(family="julia", c=["-0.4", "0.6"]))
    assert julia["family"] == {"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]}

    multibrot = cli.render_spec(arguments(family="multibrot", degree=4))
    assert multibrot["family"] == {"kind": "multibrot", "degree": 4}

    phoenix = cli.render_spec(arguments(family="phoenix", p=["-0.5", "0.1"]))
    assert phoenix["family"] == {"kind": "phoenix", "p": ["-0.5", "0.1"]}


def test_a_julia_render_without_its_constant_is_refused() -> None:
    assert cli.render(arguments(family="julia")) == 1


def test_a_relative_output_lands_under_the_repository() -> None:
    resolved = cli.resolve_output("artifacts/render.png")
    assert resolved.is_absolute()
    assert resolved.parent == cli.repo_root() / "artifacts"


@needs_engine
def test_a_render_produces_a_png_and_a_report(tmp_path) -> None:
    output = tmp_path / "small.png"
    report = engine.render_report(
        {
            "schema": 1,
            "family": {"kind": "julia", "c": ["-0.4", "0.6"]},
            "resolution": [48, 27],
            "supersample": 1,
            "colormap": "twilight_shifted",
            "colormap_dir": str(cli.colormap_dir()),
            "maxiter": 200,
            "output": str(output),
        }
    )
    assert output.is_file()
    assert output.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert report["maxiter"] == 200
    assert report["location"]["c"] == ["-0.4", "0.6"]
    assert report["resolution"] == [48, 27]


@needs_engine
def test_a_rejected_spec_surfaces_the_engine_s_complaint() -> None:
    with pytest.raises(RuntimeError, match="degree"):
        engine.render_report(
            {
                "schema": 1,
                "family": {"kind": "multibrot", "degree": 9},
                "resolution": [8, 8],
                "colormap": "twilight_shifted",
                "colormap_dir": str(cli.colormap_dir()),
                "output": "unreachable.png",
            }
        )
