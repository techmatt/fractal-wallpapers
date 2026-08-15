"""The command line is the project's only entry point, so it is smoke-tested here."""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers import cli


def test_every_runnable_thing_is_a_subcommand() -> None:
    parser = cli.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_fetch_weights_is_registered() -> None:
    args = cli.build_parser().parse_args(["fetch-weights"])
    assert args.handler is cli.fetch_weights


def test_the_walk_is_a_subcommand_with_a_default_seed_source() -> None:
    args = cli.build_parser().parse_args(["walk"])
    assert args.handler is cli.walk
    assert args.family == "julia", "the family with a tracked pool"
    assert args.seeds is None


def test_a_parameter_plane_walk_refuses_rather_than_inventing_roots() -> None:
    """There is no sampler for the c-plane, and there is not going to be one:
    an unscreened draw over the higher degrees measured zero good locations in
    144. A walk asked to source them from nothing says so, before it has built
    anything or left a run directory behind."""
    parse = cli.build_parser().parse_args
    for arguments in (
        ["walk", "--family", "multibrot", "--degree", "4"],
        ["walk", "--family", "mandelbrot"],
        ["walk", "--family", "julia", "--degree", "3"],
    ):
        assert "--seeds" in (cli.refuse_impossible_walk(parse(arguments)) or "")

    assert cli.refuse_impossible_walk(parse(["walk"])) is None
    assert cli.refuse_impossible_walk(parse(["walk", "--family", "phoenix"])) is None
    assert (
        cli.refuse_impossible_walk(parse(["walk", "--family", "mandelbrot", "--seeds", "x"]))
        is None
    )


def test_the_supply_engine_is_four_subcommands_and_no_scripts() -> None:
    """The production loop, the census it runs on, and the two derivations that
    regenerate the tables it reads. Every one of them is a step somebody will run
    twice, so every one of them has a name and `--help` text."""
    parse = cli.build_parser().parse_args
    assert parse(["harvest"]).handler is cli.harvest
    assert parse(["census"]).handler is cli.census
    assert parse(["derive-prices", "--run", "x"]).handler is cli.derive_prices
    assert parse(["derive-tau-h"]).handler is cli.derive_tau_h


def test_a_derivation_does_not_overwrite_a_shipped_table_unasked() -> None:
    """A table is the record of a decision. Replacing one is a deliberate act, so
    the default is to print what would be written."""
    for arguments in (["derive-prices", "--run", "x"], ["derive-tau-h"]):
        assert cli.build_parser().parse_args(arguments).write is False


def test_the_machine_stock_discount_is_a_flag_on_both_readers() -> None:
    """`--discount 0` has to reproduce the labels-only deficit exactly, which is
    only useful if the same switch is on the census and on the run."""
    parse = cli.build_parser().parse_args
    assert parse(["census", "--discount", "0"]).discount == 0.0
    assert parse(["harvest", "--discount", "0"]).discount == 0.0


def test_weights_manifest_is_valid_and_versioned() -> None:
    manifest_path = cli.repo_root() / cli.WEIGHTS_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema"] == 1
    assert isinstance(manifest["heads"], dict)
