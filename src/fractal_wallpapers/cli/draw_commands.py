"""`render`, `screen`, `sample-boundary`, `dump-field`, `recolor`: one picture at a time."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fractal_wallpapers import engine
from fractal_wallpapers.cli.common import (
    DEFAULT_MODE,
    boundary_default,
    location_arguments,
    resolve_output,
)
from fractal_wallpapers.paths import (
    colormap_dir,
    tracked_name,
)


def render_spec(args: argparse.Namespace) -> dict:
    """Turn command-line arguments into the JSON object the engine reads.

    Coordinates and family constants stay **strings** the whole way through. A
    location's identity is what was written, not the `f64` it rounds to, and
    parsing it here to hand the engine a float would throw that away at the one
    point in the pipeline that still has it.

    `render` and `dump-field` build the same spec: a dump is a render stopped
    one stage early, and the colormap it names is the one its record hands back
    to a recolor that does not choose for itself.

    A spec says either `mode` or `coloring`, never both — a mode *is* a coloring
    with a name. `--discrete` is the one thing here that takes the second door:
    the integer escape count is not a named mode and deliberately never will be,
    so asking for it means writing the coloring out.
    """
    family: dict[str, object] = {"kind": args.family}
    if args.family == "multibrot":
        family["degree"] = args.degree
    if args.family == "julia":
        family["degree"] = args.degree
        family["c"] = args.c
    if args.family == "phoenix":
        for key, value in (("c", args.c), ("p", args.p), ("z_prev", args.z_prev)):
            if value is not None:
                family[key] = value

    viewport = {
        key: value
        for key, value in (
            ("center_re", args.center_re),
            ("center_im", args.center_im),
            ("width", args.width),
        )
        if value is not None
    }

    spec: dict[str, object] = {
        "schema": 1,
        "family": family,
        "resolution": args.resolution,
        "supersample": args.supersample,
        **discrete_or_mode(args),
        "colormap": args.colormap,
        "colormap_dir": str(colormap_dir()),
        "output": str(resolve_output(args.out)),
    }
    if viewport:
        spec["viewport"] = viewport
    if args.maxiter is not None:
        spec["maxiter"] = args.maxiter
    return spec


def discrete_or_mode(args: argparse.Namespace) -> dict:
    """The half of a spec that says how to color: `{"mode": ...}` or a coloring."""
    if getattr(args, "discrete", None) is None:
        return {"mode": args.mode or DEFAULT_MODE}
    field: dict[str, object] = {"kind": "discrete"}
    if args.discrete > 0:
        field["cycle"] = args.discrete
    return {"coloring": {"kind": "field", "field": field}}


def refuse_impossible_location(args: argparse.Namespace) -> str | None:
    """Say why this location cannot be rendered, or `None` if it can."""
    if args.family == "julia" and args.c is None:
        return "--c is required for a julia render: it is half of the location's identity"
    if args.family not in ("julia", "multibrot") and args.degree != 2:
        return f"--degree does not apply to a {args.family} render"
    if args.discrete is not None:
        if args.mode is not None:
            return (
                "--mode and --discrete both say how to color the render, and a mode is a "
                "coloring with a name: give one or the other"
            )
        if args.discrete < 0:
            return "--discrete takes a positive band length, or no value at all for no bands"
    return None


def refuse_two_descriptions(args: argparse.Namespace) -> str | None:
    """Say why a record and a flag both describe this render, or `None`.

    A location record already says every one of the things the flags say, so a
    command handed one *and* a flag has been told two different things about one
    picture. Which one to believe is not a question with a defensible answer, so
    neither is chosen.

    What was typed is recovered by comparing against what argparse would have
    filled in, because argparse itself does not remember the difference — see
    [`location_arguments`], which stashes the defaults it set.
    """
    if not (args.location or args.manifest):
        return None
    typed = sorted(
        flag for flag, default in args.flag_defaults.items() if getattr(args, flag) != default
    )
    if typed:
        given = "--location" if args.location else "--manifest"
        return (
            f"{given} and {', '.join('--' + flag.replace('_', '-') for flag in typed)} both say "
            f"what to render. A record already carries all of it — drop the flags, or edit "
            f"the record."
        )
    if args.location and args.manifest:
        return "--location names one location and --manifest names many: give one of them"
    return None


def render(args: argparse.Namespace) -> int:
    """Render one image and print the engine's report."""
    from fractal_wallpapers import locations

    complaint = refuse_two_descriptions(args)
    if complaint is not None:
        print(complaint)
        return 1
    if args.manifest:
        return render_manifest(args)
    if args.location:
        try:
            row = locations.read_one(resolve_output(args.location))
        except locations.LocationError as refusal:
            print(refusal)
            return 1
        spec = locations.spec_of(row, resolve_output(args.out))
        print(json.dumps(engine.render_report(spec), indent=2))
        return 0

    complaint = refuse_impossible_location(args)
    if complaint is not None:
        print(complaint)
        return 1

    print(json.dumps(engine.render_report(render_spec(args)), indent=2))
    return 0


