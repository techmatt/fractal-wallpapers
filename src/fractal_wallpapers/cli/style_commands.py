"""`style`: the named layer stacks, and drawing a location in one."""

from __future__ import annotations

import argparse
import json

from fractal_wallpapers import engine
from fractal_wallpapers.cli.common import resolve_input, resolve_output
from fractal_wallpapers.paths import tracked_name


def style(args: argparse.Namespace) -> int:
    """List the styles, show one, or render locations in one."""
    from fractal_wallpapers import styles

    try:
        if args.what == "list":
            for name in styles.names():
                document = styles.load(name)
                print(f"{name:<24} {document['suggested_colormap']:<24} {document['description']}")
            return 0
        if args.what == "show":
            print(json.dumps(styles.load(args.name), indent=2, ensure_ascii=False))
            return 0
        if args.what == "tones":
            return check_tones(args, styles)
        if args.what == "keep":
            return keep_style(args)
        if args.what == "scout":
            return scout_style(args)
        if args.what == "picker":
            return build_picker(args)
        return render_style(args, styles)
    except styles.StyleError as refusal:
        print(refusal)
        return 1


def keep_style(args: argparse.Namespace) -> int:
    """Record a style picker's keeps and copy their pictures beside the reference."""
    from fractal_wallpapers import style_keeps

    named = {
        key: resolve_input(getattr(args, key)) if getattr(args, key) else None
        for key in ("manifest", "renders")
    }
    try:
        done = style_keeps.keep(
            args.name,
            resolve_input(args.choices),
            manifest_path=named["manifest"],
            renders_path=named["renders"],
        )
    except style_keeps.KeepError as refusal:
        print(refusal)
        return 1
    except RuntimeError as refusal:
        print(str(refusal).removeprefix("engine failed: "))
        return 1
    print(
        f"{done['kept']} kept ({done['copied']} copied, {done['drawn']} drawn again); "
        f"{done['total']} in {tracked_name(done['record'])}; pictures in {done['folder']}"
    )
    return 0


def scout_style(args: argparse.Namespace) -> int:
    """Draw a picker's candidate locations from the published galleries, never a spiral."""
    from collections import Counter

    from fractal_wallpapers import style_scout
    from fractal_wallpapers.curation import tentative

    if args.points:
        return scout_points(args, style_scout)
    named = args.record or [style_scout.default_record()]
    try:
        seats, passed = style_scout.candidates(
            named,
            max_p_spiral=args.max_p_spiral,
            partitions=args.partition,
            kinds=args.kind,
            degrees=args.degree,
            modes=args.mode,
        )
    except (style_scout.ScoutError, tentative.TentativeRefused) as refusal:
        print(refusal)
        return 1
    out = resolve_output(args.out)
    scratch = out.parent / f"{out.stem}.probe"
    try:
        drawn, readings = style_scout.draw(
            seats,
            args.n,
            args.seed,
            max_ink=args.max_ink,
            thinnest=args.thinnest,
            limit=args.probe_limit,
            scratch=scratch,
            log=None if args.quiet else print,
        )
    except RuntimeError as refusal:
        print(str(refusal).removeprefix("engine failed: "))
        return 1
    finally:
        if scratch.is_dir() and not any(scratch.iterdir()):
            scratch.rmdir()
    style_scout.write(drawn, out)
    skipped = ", ".join(f"{count} {why}" for why, count in passed.items() if count)
    by = Counter(row["name"].rsplit("_", 1)[0] for row in drawn)
    print(f"{len(seats)} seats to draw from ({skipped or 'none'} passed over)")
    if readings:
        ordered = sorted(readings)
        print(
            f"{len(readings)} probed: ink {ordered[0]:.4f} to {ordered[-1]:.4f}, median "
            f"{ordered[len(ordered) // 2]:.4f}; {len(drawn)} kept"
        )
    partitions = dict(sorted(by.items()))
    print(f"{len(drawn)} drawn (seed {args.seed}) into {tracked_name(out)}: {partitions}")
    return 0 if drawn else 1


