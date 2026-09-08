"""The ledger's rows and its score sidecar: where they are, and how they are read.

The bottom of this package and the bottom of the import graph. Nothing here
reaches a judge, a palette, a label store or a leg — it knows the two files, the
tiers they live on, the manifests that track them, and how to get rows in and out
of them. Everything above it in the package drives something; this does not.

## Record everything; filter nothing

No quality bar admits a row here. A floor is a reading of a score, a score is a
reading of a judge, and both move; the recipe and the pixels do not. So a
candidate a floor rejected, a candidate a person **rejected**, and a candidate
that took a seat are all one row each, and the rejection travels on the row for a
solver to honour. Record-and-rank, in [`curation.colors`]' sense.

## Scores are not part of a recipe's identity

They are in a **sidecar**, keyed `(recipe key, judge artifact, regime)`. A judge
adoption invalidates every score in this project and nothing else — not a
picture, not a recipe, not a colour — and a store that carried the score on the
recipe row would have to rewrite every row to say so. The sidecar is also what
makes an honest comparison possible at all: a recipe read by two judges appears
here twice, once per artifact, and the two numbers are two facts rather than one
overwriting the other.

**It holds ONE artifact today and the key is still right.** The two retired
judges' rows — 289,645 of 574,162, half the file — were dropped on 2026-09-06
once the comparisons they backed had been taken; `curation/README.md`'s *The two
retired artifacts were dropped* has the derivation. The morning after the next
adoption this is back to two, which is what the key is for.

The backfill measured the other half of that. The 126 duplicate renders make 128
pairs of byte-identical pictures; 59 of the pairs disagree on `P(>=3)`, and the
largest disagreement is 2.8e-7. So the judge is reproducible to about the seventh
decimal on identical bytes and no further, which is why the sidecar records what
a run **read** rather than promising that a recipe has a score.
## Where it lives

The rows are megabytes and the history guard acts at 1 MiB a file, so this gets
what the supply sidecar and the neutral-render embeddings get: the file under
`artifacts/`, a copy on the archive tier, and a **manifest** in the history
saying how many rows, how many bytes and which sha256 that copy is.
"""

from __future__ import annotations

import json
from pathlib import Path

from fractal_wallpapers import engine_fingerprint
from fractal_wallpapers.curation import durability, records
from fractal_wallpapers.paths import archive_root, hot_root, under

#: The schema every ledger and sidecar row carries.
SCHEMA = 1


#: The subtree both files live in, under the regenerable tree.
UNIT = "candidate_ledger"


#: What the three files that make up the store are called. The flatness sidecar
#: is [`curation.flatness.SIDECAR_NAME`], beside these and pruned with them.
ROWS_NAME = "rows.jsonl"


SCORES_NAME = "scores.jsonl"


#: What a candidate's engine build is recorded as. Every candidate render in
#: every pass and every run predates [`engine_fingerprint`], which stamps a view
#: directory rather than a candidate directory, so there is nothing to read: the
#: whole backfilled pool is pre-stamp material accepted as unknown-engine, by
#: rule. Spelled through the fingerprint's own constant and not as a second word
#: for one fact — "nobody wrote it down" is never equal to a real build, which is
#: the property that makes it safe to compare against.
UNKNOWN_ENGINE = engine_fingerprint.UNKNOWN


#: What a row calls the build that drew it. One field, sixteen hex characters and
#: about 30 bytes against a row's ~1,290 — 2.3% — which is the whole cost of a
#: pool that can be asked, in a year, which engine made a picture.
ENGINE_FIELD = "engine"


#: Which store a backfilled row came out of. A run records every scored candidate
#: in the tracked release store; a retired gallery pass recorded its attempts in
#: its own untracked gate store instead.
FROM_RELEASE = "release"


#: **Kept though nothing writes it any more.** The gate store was retired on
#: 2026-09-06 with the passes, so [`rebuild.sources`] stamps only `FROM_RELEASE` —
#: but 14,316 rows already in the ledger carry this one and readers split on it.
FROM_GALLERY = "gallery"


class LedgerError(RuntimeError):
    """The ledger cannot be built, or cannot be read."""


# --------------------------------------------------------------------------- #
# Where it all is.
# --------------------------------------------------------------------------- #
def store_root() -> Path:
    """The subtree the whole store sits in, on whichever tier it is on."""
    return under("curation", UNIT)


