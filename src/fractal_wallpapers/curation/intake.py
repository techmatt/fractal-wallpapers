"""Which locations curation is offered, and in what order.

A release starts from the walk ledgers it is bound to. This module turns their
union into an ordered offer — best first, per partition — and it answers
exactly one question plus the supply arithmetic that question implies. It does
not decide how many pictures to make ([`budget`]), it does not choose a palette
([`colorize`]), and it does not select a release ([`selection`]).

## The order is read at the moment it is used, and nothing is frozen

A ledger row now records the head's verdict at the moment the walk found the
place, which is what lets the supply engine's census move on a harvest alone.
Curation does **not** read that number. It re-scores the whole standing supply
into a sidecar this module owns, and ranks on `P(≥3)` descending at read time.

**The ledgers are never rewritten.** A ledger's score is a verdict frozen on the
day it was minted; when the head that produced it is retrained the pipeline has
to either believe a stale number or delete the row. Both have happened, and the
second one is worse: a head flip once took an intake from about fourteen hundred
locations to sixteen. Here a flip is a re-score of the sidecar, the ledgers are
untouched, and an old ledger score degrades the *rank quality* of a row rather
than removing it. The two readings are the same recipe through the same head
([`fractal_wallpapers.models.location_view`] owns it, so they cannot drift) and
they share one view cache, so re-scoring a harvested location costs the head and
not the engine.

## The rank orders; the level is not a quantity

An earlier standing rule said **never order or gate the mandelbrot offer by
location-head rank**. It is retired, on the batch that measured it.
`mandelbrot_offer_body` (n=150, thirty rows in each of five equal-count bands by
`P(≥3)` over the offer's junk-floor survivors, 2026-08-19) has quality decaying
with the head's score monotonically: Spearman ρ = 0.582 over the body and 0.410
within bands 1–4 alone, 90% keepers in the top two fifths against 46.7% in the
fourth. **Reading this offer best-first is correct**, which is what this module
does, and the retired rule was a claim about the order.

**What failed is the calibrated level.** The same read corrected downward on
38.7% of that body and upward on 4.0%, and of the 36 rows the head prefilled at
tier 4, seven held — a tier-4 read is close to uninformative on this material. So
the score is used as a *rank* and never as a quantity: no cut here is placed by
asking what probability means "good enough", and the two that exist are floors
rather than operating points. Floors still act — the junk floor at intake, on
this same head's scale (see [`floors`]).

**That measurement was taken on the head that has since retired.** The ρ = 0.582
body was read through `4b60deb9…`; the head serving since 2026-08-20 agrees with
it at ρ = 0.891 over this sidecar, which is close enough to keep ranking on and
far enough that the number is not transferable. The candidate's own
rank-within-offer quality is **unmeasured** and is to be re-measured only when a
decision turns on it.

## The ledgers are bound, not defaulted

Which ledgers is a decision and it is taken once, by [`binding`], at the run's
entry — never re-derived here and never defaulted to "everything under
`artifacts/`". Two harvests ranked into one offer is one funnel printed over two
populations, and nothing about it looks wrong. Every entry point in this module
resolves through the binding, so an unbound invocation with more than one ledger
present refuses and lists them rather than reading them all.

## One reader, and it is the one the supply engine already has

`supply.ledgers.admitted_union` is the single union walk over every ledger: it
checks the schema, deduplicates on location identity rather than on a row id
(the ledgers overlap, and two runs mint the same node id for different places),
and reports what it could not key. Curation reaches it with its own predicate —
**structural gates only** — because admission at the walk's own good floor is a
different question from admission to a colorize, and asking the union for one
while meaning the other is how a population and its denominator come apart.

## The one enforcing cut, and the two numbers beside it

The junk floor acts, here, at the one site that draws the colorize pool. What
comes with it is arithmetic rather than judgement:

* [`emit_cap`] — a partition may release at most a quarter of its floor-passing
  supply, so a thin partition ships nothing rather than its own least-bad row;
* [`slots`] — the release mix apportioned into whole slots, with a guaranteed
  floor of one for any partition that has something worth keeping. Both go
  through `supply.apportion`, which already owns the largest-deficit rule and the
  guarantee fixed point; a second copy here would be a second answer.
"""

