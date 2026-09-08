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


def test_one_module_defines_each_name_and_no_module_is_named_like_one() -> None:
    """The two halves of what makes `cli.<handler>` resolve to ONE object.

    `__getattr__` scans the group modules in order and hands back the first
    match, so a name defined in two of them would resolve by scan order and a
    caller would never know which it got. And a submodule is set as an attribute
    of its package by the import system — an attribute `__getattr__` never sees —
    so a module named for a handler shadows that handler permanently. Eight
    commands are also handler names (`render`, `screen`, `walk`, `reframe`,
    `recolor`, `census`, `harvest`, `modes`), which is why the modules carry a
    `_commands` suffix rather than the bare group name.
    """
    import ast
    from pathlib import Path

    #: The one name every group is meant to define. `build_parser` reaches it on
    #: the module object it just imported, never through the package, so it is
    #: the single name a scan is never asked to disambiguate.
    shared = {"add_commands"}

    package = Path(cli.__file__).parent
    defined: dict[str, str] = {}
    clashes = []
    for module in sorted(package.glob("*.py")):
        if module.name in ("__init__.py", "__main__.py"):
            continue
        tree = ast.parse(module.read_text(encoding="utf-8"))
        for node in tree.body:
            names = []
            if isinstance(node, ast.FunctionDef | ast.ClassDef):
                names = [node.name]
            elif isinstance(node, ast.Assign):
                names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names = [node.target.id]
            for name in names:
                if name in shared:
                    continue
                if name in defined and defined[name] != module.stem:
                    clashes.append(f"{name}: {defined[name]} and {module.stem}")
                defined[name] = module.stem

    assert not clashes, (
        f"two modules define one name, so __getattr__ picks by scan order: {clashes}"
    )

    shadowed = sorted(m.stem for m in package.glob("*.py") if m.stem in defined)
    assert not shadowed, (
        f"these modules are named for a name the package must resolve, and would "
        f"shadow it for good: {shadowed}"
    )


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


def test_the_labeling_rig_is_eight_steps_under_one_subcommand() -> None:
    """Register, cut, list, serve, ingest, pin, show, split — the order they happen
    in, and every one of them a step somebody runs twice."""
    parse = cli.build_parser().parse_args
    assert (
        parse(["label", "register", "--batch", "b", "--method", "m"]).handler is cli.label_register
    )
    assert parse(["label", "build", "--from-batch", "b", "--batch", "b"]).handler is cli.label_build
    assert parse(["label", "sheets"]).handler is cli.label_sheets
    assert parse(["label", "serve", "--sheet", "d"]).handler is cli.label_serve
    assert parse(["label", "ingest", "--sheet", "s", "--labeler", "m"]).handler is cli.label_ingest
    pin = ["label", "pin", "--head", "spiral", "--from-plan", "p"]
    pin += ["--batch", "b", "--reserve", "1", "--seed", "0"]
    assert parse(pin).handler is cli.label_pin
    assert parse(["label", "split"]).handler is cli.label_split
    assert parse(["label", "show"]).handler is cli.label_show
    with pytest.raises(SystemExit):
        parse(["label"])


def test_a_pin_names_an_attribute_store_and_nothing_else() -> None:
    """The reservation is intra-batch, and only an attribute store has one. A
    finished store's evaluation side is a whole batch cut blind and `label
    register --eval-only` is how it is declared."""
    parse = cli.build_parser().parse_args
    with pytest.raises(SystemExit):
        parse(
            ["label", "pin", "--head", "smooth_render", "--from-plan", "p"]
            + ["--batch", "b", "--reserve", "1", "--seed", "0"]
        )
    assert not parse(
        [
            "label",
            "pin",
            "--head",
            "spiral",
            "--from-plan",
            "p",
            "--batch",
            "b",
            "--reserve",
            "1",
            "--seed",
            "0",
        ]
    ).write


def test_an_attribute_sheet_is_cut_for_a_store_that_is_not_a_judge() -> None:
    """`--head` names a STORE. Two of the four it accepts are judges' and two are
    not — an attribute is a fact about a place rather than an opinion about it,
    and a gallery grade is an opinion conditional on a judge having already
    spoken. The rig routes all of them by the same flag."""
    parse = cli.build_parser().parse_args
    cut = parse(["label", "build", "--from-plan", "p", "--head", "spiral", "--batch", "b"])
    assert cut.handler is cli.label_build and cut.head == "spiral"
    assert "spiral" in cli.NON_LOCATION_HEADS
    registered = parse(["label", "register", "--batch", "b", "--method", "m", "--head", "spiral"])
    assert registered.handler is cli.label_register and registered.head == "spiral"