def rows_path() -> Path:
    """The ledger: one row per recipe."""
    return store_root() / ROWS_NAME


def scores_path() -> Path:
    """The score sidecar: one row per (recipe, judge artifact, regime)."""
    return store_root() / SCORES_NAME


def manifest_dir() -> Path:
    """The tracked directory the store's manifests live in."""
    return records.default_root() / UNIT


def backup_path(name: str) -> Path:
    """The durable copy, beside the gate store's and the sidecar's.

    Off a root rather than through `under()`, for [`durability`]'s reason: a copy
    that resolved through the tiers would land on the tier the original is
    already on, which is the one place a second copy is no use.

    Public because the sidecars beside this store are not all owned by it:
    [`curation.flatness`] keeps its own file in the same subtree and must put its
    copy in the same place, and a second spelling of this path is how one of them
    ends up backed up somewhere nothing looks.
    """
    archive = archive_root()
    root = hot_root() if archive is None else archive
    return Path(root) / durability.BACKUP_UNIT / UNIT / name


def _facts(path: Path) -> dict:
    """What the rows add to their own manifest: the population, and the colour rule.

    The rule and the codebook live here rather than on each row. They are
    identical on every one of them, and a share vector read next year under a
    moved codebook is a different number wearing the same name — which is a fact
    about the *store* and belongs where the store is described.
    """
    from fractal_wallpapers.palettes import codebook, dominance

    runs: dict = {}
    partitions: dict = {}
    locations: set = set()
    for row in _stream_of(Path(path)):
        run = str(row["provenance"]["run"])
        runs[run] = runs.get(run, 0) + 1
        partition = str(row.get("partition"))
        partitions[partition] = partitions.get(partition, 0) + 1
        locations.add(str((row.get("location") or {}).get("key")))
    return {
        "runs": dict(sorted(runs.items())),
        "partitions": dict(sorted(partitions.items())),
        "locations": len(locations),
        "colour": {
            "rule": dominance.RULE,
            "codebook": {
                "sigma": codebook.SIGMA,
                "swatches": len(codebook.names()),
                "census_size": list(codebook.CENSUS_SIZE),
            },
        },
        "engine": UNKNOWN_ENGINE,
    }


def durable_rows() -> durability.Durable:
    """The ledger as a [`durability.Durable`] — how it is saved, checked, restored."""
    return durability.Durable(
        name="the candidate ledger",
        live=rows_path(),
        copy=backup_path(ROWS_NAME),
        manifest=manifest_dir() / "rows.manifest.json",
        why_not_tracked=(
            "one row per recipe at about a kilobyte and a half a row, which is tens of "
            "megabytes against a 1 MiB per-file history guard, and rewritten whole on every "
            "backfill because the store upserts by key. The manifest is what the history "
            "keeps; the bytes live on both tiers."
        ),
        save_command="fractal-wallpapers curate candidate-ledger save",
        restore_command="fractal-wallpapers curate candidate-ledger restore",
        rebuild_command="fractal-wallpapers curate candidate-ledger backfill",
        facts=_facts,
    )


def durable_scores() -> durability.Durable:
    """The score sidecar as a [`durability.Durable`]."""
    return durability.Durable(
        name="the candidate ledger's scores",
        live=scores_path(),
        copy=backup_path(SCORES_NAME),
        manifest=manifest_dir() / "scores.manifest.json",
        why_not_tracked=(
            "one row per recipe per judge artifact, so it grows with the ledger and again "
            "with every judge this project ships. Same guard, same answer as the rows."
        ),
        save_command="fractal-wallpapers curate candidate-ledger save",
        restore_command="fractal-wallpapers curate candidate-ledger restore",
        rebuild_command="fractal-wallpapers curate candidate-ledger backfill",
        facts=lambda path: {},
    )


def live_artifact() -> str:
    """The sha256 of the judge shipped right now. What a score has to be read on."""
    from fractal_wallpapers.curation import floors

    return floors.live_stamp(floors.SCORING_HEAD)