from __future__ import annotations

import json
from pathlib import Path

from fractal_wallpapers.curation import binding, floors
from fractal_wallpapers.models import location_view
from fractal_wallpapers.paths import under
from fractal_wallpapers.supply import apportion, ledgers, release_mix
from fractal_wallpapers.supply.location import key_of_row
from fractal_wallpapers.supply.partitions import partition_of_row

#: The schema every score row carries.
SCHEMA = 1

#: The picture a location is judged on, pre-colour. Re-exported rather than
#: restated: [`fractal_wallpapers.models.location_view`] owns the recipe, because
#: the walk scores through it too and a head asked about two distributions under
#: one name is a head whose scores cannot be compared.
VIEW_RESOLUTION = location_view.RESOLUTION
VIEW_SUPERSAMPLE = location_view.SUPERSAMPLE
VIEW_MODE = location_view.MODE
VIEW_CURVE = location_view.CURVE


class IntakeError(RuntimeError):
    """The supply cannot be read, or cannot be scored."""


def store_dir() -> Path:
    """Where curation keeps what it derives from the ledgers. Ignored, re-derivable."""
    return under("curation")


def scores_path() -> Path:
    """The sidecar: one row per location the head has an opinion about."""
    return store_dir() / "supply_scores.jsonl"


def view_dir() -> Path:
    """Where the pictures the head is scored on live.

    Not under curation's own store: the walk renders the same pictures, under the
    same recipe and the same digest, and two caches of one file is one render
    paid for twice.
    """
    from fractal_wallpapers.discovery import scoring as discovery_scoring

    return discovery_scoring.view_dir()


# --------------------------------------------------------------------------- #
# The union, at the gates.
# --------------------------------------------------------------------------- #
def gate_survivors(paths=None) -> tuple[list[dict], dict]:
    """`(rows, diagnostics)` — every bound location no gate refused.

    The pre-floor population, which is the denominator of every "N found, M above
    floor" line this module prints. A caller that only kept the passing rows
    could not recover it.

    `paths` is the binding. It is resolved rather than defaulted: `None` means
    "the only ledger there is", and a refusal when there is more than one.
    """
    return ledgers.admitted_union(binding.resolve(paths), admit=ledgers.passes_gates)


def canonical_map() -> str:
    """The colormap the location view is drawn through, read off the tile pool."""
    try:
        return location_view.canonical_map()
    except location_view.ViewError as refusal:
        raise IntakeError(str(refusal)) from refusal


def view_row(row: dict, colormap: str, cyclic: set[str]) -> dict:
    """One ledger row as the render-cache row its picture is made from."""
    return location_view.view_row(row, colormap, cyclic)


def view_name(row: dict, colormap: str, cyclic: set[str]) -> str:
    """The file name of one location's view: a digest of the whole recipe."""
    return location_view.view_name(row, colormap, cyclic)


