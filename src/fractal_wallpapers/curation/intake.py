"""Which locations curation is offered, and in what order.

A release starts from the walk ledgers it is bound to. This module turns their
union into an ordered offer — best first, per partition — and it answers
exactly one question plus the supply arithmetic that question implies. It does
not decide how many pictures to make ([`budget`]), it does not choose a palette
([`colorize`]), and it does not select a release ([`selection`]).

## A row is re-scored at the regime it was scored at

The head reads three trained geometries and the scale is one across them, but the
*picture* is not: a location scored at 640×360 ss2 and the same location scored at
384×216 ss1 are two files. A walk now scores its own gate render, which is the
node regime, and says so on every row it writes — so this module reads a row at
the regime the row names, and never demands a deploy-geometry render for a row
that was never scored at one. A new run's rows cost the head and nothing else:
the picture is the one `expand` already wrote, reused where its recorded digest
still matches the recipe and re-drawn at 384×216 ss1 (about 0.09 s) where it does
not.

Old stock states no regime, so this module chooses one for it, and the choice is
the node regime like every walk node — never the deploy geometry. `location_views`
is a read-only record of what was scored there before a walk scored its own
frames, and nothing renders into it any more, including the first read of a row
that has never been scored at all. The regime a row was read at is stamped onto
the sidecar row as provenance, so an unstated regime becomes a stated one the
moment a score is written off it, and a re-score reads it back rather than
choosing again.

That is a ruling and not an equivalence: reading standing stock at 384×216 ss1
rather than 640×360 ss2 is defensible **because the head is regime-robust** — one
scale across all three built regimes, which is the property the adopted
checkpoint was selected for. It is what makes a node-regime read of old stock
comparable with everything else in the pool. A head without that property would
have to be re-read at one geometry or not compared.

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

* [`release_cap`] — a partition may release at most a quarter of its floor-passing
  supply, so a thin partition ships nothing rather than its own least-bad row;
* [`slots`] — the release mix apportioned into whole slots, with a guaranteed
  floor of one for any partition that has something worth keeping. Both go
  through `supply.apportion`, which already owns the largest-deficit rule and the
  guarantee fixed point; a second copy here would be a second answer.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from fractal_wallpapers.curation import binding, floors
from fractal_wallpapers.models import location_view, tiles
from fractal_wallpapers.paths import under
from fractal_wallpapers.supply import apportion, ledgers, location, release_mix
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


def view_dir(regime=None) -> Path:
    """Where the pictures the head is scored on live.

    Not under curation's own store: a picture is addressed by the digest of its
    own recipe and the walk makes the same ones, so two caches of one file is one
    render paid for twice.
    """
    from fractal_wallpapers.discovery import scoring as discovery_scoring

    return discovery_scoring.view_dir(regime)


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


def view_row(row: dict, colormap: str, cyclic: set[str], regime=None) -> dict:
    """One ledger row as the render-cache row its picture is made from."""
    return location_view.view_row(row, colormap, cyclic, regime)


def view_name(row: dict, colormap: str, cyclic: set[str], regime=None) -> str:
    """The file name of one location's view: a digest of the whole recipe."""
    return location_view.view_name(row, colormap, cyclic, regime)


# --------------------------------------------------------------------------- #
# Which picture a row is read off.
# --------------------------------------------------------------------------- #
#: How a row's picture was come by, as the tally counts them. `gate` is the walk's
#: own render, reused where the row's recorded digest still describes it; `cached`
#: is a view already in the regime's cache; `rendered` is one this pass drew.
GATE, CACHED, RENDERED = "gate", "cached", "rendered"

#: The regime a row that names none is read at. Not the deploy geometry: a row
#: with no `score_regime` has never been scored here, and scoring it like a walk
#: node is what keeps `artifacts/location_views` a read-only record instead of a
#: cache that grows by three gigabytes the first time old stock is offered. The
#: location head is regime-robust — one scale across all three built regimes — so
#: a node-regime read of standing stock is comparable with everything else in the
#: pool. Named here because [`_picture_for`] chooses it and every sidecar row
#: written off that choice carries it.
READ_REGIME = tiles.NODE_REGIME