def test_the_gallery_grade_store_is_one_of_the_heads_a_sheet_may_be_cut_for() -> None:
    """A `--head` `label ingest` cannot route to is a sheet that renders and lands nowhere.

    So the flag's choices and `intake.records_for`'s branches are one list, and
    this is the half of it argparse enforces.
    """
    from fractal_wallpapers.labeling import gallery_grade

    parse = cli.build_parser().parse_args
    assert gallery_grade.NAME in cli.NON_LOCATION_HEADS
    cut = parse(
        ["label", "build", "--from-plan", "p", "--head", gallery_grade.NAME, "--batch", "b"]
    )
    assert cut.handler is cli.label_build and cut.head == gallery_grade.NAME
    registered = parse(
        ["label", "register", "--batch", "b", "--method", "m", "--head", gallery_grade.NAME]
    )
    assert registered.handler is cli.label_register and registered.head == gallery_grade.NAME


def test_the_unaimed_draw_is_a_subcommand_that_names_its_seed() -> None:
    """A base-rate population that could not be drawn again is a population
    nobody can check."""
    parse = cli.build_parser().parse_args
    drawn = parse(["curate", "pool-draw", "--n", "500", "--seed", "3"])
    assert drawn.handler is cli.curate_pool_draw and drawn.n == 500 and drawn.seed == 3
    with pytest.raises(SystemExit):
        parse(["curate", "pool-draw", "--n", "500"])
    with pytest.raises(SystemExit):
        parse(["curate", "pool-draw", "--seed", "3"])


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
    """Through `roster`, which is the one derivation of this path since the
    layering fix — `cli.weights_commands` used to carry a second one of its own,
    because reaching `ship` for it would have put torch on the stdlib-only
    `fetch-weights --check` path."""
    from fractal_wallpapers.models import roster

    manifest = json.loads(roster.manifest_path().read_text(encoding="utf-8"))
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
    """`curate run` cannot tell a flag that defaulted to ten from one that asked
    for ten, so it does not default at all — the run's own plan answers instead."""
    from fractal_wallpapers.curation import run as run_module

    parse = cli.build_parser().parse_args
    running = parse(["curate", "run", "--run", "v1"])
    assert (running.n, running.seed, running.strange_share, running.wall_budget) == (
        None,
        None,
        None,
        None,
    )
    assert running.strange_modes is None
    planning = parse(["curate", "plan"])
    assert (planning.n, planning.strange_share) == (
        run_module.DEFAULT_N,
        run_module.STRANGE_SHARE,
    )
    assert parse(["curate", "run", "--run", "v1", "--wall-budget", "900"]).wall_budget == 900.0


def test_a_runs_release_is_a_diagnostic_ten_and_the_strange_share_is_six_tenths() -> None:
    """Matt's call of 2026-08-22, and both halves are decisions rather than
    tuning. Ten is enough pictures to see that the path works and is not a claim
    about what is worth shipping; six tenths tilts the mix towards the judge with
    a seventeen-mode roster and an acting bar to get past."""
    from fractal_wallpapers.curation import run as run_module

    assert run_module.DEFAULT_N == 10
    assert run_module.STRANGE_SHARE == 0.6
    # And the night's reservation names the same release, so a harvest that
    # reserves the leg and the run that spends it agree without being told.
    assert cli.build_parser().parse_args(["harvest"]).release_slots == run_module.DEFAULT_N


def test_a_harvest_names_its_minutes_or_derives_them_and_never_both() -> None:
    """`--finish-by` is a derivation of `--minutes`, so asking for both is asking
    the same question twice with two answers."""
    parse = cli.build_parser().parse_args
    assert parse(["harvest"]).minutes is None
    assert parse(["harvest"]).finish_by is None
    assert parse(["harvest", "--minutes", "90"]).minutes == 90.0
    assert parse(["harvest", "--finish-by", "07:00"]).finish_by == "07:00"
    with pytest.raises(SystemExit):
        parse(["harvest", "--minutes", "90", "--finish-by", "07:00"])