# --------------------------------------------------------------------------- #
# The read: what the location head says about the supply.
# --------------------------------------------------------------------------- #
def score(paths=None, device: str = "auto", limit: int | None = None, log=print) -> dict:
    """Render every bound location's canonical view and score it.

    Idempotent and resumable in both halves: a view already on disk is not
    re-rendered, and the sidecar is **upserted per ledger** rather than rewritten
    whole. Scoring one binding replaces that binding's rows and leaves every other
    ledger's alone, so two ledgers scored in two invocations hold their union and
    a re-score of one is not a deletion of the other. Written whole, this stage
    made scoping a run a destructive act: narrowing to one harvest's ledger took
    the sidecar from 12,580 rows to 6,907 and said nothing.

    A `limit` pass is explicitly a prefix, so it upserts the locations it looked
    at and clears nothing — deleting the rows it declined to re-score would be a
    partial pass silently truncating a complete one.
    """
    from fractal_wallpapers.models import scoring, ship, train

    rows, diagnostics = gate_survivors(paths)
    if limit is not None:
        rows = rows[:limit]
    if not rows:
        raise IntakeError(
            "no walk ledger holds a single gate-surviving candidate, so there is no supply to "
            "score. Run `fractal-wallpapers harvest` first."
        )

    colormap = canonical_map()
    cyclic = _cyclic_maps()
    directory = view_dir()
    directory.mkdir(parents=True, exist_ok=True)

    made = 0
    pictures = []
    for index, row in enumerate(rows, start=1):
        output, fresh = location_view.render_view(row, colormap, cyclic, directory)
        made += int(fresh)
        if fresh and made % 25 == 0:
            log(f"{index}/{len(rows)} views rendered ({made} new)")
        pictures.append(output)

    model, config, where = scoring.load(ship.shipped_path("location"), device)
    log(f"scoring {len(pictures)} locations through the shipped location head on {where}")
    classes = int(config["classes"])
    probabilities = train.score(
        model, pictures, scoring.transform_of(config), where, classes, {"batch_size": 64}
    )

    stamp = floors.live_stamp("location")
    minted = []
    for row, picture, probability in zip(rows, pictures, probabilities, strict=True):
        record = {
            "schema": SCHEMA,
            "head": "location",
            "head_sha256": stamp,
            "key": _key_text(row),
            "ledger": row.get("_ledger"),
            "node_id": row.get("node_id"),
            "partition": partition_of_row(row),
            "family": row["family"],
            "viewport": row["viewport"],
            "maxiter": row.get("maxiter"),
            "view": picture.name,
        }
        for index in range(classes - 1):
            record[f"p_ge{index + 2}"] = float(probability[index])
        minted.append(record)

    # The ledgers this invocation is answerable for, named exactly as the union
    # stamps them onto a row — including one that contributed nothing, whose
    # stale rows are still this pass's to clear.
    scoped = frozenset(diagnostics["per_ledger"]) if limit is None else frozenset()
    path, upsert = _upsert_scores(minted, scoped)

    return {
        "schema": SCHEMA,
        "head": "location",
        "head_sha256": stamp,
        "gate_survivors": len(rows),
        "views_rendered": made,
        "views_reused": len(rows) - made,
        "view": location_view.summary(colormap),
        "union": diagnostics,
        "sidecar": upsert,
        "wrote": str(path),
    }


def _upsert_scores(minted: list[dict], scoped) -> tuple[Path, dict]:
    """Write `minted` into the sidecar, replacing `scoped`'s rows and keeping the rest.

    One row per *location*, because a score is a statement about a place rather
    than about a ledger row: two ledgers that found the same place hold one row
    between them, carrying whichever of them scored it last. Sorted by key on the
    way out, so re-scoring unchanged supply rewrites the same bytes.
    """
    path = scores_path()
    fresh = {row["key"] for row in minted}
    kept = {
        row["key"]: row
        for row in _stored_scores(path)
        if row.get("ledger") not in scoped and row["key"] not in fresh
    }
    merged = dict(kept)
    for row in minted:
        merged[row["key"]] = row
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for key in sorted(merged):
            handle.write(json.dumps(merged[key], ensure_ascii=False) + "\n")
    return path, {
        "scoped_ledgers": sorted(scoped),
        "rows_scored": len(minted),
        "rows_kept": len(kept),
        "rows_total": len(merged),
    }


def _stored_scores(path: Path) -> list[dict]:
    """The sidecar as it stands, or nothing at all. Schema-checked either way."""
    if not path.is_file():
        return []
    out = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("schema") != SCHEMA:
            raise IntakeError(f"{path}:{number}: schema {row.get('schema')!r}, expected {SCHEMA}")
        out.append(row)
    return out


def _cyclic_maps() -> set[str]:
    return location_view.cyclic_maps()