def dump_field(args: argparse.Namespace) -> int:
    """Write the raw field a render would have colored, plus its record."""
    complaint = refuse_impossible_location(args)
    if complaint is not None:
        print(complaint)
        return 1

    print(json.dumps(engine.dump_field(render_spec(args)), indent=2))
    return 0


def dumped_colormap(field: Path) -> str | None:
    """The map a dumped field was drawn alongside, read off its own record.

    `None` where the record cannot be read: a recolor that could not find out
    which map it is about must not guess a fold for it.
    """
    record = Path(field).with_suffix(".json")
    if not record.is_file():
        return None
    try:
        return json.loads(record.read_text(encoding="utf-8")).get("colormap")
    except (OSError, ValueError):
        return None


def recolor(args: argparse.Namespace) -> int:
    """Color a dumped field through another colormap, without re-iterating.

    **The fold is decided here, not left off.** A recolor that sent no palette
    block got the engine's default — an unfolded bake — so a sequential map came
    out through its seam, which is not the picture any other caller in this
    project makes of it. The default is the pipeline's own rule, `mirror = the
    map is not cyclic`, owned by `palette_sets.recipe_for`; `--no-mirror` asks
    for the unfolded ramp, which is a real picture too — it is what a fold-free
    render like the tile floor's second reservation shows.
    """
    field = resolve_output(args.field)
    spec: dict[str, object] = {
        "schema": 1,
        "field": str(field),
        "colormap_dir": str(colormap_dir()),
        "output": str(resolve_output(args.out)),
    }
    if args.colormap is not None:
        spec["colormap"] = args.colormap
    if args.transform is not None:
        spec["transform"] = args.transform

    from fractal_wallpapers.labeling import finished
    from fractal_wallpapers.palettes import strip

    name = args.colormap or dumped_colormap(field)
    if name is not None:
        spec["palette"] = finished.recipe(mirror=strip.mirror_for(name, args.mirror))
    elif args.mirror is not None:
        spec["palette"] = finished.recipe(mirror=bool(args.mirror))
    print(json.dumps(engine.recolor(spec), indent=2))
    return 0


