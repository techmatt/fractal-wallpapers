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
from fractal_wallpapers.labeling.finished import HEADS as FINISHED_HEADS
from fractal_wallpapers.paths import colormap_dir, repo_root

WEIGHTS_MANIFEST = Path("models") / "weights.json"
RELEASE_URL = "https://github.com/techmatt/fractal-wallpapers/releases/download/{tag}/{asset}"

#: The mode a `render` that says nothing about coloring asks for. The engine has
#: the same default and would apply it to a spec with no `mode` key at all; it is
#: written here too so the spec a command built says what it rendered.
DEFAULT_MODE = "smooth"

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


def resolve_output(out: str) -> Path:
    """Resolve an output path against the repository, not the shell's cwd.

    A relative `--out` means the same place whichever directory the command was
    run from, which is what keeps the default landing in the ignored
    `artifacts/` tree instead of scattering PNGs wherever the caller stood.
    """
    path = Path(out)
    return path if path.is_absolute() else repo_root() / path


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
        help=f"worker processes rendering the views the head reads "
        f"(default: {scoring.DEFAULT_WORKERS}; 1 renders in this process)",
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
    chosen = [resolve_output(p) for p in (args.ledger or [])]
    chosen += [binding.of_harvest(resolve_output(d)) for d in harvests]
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


def build_scorer(args: argparse.Namespace, log=print):
    """The judge a walk consults, or `None` for the structural gates alone.

    One builder for both the walk and the harvest, because a scorer chosen two
    ways is a scorer that can differ between the run that fills a ledger and the
    run that continues it — and the ledger's `scorer` field would then name two
    things under one word.
    """
    from fractal_wallpapers.discovery import scoring

    if args.no_scoring:
        return None
    try:
        return scoring.LocationScorer(workers=args.score_workers, device=args.device, log=log)
    except Exception as refusal:  # noqa: BLE001 — an unshipped head is a refusal, not a crash
        raise SystemExit(
            f"the location head cannot be loaded, so nothing can score what this run finds: "
            f"{refusal!r}\nFetch the weights (`fractal-wallpapers fetch-weights`), or pass "
            f"--no-scoring to walk on the structural gates alone and leave every row unclassed."
        ) from refusal


def walk(args: argparse.Namespace) -> int:
    """Run one discovery walk and print what it found."""
    from fractal_wallpapers.discovery.walk import Gates, Limits, Policy, Reframings, Walk

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


def harvest(args: argparse.Namespace) -> int:
    """Run the production loop: keep finding material where it is scarcest."""
    from fractal_wallpapers.discovery.walk import Limits, Policy, Reframings, Walk
    from fractal_wallpapers.supply import ledgers, release_mix, saturation, twins
    from fractal_wallpapers.supply.census import stock_census
    from fractal_wallpapers.supply.harvest import Budget, Harvest
    from fractal_wallpapers.supply.partitions import ALL_PARTITIONS
    from fractal_wallpapers.supply.prices import load_table
    from fractal_wallpapers.supply.quota import Quota
    from fractal_wallpapers.supply.refill import Refill

    run_dir = resolve_output(args.out_dir)
    limits = Limits(
        batch=args.batch,
        root_expansions=args.root_expansions,
        plane_grace_rungs=args.plane_grace_rungs,
    )
    if args.probe is not None:
        limits.probe_probability = args.probe
    walk_run = Walk(
        out_dir=run_dir,
        seed=args.seed,
        limits=limits,
        policy=Policy(candidates=args.candidates, node_width=args.node_width),
        reframings=Reframings(neighborhood=args.neighborhood),
        colormap=args.colormap,
        scorer=build_scorer(args),
    )
    # A run told which partitions to keep books for keeps them for those alone:
    # the census, the allocation, the refill census and the served mix all read
    # this list, so naming one partition is how a leg spends a whole clock there
    # rather than steering toward it and hoping.
    partitions = list(args.partition or ALL_PARTITIONS)
    quota = Quota(
        partitions,
        run_dir,
        floor=args.floor,
        prices_config=load_table(Path(args.prices) if args.prices else None),
        census=stock_census(partitions, discount=args.discount),
        external=release_mix.externally_supplied(partitions),
    )
    # Primed before the first batch, off the same two legs of admitted stock the
    # census reads, and extended by whatever this run books. Its ledger is the
    # walk's, so what the channel accepted and what the c-spacing floor refused
    # land in the run's own record rather than only in a summary.
    twin_channel = (
        None
        if args.no_twins
        else twins.build(
            ledger=walk_run.ledger,
            ledger_paths=ledgers.ledger_paths(
                root=resolve_output(args.ledgers), exclude=walk_run.ledger.path
            ),
        )
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
    )
    memory = (
        None
        if args.no_saturation
        else saturation.build(exclude=walk_run.ledger.path, root=resolve_output(args.ledgers))
    )
    run = Harvest(
        walk_run,
        quota,
        budget=Budget(minutes=args.minutes, batches=args.batches),
        refill=refill,
        memory=memory,
        saturation_strength=0.0 if args.no_saturation else saturation.STRENGTH,
        partitions=partitions,
    )
    if run.resume():
        print(f"resumed at batch {run.batch} ({run.active_minutes:.2f} active minutes spent)")
    print(json.dumps(run.run(), indent=2))
    return 0


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
        sources.append({"name": run_dir.name, "path": str(run_dir)})

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


def label_serve(args: argparse.Namespace) -> int:
    """Serve a built sheet to a browser on this machine."""
    from fractal_wallpapers.labeling import server, sheets

    directory = resolve_output(args.sheet)
    sheets.read(directory)  # refuse a directory that is not a sheet, before binding a port
    return server.serve(directory, host=args.host, port=args.port)


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


