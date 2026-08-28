"""Every candidate this project has rendered, one row per recipe, kept.

A gallery pass makes candidates and then throws away everything about them
except a decision. The pictures stay on disk under `artifacts/`, and the rows in
the two decision stores say what was decided — but nothing anywhere answers the
question a solver has to ask first: **have we already made this picture?** 126
of the 15,488 candidate renders on record are the same recipe drawn twice by two
different passes, byte for byte, because nothing could tell either pass that the
other had already spent the seconds.

This is the store that answers it. One row per [`recipes.Recipe`], carrying the
location it stands on, the colour it turned out to be, where its picture is if
the picture is still there, and which pass paid for it.

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
makes an honest comparison possible at all: gallery1's rows and gallery4's rows
carry numbers read on different artifacts, and the same recipe drawn by both
appears here twice, once per artifact.

The backfill measured the other half of that. The 126 duplicate renders make 128
pairs of byte-identical pictures; 59 of the pairs disagree on `P(>=3)`, and the
largest disagreement is 2.8e-7. So the judge is reproducible to about the seventh
decimal on identical bytes and no further, which is why the sidecar records what
a run **read** rather than promising that a recipe has a score.

## A superseded framing is a re-key, not a rebuild

Framing refinement is moving into harvest, and a harvest refinement **moves the
location key** ([`supply.ledgers.refined_of`]) — deliberately, because a walk's
refined frame simply is the location it found. That will re-key a large fraction
of the pool.

So the row's identity is the **recipe** and never the location key. A recipe
already carries the frame it was drawn at, so one row per recipe is one row per
(location, recipe) with the location's identity as a field rather than as part of
the name. When harvest re-frames a place, the rows standing on the old key keep
their pictures and their colours, and what changes is a field: `location.key`
gains a `superseded_by` beside it. Nothing is rebuilt and nothing is deleted.

Both keys are on every row and **neither is reconciled here**. 2,903 of the
15,488 renders on record carry a `location.key` that disagrees with the viewport
they were drawn at, and every one is a refined-frame row: the gallery pass
pins a location's identity to the frame on record while rendering somewhere else
inside it, which is what stops one place taking two seats. `location.key` is that
recorded identity; `location.frame_key` is the identity of the frame the pixels
are of. A reader that wants "the same place" takes the first; a reader that wants
"the same picture" takes the recipe key.

## The `hunt` block says what the draw intended

A row made by a hunt, a mine or a depth run carries the intention beside the
outcome: which leg drew it, which mode and colormap, which band or cell it was
drawn *for*, and **`k` — which candidate at its location it was**. That last one
is here rather than only in the run's own `sequence.jsonl` because those live
under the regenerable tree and the ledger does not, and the corrections a reader
has to make are `k`-dependent: a prime rate read off the maximum of `k` noisy
judgements is a winner's-curse estimate, and the multiplier that turns it into a
calibrated one is a function of `k`.

The field is **additive**, and every row written before the stamp existed has no
`k` at all. [`k_of`] returns `None` for those rather than 1, because a reader
that took a missing `k` for a first draw would report that whole history as
unselected and under-correct every estimate over it.

## Where it lives

The rows are megabytes and the history guard acts at 1 MiB a file, so this gets
what [`curation.gallery_store`] and the supply sidecar get: the file under
`artifacts/`, a copy on the archive tier, and a **manifest** in the history
saying how many rows, how many bytes and which sha256 that copy is.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from fractal_wallpapers import engine_fingerprint
from fractal_wallpapers.curation import durability, gallery_store, recipes, records
from fractal_wallpapers.paths import archive_root, hot_root, tracked_name, under

#: The schema every ledger and sidecar row carries.
SCHEMA = 1

#: The subtree both files live in, under the regenerable tree.
UNIT = "candidate_ledger"

#: What the two files are called, wherever they are.
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

#: Which store a backfilled row came out of. A run records every scored candidate
#: in the tracked release store; a gallery pass records its attempts in
#: [`curation.gallery_store`] instead.
FROM_RELEASE = "release"
FROM_GALLERY = "gallery"


class LedgerError(RuntimeError):
    """The ledger cannot be built, or cannot be read."""


# --------------------------------------------------------------------------- #
# Where it all is.
# --------------------------------------------------------------------------- #
def store_root() -> Path:
    """The subtree the rows and the sidecar sit in, on whichever tier it is on."""
    return under("curation", UNIT)


def rows_path() -> Path:
    """The ledger: one row per recipe."""
    return store_root() / ROWS_NAME


def scores_path() -> Path:
    """The sidecar: one row per (recipe, judge artifact, regime)."""
    return store_root() / SCORES_NAME


def manifest_dir() -> Path:
    """The tracked directory both manifests live in."""
    return records.default_root() / UNIT


def _backup(name: str) -> Path:
    """The durable copy, beside the gate store's and the sidecar's.

    Off a root rather than through `under()`, for [`durability`]'s reason: a copy
    that resolved through the tiers would land on the tier the original is
    already on, which is the one place a second copy is no use.
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
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            runs[str(row["provenance"]["run"])] = runs.get(str(row["provenance"]["run"]), 0) + 1
            partition = str(row.get("partition"))
            partitions[partition] = partitions.get(partition, 0) + 1
            locations.add(str((row.get("location") or {}).get("key")))
    return {
        "runs": dict(sorted(runs.items())),
        "partitions": dict(sorted(partitions.items())),
        "locations": len(locations),
        "colour": {
            "rule": dominance.RULE,
            "share_floor": SHARE_FLOOR,
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
        copy=_backup(ROWS_NAME),
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
        copy=_backup(SCORES_NAME),
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


# --------------------------------------------------------------------------- #
# The rows.
# --------------------------------------------------------------------------- #
def row(
    *,
    recipe: recipes.Recipe,
    key: str,
    source: dict,
    also_rendered: list = (),
    also_recorded: list = (),
    colour: dict | None = None,
    picture: str | None = None,
    rejected: dict | None = None,
) -> dict:
    """One ledger row: a recipe, where it stands, what colour it is, who made it.

    `source` is the decision row this was read from — its own `location` block,
    its `key`, its run and candidate.

    The two lists beside it are different facts and are counted apart, because
    conflating them costs the ledger the number it exists to report.
    `also_rendered` is every *other render* that digests to this recipe: seconds
    a pass spent on a picture another pass already had, and the thing a cache
    prevents. `also_recorded` is every other decision **row** about the render
    this one names — a pass writes a gate row for the attempt and a release row
    for the seat, one picture, two decisions — and buys nothing but the join back
    to the seat.
    """
    location = source.get("location") or {}
    return {
        "schema": SCHEMA,
        "key": str(key),
        "partition": location.get("partition"),
        "location": {
            # The recorded identity: what the one-wallpaper-per-location cap
            # counts on, and what a refinement deliberately does NOT move.
            "key": location.get("key"),
            # The identity of the frame the pixels are of. Equal to the above on
            # every row the refine leg did not move.
            "frame_key": _frame_key(recipe),
            "agrees": location.get("key") == _frame_key(recipe),
            "family": recipe.family,
            "viewport": recipe.viewport,
            "maxiter": recipe.maxiter,
            "ledger": location.get("ledger"),
            "framing": _framing(source.get("framing")),
            # Reserved for harvest's re-framing: the location key that supersedes
            # this row's, written when a refinement moves the place this stands
            # on. A superseded row keeps its picture and its colour.
            "superseded_by": None,
        },
        "recipe": recipe.record(),
        "recipe_key": str(key),
        "palette_group": recipe.palette_group,
        "regime": recipe.regime.spelled,
        "at_candidate_regime": recipes.is_candidate_regime(recipe),
        "colour": colour,
        "provenance": {
            "run": source.get("run"),
            "candidate": source.get("candidate"),
            "store": source.get("_store"),
            "source_key": source.get("key"),
            "engine": UNKNOWN_ENGINE,
            "also_rendered": list(also_rendered),
            "also_recorded": list(also_recorded),
        },
        "picture": picture,
        "rejected": rejected,
    }


def live_artifact() -> str:
    """The sha256 of the judge shipped right now. What a score has to be read on."""
    from fractal_wallpapers.curation import floors

    return floors.live_stamp(floors.SCORING_HEAD)


def scores_by_recipe(scores=None, artifact: str | None = None, regime: str | None = None) -> dict:
    """`{recipe key: score row}` for **one** judge artifact, refusing a mixed read.

    The sidecar is keyed `(recipe key, artifact, regime)` precisely because a
    number is comparable only inside that triple. A join that flattened it to the
    recipe key alone would be last-row-wins across artifacts: two judges' scales
    in one ordering, with nothing anywhere saying so. Today the store holds one
    artifact and one regime, so such a join is right by luck; the first adoption
    is what turns luck into a silent wrong answer, and an adoption is a thing
    this project plans to do.

    So the artifact is named — `None` means the live head — and a row read on any
    other is **left out**, counted, and reported by [`stale_scores`]. Omitted and
    not silently rescaled: a recipe with no reading on the live judge has no
    score, which is a different and honest thing from having an old one.
    """
    read = read_scores() if scores is None else list(scores)
    want = live_artifact() if artifact is None else str(artifact)
    return {
        str(row["recipe_key"]): row
        for row in read
        if str(row.get("judge_artifact")) == want
        and (regime is None or str(row.get("regime")) == str(regime))
    }


def stale_scores(scores=None, artifact: str | None = None) -> dict:
    """What a join on the live judge leaves behind: `{artifact: rows}`.

    A census and not a warning. A store holding two artifacts is the ordinary
    state after an adoption — the old readings are kept, because a picture read
    by two judges is two facts — and this is how a caller says how much of its
    population it is about to have no score for.
    """
    read = read_scores() if scores is None else list(scores)
    want = live_artifact() if artifact is None else str(artifact)
    out: dict = {}
    for row in read:
        held = str(row.get("judge_artifact"))
        if held != want:
            out[held] = out.get(held, 0) + 1
    return dict(sorted(out.items(), key=lambda item: -item[1]))


def colours_by_render(rows=None) -> dict:
    """`{tracked render path: colour block}` over the rows that have both.

    The join a [`ceiling.Lens`] needs to stop decoding a picture the store has
    already read. The **render path** is the key rather than the recipe key
    because that is what a lens is holding when it asks: it resolves a candidate
    to a render and nothing downstream of that knows a recipe key. One geometry
    for every row is what makes the readings comparable at all, and the ledger's
    `picture` is that geometry by construction — the candidate render.

    A row with no picture or no colour is left out, so a lens over it decodes and
    the seating is unchanged.
    """
    stored = read() if rows is None else rows
    return {
        str(row["picture"]): row["colour"]
        for row in stored
        if row.get("picture") and row.get("colour")
    }


def reading_source(rows=None):
    """A `stored_of` for [`ceiling.Lens`]: a render path in, a colour block out.

    Built over [`colours_by_render`] and closed over it, so the ledger is read
    once for a whole seating however many candidates it tests. Answers `None`
    for a render the ledger has never seen, which is the signal for the lens to
    decode.
    """
    table = colours_by_render(rows)
    return lambda picture: table.get(tracked_name(picture))


def k_of(row: dict) -> int | None:
    """Which candidate at its location this row was, or `None` where it cannot say.

    The `k` a planner stamps in the row's `hunt` block. It is **additive**: the
    85,129 rows written before the stamp existed carry no `k` at all, and a
    reader that treated a missing one as 1 would report the whole of that history
    as unselected first draws and under-correct every winner's-curse estimate
    over it. `None` is the honest answer and a caller has to decide what to do
    with it.
    """
    held = (row.get("hunt") or {}).get("k")
    try:
        return None if held is None else int(held)
    except (TypeError, ValueError):
        return None


def _frame_key(recipe: recipes.Recipe) -> str | None:
    """The location identity of the frame a recipe was drawn at, spelled as stored.

    Through [`supply.location.location_key`], which is this project's one answer
    to "the same location", and serialized the way the decision rows already
    serialize it so the two are comparable as strings.
    """
    from fractal_wallpapers.supply import location as location_module

    try:
        return json.dumps(list(location_module.location_key(recipe.family, recipe.viewport)))
    except (KeyError, TypeError, ValueError):
        return None


def _framing(block: dict | None) -> dict | None:
    """The refine leg's verdict, thinned to what a re-key later needs.

    Both frames and which one was used. The scores that decided it stay on the
    decision row: this store is about pictures, and a framing's `P(>=4)` is about
    a location.
    """
    if not block:
        return None
    return {
        "adopted": bool(block.get("adopted")),
        "used": block.get("used"),
        "original_viewport": (block.get("original") or {}).get("viewport"),
        "refined_viewport": (block.get("refined") or {}).get("viewport"),
    }


def score_row(*, key: str, artifact: str, regime: str, head: str, read: dict, source: dict) -> dict:
    """One reading of one recipe by one judge artifact at one regime.

    Keyed on the three of them together, because that triple is what a number is
    only comparable within. `block` says whether this is what the run read on the
    night it ran or a later re-score's reading of the same picture — the same
    distinction [`records.live_reading`] draws, kept rather than collapsed.
    """
    return {
        "schema": SCHEMA,
        "key": f"{key}|{artifact}|{regime}",
        "recipe_key": str(key),
        "judge_artifact": str(artifact),
        "regime": str(regime),
        "head": str(head),
        "p_ge2": read.get("p_ge2"),
        "p_ge3": read.get("p_ge3"),
        "p_ge4": read.get("p_ge4"),
        "rank_score": read.get("rank_score"),
        "block": "scores_current" if source.get("scores_current") else "scores",
        "read_by": {"run": source.get("run"), "candidate": source.get("candidate")},
    }


# --------------------------------------------------------------------------- #
# Reading and writing.
# --------------------------------------------------------------------------- #
def read(path: Path | None = None) -> list[dict]:
    """Every ledger row on record, in key order."""
    return _rows_of(rows_path() if path is None else Path(path))


def read_scores(path: Path | None = None) -> list[dict]:
    """Every sidecar row on record, in key order."""
    return _rows_of(scores_path() if path is None else Path(path))


def _rows_of(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def write(rows) -> tuple[Path, int, int]:
    """Merge `rows` into the ledger by key. `(path, total, new)`.

    [`records.upsert_file`], which is what every other flat store here is written
    with: same key, same ordering, and a re-backfill over an unchanged pool
    writes byte-identical output.
    """
    path = rows_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    total, new = records.upsert_file(path, rows)
    return path, total, new


def write_scores(rows) -> tuple[Path, int, int]:
    path = scores_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    total, new = records.upsert_file(path, rows)
    return path, total, new


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


# --------------------------------------------------------------------------- #
# The backfill.
# --------------------------------------------------------------------------- #
def sources() -> list[dict]:
    """Every candidate on record in either store, each stamped with which one.

    The same two stores [`gallery.pool_rows`] reads, and read here **without its
    three exclusions**. A row this pass wrote, a row a person rejected and a row
    with no score are all candidates that were rendered, and the ledger's whole
    claim is that it holds every picture that exists.
    """
    out = []
    for stamped, rows in (
        (FROM_RELEASE, records.read_decisions(records.RELEASE)),
        (FROM_GALLERY, gallery_store.read()),
    ):
        for candidate in rows:
            out.append({**candidate, "_store": stamped})
    return out


def _picture_of(source: dict) -> Path:
    """Where one row's own candidate render is, whether or not it is still there."""
    from fractal_wallpapers.curation import rescore
    from fractal_wallpapers.curation import run as run_module

    return run_module.run_dir(str(source["run"])) / rescore.PICTURES / f"{source['candidate']}.jpg"


#: Which stage of a decision row is preferred as a render's own record where the
#: same render carries two. The attempt is what made the picture; the seat is a
#: verdict on it taken later, and the two carry the same recipe either way.
MADE_IT = "gate"


def renders_of(everything: list) -> tuple[dict, dict]:
    """`({picture id: [its rows]}, counts)` — the two stores collapsed onto renders.

    **Two collapses and not one**, because a render arrives on more rows than it
    was made times, in two different ways, and only one of them is a fact about
    the pool.

    A **re-stamp** is a row about a picture some *other* row made: a pass seats a
    standing candidate under its own id and names the row it decided over in
    `source`, so [`rescore.origin_of`] walks down to the render. 90 of the two
    stores' 16,029 rows are those, and they are dropped here — the pass that
    seated a picture is not the pass that paid for it.

    A **restatement** is one run's own render carrying two decision rows: a
    gallery pass writes a gate row for the attempt and a release row for the
    seat, same run, same candidate, one JPEG. 451 rows are those, and they are
    kept beside their render rather than dropped, because a solver joining a
    recipe back to the seat it took needs them.

    Collapsing only the first would have reported those 451 as duplicate renders
    — 577 where the real number is 126, which is the one number this whole store
    exists to make smaller.
    """
    from fractal_wallpapers.curation import rescore

    index = {str(candidate["key"]): candidate for candidate in everything}
    by_render: dict = {}
    counts = {"restamps": 0, "restated": 0}
    for source in everything:
        run, candidate = rescore.origin_of(source, index)
        if (str(source["run"]), str(source["candidate"])) != (run, candidate):
            counts["restamps"] += 1
            continue
        identity = f"{run}_{candidate}"
        if identity in by_render:
            counts["restated"] += 1
        by_render.setdefault(identity, []).append(source)
    for rows in by_render.values():
        rows.sort(key=lambda source: (str(source.get("stage")) != MADE_IT, str(source["key"])))
    return by_render, counts


def canonical_artifacts(candidates: list) -> dict:
    """`{spelling: the longest spelling of that artifact}` over the whole pool.

    A run record abbreviates a head stamp to sixteen hex characters and a floor
    carries all sixty-four, so one shipped artifact reaches this store under two
    names — and a sidecar keyed on the name as written would hold two rows for one
    judge and let a reader believe they were two readings. The prefix rule is
    [`rescore._same_artifact`]'s, applied once here rather than at every read.
    """
    from fractal_wallpapers.curation import rescore

    seen = {str(rescore.artifact_of(candidate) or "") for candidate in candidates}
    seen.discard("")
    longest = sorted(seen, key=len, reverse=True)
    return {name: next(full for full in longest if full.startswith(name)) for name in seen}


def backfill(recolour: bool = False, log=print) -> dict:
    """Build the ledger and the sidecar from every candidate that already exists.

    No renders: everything here is read off the two decision stores and off the
    pictures those stores point at. The colour read is the expensive half — about
    20 ms a picture — so a recipe whose colour is already on record keeps it
    unless `recolour` is set. A second backfill over an unchanged pool is
    seconds, and writes byte-identical output.
    """
    from fractal_wallpapers.palettes import groups as groups_module

    everything = sources()
    table = groups_module.member_groups()
    artifacts = canonical_artifacts(everything)
    by_render, counts = renders_of(everything)
    counts.update(
        {
            "rows_read": len(everything),
            "unreadable": 0,
            "renders": 0,
            "recipes": 0,
            "duplicate_renders": 0,
            "off_regime": 0,
            "rejected": 0,
            "recoloured": 0,
            "colour_carried": 0,
            "colour_missing": 0,
        }
    )
    held: dict = {}
    for identity in sorted(by_render):
        drawn = by_render[identity]
        try:
            recipe = recipes.of_decision(drawn[0], table)
        except recipes.RecipeError as refusal:
            counts["unreadable"] += 1
            log(f"[ledger] {drawn[0]['key']}: {refusal}")
            continue
        counts["renders"] += 1
        key = recipes.key_of(recipe)
        held.setdefault(key, (recipe, []))[1].append(drawn)

    known = {str(stored["key"]): stored for stored in read()}
    rows, scores = [], []
    for at, (key, (recipe, made)) in enumerate(sorted(held.items()), start=1):
        made.sort(key=lambda rows_: (str(rows_[0]["run"]), str(rows_[0]["candidate"])))
        every_row = [source for rows_ in made for source in rows_]
        primary = made[0][0]
        counts["duplicate_renders"] += len(made) - 1
        if not recipes.is_candidate_regime(recipe):
            counts["off_regime"] += 1
        rejected = next(
            (source.get("rejected") for source in every_row if source.get("rejected")), None
        )
        counts["rejected"] += bool(rejected)

        picture = next((p for p in (_picture_of(rows_[0]) for rows_ in made) if p.is_file()), None)
        colour, how = _colour_for(key, picture, known, recolour)
        counts[how] += 1
        rows.append(
            row(
                recipe=recipe,
                key=key,
                source=primary,
                also_rendered=[_named(rows_[0]) for rows_ in made[1:]],
                also_recorded=[
                    _named(source) for source in every_row if source["key"] != primary["key"]
                ],
                colour=colour,
                picture=None if picture is None else tracked_name(picture),
                rejected=rejected,
            )
        )
        scores.extend(_scores_for(key, recipe, every_row, artifacts))
        if at % 500 == 0:
            log(f"[ledger] {at}/{len(held)} recipes")

    counts["recipes"] = len(rows)
    counts["score_readings"] = len(scores)
    counts["locations"] = len({str((stored["location"] or {})["key"]) for stored in rows})
    counts["with_picture"] = sum(1 for stored in rows if stored["picture"])
    counts["recipe_only"] = counts["recipes"] - counts["with_picture"]
    rows_file, total, new = write(rows)
    scores_file, score_total, score_new = write_scores(scores)
    return {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rows_path": tracked_name(rows_file),
        "scores_path": tracked_name(scores_file),
        "stored": {"rows": total, "new": new, "scores": score_total, "scores_new": score_new},
        **counts,
    }


def _named(source: dict) -> dict:
    """One decision row as another row's record points at it. Enough to join back."""
    return {
        "run": source.get("run"),
        "candidate": source.get("candidate"),
        "stage": source.get("stage"),
        "store": source.get("_store"),
        "source_key": source.get("key"),
    }


def _colour_for(key: str, picture: Path | None, known: dict, recolour: bool) -> tuple:
    """`(colour block, which counter to bump)` for one recipe.

    The read is [`palettes.dominance`], which is the project's one answer to what
    colour a picture is. **The rule and the codebook it was read under are on the
    manifest and not on the row**, which is where [`curation.colors`] puts them
    for the same reason: they are one sentence and one triple, identical on every
    row, and fifteen thousand copies of them is five megabytes of one constant.

    A cell holding less than [`codebook.SMALL_SHARE`]-scale noise is dropped at
    the same threshold `codebook.census` stores at. Thirty-seven of the
    forty-eight cells are below it on the median picture, and a cell at 1e-5 of a
    picture's colour cannot satisfy or violate any constraint that acts on it.
    """
    from fractal_wallpapers.palettes import dominance

    stored = known.get(key) or {}
    if not recolour and stored.get("colour"):
        return stored["colour"], "colour_carried"
    if picture is None:
        return None, "colour_missing"
    return colour_block(dominance.of_picture(picture)), "recoloured"


def colour_block(reading) -> dict:
    """One [`palettes.dominance.Reading`] as a ledger row stores it.

    Its own function because two writers make ledger rows — this backfill, off
    pictures that already exist, and [`curation.hunt`], off a picture it has just
    rendered — and a colour block written two ways is two stores wearing one
    name. What is stored is the rounding and the share floor, and both belong to
    the *store* rather than to either writer.
    """
    return {
        "cells": list(reading.cells),
        "families": list(reading.families),
        "cell_shares": _kept(reading.cell_shares),
        "family_shares": _kept(reading.family_shares),
        "neutral": round(reading.neutral, 6),
    }


#: The share below which a cell is not stored. The same number
#: [`codebook.census`] stores at, and it is a literal there too — one place a
#: constant is written twice, because the alternative is a store that keeps
#: fourteen megabytes of numbers no constraint can read.
SHARE_FLOOR = 1e-4


def _kept(shares: dict) -> dict:
    """One share vector as it is stored: rounded, and the noise dropped."""
    return {
        name: round(float(value), 6)
        for name, value in shares.items()
        if float(value) >= SHARE_FLOOR
    }


def _scores_for(key: str, recipe: recipes.Recipe, drawn: list, artifacts: dict) -> list[dict]:
    """Every reading of this recipe that any of its renders carries.

    One row per (artifact, regime) and not one per render: two renders of one
    recipe read by one artifact are one reading, and the first of them is kept.
    A row whose artifact nothing can name is skipped rather than filed under a
    guess — [`rescore.artifact_of`] returns `None` for exactly that, and it is
    not the same fact as *stale*.
    """
    from fractal_wallpapers.curation import rescore

    out: dict = {}
    for source in drawn:
        artifact = artifacts.get(str(rescore.artifact_of(source) or ""))
        read = records.live_reading(source)
        if not artifact or read.get("p_ge3") is None:
            continue
        stamped = score_row(
            key=key,
            artifact=artifact,
            regime=recipe.regime.spelled,
            head=records.kind_of(source),
            read=read,
            source=source,
        )
        out.setdefault(stamped["key"], stamped)
    return list(out.values())


# --------------------------------------------------------------------------- #
# The census: what we already own, over the axes constraints act on.
# --------------------------------------------------------------------------- #
#: The trivial first solve the feasibility read is taken against: twenty
#: wallpapers, one per location, the hard diversity radius, the colour ceiling and
#: the group cap as budgets, the mode floors soft. Not a default anything solves
#: at — a number to answer "would any of this bind" against.
FIRST_SOLVE = 20


def census(rows=None, n: int = FIRST_SOLVE, log=print) -> dict:
    """What the ledger holds, over the axes a constraint acts on. Decides nothing.

    Location x colour cell x mode x palette group, with the partition riding on
    the location because that is where it is already recorded. Every axis reports
    its fill **and its empties**: a solver's question is never how much material
    there is, it is which of its constraints has nothing to satisfy it with.
    """
    from fractal_wallpapers.palettes import dominance

    stored = read() if rows is None else list(rows)
    if not stored:
        raise LedgerError(
            "the ledger is empty, so there is nothing to take a census over. Run "
            "`fractal-wallpapers curate candidate-ledger backfill` first."
        )
    log(f"[census] {len(stored):,} rows")
    return {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "population": _population(stored),
        "locations": _locations(stored),
        "cells": _fill(stored, dominance.cells(), _cells_of),
        "families": _fill(stored, dominance.families(), _families_of),
        "modes": _fill(stored, _production_modes(), lambda row: [(row["recipe"] or {})["mode"]]),
        "groups": _fill(stored, _drawable_groups(), lambda row: [row["palette_group"]]),
        "feasibility": feasibility(stored, n=n, log=log),
    }


def _population(stored: list) -> dict:
    runs: dict = {}
    partitions: dict = {}
    for stamped in stored:
        run = str((stamped.get("provenance") or {}).get("run"))
        runs[run] = runs.get(run, 0) + 1
        partition = str(stamped.get("partition"))
        partitions[partition] = partitions.get(partition, 0) + 1
    return {
        "recipes": len(stored),
        "with_picture": sum(1 for stamped in stored if stamped.get("picture")),
        "recipe_only": sum(1 for stamped in stored if not stamped.get("picture")),
        "off_regime": sum(1 for stamped in stored if not stamped.get("at_candidate_regime")),
        "rejected": sum(1 for stamped in stored if stamped.get("rejected")),
        "no_colour": sum(1 for stamped in stored if not stamped.get("colour")),
        "duplicate_renders": sum(
            len((stamped.get("provenance") or {}).get("also_rendered") or []) for stamped in stored
        ),
        "by_run": dict(sorted(runs.items())),
        "by_partition": dict(sorted(partitions.items())),
    }


def _locations(stored: list) -> dict:
    """How many places the ledger stands on, and how deep it stands on each."""
    per: dict = {}
    per_partition: dict = {}
    for stamped in stored:
        key = str((stamped.get("location") or {}).get("key"))
        per[key] = per.get(key, 0) + 1
        per_partition.setdefault(str(stamped.get("partition")), set()).add(key)
    depths = sorted(per.values())
    moved = sum(1 for stamped in stored if not (stamped.get("location") or {}).get("agrees"))
    return {
        "locations": len(per),
        "recipes_per_location": _spread(depths),
        "at_one_recipe": sum(1 for depth in depths if depth == 1),
        "locations_by_partition": {name: len(keys) for name, keys in sorted(per_partition.items())},
        "rows_whose_key_is_not_their_frame": moved,
    }


def _spread(values: list) -> dict:
    """Min, the quartiles, p90 and max of an already-sorted list of counts."""
    if not values:
        return {}

    def at(share: float):
        return values[min(len(values) - 1, int(share * len(values)))]

    return {
        "min": values[0],
        "p25": at(0.25),
        "median": at(0.5),
        "p75": at(0.75),
        "p90": at(0.90),
        "max": values[-1],
        "mean": round(sum(values) / len(values), 2),
    }


def _cells_of(stored: dict) -> list:
    return list((stored.get("colour") or {}).get("cells") or [])


def _families_of(stored: dict) -> list:
    return list((stored.get("colour") or {}).get("families") or [])


def _fill(stored: list, axis, values_of) -> dict:
    """One axis: how many recipes and how many locations reach each of its values.

    Both counts, because they answer different questions. A cell fifty recipes
    carry at one location is a cell the one-wallpaper-per-location rule can only
    seat once, however many recipes stand behind it.
    """
    recipes_at = {name: 0 for name in axis}
    locations_at: dict = {name: set() for name in axis}
    unlisted: dict = {}
    none = 0
    for stamped in stored:
        values = values_of(stamped)
        if not values:
            none += 1
        for value in values:
            if value in recipes_at:
                recipes_at[value] += 1
                locations_at[value].add(str((stamped.get("location") or {}).get("key")))
            else:
                unlisted[value] = unlisted.get(value, 0) + 1
    ranked = sorted(recipes_at.items(), key=lambda item: (-item[1], item[0]))
    return {
        "axis": len(axis),
        "held": sum(1 for name in axis if recipes_at[name]),
        "empty": [name for name in axis if not recipes_at[name]],
        "recipes_carrying_none": none,
        "recipes": dict(ranked),
        "locations": {name: len(locations_at[name]) for name, _count in ranked},
        "not_on_the_axis": dict(sorted(unlisted.items())),
    }


def _production_modes() -> tuple:
    """The eighteen modes a candidate can be drawn in, off the engine's own tiers."""
    from fractal_wallpapers import engine

    return tuple(engine.production_modes())


def _drawable_groups() -> tuple:
    """Every palette group the colorizer's pool can reach, through the group table.

    The pool is already one map per group — a pass records that as
    `palette_pool.collapsed` — so this is the pool's own size. Derived rather than
    assumed, because a group table that stopped collapsing would make the two
    differ and the census would go on reporting the wrong denominator.
    """
    from fractal_wallpapers.curation import colorize
    from fractal_wallpapers.palettes import groups as groups_module

    table = groups_module.member_groups()
    return tuple(sorted({groups_module.group_of(name, table) for name in colorize.pool(0)}))


def feasibility(stored: list, n: int = FIRST_SOLVE, log=print) -> dict:
    """Which of a trivial first solve's constraints could bind, on what we hold.

    Each entry says what the constraint needs, what the ledger offers, and whether
    the second is short of the first. Nothing here is a solve, and every entry
    says which kind of read it is: a constraint that cannot bind on the marginals
    can still bind jointly.
    """
    from fractal_wallpapers.curation import ceiling as ceiling_module
    from fractal_wallpapers.palettes import dominance

    locations = {str((row.get("location") or {}).get("key")) for row in stored}
    groups = {str(row.get("palette_group")) for row in stored}
    cell_allowance = int(ceiling_module.K * ceiling_module.CELL_SHARE * n) + 1
    family_allowance = int(ceiling_module.K * ceiling_module.FAMILY_SHARE * n) + 1
    cells_held = {name for row in stored for name in _cells_of(row)}
    families_held = {name for row in stored for name in _families_of(row)}
    colourless = sum(1 for row in stored if not _cells_of(row))
    return {
        "n": n,
        "one_wallpaper_per_location": {
            "needs": n,
            "holds": len(locations),
            "binds": len(locations) < n,
            "read": "marginal",
        },
        "diversity_radius": _radius_read(locations, n, log=log),
        "group_cap": {
            "cap": ceiling_module.GROUP_CAP,
            "needs": n,
            "holds": len(groups),
            "of_drawable": len(_drawable_groups()),
            "binds": len(groups) < n,
            "read": "marginal, and the loosest form of the cap: a second seat in a group "
            "is allowed when its pixel cloud is more than tau_group from every picture "
            "that group already seated",
        },
        "colour_ceiling": {
            "k": ceiling_module.K,
            "cell_allowance": cell_allowance,
            "family_allowance": family_allowance,
            "cells_held": len(cells_held),
            "cells_needed": -(-n // max(1, cell_allowance)),
            "families_held": len(families_held),
            "families_needed": -(-n // max(1, family_allowance)),
            "recipes_with_no_dominant_cell": colourless,
            "binds_on_cells": len(cells_held) < -(-n // max(1, cell_allowance)),
            "binds_on_families": len(families_held) < -(-n // max(1, family_allowance)),
            "note": "only a candidate DOMINANT in an over-allowance colour is refused, so "
            f"the {colourless:,} recipes dominant in no cell cannot be refused by it at all",
            "rule": dominance.RULE,
            "read": "marginal — the allowance is per seat and the walk is path-dependent",
        },
        "mode_floors": {
            "acts": "soft",
            "modes": len(_production_modes()),
            "modes_held": sum(1 for name in _production_modes() if _mode_count(stored, name)),
            "binds": False,
        },
    }


def _mode_count(stored: list, mode: str) -> int:
    return sum(1 for row in stored if (row.get("recipe") or {}).get("mode") == mode)


def _radius_read(locations: set, n: int, log=print) -> dict:
    """Whether `n` of the ledger's locations can be drawn under the hard radius.

    The real draw and not an estimate: [`gallery.choose`] over the embedding
    store, at [`gallery.RADIUS`], with quality flat so the answer is about the
    radius alone. A location the embedding store does not hold is one no pass
    could ever have chosen, and it is counted rather than dropped quietly.
    """
    import numpy

    from fractal_wallpapers.curation import embeddings
    from fractal_wallpapers.curation import gallery as gallery_module

    rows, matrix = embeddings.load()
    if not rows:
        return {"radius": gallery_module.RADIUS, "embedded": 0, "read": "no embedding store"}
    at = {str(row["key"]): index for index, row in enumerate(rows)}
    indices = [at[key] for key in sorted(locations) if key in at]
    log(f"[census] {len(indices):,}/{len(locations):,} ledger locations are embedded")
    picks, tally = gallery_module.choose(
        indices,
        matrix,
        numpy.ones(len(matrix), dtype=numpy.float32),
        n,
        gallery_module.RADIUS,
        0.0,
    )
    return {
        "radius": gallery_module.RADIUS,
        "embedded": len(indices),
        "unembedded": len(locations) - len(indices),
        "needs": n,
        "drawn": len(picks),
        "binds": len(picks) < n,
        "refused_by_radius": tally.get("refused_by_radius"),
        "read": "the draw itself, quality flat",
    }


__all__ = [
    "FIRST_SOLVE",
    "FROM_GALLERY",
    "FROM_RELEASE",
    "LedgerError",
    "MADE_IT",
    "ROWS_NAME",
    "SCHEMA",
    "SCORES_NAME",
    "UNIT",
    "UNKNOWN_ENGINE",
    "backfill",
    "canonical_artifacts",
    "census",
    "check",
    "colour_block",
    "colours_by_render",
    "durable_rows",
    "durable_scores",
    "feasibility",
    "k_of",
    "live_artifact",
    "manifest_dir",
    "read",
    "read_scores",
    "reading_source",
    "renders_of",
    "restore",
    "row",
    "rows_path",
    "save",
    "score_row",
    "scores_by_recipe",
    "scores_path",
    "sources",
    "stale_scores",
    "store_root",
    "write",
    "write_scores",
]