def render_manifest(args: argparse.Namespace) -> int:
    """Render every location in a manifest, and record what was drawn."""
    from fractal_wallpapers import locations

    rows = locations.read(resolve_output(args.manifest))
    if args.limit is not None:
        rows = rows[: max(0, args.limit)]
    directory = resolve_output(args.out_dir)
    directory.mkdir(parents=True, exist_ok=True)

    record = directory / "renders.jsonl"
    made, reused = 0, 0
    with record.open("w", encoding="utf-8", newline="\n") as handle:
        for index, row in enumerate(rows):
            output = directory / f"{index:05d}_{locations.name_of(row)}.png"
            if args.resume and output.is_file():
                reused += 1
                report = None
            else:
                report = engine.render_report(locations.spec_of(row, output))
                made += 1
            handle.write(
                json.dumps(
                    {
                        "schema": locations.SCHEMA,
                        "index": index,
                        **row,
                        "output": tracked_name(output),
                        "report": report,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            print(f"[render] {index + 1}/{len(rows)} {output.name}")
    print(
        json.dumps(
            {
                "locations": len(rows),
                "rendered": made,
                "already_there": reused,
                "out_dir": str(directory),
                "record": str(record),
            },
            indent=2,
        )
    )
    return 0


def screen(args: argparse.Namespace) -> int:
    """Run the structural gates over locations somebody named, and say what each said."""
    from fractal_wallpapers import locations

    try:
        rows = (
            locations.read(resolve_output(args.manifest))
            if args.manifest
            else [locations.read_one(resolve_output(args.location))]
        )
    except locations.LocationError as refusal:
        print(refusal)
        return 1
    if args.limit is not None:
        rows = rows[: max(0, args.limit)]

    directory = resolve_output(args.out_dir) if args.out_dir else None
    if directory is not None:
        directory.mkdir(parents=True, exist_ok=True)
    spec: dict = {
        "schema": 1,
        "frames": [locations.frame_of(row) for row in rows],
        "colormap": args.colormap,
        "colormap_dir": str(engine.colormap_dir()),
        "node_width": args.node_width,
        "occupancy": not args.waive_occupancy,
    }
    if directory is not None:
        spec["out_dir"] = str(directory)
    report = engine.screen(spec)

    # One frame prints its verdicts; a batch prints the tally and writes the
    # rows, because a hundred screenings scrolling past is not a report.
    if args.manifest is None:
        print(json.dumps({**report, "frames": report["frames"]}, indent=2))
        return 0 if report["frames"][0]["passed"] else 1

    out = resolve_output(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fates: dict[str, int] = {}
    with out.open("w", encoding="utf-8", newline="\n") as handle:
        for row, screened in zip(rows, report["frames"], strict=True):
            fates[screened["fate"]] = fates.get(screened["fate"], 0) + 1
            handle.write(
                json.dumps({"schema": locations.SCHEMA, **row, **screened}, ensure_ascii=False)
                + "\n"
            )
    passed = sum(1 for frame in report["frames"] if frame["passed"])
    print(
        json.dumps(
            {
                "locations": len(rows),
                "passed": passed,
                "refused": len(rows) - passed,
                "fates": dict(sorted(fates.items())),
                "tile": report["tile"],
                "field_supersample": report["field_supersample"],
                "battery": report["battery"],
                "seconds": round(report["seconds"], 1),
                "wrote": str(out),
            },
            indent=2,
        )
    )
    return 0


def sample_boundary(args: argparse.Namespace) -> int:
    """Draw frames at random and keep the ones every structural gate passed."""
    from fractal_wallpapers.discovery import boundary

    family: dict = {"kind": args.family}
    if args.family in ("multibrot", "julia"):
        family["degree"] = args.degree
    if args.family == "julia":
        if args.c is None:
            print("--c is required for a julia draw: it is half of the location's identity")
            return 1
        family["c"] = args.c

    try:
        report = boundary.sample(
            family,
            seed=args.seed,
            keep=args.keep,
            attempts=args.attempts,
            band=(args.width_low, args.width_high),
            out_dir=resolve_output(args.out_dir),
            colormap=args.colormap,
            images=not args.no_images,
        )
    except boundary.BoundaryError as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    return 0 if report["kept"] >= args.keep else 1


def add_commands(subcommands) -> None:
    """Register this group's commands, in the order they ship in."""
    draw = subcommands.add_parser(
        "render",
        help="render one location to a PNG through the engine",
        description=(
            "Render one location. Coordinates and family constants are given as decimal "
            "strings and are recorded exactly as written."
        ),
    )
    location_arguments(draw)
    record_input = draw.add_argument_group(
        "a record instead of flags",
        "either one names what the flags above would have spelled out",
    )
    record_input.add_argument(
        "--location",
        metavar="FILE",
        help="a location record to render instead of spelling one out: the "
        "{family, viewport, render} object a ledger row, a label row and a release "
        "record all already carry",
    )
    record_input.add_argument(
        "--manifest",
        metavar="FILE",
        help="a JSONL of location records to render, one picture per row, into --out-dir. "
        "A file rather than a list of paths, because a batch is hundreds of rows and a "
        "Windows command line is not",
    )
    written = draw.add_argument_group(
        "the output",
        "--out is the single render; the other three are the --manifest batch",
    )
    written.add_argument(
        "--out",
        default=str(Path("artifacts") / "render.png"),
        help="output PNG path (default: artifacts/render.png)",
    )
    written.add_argument(
        "--out-dir",
        default=str(Path("artifacts") / "renders"),
        help="where a --manifest run's pictures go (default: artifacts/renders). Each is "
        "named by its row and a digest of its own recipe, and renders.jsonl beside them "
        "is the join back to the records",
    )
    written.add_argument("--limit", type=int, help="render only the first N rows of a manifest")
    written.add_argument(
        "--resume",
        action="store_true",
        help="skip a row whose picture is already on disk",
    )
    draw.set_defaults(handler=render)

    screening = subcommands.add_parser(
        "screen",
        help="put a location through the structural gates and report every verdict",
        description=(
            "The gates a walk refuses candidates at — the interior cap, the escape band, "
            "the occupancy floor — run over a frame you name rather than one the walk "
            "proposed. Every gate that ran reports what it read and what it read that "
            "against; the ones a refusal came before report nothing, because they did not "
            "run. Nothing here is a second copy of the filter: it is the same battery the "
            "walk spends, at the geometry the walk spends it at. With --location the "
            "exit code is the verdict: 0 if the frame passed, 1 if a gate refused it. "
            "With --manifest it is 0 whenever the batch ran, because a refusal is a row "
            "in the output rather than a failure of the command."
        ),
    )
    naming = screening.add_mutually_exclusive_group(required=True)
    naming.add_argument("--location", metavar="FILE", help="one location record to screen")
    naming.add_argument("--manifest", metavar="FILE", help="a JSONL of location records to screen")
    screening.add_argument(
        "--out",
        default=str(Path("artifacts") / "screen" / "screened.jsonl"),
        help="where a --manifest run's verdicts go (default: artifacts/screen/screened.jsonl)",
    )
    screening.add_argument(
        "--out-dir",
        help="also write the frame each gate read, as a JPEG per location. A frame the "
        "interior cap refused has none: it never got past the 128-pixel probe",
    )
    screening.add_argument("--limit", type=int, help="screen only the first N rows")
    screening.add_argument(
        "--node-width",
        type=int,
        default=384,
        help="width of the frame the gates read (default: 384, the node regime's own)",
    )
    screening.add_argument(
        "--colormap",
        default="twilight_shifted",
        help="colormap the frame is shaded through before its detail is measured",
    )
    screening.add_argument(
        "--waive-occupancy",
        action="store_true",
        help="do not run the occupancy floor. What a walk does at its FIRST RUNG, where "
        "the gate over-fires on a root frame still resolving structure the tighter child "
        "has not entered yet - so a first-rung ledger candidate passed a battery of two "
        "gates and screening it against three reports a refusal its run never made",
    )
    screening.set_defaults(handler=screen)

    drawing = subcommands.add_parser(
        "sample-boundary",
        help="draw frames at random and keep the ones the structural gates pass",
        description=(
            "Deep inside a set nothing escapes and far outside everything does, so a frame "
            "that clears all three structural gates is straddling the boundary — there is "
            "no other way to clear them. That makes an unscreened uniform draw plus the "
            "gates a boundary sampler, and this is it: seeded, so a number reproduces the "
            "frames; recording every attempt and not only the keepers, because the yield "
            "is the measurement. Writes draws.jsonl (the record) and kept.jsonl (a plain "
            "location manifest of the survivors)."
        ),
    )
    drawing.add_argument(
        "--family",
        choices=["mandelbrot", "multibrot", "julia", "phoenix"],
        default="mandelbrot",
        help="which family to draw over (default: mandelbrot)",
    )
    drawing.add_argument("--degree", type=int, default=2, help="exponent d, for multibrot/julia")
    drawing.add_argument(
        "--c", nargs=2, metavar=("RE", "IM"), help="fixed constant c: required for julia"
    )
    drawing.add_argument("--seed", type=int, default=0, help="draw seed (default: 0)")
    drawing.add_argument("--keep", type=int, default=12, help="survivors to stop at (default: 12)")
    drawing.add_argument(
        "--attempts",
        type=int,
        default=4000,
        help="attempts to stop at whether or not --keep was reached (default: 4000). A draw "
        "that ends here measured a rarity and says so",
    )
    drawing.add_argument(
        "--width-low",
        type=float,
        default=boundary_default("WIDTH_LOW"),
        help=f"narrow end of the log-uniform width band (default: {boundary_default('WIDTH_LOW')})",
    )
    drawing.add_argument(
        "--width-high",
        type=float,
        default=boundary_default("WIDTH_HIGH"),
        help=f"wide end of the band (default: {boundary_default('WIDTH_HIGH')})",
    )
    drawing.add_argument(
        "--colormap",
        default="twilight_shifted",
        help="colormap the frame is shaded through before its detail is measured",
    )
    drawing.add_argument(
        "--out-dir",
        default=str(Path("artifacts") / "boundary"),
        help="where the record, the manifest and the frames go (default: artifacts/boundary)",
    )
    drawing.add_argument(
        "--no-images", action="store_true", help="record the verdicts and keep no pictures"
    )
    drawing.set_defaults(handler=sample_boundary)

    dump = subcommands.add_parser(
        "dump-field",
        help="write the raw scalar field a render would have colored",
        description=(
            "Write the field itself instead of a picture of it: little-endian f32 at "
            "supersampled resolution, plus a record beside it saying what it is. Only for "
            "modes with a single scalar field behind them; a composite or a direct trap has "
            "none, and says so."
        ),
    )
    location_arguments(dump)
    # A group for one flag, because `location_arguments` groups the fourteen it
    # adds and an ungrouped flag beside them prints under `options:` next to
    # `-h`, reading like something that got left behind.
    dump_output = dump.add_argument_group("the output")
    dump_output.add_argument(
        "--out",
        default=str(Path("artifacts") / "field.f32"),
        help="output field path (default: artifacts/field.f32)",
    )
    dump.set_defaults(handler=dump_field)

    again = subcommands.add_parser(
        "recolor",
        help="color a dumped field again without re-iterating it",
        description=(
            "Read a dumped field and color it. Everything about the location comes from the "
            "dump's own record, so this costs a pass over memory rather than a render."
        ),
    )
    again.add_argument("--field", required=True, help="path to a dumped field")
    again.add_argument("--colormap", help="colormap name (default: the one the dump recorded)")
    again.add_argument(
        "--transform",
        choices=["linear", "sqrt", "log", "scurve"],
        help="curve applied to the normalized field (default: the one the dump recorded)",
    )
    again.add_argument(
        "--mirror",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "fold the map as an out-and-back. Default: the pipeline's rule — folded "
            "unless the map is cyclic. --no-mirror draws the unfolded ramp"
        ),
    )
    again.add_argument(
        "--out",
        default=str(Path("artifacts") / "recolored.png"),
        help="output PNG path (default: artifacts/recolored.png)",
    )
    again.set_defaults(handler=recolor)
