"""Every recipe in the store was chosen at phase 0. This asks the other phases.

A pool built one draw at a time carries the draw's own shape. Nothing here ever
put a rotation of the gradient on the table — `Palette.phase` was not a member a
candidate leg could move until 2026-09-11 — so every row is a **phase-0 pick over
a phase-0 field**, and a head fitted on the pool inherits that and calls it
quality. This pass takes the residue back out, one (location, mode) group at a
time: the row's own picture against [`ROTATIONS`] fresh phases, best of the six by
`p_fine`, and the row it replaces taken out of the store.

The target to hold in mind is *what the store would look like if rotations had
been on the table from the beginning*. This does not reach it — it acts on the
rows that pass the shipped fine bar and leaves the rest — and the point is the
direction rather than the destination.

## The dump is the whole economics, so the group is the unit

`Palette.phase` is spent **after** the field is read
([`coloring`]'s recolour path, `colorize.recolored`), so five rotations of one
recipe are five colormap lookups over one iteration pass. That is the only reason
this pass is affordable at all: at full render price six candidates a row would be
six times the store's original cost, and as a recolour it is about one and a
quarter. So the unit of work is the **(location, mode) pair** and never the row —
one dump serves every rotation of every row under it — which is
[`candidate_ledger.rerender.render_pair`]'s arrangement and
[`curation.remode.blocks_of`]'s, reached rather than restated.

It also bounds the coverage, and the bound is the engine's. A dump needs a single
scalar field ([`colorize.FIELD_KIND`]), so the composites, the modulates and the
direct traps are out. The traps are out **twice over**: `phase` is a byte-for-byte
no-op on a trap figure over a flat ground, so a rotation there would be a second
recipe key for the same picture. The others are rotatable at full render price and
are recorded as owed rather than done ([`owed`]).

## Levelling: each candidate derives its own, and that is both the cheap answer
## and the only sound one

Matt's ruling is that the curve is close enough either way — share the dump's, take
phase 0's, or let each derive. Deriving is what [`colorize.render`] already does
with `borrowed` unset, so it is *zero* code and the cheapest to write; and it is
the only one of the three that keeps the ledger's second invariant. The autolevel
member of a recipe key is [`recipes.stamp_of`] — the operator, the switch and the
band — and never the curve the operator derived, so an **inherited** curve would
put a picture in the store under a key that a `re-render` of that row reproduces
differently. What it costs is the `measure` stage, which is Python: a JPEG decode
and an Oklab pass on every candidate.

## What it will not remove, and the list is longer than the prompt's

Two rows are never taken whatever the six scores say — a row seated in **any**
recorded gallery, and ⚠ a row carrying **any** human label, because a hand label
does not come back and a label pointing at a picture nobody has is worse than no
label. [`protections`] honours those and the [`sweep.prune`] rule's other three
beside them — a live release seat, a human rejection, and a row the rank key's
own fitted population names — on the argument that a pass which protects more
rows than it was asked to is safe in a direction a pass that protects fewer is
not. Each is counted apart on the record.
"""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from datetime import UTC, datetime
from pathlib import Path

from fractal_wallpapers.curation import candidate_ledger
from fractal_wallpapers.paths import tracked_name, under

#: The schema every record and every row this module writes carries.
SCHEMA = 1

#: The subtree this pass's pictures land in, under the regenerable tree. It is a
#: member of [`candidate_ledger.POOL_SUBTREES`], which is what makes them
#: reachable by `curate candidate-ledger orphans`: a leg whose subtree that sweep
#: cannot enumerate leaks every render of a killed run with no row anywhere and
#: nothing to notice it.
UNIT = "rotation"

#: What the appended files and the record are called.
ROWS_NAME = "rows.jsonl"
SCORES_NAME = "scores.jsonl"
DECISIONS_NAME = "decisions.jsonl"
REMOVED_NAME = "removed.jsonl"
PLAN_NAME = "plan.jsonl"
RECORD_NAME = "rotation.json"
MERGE_NAME = "merge.json"

#: How many rotations a row is asked beside the picture it already has. **Five**,
#: so a row is six candidates and the incumbent's share of a fair draw is a sixth.
ROTATIONS = 5

#: The tolerance knob, and a **relative** one on purpose: `p_fine` spans orders of
#: magnitude down the pool, so a fixed margin would be the whole reading at the
#: bottom and a rounding error at the top. A winning rotation is adopted where it
#: reads at least this times the incumbent's **stored** column — which is the
#: reading the pool was seated on and the one a reader of the store already has.
#:
#: Against the stored column rather than against the fresh one, and that is what
#: makes the test bite at all: a rotation that wins best-of-six has beaten the
#: incumbent's *fresh* reading by construction, so a factor on that would refuse
#: nothing ever. What it catches is the six of them coming in far under what the
#: store says the row is worth — a levelling that went somewhere else, a head that
#: has moved, a picture that is not the picture the column was read on.
TOLERANCE = 0.9

#: How many engines this pass drives at once. **Three**, this machine's render
#: pool, the same number every leg here takes and a rule about the desktop rather
#: than a tuning knob.
WORKERS = 3

#: How many (location, mode) groups are rendered before the pass stops to score
#: what it made. A chunk is the finest point the pass can be interrupted at with
#: every picture it drew either adopted or deleted, and it is a trade: the render
#: pool is idle while the heads read, so a chunk too small spends the leg's clock
#: on model loads and a chunk too large holds thousands of undecided JPEGs on
#: disk. 400 groups is about 40 minutes of rendering against about 3 of reading.
CHUNK_GROUPS = 400

#: What the draw is, spelled once: `phase` uniform over the whole turn, and
#: `cycles` **fixed at 1**. The repeat axis is not on the table —
#: `palette_variant_mine_ckpt120` measured it at 36.4% of matched pairs won at
#: repeat 3 against 52.6% at repeat 1, monotone in the tile count — so this draw
#: moves one member and the other stays the identity.
REPEAT = 1

#: How many rotations a **mined** candidate is asked beside its own phase 0.
#: Four, so a shot is five candidates. One fewer than the store arm's
#: [`ROTATIONS`] and the difference is not a taste: over the store the incumbent
#: is a picture that already exists and costs nothing to read, so a sixth
#: candidate is free; here every one of the five is a render, and the phase-0
#: control is what the other four are read against.
MINE_ROTATIONS = 4

#: What a mining leg's plan is sized off, in engine seconds a **shot** — where a
#: shot is the whole best-of-five and not one candidate. A deliberate
#: under-estimate, `palette_variant_mine_ckpt120`'s own reasoning: `rate` is in
#: the denominator of `PLAN_HEADROOM * workers * budget / rate`, the surplus of a
#: plan is never started, and clock-bound is the correct way for a leg to end.
MINE_RATE = 2.5

#: How a mining leg's plan is split between the draws. **Spelled whole**, because
#: [`depth.build_plan`] merges what it is given over [`depth.SHARES`]: naming the
#: ranked share alone leaves the near-band and flat draws on their 0.25 defaults,
#: and the leg spends half its clock on arms the last producing leg zeroed. This is
#: `palette_variant_mine_ckpt120`'s own shape, which is what *standard process*
#: means here — the ranked draw is the only one that produces a curve.
MINE_SHARES = {
    "ranked_bands": 1.0,
    "flat": 0.0,
    "near_band": 0.0,
    "mode_floor": 0.0,
    "conditioned": 0.0,
}

#: The width a mining leg draws at, and it is arithmetic rather than a knob.
#: Twelve modes cycled at width 12 is **one map per (location, mode)** — and a
#: best-of-five merges one row of the five, so a pair takes one row against
#: [`candidate_ledger.RETAIN_PER_PAIR`] and the merge is prune-free. The pilot
#: that ran width 12 over `curate depth`'s three-mode default roster lost 229 of
#: 726 rows at the merge, which is the same arithmetic read the wrong way.
MINE_WIDTH = 12


class RotationRefused(RuntimeError):
    """A population this pass will not act on, or a leg that wrote nothing."""


# --------------------------------------------------------------------------- #
# Where it keeps things.
# --------------------------------------------------------------------------- #
def store_root() -> Path:
    """The subtree every pass of this module keeps a directory under."""
    return under("curation", UNIT)


def rotation_dir(name: str) -> Path:
    """The subtree one pass owns: its rows, its pictures, its fields, its record."""
    return under("curation", UNIT, str(name))


def rows_path(name: str) -> Path:
    return rotation_dir(name) / ROWS_NAME


def scores_path(name: str) -> Path:
    return rotation_dir(name) / SCORES_NAME


def decisions_path(name: str) -> Path:
    return rotation_dir(name) / DECISIONS_NAME


def removed_path(name: str) -> Path:
    return rotation_dir(name) / REMOVED_NAME


def plan_path(name: str) -> Path:
    return rotation_dir(name) / PLAN_NAME


def record_path(name: str) -> Path:
    return rotation_dir(name) / RECORD_NAME


def merge_path(name: str) -> Path:
    return rotation_dir(name) / MERGE_NAME


def fields_dir(name: str) -> Path:
    """Where this pass's dumped fields live. One per (location, mode)."""
    return rotation_dir(name) / "fields"


def pictures_dir(name: str) -> Path:
    """The rotations, named by **recipe key**, which is the shape the ratchet's
    `recipe_key_named` counter counts and what lets a re-run find what it made."""
    return rotation_dir(name) / candidate_ledger.PICTURES_NAME


# --------------------------------------------------------------------------- #
# The intention.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Rotation:
    """One candidate this pass intends to make, before anything is rendered.

    The three-member duck type [`hunt.Maker`] reads — `mode`, `mode_params`,
    `palette` — under the names [`hunt.Try`], [`mine.Unit`] and [`depth.Shot`]
    already use, so this renders through [`mine.make`] exactly as every other
    candidate in the ledger did rather than through a second spelling of the act.
    """

    #: The row this rotates, by recipe key. Carried so a made picture can be
    #: joined back to the incumbent it is competing with, which is the only join
    #: this pass has — a rotation differs from its incumbent in the palette and
    #: nothing else, so nothing in the ledger's own shape records it.
    of_key: str
    location: str
    partition: str
    mode: str
    colormap: str
    #: Which rotation of its row this is, 1..[`ROTATIONS`]. The incumbent is 0.
    k: int
    #: The drawn phase, recorded here as well as inside `palette` because this is
    #: what the DRAW moved and `palette` is the whole pass the picture was made
    #: through — the distinction [`depth`]'s `palette_drawn` draws, same reason.
    phase: float
    band: str = UNIT
    arm: str = UNIT
    mode_params: dict = dataclass_field(default_factory=dict)
    palette: dict = dataclass_field(default_factory=dict)

    def named(self) -> dict:
        """This intention as the ledger row's `hunt` block carries it."""
        out = {
            "leg": self.arm,
            "mode": self.mode,
            "colormap": self.colormap,
            "band": self.band,
            "k": self.k,
            "rotation_of": self.of_key,
        }
        if self.palette:
            out["palette_drawn"] = dict(self.palette)
        return out