def live_engine() -> str:
    """The build a leg is drawing with, or [`UNKNOWN_ENGINE`] where it cannot be asked.

    **Called once by a leg, before its render loop, and never per row.**
    [`engine_fingerprint.current`] costs six renders the first time a process asks
    and is cached after that, so the cost is real and it is paid where a leg can
    see it — not spread invisibly over a hundred thousand row builds.

    An engine that will not fingerprint gives [`UNKNOWN_ENGINE`] rather than
    raising. This field is **provenance and never a gate**: a leg that has already
    made pictures must not fail at the moment it writes them down because the
    probe set would not render, and a row that says "nobody wrote it down" is
    exactly what such a leg produced.
    """
    try:
        return engine_fingerprint.current()
    except (engine_fingerprint.FingerprintError, OSError, RuntimeError):
        return UNKNOWN_ENGINE


def engine_of(stored: dict) -> str:
    """The build a row says drew it. [`UNKNOWN_ENGINE`] where the row says nothing.

    **One spelling, reader-side.** The whole standing pool predates the stamp, so
    a missing field is the ordinary case and not an error; a reader that spelled
    it `None`, `""` and `"unknown"` in three places would have three different
    populations of pre-stamp material.

    Nothing in this project **acts** on the answer. It is not in the recipe key,
    [`labeling.finished.check`] does not read it, `curate solve` and
    `curate headroom` do not read it, and a row whose stamp disagrees with the
    live build is admitted, scored and seatable exactly like any other. The
    guard that a picture is still the picture that was judged is a *re-render*
    (`tests/test_renders.py`), and this field does not become one.
    """
    return str((stored or {}).get(ENGINE_FIELD) or UNKNOWN_ENGINE)


def present_pictures(rows=None) -> set:
    """`{key}` for every row whose picture is **on disk**, as one batched pass.

    THE answer to "does this row still have a picture", and the only one: naming
    a picture and having one are different questions, and the two-K era made the
    difference 30,040 rows wide by design. [`prune`] closed it — a picture goes
    with its row — but the question stays worth asking, because a row that names
    an absent picture is exactly what a half-finished prune leaves behind.

    Two things make this affordable enough to sit in `solve.pool`, which every
    seating and every headroom census runs. `rehome` is called with one shared
    [`Tiers`] snapshot rather than resolving the settings per row — 1.0 s over
    the store against 215 s. And existence is answered by listing each pictures
    directory once instead of stat-ing each file: the 128,368 rows live in 21
    directories, which is 2.6 s of `scandir` against 12.8 s of `is_file`. Both
    numbers are this store on this machine, 2026-08-28.

    A row that names nothing, or whose name has no artifacts component for
    `rehome` to read, is absent — there is no picture either way.
    """
    import os
    from collections import defaultdict

    from fractal_wallpapers.paths import Tiers, rehome

    stored = read() if rows is None else rows
    tiers = Tiers.current()
    homed: dict = {}
    wanted: dict = defaultdict(set)
    for row in stored:
        named = row.get("picture")
        if not named:
            continue
        where = rehome(named, tiers)
        if where is None:
            continue
        homed[str(row["key"])] = where
        wanted[where.parent].add(where.name)

    listing: dict = {}
    for directory in wanted:
        try:
            listing[directory] = {entry.name for entry in os.scandir(directory)}
        except OSError:
            listing[directory] = set()
    return {key for key, where in homed.items() if where.name in listing.get(where.parent, ())}


# --------------------------------------------------------------------------- #
# The other direction: pictures on disk that no record names.
# --------------------------------------------------------------------------- #
#: The subtrees under `curation` that hold pool pictures. Swept 2026-09-02 over
#: 177,993 rows: `depth` 158,628 - `runs` 11,875 - `mine` 4,566 -
#: `reframe_draw` 2,283 - `hunt` 641, and **no row pointed anywhere else at all**.
#: The list is written down rather than discovered per call because it is what
#: bounds [`orphans`] — a sweep that found its own subtrees would follow the tree
#: wherever it grew.
#:
#: **`remode` joined on 2026-09-04 and adding one here is half of shipping a leg.**
#: [`curation.remode`] keeps its renders under `remode/<leg>/pictures`, and a
#: subtree absent from this tuple is not merely unswept: `orphans` enumerates
#: these names and no others, so a killed leg's pictures would sit on disk with no
#: row anywhere and nothing in the project able to find them. `tests/test_remode.py`
#: pins the membership for that reason rather than as a spelling check.
#:
#: **`label_migration` joined on 2026-09-08** for the same reason, and it is the
#: first member whose pictures were not drawn by a leg of this package at all:
#: [`curation.label_migration`] renders a candidate for every human verdict in a
#: staging store under `scratch/`, and its `merge` stage moves the ones it submits
#: into `label_migration/<store name>/pictures` precisely so that they are
#: reachable from here. `tests/test_label_migration.py` pins the membership.
POOL_SUBTREES = ("depth", "runs", "mine", "reframe_draw", "hunt", "remode", "label_migration")