def _key_text(row: dict) -> str:
    """A location key as a sidecar can carry it: JSON, so the join is exact."""
    key = key_of_row(row)
    if key is None:
        raise IntakeError(
            "a gate-surviving row carries no location identity, so its score could never be "
            "joined back to it. Every row the union keeps is keyable or is reported unkeyed."
        )
    return json.dumps(key, ensure_ascii=False)


def read_scores(path: Path | None = None) -> dict:
    """`{location key: row}` from the sidecar, schema-checked."""
    path = scores_path() if path is None else Path(path)
    if not path.is_file():
        raise IntakeError(
            f"{path} is missing — nothing has read the supply yet. Run "
            f"`fractal-wallpapers curate score` before an intake."
        )
    return {row["key"]: row for row in _stored_scores(path)}


# --------------------------------------------------------------------------- #
# The ranked offer.
# --------------------------------------------------------------------------- #
def rank_key(row: dict):
    """Best first: `P(≥3)` descending, then the location key.

    The tie-break is not cosmetic. A run has to be reproducible, and scores tie
    often enough — an unscored row, two frames of one shape — that leaving the
    order to whatever the union walk happened to produce would let two runs over
    the same ledgers pick different locations.
    """
    score_ = row.get("score")
    return (-(score_ if score_ is not None else -1.0), row["key"])


def ranked(paths=None, scores: dict | None = None) -> tuple[dict, dict]:
    """`({partition: [row, ...]}, diagnostics)` — the offer, best first per partition.

    Each returned row is the ledger's own row plus the three things the rest of
    curation joins on: its `key`, its `partition`, and the `score` the head gave
    it. A row the sidecar has no opinion about keeps a `None` score, sorts last,
    and never passes the junk floor — which is the same answer an unscored row
    gets everywhere else in this project.

    The scores are read unscoped on purpose: the binding decides which *places*
    are on offer, and a score is a statement about a place. A location this
    binding offers that some other invocation already scored joins on its key and
    keeps its number, rather than arriving unscored and dying at the floor.
    """
    survivors, diagnostics = gate_survivors(paths)
    scores = read_scores() if scores is None else scores

    offer: dict[str, list[dict]] = {}
    found: dict[str, int] = {}
    scored_counts: dict[str, int] = {}
    passing: dict[str, int] = {}
    good: dict[str, int] = {}
    unscored = 0
    for row in survivors:
        key = key_of_row(row)
        if key is None:
            continue
        text = json.dumps(key, ensure_ascii=False)
        partition = partition_of_row(row)
        read = scores.get(text)
        value = None if read is None else float(read.get("p_ge3"))
        if read is None:
            unscored += 1
        else:
            scored_counts[partition] = scored_counts.get(partition, 0) + 1
        found[partition] = found.get(partition, 0) + 1
        if floors.passes_good_floor(value):
            good[partition] = good.get(partition, 0) + 1
        if not floors.passes_junk_floor(value):
            continue
        passing[partition] = passing.get(partition, 0) + 1
        offer.setdefault(partition, []).append(
            {**row, "key": text, "partition": partition, "score": value}
        )
    for partition in offer:
        offer[partition].sort(key=rank_key)

    diagnostics = dict(diagnostics)
    diagnostics.update(
        {
            "junk_floor": floors.JUNK_FLOOR,
            "good_floor": floors.GOOD_FLOOR,
            "found_by_partition": dict(sorted(found.items())),
            "scored_by_partition": dict(sorted(scored_counts.items())),
            "passing_by_partition": dict(sorted(passing.items())),
            "good_by_partition": dict(sorted(good.items())),
            # `found` is every gate survivor; `scored` is how many of those the
            # sidecar has an opinion about; `passing` and `good` are counted over
            # `scored` and NOT over `found`. Three names for three populations,
            # because a run that printed the first as the denominator of the third
            # reported a pass rate over rows nothing had looked at.
            "found": sum(found.values()),
            "scored": sum(scored_counts.values()),
            "passing": sum(passing.values()),
            "good": sum(good.values()),
            "unscored": unscored,
        }
    )
    return offer, diagnostics


