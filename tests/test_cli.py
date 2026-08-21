"""The command line is the project's only entry point, so it is smoke-tested here."""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers import cli
from fractal_wallpapers.discovery import boundary


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


def test_the_supply_engine_is_five_subcommands_and_no_scripts() -> None:
    """The production loop, the census it runs on, and the three derivations that
    regenerate what it reads. Every one of them is a step somebody will run twice,
    so every one of them has a name and `--help` text."""
    parse = cli.build_parser().parse_args
    assert parse(["harvest"]).handler is cli.harvest
    assert parse(["census"]).handler is cli.census
    assert parse(["derive-prices", "--run", "x"]).handler is cli.derive_prices
    assert parse(["derive-tau-h"]).handler is cli.derive_tau_h
    assert parse(["derive-proven-seeds"]).handler is cli.derive_proven_seeds


def test_a_run_can_be_told_to_keep_one_partition_s_books_alone() -> None:
    """A leg aimed at one partition has to be able to say so. Steering toward it
    through the mix is not the same statement: the census, the allocation and the
    refill census all read the partition list, so naming one spends the whole
    clock there instead of whatever share the standing deficit implies."""
    parse = cli.build_parser().parse_args
    assert parse(["harvest"]).partition is None
    assert parse(["harvest", "--partition", "mandelbrot"]).partition == ["mandelbrot"]
    assert parse(["harvest", "--partition", "mandelbrot", "--partition", "phoenix"]).partition == [
        "mandelbrot",
        "phoenix",
    ]
    with pytest.raises(SystemExit):
        parse(["harvest", "--partition", "not-a-partition"])


def test_the_reframing_channel_is_reachable_from_the_production_loop() -> None:
    """`walk` could turn the probe up and the neighbourhood operator on and
    `harvest` could not, so the one command that runs for hours was the one that
    could not reach the channel. Both, or the flag on `walk` is a demo."""
    parse = cli.build_parser().parse_args
    assert parse(["harvest"]).probe is None
    assert parse(["harvest", "--probe", "1.0"]).probe == 1.0
    assert parse(["harvest", "--neighborhood"]).neighborhood is True
    assert parse(["walk", "--neighborhood"]).neighborhood is True


def test_an_unpassed_operator_flag_says_nothing_rather_than_no() -> None:
    """The shipped default is on [`Reframings`], and `store_true` would have
    every run silently overrule it with a `False` nobody typed. Both commands
    default to `None` and carry an explicit opt-out instead."""
    from fractal_wallpapers.discovery.walk import Reframings

    parse = cli.build_parser().parse_args
    for command in ("harvest", "walk"):
        assert parse([command]).neighborhood is None
        assert parse([command, "--no-neighborhood"]).neighborhood is False
        assert cli.reframings_from(parse([command])).neighborhood is Reframings().neighborhood
        assert cli.reframings_from(parse([command, "--no-neighborhood"])).neighborhood is False
        assert cli.reframings_from(parse([command, "--neighborhood"])).neighborhood is True


def test_a_derivation_does_not_overwrite_a_shipped_table_unasked() -> None:
    """A table is the record of a decision. Replacing one is a deliberate act, so
    the default is to print what would be written."""
    for arguments in (["derive-prices", "--run", "x"], ["derive-tau-h"], ["derive-proven-seeds"]):
        assert cli.build_parser().parse_args(arguments).write is False


def test_the_machine_stock_discount_is_a_flag_on_both_readers() -> None:
    """`--discount 0` has to reproduce the labels-only deficit exactly, which is
    only useful if the same switch is on the census and on the run."""
    parse = cli.build_parser().parse_args
    assert parse(["census", "--discount", "0"]).discount == 0.0
    assert parse(["harvest", "--discount", "0"]).discount == 0.0


def test_a_tile_build_names_the_regime_it_is_aimed_at() -> None:
    """The default is the canonical regime and it is the one that elides, so a
    build that says nothing writes the names the shipped corpus already has."""
    from fractal_wallpapers.models import tiles as tile_module

    parse = cli.build_parser().parse_args
    args = parse(["tiles", "build"])
    assert args.handler is cli.tiles_build
    assert cli.tile_regime(args) == tile_module.CANONICAL_REGIME
    assert cli.tile_regime(args).tag == ""

    ss1 = cli.tile_regime(parse(["tiles", "build", "--tile", "384x216", "--supersample", "1"]))
    assert ss1 == tile_module.Regime(tile=(384, 216), supersample=1)
    assert ss1.tag == "_384x216ss1"

    with pytest.raises(SystemExit):
        cli.tile_regime(parse(["tiles", "build", "--tile", "384"]))