def scout_points(args: argparse.Namespace, style_scout) -> int:
    """Measure hand-placed or atlas points for a structure the galleries lack."""
    from fractal_wallpapers import style_picker

    if args.max_ink is None and not args.thinnest:
        print("--points is for a structure the galleries lack: give --max-ink or --thinnest")
        return 1
    points = style_picker.records_as_written(resolve_input(args.points))
    out = resolve_output(args.out)
    scratch = out.parent / f"{out.stem}.probe"
    try:
        kept, readings = style_scout.measure(
            points[: args.probe_limit or None],
            args.n,
            args.max_ink,
            args.thinnest,
            scratch,
            log=None if args.quiet else print,
        )
    except RuntimeError as refusal:
        print(str(refusal).removeprefix("engine failed: "))
        return 1
    finally:
        if scratch.is_dir() and not any(scratch.iterdir()):
            scratch.rmdir()
    style_scout.write(kept, out)
    print(
        f"{len(readings)} points probed, {len(kept)} kept into {tracked_name(out)}; none of "
        "them was read by the spiral probe, so check each by eye"
    )
    return 0 if kept else 1


def build_picker(args: argparse.Namespace) -> int:
    """Turn a plan of rendered pictures into a picker and its renders sidecar."""
    from pathlib import Path

    from fractal_wallpapers import style_picker
    from fractal_wallpapers.paths import repo_root

    plan_path = resolve_input(args.plan)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    folder = Path(resolve_output(args.out or f"artifacts/pickers/{plan.get('name', '')}"))
    try:
        done = style_picker.build(plan, folder, repo_root(), resolve=resolve_input)
    except (style_picker.PickerError, KeyError) as refusal:
        print(refusal)
        return 1
    print(
        f"{done['options']} options in {done['rows']} rows: {tracked_name(done['manifest'])}, "
        f"sidecar {tracked_name(done['renders'])}"
    )
    return 0


def check_tones(args: argparse.Namespace, styles) -> int:
    """Hold each picture's lightness against the style's reference; 1 when any misses."""
    from pathlib import Path

    document = styles.load(args.name)
    named = args.reference
    reference = resolve_input(named) if named else styles.reference_path(document)
    if not reference.is_file():
        print(f"no reference picture at {reference}; pass --reference")
        return 1
    held = styles.tones(reference)
    header = " ".join(f"{key:>6}" for key in styles.TONES)
    print(f"{'':<8} {header}  picture")
    print(f"{'ref':<8} {' '.join(f'{held[k]:6.3f}' for k in styles.TONES)}  {reference.name}")
    failed = drafts = 0
    for name in args.pictures:
        try:
            stats = styles.tones(resolve_input(name))
        except OSError as unreadable:
            failed += 1
            print(f"{'UNREAD':<8} {Path(name).name}: {unreadable}")
            continue
        misses = styles.tone_misses(stats, held)
        small = stats["width"] < styles.CHECKED_WIDTH
        failed += bool(misses) or small
        drafts += small
        verdict = "DRAFT" if small else "holds" if not misses else "MISSES"
        row = " ".join(f"{stats[k]:6.3f}" for k in styles.TONES)
        print(f"{verdict:<8} {row}  {Path(name).name}{'  ' + '; '.join(misses) if misses else ''}")
    if args.pictures:
        held_count = len(args.pictures) - failed
        print(f"{held_count} of {len(args.pictures)} hold the reference's balance")
    if drafts:
        size = "x".join(map(str, styles.DRAFT_RESOLUTION))
        print(
            f"{drafts} under {styles.CHECKED_WIDTH} wide: a picture that small is the samples the "
            f"tone pass met its targets on, so its tones are a guide, not the check; draft at "
            f"--draft ({size} ss{styles.DRAFT_SUPERSAMPLE}) to check"
        )
    return 1 if failed else 0