@dataclass(frozen=True)
class Incumbent:
    """One passing ledger row, as everything below it reads one."""

    key: str
    location: str
    partition: str
    mode: str
    colormap: str
    picture: str
    #: The row's reading on the live fine column — the number the tolerance is a
    #: factor of, and what put the row in this population at all.
    p_fine: float
    #: The whole stored recipe block, so the rotation is this recipe with one
    #: member moved rather than a recipe rebuilt from a plan.
    recipe: dict
    #: Whether one of [`protections`]' five holds this row, and which.
    held_by: str | None = None

    def place(self) -> dict:
        """What [`mine.make`] reads off a place: the family, and nothing else."""
        return {"family": self.recipe["family"]}

    def frame(self) -> dict:
        """The frame the incumbent was rendered at. **No framing lookup** — this
        pass rotates a picture that exists, and adopting a refinement would move
        the place. [`curation.remode.frame_of`]'s rule, one leg over."""
        return {"viewport": self.recipe["viewport"], "maxiter": int(self.recipe["maxiter"])}

    def pass_knobs(self) -> dict:
        """Where this row's palette pass differs from the plain one. The overrides.

        **The difference and not the whole pass**, because an intention's `palette`
        is what the draw *moved* — it is recorded on the row as `palette_drawn`,
        [`depth`]'s distinction — and handing back the six knobs a plain pass
        already has would make every row look like a varied draw. On an ordinary
        row this is empty and the rotation carries its phase alone, which is what
        5,993 of 6,036 rotatable rows are.

        **`mirror` is never in it.** It is the colormap's bake —
        [`hunt.Maker.palette_for`] derives it off the map and refuses a draw that
        names it — and `mirror_cycles_audit_ckpt120` proved the derivation agrees
        with every row in the store, in both directions, so dropping it here loses
        nothing. A row where it ever stopped agreeing would fail the zero-key guard
        in [`_resolve`], which is where a disagreement belongs.

        **This is what the 43 rows of `rotation_pass_ckpt120` were.** They were
        refused as `key_does_not_reproduce`, and they were not misfiled: all 43
        digest back to their own key out of their stored recipe. What did not
        reproduce was the *rebuild*, because it was built at
        [`labeling.finished.recipe`]'s defaults and their pass carries a tuned
        `gamma` — every one of them, with `reverse` on 20 and a different
        `transfer` on 18. No candidate leg draws those knobs; the label-import path
        wrote them, and all 43 rows carry a human label. Rebuilding one at the
        defaults would have been a different picture under its key, so the guard
        was right to refuse and the plan was wrong to ask.
        """
        from fractal_wallpapers.labeling import finished

        held = dict(self.recipe.get("palette") or {})
        plain = finished.recipe(mirror=bool(held.get("mirror")))
        return {
            name: value
            for name, value in held.items()
            if name != "mirror" and plain.get(name) != value
        }


# --------------------------------------------------------------------------- #
# The population.
# --------------------------------------------------------------------------- #
def passing(bar: float | None = None, log=print) -> dict:
    """`{recipe key: p_fine}` for every row the shipped fine bar admits.

    The column `curate gallery-grade score-pool` wrote, read through its own
    module's accessor rather than off a path built here — a `p_fine` means nothing
    without the run that produced it, and there is one spelling of where it lives.
    """
    from fractal_wallpapers.curation import solve
    from fractal_wallpapers.models import gallery_grade_train as grade

    held = solve.DEFAULT_FINE_BAR if bar is None else float(bar)
    where = grade.pool_scores_path()
    if not where.is_file():
        raise RotationRefused(
            f"{tracked_name(where)} is not there, so this checkout has not read its pool "
            f"through the fine head and there is no passing set to rotate. Run "
            f"`fractal-wallpapers gallery-grade score-pool` first."
        )
    out: dict = {}
    read = 0
    for line in where.open(encoding="utf-8"):
        if not line.strip():
            continue
        row = json.loads(line)
        read += 1
        value = float(row.get("p_ge4") or 0.0)
        if value >= held:
            out[str(row["key"])] = value
    log(
        f"[rotation] {len(out):,} of {read:,} scored row(s) read p_fine >= {held:g} on "
        f"{grade.pool_scores_run()}"
    )
    return out


