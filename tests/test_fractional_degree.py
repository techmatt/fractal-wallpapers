"""A fractional degree draws pictures, and is refused everywhere else.

The engine can render `z ← z^d + c` at a non-integer `d` on the principal
branch. It exists for one figure in the article, and it is **render-only**: a
written render or dump-field spec reaches it and nothing else does. That is a
guarantee about what cannot happen, so this file is mostly refusals — the supply
engine's partition registry, the plane question the render-cache builds jobs
through, the framing table, and the command line all turn it away, each with a
message rather than a default.

The half that renders needs a built binary and skips without one, the same way
the rest of the engine-facing tests do.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers import cli, engine
from fractal_wallpapers.supply import location, partitions

try:
    ENGINE = engine.engine_path()
except FileNotFoundError:
    ENGINE = None

needs_engine = pytest.mark.skipif(ENGINE is None, reason="the engine is not built")

FRACTIONAL = {"kind": "fractional_multibrot", "degree": "2.5"}

#: Somewhere to look. A render-only family has no home view, so every spec for
#: one says where it is framed.
VIEWPORT = {"center_re": "-0.4", "center_im": "0", "width": "4.0"}


def test_the_supply_engine_has_no_partition_to_put_it_in() -> None:
    """The books are keyed on partitions, and this family registers none.

    Every per-partition table — the ratio, the price, the floor, τ_h — is reached
    through this resolver, and it refuses an unregistered kind rather than
    routing it to a default. So a fractional-degree row cannot be counted,
    priced, or allocated against: not because each table checks, but because
    there is no key to check with.
    """
    with pytest.raises(partitions.UnregisteredPartition):
        partitions.partition_of_family(FRACTIONAL)
    with pytest.raises(partitions.UnregisteredPartition):
        partitions.partition_of_row({"family": FRACTIONAL, "viewport": VIEWPORT})


def test_a_fractional_row_carries_no_location_identity() -> None:
    """The identity a label and a ledger row join on is unreachable for it.

    `key_of_row` answers `None` for a row it cannot key, and the caller counts
    those rather than dropping them — so such a row would show up as an
    unjoinable row in a report, which is the loudest failure available short of
    an exception.
    """
    assert location.key_of_row({"family": FRACTIONAL, "viewport": VIEWPORT}) is None


def test_the_render_cache_cannot_build_a_job_for_it() -> None:
    """A judge's corpus is built through the plane question, which refuses it."""
    with pytest.raises(ValueError, match="render jobs"):
        engine.pixel_is_z0(FRACTIONAL)
    assert "fractional_multibrot" not in engine.PARAMETER_KINDS | engine.DYNAMICAL_KINDS


def family_choices() -> dict[str, list[str]]:
    """Every family a subcommand will accept, by subcommand."""
    import argparse

    parser = cli.build_parser()
    offered = {}
    for action in parser._subparsers._group_actions:
        if not isinstance(action, argparse._SubParsersAction):
            continue
        for name, subparser in action.choices.items():
            for option in subparser._actions:
                if "--family" in option.option_strings and option.choices:
                    offered[name] = list(option.choices)
    return offered


def test_no_subcommand_offers_it() -> None:
    """It is reachable by writing a spec, and by nothing on the command line.

    Which is the *whole* of the reachability guarantee on this side: a family
    nobody can name to a subcommand cannot arrive in a discovery run, a harvest,
    or a release by anyone typing it.
    """
    offered = family_choices()
    assert offered, "no subcommand offers a --family at all, so this proves nothing"
    for command, choices in offered.items():
        assert "fractional_multibrot" not in choices, command
        assert "mandelbrot" in choices, f"{command}: the check itself is looking at nothing"


@needs_engine
def test_the_framing_table_has_no_row_for_it() -> None:
    """No home view, so no place a walk or a refill could be told to start."""
    with pytest.raises(RuntimeError, match="render-only"):
        engine.home_view(FRACTIONAL)


@needs_engine
def test_a_fractional_render_records_the_degree_it_was_written_with(tmp_path) -> None:
    """The end-to-end proof: a picture at d = 2.5, and a record that says so.

    The degree survives as the string the spec wrote, exactly as a coordinate
    does, so the record is the whole identity of the render and two nearby
    degrees are two renders rather than two roundings of one.
    """
    output = tmp_path / "fractional.png"
    report = engine.render_report(
        {
            "schema": 1,
            "family": FRACTIONAL,
            "viewport": VIEWPORT,
            "resolution": [160, 90],
            "supersample": 1,
            "mode": "smooth",
            "colormap": "twilight_shifted",
            "colormap_dir": str(engine.colormap_dir()),
            "output": str(output),
        }
    )
    assert output.is_file()
    assert report["location"]["family"] == "fractional_multibrot"
    assert report["location"]["degree"] == "2.5"
    # Some of the frame escapes and some of it does not: a set was drawn, rather
    # than a flat field that happens to have written a file.
    assert 0.05 < report["interior_fraction"] < 0.95


@needs_engine
def test_an_integer_degree_still_records_a_bare_number(tmp_path) -> None:
    """The wire that already existed is unchanged, byte for byte."""
    report = engine.render_report(
        {
            "schema": 1,
            "family": {"kind": "multibrot", "degree": 3},
            "resolution": [64, 36],
            "supersample": 1,
            "mode": "smooth",
            "colormap": "twilight_shifted",
            "colormap_dir": str(engine.colormap_dir()),
            "output": str(tmp_path / "integer.png"),
        }
    )
    assert report["location"]["degree"] == 3
    assert '"degree": 3' in json.dumps(report["location"], indent=1)


@needs_engine
def test_a_render_without_a_viewport_is_refused_rather_than_framed(tmp_path) -> None:
    """No default frame is invented for a family the home table has no row for."""
    with pytest.raises(RuntimeError, match="no home view"):
        engine.render_report(
            {
                "schema": 1,
                "family": FRACTIONAL,
                "resolution": [32, 18],
                "mode": "smooth",
                "colormap": "twilight_shifted",
                "colormap_dir": str(engine.colormap_dir()),
                "output": str(tmp_path / "unframed.png"),
            }
        )


@needs_engine
def test_a_whole_degree_belongs_to_the_integer_family(tmp_path) -> None:
    """One picture, one name: `degree: "3.0"` is the multibrot's and is refused."""
    with pytest.raises(RuntimeError, match="whole number"):
        engine.render_report(
            {
                "schema": 1,
                "family": {"kind": "fractional_multibrot", "degree": "3.0"},
                "viewport": VIEWPORT,
                "resolution": [32, 18],
                "mode": "smooth",
                "colormap": "twilight_shifted",
                "colormap_dir": str(engine.colormap_dir()),
                "output": str(tmp_path / "whole.png"),
            }
        )