def render_style(args: argparse.Namespace, styles) -> int:
    """Draw one location record, or every row of a manifest, in a style."""
    from fractal_wallpapers import locations

    document = styles.load(args.name)
    from fractal_wallpapers import style_picker

    try:
        if args.location:
            source = resolve_output(args.location)
            rows = [locations.read_one(source, drawing=True)]
        else:
            source = resolve_output(args.manifest)
            rows = locations.read(source, drawing=True)
    except locations.LocationError as refusal:
        print(refusal)
        return 1
    # The records as written: what names a picture and what the render log keeps, since
    # the read above folds `maxiter` into the render and drops `name` and `note`.
    written = style_picker.records_as_written(source)
    if len(written) != len(rows):
        written = rows

    resolution, supersample = list(args.resolution), args.supersample
    if args.draft:
        resolution, supersample = list(styles.DRAFT_RESOLUTION), styles.DRAFT_SUPERSAMPLE
    for row in rows:
        row["render"] = {**row["render"], "resolution": resolution, "supersample": supersample}
    colormap = args.colormap or document["suggested_colormap"]
    if args.location:
        targets = [resolve_output(args.out)]
        targets[0].parent.mkdir(parents=True, exist_ok=True)
    else:
        directory = resolve_output(args.out_dir)
        directory.mkdir(parents=True, exist_ok=True)
        targets = [
            directory / f"{index:02d}_{raw.get('name') or locations.name_of(row)}_{colormap}.png"
            for index, (row, raw) in enumerate(zip(rows, written, strict=True))
        ]

    for row, raw, output in zip(rows, written, targets, strict=True):
        spec = styles.spec_of(row, document, output, colormap=args.colormap)
        try:
            report = engine.render_report(spec)
        except RuntimeError as refusal:
            print(str(refusal).removeprefix("engine failed: "))
            return 1
        report.pop("style", None)
        print(json.dumps({"output": tracked_name(output), **report}, ensure_ascii=False))
        drawn = style_picker.log_row(
            output, raw, document["name"], colormap, resolution, supersample, spec["style"]
        )
        style_picker.append_log([drawn], output.parent)
    return 0