@pytest.mark.slow
def test_a_derived_plan_reserves_the_release_the_run_will_actually_ask_for() -> None:
    """`--release-slots` had no default while a release was a number somebody
    chose per night. A run keeps a diagnostic ten now, so the reservation's
    default is that ten — and the colorize term beside it is derived from the
    night's own shape through `curation.budget` rather than from a constant.

    **The finish time is three hours from now and not a literal.** It used to be
    `07:00`, which made this a test that failed for anybody who ran the lane in
    the half hour before seven in the morning: `harvest_minutes` refuses a plan
    whose remaining clock cannot cover its own reservation — 29 minutes on this
    machine — and it refused at 06:53 on 2026-09-06. Nothing here is about a
    particular hour; what it needs is a finish time far enough out that the
    reservation fits, and three hours is that at every hour of the day.
    """
    import datetime

    from fractal_wallpapers.curation import run as run_module

    finish = (datetime.datetime.now() + datetime.timedelta(hours=3)).strftime("%H:%M")
    parse = cli.build_parser().parse_args
    minutes, plan = cli.harvest_minutes(parse(["harvest", "--finish-by", finish]))
    assert plan.release_slots == run_module.DEFAULT_N
    assert plan.attempts == cli.curation_attempts(parse(["harvest"]))

    # A night that will draw a third strange mode reserves the colorize leg for
    # one, which no copy of the mode table in `schedule` could have done.
    _, wider = cli.harvest_minutes(
        parse(["harvest", "--finish-by", finish, "--strange-modes", "3"])
    )
    assert wider.attempts > plan.attempts
    assert wider.curation > plan.curation

    minutes, plan = cli.harvest_minutes(parse(["harvest"]))
    assert (minutes, plan) == (cli.DEFAULT_HARVEST_MINUTES, None)

    minutes, plan = cli.harvest_minutes(parse(["harvest", "--minutes", "0"]))
    assert (minutes, plan) == (0.0, None)

    minutes, plan = cli.harvest_minutes(
        parse(["harvest", "--finish-by", finish, "--release-slots", "80"])
    )
    assert plan is not None
    assert minutes == plan.active_minutes
    assert plan.record()["release_slots"] == 80


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


def test_both_gallery_changes_are_the_default_and_the_incumbent_is_still_reachable() -> None:
    """Flipped on 2026-08-28. `curate solve run` with no flag now chooses under the
    proportional palette-group cap and a fitted key. A third default joined
    them on 2026-09-04 — the spiral share cap — so the incumbent invocation carries
    a third flag: it solved with NO cap, and saying nothing no longer means that.

    The key half moved again on 2026-09-07, when the cascade was adopted. It is
    still one flag away from the pre-flip order, which is why `--key` carries
    three names rather than two: `p_ge4` is the incumbent this test spells and
    `rank-key` is the order everything between the two flips ran.
    """
    from fractal_wallpapers.curation import ceiling, solve

    parse = cli.build_parser().parse_args
    unflagged = parse(["curate", "solve", "run", "--n", "150"])
    assert unflagged.handler is cli.curate_solve
    assert unflagged.group_cap == solve.DEFAULT_GROUP_CAP == ceiling.PROPORTIONAL
    assert unflagged.key == solve.DEFAULT_KEY == solve.CASCADE_KEY
    assert parse(["curate", "solve", "run", "--n", "150", "--key", "rank-key"]).key == "rank-key"
    assert unflagged.spiral_cap == solve.DEFAULT_SPIRAL_CAP == 0.10
    incumbent = parse(
        [
            "curate",
            "solve",
            "run",
            "--n",
            "150",
            "--group-cap",
            "identity",
            "--key",
            "p_ge4",
            "--spiral-cap",
            "none",
        ]
    )
    assert (incumbent.group_cap, incumbent.key) == (ceiling.IDENTITY, solve.JUDGE_KEY)
    assert incumbent.spiral_cap is None, "the incumbent gallery solved uncapped"
    with pytest.raises(SystemExit):
        parse(["curate", "solve", "run", "--group-cap", "whatever_matt_meant"])
    with pytest.raises(SystemExit):
        parse(["curate", "solve", "run", "--key", "whatever_matt_meant"])


def test_the_fine_bar_is_a_flag_a_record_keeps_and_it_moves_no_default() -> None:
    """The quality bar is a PARAMETER, and both verbs read it.

    A bar that only `run` accepted would be a bar no tracked manifest could ever
    carry, and the manifest is where a record says what made it. Unsaid it is
    `None` on both, which is the default this leg deliberately did not move:
    Matt has adopted `p_fine(>=4) >= 0.50` at n=1000 and ruled that the flip
    happens in the same act that makes the first cascade record.
    """
    from fractal_wallpapers.curation import solve

    parse = cli.build_parser().parse_args
    assert solve.DEFAULT_FINE_BAR is None
    assert parse(["curate", "solve", "run", "--n", "150"]).fine_bar is None
    assert parse(["curate", "solve", "record"]).fine_bar is None
    assert parse(["curate", "solve", "run", "--fine-bar", "0.50"]).fine_bar == 0.50
    assert parse(["curate", "solve", "record", "--fine-bar", "0.50"]).fine_bar == 0.50


