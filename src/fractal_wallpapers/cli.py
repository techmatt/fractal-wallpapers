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

from fractal_wallpapers import engine, paths
from fractal_wallpapers import schedule as schedule_module
from fractal_wallpapers.curation import manufacture as manufacture_module
from fractal_wallpapers.labeling import sheets as sheets_module
from fractal_wallpapers.labeling.finished import HEADS as FINISHED_HEADS
from fractal_wallpapers.palettes import clusters as palette_clusters
from fractal_wallpapers.palettes import color_mass as color_mass_module
from fractal_wallpapers.palettes import groups as palette_groups
from fractal_wallpapers.palettes import strip as palette_strip
from fractal_wallpapers.paths import (
    StorageRefusal,
    colormap_dir,
    rehome,
    repo_root,
    tracked_name,
)

WEIGHTS_MANIFEST = Path("models") / "weights.json"
RELEASE_URL = "https://github.com/techmatt/fractal-wallpapers/releases/download/{tag}/{asset}"

#: The mode a `render` that says nothing about coloring asks for. The engine has
#: the same default and would apply it to a spec with no `mode` key at all; it is
#: written here too so the spec a command built says what it rendered.
DEFAULT_MODE = "smooth"

#: The harvest's active-minute budget when neither `--minutes` nor `--finish-by`
#: says otherwise. Here rather than as the flag's `default=` because the two
#: flags are exclusive and `--minutes 0` is a real answer: a default filled in by
#: argparse could not be told from a caller who asked for it.
DEFAULT_HARVEST_MINUTES = 10.0

__all__ = ["build_parser", "main", "repo_root"]


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


#: What a manifest row has to say before a release can be cut from it. An asset
#: nobody can hash is a download nobody checked, and one that cannot name its
#: commit is a file nobody can rebuild.
REQUIRED_FIELDS = ("tag", "asset", "sha256", "source_commit", "provenance")


def check_weights(manifest: dict) -> int:
    """Read the manifest against the local tree: no network, no downloads.

    The dry run a release is cut after. It answers three questions the release
    itself cannot be un-cut to fix — is every head this project trains actually
    in here, does every row say the things a row has to say, and does the file
    each row names exist and hash to what the row claims.

    All of it is stdlib, and stays that way: the roster comes from the light
    module that owns it rather than from `ship`, which would drag the training
    stack into a check that reads JSON and hashes a file. A fresh clone runs
    this on `pip install -e .`, before it has any reason to own torch.
    """
    from fractal_wallpapers.models import roster

    heads = manifest.get("heads", {})
    complaints = []
    for head in roster.HEADS:
        if head not in heads:
            complaints.append(f"{head}: no manifest entry; a release cut now would omit it")
    for head, entry in sorted(heads.items()):
        missing = [field for field in REQUIRED_FIELDS if field not in entry]
        if missing:
            complaints.append(f"{head}: entry names no {', '.join(missing)}")
        asset = entry.get("asset")
        if not asset:
            continue
        path = repo_root() / "models" / head / asset
        if not path.is_file():
            complaints.append(f"{head}: {asset} is not on disk, so nothing was hashed")
            continue
        digest = sha256_of(path)
        size = path.stat().st_size
        if digest != entry.get("sha256"):
            complaints.append(f"{head}: {asset} hashes to {digest}, not {entry.get('sha256')}")
        elif "bytes" in entry and size != entry["bytes"]:
            complaints.append(f"{head}: {asset} is {size} bytes, not {entry['bytes']}")
        else:
            commit = str(entry.get("source_commit", ""))[:12] or "?"
            print(f"{head}: {asset} {size:>9} bytes  verified  from {commit}")
    for complaint in complaints:
        print(complaint)
    print(
        f"{len(heads)} of {len(roster.HEADS)} heads present; "
        f"{'release-complete' if not complaints else f'{len(complaints)} gap(s)'}"
    )
    return 1 if complaints else 0


def fetch_weights(args: argparse.Namespace) -> int:
    """Download each head's weights from GitHub Releases and verify its sha256."""
    manifest_path = repo_root() / WEIGHTS_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if args.check:
        return check_weights(manifest)
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


def score_locations(args: argparse.Namespace) -> int:
    """Score a list of locations through the shipped location head."""
    from fractal_wallpapers import locations
    from fractal_wallpapers.models import location_scoring
    from fractal_wallpapers.models import tiles as tile_module

    try:
        rows = locations.read(resolve_output(args.manifest))
    except locations.LocationError as refusal:
        print(refusal)
        return 1
    if args.limit is not None:
        rows = rows[: max(0, args.limit)]

    regime = tile_module.regime_of(args.regime)
    report = location_scoring.score(
        rows,
        out=resolve_output(args.out),
        regime=None if regime == tile_module.CANONICAL_REGIME else regime,
        device=args.device,
        workers=args.score_workers,
        views=resolve_output(args.views) if args.views else None,
    )
    print(json.dumps(report, indent=2))
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
        from fractal_wallpapers.discovery import plane_seeds

        return (
            f"a {args.family} walk has no sampler: an unscreened draw over the parameter "
            f"plane measured zero good locations in 144, so none is built. Its roots come "
            f"from the tracked plane seed pool — pass --seeds {plane_seeds.pool_path()} "
            f"(derive it with `fractal-wallpapers derive-plane-seeds --write` if it is not "
            f"there), or let the reframing operators find them from a walk that already "
            f"reached somewhere."
        )
    return None


def grace_flag(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
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


def scoring_flags(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
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
    parser.add_argument("--device", default="auto", help="cuda, cpu, or auto")
    parser.add_argument(
        "--no-scoring",
        action="store_true",
        help="run the null scorer: structural gates only, every row left unclassed and "
        "invisible to the standing deficit",
    )
    return parser


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


def ledger_flags(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
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


def score_parity(args: argparse.Namespace) -> int:
    """Score one batch of real locations both ways and compare."""
    from fractal_wallpapers.curation import binding, intake
    from fractal_wallpapers.discovery import scoring

    try:
        rows, _diagnostics = intake.gate_survivors(declared_ledgers(args))
    except binding.Unbound as refusal:
        print(refusal)
        return 1
    candidates = rows[: max(1, int(args.rows))]
    if not candidates:
        print(
            "no walk ledger holds a gate-surviving candidate, so there is nothing to score "
            "both ways. Run `fractal-wallpapers harvest` first."
        )
        return 1
    report = scoring.parity(candidates, args.score_workers, resolve_output(args.out_dir))
    print(json.dumps(report, indent=2))
    return 0 if report["held"] else 1


def derive_plane_seeds(args: argparse.Namespace) -> int:
    """Re-derive the parameter-plane seed pool; verify unless told to write."""
    from fractal_wallpapers.discovery import plane_seeds

    out = Path(args.out) if args.out else plane_seeds.pool_path()
    derived = plane_seeds.derive(
        columns=args.columns if args.columns is not None else plane_seeds.COLUMNS,
        per_partition=(
            args.per_partition if args.per_partition is not None else plane_seeds.PER_PARTITION
        ),
    )
    if args.write:
        plane_seeds.write(derived["rows"], out)
        print(json.dumps({"wrote": str(out), **derived["record"]}, indent=2))
        return 0
    verdict = plane_seeds.verify(derived["rows"], out)
    print(json.dumps({"verify": verdict, **derived["record"]}, indent=2))
    if not verdict["held"]:
        print(
            "\nthe tracked pool is not what this procedure produces. Nothing was written: "
            "re-run with --write if the procedure is the thing that changed."
        )
    return 0 if verdict["held"] else 1


def derive_proven_seeds(args: argparse.Namespace) -> int:
    """Print the proven-label seed set, and say how it compares to a file."""
    from fractal_wallpapers.supply import proven

    derived = proven.derive(
        tier_floor=args.tier_floor if args.tier_floor is not None else proven.TIER_FLOOR,
        partitions=tuple(args.partition or proven.SERVED),
    )
    out: dict = {"record": derived["record"]}
    if args.against:
        out["against"] = proven.compare(derived["rows"], resolve_output(args.against))
    if args.write:
        path = resolve_output(args.out)
        proven.write(derived["rows"], path)
        out["wrote"] = display_path(path)
    print(json.dumps(out, indent=2))
    lost = (out.get("against") or {}).get("lost", 0)
    if lost:
        print(
            f"\n{lost} location(s) the file holds are not in the derived set. A verdict was "
            "withdrawn, lowered, or is no longer readable — that is a thing to explain, not "
            "a thing to re-derive past."
        )
        return 1
    return 0


def build_proven_channel(args: argparse.Namespace, partitions):
    """The proven-label channel this run asked for by name, or `None`.

    Derived from the label store as it stands rather than read from a file: a
    keeper labelled this morning is a root this afternoon, and there is nothing
    to refresh. Off by default — the channel feeds on this project's own past
    output, so adopting it is a decision a run states.
    """
    from fractal_wallpapers.supply import proven

    if proven.CHANNEL not in (getattr(args, "root_channels", None) or ()):
        return None
    return proven.build(partitions=partitions)


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


def walk(args: argparse.Namespace) -> int:
    """Run one discovery walk and print what it found."""
    from fractal_wallpapers.discovery.walk import Gates, Limits, Policy, Walk

    complaint = refuse_impossible_walk(args)
    if complaint is not None:
        print(complaint)
        return 1

    run = Walk(
        scorer=build_scorer(args),
        out_dir=resolve_output(args.out_dir),
        seed=args.seed,
        limits=Limits(
            batch=args.batch,
            batches=args.batches,
            root_expansions=args.root_expansions,
            probe_probability=args.probe,
            plane_grace_rungs=args.plane_grace_rungs,
            **refine_limits(args),
        ),
        policy=Policy(candidates=args.candidates, node_width=args.node_width),
        gates=Gates(),
        reframings=reframings_from(args, enabled=not args.no_reframings),
        colormap=args.colormap,
        report_foci=args.foci,
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


def harvest_minutes(args: argparse.Namespace):
    """`(minutes, plan)` — the active-minute budget this leg is held to, and why.

    `--finish-by` is a *derivation* of `--minutes` rather than a second budget:
    the loop still stops on active minutes and nothing here paces it. What the
    plan buys is that the number was arrived at from a time somebody named, on
    the record, in terms a readout can subtract afterwards.
    """
    from fractal_wallpapers import schedule

    if args.finish_by is None:
        minutes = DEFAULT_HARVEST_MINUTES if args.minutes is None else args.minutes
        return minutes, None
    derived = schedule.plan(
        args.finish_by,
        args.release_slots,
        curation_attempts(args),
        renders_views=harvest_draws_views(args),
        release_workers=args.release_workers,
    )
    for line in derived.lines():
        print(f"[plan] {line}")
    return derived.active_minutes, derived


def curation_attempts(args: argparse.Namespace) -> int:
    """Colorize attempts the curation leg this night reserves for will actually plan.

    Derived through `curation.budget` rather than restated here, and derived from
    the shape the night will run the curation at — the release ceiling, the
    strange share, the modes each head draws. The reservation used to be `4n`
    times this module's own copies of those three, which was a restatement of
    curation's arithmetic and was pinned to it by the suite; it stopped being
    pinnable the moment the mode table became a parameter of a run.
    """
    from fractal_wallpapers.curation import budget

    modes = None if args.strange_modes is None else {budget.STRANGE: args.strange_modes}
    slots = budget.head_slots(args.release_slots, args.strange_share)
    wanted, _ = budget.head_attempts(slots, None, modes=budget.modes_of(modes))
    return sum(wanted.values())


def harvest_draws_views(args: argparse.Namespace) -> bool:
    """Whether this run will render views for its judge, or score the gate renders.

    The one thing that decides it is whether the walk's own gate render *is* the
    picture the head reads — `discovery.identity`'s claim, asked here of the same
    four settings the walk will assert it on a moment later. A run that fails that
    claim is refused when the walk is built, so answering `True` for it costs
    nothing and guessing the other way would silently pick the cheap ratio for a
    night that draws a view per survivor.

    A run with no scorer at all draws nothing either, and gets the same answer as
    one that scores what it drew: the ratio is about views rendered, not about
    whether anything was judged.
    """
    from fractal_wallpapers.discovery import identity
    from fractal_wallpapers.models import tiles as tile_module

    if args.no_scoring:
        return False
    try:
        identity.enforce(
            args.colormap, args.node_width, tile_module.NODE_REGIME, log=lambda *_: None
        )
    except identity.IdentityBroken:
        return True
    return False


def harvest(args: argparse.Namespace) -> int:
    """Run the production loop: keep finding material where it is scarcest."""
    from fractal_wallpapers.discovery.walk import Limits, Policy, Walk
    from fractal_wallpapers.supply import autopsy, ledgers, novelty, release_mix, saturation, twins
    from fractal_wallpapers.supply.census import stock_census
    from fractal_wallpapers.supply.harvest import Budget, Harvest
    from fractal_wallpapers.supply.partitions import ALL_PARTITIONS
    from fractal_wallpapers.supply.prices import load_table
    from fractal_wallpapers.supply.quota import Quota
    from fractal_wallpapers.supply.refill import Refill

    minutes, derived = harvest_minutes(args)
    run_dir = resolve_output(args.out_dir)
    limits = Limits(
        batch=args.batch,
        root_expansions=args.root_expansions,
        plane_grace_rungs=args.plane_grace_rungs,
        **refine_limits(args),
        # `None` and not `0`: zero is a real answer to "how many admissions may a
        # lineage book" and it is not the one the flag's zero means.
        lineage_admissions=args.lineage_cap if args.lineage_cap > 0 else None,
    )
    if args.probe is not None:
        limits.probe_probability = args.probe
    walk_run = Walk(
        out_dir=run_dir,
        seed=args.seed,
        limits=limits,
        policy=Policy(candidates=args.candidates, node_width=args.node_width),
        reframings=reframings_from(args),
        colormap=args.colormap,
        scorer=build_scorer(args),
        report_foci=args.foci,
    )
    # A run told which partitions to keep books for keeps them for those alone:
    # the census, the allocation, the refill census and the served mix all read
    # this list, so naming one partition is how a leg spends a whole clock there
    # rather than steering toward it and hoping.
    partitions = list(args.partition or ALL_PARTITIONS)
    # Found once, read by three builders. Each of them used to look the ledgers up
    # for itself, which on an archive root is the same directory walk three times
    # over — the whole of what `schedule.LEDGER_LOAD_SECONDS` had grown to reserve.
    ledger_files = ledgers.ledger_paths(
        root=resolve_output(args.ledgers), exclude=walk_run.ledger.path
    )
    print(f"[plan] ledgers: {len(ledger_files)} under {display_path(resolve_output(args.ledgers))}")
    # The protected exploration share, and the cross-run record of which lineages
    # have ever produced that decides who is in it. Built off the same ledger root
    # the saturation memory reads, minus this run's own file.
    exploration = (
        None
        if args.no_exploration
        else novelty.Exploration(
            lineages=novelty.build(paths=ledger_files),
            floor=args.exploration_floor,
            start=args.exploration_start,
            ema=args.exploration_ema,
        )
    )
    quota = Quota(
        partitions,
        run_dir,
        floor=args.floor,
        prices_config=load_table(Path(args.prices) if args.prices else None),
        census=stock_census(partitions, discount=args.discount),
        external=release_mix.externally_supplied(partitions),
        exploration=exploration,
    )
    # Primed before the first batch, off the same two legs of admitted stock the
    # census reads, and extended by whatever this run books. Its ledger is the
    # walk's, so what the channel accepted and what the c-spacing floor refused
    # land in the run's own record rather than only in a summary.
    twin_channel = (
        None if args.no_twins else twins.build(ledger=walk_run.ledger, ledger_paths=ledger_files)
    )
    refill = Refill(
        walk_run,
        low_water=args.low_water,
        cooldown=args.cooldown,
        share=args.refill_share,
        seeds=Path(args.seeds) if args.seeds else None,
        external=quota.external,
        partitions=partitions,
        twins=twin_channel,
        proven=build_proven_channel(args, partitions),
    )
    memory = None if args.no_saturation else saturation.build(paths=ledger_files)
    run = Harvest(
        walk_run,
        quota,
        budget=Budget(minutes=minutes, batches=args.batches),
        refill=refill,
        memory=memory,
        saturation_strength=0.0 if args.no_saturation else saturation.STRENGTH,
        discount_k=args.lineage_discount,
        discount_floor=args.lineage_discount_floor,
        partitions=partitions,
        finish_by=None if derived is None else derived.record(),
    )
    # Before the first batch, not in the readout. run10 opened with 39, 46 and 52
    # derived parameters in its three julia twins and 209 and 96 in the two
    # tracked `c`-pools, against 413 to 507 a parameter plane; all five ran dry
    # and the readout is where that surfaced, the following morning. What the
    # share can reach is a fact about the pools at launch, and it was readable
    # then.
    for line in refill.pool_lines():
        print(f"[plan] {line}")
    if run.resume():
        print(f"resumed at batch {run.batch} ({run.active_minutes:.2f} active minutes spent)")
    summary = run.run()
    sheet = autopsy.write(run_dir, summary)
    if sheet is not None:
        print(f"channel autopsy -> {display_path(sheet)}")
    print(json.dumps(summary, indent=2))
    return 0


def deep_roots(args: argparse.Namespace) -> int:
    """Fill the seats and print them, standing on none of them."""
    import random

    from fractal_wallpapers.deep import roots as roots_module
    from fractal_wallpapers.deep import run as deep_module

    seats, sourcing = roots_module.sourced(
        deep_module.DEFAULT_SEATS if args.seats is None else args.seats,
        random.Random(args.seed),
        newton_share=args.newton_share,
        anchors_per_family=args.anchors,
    )
    if args.out:
        path = resolve_output(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for seat in seats:
                handle.write(json.dumps(seat.record(), ensure_ascii=False) + "\n")
        print(f"{len(seats)} seat(s) -> {display_path(path)}")
    print(json.dumps({"seats": [seat.record() for seat in seats], "sourcing": sourcing}, indent=2))
    return 0 if seats else 1


def deep_walk(args: argparse.Namespace) -> int:
    """Source the seats, stand on them, and record everything that is seen."""
    from fractal_wallpapers.deep import run as deep_module

    limits = deep_module.Limits(
        # `seats` and `batches` stay `None` unless a flag said otherwise, which
        # is what lets the wall budget size them. A default filled in here would
        # out-rank the projection with a number nobody chose.
        seats=args.seats,
        newton_share=args.newton_share,
        anchors_per_family=deep_anchor_pool(args),
        batch=args.batch,
        batches=args.batches,
        root_expansions=args.root_expansions,
        lineage_admissions=args.lineage_cap if args.lineage_cap > 0 else None,
    )
    if args.reseat is not None:
        limits.reseat = bool(args.reseat)
    run = deep_module.Deep(
        out_dir=resolve_output(args.out_dir),
        seed=args.seed,
        limits=limits,
        wall_budget=args.wall_budget,
        evaluation_reserve=not args.no_evaluation_reserve,
        scorer=build_scorer(args),
        colormap=args.colormap,
        node_width=args.node_width,
    )
    if run.projection is not None:
        print(json.dumps({"projection": run.projection.record()}, indent=2))
        if run.seats_wanted < 1:
            print(
                f"the budget affords no seat: {args.wall_budget:.0f}s leaves "
                f"{run.projection.room:.0f}s usable against {run.projection.per_seat:.0f}s a seat"
            )
            return 1
    if not run.source():
        print("no seats: neither channel produced a nucleus this mode can frame")
        return 1
    print(json.dumps(run.run(), indent=2))
    return 0


def deep_anchor_pool(args: argparse.Namespace) -> int:
    """Anchors per family the Newton channel may draw on for this whole run.

    `--anchors` is a floor rather than the answer when a budget is in play. The
    flag's default is eight, which is 32 anchors over the four parameter planes;
    a projection at eight hours asks for a few hundred descents and would run the
    queues dry in its first round. So a budgeted run raises the pool to what its
    own projection needs, at `deep_run1`'s measured arrival rate, and the flag
    still wins whenever it is set higher.
    """
    import math

    from fractal_wallpapers.deep import budget as budget_module
    from fractal_wallpapers.deep import roots as roots_module
    from fractal_wallpapers.deep import run as deep_module

    if args.wall_budget is None:
        return args.anchors
    seats = args.seats
    if seats is None:
        seats = budget_module.project(
            args.wall_budget, evaluation=not args.no_evaluation_reserve
        ).seats
    # One anchor a family is a count of the families the tracked pool solved, read
    # rather than written down: the day a fifth parameter plane is seeded, the
    # pool this asks for divides by five without anything here being edited.
    families = max(1, len(roots_module.anchors(1)))
    wanted = math.ceil(
        max(0, int(seats)) * float(args.newton_share) * roots_module.DESCENTS_PER_SEAT / families
    )
    return max(args.anchors, wanted, deep_module.DEFAULT_SEATS)


def census(args: argparse.Namespace) -> int:
    """Print the standing deficit and the allocation it implies, running nothing.

    Three reads off one census, because the question anybody asks first is what
    the machine leg moved: the labels-only deficit as it was, the effective
    deficit as it now is, and the discounted currency that separates them. Both
    allocations are quoted at seed prices — a price table is a fact about a run,
    and this is not a run.
    """
    from fractal_wallpapers.supply import census as census_module
    from fractal_wallpapers.supply import release_mix
    from fractal_wallpapers.supply.allocation import allocate
    from fractal_wallpapers.supply.partitions import ALL_PARTITIONS
    from fractal_wallpapers.supply.prices import load_table

    partitions = list(ALL_PARTITIONS)
    stock_census = census_module.stock_census(partitions, discount=args.discount)
    ratios = release_mix.ratios(partitions)
    external = release_mix.externally_supplied(partitions)
    seed = load_table(Path(args.prices) if args.prices else None)["prices"]

    labels = stock_census.currency
    stock = stock_census.stock()
    labels_target, labels_anchor = census_module.targets(labels, partitions, ratios)
    labels_deficit = {p: max(0.0, labels_target[p] - float(labels.get(p, 0.0))) for p in partitions}
    target, anchor = census_module.targets(stock, partitions, ratios)
    deficit = {p: max(0.0, target[p] - float(stock.get(p, 0.0))) for p in partitions}

    labels_allocation = allocate(labels_deficit, seed, partitions, args.floor, external)
    allocation = allocate(deficit, seed, partitions, args.floor, external)
    print(
        json.dumps(
            {
                "currency": stock_census.summary(),
                "target_rule": census_module.TARGET_RULE,
                "ratio": ratios,
                "externally_supplied": sorted(external),
                "labels_only": {
                    "anchor": round(labels_anchor, 3),
                    "target": {p: round(labels_target[p], 3) for p in partitions},
                    "deficit": {p: round(labels_deficit[p], 3) for p in partitions},
                    "allocation_at_seed_prices": labels_allocation.summary(),
                },
                "with_machine_stock": {
                    "discount": stock_census.machine_leg().discount,
                    "anchor": round(anchor, 3),
                    "stock": {p: round(stock[p], 3) for p in partitions},
                    "target": {p: round(target[p], 3) for p in partitions},
                    "deficit": {p: round(deficit[p], 3) for p in partitions},
                    "allocation_at_seed_prices": allocation.summary(),
                },
                "deficit_delta": {p: round(deficit[p] - labels_deficit[p], 3) for p in partitions},
                "share_delta": {
                    p: round(allocation.share[p] - labels_allocation.share[p], 4)
                    for p in partitions
                },
            },
            indent=2,
        )
    )
    return 0


def derive_prices(args: argparse.Namespace) -> int:
    """Regenerate the cost-to-find seed table from finished runs."""
    from fractal_wallpapers.supply import prices as price_module
    from fractal_wallpapers.supply.partitions import ALL_PARTITIONS

    blocks, sources = [], []
    for name in args.run:
        run_dir = resolve_output(name)
        summary = run_dir / "summary.json"
        if not summary.is_file():
            # The summary is written when a run finishes, so its presence is what
            # says the run reached an end. A checkpoint holds the same counters
            # mid-flight and would price a partial population as a whole one.
            print(f"{summary} is missing - that run has not finished; state.json is not a")
            print("substitute, it would price a partial population as a whole one.")
            return 1
        document = json.loads(summary.read_text(encoding="utf-8"))
        cost = ((document.get("quota") or {}).get("cost")) or {}
        if not cost:
            print(f"{summary} carries no cost block - nothing to derive a price table from")
            return 1
        blocks.append(cost)
        # The table this derives is tracked, so the run it was derived from is
        # named as a tracked record names a place under the regenerable tree.
        sources.append({"name": run_dir.name, "path": tracked_name(run_dir)})

    try:
        table = price_module.derive(blocks, sources, ALL_PARTITIONS)
        if args.regularize:
            table = price_module.regularize(
                table, alpha=args.alpha, clamp=args.clamp, source=args.measured or ""
            )
    except price_module.PriceTableError as refusal:
        # Fail closed rather than fall back to the seed: a regenerated table that
        # is byte-identical to the flat seed reports itself as a measurement and
        # is not one, and afterwards nobody can tell the two apart.
        print(refusal)
        return 1
    out = (
        resolve_output(args.out)
        if args.out
        else (
            price_module.seed_table_path()
            if args.regularize
            else price_module.measured_table_path()
        )
    )
    if args.write:
        out.parent.mkdir(parents=True, exist_ok=True)
        # `newline="\n"` because this writes a TRACKED table: without it Windows
        # writes CRLF, `.gitattributes` normalizes it back to LF on the way into
        # the index, and every regeneration leaves a working tree whose bytes are
        # not the bytes that were committed.
        write_tracked_json(out, table)
        print(f"wrote {out}")
    else:
        print(json.dumps(table, indent=2))
        print("(dry run - pass --write to replace the shipped table)")
    return 0


def derive_tau_h(args: argparse.Namespace) -> int:
    """Re-derive the cheap cut from this repository's own walks."""
    from fractal_wallpapers.supply import tau_h as tau_module
    from fractal_wallpapers.supply.partitions import ALL_PARTITIONS

    rows = tau_module.rows_from_ledgers([Path(p) for p in args.ledger] if args.ledger else None)
    table = tau_module.artifact(rows, ALL_PARTITIONS, keep=args.keep)
    out = resolve_output(args.out) if args.out else tau_module.table_path()
    if args.write:
        out.parent.mkdir(parents=True, exist_ok=True)
        write_tracked_json(out, table)
        print(f"wrote {out}")
    else:
        print(json.dumps(table, indent=2))
        print("(dry run - pass --write to replace the shipped table)")
    return 0


def label_register(args: argparse.Namespace) -> int:
    """Register a batch's generation method, before it has any rows."""
    from fractal_wallpapers.labeling import finished, store
    from fractal_wallpapers.labeling import registry as registry_module

    registration = registry_module.Registration(
        batch=args.batch,
        method=args.method,
        score_unconditioned=args.score_unconditioned,
        anchored=args.anchored,
        eval_only=args.eval_only,
        why=args.why or "",
    )
    known = finished.registry(args.head) if args.head else store.registry()
    if args.batch in known:
        print(f"batch {args.batch!r} is already registered; a second row would restate it")
        return 1
    row = finished.register(args.head, registration) if args.head else store.register(registration)
    eligible = registry_module.registration_of(row).eval_eligible
    print(json.dumps({**row, "head": args.head or "location", "eval_eligible": eligible}, indent=2))
    return 0


def label_build(args: argparse.Namespace) -> int:
    """Cut a labeling sheet and render every unit of it."""
    from fractal_wallpapers.labeling import finished, sheets, store

    if args.head and not args.from_plan:
        print("--head names a finished-render judge, and those sheets are cut from --from-plan")
        return 1
    if args.reuse_renders and not args.head:
        print("--reuse-renders reads a finished-render cache, so it needs --head")
        return 1

    if args.head:
        units = sheets.units_from_plan(resolve_output(args.from_plan))
        source = sheets.finished_source(
            args.head,
            seed=args.seed,
            resolution=tuple(args.resolution),
            supersample=args.supersample,
            reuse_cache=args.reuse_renders,
            order_by=args.order_by,
        )
    else:
        if args.from_plan:
            units = sheets.units_from_location_plan(resolve_output(args.from_plan))
        elif args.from_ledger:
            units = sheets.units_from_ledger(
                resolve_output(args.from_ledger), admitted_only=args.admitted_only
            )
        else:
            units = sheets.units_from_batch(args.from_batch)
        # The same builder the walk and the harvest consult, so the judge that
        # prefills a correction sheet is the judge that scored the ledger it was
        # cut from — and `--no-scoring` is the one way to a blind page.
        source = sheets.location_source(
            scorer=build_scorer(args),
            resolution=tuple(args.resolution),
            supersample=args.supersample,
        )
    if args.limit:
        units = units[: args.limit]
    if not units:
        print("no units: there is nothing to judge")
        return 1

    # Every batch a row will LAND in, which on a revision sheet is the batch each
    # unit came out of and not the sheet's own name. Checked after the units are
    # read and before a pixel is rendered.
    known = finished.registry(args.head) if args.head else store.registry()
    unregistered = sorted({unit.get("batch") or args.batch for unit in units} - set(known))
    if unregistered:
        head = f" --head {args.head}" if args.head else ""
        print(f"not registered: {unregistered}; register a batch before its rows exist:")
        print(f"  fractal-wallpapers label register --batch {unregistered[0]} --method '...'{head}")
        return 1

    sheet = sheets.build(
        source,
        units,
        directory=resolve_output(args.out_dir),
        batch=args.batch,
        seed=args.seed,
        title=args.title,
    )
    print(json.dumps(sheet.manifest, indent=2))
    return 0


def sheet_identity(manifest: dict, units: int) -> str:
    """What a sheet is, said the one way both `label sheets` and `label serve` say it."""
    batch = manifest.get("batch") or "(no batch)"
    return f"{manifest.get('head', '?')} · {batch} · {units} units"


def label_sheets(args: argparse.Namespace) -> int:
    """Print every built sheet under a directory: where it is, and what it holds.

    A sheet's directory name is chosen by whoever cut it and need not be the
    batch inside it, so the only authority on what a directory holds is its own
    manifest. Without this, finding a sheet to serve means opening them by hand.
    """
    from fractal_wallpapers.labeling import sheets, store

    root = resolve_output(args.under)
    if not root.is_dir():
        print(f"{display_path(root)} is not a directory")
        return 1
    found = 0
    for manifest_path in sorted(root.rglob(sheets.MANIFEST_NAME)):
        directory = manifest_path.parent
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as unreadable:
            # One unreadable manifest is not a reason to hide the others.
            print(f"{display_path(directory)}  unreadable: {unreadable}")
            found += 1
            continue
        units = manifest.get("units")
        if units is None:
            units = sum(1 for _ in (directory / sheets.ROWS_NAME).open(encoding="utf-8"))
        print(f"{display_path(directory):34}  {sheet_identity(manifest, units)}")
        if args.drops:
            try:
                drop = display_path(store.export_path(manifest.get("head", ""), manifest["batch"]))
            except (store.LabelError, KeyError) as unnamed:
                # A sheet whose manifest cannot name a drop is worth listing anyway.
                drop = f"(none: {unnamed})"
            print(f"{'':34}  labels -> {drop}")
        found += 1
    if not found:
        print(f"no sheet under {display_path(root)}")
    return 0


def label_serve(args: argparse.Namespace) -> int:
    """Serve a built sheet to a browser on this machine."""
    from fractal_wallpapers.labeling import server, sheets, store

    directory = resolve_output(args.sheet)
    sheet = sheets.read(directory)  # refuse a directory that is not a sheet, before binding a port
    manifest = sheet.manifest
    # What a labeler actually needs to know before typing into the page: which
    # sheet this is, and where their verdicts will land when they save.
    drop = store.export_path(manifest["head"], manifest.get("batch", ""))
    banner = [
        sheet_identity(manifest, len(sheet.rows)),
        f"labels -> {display_path(drop)}",
    ]
    return server.serve(directory, host=args.host, port=args.port, banner=banner)


def label_ingest(args: argparse.Namespace) -> int:
    """Resolve a sheet's export into store rows, through the one writer."""
    from fractal_wallpapers.labeling import intake

    report = intake.run(
        sheet=resolve_output(args.sheet),
        labels=args.labels,
        labeler=args.labeler,
        write=args.write,
    )
    print(json.dumps(report, indent=2))
    return 0


def label_show(args: argparse.Namespace) -> int:
    """Print what the store currently says, resolved."""
    from collections import Counter

    from fractal_wallpapers.labeling import pins, store
    from fractal_wallpapers.labeling import registry as registry_module
    from fractal_wallpapers.labeling import split as split_module
    from fractal_wallpapers.supply.partitions import partition_of_family

    del args
    resolution = store.resolved()
    scored = resolution.scored()
    keys = pins.pinned()
    print(
        json.dumps(
            {
                "store": resolution.summary(),
                "registry": registry_module.summary(store.registry()),
                "scores": {
                    str(score): sum(1 for row in scored if row["score"] == score)
                    for score in store.SCORES
                },
                "partitions": dict(
                    sorted(Counter(partition_of_family(row["family"]) for row in scored).items())
                ),
                "batches": dict(sorted(Counter(row["batch"] for row in scored).items())),
                "eval_side": {"pinned_locations": len(keys), "recipe": split_module.recipe()},
            },
            indent=2,
        )
    )
    return 0


def label_split(args: argparse.Namespace) -> int:
    """Re-derive the train/evaluation split, keeping every pin that already exists."""
    from fractal_wallpapers.labeling import pins, store
    from fractal_wallpapers.labeling import split as split_module

    resolution = store.resolved()
    drawn = split_module.derive(
        resolution.scored(),
        known=store.registry(),
        seed=args.seed,
        share=args.share,
        pinned=pins.pinned(),
    )
    if args.write:
        members, recipe = split_module.write(drawn)
        print(f"wrote {members} and {recipe}")
    print(json.dumps(drawn.recipe(), indent=2))
    if not args.write:
        print("(dry run - pass --write to ship it)")
    return 0


def tiles_plan(args: argparse.Namespace) -> int:
    """Turn the label store into the population a tile build runs over."""
    from collections import Counter

    from fractal_wallpapers.labeling import store
    from fractal_wallpapers.models import tiles as tile_module

    population = tile_module.plan(store.resolved().scored(), seed=args.seed)
    plan_file, locations_file = tile_module.write_plan(population)
    pool = tile_module.palette_pool()
    print(
        json.dumps(
            {
                "locations": len(population),
                "seed": args.seed,
                "seed_tag": tile_module.SEED_TAG,
                "sides": dict(sorted(Counter(row["side"] for row in population).items())),
                "scores": dict(sorted(Counter(row["score"] for row in population).items())),
                "partitions": dict(sorted(Counter(row["partition"] for row in population).items())),
                "biased": sum(1 for row in population if row["biased"]),
                "groups": len({row["group"] for row in population}),
                "palettes": {
                    "draw": len(pool["draw"]),
                    "floor": pool["floor"],
                    "invariance_holdout": len(pool["invariance_holdout"]),
                },
                "wrote": [str(plan_file), str(locations_file)],
            },
            indent=2,
        )
    )
    return 0


def tile_regime(args: argparse.Namespace):
    """The regime a `tiles` subcommand was aimed at, from its two flags."""
    from fractal_wallpapers.models import tiles as tile_module

    size = str(args.tile).lower().split("x")
    if len(size) != 2 or not all(part.isdigit() for part in size):
        raise SystemExit(f"--tile takes WIDTHxHEIGHT, not {args.tile!r}")
    return tile_module.Regime(tile=(int(size[0]), int(size[1])), supersample=int(args.supersample))


def tiles_build(args: argparse.Namespace) -> int:
    """Render every tile of the plan, one iteration pass per location."""
    from fractal_wallpapers.models import tiles as tile_module

    regime = tile_regime(args)
    log = tile_module.build_log_path(regime)
    report = tile_module.build(limit=args.limit, log=log, regime=regime)
    record = {
        "schema": tile_module.SCHEMA,
        "plan": str(tile_module.plan_path()),
        "locations": str(tile_module.locations_path()),
        "log": str(log),
        "report": report,
    }
    tile_module.build_record_path(regime).write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    summary = {key: value for key, value in report.items() if key != "recipe"}
    summary["recipe"] = {
        key: value for key, value in report["recipe"].items() if key != "palette_pool"
    }
    summary["recipe"]["palette_pool"] = f"{len(report['recipe']['palette_pool'])} names"
    print(json.dumps(summary, indent=2))
    return 0


def renders_plan(args: argparse.Namespace) -> int:
    """Turn a finished-render store into the pictures a build has to make."""
    from collections import Counter

    from fractal_wallpapers.models import renders

    jobs = renders.plan(args.head, seed=args.seed)
    path = renders.write_plan(args.head, jobs, seed=args.seed)
    print(
        json.dumps(
            {
                "head": args.head,
                "pictures": len(jobs),
                "seed": args.seed,
                "locations": len({json.dumps([j["family"], j["viewport"]]) for j in jobs}),
                "batches": dict(sorted(Counter(job["batch"] for job in jobs).items())),
                "modes": dict(sorted(Counter(job["mode"] for job in jobs).items())),
                "scores": dict(sorted(Counter(job["score"] for job in jobs).items())),
                "wrote": str(path),
            },
            indent=2,
        )
    )
    return 0


def renders_build(args: argparse.Namespace) -> int:
    """Render every picture of the plan, skipping the ones already on disk."""
    from fractal_wallpapers.models import renders

    report = renders.build(args.head, limit=args.limit)
    renders.build_record_path(args.head).write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(report, indent=2))
    return 0


def renders_verify(args: argparse.Namespace) -> int:
    """Compare regenerated pictures against the ones the verdicts were cast on."""
    from fractal_wallpapers.models import renders

    try:
        report = renders.verify(Path(args.source), args.head, sample=args.sample, seed=args.seed)
    except renders.RenderCacheError as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    return 0


def judge_preregister(args: argparse.Namespace) -> int:
    """Write a finished-render judge's bar, before the head that it judges exists."""
    from fractal_wallpapers.models import finished_acceptance

    path = finished_acceptance.prereg_path(args.head)
    if path.is_file() and not args.force:
        print(f"{path} already exists. A bar rewritten after the numbers are in is not a bar;")
        print("pass --force only if no head has been trained against this one yet.")
        return 1
    try:
        bar = finished_acceptance.preregister(args.head, Path(args.source))
    except finished_acceptance.AcceptanceError as refusal:
        print(refusal)
        return 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bar, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(bar, indent=2))
    return 0


def judge_train(args: argparse.Namespace) -> int:
    """Train the finished-render judge on the render cache.

    `render` is the shipped judge and trains over both label stores pooled; the
    two superseded per-kind judges still train from here, because a superseded
    run has to stay reproducible for as long as its records are readable.
    """
    from fractal_wallpapers.models import finished_train, render_train

    if args.head == render_train.HEAD:
        try:
            record = render_train.run(
                device=args.device,
                epochs=args.epochs,
                seed=args.seed,
                run_name=args.run,
                only=args.only,
                per_kind=args.two_head,
                backbone=args.backbone,
            )
        except render_train.TrainingError as refusal:
            print(refusal)
            return 1
        print(json.dumps({k: v for k, v in record.items() if k != "history"}, indent=2))
        return 0
    try:
        record = finished_train.run(
            args.head,
            device=args.device,
            epochs=args.epochs,
            seed=args.seed,
            run_name=args.run,
        )
    except finished_train.TrainingError as refusal:
        print(refusal)
        return 1
    print(json.dumps({key: record[key] for key in record if key != "history"}, indent=2))
    return 0


def judge_score(args: argparse.Namespace) -> int:
    """Score a side of the judge's corpus through a trained checkpoint.

    `render` reads BOTH label stores, because one judge answers for both kinds and
    its blind sheets are one per kind. `--kind` narrows it to one of them.
    """
    from fractal_wallpapers.models import finished_scoring, render_train

    if args.head == render_train.HEAD:
        kinds = [args.kind] if args.kind else list(render_train.KINDS)
        try:
            for kind in kinds:
                print(
                    json.dumps(
                        render_train.score(
                            kind, which=args.which, device=args.device, run_name=args.run
                        ),
                        indent=2,
                    )
                )
        except render_train.TrainingError as refusal:
            print(refusal)
            return 1
        return 0
    print(
        json.dumps(
            finished_scoring.run(
                args.head,
                which=args.which,
                side=args.side,
                device=args.device,
                into=args.run,
            ),
            indent=2,
        )
    )
    return 0


def judge_accept(args: argparse.Namespace) -> int:
    """Read a trained judge against its pre-registered bar.

    `render` is read against the non-inferiority bar its own band was registered
    under, which is a different document from the two superseded heads' — see
    [`fractal_wallpapers.models.render_acceptance`].
    """
    from fractal_wallpapers.models import finished_acceptance, render_train

    if args.head == render_train.HEAD:
        from fractal_wallpapers.models import render_acceptance

        try:
            report = render_acceptance.read(runs=args.run or None)
        except render_acceptance.ComparisonError as refusal:
            print(refusal)
            return 1
        path = render_acceptance.comparison_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps(report, indent=2))
        return 0 if report["verdict"] != "FAIL" else 1

    try:
        report = finished_acceptance.read(args.head, runs=args.run or None)
    except finished_acceptance.AcceptanceError as refusal:
        print(refusal)
        return 1
    path = finished_acceptance.acceptance_path(args.head)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, indent=2))
    return 0 if report["verdict"] != "FAIL" else 1