#: What every leg calls the directory it keeps its candidates in. [`orphans`]
#: looks at `<subtree>/<leg>/pictures` and at **no other shape**, which is what
#: keeps it structurally unable to reach a leg's `fields/`, its `candidates/`,
#: its `release/` or a sheet, whatever any record says.
PICTURES_NAME = "pictures"


#: What [`orphans`]'s `unmerged` takes to mean *every leg it would otherwise list*.
#: A string rather than a bool so the parameter has one type: a caller either
#: names legs or names all of them, and there is no third spelling.
ALL_UNMERGED = "all"


# --------------------------------------------------------------------------- #
# Reading and writing.
# --------------------------------------------------------------------------- #
def stream(path: Path | None = None):
    """Every ledger row, one at a time, in key order. **The reader.**

    Streaming rather than reading whole, which is what this was until
    2026-08-29. `read` built the whole file into one string, split it, and kept
    366,236 dictionaries: 46.5 s and several gigabytes of peak, paid fourteen
    times in a session by readers that each wanted a handful of fields per row.
    A generator costs one line at a time, and a caller that genuinely needs the
    list still says so by calling [`read`].

    An absent file yields nothing rather than raising: a checkout that has never
    backfilled is a state and not a failure, and every caller here already treats
    an empty ledger as one.
    """
    where = rows_path() if path is None else Path(path)
    yield from _stream_of(where)


def stream_scores(path: Path | None = None):
    """Every sidecar row, one at a time, in key order."""
    yield from _stream_of(scores_path() if path is None else Path(path))


def read(path: Path | None = None) -> list[dict]:
    """Every ledger row on record, in key order, as a list.

    Off [`stream`], so the 1.1 GB intermediate string is gone even here. A
    caller that only sweeps the rows once should take the stream: this holds
    every row at once because that is what its name promises.
    """
    return list(stream(path))


def read_scores(path: Path | None = None) -> list[dict]:
    """Every sidecar row on record, in key order."""
    return list(stream_scores(path))


def by_key(keys, path: Path | None = None) -> dict:
    """`{key: row}` for the keys asked for, in one streamed pass. **The lookup.**

    For a caller that wants a handful of rows out of a store of hundreds of
    thousands — the release render behind a solve's seats is a hundred and fifty
    of them. It stops as soon as it has them all, so a seat set that happens to
    sit early in key order costs a fraction of the file and never costs more than
    one pass of it.
    """
    wanted = {str(key) for key in keys}
    out: dict = {}
    for row in stream(path):
        key = str(row["key"])
        if key in wanted:
            out[key] = row
            if len(out) == len(wanted):
                break
    return out


def _stream_of(path: Path):
    if not path.is_file():
        return
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def write(rows) -> tuple[Path, int, int]:
    """Merge `rows` into the ledger by key. `(path, total, new)`. **Internal.**

    [`records.upsert_file`], which is what every other flat store here is written
    with: same key, same ordering, and a re-backfill over an unchanged pool
    writes byte-identical output.

    Every caller outside this module goes through [`merge`] instead, and
    `tests/test_ledger_tracking.py` is what holds that: this writes the bytes and
    says nothing about them, and a store written without being recorded is the
    era this module just spent.
    """
    path = rows_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    total, new = records.upsert_file(path, rows)
    return path, total, new


def write_scores(rows) -> tuple[Path, int, int]:
    """Merge score readings into the sidecar by key. `(path, total, new)`. **Internal.**"""
    path = scores_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    total, new = records.upsert_file(path, rows)
    return path, total, new


