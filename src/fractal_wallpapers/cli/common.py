"""Flag helpers, path helpers, and the defaults readers more than one group needs."""

from __future__ import annotations

import argparse
import json
import os
import re
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


# --------------------------------------------------------------------------- #
# What this command line writes its text as.
# --------------------------------------------------------------------------- #
def speak_utf8() -> None:
    """Make stdout and stderr UTF-8, on a Windows shell that would not be.

    **Redirected output on Windows is the ANSI code page, not the console's.** A
    help screen written to a file or a pipe here went out as cp1252, so every
    em-dash in this project's prose landed as the byte `0x97` and every reader
    that assumed UTF-8 — PowerShell 7, a browser, `git`, this repository's own
    files — showed it as a replacement character. Worse where the character is
    not in cp1252 at all: `curate derive-tau-h --help` and `label build --help`
    carry a `τ` and a `→`, and those did not mojibake, they raised
    `UnicodeEncodeError` and took the command down while argparse was printing.

    A console that a person is looking at never went through any of this — CPython
    writes to a Windows console with `WriteConsoleW` and the code page is not
    consulted — so this changes nothing an interactive user sees and fixes
    everything a pipe does.

    `errors="replace"` on top, because a stream that somebody has deliberately
    set to a narrow encoding is their decision and losing a dash is better than
    losing the screen. Guarded on `reconfigure` being there at all: pytest's
    capture object is a file-like that is not a `TextIOWrapper`.
    """
    import sys

    for stream in (sys.stdout, sys.stderr):
        encoding = (getattr(stream, "encoding", None) or "").lower().replace("-", "")
        if encoding in ("utf8", "utf8sig") or not hasattr(stream, "reconfigure"):
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            continue


# --------------------------------------------------------------------------- #
# `--help`, in two tiers.
# --------------------------------------------------------------------------- #
#: Print every `help=` whole rather than summarised. Read once, at parse time.
HELP_ENV = "FRACTAL_WALLPAPERS_HELP"

#: What the note at the foot of a trimmed `--help` says. It has to be there: a
#: reader who cannot tell that a screen is a summary is a reader who thinks the
#: flag's contract is one sentence long.
TRIMMED_NOTE = f"… marks help trimmed to its contract. {HELP_ENV}=full prints the reasoning whole."

#: A sentence ends at a period that follows a letter, a digit, a closing bracket
#: or a backtick and is followed by space or end of string. Written as a
#: lookbehind so it cannot fire inside `0.65`, `e.g`, `--n`, `1e-9` or a version
#: number, each of which is in a help string here and each of which a naive
#: `split(". ")` cuts in half. **Uppercase counts**: this project shouts a word
#: it means literally, so a sentence ends `must be expected to DELIVER.` and a
#: class of lowercase-only ran on past it into the next one.
_SENTENCE_END = re.compile(r"(?<=[A-Za-z0-9)`\]\"%])\.(?=\s|$)")

#: A sentence opening with one of these is the other half of the contract rather
#: than the reasoning, so the summary keeps it. `DEFAULT:` is this project's own
#: spelling and appears in 40-odd help strings; the lowercase forms catch the
#: parenthetical `(default 3)` shape written as its own sentence.
_CONTRACT_OPENERS = ("DEFAULT", "Default", "default")


def help_summary(text: str) -> str:
    """One help string trimmed to its contract: what it does, and the default.

    The two-tier rule. Every `help=` in this package is written as the contract
    first and the reasoning after — the ruling that set the flag, the date it
    changed, the measurement behind the number — and that reasoning is genuinely
    the best explanation of those flags anywhere, so it is kept. It is just not
    what a person reaching for `--help` is asking for. 798 help strings carry
    72,280 characters between them and `curate solve record --help` spent about
    forty lines on `--themed`, `--themed-cap` and `--themed-radius` alone, which
    is how a session came to need four `--help` invocations to find that
    `--no-render` is on `solve run` and not on `solve record`.

    Trimmed here rather than by rewriting all 798, because a rewrite either
    throws the reasoning away or moves it one file from the flag it is about, and
    because a second copy of a contract is a copy that drifts. [`TieredHelp`]
    applies this at format time and `FRACTAL_WALLPAPERS_HELP=full` turns it off,
    so both tiers come out of ONE string and no reader is stuck with the summary.

    `tests/test_help_tiers.py` holds every summary to being a real sentence and
    to fitting a screen, which is the guard that keeps a newly written help
    string's first sentence from being a paragraph.
    """
    flat = " ".join(text.split())
    end = _SENTENCE_END.search(flat)
    if end is None:
        return flat
    summary, rest = flat[: end.end()], flat[end.end() :].strip()
    if rest.startswith(_CONTRACT_OPENERS):
        following = _SENTENCE_END.search(rest)
        summary = f"{summary} {rest if following is None else rest[: following.end()]}"
    return summary