def judge_ship(args: argparse.Namespace) -> int:
    """Stage a judge's half-precision artifact and its manifest entry."""
    from fractal_wallpapers.models import finished_acceptance, render_train, ship

    if args.head == render_train.HEAD:
        from fractal_wallpapers.models import render_acceptance

        verdict_path = render_acceptance.comparison_path()
        reading = "band_only_verdict"
    else:
        verdict_path = finished_acceptance.acceptance_path(args.head)
        reading = "verdict"
    if not verdict_path.is_file():
        print(f"{verdict_path} is missing: nothing has judged this head yet.")
        print("Run `fractal-wallpapers renders accept` first.")
        return 1
    report = json.loads(verdict_path.read_text(encoding="utf-8"))
    # The render judge is read BAND-ONLY, by Matt's standing ruling of 2026-08-23:
    # the per-seed conjunction runs one test per gated arm per seed and its
    # false-alarm size was never pre-stated, so it does not gate. The record
    # carries both readings and this is the one that ships.
    verdict = report.get("multiplicity", {}).get(reading, report["verdict"])
    if verdict == "FAIL" and not args.force:
        print(f"the acceptance read says {verdict}. Shipping a head that failed its own")
        print("pre-registered bar needs --force and a sentence about why.")
        return 1

    print(
        json.dumps(
            ship.stage(
                name=args.head, which=args.which, tag=args.tag, device=args.device, run=args.run
            ),
            indent=2,
        )
    )
    return 0


def judge_disagreements(args: argparse.Namespace) -> int:
    """Copy out the sheet rows the judge and a superseded head read most differently."""
    from fractal_wallpapers.models import render_acceptance

    try:
        report = render_acceptance.disagreements(
            run=args.run, per_kind=args.per_kind, out_dir=args.out_dir
        )
    except render_acceptance.ComparisonError as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    return 0


def judge_glance(args: argparse.Namespace) -> int:
    """Lay one batch's rows out under the candidate's ordering and the incumbent's."""
    from fractal_wallpapers.models import render_glance

    try:
        report = render_glance.write(
            batch=args.batch,
            run=args.run,
            path=resolve_output(args.out) if args.out else None,
            rows=args.rows if args.rows is not None else render_glance.ROWS,
            which=args.which,
            device=args.device,
        )
    except render_glance.GlanceError as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    return 0


def figure_score_to_decision(args: argparse.Namespace) -> int:
    """Draw one frame per outcome the judges' ladder has, plus their provenance."""
    from fractal_wallpapers.models import decisions

    try:
        if args.coverage:
            spread = decisions.coverage(decisions.held_out(args.head, args.run))
            print(json.dumps(spread, indent=2))
            return 0
        report = decisions.draw(
            args.family, resolve_output(args.out_dir) if args.out_dir else None, args.head, args.run
        )
    except decisions.DecisionError as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


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


def palettes_clusters(args: argparse.Namespace) -> int:
    """Regroup the library and rewrite the tracked clustering."""
    try:
        report = palette_clusters.run(count=args.clusters)
    except palette_clusters.ClusterError as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
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


def palette_extract(args: argparse.Namespace) -> int:
    """Vendor the real candidate sets a production colorize run recorded."""
    from fractal_wallpapers.models import palette_sets

    try:
        report = palette_sets.run(Path(args.source))
    except palette_sets.SetsError as refusal:
        print(refusal)
        return 1
    report["colormaps"].pop("names", None)
    print(json.dumps(report, indent=2))
    return 0


def palette_plan(args: argparse.Namespace) -> int:
    """Draw the distillation corpus: which places, which maps, in which order."""
    from fractal_wallpapers.models import palette_corpus

    try:
        rows = palette_corpus.draw(
            sets=args.sets,
            candidates=args.candidates,
            seed=args.seed,
            hard_share=args.hard_share,
        )
    except palette_corpus.CorpusError as refusal:
        print(refusal)
        return 1
    path = palette_corpus.write_plan(rows)
    from collections import Counter

    print(
        json.dumps(
            {
                "plan": str(path),
                "sets": len(rows),
                "candidates": sum(len(row["candidates"]) for row in rows),
                "per_partition": dict(sorted(Counter(r["partition"] for r in rows).items())),
                "seed": args.seed,
                "mix": palette_corpus.mix(rows),
            },
            indent=2,
        )
    )
    return 0


def palette_build(args: argparse.Namespace) -> int:
    """Render the candidate pictures, for the corpus, the real sets, or both."""
    from fractal_wallpapers.models import palette_corpus, palette_sets

    rows: list = []
    if args.which in ("corpus", "all"):
        rows.extend(palette_corpus.read_plan())
    if args.which in ("sets", "all"):
        rows.extend(palette_sets.read())
    print(json.dumps(palette_corpus.build(rows, limit=args.limit), indent=2))
    return 0


def palette_label(args: argparse.Namespace) -> int:
    """Ask the teacher about every candidate and write the machine-labeled rows."""
    from fractal_wallpapers.models import palette_corpus

    try:
        report = palette_corpus.label(Path(args.source), palette_corpus.read_plan())
    except (palette_corpus.CorpusError, FileNotFoundError) as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    return 0


def palette_preregister(args: argparse.Namespace) -> int:
    """Write the palette head's bar, before there is a head to judge against it."""
    from fractal_wallpapers.models import palette_acceptance

    path = palette_acceptance.prereg_path()
    if path.is_file() and not args.force:
        print(f"{path} already exists. A bar rewritten after the numbers are in is not a bar;")
        print("pass --force only if no head has been trained against this one yet.")
        return 1
    print(json.dumps(palette_acceptance.preregister(), indent=2))
    return 0


def palette_train_head(args: argparse.Namespace) -> int:
    """Distil one palette head from the teacher's labels."""
    from fractal_wallpapers.models import palette_train

    try:
        record = palette_train.run(
            device=args.device,
            epochs=args.epochs,
            seed=args.seed,
            run_name=args.run,
            listwise=args.listwise,
        )
    except palette_train.TrainingError as refusal:
        print(refusal)
        return 1
    print(json.dumps({key: record[key] for key in record if key != "history"}, indent=2))
    return 0


def palette_score(args: argparse.Namespace) -> int:
    """Score the real candidate sets through the student and through the teacher."""
    from fractal_wallpapers.models import palette_scoring

    print(
        json.dumps(
            palette_scoring.run(
                Path(args.source), which=args.which, device=args.device, into=args.run
            ),
            indent=2,
        )
    )
    return 0


def palette_accept(args: argparse.Namespace) -> int:
    """Read the distilled head against its pre-registered bar."""
    from fractal_wallpapers.models import palette_acceptance

    try:
        report = palette_acceptance.read(runs=args.run or None)
    except palette_acceptance.AcceptanceError as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    return 0 if report["verdict"] != "FAIL" else 1


def palette_ship(args: argparse.Namespace) -> int:
    """Stage the palette head's half-precision artifact and its manifest entry."""
    from fractal_wallpapers.models import palette_acceptance, ship

    verdict_path = palette_acceptance.acceptance_path()
    if not verdict_path.is_file():
        print(f"{verdict_path} is missing: nothing has judged this head yet.")
        print("Run `fractal-wallpapers palette accept` first.")
        return 1
    verdict = json.loads(verdict_path.read_text(encoding="utf-8"))["verdict"]
    if verdict == "FAIL" and not args.force:
        print(f"the acceptance read says {verdict}. Shipping a head that failed its own")
        print("pre-registered bar needs --force and a sentence about why.")
        return 1
    print(
        json.dumps(
            ship.stage(
                name="palette", which=args.which, tag=args.tag, device=args.device, run=args.run
            ),
            indent=2,
        )
    )
    return 0


def one_regime(named: str):
    """One regime, by the name its files carry."""
    from fractal_wallpapers.models import tiles as tile_module

    try:
        return tile_module.regime_of(named)
    except ValueError as unparsed:
        raise SystemExit(str(unparsed)) from None


def head_regimes(args: argparse.Namespace) -> tuple:
    """The regimes a `head` subcommand was aimed at, canonical first.

    Named as they appear in the files a build wrote — `640x360ss1` — with the
    canonical one spelled out in full rather than by the empty segment it elides
    to in a name. No flag means the canonical regime alone, which is what the
    shipped head trains and scores at.
    """
    from fractal_wallpapers.models import tiles as tile_module

    stated = list(args.regime or [])
    if not stated:
        return (tile_module.CANONICAL_REGIME,)
    try:
        drawn = tuple(dict.fromkeys(tile_module.regime_of(name) for name in stated))
    except ValueError as unparsed:
        raise SystemExit(str(unparsed)) from None
    if tile_module.CANONICAL_REGIME not in drawn:
        raise SystemExit(
            "the canonical regime has to be one of them: the selection slice, the deploy "
            "view and every score file are read at it. Add --regime 640x360ss2."
        )
    return (
        tile_module.CANONICAL_REGIME,
        *(regime for regime in drawn if regime != tile_module.CANONICAL_REGIME),
    )


def head_train(args: argparse.Namespace) -> int:
    """Train one head on the built tiles."""
    from fractal_wallpapers.models import train

    record = train.train(
        name=args.head,
        device=args.device,
        epochs=args.epochs,
        seed=args.seed,
        run=args.run,
        regimes=head_regimes(args),
        selection=args.selection,
    )
    print(json.dumps({key: record[key] for key in record if key != "history"}, indent=2))
    return 0


def head_score(args: argparse.Namespace) -> int:
    """Score one side of the build through a trained checkpoint."""
    from fractal_wallpapers.models import scoring

    print(
        json.dumps(
            scoring.run(
                name=args.head,
                which=args.which,
                side=args.side,
                device=args.device,
                into=args.run,
                regime=one_regime(args.regime),
            ),
            indent=2,
        )
    )
    return 0


def head_floor(args: argparse.Namespace) -> int:
    """Fit one finished-render head's release floor off its own labels."""
    from fractal_wallpapers.curation import floors
    from fractal_wallpapers.models import release_floor

    try:
        record = release_floor.run(args.head, device=args.device, resamples=args.bootstrap)
    except (release_floor.FloorFitError, floors.HeadStampMismatch, FileNotFoundError) as refusal:
        print(refusal)
        return 1
    print(json.dumps(record, indent=2))
    # A measurement, never a move: `curation.floors` is the only owner of a height
    # that acts, and putting this one there is somebody's decision.
    # Every MEASURED height is held to reproducing, not only the acting one. A
    # floor that is recorded and does not re-fit is a number nobody can check,
    # and whether it happens to gate today is a different question from whether
    # it is still true.
    standing = floors.MEASURED_RELEASE_FLOORS.get(args.head)
    if standing is not None:
        acting = args.head in floors.ACTING_RELEASE_BARS
        held = record["rounded_up_to_0_005"] == standing.value
        print(
            f"standing {'bar' if acting else 'floor (advisory)'} {standing.value:g} vs this "
            f"fit {record['rounded_up_to_0_005']:g} on the 0.005 grid "
            f"({record['rounded_up_3_places']:g} at three places): "
            f"{'REPRODUCED' if held else 'DOES NOT REPRODUCE'}"
        )
        if held and standing.head_sha256 != record["head_sha256"]:
            print(
                f"but the standing height is stamped {standing.head_sha256[:12]} and this "
                f"fit read {record['head_sha256'][:12]}: the height is right and the stamp "
                f"is stale. Restate it."
            )
            return 1
        return 0 if held else 1
    print(
        f"no measured floor on {args.head}. This is a reading, and wiring it into a "
        f"selection is a separate decision."
    )
    return 0


def head_audit(args: argparse.Namespace) -> int:
    """Read a run's clock against its own epochs, then re-score to settle it."""
    from fractal_wallpapers.models import audit

    report = audit.run(name=args.head, run_name=args.run, which=args.which, device=args.device)
    write_tracked_json(audit.audit_path(args.head, args.run), report)
    print(json.dumps(report, indent=2))
    return 0 if report["verdict"] == "REPRODUCED" else 1


