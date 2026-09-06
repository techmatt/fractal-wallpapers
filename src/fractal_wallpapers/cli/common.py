"""Flag helpers, path helpers, and the defaults readers more than one group needs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fractal_wallpapers import paths
from fractal_wallpapers.labeling.attributes import NAMES as ATTRIBUTE_NAMES
from fractal_wallpapers.labeling.finished import HEADS as FINISHED_HEADS
from fractal_wallpapers.labeling.gallery_grade import NAME as GALLERY_GRADE
from fractal_wallpapers.paths import (
    StorageRefusal,
    rehome,
    repo_root,
    tracked_name,
)

#: The mode a `render` that says nothing about coloring asks for. The engine has
#: the same default and would apply it to a spec with no `mode` key at all; it is
#: written here too so the spec a command built says what it rendered.
DEFAULT_MODE = "smooth"


def resolve_input(named: str) -> Path:
    """Resolve a path this invocation READS, against the repository and the tiers.

    The same resolution [`resolve_output`] does and **without its archive
    refusal**. That guard is about where new bytes land: writing to the archive
    puts fresh output behind a seek-bound disk and splits a subtree across both
    tiers. Neither is true of a read. A ledger that has been archived is still a
    ledger, and the whole point of the archive tier is that what lives there
    stays nameable — an input refused by an output guard is a subtree somebody
    has to restore before they may so much as read it.
    """
    path = Path(named)
    if path.is_absolute():
        return path
    resolved = rehome(path)
    return repo_root() / path if resolved is None else resolved


def resolve_output(out: str) -> Path:
    """Resolve an output path against the repository, not the shell's cwd.

    A relative `--out` means the same place whichever directory the command was
    run from, which is what keeps the default landing in the ignored
    `artifacts/` tree instead of scattering PNGs wherever the caller stood.

    "The ignored tree" is a setting, so a relative path that names it resolves
    through the tiers rather than against the checkout — a default of
    `artifacts/walk` follows its subtree to whichever disk that subtree is on,
    and every other relative path still means a place inside the repository.

    Writes land hot, which for a name nothing holds yet is what the resolution
    already says. The case worth refusing is a name that resolves to the
    *archive*: writing there would put new output behind a seek-bound disk and
    leave one subtree spread across both tiers, which is the state the whole
    mechanism exists to keep out of. Restoring first is the answer, so this says
    so rather than doing either.
    """
    path = Path(out)
    if path.is_absolute():
        return path
    resolved = rehome(path)
    if resolved is None:
        return repo_root() / path
    archive = paths.archive_root()
    if archive is not None and archive in resolved.parents:
        subtree = resolved.relative_to(archive).parts[0]
        raise StorageRefusal(
            f"{display_path(resolved)} is on the archive tier, and output does not get "
            f"written there: it would land behind slow storage and split that subtree "
            f"across both tiers. Bring it back first — "
            f"`fractal-wallpapers storage restore {subtree}` — or name somewhere else."
        )
    return resolved


def display_path(path: Path) -> str:
    """The counterpart to `resolve_output`: an absolute path said the short way.

    Printed paths are for a person to read and retype, and `artifacts/walk` is
    both shorter and more portable than the absolute path this process resolved
    it to. Anything outside the repository — or outside the artifacts tree — is
    printed whole, because shortening it would be a lie about where it is.

    This is `tracked_name`'s question asked out loud instead of into a record,
    and it is that function rather than a second copy of it: the two would
    disagree the first time one of them learned something.
    """
    return tracked_name(path)


def write_tracked_json(path: Path, document: dict) -> Path:
    """Write a JSON document that git tracks, with the line endings git will keep.

    Every other writer of a tracked file in this project pins `newline="\\n"`; the
    two table regenerators did not, and on Windows `write_text` translates each
    `\\n` to CRLF. `.gitattributes` normalizes that back on the way into the index,
    so the commit was always right — but the working tree afterwards held bytes
    that were not the committed bytes, and a regeneration therefore could not be
    checked by comparing the file to the one it replaced.
    """
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


#: What the four flag helpers below take. A parser, or one of its argument
#: groups: `add_argument` is the same call on either, and a command whose help
#: is grouped hands the group so the shared flag prints under a heading instead
#: of beside `-h`. Annotated rather than left implicit because the helpers are
#: called both ways now — `walk` and `harvest` hand a group, twenty-odd other
#: commands hand the parser.
FlagContainer = argparse.ArgumentParser | argparse._ArgumentGroup


def device_flag(parser: FlagContainer) -> FlagContainer:
    """Where a head runs, on every command that loads one.

    Thirty-two commands take this and every one of them meant the same thing, but
    it was written out thirty-two times and the sentence had already drifted two
    ways — half said `(default)` after `auto` and half did not, for one flag with
    one default. That is what a copied `add_argument` costs: nothing at all until
    somebody edits one of them, and then a difference in `--help` that reads like
    a difference in behaviour. One definition, like [`scoring_flags`] and
    [`ledger_flags`].
    """
    parser.add_argument("--device", default="auto", help="cuda, cpu, or auto (default)")
    return parser


def grace_flag(parser: FlagContainer) -> FlagContainer:
    """The expansion grace, on every command that walks.

    One definition for the same reason [`scoring_flags`] is one: a harvest that
    resumes a walk under a different depth policy writes two policies into one
    run seed's ledger.
    """
    from fractal_wallpapers.discovery.walk import Limits

    parser.add_argument(
        "--plane-grace-rungs",
        type=int,
        default=Limits.plane_grace_rungs,
        help=f"rungs below a parameter-plane seed root that the expansion junk floor does "
        f"not act on (default: {Limits.plane_grace_rungs}; 0 gates every rung). Booking "
        f"stays at the good floor, and dynamical roots are untouched",
    )
    return parser


def scoring_flags(parser: FlagContainer) -> FlagContainer:
    """The three flags every command that scores locations takes.

    One definition, because a walk and the harvest that wraps it have to be able
    to score the same way: a flag that exists on one and not the other is how a
    resumed run writes rows a different judge produced.
    """
    from fractal_wallpapers.discovery import scoring

    parser.add_argument(
        "--score-workers",
        type=int,
        default=scoring.DEFAULT_WORKERS,
        help=f"worker processes rendering views the head reads that nobody has drawn "
        f"(default: {scoring.DEFAULT_WORKERS}; 1 renders in this process). A walk draws "
        f"none — it scores the gate render — so this reaches a re-score alone",
    )
    device_flag(parser)
    parser.add_argument(
        "--no-scoring",
        action="store_true",
        help="run the null scorer: structural gates only, every row left unclassed and "
        "invisible to the standing deficit",
    )
    return parser


def reframing_default(name: str):
    """One of the reframing channel's constants, for a help string that cannot drift."""
    from fractal_wallpapers.discovery import reframing

    return getattr(reframing, name)