def test_the_labeling_rig_is_seven_steps_under_one_subcommand() -> None:
    """Register, cut, list, serve, ingest, show, split — the order they happen in,
    and every one of them a step somebody runs twice."""
    parse = cli.build_parser().parse_args
    assert (
        parse(["label", "register", "--batch", "b", "--method", "m"]).handler is cli.label_register
    )
    assert parse(["label", "build", "--from-batch", "b", "--batch", "b"]).handler is cli.label_build
    assert parse(["label", "sheets"]).handler is cli.label_sheets
    assert parse(["label", "serve", "--sheet", "d"]).handler is cli.label_serve
    assert parse(["label", "ingest", "--sheet", "s", "--labeler", "m"]).handler is cli.label_ingest
    assert parse(["label", "split"]).handler is cli.label_split
    assert parse(["label", "show"]).handler is cli.label_show
    with pytest.raises(SystemExit):
        parse(["label"])


def test_there_is_one_path_into_the_stores_and_not_one_each() -> None:
    """`record` and `ingest` did the same thing against two stores, and only one
    of them ever grew the count checks. There is no `record`."""
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["label", "record", "--sheet", "d", "--labeler", "m"])
    assert not hasattr(cli, "label_record")


def test_a_finished_render_sheet_is_cut_from_a_plan_and_names_its_judge() -> None:
    """The population is a decision the generator does not make. What it needs to
    be told is which judge the page prefills from, and that decides the store."""
    parse = cli.build_parser().parse_args
    cut = parse(["label", "build", "--from-plan", "p", "--head", "strange_render", "--batch", "b"])
    assert cut.handler is cli.label_build and cut.head == "strange_render"
    assert parse(["label", "build", "--from-batch", "b", "--batch", "b"]).head is None
    with pytest.raises(SystemExit):
        parse(["label", "build", "--from-plan", "p", "--head", "no_such_head", "--batch", "b"])
    with pytest.raises(SystemExit):
        parse(["label", "build", "--from-plan", "p", "--from-batch", "b", "--batch", "b"])


def test_an_export_defaults_to_the_sheet_s_own_drop() -> None:
    """Matt's convention, and now the rig's: a page saves to
    labels/<head>.<sheet>.json, so the step has to be told nothing about where
    the file it just wrote is."""
    parse = cli.build_parser().parse_args
    assert parse(["label", "ingest", "--sheet", "s", "--labeler", "m"]).labels is None


def test_an_ingest_does_not_append_to_a_shipped_store_unasked() -> None:
    """The store is the corpus. Appending to it is a deliberate act, so the
    default prints what would be written and touches nothing."""
    assert (
        cli.build_parser().parse_args(["label", "ingest", "--sheet", "s", "--labeler", "m"]).write
        is False
    )


def test_a_finished_render_batch_is_registered_by_the_same_step() -> None:
    """Registration before rows is enforced by both writers, so both stores need
    a way to register that is not a one-off script."""
    parse = cli.build_parser().parse_args
    assert parse(["label", "register", "--batch", "b", "--method", "m"]).head is None
    assert (
        parse(
            ["label", "register", "--batch", "b", "--method", "m", "--head", "strange_render"]
        ).head
        == "strange_render"
    )
    with pytest.raises(SystemExit):
        parse(["label", "register", "--batch", "b", "--method", "m", "--head", "no_such_head"])


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
    assert args.eval_only is False, "a pin is bought on purpose, never by default"


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


def test_finding_a_sheet_to_serve_is_a_command() -> None:
    """A sheet's directory name is whoever-cut-it's choice and need not be the
    batch inside it, so the mapping lived only in each manifest and finding a
    sheet meant opening candidates by hand."""
    parse = cli.build_parser().parse_args
    listing = parse(["label", "sheets"])
    assert listing.handler is cli.label_sheets
    assert listing.under == "artifacts", "the ignored tree everything is built into"
    assert listing.drops is False
    assert parse(["label", "sheets", "--drops"]).drops is True


def test_a_sheet_says_its_judge_its_batch_and_its_size() -> None:
    """One phrasing, used by the listing and by the server's banner, so a sheet
    is not described two different ways by two commands."""
    said = cli.sheet_identity({"head": "location", "batch": "twin_top_slices"}, 96)
    assert "location" in said and "twin_top_slices" in said and "96 units" in said
    assert "(no batch)" in cli.sheet_identity({"head": "location"}, 3), "a batch is not required"


