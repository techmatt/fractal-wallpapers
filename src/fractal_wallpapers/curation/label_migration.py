"""The judged recipes, re-expressed at candidate geometry, staged outside every store.

Two corpora of human verdicts sit in `data/smooth_render/` and
`data/strange_render/`, and each row carries the whole recipe of the picture
somebody judged — at **label geometry**, 1280x720 ss2. The candidate pool is a
different geometry, 640x360 ss2, and nothing had ever asked the obvious question:
what does the pipeline think of the same recipe as a candidate? A judged picture
is the closest thing this project has to ground truth about what is worth
keeping, and every score the pool is seated on is a model's guess at it.

So this derives, for every resolved label row, the **same recipe at candidate
geometry** — geometry changed and nothing else — renders it, and reads it through
the two heads a seating uses: the shipped render judge, and the fine-tier
gallery-grade head. The answer is a readout, not a merge.

## ★ It stages. It writes into no store this project reads

Nothing here touches the candidate ledger, its score sidecar, the fine head's
pool scores, or either label store. Every row this leg makes lands under one
directory a caller names, by default [`DEFAULT_STORE`], and `scratch/` is ignored.
Merging these rows into the pool is a separate act against a separate decision;
deciding whether to is what the readout is for.

## The one thing that is not "geometry and nothing else"

A candidate render goes through the autolevel operator and a ledger row's recipe
key carries the operator's stamp. So a derived recipe carries
[`recipes.live_stamp`] — the identity a render in that mode would carry **right
now** — because that is what makes the derived key comparable with a ledger key at
all. Without it no derived recipe could ever be found in the pool and the overlap
figure would be zero by construction rather than by measurement.

Matt's ruling of 2026-09-08 settles what that costs: a label that is true for the
levelling at 1280x720 ss2 is true at eval resolution, and epsilon variations are
not to be evaluated. So the readout answers *did my picture get seated* and
carries no caveat about divergence. What this leg does do is **record every curve
it derives** — the operator's whole stamp, [`depth.levelling_of`]'s three-way
verdict off it, and the levelled stop list itself, written beside the picture the
way a candidate leg writes it. Defining levelling once at eval resolution and
carrying that curve up is a change somebody intends to make, and these are its
seed; nothing here acts on that intent.

## The curve and the palette are the row's, and that needed a door

The candidate path spends `colorize.CURVE` and the plain palette recipe. **The
corpora do not**: 6,420 of the 11,966 resolved rows carry palette knobs that path
never produces and 868 read their field through `log`. So `colorize.render_row`
grew a `curve` and a `palette` override, off by default, and this is its only
caller. It also means the key-level overlap this leg measures is bounded above by
the plain-recipe half of the corpora, which is a fact about the two stores rather
than about the pool.

## The stages

```
census   read-only: how much of the ledger the fine head has read, and the gap
derive   every resolved row -> a candidate-geometry recipe and its key; the overlap
render   one picture per derived key, levelled, with its curve written beside it
score    the shipped render judge and the fine head, both at candidate geometry
readout  the distributions, the bars, the places, what the path can express, the prune
page     one row per label-4 verdict: what was judged, beside what a candidate is
merge    the scored rows the pool does not already hold, through THE door
```

Each writes one file and reads the ones before it, so a killed stage costs itself
and nothing earlier. Every labelling sitting produces new rows, so this is a verb
and not a script: re-running `derive` after a batch lands re-uses every picture
already on disk.
"""

from __future__ import annotations

import json
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path

from fractal_wallpapers.curation import recipes as recipes_module
from fractal_wallpapers.labeling import finished
from fractal_wallpapers.paths import repo_root

#: The schema every row and record this module writes carries.
SCHEMA = 1

#: Where a staging store lands unless a caller names one, under the checkout's
#: ignored scratch tree. **Not `artifacts/`**: a staged row is not runtime output
#: of the pipeline, it is a reading nothing in the pipeline may find by accident,
#: and the three-way `artifacts/` decision has no bin for *must not be read*.
DEFAULT_STORE = Path("scratch") / "label_migration"

#: The files one staging store holds, in the order the stages write them.
RECIPES_NAME = "recipes.jsonl"
RENDERS_NAME = "renders.jsonl"
SCORES_NAME = "scores.jsonl"
READOUT_NAME = "readout.json"
PAGE_NAME = "index.html"
MERGE_NAME = "merge.json"

#: Where the candidate-geometry pictures go, and — beside each one, under
#: `<key>.leveled/` — the levelled colormap the operator rendered it through.
#: `colorize.render` writes that directory itself and this leg **keeps** it rather
#: than sweeping it, which is the whole of the addendum's *record what you
#: compute*.
PICTURES_NAME = "pictures"

#: Where [`page`]'s own copies of the two pictures go. Copies and not links, so
#: the directory can be handed to somebody whole.
PAGE_PICTURES = "page_pictures"

#: How wide a picture on the page is written. Both sides are written at this
#: width so the pair is a comparison at **one display size** and not a comparison
#: of two sizes — the candidate at its own 640, the judged render reduced to it.
PAGE_WIDTH = 640

#: JPEG quality the page's copies are written at.
PAGE_QUALITY = 88

#: How many engines the render stage drives. **Three**, this machine's render
#: pool, and a rule about the desktop rather than a knob.
WORKERS = 3

#: How many pictures a judge reads at once.
SCORE_BATCH = 128

#: How many renders one worker takes per task. A chunk rather than a row so the
#: spawn cost is amortised, and small enough that the log moves.
RENDER_CHUNK = 24

#: The human verdict classes this leg renders, scores and reads out. **3 and 4**,
#: Matt's ruling of 2026-09-08, taken against a leg already in flight.
#:
#: What the 1s and 2s buy is calibration of the fine head across the full human
#: range, and that is eval-instrument work rather than a question about the pool.
#: They are also a population the head never meets in production: `score-pool`
#: runs on coarse-clears only ([`census`] names the condition), so a row the render
#: judge puts at the bottom is a row `p_fine` is never asked about. Rendering them
#: was half the leg's cost for an answer nothing acts on.
#:
#: **It restricts the renders and not the derivation.** [`expressibility`] reads
#: `recipes.jsonl` and needs no picture, so which judged recipes the candidate path
#: can produce at all is still answered across every class — that finding is the
#: reason the leg is worth running and it must not shrink with the render
#: population.
KEPT_CLASSES: tuple[int, ...] = (3, 4)

#: The subtree under `artifacts/curation` this leg's **merged** pictures live in,
#: and it is named in [`candidate_ledger.POOL_SUBTREES`] as well. A staged picture
#: lives in the store under `scratch/` and cannot merge from there: the orphan
#: sweep enumerates `<subtree>/<leg>/pictures` and no other shape, so a picture
#: anywhere else is a picture with a ledger row that nothing in the project can
#: ever find again. Adding a name to that tuple is half of shipping a leg, and
#: this is the other half.
#:
#: The pictures are **moved** and not copied. Both trees are on the same volume,
#: so the move is a rename; a copy would be a gibibyte of the same JPEGs twice, and
#: [`page`] already keeps its own reduced copies under [`PAGE_PICTURES`], so the
#: page survives the move with nothing repointed.
POOL_SUBTREE = "label_migration"


class MigrationError(RuntimeError):
    """A stage that cannot run, or a store that cannot be read."""


# --------------------------------------------------------------------------- #
# The store.
# --------------------------------------------------------------------------- #
def store_root(store: str | Path | None = None) -> Path:
    """The directory one staging run owns. A relative name is under the checkout."""
    where = Path(DEFAULT_STORE if store is None else store)
    return where if where.is_absolute() else repo_root() / where


def _path(store, name: str) -> Path:
    return store_root(store) / name


def leg_of(store: str | Path | None = None) -> str:
    """What the pool calls this store's contribution: the store directory's own name.

    One name for the two halves, so a reader who has the staged store can find its
    pictures in the pool and a reader who has a ledger row's `provenance.run` can
    find the store it came from. That is the whole reason it is derived rather than
    a flag: a leg name a caller chose is a leg name nothing joins back.
    """
    return store_root(store).name


def merged_pictures_dir(store: str | Path | None = None) -> Path:
    """Where this store's merged pictures live in the pool, under [`POOL_SUBTREE`]."""
    from fractal_wallpapers.curation import candidate_ledger
    from fractal_wallpapers.paths import under

    return under("curation", POOL_SUBTREE, leg_of(store)) / candidate_ledger.PICTURES_NAME


def in_population(row: dict, classes=KEPT_CLASSES) -> bool:
    """Whether one derived recipe is in the population this leg renders and reads.

    **Any verdict qualifies the key.** A key carrying two verdicts is one of
    [`finished.crossovers`]' itinerary pairs — literally the same pixels judged in
    both stores — and dropping it because its *other* verdict is low would drop a
    picture somebody called a 4. Over the 2026-09-08 derivation the rule buys
    nothing, because all 117 crossover pairs happen to fall on one side of the
    boundary together; it is the rule anyway, since which side they fall on is a
    fact about today's corpora rather than about the join.
    """
    wanted = {int(name) for name in classes}
    return any(int(label["score"]) in wanted for label in row.get("labels") or ())