def plane_seed_default(name: str):
    """One of the plane-seed deriver's constants, for a help string that cannot drift."""
    from fractal_wallpapers.discovery import plane_seeds

    return getattr(plane_seeds, name)


def boundary_default(name: str):
    """One of the boundary draw's constants, for a help string that cannot drift."""
    from fractal_wallpapers.discovery import boundary

    return getattr(boundary, name)


def proven_default(name: str):
    """One of the proven channel's constants, for a help string that cannot drift."""
    from fractal_wallpapers.supply import proven

    return getattr(proven, name)


def novelty_default(name: str):
    """One of the novelty levers' constants, for a help string that cannot drift."""
    from fractal_wallpapers.supply import novelty

    return getattr(novelty, name)


def ledger_flags(parser: FlagContainer) -> FlagContainer:
    """The two ways an invocation declares which ledgers it is bound to.

    One definition, because every curation stage has to declare the binding the
    same way: a flag that exists on `run` and not on `score` is a run scored
    against a supply it did not release.
    """
    parser.add_argument(
        "--ledger",
        action="append",
        help="a walk ledger this invocation is bound to (repeatable). With more than one "
        "ledger present and none named, the command refuses and lists them",
    )
    parser.add_argument(
        "--harvest",
        action="append",
        metavar="DIR",
        help="a harvest run's --out-dir; its walk.jsonl is the binding (repeatable). The "
        "usual way to say 'the harvest that fed this run'",
    )
    return parser