def regime_of(row: dict):
    """The regime a ledger row's score **states**, or `None` where it states none.

    `None` is not a regime and is not the deploy one: it is the honest answer for
    every row written before a walk said so, and what to do about it is
    [`_picture_for`]'s decision, taken at [`READ_REGIME`].
    """
    stated = row.get("score_regime")
    if not stated:
        return None
    try:
        return tiles.regime_of(str(stated))
    except ValueError as bad:
        raise IntakeError(
            f"a ledger row states scoring regime {stated!r}, which is not a regime: {bad}"
        ) from bad


def gate_render(row: dict, colormap: str, cyclic: set[str], regime) -> Path | None:
    """The walk's own picture of this row, where it is still the recipe's picture.

    Four things have to hold, and any of them failing means re-rendering rather
    than refusing: the row names an image, the digest it recorded still matches
    what the recipe produces today, the file is where the run that wrote it left
    it, and a stamp beside it says **today's engine** drew it.

    The digest tells a gate render apart from a frame that sits at the same
    coordinates and was drawn some other way. What it cannot tell apart is two
    builds of the engine carrying out the same recipe: the build is not in the
    recipe, so it is not in the digest, and every gate render made before the
    stamp existed is a picture of the right place at the right size drawn by a
    program nobody wrote down. Those are re-rendered. See
    [`fractal_wallpapers.engine_fingerprint`].
    """
    from fractal_wallpapers import engine_fingerprint
    from fractal_wallpapers.discovery import walk as walk_module
    from fractal_wallpapers.paths import rehome

    name, recorded, ledger = row.get("image"), row.get("score_view"), row.get("_ledger")
    if not (name and recorded and ledger):
        return None
    if view_name(row, colormap, cyclic, regime) != recorded:
        return None
    where = rehome(ledger) or Path(ledger)
    picture = walk_module.views_dir(where.parent) / name
    if not picture.is_file():
        return None
    return picture if engine_fingerprint.stamps(picture.parent).is_current(name) else None


# --------------------------------------------------------------------------- #
# The read: what the location head says about the supply.
# --------------------------------------------------------------------------- #
def read_keys(path) -> set[str]:
    """The location keys a **key manifest** names, as the sidecar spells them.

    A JSONL record like every other in this project — one object a line, an
    integer `schema`, and a `key` holding the location key exactly as
    [`_key_text`] writes it. A manifest and not a repeated flag because a
    Windows command line overflows long before a list of locations does, and
    because the thing that produces one — `curate reach --write` — is a command
    whose whole output is a list of places.
    """
    path = Path(path)
    if not path.is_file():
        raise IntakeError(
            f"{path} is not there, so there is no set of locations to score. "
            f"`fractal-wallpapers curate reach --write {path}` writes one."
        )
    keys = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("schema") != SCHEMA:
            raise IntakeError(f"{path}:{number}: schema {row.get('schema')!r}, expected {SCHEMA}")
        keys.add(str(row["key"]))
    return keys


def key_manifest(rows) -> list[dict]:
    """`rows` as a key manifest [`read_keys`] can read back."""
    return [
        {"schema": SCHEMA, "key": str(row["key"]), "partition": str(row.get("partition") or "")}
        for row in rows
    ]