def head_preregister(args: argparse.Namespace) -> int:
    """Write the bar, before the head that will be judged against it exists."""
    from fractal_wallpapers.models import acceptance

    path = acceptance.prereg_path(args.head)
    if path.is_file() and not args.force:
        print(f"{path} already exists. A bar rewritten after the numbers are in is not a bar;")
        print("pass --force only if no head has been trained against this one yet.")
        return 1
    bar = acceptance.preregister(args.head)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bar, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(bar, indent=2))
    return 0


def head_accept(args: argparse.Namespace) -> int:
    """Read a trained head against the pre-registered bar."""
    from fractal_wallpapers.models import acceptance

    report = acceptance.read(args.head, runs=args.run or None)
    path = acceptance.acceptance_path(args.head)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, indent=2))
    return 0 if report["verdict"] != "FAIL" else 1


def head_ship(args: argparse.Namespace) -> int:
    """Stage the half-precision artifact and its manifest entry."""
    from fractal_wallpapers.models import acceptance, ship

    verdict_path = acceptance.acceptance_path(args.head)
    if not verdict_path.is_file():
        print(f"{verdict_path} is missing: nothing has judged this head yet.")
        print("Run `fractal-wallpapers head accept` first.")
        return 1
    verdict = json.loads(verdict_path.read_text(encoding="utf-8"))["verdict"]
    if verdict == "FAIL" and not args.force:
        print(f"the acceptance read says {verdict}. Shipping a head that failed its own")
        print("pre-registered bar needs --force and a sentence about why.")
        return 1

    print(
        json.dumps(
            ship.stage(
                name=args.head,
                which=args.which,
                tag=args.tag,
                device=args.device,
                run=args.run,
            ),
            indent=2,
        )
    )
    return 0


def import_labels(args: argparse.Namespace) -> int:
    """Import the source project's location labels as flat rows."""
    from fractal_wallpapers.labeling import corpus_import

    try:
        report = corpus_import.run(Path(args.source), seed=args.seed, share=args.share)
    except corpus_import.CorpusImportError as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    return 0


def import_finished(args: argparse.Namespace) -> int:
    """Import the source project's finished-render corpora as flat rows."""
    from fractal_wallpapers.labeling import finished, finished_import

    heads = [args.head] if args.head else sorted(finished.HEADS)
    reports = {}
    for head in heads:
        try:
            reports[head] = finished_import.run(Path(args.source), head)
        except (finished_import.FinishedImportError, finished.FinishedError) as refusal:
            print(refusal)
            return 1
    print(json.dumps(reports, indent=2))
    return 0


def coloring_derive_band(args: argparse.Namespace) -> int:
    """Measure a reference set of finished wallpapers and derive the tone band."""
    from fractal_wallpapers.coloring import band

    try:
        record = band.derive(Path(args.source))
    except band.BandError as refusal:
        print(refusal)
        return 1
    if args.write:
        print(f"wrote {band.write(record)}")
    printable = {key: value for key, value in record.items() if key != "per_image"}
    print(json.dumps(printable, indent=2))
    if not args.write:
        print("(dry run - pass --write to replace the shipped band)")
    return 0


def coloring_show(args: argparse.Namespace) -> int:
    """Print the operator's switch and the band it is projecting onto."""
    from fractal_wallpapers.coloring import autolevel, band

    del args
    try:
        record = band.load()
    except band.BandError as refusal:
        print(refusal)
        return 1
    print(
        f"{autolevel.OPERATOR} · switch {'ON' if autolevel.enabled() else 'OFF'} "
        f"(default {autolevel.SWITCH_DEFAULT}, {autolevel.SWITCH_ENV}="
        f"{__import__('os').environ.get(autolevel.SWITCH_ENV)!r})"
    )
    print(
        f"band {record['_path']} · {record['n_images']} images · derived {record['derived']} "
        f"· sha256 {record['_sha256'][:16]}"
    )
    for name, edges in band.bands(record).items():
        print(f"  {name:<10} [{edges[0]:.4f}, {edges[1]:.4f}]")
    return 0


def curate_score(args: argparse.Namespace) -> int:
    """Read the harvest ledgers through the location head, into curation's sidecar."""
    from fractal_wallpapers.curation import binding, intake

    try:
        report = intake.score(
            declared_ledgers(args),
            device=args.device,
            limit=args.limit,
            keys=intake.read_keys(resolve_output(args.key_file)) if args.key_file else None,
        )
    except (binding.Unbound, intake.IntakeError) as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    return 0


def curate_sidecar(args: argparse.Namespace) -> int:
    """Record, check or restore the supply sidecar against its tracked manifest."""
    from fractal_wallpapers.curation import durability

    doing = {
        "save": lambda: durability.save(),
        "check": lambda: durability.check(),
        "restore": lambda: durability.restore(force=args.force),
    }[args.what]
    try:
        report = doing()
    except durability.DurableLost as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    # `check` is the one that answers a yes/no question, so it is the one with an
    # exit code worth reading. A short or missing sidecar is a build failure.
    if args.what == "check" and report.get("verdict") in {"short", "missing"}:
        return 1
    return 0


def curate_mass_sweep(args: argparse.Namespace) -> int:
    """Record, check or restore the colour-mass sweep log against its tracked manifest."""
    from fractal_wallpapers.curation import durability
    from fractal_wallpapers.palettes import color_mass

    doing = {
        "save": lambda: color_mass.save_sweep_log(),
        "check": lambda: color_mass.check_sweep_log(),
        "restore": lambda: color_mass.restore_sweep_log(force=args.force),
    }[args.what]
    try:
        report = doing()
    except durability.DurableLost as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    # `missing` is not a failure here the way it is for the sidecar: the log is
    # archived on purpose and a checkout with no local copy is the resting state.
    # `short` still is — a truncated log would cut a different map.
    if args.what == "check" and report.get("verdict") == "short":
        return 1
    return 0


def curate_on_demand(args: argparse.Namespace) -> int:
    """Reconcile a pass's on-demand log and its gate store. Records only."""
    from fractal_wallpapers.curation import gallery as gallery_module

    try:
        report = gallery_module.reconcile_on_demand(
            args.pass_id,
            dry_run=args.dry_run,
            log=(lambda _line: None) if args.quiet else print,
        )
    except gallery_module.PassRefused as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    return 0


def curate_redraw(args: argparse.Namespace) -> int:
    """Re-render every stale location view and amend the score read off it."""
    from fractal_wallpapers import engine_fingerprint
    from fractal_wallpapers.curation import amend

    try:
        report = amend.refresh(device=args.device, limit=args.limit, resume=not args.no_resume)
    except (amend.AmendError, engine_fingerprint.FingerprintError) as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    return 0


def curate_draw(args: argparse.Namespace) -> int:
    """Take step 4's draw over the current pool and print what it chose."""
    from fractal_wallpapers.curation import amend, gallery, intake

    try:
        report = gallery.dry_draw(
            n=args.n,
            radius=args.radius,
            quality_weight=args.quality_weight,
            strange_share=args.strange_share,
            draw_seed=args.draw_seed,
            top_k=args.draw_top_k,
            amended=not args.no_amended,
        )
    except (gallery.PassRefused, intake.IntakeError, amend.AmendError) as refusal:
        print(refusal)
        return 1
    if args.out:
        where = resolve_output(args.out)
        where.parent.mkdir(parents=True, exist_ok=True)
        where.write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n"
        )
        print(f"wrote {where}")
    print(json.dumps({key: value for key, value in report.items() if key != "chosen"}, indent=2))
    return 0


def curate_embed(args: argparse.Namespace) -> int:
    """Embed every admitted location the neutral-render store does not hold yet."""
    from fractal_wallpapers.curation import embeddings, neutral

    try:
        report = embeddings.build(
            limit=args.limit,
            device=args.device,
            sample=args.sample,
            seed=args.seed,
            unit_seconds=args.unit_seconds,
        )
    except (embeddings.StoreRefused, neutral.NeutralError) as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    # A store short of its population is a gallery pass that silently cannot
    # choose the locations it is missing, so the count is the exit code.
    return 0 if report["complete"] else 1


def curate_embeddings(args: argparse.Namespace) -> int:
    """Record, check or restore the embedding store against its tracked manifest."""
    from fractal_wallpapers.curation import durability, embeddings

    which = embeddings.store()
    doing = {
        "save": lambda: durability.save(which),
        "check": lambda: durability.check(which),
        "restore": lambda: durability.restore(which, force=args.force),
    }[args.what]
    try:
        report = doing()
    except durability.DurableLost as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    if args.what == "check" and report.get("verdict") in {"short", "missing"}:
        return 1
    return 0


def curate_neighbours(args: argparse.Namespace) -> int:
    """The cheap sanity read: nearest neighbours by cosine, with their pictures."""
    from fractal_wallpapers.curation import embeddings

    try:
        report = embeddings.neighbours(k=args.k, sample=args.sample, seed=args.seed)
    except embeddings.StoreRefused as refusal:
        print(refusal)
        return 1
    print(f"{report['rows']:,} embedded locations; pictures under {report['pictures']}")
    spread = report["background"]
    print(
        f"background cosine over {spread['pairs']:,} random pairs: "
        f"min {spread['min']:.3f}, p01 {spread['p01']:.3f}, median {spread['median']:.3f}, "
        f"p99 {spread['p99']:.3f}, max {spread['max']:.3f}"
    )
    for cell in report["sample"]:
        print(f"\n{cell['partition']:<18} {cell['picture']}  {cell['key']}")
        for near in cell["nearest"]:
            print(
                f"  {near['cosine']:.4f}  {near['partition']:<18} {near['picture']}  {near['key']}"
            )
    return 0


