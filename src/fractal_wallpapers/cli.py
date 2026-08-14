"""The `fractal-wallpapers` command line.

Everything runnable in this project is a subcommand here. There is no
`scripts/` directory: if a step is worth running twice it gets a subcommand,
a name, and `--help` text.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from collections.abc import Sequence
from pathlib import Path

from fractal_wallpapers import engine
from fractal_wallpapers.paths import colormap_dir, repo_root

WEIGHTS_MANIFEST = Path("models") / "weights.json"
RELEASE_URL = "https://github.com/techmatt/fractal-wallpapers/releases/download/{tag}/{asset}"

__all__ = ["build_parser", "main", "repo_root"]


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_weights(args: argparse.Namespace) -> int:
    """Download each head's weights from GitHub Releases and verify its sha256."""
    manifest_path = repo_root() / WEIGHTS_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    heads = manifest.get("heads", {})
    if not heads:
        print(f"no weights listed in {WEIGHTS_MANIFEST.as_posix()}; nothing to fetch")
        return 0

    for head, entry in sorted(heads.items()):
        if args.head and head != args.head:
            continue
        destination = repo_root() / "models" / head / entry["asset"]
        if destination.is_file() and sha256_of(destination) == entry["sha256"]:
            print(f"{head}: already present")
            continue
        url = RELEASE_URL.format(tag=entry["tag"], asset=entry["asset"])
        print(f"{head}: fetching {url}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, destination)  # noqa: S310
        actual = sha256_of(destination)
        if actual != entry["sha256"]:
            destination.unlink()
            print(f"{head}: sha256 mismatch (expected {entry['sha256']}, got {actual})")
            return 1
        print(f"{head}: verified")
    return 0


def resolve_output(out: str) -> Path:
    """Resolve an output path against the repository, not the shell's cwd.

    A relative `--out` means the same place whichever directory the command was
    run from, which is what keeps the default landing in the ignored
    `artifacts/` tree instead of scattering PNGs wherever the caller stood.
    """
    path = Path(out)
    return path if path.is_absolute() else repo_root() / path


def render_spec(args: argparse.Namespace) -> dict:
    """Turn command-line arguments into the JSON object the engine reads.

    Coordinates and family constants stay **strings** the whole way through. A
    location's identity is what was written, not the `f64` it rounds to, and
    parsing it here to hand the engine a float would throw that away at the one
    point in the pipeline that still has it.

    `render` and `dump-field` build the same spec: a dump is a render stopped
    one stage early, and the colormap it names is the one its record hands back
    to a recolor that does not choose for itself.
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
        "mode": args.mode,
        "colormap": args.colormap,
        "colormap_dir": str(colormap_dir()),
        "output": str(resolve_output(args.out)),
    }
    if viewport:
        spec["viewport"] = viewport
    if args.maxiter is not None:
        spec["maxiter"] = args.maxiter
    return spec


def refuse_impossible_location(args: argparse.Namespace) -> str | None:
    """Say why this location cannot be rendered, or `None` if it can."""
    if args.family == "julia" and args.c is None:
        return "--c is required for a julia render: it is half of the location's identity"
    if args.family not in ("julia", "multibrot") and args.degree != 2:
        return f"--degree does not apply to a {args.family} render"
    return None


def render(args: argparse.Namespace) -> int:
    """Render one image and print the engine's report."""
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


def recolor(args: argparse.Namespace) -> int:
    """Color a dumped field through another colormap, without re-iterating."""
    spec: dict[str, object] = {
        "schema": 1,
        "field": str(resolve_output(args.field)),
        "colormap_dir": str(colormap_dir()),
        "output": str(resolve_output(args.out)),
    }
    if args.colormap is not None:
        spec["colormap"] = args.colormap
    if args.transform is not None:
        spec["transform"] = args.transform
    print(json.dumps(engine.recolor(spec), indent=2))
    return 0


def refuse_impossible_walk(args: argparse.Namespace) -> str | None:
    """Say why this walk has nowhere to start, or `None` if it has.

    Checked before anything is built, because "there is no supply for this" is a
    refusal and a refusal should not leave a run directory behind it.
    """
    if args.seeds:
        return None
    if args.family == "julia" and args.degree != 2:
        return (
            "the tracked c-pool is degree 2; a higher-degree julia walk needs --seeds, "
            "because its parameters live in a different plane and no pool of them is "
            "tracked yet"
        )
    if args.family in ("mandelbrot", "multibrot"):
        return (
            f"a {args.family} walk has no seed pool and no sampler: an unscreened draw "
            "over the parameter plane measured zero good locations in 144, so none is "
            "built. Supply roots with --seeds FILE, or let the reframing operators find "
            "them from a walk that already reached somewhere."
        )
    return None


def walk(args: argparse.Namespace) -> int:
    """Run one discovery walk and print what it found."""
    from fractal_wallpapers.discovery.walk import Gates, Limits, Policy, Reframings, Walk

    complaint = refuse_impossible_walk(args)
    if complaint is not None:
        print(complaint)
        return 1

    run = Walk(
        out_dir=resolve_output(args.out_dir),
        seed=args.seed,
        limits=Limits(
            batch=args.batch,
            batches=args.batches,
            root_expansions=args.root_expansions,
            probe_probability=args.probe,
        ),
        policy=Policy(candidates=args.candidates, node_width=args.node_width),
        gates=Gates(),
        reframings=Reframings(
            enabled=not args.no_reframings,
            neighborhood=args.neighborhood,
        ),
        colormap=args.colormap,
    )

    if args.seeds:
        roots = run.seed_from_file(Path(args.seeds), limit=args.roots)
    elif args.family == "phoenix":
        roots = run.seed_from_phoenix_pool(limit=args.roots)
    else:
        roots = run.seed_from_julia_pool(limit=args.roots)

    if roots == 0:
        print("no roots: nothing to walk")
        return 1
    print(json.dumps(run.run(), indent=2))
    return 0


def modes(args: argparse.Namespace) -> int:
    """List the named colorings and what each one is for.

    Takes the parsed arguments and reads none of them, because every handler
    has the same shape and one exception is worse than one unused parameter.
    """
    del args
    for mode in engine.modes():
        print(f"{mode['name']:<22} {mode['identity']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fractal-wallpapers",
        description="ML-steered fractal wallpaper generator.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    fetch = subcommands.add_parser(
        "fetch-weights",
        help="download model weights from GitHub Releases into models/<head>/",
    )
    fetch.add_argument("--head", help="fetch only this head instead of all of them")
    fetch.set_defaults(handler=fetch_weights)

    draw = subcommands.add_parser(
        "render",
        help="render one location to a PNG through the engine",
        description=(
            "Render one location. Coordinates and family constants are given as decimal "
            "strings and are recorded exactly as written."
        ),
    )
    location_arguments(draw)
    draw.add_argument(
        "--out",
        default=str(Path("artifacts") / "render.png"),
        help="output PNG path (default: artifacts/render.png)",
    )
    draw.set_defaults(handler=render)

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
    dump.add_argument(
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
        "--out",
        default=str(Path("artifacts") / "recolored.png"),
        help="output PNG path (default: artifacts/recolored.png)",
    )
    again.set_defaults(handler=recolor)

    search = subcommands.add_parser(
        "walk",
        help="descend from seeds, keeping what survives the structural gates",
        description=(
            "Run one discovery walk. Roots come from the tracked seed pools for the "
            "dynamical families and from an explicit --seeds file for the parameter "
            "plane; there is no sampler behind either. Everything the walk sees — "
            "survivors and rejects alike — lands in walk.jsonl under --out-dir, with the "
            "gate that refused it or a thumbnail if none did."
        ),
    )
    search.add_argument(
        "--family",
        choices=["mandelbrot", "multibrot", "julia", "phoenix"],
        default="julia",
        help="which family to walk (default: julia, the one with a tracked c-pool)",
    )
    search.add_argument("--degree", type=int, default=2, help="exponent d, for multibrot and julia")
    search.add_argument(
        "--seeds",
        help="JSONL file of root locations: one {family, viewport} object per line",
    )
    search.add_argument("--roots", type=int, help="use only this many of the available roots")
    search.add_argument("--seed", type=int, default=0, help="run seed (default: 0)")
    search.add_argument("--batch", type=int, default=8, help="nodes expanded per batch")
    search.add_argument("--batches", type=int, default=4, help="batches to run")
    search.add_argument(
        "--root-expansions",
        type=int,
        default=12,
        help="expansions any one root may pay for, its reframings included",
    )
    search.add_argument("--candidates", type=int, default=4, help="candidates drawn per node")
    search.add_argument("--node-width", type=int, default=384, help="node render width in pixels")
    search.add_argument(
        "--probe",
        type=float,
        default=0.25,
        help="probability the reframing probe fires on an admission (default: 0.25)",
    )
    search.add_argument(
        "--no-reframings",
        action="store_true",
        help="expand only what the walk descends into; fire no reframing operators",
    )
    search.add_argument(
        "--neighborhood",
        action="store_true",
        help="also enumerate neighbouring nuclei (the expensive operator; off by default)",
    )
    search.add_argument(
        "--colormap", default="twilight_shifted", help="colormap for the steering thumbnails"
    )
    search.add_argument(
        "--out-dir",
        default=str(Path("artifacts") / "walk"),
        help="where the ledger and thumbnails go (default: artifacts/walk)",
    )
    search.set_defaults(handler=walk)

    listing = subcommands.add_parser("modes", help="list the named colorings")
    listing.set_defaults(handler=modes)

    return parser


def location_arguments(draw: argparse.ArgumentParser) -> None:
    """Add the arguments that name a location and how to color it.

    Shared by `render` and `dump-field`, which describe the same thing and
    differ only in how far down the pipeline they go.
    """
    draw.add_argument(
        "--family",
        choices=["mandelbrot", "multibrot", "julia", "phoenix"],
        default="mandelbrot",
        help="which recurrence to iterate (default: mandelbrot)",
    )
    draw.add_argument(
        "--degree",
        type=int,
        default=2,
        help="exponent d in z^d + c, for multibrot (3-5) and julia (2-5)",
    )
    draw.add_argument(
        "--c",
        nargs=2,
        metavar=("RE", "IM"),
        help="fixed constant c: required for julia, optional for phoenix",
    )
    draw.add_argument(
        "--p",
        nargs=2,
        metavar=("RE", "IM"),
        help="phoenix coefficient of z_(n-1) (default: -0.5 0)",
    )
    draw.add_argument(
        "--z-prev",
        nargs=2,
        metavar=("RE", "IM"),
        help="phoenix slice coordinate z_(-1) (default: 0 0)",
    )
    draw.add_argument("--center-re", help="view center, real part (default: the family's home)")
    draw.add_argument("--center-im", help="view center, imaginary part")
    draw.add_argument("--width", help="view width in plane units (default: 3.0)")
    draw.add_argument(
        "--resolution",
        nargs=2,
        type=int,
        metavar=("W", "H"),
        default=[1920, 1080],
        help="output size in pixels (default: 1920 1080)",
    )
    draw.add_argument(
        "--supersample",
        type=int,
        default=2,
        help="samples per output pixel, per axis (default: 2)",
    )
    draw.add_argument(
        "--mode",
        default="smooth",
        help="named coloring (default: smooth); see the modes subcommand",
    )
    draw.add_argument(
        "--colormap",
        default="twilight_shifted",
        help="colormap name under data/palettes (default: twilight_shifted)",
    )
    draw.add_argument(
        "--maxiter",
        type=int,
        help="iteration cap; omit to let the depth-aware policy choose",
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