def score(
    paths=None,
    device: str = "auto",
    limit: int | None = None,
    keys=None,
    log=print,
) -> dict:
    """Read every bound location through the head, at the regime its row names.

    Idempotent and resumable in both halves: a picture already on disk is not
    re-made, and the sidecar is **upserted per ledger** rather than rewritten
    whole. Scoring one binding replaces that binding's rows and leaves every other
    ledger's alone, so two ledgers scored in two invocations hold their union and
    a re-score of one is not a deletion of the other. Written whole, this stage
    made scoping a run a destructive act: narrowing to one harvest's ledger took
    the sidecar from 12,580 rows to 6,907 and said nothing.

    **No deploy-geometry render is ever demanded, of any row.** A new run's rows
    are node-regime rows and their picture is the gate render the walk already
    wrote; only a row whose recipe has moved out from under its recorded digest
    costs an engine call. Standing stock states no regime at all and is read at
    384×216 ss1 like everything else, into `artifacts/node_views/<regime>/`.

    A `limit` pass is explicitly a prefix, so it upserts the locations it looked
    at and clears nothing — deleting the rows it declined to re-score would be a
    partial pass silently truncating a complete one. `keys` is the same rule from
    the other side: a **named set** of locations off a key manifest, upserted
    without clearing anything the binding also holds.

    `keys` exists because "score the ledgers those rows name" and "score those
    rows" are different amounts of work by two orders of magnitude. The three
    ledgers a gallery pass's unreached locations sit on can hold twenty thousand
    gate survivors between them — hours of engine time to score standing stock
    nothing has asked for — where the unreached locations themselves are a single
    batch. Closing a reach gap is the second thing, and scoring the ledgers whole
    is the first; they are separate legs on purpose.
    """
    from fractal_wallpapers.models import scoring, ship, train

    rows, diagnostics = gate_survivors(paths)
    if keys is not None:
        wanted = {str(key) for key in keys}
        rows = [row for row in rows if _key_text(row) in wanted]
    if limit is not None:
        rows = rows[:limit]
    if not rows:
        raise IntakeError(
            "no walk ledger holds a single gate-surviving candidate, so there is no supply to "
            "score. Run `fractal-wallpapers harvest` first."
        )

    colormap = canonical_map()
    cyclic = _cyclic_maps()

    tally: dict[str, int] = {}
    pictures: list[Path] = []
    regimes: list[str] = []
    for index, row in enumerate(rows, start=1):
        picture, how, spelled = _picture_for(row, colormap, cyclic)
        tally[how] = tally.get(how, 0) + 1
        pictures.append(picture)
        regimes.append(spelled)
        if how == RENDERED and tally[RENDERED] % 25 == 0:
            log(f"{index}/{len(rows)} read ({tally[RENDERED]} views rendered)")

    model, config, where = scoring.load(ship.shipped_path("location"), device)
    log(f"scoring {len(pictures)} locations through the shipped location head on {where}")
    classes = int(config["classes"])
    probabilities = train.score(
        model, pictures, scoring.transform_of(config), where, classes, {"batch_size": 64}
    )

    stamp = floors.live_stamp("location")
    minted = []
    for row, picture, spelled, probability in zip(
        rows, pictures, regimes, probabilities, strict=True
    ):
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
            # The picture, and the geometry it was drawn at. A reader that joined
            # on the name alone would be assuming every row is a deploy-geometry
            # one, which stopped being true the day a walk scored its own frames.
            "view": picture.name,
            "regime": spelled,
        }
        for index in range(classes - 1):
            record[f"p_ge{index + 2}"] = float(probability[index])
        minted.append(record)

    # The ledgers this invocation is answerable for, named exactly as the union
    # stamps them onto a row — including one that contributed nothing, whose
    # stale rows are still this pass's to clear.
    scoped = (
        frozenset(diagnostics["per_ledger"]) if (limit is None and keys is None) else frozenset()
    )
    path, upsert = _upsert_scores(minted, scoped)

    return {
        "schema": SCHEMA,
        "head": "location",
        "head_sha256": stamp,
        "gate_survivors": len(rows),
        # Three ways a picture was come by, not two: the walk's own gate render,
        # a view already cached at that regime, and one this pass drew.
        "pictures": {name: tally.get(name, 0) for name in (GATE, CACHED, RENDERED)},
        "views_rendered": tally.get(RENDERED, 0),
        "views_reused": len(rows) - tally.get(RENDERED, 0),
        "by_regime": dict(sorted(Counter(regimes).items())),
        # The recipe, per geometry this pass actually read at — `by_regime` counts
        # the rows and this says what one of them was drawn like. A single cell
        # naming the deploy geometry described a picture the pass had not made
        # since old stock stopped falling to it.
        "view": {
            spelled: location_view.summary(colormap, tiles.regime_of(spelled))
            for spelled in sorted(set(regimes))
        },
        "union": diagnostics,
        "sidecar": upsert,
        "wrote": str(path),
    }