def curate_reach(args: argparse.Namespace) -> int:
    """Which judged locations the gallery pass cannot select, and why."""
    from fractal_wallpapers.curation import embeddings, intake

    pool = embeddings.judged_pool()
    report = embeddings.unreachable(pool)
    if args.write:
        where = resolve_output(args.write)
        cell = report["absent_from_the_sidecar"]
        rows = intake.key_manifest(
            {"key": key, "partition": pool.get(key, "")} for key in cell["keys"]
        )
        where.parent.mkdir(parents=True, exist_ok=True)
        with where.open("w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"wrote {len(rows)} unreachable key(s) to {display_path(where)}")
    print(
        f"{report['judged']} judged locations; {report['admitted']} are in the admitted "
        f"population the gallery pass selects over"
    )
    for cause in ("below_the_junk_floor", "absent_from_the_sidecar"):
        cell = report[cause]
        print(f"{cell['count']:>5}  {cause.replace('_', ' ')}")
        if args.keys:
            for key in cell["keys"]:
                print(f"       {pool.get(key, '?'):<18} {key}")
    return 0


def curate_ledgers(args: argparse.Namespace) -> int:
    """Which walk ledger each released row names, and whether it still resolves."""
    from fractal_wallpapers.curation import durability

    report = durability.pool_ledgers()
    for cell in report["ledgers"]:
        where = f"{cell['tier']} tier" if cell["resolves"] else "NOT FOUND"
        print(f"{cell['rows']:>6}  {cell['ledger']:<44}  {where}  {','.join(cell['runs'])}")
    print(
        f"{report['pool_rows']:,} released rows name {report['ledgers_named']} ledger(s); "
        f"{report['ledgers_absent']} do not resolve, holding "
        f"{report['rows_on_absent_ledgers']:,} row(s)"
    )
    if args.write:
        write_tracked_json(durability.provenance_path(), report)
        print(f"wrote {display_path(durability.provenance_path())}")
    return 0


def curate_rescore(args: argparse.Namespace) -> int:
    """Read every candidate the pool holds through today's finished-render heads."""
    from fractal_wallpapers.curation import floors, rescore

    try:
        report = rescore.run(device=args.device)
    except (rescore.RescoreError, floors.HeadStampMismatch) as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    return 0


def drawn_modes(args: argparse.Namespace):
    """The mode table this invocation asks for, or `None` for curation's own.

    Only the strange judge's count is on the command line: the smooth judge owns
    one coloring, so a second draw at a location would render the same picture,
    and a table with a knob for it would be a knob nobody may turn.
    """
    from fractal_wallpapers.curation import budget

    if args.strange_modes is None:
        return None
    return {budget.SMOOTH: 1, budget.STRANGE: args.strange_modes}


def curate_plan(args: argparse.Namespace) -> int:
    """Print the offer and the budget it implies, making no picture."""
    from fractal_wallpapers.curation import binding, budget, floors, intake

    try:
        offer, supply = intake.ranked(declared_ledgers(args))
    except (binding.Unbound, intake.IntakeError) as refusal:
        print(refusal)
        return 1
    claims = intake.guaranteed(supply)
    modes = budget.modes_of(drawn_modes(args))
    plan, record = budget.plan(
        offer,
        args.n,
        args.strange_share,
        budget=args.attempts,
        guarantees=claims,
        modes=modes,
    )
    print(
        json.dumps(
            {
                "cuts": floors.summary(modes),
                "supply": supply,
                "lines": intake.supply_lines(supply),
                "release_caps": intake.release_caps(offer),
                "guaranteed": claims,
                "budget": record,
                "attempts": [
                    {"head": a.head, "partition": a.partition, "rank": a.rank} for a in plan
                ],
            },
            indent=2,
        )
    )
    return 0


def curate_run(args: argparse.Namespace) -> int:
    """Make a release: colorize, select, render at full resolution, record it all."""
    from fractal_wallpapers.curation import binding, durability, intake, records
    from fractal_wallpapers.curation import run as run_module
    from fractal_wallpapers.deep import run as deep_run

    try:
        summary = run_module.curate(
            run=args.resume or args.run,
            n=args.n,
            seed=args.seed,
            strange_share=args.strange_share,
            modes=drawn_modes(args),
            attempts=args.attempts,
            workers=args.workers,
            ephemeral=args.ephemeral,
            ledgers=declared_ledgers(args),
            device=args.device,
            skip_release=args.skip_release,
            wall_budget=args.wall_budget,
            ceilings=deep_run.HUNG_CEILING if args.deep else None,
            resume=bool(args.resume),
        )
    except (
        binding.Unbound,
        durability.DurableLost,
        intake.IntakeError,
        records.NotIsolated,
        run_module.RunRefused,
    ) as refusal:
        print(refusal)
        return 1
    print(json.dumps(summary, indent=2))
    # A run that cannot balance its plan against what it made has shipped
    # pictures and lost track of which, and that is a failure whatever the
    # release looks like.
    return 0 if summary["reconciliation"]["holds"] else 1


def curate_gallery(args: argparse.Namespace) -> int:
    """One gallery pass: choose N wallpapers over the whole pool, and render them."""
    from fractal_wallpapers.curation import (
        durability,
        embeddings,
        floors,
        gallery,
        gallery_store,
    )

    if args.migrate:
        if not args.pass_id:
            print(
                "--migrate acts on one named pass, so it needs --pass. There is no ordinal to "
                "guess: a pass that has never run has nothing in the old layout to move."
            )
            return 1
        try:
            print(json.dumps(gallery_store.migrate(args.pass_id), indent=2))
        except durability.DurableLost as refusal:
            print(refusal)
            return 1
        return 0

    from fractal_wallpapers.curation import ceiling as ceiling_module
    from fractal_wallpapers.curation import release as release_module

    try:
        regime = release_module.regime_of(args.release_regime)
    except ValueError as refusal:
        print(refusal)
        return 1

    try:
        targets = dict(ceiling_module.parse_target(text) for text in (args.target or []))
    except ceiling_module.TargetRefused as refusal:
        print(refusal)
        return 1

    try:
        record = gallery.run(
            pass_id=args.pass_id,
            n=args.n,
            radius=args.radius,
            quality_weight=args.quality_weight,
            strange_share=args.strange_share,
            attempts=args.attempts,
            reseat=args.reseat,
            no_attempts=args.no_attempts,
            full_size=not args.no_full_size,
            regime=regime,
            refine=not args.no_refine,
            margin=args.refine_margin,
            seed=args.seed,
            draw_seed=args.draw_seed,
            draw_top_k=args.draw_top_k,
            targets=targets,
            workers=args.workers,
            device=args.device,
        )
    except (
        ceiling_module.TargetRefused,
        gallery.PassRefused,
        gallery_store.LayoutRefused,
        durability.DurableLost,
        embeddings.StoreRefused,
        floors.HeadStampMismatch,
    ) as refusal:
        print(refusal)
        return 1
    print_gallery(record)
    return 0


def print_gallery(record: dict) -> None:
    """The pass's numbers, the retro table, and where the two sheets landed.

    The pass record is written whole and is far too long to read on a terminal —
    fifty slots with their neighbourhoods on them — so what is printed here is the
    three things a person acts on: whether the radius is set right, which cells the
    pool could not fill, and where to look at the pictures.
    """
    plan, seating = record["plan"], record["seating"]
    print(
        f"\ngallery {record['pass']}: {seating['filled']}/{seating['slots']} slot(s) filled "
        f"of {plan['requested']} asked for, in {record['seconds']:.0f}s"
    )
    print(
        f"  radius {plan['radius']:g} cosine, quality weight {plan['quality_weight']:g}: "
        f"{record['config']['quality_weight_form']}"
    )
    # The seed, always, and whether it was given: a pass that drew its own is
    # re-runnable only from the number printed here and written to the record.
    # Tolerant of a record written before the draw took a seed, because
    # `read_pass` puts any pass back together and this prints what it finds.
    config = record["config"]
    if config.get("draw_seed") is not None:
        print(
            f"  draw seed {config['draw_seed']} "
            f"({'given' if config.get('draw_seed_given') else 'drawn'}), first pick out of "
            f"each partition's top {config.get('draw_top_k')} - re-run it with "
            f"--draw-seed {config['draw_seed']}"
        )
    pool = record.get("pool") or {}
    print(
        f"  {pool.get('pass_candidates', 0)} candidate(s) of this pass's own making seated "
        f"against; {pool.get('standing_rows', 0)} standing pool row(s) not seatable - "
        f"candidates are per-pass, locations are not"
    )

    print("\nRETRO TABLE - the nearest chosen pairs, overall")
    for cell in plan["retro"]["overall"]:
        print(f"  {cell['cosine_distance']:.4f}  {cell['a']['partition']:<18} {cell['a']['key']}")
        print(f"  {'':>6}  {cell['b']['partition']:<18} {cell['b']['key']}")
    for name, table in sorted(plan["retro"]["by_partition"].items()):
        if not table:
            continue
        print(f"\nRETRO TABLE - {name}")
        for cell in table:
            print(f"  {cell['cosine_distance']:.4f}  {cell['a']['key']}")
            print(f"  {'':>6}  {cell['b']['key']}")

    print("\nSLOTS - filled, unfilled, and why")
    for name, cell in sorted(seating["by_partition_head"].items()):
        why = ", ".join(f"{count} {reason}" for reason, count in sorted(cell["reasons"].items()))
        print(
            f"  {name:<34} {cell['filled']:>3}/{cell['slots']:<3} filled"
            + (f"  ({why})" if why else "")
        )

    # What the re-seat loop recovered. Printed as its own block because it is the
    # one number that says whether an unfilled slot is a fact about the pool or a
    # fact about where one draw happened to look.
    loop = seating.get("reseat") or {}
    if loop:
        by_try = ", ".join(
            f"{count} on try {number}" for number, count in sorted(loop["filled_on_try"].items())
        )
        print(
            f"\nRE-SEAT: {loop['recovered']} slot(s) filled on a neighbourhood the first draw "
            f"did not give them, {loop['allowed']} tries allowed"
        )
        print(f"  {by_try}")
        if loop["unfilled"]:
            print(
                f"  {loop['unfilled']} still unfilled after "
                f"{loop['unfilled_tries']} neighbourhood(s) each"
                + (
                    f"; {loop['exhausted']} ran their partition's draw out"
                    if loop["exhausted"]
                    else ""
                )
            )

    refine = record.get("refine") or {}
    if refine.get("locations"):
        widths = ", ".join(f"x{name}: {count}" for name, count in refine["chosen_width"].items())
        moves = ", ".join(f"{name}: {count}" for name, count in refine["chosen_move"].items())
        gain = refine.get("gain_adopted") or {}
        print(
            f"\nREFINE: {refine['adopted']}/{refine['locations']} location(s) took a new framing "
            f"at margin {refine['margin']:g} ({refine['adopted_share'] * 100:.1f}%), "
            f"{refine['frames']} frame(s) in {refine['seconds']:.0f}s "
            f"({refine['seconds_per_location']:.2f}s a location)"
        )
        if widths:
            print(f"  width {widths}   move {moves}")
        if gain:
            print(
                f"  gain where adopted, nats of log-odds on P(>=4): median {gain['median']:.2f}, "
                f"q25 {gain['q25']:.2f}, q75 {gain['q75']:.2f}, max {gain['max']:.2f}"
            )
        refused = ", ".join(f"{count} {name}" for name, count in refine["refused"].items())
        if refused:
            print(f"  kept the recorded framing: {refused}")
        agreement = refine.get("sidecar_agreement") or {}
        if agreement.get("compared"):
            print(
                f"  the scan's read of the recorded framing against the sidecar's: "
                f"{agreement['exact']}/{agreement['compared']} exact, "
                f"largest gap {agreement['max_abs_delta_p_ge4']:g}"
            )
    elif not refine.get("on", True):
        print("\nREFINE: off (--no-refine); every attempt is framed where the pool records it")

    attempts, rendered = record["attempts"], record["render"]
    print(
        f"\nattempts: {attempts.get('made', 0)} made, {attempts.get('resumed', 0)} resumed, "
        f"{attempts.get('failed', 0)} failed of {attempts.get('planned', 0)} planned"
        + (
            f"; {attempts['seconds_per_attempt']:.2f}s each"
            if attempts.get("seconds_per_attempt")
            else ""
        )
        + (
            f"; {attempts['dropped_candidate_jpegs']:,} palette-candidate JPEG(s) dropped"
            if attempts.get("dropped_candidate_jpegs")
            else ""
        )
    )
    if rendered.get("skipped"):
        print(
            f"full size: SKIPPED ({rendered['skipped']}) — "
            f"{rendered['counts']['not_started']} seat(s) recorded `unrendered`, judged off "
            f"their candidate renders. Re-run this --pass without the flag to make them."
        )
    else:
        from fractal_wallpapers.curation import release as release_module

        made = release_module.regime_from_geometry(rendered.get("geometry"))
        print(
            f"full size: {rendered['counts']['made']} rendered, {rendered['counts']['resumed']} "
            f"reused, {rendered['counts']['failed']} failed"
            + (f" at {made.spelled}" if made is not None else "")
            + (
                f"; {rendered['seconds_per_full_size']:.1f}s each"
                if rendered.get("seconds_per_full_size")
                else ""
            )
        )
    store = record["records"]["attempts"]
    print(
        f"\nattempt store: {store['rows']:,} pool row(s) in {store['store']}, untracked"
        + (f", {store['bytes']:,} bytes" if store.get("bytes") else "")
    )
    if store.get("copy"):
        print(f"               copy {store['copy']}, manifest {store['manifest']}")
    # Read off the disk here rather than recorded inside the pass record: a total
    # written into the files it measures would change the number it reported.
    from fractal_wallpapers.curation import gallery

    tracked = gallery.tracked_bytes(record["pass"])
    print(
        f"tracked bytes: {tracked['total']:,} over {len(tracked['files'])} file(s), "
        f"largest {tracked['largest']:,}"
    )
    print(f"\nrecord {record['record']}")
    for name, where in record["sheets"].items():
        print(f"sheet  {name:<14} {where}")


def curate_gallery_store(args: argparse.Namespace) -> int:
    """Record, check or restore one pass's attempt store against its tracked manifest."""
    from fractal_wallpapers.curation import durability, gallery_store

    doing = {
        "save": lambda: gallery_store.save(args.pass_id),
        "check": lambda: gallery_store.check(args.pass_id),
        "restore": lambda: gallery_store.restore(args.pass_id, force=args.force),
    }[args.what]
    try:
        report = doing()
    except durability.DurableLost as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    if args.what == "check" and report.get("verdict") in {"short", "missing"}:
        return 1
    return 0


def curate_reject(args: argparse.Namespace) -> int:
    """Apply today's acting release bars to a run that was released before they acted."""
    from fractal_wallpapers.curation import floors, records, rejection

    if args.ephemeral:
        records.use(records.scratch_root(args.run))
    try:
        report = rejection.apply(
            args.run, rejector=args.rejector, date=args.date, dry_run=args.dry_run
        )
    except (rejection.RejectionRefused, floors.HeadStampMismatch) as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    return 0


def curate_below_bar(args: argparse.Namespace) -> int:
    """Draw the glance sheet of every served wallpaper an acting bar would take back.

    Report only, and the read to take before `curate reject`: the same rule, the
    same rows, laid out as pictures for the one judgement no head is asked for.
    """
    from fractal_wallpapers.curation import below_bar, records

    if args.ephemeral:
        records.use(records.scratch_root("below_bar"))
    try:
        report = below_bar.write(
            path=Path(args.out) if args.out else None,
            exclude=args.exclude or (),
            reason=args.exclude_reason,
        )
    except ValueError as refusal:
        print(refusal)
        return 1
    print(
        f"{report['below_bar']} served row(s) below an acting bar, {report['shown']} on the "
        f"sheet, {len(report['held_by_ruling'])} held in service by a ruling — "
        f"{report['sheet']}"
    )
    print(json.dumps(report, indent=2))
    return 0


def curate_repeats(args: argparse.Namespace) -> int:
    """List every location the collection has served more than one wallpaper of.

    Report only. The one-wallpaper-per-location rule acts at selection from
    2026-08-22 and cannot reach backwards: these are the pairs the collection
    accumulated while the rule was per-run and at two. `retire-repeats` is what
    settles them, and this is the read to take before and after it.
    """
    from fractal_wallpapers.curation import served_locations

    index = served_locations.build()
    rows = served_locations.repeats(index)
    extra = sum(len(cell["served"]) - 1 for cell in rows)
    print(
        f"{index.summary()['served_rows']} served wallpaper(s), {len(rows)} location(s) "
        f"holding more than one, {extra} wallpaper(s) over the one-per-location rule"
    )
    print(json.dumps(rows, indent=2))
    return 0


def curate_retire_repeats(args: argparse.Namespace) -> int:
    """Retire every wallpaper past the best one at a location, collection-wide."""
    from fractal_wallpapers.curation import records, rejection

    if args.ephemeral:
        records.use(records.scratch_root("retire_repeats"))
    try:
        report = rejection.retire_repeats(
            rejector=args.rejector, date=args.date, dry_run=args.dry_run
        )
    except rejection.RejectionRefused as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    # The pass exists to leave the collection one-per-location. A run of it that
    # wrote rejections and left a group standing has done half a decision, and
    # saying so in the exit code is what stops the next step reading the report
    # as the rule being settled.
    return 0 if report["groups_remaining"] in (0, None) else 1


def curate_parity(args: argparse.Namespace) -> int:
    """Render a real release plan both ways and compare the bytes."""
    from fractal_wallpapers.curation import checks, records

    if args.ephemeral:
        records.use(records.scratch_root(args.run))
    try:
        report = checks.parity(args.run, rows=args.rows, workers=args.workers)
    except checks.CheckError as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    return 0 if report["held"] else 1


def curate_replay(args: argparse.Namespace) -> int:
    """Re-derive every released picture from its own record and compare the bytes."""
    from fractal_wallpapers.curation import checks, records

    if args.ephemeral:
        records.use(records.scratch_root(args.run))
    try:
        report = checks.replay(args.run)
    except (checks.CheckError, FileNotFoundError) as refusal:
        print(refusal)
        return 1
    print(json.dumps({key: report[key] for key in report if key != "detail"}, indent=2))
    for row in report["detail"]:
        print(f"  {row['candidate']}: {row.get('arm', 'no picture')} -> {row['verdict']}")
    return 0 if report["held"] else 1


def curate_colors(args: argparse.Namespace) -> int:
    """Take the colour census, and optionally draw the sheets a person rules from."""
    from fractal_wallpapers.curation import color_sheets, colors, swatch_frequency

    stages = tuple(args.stage) if args.stage else colors.STAGES
    if args.sheets and "survival" not in stages:
        print(
            "the sheets are drawn from the candidate renders, so they need the survival "
            "stage. Add --stage survival, or drop --sheets."
        )
        return 1
    try:
        readout = colors.take(stages=stages)
    except colors.CensusError as refusal:
        print(refusal)
        return 1

    for name in stages:
        table = readout["stages"][name]
        print(f"\n=== {name}")
        if name == "library":
            missing = [
                swatch
                for swatch, cell in table["metrics"]["swatches"].items()
                if cell["at_10pct"] == 0
            ]
            print(f"  {table['maps']} maps ({table['in_pool']} in the pool)")
            print(f"  swatches no map carries at 10%: {missing or 'none'}")
        elif name == "picks":
            ranked = sorted(
                table["swatches"].items(),
                key=lambda item: (item[1]["selection_ratio"] is None, item[1]["selection_ratio"]),
            )
            print(f"  {table['sets']} candidate sets")
            for swatch, cell in ranked[:5]:
                print(
                    f"  least picked  {swatch:<26} offered {cell['offered']:>6} "
                    f"picked {cell['picked']:>5}  x{cell['selection_ratio']}"
                )
        elif name == "survival":
            print(f"  {table['pool']['renders']} candidate renders (score-free)")
            for head, cell in table["floor_referenced"].items():
                print(
                    f"  {head:<15} n={cell['n']:>4} floor={cell['floor']} clears={cell['clears']}"
                )
        elif name == "labels":
            for head, cell in table.items():
                keepers = cell["keepers"]
                print(
                    f"  {head:<15} {cell['pictures']} judged, {keepers['n']} at 3 or 4, "
                    f"{len(keepers['unrepresented_swatches'])} swatches with no keeper"
                )

    print(f"\ncensus  {display_path(colors.readout_path())}")
    print(f"rows    {display_path(colors.rows_path())}")
    print(f"manifest {display_path(colors.manifest_path())}")

    if args.sheets:
        rows = [
            json.loads(line)
            for line in colors.rows_path().read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        written = color_sheets.write(rows, repo_root() / "scratch")
        print(f"sheets  {display_path(Path(written['by_swatch']))}")
        print(f"        {display_path(Path(written['sparse']))}")

    if args.frequency:
        try:
            table = swatch_frequency.write(readout, repo_root() / "scratch")
        except swatch_frequency.SheetError as refusal:
            print(refusal)
            return 1
        print()
        print(f"frequency {display_path(Path(table['csv']))}")
        print(f"          {display_path(Path(table['page']))}")
        print(f"  {table['swatches']} swatches over {table['renders']} judged renders")
        print(f"  most common: {', '.join(f'{n} ({c})' for n, c in table['top'])}")
        print(f"  never dominant: {len(table['zero_dominance'])}")
        print(f"  carried by no map at 10%: {len(table['uncarried'])}")
    return 0


def curate_coverage(args: argparse.Namespace) -> int:
    """Coverage on pixels: how many maps can put each swatch on a real share of a picture."""
    from fractal_wallpapers.curation import palette_coverage as coverage

    try:
        if args.step_of_coverage in ("panel", "all"):
            coverage.build_panel()
        if args.step_of_coverage in ("probe", "all"):
            coverage.probe(workers=args.workers)
        if args.step_of_coverage in ("read", "all"):
            readout = coverage.take()
        else:
            return 0
    except coverage.CoverageError as refusal:
        print(refusal)
        return 1

    thin = coverage.thinnest(readout)
    table = readout["capability"]
    print(f"\npanel   {len(readout['panel']['cells'])} cells, {readout['panel']['modes']}")
    print(
        f"maps    {table['all']['maps']} ({table['prior']['maps']} pre-existing, "
        f"{table['drop']['maps']} in the drop)"
    )
    print(f"thinnest at 10%: {', '.join(thin)}")
    for swatch in thin:
        cells = table["all"]["swatches"][swatch]
        prior = table["prior"]["swatches"][swatch]
        print(
            f"  {swatch:<26} "
            + "  ".join(
                f"{int(t * 100):>2}%: {cells[f'at_{int(t * 100)}pct']:>3}"
                f"({prior[f'at_{int(t * 100)}pct']:>3})"
                for t in coverage.THRESHOLDS
            )
        )
    print(f"false capabilities (fold off only): {len(readout['false_capabilities'])}")
    print(
        f"realized: {readout['realized']['maps']} maps over "
        f"{readout['realized']['renders']} pool renders"
    )
    print(f"\ncoverage {display_path(coverage.readout_path())}")
    print(f"rows     {display_path(coverage.rows_path())}")

    if args.sheet or args.by_swatch:
        rows = coverage.read_rows()
        where = repo_root() / "scratch" / "palette_coverage"
        if args.sheet:
            print(f"sheet    {display_path(coverage.contact_sheet(readout, rows, where))}")
        if args.by_swatch:
            print(f"by-swatch {display_path(coverage.by_swatch_sheet(readout, rows, where))}")
    return 0


def curate_manufacture(args: argparse.Namespace) -> int:
    """Force the rare swatches onto good places, measure what landed, and cut the sheets."""
    from fractal_wallpapers.curation import manufacture

    steps = ("register", "plan", "screen", "confirm", "select", "read")
    wanted = steps if args.step_of_manufacture == "all" else (args.step_of_manufacture,)
    try:
        if "register" in wanted:
            for line in manufacture.register(write=args.write):
                print(line)
            if wanted == ("register",):
                return 0
        if "plan" in wanted:
            manufacture.build_plan(
                oversample=args.oversample,
                rows_per_kind=args.rows_per_kind,
                seed=args.seed,
                batch=args.batch,
            )
        if "screen" in wanted:
            manufacture.screen(workers=args.workers, device=args.device, batch=args.batch)
        if "confirm" in wanted:
            manufacture.confirm(workers=args.workers, device=args.device, batch=args.batch)
        if "select" in wanted:
            manufacture.select(rows_per_kind=args.rows_per_kind, batch=args.batch)
        if args.step_of_manufacture == "top-up":
            manufacture.top_up(oversample=args.oversample, batch=args.batch)
            return 0
        if args.step_of_manufacture == "knobs":
            probe = manufacture.probe_knobs(sample=args.knob_sample, batch=args.batch)
            print(json.dumps(probe, indent=2))
            return 0
        if args.step_of_manufacture == "verify":
            if not args.sheet:
                print("--step verify needs --sheet, the built sheet to check")
                return 1
            held = manufacture.verify(resolve_output(args.sheet), args.batch)
            print(json.dumps(held, indent=2))
            return 0 if held["held"] else 1
        if "read" not in wanted:
            return 0
        readout = manufacture.read(args.batch)
    except manufacture.ManufactureError as refusal:
        print(refusal)
        return 1

    spent = readout["yield"]
    print(
        f"\n{spent['attempts']} attempts over {spent['locations']} locations -> "
        f"{spent['attempts_past_screen']} past the screen -> {spent['confirmed']} confirmed -> "
        f"{spent['served']} served "
        f"({spent['lost_to_colour']} lost to colour, {spent['lost_to_tier']} to the tier cut)"
    )
    selection = readout["selection"]
    for kind, rows in sorted(selection["rows"].items()):
        print(f"{kind:<16} {rows} rows")
    if selection["shortfall"]:
        print(f"short in {len(selection['shortfall'])} cell(s): {selection['shortfall']}")
    spread = selection["rows_per_map"]
    print(
        f"maps {spread['maps_used']} carrying at most {spread['cap']} rows each, "
        f"{spread['distribution']}; tiers {selection['tiers']}; arms {selection['arms']}"
    )

    print("\nper target swatch: locations that reached 10%, worst first")
    for swatch, cell in readout["hit_rate"].items():
        flag = "  DEFECT?" if cell["probable_defect"] else ""
        print(
            f"  {swatch:<24} {cell['reached']:>3}/{cell['locations']:<3} "
            f"{cell['rate']:.2f}  best {cell['best_share']:.3f}{flag}"
        )
    moved = readout["drift"]
    if moved["rows"]:
        print(
            f"\ncandidate -> sheet geometry over {moved['rows']} rows: share moves a median "
            f"{moved['share_median']:.4f}, p95 {moved['share_p95']:.4f}, worst "
            f"{moved['share_worst']:.4f}; {moved['crossed_the_threshold']} cross 10%; "
            f"tier {moved['tier']}"
        )
    print(f"\nplan      {display_path(manufacture.plan_path(args.batch))}")
    for kind in sorted(selection["rows"]):
        print(f"sheet plan {display_path(manufacture.sheet_plan_path(kind, args.batch))}")
    print(f"record    {display_path(manufacture.record_dir(args.batch))}")
    return 0


def curate_expressed(args: argparse.Namespace) -> int:
    """How much of the codebook the finished collection expresses, and what a floor could ask."""
    from fractal_wallpapers.curation import expressed

    try:
        if args.step_of_expressed in ("census", "all"):
            expressed.census()
        readout = expressed.take() if args.step_of_expressed in ("read", "all") else None
    except expressed.ExpressedError as refusal:
        print(refusal)
        return 1
    if readout is None:
        return 0

    population = readout["population"]
    budget = readout["budget"]
    print(
        f"\npopulation {population['pictures']} finished wallpapers over "
        f"{len(population['runs'])} passes, {population['rejected_afterwards']} since taken back"
    )
    for label in ("all", "non_neutral"):
        cell = budget[label]
        spread = cell["distribution"]
        print(
            f"{label:<12} mean {cell['sum_coverage']:.3f} swatches expressed over "
            f"{cell['swatches']} "
            f"(median {spread['median']:g}, {spread['min']}-{spread['max']}); "
            f"largest uniform floor that fits: {cell['implied_ceiling']:.4f}"
        )
    print("\nthinnest first:")
    for swatch in readout["ranked"][:12]:
        value = readout["coverage"][swatch]
        print(f"  {swatch:<26} {value:.4f}  ({round(value * population['pictures'])})")
    print(f"  ... and {len(readout['ranked']) - 12} more, in the readout")
    census_gap = readout["agreement"]["census_decode"]
    print(
        f"\n160x90 decode moves a swatch by at most "
        f"{census_gap['worst_swatch_move']:.4f} and flips "
        f"{census_gap['threshold_cells_flipped']} of {census_gap['threshold_cells']} cells"
    )
    cost = readout["recolor_cost"]
    print(
        f"recolor pass over {cost['thin_swatches']} thin swatches would put "
        f"{cost['carriers_union']} carrier maps through "
        f"{cost['populations']['field']['pictures']} field pictures and "
        f"{cost['populations']['not_field']['pictures']} that need a re-render"
    )
    print(f"\nexpressed {display_path(expressed.readout_path())}")
    print(f"pictures  {display_path(expressed.pictures_path())}")
    return 0


def modes(args: argparse.Namespace) -> int:
    """List the named colorings, what each one is for, and whether it ships.

    The tier is shown because it is the difference between a mode a run will draw
    and one only a person will ask for by name, and a list that hid it would read
    as sixteen interchangeable choices plus three.

    Takes the parsed arguments and reads none of them, because every handler
    has the same shape and one exception is worse than one unused parameter.
    """
    del args
    for mode in engine.modes():
        tier = "" if mode["tier"] == engine.PRODUCTION else f"[{mode['tier']}] "
        print(f"{mode['name']:<22} {tier}{mode['identity']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    from fractal_wallpapers.curation import run as curation_run
    from fractal_wallpapers.discovery.walk import Limits as WalkLimits
    from fractal_wallpapers.supply.partitions import ALL_PARTITIONS

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
    fetch.add_argument(
        "--check",
        action="store_true",
        help=(
            "verify the manifest against the local tree and download nothing: every head "
            "present, every entry complete, every named artifact on disk and hashing true"
        ),
    )
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
        "--location",
        metavar="FILE",
        help="a location record to render instead of spelling one out: the "
        "{family, viewport, render} object a ledger row, a label row and a release "
        "record all already carry",
    )
    draw.add_argument(
        "--manifest",
        metavar="FILE",
        help="a JSONL of location records to render, one picture per row, into --out-dir. "
        "A file rather than a list of paths, because a batch is hundreds of rows and a "
        "Windows command line is not",
    )
    draw.add_argument(
        "--out",
        default=str(Path("artifacts") / "render.png"),
        help="output PNG path (default: artifacts/render.png)",
    )
    draw.add_argument(
        "--out-dir",
        default=str(Path("artifacts") / "renders"),
        help="where a --manifest run's pictures go (default: artifacts/renders). Each is "
        "named by its row and a digest of its own recipe, and renders.jsonl beside them "
        "is the join back to the records",
    )
    draw.add_argument("--limit", type=int, help="render only the first N rows of a manifest")
    draw.add_argument(
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
    search.add_argument(
        "--node-width",
        type=int,
        default=384,
        help="node render width in pixels. A scored run refuses anything but the node "
        "regime's own width: the head reads that frame as a tile",
    )
    search.add_argument(
        "--probe",
        type=float,
        default=0.25,
        help="probability the reframing probe fires on an admission (default: 0.25)",
    )
    search.add_argument(
        "--refine-per-walk",
        type=int,
        default=None,
        metavar="K",
        help="how many of this walk's best gate survivors have their FRAMING refined when the "
        "walk closes, best first by the seating statistic. The gallery pass's step 5a at the "
        "other end of the pipeline and through the same code: a small window of framings drawn "
        "at the node regime, read through the location head, the best adopted if it beats the "
        "recorded framing by --refine-margin. It is recorded as a later ledger row that the "
        "readers prefer, never as an edit; nothing feeds back into this walk's reward or "
        f"descent (default: {WalkLimits.refine_per_walk}; 0 disables the leg)",
    )
    search.add_argument(
        "--refine-margin",
        type=float,
        default=None,
        metavar="DELTA",
        help="how much better a framing has to read before it is adopted, in NATS of log-odds "
        "on P(>=4). The gallery pass's own default unless said otherwise, so a scan taken here "
        "and a scan taken at a pass are the same decision",
    )
    search.add_argument(
        "--no-reframings",
        action="store_true",
        help="expand only what the walk descends into; fire no reframing operators",
    )
    neighborhood = search.add_mutually_exclusive_group()
    neighborhood.add_argument(
        "--neighborhood",
        dest="neighborhood",
        action="store_true",
        default=None,
        help="enumerate neighbouring nuclei (on by default; the expensive operator)",
    )
    neighborhood.add_argument(
        "--no-neighborhood",
        dest="neighborhood",
        action="store_false",
        help="fire only the snap and the lateral step, and pay neither the "
        "neighbourhood enumeration's clock nor its frontier",
    )
    search.add_argument(
        "--colormap",
        default="twilight_shifted",
        help="colormap the gate renders are drawn through. A scored run refuses any map "
        "but the tile pool's floor palette: the head reads the gate render as a tile",
    )
    search.add_argument(
        "--out-dir",
        default=str(Path("artifacts") / "walk"),
        help="where the ledger and thumbnails go (default: artifacts/walk)",
    )
    search.add_argument(
        "--foci",
        action="store_true",
        help="record each expanded node's kept focus set beside its candidates: where the "
        "peaks were, which blurring scales found each one, how alone it stands and how far "
        "the nearest kept neighbour is. Off by default, and a run without it writes the "
        "ledger it always wrote - the set is read either way and this decides only whether "
        "it is kept",
    )
    grace_flag(search)
    scoring_flags(search)
    search.set_defaults(handler=walk)

    production = subcommands.add_parser(
        "harvest",
        help="the production loop: keep finding material where it is scarcest",
        description=(
            "Run batches until the active-time budget is spent, dividing each batch's slots "
            "between partitions by how far each one is below its intended share of the "
            "release. Checkpoints at every batch boundary and resumes from the checkpoint "
            "if one is there, so a killed run continues rather than restarting."
        ),
    )
    production.add_argument("--seed", type=int, default=0, help="run seed (default: 0)")
    production.add_argument("--batch", type=int, default=8, help="node slots per batch")
    harvest_clock = production.add_mutually_exclusive_group()
    harvest_clock.add_argument(
        "--minutes",
        type=float,
        default=None,
        help=f"active-minute budget across every session of this run "
        f"(default: {DEFAULT_HARVEST_MINUTES:g}; 0 for none)",
    )
    harvest_clock.add_argument(
        "--finish-by",
        metavar="HH:MM",
        help="derive --minutes from a wall-clock finish time instead of naming it: the "
        "span to the next HH:MM, less the release leg (--release-slots), the closing "
        "re-score, the ledger load and a margin, converted from wall to ACTIVE minutes. "
        "The derived plan is printed at startup and written into the run summary",
    )
    production.add_argument(
        "--release-slots",
        type=int,
        default=curation_run.DEFAULT_N,
        help=f"the release ceiling the curation leg will be asked for (default: "
        f"{curation_run.DEFAULT_N}, the diagnostic release a run keeps). Read only with "
        f"--finish-by, which reserves this many pictures at the measured rate",
    )
    production.add_argument(
        "--strange-share",
        type=float,
        default=curation_run.STRANGE_SHARE,
        help=f"the share of those slots the strange judge will fill (default: "
        f"{curation_run.STRANGE_SHARE:g}). Read only with --finish-by: it is one of the "
        f"three terms that turn a release ceiling into a colorize attempt count, and the "
        f"reservation has to be for the night that will actually be run",
    )
    production.add_argument(
        "--strange-modes",
        type=int,
        default=None,
        help="modes the strange judge will draw at each location (default: curation's own). "
        "Read only with --finish-by, for the same reason as --strange-share",
    )
    production.add_argument(
        "--release-workers",
        type=int,
        default=schedule_module.RELEASE_WORKERS,
        help=f"worker processes the release leg will run at, which is what the reserved "
        f"rate is scaled to (default: {schedule_module.RELEASE_WORKERS}, the count every "
        f"release on record was measured at). Read only with --finish-by; it reserves "
        f"the clock, it does not pass anything to `curate run`",
    )
    production.add_argument(
        "--batches", type=int, help="stop after this many batches, whatever the clock says"
    )
    production.add_argument(
        "--seeds",
        help="a JSONL seed file for the parameter planes, which have no sampler "
        "(default: the tracked plane seed pool, data/discovery/plane_seed_pool.jsonl)",
    )
    production.add_argument(
        "--root-expansions",
        type=int,
        default=12,
        help="expansions any one root may pay for, its reframings included",
    )
    production.add_argument("--candidates", type=int, default=4, help="candidates drawn per node")
    production.add_argument(
        "--node-width",
        type=int,
        default=384,
        help="node render width in pixels. A scored run refuses anything but the node "
        "regime's own width: the head reads that frame as a tile",
    )
    production.add_argument(
        "--partition",
        action="append",
        choices=list(ALL_PARTITIONS),
        help="keep the books for this partition alone (repeatable; default: every one). A "
        "run told one partition allocates its whole clock there, and its census, price "
        "and refill census cover that partition only",
    )
    production.add_argument(
        "--probe",
        type=float,
        default=None,
        help="probability the reframing probe fires on an admission (default: "
        f"{WalkLimits.probe_probability})",
    )
    production.add_argument(
        "--refine-per-walk",
        type=int,
        default=None,
        metavar="K",
        help="how many of this walk's best gate survivors have their FRAMING refined when the "
        "walk closes, best first by the seating statistic. The gallery pass's step 5a at the "
        "other end of the pipeline and through the same code: a small window of framings drawn "
        "at the node regime, read through the location head, the best adopted if it beats the "
        "recorded framing by --refine-margin. It is recorded as a later ledger row that the "
        "readers prefer, never as an edit; nothing feeds back into this walk's reward or "
        f"descent (default: {WalkLimits.refine_per_walk}; 0 disables the leg)",
    )
    production.add_argument(
        "--refine-margin",
        type=float,
        default=None,
        metavar="DELTA",
        help="how much better a framing has to read before it is adopted, in NATS of log-odds "
        "on P(>=4). The gallery pass's own default unless said otherwise, so a scan taken here "
        "and a scan taken at a pass are the same decision",
    )
    harvest_neighborhood = production.add_mutually_exclusive_group()
    harvest_neighborhood.add_argument(
        "--neighborhood",
        dest="neighborhood",
        action="store_true",
        default=None,
        help="enumerate neighbouring nuclei (on by default; the expensive operator)",
    )
    harvest_neighborhood.add_argument(
        "--no-neighborhood",
        dest="neighborhood",
        action="store_false",
        help="fire only the snap and the lateral step, and pay neither the "
        "neighbourhood enumeration's clock nor its frontier",
    )
    production.add_argument(
        "--floor",
        type=float,
        default=0.05,
        help="the share of the clock every partition floors at (default: 0.05)",
    )
    production.add_argument(
        "--discount",
        type=float,
        help="what an unlabelled machine-scored find is worth against the deficit "
        "(default: 0.2); 0 reproduces the labels-only deficit exactly",
    )
    production.add_argument("--prices", help="a cost-to-find seed table other than the shipped one")
    production.add_argument(
        "--low-water", type=int, default=8, help="a partition below this many nodes is starved"
    )
    production.add_argument(
        "--cooldown", type=int, default=10, help="batches a partition waits between refills"
    )
    production.add_argument(
        "--refill-share",
        type=float,
        default=0.25,
        help="share of the loop's clock refills may spend (default: 0.25)",
    )
    production.add_argument(
        "--lineage-cap",
        type=int,
        default=0,
        help="admissions any one lineage may book before the walk stops expanding it "
        "(default: 0, no cap). The hard stop that stands above the soft discount below",
    )
    production.add_argument(
        "--lineage-discount",
        type=float,
        default=novelty_default("DISCOUNT_K"),
        help=f"how fast a lineage's contest credit decays with what it has already booked "
        f"this run: credit x= max(floor, 1/(1+k*n)) (default: "
        f"{novelty_default('DISCOUNT_K')}; 0 turns the discount off). In the contest only - "
        f"the exploration share is never priced",
    )
    production.add_argument(
        "--lineage-discount-floor",
        type=float,
        default=novelty_default("DISCOUNT_FLOOR"),
        help=f"the floor that discount never falls below "
        f"(default: {novelty_default('DISCOUNT_FLOOR')})",
    )
    production.add_argument(
        "--exploration-floor",
        type=float,
        default=novelty_default("SHARE_FLOOR"),
        help=f"share of the post-floor slots reserved for lineages no run has ever booked "
        f"an admission from, which the share never falls below "
        f"(default: {novelty_default('SHARE_FLOOR')})",
    )
    production.add_argument(
        "--exploration-start",
        type=float,
        default=novelty_default("SHARE_START"),
        help=f"what that share opens at before it has priced itself "
        f"(default: {novelty_default('SHARE_START')})",
    )
    production.add_argument(
        "--exploration-ema",
        type=float,
        default=novelty_default("SHARE_EMA"),
        help=f"per-served-batch smoothing weight for the share's self-pricing "
        f"(default: {novelty_default('SHARE_EMA')})",
    )
    production.add_argument(
        "--no-exploration",
        action="store_true",
        help="allocate the whole post-floor batch by deficit; no protected share",
    )
    production.add_argument(
        "--no-saturation",
        action="store_true",
        help="do not read earlier runs' ledgers; every place ranks as untouched",
    )
    production.add_argument(
        "--no-twins",
        action="store_true",
        help="do not derive Julia parameters from admitted parameter-plane locations; the "
        "three higher-degree Julia partitions then have no channel at all and say so",
    )
    production.add_argument(
        "--root-channel",
        action="append",
        dest="root_channels",
        choices=[proven_default("CHANNEL")],
        help=f"draw roots from this channel as well as the partition's own pool; "
        f"repeatable. {proven_default('CHANNEL')!r} roots the walk at every location a human "
        f"has scored a keeper, interleaved with the pool rather than replacing it — on the "
        f"dynamical partitions at the labelled viewport, which is a frame their `c`-pools "
        f"cannot express",
    )
    production.add_argument(
        "--ledgers",
        default="artifacts",
        help="where earlier runs' ledgers live (default: artifacts)",
    )
    production.add_argument(
        "--colormap",
        default="twilight_shifted",
        help="colormap the gate renders are drawn through. A scored run refuses any map "
        "but the tile pool's floor palette: the head reads the gate render as a tile",
    )
    production.add_argument(
        "--out-dir",
        default=str(Path("artifacts") / "harvest"),
        help="the run directory (default: artifacts/harvest)",
    )
    production.add_argument(
        "--foci",
        action="store_true",
        help="record each expanded node's kept focus set beside its candidates: where the "
        "peaks were, which blurring scales found each one, how alone it stands and how far "
        "the nearest kept neighbour is. Off by default, and a run without it writes the "
        "ledger it always wrote - the set is read either way and this decides only whether "
        "it is kept",
    )
    grace_flag(production)
    scoring_flags(production)
    production.set_defaults(handler=harvest)

    checking = subcommands.add_parser(
        "score-parity",
        help="score one batch of locations serially and through the pool, and compare",
        description=(
            "The scoring pass renders each location's canonical view in worker processes "
            "and reads the batch through the head in the parent. This makes the same views "
            "both ways, into two directories, and compares the bytes and the scores — so a "
            "disagreement is attributable to the render or to the read rather than to "
            "either by elimination."
        ),
    )
    ledger_flags(checking)
    checking.add_argument("--rows", type=int, default=6, help="locations to score both ways")
    checking.add_argument(
        "--out-dir",
        default=str(Path("scratch") / "score_parity"),
        help="where the two arms' views go (default: scratch/score_parity)",
    )
    scoring_flags(checking)
    checking.set_defaults(handler=score_parity)

    reading_locations = subcommands.add_parser(
        "score-locations",
        help="score a list of locations through the shipped location head",
        description=(
            "Everything else that scores locations reads a ledger. This reads a JSONL of "
            "location records and writes one score row apiece — the row a panel that wants "
            "to print P(>=3) under a picture needs. Every row names the sha256 of the "
            "artifact that produced it and the regime it was read at, because heads are "
            "re-shipped and the floors that read them are restated at the flip: a score "
            "that cannot say what produced it goes quietly stale."
        ),
    )
    reading_locations.add_argument(
        "--manifest", required=True, metavar="FILE", help="JSONL of location records"
    )
    reading_locations.add_argument(
        "--out",
        default=str(Path("artifacts") / "location_scores.jsonl"),
        help="where the score rows go (default: artifacts/location_scores.jsonl)",
    )
    reading_locations.add_argument("--limit", type=int, help="score only the first N rows")
    reading_locations.add_argument(
        "--regime",
        default="640x360ss2",
        metavar="WxHssN",
        help="the geometry to read the pictures at (default: 640x360ss2, the deploy view)",
    )
    reading_locations.add_argument(
        "--views", help="where the rendered views are cached (default: the regime's own tree)"
    )
    reading_locations.add_argument(
        "--score-workers",
        type=int,
        default=1,
        help="worker processes rendering the views the head reads (default: 1, which "
        "renders in this process; one render already spends the whole machine)",
    )
    reading_locations.add_argument("--device", default="auto", help="cuda, cpu, or auto")
    reading_locations.set_defaults(handler=score_locations)

    seeding = subcommands.add_parser(
        "derive-plane-seeds",
        help="re-derive the tracked parameter-plane seed pool, and check the shipped one",
        description=(
            "Walk a grid over each parameter plane's home frame, identify the atom under "
            "every point, and keep one root per distinct atom spread over periods. Verifies "
            "against the tracked pool by default and writes only with --write: the pool is "
            "shipped data, and the claim it makes is that this procedure still produces it."
        ),
    )
    seeding.add_argument(
        "--columns",
        type=int,
        default=None,
        help=f"grid columns over each home frame (default: {plane_seed_default('COLUMNS')})",
    )
    seeding.add_argument(
        "--per-partition",
        type=int,
        default=None,
        help=f"roots kept per partition (default: {plane_seed_default('PER_PARTITION')})",
    )
    seeding.add_argument(
        "--out", help="path to verify against or write (default: the tracked pool)"
    )
    seeding.add_argument(
        "--write", action="store_true", help="write it; otherwise verify and print the difference"
    )
    seeding.set_defaults(handler=derive_plane_seeds)

    proving = subcommands.add_parser(
        "derive-proven-seeds",
        help="build the proven-label seed set from the label store",
        description=(
            "One root per location a human scored a keeper, on every partition but the "
            "pinned classic phoenix. Not a tracked file: the seed set is a query over the "
            "label store, re-derived whenever it is asked for, and a harvest draws it live "
            "with `--root-channel proven`. Printing one is for reading it, diffing it, or "
            "passing it as --seeds."
        ),
    )
    proving.add_argument(
        "--tier-floor",
        type=int,
        default=None,
        help=f"the label class a location must reach (default: {proven_default('TIER_FLOOR')})",
    )
    proving.add_argument(
        "--partition",
        action="append",
        # Refused at the parser, the way an unregistered channel name is. Without
        # this the subcommand will happily print a seed set for a partition the
        # channel does not serve, and a file no harvest can consume reads exactly
        # like one it can.
        choices=list(proven_default("SERVED")),
        help="derive for this partition alone; repeatable (default: every served partition)",
    )
    proving.add_argument(
        "--out",
        default="artifacts/proven_seeds.jsonl",
        help="where --write puts the seed file (default: artifacts/proven_seeds.jsonl)",
    )
    proving.add_argument("--write", action="store_true", help="write the seed file")
    proving.add_argument(
        "--against",
        help="a seed file to compare the derived set against, by location and not by id",
    )
    proving.set_defaults(handler=derive_proven_seeds)

    standing = subcommands.add_parser(
        "census",
        help="print the standing deficit and the allocation it implies, running nothing",
        description=(
            "Census what every partition holds — human labels, plus discounted machine-scored "
            "finds a human has not looked at — against what the release mix says it is owed, "
            "and show the allocation that follows. Quoted at seed prices, because a price "
            "table is a fact about a run and this is not one."
        ),
    )
    standing.add_argument(
        "--discount",
        type=float,
        help="what an unlabelled machine-scored find is worth against the deficit "
        "(default: 0.2); 0 reproduces the labels-only deficit exactly",
    )
    standing.add_argument("--floor", type=float, default=0.05, help="the per-partition floor")
    standing.add_argument("--prices", help="a cost-to-find seed table other than the shipped one")
    standing.set_defaults(handler=census)

    pricing = subcommands.add_parser(
        "derive-prices",
        help="regenerate the cost-to-find seed table from finished runs",
        description=(
            "Pool the minutes and the currency of every source run, divide once, and write "
            "the measured table. With --regularize, shrink it toward its own median and "
            "write the seed a run is actually handed. Never hand-edit either file: every "
            "constant reaches a shipped table through a regeneration."
        ),
    )
    pricing.add_argument(
        "--run", action="append", required=True, help="a finished run directory (repeatable)"
    )
    pricing.add_argument(
        "--regularize", action="store_true", help="shrink the measured table into a seed"
    )
    pricing.add_argument("--alpha", type=float, default=0.9, help="shrinkage weight in log space")
    pricing.add_argument(
        "--clamp", type=float, default=16.0, help="band the live estimate may occupy"
    )
    pricing.add_argument("--measured", help="path recorded as the regularizer's source")
    pricing.add_argument("--out", help="where to write (default: the shipped table)")
    pricing.add_argument("--write", action="store_true", help="write it; otherwise print it")
    pricing.set_defaults(handler=derive_prices)

    cut = subcommands.add_parser(
        "derive-tau-h",
        help="re-derive the cheap cut from this repository's own walks",
        description=(
            "τ_h is the cut on a cheap score that decides which candidates are worth a "
            "full-resolution confirmation. It is a point on one scorer's probability scale, "
            "so it is derived here and never transferred; a partition with too few good "
            "rows fails open and confirms everything."
        ),
    )
    cut.add_argument("--ledger", action="append", help="a walk ledger (repeatable)")
    cut.add_argument(
        "--keep", type=float, default=0.90, help="fraction of good frames the cut retains"
    )
    cut.add_argument("--out", help="where to write (default: the shipped table)")
    cut.add_argument("--write", action="store_true", help="write it; otherwise print it")
    cut.set_defaults(handler=derive_tau_h)

    listing = subcommands.add_parser("modes", help="list the named colorings")
    listing.set_defaults(handler=modes)

    label_commands(subcommands)
    tile_commands(subcommands)
    render_commands(subcommands)
    head_commands(subcommands)
    regime_commands(subcommands)
    palette_commands(subcommands)
    library_commands(subcommands)
    figure_commands(subcommands)
    coloring_commands(subcommands)
    curate_commands(subcommands)
    deep_commands(subcommands)
    storage_commands(subcommands)

    bringing = subcommands.add_parser(
        "import-labels",
        help="import the source project's location labels into this store, as flat rows",
        description=(
            "Read another corpus through its own canonical reader, resolve every label once "
            "— amendment overlay applied, revision rows read past, one verdict per location "
            "as the maximum over its crops — and write flat rows here. Registers each batch "
            "it lands before writing a row of it, and draws the split when it is done."
        ),
    )
    bringing.add_argument("--source", required=True, help="the source repository's root")
    bringing.add_argument("--seed", type=int, default=0, help="the split draw's seed (default: 0)")
    bringing.add_argument(
        "--share", type=float, default=0.20, help="the evaluation side's target share"
    )
    bringing.set_defaults(handler=import_labels)

    finishing = subcommands.add_parser(
        "import-finished",
        help="import the source project's finished-render corpora into their stores",
        description=(
            "Read both finished-render corpora through the source's own resolution rules — "
            "one exported file per finished sheet, joined by image id, asserted in both "
            "directions — and write flat rows here. Every registration flag is read from the "
            "source and checked against this repository's table row by row; a single "
            "disagreement writes nothing. Brings across every colormap the rows name, because "
            "a row naming a map nobody holds is not a row that can be rendered."
        ),
    )
    finishing.add_argument("--source", required=True, help="the source repository's root")
    finishing.add_argument("--head", help="import only this judge's corpus instead of both")
    finishing.set_defaults(handler=import_finished)

    return parser


def label_commands(subcommands) -> None:
    """The labeling rig: register a batch, cut a sheet, serve it, record it, split it."""
    labelling = subcommands.add_parser(
        "label",
        help="collect human verdicts: register, build, sheets, serve, ingest, show, split",
        description=(
            "The labeling rig and the store behind it. A batch is registered before it has "
            "rows, a sheet is cut from a walk's ledger or from a batch already stored, the "
            "page is served locally, and what comes back is recorded through the one writer."
        ),
    )
    steps = labelling.add_subparsers(dest="step", required=True)

    registering = steps.add_parser(
        "register",
        help="register a batch's generation method, before it has any rows",
        description=(
            "Say how a population was drawn, while that is still knowable. Two flags decide "
            "whether anything measured on it can be read as a rate about the world: whether "
            "a model score was in the draw, and whether the page anchored the labels to a "
            "head's own verdict. Eval-eligibility follows from the two and is never stored."
        ),
    )
    registering.add_argument("--batch", required=True, help="the name its rows will carry")
    registering.add_argument("--method", required=True, help="how the population was drawn")
    registering.add_argument(
        "--head",
        choices=sorted(FINISHED_HEADS),
        help="register in a finished-render store instead of the location store",
    )
    registering.add_argument(
        "--score-unconditioned",
        action="store_true",
        help="no model score anywhere in the selection (a systematic draw qualifies)",
    )
    registering.add_argument(
        "--anchored",
        action="store_true",
        help="the page serves a head's own verdict prefilled, or orders rows by its score",
    )
    registering.add_argument(
        "--eval-only",
        action="store_true",
        help="bought as an instrument: pinned to the evaluation side and never trainable",
    )
    registering.add_argument("--why", help="the sentence a later reader will need")
    registering.set_defaults(handler=label_register)

    building = steps.add_parser(
        "build",
        help="cut a sheet and render every unit of it",
        description=(
            "One generator, two row sources. A LOCATION sheet asks whether a place is worth "
            "rendering and renders each unit twice — through the canonical colormap, which is "
            "what a head sees, and through the vivid one, which is what a person judges from, "
            "both named maps in the committed library. A FINISHED-RENDER sheet asks whether a "
            "picture is worth keeping and renders each unit once, through its own whole recipe, "
            "at the geometry both corpora were collected at. Either way the suggestions are the "
            "shipped judge's own decode, the page reads good→bad by its score, and the sheet "
            "is a manifest, a row file carrying every unit's whole join, and a page that serves "
            "the file order and never reshuffles."
        ),
    )
    source = building.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--from-ledger", help="a walk ledger; its admitted candidates are the units"
    )
    source.add_argument("--from-batch", help="a batch already in the store, to judge again")
    source.add_argument(
        "--from-plan",
        help="a JSONL of units — the population somebody selected. Finished-render units with "
        "--head, locations without it; either way the selection is the caller's and is "
        "recorded in the batch's registration",
    )
    building.add_argument(
        "--head",
        choices=sorted(FINISHED_HEADS),
        help="the finished-render judge a --from-plan sheet is cut for",
    )
    building.add_argument(
        "--admitted-only",
        action="store_true",
        help="cut to what the scorer admitted rather than to everything the gates passed; "
        "empty until a head exists, because admission needs a score",
    )
    building.add_argument(
        "--batch",
        required=True,
        help="the registered batch the rows land in, and what the page keys its saved session "
        "on. A plan unit may name its own batch — a revision sheet re-serves rows from several "
        "at once and each keeps its registration — and then this is only the sheet's name",
    )
    building.add_argument("--seed", type=int, default=0, help="the presentation seed (default: 0)")
    building.add_argument("--limit", type=int, help="cut the sheet to this many units")
    building.add_argument("--title", default="", help="what the page calls itself")
    building.add_argument(
        "--resolution",
        nargs=2,
        type=int,
        metavar=("W", "H"),
        default=[1280, 720],
        help="render size (default: 1280 720, what both finished corpora were collected at)",
    )
    building.add_argument("--supersample", type=int, default=2, help="samples per pixel, per axis")
    building.add_argument(
        "--reuse-renders",
        action="store_true",
        help="take a unit's picture off this head's render cache where the cache already holds "
        "that exact spec, instead of rendering it again. The cache names a picture by a digest "
        "of everything the engine is told, so a hit is the same picture",
    )
    building.add_argument(
        "--order-by",
        choices=list(sheets_module.ORDERINGS),
        default="rank",
        help="which reading a FINISHED-RENDER page is ordered good-to-bad by: `rank`, the "
        "head's expected tier over the whole scale (default), or `top`, its last cutpoint "
        "alone — which is what separates rows at the good end of a page, where the "
        "cutpoint below it is saturated",
    )
    building.add_argument(
        "--out-dir",
        default=str(Path("artifacts") / "sheet"),
        help="where the sheet is built (default: artifacts/sheet)",
    )
    scoring_flags(building)
    building.set_defaults(handler=label_build)

    listing_sheets = steps.add_parser(
        "sheets",
        help="list the built sheets, with what each one holds",
        description=(
            "A sheet's directory name is chosen by whoever cut it and does not have to be "
            "the batch inside it, so the only authority on what a directory holds is its own "
            "manifest. This reads them, so that finding a sheet to serve is a command rather "
            "than opening candidates by hand."
        ),
    )
    listing_sheets.add_argument(
        "--under", default="artifacts", help="where to look (default: artifacts)"
    )
    listing_sheets.add_argument(
        "--drops", action="store_true", help="also print where each sheet's labels would land"
    )
    listing_sheets.set_defaults(handler=label_sheets)

    serving = steps.add_parser(
        "serve",
        help="serve a built sheet to a browser on this machine",
        description=(
            "Binds exclusively, so a second launcher fails instead of silently co-hosting the "
            "port and serving half the images out of the wrong directory."
        ),
    )
    serving.add_argument("--sheet", required=True, help="a built sheet directory")
    serving.add_argument("--host", default="127.0.0.1", help="address to bind (default: loopback)")
    serving.add_argument("--port", type=int, default=8010, help="first port to try (default: 8010)")
    serving.set_defaults(handler=label_serve)

    ingesting = steps.add_parser(
        "ingest",
        help="resolve a sheet's export into store rows — the one path into either store",
        description=(
            "The seam between a sheet that lives somewhere untracked and a store that has to "
            "outlive it. Each exported unit is joined to its sheet row here, once, and lands "
            "as a row carrying the whole join — the place for a location, and the place with "
            "the mode, its own settings, its curve, the map, every knob of the palette pass "
            "and the geometry for a finished render. The sheet says which judge it was cut "
            "for and that decides which store it lands in. Only units the page exported become "
            "labels: a suggestion the labeler never reviewed is absent from that file and "
            "cannot reach a store as a verdict. Both counts are checked in both directions, "
            "nothing already stored is written twice, a verdict that changed is a new row "
            "rather than an edit, and the evaluation pin is asserted after the write."
        ),
    )
    ingesting.add_argument(
        "--sheet", required=True, help="a built sheet directory, or a manifest, rows or stem"
    )
    ingesting.add_argument(
        "--labels",
        help="the export to read (default: labels/<head>.<sheet>.json, where this "
        "sheet's page saves)",
    )
    ingesting.add_argument("--labeler", required=True, help="who cast the verdicts")
    ingesting.add_argument("--write", action="store_true", help="append; otherwise print the plan")
    ingesting.set_defaults(handler=label_ingest)

    showing = steps.add_parser("show", help="print what the store currently says, resolved")
    showing.set_defaults(handler=label_show)

    splitting = steps.add_parser(
        "split",
        help="re-derive the train/evaluation split, keeping every pin that exists",
        description=(
            "A seeded draw over location groups. A group reaches the evaluation side only if "
            "every location in it is eval-eligible, and a location already pinned there is "
            "never released — re-deriving adds, and only adds."
        ),
    )
    splitting.add_argument("--seed", type=int, default=0, help="the draw's seed (default: 0)")
    splitting.add_argument(
        "--share", type=float, default=0.20, help="target share of locations on the evaluation side"
    )
    splitting.add_argument("--write", action="store_true", help="ship it; otherwise print it")
    splitting.set_defaults(handler=label_split)


def tile_commands(subcommands) -> None:
    """The training tiles: plan the population, then render it."""
    tiling = subcommands.add_parser(
        "tiles",
        help="build the pictures a head is trained on: plan, then render",
        description=(
            "One iteration pass per location and every tile a colored crop of it, each "
            "drawing its own colormap, framing, reconstruction and JPEG quality. The plan "
            "says which locations; the recipe behind the fan-out belongs to the engine."
        ),
    )
    steps = tiling.add_subparsers(dest="step", required=True)

    planning = steps.add_parser(
        "plan",
        help="turn the label store into the population a build runs over",
        description=(
            "Every labeled location is in the plan, evaluation side included: a held-out "
            "location has to be scored through the same pictures the training side was "
            "learned from, or the number measures the render as much as the head. The plan "
            "is shuffled by a seed, so any prefix of it is a fair sample and a bounded "
            "rehearsal projects the whole build honestly."
        ),
    )
    planning.add_argument("--seed", type=int, default=0, help="the shuffle's seed (default: 0)")
    planning.set_defaults(handler=tiles_plan)

    building = steps.add_parser(
        "build",
        help="render every tile of the plan, at one regime",
        description=(
            "Resumable by construction: a location whose tiles are all on disk is skipped "
            "before its field is iterated, so a killed run continues rather than restarting. "
            "A build is aimed at a regime — a tile size and a field supersample — which is "
            "written into every file name it makes, so two regimes share one cache without "
            "either skipping over the other's pictures. The canonical 640x360 at supersample "
            "2 writes the bare names; anything else adds its own segment, and its manifest, "
            "build record and log take the same segment. Progress goes to "
            "artifacts/tiles/build<regime>.log as it runs."
        ),
    )
    building.add_argument(
        "--limit",
        type=int,
        help="stop after this many locations; every row it writes is stamped partial",
    )
    building.add_argument(
        "--tile",
        default="640x360",
        metavar="WIDTHxHEIGHT",
        help="one tile's output size (default: 640x360)",
    )
    building.add_argument(
        "--supersample",
        type=int,
        default=2,
        help="field samples per output pixel per axis (default: 2)",
    )
    building.set_defaults(handler=tiles_build)


def render_commands(subcommands) -> None:
    """The finished-render cache: plan the pictures, then make them."""
    caching = subcommands.add_parser(
        "renders",
        help="build the pictures a finished-render judge is trained on: plan, then render",
        description=(
            "A finished-render row records the recipe rather than the picture, so the "
            "pictures are regenerated here — every one of them, training and evaluation "
            "alike, through this repository's own coloring path. A head trained on one "
            "renderer's pictures and deployed against another's measures the difference "
            "between the two renderers."
        ),
    )
    steps = caching.add_subparsers(dest="step", required=True)

    planning = steps.add_parser(
        "plan",
        help="turn a store into the pictures a build has to make",
        description=(
            "One job per distinct picture: rows that share a place, a mode with its "
            "settings, a curve, a map and a recipe share a file. The plan is shuffled by a "
            "seed, so any prefix of it is a fair sample and a bounded rehearsal projects "
            "the whole build honestly."
        ),
    )
    planning.add_argument("--head", required=True, help="which judge's corpus")
    planning.add_argument("--seed", type=int, default=0, help="the shuffle's seed (default: 0)")
    planning.set_defaults(handler=renders_plan)

    building = steps.add_parser(
        "build",
        help="render every picture of the plan",
        description=(
            "Resumable by construction: a picture already on disk is skipped before its "
            "field is iterated, and a file is named for a digest of its own recipe, so a "
            "re-planned build re-uses everything it already has. Progress goes to "
            "build.log as it runs."
        ),
    )
    building.add_argument("--head", required=True, help="which judge's corpus")
    building.add_argument("--limit", type=int, help="stop after this many jobs of the plan")
    building.set_defaults(handler=renders_build)

    checking = steps.add_parser(
        "verify",
        help="compare regenerated pictures against the ones the verdicts were cast on",
        description=(
            "The whole coloring recipe is reproduced from a record rather than shared, and "
            "every knob of it is a way to be quietly wrong: the picture still looks like a "
            "fractal and the verdict is about something else. Compares the pairs directly "
            "against the only honest yardstick — what re-compressing the judged picture "
            "costs. Needs the source project present."
        ),
    )
    checking.add_argument("--head", required=True, help="which judge's corpus")
    checking.add_argument("--source", required=True, help="the source repository's root")
    checking.add_argument("--sample", type=int, default=60, help="how many pairs to compare")
    checking.add_argument("--seed", type=int, default=0, help="the sample's seed (default: 0)")
    checking.set_defaults(handler=renders_verify)

    registering = steps.add_parser(
        "preregister",
        help="write a judge's bar, before there is a head to judge against it",
        description=(
            "Builds the bar out of the source project's committed reading of this judge's "
            "blind sheet — the only labels on it that no head suggested — and out of how "
            "precisely that sheet can tell two heads apart at all. Copies those figures in "
            "so the bar stays re-readable without the other repository, and refuses to "
            "overwrite a bar that already exists."
        ),
    )
    registering.add_argument("--head", required=True, help="which judge")
    registering.add_argument("--source", required=True, help="the source repository's root")
    registering.add_argument(
        "--force", action="store_true", help="overwrite a bar no head has been judged against"
    )
    registering.set_defaults(handler=judge_preregister)

    training = steps.add_parser(
        "train",
        help="train a judge on the built render cache",
        description=(
            "One epoch is one pass over pictures, not over places: a place that carries a "
            "dozen colorings contributes a dozen examples, because the differences between "
            "them are what is being learned. The sampler equalizes places so that a "
            "heavily-coloured one is still worth one place's gradient."
        ),
    )
    training.add_argument("--head", required=True, help="which judge")
    training.add_argument("--device", default="auto", help="cuda, cpu, or auto (default)")
    training.add_argument("--epochs", type=int, help="override the recipe's epoch count")
    training.add_argument("--seed", type=int, help="override the recipe's seed")
    training.add_argument(
        "--only",
        help="render only: train the ABLATION instead — one kind's share of exactly the "
        "pooled split, under exactly this recipe. The arm that separates pooling from what "
        "pooling changed alongside it",
    )
    training.add_argument(
        "--two-head",
        action="store_true",
        help="render only: one backbone, TWO last layers — one ordinal head per kind. Shares "
        "every representation and lets the kinds keep two scales, at the cost of having to "
        "be told which kind it is reading",
    )
    training.add_argument(
        "--backbone",
        help="render only: train at a backbone other than the recipe's pinned one. The one "
        "value a joint judge cannot inherit, so the choice is worth being able to re-ask",
    )
    training.add_argument(
        "--run",
        help="name this run, so its checkpoint and records land in their own directory. "
        "What a seed band is made of; omit for the judge's one run",
    )
    training.set_defaults(handler=judge_train)

    reading = steps.add_parser(
        "score",
        help="score one side of a judge's corpus through a trained checkpoint",
        description=(
            "A score row carries its whole join — the place and the recipe that made the "
            "picture — plus the picture's own name, which is a digest of that recipe."
        ),
    )
    reading.add_argument("--head", required=True, help="which judge")
    reading.add_argument(
        "--kind",
        help="render only: read one label store's sheet rather than both",
    )
    reading.add_argument("--which", default="best", choices=["best", "last"])
    reading.add_argument("--side", default="eval", choices=["eval", "train"])
    reading.add_argument("--device", default="auto")
    reading.add_argument("--run", help="the named training run to score")
    reading.set_defaults(handler=judge_score)

    judging = steps.add_parser(
        "accept",
        help="read a trained judge against its pre-registered bar",
        description=(
            "The bar comes from the file and nothing here may invent one. Exits non-zero "
            "only on FAIL; BORDERLINE is a real answer and means the sheet could not "
            "resolve the question with one seed."
        ),
    )
    judging.add_argument("--head", required=True, help="which judge")
    judging.add_argument(
        "--run",
        action="append",
        help="a named run to judge (repeatable). More than one is the pre-registered "
        "escalation: the boundary is read on the MEDIAN run by its own statistic",
    )
    judging.set_defaults(handler=judge_accept)

    shipping = steps.add_parser(
        "ship",
        help="stage a judge's half-precision artifact and its manifest entry",
        description=(
            "Halves the weights, proves the artifact re-reads bit-identically, checks the "
            "shipped judge still orders its blind sheet the same way, hashes what was "
            "checked, and writes the manifest entry. Creating the release is a person's step."
        ),
    )
    shipping.add_argument("--head", required=True, help="which judge")
    shipping.add_argument("--which", default="best", choices=["best", "last"])
    shipping.add_argument("--tag", default="weights-v1", help="the release tag to name")
    shipping.add_argument("--device", default="auto")
    shipping.add_argument("--run", help="the named training run to ship")
    shipping.add_argument(
        "--force", action="store_true", help="ship a judge whose acceptance read failed"
    )
    shipping.set_defaults(handler=judge_ship)

    glancing = steps.add_parser(
        "glance",
        help="lay one batch's rows out under a candidate's ordering and the shipped one's",
        description=(
            "The read a band cannot give. A correction batch is anchored and train-side, so "
            "no rate quoted off it is a rate — what a person can still ask is whether the "
            "pictures come out in a better order. Two columns of the same rows, the pair of "
            "scores under each, and the rows that moved furthest either way. Lands in "
            "scratch/, decides nothing, and re-renders nothing."
        ),
    )
    glancing.add_argument(
        "--batch", required=True, help="the batch to lay out; a prefix, so a contrast arm comes too"
    )
    glancing.add_argument("--run", required=True, help="the candidate run to order by")
    glancing.add_argument("--which", default="best", choices=["best", "last"])
    # The default lives in the module and is resolved in the handler, not here:
    # this parser is built on the base install, where the module's import graph is
    # not available. `tests/test_base_install.py` is what says so.
    glancing.add_argument("--rows", type=int, help="rows per column (default: the module's, 12)")
    glancing.add_argument("--out", help="where the page lands (default: scratch/)")
    glancing.add_argument("--device", default="auto")
    glancing.set_defaults(handler=judge_glance)

    drawing = steps.add_parser(
        "disagreements",
        help="copy out the sheet rows the judge and a superseded head read most differently",
        description=(
            "Admissions and rejects, per kind: the rows where the shipped judge's "
            "probability at that sheet's own boundary sits furthest above the superseded "
            "head's, and the rows where it sits furthest below. Lands in scratch/, which is "
            "disposable."
        ),
    )
    drawing.add_argument("--run", help="the training run to read (default: the band's median)")
    drawing.add_argument(
        "--per-kind", type=int, default=6, help="rows per direction per kind (default: 6)"
    )
    drawing.add_argument("--out-dir", help="where the pictures land (default: scratch/)")
    drawing.set_defaults(handler=judge_disagreements)


def figure_commands(subcommands) -> None:
    """The figures the article needs that only this repository can draw."""
    group = subcommands.add_parser(
        "figures",
        help="draw a figure the article needs from this repository's own records",
        description=(
            "A figure here is a command rather than a saved picture: it is drawn from the "
            "tracked records and the shipped weights, so it can be redrawn when either "
            "moves. The pictures land under artifacts/, which is regenerable by definition."
        ),
    )
    steps = group.add_subparsers(dest="step", required=True)

    ladder = steps.add_parser(
        "judges-score-to-decision",
        help="one frame per outcome: refused, expandable, find, exceptional",
        description=(
            "Four held-out human-labeled locations of one family, one for each outcome the "
            "head's score lands in, each rendered as the canonical view the head read. The "
            "sidecar carries every frame's row key, the person's class and the head's own "
            "probabilities — the human label is shown, never used to choose the frame."
        ),
    )
    ladder.add_argument(
        "--family",
        default="julia:multibrot3",
        help="the partition to draw from (default: julia:multibrot3)",
    )
    ladder.add_argument("--head", default="location", help="which judge's ladder")
    ladder.add_argument("--run", help="a training run other than the shipped one")
    ladder.add_argument(
        "--coverage",
        action="store_true",
        help="print how every family's held-out rows spread across the four, and draw nothing",
    )
    ladder.add_argument(
        "--out-dir",
        help="where the frames land (default: artifacts/figures/judges_score_to_decision)",
    )
    ladder.set_defaults(handler=figure_score_to_decision)


def library_commands(subcommands) -> None:
    """The colormap library itself: where its maps came from, how they group, what they look like.

    Kept apart from `palette`, which is the *head* that chooses between maps.
    These are about the maps: nothing here loads a model, and the one that reads a
    label reads it only to decide which of two identical maps a record names.
    """
    group = subcommands.add_parser(
        "palettes",
        help="the colormap library: ingest, provenance, clusters, groups, and a map's gradient",
        description=(
            "The maps themselves, not the head that picks between them. `ingest` densifies "
            "a drop of authored palettes into the library, `provenance` rebuilds the record "
            "of how the made maps were made, `clusters` regroups the library into sixteen "
            "families, `groups` says which maps are near enough to be one choice, "
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

    grouping = steps.add_parser(
        "clusters",
        help="regroup the library and rewrite the tracked clustering",
        description=(
            "Ward's linkage over palette space, cut at sixteen, each cluster shown by its "
            "five most central maps. A pure function of the tracked library, which is what "
            "lets a test hold the committed file to this command's own output."
        ),
    )
    grouping.add_argument(
        "--clusters",
        type=int,
        default=palette_clusters.CLUSTERS,
        help=f"how many groups to cut the tree into (default: {palette_clusters.CLUSTERS})",
    )
    grouping.set_defaults(handler=palettes_clusters)

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


def palette_commands(subcommands) -> None:
    """The palette head, end to end: it is distilled, so it has two extra steps."""
    from fractal_wallpapers.models import palette_corpus

    group = subcommands.add_parser(
        "palette",
        help="the palette head end to end: extract, plan, build, label, train, ship",
        description=(
            "The one head this project does not train from human labels: there is no "
            "palette-preference corpus here to train it on, so it is distilled from the "
            "source project's pretrained head. Two steps exist that the other heads do not "
            "— vendoring the real candidate sets that head was really asked, and generating "
            "a corpus for it to answer — and both write text records the rest of the chain "
            "reads, so the head is regenerable from this repository forever."
        ),
    )
    steps = group.add_subparsers(dest="step", required=True)

    extracting = steps.add_parser(
        "extract",
        help="vendor the real candidate sets a production colorize run recorded",
        description=(
            "Rebuilds each set from the source's pool, its flavour table and the cap its "
            "release driver applies, and refuses to write anything unless every one of the "
            "recorded winners falls inside the set rebuilt for it. Brings across every map "
            "those sets name that this repository does not already hold."
        ),
    )
    extracting.add_argument("--source", required=True, help="the source repository's root")
    extracting.set_defaults(handler=palette_extract)

    planning = steps.add_parser(
        "plan",
        help="draw the distillation corpus: which places, which maps",
        description=(
            "Locations from this repository's own label corpus at the tiers that reach "
            "colorize, apportioned evenly across the partitions and capped by what each can "
            "supply; maps drawn from the shipped pool. Seeded end to end, and the vendored "
            "sets' own locations are excluded — they are the instrument."
        ),
    )
    planning.add_argument(
        "--sets", type=int, default=palette_corpus.SETS, help="how many candidate sets"
    )
    planning.add_argument(
        "--candidates", type=int, default=palette_corpus.CANDIDATES, help="maps per set"
    )
    planning.add_argument("--seed", type=int, default=palette_corpus.SEED, help="the draw's seed")
    planning.add_argument(
        "--hard-share",
        type=float,
        default=palette_corpus.HARD_SHARE,
        help="the share of sets built as palette-space neighbourhoods rather than uniform draws",
    )
    planning.set_defaults(handler=palette_plan)

    building = steps.add_parser(
        "build",
        help="render the candidate pictures",
        description=(
            "Resumable: a picture already on disk is skipped before its field is iterated, "
            "and a file is named for a digest of its own recipe, so two sets that draw the "
            "same map at the same place share one file."
        ),
    )
    building.add_argument(
        "--which",
        default="all",
        choices=["corpus", "sets", "all"],
        help="the distillation corpus, the vendored real sets, or both (default)",
    )
    building.add_argument("--limit", type=int, help="stop after this many pictures")
    building.set_defaults(handler=palette_build)

    labeling = steps.add_parser(
        "label",
        help="ask the teacher about every candidate and write the rows",
        description=(
            "The teacher is resolved through the source project's own single-source "
            "pointer and read on this repository's pictures. Every row carries its whole "
            "join, the teacher's score, and the sha256 of the weights that cast it."
        ),
    )
    labeling.add_argument("--source", required=True, help="the source repository's root")
    labeling.set_defaults(handler=palette_label)

    registering = steps.add_parser(
        "preregister",
        help="write the bar, before there is a head to judge against it",
        description=(
            "The bar is equivalence with the teacher on the real sets, and its calibrating "
            "number is declared as a rule rather than a value: the renderer control, which "
            "is how far the teacher already disagrees with its own recorded choices when "
            "the picture is made here instead of there."
        ),
    )
    registering.add_argument(
        "--force", action="store_true", help="overwrite a bar no head has been judged against"
    )
    registering.set_defaults(handler=palette_preregister)

    training = steps.add_parser(
        "train",
        help="distil one palette head from the teacher's labels",
        description=(
            "A batch is sixteen candidate SETS, because the loss centres inside a set. The "
            "epoch is chosen on the held-out distillation loss — a proper scoring rule for "
            "the vector being distilled — and never on a rank statistic."
        ),
    )
    training.add_argument("--device", default="auto", help="cuda, cpu, or auto (default)")
    training.add_argument("--epochs", type=int, help="override the recipe's epoch count")
    training.add_argument("--seed", type=int, help="override the recipe's seed")
    training.add_argument(
        "--listwise",
        type=float,
        help=(
            "weight of the listwise term beside the regression (0 is the regression alone). "
            "Its temperature is read off the corpus, never passed here"
        ),
    )
    training.add_argument(
        "--run", help="name this run, so its records land in their own directory: a seed band"
    )
    training.set_defaults(handler=palette_train_head)

    reading = steps.add_parser(
        "score",
        help="read the real candidate sets through the student and the teacher",
        description=(
            "Both readings on the same pictures, so what is compared is two functions and "
            "not two rendering pipelines. One row per set: the location, the candidates in "
            "order, both score vectors, and both picks."
        ),
    )
    reading.add_argument("--source", required=True, help="the source repository's root")
    reading.add_argument("--which", default="best", choices=["best", "last"])
    reading.add_argument("--device", default="auto")
    reading.add_argument("--run", help="the named training run to score")
    reading.set_defaults(handler=palette_score)

    judging = steps.add_parser(
        "accept",
        help="read the distilled head against its pre-registered bar",
        description=(
            "The bar comes from the file and nothing here may invent one. More than one "
            "--run is the seed band: the arms are read on the MEDIAN run by the top-pick "
            "statistic, never on the best of them."
        ),
    )
    judging.add_argument("--run", action="append", help="a named run to judge (repeatable)")
    judging.set_defaults(handler=palette_accept)

    shipping = steps.add_parser(
        "ship",
        help="stage the half-precision artifact and its manifest entry",
        description=(
            "The same cast, re-read and hash the other three heads ship through. What "
            "differs is the statistic: this head's decisions are top picks and its ordering "
            "is counted in discordant candidate pairs."
        ),
    )
    shipping.add_argument("--which", default="best", choices=["best", "last"])
    shipping.add_argument("--tag", default="weights-v1", help="the release tag to name")
    shipping.add_argument("--device", default="auto")
    shipping.add_argument("--run", help="the named training run to ship")
    shipping.add_argument(
        "--force", action="store_true", help="ship a head whose acceptance read failed"
    )
    shipping.set_defaults(handler=palette_ship)


def head_commands(subcommands) -> None:
    """A judge, end to end: pre-register the bar, train, score, judge, ship."""
    from fractal_wallpapers.models import release_floor as release_floor_module

    judging = subcommands.add_parser(
        "head",
        help="a judge end to end: preregister, train, score, accept, ship",
        description=(
            "The five steps are separate commands on purpose. Each writes a record the next "
            "one reads, so a training run can be re-scored and a score can be re-judged "
            "without any of it happening again — and so the bar is written down before the "
            "head it judges exists."
        ),
    )
    steps = judging.add_subparsers(dest="step", required=True)

    def with_head(parser):
        parser.add_argument("--head", default="location", help="which judge (default: location)")
        return parser

    registering = with_head(
        steps.add_parser(
            "preregister",
            help="write the bar, before there is a head to judge against it",
            description=(
                "Builds the bar out of the incumbent head's committed scores on this "
                "repository's own evaluation side, and out of how precisely that population "
                "can tell two heads apart at all. Refuses to overwrite an existing bar."
            ),
        )
    )
    registering.add_argument(
        "--force", action="store_true", help="overwrite a bar no head has been judged against"
    )
    registering.set_defaults(handler=head_preregister)

    training = with_head(steps.add_parser("train", help="train a head on the built tiles"))
    training.add_argument("--device", default="auto", help="cuda, cpu, or auto (default)")
    training.add_argument("--epochs", type=int, help="override the recipe's epoch count")
    training.add_argument("--seed", type=int, help="override the recipe's seed")
    training.add_argument(
        "--regime",
        action="append",
        metavar="WxHssN",
        help="a geometry to draw the tiles at, e.g. 640x360ss1 (repeatable). Every regime "
        "given adds a pass over the whole population to each epoch — the same label row, "
        "the same slot, a different geometry — and the head is told nothing about which "
        "one it is looking at. The canonical 640x360ss2 must be among them; omit the flag "
        "for it alone, which is the shipped recipe",
    )
    training.add_argument(
        "--selection",
        choices=["ap_ge2", "cutpoint_cross_entropy"],
        help="which objective chooses the epoch, over the training-side selection slice at "
        "the canonical regime (default: the recipe's own)",
    )
    training.add_argument(
        "--run",
        help="name this run, so its checkpoint and records land in their own directory. "
        "What a seed band is made of; omit for the head's one run",
    )
    training.set_defaults(handler=head_train)

    reading = with_head(
        steps.add_parser(
            "score",
            help="score one side of the build through a trained checkpoint",
            description=(
                "Every location goes through its canonical tile — the deploy view — so the "
                "number is the one a deployed judge would produce. A score row carries its "
                "whole join, the same rule a label row does."
            ),
        )
    )
    reading.add_argument("--which", default="best", choices=["best", "last"])
    reading.add_argument("--side", default="eval", choices=["eval", "train"])
    reading.add_argument("--device", default="auto")
    reading.add_argument("--run", help="the named training run to score (default: the head's own)")
    reading.add_argument(
        "--regime",
        default="640x360ss2",
        metavar="WxHssN",
        help="the geometry to read the pictures at (default: 640x360ss2, the deploy view). "
        "Anything else writes scores<regime>.jsonl beside the canonical read",
    )
    reading.set_defaults(handler=head_score)

    auditing = with_head(
        steps.add_parser(
            "audit",
            help="prove a run's record and its checkpoint are one trajectory",
            description=(
                "Two readings, and only the second settles anything. The clock reading "
                "compares wall_seconds against the sum of the epoch seconds and says what "
                "that can prove — which is less than it looks, because the wall starts "
                "after a resume loads and the history does not. The re-score reads the "
                "run's own selection slice back through its checkpoint and reproduces the "
                "record's best epoch, which needs no log and no clock. Writes audit.json "
                "beside the record."
            ),
        )
    )
    auditing.add_argument("--which", default="best", choices=["best", "last"])
    auditing.add_argument("--device", default="auto")
    auditing.add_argument("--run", help="the named training run to audit (default: the head's own)")
    auditing.set_defaults(handler=head_audit)

    flooring = steps.add_parser(
        "floor",
        help="fit a finished-render head's release floor off its own labels",
        description=(
            "Score every labeled picture of this head's corpus through the SHIPPED "
            "artifact, fit P(the human said >=3) against the head's own P(>=3) as a "
            "monotone curve, and read the lowest score whose fitted agreement reaches a "
            "half. The floor is that crossing rounded UP. Writes the value with the head "
            "sha, the row count, a place-clustered bootstrap interval and a hash of both "
            "inputs — and changes no cut: `curation.floors` owns every height that acts, "
            "and moving one there is a decision somebody takes after reading this. Where "
            "the head already has an acting bar this is a TEST of it, and exits non-zero "
            "when the re-fit does not reproduce the standing number."
        ),
    )
    flooring.add_argument(
        "--head",
        required=True,
        choices=sorted(FINISHED_HEADS),
        help="which finished-render judge to fit",
    )
    flooring.add_argument("--device", default="auto", help="cuda, cpu, or auto (default)")
    flooring.add_argument(
        "--bootstrap",
        type=int,
        default=release_floor_module.BOOTSTRAP,
        help=f"resamples in the place-clustered interval "
        f"(default: {release_floor_module.BOOTSTRAP}; 0 to skip it)",
    )
    flooring.set_defaults(handler=head_floor)

    judging_step = with_head(
        steps.add_parser(
            "accept",
            help="read a trained head against the pre-registered bar",
            description=(
                "The bar comes from the file and nothing here may invent one. Exits non-zero "
                "only on FAIL; BORDERLINE is a real answer and means the population could not "
                "resolve the question with one seed."
            ),
        )
    )
    judging_step.add_argument(
        "--run",
        action="append",
        help="a named run to judge (repeatable). More than one is the pre-registered "
        "escalation: each cutpoint is read on the MEDIAN run by its own statistic",
    )
    judging_step.set_defaults(handler=head_accept)

    shipping = with_head(
        steps.add_parser(
            "ship",
            help="stage the half-precision artifact and its manifest entry",
            description=(
                "Halves the weights, proves the artifact re-reads bit-identically, checks the "
                "shipped head still orders the evaluation side the same way, hashes what was "
                "checked, and writes the manifest entry. Creating the release is a person's "
                "step."
            ),
        )
    )
    shipping.add_argument("--which", default="best", choices=["best", "last"])
    shipping.add_argument("--tag", default="weights-v1", help="the release tag to name")
    shipping.add_argument("--device", default="auto")
    shipping.add_argument("--run", help="the named training run to ship (default: the head's own)")
    shipping.add_argument(
        "--force", action="store_true", help="ship a head whose acceptance read failed"
    )
    shipping.set_defaults(handler=head_ship)


def regime_preregister(args: argparse.Namespace) -> int:
    """Write the bar for the cross-regime study, before the candidate exists."""
    from fractal_wallpapers.models import regime_acceptance

    path = regime_acceptance.prereg_path(args.head)
    if path.is_file() and not args.force:
        print(f"{path} already exists. A bar rewritten after the numbers are in is not a bar;")
        print("amend it in place — the record carries an append-only list for that.")
        return 1
    bar = regime_acceptance.preregister(args.head)
    write_tracked_json(path, bar)
    print(json.dumps(bar, indent=2))
    return 0


def regime_accept(args: argparse.Namespace) -> int:
    """Read the candidate band against the pre-registered cross-regime bar."""
    from fractal_wallpapers.models import regime_acceptance

    report = regime_acceptance.read(args.head)
    write_tracked_json(regime_acceptance.acceptance_path(args.head), report)
    print(json.dumps(report, indent=2))
    return 0 if report["verdict"] != "FAIL" else 1


def flip_preregister(args: argparse.Namespace) -> int:
    """Write the second bar — flips on production stock — before any row is scored."""
    from fractal_wallpapers.models import regime_flips

    path = regime_flips.prereg_path(args.head)
    if path.is_file() and not args.force:
        print(f"{path} already exists. A bar rewritten after the numbers are in is not a bar;")
        print("amend it in place — the record carries an append-only list for that.")
        return 1
    bar = regime_flips.preregister(args.head)
    write_tracked_json(path, bar)
    print(json.dumps(bar, indent=2))
    return 0


def flip_score(args: argparse.Namespace) -> int:
    """Draw the stock, render it at every regime, and read every run over it."""
    from fractal_wallpapers.models import regime_flips

    report = regime_flips.score(
        head=args.head,
        limit=args.limit,
        workers=args.workers,
        device=args.device,
    )
    print(json.dumps(report, indent=2))
    return 0


def flip_read(args: argparse.Namespace) -> int:
    """Read the band against the second bar."""
    from fractal_wallpapers.models import regime_flips

    report = regime_flips.read(args.head)
    write_tracked_json(regime_flips.acceptance_path(args.head), report)
    print(json.dumps(report, indent=2))
    return 0 if report["verdict"] != "FAIL" else 1


#: Which pre-registered read authorizes a staging, by the population it was made
#: on. Two bars judge this candidate and they are not interchangeable: one is the
#: evaluation split, the other is production stock.
STAGING_READS = {"split": "regime_acceptance", "stock": "regime_flips"}


def regime_restate(args: argparse.Namespace) -> int:
    """Restate every cut the candidate's scale moves, against a fixed pool."""
    from fractal_wallpapers.models import adoption

    path = adoption.restatement_path(args.head)
    if path.is_file() and not args.force:
        print(f"{path} already exists, and the population it was measured against is the")
        print("shipped head's read of the sidecar — which a re-score replaces. Re-measuring")
        print("after a flip restates the candidate against itself.")
        return 1
    try:
        record = adoption.restate(head=args.head, device=args.device)
    except adoption.AdoptionError as refusal:
        print(refusal)
        return 1
    write_tracked_json(path, record)
    print(json.dumps(record, indent=2))
    return 0


def regime_adopt(args: argparse.Namespace) -> int:
    """Flip the shipped head to the staged candidate, at the restated cuts."""
    from fractal_wallpapers.models import adoption

    try:
        record = adoption.adopt(head=args.head, tag=args.tag or adoption.TAG)
    except adoption.AdoptionError as refusal:
        print(refusal)
        return 1
    write_tracked_json(adoption.adoption_path(args.head), record)
    print(json.dumps(record, indent=2))
    return 0


def regime_stage(args: argparse.Namespace) -> int:
    """Halve, verify and hash the winning seed — beside the shipped head."""
    import importlib

    from fractal_wallpapers.models import ship

    judge = importlib.import_module(f"fractal_wallpapers.models.{STAGING_READS[args.read]}")
    verdict_path = judge.acceptance_path(args.head)
    if not verdict_path.is_file():
        print(f"{verdict_path} is missing: nothing has judged this candidate on the")
        print(f"{args.read} population yet. Run the read that writes it first.")
        return 1
    judged = json.loads(verdict_path.read_text(encoding="utf-8"))
    if judged["verdict"] == "FAIL" and not args.force:
        print(f"the {args.read} read says {judged['verdict']}. Staging a candidate that")
        print("failed its own pre-registered bar needs --force and a sentence about why.")
        return 1
    chosen = judged["staged"]["seed"] if "staged" in judged else judged["gated_on"]
    record = ship.stage_candidate(
        name=args.head,
        which=args.which,
        run=args.run or chosen,
        device=args.device,
        why=args.why,
        verdict=verdict_path,
    )
    print(json.dumps({key: record[key] for key in record if key != "agreement"}, indent=2))
    return 0


def regime_commands(subcommands) -> None:
    """One head, three regimes: the bar, the read against it, the candidate."""
    studying = subcommands.add_parser(
        "regime",
        help="judge a location head's agreement with itself across rendering regimes",
        description=(
            "The shipped location head learned one geometry and is only honest there: read "
            "at a cheaper regime its scores fall, worst on multibrot3, far enough to cross "
            "the floors the supply engine acts on. These steps write a bar for a head "
            "trained over every cached regime at once, read a seed band against it, and "
            "stage the winner beside the shipped head. There are two bars and two "
            "populations: the first is read on the evaluation split, where most rows agree "
            "trivially, and the flip- steps re-ask the same question on production stock at "
            "the gates the supply engine acts on. Adopting the winner is the last two "
            "steps and is priced rather than assumed: a location retrain moves the scale "
            "every floor is calibrated against, so `restate` measures where those floors "
            "land on the new scale and `adopt` flips what serves."
        ),
    )
    steps = studying.add_subparsers(dest="step", required=True)

    def with_head(parser):
        parser.add_argument("--head", default="location", help="which judge (default: location)")
        return parser

    registering = with_head(
        steps.add_parser(
            "preregister",
            help="write the bar, before there is a candidate to judge against it",
            description=(
                "Two arms: the candidate must not be significantly worse than the shipped "
                "head at the canonical regime on the repository's proper scoring rule, and "
                "all four cross-regime consistency slices must significantly improve. "
                "Refuses to overwrite an existing bar — amendments are appended to it."
            ),
        )
    )
    registering.add_argument(
        "--force", action="store_true", help="overwrite a bar no candidate has been judged against"
    )
    registering.set_defaults(handler=regime_preregister)

    judging = with_head(
        steps.add_parser(
            "accept",
            help="read the candidate band against the pre-registered bar",
            description=(
                "Every arm is a paired cluster bootstrap over the evaluation side, read on "
                "the MEDIAN seed of the band by that arm's own statistic. Exits non-zero "
                "on FAIL."
            ),
        )
    )
    judging.set_defaults(handler=regime_accept)

    staging = with_head(
        steps.add_parser(
            "stage",
            help="halve, verify and hash the winning seed as a candidate artifact",
            description=(
                "The same cast, re-read, agreement check and hash a shipment gets, into "
                "<head>.candidate.fp16.pt beside the shipped artifact. It does NOT write "
                "the weights manifest, so no serving path resolves it: adopting a candidate "
                "is a separate decision with a separate price."
            ),
        )
    )
    staging.add_argument("--which", default="best", choices=["best", "last"])
    staging.add_argument("--device", default="auto")
    staging.add_argument(
        "--run", help="the run to stage (default: the seed the bar's selection rule chose)"
    )
    staging.add_argument("--why", default="", help="one sentence: what this candidate is for")
    staging.add_argument(
        "--read",
        default="split",
        choices=sorted(STAGING_READS),
        help=(
            "which pre-registered read authorizes this staging, by the population it was "
            "made on: the evaluation split, or production stock (default: split)"
        ),
    )
    staging.add_argument("--force", action="store_true", help="stage a candidate whose read failed")
    staging.set_defaults(handler=regime_stage)

    registering_flips = with_head(
        steps.add_parser(
            "flip-preregister",
            help="write the second bar: decision flips on production stock",
            description=(
                "The first bar was read on the evaluation split, where 78% of rows read "
                "below P(>=3)=0.05 at every geometry and agree trivially — three of its "
                "four slices could not clear zero. This one re-asks the consistency "
                "question on the population the motivating numbers came from, at the gates "
                "the supply engine actually acts on. Refuses to overwrite an existing bar."
            ),
        )
    )
    registering_flips.add_argument(
        "--force", action="store_true", help="overwrite a bar no candidate has been judged against"
    )
    registering_flips.set_defaults(handler=flip_preregister)

    reading = with_head(
        steps.add_parser(
            "flip-score",
            help="draw the stock, render it at every regime, and read every run over it",
            description=(
                "The draw is the bar's: its size and its seed come out of the "
                "pre-registration, and every location the label store holds is excluded. "
                "Renders are reused, so a re-run costs the engine nothing it already paid."
            ),
        )
    )
    reading.add_argument(
        "--limit",
        type=int,
        help=(
            "read a prefix of the draw. The rehearsal a render budget is estimated from: "
            "it writes no verdict and the read refuses a population smaller than the bar's"
        ),
    )
    reading.add_argument(
        "--workers",
        type=int,
        help=(
            "render worker processes (default: the scorer's own, which is one — a single "
            "view already spends the whole machine, and every fan-out arm measures slower)"
        ),
    )
    reading.add_argument("--device", default="auto")
    reading.set_defaults(handler=flip_score)

    judging_flips = with_head(
        steps.add_parser(
            "flip-read",
            help="read the band against the second bar",
            description=(
                "A paired bootstrap over LOCATIONS — stock has no neighbourhood groups — on "
                "the seed the training-side selection rule froze. Exits non-zero on FAIL."
            ),
        )
    )
    judging_flips.set_defaults(handler=flip_read)

    restating = with_head(
        steps.add_parser(
            "restate",
            help="restate every cut the candidate's scale moves, before anything flips",
            description=(
                "The junk floor, the good floor and the great cut are points on the shipped "
                "head's probability scale and say nothing on another head's. Each is "
                "restated as the candidate score passing the SAME FRACTION of a fixed "
                "reference pool — the whole curation sidecar, read through the pictures its "
                "own scores were taken off. Refuses once the flip has happened: the "
                "fractions are the retired head's reads, and a re-score replaces them."
            ),
        )
    )
    restating.add_argument("--device", default="auto")
    restating.add_argument(
        "--force", action="store_true", help="overwrite a restatement nothing has flipped against"
    )
    restating.set_defaults(handler=regime_restate)

    adopting = with_head(
        steps.add_parser(
            "adopt",
            help="flip the shipped head to the staged candidate, at the restated cuts",
            description=(
                "Ships the candidate under the head's own asset name and checks that what "
                "landed is the artifact the two bars judged. Refuses unless the restatement "
                "is already recorded AND the modules that own the cuts already declare it — "
                "which is the refusal the cuts themselves would make on their first call, "
                "taken one step earlier."
            ),
        )
    )
    adopting.add_argument(
        "--tag", default=None, help="the release tag to name (default: the head's next one)"
    )
    adopting.set_defaults(handler=regime_adopt)


def storage_archive(args: argparse.Namespace) -> int:
    """Move a finished subtree to slow bulk storage."""
    from fractal_wallpapers import storage
    from fractal_wallpapers.paths import ARCHIVE

    print(json.dumps(storage.move(args.subtree, to=ARCHIVE), indent=2))
    return 0


def storage_restore(args: argparse.Namespace) -> int:
    """Bring an archived subtree back to where work happens."""
    from fractal_wallpapers import storage
    from fractal_wallpapers.paths import HOT

    print(json.dumps(storage.move(args.subtree, to=HOT), indent=2))
    return 0


def storage_status(args: argparse.Namespace) -> int:
    """One screen: every subtree, its tier, its size."""
    from fractal_wallpapers import storage

    report = storage.status(sizes=not args.no_sizes)
    print(f"hot     {report['hot']}")
    archive = report["archive"] or "(none configured)"
    print(f"archive {archive}{'' if report['archive_reachable'] else '   NOT REACHABLE'}")
    if report["archive"] and not report["archive_reachable"]:
        print("        Only the hot tier is listed below; archived subtrees are not shown.")
    print()
    totals: dict[str, list[int]] = {}
    for row in report["units"]:
        if row["tier"] == "BOTH":
            print(f"{row['name']:<28} BOTH TIERS — {row['collision']}")
            continue
        counted = totals.setdefault(row["tier"], [0, 0])
        counted[0] += row.get("files", 0)
        counted[1] += row.get("bytes", 0)
        size = (
            ""
            if args.no_sizes
            else f"{row['files']:>10,} files  {storage.bytes_said_plainly(row['bytes']):>12}"
        )
        print(f"{row['name']:<28} {row['tier']:<8}{size}")
    if not args.no_sizes:
        print()
        for tier, (files, size) in sorted(totals.items()):
            print(f"{tier:<28} {'':<8}{files:>10,} files  {storage.bytes_said_plainly(size):>12}")
    return 0


def deep_commands(subcommands) -> None:
    """`deep roots` and `deep walk`: the run mode for the release-stock tail."""
    from fractal_wallpapers.deep import depth
    from fractal_wallpapers.deep import run as deep_module

    diving = subcommands.add_parser(
        "deep",
        help="the deep run mode: source, score and record below the shallow walk's floor",
        description=(
            f"A separate sourcing mode for the tail the ordinary walk cannot reach. Its "
            f"floor is {depth.MIN_WIDTH:.0e} against the shallow walk's "
            f"{depth.SHALLOW_MIN_WIDTH:.0e}, and depth comes from WHICH ATOM it stands on "
            f"rather than from how far it descended: a seat is a nucleus whose own framing "
            f"band already lands below the shallow floor. Pure f64 end to end - there is no "
            f"perturbation kernel here - so a seat is refused up front unless f64 still "
            f"resolves its money shot at release geometry. Release the ledger it writes "
            f"with `curate run --deep --harvest <out-dir>`, which swaps in this mode's own "
            f"hung-unit ceilings."
        ),
    )
    steps = diving.add_subparsers(dest="step", required=True)

    def seat_flags(parser):
        parser.add_argument(
            "--seats",
            type=int,
            default=None,
            help=f"nuclei this run stands on. THE budget lever of this mode. Left unset it "
            f"is sized from --wall-budget where there is one, and is "
            f"{deep_module.DEFAULT_SEATS} where there is not",
        )
        parser.add_argument(
            "--newton-share",
            type=float,
            default=deep_module.Limits().newton_share,
            help="share of the seats the Newton channel is asked for first; whatever it "
            "cannot fill the continuation channel does, in the same call",
        )
        parser.add_argument(
            "--anchors",
            type=int,
            default=deep_module.Limits().anchors_per_family,
            help="plane-seed atoms per family a Newton ladder may start from, deepest first",
        )
        parser.add_argument("--seed", type=int, default=0, help="run seed (default: 0)")
        return parser

    sourcing = seat_flags(
        steps.add_parser(
            "roots",
            help="fill the seats and print them, standing on none of them",
            description=(
                "Both channels. `newton` tracks the boundary down from a tracked plane-seed "
                "atom, one Newton solve per rung at the precision the atom itself asks for, "
                "until an atom's band lands in this mode's window; `continuation` takes "
                "places earlier ledgers already admitted at the shallow floor. Every miss "
                "is counted with the reason, and every ladder is printed whether or not it "
                "arrived."
            ),
        )
    )
    sourcing.add_argument("--out", help="also write one seat per line to this JSONL file")
    sourcing.set_defaults(handler=deep_roots)

    walking = seat_flags(
        steps.add_parser(
            "walk",
            help="source the seats, stand on them, and record every fate",
            description=(
                "The shipped location head judges, at its own existing floors, with no "
                "deep-specific gate and no deep-specific calibration - it has seen nothing "
                "below 1.8e-10, so what this run buys is the record of what it said, at "
                "every fate, about material two decades below where it was trained."
            ),
        )
    )
    walking.add_argument(
        "--batch", type=int, default=deep_module.Limits().batch, help="nodes expanded per batch"
    )
    walking.add_argument(
        "--batches",
        type=int,
        default=None,
        help=f"batches to run. Left unset it is sized from the seats - a generous ceiling, "
        f"since the frontier empties long before it binds - and is {deep_module.DEFAULT_BATCHES} "
        f"for an unbudgeted run",
    )
    walking.add_argument(
        "--root-expansions",
        type=int,
        default=deep_module.Limits().root_expansions,
        help="expansions any one seat's roots may pay for",
    )
    walking.add_argument(
        "--wall-budget",
        type=float,
        metavar="SECONDS",
        help="size the seating against this, and stop cleanly rather than start a batch that "
        "would overrun it. Covers this run AND the evaluation frames that follow it: a "
        "seat is priced sourcing + walk + evaluation off deep_run1's measurements, so eight "
        "hours buys about 184 seats where that run took 32 and spent a quarter of its clock",
    )
    walking.add_argument(
        "--no-evaluation-reserve",
        action="store_true",
        help="a WALK-ONLY run: price a seat at sourcing and walk alone and let the budget "
        "buy far more of them. Not a saving - a run that takes this and then draws a "
        "frames anyway has no budget for them",
    )
    reseating = walking.add_mutually_exclusive_group()
    reseating.add_argument(
        "--reseat",
        dest="reseat",
        action="store_true",
        default=None,
        help="source again into the same run when the frontier empties with budget left "
        "(on by default, and inert without --wall-budget)",
    )
    reseating.add_argument(
        "--no-reseat",
        dest="reseat",
        action="store_false",
        help="stop when the frontier empties, whatever the budget has left",
    )
    walking.add_argument(
        "--lineage-cap",
        type=int,
        default=deep_module.LINEAGE_ADMISSIONS,
        help=f"admissions any one lineage may book before the walk stops expanding it "
        f"(default: {deep_module.LINEAGE_ADMISSIONS}; 0 turns the cap off). deep_run1 put "
        f"741 admissions on 15 of its 48 roots and 85 on one, and its floor frames were "
        f"largely one composition. Nothing is retro-refused: expansion stops, fates stand",
    )
    walking.add_argument(
        "--node-width",
        type=int,
        default=384,
        help="node render width in pixels; a scored run refuses any other",
    )
    walking.add_argument(
        "--colormap", default="twilight_shifted", help="colormap the gate renders are drawn through"
    )
    walking.add_argument(
        "--out-dir",
        default=str(Path("artifacts") / "deep"),
        help="where the ledger and thumbnails go (default: artifacts/deep)",
    )
    scoring_flags(walking)
    walking.set_defaults(handler=deep_walk)


def storage_commands(subcommands) -> None:
    """The two tiers: what is where, and moving a subtree between them."""
    storing = subcommands.add_parser(
        "storage",
        help="the hot and archive tiers: what is where, and moving a subtree between them",
        description=(
            "The regenerable tree lives on two disks. Work happens hot, on the fast one, "
            "and every write lands there; a subtree nothing is using archives to the slow "
            "one and reads through from there until it is restored. A subtree is in exactly "
            "one tier at a time, and which one is simply where its files are — there is no "
            "registry to fall out of step. Every move copies, verifies, and only then "
            "deletes the source."
        ),
    )
    steps = storing.add_subparsers(dest="step", required=True)

    def with_subtree(parser):
        parser.add_argument(
            "subtree",
            help="a top-level name of the artifacts tree, as `storage status` lists it",
        )
        return parser

    archiving = with_subtree(
        steps.add_parser(
            "archive",
            help="move a finished subtree to slow bulk storage",
            description=(
                "For a subtree nothing is actively reading. It stays readable — every name "
                "under it resolves through to the archive — but a random small-file read "
                "pattern over it is an order of magnitude slower, which is why the trainers "
                "refuse to run against one."
            ),
        )
    )
    archiving.set_defaults(handler=storage_archive)

    restoring = with_subtree(
        steps.add_parser(
            "restore",
            help="bring an archived subtree back to where work happens",
            description=(
                "The step before a retrain. Measured against a USB hard drive this is tens "
                "of minutes for a large cache, and it says so with an estimate before it "
                "starts rather than after."
            ),
        )
    )
    restoring.set_defaults(handler=storage_restore)

    showing = steps.add_parser(
        "status",
        help="every subtree, its tier and its size",
    )
    showing.add_argument(
        "--no-sizes",
        action="store_true",
        help="tiers only. Walking a million files for their sizes is minutes on the archive",
    )
    showing.set_defaults(handler=storage_status)


def coloring_commands(subcommands) -> None:
    """The tone band, and the operator that projects onto it."""
    colouring = subcommands.add_parser(
        "coloring",
        help="the tone band and the autolevel operator: show it, derive it",
        description=(
            "The autolevel operator pulls a render's tone onto a band of finished "
            "wallpapers that are already good, or — when it is already inside the band — "
            "leaves it exactly alone and hands back the render's own bytes."
        ),
    )
    steps = colouring.add_subparsers(dest="step", required=True)

    showing = steps.add_parser("show", help="print the switch and the band it projects onto")
    showing.set_defaults(handler=coloring_show)

    deriving = steps.add_parser(
        "derive-band",
        help="measure a reference set of finished wallpapers and derive the band",
        description=(
            "Reads a folder of finished wallpapers and writes the tracked band record. The "
            "folder is only ever read, and what ships is the measurement plus the names it "
            "was taken over — never a path. A re-derivation that moves an edge is a new band "
            "and therefore a new decision, which is why it needs --write."
        ),
    )
    deriving.add_argument(
        "--from",
        dest="source",
        required=True,
        help="a folder of finished wallpapers, read only",
    )
    deriving.add_argument("--write", action="store_true", help="write it; otherwise print it")
    deriving.set_defaults(handler=coloring_derive_band)


def curate_commands(subcommands) -> None:
    """The last stage: harvest supply in, released wallpapers out."""
    import math

    from fractal_wallpapers.curation import below_bar as below_bar_module
    from fractal_wallpapers.curation import budget as budget_module
    from fractal_wallpapers.curation import colors as colors_module
    from fractal_wallpapers.curation import embeddings as embeddings_module
    from fractal_wallpapers.curation import framing as framing_module
    from fractal_wallpapers.curation import gallery as gallery_module
    from fractal_wallpapers.curation import run as run_module

    curating = subcommands.add_parser(
        "curate",
        help="make a release: score the supply, colorize, select, render at full size",
        description=(
            "The end-to-end path. Every step is bound to the ledgers it reads — name them "
            "with --ledger, or name the harvest that wrote them with --harvest; nothing "
            "defaults to all of them. `score` reads the bound ledgers through the location "
            "head into a sidecar this stage owns, upserting one binding's rows without "
            "touching another's and never rewriting a ledger; `plan` prints the offer and "
            "the budget it implies without making a picture; and `run` does the whole thing, "
            "records its binding in its own plan, and records every decision."
        ),
    )
    steps = curating.add_subparsers(dest="step", required=True)

    reading = ledger_flags(
        steps.add_parser(
            "score",
            help="read the harvest ledgers through the location head",
            description=(
                "Reads each gate-surviving location through the head, at the regime its own "
                "ledger row names: a walk's gate render where the row's recorded digest still "
                "describes it, the deploy view already on disk for the standing stock. No "
                "deploy-geometry render is ever demanded for a row that was not scored at one. "
                "Resumable in both halves: a picture already on disk is not re-made."
            ),
        )
    )
    reading.add_argument("--device", default="auto", help="cuda, cpu, or auto (default)")
    reading.add_argument("--limit", type=int, help="score only this many locations")
    reading.add_argument(
        "--key-file",
        metavar="PATH",
        help="score only the locations this key manifest names, out of the bound ledgers "
        "(`curate reach --write` writes one). Like --limit it is a partial pass, so it "
        "upserts what it looked at and clears nothing",
    )
    reading.set_defaults(handler=curate_score)

    sidecar = steps.add_parser(
        "sidecar",
        help="the supply sidecar's durability: record it, check it, restore it",
        description=(
            "artifacts/curation/supply_scores.jsonl is the head's read of the standing "
            "supply and the one file under the regenerable tree that the checkout cannot "
            "regenerate — the ledgers it reads are under that tree too. It is too big and "
            "too churny to track, so what the history keeps is a manifest: the row count, "
            "the byte count, the sha256 and the per-ledger split. `save` writes a copy to "
            "the archive tier and records it; `check` reads the live file against the "
            "manifest; `restore` brings the copy back, counted before it is believed."
        ),
    )
    sidecar.add_argument(
        "what",
        choices=["check", "save", "restore"],
        help="check the live file against the manifest, save a fresh copy and manifest, "
        "or restore the copy",
    )
    sidecar.add_argument(
        "--force",
        action="store_true",
        help="with `restore`: overwrite a live sidecar that holds MORE rows than the "
        "manifest records. Those rows are a harvest nobody has saved yet",
    )
    sidecar.set_defaults(handler=curate_sidecar)

    mass_sweep = steps.add_parser(
        "mass-sweep",
        help="the colour-mass sweep log's durability: record it, check it, restore it",
        description=(
            "artifacts/curation/palette_mass_sweep/rows.jsonl is the 25.7 MB experiment log "
            "the tracked colour-mass map was cut from: one row per (palette group, mode, "
            "location) with its 48-cell vector, its recipe and whether autolevel acted. It "
            "is insurance rather than a record anything reads — what production reads is "
            "the map under data/palettes/color_mass/ — and it is the only thing that would "
            "let the map be re-cut on other terms. Re-deriving it is 8.7 h of wall over "
            "27,053 renders whose pictures were deleted, so the bytes go to the archive "
            "tier and the history keeps the manifest."
        ),
    )
    mass_sweep.add_argument(
        "what",
        choices=["check", "save", "restore"],
        help="check the live log against the manifest, save a fresh copy and manifest, "
        "or restore the archived copy",
    )
    mass_sweep.add_argument(
        "--force",
        action="store_true",
        help="with `restore`: overwrite a live log that holds MORE rows than the manifest records",
    )
    mass_sweep.set_defaults(handler=curate_mass_sweep)

    on_demand = steps.add_parser(
        "on-demand",
        help="reconcile a pass's on-demand log with its attempt store",
        description=(
            "An on-demand pick is the extra picture a seat asks for when the colour ceiling "
            "refuses everything the plan offered, and it is a pool row like any other. Two "
            "things went wrong with that and both are repaired here, from the candidate "
            "each pick was asked beside: the log carries `ledger: null` on every row written "
            "before the renderer started carrying it across, and gallery3's picks never "
            "reached the attempt store at all, so no reader of the pool can see them. "
            "Records only — nothing is rendered, and a second run writes identical bytes."
        ),
    )
    on_demand.add_argument("--pass", dest="pass_id", required=True, help="the pass id")
    on_demand.add_argument(
        "--dry-run",
        action="store_true",
        help="say what would be filled and how many store rows would be added, writing nothing",
    )
    on_demand.add_argument("--quiet", action="store_true", help="do not print progress")
    on_demand.set_defaults(handler=curate_on_demand)

    redrawing = steps.add_parser(
        "redraw",
        help="re-render every stale location view and amend the score read off it",
        description=(
            "A standing seating score is a reading of a picture, and the sidecar row names "
            "which picture. For tens of thousands of rows that name no longer describes "
            "anything: the view was drawn at a geometry the read no longer uses, under a "
            "recipe whose digest has since moved, or by an engine build nobody wrote down — "
            "and the build is not in the digest, so nothing before this could ask. This "
            "re-renders every stale view at the node regime, reads it through the shipped "
            "location head, and appends the result to an APPEND-ONLY amendment keyed by "
            "(location key, engine fingerprint). The sidecar is never edited. Every reader "
            "of a seating score prefers the amendment from the moment it lands. Serial "
            "(the engine threads inside one render) at about 0.03 s a view, so a whole "
            "supply is the best part of an hour; idempotent and resumable."
        ),
    )
    redrawing.add_argument(
        "--limit",
        type=int,
        help="stop after this many stale locations. A smoke leg, not a scoping flag: the "
        "amendment is append-only, so a limited pass amends a prefix and leaves the rest "
        "stale rather than declaring them current",
    )
    redrawing.add_argument(
        "--no-resume",
        action="store_true",
        help="re-read locations this engine build has already amended. Off by default, "
        "which is what makes an interrupted refresh cheap to finish",
    )
    redrawing.add_argument("--device", default="auto", help="cuda, cpu, or auto (default)")
    redrawing.set_defaults(handler=curate_redraw)

    drawing = steps.add_parser(
        "draw",
        help="step 4 alone: which locations a pass would choose, claiming nothing",
        description=(
            "The point draw and nothing else — no attempts, no renders, no pass id, no row "
            "written anywhere. `gallery --no-attempts` is the affordance for iterating on a "
            "pass; this is the one for COMPARING two selections, which needs a selection "
            "that claims nothing so the two can be taken over the same pool in either "
            "order. --no-amended takes the draw over the sidecar as it stands rather than "
            "over `curate redraw`'s re-read of it, and the difference between the two "
            "chosen sets is the entry bias the stale readings were buying."
        ),
    )
    drawing.add_argument(
        "-n",
        "--n",
        type=int,
        default=gallery_module.DEFAULT_N,
        help=f"locations to choose (default: {gallery_module.DEFAULT_N})",
    )
    drawing.add_argument("--radius", type=float, default=gallery_module.RADIUS)
    drawing.add_argument("--quality-weight", type=float, default=gallery_module.QUALITY_WEIGHT)
    drawing.add_argument("--strange-share", type=float, default=run_module.STRANGE_SHARE)
    drawing.add_argument(
        "--draw-seed",
        type=int,
        default=gallery_module.DEFAULT_SEED,
        help=f"the ROOT seed the draw runs under (default: {gallery_module.DEFAULT_SEED}). "
        f"Fixed rather than drawn, unlike a pass: a dry selection exists to be compared "
        f"with another one, and a comparison needs both sides on the same seed",
    )
    drawing.add_argument(
        "--draw-top-k",
        type=int,
        default=gallery_module.DRAW_TOP_K,
        metavar="K",
        help=f"how many of a partition's strongest locations the first pick is drawn from "
        f"(default: {gallery_module.DRAW_TOP_K}; 1 is the argmax draw gallery1 through "
        f"gallery3 took)",
    )
    drawing.add_argument(
        "--no-amended",
        action="store_true",
        help="draw over the sidecar's standing scores rather than the amendment",
    )
    drawing.add_argument(
        "--out",
        help="write the chosen set here as JSON as well as printing the summary",
    )
    drawing.set_defaults(handler=curate_draw)

    embedding_step = steps.add_parser(
        "embed",
        help="one DINOv2 vector per admitted location, from a neutral render",
        description=(
            "The gallery pass picks locations by how far apart they look, so every location "
            "the judge admits over the junk floor needs one picture that says nothing about "
            "a coloring nobody has chosen yet: the NEUTRAL RENDER, this location's smooth "
            "field through one fixed cyclic map at one fixed small geometry. A frozen DINOv2 "
            "reads a unit vector off it and the vector is kept forever, keyed by the exact "
            "location key. Incremental and idempotent: what is already stored is subtracted "
            "before anything is drawn, so a later harvest's admissions are a second run of "
            "this. Exits non-zero when the store does not cover the admitted population."
        ),
    )
    embedding_step.add_argument("--device", default="auto", help="cuda, cpu, or auto (default)")
    embedding_step.add_argument(
        "--sample",
        type=int,
        help="embed a stratified draw of this many outstanding locations rather than all of "
        "them, spread over the partitions in proportion to their supply. The pilot",
    )
    embedding_step.add_argument(
        "--limit", type=int, help="stop after this many locations; a prefix, not a sample"
    )
    embedding_step.add_argument(
        "--seed",
        type=int,
        default=embeddings_module.SAMPLE_SEED,
        help=f"the seed --sample draws under (default: {embeddings_module.SAMPLE_SEED})",
    )
    embedding_step.add_argument(
        "--unit-seconds",
        type=float,
        default=embeddings_module.UNIT_SECONDS,
        help=f"kill one neutral render that runs past this and carry on "
        f"(default: {embeddings_module.UNIT_SECONDS:g})",
    )
    embedding_step.set_defaults(handler=curate_embed)

    embedding_store = steps.add_parser(
        "embeddings",
        help="the embedding store's durability: record it, check it, restore it",
        description=(
            "The vectors cost a pass of the encoder over every admitted location and their "
            "input lives under the regenerable tree, so the store gets what the supply "
            "sidecar gets: a copy on the archive tier, a tracked manifest carrying the row "
            "count, the bytes, the sha256 and the frozen choices every vector was made "
            "under, and a restore that counts before it believes. The neutral JPEGs are not "
            "copied: every row carries the join its own picture re-renders from."
        ),
    )
    embedding_store.add_argument(
        "what",
        choices=["check", "save", "restore"],
        help="check the live store against the manifest, save a fresh copy and manifest, "
        "or restore the copy",
    )
    embedding_store.add_argument(
        "--force",
        action="store_true",
        help="with `restore`: overwrite a live store that holds MORE rows than the manifest "
        "records. Those rows are admissions nobody has saved yet",
    )
    embedding_store.set_defaults(handler=curate_embeddings)

    neighbouring = steps.add_parser(
        "neighbours",
        help="nearest neighbours by cosine in the embedding store, with their pictures",
        description=(
            "The sanity read, and it does not settle anything by itself: it names the "
            "neutral JPEGs of a few random locations and of whatever the store says is "
            "nearest to each, so a person can open them and see whether near means alike."
        ),
    )
    neighbouring.add_argument("-k", type=int, default=3, help="neighbours per row (default: 3)")
    neighbouring.add_argument("--sample", type=int, default=10, help="rows to read (default: 10)")
    neighbouring.add_argument(
        "--seed",
        type=int,
        default=embeddings_module.SAMPLE_SEED,
        help=f"the seed the rows are drawn under (default: {embeddings_module.SAMPLE_SEED})",
    )
    neighbouring.set_defaults(handler=curate_neighbours)

    reaching = steps.add_parser(
        "reach",
        help="which judged locations the gallery pass cannot select, and why",
        description=(
            "The gallery pass selects over the ADMITTED population — every location the "
            "location judge puts over the junk floor — and the accumulated pool is a "
            "different set. A judged location outside the admitted one cannot be chosen, "
            "however good the wallpaper somebody already made of it, and there are two ways "
            "for that to happen: today's head reads it below the junk floor, which is a "
            "judgement, or the supply sidecar has no row for it at all, which is not a "
            "judgement about anything. The second is a location whose ledger was never "
            "scored into the sidecar."
        ),
    )
    reaching.add_argument(
        "--keys", action="store_true", help="print every location key, not only the counts"
    )
    reaching.add_argument(
        "--write",
        metavar="PATH",
        help="write the locations with NO sidecar row at all as a key manifest, which "
        "`curate score --key-file` reads back. The other cause - below the junk floor - is a "
        "judgement and not a gap, so it is never written here",
    )
    reaching.set_defaults(handler=curate_reach)

    naming_ledgers = steps.add_parser(
        "ledgers",
        help="which walk ledger each released row names, and whether it still resolves",
        description=(
            "Provenance, not a repair. A released row carries its whole join and re-renders "
            "from itself, so a row whose ledger has gone is still a wallpaper somebody can "
            "rebuild — what it cannot be is re-OFFERED, because an intake starts from "
            "ledgers. Resolution goes through the same tier funnel every reader uses, so a "
            "ledger that has merely been archived reads as present."
        ),
    )
    naming_ledgers.add_argument(
        "--write",
        action="store_true",
        help="write the tracked provenance record as well as printing it",
    )
    naming_ledgers.set_defaults(handler=curate_ledgers)

    rereading = steps.add_parser(
        "rescore",
        help="read every candidate the pool holds through today's finished-render heads",
        description=(
            "Not `score`, which reads LOCATIONS through the location head over the walk "
            "ledgers. This reads the accumulated pool's own candidate renders — "
            "pictures/NNNN.jpg, 640x360, the picture each gate decision was taken on — "
            "through whichever finished-render head owns each row, at the artifact shipped "
            "now. The run's own scores are left exactly as they are, as that night's "
            "provenance; the reading lands in a `scores_current` block carrying the head "
            "sha. Rows judged by a retired head gain the cutpoints it never had."
        ),
    )
    rereading.add_argument("--device", default="auto", help="cuda, cpu, or auto (default)")
    rereading.set_defaults(handler=curate_rescore)

    def with_shape(parser, defaults=True):
        # A run takes `None` where `plan` takes a number: a resumed run reads its
        # shape back out of its own sidecar, and a flag that defaulted to 6 here
        # could not be told from a flag that asked for 6.
        parser.add_argument(
            "-n",
            type=int,
            default=run_module.DEFAULT_N if defaults else None,
            help=f"release slots to fill (default: {run_module.DEFAULT_N}, or the resumed "
            f"run's own). A run's release is a DIAGNOSTIC — enough pictures to see that the "
            f"path works — and not a claim about what is worth shipping, which is a decision "
            f"over the whole accumulated pool",
        )
        parser.add_argument(
            "--strange-share",
            type=float,
            default=run_module.STRANGE_SHARE if defaults else None,
            help=f"share of the slots the strange judge fills "
            f"(default: {run_module.STRANGE_SHARE:g})",
        )
        parser.add_argument(
            "--strange-modes",
            type=int,
            default=None,
            help=f"modes the strange judge draws at each location it pays for "
            f"(default: {budget_module.MODES_PER_LOCATION[budget_module.STRANGE]}). The "
            f"smooth judge always draws one: the smooth coloring is the only mode it owns "
            f"and a second draw would render the same picture",
        )
        parser.add_argument(
            "--attempts", type=int, help="cap the total colorize attempts; omit for the multiple"
        )
        return parser

    planning = with_shape(
        ledger_flags(
            steps.add_parser(
                "plan",
                help="print the offer and the budget it implies, making nothing",
            )
        )
    )
    planning.set_defaults(handler=curate_plan)

    running = with_shape(
        ledger_flags(
            steps.add_parser(
                "run",
                help="make a release and record every decision",
                description=(
                    "Full resolution is the expensive part — measure one before asking for "
                    "many. Nothing is padded or backfilled: a judge that cannot fill its "
                    "quota under the slot and supply caps, the acting bar, and the "
                    "one-wallpaper-per-location rule ships fewer, and says so. "
                    "A long run wants --wall-budget: it stops cleanly at the last unit it "
                    "can afford rather than finding out afterwards, and --resume continues "
                    "an interrupted one from what it finished."
                ),
            )
        ),
        defaults=False,
    )
    naming = running.add_mutually_exclusive_group(required=True)
    naming.add_argument("--run", help="the name this run's records carry")
    naming.add_argument(
        "--resume",
        metavar="RUN",
        help="continue an interrupted run: its finished attempts and release renders are "
        "skipped, and its shape is read back from its own plan rather than from these flags",
    )
    running.add_argument("--seed", type=int, help="run seed (default: 0)")
    running.add_argument(
        "--wall-budget",
        type=float,
        metavar="SECONDS",
        help="stop cleanly rather than start a unit of work that would overrun this. Covers "
        "the whole run, intake through the last release render",
    )
    running.add_argument(
        "--workers",
        type=int,
        default=3,
        help="worker processes for the full-resolution pass (1 is the serial path)",
    )
    running.add_argument("--device", default="auto", help="cuda, cpu, or auto (default)")
    running.add_argument(
        "--ephemeral",
        action="store_true",
        help="redirect the WHOLE record store under scratch/. A rehearsal that writes the "
        "durable store adds rows a later calibration pass cannot tell from a release's",
    )
    running.add_argument(
        "--skip-release",
        action="store_true",
        help="reuse the full-resolution pictures already on disk instead of rendering "
        "(with --resume: the pictures are this run's own, from before it was interrupted)",
    )
    running.add_argument(
        "--deep",
        action="store_true",
        help="hold this run to the deep mode's hung-unit ceilings instead of the shallow "
        "ones. A deep release frame was measured at 607s against a shallow distribution "
        "whose median is 87.8s, and the backstop only ever raises itself off units a run "
        "has FINISHED - so a deep row killed at the shallow colorize ceiling never teaches "
        "the run that its class is slow",
    )
    running.set_defaults(handler=curate_run)

    gallerying = steps.add_parser(
        "gallery",
        help="one pass over the whole pool: choose N wallpapers and render them",
        description=(
            "THE second phase. A run accumulates candidates and keeps a small diagnostic "
            "release; this chooses what the collection ships, once, over everything the pool "
            "holds. Slots per partition come off the release mix over a pool-wide "
            "denominator; the locations come off a quality-weighted farthest-point draw with "
            "a hard cosine radius over the neutral-render embeddings; each chosen point buys "
            "a small judged attempt on its own neighbourhood; and the winners are rendered "
            "at full size. Both measured floors ACT here, and a slot with nothing above its "
            "head's floor is output UNFILLED with the reason named - unfilled beats padded, "
            "because an empty slot is the signal for where to label or walk next. Each "
            "invocation is a PASS with its own id and its own record; a new pass supersedes "
            "the previous gallery and deletes nothing."
        ),
    )
    gallerying.add_argument(
        # Both spellings. `-n` is what every other count in this CLI is called and
        # `--n` is what a person types when the flag beside it is `--radius`;
        # refusing one of them is a typo that costs a run's setup to discover.
        "-n",
        "--n",
        type=int,
        default=gallery_module.DEFAULT_N,
        help=f"wallpapers to choose (default: {gallery_module.DEFAULT_N})",
    )
    gallerying.add_argument(
        "--pass-id",
        help="the name this pass's records carry (default: the next unused ordinal, "
        f"{gallery_module.PASS_PREFIX}N). Naming a pass that already has a record re-runs it "
        "in place, reusing whatever attempts and full-size renders it already finished",
    )
    gallerying.add_argument(
        "--radius",
        type=float,
        default=gallery_module.RADIUS,
        help=f"the HARD radius, in cosine distance over the neutral-render embedding: "
        f"nothing this close to an already-chosen point may be chosen "
        f"(default: {gallery_module.RADIUS:g})",
    )
    gallerying.add_argument(
        "--quality-weight",
        type=float,
        default=gallery_module.QUALITY_WEIGHT,
        metavar="GAMMA",
        help=f"the exponent on location quality in the farthest-point gain, which is the "
        f"cosine distance to the nearest chosen point times location P(>=4) to the GAMMA "
        f"(default: {gallery_module.QUALITY_WEIGHT:g}; 0 is pure farthest point)",
    )
    gallerying.add_argument(
        "--strange-share",
        type=float,
        default=run_module.STRANGE_SHARE,
        help=f"share of each partition's slots the strange judge fills "
        f"(default: {run_module.STRANGE_SHARE:g})",
    )
    gallerying.add_argument(
        "--attempts",
        metavar="M,SMOOTH,STRANGE",
        default=",".join(str(part) for part in gallery_module.ATTEMPTS),
        help="locations tried near each chosen point, then the smooth attempts each of them "
        "gets on distinct palette anchors and the strange attempts each gets on distinct "
        f"modes (default: {','.join(str(part) for part in gallery_module.ATTEMPTS)})",
    )
    gallerying.add_argument(
        "--reseat",
        type=int,
        default=gallery_module.RESEAT_TRIES,
        metavar="K",
        help="how many NEIGHBOURHOODS a slot may try before it reports below_bar. A slot "
        "whose candidates all land under its head's floor takes the next farthest point "
        "under the same radius and weighting and tries again, so below_bar means k "
        "neighbourhoods in a row failed rather than one "
        f"(default: {gallery_module.RESEAT_TRIES}; 0 is one neighbourhood and no re-seat)",
    )
    gallerying.add_argument(
        "--no-attempts",
        action="store_true",
        help="make no candidate, and so seat nothing: candidates are per-pass, and without "
        "the attempt leg the pass has none. A DEV AFFORDANCE for iterating on the SELECTION "
        "- the slot allocation, the head split, the point draw, the retro table and the two "
        "embedding sheets are all taken whole and cost no render - and never how a pass is "
        "really run",
    )
    gallerying.add_argument(
        "--no-refine",
        action="store_true",
        help="do not scan a location's framing before its attempts render. Refining is ON: "
        "before the attempt leg colours a location, a small window of framings around the one "
        "the pool records is drawn at the node regime and read through the location head, and "
        "the best is adopted if it beats the recorded framing by --refine-margin. Seating and "
        "the radius are decided on unrefined geometry either way, so this changes what the "
        "attempts are pictures OF and nothing about which places the pass chose",
    )
    gallerying.add_argument(
        "--refine-margin",
        type=float,
        default=framing_module.MARGIN,
        metavar="DELTA",
        help=f"how much better a framing has to read before it is adopted, in NATS of log-odds "
        f"on P(>=4) - strict improvement, never argmax, so a window whose best does not clear "
        f"it keeps the recorded framing. Log-odds and not probability because the locations "
        f"this step sees read P(>=4) near 1 at every framing, where an absolute margin refuses "
        f"everything (default: {framing_module.MARGIN:g} nats, a factor of "
        f"{math.exp(framing_module.MARGIN):.1f} in the odds)",
    )
    gallerying.add_argument(
        "--no-full-size",
        action="store_true",
        help="take every seating decision and skip the release leg, so no winner is "
        "rendered at all. The seats are recorded `unrendered` — took the slot, no "
        "picture, nothing failed — and the sheets show each winner's candidate render and "
        "say so. Re-running the same --pass without this flag makes the pictures and lifts "
        "the rows to `released`",
    )
    gallerying.add_argument(
        "--release-regime",
        metavar="WxHssN",
        default=gallery_module.RELEASE_REGIME.spelled,
        help=f"the pixels step 7 makes a winner out of: the frame it ships at and the field "
        f"supersample under it (default: {gallery_module.RELEASE_REGIME.spelled}, on Matt's "
        f"call of 2026-08-25 — a released wallpaper does not need the full frame and step 7 "
        f"is the slow leg of a pass). "
        f"{gallery_module.FORMER_RELEASE_REGIME.spelled} is what gallery1 through gallery3 "
        f"shipped at and is still reachable here. The regime is recorded on the pass record "
        f"and on every release row, and a picture already on disk at another frame is made "
        f"again rather than kept",
    )
    gallerying.add_argument(
        "--seed",
        type=int,
        default=gallery_module.DEFAULT_SEED,
        help=f"the seed the palette anchors and the mode draws are taken under "
        f"(default: {gallery_module.DEFAULT_SEED})",
    )
    gallerying.add_argument(
        "--draw-seed",
        type=int,
        default=None,
        help="the ROOT seed the point draw is taken under, which is a different seed from "
        "--seed: this one decides where each partition's draw starts. Absent, one is DRAWN "
        "and written to the record, so two passes over an unchanged pool choose different "
        "places and either is re-runnable from what it wrote down. Each partition derives "
        "its own seed off the root and the record carries the resolved integer",
    )
    gallerying.add_argument(
        "--draw-top-k",
        type=int,
        default=gallery_module.DRAW_TOP_K,
        metavar="K",
        help=f"how many of a partition's strongest live locations the FIRST pick is drawn "
        f"from. Every pick after the first is the deterministic gain, so this is the whole "
        f"of a draw's freedom, and every distance the draw measures is measured against what "
        f"is already chosen - moving the first pick moves the pass "
        f"(default: {gallery_module.DRAW_TOP_K}; 1 is the argmax the draw took before the "
        f"seed existed)",
    )
    gallerying.add_argument(
        "--target",
        action="append",
        default=[],
        metavar="CELL=FRACTION",
        help="ask the pass for at least ceil(FRACTION x N) pictures DOMINANT in one codebook "
        "cell, e.g. --target dark_vivid_green=0.05. Repeatable. A target steers the plan — "
        "one extra carrier attempt per location per targeted cell, coloured by a map drawn "
        "from the tracked carrier table — and steers the seat, mandating the colour once "
        "every remaining seat is needed for it. It never lowers a floor and never pads: an "
        "unmet target is reported SHORT. Refused before anything renders if the fractions "
        "sum above one or a cell has no carrier this pass can draw",
    )
    gallerying.add_argument(
        "--workers",
        type=int,
        default=3,
        help="worker processes for the full-resolution pass (1 is the serial path)",
    )
    gallerying.add_argument("--device", default="auto", help="cuda, cpu, or auto (default)")
    gallerying.add_argument(
        "--migrate",
        action="store_true",
        help="move --pass out of the layout that predates the store split — attempt rows "
        "into the untracked gate store beside its manifest, the release store rewritten to "
        "the winners alone — and stop. Reads and writes records only; renders nothing",
    )
    gallerying.set_defaults(handler=curate_gallery)

    pass_store = steps.add_parser(
        "gallery-store",
        help="a gallery pass's attempt store: record it, check it, restore it",
        description=(
            "A pass makes locations x heads x draws attempts per slot and each one is a pool "
            "row carrying its whole join — 1,120 rows at n=50 and ten times that at n=500, "
            "at about 3.8 KB a row. They live under the regenerable tree rather than in the "
            "history, so they get what the supply sidecar and the embedding store get: a "
            "copy on the archive tier, a tracked manifest carrying the row count, the bytes, "
            "the sha256 and the population the attempts were made over, and a restore that "
            "counts before it believes."
        ),
    )
    pass_store.add_argument(
        "what",
        choices=["check", "save", "restore"],
        help="check the live store against the manifest, save a fresh copy and manifest, "
        "or restore the copy",
    )
    pass_store.add_argument(
        "--pass",
        dest="pass_id",
        required=True,
        help="which pass's store, by id",
    )
    pass_store.add_argument(
        "--force",
        action="store_true",
        help="with `restore`: overwrite a live store that holds MORE rows than the manifest "
        "records. Those rows are attempts nobody has saved yet",
    )
    pass_store.set_defaults(handler=curate_gallery_store)

    rejecting = steps.add_parser(
        "reject",
        help="apply today's acting release bars to a run released before they acted",
        description=(
            "A rule, not a list: every row this run serves whose head has an ACTING release "
            "bar and which does not clear it is stamped rejected — recorded, dated and "
            "attributed, with nothing deleted and no score touched — and the run's sheet is "
            "redrawn so those rows no longer appear as released. Heads whose cut only "
            "annotates are not touched. Idempotent: a second pass with the same arguments "
            "finds nothing left to do and rewrites the same bytes."
        ),
    )
    rejecting.add_argument("--run", required=True, help="the run to apply the bars to")
    rejecting.add_argument(
        "--rejector",
        required=True,
        help="who is taking these rows back — a person, or the named review standing for one. "
        "An unattributed retraction cannot be told from a bug in the release path",
    )
    rejecting.add_argument(
        "--date", required=True, metavar="YYYY-MM-DD", help="the date of the review verdict"
    )
    rejecting.add_argument(
        "--dry-run", action="store_true", help="print what would be rejected and write nothing"
    )
    rejecting.add_argument(
        "--ephemeral", action="store_true", help="read the run's ephemeral record store"
    )
    rejecting.set_defaults(handler=curate_reject)

    glancing = steps.add_parser(
        "below-bar",
        help="draw the glance sheet of every served wallpaper an acting bar would take back",
        description=(
            "The read to take before `reject`, off the same rule and the same rows: every "
            "wallpaper the collection still serves whose KIND has an ACTING release bar it "
            "does not clear, one row each with the picture, the key, the kind, and the "
            "current score against that kind's floor, best score first. Rows a tracked "
            "ruling holds in service are on the page under their own heading and are not "
            "counted with the rest. It decides nothing, rejects nothing, re-renders nothing "
            "and writes nothing but the sheet."
        ),
    )
    glancing.add_argument(
        "--out",
        metavar="PATH",
        help=f"where to write the sheet (default {below_bar_module.DEFAULT_SHEET.as_posix()})",
    )
    glancing.add_argument(
        "--exclude",
        action="append",
        metavar="RUN|STAGE|CANDIDATE",
        help="drop one row from the sheet by its record key, repeatable. Refuses a key that "
        "is not below the bar today, since a sheet quietly a row short cannot be checked",
    )
    glancing.add_argument(
        "--exclude-reason",
        default="",
        metavar="TEXT",
        help="why those rows were dropped, printed on the sheet beside the keys. An "
        "exclusion is a person's call rather than a rule, so the page carries the call",
    )
    glancing.add_argument("--ephemeral", action="store_true", help="read an ephemeral record store")
    glancing.set_defaults(handler=curate_below_bar)

    repeating = steps.add_parser(
        "repeats",
        help="list every location the collection has served more than one wallpaper of",
        description=(
            "A location is released once, collection-wide (curation.floors.CLUSTER_CAP). "
            "That rule acts at selection and cannot reach backwards, so this is the read of "
            "it against what the collection already holds: every near-duplicate group with "
            "more than one served wallpaper in it, with both heads' scores. It decides "
            "nothing, rejects nothing and writes nothing — `retire-repeats` is the pass "
            "that acts on what this lists."
        ),
    )
    repeating.set_defaults(handler=curate_repeats)

    retiring = steps.add_parser(
        "retire-repeats",
        help="retire every wallpaper past the best one at a location",
        description=(
            "One wallpaper per location acts at selection and cannot reach backwards, so "
            "this applies it once to the collection that predates it. Each near-duplicate "
            "group keeps the highest P(>=3) on its own head's scale — ties to the later run "
            "— and every other wallpaper of that place is stamped rejected with the reason "
            "`location_served` and the survivor's key on the row. Nothing is deleted, no "
            "score is touched, and no bar is read: a retired row is a second picture of a "
            "place, not a bad picture. Run `repeats` first to read what it will do."
        ),
    )
    retiring.add_argument(
        "--rejector",
        required=True,
        help="who is taking these rows back — a person, or the named review standing for one. "
        "An unattributed retraction cannot be told from a bug in the release path",
    )
    retiring.add_argument(
        "--date", required=True, metavar="YYYY-MM-DD", help="the date of the review verdict"
    )
    retiring.add_argument(
        "--dry-run", action="store_true", help="print what would be retired and write nothing"
    )
    retiring.add_argument(
        "--ephemeral", action="store_true", help="read and write an ephemeral record store"
    )
    retiring.set_defaults(handler=curate_retire_repeats)

    checking = steps.add_parser(
        "parity",
        help="render a real release plan serially and concurrently, and compare the bytes",
        description=(
            "The concurrent pass claims to produce the same file as the serial one, not "
            "merely equivalent output. This is the only way to know."
        ),
    )
    checking.add_argument("--run", required=True, help="the run whose plan to re-render")
    checking.add_argument("--rows", type=int, default=2, help="how many rows (default: 2)")
    checking.add_argument("--workers", type=int, default=3, help="the concurrent arm's workers")
    checking.add_argument(
        "--ephemeral", action="store_true", help="read the run's ephemeral record store"
    )
    checking.set_defaults(handler=curate_parity)

    replaying = steps.add_parser(
        "replay",
        help="re-derive every released picture from its own record and compare the bytes",
        description=(
            "An in-band row is re-rendered with the operator off and must be identical; an "
            "acting row's stop list is rebuilt from its stamp alone — no image, no "
            "re-measurement — and must render identically."
        ),
    )
    replaying.add_argument("--run", required=True, help="the run to replay")
    replaying.add_argument(
        "--ephemeral", action="store_true", help="read the run's ephemeral record store"
    )
    replaying.set_defaults(handler=curate_replay)

    colouring_census = steps.add_parser(
        "colors",
        help="the colour census: what can be expressed, picked, kept and labelled",
        description=(
            "A standing record-and-rank over colour. It carries no cut and removes nothing: "
            "it describes the colour distribution at four stages so a bias claim can be "
            "checked against numbers. The stages exist to tell apart four situations that "
            "look identical from outside and have different fixes — a colour the library "
            "cannot express, one the palette head never picks, one that is picked and dies "
            "at a render floor, and one nobody has ever labelled. Counted through 52 "
            "swatches in Oklab; the codebook is written into the artifact so a share vector "
            "read next year is read under the codebook that produced it."
        ),
    )
    colouring_census.add_argument(
        "--stage",
        action="append",
        choices=list(colors_module.STAGES),
        help="run only this stage; repeatable. Omit for all four",
    )
    colouring_census.add_argument(
        "--sheets",
        action="store_true",
        help="also write the two glance sheets to scratch/ — the pool by dominant swatch, "
        "and the sparsest swatches drawn whole. Needs the survival stage",
    )
    colouring_census.add_argument(
        "--frequency",
        action="store_true",
        help="also write the swatch frequency sheet to scratch/ — all 52 swatches ordered by "
        "how often each dominates a judged render, as a csv and as a colour-filled page. "
        "Joins the library and survival stages, so it reads them off the merged artifact",
    )
    colouring_census.set_defaults(handler=curate_colors)

    covering = steps.add_parser(
        "coverage",
        help="coverage on pixels: how many maps can put each swatch on a real share of an image",
        description=(
            "The census counts a swatch's share of a colormap's ramp; this counts its share "
            "of an image's pixels, which is a different number. An escape-time field piles "
            "up at one end of its own stretch and production folds every non-cyclic map, so "
            "a map can carry a colour across a quarter of its gradient and put it almost "
            "nowhere. Two reads, side by side and never pooled: capability, a max over a "
            "fixed probe panel chosen for its field shapes; and realized supply, a count "
            "over the renders the pool already holds, which re-renders nothing. A map "
            "reaching a swatch only with the fold off is reported apart as a false "
            "capability, because production never colours that way."
        ),
    )
    covering.add_argument(
        "--step",
        dest="step_of_coverage",
        choices=["all", "panel", "probe", "read"],
        default="all",
        help="run one step only: draw and choose the panel, put every map through it, or "
        "read the tables off rows already written (default: all three)",
    )
    covering.add_argument(
        "--workers",
        type=int,
        default=6,
        help="how many cells are probed at once (default: 6)",
    )
    covering.add_argument(
        "--sheet",
        action="store_true",
        help="also write the contact sheet to scratch/ — the weakest picture each threshold "
        "admits, for the swatches fewest maps can reach, so the bar is set by eye",
    )
    covering.add_argument(
        "--by-swatch",
        action="store_true",
        help="also write the by-swatch sheet to scratch/ — all 52, ordered by scarcity on "
        "pixels, each with its counts against the pre-existing library, a picture of every "
        "rung, and the maps reaching 20% with the drop's members marked",
    )
    covering.set_defaults(handler=curate_coverage)

    manufacturing = steps.add_parser(
        "manufacture",
        help="force the rare swatches onto good places, and cut the correction sheets",
        description=(
            "Every other population here is found; this one is made. A location a person "
            "already scored a keeper is coloured through a map CHOSEN because the coverage "
            "read says it can reach a target swatch, in a mode drawn the way a run draws "
            "one, under the identity recipe production uses. A map's ramp does not predict "
            "what a picture holds, so the order is build, measure, then select: every "
            "attempt is screened at candidate geometry, the best one at each location is "
            "re-rendered at the sheet's own, and both cuts — a tenth of the pixels on the "
            "target, at least a 2 from the render judge — act on that second reading. The "
            "batch is model- and construction-conditioned and is registered train-side "
            "before a pixel is made; a tenth of its rows force the same swatches through "
            "maps the library already held, so a correction cannot be read as being about "
            "the drop when it is about the colour."
        ),
    )
    manufacturing.add_argument(
        "--step",
        dest="step_of_manufacture",
        choices=[
            "all",
            "register",
            "plan",
            "screen",
            "confirm",
            "select",
            "read",
            "top-up",
            "verify",
            "knobs",
        ],
        default="all",
        help="run one step only (default: all six, in order). Three are not among them: "
        "`top-up` extends the plan for the cells a selection came back short in, `verify` is "
        "taken against a sheet after it has been built, and `knobs` measures the "
        "counterfactual the diagnostic asks about",
    )
    manufacturing.add_argument(
        "--sheet",
        help="a built sheet, for --step verify: does it serve the picture the cuts were "
        "taken on, byte for byte, and does its own reading of the judge agree",
    )
    manufacturing.add_argument(
        "--batch",
        default=manufacture_module.BATCH,
        help=f"the batch this is (default: {manufacture_module.BATCH})",
    )
    manufacturing.add_argument(
        "--rows-per-kind",
        type=int,
        default=manufacture_module.ROWS_PER_KIND,
        help=f"rows on each kind's sheet (default: {manufacture_module.ROWS_PER_KIND})",
    )
    manufacturing.add_argument(
        "--oversample",
        type=float,
        default=4.0,
        help="how many locations a cell attempts per row it owes (default: 4). The yield is "
        "a property of this population and nothing measured elsewhere predicts it, so pilot "
        "it on a small plan before spending the night's build on a guess",
    )
    manufacturing.add_argument(
        "--seed", type=int, default=manufacture_module.SEED, help="the draw's seed"
    )
    manufacturing.add_argument(
        "--workers", type=int, default=6, help="how many groups are built at once (default: 6)"
    )
    manufacturing.add_argument("--device", default="auto", help="cuda, cpu, or auto")
    manufacturing.add_argument(
        "--knob-sample",
        type=int,
        default=120,
        help="how many missed attempts --step knobs re-colours through the knob grid "
        "(default: 120). Nothing in this project renders through those knobs; the sweep "
        "prices what a draw production does not make would have bought",
    )
    manufacturing.add_argument(
        "--write",
        action="store_true",
        help="the register step appends; otherwise it prints what it would register",
    )
    manufacturing.set_defaults(handler=curate_manufacture)

    expressing = steps.add_parser(
        "expressed",
        help="how much of the codebook the finished collection expresses, and what a "
        "per-swatch floor could arithmetically ask for",
        description=(
            "COVERAGE(s) is the fraction of finished full-size wallpapers in which at least "
            "a tenth of the pixels are assigned to swatch s, read off the shipped render at "
            "its own resolution rather than off the candidate that stands behind it. Summed "
            "over the fifty-two, COVERAGE is the mean number of swatches a wallpaper "
            "expresses — which is what decides whether a uniform per-swatch floor can exist "
            "at all, since a floor of f across k swatches asks the average picture for f*k "
            "expressed colours. Measurement only: no floor is set and nothing is gated."
        ),
    )
    expressing.add_argument(
        "--step",
        dest="step_of_expressed",
        choices=["all", "census", "read"],
        default="all",
        help="run one step only: census every finished wallpaper, or read the tables off a "
        "census already taken (default: both)",
    )
    expressing.set_defaults(handler=curate_expressed)


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
    draw.add_argument(
        "--width", help="view width in plane units (default: the family's home width)"
    )
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
        help=f"named coloring (default: {DEFAULT_MODE}); see the modes subcommand",
    )
    draw.add_argument(
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


def main(argv: Sequence[str] | None = None) -> int:
    from fractal_wallpapers.discovery.identity import IdentityBroken

    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except IdentityBroken as refusal:
        # Also here rather than in one command: both `walk` and `harvest` build
        # the walk that raises it, the message names the flag to change, and a
        # traceback would bury an instruction under a stack.
        print(refusal)
        return 1
    except StorageRefusal as refusal:
        # Handled here and nowhere else. Every other refusal in this file is
        # about one command's arguments and is caught by that command; these are
        # about the machine — an unplugged disk, a subtree on the wrong tier, one
        # name in both tiers — and any subcommand that touches the regenerable
        # tree can raise one. Caught rather than left to a traceback because each
        # message is an instruction, and an operator reading a stack trace to
        # find it would be reading it past the part that says nothing fell back.
        print(refusal)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
