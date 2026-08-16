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


def test_the_labeling_rig_is_five_steps_under_one_subcommand() -> None:
    """Register, cut, serve, record, split — the order they happen in, and every
    one of them a step somebody runs twice."""
    parse = cli.build_parser().parse_args
    assert (
        parse(["label", "register", "--batch", "b", "--method", "m"]).handler is cli.label_register
    )
    assert parse(["label", "build", "--from-batch", "b", "--batch", "b"]).handler is cli.label_build
    assert parse(["label", "serve", "--sheet", "d"]).handler is cli.label_serve
    assert parse(
        ["label", "record", "--sheet", "d", "--labels", "l", "--labeler", "m"]
    ).handler is (cli.label_record)
    assert parse(["label", "split"]).handler is cli.label_split
    assert parse(["label", "show"]).handler is cli.label_show
    with pytest.raises(SystemExit):
        parse(["label"])


def test_a_sheet_is_cut_from_one_source_or_the_other() -> None:
    """A ledger and a stored batch are two populations; a sheet that took both
    would be one cut with two generation methods and one registration."""
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["label", "build", "--batch", "b"])
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(
            ["label", "build", "--batch", "b", "--from-batch", "x", "--from-ledger", "y"]
        )


def test_registering_a_batch_claims_neither_property_by_default() -> None:
    """Both flags are claims about how a population was drawn, and the fail-closed
    reading of an unmade claim is the safe one."""
    args = cli.build_parser().parse_args(["label", "register", "--batch", "b", "--method", "m"])
    assert args.score_unconditioned is False
    assert args.anchored is False


def test_the_split_is_not_reshipped_unasked() -> None:
    assert cli.build_parser().parse_args(["label", "split"]).write is False


def test_the_import_names_its_source_rather_than_knowing_it() -> None:
    """No tracked file may hold an absolute path, and the corpus it reads lives
    outside this repository — so the source is an argument, always."""
    args = cli.build_parser().parse_args(["import-labels", "--source", "somewhere"])
    assert args.handler is cli.import_labels
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["import-labels"])


def test_the_palette_head_is_eight_steps_under_one_subcommand() -> None:
    """It is distilled rather than trained from labels, so it has two steps the
    other heads do not: vendoring the real candidate sets and generating a corpus."""
    parser = cli.build_parser()
    handlers = {
        step: parser.parse_args(["palette", step, *extra]).handler
        for step, extra in (
            ("extract", ["--source", "."]),
            ("plan", []),
            ("build", []),
            ("label", ["--source", "."]),
            ("preregister", []),
            ("train", []),
            ("score", ["--source", "."]),
            ("accept", []),
            ("ship", []),
        )
    }
    assert handlers["extract"] is cli.palette_extract
    assert handlers["label"] is cli.palette_label
    assert handlers["train"] is cli.palette_train_head
    assert len(set(handlers.values())) == len(handlers)


def test_the_two_things_that_were_arms_are_arms_on_the_command_line() -> None:
    """The hard/uniform mix and the listwise term are both decisions the records
    have to carry, so both are flags with the declared default already in them."""
    from fractal_wallpapers.models import palette_corpus

    parser = cli.build_parser()
    assert parser.parse_args(["palette", "plan"]).hard_share == palette_corpus.HARD_SHARE
    assert parser.parse_args(["palette", "plan", "--hard-share", "0"]).hard_share == 0.0
    assert parser.parse_args(["palette", "train"]).listwise is None
    assert parser.parse_args(["palette", "train", "--listwise", "1"]).listwise == 1.0


def test_the_teacher_is_never_assumed_to_be_here() -> None:
    """Every step that needs the source project names it on the command line."""
    parser = cli.build_parser()
    for step in ("extract", "label", "score"):
        with pytest.raises(SystemExit):
            parser.parse_args(["palette", step])


def test_weights_manifest_is_valid_and_versioned() -> None:
    manifest_path = cli.repo_root() / cli.WEIGHTS_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema"] == 1
    assert isinstance(manifest["heads"], dict)


def test_a_run_is_either_started_or_resumed_and_never_both() -> None:
    """Continuing a run is a decision, not a default: the name it is given says
    which of the two the caller meant."""
    parse = cli.build_parser().parse_args
    assert parse(["curate", "run", "--run", "v1"]).resume is None
    assert parse(["curate", "run", "--resume", "v1"]).run is None
    with pytest.raises(SystemExit):
        parse(["curate", "run"])
    with pytest.raises(SystemExit):
        parse(["curate", "run", "--run", "v1", "--resume", "v1"])


def test_a_run_s_shape_defaults_to_the_run_s_own_and_a_plan_s_to_a_number() -> None:
    """`curate run` cannot tell a flag that defaulted to 6 from one that asked for
    6, so it does not default at all — the run's own plan answers instead."""
    parse = cli.build_parser().parse_args
    running = parse(["curate", "run", "--run", "v1"])
    assert (running.n, running.seed, running.strange_share, running.wall_budget) == (
        None,
        None,
        None,
        None,
    )
    planning = parse(["curate", "plan"])
    assert (planning.n, planning.strange_share) == (6, 0.5)
    assert parse(["curate", "run", "--run", "v1", "--wall-budget", "900"]).wall_budget == 900.0