def _population(store, classes=KEPT_CLASSES) -> tuple[dict, dict]:
    """`(the derived rows this leg acts on, every derived row)`, both keyed."""
    every = {str(row["key"]): row for row in _read_jsonl(_path(store, RECIPES_NAME))}
    kept = {key: row for key, row in every.items() if in_population(row, classes)}
    return kept, every


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        raise MigrationError(f"{path} is not there — run the stage that writes it first")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _write_jsonl(path: Path, rows) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def _write_json(path: Path, document: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- #
# The census. Read-only, and about the POOL rather than the corpora — it is here
# because it is the question this leg exists downstream of.
# --------------------------------------------------------------------------- #
def census(log=print) -> dict:
    """How much of the candidate ledger the fine head has read, and what the gap costs.

    The fine bar acts on the whole seating pool, so a row with no `p_fine` is
    **outside** the population the bar acts on rather than under it. This says how
    large that population is, per mode, and — the question that matters — how many
    of its rows would be *seatable if scored*: they clear their own mode's
    [`headroom.bars`] render-judge bar and are refused by nothing else.

    ## What decides which rows the fine head runs on today

    One condition in one place. `curate gallery-grade score-pool` builds its
    population with [`solve.pool`] and hands it to
    `models.gallery_grade_train.score_pool`, which skips every candidate reading
    `above_bar is False` — and [`solve.Candidate.above_bar`] is
    `score >= solve.Q4_BAR`. So it runs on **coarse-clears only**, on the render
    judge's own `p_ge4` at [`curation.floors.RELEASE_ADVISORY`], and the head's own
    docstring says why: every row it was fitted on had cleared a gate, so its
    output below one is undefined.

    That is the same height [`headroom.bars`] uses by default, which is why the
    gap this measures can read zero — and it is not guaranteed to stay zero, in
    two directions. The census bar falls back to `P(>=3)` for a mode holding fewer
    than [`headroom.FALLBACK_LOCATIONS`] distinct clearing places, and a row
    clearing on the fallback column is a row the fine head does not read at all;
    no accepted mode is on the fallback today. And the pool scores are a file
    somebody ran once, so every above-bar row merged since is unread.
    """
    from fractal_wallpapers.curation import candidate_ledger, headroom, mode_policy, solve
    from fractal_wallpapers.models import gallery_grade_train

    began = time.time()
    fine = gallery_grade_train.read_pool_scores()
    rows = candidate_ledger.read()
    scores = candidate_ledger.read_scores()
    artifact = candidate_ledger.live_artifact()
    by_key = candidate_ledger.scores_by_recipe(scores, artifact=artifact)
    candidates, refused = solve.pool(rows=rows, scores=scores, log=log)
    table = headroom.bars(candidates)
    present = candidate_ledger.present_pictures(rows)
    log(
        f"[census] {len(rows):,} ledger row(s), {len(fine):,} carry a p_fine reading; "
        f"pool {len(candidates):,}"
    )

    per: dict = {}
    for row in rows:
        mode = mode_policy.routed_mode_of(row)
        seat = per.setdefault(mode, _census_seat(mode_policy.is_accepted(mode)))
        seat["rows"] += 1
        key = str(row["key"])
        has_fine = key in fine
        seat["with_p_fine"] += has_fine
        reading = by_key.get(key)
        clears = _clears_its_bar(row, mode, reading, table)
        seat["clears_the_bar"] += clears
        if not seat["on_the_roster"]:
            seat["off_the_roster"] += 1
            continue
        if row.get("rejected"):
            seat["rejected"] += 1
            continue
        if not row.get("at_candidate_regime"):
            seat["off_regime"] += 1
            continue
        if reading is None or reading.get("p_ge4") is None:
            seat["no_render_score"] += 1
            continue
        if not clears or has_fine:
            continue
        seat["seatable_if_scored"] += 1
        if key in present:
            seat["seatable_and_has_its_picture"] += 1
        else:
            seat["seatable_and_needs_a_re_render"] += 1

    totals = {name: 0 for name in _census_seat(True) if name != "on_the_roster"}
    for seat in per.values():
        for name in totals:
            totals[name] += seat[name]
    record = {
        "schema": SCHEMA,
        "taken_at": _now(),
        "judge_artifact": artifact,
        "ledger_rows": len(rows),
        "p_fine_rows": len(fine),
        "p_fine_rows_not_in_the_ledger": len(set(fine) - {str(row["key"]) for row in rows}),
        "pool": len(candidates),
        "pool_refused": refused,
        "bars": {
            "default": table["default"],
            "fallback": table["fallback"],
            "on_fallback": table["on_fallback"],
            "still_thin": table["still_thin"],
        },
        "what_decides_who_the_fine_head_reads": {
            "path": "cli/gallery_grade_commands.py `score-pool` -> curation.solve.pool -> "
            "models.gallery_grade_train.score_pool",
            "condition": "`if getattr(candidate, 'above_bar', True) is False: continue` in "
            "score_pool; solve.Candidate.above_bar is `score >= solve.Q4_BAR`",
            "so": f"coarse-clears only, on the render judge's p_ge4 at {solve.Q4_BAR}, "
            "which is curation.floors.RELEASE_ADVISORY",
            "why": "the head was fitted only on rows that had cleared a gate, so its output "
            "below one is undefined",
        },
        "totals": totals,
        "per_mode": dict(sorted(per.items(), key=lambda item: -item[1]["rows"])),
        "seconds": round(time.time() - began, 1),
    }
    log(
        f"[census] {totals['seatable_if_scored']:,} unscored row(s) clear their own mode's "
        f"bar and would be seatable if scored; {totals['seatable_and_needs_a_re_render']:,} "
        f"of those have lost their picture"
    )
    return record


def _census_seat(accepted: bool) -> dict:
    return {
        "on_the_roster": bool(accepted),
        "rows": 0,
        "with_p_fine": 0,
        "clears_the_bar": 0,
        "seatable_if_scored": 0,
        "seatable_and_has_its_picture": 0,
        "seatable_and_needs_a_re_render": 0,
        "off_the_roster": 0,
        "rejected": 0,
        "off_regime": 0,
        "no_render_score": 0,
    }


def _clears_its_bar(row: dict, mode: str, reading: dict | None, table: dict) -> bool:
    """Whether one ledger row clears its own mode's census bar, through `headroom`.

    Asked with [`headroom.clears`] and never with a restated constant, so the
    column and its height cannot come apart here. A mode the roster does not hold
    has no rule and clears nothing, which is [`headroom.clearing`]'s own answer by
    a second route.
    """
    from fractal_wallpapers.curation import headroom, solve

    if reading is None or reading.get("p_ge4") is None:
        return False
    return headroom.clears(
        solve.Candidate(
            key=str(row["key"]),
            location=str((row.get("location") or {}).get("key")),
            partition=str(row.get("partition")),
            mode=mode,
            group="",
            kind="",
            cells=(),
            families=(),
            score=float(reading["p_ge4"]),
            p_ge3=float(reading.get("p_ge3") or 0.0),
            picture=str(row.get("picture") or ""),
        ),
        (table["modes"].get(mode) or {}).get("rule"),
    )


# --------------------------------------------------------------------------- #
# derive.
# --------------------------------------------------------------------------- #
def derive(store=None, log=print) -> dict:
    """Every resolved label row as a recipe at candidate geometry. Writes `recipes.jsonl`.

    The population is [`finished.resolved`]`.scored()` over **both** stores and
    **every** label class. The recipe is the row's own — its frame, its maxiter,
    its mode with its settings, its curve, its map and all seven palette knobs —
    with [`recipes.CANDIDATE_REGIME`] in place of the label regime and
    [`recipes.live_stamp`] for the operator. Nothing else moves. The resolution
    and the supersample come from that constant and never from a caller.

    Two verdicts can derive one recipe, and 117 do: those are
    [`finished.crossovers`]' pairs, one picture judged in both stores because its
    modulate texture said nothing. They are kept as two verdicts on one key rather
    than collapsed, so a per-class readout counts each verdict once and each
    picture once.

    The overlap figure this reports is the **first key-level comparison of the two
    stores this project has taken**; everything before it compared them by place.
    """
    from fractal_wallpapers.coloring import texture_flat
    from fractal_wallpapers.curation import candidate_ledger, colorize, mode_policy
    from fractal_wallpapers.palettes import groups as groups_module

    began = time.time()
    band = colorize.band()
    groups = groups_module.member_groups()
    cyclic = colorize.cyclic()
    held: dict = {}
    refused: list = []
    per_class: dict = {}
    label_regimes: dict = {}
    for head in finished.HEADS:
        resolution = finished.resolved(head)
        log(f"[derive] {head}: {resolution.summary()}")
        for row in resolution.scored():
            name = f"{head}/{row['score']}"
            per_class[name] = per_class.get(name, 0) + 1
            geometry = row.get("render") or {}
            spelled = f"{geometry.get('resolution')}ss{geometry.get('supersample')}"
            label_regimes[spelled] = label_regimes.get(spelled, 0) + 1
            try:
                recipe = recipe_of(row, band, groups)
                key = recipes_module.key_of(recipe)
            except Exception as failure:  # noqa: BLE001 — a refusal is a recorded fact
                refused.append(
                    {"head": head, "batch": row.get("batch"), "why": repr(failure)[:200]}
                )
                continue
            entry = held.setdefault(key, {"recipe": recipe, "labels": [], "flat": None})
            if entry["flat"] is None:
                entry["flat"] = bool(texture_flat.flat_for(row))
            entry["labels"].append(
                {
                    "head": head,
                    "score": int(row["score"]),
                    "batch": row.get("batch"),
                    "recorded_at": row.get("recorded_at"),
                    "labeler": row.get("labeler"),
                    "origin": row.get("origin"),
                    "partition": row.get("partition"),
                    "label_render": geometry,
                    "label_picture": label_picture(head, row),
                }
            )

    ledger = {str(row["key"]) for row in candidate_ledger.stream()}
    rows = []
    for key, entry in sorted(held.items()):
        recipe = entry["recipe"]
        rows.append(
            {
                "schema": SCHEMA,
                "key": key,
                "in_the_candidate_ledger": key in ledger,
                "location": _location_of(recipe),
                "partition": _partition_of(entry["labels"]),
                "mode": recipe.mode,
                "mode_params": dict(recipe.mode_params),
                # What the pool would COUNT this as — the mode a bar and a floor
                # are read per. The render is at `mode` and never at this.
                "routed_mode": mode_policy.routed_mode(recipe.mode, entry["flat"]),
                "texture_flat": entry["flat"],
                "plain_candidate_recipe": recipe.curve == colorize.CURVE
                and recipe.palette == finished.recipe(mirror=recipe.colormap not in cyclic),
                "recipe": recipe.record(),
                "labels": entry["labels"],
            }
        )
    overlap = sum(1 for row in rows if row["in_the_candidate_ledger"])
    plain = sum(1 for row in rows if row["plain_candidate_recipe"])
    path = _write_jsonl(_path(store, RECIPES_NAME), rows)
    record = {
        "schema": SCHEMA,
        "taken_at": _now(),
        "store": str(store_root(store)),
        "label_verdicts": sum(per_class.values()),
        "per_label_class": dict(sorted(per_class.items())),
        "derived_recipes": len(rows),
        "keys_carrying_two_verdicts": sum(1 for row in rows if len(row["labels"]) > 1),
        "already_in_the_candidate_ledger": overlap,
        "already_in_the_candidate_ledger_share": round(overlap / max(1, len(rows)), 4),
        "expressible_by_the_candidate_path": plain,
        "expressible_is": (
            "the row's curve is colorize.CURVE and its palette is the plain recipe, so a "
            "candidate leg could have made this picture at all. The overlap is bounded "
            "above by it"
        ),
        "label_regimes": dict(sorted(label_regimes.items(), key=lambda item: -item[1])),
        "candidate_regime": recipes_module.CANDIDATE_REGIME.spelled,
        "autolevel_on_the_derived_key": (
            "recipes.live_stamp — the identity a render in that mode carries right now. "
            "Without it no derived key could be found in the ledger at all"
        ),
        "refused": refused[:20],
        "refused_count": len(refused),
        "wrote": str(path),
        "seconds": round(time.time() - began, 1),
    }
    log(
        f"[derive] {len(rows):,} distinct recipe(s) from {record['label_verdicts']:,} "
        f"verdict(s); {overlap:,} already in the candidate ledger; {plain:,} the candidate "
        f"path could have made"
    )
    return record


def recipe_of(row: dict, band: dict | None, groups: dict):
    """One label row as a [`recipes.Recipe`] at candidate geometry."""
    from fractal_wallpapers.palettes import groups as groups_module

    render = row.get("render") or {}
    mode = str(row["mode"])
    colormap = str(row["colormap"])
    return recipes_module.Recipe(
        family=row["family"],
        viewport=row["viewport"],
        maxiter=int(render["maxiter"]),
        regime=recipes_module.CANDIDATE_REGIME,
        mode=mode,
        mode_params=dict(row.get("mode_params") or {}),
        curve=str(row["curve"]),
        colormap=colormap,
        palette=dict(row["recipe"]),
        autolevel=recipes_module.live_stamp(mode, band),
        palette_group=groups_module.group_of(colormap, groups),
    )


def _location_of(recipe) -> str:
    """The recipe's place, spelled the way every store here spells one."""
    from fractal_wallpapers.supply.location import location_key

    return json.dumps(list(location_key(recipe.family, recipe.viewport)))


def _partition_of(labels: list) -> str | None:
    for label in labels:
        if label.get("partition"):
            return str(label["partition"])
    return None


def label_picture(head: str, row: dict) -> str:
    """Where the render cache keeps the picture this verdict was cast on.

    Through [`renders.job_name`] on the row itself, which is the derivation
    `renders.plan` uses — so this names the file that build wrote and never a
    second guess at it.
    """
    from fractal_wallpapers.models import renders

    stripped = {key: value for key, value in row.items() if not key.startswith("_")}
    stripped["_head"] = head
    return str(renders.crop_dir(head) / f"{renders.job_name(stripped)}.jpg")


# --------------------------------------------------------------------------- #
# render.
# --------------------------------------------------------------------------- #
def render_chunk(payload: dict) -> list:
    """One chunk of derived recipes, in a worker. **Module level**, for the spawn.

    Every render takes the engine path: the field cache cannot serve a curve or a
    palette override, and `colorize.render` refuses the pair rather than serving
    the plain picture under the override's name.
    """
    from fractal_wallpapers.curation import colorize, depth

    band = colorize.band()
    cyclic = colorize.cyclic()
    out = []
    for job in payload["rows"]:
        stored = job["recipe"]
        picture = Path(job["picture"])
        row = {
            "schema": SCHEMA,
            "key": job["key"],
            "picture": str(picture),
            "made": False,
            "seconds": None,
            "why": None,
        }
        if picture.is_file():
            out.append({**row, **job["standing"], "made": True, "why": "already on disk"})
            continue
        began = time.time()
        try:
            recipe = recipes_module.of_record(stored)
            _made, stamp = colorize.render(
                {
                    "family": recipe.family,
                    "viewport": recipe.viewport,
                    "maxiter": recipe.maxiter,
                },
                recipe.mode,
                recipe.colormap,
                cyclic,
                picture,
                render_geometry=recipe.render(),
                level=True,
                band=band,
                fields=None,
                mode_params=recipe.mode_params,
                curve=recipe.curve,
                palette=recipe.palette,
            )
        except Exception as failure:  # noqa: BLE001 — a failed render is a recorded fact
            row["why"] = repr(failure)[:300]
            row["seconds"] = round(time.time() - began, 3)
            out.append(row)
            continue
        # The curve, written down. `colorize.render` names the directory after the
        # picture and leaves it there when the operator acted; where it did not,
        # the render IS the base map's own bytes and there is no curved stop list.
        curved = picture.parent / f"{picture.stem}.leveled" / f"{recipe.colormap}.json"
        out.append(
            {
                **row,
                "made": True,
                "seconds": round(time.time() - began, 3),
                "autolevel": stamp,
                "levelling": depth.levelling_of(
                    {"autolevel": stamp, "acted": bool(stamp and stamp.get("acted"))}
                ),
                "operator_acted": bool(stamp and stamp.get("acted")),
                "operator_applies": recipes_module.autolevel_applies(colorize.kind_of(recipe.mode)),
                "leveled_colormap": str(curved) if curved.is_file() else None,
            }
        )
    return out


def render(
    store=None,
    limit: int | None = None,
    workers: int = WORKERS,
    classes=KEPT_CLASSES,
    log=print,
) -> dict:
    """Render the population's derived recipes at candidate geometry. Writes `renders.jsonl`.

    Each at **its own** `recipe["mode"]` and never the routed one: routing says
    which judge's corpus a picture belongs to, and a render at the routed mode
    would be a different picture.

    `classes` is the human verdicts a recipe has to carry one of —
    [`KEPT_CLASSES`], and [`in_population`] is the test.

    Resumable, and this is a leg that has been resumed. A picture already on disk
    is not made again and its previous row — stamp, levelling verdict, levelled
    colormap — is carried forward, so a killed leg continues and the record stays
    complete. **A picture made for a recipe the population no longer holds stays on
    disk and keeps its row**, marked `in_the_population: false`: it cost engine
    seconds somebody paid, its levelled curve is the thing addendum 1 asked to be
    recorded, and deleting either would make the trim look free. Nothing downstream
    reads those rows.

    A kill leaves the temporaries [`colorize.WRITING_INFIX`] names, so they are
    swept before anything renders — the presence of a picture is what makes this
    resumable, and a half-written one must never be mistaken for a finished one.
    """
    from concurrent.futures import ProcessPoolExecutor

    from fractal_wallpapers.curation import colorize

    began = time.time()
    kept, every = _population(store, classes)
    pictures = store_root(store) / PICTURES_NAME
    pictures.mkdir(parents=True, exist_ok=True)
    swept = colorize.sweep_writing(pictures)
    if swept:
        log(f"[render] swept {swept:,} half-written picture(s) a killed leg left")
    wanted = list(kept.values())
    if limit is not None:
        wanted = wanted[: int(limit)]
    carried = ("autolevel", "levelling", "operator_acted", "operator_applies", "leveled_colormap")
    standing = {}
    if _path(store, RENDERS_NAME).is_file():
        standing = {
            str(row["key"]): {name: row.get(name) for name in carried}
            for row in _read_jsonl(_path(store, RENDERS_NAME))
        }
    jobs = [
        {
            "key": str(row["key"]),
            "recipe": row["recipe"],
            "picture": str(pictures / f"{row['key']}.jpg"),
            "standing": standing.get(str(row["key"]), dict.fromkeys(carried)),
        }
        for row in wanted
    ]
    # What the trim already cost: a picture on disk for a recipe outside the
    # population. Kept, never scored, and counted so the cost is visible.
    outside = [
        {
            "schema": SCHEMA,
            "key": key,
            "picture": str(pictures / f"{key}.jpg"),
            "made": True,
            "seconds": None,
            "why": "rendered before the population was trimmed to "
            f"{tuple(int(name) for name in classes)}",
            "in_the_population": False,
            **standing.get(key, dict.fromkeys(carried)),
        }
        for key in every
        if key not in kept and (pictures / f"{key}.jpg").is_file()
    ]
    on_disk = sum(1 for job in jobs if Path(job["picture"]).is_file())
    log(
        f"[render] {len(jobs):,} recipe(s) in the population of {len(every):,}, "
        f"{on_disk:,} already on disk, {len(outside):,} rendered before the trim, "
        f"{int(workers)} worker(s)"
    )

    chunks = [{"rows": jobs[at : at + RENDER_CHUNK]} for at in range(0, len(jobs), RENDER_CHUNK)]
    made, failed, engine_seconds = 0, 0, 0.0
    why: list = []
    rows: list = []
    # Counted directly and NOT as `made - on_disk`: the resume skips are scattered
    # through the plan rather than at the front of it, so that subtraction reads
    # zero until more rows have come back than the whole skip set and prints an
    # ETA in the billions of minutes while the leg is in fact running fine.
    drawn = 0
    with ProcessPoolExecutor(max_workers=int(workers)) as pool:
        for done, batch in enumerate(pool.map(render_chunk, chunks), start=1):
            for row in batch:
                rows.append(row)
                made += bool(row["made"])
                drawn += bool(row["made"]) and row["seconds"] is not None
                failed += not row["made"]
                engine_seconds += float(row["seconds"] or 0.0)
                if not row["made"] and len(why) < 20:
                    why.append(f"{row['key']}: {row['why']}")
            if done % 20 == 0 or done == len(chunks):
                wall = time.time() - began
                rate = drawn / max(1e-9, wall)
                left = max(0, len(jobs) - on_disk - drawn) / max(1e-9, rate)
                log(
                    f"[render] {made:,} of {len(jobs):,} in {wall / 60:.1f} min "
                    f"({rate:.2f}/s, ~{left / 60:.0f} min left), {failed:,} failed"
                )
    for row in rows:
        row["in_the_population"] = True
    path = _write_jsonl(_path(store, RENDERS_NAME), rows + outside)
    levelling: dict = {}
    for row in rows:
        name = str(row.get("levelling"))
        levelling[name] = levelling.get(name, 0) + 1
    fresh = max(1, drawn)
    record = {
        "schema": SCHEMA,
        "taken_at": _now(),
        "store": str(store_root(store)),
        "regime": recipes_module.CANDIDATE_REGIME.spelled,
        "population": {
            "classes": [int(name) for name in classes],
            "derived_recipes": len(every),
            "in_the_population": len(kept),
            "rendered_before_the_trim": len(outside),
            "any_verdict_qualifies": "a key carrying two verdicts is in if either is kept — "
            "those are finished.crossovers' pairs, the same pixels judged in both stores",
            "kept_on_disk": "a picture made for a recipe outside the population stays, keeps "
            "its levelled curve and its row, and is scored by nothing",
        },
        "asked": len(jobs),
        "already_on_disk": on_disk,
        "made": made,
        "drawn_this_run": drawn,
        "failed": failed,
        "why": why,
        "rendered_at_their_own_mode": "recipe['mode'], never the routed mode",
        "operator_acted": sum(1 for row in rows if row.get("operator_acted")),
        "operator_applies": sum(1 for row in rows if row.get("operator_applies")),
        "levelled_colormaps_written": sum(1 for row in rows if row.get("leveled_colormap")),
        "levelling": dict(sorted(levelling.items())),
        "levelling_is": "curation.depth.levelling_of over each render's own stamp",
        "workers": int(workers),
        "wall_seconds": round(time.time() - began, 1),
        "engine_seconds": round(engine_seconds, 1),
        "seconds_per_picture": round(engine_seconds / fresh, 4),
        "seconds_per_picture_is": "per ENGINE over the pictures this run made; wall a picture "
        "is this over the concurrency",
        "wrote": str(path),
    }
    log(f"[render] {made:,} made, {failed:,} failed in {record['wall_seconds'] / 60:.1f} min")
    return record


# --------------------------------------------------------------------------- #
# score.
# --------------------------------------------------------------------------- #
def score(store=None, device: str = "auto", batch: int = SCORE_BATCH, log=print) -> dict:
    """Both heads over the staged pictures, at candidate geometry. Writes `scores.jsonl`.

    The shipped render judge through [`colorize.load_judge`] — the same call every
    candidate leg makes — and the fine-tier head through the band's own picked
    run, the one `gallery-grade score-pool` writes the pool column from. **Neither
    reading is written into a store the pipeline reads**: `pool_scores.jsonl` is
    left exactly as it stands, and so is the ledger's sidecar.

    This is the existing regime and creates no second one. Every picture read here
    is 640x360 ss2, which is what the sidecar already holds and what both heads are
    deployed against; nothing is scored at label geometry and `rerender.rescore` is
    not touched.

    **Only the population is read.** A picture rendered before the trim carries
    `in_the_population: false` and is skipped here, so the 1s and 2s already on disk
    cost nothing further.
    """
    from fractal_wallpapers.curation import candidate_ledger, colorize
    from fractal_wallpapers.models import gallery_grade_train, head, scoring, train

    began = time.time()
    staged = {
        str(row["key"]): row
        for row in _read_jsonl(_path(store, RENDERS_NAME))
        if row.get("in_the_population", True)
    }
    keys, paths = [], []
    for key, row in sorted(staged.items()):
        where = Path(row["picture"])
        if where.is_file():
            keys.append(key)
            paths.append(where)
    log(f"[score] {len(paths):,} of {len(staged):,} in-population picture(s) on disk")
    if not paths:
        raise MigrationError("no staged picture is on disk — run the render stage first")

    model, config, where = colorize.load_judge(device)
    judge = train.score(
        model,
        paths,
        scoring.transform_of(config),
        where,
        int(config["classes"]),
        {"batch_size": int(batch)},
    )
    log(f"[score] the render judge read {len(paths):,} picture(s) on {where}")

    picked = gallery_grade_train.band()["pick"]
    run = gallery_grade_train.run_name(picked["arm"], picked["seed"])
    checkpoint = gallery_grade_train.run_dir(picked["arm"], picked["seed"]) / "best.pt"
    fine_model, fine_config, fine_where = gallery_grade_train.load_checkpoint(checkpoint, device)
    fine = train.score(
        fine_model,
        paths,
        head.Transform(
            tuple(fine_config["mean"]),
            tuple(fine_config["std"]),
            fine_config["interpolation"],
            train=False,
            target=tuple(fine_config["target_dims"]),
        ),
        fine_where,
        int(fine_config["classes"]),
        fine_config,
    )
    log(f"[score] the fine head {run} read them on {fine_where}")

    rows = [
        {
            "schema": SCHEMA,
            "key": key,
            "regime": recipes_module.CANDIDATE_REGIME.spelled,
            "judge": _reading(judge[index]),
            "fine": _reading(fine[index]),
        }
        for index, key in enumerate(keys)
    ]
    path = _write_jsonl(_path(store, SCORES_NAME), rows)
    record = {
        "schema": SCHEMA,
        "taken_at": _now(),
        "store": str(store_root(store)),
        "read": len(rows),
        "regime": recipes_module.CANDIDATE_REGIME.spelled,
        "judge_artifact": candidate_ledger.live_artifact(),
        "fine_run": run,
        "wrote_nothing_into": [
            "the candidate ledger and its score sidecar",
            str(gallery_grade_train.pool_scores_path()),
            "either finished-render label store",
        ],
        "seconds": round(time.time() - began, 1),
        "wrote": str(path),
    }
    log(f"[score] {len(rows):,} row(s) read by both heads in {record['seconds']}s")
    return record


def _reading(probabilities) -> dict:
    row = {f"p_ge{index + 2}": float(value) for index, value in enumerate(probabilities)}
    row["rank_score"] = float(sum(float(value) for value in probabilities))
    return row


# --------------------------------------------------------------------------- #
# readout.
# --------------------------------------------------------------------------- #
def readout(store=None, stamp: str | None = None, classes=KEPT_CLASSES, log=print) -> dict:
    """What the two heads say about the judged recipes. Writes `readout.json`.

    Per human label class, the shape of both columns; then the label-4 rows
    against their mode's render-judge bar and against the fine bar; then where
    those stand against a recorded gallery; then [`expressibility`] — which judged
    recipes the candidate path could produce at all, cross-tabbed and explained,
    with the seated gallery as its control; then [`fine_by_expressibility`], which
    is that line laid over `p_fine`; then what a merge would cost at the prune,
    priced over the whole scored population and over the label-4 rows apart.
    Nothing is merged and nothing is written into a store.
    """
    from fractal_wallpapers.curation import (
        candidate_ledger,
        headroom,
        solve,
        tentative,
    )

    began = time.time()
    # `derived` is the POPULATION and `every` is the whole derivation. The split is
    # load-bearing: `expressibility` reads `every`, because which judged recipes the
    # candidate path can produce at all is a question about the corpora and must not
    # shrink with what this leg happened to render.
    derived, every = _population(store, classes)
    scored = {str(row["key"]): row for row in _read_jsonl(_path(store, SCORES_NAME))}
    staged = {str(row["key"]): row for row in _read_jsonl(_path(store, RENDERS_NAME))}
    log(
        f"[readout] {len(derived):,} in the population of {len(every):,} derived, "
        f"{len(scored):,} scored"
    )

    ledger_rows = candidate_ledger.read()
    ledger_scores = candidate_ledger.read_scores()
    candidates, _refused = solve.pool(rows=ledger_rows, scores=ledger_scores, log=log)
    table = headroom.bars(candidates)

    # --- per label class ------------------------------------------------------ #
    # `per_class` and NOT `classes`: the parameter of that name is the population,
    # and a local rebinding it turns the record's own `population.classes` into a
    # list of "smooth_render/3" strings at the last line of the stage.
    per_class: dict = {}
    verdicts = 0
    for key, row in derived.items():
        reading = scored.get(key)
        if reading is None:
            continue
        for label in row["labels"]:
            verdicts += 1
            seat = per_class.setdefault(
                f"{label['head']}/{label['score']}", {"p_ge4": [], "p_fine": []}
            )
            seat["p_ge4"].append(float(reading["judge"]["p_ge4"]))
            seat["p_fine"].append(float(reading["fine"]["p_ge4"]))
    distributions = {
        name: {"p_ge4": _quantiles(seat["p_ge4"]), "p_fine": _quantiles(seat["p_fine"])}
        for name, seat in sorted(per_class.items())
    }

    # --- the label-4 rows ----------------------------------------------------- #
    fine_bar = float(solve.DEFAULT_FINE_BAR)
    fours = [
        key
        for key, row in derived.items()
        if key in scored and any(int(label["score"]) == 4 for label in row["labels"])
    ]
    cleared: dict = {"judge": [], "fine": [], "both": []}
    for key in sorted(fours):
        row, reading = derived[key], scored[key]
        rule = (table["modes"].get(str(row["routed_mode"])) or {}).get("rule")
        clears_judge = headroom.clears(
            solve.Candidate(
                key=key,
                location=str(row["location"]),
                partition=str(row.get("partition")),
                mode=str(row["routed_mode"]),
                group=str((row["recipe"] or {}).get("palette_group")),
                kind="",
                cells=(),
                families=(),
                score=float(reading["judge"]["p_ge4"]),
                p_ge3=float(reading["judge"]["p_ge3"]),
                picture=str((staged.get(key) or {}).get("picture") or ""),
            ),
            rule,
        )
        clears_fine = float(reading["fine"]["p_ge4"]) >= fine_bar
        if clears_judge:
            cleared["judge"].append(key)
        if clears_fine:
            cleared["fine"].append(key)
        if clears_judge and clears_fine:
            cleared["both"].append(key)

    # --- against the recorded gallery ----------------------------------------- #
    named = tentative.latest() if stamp is None else str(stamp)
    gallery = _read_jsonl(tentative.rows_path(named))
    seated = {str(row["location"]) for row in gallery if row.get("location")}
    at_seated = [key for key in cleared["both"] if derived[key]["location"] in seated]
    both_places = {derived[key]["location"] for key in cleared["both"]}
    places = {
        "stamp": named,
        "seats": len(seated),
        "clearing_both": len(cleared["both"]),
        "at_a_place_the_gallery_holds": len(at_seated),
        "at_a_place_the_gallery_does_not_hold": len(cleared["both"]) - len(at_seated),
        "distinct_places_clearing_both": len(both_places),
        "distinct_places_the_gallery_does_not_hold": len(both_places - seated),
        "one_wallpaper_per_location": "a place the gallery already holds is a place a new "
        "row can only DISPLACE at, never add to",
    }

    # The WHOLE scored population first, because that is what a merge submits. The
    # label-4 pricing is kept beside it and priced second off the same cache: it is
    # a subset, so every picture it reads has already been read.
    flat_cache: dict = {}
    priced = sorted(key for key in derived if key in scored)
    prune = _price_the_prune(
        priced, derived, scored, staged, ledger_rows, ledger_scores, flat_cache, log=log
    )
    prune["priced_over"] = "every scored row of the population — what a merge submits"
    prune_fours = _price_the_prune(
        sorted(fours), derived, scored, staged, ledger_rows, ledger_scores, flat_cache, log=log
    )
    prune_fours["priced_over"] = "the label-4 rows alone, which is a SUBSET of the merge"
    identity = _byte_identity(derived, staged, ledger_rows, log=log)
    reach = expressibility(every, log=log)
    reach["the_seated_gallery"] = seat_expressibility(
        named, [row["key"] for row in gallery if row.get("key")], ledger_rows, log=log
    )
    record = {
        "schema": SCHEMA,
        "taken_at": _now(),
        "store": str(store_root(store)),
        "regime": recipes_module.CANDIDATE_REGIME.spelled,
        "regime_is": "every score in this readout was read at candidate geometry, which is "
        "the regime the ledger's sidecar and both heads already stand at. Nothing was "
        "scored at label geometry and rerender.rescore was not touched",
        "population": {
            "classes": [int(name) for name in classes],
            "derived_recipes": len(every),
            "in_the_population": len(derived),
            "is": "the renders, the scores, the bars, the places and the prune are over "
            "the population; `expressibility` below is over the WHOLE derivation",
        },
        "verdicts_read": verdicts,
        "recipes_scored": len(scored),
        "per_label_class": distributions,
        "bars": {
            "render_judge": "each row's own ROUTED mode's headroom.bars rule",
            "default": table["default"],
            "fallback": table["fallback"],
            "on_fallback": table["on_fallback"],
            "fine": {"column": "p_fine(>=4)", "at": fine_bar, "from": "solve.DEFAULT_FINE_BAR"},
        },
        "label_4": {
            "rows": len(fours),
            "clears_the_render_judge_bar": len(cleared["judge"]),
            "clears_the_fine_bar": len(cleared["fine"]),
            "clears_both": len(cleared["both"]),
        },
        "places": places,
        "byte_identity": identity,
        "expressibility": reach,
        "fine_by_expressibility": fine_by_expressibility(derived, scored, log=log),
        "prune": prune,
        "prune_label_4": prune_fours,
        "seconds": round(time.time() - began, 1),
    }
    _write_json(_path(store, READOUT_NAME), record)
    log(
        f"[readout] {len(fours):,} label-4 row(s): {len(cleared['judge']):,} clear the judge, "
        f"{len(cleared['fine']):,} the fine bar, {len(cleared['both']):,} both; "
        f"{places['at_a_place_the_gallery_does_not_hold']:,} of those stand where {named} "
        f"does not"
    )
    return record


def fine_by_expressibility(derived: dict, scored: dict, log=print) -> dict:
    """`p_fine` for the recipes the candidate path can produce against those it cannot.

    The cross-tab the readout was missing, and it needs no render: `expressibility`
    already says which side of the line every derived recipe falls on, and `score`
    already read both heads over the population. Split by human class as well,
    because the question is not "are the inexpressible ones different" but **is the
    inexpressible half worth chasing** — and only a class the humans called good can
    answer that. A palette knob the roster could grow to take is worth growing
    toward if the pictures behind it score; if they score like the rest, the whole
    inexpressible half is a curiosity rather than a supply gap.

    Over the **population** and not the whole derivation, because a score is what
    this reads and only the population has one.
    """
    seats: dict = {}
    for key, row in derived.items():
        reading = scored.get(key)
        if reading is None:
            continue
        side = "expressible" if row["plain_candidate_recipe"] else "not_expressible"
        for label in row["labels"]:
            name = f"{label['head']}/{label['score']}"
            seats.setdefault(name, {}).setdefault(side, []).append(float(reading["fine"]["p_ge4"]))
    out: dict = {}
    for name in sorted(seats):
        out[name] = {
            side: {"n": len(values), **_quantiles(values)}
            for side, values in sorted(seats[name].items())
        }
    both = {"expressible": [], "not_expressible": []}
    for held in seats.values():
        for side, values in held.items():
            both[side].extend(values)
    out["all_classes"] = {
        side: {"n": len(values), **_quantiles(values)} for side, values in sorted(both.items())
    }
    log(
        f"[fine-by-reach] {len(both['expressible']):,} expressible against "
        f"{len(both['not_expressible']):,} not, over {len(scored):,} scored row(s)"
    )
    out["is"] = (
        "p_fine(>=4) at candidate geometry, split by whether the candidate path can "
        "produce the recipe at all — `expressibility`'s own line. A verdict is counted "
        "under its own class, so a recipe carrying two verdicts is in two rows"
    )
    return out


#: What a recipe is outside the candidate path **for**. A recipe can be outside on
#: both counts at once and the three names are exclusive, so the cause block adds
#: up to the inexpressible set exactly.
PALETTE_ONLY, CURVE_ONLY, BOTH = "palette_knobs", "log_field_read", "both"


def expressibility(derived: dict, cyclic=None, log=print) -> dict:
    """Which judged recipes the candidate path could produce, cross-tabbed and explained.

    **The most decision-relevant thing this leg makes**, and the readout carries it
    for that reason. The candidate path spends `colorize.CURVE` and
    `finished.recipe(mirror=colormap not in cyclic)` at every attempt; a label row
    that names anything else is a picture the pipeline cannot draw at all, so its
    absence from the pool is not a supply gap somebody could mine and close — it is
    a statement about what the pipeline is able to make.

    Three questions, and they are separate:

    * **against the human label** — a class the path cannot express is a class the
      pool cannot hold however much of it is rendered, and the label-4 count is the
      one that decides anything;
    * **what puts a recipe outside** — the palette knobs, the `log` field read, or
      both, exclusive so the three add to the set; and for the palette group, the
      *values actually used*, so it is visible whether the corpus sits at a handful
      of settings the path could grow to take or spreads across a continuum;
    * a continuous knob is reported as a distribution and a discrete one as a
      count, because "gamma moves" and "gamma takes these three values" are
      different findings and one shape cannot say both.

    `cyclic` is the set of maps production does not fold — [`colorize.cyclic`]
    unsaid. A **parameter** rather than an unconditional read, for the reason
    [`solve.pool`]'s `spirals` is one: a store reached from inside production code
    is a store a test cannot redirect, and every guard here builds three synthetic
    rows and would otherwise sweep the real colormap library to do it.
    """
    from fractal_wallpapers.curation import colorize

    # Read once and not per row. `palette_sets.cyclic` parses every tracked
    # colormap document on every call, so asking it inside the loop turns a second
    # of arithmetic into a quarter of an hour of JSON — the same mistake
    # `_shared_field`'s `_CYCLIC` module global exists to avoid.
    cyclic = colorize.cyclic() if cyclic is None else set(cyclic)
    by_class: dict = {}
    by_store: dict = {}
    label_4_outside = {"smooth_render": 0, "strange_render": 0}
    causes = {PALETTE_ONLY: 0, CURVE_ONLY: 0, BOTH: 0}
    knobs: dict = {}
    outside = 0
    for row in derived.values():
        plain = bool(row["plain_candidate_recipe"])
        for label in row["labels"]:
            name = f"{label['head']}/{label['score']}"
            seat = by_class.setdefault(name, {"expressible": 0, "not_expressible": 0})
            seat["expressible" if plain else "not_expressible"] += 1
            store = by_store.setdefault(
                str(label["head"]), {"expressible": 0, "not_expressible": 0}
            )
            store["expressible" if plain else "not_expressible"] += 1
            if not plain and int(label["score"]) == 4:
                label_4_outside[str(label["head"])] += 1
        if plain:
            continue
        outside += 1
        recipe = row["recipe"]
        wanted = finished.recipe(mirror=str(recipe["colormap"]) not in cyclic)
        moved = {
            knob: recipe["palette"][knob]
            for knob in wanted
            if recipe["palette"].get(knob) != wanted[knob]
        }
        curved = str(recipe["curve"]) != colorize.CURVE
        causes[BOTH if (moved and curved) else (CURVE_ONLY if curved else PALETTE_ONLY)] += 1
        for knob, value in moved.items():
            held = knobs.setdefault(knob, {"recipes": 0, "values": {}})
            held["recipes"] += 1
            spelled = json.dumps(value, sort_keys=True)
            held["values"][spelled] = held["values"].get(spelled, 0) + 1

    log(
        f"[expressibility] {outside:,} of {len(derived):,} recipe(s) the candidate path "
        f"cannot produce; {sum(label_4_outside.values()):,} of them carry a human 4"
    )
    return {
        "expressible": len(derived) - outside,
        "not_expressible": outside,
        "expressible_is": (
            "the row's curve is colorize.CURVE and its palette is "
            "finished.recipe(mirror=colormap not in cyclic) — what every candidate leg "
            "spends. A recipe outside it is one no mine could ever draw"
        ),
        "by_label_class": dict(sorted(by_class.items())),
        "by_store": dict(sorted(by_store.items())),
        "label_4_the_candidate_path_cannot_produce": {
            **label_4_outside,
            "total": sum(label_4_outside.values()),
        },
        "what_puts_a_recipe_outside": causes,
        "causes_are_exclusive": "a recipe on both counts is `both` and never in either "
        "single bucket, so the three add to not_expressible",
        "palette_knobs": {knob: _knob_shape(knob, held) for knob, held in sorted(knobs.items())},
    }


#: The palette knobs that take a number and are read as a distribution. The other
#: four are flags or small objects and are read as counts: `gamma` spreading over
#: two hundred values and `mirror` taking two are different findings, and one shape
#: cannot state both.
CONTINUOUS_KNOBS = ("gamma", "cycles", "phase")


def _knob_shape(knob: str, held: dict) -> dict:
    """One knob's recipes and the values it actually took."""
    out = {"recipes": held["recipes"], "distinct_values": len(held["values"])}
    ranked = sorted(held["values"].items(), key=lambda item: (-item[1], item[0]))
    if knob in CONTINUOUS_KNOBS:
        spread = []
        for spelled, count in held["values"].items():
            spread.extend([float(json.loads(spelled))] * count)
        out["distribution"] = _quantiles(spread)
    out["most_used"] = {spelled: count for spelled, count in ranked[:12]}
    return out


def seat_expressibility(stamp: str, seats: list, ledger_rows: list, cyclic=None, log=print) -> dict:
    """Whether the recipes a recorded gallery seats are ones the candidate path makes.

    It should be **all of them** — every seat is a candidate ledger row and every
    ledger row was drawn by a leg that spends `colorize.CURVE` and the plain
    palette. Asserting it rather than assuming it is the point: this is the control
    on [`expressibility`], and a seat outside would mean a row reached the pool by
    some path nobody has written down.
    """
    from fractal_wallpapers.curation import colorize

    # Once, and a parameter, both for [`expressibility`]'s reasons.
    cyclic = colorize.cyclic() if cyclic is None else set(cyclic)
    held = {str(row["key"]): row for row in ledger_rows}
    inside, outside, unknown = 0, [], 0
    for key in seats:
        row = held.get(str(key))
        recipe = None if row is None else (row.get("recipe") or {})
        if not recipe or recipe.get("palette") is None:
            unknown += 1
            continue
        colormap = str(recipe["colormap"])
        wanted = finished.recipe(mirror=colormap not in cyclic)
        if str(recipe["curve"]) == colorize.CURVE and recipe["palette"] == wanted:
            inside += 1
        else:
            outside.append({"key": str(key), "curve": recipe["curve"], "colormap": colormap})
    log(
        f"[seats] {inside:,} of {len(seats):,} seat(s) in {stamp} stand at a recipe the "
        f"candidate path can express; {len(outside):,} do not"
    )
    return {
        "stamp": stamp,
        "seats": len(seats),
        "expressible": inside,
        "not_expressible": len(outside),
        "no_ledger_row": unknown,
        "the_ones_that_are_not": outside[:20],
        "expected": "all of them — every seat is a ledger row and every ledger row was "
        "drawn by a leg spending colorize.CURVE and the plain palette",
    }


def _quantiles(values: list) -> dict:
    """The shape of one column, in the numbers a reader of a distribution wants."""
    if not values:
        return {"n": 0}
    ordered = sorted(values)

    def at(share: float) -> float:
        return round(ordered[min(len(ordered) - 1, int(share * len(ordered)))], 4)

    return {
        "n": len(ordered),
        "min": round(ordered[0], 4),
        "p10": at(0.10),
        "median": round(statistics.median(ordered), 4),
        "p90": at(0.90),
        "max": round(ordered[-1], 4),
        "mean": round(statistics.fmean(ordered), 4),
    }


def _price_the_prune(
    arriving_keys,
    derived,
    scored,
    staged,
    ledger_rows,
    ledger_scores,
    flat_cache: dict | None = None,
    log=print,
) -> dict:
    """What [`retention.decide`] would do to a set of staged rows on arrival.

    Takes the population it prices rather than assuming one. It was the label-4
    rows alone, which priced the wrong thing: a merge submits every **scored** row,
    and the pairs those extra rows land in are pairs the label-4 pricing never
    reached at all — so the figure it gave was a floor under the real one and read
    like the whole of it. Both are recorded now, the whole population first.

    `flat_cache` is `{key: flat fraction}` shared across calls, because the staged
    side of this reads a **picture** per row and two pricings over nested
    populations would read the smaller one's pictures twice.

    Restricted to the `(location, mode+settings)` pairs those rows land in,
    because the decision is per pair and no pair they do not reach can move. The
    pair itself is [`retention._pair_of`] and not a second spelling of it: the
    mode half is `colorize.spelled`, and a rule written twice is a rule that
    disagrees with itself the first time either copy is edited.

    Both sides are ranked on the **shipped rank key** — the one the prune ranks on,
    through `sweep._prune_ranks` — and the staged rows' features come off their own
    staged readings plus the flatness of their own staged pictures, so nothing is
    imputed. A row the key cannot read carries no value and `decide` ranks it last
    within its pair, which is the pessimistic direction and `curation.solve`'s own
    convention for the case.
    """
    from fractal_wallpapers.curation import candidate_ledger, flatness, intake, rank_key, retention

    keep = retention.keep_per_pair()
    incoming = {
        key: retention._pair_of(
            {
                "location": {"key": derived[key]["location"]},
                "recipe": {
                    "mode": derived[key]["mode"],
                    "mode_params": derived[key].get("mode_params") or {},
                },
            }
        )
        for key in arriving_keys
    }
    pairs = set(incoming.values())
    held = []
    for row in ledger_rows:
        stub = {
            "key": str(row["key"]),
            "location": {"key": str((row.get("location") or {}).get("key"))},
            "recipe": {
                "mode": str((row.get("recipe") or {}).get("mode")),
                "mode_params": (row.get("recipe") or {}).get("mode_params") or {},
            },
        }
        if retention._pair_of(stub) in pairs:
            held.append(stub)
    log(f"[prune-price] {len(pairs):,} pair(s) reached, {len(held):,} ledger row(s) in them")

    artifact = candidate_ledger.live_artifact()
    readings = {
        str(row["recipe_key"]): row
        for row in ledger_scores
        if str(row.get("judge_artifact")) == artifact
    }
    flat = flatness.by_recipe(flatness.read())
    locations = intake.read_scores()
    model = rank_key.load()
    values: dict = {}
    ledger_gaps = {"no_reading": 0, "no_flatness": 0}
    for stub in held:
        reading = readings.get(stub["key"])
        held_flat = flat.get(stub["key"])
        if reading is None:
            ledger_gaps["no_reading"] += 1
            continue
        if held_flat is None:
            ledger_gaps["no_flatness"] += 1
            continue
        values[stub["key"]] = model.score(
            _features(
                locations.get(stub["location"]["key"]) or {},
                float(reading.get("p_ge3") or 0.0),
                float(reading.get("p_ge4") or 0.0),
                float(held_flat),
                rank_key,
                flatness,
            )
        )

    if flat_cache is None:
        flat_cache = {}
    arriving, staged_gaps = [], {"no_picture": 0, "no_flatness": 0}
    for key in arriving_keys:
        row, reading = derived[key], scored[key]
        arriving.append(
            {
                "key": key,
                "location": {"key": row["location"]},
                "recipe": {"mode": row["mode"], "mode_params": row.get("mode_params") or {}},
            }
        )
        picture = (staged.get(key) or {}).get("picture")
        if not picture or not Path(picture).is_file():
            staged_gaps["no_picture"] += 1
            continue
        if key not in flat_cache:
            flat_cache[key] = flatness.fraction(Path(picture))
        held_flat = flat_cache[key]
        if held_flat is None:
            staged_gaps["no_flatness"] += 1
            continue
        values[key] = model.score(
            _features(
                locations.get(row["location"]) or {},
                float(reading["judge"]["p_ge3"]),
                float(reading["judge"]["p_ge4"]),
                float(held_flat),
                rank_key,
                flatness,
            )
        )

    before = retention.decide(held, values, keep=keep)
    after = retention.decide(held + arriving, values, keep=keep)
    dropped = [key for key in incoming if after.get(key) == retention.DROPPED]
    displaced = [
        stub["key"]
        for stub in held
        if before.get(stub["key"]) == retention.RANKED
        and after.get(stub["key"]) == retention.DROPPED
    ]
    at_pairs: dict = {}
    for key in dropped:
        place, mode = incoming[key]
        at_pairs[f"{mode} @ {place}"] = at_pairs.get(f"{mode} @ {place}", 0) + 1
    return {
        "keep_per_pair": keep,
        "staged_rows_priced": len(arriving),
        "pairs_reached": len(pairs),
        "ledger_rows_in_those_pairs": len(held),
        "ledger_rank_gaps": ledger_gaps,
        "staged_rank_gaps": staged_gaps,
        "pruned_on_arrival": len(dropped),
        "survives_the_prune": len(arriving) - len(dropped),
        "ledger_rows_it_would_displace": len(displaced),
        "pairs_a_staged_row_is_pruned_at": len({incoming[key] for key in dropped}),
        "pruned_at": dict(sorted(at_pairs.items(), key=lambda item: (-item[1], item[0]))[:40]),
        "priced_and_not_merged": True,
    }


def _byte_identity(derived: dict, staged: dict, ledger_rows: list, log=print) -> dict:
    """Is a staged picture at an overlapping key the SAME FILE the ledger holds?

    The overlap figure [`derive`] reports is a claim about identity: a derived key
    equal to a ledger key asserts the two name one picture. This proves it on the
    pixels rather than on the digest — every staged row whose key the ledger also
    holds, hashed against the ledger's own file.

    A mismatch would mean the recipe key is not the whole of what decides a picture,
    which is the one failure `recipes.Recipe.pixels` exists to make impossible and
    the one worth a sweep rather than a sample. It covers only what has been
    rendered, so the count it reached is reported beside the verdict.
    """
    import hashlib

    from fractal_wallpapers.curation import candidate_ledger
    from fractal_wallpapers.paths import Tiers, rehome

    tiers = Tiers.current()
    held = {str(row["key"]): row for row in ledger_rows}
    # COUNTED apart from the sample. A `len` over a list capped for the record
    # reports the cap as the finding, which is how "20 differ" can mean "at least
    # twenty and nobody looked".
    same, differ, absent = 0, 0, 0
    sample: list = []
    builds: dict = {}
    modes: dict = {}
    reached_modes: dict = {}
    for key, row in derived.items():
        if not row.get("in_the_candidate_ledger"):
            continue
        mine = (staged.get(key) or {}).get("picture")
        stored = held.get(key) or {}
        theirs = stored.get("picture")
        where = None if not theirs else rehome(str(theirs), tiers)
        if not mine or not Path(mine).is_file() or where is None or not where.is_file():
            absent += 1
            continue
        reached_modes[str(row.get("mode"))] = reached_modes.get(str(row.get("mode")), 0) + 1
        if hashlib.sha256(Path(mine).read_bytes()).hexdigest() == (
            hashlib.sha256(where.read_bytes()).hexdigest()
        ):
            same += 1
            continue
        differ += 1
        # Which engine build drew the ledger's copy. The recipe key digests what
        # the engine is TOLD and not the binary that was told it, so a row drawn by
        # an older build is the one honest way two files can share a key — which is
        # a fact about provenance rather than a hole in the key.
        build = candidate_ledger.engine_of(stored)
        builds[build] = builds.get(build, 0) + 1
        modes[str(row.get("mode"))] = modes.get(str(row.get("mode")), 0) + 1
        if len(sample) < 20:
            sample.append({"key": key, "ledger_engine": build, "mode": row.get("mode")})
    log(
        f"[byte-identity] {same:,} staged picture(s) are byte-identical to the ledger's own; "
        f"{differ:,} differ, {absent:,} not comparable"
    )
    return {
        "reached": same + differ,
        "byte_identical": same,
        "differ": differ,
        "share_identical": round(same / max(1, same + differ), 6),
        "no_picture_on_one_side": absent,
        "live_engine": candidate_ledger.live_engine(),
        "the_ledger_builds_that_differ": dict(sorted(builds.items(), key=lambda i: -i[1])),
        "the_modes_that_differ": dict(sorted(modes.items(), key=lambda i: -i[1])),
        "differ_share_of_each_mode_reached": {
            mode: round(modes.get(mode, 0) / count, 4)
            for mode, count in sorted(reached_modes.items())
            if modes.get(mode)
        },
        "modes_reached": dict(sorted(reached_modes.items(), key=lambda i: -i[1])),
        "a_sample_that_differs": sample,
        "is": "the overlap figure is an identity claim, and this proves it on pixels rather "
        "than on the digest. The recipe key digests what the engine is TOLD, not the binary "
        "that was told it, so a row drawn by an older build is the expected way two files "
        "share a key",
    }


def _features(place: dict, p_ge3: float, p_ge4: float, flat: float, rank_key, flatness) -> dict:
    """One row's four columns, spelled as [`rank_key.features_for`] spells them."""
    loc = place.get("p_ge4")
    return {
        "loc_p_ge4": rank_key.NO_LOCATION_READING if loc is None else float(loc),
        "p_ge3": float(p_ge3),
        "p_ge4": float(p_ge4),
        flatness.COLUMN: float(flat),
    }


# --------------------------------------------------------------------------- #
# the page.
# --------------------------------------------------------------------------- #
PAGE = """<!doctype html>
<meta charset="utf-8"><title>judged recipes at candidate geometry</title>
<style>
 body {{ font: 13px/1.45 system-ui, sans-serif; margin: 1.5rem;
         background: #14161a; color: #dfe3e8; }}
 h1 {{ font-size: 1.15rem; margin: 0 0 .35rem; }}
 .lede {{ max-width: 64rem; color: #9aa4b1; margin: 0 0 1.25rem; }}
 .lede b {{ color: #dfe3e8; }}
 .lede em {{ color: #d8b45a; font-style: normal; }}
 .row {{ background: #1c1f26; border-radius: 6px; margin: 0 0 1rem; overflow: hidden;
         max-width: 84rem; }}
 .pair {{ display: grid; grid-template-columns: 1fr 1fr; gap: 2px; background: #0e1013; }}
 figure {{ margin: 0; position: relative; }}
 img {{ display: block; width: 100%; }}
 figcaption {{ position: absolute; left: 0; top: 0; background: rgba(10,12,15,.78);
               padding: .15rem .45rem; font-size: .68rem; letter-spacing: .04em;
               text-transform: uppercase; color: #9aa4b1; }}
 .judged figcaption {{ color: #d8b45a; }}
 .facts {{ display: flex; flex-wrap: wrap; gap: .15rem 1.1rem; padding: .55rem .7rem .65rem; }}
 .facts span {{ white-space: nowrap; }}
 .lab {{ color: #6b7480; }}
 .key {{ font-family: ui-monospace, monospace; color: #6b7480; font-size: .72rem; }}
 .gone {{ padding: 4rem 1rem; text-align: center; color: #6b7480; }}
</style>
<h1>Judged recipes at candidate geometry</h1>
<p class="lede">{lede}</p>
{cards}
"""


def page(store=None, classes=KEPT_CLASSES, log=print) -> dict:
    """One entry per label-4 verdict, judged picture beside candidate picture.

    Sorted by `p_fine` **ascending**, so the rows the pipeline likes least come
    first — which is the direction somebody reading for disagreement wants.

    Both pictures are written beside the page at [`PAGE_WIDTH`], so the pair is a
    comparison at one display size and not a comparison of two sizes. The left
    picture is the one the verdict was cast on, at label geometry; every number in
    the caption was read at candidate geometry, off the right-hand picture, and the
    page says so.
    """
    began = time.time()
    derived, _every = _population(store, classes)
    scored = {str(row["key"]): row for row in _read_jsonl(_path(store, SCORES_NAME))}
    staged = {str(row["key"]): row for row in _read_jsonl(_path(store, RENDERS_NAME))}
    where = _path(store, READOUT_NAME)
    read = json.loads(where.read_text(encoding="utf-8")) if where.is_file() else {}

    beside = store_root(store) / PAGE_PICTURES
    beside.mkdir(parents=True, exist_ok=True)
    entries = []
    for key, row in derived.items():
        reading = scored.get(key)
        if reading is None:
            continue
        for label in row["labels"]:
            if int(label["score"]) == 4:
                entries.append((float(reading["fine"]["p_ge4"]), key, label))
    entries.sort(key=lambda item: (item[0], item[1]))
    log(f"[page] {len(entries):,} label-4 verdict(s)")

    cards, missing = [], {"judged": 0, "candidate": 0}
    for fine_score, key, label in entries:
        judged = _beside(label.get("label_picture"), beside, f"{key}.judged.jpg")
        candidate = _beside((staged.get(key) or {}).get("picture"), beside, f"{key}.candidate.jpg")
        missing["judged"] += judged is None
        missing["candidate"] += candidate is None
        cards.append(_card(key, derived[key], label, scored[key], judged, candidate, fine_score))

    page_path = _path(store, PAGE_NAME)
    page_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.write_text(
        PAGE.format(lede=_lede(len(entries), read), cards="\n".join(cards)),
        encoding="utf-8",
        newline="\n",
    )
    record = {
        "schema": SCHEMA,
        "taken_at": _now(),
        "page": str(page_path),
        "pictures": str(beside),
        "entries": len(entries),
        "missing_pictures": missing,
        "sorted_by": "p_fine ascending",
        "width": PAGE_WIDTH,
        "seconds": round(time.time() - began, 1),
    }
    log(f"[page] {len(entries):,} entr(ies) -> {page_path}")
    return record


def _lede(entries: int, read: dict) -> str:
    label4 = read.get("label_4") or {}
    fine_bar = ((read.get("bars") or {}).get("fine") or {}).get("at")
    stamp = (read.get("places") or {}).get("stamp")
    return (
        f"<b>{entries:,}</b> human <b>4</b> verdicts from both finished-render stores, each "
        f"one's recipe re-expressed at <b>{recipes_module.CANDIDATE_REGIME.spelled}</b> — "
        "geometry changed and nothing else — then rendered and read. "
        "<em>Both scores in every caption are candidate-geometry scores</em>, read off the "
        "right-hand picture. <em>The left picture is the one Matt judged</em>, at "
        "1280&times;720 ss2, reduced here so the pair sits at one display size. "
        + (
            f"<b>{label4.get('clears_the_render_judge_bar')}</b> clear their mode's "
            f"render-judge bar, <b>{label4.get('clears_the_fine_bar')}</b> the fine bar at "
            f"{fine_bar}, <b>{label4.get('clears_both')}</b> both. "
            if label4
            else ""
        )
        + "Sorted by <b>p_fine ascending</b>: the rows the pipeline likes least come first. "
        "Nothing here was merged into any store"
        + (f"; the gallery compared against is {stamp}." if stamp else ".")
    )


def _beside(source, directory: Path, name: str) -> str | None:
    """One picture copied beside the page at [`PAGE_WIDTH`]. Returns its relative name."""
    from PIL import Image

    if not source:
        return None
    where = Path(source)
    if not where.is_file():
        return None
    out = directory / name
    if not out.is_file():
        with Image.open(where) as opened:
            image = opened.convert("RGB")
            if image.width != PAGE_WIDTH:
                height = max(1, round(image.height * PAGE_WIDTH / image.width))
                image = image.resize((PAGE_WIDTH, height), Image.LANCZOS)
            image.save(out, "JPEG", quality=PAGE_QUALITY)
    return f"{PAGE_PICTURES}/{name}"


def _card(key, row, label, reading, judged, candidate, fine_score) -> str:
    facts = [
        f'<span><span class="lab">human</span> <b>{label["score"]}</b> '
        f"({label['head']} &middot; {label.get('batch')})</span>",
        f'<span><span class="lab">p_ge4</span> {float(reading["judge"]["p_ge4"]):.4f}</span>',
        f'<span><span class="lab">p_fine</span> {float(fine_score):.4f}</span>',
        f'<span><span class="lab">mode</span> {row["mode"]}</span>',
        f'<span><span class="lab">palette</span> {row["recipe"]["colormap"]}</span>',
        f'<span><span class="lab">place</span> <span class="key">{row["location"]}</span></span>',
        f'<span class="key">{key}</span>',
    ]
    left = (
        f'<figure class="judged"><img loading="lazy" src="{judged}">'
        "<figcaption>judged &middot; 1280&times;720 ss2</figcaption></figure>"
        if judged
        else '<figure class="judged"><div class="gone">no judged picture</div></figure>'
    )
    right = (
        f'<figure><img loading="lazy" src="{candidate}">'
        "<figcaption>candidate &middot; 640&times;360 ss2</figcaption></figure>"
        if candidate
        else '<figure><div class="gone">no candidate picture</div></figure>'
    )
    return (
        f'<div class="row"><div class="pair">{left}{right}</div>'
        f'<div class="facts">{"".join(facts)}</div></div>'
    )


# --------------------------------------------------------------------------- #
# merge.
# --------------------------------------------------------------------------- #
def merge(store=None, log=print) -> dict:
    """This store's scored rows into the pool, through THE door. Writes `merge.json`.

    Every scored row is *offered* and the ones the pool already holds are **not
    submitted**, which is the same statement twice rather than two rules:
    [`records.upsert_file`] replaces a stored row outright — it carries a human
    rejection across and nothing else — so submitting a row at a key the ledger
    already holds would overwrite that row's picture, its provenance, its `hunt`
    block, its colour and its engine field with this leg's. That is a rewrite, and
    a leg whose whole claim is *these are new candidates* has no business making
    one. The overlap is not small: 2,314 of the 5,329 scored rows of the
    2026-09-08 store stand at keys the pool already holds, and 2,200 of them are
    byte-identical to the ledger's own file anyway — see [`_byte_identity`], which
    is the measurement that makes leaving them out cheap rather than a loss.

    ## What a row needs that the staging store does not carry

    * **A colour block.** [`solve.pool`] reads `colour.cells` and
      `colour.families`, and the ceiling and every colour rule act on them; a row
      with none is a row that escapes the cell allowance. Read here, once per
      merged picture, through [`palettes.dominance.of_picture`] — the same call
      [`hunt`] makes at render time.
    * **A home under `artifacts/`.** See [`POOL_SUBTREE`]: the pictures move out of
      the store before the row that names them is written.
    * **An engine build.** The staging store records none, so this asks
      [`candidate_ledger.live_engine`] and stamps it only where the build still
      reads what the readout recorded for the leg that drew the pictures. A
      different build now means the field cannot be honest, and
      [`candidate_ledger.UNKNOWN_ENGINE`] is what the whole backfilled pool
      already carries.

    `texture_flat` is carried from the staged recipe row, which took it from
    [`coloring.texture_flat`]'s register rather than from an engine report — the
    render stage did not keep the report. It is recorded as such on the record: the
    register's reading is a measurement where it has one and `False` where it does
    not, and `False` is what every reader concluded before the flag existed.
    """
    from fractal_wallpapers.curation import candidate_ledger, hunt
    from fractal_wallpapers.palettes import dominance
    from fractal_wallpapers.paths import tracked_name

    began = time.time()
    derived = {str(row["key"]): row for row in _read_jsonl(_path(store, RECIPES_NAME))}
    staged = {str(row["key"]): row for row in _read_jsonl(_path(store, RENDERS_NAME))}
    scored = {str(row["key"]): row for row in _read_jsonl(_path(store, SCORES_NAME))}
    if not scored:
        raise MigrationError(
            f"{tracked_name(_path(store, SCORES_NAME))} holds no row, so nothing here has a "
            f"score and nothing may merge. Run the score stage first."
        )

    build, why = _build_for(store)
    log(f"[merge] the pictures are stamped {build!r}: {why}")

    ledger_keys = {str(row["key"]) for row in candidate_ledger.stream()}
    artifact = candidate_ledger.live_artifact()
    regime = recipes_module.CANDIDATE_REGIME.spelled
    sidecar = {
        str(row["key"]) for row in candidate_ledger.stream_scores()
    }  # keyed `<recipe>|<artifact>|<regime>`
    offered = sorted(scored)
    standing = [key for key in offered if key in ledger_keys]
    submitting = [key for key in offered if key not in ledger_keys]
    log(
        f"[merge] {len(offered):,} scored row(s) offered; {len(standing):,} stand at a key "
        f"the pool already holds and are NOT submitted; {len(submitting):,} are new"
    )

    where = merged_pictures_dir(store)
    where.mkdir(parents=True, exist_ok=True)
    rows, scores, moved, absent, no_colour = [], [], 0, [], 0
    for key in submitting:
        held = staged.get(key) or {}
        picture = Path(held.get("picture") or "")
        landing = where / picture.name
        if not landing.is_file():
            if not picture.is_file():
                absent.append(key)
                continue
            picture.replace(landing)
            moved += 1
            # The levelled stop list beside it, where the operator acted. It is
            # part of the record of how the picture was made and a candidate leg
            # keeps it beside the picture, so it moves with it or it is orphaned.
            curves = picture.parent / f"{picture.stem}.leveled"
            if curves.is_dir() and not (where / curves.name).exists():
                curves.replace(where / curves.name)
        recipe = recipes_module.of_record(derived[key]["recipe"])
        try:
            colour = candidate_ledger.colour_block(dominance.of_picture(landing))
        except Exception:  # noqa: BLE001 — a picture the reading refuses is a counted fact
            colour, _ = None, no_colour
            no_colour += 1
        source = {
            "key": key,
            "run": leg_of(store),
            "candidate": key,
            "location": {
                "key": derived[key]["location"],
                "partition": derived[key].get("partition"),
            },
        }
        row = candidate_ledger.row(
            recipe=recipe,
            key=key,
            source=source,
            colour=colour,
            picture=tracked_name(landing),
            texture_flat=bool(derived[key].get("texture_flat")),
            engine=build,
        )
        row["hunt"] = candidate_ledger.hunt_block({"seconds": held.get("seconds")})
        rows.append(row)
        reading = scored[key]
        if f"{key}|{artifact}|{regime}" in sidecar:
            continue
        scores.append(
            candidate_ledger.score_row(
                key=key,
                artifact=artifact,
                regime=regime,
                # The sidecar's `head` is the label store's KIND — `smooth_render`
                # or `strange_render` — and never a mode. Through [`hunt.kind_of`]
                # off the recipe's own mode and the staged row's `texture_flat`,
                # which is the same call every candidate leg's score row is built
                # with, rather than the routed mode this store also carries.
                head=hunt.kind_of(str(derived[key]["mode"]), bool(derived[key]["texture_flat"])),
                read=reading["judge"],
                source=source,
            )
        )
    log(
        f"[merge] {len(rows):,} row(s) built, {moved:,} picture(s) moved into "
        f"{tracked_name(where)}, {len(scores):,} score row(s) the sidecar lacks"
    )
    if not rows:
        raise MigrationError(
            "every scored row of this store already stands in the pool, so a merge would "
            "only rewrite rows it does not own. Nothing was written."
        )

    written = candidate_ledger.merge(rows, scores, log=log)
    record = {
        "schema": SCHEMA,
        "taken_at": _now(),
        "store": str(store_root(store)),
        "leg": leg_of(store),
        "pictures": tracked_name(where),
        "engine": {"stamped": build, "why": why},
        "offered": len(offered),
        "already_in_the_pool": len(standing),
        "submitted": len(rows),
        "not_submitted_is": (
            "a key the pool already holds is left alone: records.upsert_file REPLACES a "
            "stored row, so submitting one would rewrite a row this leg does not own"
        ),
        "pictures_moved": moved,
        "pictures_absent": absent,
        "colour_refused": no_colour,
        "score_rows_written": len(scores),
        "score_rows_the_sidecar_already_had": len(rows) - len(scores),
        "texture_flat_from": (
            "the staged recipe row, which read coloring.texture_flat's register — the "
            "render stage kept no engine report"
        ),
        "ledger": written["ledger"],
        "scores": written["scores"],
        "recorded": written["recorded"],
        "repeat_draws": written["repeat_draws"],
        "flatness": written["flatness"],
        "pruned": written["pruned"],
        "locations_touched": len({str(row["location"]["key"]) for row in rows}),
        "seconds": round(time.time() - began, 1),
    }
    _write_json(_path(store, MERGE_NAME), record)
    log(
        f"[merge] merged {len(rows):,} row(s): the ledger holds "
        f"{written['ledger']['rows']:,} recipes, {written['ledger']['new']:,} of them new"
    )
    return record


def _build_for(store) -> tuple[str, str]:
    """Which engine build this store's pictures may honestly be stamped with.

    The staging store records none — the render stage kept no fingerprint — so the
    only evidence is [`readout`]'s, which ran after the renders and wrote the build
    live at that moment. A build that still reads the same is the build that drew
    them; anything else and the field cannot be answered, which is what
    [`candidate_ledger.UNKNOWN_ENGINE`] is for and what the whole backfilled pool
    already carries.
    """
    from fractal_wallpapers.curation import candidate_ledger

    live = str(candidate_ledger.live_engine())
    path = _path(store, READOUT_NAME)
    if not path.is_file():
        return candidate_ledger.UNKNOWN_ENGINE, (
            f"{path.name} is not there, so nothing says which build drew these pictures"
        )
    recorded = str(
        (json.loads(path.read_text(encoding="utf-8")).get("byte_identity") or {}).get("live_engine")
    )
    if recorded != live:
        return candidate_ledger.UNKNOWN_ENGINE, (
            f"the readout recorded {recorded!r} and the live build is {live!r}, so the build "
            f"that drew these pictures is no longer the one this box would ask"
        )
    return live, f"the readout recorded {recorded!r} and the live build still reads it"


__all__ = [
    "DEFAULT_STORE",
    "PAGE_NAME",
    "PAGE_PICTURES",
    "PAGE_WIDTH",
    "PICTURES_NAME",
    "READOUT_NAME",
    "RECIPES_NAME",
    "RENDERS_NAME",
    "RENDER_CHUNK",
    "SCHEMA",
    "SCORES_NAME",
    "KEPT_CLASSES",
    "MERGE_NAME",
    "POOL_SUBTREE",
    "SCORE_BATCH",
    "WORKERS",
    "BOTH",
    "CONTINUOUS_KNOBS",
    "CURVE_ONLY",
    "PALETTE_ONLY",
    "MigrationError",
    "census",
    "derive",
    "expressibility",
    "fine_by_expressibility",
    "in_population",
    "label_picture",
    "leg_of",
    "merge",
    "merged_pictures_dir",
    "page",
    "readout",
    "recipe_of",
    "render",
    "render_chunk",
    "score",
    "seat_expressibility",
    "store_root",
]