class TieredHelp(argparse.HelpFormatter):
    """The default formatter: `help=` summarised, with a footer saying so.

    Summarises in `_expand_help` and not in `_get_help_string`, because that is
    the hook that runs AFTER argparse's own `%(default)s` substitution — a
    summary taken before it would cut a `%`-escape in half and raise on the
    half. Truncation is recorded on the instance rather than returned, and the
    footer is added in `format_help`, so a screen with nothing trimmed on it
    carries no note.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._trimmed = False

    def _expand_help(self, action) -> str:
        expanded = super()._expand_help(action)
        if os.environ.get(HELP_ENV, "").lower() == "full":
            return expanded
        summary = help_summary(expanded)
        if len(summary) < len(" ".join(expanded.split())):
            self._trimmed = True
            return f"{summary} …"
        return summary

    def format_help(self) -> str:
        assembled = super().format_help()
        if not self._trimmed:
            return assembled
        return f"{assembled}\n{TRIMMED_NOTE}\n"


class Parser(argparse.ArgumentParser):
    """An `ArgumentParser` that formats its help in two tiers, and so do its kin.

    A subclass rather than `formatter_class=` at every site, because
    `add_subparsers` defaults `parser_class` to `type(self)`: one class named
    once at the root reaches all 48 `curate` steps and all 102 nested verbs,
    where the keyword argument would have to be repeated at every `add_parser`
    call and would be silently missing from the next one written.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("formatter_class", TieredHelp)
        super().__init__(*args, **kwargs)


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


def tag_flag(parser: FlagContainer) -> FlagContainer:
    """Which release a shipment names, on every `ship` verb there is.

    [`device_flag`]'s argument, and this one had already paid it: four heads ship
    and three of them wrote `default="weights-v1"` out by hand, so the day the
    scheme changed to one dated package the constant had to be found in four
    places and was found in two. One definition off [`roster.TAG`], which is also
    what `weights.json`'s rows and `fetch-weights --check`'s one-tag guard read,
    so a stage cannot name a release the manifest does not.
    """
    from fractal_wallpapers.models import roster

    parser.add_argument(
        "--tag",
        default=roster.TAG,
        help=f"the release tag to name (default {roster.TAG}, the one package every head "
        f"ships in since 2026-09-14). Dated rather than numbered: a head's version history "
        f"is its sha256 in models/weights.json and that file's git history, not a tag name. "
        f"A PUBLISHED TAG IS NEVER MOVED — shipping a head after this one is up means cutting "
        f"a new dated tag and repointing every row at it, never replacing an asset under a "
        f"name a clone has already trusted",
    )
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


# --------------------------------------------------------------------------- #
# The durability trio, shared by seven groups.
# --------------------------------------------------------------------------- #
def keeping_verbs(verbs, *, noun: str, force: str, order=("check", "save", "restore")):
    """`check`, `save`, `restore` — the three verbs every durable store shares.

    Seven groups spell them and only the noun and the order move, so they are
    written once here for the reason [`common.device_flag`] gives: a copied
    `add_argument` costs nothing until somebody edits one of them, and then
    `--help` carries a difference that reads like a difference in behaviour.

    A REAL subparser per verb rather than one `choices=` positional, which is
    what every one of them did before: a positional puts the whole group's flags
    on every verb, so `--force` was accepted by `check` and dropped on the floor,
    and `--help` at the group was every verb's flags at once with nothing saying
    which belonged to which.

    Takes the subparsers action rather than the parser, because three of the
    groups register another verb first — `spiral-scores` builds, `flatness` and
    `signatures` sweep — and the registration order is the `--help` surface.
    """
    for name in order:
        if name == "check":
            verbs.add_parser("check", help=f"check the live {noun} against the manifest")
        elif name == "save":
            verbs.add_parser("save", help="save a fresh copy and manifest")
        else:
            restoring = verbs.add_parser(
                "restore", help="restore the archived copy, counted before it is believed"
            )
            restoring.add_argument("--force", action="store_true", help=force)
    return verbs