def declared_ledgers(args: argparse.Namespace):
    """The ledgers this invocation names, or `None` if it named none.

    Resolution — including the refusal when nothing is named and there is more
    than one ledger to mean — belongs to `curation.binding` and happens where the
    binding is used, not here: a resumed run names nothing and is bound by its
    own plan.
    """
    from fractal_wallpapers.curation import binding

    harvests = getattr(args, "harvest", None) or []
    # Through `resolve_input`, which is the same tier resolution without the
    # archive refusal: a ledger and a harvest directory are things this
    # invocation reads, and an archived one is still readable.
    chosen = [resolve_input(p) for p in (args.ledger or [])]
    chosen += [binding.of_harvest(resolve_input(d)) for d in harvests]
    return chosen or None


def walk_default(name: str):
    """One of the walk's own limits, for a flag default that cannot drift from it."""
    from fractal_wallpapers.discovery.walk import Limits

    return getattr(Limits(), name)


def sampler_default(name: str):
    """One of the viewport sampler's constants, for a help string that cannot drift."""
    from fractal_wallpapers.discovery import viewport_sampler

    return getattr(viewport_sampler, name)


def build_scorer(args: argparse.Namespace, log=print):
    """The judge a walk consults, or `None` for the structural gates alone.

    One builder for both the walk and the harvest, because a scorer chosen two
    ways is a scorer that can differ between the run that fills a ledger and the
    run that continues it — and the ledger's `scorer` field would then name two
    things under one word.

    It reads at the **node regime**, which is the frame `expand` already draws
    every gate survivor at: the head is handed the picture the walk made rather
    than a second one of the same place. Whether that is legitimate is checked at
    the run's start, not here — see `discovery.identity`.
    """
    from fractal_wallpapers.discovery import scoring
    from fractal_wallpapers.models import tiles as tile_module

    if args.no_scoring:
        return None
    try:
        return scoring.LocationScorer(
            workers=args.score_workers,
            device=args.device,
            regime=tile_module.NODE_REGIME,
            log=log,
        )
    except Exception as refusal:  # noqa: BLE001 — an unshipped head is a refusal, not a crash
        raise SystemExit(
            f"the location head cannot be loaded, so nothing can score what this run finds: "
            f"{refusal!r}\nFetch the weights (`fractal-wallpapers fetch-weights`), or pass "
            f"--no-scoring to walk on the structural gates alone and leave every row unclassed."
        ) from refusal


def reframings_from(args: argparse.Namespace, *, enabled: bool = True):
    """Which reframing operators a run fires, defaults left alone unless told.

    `--neighborhood` and `--no-neighborhood` both default to `None` so that a
    run says nothing about the operator unless it was asked to: the shipped
    default lives on [`Reframings`], not here, and a flag no one passed must not
    quietly overrule it.
    """
    from fractal_wallpapers.discovery.walk import Reframings

    reframings = Reframings(enabled=enabled)
    if getattr(args, "neighborhood", None) is not None:
        reframings.neighborhood = bool(args.neighborhood)
    return reframings


def refine_limits(args: argparse.Namespace) -> dict:
    """The refine leg's two limits, defaults left alone unless the flags were passed.

    Both default to `None` at the parser so a run says nothing about the leg
    unless it was asked to: the shipped `k` lives on [`Limits`] and the margin
    lives on `curation.framing`, and a flag nobody typed must not quietly
    overrule either.
    """
    out: dict = {}
    if getattr(args, "refine_per_walk", None) is not None:
        out["refine_per_walk"] = max(0, int(args.refine_per_walk))
    if getattr(args, "refine_margin", None) is not None:
        out["refine_margin"] = float(args.refine_margin)
    return out


