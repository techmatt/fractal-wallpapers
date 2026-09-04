"""`palettes`: the colormap library and what is measured over it."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fractal_wallpapers.cli.common import (
    resolve_output,
)
from fractal_wallpapers.palettes import color_mass as color_mass_module
from fractal_wallpapers.palettes import groups as palette_groups
from fractal_wallpapers.palettes import strip as palette_strip
from fractal_wallpapers.paths import (
    tracked_name,
)


def palettes_provenance(args: argparse.Namespace) -> int:
    """Rebuild the record of how the made maps were made."""
    from fractal_wallpapers.palettes import provenance

    try:
        report = provenance.run(Path(args.source), Path(args.images) if args.images else None)
    except provenance.ProvenanceError as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def palettes_ingest(args: argparse.Namespace) -> int:
    """Densify a drop of authored palettes into maps the engine can bake."""
    from fractal_wallpapers.palettes import authored_import

    try:
        report = authored_import.run(args.drop)
    except authored_import.AuthoredImportError as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def palettes_groups(args: argparse.Namespace) -> int:
    """Recompute which maps are near enough to be one choice, and rewrite the table."""
    try:
        report = palette_groups.run(cut=args.cut, log=None if args.quiet else print)
    except palette_groups.GroupError as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    return 0


def palettes_reference_fields(args: argparse.Namespace) -> int:
    """Dump the three fields every palette sheet is rendered on."""
    from fractal_wallpapers.palettes import reference_fields

    try:
        report = reference_fields.run(force=args.force)
    except reference_fields.ReferenceFieldError as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def palettes_carriers(args: argparse.Namespace) -> int:
    """Rebuild the table of which map can make a picture of which colour."""
    from fractal_wallpapers.palettes import carriers

    try:
        report = carriers.run(force=args.force, log=None if args.quiet else print)
    except carriers.CarrierError as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def palettes_color_mass(args: argparse.Namespace) -> int:
    """Cut the tracked colour-mass map out of the census and the sweep."""
    from fractal_wallpapers.palettes import color_mass

    try:
        sweep = Path(args.sweep) if args.sweep else color_mass.sweep_log_path()
        report = color_mass.build(
            census=Path(args.census),
            sweep=sweep,
            floor=args.floor,
            log=(lambda _line: None) if args.quiet else print,
        )
    except (color_mass.ColorMassError, OSError) as refusal:
        print(refusal)
        return 1
    print(json.dumps({key: value for key, value in report.items() if key != "files"}, indent=2))
    return 0


def palettes_strip(args: argparse.Namespace) -> int:
    """Draw one map's gradient, or every map a manifest names."""
    if args.name is not None:
        output = resolve_output(args.out or Path("artifacts") / "figures" / f"{args.name}.png")
        names, outputs = [args.name], [output]
    else:
        directory = resolve_output(args.out_dir)
        names = palette_strip.names_from(resolve_output(args.manifest))
        outputs = [directory / f"{name}.png" for name in names]

    drawn = []
    for name, output in zip(names, outputs, strict=True):
        try:
            drawn.append(palette_strip.draw(name, output, args.width, args.height, args.mirror))
        except palette_strip.StripError as refusal:
            print(refusal)
            return 1
        print(f"[strip] {name} -> {tracked_name(output)}")
    print(json.dumps({"strips": len(drawn), "drawn": drawn}, indent=2))
    return 0