def funnel_line(diagnostics: dict) -> str:
    """The whole supply in one line, with each number over the population it is of.

    Written this way because the first production run's version was not: *"22,751
    found, 1,245 above the junk floor"* put every gate survivor in the denominator
    and only the scored prefix in the numerator, and the resulting rate was a
    fifth of the real one. The scored count sits between the two, so the reader
    can see which denominator each number belongs to instead of assuming.
    """
    found = int(diagnostics.get("found", 0))
    scored = int(diagnostics.get("scored", 0))
    return (
        f"{found} found -> {scored} scored -> {diagnostics.get('passing', 0)} above the junk "
        f"floor ({floors.JUNK_FLOOR}), {diagnostics.get('good', 0)} above the good floor "
        f"({floors.GOOD_FLOOR}); {found - scored} found but unscored"
    )


def supply_lines(diagnostics: dict) -> list[str]:
    """One line per partition the union saw, including the ones that emit nothing.

    A partition that vanishes from a readout because its supply died is the exact
    failure this line exists to make visible, so it gets a line with a zero on it
    rather than no line.
    """
    found = diagnostics.get("found_by_partition", {})
    scored = diagnostics.get("scored_by_partition", {})
    passing = diagnostics.get("passing_by_partition", {})
    good = diagnostics.get("good_by_partition", {})
    out = []
    for partition in sorted(set(found) | set(scored) | set(passing) | set(good)):
        n_pass = passing.get(partition, 0)
        n_good = good.get(partition, 0)
        line = (
            f"{partition}: {found.get(partition, 0)} found, {scored.get(partition, 0)} scored, "
            f"{n_pass} of those above the junk floor, {n_good} above the good floor"
        )
        if not floors.emit_cap(n_pass):
            line += (
                " -> releases 1 (slot guarantee), then 0 (thin supply)"
                if n_good
                else " -> releases 0 (thin supply)"
            )
        out.append(line)
    return out


def emit_caps(offer: dict) -> dict:
    """`{partition: cap}` — the thin-supply cap over each partition's ranked offer."""
    return {partition: floors.emit_cap(len(rows)) for partition, rows in sorted(offer.items())}


def guaranteed(diagnostics: dict) -> list[str]:
    """The partitions a release owes a slot: every one with something worth keeping.

    The trigger is the good floor rather than the junk floor. Below about seven
    release slots the mix structurally zeroes the lowest-ratio partitions whatever
    their supply, so the garnish would never ship; the guarantee is one slot
    across the whole release and the remainder is the mix exactly as before.
    """
    return sorted(p for p, n in (diagnostics.get("good_by_partition") or {}).items() if n > 0)


def slots(partitions, n: int, guarantees=(), caps: dict | None = None) -> dict:
    """`{partition: slots}` — `n` release slots over the mix, with a guaranteed floor.

    Through `supply.apportion`, which owns the largest-deficit rule and the
    guarantee fixed point. The weights are the release mix restricted to the
    partitions this pass actually has candidates for: a partition with nothing to
    offer must not hold a slot hostage.
    """
    partitions = sorted(set(partitions))
    if not partitions or n <= 0:
        return dict.fromkeys(partitions, 0)
    weights = release_mix.shares(partitions)
    return apportion.allocate_slots(weights, int(n), caps=caps, guaranteed=guarantees)


__all__ = [
    "SCHEMA",
    "VIEW_CURVE",
    "VIEW_MODE",
    "VIEW_RESOLUTION",
    "VIEW_SUPERSAMPLE",
    "IntakeError",
    "canonical_map",
    "emit_caps",
    "funnel_line",
    "gate_survivors",
    "guaranteed",
    "rank_key",
    "ranked",
    "read_scores",
    "score",
    "scores_path",
    "slots",
    "store_dir",
    "supply_lines",
    "view_dir",
    "view_name",
    "view_row",
]