def location_arguments(draw: argparse.ArgumentParser) -> None:
    """Add the arguments that name a location and how to color it.

    Shared by `render` and `dump-field`, which describe the same thing and
    differ only in how far down the pipeline they go.

    Grouped, and the groups are made here rather than by each caller: fourteen
    flags in one block is a wall, and they answer three separate questions —
    which recurrence, which frame of the plane, and how the count that comes
    back becomes pixels. Made here, both commands describe a location the same
    way, and a caller that adds flags of its own adds its own group beside
    these rather than leaving them stranded in `options:`.
    """
    recurrence = draw.add_argument_group("the recurrence")
    frame = draw.add_argument_group("the frame")
    coloring = draw.add_argument_group(
        "the coloring",
        "the cap is here because what it bounds is the count the colormap reads",
    )
    recurrence.add_argument(
        "--family",
        choices=["mandelbrot", "multibrot", "julia", "phoenix"],
        default="mandelbrot",
        help="which recurrence to iterate (default: mandelbrot)",
    )
    recurrence.add_argument(
        "--degree",
        type=int,
        default=2,
        help="exponent d in z^d + c, for multibrot (3-5) and julia (2-5)",
    )
    recurrence.add_argument(
        "--c",
        nargs=2,
        metavar=("RE", "IM"),
        help="fixed constant c: required for julia, optional for phoenix",
    )
    recurrence.add_argument(
        "--p",
        nargs=2,
        metavar=("RE", "IM"),
        help="phoenix coefficient of z_(n-1) (default: -0.5 0)",
    )
    recurrence.add_argument(
        "--z-prev",
        nargs=2,
        metavar=("RE", "IM"),
        help="phoenix slice coordinate z_(-1) (default: 0 0)",
    )
    frame.add_argument("--center-re", help="view center, real part (default: the family's home)")
    frame.add_argument("--center-im", help="view center, imaginary part")
    frame.add_argument(
        "--width", help="view width in plane units (default: the family's home width)"
    )
    frame.add_argument(
        "--resolution",
        nargs=2,
        type=int,
        metavar=("W", "H"),
        default=[1920, 1080],
        help="output size in pixels (default: 1920 1080)",
    )
    frame.add_argument(
        "--supersample",
        type=int,
        default=2,
        help="samples per output pixel, per axis (default: 2)",
    )
    coloring.add_argument(
        "--mode",
        help=f"named coloring (default: {DEFAULT_MODE}); see the modes subcommand",
    )
    coloring.add_argument(
        "--discrete",
        nargs="?",
        type=int,
        const=0,
        metavar="CYCLE",
        help=(
            "color from the INTEGER iteration count instead of a named mode: flat bands, "
            "the picture the smooth count exists to fix. Give CYCLE to repeat the gradient "
            "every CYCLE iterations. A teaching mode — it is not in the catalog, so nothing "
            "that draws a mode can reach it"
        ),
    )
    coloring.add_argument(
        "--colormap",
        default="twilight_shifted",
        help="colormap name under data/palettes (default: twilight_shifted)",
    )
    coloring.add_argument(
        "--maxiter",
        type=int,
        help="iteration cap; omit to let the depth-aware policy choose",
    )
    # What every one of those flags means when nobody passes it, carried onto the
    # namespace. argparse fills a default in and does not remember that it did,
    # so a command handed a whole location record has no other way to tell a flag
    # that was typed from one that was not — and quietly ignoring a typed --width
    # because a record was also given is exactly the kind of picture nobody can
    # tell from the one they asked for.
    draw.set_defaults(
        flag_defaults={
            action.dest: action.default
            for action in draw._actions
            if action.dest not in ("help", "handler")
        }
    )


#: Every store a sheet may be cut for that is not the location corpus: the two
#: finished-render judges, the location-attribute stores, and the gallery-grade
#: store. One list, because a `--head` that accepted a store `label ingest` cannot
#: route to is a sheet that renders for an hour and then has nowhere to land.
NON_LOCATION_HEADS: tuple[str, ...] = tuple(
    sorted({*FINISHED_HEADS, *ATTRIBUTE_NAMES, GALLERY_GRADE})
)