def add_commands(subcommands) -> None:
    """The colormap library itself: where its maps came from, how they group, what they look like.

    Kept apart from `palette`, which is the *head* that chooses between maps.
    These are about the maps: nothing here loads a model, and the one that reads a
    label reads it only to decide which of two identical maps a record names.
    """
    group = subcommands.add_parser(
        "palettes",
        help="the colormap library: ingest, provenance, groups, and a map's gradient",
        description=(
            "The maps themselves, not the head that picks between them. `ingest` densifies "
            "a drop of authored palettes into the library, `provenance` rebuilds the record "
            "of how the made maps were made, `groups` says which maps are near enough to "
            "be one choice, "
            "`reference-fields` remakes the pictures a palette sheet is judged on, "
            "`carriers` says which map can make a picture of which colour, and "
            "`strip` draws one map's gradient the way a render spends it."
        ),
    )
    steps = group.add_subparsers(dest="step", required=True)

    ingesting = steps.add_parser(
        "ingest",
        help="densify a drop of authored palettes into the colormap library",
        description=(
            "Reads a tracked drop under data/palettes/batches, interpolates each palette's "
            "OKLCH control points in OKLab, and writes it beside the other maps. Whether a "
            "map is cyclic is measured on the gradient — twice — rather than assumed from "
            "the drop it arrived in, and a name the library already holds is refused until "
            "the drop's renames.json says what it ships as."
        ),
    )
    ingesting.add_argument("--drop", required=True, help="the drop's directory name")
    ingesting.set_defaults(handler=palettes_ingest)

    recovering = steps.add_parser(
        "provenance",
        help="rebuild the record of how the authored and extracted maps were made",
        description=(
            "Reads the generator's batch archive and the source project's pooled library, "
            "matches by name, and writes one row per made map beside the colormaps. An "
            "unmatched name on either side is reported, never guessed at."
        ),
    )
    recovering.add_argument("--source", required=True, help="the source project's root")
    recovering.add_argument(
        "--images",
        help=(
            "directory of the pictures the extracted maps were read from, so a row can "
            "name the file rather than the stem"
        ),
    )
    recovering.set_defaults(handler=palettes_provenance)

    collapsing = steps.add_parser(
        "groups",
        help="recompute which maps are near enough to be one choice",
        description=(
            "Average linkage over M1 — the sliced Wasserstein distance between two maps' "
            "hue-weighted Oklab clouds, read through the engine's own bake — cut where a "
            "forty-six pair calibration sheet marked by eye says the line is. Writes the "
            "tracked table the drawable pool collapses through. A pure function of the "
            "library, which is what lets a test hold the committed file to this command."
        ),
    )
    collapsing.add_argument(
        "--cut",
        type=float,
        default=palette_groups.CUT,
        help=(
            f"the linkage height maps stop being one choice at (default: {palette_groups.CUT}, "
            "the only cut every mark on the calibration sheet agrees with)"
        ),
    )
    collapsing.add_argument(
        "--quiet", action="store_true", help="do not print the metric's progress"
    )
    collapsing.set_defaults(handler=palettes_groups)

    pinning = steps.add_parser(
        "reference-fields",
        help="dump the three fields every palette sheet is rendered on",
        description=(
            "Three released gallery3 locations — one coloured once, one the ramp sweeps "
            "across several times, one a parameter plane — remade from their tracked specs "
            "into artifacts/. The spec is what the repository keeps; the field is a "
            "megabyte of floats and is regenerated rather than committed."
        ),
    )
    pinning.add_argument(
        "--force", action="store_true", help="re-dump a field that is already on disk"
    )
    pinning.set_defaults(handler=palettes_reference_fields)

    carrying = steps.add_parser(
        "carriers",
        help="rebuild the table of which map can make a picture of which colour",
        description=(
            "Every map in the library recoloured onto the three pinned reference fields and "
            "read for the colours it is OF: a map CARRIES a cell when that field's picture "
            "is dominant in it. Writes the tracked table a colour target draws its carrier "
            "attempts from, and refuses to launch against. Keyed to the MAP and never to the "
            "palette group — members of one group disagree on their dominant cell in 120 of "
            "195 reads, and 96 of those cross a hue family. About ninety seconds; the "
            "recolours are kept under artifacts/ and a second run is the census alone."
        ),
    )
    carrying.add_argument(
        "--force", action="store_true", help="re-dump the reference fields before reading"
    )
    carrying.add_argument("--quiet", action="store_true", help="do not print progress")
    carrying.set_defaults(handler=palettes_carriers)

    massing = steps.add_parser(
        "color-mass",
        help="cut the tracked map of what colour each (palette group, mode) pair makes",
        description=(
            "The mean chromatic share per codebook cell for every one of the 14,796 "
            "(palette group, mode) pairs, unioned over the two measurements that exist: "
            "the judged pool, which is where the palette head went, and the seeded "
            "two-location sweep, which covers the grid it never visited. Stored sparse, "
            "one tracked file per mode. Reads records only and renders nothing; the two "
            "source files are experiment logs and are named rather than assumed."
        ),
    )
    massing.add_argument(
        "--census",
        default=str(Path("scratch") / "palette_mass_census" / "observations.jsonl"),
        help="the census's per-observation record",
    )
    massing.add_argument(
        # Resolved in the handler and not here. `paths.under` reads the configured
        # tiers, and building a parser must not touch a disk: `--help` on a machine
        # whose hot root is unplugged would raise before argparse said anything.
        "--sweep",
        default=None,
        help=(
            "the sweep's per-render record (default: "
            "artifacts/curation/palette_mass_sweep/rows.jsonl, on whichever tier holds it)"
        ),
    )
    massing.add_argument(
        "--floor",
        type=float,
        default=color_mass_module.STORED_FLOOR,
        help=(
            f"the smallest mean share a cell is stored at (default: "
            f"{color_mass_module.STORED_FLOOR})"
        ),
    )
    massing.add_argument("--quiet", action="store_true", help="do not print per-mode progress")
    massing.set_defaults(handler=palettes_color_mass)

    drawing = steps.add_parser(
        "strip",
        help="draw one map's gradient as the renderer spends it",
        description=(
            "A horizontal ramp, colored by the engine through the same bake a wallpaper "
            "gets — folded where the map is sequential, unless told otherwise. Nothing "
            "here interpolates a colour: a second densifier is how two pictures of one "
            "map come to disagree."
        ),
    )
    named = drawing.add_mutually_exclusive_group(required=True)
    named.add_argument("--name", help="one colormap")
    named.add_argument(
        "--manifest",
        help="a file of colormap names, one to a line — `#` starts a comment",
    )
    drawing.add_argument(
        "--width", type=int, default=palette_strip.WIDTH, help="strip width in pixels"
    )
    drawing.add_argument(
        "--height", type=int, default=palette_strip.HEIGHT, help="strip height in pixels"
    )
    drawing.add_argument(
        "--mirror",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="override the fold. Default: folded unless the map is cyclic",
    )
    drawing.add_argument("--out", help="output PNG path, for --name")
    drawing.add_argument(
        "--out-dir",
        default=str(Path("artifacts") / "figures" / "palette_strips"),
        help="where a manifest's strips land (default: artifacts/figures/palette_strips)",
    )
    drawing.set_defaults(handler=palettes_strip)