def test_the_spiral_cap_keeps_no_cap_a_zero_cap_and_a_slack_cap_apart() -> None:
    """Three answers and not two. `none` is no cap at all; `0` is a cap whose
    allowance is zero, so no spiral may be seated; `1.0` is a cap that runs and
    does not bind, which is what a record that should say it ran one is spelled
    with. A float flag with a sentinel could not hold the three apart, which is
    why `--spiral-cap` takes a converter."""
    from fractal_wallpapers.curation import solve

    parse = cli.build_parser().parse_args

    def cap(*named):
        return parse(["curate", "solve", "run", "--n", "150", *named]).spiral_cap

    assert cap() == solve.DEFAULT_SPIRAL_CAP
    assert cap("--spiral-cap", "none") is None
    assert cap("--spiral-cap", "off") is None
    assert cap("--spiral-cap", "NONE") is None, "a reader will type it either way"
    assert cap("--spiral-cap", "0") == 0.0, "a zero cap is not the same as no cap"
    assert cap("--spiral-cap", "1.0") == 1.0
    assert cap("--spiral-cap", "0.25") == 0.25
    # `record` reads the same flag off the same container, so it cannot drift.
    assert parse(["curate", "solve", "record", "--n", "1000"]).spiral_cap == (
        solve.DEFAULT_SPIRAL_CAP
    )
    with pytest.raises(SystemExit):
        parse(["curate", "solve", "run", "--spiral-cap", "banana"])
    with pytest.raises(SystemExit):
        parse(["curate", "solve", "run", "--spiral-cap", "-1"])


def test_the_release_leg_is_on_by_default_and_carries_the_shipping_regime() -> None:
    """The gallery leg renders its seats unless told not to, and it renders them at
    the one geometry every leg that ships a wallpaper ships."""
    from fractal_wallpapers.curation import release

    parse = cli.build_parser().parse_args
    quiet = parse(["curate", "solve", "run", "--n", "150", "--no-render"])
    assert quiet.no_render is True
    asked = parse(["curate", "solve", "run", "--n", "150"])
    assert asked.no_render is False
    assert asked.release_regime == release.RELEASE_REGIME.spelled


def test_the_retired_experiments_went_with_the_solver_they_experimented_on() -> None:
    """`sweep` and `truncate` were both instruments on the exact solve. A subcommand
    that answers about a program nothing runs is worse than no subcommand."""
    parse = cli.build_parser().parse_args
    assert parse(["curate", "solve", "run"]).what == "run"
    with pytest.raises(SystemExit):
        parse(["curate", "solve", "sweep"])
    with pytest.raises(SystemExit):
        parse(["curate", "solve", "truncate"])
    with pytest.raises(SystemExit):
        parse(["curate", "seat", "--n", "150"])


def test_the_flatness_sweep_and_the_rank_key_fit_are_subcommands_with_defaults() -> None:
    """There is no `scripts/`, so the sidecar and the fitted artifact are both
    rebuilt by a named verb and the default verb is the one that does the work."""
    from fractal_wallpapers.curation import flatness

    parse = cli.build_parser().parse_args
    swept = parse(["curate", "flatness"])
    assert swept.handler is cli.curate_flatness
    assert (swept.what, swept.workers, swept.all) == ("sweep", flatness.WORKERS, False)
    assert parse(["curate", "flatness", "check"]).what == "check"
    fitted = parse(["curate", "rank-key"])
    assert fitted.handler is cli.curate_rank_key
    assert fitted.what == "fit"
    assert parse(["curate", "rank-key", "show"]).what == "show"


def test_no_handler_materialises_the_ledger_for_a_cost_table_it_discards() -> None:
    """`headroom.population` IS `solve.pool` plus a per-mode render cost read off
    every ledger row, so a handler that wants only the candidates and reaches it
    anyway buys one whole-ledger copy — 5.1 s and 177,993 rows — for a table it
    throws away. Five sites did; `curate headroom` is the one that reads the table.
    Source-level because the alternative is a fixture that loads the real pool.

    Over the whole package rather than one module: `cli` is a directory now, and
    `inspect.getsource` on a package reads `__init__.py` alone — which holds no
    handler at all, so the guard would pass by having nothing left to look at."""
    import re
    from pathlib import Path

    package = Path(cli.__file__).parent
    source = "\n".join(m.read_text(encoding="utf-8") for m in sorted(package.glob("*.py")))
    binds = re.findall(r"^\s*(.*)=\s*headroom\.population\(", source, re.MULTILINE)
    assert binds, "the census handler still reaches it; this guard has lost its subject"
    for bound in binds:
        # The middle of the three is the cost table. A throwaway name there is a
        # handler paying for the whole ledger to read nothing off it.
        names = [name.strip() for name in bound.split(",")]
        assert len(names) == 3, f"{bound.strip()!r} is not the three-tuple this returns"
        assert not names[1].startswith("_"), (
            f"{bound.strip()!r} discards the cost table: take `solve.pool()` instead"
        )


