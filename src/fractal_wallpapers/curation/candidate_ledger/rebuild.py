"""Building the ledger out of the stores that predate it.

The tracked release store, read once into one row per recipe, with the colour and
the texture flag resolved on the way through. It ends at [`merge.merge`] like every
other writer.

⚠ **This backfill is no longer complete, and that is a decision rather than a
gap.** It read a second store until 2026-09-06: the four retired gallery passes'
attempt rows, stamped [`store.FROM_GALLERY`], which were about a third of what a
backfill could reach. That store was retired with the passes, so a rebuild from
scratch would now produce a ledger short those rows. It is not a recovery path
anybody should need — the ledger is durable, mirrored and checked, and
`FROM_GALLERY` rows already in it are untouched and still read — but a rebuild is
no longer a way to get them back. The passes' seated **winners** are release rows
and still arrive here.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fractal_wallpapers.curation import recipes, records
from fractal_wallpapers.curation.candidate_ledger import door as door_module
from fractal_wallpapers.curation.candidate_ledger import rows as rows_module
from fractal_wallpapers.curation.candidate_ledger import store
from fractal_wallpapers.curation.candidate_ledger.store import (
    FROM_RELEASE,
    MADE_IT,
    SCHEMA,
)
from fractal_wallpapers.paths import tracked_name


# --------------------------------------------------------------------------- #
# The backfill.
# --------------------------------------------------------------------------- #
def sources() -> list[dict]:
    """Every candidate on record in the release store, stamped with which store.

    The same store [`rescore.pool_rows`] reads, and read here **without its three
    exclusions**. A row this pass wrote, a row a person rejected and a row with no
    score are all candidates that were rendered, and the ledger's whole claim is
    that it holds every picture that exists.

    The stamp is kept though there is one store to stamp: rows already in the
    ledger carry [`store.FROM_GALLERY`] and readers split on it.
    """
    return [
        {**candidate, "_store": FROM_RELEASE}
        for candidate in records.read_decisions(records.RELEASE)
    ]


def _picture_of(source: dict) -> Path:
    """Where one row's own candidate render is, whether or not it is still there."""
    from fractal_wallpapers.curation import rescore, run_layout

    return run_layout.run_dir(str(source["run"])) / rescore.PICTURES / f"{source['candidate']}.jpg"


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
            "texture_flat": 0,
            "texture_flat_from_register": 0,
            "texture_flat_carried": 0,
            "texture_flat_unmeasured": 0,
            "texture_flat_no_texture": 0,
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

    known = {str(stored["key"]): stored for stored in store.read()}
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
        flat, from_where = _texture_flat_for(recipe, known.get(key) or {})
        counts[from_where] += 1
        counts["texture_flat"] += int(flat)
        rows.append(
            rows_module.row(
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
                texture_flat=flat,
                # **Carried, never re-asked.** A backfill re-derives a row from
                # the decision stores and the picture on disk, and neither says
                # which build drew it — but the row standing here may already
                # say, and this function rewrites every row it touches. Stamping
                # with the *live* build would be a lie about an old picture and
                # dropping the field would make a backfill quietly un-stamp the
                # pool. Absent on both sides, the answer is unknown-engine, which
                # is what the whole backfilled pool is.
                engine=store.engine_of(known.get(key) or {}),
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
    written = door_module.merge(rows, scores, log=log)
    return {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rows_path": written["rows_path"],
        "scores_path": written["scores_path"],
        "stored": {
            "rows": written["ledger"]["rows"],
            "new": written["ledger"]["new"],
            "scores": written["scores"]["rows"],
            "scores_new": written["scores"]["new"],
        },
        "recorded": written["recorded"],
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
    return rows_module.colour_block(dominance.of_picture(picture)), "recoloured"


def _texture_flat_for(recipe: recipes.Recipe, stored: dict) -> tuple[bool, str]:
    """`(the flag, which counter to bump)` for one recipe. Renders nothing.

    A backfill rebuilds the ledger out of the two decision stores and drives no
    engine, so the one thing it cannot do is *measure* this. Two places have the
    answer and they are asked in that order:

    * **The register** — [`fractal_wallpapers.coloring.texture_flat`] — which is
      the measurement, tracked, and keyed on the field side of the render so one
      probe answers for every map at a location.
    * **The row already on record**, for a candidate mined since the engine began
      reporting it. That row's flag came straight off the engine and no register
      entry exists for it.

    They cannot disagree: both are the engine's answer about one field identity.
    A recipe neither knows reads `False`, which is what every reader concluded
    before the flag existed. A mode with no texture layer is counted apart from
    that and not as a fallback: `False` is the only true answer there, and sixteen
    of the seventeen production modes are in it.
    """
    from fractal_wallpapers.coloring import texture_flat

    if not texture_flat.has_a_texture(recipe.mode):
        return False, "texture_flat_no_texture"
    measured = texture_flat.register().get(texture_flat.field_key(recipe.row()))
    if measured is not None:
        return bool(measured), "texture_flat_from_register"
    if "texture_flat" in stored:
        return bool(stored["texture_flat"]), "texture_flat_carried"
    return False, "texture_flat_unmeasured"


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
        stamped = rows_module.score_row(
            key=key,
            artifact=artifact,
            regime=recipe.regime.spelled,
            head=records.kind_of(source),
            read=read,
            source=source,
        )
        out.setdefault(stamped["key"], stamped)
    return list(out.values())
