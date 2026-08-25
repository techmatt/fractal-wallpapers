"""Manufacturing colour: forcing rare swatches onto good places, and cutting the sheet.

Every other population in this project is *found*. A walk finds places, a run
colours whatever the palette head picks, and the colour a finished wallpaper ends
up holding is a by-product of both. [`expressed`] measured what that produces:
eight of the fifty-two swatches appear on **none** of the 246 finished pictures
and twenty-one appear on five or fewer, while the library holds 38 to 258 maps
that can reach each of those twenty-one. The gap is not capability. Nothing has
ever *asked* for those colours.

This module asks. It is the only population here that is manufactured rather than
observed, and everything about it follows from that one fact:

```text
a row is        a location that is already known good, coloured through a map
                CHOSEN because it carries a target swatch, in a mode drawn the
                way production draws one
the batch is    train-side and biased, by construction, and registered as such
                BEFORE a pixel is made
what it buys    human verdicts on pictures the pool would never have produced,
                so the render judge can be corrected where it has seen nothing
what it is not  a rate about anything. The population is enriched twice over —
                by location quality and by a passing score — so a correction
                rate off this sheet is a CEILING and never a base rate
```

## A map's ramp does not predict what a picture holds, so nothing is selected on it

[`palette_coverage`] reads capability off a fixed probe panel: *could this map
ever put that swatch on a real share of some picture*. It is a max over sixteen
cells and it is the right instrument for a library. It is a poor predictor of one
frame — the median map that reaches a swatch at all reaches it on three to six of
the sixteen — so a plan drawn off the panel and shipped unmeasured would be a
sheet of pictures nobody checked the colour of.

So the order here is **build, measure, then select**, and the panel is used for
one thing only: deciding which maps are worth *attempting* for a swatch. What
fills a quota is the share the codebook reads off the rendered picture.

## Two geometries, and only one of them decides anything

An attempt is screened at candidate geometry — `640x360 x2`, where both release
floors were fitted and where `rescore` reads the pool — because that is a quarter
of the cost of the picture a person will judge. Nothing is *selected* there. The
best surviving attempt at each location is then re-rendered at the sheet's own
`1280x720 x2`, censused again and judged again, and **both cuts act on that
second reading**: a new map can wreck a picture an old map carried, and the score
that matters is the one on the picture that will be on the sheet.

The candidate reading is kept on every row anyway, because the difference between
the two is a measurement this project wants and has never had at this pair of
sizes — [`drift`] reports it.

## The knob draw, which is the diagnostic's own premise and is not true

The palette pass has seven knobs and **production draws none of them**. Every
colorize this repository makes is [`labeling.finished.recipe`] at the identity —
gamma 1.0, cycles 1.0, phase 0.0, no reverse, the value transfer, no rolloff —
with `mirror` read off the map's cyclicity by [`models.palette_sets.recipe_for`]
rather than sampled. That is what this module does too, because the sheet has to
be about the colour and not about a knob draw production would never make.

It matters for reading the hit rate. A palette free to cycle and shift phase can
put its colours somewhere on almost any field; a palette pinned at the identity
can only put them where the field's own stretch happens to land. Every one of the
two hundred maps in the `rare-colors-2026-08` drop is cyclic, so every new-map row
here is `mirror=False` and the whole recipe is the identity — the draw varies
**nothing**. The contrast arm's library maps are mostly sequential and therefore
mostly folded, which is the only recipe difference anywhere in the batch.

## The contrast arm, and why ten percent of the rows are not new maps

Without it every finding is confounded. A correction on a row drawn through a map
from the drop could be about the colour, or about the drop — two hundred maps
authored in one run by one generator against one brief, which is exactly the kind
of thing a judge can have a blanket opinion about. So roughly a tenth of the rows
force the *same* target swatches through maps that were already in the library
before the drop, and land in their own registered batch so the arm is separable
from the store alone.
"""

from __future__ import annotations

import json
import random
import shutil
from functools import lru_cache
from pathlib import Path

#: The two kinds, which are the two label stores and the two sheets. Named
#: through `budget` so the roster of modes each one owns has one owner, and
#: `SMOOTH` is re-exported rather than restated for the same reason.
from fractal_wallpapers.curation.budget import KINDS, SMOOTH
from fractal_wallpapers.palettes import codebook

#: The artifact's schema, carried from the first row.
SCHEMA = 1

#: How many rows each kind's sheet holds.
ROWS_PER_KIND = 250

#: Roughly what share of a kind's rows are the contrast arm — the same target
#: swatches forced through maps the library already held. Rounded to whole rows
#: per swatch, so the realized share moves a little and the record says what it was.
CONTRAST_SHARE = 0.10

#: How many colorize attempts one location is given. For the strange kind they
#: are split over [`STRANGE_MODES`] modes, so the mode draw is production's own.
ATTEMPTS_PER_LOCATION = 4

#: How many modes a strange location is tried in — `budget.MODES_PER_LOCATION`'s
#: value for that kind, drawn without replacement off the location the same way.
STRANGE_MODES = 2

#: A target swatch is REACHED when it holds at least this share of a picture's
#: pixels. [`codebook.SHARE_THRESHOLDS`]' own "present" height, and the one
#: `expressed` counts coverage at, so three modules mean one thing by the word.
REACHED = 0.10

#: What a candidate must show at candidate geometry to be worth confirming at
#: sheet geometry. Measured rather than chosen — `expressed.SCREEN`, under which
#: not one of the 788 released (picture, swatch) cells at 10% falls.
SCREEN_SHARE = 0.06

#: The tier a picture must reach to be served. "At least a 2" on the render
#: judge's own scale, read as its first unconditional cutpoint.
SCREEN_TIER = 2
SCREEN_PROBABILITY = 0.50

#: What the candidate render has to say before the sheet render is paid for.
#: Half the acting height on purpose: this decides what is worth *measuring*
#: again at four times the pixels, and a pre-filter set at the acting height
#: would be the acting cut taken at the geometry it is not taken at.
CONFIRM_PROBABILITY = 0.25

#: The panel share above which a map is worth *attempting* for a swatch. The
#: capability read's own present threshold; it decides nothing about a row.
CARRIER_FLOOR = 0.10

#: At most this many of a sheet's rows come through one colormap. Four rather
#: than a share, because the binding case is the swatch with the fewest carriers
#: — `light_vivid_teal` has eleven in the drop — and 11 x 4 still covers the two
#: kinds' quotas for it.
ROWS_PER_MAP = 4

#: Where a candidate is screened. Both release floors were fitted here and
#: `rescore` reads the whole pool here.
CANDIDATE_RESOLUTION = (640, 360)
CANDIDATE_SUPERSAMPLE = 2

#: What a person judges. The geometry both finished-render corpora were collected
#: at, which is what `labeling.sheets` renders a finished unit at.
SHEET_RESOLUTION = (1280, 720)
SHEET_SUPERSAMPLE = 2

#: The batch a new-map row lands in, and the contrast arm's own beside it. The
#: stamp every row carries: a census or a preference read separates forced supply
#: from free supply by this name and by nothing else.
BATCH = "manufactured_rare_colors"
CONTRAST_BATCH = "manufactured_rare_colors_contrast"

#: The seed every draw here is taken under, so the plan is a function of the
#: stores and this file rather than of a shuffle.
SEED = 20260824

#: Which tier a row's location came from. The first is preferred and the second
#: is the extension a short quota reaches for; every row says which it is.
TIERS = ("human_q3", "admitted")


class ManufactureError(RuntimeError):
    """The batch cannot be planned, built or selected over the stores as they are."""


# --------------------------------------------------------------------------- #
# Where it lands.
# --------------------------------------------------------------------------- #
def work_dir(batch: str = BATCH) -> Path:
    """Everything this batch builds. Ignored, regenerable, and large."""
    from fractal_wallpapers.paths import under

    return under("curation", "manufacture", batch)


