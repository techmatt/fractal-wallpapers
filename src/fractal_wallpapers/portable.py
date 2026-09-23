"""What a fresh box needs to continue every stage, carried out of this one and in.

The repository tracks code, labels, weights by release tag and the published
record. Everything else a production verb reads is untracked: the walk ledgers,
the candidate pool, the sidecars and stores beside it, the levelling sequences.
This module is that set written down, and the two commands that move it:
`storage export --to DIR` and `storage import --from DIR --root ROOT`.

## The roster was measured, not inferred

[`ROSTER`] is what the production verbs were **seen to open**, on 2026-09-16,
by an audit hook over every `open`, `scandir` and rename a verb made — the plan
and no-render forms of `curate run`, `hunt`, `depth`, `mine`, `rotate`, `score`,
`solve`, `atlas`, the census and the re-render, and the writing forms (a hunt, a
merge, a reframe) from a throwaway root after an import. Each entry says which
verbs read it and why it cannot simply be rebuilt. The Durables are all on it,
and `tests/test_portable.py` holds that: a new [`curation.durability.Durable`]
that nobody added here is a file the next box would silently not have.

A name on the roster is a *pattern* over the regenerable tree, and it resolves
through [`paths.Tiers`] across **both** tiers: a walk ledger archived last week is
still saturation memory, and an export that read the hot tier alone would carry
half of it without saying so. An unreachable archive therefore refuses rather
than exporting the hot half.

## Pictures do not travel, and the pool's are written down instead

Matt's ruling of 2026-09-16: a fresh box re-renders. A solve is **not**
picture-free — `solve.pool` refuses every row whose JPEG is not on disk as
`picture_absent`, and the twin test opens a picture wherever the reduced
signature sidecar has no row — so the first leg on a fresh box is
`curate candidate-ledger re-render --seatable`, then a solve, and `--rest` whenever
nothing else wants the render pool. What the export
carries in their place is `pictures.jsonl`: one row per candidate the solve can
seat, with the picture's name, size and sha256, so the re-render can be read
against the bytes it is meant to reproduce. It also says, per row, whether the
build that drew it fingerprints as the exporting build (`same_build`), is
unrecorded (`unknown_build`), or differs (`other_build`) — the first is what a
byte-identical re-derivation is expected of.

## Import refuses before it writes, and writes only what is named

Every file is checked against the manifest's size and sha256 before the first
byte lands; a file in the directory the manifest does not name is a refusal too,
because an export that grew a file is not the export that was measured. A
destination that already exists is refused rather than overwritten or merged —
this is the collision [`paths.TierCollision`] exists for, arriving by copy. Each
file is written to a temporary and renamed, so presence still means complete.

**Tiers on the target.** A file keeps its tier when the box has an archive
(`--archive-root`), and lands under `--root` when it does not: a single-root box
is simply a box whose every name is hot, which is what `paths` already means by
no archive configured. Checkout-side files — the label inbox — land under this
checkout.

## What does not travel with it, and is not state

Weights come from `fetch-weights`; the engine is `cargo build --release`; the
DINOv2 backbone is a Hugging Face download on first `curate embed`. None of the
three is on the roster, and the manifest records the exporting build's
fingerprint and the weights manifest's hashes so the importing box can say
whether it matches. **A different engine fingerprint empties the score
amendment's overlay** (`amend.read` keeps only rows drawn by the running build),
which is why `import` says so out loud rather than leaving a seating to fall back
to un-amended scores in silence.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import shutil
import subprocess
import time
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from fractal_wallpapers.paths import (
    ARCHIVE,
    ARTIFACTS_NAME,
    HOT,
    ArchiveUnreachable,
    StorageRefusal,
    Tiers,
    repo_root,
)

#: The schema the manifest and `pictures.jsonl` carry.
SCHEMA = 1

#: What the export directory's manifest and picture record are called.
MANIFEST_NAME = "portable.json"
PICTURES_NAME = "pictures.jsonl"

#: The two subdirectories of an export: files under the regenerable tree, and
#: untracked files under the checkout.
TREE = "tree"
CHECKOUT = "checkout"

#: **The solve a fresh box compares its first seating against**, and the record
#: that holds its seats. A tentative record at the size `curation.targets` sets —
#: `curate solve record --collection green`, n = 300 — taken over the closed pool
#: on 2026-09-22 and re-run `--no-render` straight after: 300 of 300 seats in the
#: same order. **It travels through the roster and not the keep list** —
#: `tentative.KEPT_UNPUBLISHED` pins seats against a prune, and a comparison
#: target has no business doing that.
#:
#: **A themed reference decays as the pool grows, and it is re-cut at an export.**
#: The themed bar is read off the cell's own `multiple * n`-th best candidate, so
#: every leg that adds rows to the cell can move the bar and re-rank the cell under
#: it. The two records before this one both stopped reproducing that way — 282 of
#: 300 in common, then 230 of 300 with 3 at the same index once five days of mining
#: took the bar off its 0.01 floor to a reachable 0.015935. Mining closed on
#: 2026-09-21, so this record should hold while the pool does, and it seats exactly
#: what the kept `final139_green` seats, in the same order.
REFERENCE = {"stamp": "20260923T040952Z", "collection": "green"}

#: **The n = 1000 check beside [`REFERENCE`].**
#: `final139_general` is the general seating of the closed pool at
#: [`curation.tentative.RECORDED_SEATS`] — the shipped fine bar, no theme, no
#: collection — and it re-seated **1000 of 1000 in order** on 2026-09-21, over the
#: pool it was itself taken on hours earlier and which mining closed behind.
#:
#: **It travels on the keep list and not the roster**, which is the opposite of
#: [`REFERENCE`] and for the opposite reason: it is one of the twenty
#: `tentative.KEPT_UNPUBLISHED` records already, so `{kept}` carries its rows and
#: `{kept_solves}` its `solve.json`, and adding it to the roster would carry the
#: same three files twice.
#:
#: ⚠ **The two checks are not interchangeable and neither replaces the other.**
#: This one is the general pass on the whole pool; [`REFERENCE`] is the themed
#: one, `--collection green` at a relaxed bar, and it is the only comparison
#: target on the collection path. A box that ran one has not run the other.
GENERAL_CHECK = {"stamp": "20260922T012627Z", "name": "final139_general", "n": 1000}

#: Where the export writes what the reference is and how to reproduce it.
REFERENCE_README = "reference/README.md"

#: Bytes read at a time while hashing and copying.
CHUNK = 1 << 20


class PortableRefusal(StorageRefusal):
    """An export or import that cannot be made as asked. Nothing was written."""


@dataclass(frozen=True)
class Entry:
    """One line of the roster: a set of files, who reads them, and why they travel.

    `patterns` are POSIX globs. For a [`TREE`] entry they are relative to the
    regenerable tree and the first component is matched against the top-level
    names of **both** tiers; for a [`CHECKOUT`] entry they are relative to the
    checkout, and a tracked file is never taken — the clone brings it.
    """

    name: str
    root: str
    patterns: tuple[str, ...]
    verbs: tuple[str, ...]
    why: str


#: The pool subtrees whose legs keep a levelling sequence, as `stamps` names them.
#: Spelled here as a glob rather than imported, because the roster is data a
#: reader should be able to take in at a glance; `tests/test_portable.py` holds
#: it to [`curation.stamps.SEQUENCE_STORES`].
SEQUENCE_GLOB = "curation/{depth,mine,remode,rotation}/*/sequence.jsonl"


#: Everything a production verb was seen to read that the clone does not bring.
#: Measured 2026-09-16 (see the module docstring); `verbs` is who opened it.
ROSTER: tuple[Entry, ...] = (
    Entry(
        "supply sidecar",
        TREE,
        ("curation/supply_scores.jsonl",),
        (
            "curate run",
            "curate plan",
            "curate score",
            "curate depth plan",
            "curate mine plan",
            "curate solve run",
        ),
        "guarded Durable: the standing supply a run is offered; a scoring pass over every "
        "ledger to rebuild",
    ),
    Entry(
        "score amendment",
        TREE,
        ("curation/score_amendments.jsonl",),
        ("curate run", "curate plan", "curate depth plan", "curate mine plan", "curate solve run"),
        "guarded Durable: ~90,000 re-rendered views re-read; append-only, keyed on the engine "
        "fingerprint",
    ),
    Entry(
        "hunt frame index",
        TREE,
        ("curation/hunt/frames.jsonl",),
        ("curate run", "curate hunt", "curate depth plan", "curate mine plan"),
        "guarded Durable with NO rebuild: the scan it was cut from was deleted 2026-09-02",
    ),
    Entry(
        "candidate ledger",
        TREE,
        (
            "curation/candidate_ledger/rows.jsonl",
            "curation/candidate_ledger/scores.jsonl",
            "curation/candidate_ledger/flatness.jsonl",
            "curation/candidate_ledger/reduced_signatures.jsonl",
        ),
        (
            "curate solve run",
            "curate atlas",
            "curate depth plan",
            "curate mine plan",
            "curate rotate plan",
            "curate candidate-ledger",
            "merge",
        ),
        "four Durables: the pool itself, its judge readings, and the two sidecars the rank key "
        "and the twin test read instead of pictures",
    ),
    Entry(
        "candidate ledger records",
        TREE,
        (
            "curation/candidate_ledger/displaced/*.jsonl",
            "curation/candidate_ledger/family_allowance/*.jsonl",
        ),
        (),
        "the one entry no verb reads: forensic lists every prune writes of what it displaced "
        "and what the family allowance kept, which `sweep.FAMILY_KEPT_DIR` says cannot be "
        "re-derived once the population has moved. Five megabytes, so carried rather than lost",
    ),
    Entry(
        "embedding store",
        TREE,
        ("curation/neutral_embeddings.jsonl",),
        ("curate solve run", "curate hunt plan", "curate depth plan", "curate mine plan"),
        "Durable: one DINOv2 vector per admitted location off a neutral render",
    ),
    Entry(
        "spiral score store",
        TREE,
        ("curation/spiral_scores.jsonl",),
        ("curate solve run",),
        "Durable: P(spiral) per location, the share cap's input",
    ),
    Entry(
        "colour-mass sweep log",
        TREE,
        ("curation/palette_mass_sweep/rows.jsonl",),
        ("curate mass-sweep",),
        "Durable: 8.7 hours of renders",
    ),
    Entry(
        "levelling sequences",
        TREE,
        (SEQUENCE_GLOB,),
        ("curate atlas", "curate depth plan", "curate autolevel", "curate solve browse"),
        "the autolevel stamp every candidate was levelled under; a seat opens as the picture it "
        "shipped only by replaying it",
    ),
    Entry(
        "autolevel backfill",
        TREE,
        ("curation/autolevel_backfill.jsonl",),
        ("curate atlas", "curate autolevel"),
        "the curves re-derived for seats written before their leg kept a sequence",
    ),
    Entry(
        "depth leg records",
        TREE,
        ("curation/depth/*/depth.json",),
        ("curate depth plan",),
        "`--rate` reads itself off these, since 2026-09-15",
    ),
    Entry(
        "kept tentative records",
        TREE,
        (
            "curation/tentative/{kept}/gallery.jsonl",
            "curation/tentative/{kept}/manifest.json",
            "curation/tentative/{kept}/recipes.jsonl",
        ),
        ("curate rotate plan", "curate atlas", "curate autolevel", "curate solve list"),
        "the seats `tentative.protected_keys()` pins and the records figures resolve. `{kept}` "
        "is `tentative.kept()`'s two tuples and nothing else: an off-list record is discarded "
        "by default and does not travel. The published ones' text is tracked and comes with "
        "the clone",
    ),
    Entry(
        "kept solve records",
        TREE,
        ("curation/solve/{kept_solves}/solve.json",),
        ("curate solve list", "curate solve recipes"),
        "the seating each kept record came from. A kept `manifest.json` names its solve record "
        "by path, so a box that took the records without these holds a manifest pointing at a "
        "file that is not there. `{kept_solves}` is read off those manifests rather than listed, "
        "because `curation/solve/` also holds the legs of records that were discarded and an "
        "off-list record does not travel",
    ),
    Entry(
        "reference solve",
        TREE,
        (
            "curation/tentative/{reference}/gallery.jsonl",
            "curation/tentative/{reference}/manifest.json",
            "curation/solve/tentative_n*_{reference}/solve.json",
        ),
        ("curate solve run", "curate solve list"),
        "the seating a fresh box reproduces `--no-render` before it trusts its own: "
        "`REFERENCE` names it and the export writes `reference/README.md` saying how. Not on "
        "the keep list, so `{kept}` never reaches it",
    ),
    Entry(
        "mine leg records",
        TREE,
        ("curation/mine/*/mine.json",),
        ("curate mine plan", "curate mine run"),
        "`--rate` reads itself off these, since 2026-09-16 — `mine.measured_rate`. Without "
        "them a fresh box plans at `mine.PILOT_RATE` rather than at what a mine here cost",
    ),
    Entry(
        "built label sheets",
        TREE,
        (
            "sheet/*/sheet.json",
            "sheet/*/sheet.jsonl",
            "sheet/*/measure.json",
            "sheet/*/verify.json",
            "*/sheet.json",
            "*/sheet.jsonl",
        ),
        ("label sheets", "label ingest"),
        "what a sheet put in front of a labeler; `label ingest` resolves an export through it, "
        "so an export in the inbox without its sheet cannot be ingested",
    ),
    Entry(
        "gallery-grade pool scores",
        TREE,
        ("gallery_grade_head/pool_scores.jsonl",),
        ("curate solve run", "curate atlas", "curate rotate plan"),
        "the cascade refuses without it; a pass of the fine head over the whole pool",
    ),
    Entry(
        "walk ledgers",
        TREE,
        ("*/walk.jsonl",),
        ("census", "harvest", "reframe", "curate plan", "curate score", "curate depth plan"),
        "every walk ever run, on either tier: the supply union and the saturation memory",
    ),
    Entry(
        "colour census",
        TREE,
        ("curation/colors/rows.jsonl", "curation/colors/census.json"),
        ("curate colors", "curate coverage"),
        "the census rows a partial `curate colors` carries forward, and `coverage` reads; "
        "rebuilding them decodes every judged picture, which a fresh box does not have",
    ),
    Entry(
        "shipped gallery-grade run checkpoints",
        CHECKOUT,
        ("models/gallery_grade/{gallery_grade_runs}/best.pt",),
        ("curate rotate", "gallery-grade score"),
        "the three fp32 seeds the shipped ensemble was halved from. `rotation.score_fine` loads "
        "them with no fallback to the release artifact, so a box with only `fetch-weights` "
        "cannot run `curate rotate`; `score_pool` falls back but stamps its rows with the fp16 "
        "file, so the pool score store would carry two weights stamps. No release carries them "
        "(`models/weights.json` names one asset per head)",
    ),
    Entry(
        "label inbox",
        CHECKOUT,
        ("labels/*", "labels/archive/*"),
        ("label ingest",),
        "unprocessed exports `label ingest` reads, and the processed ones that are the only "
        "record of what a batch put in front of a labeler",
    ),
)


# --------------------------------------------------------------------------- #
# Small pieces.
# --------------------------------------------------------------------------- #
def kept_stamps() -> tuple[str, ...]:
    """The keep list as code states it — no store read, so a test's tmp roots see the same."""
    from fractal_wallpapers.curation import tentative

    return tuple(tentative.PUBLISHED) + tuple(tentative.KEPT_UNPUBLISHED)


