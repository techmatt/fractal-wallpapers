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
        "colormap": args.colormap,
        "colormap_dir": str(colormap_dir()),
        "output": str(resolve_output(args.out)),
    }
    if viewport:
        spec["viewport"] = viewport
    if args.maxiter is not None:
        spec["maxiter"] = args.maxiter
    return spec


def render(args: argparse.Namespace) -> int:
    """Render one image and print the engine's report."""
    if args.family == "julia" and args.c is None:
        print("--c is required for a julia render: it is half of the location's identity")
        return 1
    if args.family not in ("julia", "multibrot") and args.degree != 2:
        print(f"--degree does not apply to a {args.family} render")
        return 1

    report = engine.render_report(render_spec(args))
    print(json.dumps(report, indent=2))
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
        "--colormap",
        default="twilight_shifted",
        help="colormap name under data/palettes (default: twilight_shifted)",
    )
    draw.add_argument(
        "--maxiter",
        type=int,
        help="iteration cap; omit to let the depth-aware policy choose",
    )
    draw.add_argument(
        "--out",
        default=str(Path("artifacts") / "render.png"),
        help="output PNG path (default: artifacts/render.png)",
    )
    draw.set_defaults(handler=render)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