def add_commands(subcommands) -> None:
    """Register this group's commands, in the order they ship in."""
    group = subcommands.add_parser(
        "style",
        help="the named layer stacks (data/styles/): list, show, or render a location in one",
    )
    group.set_defaults(handler=style)
    verbs = group.add_subparsers(dest="what", required=True)
    verbs.add_parser("list", help="every style, its suggested colormap and what it is")
    show = verbs.add_parser("show", help="print one style file whole")
    show.add_argument("name", help="a style name `style list` prints")
    tones = verbs.add_parser(
        "tones",
        help="hold rendered pictures' lightness against the style's reference picture",
    )
    tones.add_argument("name", help="a style name `style list` prints, or a draft .json")
    tones.add_argument(
        "pictures",
        nargs="*",
        help="rendered pictures to check (none: print the reference's own numbers)",
    )
    tones.add_argument(
        "--reference",
        help="the reference picture (default: the style file's, beside this checkout)",
    )

    scout = verbs.add_parser(
        "scout",
        help="draw a picker's candidate locations from the published galleries, never a "
        "spiral, stratified over partitions and seeded; filters say what structure a style "
        "needs",
    )
    scout.add_argument("--out", required=True, help="the location manifest to write (JSONL)")
    scout.add_argument("--n", type=int, default=40, help="how many to draw (default: 40)")
    scout.add_argument("--seed", type=int, default=0, help="the draw's seed (default: 0)")
    scout.add_argument(
        "--record",
        action="append",
        help="a published record, by name (final139_green) or stamp; repeatable, a seat in "
        "two counts once (default: tentative.DEFAULT's, final139_general)",
    )
    scout.add_argument(
        "--max-p-spiral",
        type=float,
        help="pass over a seat whose spiral probe reads above this, beside the `spiral` flag "
        "every row carries (the flag sits near 0.3)",
    )
    scout.add_argument(
        "--partition",
        action="append",
        help="only this gallery partition (mandelbrot, julia:multibrot3, ...); repeatable",
    )
    scout.add_argument(
        "--kind", action="append", choices=["julia", "plane"], help="dynamical or parameter plane"
    )
    scout.add_argument("--degree", action="append", type=int, help="only this degree; repeatable")
    scout.add_argument(
        "--mode", action="append", help="only seats seated in this named mode; repeatable"
    )
    scout.add_argument(
        "--max-ink",
        type=float,
        help="probe each drawn seat (a 320x200 render, about a second) and keep it when a "
        "hair of light at the set paints at most this share of the frame: 0.03 is thin "
        "dendrites, 0.10 is what a distance glow draws without flooding (README)",
    )
    scout.add_argument(
        "--thinnest",
        action="store_true",
        help="probe a batch (--probe-limit) and keep the --n thinnest, thinnest first: for a "
        "style that needs thin sets, which the galleries hold few of",
    )
    scout.add_argument(
        "--probe-limit",
        type=int,
        help="seats a measured draw probes at most (default: ten per seat asked for)",
    )
    scout.add_argument(
        "--points",
        metavar="FILE",
        help="measure these hand-placed or atlas location records (JSONL) instead of a "
        "gallery: only for a style whose README entry names a structure the galleries lack; "
        "needs --max-ink or --thinnest",
    )
    scout.add_argument("--quiet", action="store_true", help="do not print each probe")

    picker = verbs.add_parser(
        "picker",
        help="build a picker from a plan of rendered pictures: JPEGs, a manifest whose rows "
        "default to nothing selected, and the renders sidecar `style keep` reads",
    )
    picker.add_argument("plan", help="the plan JSON (style_picker.py's docstring has its shape)")
    picker.add_argument(
        "--out",
        help="the picker folder (default: artifacts/pickers/<plan name>/)",
    )

    keep = verbs.add_parser(
        "keep",
        help="record a style picker's keeps (data/styles/<name>.keeps.json) and copy their "
        "pictures to fractal-drive-sync/style-keeps/<name>/; re-running merges",
    )
    keep.add_argument("name", help="the style the picker was for")
    keep.add_argument("choices", help="the picker's saved <picker>.choices.json")
    keep.add_argument(
        "--manifest",
        help="the picker manifest (default: the one the choices file names)",
    )
    keep.add_argument(
        "--renders",
        help="the renders sidecar, one row per option key (default: renders.jsonl beside "
        "the manifest)",
    )

    render = verbs.add_parser(
        "render",
        help="draw a location record, or each row of a manifest, in a style with any colormap",
    )
    render.add_argument("name", help="a style name `style list` prints")
    where = render.add_mutually_exclusive_group(required=True)
    where.add_argument(
        "--location",
        metavar="FILE",
        help="one location record: the {family, viewport, maxiter} object `render` reads",
    )
    where.add_argument(
        "--manifest",
        metavar="FILE",
        help="a JSONL of location records, one picture per row, into --out-dir",
    )
    render.add_argument(
        "--colormap",
        help="any colormap `palettes list` prints (default: the style's suggested one)",
    )
    render.add_argument(
        "--resolution",
        nargs=2,
        type=int,
        metavar=("W", "H"),
        default=[2560, 1600],
        help="output size in pixels (default: 2560 1600)",
    )
    render.add_argument(
        "--supersample",
        type=int,
        default=2,
        help="samples per output pixel, per axis (default: 2)",
    )
    render.add_argument(
        "--draft",
        action="store_true",
        help="draw at the draft size whose tones are the full size's (1280x800 ss2), in "
        "place of --resolution and --supersample",
    )
    render.add_argument(
        "--out",
        default="artifacts/style.png",
        help="the picture, for --location (default: artifacts/style.png)",
    )
    render.add_argument(
        "--out-dir",
        default="artifacts/styles",
        help="where a --manifest run's pictures go (default: artifacts/styles)",
    )