#: How many rows one (location, `recipe.mode`) pair keeps, ranked by the shipped
#: [`curation.rank_key`]. **The** constant: a picture is kept if and only if its
#: row is, so this bounds the pictures too and there is no second number.
#:
#: **Five** since 2026-09-06, Matt's decision at ckpt 112. It was **three** from
#: 2026-08-29, settled on the replay in `PRUNE1_replay_bestk_report.md`: at K=3
#: the solve at n=150 reproduced the full pool's seats exactly, and at K=2 it did
#: not. What raised it is a different question — not whether the keep reproduces
#: today's seats but which seats a deeper pool would have produced, which the
#: retained rows cannot show because the rest were pruned before they could
#: become seats. Simulated over 674,089 attempts, keep 4 costs 1.221x and holds
#: 99.3% of today's live release seats where keep 5 costs 1.385x and holds 100%;
#: **retention is not retroactive, so an error toward 4 is permanent** and that
#: asymmetry is what chose 5.
#:
#: It was one of two until 2026-08-29 — `retention.KEEP_PER_PAIR` kept five
#: **pictures** a pair by raw `P(>=4)`, on a different ranking, and the two were
#: not nested, so a row in the top three by rank could be sixth by `P(>=4)` and
#: have lost its picture. That second spelling is gone, and the coincidence that
#: this constant is now also five is exactly that — a coincidence, on the shipped
#: rank key and over rows rather than pictures.
RETAIN_PER_PAIR = 5


#: Why a row survives [`prune`]. The first is [`retention.RANKED`]; the five
#: after it are the protections, and each one keeps a row the rank let go.
RETAINED_RANKED = "ranked"


RETAINED_SEATED = "seated_in_a_live_release_row"


RETAINED_REJECTED = "carries_a_human_rejected_verdict"


RETAINED_LABELED = "a_label_row_joins_to_it"


RETAINED_FITTED = "named_by_the_rank_key_population"


#: A seat in a **tentative gallery** — [`curation.tentative`] — which is a
#: recorded gallery somebody has started referring to pictures by. It protects
#: for the same reason a live release row does and needs its own class for a
#: sharper one: a seat is chosen on the gallery's objective, over a view, against
#: the colour rules, and none of that is being in the top [`RETAIN_PER_PAIR`] of
#: its own (location, mode) pair, so the rank drops these routinely. An ID that stopped
#: resolving would take its picture with it and there is no way to notice.
RETAINED_TENTATIVE = "seated_in_a_tentative_gallery"


RETAINED_REASONS = (
    RETAINED_RANKED,
    RETAINED_SEATED,
    RETAINED_REJECTED,
    RETAINED_LABELED,
    RETAINED_FITTED,
    RETAINED_TENTATIVE,
)


#: The two fields of the block that say the row's palette was **asked for a
#: colour**, so a rate taken over the store can drop it. `drawn_for` is the aimed
#: arm's own cell, present on that arm's rows alone; `drawn_cells` is the whole
#: leg's `--draw-cells` narrowing and is on every row such a leg made. Both are
#: written only when the draw named one, so a row from an unnarrowed leg carries
#: the two fields this block has always carried and nothing more.
ASKED_FOR = ("drawn_for", "drawn_cells")


def save(log=print) -> dict:
    """Copy both files to the archive tier and write both manifests."""
    return {
        "rows": durability.save(durable_rows(), log=log),
        "scores": durability.save(durable_scores(), log=log),
    }


def check(log=print) -> dict:
    """Are both files whole, against what the manifests say they were."""
    return {
        "rows": durability.check(durable_rows(), log=log),
        "scores": durability.check(durable_scores(), log=log),
    }


def restore(force: bool = False, log=print) -> dict:
    """Bring both files back from the archive tier."""
    return {
        "rows": durability.restore(durable_rows(), force=force, log=log),
        "scores": durability.restore(durable_scores(), force=force, log=log),
    }


#: Which stage of a decision row is preferred as a render's own record where the
#: same render carries two. The attempt is what made the picture; the seat is a
#: verdict on it taken later, and the two carry the same recipe either way.
MADE_IT = "gate"


# --------------------------------------------------------------------------- #
# The census: what we already own, over the axes constraints act on.
# --------------------------------------------------------------------------- #
#: The trivial first solve the feasibility read is taken against: twenty
#: wallpapers, one per location, the hard diversity radius, the colour ceiling and
#: the group cap as budgets, the mode floors soft. Not a default anything solves
#: at — a number to answer "would any of this bind" against.
FIRST_SOLVE = 20