def plan_path(batch: str = BATCH) -> Path:
    """The knobs, the targets, the quotas and the populations they were drawn from."""
    return work_dir(batch) / "plan.json"


def attempts_path(batch: str = BATCH) -> Path:
    """One row per colorize this batch intends: a place, a mode and a map."""
    return work_dir(batch) / "attempts.jsonl"


def screened_path(batch: str = BATCH) -> Path:
    """Every attempt, measured and judged at candidate geometry."""
    return work_dir(batch) / "screened.jsonl"


def confirmed_path(batch: str = BATCH) -> Path:
    """The best surviving attempt at each location, measured and judged at sheet geometry."""
    return work_dir(batch) / "confirmed.jsonl"


def sheet_plan_path(kind: str, batch: str = BATCH) -> Path:
    """One kind's selected rows, in the shape `label build --from-plan` reads."""
    return work_dir(batch) / f"{kind}.plan.jsonl"


def record_dir(batch: str = BATCH) -> Path:
    """The tracked record: what was manufactured, and out of what."""
    from fractal_wallpapers.paths import repo_root

    return repo_root() / "data" / "curation" / "manufacture" / batch


def _write_jsonl(path: Path, rows) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
            count += 1
    return count


def _read_jsonl(path: Path) -> list[dict]:
    path = Path(path)
    if not path.is_file():
        raise ManufactureError(f"{path} does not exist; the step before this one has not run")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _write_json(path: Path, document: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


# --------------------------------------------------------------------------- #
# What to aim at, and what can reach it.
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def targets() -> tuple[str, ...]:
    """The swatches this batch is manufacturing, thinnest first.

    `expressed`'s own thin list — the swatches at most five of the 246 finished
    wallpapers express — read off the artifact rather than restated, because a
    second copy of that list is a second claim about the collection.
    """
    from fractal_wallpapers.curation import expressed

    path = expressed.readout_path()
    if not path.is_file():
        raise ManufactureError(
            f"{path} does not exist. `fractal-wallpapers curate expressed` is what says "
            f"which swatches the finished collection is thin in, and this batch aims at "
            f"that list rather than at one of its own."
        )
    thin = json.loads(path.read_text(encoding="utf-8")).get("thin") or []
    if not thin:
        raise ManufactureError(f"{path} names no thin swatch, so there is nothing to aim at")
    return tuple(str(name) for name in thin)


def carriers() -> tuple[dict, dict]:
    """`(new, library)` — per swatch, the maps worth attempting for it, best first.

    Read off the coverage rows rather than the readout, because the readout
    counts carriers and this needs to name them. The split is the drop: a map the
    `rare-colors-2026-08` ingest brought in is the new-map arm's material, and
    everything the library already held is the contrast arm's.
    """
    from fractal_wallpapers.curation import palette_coverage as coverage

    if not coverage.rows_path().is_file():
        raise ManufactureError(
            f"{coverage.rows_path()} does not exist. `fractal-wallpapers curate coverage` "
            f"is what says which maps can put a swatch on real pixels, and this batch draws "
            f"its maps from that read."
        )
    best = coverage.reach(coverage.read_rows(), fold="production")
    drop = coverage.of_drop()
    new: dict[str, list[str]] = {}
    library: dict[str, list[str]] = {}
    for swatch in targets():
        reaching = sorted(
            ((best[name].get(swatch, 0.0), name) for name in best),
            key=lambda pair: (-pair[0], pair[1]),
        )
        for share, name in reaching:
            if share < CARRIER_FLOOR:
                break
            (new if name in drop else library).setdefault(swatch, []).append(name)
    missing = [swatch for swatch in targets() if not new.get(swatch) or not library.get(swatch)]
    if missing:
        raise ManufactureError(
            f"no arm can be built for {missing}: a target needs carriers in the drop AND in "
            f"the pre-existing library, or its contrast row would be forced through a map "
            f"that cannot reach it."
        )
    return new, library


# --------------------------------------------------------------------------- #
# Where to put them.
# --------------------------------------------------------------------------- #
def human_locations() -> list[dict]:
    """Every distinct place a person scored a keeper, at the frame they scored it.

    The preferred tier. A verdict of 3 or 4 on the location scale is a human
    saying this place is worth rendering, which is the one thing that cannot be
    bought with compute — and it is the same channel `supply.proven` roots a walk
    at, read the same way.
    """
    from fractal_wallpapers.labeling import store
    from fractal_wallpapers.supply.location import location_key
    from fractal_wallpapers.supply.partitions import partition_of_family

    seen: dict = {}
    for row in store.resolved().scored():
        if int(row["score"]) < 3:
            continue
        key = location_key(row["family"], row["viewport"])
        if key is None or key in seen:
            continue
        maxiter = (row.get("render") or {}).get("maxiter")
        if not maxiter:
            continue
        seen[key] = {
            "key": json.dumps(key),
            "family": row["family"],
            "viewport": row["viewport"],
            "maxiter": int(maxiter),
            "partition": partition_of_family(row["family"]),
            "tier": TIERS[0],
            "score": int(row["score"]),
        }
    return list(seen.values())


def admitted_locations(exclude: set[str]) -> list[dict]:
    """High-scoring admitted places, best first — the extension a short quota reaches for.

    The curation sidecar, above the junk floor, ranked on the location head's
    `P(>=4)`. It is a rank and never a height: the only cut placed on that scale
    here is the floor, and what this does with the rest of it is order.

    Read through [`intake.read_scores`], which is where [`curation.amend`]'s
    re-read of a location whose old view no longer exists is preferred. Both the
    floor and the order turn on the score, so opening the file directly would
    extend a short quota into places chosen on a number about a lost picture.
    """
    from fractal_wallpapers.curation import floors, intake
    from fractal_wallpapers.supply.partitions import partition_of_family

    try:
        supply = list(intake.read_scores().values())
    except intake.IntakeError as absent:
        raise ManufactureError(
            f"{intake.scores_path()} does not exist, so there is no admitted population to "
            f"extend into. `fractal-wallpapers curate sidecar restore` brings it back. "
            f"({absent})"
        ) from absent
    rows: dict = {}
    for row in supply:
        if row.get("p_ge3") is None or float(row["p_ge3"]) < floors.JUNK_FLOOR:
            continue
        key = row["key"]
        if key in exclude:
            continue
        if not row.get("maxiter"):
            continue
        held = rows.get(key)
        if held is not None and float(held["score"]) >= float(row.get("p_ge4") or 0.0):
            continue
        rows[key] = {
            "key": key,
            "family": row["family"],
            "viewport": row["viewport"],
            "maxiter": int(row["maxiter"]),
            "partition": row.get("partition") or partition_of_family(row["family"]),
            "tier": TIERS[1],
            "score": float(row.get("p_ge4") or 0.0),
        }
    return sorted(rows.values(), key=lambda row: (-row["score"], row["key"]))


# --------------------------------------------------------------------------- #
# The registration, which happens before anything is built.
# --------------------------------------------------------------------------- #
#: What each batch says about how it was drawn. Two arms, one sentence each, and
#: neither of them is score-unconditioned: the extension tier is ranked on the
#: location head, every map is chosen off the coverage read, and both cuts that
#: decide a row are read off the render judge. Anchored too — the page serves
#: that judge's own decode prefilled and reads good-to-bad by its score. So both
#: are train-side, by construction rather than by policy, and `eval_only` is not
#: the answer either: an instrument is a population somebody bought to measure
#: with, and this one was bought to correct with.
METHODS = {
    BATCH: (
        "manufactured. One row per location, no location twice. Locations are places a "
        "person scored 3 or 4 on the location scale, extended into the highest-scoring "
        "admitted supply where a swatch quota could not be filled from those; every row "
        "stamps which tier it came from. Each location is aimed at one of the thin swatches "
        "`curate expressed` names, tried through maps the `curate coverage` panel says can "
        "reach it — here the maps of the `rare-colors-2026-08` drop — in modes drawn the way "
        "a production run draws them, under the identity palette recipe production uses. "
        "Every attempt was built and censused; what filled a quota is the share measured on "
        "the picture served, and every served row also cleared the render judge at >= 2 on "
        "that same picture."
    ),
    CONTRAST_BATCH: (
        "the contrast arm of the same manufacture, drawn identically in every respect but "
        "one: its maps are the ones the library already held before the "
        "`rare-colors-2026-08` drop, forced to the same target swatches. Its own batch so "
        "that a verdict about the colour and a verdict about the drop are separable from the "
        "store alone."
    ),
}

#: The sentence a later reader needs about what this population is not.
WHY = (
    "A correction rate off these sheets is a CEILING and never a base rate: the population "
    "is enriched twice over, by location quality and by a passing score. Registered before "
    "the first pixel because the honest answer to `was a model score in the selection` is "
    "only available while the population is being drawn."
)


def register(write: bool = False, log=print) -> list[str]:
    """Register both arms in both stores, before the batch has any rows.

    Four registrations, because a batch is one population drawn by one method and
    the two stores keep their own registries. Idempotent by refusal: a batch
    already registered is left alone and said so, since a second row would
    restate a claim rather than correct one.
    """
    from fractal_wallpapers.labeling import finished
    from fractal_wallpapers.labeling import registry as registry_module

    lines = []
    for kind in KINDS:
        known = finished.registry(kind)
        for batch, method in METHODS.items():
            if batch in known:
                lines.append(f"{kind}/{batch}: already registered, left alone")
                continue
            registration = registry_module.Registration(
                batch=batch,
                method=method,
                score_unconditioned=False,
                anchored=True,
                eval_only=False,
                why=WHY,
            )
            if not write:
                lines.append(f"{kind}/{batch}: would register, side={registration.side}")
                continue
            finished.register(kind, registration)
            lines.append(f"{kind}/{batch}: registered, side={registration.side}")
    del log
    return lines


def registered() -> None:
    """Refuse to build anything the registry has not been told about first.

    The ordering is the design and this is where it bites: `store.append` refuses
    an unregistered row, but that is at ingest, which is after the whole build has
    been paid for. Fail closed here instead.
    """
    from fractal_wallpapers.labeling import finished

    missing = [
        f"{kind}/{batch}"
        for kind in KINDS
        for batch in METHODS
        if batch not in finished.registry(kind)
    ]
    if missing:
        raise ManufactureError(
            f"not registered: {missing}. A batch is registered before it has rows, because "
            f"whether a model score was in the selection is answerable while the population "
            f"is being drawn and is answered from memory afterwards. "
            f"`fractal-wallpapers curate manufacture --step register --write` writes them."
        )


# --------------------------------------------------------------------------- #
# The plan.
# --------------------------------------------------------------------------- #
def quotas(rows_per_kind: int = ROWS_PER_KIND) -> dict:
    """`{kind: {swatch: {arm: rows}}}` — what each cell of the batch owes.

    Even over the targets, through the supply engine's own apportionment so a
    remainder that will not divide is spread rather than dropped on one swatch.
    """
    from fractal_wallpapers.supply import apportion

    names = targets()
    weights = dict.fromkeys(names, 1.0)
    total = apportion.allocate_slots(weights, rows_per_kind)
    contrast = apportion.allocate_slots(weights, round(rows_per_kind * CONTRAST_SHARE))
    out = {}
    for kind in KINDS:
        out[kind] = {
            swatch: {
                "new": int(total.get(swatch, 0)) - int(contrast.get(swatch, 0)),
                "contrast": int(contrast.get(swatch, 0)),
            }
            for swatch in names
        }
    return out


def modes_of(kind: str, key: str, seed: int) -> list[str]:
    """The modes one location is tried in, drawn the way a production run draws them.

    Uniform and without replacement off the location and the kind, which is
    `curation.colorize.modes_drawn_for` exactly — reached through a plan-shaped
    object rather than reimplemented, so a change to the roster or to the draw
    reaches this batch too.
    """
    from fractal_wallpapers.curation import colorize

    class _Plan:
        head = kind
        modes_drawn = 1 if kind == SMOOTH else STRANGE_MODES

    plan = _Plan()
    plan.key = key
    return colorize.modes_drawn_for(plan, seed)


def _cells(quota: dict) -> list[tuple[str, str, str]]:
    """Every `(kind, swatch, arm)` this batch owes rows to, in a fixed order."""
    return [
        (kind, swatch, arm)
        for kind in KINDS
        for swatch in targets()
        for arm in ("new", "contrast")
        if quota[kind][swatch][arm] > 0
    ]


def build_plan(
    oversample: float = 4.0,
    rows_per_kind: int = ROWS_PER_KIND,
    seed: int = SEED,
    batch: str = BATCH,
    log=print,
) -> dict:
    """Draw the whole batch: which place, in which mode, through which map.

    `oversample` is how many locations a cell attempts per row it owes. It is a
    knob and not a constant because the yield is a property of *this* population
    — good places, forced colours — and nothing measured anywhere else predicts
    it. Pilot it, then plan against what the pilot measured.
    """
    registered()
    quota = quotas(rows_per_kind)
    new_maps, library_maps = carriers()
    people = human_locations()
    draw = random.Random((seed, "locations").__str__())
    draw.shuffle(people)

    cells = _cells(quota)
    wanted = {cell: max(1, round(quota[cell[0]][cell[1]][cell[2]] * oversample)) for cell in cells}
    needed = sum(wanted.values())
    spare = admitted_locations({row["key"] for row in people}) if needed > len(people) else []
    pool = people + spare[: max(0, needed - len(people))]
    if len(pool) < needed:
        raise ManufactureError(
            f"the plan wants {needed} distinct locations at one row per location and both "
            f"tiers together hold {len(pool)}. Lower --oversample or lower --rows-per-kind; "
            f"the one thing that is not on the table is colouring one place several ways."
        )
    log(
        f"[plan] {needed} locations over {len(cells)} cells: "
        f"{len(people)} human, {len(pool) - len(people)} admitted"
    )

    attempts: list[dict] = []
    taken = 0
    for kind, swatch, arm in cells:
        maps = (new_maps if arm == "new" else library_maps)[swatch]
        for index in range(wanted[(kind, swatch, arm)]):
            location = pool[taken]
            taken += 1
            modes = modes_of(kind, location["key"], seed)
            per_mode = max(1, ATTEMPTS_PER_LOCATION // len(modes))
            for mode_index, mode in enumerate(modes):
                for slot in range(per_mode):
                    # Round-robin down the carrier list rather than a draw, so no
                    # map is over-attempted while another is never tried: the
                    # cap acts at selection and this is what gives it something
                    # to choose between.
                    position = (index * per_mode * len(modes) + mode_index * per_mode + slot) % len(
                        maps
                    )
                    attempts.append(
                        {
                            "schema": SCHEMA,
                            "attempt": len(attempts),
                            "kind": kind,
                            "arm": arm,
                            "batch": BATCH if arm == "new" else CONTRAST_BATCH,
                            "target": swatch,
                            "mode": mode,
                            "mode_index": mode_index,
                            "modes_drawn": len(modes),
                            "colormap": maps[position],
                            "panel_share": None,
                            **{
                                key: location[key]
                                for key in (
                                    "key",
                                    "family",
                                    "viewport",
                                    "maxiter",
                                    "partition",
                                    "tier",
                                )
                            },
                            "location_score": location["score"],
                        }
                    )
    _write_jsonl(attempts_path(batch), attempts)
    document = {
        "schema": SCHEMA,
        "batch": batch,
        "seed": seed,
        "oversample": oversample,
        "rows_per_kind": rows_per_kind,
        "attempts_per_location": ATTEMPTS_PER_LOCATION,
        "strange_modes": STRANGE_MODES,
        "rows_per_map": ROWS_PER_MAP,
        "reached": REACHED,
        "screen": {"share": SCREEN_SHARE, "tier": SCREEN_TIER, "probability": SCREEN_PROBABILITY},
        "geometry": {
            "candidate": {
                "resolution": list(CANDIDATE_RESOLUTION),
                "supersample": CANDIDATE_SUPERSAMPLE,
            },
            "sheet": {"resolution": list(SHEET_RESOLUTION), "supersample": SHEET_SUPERSAMPLE},
        },
        "targets": targets(),
        "quotas": quota,
        "carriers": {
            swatch: {"new": len(new_maps[swatch]), "library": len(library_maps[swatch])}
            for swatch in targets()
        },
        "locations": {
            "wanted": needed,
            "human_q3": min(needed, len(people)),
            "admitted": max(0, needed - len(people)),
            "human_q3_available": len(people),
        },
        "attempts": len(attempts),
        "recipe": recipe_note(),
    }
    _write_json(plan_path(batch), document)
    log(f"[plan] {len(attempts)} attempts over {needed} locations")
    return document


def top_up(oversample: float = 3.0, batch: str = BATCH, log=print) -> dict:
    """Extend the plan for the cells the selection came back short in.

    The tier rule, acted on rather than stated: a quota that could not be filled
    reaches for **more of the preferred tier first** and only drops to the
    admitted supply when the human one is exhausted. A batch that jumped straight
    to the extension while a thousand labelled keepers sat unused would be
    reporting a tier split about its own draw order.

    Appends; it never rewrites an attempt. Every existing attempt keeps its id and
    every built group keeps its record, so the screen and the confirm resume onto
    what is already on disk and pay only for what this added. The round-robin down
    each cell's carrier list picks up where the cell left off, so a cell short
    because its best maps hit the per-map cap is offered different ones.
    """
    plan = json.loads(plan_path(batch).read_text(encoding="utf-8"))
    summary = json.loads((work_dir(batch) / "selection.json").read_text(encoding="utf-8"))
    shortfall = summary.get("shortfall") or {}
    if not shortfall:
        log("[top-up] nothing is short; the plan stands")
        return plan
    attempts = _read_jsonl(attempts_path(batch))
    held = {row["key"] for row in attempts}
    new_maps, library_maps = carriers()
    seed = int(plan["seed"])

    people = [row for row in human_locations() if row["key"] not in held]
    random.Random((seed, "locations").__str__()).shuffle(people)
    needed = sum(max(1, round(count * oversample)) for count in shortfall.values())
    pool = people + (
        admitted_locations(held | {row["key"] for row in people})[: max(0, needed - len(people))]
        if needed > len(people)
        else []
    )
    if len(pool) < needed:
        raise ManufactureError(
            f"the top-up wants {needed} distinct unused locations and both tiers together "
            f"hold {len(pool)}. Lower --oversample, or accept the shortfall and report it."
        )
    log(
        f"[top-up] {len(shortfall)} short cell(s), {needed} more locations: "
        f"{min(needed, len(people))} human, {max(0, needed - len(people))} admitted"
    )

    taken = 0
    added = 0
    for name, count in sorted(shortfall.items()):
        kind, swatch, arm = name.split("/")
        maps = (new_maps if arm == "new" else library_maps)[swatch]
        already = sum(
            1 for row in attempts if (row["kind"], row["target"], row["arm"]) == (kind, swatch, arm)
        )
        for step in range(max(1, round(count * oversample))):
            location = pool[taken]
            taken += 1
            modes = modes_of(kind, location["key"], seed)
            per_mode = max(1, ATTEMPTS_PER_LOCATION // len(modes))
            for mode_index, mode in enumerate(modes):
                for slot in range(per_mode):
                    index = already // ATTEMPTS_PER_LOCATION + step
                    position = (index * per_mode * len(modes) + mode_index * per_mode + slot) % len(
                        maps
                    )
                    attempts.append(
                        {
                            "schema": SCHEMA,
                            "attempt": len(attempts),
                            "kind": kind,
                            "arm": arm,
                            "batch": BATCH if arm == "new" else CONTRAST_BATCH,
                            "target": swatch,
                            "mode": mode,
                            "mode_index": mode_index,
                            "modes_drawn": len(modes),
                            "colormap": maps[position],
                            "panel_share": None,
                            **{
                                key: location[key]
                                for key in (
                                    "key",
                                    "family",
                                    "viewport",
                                    "maxiter",
                                    "partition",
                                    "tier",
                                )
                            },
                            "location_score": location["score"],
                            "top_up": True,
                        }
                    )
                    added += 1
    _write_jsonl(attempts_path(batch), attempts)
    plan["locations"]["wanted"] += needed
    plan["locations"]["human_q3"] += min(needed, len(people))
    plan["locations"]["admitted"] += max(0, needed - len(people))
    plan["attempts"] = len(attempts)
    plan["top_ups"] = [*plan.get("top_ups", []), {"cells": shortfall, "attempts": added}]
    _write_json(plan_path(batch), plan)
    log(f"[top-up] {added} more attempts, {len(attempts)} in the plan")
    return plan


def recipe_note() -> dict:
    """What the palette pass is on every row, and what varied across the batch.

    Written into the plan because it is the diagnostic's own premise. Production
    samples no knob at all; the only thing that moves across this batch is the
    fold, and that is read off the map rather than drawn.
    """
    from fractal_wallpapers.labeling import finished

    return {
        "knobs": finished.recipe(),
        "sampled": [],
        "varied": ["mirror"],
        "mirror_rule": (
            "models.palette_sets.recipe_for — folded unless the map is cyclic. Read off the "
            "map, never drawn: every map of the rare-colours drop is cyclic, so every "
            "new-map row is unfolded and the whole recipe is the identity."
        ),
    }


# --------------------------------------------------------------------------- #
# The build, at both geometries.
# --------------------------------------------------------------------------- #
def _geometry(maxiter: int, resolution, supersample: int) -> dict:
    return {
        "resolution": list(resolution),
        "supersample": int(supersample),
        "maxiter": int(maxiter),
    }


def _leveled_recolor(
    field: Path, colormap: str, mirror: bool, output: Path, band, recipe: dict | None = None
) -> dict | None:
    """One dumped field through one map, levelled the way a render of it would be.

    The recolor path's twin of [`curation.colorize.render`], and it keeps that
    function's two properties rather than half of them. A field mode is dumped
    once and every map after it is a pass over memory — but the operator still
    has to act, or the picture is not the picture production would have made; and
    nothing exists at `output` until the row is finished, because the levelled
    path writes twice to one name and a kill between the two would leave a
    decodable picture that never saw the operator.

    `recipe` is the whole palette pass and defaults to production's, which is the
    identity plus the fold. It is a parameter for exactly one caller — the knob
    probe, which is the only thing in this project that ever moves one — and a
    build that passed anything else here would be a batch this repository could
    not reproduce.

    **The curve is stated on every recolor and never left to the dump.** A dumped
    field records the curve it was dumped under, which is the *mode's own*; a
    render states [`colorize.CURVE`] and `renders.coloring_of` writes it over the
    mode's. Those agree for every field mode but one — `trap_circle` names `log`
    and everything else names `linear` — so a recolor that inherited the dump's
    curve produced a different picture from the render of the same row, for that
    one mode, and for no other. `manufacture.verify` is what found it.
    """
    from fractal_wallpapers import engine, paths
    from fractal_wallpapers.coloring import autolevel
    from fractal_wallpapers.curation import colorize
    from fractal_wallpapers.labeling import finished

    output.parent.mkdir(parents=True, exist_ok=True)
    scratch = colorize.writing_path(output)
    scratch.unlink(missing_ok=True)
    spec = {
        "schema": 1,
        "field": str(field),
        "colormap": colormap,
        "colormap_dir": str(paths.colormap_dir()),
        "transform": colorize.CURVE,
        "palette": finished.recipe(mirror=mirror) if recipe is None else recipe,
        "output": str(scratch),
    }
    engine.recolor(spec)
    entry = json.loads((paths.colormap_dir() / f"{colormap}.json").read_text(encoding="utf-8"))

    def rerender(stops):
        # Named for the FINAL picture and not for the temporary, the way the
        # render path names it: the levelled colormap is the record of what this
        # row was coloured through, and the sheet is pointed at it by name.
        directory = output.parent / f"{output.stem}.leveled"
        autolevel.overriding_colormap(colormap, stops, entry.get("kind"), directory)
        engine.recolor({**spec, "colormap_dir": str(directory)})
        return scratch

    leveled = autolevel.maybe_level(
        scratch, {"name": colormap, "stops": entry["stops"], "mirror": mirror}, rerender, band
    )
    Path(leveled.image).replace(output)
    return leveled.stamp


def _group_record(directory: Path, name: str) -> Path:
    """Where one group's finished rows are kept, so a killed leg resumes on them."""
    return directory / "rows" / f"{name}.json"


@lru_cache(maxsize=1)
def _band_and_cyclic():
    """The tone band and the cyclic set, read once per worker process.

    Both are tracked files that answer the same thing for every row, and a group
    is one row on the confirm leg — so reading them per group is a file read and
    a JSON parse for every picture, paid 1,045 times to learn 1,045 identical
    answers. Cached on the process rather than passed down, because the payload a
    worker receives is pickled and the band is a document.
    """
    from fractal_wallpapers.coloring import band as band_module
    from fractal_wallpapers.models import palette_sets

    return band_module.load(), palette_sets.cyclic()


def _build_group(payload: tuple) -> list[dict]:
    """One `(location, mode)` group, every map of it. A worker's whole job.

    Top level so it can be pickled. Grouped this way because a field mode dumps
    its field once and recolours from it, which is the whole reason the seven
    field modes are cheap and the other eleven are not.

    **A group is the resume unit, not a picture.** What a row carries beside its
    picture — the operator's stamp, what the census read, what it cost — is not
    recoverable by looking at a JPEG, so a leg that resumed on files alone would
    come back with a stamp of `null` on every row it did not make itself. The
    rows are written when the group finishes and re-read whole.
    """
    import time

    from fractal_wallpapers import engine, paths
    from fractal_wallpapers.curation import colorize

    rows, directory, resolution, supersample = payload
    directory = Path(directory)
    first = rows[0]
    record = _group_record(directory, first["group"])
    if record.is_file():
        held = json.loads(record.read_text(encoding="utf-8"))
        if [row["attempt"] for row in held] == [row["attempt"] for row in rows]:
            return held

    band, cyclic = _band_and_cyclic()
    location = {key: first[key] for key in ("family", "viewport", "maxiter")}
    geometry = _geometry(first["maxiter"], resolution, supersample)

    field = None
    dump_failure = None
    if colorize.kind_of(first["mode"]) == "field":
        field = directory / "fields" / f"{first['group']}.f32"
        try:
            if not (field.is_file() and field.with_suffix(".json").is_file()):
                field.parent.mkdir(parents=True, exist_ok=True)
                engine.dump_field(
                    {
                        "schema": 1,
                        "family": first["family"],
                        "viewport": first["viewport"],
                        "resolution": list(resolution),
                        "supersample": int(supersample),
                        "maxiter": int(first["maxiter"]),
                        "mode": first["mode"],
                        "colormap": "twilight_shifted",
                        "colormap_dir": str(paths.colormap_dir()),
                        "output": str(field),
                    }
                )
        except Exception as failure:  # noqa: BLE001 — a failed dump is a recorded row
            dump_failure = repr(failure)[:400]

    out = []
    for row in rows:
        if dump_failure is not None:
            out.append({**row, "picture": None, "error": dump_failure})
            continue
        picture = directory / "pictures" / f"{row['attempt']:06d}.jpg"
        started = time.time()
        mirror = row["colormap"] not in cyclic
        try:
            if field is not None:
                stamp = _leveled_recolor(field, row["colormap"], mirror, picture, band)
            else:
                _, stamp = colorize.render(
                    location,
                    row["mode"],
                    row["colormap"],
                    cyclic,
                    picture,
                    render_geometry=geometry,
                    level=True,
                    band=band,
                )
            read = codebook.of_picture(picture)
        except Exception as failure:  # noqa: BLE001 — a failed attempt is a recorded row
            out.append({**row, "picture": None, "error": repr(failure)[:400]})
            continue
        out.append(
            {
                **row,
                "picture": str(picture.relative_to(directory)),
                "mirror": mirror,
                "autolevel": stamp,
                "seconds": round(time.time() - started, 3),
                "share": float((read["shares"] or {}).get(row["target"], 0.0)),
                "dominant": read["dominant"],
                "entropy_bits": read["entropy_bits"],
                "present": read["present"],
                "error": None,
            }
        )
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps(out), encoding="utf-8", newline="\n")
    return out


def _grouped(rows: list[dict]) -> list[list[dict]]:
    """Attempts gathered into `(location, mode)` groups, each a worker's payload."""
    import hashlib

    groups: dict[str, list[dict]] = {}
    for row in rows:
        digest = hashlib.sha256(row["key"].encode("utf-8")).hexdigest()[:12]
        name = f"{row['mode']}_{digest}"
        groups.setdefault(name, []).append({**row, "group": name})
    return [groups[name] for name in sorted(groups)]


def _judge(pictures: list[Path], device: str = "auto", log=print) -> tuple[list, int, str]:
    """Every picture through the shipped finished-render judge, in one pass.

    One model load for the whole batch rather than one per worker: the render is
    what costs, and a judge loaded in six processes is six copies of a gigabyte
    doing the arithmetic a single batched pass does at 136 pictures a second.
    """
    from fractal_wallpapers.curation import floors
    from fractal_wallpapers.models import render_train, scoring, ship, train

    judge = floors.SCORING_HEAD
    stamp = floors.live_stamp(judge)
    log(f"[judge] {len(pictures)} pictures through {judge} {stamp[:12]}")
    model, config, where = render_train.load_checkpoint(ship.shipped_path(judge), device)
    classes = int(config["classes"])
    probabilities = train.score(
        model, pictures, scoring.transform_of(config), where, classes, {"batch_size": 64}
    )
    return probabilities, classes, stamp


def _scored(row: dict, probability, classes: int, stamp: str) -> dict:
    block = {
        "judge": stamp,
        **{f"p_ge{index + 2}": float(probability[index]) for index in range(classes - 1)},
    }
    block["rank_score"] = float(sum(probability))
    block["tier"] = 1 + sum(1 for value in probability if value >= SCREEN_PROBABILITY)
    return {**row, "scores": block}


def _measure(
    rows: list[dict],
    directory: Path,
    resolution,
    supersample: int,
    workers: int,
    device: str,
    log,
) -> list[dict]:
    """Build every row, census it, then judge the lot. The two stages' shared engine."""
    import time
    from concurrent.futures import ProcessPoolExecutor

    groups = _grouped(rows)
    started = time.time()
    log(f"[build] {len(rows)} attempts in {len(groups)} groups over {workers} workers")
    built: list[dict] = []
    payloads = [(group, str(directory), list(resolution), int(supersample)) for group in groups]
    if workers <= 1:
        for done, payload in enumerate(payloads, start=1):
            built.extend(_build_group(payload))
            if done % 25 == 0 or done == len(payloads):
                log(f"[build] {done}/{len(payloads)} groups, {time.time() - started:.0f}s")
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for done, made in enumerate(pool.map(_build_group, payloads), start=1):
                built.extend(made)
                if done % 25 == 0 or done == len(payloads):
                    log(f"[build] {done}/{len(payloads)} groups, {time.time() - started:.0f}s")
    log(f"[build] {len(built)} rows in {time.time() - started:.0f}s")

    made = [row for row in built if row.get("picture")]
    failed = [row for row in built if not row.get("picture")]
    if failed:
        log(f"[build] {len(failed)} attempt(s) produced no picture and carry their error")
    if made:
        probabilities, classes, stamp = _judge(
            [directory / row["picture"] for row in made], device, log
        )
        made = [
            _scored(row, probability, classes, stamp)
            for row, probability in zip(made, probabilities, strict=True)
        ]
    return sorted(made + failed, key=lambda row: row["attempt"])


def screen(workers: int = 6, device: str = "auto", batch: str = BATCH, log=print) -> list[dict]:
    """Every planned attempt at candidate geometry, censused and judged.

    Nothing is selected here. The screen is a pre-filter on what is worth
    re-rendering at the size a person will judge, and it is deliberately generous
    on both axes.
    """
    rows = _read_jsonl(attempts_path(batch))
    directory = work_dir(batch) / "candidate"
    measured = _measure(
        rows, directory, CANDIDATE_RESOLUTION, CANDIDATE_SUPERSAMPLE, workers, device, log
    )
    _write_jsonl(screened_path(batch), measured)
    passing = [row for row in measured if _passes_screen(row)]
    log(f"[screen] {len(passing)} of {len(measured)} attempts are worth confirming")
    return measured


def _passes_screen(row: dict) -> bool:
    """Worth the sheet-geometry render: some colour, and not obviously a 1."""
    if not row.get("picture") or row.get("scores") is None:
        return False
    return (
        float(row["share"]) >= SCREEN_SHARE and float(row["scores"]["p_ge2"]) >= CONFIRM_PROBABILITY
    )


def confirm(workers: int = 6, device: str = "auto", batch: str = BATCH, log=print) -> list[dict]:
    """The best surviving attempt at each location, at the geometry the sheet serves.

    One per location and never more, because the sheet holds one row per location
    — so the choice of which of a location's four attempts is confirmed is made
    here, on the target share the screen measured, and everything after it is
    made on this render.
    """
    screened = _read_jsonl(screened_path(batch))
    best: dict[str, dict] = {}
    for row in screened:
        if not _passes_screen(row):
            continue
        held = best.get(row["key"])
        if held is None or float(row["share"]) > float(held["share"]):
            best[row["key"]] = row
    chosen = [
        {key: value for key, value in row.items() if key not in ("picture", "seconds", "autolevel")}
        for row in sorted(best.values(), key=lambda row: row["attempt"])
    ]
    for row in chosen:
        row["candidate"] = {
            "share": row.pop("share"),
            "dominant": row.pop("dominant"),
            "entropy_bits": row.pop("entropy_bits"),
            "present": row.pop("present"),
            "scores": row.pop("scores"),
        }
    log(f"[confirm] {len(chosen)} locations of {len({row['key'] for row in screened})} attempted")
    directory = work_dir(batch) / "sheet"
    measured = _measure(
        chosen, directory, SHEET_RESOLUTION, SHEET_SUPERSAMPLE, workers, device, log
    )
    for row in measured:
        picture = row.get("picture")
        if not picture:
            continue
        leveled = (directory / picture).parent / f"{Path(picture).stem}.leveled"
        row["leveled"] = str(leveled) if leveled.is_dir() else None
    _write_jsonl(confirmed_path(batch), measured)
    served = [row for row in measured if serves(row)]
    log(f"[confirm] {len(served)} of {len(measured)} clear both cuts on the sheet render")
    return measured


def serves(row: dict) -> bool:
    """Both acting cuts, on the picture that will be on the sheet.

    The colour cut and the tier cut, and both read off the sheet-geometry render
    rather than off the candidate that stood behind it — a new map can wreck a
    picture an old map carried, and the reading that decides has to be the one a
    person will be looking at.
    """
    if not row.get("picture") or row.get("scores") is None:
        return False
    return float(row["share"]) >= REACHED and int(row["scores"]["tier"]) >= SCREEN_TIER


# --------------------------------------------------------------------------- #
# The selection, and the two sheet plans it writes.
# --------------------------------------------------------------------------- #
def select(rows_per_kind: int = ROWS_PER_KIND, batch: str = BATCH, log=print) -> dict:
    """Fill every cell's quota from what actually landed, and write the sheet plans.

    Ranked inside a cell by the **target share** and not by the judge's own
    score. Both are available and the choice is deliberate: the tier cut has
    already removed everything a person would not be asked about, and ranking the
    survivors by the head's opinion would enrich the sheet a third time on the
    very axis the sheet exists to correct.
    """
    confirmed = _read_jsonl(confirmed_path(batch))
    quota = quotas(rows_per_kind)
    served = [row for row in confirmed if serves(row)]
    cells: dict[tuple, list[dict]] = {}
    for row in served:
        cells.setdefault((row["kind"], row["target"], row["arm"]), []).append(row)

    per_map: dict[str, int] = {}
    taken: dict[tuple, list[dict]] = {}
    capped = 0
    for cell in _cells(quota):
        kind, swatch, arm = cell
        want = quota[kind][swatch][arm]
        offer = sorted(cells.get(cell, []), key=lambda row: (-float(row["share"]), row["attempt"]))
        kept = []
        for row in offer:
            if len(kept) >= want:
                break
            if per_map.get(row["colormap"], 0) >= ROWS_PER_MAP:
                capped += 1
                continue
            per_map[row["colormap"]] = per_map.get(row["colormap"], 0) + 1
            kept.append(row)
        taken[cell] = kept

    shortfall = {
        f"{kind}/{swatch}/{arm}": quota[kind][swatch][arm] - len(taken[(kind, swatch, arm)])
        for kind, swatch, arm in _cells(quota)
        if len(taken[(kind, swatch, arm)]) < quota[kind][swatch][arm]
    }
    plans = {}
    for kind in KINDS:
        chosen = [row for cell, rows in taken.items() if cell[0] == kind for row in rows]
        chosen.sort(key=lambda row: (targets().index(row["target"]), -float(row["share"])))
        plans[kind] = _write_jsonl(sheet_plan_path(kind, batch), [_unit(row) for row in chosen])
        log(f"[select] {kind}: {plans[kind]} of {rows_per_kind} rows")
    if shortfall:
        log(f"[select] {sum(shortfall.values())} row(s) short in {len(shortfall)} cell(s)")

    summary = {
        "schema": SCHEMA,
        "batch": batch,
        "rows": plans,
        "confirmed": len(confirmed),
        "served": len(served),
        "shortfall": shortfall,
        "capped_out": capped,
        "rows_per_map": {
            "cap": ROWS_PER_MAP,
            "maps_used": len(per_map),
            "distribution": {
                str(count): sum(1 for value in per_map.values() if value == count)
                for count in sorted(set(per_map.values()))
            },
        },
        "tiers": _tally([row for rows in taken.values() for row in rows], lambda row: row["tier"]),
        "arms": _tally([row for rows in taken.values() for row in rows], lambda row: row["arm"]),
        "modes": _tally([row for rows in taken.values() for row in rows], lambda row: row["mode"]),
    }
    _write_json(work_dir(batch) / "selection.json", summary)
    _record(taken, summary, batch)
    return summary


def _tally(rows: list[dict], of) -> dict:
    out: dict[str, int] = {}
    for row in rows:
        out[str(of(row))] = out.get(str(of(row)), 0) + 1
    return dict(sorted(out.items()))


def _unit(row: dict) -> dict:
    """One selected row as the plan unit `label build --from-plan` reads.

    It states its own recipe and its own map, because a unit that let the sheet
    re-pick either would be a different picture from the one measured — and it
    names the levelled colormap the operator wrote, so the sheet's render is that
    picture rather than one made through the map before the operator touched it.
    """
    from fractal_wallpapers.curation import colorize
    from fractal_wallpapers.labeling import finished

    facts = [
        f"target {row['target']} · {row['share']:.3f} of pixels",
        f"{row['arm']} arm · {row['tier']} location · dominant {row['dominant']}",
    ]
    unit = {
        "family": row["family"],
        "viewport": row["viewport"],
        "maxiter": int(row["maxiter"]),
        "mode": row["mode"],
        "mode_params": {},
        "curve": colorize.CURVE,
        "colormap": row["colormap"],
        "recipe": finished.recipe(mirror=bool(row["mirror"])),
        "batch": row["batch"],
        "section": "",
        "facts": facts,
    }
    if row.get("leveled"):
        unit["leveled"] = row["leveled"]
    return unit


def _record(taken: dict, summary: dict, batch: str) -> None:
    """The tracked record: every selected row, keyed on its render identity.

    A store row carries the place, the recipe and the verdict, and deliberately
    not what the page printed under the picture. So which target this row was
    manufactured for, which arm it is, which tier its location came from and what
    the two geometries measured live here — joined to the store on
    `finished.render_key`, which is the identity a verdict is cast on.
    """
    from fractal_wallpapers.labeling import finished
    from fractal_wallpapers.paths import tracked_name

    directory = record_dir(batch)
    directory.mkdir(parents=True, exist_ok=True)
    for kind in KINDS:
        rows = []
        for cell, chosen in sorted(taken.items()):
            if cell[0] != kind:
                continue
            for row in chosen:
                unit = _unit(row)
                rows.append(
                    {
                        "schema": SCHEMA,
                        "batch": row["batch"],
                        "kind": kind,
                        "arm": row["arm"],
                        "target": row["target"],
                        "tier": row["tier"],
                        "location_score": row["location_score"],
                        "mode": row["mode"],
                        "colormap": row["colormap"],
                        "mirror": bool(row["mirror"]),
                        "render_key": list(
                            finished.render_key(
                                {
                                    **unit,
                                    "recipe": unit["recipe"],
                                }
                            )
                            or []
                        ),
                        "sheet": {
                            "share": row["share"],
                            "dominant": row["dominant"],
                            "entropy_bits": row["entropy_bits"],
                            "present": row["present"],
                            "scores": row["scores"],
                        },
                        "candidate": row.get("candidate"),
                    }
                )
        _write_jsonl(directory / f"{kind}.jsonl", rows)
    _write_json(
        directory / "batch.json",
        {
            **summary,
            "plan": tracked_name(plan_path(batch)),
            "rows_file": [f"{kind}.jsonl" for kind in KINDS],
        },
    )


# --------------------------------------------------------------------------- #
# The readout.
# --------------------------------------------------------------------------- #
def hit_rate(batch: str = BATCH) -> dict:
    """Per target swatch, the fraction of ATTEMPTED LOCATIONS that reached 10%.

    Not the map-by-cell count and not the attempt count: a location is one trial,
    it is a hit when any of its attempts put the target on a tenth of the
    picture, and the denominator is every location the plan aimed at that swatch.

    Read at candidate geometry, which is where every attempted location has a
    reading — a location whose four attempts all failed the screen was never
    rendered at sheet geometry, so a rate taken there would have the hits in the
    numerator and only the hits in the denominator too.

    The reading is against a knob draw that varied **nothing** — see
    [`recipe_note`] — so a low rate here cannot be an under-explored recipe. If
    more than half a swatch's locations fail, that is a defect in what the plan
    asked for rather than a fact about where it asked.
    """
    screened = _read_jsonl(screened_path(batch))
    by_swatch: dict[str, dict] = {}
    for row in screened:
        cell = by_swatch.setdefault(row["target"], {"best": {}, "attempts": 0, "arm": {}})
        cell["attempts"] += 1
        share = float(row.get("share") or 0.0)
        cell["best"][row["key"]] = max(share, cell["best"].get(row["key"], 0.0))
        cell["arm"][row["key"]] = row["arm"]
    out = {}
    for swatch, cell in by_swatch.items():
        best = cell["best"]
        values = list(best.values())
        reached = sum(1 for value in values if value >= REACHED)
        arms: dict[str, list[float]] = {}
        for key, value in best.items():
            arms.setdefault(cell["arm"][key], []).append(value)
        out[swatch] = {
            "locations": len(values),
            "reached": reached,
            "rate": round(reached / len(values), 4) if values else 0.0,
            "attempts": cell["attempts"],
            "best_share": round(max(values), 4) if values else 0.0,
            "median_share": round(sorted(values)[len(values) // 2], 4) if values else 0.0,
            "by_arm": {
                arm: {
                    "locations": len(shares),
                    "rate": round(sum(1 for value in shares if value >= REACHED) / len(shares), 4),
                }
                for arm, shares in sorted(arms.items())
            },
            "probable_defect": bool(values) and reached / len(values) < 0.5,
        }
    return dict(sorted(out.items(), key=lambda pair: pair[1]["rate"]))


def drift(batch: str = BATCH) -> dict:
    """How far the sheet render moved from the candidate that stood behind it.

    Two numbers this project has never had at this pair of sizes: how much a
    target swatch's share moves between `640x360 x2` and `1280x720 x2`, and how
    often the judge's tier moves with it. Both are read off rows that were
    rendered at both, which is every confirmed row.
    """
    confirmed = [row for row in _read_jsonl(confirmed_path(batch)) if row.get("scores")]
    moves = []
    tier_moves = {"up": 0, "down": 0, "same": 0}
    crossed = 0
    for row in confirmed:
        candidate = row.get("candidate") or {}
        if not candidate.get("scores"):
            continue
        moves.append(abs(float(row["share"]) - float(candidate["share"])))
        was, now = int(candidate["scores"]["tier"]), int(row["scores"]["tier"])
        tier_moves["up" if now > was else "down" if now < was else "same"] += 1
        if (float(candidate["share"]) >= REACHED) != (float(row["share"]) >= REACHED):
            crossed += 1
    moves.sort()
    return {
        "rows": len(moves),
        "share_median": round(moves[len(moves) // 2], 4) if moves else None,
        "share_p95": round(moves[int(0.95 * (len(moves) - 1))], 4) if moves else None,
        "share_worst": round(moves[-1], 4) if moves else None,
        "crossed_the_threshold": crossed,
        "tier": tier_moves,
    }


#: The knob grid the probe sweeps, and it is a MEASUREMENT rather than a policy.
#: Three traversals of the gradient and three starting places on it, which is the
#: coarsest grid that can answer "would exploring have helped" — `cycles` and
#: `phase` are the two knobs the engine only honours on a cyclic map, and every
#: map of the drop is cyclic. Nothing in this repository renders through any of
#: these; production is the first cell of the grid.
KNOB_GRID = ((1.0, 0.0), (1.0, 1 / 3), (1.0, 2 / 3), (2.0, 0.0), (2.0, 0.5), (3.0, 0.0))


def probe_knobs(sample: int = 120, batch: str = BATCH, seed: int = SEED, log=print) -> dict:
    """What a knob draw would have bought, on the attempts that failed without one.

    The diagnostic's own hypothesis, measured instead of argued. Matt's rule says
    a swatch more than half of whose locations fail is a probable defect, on the
    reasoning that *a palette free to cycle and shift phase should be able to put
    its colours somewhere on almost any field*. Production's palette is not free
    to do either — see [`recipe_note`] — so the rule's premise is not a
    description of this pipeline, and the honest way to report the hit rate
    "against what the knob draw actually varied" is to say that it varied nothing
    and then to price the counterfactual.

    So: a seeded sample of attempts that missed the target at the identity, each
    re-coloured through [`KNOB_GRID`] off the field it already has on disk, levelled
    the same way. What comes back is how many of them any cell of the grid would
    have rescued — an upper bound on a knob draw, since the draw would take one
    cell and this takes the best of six.

    Only the field modes can be probed: a composite normalizes two fields against
    the whole frame and a direct trap is colour-valued before any gradient is
    spent, so neither has a dumped field to sweep. The sample says so.
    """
    import time

    from fractal_wallpapers.labeling import finished

    band, cyclic = _band_and_cyclic()
    directory = work_dir(batch) / "candidate"
    fields = directory / "fields"
    missed = [
        row
        for row in _read_jsonl(screened_path(batch))
        if row.get("picture")
        and float(row["share"]) < REACHED
        and row["colormap"] in cyclic
        and (fields / f"{row['group']}.f32").is_file()
    ]
    if not missed:
        raise ManufactureError(
            "no attempt missed its target on a cyclic map with a dumped field, so there is "
            "nothing for the knob probe to sweep. It reads the screen's own rows."
        )
    draw = random.Random((seed, "knobs").__str__())
    drawn = draw.sample(missed, min(sample, len(missed)))
    where_pictures = directory / "knobs"
    started = time.time()
    log(f"[knobs] {len(drawn)} missed attempts x {len(KNOB_GRID)} cells")

    rescued = 0
    rows = []
    for index, row in enumerate(drawn, start=1):
        best, cell = float(row["share"]), None
        for step, (cycles, phase) in enumerate(KNOB_GRID):
            if (cycles, phase) == (1.0, 0.0):
                continue
            # A name per cell rather than one reused path. The levelled path
            # renames a temporary onto its output, and on Windows that rename is
            # refused while anything still holds the destination — which is what
            # happens when a tight loop rewrites one filename a thousand times.
            output = where_pictures / f"{row['attempt']:06d}_{step}.jpg"
            recipe = finished.recipe(cycles=cycles, phase=phase, mirror=bool(row["mirror"]))
            _leveled_recolor(
                fields / f"{row['group']}.f32", row["colormap"], row["mirror"], output, band, recipe
            )
            share = float((codebook.of_picture(output)["shares"] or {}).get(row["target"], 0.0))
            if share > best:
                best, cell = share, {"cycles": cycles, "phase": round(phase, 4)}
            output.unlink(missing_ok=True)
            shutil.rmtree(output.parent / f"{output.stem}.leveled", ignore_errors=True)
        rescued += best >= REACHED
        rows.append(
            {
                "attempt": row["attempt"],
                "target": row["target"],
                "mode": row["mode"],
                "colormap": row["colormap"],
                "identity": float(row["share"]),
                "best": round(best, 4),
                "knobs": cell,
            }
        )
        if index % 25 == 0 or index == len(drawn):
            log(f"[knobs] {index}/{len(drawn)}, {time.time() - started:.0f}s")
    shutil.rmtree(where_pictures, ignore_errors=True)
    _write_jsonl(work_dir(batch) / "knobs.jsonl", rows)
    return {
        "grid": [{"cycles": c, "phase": round(p, 4)} for c, p in KNOB_GRID],
        "probeable": len(missed),
        "missed": sum(
            1
            for row in _read_jsonl(screened_path(batch))
            if row.get("picture") and float(row["share"]) < REACHED
        ),
        "sampled": len(drawn),
        "rescued": rescued,
        "rescue_rate": round(rescued / len(drawn), 4),
        "median_gain": round(
            sorted(row["best"] - row["identity"] for row in rows)[len(rows) // 2], 4
        ),
        "best_gain": round(max(row["best"] - row["identity"] for row in rows), 4),
        "seconds": round(time.time() - started, 1),
    }


def verify(sheet: Path, batch: str = BATCH) -> dict:
    """The one claim only a comparison can settle: the sheet serves the picture that was cut on.

    Both acting cuts are taken on a render this module made, and the sheet is
    built by a different command that renders again from the plan. If those two
    renders are not the same picture, then a row was screened on one thing and a
    person is looking at another — which is the failure the whole two-geometry
    design exists to avoid and the one no amount of care in either half can rule
    out on its own.

    So it is checked rather than argued: every served row's sheet picture against
    the confirmed picture, byte for byte, and the sheet's own reading of the judge
    against the reading the cut was taken on. The levelled colormap is what makes
    it true — a plan unit names the directory the operator wrote, so the sheet's
    render is that render and not one through the map before the operator touched
    it — and a row whose unit lost that name would come back `different` here.
    """
    import hashlib

    from fractal_wallpapers.labeling import finished

    sheet = Path(sheet)
    manifest = sheet / "sheet.json"
    if not manifest.is_file():
        raise ManufactureError(f"{sheet} is not a built sheet: it holds no sheet.json")
    rows = _read_jsonl(sheet / "sheet.jsonl")
    made = work_dir(batch) / "sheet"
    index = {}
    for row in _read_jsonl(confirmed_path(batch)):
        if not (row.get("picture") and serves(row)):
            continue
        key = finished.render_key(_unit(row))
        if key is not None:
            index[key] = row
    same = different = unmatched = 0
    worst = 0.0
    for row in rows:
        source = index.get(finished.render_key(row["join"]))
        if source is None:
            unmatched += 1
            continue
        served = hashlib.sha256((sheet / row["pictures"][0]["path"]).read_bytes()).hexdigest()
        cut_on = hashlib.sha256((made / source["picture"]).read_bytes()).hexdigest()
        same, different = (same + 1, different) if served == cut_on else (same, different + 1)
        for column, value in (row.get("columns") or {}).items():
            worst = max(worst, abs(float(value) - float(source["scores"][column])))
    return {
        "sheet": str(sheet),
        "rows": len(rows),
        "identical": same,
        "different": different,
        "unmatched": unmatched,
        "worst_score_gap": worst,
        "held": different == 0 and unmatched == 0,
    }


def read(batch: str = BATCH) -> dict:
    """Everything the report needs, off the rows the batch already wrote."""
    plan = json.loads(plan_path(batch).read_text(encoding="utf-8"))
    selection = json.loads((work_dir(batch) / "selection.json").read_text(encoding="utf-8"))
    return {
        "schema": SCHEMA,
        "batch": batch,
        "plan": plan,
        "selection": selection,
        "hit_rate": hit_rate(batch),
        "drift": drift(batch),
        "yield": _yield(batch),
    }


def _yield(batch: str) -> dict:
    """Where the attempts went: built, screened, confirmed, served, seated."""
    screened = _read_jsonl(screened_path(batch))
    confirmed = _read_jsonl(confirmed_path(batch))
    locations = {row["key"] for row in screened}
    return {
        "attempts": len(screened),
        "attempts_built": sum(1 for row in screened if row.get("picture")),
        "attempts_failed": sum(1 for row in screened if not row.get("picture")),
        "attempts_past_screen": sum(1 for row in screened if _passes_screen(row)),
        "locations": len(locations),
        "locations_past_screen": len({row["key"] for row in screened if _passes_screen(row)}),
        "confirmed": len(confirmed),
        "served": sum(1 for row in confirmed if serves(row)),
        "lost_to_colour": sum(
            1 for row in confirmed if row.get("scores") and float(row["share"]) < REACHED
        ),
        "lost_to_tier": sum(
            1
            for row in confirmed
            if row.get("scores")
            and float(row["share"]) >= REACHED
            and int(row["scores"]["tier"]) < SCREEN_TIER
        ),
    }


__all__ = [
    "ATTEMPTS_PER_LOCATION",
    "BATCH",
    "CONTRAST_BATCH",
    "CONTRAST_SHARE",
    "REACHED",
    "ROWS_PER_KIND",
    "ROWS_PER_MAP",
    "SCHEMA",
    "SCREEN_SHARE",
    "SCREEN_TIER",
    "SEED",
    "TIERS",
    "ManufactureError",
    "admitted_locations",
    "attempts_path",
    "build_plan",
    "carriers",
    "confirm",
    "confirmed_path",
    "drift",
    "hit_rate",
    "human_locations",
    "modes_of",
    "plan_path",
    "probe_knobs",
    "quotas",
    "read",
    "recipe_note",
    "record_dir",
    "screen",
    "screened_path",
    "select",
    "serves",
    "sheet_plan_path",
    "targets",
    "top_up",
    "verify",
    "work_dir",
]