def kept_solve_records() -> tuple[str, ...]:
    """The `curation/solve/<name>` each kept record's manifest names, by name and in order.

    Read off the manifests rather than listed, because `curation/solve/` also holds
    the legs of records that were discarded, and an off-list record does not travel.
    A record the box does not hold, or one whose manifest names no solve, contributes
    nothing — the record itself is already absent from the export by the same rule.
    """
    try:
        base = Tiers.current().unit("curation")
    except StorageRefusal:
        return ()
    names: list[str] = []
    for stamp in kept_stamps():
        manifest = base / "tentative" / stamp / "manifest.json"
        if not manifest.is_file():
            continue
        held = json.loads(manifest.read_text(encoding="utf-8"))
        record = str(((held.get("solve") or {}).get("record")) or "")
        parts = PurePosixPath(record).parts
        if len(parts) < 2:
            continue
        if parts[-2] not in names:
            names.append(parts[-2])
    return tuple(names)


def gallery_grade_runs() -> tuple[str, ...]:
    """The run directories the shipped gallery-grade ensemble resolves to, by name."""
    from fractal_wallpapers.models import gallery_grade_train

    arm, seeds, _column = gallery_grade_train.shipped_runs()
    return tuple(gallery_grade_train.run_dir(arm, seed).name for seed in seeds)