def protections(log=print) -> dict:
    """`{reason: {recipe key}}` — every row this pass will not remove.

    [`sweep._prune_protections`]' five, resolved the same way and off the same
    modules, because a second answer to *what does this store keep* is a second
    store. Two of them are the ones the pass is told about by name and the other
    three are here on the argument in the module docstring; they are kept apart so
    the caller can say which held what.

    **The reference sets only, and never a pass of the ledger.** Four small stores
    — the release index, the label stores, the recorded galleries and the rank
    key's fitted population — plus [`holder_of`], which is the per-row half. A
    version of this that streamed the store to build five key sets was a second
    twenty-second read of half a gigabyte for an answer [`population`] is already
    standing in the right place to take.
    """
    from fractal_wallpapers.curation import rank_key, retention, served_locations, tentative
    from fractal_wallpapers.curation.candidate_ledger import store as store_module

    index = served_locations.build()
    live: set = set()
    for held in index.rows:
        live.add((str(held.get("run")), str(held.get("candidate"))))
        source = held.get("source") or {}
        if source.get("run") is not None:
            live.add((str(source.get("run")), str(source.get("candidate"))))
    marked = retention.labeled_renders()
    recorded = tentative.protected_keys()
    fitted = {
        str(json.loads(line)["recipe_key"])
        for line in rank_key.population_path().read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    out = {
        store_module.RETAINED_SEATED: live,
        store_module.RETAINED_LABELED: marked,
        store_module.RETAINED_FITTED: fitted,
        store_module.RETAINED_TENTATIVE: recorded,
    }
    log(
        "[rotation] never removed: a live release seat in "
        f"{len(live):,} (run, candidate) pair(s), {len(marked):,} human-labelled render "
        f"key(s), {len(fitted):,} recipe(s) the rank key was fitted on, {len(recorded):,} "
        f"seat(s) over {len(tentative.stamps())} recorded gallery/ies, and any row carrying "
        "a recorded rejection"
    )
    return out


def holder_of(row: dict, held: dict) -> str | None:
    """Which of [`protections`]' five holds this ledger row, or `None`.

    First one wins and the order is [`store.RETAINED_REASONS`]', so a row held by
    two reasons is counted once and always under the same one — which is what
    makes the census add up to the rows rather than to the reasons.

    The rejection is the one asked off the row itself: it is a bare boolean the
    row carries, so there is no reference set for it to be in.
    """
    from fractal_wallpapers.curation import retention
    from fractal_wallpapers.curation.candidate_ledger import store as store_module

    provenance = row.get("provenance") or {}
    live = held[store_module.RETAINED_SEATED]
    seat = (str(provenance.get("run")), str(provenance.get("candidate")))
    also = tuple(
        (str(named.get("run")), str(named.get("candidate")))
        for named in (provenance.get("also_recorded") or ())
    )
    if seat in live or any(named in live for named in also):
        return store_module.RETAINED_SEATED
    if row.get("rejected"):
        return store_module.RETAINED_REJECTED
    if retention.render_key_of(row) in held[store_module.RETAINED_LABELED]:
        return store_module.RETAINED_LABELED
    if str(row["key"]) in held[store_module.RETAINED_FITTED]:
        return store_module.RETAINED_FITTED
    if str(row["key"]) in held[store_module.RETAINED_TENTATIVE]:
        return store_module.RETAINED_TENTATIVE
    return None


#: Why a passing row is not one this pass can rotate. Each is a fact about the
#: recipe and not about the row's quality, and each is counted on the record —
#: a census of what the operation cannot reach is half of what the next pass is
#: sized off.
REFUSALS = (
    "mode_cannot_dump",
    "dumpable_not_owed",
    "direct_trap",
    "already_rotated",
    "repeated_gradient",
    "carries_mode_settings",
    "curve_override",
    "off_candidate_regime",
    "no_picture",
    "key_does_not_reproduce",
)


def refusal_of(row: dict, kinds: dict, owed: bool = False) -> str | None:
    """Which of [`REFUSALS`] keeps this row out, or `None`. First one wins.

    The order is the order a reader wants them counted in: the mode first,
    because that is a property of the coverage rather than of the row, and the
    recipe's own members after it.

    **`owed` swaps which side of the dump the pass is about, and the two arms
    partition the passing set.** The dumpable arm takes the `field` colorings and
    records the rest as owed — the composites and `itinerary`, whose coloring has
    no single scalar field to dump and recolour. The owed arm takes exactly those
    and refuses the dumpable ones as `dumpable_not_owed`, which is the other arm's
    work rather than a debt. Swapped and not widened, because the two are priced an
    order apart: an owed row is six iteration passes against a dumpable row's one,
    so a leg holding both would report one seconds-a-row over two prices and a
    re-run of the cheap arm nobody asked for.

    Nothing else about the pass changes. [`colorize.render`] already renders these
    — a mode with no field to dump falls through to the render path — so the flag
    buys clock and no new code. The direct traps stay refused in both arms, because
    `phase` is a no-op on a trap figure over a flat ground and there is nothing
    there to come back for.
    """
    from fractal_wallpapers.curation import colorize

    recipe = row.get("recipe") or {}
    mode = str(recipe.get("mode") or "")
    kind = kinds.get(mode)
    if kind == colorize.DIRECT_KIND:
        return "direct_trap"
    if owed:
        if kind == colorize.FIELD_KIND:
            return "dumpable_not_owed"
    elif kind != colorize.FIELD_KIND:
        return "mode_cannot_dump"
    palette = recipe.get("palette") or {}
    if float(palette.get("phase") or 0.0):
        return "already_rotated"
    if float(palette.get("cycles") or 1.0) != float(REPEAT):
        return "repeated_gradient"
    if recipe.get("mode_params"):
        return "carries_mode_settings"
    if str(recipe.get("curve") or "") != colorize.CURVE:
        return "curve_override"
    if not row.get("at_candidate_regime"):
        return "off_candidate_regime"
    if not row.get("picture"):
        return "no_picture"
    return None


def _undumpable(sources: list, kinds: dict) -> int:
    """How many of a population's rows are on a mode with no field to dump."""
    from fractal_wallpapers.curation import colorize

    return sum(1 for one in sources if kinds.get(one.mode) != colorize.FIELD_KIND)


def population(bar: float | None = None, owed: bool = False, log=print) -> dict:
    """Everything this pass acts on, out of **one** stream of the ledger.

    The ledger is half a gigabyte read whole, so it is read once: the passing
    join, the refusal census, the guard resolution and the set of keys already in
    the store all come off the same pass. `sources` is in **store order**, which
    is the ordering the prompt's de-biasing argument turns on — taking the best
    rows first would reproduce the selection this pass exists to undo.
    """
    from fractal_wallpapers.engine_spec import catalog

    started = time.time()
    from fractal_wallpapers.curation.candidate_ledger import store as store_module

    admitted = passing(bar, log=log)
    held = protections(log=log)
    kinds = {mode: coloring.get("kind") for mode, coloring in catalog().items()}
    sources: list[Incumbent] = []
    refused = dict.fromkeys(REFUSALS, 0)
    protected = dict.fromkeys(store_module.RETAINED_REASONS[1:], 0)
    known: set = set()
    read = 0
    for row in candidate_ledger.stream():
        read += 1
        key = str(row["key"])
        known.add(key)
        value = admitted.get(key)
        if value is None:
            continue
        why = refusal_of(row, kinds, owed=bool(owed))
        if why is not None:
            refused[why] += 1
            continue
        holder = holder_of(row, held)
        if holder is not None:
            protected[holder] += 1
        location = str((row.get("location") or {}).get("key"))
        recipe = row["recipe"]
        sources.append(
            Incumbent(
                key=key,
                location=location,
                partition=str(row.get("partition") or ""),
                mode=str(recipe.get("mode") or ""),
                colormap=str(recipe.get("colormap") or ""),
                picture=str(row["picture"]),
                p_fine=float(value),
                recipe=recipe,
                held_by=holder,
            )
        )
    log(
        f"[rotation] {read:,} ledger row(s) read in {time.time() - started:.0f}s; "
        f"{len(sources):,} rotatable, {sum(refused.values()):,} refused, "
        f"{sum(protected.values()):,} of the rotatable held by a protection"
    )
    log(
        f"[rotation] the OWED arm: {len(sources):,} row(s) on a mode with no field to "
        f"dump, at full render price; the dumpable rows are the other arm's"
        if owed
        else "[rotation] the dumpable arm: a row whose mode cannot dump is refused and "
        "recorded as owed"
    )
    return {
        "ledger_rows": read,
        "passing": len(admitted),
        "sources": sources,
        "refused": refused,
        "protected": protected,
        "known": known,
        "bar": float(bar) if bar is not None else None,
        # **On the population and not only on the record**, so the arm a leg ran
        # is readable off the thing every other number here was counted over.
        "owed": bool(owed),
    }


#: What a refusal census counts and does **not** owe. A direct trap because
#: `phase` is a no-op on a trap figure over a flat ground, so there is no
#: rotation of one to come back for; a dumpable row on the owed arm because it is
#: the other arm's work and is priced an order cheaper. Everything else in
#: [`REFUSALS`] is a row some renderer could rotate.
NOT_OWED = ("direct_trap", "dumpable_not_owed")


def owed(refused: dict) -> dict:
    """What this pass could not reach and another could. A census.

    Everything in [`REFUSALS`] but [`NOT_OWED`] is a row a renderer could rotate,
    the composites at the price of an iteration pass a candidate — six times a
    dumpable row's per-row cost, which is why they are recorded rather than taken
    by the arm that finds them.
    """
    return {name: int(count) for name, count in refused.items() if name not in NOT_OWED and count}


# --------------------------------------------------------------------------- #
# The draw.
# --------------------------------------------------------------------------- #
def draws(key: str, seed: int, count: int = ROTATIONS) -> list[float]:
    """The phases one row's rotations are drawn at. Uniform over the turn.

    Seeded **per row and off the row's own key**, not off a stream shared by the
    whole pass. That is what makes a partial pass reproducible: a leg that stopped
    at the clock and a leg re-run over the same population draw the same phases
    for the same rows however many rows came before them, so a second pass adds
    rows rather than re-asking the ones the first one answered differently.
    """
    rng = random.Random(f"{int(seed)}|{key}")
    return [round(rng.random(), 6) for _ in range(int(count))]


def plan_of(sources: list, seed: int, known: set, count: int = ROTATIONS) -> tuple[list, dict]:
    """`(groups, shape)` — the pass's work, cut at the (location, mode) pair.

    One dump serves every rotation of every row under a pair, so the pair is the
    unit and a plan cut per row would hand one place to three workers and pay the
    dump three times over. First-appearance order inside and between, which is
    store order: the prompt's ordering rule applies **within** the passing set,
    and taking the good rows of it first is exactly the selection being undone.

    A rotation whose key the store already holds is dropped rather than rendered —
    which on a continuous draw is all but unreachable, and is the same guard every
    other leg here runs.
    """
    order: dict = {}
    shape = {"rows": 0, "rotations": 0, "already_in_ledger": 0, "held": 0}
    for source in sources:
        shape["rows"] += 1
        shape["held"] += int(source.held_by is not None)
        made = []
        for at, phase in enumerate(draws(source.key, seed, count), start=1):
            rotation = Rotation(
                of_key=source.key,
                location=source.location,
                partition=source.partition,
                mode=source.mode,
                colormap=source.colormap,
                k=at,
                phase=float(phase),
                # **The incumbent's own pass with the phase moved**, and not the
                # default pass at a drawn phase. [`Incumbent.pass_knobs`] is the
                # difference and the 43 rows it recovers are its whole reason.
                palette={**source.pass_knobs(), "phase": float(phase)},
            )
            made.append(rotation)
        shape["rotations"] += len(made)
        order.setdefault((source.location, source.mode), []).append((source, made))
    groups = list(order.values())
    shape["groups"] = len(groups)
    shape["rows_a_group"] = round(shape["rows"] / max(1, len(groups)), 3)
    # The dedupe needs a resolved key and so lives in [`_resolve`], which is the
    # first place one exists. `known` is taken here so the signature says what
    # the plan is a plan against.
    shape["already_in_ledger"] = None
    return groups, shape


# --------------------------------------------------------------------------- #
# The workers.
# --------------------------------------------------------------------------- #
#: One [`hunt.Maker`] per worker **process**, built on the first block it is
#: handed. [`remode._MAKER`]'s reason: the judge is two seconds to load, so three
#: of them are free and one per group would be most of a chunk.
_MAKER: dict = {}


def _maker_for(name: str, device: str, fields: str):
    from fractal_wallpapers.curation import hunt

    key = (str(name), str(device), str(fields))
    if key not in _MAKER:
        _MAKER[key] = hunt.Maker(name, device=device, log=lambda *_a: None, fields=Path(fields))
    return _MAKER[key]


def render_group(payload: tuple) -> list:
    """One (location, mode) group, start to finish, in one worker. `[(at, result)]`.

    **Module level and taking a plain tuple**, because a Windows pool *spawns* and
    a closure over the plan would not pickle.

    Two kinds of result come back and the incumbent's is the cheap one: its
    picture is already on disk, so it is **read** by the coarse judge and never
    re-rendered. That is a sixth of the pass's candidates costing nothing, and it
    is also the only arrangement under which the six readings are comparable — one
    judge, one process, one batch.

    Through [`mine.make`], which is [`hunt.Maker.make`] with a stopwatch on each
    stage: the same [`colorize.render`], the same judge and the same colour read
    as every candidate already in the ledger. A pass that made its pictures its
    own way would be stocking the pool with rows nothing else could compare to.
    """
    from fractal_wallpapers.curation import colorize
    from fractal_wallpapers.paths import Tiers, rehome

    name, device, fields, pictures, group, deadline = payload
    maker = _maker_for(name, device, fields)
    tiers = Tiers.current()
    out = []
    for at, (incumbent, made) in group:
        if time.monotonic() >= deadline:
            break
        where = rehome(str(incumbent["picture"]), tiers)
        if where is None or not where.is_file():
            out.append((at, {"failed": "the incumbent's picture is not on disk", "rotations": []}))
            continue
        began = colorize.tick()
        read = colorize.score_picture(maker.judge(), where)
        held = {
            "incumbent": {
                "key": incumbent["key"],
                "picture": str(where),
                "verdict": read,
                "seconds": round(colorize.tick() - began, 4),
            },
            "rotations": [],
        }
        # **The deadline is asked once a row and never inside one.** A row cut in
        # half is a decision taken over four candidates while the record says six,
        # which is worse than a row this pass never reached: the six are a
        # best-of-k and k is what the reading means. A row is about two and a half
        # seconds, so that is a fine enough point to stop at.
        for rotation, place, frame, key in made:
            held["rotations"].append(_made(maker, rotation, place, frame, key, pictures))
        out.append((at, held))
    return out


def _made(maker, intention, place: dict, frame: dict, key: str, pictures) -> dict:
    """One candidate, rendered and judged, as both arms' workers carry one.

    [`mine.make`] and what comes back off it, in one place because the two arms
    would otherwise be two spellings of the same act. A failed render is a
    **recorded fact** and not an exception that ends a block: a row is a
    best-of-k and the k that landed is what the reading means, so the failure has
    to reach the decision rather than the log.
    """
    from fractal_wallpapers.curation import mine

    try:
        result = mine.make(maker, intention, place, frame, key, pictures=Path(pictures))
    except Exception as failure:  # noqa: BLE001 — a failed render is a recorded fact
        return {"key": key, "failed": repr(failure)[:400]}
    return {
        "key": key,
        "picture": str(result["picture"]),
        "verdict": result["verdict"],
        "colour": result["colour"],
        "cells": result["cells"],
        "acted": bool(result["acted"]),
        "autolevel": result["autolevel"],
        "texture_flat": bool(result["texture_flat"]),
        "stages": result["stages"].named(),
        "seconds": round(result["stages"].total(), 4),
    }


def render_draw_group(payload: tuple) -> list:
    """One location's **drawn** candidates and their rotations. `[(at, result)]`.

    [`render_group`]'s other half, and the difference is one line: there is no
    picture on disk to read, so the phase-0 candidate is *rendered* like every
    rotation beside it. Everything else — the maker, the dump the group shares,
    the judge, the shape of a result — is the same, which is what makes a mined
    best-of-five readable beside a stored row's best-of-six.

    A separate function rather than a flag, because the two arms disagree about
    what an incumbent **is**: over the store it is a row that already exists and
    the pass may not be able to remove, and here it is the candidate a leg with no
    rotations on the table would have made and nothing else.
    """
    name, device, fields, pictures, group, deadline = payload
    maker = _maker_for(name, device, fields)
    out = []
    for at, (_incumbent, made) in group:
        if time.monotonic() >= deadline:
            break
        held: dict = {"incumbent": None, "rotations": []}
        for intention, place, frame, key in made:
            entry = _made(maker, intention, place, frame, key, pictures)
            if int(intention.k) == 0:
                held["incumbent"] = entry
            else:
                held["rotations"].append(entry)
        if held["incumbent"] is None or held["incumbent"].get("failed"):
            # The phase-0 candidate is the control this whole draw is read
            # against, so a shot that lost it has nothing to report rather than a
            # best-of-four to report as a best-of-five.
            why = (held["incumbent"] or {}).get("failed", "no phase-0 candidate was planned")
            out.append((at, {"failed": why, "rotations": held["rotations"]}))
            continue
        out.append((at, held))
    return out


# --------------------------------------------------------------------------- #
# The fine head.
# --------------------------------------------------------------------------- #
def score_fine(paths: list, device: str = "auto", log=print) -> tuple[list, str]:
    """`([p_fine], column)` — the gallery-grade head's `P(>=4)` over these pictures.

    The shipped ensemble, resolved through [`gallery_grade_train.shipped_runs`]
    and averaged on the **probability** scale, which is `score_pool`'s own path and
    the scale the pool carries and the bar cuts on. No checkpoint is named here: a
    hard-coded run would score this pass's candidates on one column while the pool
    the tolerance is a factor of was read on another, and the whole comparison
    would silently stop meaning anything.

    **The live column is never written.** `score_pool` rewrites the pool's scores
    whole; this reads and returns.
    """
    from fractal_wallpapers.models import gallery_grade_train as grade
    from fractal_wallpapers.models import head, train

    if not paths:
        return [], ""
    arm, seeds, column = grade.shipped_runs()
    loaded = [grade.load_checkpoint(grade.run_dir(arm, one) / "best.pt", device) for one in seeds]
    models = [one[0] for one in loaded]
    config, where = loaded[0][1], loaded[0][2]
    classes = int(config["classes"])
    transform = head.Transform(
        tuple(config["mean"]),
        tuple(config["std"]),
        config["interpolation"],
        train=False,
        target=tuple(config["target_dims"]),
    )
    began = time.time()
    read = train.score_many(models, paths, transform, where, classes, config)
    log(
        f"[rotation] fine head {column} ({len(models)} checkpoint(s)): {len(paths):,} "
        f"picture(s) in {time.time() - began:.0f}s"
    )
    at = classes - 2
    return [float(row[at]) for row in read.mean(axis=0).tolist()], column


# --------------------------------------------------------------------------- #
# The decision.
# --------------------------------------------------------------------------- #
#: What a row's six candidates came to. `held` is the row a guard kept whatever
#: the scores said; `kept` is the incumbent winning on its own merits.
ADOPTED = "adopted"
HELD = "held"
KEPT = "kept"
REFUSED_BY_TOLERANCE = "refused_by_tolerance"
NOTHING_MADE = "nothing_made"

VERDICTS = (ADOPTED, HELD, KEPT, REFUSED_BY_TOLERANCE, NOTHING_MADE)


def decide(incumbent: dict, rotations: list, tolerance: float = TOLERANCE) -> dict:
    """What becomes of one row and its rotations. Pure — decides, deletes nothing.

    Best of the six by `p_fine`. Where the winner is the incumbent there is
    nothing to do; where it is a rotation, [`TOLERANCE`] is asked against the
    **stored** column and the row is replaced only if it clears. `p_coarse` is
    carried on every candidate and gated on for none of them, which is the prompt's
    instruction and also the reading `palette_variant_mine_ckpt120` gives for it:
    the two heads move in opposite directions on 30.8% of matched pairs, so a
    second gate here would be a second rule nobody ruled on.
    """
    made = [held for held in rotations if held.get("p_fine") is not None]
    if not made:
        return {"verdict": NOTHING_MADE, "winner": None, "adopt": None, "remove": None}
    best = max(made, key=lambda held: float(held["p_fine"]))
    fresh = incumbent.get("p_fine")
    if fresh is not None and float(fresh) >= float(best["p_fine"]):
        return {"verdict": KEPT, "winner": incumbent["key"], "adopt": None, "remove": None}
    if float(best["p_fine"]) < float(tolerance) * float(incumbent["stored_p_fine"]):
        return {
            "verdict": REFUSED_BY_TOLERANCE,
            "winner": best["key"],
            "adopt": None,
            "remove": None,
        }
    if incumbent.get("held_by"):
        # The winner is still adopted — a rotation that beats a labelled row is a
        # picture worth having — and what the guard refuses is the **removal**.
        # Both, as the prompt has it: if a labelled row's rotation wins, keep both.
        return {"verdict": HELD, "winner": best["key"], "adopt": best["key"], "remove": None}
    return {
        "verdict": ADOPTED,
        "winner": best["key"],
        "adopt": best["key"],
        "remove": incumbent["key"],
    }


# --------------------------------------------------------------------------- #
# The pass.
# --------------------------------------------------------------------------- #
def _resolve(maker, groups: list, known: set, log=print) -> tuple[list, dict]:
    """Every rotation given its recipe and its key, in the parent. `(groups, census)`.

    Two guards run here and neither costs an engine.

    **The incumbent's own key has to reproduce.** A rotation is built by the
    candidate path — [`hunt.Maker.recipe_for`], the derivation every row in the
    ledger was made through — so the proof that it moved *only* the phase is that
    the same derivation at phase 0 digests to the key the row is already filed
    under. A row whose stored recipe and the live checkout disagree is refused
    rather than rotated: its six candidates would be six pictures of something
    else, compared against a column read on the row it is not.

    **The rebuild carries the row's own palette knobs** — [`Incumbent.pass_knobs`]
    — so what this guard now catches is a real disagreement and not a row whose
    pass the plan could not spell. It refused 43 rows of
    `rotation_pass_ckpt120` on a tuned `gamma` the candidate path never draws, and
    none of those 43 was misfiled: every one digests back to its own key out of its
    own stored recipe, as all 374,309 rows in the store do.

    **A rotation whose key the store already holds is dropped.** All but
    unreachable on a continuous draw, and the same guard every other leg here
    runs.
    """
    from fractal_wallpapers.curation import recipes as recipes_module

    out: list = []
    census = {"rows": 0, "rotations": 0, "already_in_ledger": 0, "key_does_not_reproduce": 0}
    at = 0
    for group in groups:
        held: list = []
        for source, made in group:
            place, frame = source.place(), source.frame()
            zero = Rotation(
                of_key=source.key,
                location=source.location,
                partition=source.partition,
                mode=source.mode,
                colormap=source.colormap,
                k=0,
                phase=0.0,
                palette=source.pass_knobs(),
            )
            again = recipes_module.key_of(maker.recipe_for(zero, place, frame))
            if again != source.key:
                census["key_does_not_reproduce"] += 1
                continue
            resolved = []
            for rotation in made:
                recipe = maker.recipe_for(rotation, place, frame)
                key = recipes_module.key_of(recipe)
                if key in known:
                    census["already_in_ledger"] += 1
                    continue
                resolved.append((rotation, recipe, key))
            if not resolved:
                continue
            at += 1
            census["rows"] += 1
            census["rotations"] += len(resolved)
            held.append((at, source, resolved, place, frame))
        if held:
            out.append(held)
    log(
        f"[rotation] {census['rows']:,} row(s) over {len(out):,} group(s) resolved to "
        f"{census['rotations']:,} rotation(s); {census['key_does_not_reproduce']:,} row(s) "
        f"do not reproduce their own key and are refused"
    )
    return out, census


def _chunks(groups: list, size: int):
    """The groups in runs of `size`, which is the pass's interruption point."""
    for at in range(0, len(groups), max(1, int(size))):
        yield groups[at : at + max(1, int(size))]


def run(
    name: str,
    *,
    bar: float | None = None,
    seed: int = 0,
    tolerance: float = TOLERANCE,
    rotations: int = ROTATIONS,
    budget: float = 3600.0,
    workers: int = WORKERS,
    device: str = "auto",
    chunk: int = CHUNK_GROUPS,
    groups: int | None = None,
    # `take_owed` and not `owed`, which is what the flag is called: the census
    # [`owed`] is read below and a parameter of that name would shadow it for the
    # whole of this function. [`depth.build_plan`]'s `near_named`, same reason.
    take_owed: bool = False,
    world: dict | None = None,
    log=print,
) -> dict:
    """One pass, end to end: render, read, decide, and free what lost. The record.

    The parent resolves every recipe and writes every row; the workers only make
    pictures. The chunk is the loop — a chunk of groups renders on the pool, the
    fine head reads everything the chunk made in **one** batch, the decisions are
    taken and appended, and every rotation that was not adopted has its picture
    and its `<stem>.leveled/` unlinked before the next chunk starts. So the disk
    holds one chunk of undecided candidates and never a pass of them, and a pass
    killed at the clock leaves no picture that is neither adopted nor gone.

    Nothing is merged here and nothing is removed from the store here: this writes
    the rows it would adopt and the keys it would remove into its own two files,
    and [`merge`] is the transaction. Same split as every other leg — the ledger
    is rewritten whole on every upsert, and that is not something to do once a
    chunk.

    ## What a second leg reads is `rows_remaining`, and it is neither count of
    ## groups

    **This arm takes no resume index and needs none.** A clock-bound pass is
    continued by running it again: [`population`] re-reads the store, an adopted
    row's incumbent has been removed and the adoption stands in its place, so what
    the plan comes back holding is what is left. The figure that says how much
    that is — and the only one a next leg or a sizing estimate should be read off
    — is **`counts.rows_remaining`**, which is the resolved passing set less the
    rows actually decided.

    ⚠ **`groups_done` is not it**, and the arithmetic does not convert. It is
    incremented by the whole chunk once the pool returns while each worker breaks
    out of its own group list at the deadline, so it rounds **up** to the chunk:
    `owed_ckpt121` recorded `groups_done: 1600`, exactly four chunks of 400,
    against an honest `rows_remaining: 237` — and 237 rows do not divide into the
    5 groups that arithmetic leaves. `counts.groups_decided` is the honest count
    of groups this pass wrote a decision for, kept beside it for exactly that
    comparison; `groups_done` keeps its meaning, which is what the pool was handed.
    """
    from fractal_wallpapers.curation import candidate_ledger as ledger
    from fractal_wallpapers.curation import colorize, hunt, release
    from fractal_wallpapers.curation.candidate_ledger import sweep

    started = time.monotonic()
    began_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    world = population(bar, owed=bool(take_owed), log=log) if world is None else world
    planned, shape = plan_of(world["sources"], seed, world["known"], rotations)
    build = ledger.live_engine()
    artifact = hunt._artifact()
    maker = hunt.Maker(name, device=device, log=log, fields=fields_dir(name))
    resolved, census = _resolve(maker, planned, world["known"], log=log)
    if groups is not None:
        resolved = resolved[: max(0, int(groups))]
        log(f"[rotation] limited to {len(resolved):,} whole group(s)")

    rows_file = rows_path(name)
    rows_file.parent.mkdir(parents=True, exist_ok=True)
    pictures_dir(name).mkdir(parents=True, exist_ok=True)
    scores_file = scores_path(name)
    decisions_file = decisions_path(name)
    removed_file = removed_path(name)
    plan_file = plan_path(name)
    with plan_file.open("w", encoding="utf-8", newline="\n") as handle:
        for group in resolved:
            for at, source, made, _place, _frame in group:
                handle.write(
                    json.dumps(
                        {
                            "schema": SCHEMA,
                            "at": at,
                            "of_key": source.key,
                            "location": source.location,
                            "mode": source.mode,
                            "colormap": source.colormap,
                            "stored_p_fine": round(source.p_fine, 6),
                            "held_by": source.held_by,
                            "seed": int(seed),
                            "phases": [round(rotation.phase, 6) for rotation, _r, _k in made],
                            "keys": [key for _rotation, _recipe, key in made],
                        }
                    )
                    + "\n"
                )

    counts = dict.fromkeys(VERDICTS, 0)
    counts |= {
        "groups_planned": len(resolved),
        "groups_done": 0,
        # **What came back, against `groups_done`'s what went out**, and the same
        # rounding the mine arm's `blocks_done` has: `owed_ckpt121` recorded
        # `groups_done: 1600`, four whole chunks, against 237 rows left undone.
        # Neither of the two is the figure a second leg reads — see the docstring.
        "groups_decided": 0,
        "rows_visited": 0,
        "rotations_made": 0,
        "rotations_failed": 0,
        "rotations_freed": 0,
        "incumbents_unreadable": 0,
        "stopped_for_budget": 0,
        "fields_swept": 0,
        "autolevel_acted": 0,
    }
    # Three is the machine's rule and not a floor: a pass with fewer groups than
    # workers gets one worker a group, and the record says so.
    held_workers = max(1, min(int(workers), max(1, len(resolved))))
    counts["workers"] = held_workers
    engine_seconds = 0.0
    fine_column = ""
    freed: list = []
    render_started = time.monotonic()
    deadline = render_started + float(budget)
    by_at: dict = {}
    #: Which group each `at` belongs to, so a decision can be counted against the
    #: group it came out of. The mine arm reads the location off the shot; here
    #: the group is [`plan_of`]'s (location, mode) cut and is not on the row.
    group_of = {at: which for which, group in enumerate(resolved) for at, *_rest in group}
    #: The groups this pass has written a decision for. `groups_done` counts the
    #: groups handed to the pool, which a chunk rounds up.
    decided: set = set()

    def payload_of(group: list) -> tuple:
        return (
            name,
            device,
            str(fields_dir(name)),
            str(pictures_dir(name)),
            [
                (
                    at,
                    (
                        {"key": source.key, "picture": source.picture},
                        [(rotation, place, frame, key) for rotation, _recipe, key in made],
                    ),
                )
                for at, source, made, place, frame in group
            ],
            deadline,
        )

    def take_chunk(block: list) -> None:
        """One chunk of groups: rendered, read through the fine head, decided."""
        nonlocal engine_seconds, fine_column
        landed: list = []
        if held_workers <= 1:
            # The serial path is the fallback and not a branch of the pool it
            # falls back FOR: no pool, no pickling, no second Maker.
            for group in block:
                if time.monotonic() >= deadline:
                    continue
                landed += render_group(payload_of(group))
        else:
            from concurrent.futures import ProcessPoolExecutor

            from fractal_wallpapers.curation import depth

            with ProcessPoolExecutor(
                max_workers=held_workers,
                initializer=depth._worker_init,
                initargs=(release.engine_threads_for(held_workers),),
            ) as pool:
                for done, pairs in enumerate(
                    pool.map(render_group, [payload_of(group) for group in block]), start=1
                ):
                    landed += pairs
                    # **Inside the chunk and not at the end of it.** A group's
                    # field is dead the moment its last rotation is painted, and a
                    # chunk is hundreds of groups: swept only between chunks, a
                    # 400-group chunk would hold 1.4 GiB of `.f32` it has no use
                    # for. `colorize.FIELDS_SWEPT_EVERY` is the cadence and
                    # `FIELDS_KEPT` the depth, both read rather than restated.
                    if done % colorize.FIELDS_SWEPT_EVERY == 0:
                        counts["fields_swept"] += colorize.sweep_fields(maker.fields)
                    if done % 250 == 0:
                        log(
                            f"[rotation] {counts['groups_done'] + done:,} of "
                            f"{len(resolved):,} group(s) rendered, "
                            f"{time.monotonic() - render_started:.0f}s of {budget:.0f}s"
                        )
        counts["groups_done"] += len(block)

        # ---- everything this chunk can read, in ONE batch --------------------- #
        paths: list = []
        where: list = []
        for at, result in landed:
            if result.get("failed"):
                counts["incumbents_unreadable"] += 1
                continue
            paths.append(Path(result["incumbent"]["picture"]))
            where.append((at, 0))
            for index, made in enumerate(result["rotations"]):
                if made.get("failed"):
                    counts["rotations_failed"] += 1
                    log(f"[rotation] {made['key']} failed: {made['failed']}")
                    continue
                engine_seconds += float(made.get("seconds") or 0.0)
                counts["rotations_made"] += 1
                counts["autolevel_acted"] += int(made.get("acted") or False)
                paths.append(Path(made["picture"]))
                where.append((at, index + 1))
        read, column = score_fine(paths, device=device, log=log)
        fine_column = column or fine_column
        fine = {held: value for held, value in zip(where, read, strict=True)}

        # ---- the decision, one row at a time ---------------------------------- #
        for at, result in landed:
            if result.get("failed"):
                continue
            source, made, place, frame = by_at[at]
            counts["rows_visited"] += 1
            incumbent = {
                "key": source.key,
                "stored_p_fine": source.p_fine,
                "p_fine": fine.get((at, 0)),
                "p_coarse": float(result["incumbent"]["verdict"].get("p_ge4") or 0.0),
                "held_by": source.held_by,
            }
            candidates = []
            for index, held in enumerate(result["rotations"]):
                if held.get("failed"):
                    continue
                candidates.append(
                    {
                        "key": held["key"],
                        "phase": float(made[index][0].phase),
                        "p_fine": fine.get((at, index + 1)),
                        "p_coarse": float(held["verdict"].get("p_ge4") or 0.0),
                        "picture": held["picture"],
                        "index": index,
                    }
                )
            verdict = decide(incumbent, candidates, tolerance)
            counts[verdict["verdict"]] += 1
            adopted = verdict["adopt"]
            for candidate in candidates:
                if candidate["key"] == adopted:
                    rotation, recipe, key = made[candidate["index"]]
                    won = result["rotations"][candidate["index"]]
                    origin = {
                        "key": f"{name}|{at:05d}",
                        "run": name,
                        "candidate": f"{at:05d}",
                        "location": {"key": source.location, "partition": source.partition},
                    }
                    stored = ledger.row(
                        recipe=recipe,
                        key=key,
                        source=origin,
                        colour=won["colour"],
                        picture=tracked_name(Path(won["picture"])),
                        texture_flat=won["texture_flat"],
                        engine=build,
                    )
                    stored["hunt"] = ledger.hunt_block(
                        {"seconds": won["seconds"], **rotation.named()}
                    )
                    hunt._append(rows_file, stored)
                    hunt._append(
                        scores_file,
                        ledger.score_row(
                            key=key,
                            artifact=artifact,
                            regime=recipe.regime.spelled,
                            head=hunt.kind_of(source.mode, won["texture_flat"]),
                            read=won["verdict"],
                            source=origin,
                        ),
                    )
                else:
                    # Not adopted, so nothing will ever name it. Freed at the end
                    # of the chunk in one call rather than here, because
                    # [`sweep.delete_pictures`] resolves the tiers once.
                    freed.append(candidate["picture"])
            if verdict["remove"]:
                hunt._append(
                    removed_file,
                    {
                        "schema": SCHEMA,
                        "key": verdict["remove"],
                        "replaced_by": adopted,
                        "stored_p_fine": round(source.p_fine, 6),
                        "picture": source.picture,
                    },
                )
            hunt._append(
                decisions_file,
                {
                    "schema": SCHEMA,
                    "at": at,
                    "verdict": verdict["verdict"],
                    "of_key": source.key,
                    "location": source.location,
                    "partition": source.partition,
                    "mode": source.mode,
                    "colormap": source.colormap,
                    "held_by": source.held_by,
                    "winner": verdict["winner"],
                    "adopted": adopted,
                    "removed": verdict["remove"],
                    "incumbent": {
                        "stored_p_fine": round(source.p_fine, 6),
                        "p_fine": incumbent["p_fine"],
                        "p_coarse": round(incumbent["p_coarse"], 6),
                    },
                    "rotations": [
                        {
                            "key": candidate["key"],
                            "phase": candidate["phase"],
                            "p_fine": candidate["p_fine"],
                            "p_coarse": round(candidate["p_coarse"], 6),
                            "seconds": result["rotations"][candidate["index"]]["seconds"],
                        }
                        for candidate in candidates
                    ],
                },
            )
            # After the append and never before it: what this counts is the file.
            decided.add(group_of[at])
        counts["groups_decided"] = len(decided)
        if freed:
            counts["rotations_freed"] += len(freed)
            sweep.delete_pictures(list(freed), log=log)
            freed.clear()
        counts["fields_swept"] += colorize.sweep_fields(maker.fields)
        log(
            f"[rotation] {counts['groups_done']:,} of {len(resolved):,} group(s), "
            f"{counts['rows_visited']:,} row(s): {counts[ADOPTED]:,} adopted, "
            f"{counts[KEPT]:,} kept, {counts[HELD]:,} held, "
            f"{counts[REFUSED_BY_TOLERANCE]:,} under tolerance; "
            f"{time.monotonic() - render_started:.0f}s of {budget:.0f}s"
        )

    for group in resolved:
        for at, source, made, place, frame in group:
            by_at[at] = (source, made, place, frame)

    for block in _chunks(resolved, chunk):
        if time.monotonic() >= deadline:
            counts["stopped_for_budget"] += sum(len(group) for group in block)
            continue
        take_chunk(block)

    counts["rows_remaining"] = census["rows"] - counts["rows_visited"]
    record = {
        "schema": SCHEMA,
        "name": name,
        "began_at": began_at,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seed": int(seed),
        "tolerance": float(tolerance),
        "rotations_a_row": int(rotations),
        "repeat": REPEAT,
        "bar": world.get("bar"),
        # **Which arm this was**, and it is the one knob that changes what the
        # per-row cost means: the owed arm renders six iteration passes a row
        # where the dumpable arm pays one and recolours.
        "owed_arm": bool(world.get("owed", take_owed)),
        "fine_column": fine_column,
        "engine": build,
        "judge_artifact": artifact,
        "population": {
            "ledger_rows": world["ledger_rows"],
            "passing": world["passing"],
            "rotatable": len(world["sources"]),
            "refused": world["refused"],
            "owed": owed(world["refused"]),
            "protected": world["protected"],
        },
        "plan": {**shape, **census},
        "counts": counts,
        "budget": {
            "render_seconds": round(float(budget), 1),
            "render_wall": round(time.monotonic() - render_started, 1),
            "wall_seconds": round(time.monotonic() - started, 1),
            "engine_seconds": round(engine_seconds, 1),
            "seconds_a_rotation": round(engine_seconds / max(1, counts["rotations_made"]), 4),
            "seconds_a_row": round(engine_seconds / max(1, counts["rows_visited"]), 4),
        },
        "files": {
            "rows": tracked_name(rows_file),
            "scores": tracked_name(scores_file),
            "decisions": tracked_name(decisions_file),
            "removed": tracked_name(removed_file),
            "plan": tracked_name(plan_file),
        },
    }
    record_path(name).write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    log(
        f"[rotation] {counts['rows_visited']:,} row(s) visited, {counts[ADOPTED]:,} adopted, "
        f"{counts['rows_remaining']:,} of the passing set remain"
    )
    return record


# --------------------------------------------------------------------------- #
# The mining arm.
# --------------------------------------------------------------------------- #
def drawn_rotations(shot, seed: int, count: int = MINE_ROTATIONS) -> list:
    """One drawn shot expanded into its phase-0 control and `count` rotations.

    The control is the shot **exactly as a leg with no rotations on the table
    would have made it** — same place, same mode, same map, the plain palette
    pass — and it is `k=0`. That is the whole of what makes the five readable: a
    best-of-five over a candidate nobody would have drawn is a number about
    nothing.

    Seeded off the shot's own `(location, mode, colormap)` rather than off a
    stream, for [`draws`]' reason one leg over: a plan truncated at the clock and
    a plan re-run draw the same phases for the same shots.
    """
    from fractal_wallpapers.curation import colorize

    at_zero = Rotation(
        of_key="",
        location=shot.location,
        partition=shot.partition,
        mode=shot.mode,
        colormap=shot.colormap,
        k=0,
        phase=0.0,
        band=str(shot.band),
        arm=str(shot.arm),
        mode_params=dict(shot.mode_params or {}),
    )
    # ⚠ **A direct trap is drawn bare and this is where that happens.** `phase` is
    # a no-op on a trap figure over a flat ground, so a rotation of one would take
    # a second recipe key for a byte-identical picture and put a duplicate in the
    # pool under a name claiming it was varied.
    if colorize.kind_of(shot.mode) == colorize.DIRECT_KIND:
        return [at_zero]
    made = [at_zero]
    for at, phase in enumerate(
        draws(f"{shot.location}|{shot.mode}|{shot.colormap}", seed, count), start=1
    ):
        made.append(
            Rotation(
                of_key="",
                location=shot.location,
                partition=shot.partition,
                mode=shot.mode,
                colormap=shot.colormap,
                k=at,
                phase=float(phase),
                band=str(shot.band),
                arm=str(shot.arm),
                mode_params=dict(shot.mode_params or {}),
                palette={"phase": float(phase)},
            )
        )
    return made


def decided_blocks(name: str) -> int:
    """How many location blocks `name` actually decided. Off `decisions.jsonl`.

    **The file and never the record.** `blocks_done` is incremented by the whole
    chunk once [`render_draw_group`] returns while each worker breaks out of its
    own block list at the deadline, so a leg cut mid-chunk counts blocks it never
    rendered — `mine_ckpt120` recorded 400 against the 247 locations its
    `decisions.jsonl` holds. A decision row is written only after a shot's five
    candidates have been read and one of them adopted, so a location that appears
    in that file was rendered and a location that does not was not.

    A block is the **location**, which is [`depth.blocks_of`]'s cut, so this
    counts distinct `location` values and not rows: a location at 11 of its 12
    shots counts once, and resuming past it gives up those 11.
    """
    path = decisions_path(name)
    if not path.is_file():
        return 0
    seen: set[str] = set()
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                seen.add(str(json.loads(line)["location"]))
    return len(seen)


def resume_index(name: str) -> int:
    """The index `--from-block` wants to continue `name`. **The honest figure.**

    Where `name` picked up plus what it decided — `from_block` off its record and
    [`decided_blocks`] off its decisions — because `--from-block` indexes the
    **whole** plan and a resumed leg's own file holds only its own half. So
    `mine_ckpt120` resumes at 247 and the leg that resumed it, having skipped 247
    and decided 129, resumes at 376.

    Every mine record carries this as `resume_from_block`; this recomputes it from
    the files so that a record written before that field existed still answers.
    """
    record = record_path(name)
    at = 0
    if record.is_file():
        at = int(json.loads(record.read_text(encoding="utf-8")).get("from_block") or 0)
    return at + decided_blocks(name)


def plan_identity(
    *,
    seed: int,
    rate: float,
    plan_budget: float,
    width: int,
    workers: int,
    roster,
    shares: dict,
) -> tuple:
    """What has to agree for two mine legs to be halves of one block plan.

    Everything [`depth.build_plan`] is sized and drawn off:
    `PLAN_HEADROOM * workers * plan_budget / rate` for the count, and the seed,
    the width, the roster and the split for the draw. A leg that changed any of
    them rebuilt a **different** plan under the resume's name, which is the defect
    `overnight_ckpt121` caught by restating `--rate`: the flag defaults to
    [`MINE_RATE`] 2.5 where `mine_ckpt120` ran at 6.0, so an unrestated resume
    would have planned 27,648 shots against the first leg's 11,520.

    ⚠ **A zero share is not part of the identity.** The resolved table grows a key
    whenever a draw is added to [`depth.DRAWS`] — `conditioned` landed between
    these two legs — so comparing the tables whole would refuse a legitimate
    resume over an arm neither leg spent a second on.
    """
    spent = {arm: float(value) for arm, value in dict(shares).items() if float(value)}
    return (
        int(seed),
        float(rate),
        float(plan_budget),
        int(width),
        int(workers),
        tuple(str(one) for one in roster),
        tuple(sorted(spent.items())),
    )


def identity_of(record: dict) -> tuple:
    """[`plan_identity`] off a record, so the live leg and the recorded one agree.

    `plan_budget_seconds` and `from_block` landed with the resume protocol on
    2026-09-12, so a record written before it answers off `plan.budget_seconds` —
    which is the same number for a first leg, being the only budget it had.
    """
    plan = dict(record.get("plan") or {})
    return plan_identity(
        seed=int(record.get("seed") or 0),
        rate=float(plan.get("rate_seconds") or 0.0),
        plan_budget=float(record.get("plan_budget_seconds") or plan.get("budget_seconds") or 0.0),
        width=int(plan.get("width") or record.get("width") or 0),
        workers=int(plan.get("workers_sized_for") or 0),
        roster=record.get("roster") or (),
        shares=record.get("shares") or {},
    )


def resumable(identity: tuple) -> dict:
    """`{name: resume_index}` over every mine leg on record that ran this plan.

    The store's own legs, read off their records — [`rotation_dir`]'s siblings —
    because a resume names no first leg and there is nothing else to ask. A leg
    whose [`plan_identity`] differs is not a half of this plan and is not offered,
    which is what makes the guard in [`mine`] refuse a resume whose `--rate` or
    `--plan-budget` was left on the default.
    """
    root = store_root()
    if not root.is_dir():
        return {}
    out: dict = {}
    for held in sorted(root.iterdir()):
        record = held / RECORD_NAME
        if not held.is_dir() or not record.is_file():
            continue
        try:
            read = json.loads(record.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if str(read.get("arm")) != "mine" or identity_of(read) != identity:
            continue
        out[held.name] = resume_index(held.name)
    return out


def refuse_unreachable_resume(from_block: int, *, log=print, **identity) -> dict:
    """Refuse a `--from-block` above what any leg of this plan actually rendered.

    **Passing one always discards work that was paid for**, which is what makes
    this an error and not a warning: the blocks between what was rendered and the
    index asked for are blocks the first leg drew, dumped fields for and rendered
    candidates into, and skipping them throws that away with nothing in the store
    to say it happened — each shot's four losers are freed rather than merged.
    `overnight_ckpt121` was handed `--from-block 400` off `blocks_done` against
    247 rendered: 153 locations, about 1,836 shots.

    Run **before the population read**, so an unattended leg fails in its first
    seconds rather than four hours in. `{name: index}` of the legs it accepted is
    returned so a caller can say which one it is continuing.
    """
    if int(from_block) <= 0:
        return {}
    held = resumable(plan_identity(**identity))
    if not held:
        raise RotationRefused(
            f"--from-block {int(from_block):,} names a plan no mine leg on record ran, so "
            f"there is nothing to continue and every block skipped would be a block nobody "
            f"rendered. A resume rebuilds the first leg's plan exactly, which means "
            f"restating its --seed, --rate, --plan-budget, --width, --workers, --roster and "
            f"--shares: the plan is PLAN_HEADROOM * workers * plan_budget / rate, and --rate "
            f"defaulting to {MINE_RATE:g} where the first leg ran at another value is the "
            f"usual cause."
        )
    reached = max(held.values())
    if int(from_block) > reached:
        raise RotationRefused(
            f"--from-block {int(from_block):,} is above the {reached:,} location block(s) "
            f"this plan has actually rendered, so {int(from_block) - reached:,} block(s) of "
            f"paid-for work would be skipped and never merged. Pass `resume_from_block` off "
            f"the record and not `blocks_done`, which counts the blocks handed to the pool "
            f"and not the ones that came back: "
            f"{', '.join(f'{name} {at:,}' for name, at in sorted(held.items()))}."
        )
    log(
        f"[rotation] resuming a plan {len(held)} leg(s) have run, the furthest to block "
        f"{reached:,}: {', '.join(f'{name} {at:,}' for name, at in sorted(held.items()))}"
    )
    return held


def resumed(
    blocks: list, from_block: int, plan_budget: float, budget: float, log=print
) -> tuple[list, int]:
    """The block plan with the blocks a first leg already did dropped. `(blocks, n)`.

    **A slice of the whole plan and nothing else.** The plan is rebuilt entire —
    which is what [`mine`]'s `plan_budget` is for — so that block N here is the
    same block N the first leg had, and then the ones it finished come off the
    front. Everything downstream is unchanged: the phases are seeded off each
    shot's own `(location, mode, colormap)`, so a block draws what it would have
    drawn whenever it is reached.

    An index past the end leaves nothing on the table rather than raising, and says
    so: a leg told to resume past its own plan has finished, and that is a fact to
    report and not an error to handle.
    """
    planned = len(blocks)
    skipped = max(0, min(int(from_block), planned))
    if not skipped:
        return blocks, 0
    held = blocks[skipped:]
    log(
        f"[rotation] resumed at block {skipped:,} of {planned:,}: {len(held):,} block(s) "
        f"on the table, the plan sized off {float(plan_budget):,.0f}s and the clock "
        f"{float(budget):,.0f}s"
    )
    return held, skipped


def mine(
    name: str,
    *,
    seed: int = 0,
    rate: float = MINE_RATE,
    budget: float = 3600.0,
    width: int = MINE_WIDTH,
    rotations: int = MINE_ROTATIONS,
    roster: list | None = None,
    shares: dict | None = None,
    #: The budget the PLAN is sized off, where that is not the clock this leg has.
    #: Unsaid it is `budget`, which is every first leg. A **resumed** leg says both:
    #: the plan budget rebuilds the same block plan and `budget` is what is left to
    #: spend on it.
    plan_budget: float | None = None,
    #: Whole blocks of that plan to skip, so a second leg continues the first
    #: rather than re-drawing it. See the docstring.
    from_block: int = 0,
    workers: int = WORKERS,
    device: str = "auto",
    chunk: int = CHUNK_GROUPS,
    log=print,
) -> dict:
    """A standard mining leg where every candidate is the best of five phases.

    **Standard process and standard mode policy**: the draw is
    [`depth.build_plan`]'s, over [`mode_policy.mined`]'s roster, and the one thing
    that differs from a production depth leg is that each drawn shot becomes a
    phase-0 control plus [`MINE_ROTATIONS`] rotations, all five are read through
    the fine head, and the best of them is the row that merges.

    ⚠ **The four that lose are recorded and not merged, and both halves matter.**
    Merging all five would put four near-duplicates of one picture in the pool at
    one (location, mode), which the retention rule would then spend its keep on.
    Recording only the winner is the other failure and is the subtler one: a store
    that keeps the argmax of five and forgets the five is the
    selected-at-one-phase bias again, one level up, and every rate read off it
    would be a winner's-curse estimate with nothing beside it to correct by.
    `decisions.jsonl` carries all five with their drawn phases and both columns.

    The block is the **location** rather than the (location, mode) pair, because
    that is [`depth.blocks_of`]'s cut and a location's every mode shares one
    worker and therefore one field cache.

    **A clock-bound leg is resumed by INDEX and never by re-drawing.** `budget`
    sizes the plan *and* is the deadline, so a second leg handed the clock it has
    left would plan a smaller draw and start it at the beginning — and the dedupe
    does not save it: each shot's four losers are recorded and **freed** rather
    than merged, so nothing in the store says they were made. Worse, where a
    rotation won and its control did not merge, the shot comes back as a
    best-of-*four* read against the same control, which is a different number
    under the same name. So a resumed leg says `plan_budget` — the first leg's
    budget, which rebuilds its block plan exactly — and `from_block`. `budget` is
    then only the clock. The record carries both, and `blocks_skipped` beside
    `blocks_planned`, so the two legs read back as one.

    ⚠⚠ **"Rebuilds its block plan exactly" is true of the flags and FALSE of the
    population, and that is the bigger of the two defects here.** The plan is a
    deterministic function of the **drawable pool**, and `hunt.drawable` is the
    admitted population less `hunt.opened_locations` — so every location this leg
    merges leaves the pool, `depth.ranked_bands` re-cuts its bands over what is
    left, and each cell is re-shuffled. Reconstructed 2026-09-12 over the live
    store: put `mine_ckpt120`'s locations back in the pool and its 247 blocks come
    back 247 of 247 in order; take them out again and its resume's 129 come back
    at indices 248-376, with **none of the first leg's 247 in that plan at all**.
    So a resume cannot re-render merged work on this arm — which is why the
    `already_in_ledger` census below reads 0 by construction — and cannot continue
    anything either: the index skips fresh blocks. `curation/LEGS.md`'s
    *`--from-block` cannot continue a mining plan, because a merge moves it* has
    the measurement and names the arms where it does bite.

    ⚠ **`rate` rebuilds the plan too, and `from_block` is not `blocks_done`.**
    The plan is `PLAN_HEADROOM * workers * plan_budget / rate`, so a resume that
    leaves `rate` on [`MINE_RATE`] while the first leg ran at another one rebuilds
    a *different* plan under the resume's name. And `blocks_done` is incremented
    by the whole chunk once [`render_draw_group`] returns, while each worker
    breaks out of its own block list at the deadline — so a leg cut mid-chunk
    counts blocks it never rendered. `mine_ckpt120` reported 400 against a chunk
    of 400 and had rendered 247. `curation/LEGS.md`'s *A clock-bound leg is
    resumed by INDEX, never by re-drawing* has the reading.

    **The field to pass is `resume_from_block` and nothing else.** It is written
    on every record beside `from_block` — where this leg picked up against where
    the next one should — and it is [`resume_index`]: the blocks this leg skipped
    plus the locations its `decisions.jsonl` actually holds. `blocks_done` is
    kept, unchanged, as what it has always been: the blocks handed to the pool.

    **An over-large `from_block` is refused here, before the population read.**
    [`resumable`] offers the legs on record that ran *this* plan and what each of
    them reached; an index above the best of those discards rendered work every
    time it is passed, and four hours is the wrong place to find that out.
    """
    from fractal_wallpapers.curation import candidate_ledger as ledger
    from fractal_wallpapers.curation import colorize, depth, hunt, mode_policy, release
    from fractal_wallpapers.curation import recipes as recipes_module
    from fractal_wallpapers.curation.candidate_ledger import sweep

    started = time.monotonic()
    began_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    roster = list(roster) if roster else mode_policy.mined()
    # ⚠ `curate depth`'s own default roster is the three SHAREABLE modes and not
    # the policy's twelve, and nothing warns — `palette_variant_mine_ckpt120`'s
    # pilot ran on it by accident. The default here is the policy.
    # **The whole table and not one entry**, because `build_plan` merges what it is
    # given over `depth.SHARES` — so naming the ranked share alone would leave the
    # near-band and flat draws on their defaults and spend half this leg on arms
    # the last producing leg zeroed. `palette_variant_mine_ckpt120`'s shape.
    shares = dict(shares) if shares else dict(MINE_SHARES)
    sized_for = float(budget if plan_budget is None else plan_budget)
    refuse_unreachable_resume(
        int(from_block),
        seed=int(seed),
        rate=float(rate),
        plan_budget=sized_for,
        width=int(width),
        workers=int(workers),
        roster=roster,
        shares=shares,
        log=log,
    )
    world = depth.population(log=log)
    intended, shape = depth.build_plan(
        world,
        seed=int(seed),
        rate=float(rate),
        budget=sized_for,
        width=int(width),
        roster=roster,
        shares=shares,
        workers=int(workers),
        log=log,
    )
    build = ledger.live_engine()
    artifact = hunt._artifact()
    maker = hunt.Maker(name, device=device, log=log, fields=fields_dir(name))
    known = set(world["known"]) | {str(row["key"]) for row in world["rows"]}

    # The plan resolved: every shot's five recipes and keys, in the parent.
    order: dict = {}
    # ⚠ **`already_in_ledger` reads 0 on a wholly RANKED leg however the draw
    # goes, and that is arithmetic rather than a clean bill of health.** The
    # ranked, flat and aimed draws all come out of `world["pools"]`, which is
    # `hunt.drawable` — the admitted population less `hunt.opened_locations` — so
    # a shot is always at a location the ledger has never stood on and its keys
    # cannot be ones the ledger holds. Measured 2026-09-12 on a rebuild over the
    # live store: 46,080 keys drawn, 0 hits, against 2,950 of `mine_ckpt120`'s
    # 2,954 adopted keys present in this very `known` set. It counts something
    # real only where the split spends on `near_band`, `mode_floor` or
    # `conditioned`, which draw at OPENED locations — and there it catches
    # exactly the one candidate of five that merged, dropping the shot outright
    # when that was the k=0 control. See the docstring.
    census = {"shots": 0, "candidates": 0, "already_in_ledger": 0, "unresolvable": 0, "bare": 0}
    at = 0
    for shot in intended:
        place = world["by_key"].get(shot.location)
        if place is None:
            census["unresolvable"] += 1
            continue
        frame = hunt.frame_for(place, world["index"])
        made = []
        for intention in drawn_rotations(shot, int(seed), int(rotations)):
            recipe = maker.recipe_for(intention, place, frame)
            key = recipes_module.key_of(recipe)
            if key in known:
                census["already_in_ledger"] += 1
                continue
            known.add(key)
            made.append((intention, recipe, key, place, frame))
        if not made or int(made[0][0].k) != 0:
            # No control, no comparison — see [`render_draw_group`].
            census["already_in_ledger"] += len(made)
            continue
        at += 1
        census["shots"] += 1
        census["candidates"] += len(made)
        census["bare"] += int(len(made) == 1)
        order.setdefault(shot.location, []).append((at, shot, made))
    blocks = list(order.values())
    log(
        f"[rotation] {census['shots']:,} shot(s) over {len(blocks):,} location block(s) "
        f"resolved to {census['candidates']:,} candidate(s), {census['bare']:,} of them a "
        f"direct trap drawn bare"
    )
    planned_blocks = len(blocks)
    blocks, skipped = resumed(blocks, from_block, sized_for, float(budget), log=log)

    rows_file = rows_path(name)
    rows_file.parent.mkdir(parents=True, exist_ok=True)
    pictures_dir(name).mkdir(parents=True, exist_ok=True)
    scores_file = scores_path(name)
    decisions_file = decisions_path(name)
    counts = {
        # **The whole plan's count, not the slice's**, so `blocks_done` and
        # `blocks_skipped` add up against it across both halves of one leg.
        "blocks_planned": planned_blocks,
        "blocks_skipped": skipped,
        "blocks_done": 0,
        # **What came back, against `blocks_done`'s what went out.** Filled from
        # [`decided`] at the end, and the record's `resume_from_block` is this
        # plus `blocks_skipped`. See [`decided_blocks`].
        "blocks_decided": 0,
        "shots_visited": 0,
        "candidates_made": 0,
        "candidates_failed": 0,
        "candidates_freed": 0,
        "control_won": 0,
        "rotation_won": 0,
        "bare": 0,
        "lost_the_control": 0,
        "stopped_for_budget": 0,
        "fields_swept": 0,
        "autolevel_acted": 0,
    }
    held_workers = depth.workers_for(blocks, int(workers), log=log)
    counts["workers"] = held_workers
    engine_seconds = 0.0
    fine_column = ""
    freed: list = []
    #: The locations this leg has written a decision for, which is the only thing
    #: that says where it got to: `blocks_done` counts what was handed to the
    #: pool and a worker breaks out of its own block list at the deadline.
    #: Distinct locations rather than shots, because the block is the location.
    decided: set = set()
    render_started = time.monotonic()
    deadline = render_started + float(budget)
    by_at = {at: (shot, made) for block in blocks for at, shot, made in block}

    def payload_of(block: list) -> tuple:
        return (
            name,
            device,
            str(fields_dir(name)),
            str(pictures_dir(name)),
            [
                (
                    at,
                    (
                        None,
                        [
                            (intention, place, frame, key)
                            for intention, _r, key, place, frame in made
                        ],
                    ),
                )
                for at, _shot, made in block
            ],
            deadline,
        )

    def take_chunk(block: list) -> None:
        nonlocal engine_seconds, fine_column
        landed: list = []
        if held_workers <= 1:
            for one in block:
                if time.monotonic() >= deadline:
                    continue
                landed += render_draw_group(payload_of(one))
        else:
            from concurrent.futures import ProcessPoolExecutor

            with ProcessPoolExecutor(
                max_workers=held_workers,
                initializer=depth._worker_init,
                initargs=(release.engine_threads_for(held_workers),),
            ) as pool:
                for done, pairs in enumerate(
                    pool.map(render_draw_group, [payload_of(one) for one in block]), start=1
                ):
                    landed += pairs
                    if done % colorize.FIELDS_SWEPT_EVERY == 0:
                        counts["fields_swept"] += colorize.sweep_fields(maker.fields)
        counts["blocks_done"] += len(block)

        paths: list = []
        where: list = []
        for at, result in landed:
            if result.get("failed"):
                counts["lost_the_control"] += 1
                freed.extend(
                    one["picture"] for one in result.get("rotations", ()) if one.get("picture")
                )
                continue
            for index, one in enumerate([result["incumbent"], *result["rotations"]]):
                if one.get("failed"):
                    counts["candidates_failed"] += 1
                    continue
                engine_seconds += float(one.get("seconds") or 0.0)
                counts["candidates_made"] += 1
                counts["autolevel_acted"] += int(one.get("acted") or False)
                paths.append(Path(one["picture"]))
                where.append((at, index))
        read, column = score_fine(paths, device=device, log=log)
        fine_column = column or fine_column
        fine = dict(zip(where, read, strict=True))

        for at, result in landed:
            if result.get("failed"):
                continue
            shot, made = by_at[at]
            counts["shots_visited"] += 1
            five = []
            for index, one in enumerate([result["incumbent"], *result["rotations"]]):
                if one.get("failed"):
                    continue
                intention, recipe, key, _place, _frame = made[index]
                five.append(
                    {
                        "key": key,
                        "k": int(intention.k),
                        "phase": float(intention.phase),
                        "p_fine": fine.get((at, index)),
                        "p_coarse": round(float(one["verdict"].get("p_ge4") or 0.0), 6),
                        "seconds": one["seconds"],
                        "index": index,
                        "picture": one["picture"],
                    }
                )
            readable = [one for one in five if one["p_fine"] is not None]
            if not readable:
                freed.extend(one["picture"] for one in five)
                continue
            best = max(readable, key=lambda one: float(one["p_fine"]))
            counts["rotation_won"] += int(best["k"] > 0)
            counts["control_won"] += int(best["k"] == 0)
            counts["bare"] += int(len(five) == 1)
            intention, recipe, key, _place, _frame = made[best["index"]]
            won = [result["incumbent"], *result["rotations"]][best["index"]]
            origin = {
                "key": f"{name}|{at:05d}",
                "run": name,
                "candidate": f"{at:05d}",
                "location": {"key": shot.location, "partition": shot.partition},
            }
            stored = ledger.row(
                recipe=recipe,
                key=key,
                source=origin,
                colour=won["colour"],
                picture=tracked_name(Path(won["picture"])),
                texture_flat=won["texture_flat"],
                engine=build,
            )
            # The SHOT's own block, plus what this pass added to it: the drawn
            # phase and how many candidates it won against. `shot.named()` carries
            # the arm, the band and the rank, which is what a mining readout is
            # banded on and what a row that had forgotten them could not be in.
            stored["hunt"] = ledger.hunt_block(
                {
                    "seconds": won["seconds"],
                    **shot.named(),
                    "palette_drawn": dict(intention.palette),
                    "best_of": len(readable),
                }
            )
            hunt._append(rows_file, stored)
            hunt._append(
                scores_file,
                ledger.score_row(
                    key=key,
                    artifact=artifact,
                    regime=recipe.regime.spelled,
                    head=hunt.kind_of(shot.mode, won["texture_flat"]),
                    read=won["verdict"],
                    source=origin,
                ),
            )
            freed.extend(one["picture"] for one in five if one["index"] != best["index"])
            hunt._append(
                decisions_file,
                {
                    "schema": SCHEMA,
                    "at": at,
                    "arm": shot.arm,
                    "band": shot.band,
                    "location": shot.location,
                    "partition": shot.partition,
                    "mode": shot.mode,
                    "colormap": shot.colormap,
                    "rank_fraction": shot.rank_fraction,
                    "adopted": key,
                    "winner_k": best["k"],
                    # ⚠ All five, losers included. A store that keeps the argmax
                    # and forgets what it was the argmax OF is the
                    # selected-at-one-phase bias one level up.
                    "candidates": [
                        {
                            name_: one[name_]
                            for name_ in ("key", "k", "phase", "p_fine", "p_coarse", "seconds")
                        }
                        for one in five
                    ],
                },
            )
            # After the append and never before it: what this counts is the file.
            decided.add(str(shot.location))
        counts["blocks_decided"] = len(decided)
        if freed:
            counts["candidates_freed"] += len(freed)
            sweep.delete_pictures(list(freed), log=log)
            freed.clear()
        counts["fields_swept"] += colorize.sweep_fields(maker.fields)
        log(
            f"[rotation] {skipped + counts['blocks_done']:,} of {planned_blocks:,} block(s), "
            f"{counts['shots_visited']:,} shot(s): {counts['rotation_won']:,} won by a "
            f"rotation, {counts['control_won']:,} by phase 0; "
            f"{time.monotonic() - render_started:.0f}s of {budget:.0f}s"
        )

    for one in _chunks(blocks, chunk):
        if time.monotonic() >= deadline:
            counts["stopped_for_budget"] += sum(len(held) for held in one)
            continue
        take_chunk(one)

    record = {
        "schema": SCHEMA,
        "name": name,
        "arm": "mine",
        "began_at": began_at,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seed": int(seed),
        "rotations_a_shot": int(rotations),
        "repeat": REPEAT,
        "roster": roster,
        # **The resolved table here and what was asked beside it**, not the ask
        # alone: this line used to be the caller's dict, which reads as the split
        # the leg ran and is only that when the caller spelled it whole.
        # [`depth.resolve_split`] is where both come from.
        "shares": dict(shape["split"]["shares"]),
        "shares_asked": dict(shares),
        # **What the plan was sized off and where this leg picked it up**, which is
        # the whole of what makes two clock-bound halves one leg.
        "plan_budget_seconds": sized_for,
        "from_block": skipped,
        # **Where the NEXT leg starts, and the only field `--from-block` takes.**
        # `blocks_skipped` plus the locations `decisions.jsonl` actually holds —
        # [`resume_index`] recomputes exactly this off the files. It is not
        # `blocks_skipped + blocks_done`: that counts the blocks handed to the
        # pool, and a leg cut mid-chunk is handed more than it renders.
        "resume_from_block": skipped + counts["blocks_decided"],
        "width": int(width),
        "fine_column": fine_column,
        "engine": build,
        "judge_artifact": artifact,
        "plan": {**shape, **census},
        "counts": counts,
        "budget": {
            "render_seconds": round(float(budget), 1),
            "render_wall": round(time.monotonic() - render_started, 1),
            "wall_seconds": round(time.monotonic() - started, 1),
            "engine_seconds": round(engine_seconds, 1),
            "seconds_a_candidate": round(engine_seconds / max(1, counts["candidates_made"]), 4),
            "seconds_a_shot": round(engine_seconds / max(1, counts["shots_visited"]), 4),
        },
        "files": {
            "rows": tracked_name(rows_file),
            "scores": tracked_name(scores_file),
            "decisions": tracked_name(decisions_file),
        },
    }
    record_path(name).write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    log(
        f"[rotation] {counts['shots_visited']:,} shot(s), {counts['candidates_made']:,} "
        f"candidate(s) made, {counts['rotation_won']:,} won by a rotation"
    )
    # ⚠ **Printed, because the number a resume needs should not need the record.**
    # `blocks_done` is what the pool was handed and reads as progress; this is what
    # came back. `mine_ckpt120` logged 400 and had decided 247.
    log(
        f"[rotation] resume this plan at --from-block {record['resume_from_block']:,} "
        f"({skipped:,} skipped + {counts['blocks_decided']:,} decided of "
        f"{counts['blocks_done']:,} handed to the pool), with --plan-budget "
        f"{sized_for:,.0f} --rate {float(rate):g} --seed {int(seed)} --width {int(width)}"
    )
    return record


def merge(name: str, apply: bool = True, log=print) -> dict:
    """Put this pass's adoptions in the store, and take the rows they replace out.

    **The removal runs first**, which is the one ordering decision here and is not
    arbitrary. A rotation lands on the same `(location, mode)` pair its incumbent
    stands in — the palette is not part of what [`retention`] pairs on — so merging
    first would hand [`sweep.prune`] a pair one row over its real size and let the
    rule evict a **third** row that this pass never decided anything about.
    Removed first, the pair is back at the size it was when the door prunes, and
    the only rows that move are the ones on the record.

    Then [`candidate_ledger.merge`] — THE door, and the same one every leg comes
    through: the upsert, the flatness sweep, the prune and all four manifests.

    **A pass whose pictures have been swept is refused before the removal**, which
    is why the door's own copy of that guard is not enough: the removal above runs
    first and is the irreversible half, so a swept pass caught only at the door
    would already have taken its 19 live rows out. See [`sweep.refuse_swept`].
    """
    from fractal_wallpapers.curation import hunt
    from fractal_wallpapers.curation.candidate_ledger import sweep

    sweep.refuse_swept([rotation_dir(name)])
    rows = hunt._read(rows_path(name))
    scores = hunt._read(scores_path(name))
    removing = hunt._read(removed_path(name))
    if not rows and not removing:
        raise RotationRefused(
            f"{tracked_name(rows_path(name))} holds no row and "
            f"{tracked_name(removed_path(name))} names nothing to remove, so there is "
            f"nothing to merge. This pass writes both as it decides; two empty files mean "
            f"no row was decided."
        )
    taken = (
        sweep.remove(
            [str(row["key"]) for row in removing],
            why=f"rotation/{name}",
            apply=apply,
            log=log,
        )
        if removing
        else None
    )
    written = candidate_ledger.merge(rows, scores, log=log) if rows and apply else None
    report = {
        "schema": SCHEMA,
        "name": name,
        "applied": bool(apply),
        "removed": taken,
        "merged": len(rows),
        "ledger": None if written is None else written["ledger"],
        "scores": None if written is None else written["scores"],
        "recorded": None if written is None else written["recorded"],
        "repeat_draws": None if written is None else written["repeat_draws"],
        "pruned": None if written is None else written["pruned"],
        "locations_touched": len({str((row.get("location") or {})["key"]) for row in rows}),
    }
    if apply:
        merge_path(name).write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
    log(
        f"[rotation] removed {0 if taken is None else taken['in_the_store']:,} row(s) and "
        f"merged {len(rows):,}"
    )
    return report


def read(name: str) -> dict:
    """One finished pass's record, read back. Raises if it never wrote one."""
    path = record_path(name)
    if not path.is_file():
        raise RotationRefused(
            f"{tracked_name(path)} does not exist, so there is no rotation pass by that "
            f"name on this machine. `curate rotate run --name {name}` writes it."
        )
    return json.loads(path.read_text(encoding="utf-8"))


__all__ = [
    "ADOPTED",
    "CHUNK_GROUPS",
    "DECISIONS_NAME",
    "HELD",
    "KEPT",
    "MERGE_NAME",
    "MINE_RATE",
    "MINE_ROTATIONS",
    "MINE_SHARES",
    "MINE_WIDTH",
    "NOTHING_MADE",
    "NOT_OWED",
    "PLAN_NAME",
    "RECORD_NAME",
    "REFUSALS",
    "REFUSED_BY_TOLERANCE",
    "REMOVED_NAME",
    "REPEAT",
    "ROTATIONS",
    "ROWS_NAME",
    "SCHEMA",
    "SCORES_NAME",
    "TOLERANCE",
    "UNIT",
    "VERDICTS",
    "WORKERS",
    "Incumbent",
    "Rotation",
    "RotationRefused",
    "decide",
    "decisions_path",
    "drawn_rotations",
    "draws",
    "fields_dir",
    "merge",
    "mine",
    "merge_path",
    "owed",
    "passing",
    "pictures_dir",
    "plan_of",
    "plan_path",
    "holder_of",
    "population",
    "protections",
    "read",
    "record_path",
    "refusal_of",
    "removed_path",
    "render_draw_group",
    "render_group",
    "resumed",
    "rotation_dir",
    "rows_path",
    "run",
    "score_fine",
    "scores_path",
]