def test_every_subcommands_help_renders() -> None:
    """`--help` on any verb, at any depth. It is not a formality: argparse
    `%`-expands a help string as it prints it, so one unescaped `%` in one
    option's text raises `ValueError` and takes down that whole parser's help
    and nothing else — no import fails, no other command notices, and the only
    symptom is a verb whose `--help` crashes. `curate coverage --help` was in
    that state for as long as `--by-swatch` has named a threshold in percent.
    """
    import argparse

    def walk(parser, path):
        try:
            parser.format_help()
        except Exception as failure:  # noqa: BLE001 — the point is which verb, not the type
            raise AssertionError(f"`{path} --help` does not render: {failure!r}") from failure
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                for name, child in action.choices.items():
                    walk(child, f"{path} {name}")

    walk(cli.build_parser(), "fractal-wallpapers")


def test_every_leg_that_drives_the_engine_defaults_to_the_locked_three() -> None:
    """The render pool is three workers. Two `--workers` defaults sat at 6 —
    `curate coverage --step probe`, whose every probe is a recolor through the
    engine, and `curate manufacture`, which builds a group by rendering — and
    both are the locked number now, read off the module that owns it rather
    than restated."""
    from fractal_wallpapers.curation import flatness, release

    parse = cli.build_parser().parse_args
    assert release.DEFAULT_WORKERS == 3
    assert parse(["curate", "coverage"]).workers == release.DEFAULT_WORKERS
    assert parse(["curate", "manufacture"]).workers == release.DEFAULT_WORKERS
    assert parse(["curate", "solve", "run"]).workers == release.DEFAULT_WORKERS
    assert parse(["curate", "flatness"]).workers == flatness.WORKERS == 3


#: Flags on one command past which its `--help` stops being a list and starts
#: being a wall. Not a measured constant — it is where the line was drawn when
#: the five commands over it were grouped, and it is here so the sixth trips
#: this test rather than shipping flat.
WALL = 20


def commands_and_their_flags():
    """Every command in the tree, with its optionals and its named groups."""
    import argparse

    def walk(parser, path):
        flags = [
            action
            for action in parser._actions
            if not isinstance(action, argparse._SubParsersAction | argparse._HelpAction)
            and action.option_strings
        ]
        named = [
            group
            for group in parser._action_groups
            if group is not parser._optionals and group is not parser._positionals
        ]
        yield path, parser, flags, named
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                for name, child in action.choices.items():
                    yield from walk(child, f"{path} {name}")

    return list(walk(cli.build_parser(), "fractal-wallpapers"))


def test_a_command_past_the_wall_groups_its_help() -> None:
    """Twenty flags in one undivided block is a reference nobody reads.

    Five commands were over the line when this was written — `harvest` at 45,
    `curate solve` at 30, `curate depth` at 26, `walk` at 24, `render` at 20 —
    and the point of the test is the sixth: a flag added to a flat command that
    tips it over prints a wall unless somebody names the seams, and nothing but
    this would say so.
    """
    flat = [
        (path, len(flags))
        for path, _, flags, named in commands_and_their_flags()
        if len(flags) >= WALL and not named
    ]
    assert not flat, (
        f"over {WALL} flags and no argument groups: {flat}. Read the flags, find the "
        f"seams the code already has, and `add_argument_group` them"
    )


def test_a_grouped_command_leaves_no_flag_behind() -> None:
    """Argparse prints an ungrouped optional in the default `options:` block —
    above every named group and beside `-h` — so one flag that missed a group on
    a command whose others all found one does not read as ungrouped. It reads as
    belonging with `--help`, which is worse than the flat list the grouping was
    for."""
    stray = {
        path: sorted(
            action.option_strings[0]
            for action in parser._optionals._group_actions
            if action.option_strings and action.option_strings[0] != "-h"
        )
        for path, parser, _, named in commands_and_their_flags()
        if named
    }
    stray = {path: flags for path, flags in stray.items() if flags}
    assert not stray, f"grouped commands with flags outside every group: {stray}"