def _picture_for(row: dict, colormap: str, cyclic: set[str]) -> tuple[Path, str, str]:
    """`(picture, how, regime)` — the picture this row's score is read off.

    A row that states a regime is read at the one it states, off the gate render
    the walk already made where that picture is still what the recipe describes.
    A row that states none has never been scored here, so this chooses for it,
    and the choice is [`READ_REGIME`] — the node regime, like every walk node,
    never the deploy geometry. The regime is returned so the sidecar row can
    carry it: an unstated regime becomes a stated one at the moment a score is
    written off it.
    """
    stated = regime_of(row)
    regime = READ_REGIME if stated is None else stated
    spelled = regime.spelled
    if stated is not None:
        picture = gate_render(row, colormap, cyclic, regime)
        if picture is not None:
            return picture, GATE, spelled
    directory = view_dir(regime)
    directory.mkdir(parents=True, exist_ok=True)
    picture, fresh = location_view.render_view(row, colormap, cyclic, directory, regime)
    return picture, (RENDERED if fresh else CACHED), spelled


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
    return location.key_text(key)


def stored_scores(path: Path | None = None) -> list[dict]:
    """The sidecar exactly as it stands, un-amended, in file order.

    What the head said on the night it said it, joined to the picture it was said
    about. [`curation.amend`] reads this to decide which of those pictures no
    longer exists; nothing that *seats* should, because a standing score read off
    a picture nobody has is the thing the amendment exists to stop being used.
    """
    return _stored_scores(scores_path() if path is None else Path(path))


def read_scores(path: Path | None = None, amended: bool = True) -> dict:
    """`{location key: row}` from the sidecar, amended, schema-checked.

    **The one door every seating score comes through.** A row whose standing
    score was read off a picture that is not today's — another geometry, a recipe
    whose digest has moved, an engine build nobody wrote down — is replaced by the
    re-read in [`curation.amend`], which carries what it was in an `amended`
    block. Overlaid here rather than at each read site, because there are five of
    them and a preference each of them had to remember is a preference one of them
    will not.

    `amended=False` is what the *measurement* of the shift is taken against, and
    is not a way to seat on the old numbers.
    """
    path = scores_path() if path is None else Path(path)
    if not path.is_file():
        raise IntakeError(
            f"{path} is missing — nothing has read the supply yet. Run "
            f"`fractal-wallpapers curate score` before an intake."
        )
    scores = {row["key"]: row for row in _stored_scores(path)}
    if not amended:
        return scores
    from fractal_wallpapers.curation import amend

    return amend.overlay(scores)


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
        text = location.key_text(key)
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
    """One line per partition the union saw, including the ones that release nothing.

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
        if not floors.release_cap(n_pass):
            line += (
                " -> releases 1 (slot guarantee), then 0 (thin supply)"
                if n_good
                else " -> releases 0 (thin supply)"
            )
        out.append(line)
    return out


def release_caps(offer: dict) -> dict:
    """`{partition: cap}` — the thin-supply cap over each partition's ranked offer."""
    return {partition: floors.release_cap(len(rows)) for partition, rows in sorted(offer.items())}


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
    "CACHED",
    "GATE",
    "RENDERED",
    "SCHEMA",
    "VIEW_CURVE",
    "VIEW_MODE",
    "VIEW_RESOLUTION",
    "VIEW_SUPERSAMPLE",
    "IntakeError",
    "canonical_map",
    "release_caps",
    "funnel_line",
    "gate_render",
    "gate_survivors",
    "guaranteed",
    "key_manifest",
    "rank_key",
    "read_keys",
    "ranked",
    "regime_of",
    "read_scores",
    "stored_scores",
    "score",
    "scores_path",
    "slots",
    "store_dir",
    "supply_lines",
    "view_dir",
    "view_name",
    "view_row",
]