def _expand(pattern: str) -> list[str]:
    """`a/{b,c}/d` as `a/b/d` and `a/c/d`, and `{kept}` as every kept stamp. One group."""
    if "{kept}" in pattern:
        return [pattern.replace("{kept}", stamp) for stamp in kept_stamps()]
    if "{kept_solves}" in pattern:
        return [pattern.replace("{kept_solves}", name) for name in kept_solve_records()]
    if "{reference}" in pattern:
        return [pattern.replace("{reference}", REFERENCE["stamp"])]
    if "{gallery_grade_runs}" in pattern:
        return [pattern.replace("{gallery_grade_runs}", run) for run in gallery_grade_runs()]
    start = pattern.find("{")
    if start < 0:
        return [pattern]
    end = pattern.index("}", start)
    return [
        pattern[:start] + choice + pattern[end + 1 :]
        for choice in pattern[start + 1 : end].split(",")
    ]


def _hash_copy(source: Path, destination: Path) -> dict:
    """Copy through a temporary, hashing the bytes read. `{bytes, sha256}` of the source."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    writing = destination.with_name(destination.name + ".writing")
    digest = hashlib.sha256()
    size = 0
    with source.open("rb") as reading, writing.open("wb") as written:
        for chunk in iter(lambda: reading.read(CHUNK), b""):
            digest.update(chunk)
            written.write(chunk)
            size += len(chunk)
    shutil.copystat(source, writing)
    writing.replace(destination)
    return {"bytes": size, "sha256": digest.hexdigest()}


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tracked_files() -> set[str]:
    """Every path git tracks in this checkout, POSIX and relative. Empty without git."""
    try:
        listed = subprocess.run(
            ["git", "-C", str(repo_root()), "ls-files", "-z"],
            capture_output=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return set()
    return {name for name in listed.decode("utf-8").split("\0") if name}


# --------------------------------------------------------------------------- #
# Resolving the roster.
# --------------------------------------------------------------------------- #
def resolve(roster=ROSTER, tiers: Tiers | None = None, tracked: set[str] | None = None) -> list:
    """`[{path, root, tier, source, entries}]` for every file the roster names now.

    `path` is the name a record would carry — `artifacts/<rest>` for the tree,
    checkout-relative otherwise — and is the key: a file two entries both match
    is carried once, naming both.
    """
    tiers = Tiers.current() if tiers is None else tiers
    if tiers.archive is not None and not tiers.archive_is_reachable:
        raise ArchiveUnreachable(
            f"the archive at {tiers.archive} is not there, and half the walk ledgers and every "
            "archived record live on it. An export of the hot tier alone would be an export "
            "that silently lost them. Plug it in, or set the archive root to nothing if this "
            "machine genuinely has none."
        )
    tracked = tracked_files() if tracked is None else tracked
    found: dict[str, dict] = {}
    names = tiers.names()
    for entry in roster:
        for pattern in (piece for raw in entry.patterns for piece in _expand(raw)):
            for source, name, tier in _matches(entry.root, pattern, tiers, names):
                if name in tracked or name.endswith(".writing") or not source.is_file():
                    continue
                cell = found.setdefault(
                    name,
                    {
                        "path": name,
                        "root": entry.root,
                        "tier": tier,
                        "source": source,
                        "entries": [],
                    },
                )
                if entry.name not in cell["entries"]:
                    cell["entries"].append(entry.name)
    return [found[name] for name in sorted(found)]


def _matches(root: str, pattern: str, tiers: Tiers, names: list[str]):
    """`(source, recorded name, tier)` for one pattern."""
    parts = PurePosixPath(pattern).parts
    if root == CHECKOUT:
        base = repo_root()
        for source in sorted(base.glob(pattern)):
            yield source, source.relative_to(base).as_posix(), CHECKOUT
        return
    first, rest = parts[0], parts[1:]
    for unit in names:
        if not fnmatch.fnmatchcase(unit, first):
            continue
        where = tiers.unit(unit)
        tier = tiers.tier_of(unit)
        candidates = [where] if not rest else sorted(where.glob("/".join(rest)))
        for source in candidates:
            below = source.relative_to(where).as_posix()
            name = f"{ARTIFACTS_NAME}/{unit}" + ("" if below == "." else f"/{below}")
            yield source, name, tier


def _stored_path(export: Path, row: dict) -> Path:
    """Where one manifest row sits inside an export directory."""
    if row["root"] == CHECKOUT:
        return export / CHECKOUT / PurePosixPath(row["path"])
    below = PurePosixPath(row["path"]).relative_to(ARTIFACTS_NAME)
    return export / TREE / below


# --------------------------------------------------------------------------- #
# The pool's pictures, written down rather than carried.
# --------------------------------------------------------------------------- #
def pool_pictures(log=print) -> list[dict]:
    """One row per candidate the solve can seat: its picture, size, sha256 and build.

    Through `solve.pool` itself rather than a restatement of its refusals, so
    "can seat" means exactly what the seating means by it. Loads the pool: this
    is a pool-holding step.
    """
    from fractal_wallpapers import engine_fingerprint
    from fractal_wallpapers.curation import candidate_ledger, solve
    from fractal_wallpapers.paths import rehome

    candidates, _refused = solve.pool(log=log)
    wanted = {candidate.key for candidate in candidates}
    built: dict[str, str] = {}
    for row in candidate_ledger.stream():
        if row.get("key") in wanted:
            built[str(row["key"])] = candidate_ledger.engine_of(row)
    try:
        build = engine_fingerprint.current()
    except Exception:  # noqa: BLE001 — provenance, never a gate; see `store.live_engine`
        build = engine_fingerprint.UNKNOWN
    tiers = Tiers.current()
    out = []
    started = time.perf_counter()
    for number, candidate in enumerate(sorted(candidates, key=lambda c: c.key), start=1):
        where = rehome(candidate.picture, tiers)
        drew = built.get(candidate.key, engine_fingerprint.UNKNOWN)
        if drew == engine_fingerprint.UNKNOWN:
            rederivable = "unknown_build"
        elif drew == build:
            rederivable = "same_build"
        else:
            rederivable = "other_build"
        out.append(
            {
                "schema": SCHEMA,
                "key": candidate.key,
                "picture": candidate.picture,
                "bytes": where.stat().st_size,
                "sha256": sha256_of(where),
                "engine": drew,
                "rederivable": rederivable,
            }
        )
        if number % 20_000 == 0:
            log(
                f"[pictures] {number:,}/{len(candidates):,} hashed in "
                f"{time.perf_counter() - started:.0f}s"
            )
    return out


# --------------------------------------------------------------------------- #
# Export.
# --------------------------------------------------------------------------- #
def export(to: Path, roster=ROSTER, pictures: bool = True, log=print) -> dict:
    """Copy the roster to `to`, and write the manifest that proves what was copied."""
    to = Path(to)
    if to.exists() and any(to.iterdir()):
        raise PortableRefusal(
            f"{to} already holds files. An export goes to an empty directory, so the manifest "
            "is the whole of what is there."
        )
    rows = resolve(roster)
    log(f"[export] {len(rows):,} file(s) named by {len(roster)} roster entries")
    started = time.perf_counter()
    total = 0
    for number, row in enumerate(rows, start=1):
        measured = _hash_copy(row["source"], _stored_path(to, row))
        row.update(measured)
        total += measured["bytes"]
        if number % 200 == 0 or number == len(rows):
            log(
                f"[export] {number:,}/{len(rows):,} files, {total / 2**30:.2f} GiB, "
                f"{time.perf_counter() - started:.0f}s"
            )
    for row in rows:
        stored = _stored_path(to, row)
        if stored.stat().st_size != row["bytes"] or sha256_of(stored) != row["sha256"]:
            raise PortableRefusal(f"{stored} does not read back as the bytes copied into it")
    log(f"[export] every copy read back identical ({total / 2**30:.2f} GiB)")

    picture_summary = None
    if pictures:
        listed = pool_pictures(log=log)
        path = to / PICTURES_NAME
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for row in listed:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        picture_summary = {
            "file": PICTURES_NAME,
            "sha256": sha256_of(path),
            "pictures": len(listed),
            "bytes": sum(row["bytes"] for row in listed),
            "by_rederivable": dict(Counter(row["rederivable"] for row in listed)),
            "note": (
                "not carried: the candidates the solve can seat, whose pictures a fresh box "
                "puts back with `curate candidate-ledger re-render` before it solves"
            ),
        }
    reference = (
        _write_reference(to, rows, log=log)
        if any(entry.name == REFERENCE_ENTRY for entry in roster)
        else None
    )
    manifest = _manifest(rows, roster, picture_summary)
    manifest["reference"] = reference
    (to / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    log(f"[export] wrote {to / MANIFEST_NAME}")
    return manifest


#: The roster entry [`REFERENCE`] travels in.
REFERENCE_ENTRY = "reference solve"


def reference_invocation() -> str:
    """The exact command that re-seats [`REFERENCE`] on a box holding its stores."""
    return (
        f"fractal-wallpapers curate solve run --name reference_{REFERENCE['collection']} "
        f"--collection {REFERENCE['collection']} --no-render --no-sheet"
    )


def general_check_invocation() -> str:
    """The exact command that re-seats [`GENERAL_CHECK`] on a box holding its stores.

    `--n` and not `--collection`: the general pass is the one `curation.targets`
    has no row for, and its size is `tentative.RECORDED_SEATS`.
    """
    return (
        "fractal-wallpapers curate solve run --name reference_general "
        f"--n {GENERAL_CHECK['n']} --no-render --no-sheet"
    )


def _write_reference(to: Path, rows: list, log=print) -> dict:
    """Write `reference/README.md` for [`REFERENCE`]; refuse if its record did not travel.

    A reference the roster resolved to nothing is an export that would send a fresh
    box looking for a comparison target it does not have, so it refuses rather than
    writing a README about a record that is not there.
    """
    stamp = REFERENCE["stamp"]
    carried = [row for row in rows if REFERENCE_ENTRY in row["entries"]]
    if not any(row["path"].endswith(f"tentative/{stamp}/gallery.jsonl") for row in carried):
        raise PortableRefusal(
            f"the reference record {stamp} is not on this machine, so the export has no "
            "comparison target to carry. Take a fresh one (`curate solve record --collection "
            f"{REFERENCE['collection']}`), check a `--no-render` run re-seats it, and repoint "
            "`portable.REFERENCE`."
        )
    manifest_row = next(row for row in carried if row["path"].endswith("manifest.json"))
    held = json.loads(Path(manifest_row["source"]).read_text(encoding="utf-8"))
    n = int(held["solve"]["config"]["n"])
    record = held["solve"]["record"]
    text = "\n".join(
        [
            "# The reference solves",
            "",
            "**Two checks and they are two different passes.** The themed one below is the "
            "only comparison target on the collection path; the n = "
            f"{GENERAL_CHECK['n']} one after it is the general pass over the whole pool. "
            "A box that ran one has not run the other.",
            "",
            "## The themed check",
            "",
            f"- **Stamp:** `{stamp}` (tentative record, not published)",
            f"- **Collection:** `{REFERENCE['collection']}`, **n = {n}** (`curation/targets.py`)",
            f"- **Taken at commit:** `{held.get('source_commit')}`",
            f"- **Seats:** `artifacts/curation/tentative/{stamp}/gallery.jsonl`, and in order "
            f"as `seated` in `{record}`",
            "",
            "After `storage import`, `fetch-weights`, the release engine build and "
            "`curate candidate-ledger re-render --seatable`, run:",
            "",
            "```",
            reference_invocation(),
            "```",
            "",
            f"and compare `seated` in `artifacts/curation/solve/reference_"
            f"{REFERENCE['collection']}/solve.json` with the record's: the same {n} keys in "
            "the same order is a box whose stores, code and judges agree with this one. "
            "Run on the exporting box straight after the record was taken, on 2026-09-22, it "
            "re-seated all of them in order. "
            "A different engine fingerprint (read `storage import`'s `engine:` line) "
            "empties the score amendment's overlay, and that alone moves seats.",
            "",
            "**A themed record decays as the pool grows**: its bar is read off the cell's own "
            "best candidates, so a leg that adds rows to the cell re-ranks it. Mining closed "
            "before this record was taken, so a divergence on a box that has mined nothing "
            "since the import is the box and not the pool.",
            "",
            f"## The n = {GENERAL_CHECK['n']} check",
            "",
            f"- **Stamp:** `{GENERAL_CHECK['stamp']}` (`{GENERAL_CHECK['name']}`, kept and "
            "not published)",
            f"- **No collection**, **n = {GENERAL_CHECK['n']}** "
            "(`curation/tentative.py`'s `RECORDED_SEATS`), on the shipped fine bar",
            f"- **Seats:** `artifacts/curation/tentative/{GENERAL_CHECK['stamp']}/"
            "gallery.jsonl`, and in order as `seated` in "
            f"`artifacts/curation/solve/{GENERAL_CHECK['name']}/solve.json`",
            "",
            "After the same four steps, run:",
            "",
            "```",
            general_check_invocation(),
            "```",
            "",
            "and compare `seated` in `artifacts/curation/solve/reference_general/solve.json` "
            f"with the record's: the same {GENERAL_CHECK['n']} keys in the same order is a box "
            "whose stores, code and judges agree with this one. It re-seated all of them in "
            "order on the exporting box on 2026-09-21 and again on 2026-09-22, over the pool "
            "mining closed behind.",
            "",
        ]
    )
    path = to / REFERENCE_README
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    log(f"[export] wrote {path}")
    return {
        "file": REFERENCE_README,
        "sha256": sha256_of(path),
        "stamp": stamp,
        "collection": REFERENCE["collection"],
        "n": n,
        "invocation": reference_invocation(),
        "general": {
            "stamp": GENERAL_CHECK["stamp"],
            "name": GENERAL_CHECK["name"],
            "n": GENERAL_CHECK["n"],
            "invocation": general_check_invocation(),
        },
    }


def _manifest(rows: list, roster, pictures: dict | None) -> dict:
    from fractal_wallpapers import engine_fingerprint

    try:
        build = engine_fingerprint.current()
    except Exception:  # noqa: BLE001 — recorded as unknown, the same as a row that never said
        build = engine_fingerprint.UNKNOWN
    try:
        commit = subprocess.run(
            ["git", "-C", str(repo_root()), "rev-parse", "HEAD"],
            capture_output=True,
            check=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    weights = repo_root() / "models" / "weights.json"
    heads = (
        {
            name: head.get("sha256")
            for name, head in json.loads(weights.read_text(encoding="utf-8"))
            .get("heads", {})
            .items()
        }
        if weights.is_file()
        else {}
    )
    by_entry: dict[str, list] = {entry.name: [0, 0] for entry in roster}
    for row in rows:
        for name in row["entries"]:
            by_entry[name][0] += 1
            by_entry[name][1] += row["bytes"]
    return {
        "schema": SCHEMA,
        "exported": datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
        "commit": commit,
        "engine": build,
        "weights": heads,
        "files_count": len(rows),
        "bytes": sum(row["bytes"] for row in rows),
        "by_tier": dict(Counter(row["tier"] for row in rows)),
        "entries": [
            {
                "name": entry.name,
                "root": entry.root,
                "patterns": list(entry.patterns),
                "verbs": list(entry.verbs),
                "why": entry.why,
                "files": by_entry[entry.name][0],
                "bytes": by_entry[entry.name][1],
            }
            for entry in roster
        ],
        "pictures": pictures,
        "files": [
            {key: row[key] for key in ("path", "root", "tier", "bytes", "sha256", "entries")}
            for row in rows
        ],
    }


# --------------------------------------------------------------------------- #
# Import.
# --------------------------------------------------------------------------- #
def _stored_name(row: dict) -> str:
    """One manifest row's name relative to an export's root, as a posix string."""
    return _stored_path(Path(), row).as_posix()


def _roots(source) -> tuple[Path, ...]:
    """`source` as the roots of one export: a path, or several a transfer split it across."""
    if isinstance(source, str | Path):
        return (Path(source),)
    roots = tuple(Path(root) for root in source)
    if not roots:
        raise PortableRefusal("no export directory was named.")
    return roots


def layout(source) -> dict[str, Path]:
    """`{name relative to the export root: file}` over every root of one export.

    **One export may arrive as several directories.** A transfer tool split the
    2026-09-16 export by subtree into two sibling folders with no file in both,
    and the manifest validated the hand-merge fine — it just would not build it.
    So the roots are merged by relative path here, before anything is checked: a
    name in two roots is one file only if its bytes are, and two different files
    under one name are refused, because nothing could say which the manifest meant.
    """
    found: dict[str, Path] = {}
    clashes = []
    for root in _roots(source):
        if not root.is_dir():
            raise PortableRefusal(f"{root} is not a directory. Nothing was written.")
        for here, _, files in os.walk(root):
            for name in files:
                path = Path(here) / name
                relative = path.relative_to(root).as_posix()
                held = found.get(relative)
                if held is None:
                    found[relative] = path
                elif held.stat().st_size != path.stat().st_size or (
                    sha256_of(held) != sha256_of(path)
                ):
                    clashes.append(relative)
    if clashes:
        raise PortableRefusal(
            f"{len(clashes)} name(s) are under more than one --from root with different bytes, "
            f"e.g. {clashes[:5]}. Nothing was written."
        )
    return found


def read_manifest(source) -> dict:
    roots = _roots(source)
    held = [root / MANIFEST_NAME for root in roots if (root / MANIFEST_NAME).is_file()]
    if not held:
        raise PortableRefusal(
            f"no {MANIFEST_NAME} under {[str(root) for root in roots]}, so it is not an export."
        )
    path = held[0]
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if any(json.loads(other.read_text(encoding="utf-8")) != manifest for other in held[1:]):
        raise PortableRefusal(f"the --from roots carry different {MANIFEST_NAME} files.")
    if manifest.get("schema") != SCHEMA:
        raise PortableRefusal(f"{path}: schema {manifest.get('schema')!r}, expected {SCHEMA}")
    return manifest


def destination_of(row: dict, root: Path, archive: Path | None) -> Path:
    """Where one manifest row lands: its tier where the box has one, `root` where not."""
    if row["root"] == CHECKOUT:
        return repo_root() / PurePosixPath(row["path"])
    below = PurePosixPath(row["path"]).relative_to(ARTIFACTS_NAME)
    base = archive if (row["tier"] == ARCHIVE and archive is not None) else root
    return Path(base) / below


def verify_export(source, manifest: dict, log=print) -> dict:
    """Every named file present at its size and sha256, and nothing else there.

    `source` is one export directory or several ([`layout`]). The merged layout is
    returned, so an import copies from exactly the files it verified.
    """
    files = layout(source)
    named = {_stored_name(row): row for row in manifest["files"]}
    reference = manifest.get("reference")
    beside = {MANIFEST_NAME, PICTURES_NAME}
    if reference:
        beside.add(PurePosixPath(reference["file"]).as_posix())
    extra = sorted(name for name in files if name not in beside and name not in named)
    if extra:
        raise PortableRefusal(
            f"{len(extra)} file(s) in {source} are not in its manifest, e.g. "
            f"{extra[:5]}. Nothing was written."
        )
    bad = []
    for number, (name, row) in enumerate(named.items(), start=1):
        path = files.get(name)
        if (
            path is None
            or path.stat().st_size != row["bytes"]
            or (sha256_of(path) != row["sha256"])
        ):
            bad.append(row["path"])
        if number % 500 == 0:
            log(f"[import] verified {number:,}/{len(named):,}")
    pictures = manifest.get("pictures")
    if pictures and (
        PICTURES_NAME not in files or sha256_of(files[PICTURES_NAME]) != pictures["sha256"]
    ):
        bad.append(PICTURES_NAME)
    if reference:
        written = files.get(PurePosixPath(reference["file"]).as_posix())
        if written is None or sha256_of(written) != reference["sha256"]:
            bad.append(reference["file"])
    if bad:
        raise PortableRefusal(
            f"{len(bad)} file(s) do not match the manifest, e.g. {bad[:5]}. Nothing was written."
        )
    roots = _roots(source)
    log(
        f"[import] {len(named):,} file(s) match the manifest"
        + (f", merged from {len(roots)} roots" if len(roots) > 1 else "")
    )
    return files


def import_(source, root: Path, archive: Path | None = None, log=print) -> dict:
    """Land an export at `root` (and `archive`, where the box has one). Refuses before writing.

    `source` is one export directory, or every directory a transfer split one
    export across — merged by relative path through [`layout`] before the check.
    """
    root = Path(root)
    archive = None if archive is None else Path(archive)
    manifest = read_manifest(source)
    files = verify_export(source, manifest, log=log)

    landing = [(row, destination_of(row, root, archive)) for row in manifest["files"]]
    present = [str(where) for _, where in landing if where.exists()]
    if present:
        raise PortableRefusal(
            f"{len(present)} destination(s) already exist, e.g. {present[:5]}. An import lands "
            "on a box that does not hold these files; overwriting or merging one would be "
            "the two-copies failure the tiers refuse. Nothing was written."
        )
    if archive is not None:
        collided = sorted(
            {
                PurePosixPath(row["path"]).parts[1]
                for row, where in landing
                if row["root"] != CHECKOUT
                and (
                    (root if row["tier"] == ARCHIVE else archive)
                    / PurePosixPath(row["path"]).parts[1]
                ).exists()
            }
        )
        if collided:
            raise PortableRefusal(
                f"these names would land in one tier while the other already holds them: "
                f"{collided[:10]}. Nothing was written."
            )

    written = 0
    for number, (row, where) in enumerate(landing, start=1):
        copied = _hash_copy(files[_stored_name(row)], where)
        if copied["sha256"] != row["sha256"]:
            raise PortableRefusal(f"{where} was written as bytes the manifest does not name")
        written += copied["bytes"]
        if number % 200 == 0 or number == len(landing):
            log(f"[import] {number:,}/{len(landing):,} files, {written / 2**30:.2f} GiB")
    return {
        "files": len(landing),
        "bytes": written,
        "from": [str(held) for held in _roots(source)],
        "root": str(root),
        "archive": None if archive is None else str(archive),
        "by_tier_landed": dict(
            Counter(
                CHECKOUT
                if row["root"] == CHECKOUT
                else (ARCHIVE if row["tier"] == ARCHIVE and archive is not None else HOT)
                for row, _ in landing
            )
        ),
        "exported_engine": manifest.get("engine"),
        "pictures": manifest.get("pictures"),
    }


def engine_agrees(manifest: dict) -> tuple[str, bool | None]:
    """`(this build's fingerprint, whether it is the exporting build's)`; None if unknowable."""
    from fractal_wallpapers import engine_fingerprint

    try:
        build = engine_fingerprint.current()
    except Exception:  # noqa: BLE001 — an unbuilt engine is an answer, not an error here
        return engine_fingerprint.UNKNOWN, None
    exported = manifest.get("engine")
    if not exported or exported == engine_fingerprint.UNKNOWN:
        return build, None
    return build, build == exported


__all__ = [
    "CHECKOUT",
    "GENERAL_CHECK",
    "MANIFEST_NAME",
    "PICTURES_NAME",
    "REFERENCE",
    "REFERENCE_ENTRY",
    "REFERENCE_README",
    "ROSTER",
    "SCHEMA",
    "SEQUENCE_GLOB",
    "TREE",
    "Entry",
    "PortableRefusal",
    "destination_of",
    "engine_agrees",
    "export",
    "import_",
    "kept_solve_records",
    "layout",
    "pool_pictures",
    "read_manifest",
    "resolve",
    "verify_export",
]