def test_a_location_record_is_renderable_without_retyping_its_constants() -> None:
    """Every ledger row, label row and release record is a {family, viewport,
    render} object, and `render` could take none of it: every constant was a
    flag. That is why the one caller outside this repository that had to redraw a
    row bypassed the engine seam and shelled the binary."""
    parse = cli.build_parser().parse_args
    assert parse(["render"]).location is None
    assert parse(["render", "--location", "row.json"]).location == "row.json"
    assert parse(["render", "--manifest", "rows.jsonl"]).manifest == "rows.jsonl"
    assert parse(["render", "--manifest", "rows.jsonl"]).handler is cli.render


def test_a_record_and_a_flag_cannot_both_describe_one_render() -> None:
    """A record already says everything the flags say, so a command given both
    has been told two different things about one picture. Neither is chosen —
    quietly ignoring a typed --width produces a picture nobody can tell from the
    one they asked for."""
    parse = cli.build_parser().parse_args
    assert cli.refuse_two_descriptions(parse(["render"])) is None
    assert cli.refuse_two_descriptions(parse(["render", "--location", "row.json"])) is None
    assert cli.refuse_two_descriptions(parse(["render", "--width", "0.5"])) is None

    complaint = cli.refuse_two_descriptions(
        parse(["render", "--location", "r.json", "--width", "1"])
    )
    assert "--width" in (complaint or "")
    complaint = cli.refuse_two_descriptions(
        parse(["render", "--manifest", "r.jsonl", "--supersample", "4"])
    )
    assert "--supersample" in (complaint or "")
    both = cli.refuse_two_descriptions(parse(["render", "--location", "a", "--manifest", "b"]))
    assert "one of them" in (both or "")


def test_the_flag_defaults_a_render_compares_against_are_the_ones_argparse_holds() -> None:
    """The comparison is against a dict carried on the namespace, because argparse
    fills a default in and does not remember that it did. This is what keeps that
    dict from being a second, drifting copy of the parser's own defaults."""
    args = cli.build_parser().parse_args(["render"])
    for flag, default in args.flag_defaults.items():
        assert getattr(args, flag) == default, flag
    assert "width" in args.flag_defaults and "colormap" in args.flag_defaults
    assert "location" not in args.flag_defaults, "not one of the flags that spells a location out"


def test_the_structural_gates_are_reachable_without_proposing_anything() -> None:
    """They lived only inside `expand`, which proposes children rather than
    judging a frame you name — so the one filter the article spends a figure on
    could not be pointed at a picture."""
    parse = cli.build_parser().parse_args
    assert parse(["screen", "--location", "row.json"]).handler is cli.screen
    assert parse(["screen", "--manifest", "rows.jsonl"]).manifest == "rows.jsonl"
    assert parse(["screen", "--location", "row.json"]).node_width == 384
    with pytest.raises(SystemExit):
        parse(["screen"])
    with pytest.raises(SystemExit):
        parse(["screen", "--location", "a", "--manifest", "b"])


def test_the_boundary_draw_is_a_named_seeded_subcommand() -> None:
    """The prose claims more than a hundred such draws and nothing here could
    make one: the flat-draw label batch is the *record* of a draw made in another
    project, not a generator. A record of a draw cannot be re-run."""
    parse = cli.build_parser().parse_args
    args = parse(["sample-boundary"])
    assert args.handler is cli.sample_boundary
    assert args.seed == 0, "seeded, and the seed is recorded"
    assert args.family == "mandelbrot"
    assert (args.width_low, args.width_high) == (boundary.WIDTH_LOW, boundary.WIDTH_HIGH)
    assert parse(["sample-boundary", "--seed", "7"]).seed == 7


def test_a_list_of_locations_can_be_scored_without_a_ledger() -> None:
    """`curate score` reads a ledger and `score-parity` reads a ledger; nothing
    read a list. Any panel that wants to print P(>=3) under a picture needs one."""
    parse = cli.build_parser().parse_args
    args = parse(["score-locations", "--manifest", "rows.jsonl"])
    assert args.handler is cli.score_locations
    assert args.regime == "640x360ss2", "the deploy view"
    with pytest.raises(SystemExit):
        parse(["score-locations"])


def test_the_focus_report_is_off_on_both_commands_that_walk() -> None:
    """Production output is what it always was unless somebody asks. And it has to
    be on both: a flag on `walk` that `harvest` cannot reach is a demo."""
    parse = cli.build_parser().parse_args
    assert parse(["walk"]).foci is False
    assert parse(["harvest"]).foci is False
    assert parse(["walk", "--foci"]).foci is True
    assert parse(["harvest", "--foci"]).foci is True