def tiles_build(args: argparse.Namespace) -> int:
    """Render every tile of the plan, one iteration pass per location."""
    from fractal_wallpapers.models import tiles as tile_module

    log = tile_module.tile_dir() / "build.log"
    report = tile_module.build(limit=args.limit, log=log)
    record = {
        "schema": tile_module.SCHEMA,
        "plan": str(tile_module.plan_path()),
        "locations": str(tile_module.locations_path()),
        "log": str(log),
        "report": report,
    }
    tile_module.build_record_path().write_text(
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
    """Train one finished-render judge on the render cache."""
    from fractal_wallpapers.models import finished_train

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
    """Score one side of a judge's corpus through a trained checkpoint."""
    from fractal_wallpapers.models import finished_scoring

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
    """Read a trained judge against its pre-registered bar."""
    from fractal_wallpapers.models import finished_acceptance

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
    from fractal_wallpapers.models import finished_acceptance, ship

    verdict_path = finished_acceptance.acceptance_path(args.head)
    if not verdict_path.is_file():
        print(f"{verdict_path} is missing: nothing has judged this head yet.")
        print("Run `fractal-wallpapers renders accept` first.")
        return 1
    verdict = json.loads(verdict_path.read_text(encoding="utf-8"))["verdict"]
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


def head_train(args: argparse.Namespace) -> int:
    """Train one head on the built tiles."""
    from fractal_wallpapers.models import train

    record = train.train(
        name=args.head, device=args.device, epochs=args.epochs, seed=args.seed, run=args.run
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
            ),
            indent=2,
        )
    )
    return 0


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
        report = intake.score(declared_ledgers(args), device=args.device, limit=args.limit)
    except (binding.Unbound, intake.IntakeError) as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    return 0


def curate_plan(args: argparse.Namespace) -> int:
    """Print the offer and the budget it implies, making no picture."""
    from fractal_wallpapers.curation import binding, budget, floors, intake

    try:
        offer, supply = intake.ranked(declared_ledgers(args))
    except (binding.Unbound, intake.IntakeError) as refusal:
        print(refusal)
        return 1
    claims = intake.guaranteed(supply)
    plan, record = budget.plan(
        offer, args.n, args.strange_share, budget=args.attempts, guarantees=claims
    )
    print(
        json.dumps(
            {
                "cuts": floors.summary(),
                "supply": supply,
                "lines": intake.supply_lines(supply),
                "emit_caps": intake.emit_caps(offer),
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
    from fractal_wallpapers.curation import binding, intake, records
    from fractal_wallpapers.curation import run as run_module

    try:
        summary = run_module.curate(
            run=args.resume or args.run,
            n=args.n,
            seed=args.seed,
            strange_share=args.strange_share,
            attempts=args.attempts,
            workers=args.workers,
            ephemeral=args.ephemeral,
            ledgers=declared_ledgers(args),
            device=args.device,
            skip_release=args.skip_release,
            wall_budget=args.wall_budget,
            resume=bool(args.resume),
        )
    except (
        binding.Unbound,
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
    production.add_argument(
        "--minutes",
        type=float,
        default=10.0,
        help="active-minute budget across every session of this run (default: 10; 0 for none)",
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
    production.add_argument("--node-width", type=int, default=384, help="node render width")
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
        "--neighborhood",
        action="store_true",
        help="also enumerate neighbouring nuclei (the expensive operator; off by default)",
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
        "--ledgers",
        default="artifacts",
        help="where earlier runs' ledgers live (default: artifacts)",
    )
    production.add_argument(
        "--colormap", default="twilight_shifted", help="colormap for the steering thumbnails"
    )
    production.add_argument(
        "--out-dir",
        default=str(Path("artifacts") / "harvest"),
        help="the run directory (default: artifacts/harvest)",
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
    palette_commands(subcommands)
    coloring_commands(subcommands)
    curate_commands(subcommands)

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
        help="collect human verdicts: register, build, serve, record, split",
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
        "--out-dir",
        default=str(Path("artifacts") / "sheet"),
        help="where the sheet is built (default: artifacts/sheet)",
    )
    scoring_flags(building)
    building.set_defaults(handler=label_build)

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
        help="render every tile of the plan",
        description=(
            "Resumable by construction: a location whose tiles are all on disk is skipped "
            "before its field is iterated, so a killed run continues rather than restarting. "
            "Progress goes to artifacts/tiles/build.log as it runs."
        ),
    )
    building.add_argument(
        "--limit",
        type=int,
        help="stop after this many locations; every row it writes is stamped partial",
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
    reading.set_defaults(handler=head_score)

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
                "Renders each gate-surviving location's canonical view — the same picture a "
                "deployed judge is handed — and scores it. Resumable in both halves: a view "
                "already on disk is not re-rendered."
            ),
        )
    )
    reading.add_argument("--device", default="auto", help="cuda, cpu, or auto (default)")
    reading.add_argument("--limit", type=int, help="score only this many locations")
    reading.set_defaults(handler=curate_score)

    def with_shape(parser, defaults=True):
        # A run takes `None` where `plan` takes a number: a resumed run reads its
        # shape back out of its own sidecar, and a flag that defaulted to 6 here
        # could not be told from a flag that asked for 6.
        parser.add_argument(
            "-n",
            type=int,
            default=6 if defaults else None,
            help="release slots to fill (default: 6, or the resumed run's own)",
        )
        parser.add_argument(
            "--strange-share",
            type=float,
            default=0.5 if defaults else None,
            help="share of the slots the strange judge fills (default: 0.5)",
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
                    "quota under the slot, supply and look caps ships fewer, and says so. "
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
    running.set_defaults(handler=curate_run)

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


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
