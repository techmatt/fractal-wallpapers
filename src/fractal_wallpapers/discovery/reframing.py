"""The reframing channel: an operator's own view, scored and recorded as a location.

The walk fires the reframing operators and pushes what they build onto the
frontier as a **node**. Only what `expand` draws *below* a node becomes a
candidate, so the nucleus-centred picture the operator constructed is never
scored, never gated, never ledgered — measured on one production harvest, 0 of
14,678 distinct available reframing viewports appear as a candidate viewport. The
walk then descends straight into the atom's black body: over twelve ledgers the
42,904 candidates below a reframing sit at a median of 1.66 atom sizes, and 9,432
of their interior-cap refusals are there. That is why the standing candidate pool
holds fourteen frames that are minibrot centres in the sense the gallery wants,
and why no seating has ever held more than one.

This channel is the other half of that operator. It fires them at **seeds**,
takes the view they build as a **candidate**, and writes it to a walk-shaped
ledger the supply union already reads. Nothing about the walk changes.

```text
proven roots (label store, q3 and q4, parameter planes, pins excluded)
        │  snap_at_seed             the atom the judged view is centred on
        │  expand_neighborhood      distinct atoms around it
        ▼
   one nucleus                      deduplicated on the atom key, across the run
        │  16x / 24x / 32x          the three rungs, offered directly
        ▼
   engine.screen                    the walk's own gate battery, node regime
        │  the location head over the frames it just drew
        ▼
   ONE candidate row                the rung the head picked, every rung recorded
```

## Four rulings this module is the shape of

**An operator's own view is a candidate.** The maker's rule, and the finding the
audit closed on. Whatever the operators build here is scored, gated and recorded;
it is not a place to descend from.

**One nucleus is one location, and the rungs are its framings.** A nucleus at
three widths is not three locations — that would put one atom into three seats
and would count one find three times in every book downstream. So the three rungs
are drawn, all three are scored, all three readings are on the row, and the
location's own score is the rung the head picked. The rungs are **offered
directly** rather than walked to, because the built refinement moves x1.414 a
step ([`curation.framing.WIDTH_LADDER`]) and cannot reach 32x from 16x in one
move.

**Record and rank, never gate.** Every derived nucleus is scored and written,
whatever the head said. Distinctness is applied where a *sheet* is cut and never
to the ledger, so a sitting never sees fifty lookalikes off one seed and the
record still says what the channel found.

**The seed is a place a person judged.** Which is why [`operators.snap_at_seed`]
exists and why every derived row carries the seed's tier: the claim being
inherited is somebody's verdict on a picture, and a channel that could not say
whose verdict, at what tier, would be unpriceable.

## Why 24x and 32x, and why not 4x

Measured body width of eleven ring-seeded atoms at 1280 px
(`scratch/framing_ladder.jsonl`): 115-183 px at the 16x rung, 57-92 px at 32x,
28-45 px at 64x. The band that reads as *a minibrot with detail around it* is
50-100 px, which is the 32x rung and nothing else; the walk's widest rung, 16x, is
a factor of two too tight. 24x is the rung in between, carried because nothing has
ever been labelled at either and the head's pick across the three is itself the
measurement.

Nothing below 16x is offered. The 2x frame is 50-75% interior and is refused
outright by the walk's own `interior_cap`; 4x is the walk's "is this atom any
good" frame and this channel is not asking that question.

## What is priced, and against what

Every row carries the seconds its operator spent and the Newton solves it charged,
per operator and per rung, so "candidates per operator-minute" is a division on
the record rather than a stopwatch reading. That is the number an evening leg is
sized against: the target is a thousand nuclei the location head scores q4, and
the channel's own yield per minute is what says whether a night reaches it.

## Generations

A nucleus the head scores at or above the q4 admission bar — the keeper floor on
`P(>=3)` **and** the great cut on `P(>=4)`, both through
[`supply.currency`] rather than restated — is a seed for the next generation, and
its generation number is on its row. The loop is bounded by `--generations`;
generation 1 alone is the channel firing at proven roots exactly.
"""

from __future__ import annotations

import json
import math
import random
import time
from dataclasses import dataclass, field
from pathlib import Path

from fractal_wallpapers import engine
from fractal_wallpapers.discovery import ledger as ledger_module
from fractal_wallpapers.discovery import operators
from fractal_wallpapers.discovery.ledger import Ledger
from fractal_wallpapers.supply import currency as money
from fractal_wallpapers.supply.location import key_of_row, location_key

#: The schema every record this module writes outside the ledger carries.
SCHEMA = 1

#: What this channel is called wherever a row's provenance is read back.
CHANNEL = "reframing"

#: The rungs, in atom sizes. See the module docstring for the measurement.
#:
#: Offered directly and not walked to: `refine_framings` moves x1.414 a step, so
#: half an octave cannot turn 16x into 32x however many times it fires.
RUNGS: tuple[float, ...] = (16.0, 24.0, 32.0)

#: The lowest label tier a seed may carry. Both of the currency's paid classes:
#: q3 and q4 alike are places a person called a keeper, and the channel is a claim
#: about the *neighbourhood* of one rather than about the frame itself.
SEED_TIER_FLOOR = 3

#: Frames per [`engine.screen`] call. One engine process per batch, so this trades
#: the process launch against how long the leg goes without saying anything.
#: [`curation.framing.BATCH`]'s number, for the same reason it is that one there.
SCREEN_BATCH = 64

#: Seeds fired before the batch's nuclei are drawn and scored. Small enough that a
#: killed leg loses a minute rather than an hour, large enough that the head and
#: the engine are each entered a few times a minute rather than per nucleus.
SEED_BATCH = 24

#: The operators this channel fires, in order.
#:
#: `snap_to_nucleus` is deliberately absent, and it is the one exclusion worth
#: stating. At a seed it is [`operators.snap_at_seed`] with the looser radius, so
#: firing both would return one atom under two names for every seed the tighter
#: one accepts and would buy only the annulus between 0.75 and 1.0 frame widths —
#: at a second full Newton pass. The maker did not fire it at seeds either: its
#: `snap_to_nucleus` rows are all walk-triggered.
OPERATORS = ("snap_at_seed", "expand_neighborhood")

#: What a run directory is called when nobody names one. A **top-level** name of
#: the regenerable tree, because the supply union looks a ledger up at
#: `<run directory>/walk.jsonl` and nothing deeper is ever read again.
DEFAULT_OUT = Path("artifacts") / "reframe"


class ChannelRefused(RuntimeError):
    """The channel cannot be built, or cannot be run."""


class PinnedPlace(RuntimeError):
    """A pinned location reached the channel as a seed or as a derived frame.

    Raised rather than counted. The pin is asserted on the coordinate, so a frame
    the channel *manufactured* onto a pinned place spends that blind slice exactly
    as a re-draw of it would — and a channel that produced a thousand rows a night
    would spend it silently.
    """


# --------------------------------------------------------------------------- #
# The seeds.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Seed:
    """One place the operators are fired at, and what makes it a seed."""

    #: The seed's own id: a proven row's, or the atom key of a derived nucleus.
    id: str
    family: dict
    viewport: dict
    #: The human tier this seed descends from — its own for a proven root, its
    #: generation-1 ancestor's for a derived one. Never the head's number: a tier
    #: is what a person cast.
    tier: int
    #: Which generation *produced* this seed. `0` is a proven root.
    generation: int
    #: `proven` for a label-store root, `reframing` for a nucleus this channel found.
    kind: str = "proven"

    def view(self) -> dict:
        """The view an operator takes, coordinates as the decimal strings they are."""
        return {"node_id": None, **{k: str(v) for k, v in self.viewport.items()}}

    def degree(self) -> int | None:
        return operators.degree_of(self.family.get("kind"), int(self.family.get("degree", 2)))


def seeds(
    *,
    tier_floor: int = SEED_TIER_FLOOR,
    partitions=None,
    pinned: set | None = None,
    label_paths=None,
    rows: list[dict] | None = None,
) -> tuple[list[Seed], dict]:
    """`(seeds, record)` — the proven parameter-plane roots, pins excluded.

    Off [`supply.proven`] and not off a second query: that module already owns
    what "proven" means, resolves the store to one row per location, keeps human
    verdicts only, and orders by a digest so a short leg reaches a spread of
    places rather than a basin. What is added here is the two filters this channel
    needs — the parameter planes alone, because a Julia viewport is a z-plane point
    with no nucleus in the parameter-plane sense, and the pin.
    """
    from fractal_wallpapers.labeling import pins as pin_module
    from fractal_wallpapers.supply import proven
    from fractal_wallpapers.supply.partitions import PARAMETER_PLANES

    served = tuple(PARAMETER_PLANES if partitions is None else partitions)
    pinned = pin_module.every_pinned() if pinned is None else pinned
    derived = proven.derive(
        tier_floor=int(tier_floor), partitions=served, label_paths=label_paths, rows=rows
    )
    kept: list[Seed] = []
    refused_pinned = 0
    unkeyed = 0
    for row in derived["rows"]:
        key = key_of_row(row)
        if key is None:
            unkeyed += 1
            continue
        if key in pinned:
            refused_pinned += 1
            continue
        kept.append(
            Seed(
                id=row["id"],
                family=row["family"],
                viewport=row["viewport"],
                tier=int(row["provenance"]["tier"]),
                generation=0,
            )
        )
    tiers: dict[str, int] = {}
    for seed in kept:
        tiers[str(seed.tier)] = tiers.get(str(seed.tier), 0) + 1
    return kept, {
        "channel": CHANNEL,
        "tier_floor": int(tier_floor),
        "partitions": list(served),
        "proven_rows": derived["record"]["rows"],
        "labels_read": derived["record"]["labels_read"],
        "pinned_places": len(pinned),
        "refused_pinned": refused_pinned,
        "refused_unkeyed": unkeyed,
        "seeds": len(kept),
        "tiers": {tier: tiers[tier] for tier in sorted(tiers, reverse=True)},
        "rule": "a proven parameter-plane location no eval pin covers, best tier first",
    }


# --------------------------------------------------------------------------- #
# Firing the operators.
# --------------------------------------------------------------------------- #
@dataclass
class Nucleus:
    """One atom the channel found, with a frame per rung and nothing decided yet."""

    key: str
    operator: str
    seed: Seed
    generation: int
    period: int
    window_scale: float
    log10_abs_A: float | None
    #: `{rung: Reframing}` for every rung, available or not.
    rungs: dict[float, operators.Reframing] = field(default_factory=dict)
    #: Newton solves this nucleus was charged, and the operator seconds behind it.
    solves: int = 0
    seconds: float = 0.0
    #: Operators that reached this same atom after the first one did.
    also_found_by: list[str] = field(default_factory=list)

    def frames(self) -> list[tuple[float, operators.Reframing]]:
        """The rungs that have a frame at all, in ladder order."""
        return [(rung, row) for rung, row in sorted(self.rungs.items()) if row.available]


def fire(seed: Seed, rng: random.Random, *, rungs=RUNGS, probe_max=None, found_max=None):
    """`(nuclei, cost)` — every atom this seed's operators reached, at every rung.

    One Newton pass at the seed's centre answers [`operators.snap_at_seed`] and
    then seeds the neighbourhood enumeration through the shared
    [`operators.ParentAtom`], so the atom under the seed is solved for once even
    though two operators want it.

    A seed on a family with no parameter-plane degree returns nothing and says so:
    the operators are undefined there rather than unlucky.
    """
    degree = seed.degree()
    ladder = list(rungs)
    cost: dict = {
        "operators": {},
        "degree": degree,
        "refusals": {},
    }
    if degree is None:
        cost["refusals"]["reframing_undefined"] = 1
        return [], cost

    view = seed.view()
    found: dict[str, Nucleus] = {}

    def collect(operator: str, rows, seconds: float) -> None:
        charged = sum(row.newton_solves for row in rows)
        tally = cost["operators"].setdefault(
            operator, {"calls": 0, "seconds": 0.0, "solves": 0, "nuclei": 0, "refusals": {}}
        )
        tally["calls"] += 1
        tally["seconds"] += seconds
        tally["solves"] += charged
        for row in rows:
            if not row.available:
                where = tally["refusals"]
                where[row.reason] = where.get(row.reason, 0) + 1
                continue
            held = found.get(row.key)
            if held is None:
                held = Nucleus(
                    key=row.key,
                    operator=operator,
                    seed=seed,
                    generation=seed.generation + 1,
                    period=int(row.period),
                    window_scale=float(row.window_scale),
                    log10_abs_A=row.log10_abs_A,
                    solves=charged,
                    seconds=seconds,
                )
                found[row.key] = held
                tally["nuclei"] += 1
            elif held.operator != operator and operator not in held.also_found_by:
                held.also_found_by.append(operator)
            held.rungs.setdefault(float(row.framing), row)

    started = time.monotonic()
    snapped = operators.snap_at_seed(view, degree=degree, framings=ladder)
    collect("snap_at_seed", snapped, time.monotonic() - started)
    parent = operators.parent_atom_from_snap(snapped)

    started = time.monotonic()
    neighbours = operators.expand_neighborhood(
        view,
        rng,
        degree=degree,
        framings=ladder,
        parent=parent,
        **({} if probe_max is None else {"probe_max": int(probe_max)}),
        **({} if found_max is None else {"found_max": int(found_max)}),
    )
    collect("expand_neighborhood", neighbours, time.monotonic() - started)

    return list(found.values()), cost


# --------------------------------------------------------------------------- #
# Drawing the rungs and reading them.
# --------------------------------------------------------------------------- #
def frame_of(nucleus: Nucleus, rung: float, row: operators.Reframing) -> dict:
    """One rung as the location it is: the seed's family, the atom's frame."""
    del nucleus, rung
    return {
        "center_re": str(row.center_re),
        "center_im": str(row.center_im),
        "width": repr(float(row.width)),
    }


def screen_rungs(pairs: list[tuple], directory: Path, log=print) -> list[dict]:
    """Draw every `(nucleus, rung)` at the node regime and say what the gates made of it.

    [`engine.screen`] is the walk's own battery at the walk's own geometry, so a
    frame this channel admits is a frame a walk would have admitted, and the
    picture it writes is the one the head reads — no view is rendered for scoring.
    """
    from fractal_wallpapers.models import location_view
    from fractal_wallpapers.models import tiles as tile_module

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    colormap = location_view.canonical_map()
    node_width = int(tile_module.NODE_REGIME.tile[0])
    out: list[dict] = []
    for start in range(0, len(pairs), SCREEN_BATCH):
        chunk = pairs[start : start + SCREEN_BATCH]
        report = engine.screen(
            {
                "schema": 1,
                "frames": [
                    {"family": nucleus.seed.family, **frame_of(nucleus, rung, nucleus.rungs[rung])}
                    for nucleus, rung in chunk
                ],
                "colormap": colormap,
                "colormap_dir": str(engine.colormap_dir()),
                "node_width": node_width,
                "out_dir": str(directory),
            }
        )
        for offset, (screened, (nucleus, rung)) in enumerate(
            zip(report["frames"], chunk, strict=True)
        ):
            picture = None
            if screened.get("image"):
                # `screen` names its frames by position in its own batch, so a
                # second chunk would overwrite the first's.
                name = f"{start + offset:06d}_k{rung:g}.jpg"
                (directory / screened["image"]).replace(directory / name)
                picture = name
            out.append(
                {
                    "nucleus": nucleus,
                    "rung": float(rung),
                    "picture": picture,
                    "fate": screened["fate"],
                    "passed": bool(screened["passed"]),
                    "viewport": {
                        "center_re": screened["center_re"],
                        "center_im": screened["center_im"],
                        "width": screened["width"],
                    },
                    "maxiter": int(screened["maxiter"]),
                    "interior_fraction": screened.get("interior_fraction"),
                    "escape": screened.get("escape"),
                    "occupancy": screened.get("occupancy"),
                    "p_ge3": None,
                    "p_ge4": None,
                    "probabilities": (),
                    "error": None,
                    "regime": None,
                    "view": None,
                }
            )
        log(f"[reframe] {min(start + SCREEN_BATCH, len(pairs))}/{len(pairs)} rung(s) drawn")
    return out


def read_rungs(drawn: list[dict], scorer, directory: Path) -> None:
    """Score every drawn rung through the head, in place.

    The picture is handed over rather than named, so the head reads the frame
    `screen` drew instead of rendering a second one of the same place — the
    identity the walk already relies on, at the regime it relies on it at.
    """
    wanted = [index for index, cell in enumerate(drawn) if cell["picture"]]
    if not wanted:
        return
    candidates = [
        {
            "family": drawn[index]["nucleus"].seed.family,
            "viewport": drawn[index]["viewport"],
            "maxiter": drawn[index]["maxiter"],
        }
        for index in wanted
    ]
    pictures = [Path(directory) / drawn[index]["picture"] for index in wanted]
    for index, reading in zip(wanted, scorer.read(candidates, pictures=pictures), strict=True):
        drawn[index]["p_ge3"] = reading.score
        drawn[index]["p_ge4"] = reading.great
        drawn[index]["probabilities"] = tuple(reading.probabilities)
        drawn[index]["error"] = reading.error
        drawn[index]["regime"] = reading.regime
        drawn[index]["view"] = reading.view


def rank(cell: dict):
    """Best first among the rungs of one nucleus: `P(>=4)`, then `P(>=3)`.

    [`curation.framing.rank`]'s order, deliberately — the seating statistic, so
    the rung this channel picks is the rung a gallery would have reached for.
    """
    return (
        -(cell["p_ge4"] if cell["p_ge4"] is not None else -1.0),
        -(cell["p_ge3"] if cell["p_ge3"] is not None else -1.0),
        cell["rung"],
    )


def pick(readings: list[dict]) -> tuple[dict, str]:
    """`(the rung the head picked, why)` for one nucleus.

    Only a rung the gates passed and the head scored may be picked: a frame the
    battery refused is a frame no walk would have admitted. Where none qualifies
    the *widest attempted* rung is the row — record and rank, so the nucleus is on
    the ledger carrying the refusal it earned rather than not being there at all.
    """
    scored = [cell for cell in readings if cell["passed"] and cell["p_ge4"] is not None]
    if scored:
        return min(scored, key=rank), "head"
    return max(readings, key=lambda cell: cell["rung"]), "no_scored_rung"


# --------------------------------------------------------------------------- #
# The row.
# --------------------------------------------------------------------------- #
def fate_of(cell: dict) -> str:
    """The ledger fate one drawn rung earned, on the floors as they stand.

    A gate refusal keeps the gate's own name — the same words a walk's candidate
    carries — and a frame that passed is decided by the two floors through
    [`supply.ledgers`]' own reader, so a row this channel writes and a row a walk
    writes are decided by one function.
    """
    from fractal_wallpapers.supply import ledgers

    if not cell["passed"]:
        return str(cell["fate"])
    return ledgers.fate_of(cell["p_ge3"])


def is_head_q4(cell: dict) -> bool:
    """Whether the head calls this frame a class 4: the q4 admission bar.

    Both cuts, through the currency: the keeper floor on `P(>=3)` decides whether
    there is a class at all, and the great cut on `P(>=4)` decides which. It is
    [`supply.currency.good_class`] and not a second reading of two numbers.
    """
    return money.good_class(cell["p_ge3"], cell["p_ge4"]) == 4


def candidate_row(
    nucleus: Nucleus,
    readings: list[dict],
    chosen: dict,
    why: str,
    *,
    run_seed: int,
    batch: int,
    scorer_name: str,
) -> dict:
    """One nucleus as the candidate row the supply union reads.

    Walk-shaped, field for field, because the union is one reader and a channel
    that wrote a shape of its own would be supply nothing counts. What is added is
    one block — `reframing` — carrying everything that makes this row this
    channel's: the seed and its tier, the operator, every rung's own reading, which
    rung was picked, the generation, and what it cost.
    """
    return {
        "run_seed": run_seed,
        "batch": batch,
        "parent_node_id": None,
        "root_id": nucleus.seed.id,
        "depth": nucleus.generation,
        "child_index": 0,
        "family": nucleus.seed.family,
        "viewport": chosen["viewport"],
        "branch": None,
        "placement": None,
        "focus_score": None,
        "maxiter": chosen["maxiter"],
        "interior_fraction": chosen["interior_fraction"],
        "escape": chosen["escape"],
        "occupancy": chosen["occupancy"],
        "image": chosen["picture"],
        "origin": nucleus.operator,
        "atom_key": nucleus.key,
        "channel": CHANNEL,
        "fate": fate_of(chosen),
        "scorer": scorer_name,
        # A reframing is not a descent, so there is no rung below a plane root to
        # report and no grace that could have acted on one. Spelled `null` rather
        # than omitted: a reader that met an absent field would be reading a
        # ledger written before the fields existed, which this is not.
        "plane_rung": None,
        "cleared_junk": None,
        "grace": None,
        "score": chosen["p_ge3"],
        "score_great": chosen["p_ge4"],
        "score_error": chosen["error"],
        "score_regime": chosen["regime"],
        "score_view": chosen["view"],
        "reframing": {
            "channel": CHANNEL,
            "generation": nucleus.generation,
            "operator": nucleus.operator,
            "also_found_by": list(nucleus.also_found_by),
            "seed": {
                "id": nucleus.seed.id,
                "kind": nucleus.seed.kind,
                "tier": nucleus.seed.tier,
                "generation": nucleus.seed.generation,
                "family": nucleus.seed.family,
                "viewport": nucleus.seed.viewport,
            },
            "atom": {
                "key": nucleus.key,
                "period": nucleus.period,
                "window_scale": nucleus.window_scale,
                "log10_abs_A": nucleus.log10_abs_A,
            },
            "rungs": [float(rung) for rung in sorted(nucleus.rungs)],
            "rungs_drawn": [
                {
                    "rung": cell["rung"],
                    "fate": cell["fate"],
                    "passed": cell["passed"],
                    "p_ge3": cell["p_ge3"],
                    "p_ge4": cell["p_ge4"],
                    "error": cell["error"],
                    "viewport": cell["viewport"],
                    "maxiter": cell["maxiter"],
                    "picture": cell["picture"],
                }
                for cell in readings
            ],
            "chosen_rung": chosen["rung"],
            "chosen_by": why,
            "head_q4": is_head_q4(chosen),
            "newton_solves": nucleus.solves,
            "operator_seconds": round(nucleus.seconds, 4),
        },
    }


# --------------------------------------------------------------------------- #
# The leg.
# --------------------------------------------------------------------------- #
class Channel:
    """One run of the channel: seeds in, candidate rows out, on a clock."""

    def __init__(
        self,
        *,
        out_dir: Path,
        scorer,
        seed: int = 0,
        rungs=RUNGS,
        minutes: float | None = None,
        generations: int = 1,
        pinned: set | None = None,
        seed_batch: int = SEED_BATCH,
        log=print,
    ):
        from fractal_wallpapers.labeling import pins as pin_module

        self.out_dir = Path(out_dir)
        self.scorer = scorer
        self.seed = int(seed)
        self.rungs = tuple(float(rung) for rung in rungs)
        self.minutes = None if minutes in (None, 0) else float(minutes)
        self.generations = max(1, int(generations))
        self.seed_batch = max(1, int(seed_batch))
        self.log = log
        self.rng = random.Random(self.seed)
        self.pinned = pin_module.every_pinned() if pinned is None else set(pinned)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.ledger = Ledger(self.out_dir / ledger_module.LEDGER_NAME)
        self.frames_dir = self.out_dir / "rungs"
        #: Atom keys this run has already made a location of. One nucleus is one
        #: location, whichever operator or seed reached it first.
        self.seen: set[str] = set()
        self.counts: dict[str, int] = {}
        self.cost: dict = {}
        self.started = time.monotonic()
        self.batch_index = 0
        self.rows_written = 0

    # ---------------------------------------------------------------- clock
    def spent(self) -> float:
        return time.monotonic() - self.started

    def out_of_time(self) -> bool:
        return self.minutes is not None and self.spent() >= self.minutes * 60.0

    def _count(self, name: str, by: int = 1) -> None:
        self.counts[name] = self.counts.get(name, 0) + by

    def _charge(self, cost: dict) -> None:
        for operator, tally in cost.get("operators", {}).items():
            held = self.cost.setdefault(
                operator, {"calls": 0, "seconds": 0.0, "solves": 0, "nuclei": 0, "refusals": {}}
            )
            held["calls"] += tally["calls"]
            held["seconds"] += tally["seconds"]
            held["solves"] += tally["solves"]
            held["nuclei"] += tally["nuclei"]
            for reason, n in tally["refusals"].items():
                held["refusals"][reason] = held["refusals"].get(reason, 0) + n
        for reason, n in cost.get("refusals", {}).items():
            self._count(f"seed_refused:{reason}", n)

    # ----------------------------------------------------------- the guard
    def refuse_a_pinned_frame(self, family: dict, viewport: dict, what: str) -> None:
        """Raise if this frame lands on a place an eval pin covers."""
        try:
            key = location_key(family, viewport)
        except (KeyError, TypeError, ValueError):
            return
        if key in self.pinned:
            raise PinnedPlace(
                f"{what} lands on {key!r}, which an evaluation pin covers. A blind slice is "
                f"spent the moment a training population reaches it, and a manufactured frame "
                f"spends it exactly as a re-draw would — fix the channel, never the pin."
            )

    # ------------------------------------------------------------- the loop
    def run(self, roots: list[Seed]) -> dict:
        """Fire every generation the budget allows and return what was found."""
        header = {
            "channel": CHANNEL,
            "run_seed": self.seed,
            "rungs": list(self.rungs),
            "operators": list(OPERATORS),
            "generations": self.generations,
            "minutes": self.minutes,
            "seeds": len(roots),
            "pinned_places": len(self.pinned),
            "scorer": self.scorer.name,
            "q4_bar": {
                "good_floor": money.GOOD_FLOOR,
                "great_cut": money.GREAT_CUT,
            },
        }
        self.ledger.write("reframing_run", **header)
        self.log(f"[reframe] {json.dumps(header)}")

        pending = list(roots)
        consumed = 0
        per_generation: list[dict] = []
        for generation in range(1, self.generations + 1):
            if not pending or self.out_of_time():
                break
            found, used, promoted = self._generation(generation, pending)
            consumed += used
            per_generation.append(
                {
                    "generation": generation,
                    "seeds_offered": len(pending),
                    "seeds_consumed": used,
                    "locations": found,
                    "promoted": len(promoted),
                }
            )
            pending = promoted
        report = self.summary(roots, consumed, per_generation)
        self.ledger.write("reframing_summary", **report)
        self.ledger.close()
        return report

    def _generation(self, generation: int, pending: list[Seed]) -> tuple[int, int, list[Seed]]:
        """`(locations written, seeds consumed, next generation's seeds)`."""
        written = 0
        consumed = 0
        promoted: list[Seed] = []
        for start in range(0, len(pending), self.seed_batch):
            if self.out_of_time():
                break
            chunk = pending[start : start + self.seed_batch]
            self.batch_index += 1
            nuclei: list[Nucleus] = []
            for seed in chunk:
                consumed += 1
                self.refuse_a_pinned_frame(seed.family, seed.viewport, f"seed {seed.id}")
                found, cost = fire(seed, self.rng, rungs=self.rungs)
                self._charge(cost)
                for nucleus in found:
                    if nucleus.key in self.seen:
                        self._count("nucleus_already_found")
                        continue
                    if not nucleus.frames():
                        self._count("nucleus_no_frame")
                        continue
                    self.seen.add(nucleus.key)
                    nuclei.append(nucleus)
            written += self._draw(nuclei, promoted)
            self.log(
                f"[reframe] generation {generation}: "
                f"{min(start + self.seed_batch, len(pending)):,}/{len(pending):,} seed(s), "
                f"{written:,} location(s), {self.spent() / 60.0:.1f} min"
            )
        return written, consumed, promoted

    def _draw(self, nuclei: list[Nucleus], promoted: list[Seed]) -> int:
        """Screen, score and write one batch of nuclei. One row per nucleus."""
        if not nuclei:
            return 0
        pairs = [(nucleus, rung) for nucleus in nuclei for rung, _row in nucleus.frames()]
        for nucleus, rung in pairs:
            self.refuse_a_pinned_frame(
                nucleus.seed.family,
                frame_of(nucleus, rung, nucleus.rungs[rung]),
                f"the {rung:g}x rung of atom {nucleus.key}",
            )
        drawn = screen_rungs(pairs, self.frames_dir, log=self.log)
        read_rungs(drawn, self.scorer, self.frames_dir)

        by_nucleus: dict[str, list[dict]] = {}
        for cell in drawn:
            by_nucleus.setdefault(cell["nucleus"].key, []).append(cell)

        written = 0
        for nucleus in nuclei:
            readings = by_nucleus.get(nucleus.key)
            if not readings:
                continue
            chosen, why = pick(readings)
            # The chosen frame is what the location IS, so the pin is asserted on
            # the frame the engine reports rather than on the one we asked for.
            self.refuse_a_pinned_frame(
                nucleus.seed.family, chosen["viewport"], f"the chosen rung of atom {nucleus.key}"
            )
            row = candidate_row(
                nucleus,
                readings,
                chosen,
                why,
                run_seed=self.seed,
                batch=self.batch_index,
                scorer_name=self.scorer.name,
            )
            self.ledger.write("candidate", node_id=None, **row)
            written += 1
            self.rows_written += 1
            self._count(f"fate:{row['fate']}")
            self._count(f"rung_picked:{chosen['rung']:g}")
            self._count(f"operator:{nucleus.operator}")
            for cell in readings:
                self._count(f"rung_drawn:{cell['rung']:g}")
                if cell["passed"]:
                    self._count(f"rung_passed:{cell['rung']:g}")
                if cell["p_ge4"] is not None and is_head_q4(cell):
                    self._count(f"rung_head_q4:{cell['rung']:g}")
            if row["reframing"]["head_q4"]:
                self._count("head_q4")
                promoted.append(
                    Seed(
                        id=nucleus.key,
                        family=nucleus.seed.family,
                        viewport=chosen["viewport"],
                        tier=nucleus.seed.tier,
                        generation=nucleus.generation,
                        kind=CHANNEL,
                    )
                )
        return written

    # ------------------------------------------------------------ the record
    def summary(self, roots: list[Seed], consumed: int, per_generation: list[dict]) -> dict:
        seconds = self.spent()
        operator_seconds = sum(tally["seconds"] for tally in self.cost.values())
        nuclei = len(self.seen)
        q4 = self.counts.get("head_q4", 0)
        return {
            "channel": CHANNEL,
            "run_seed": self.seed,
            "seconds": round(seconds, 2),
            "operator_seconds": round(operator_seconds, 2),
            "seeds_available": len(roots),
            "seeds_consumed": consumed,
            "nuclei": nuclei,
            "locations": self.rows_written,
            "head_q4": q4,
            "generations": per_generation,
            "cost": {
                operator: {
                    **{k: (round(v, 3) if isinstance(v, float) else v) for k, v in tally.items()},
                    "seconds_per_nucleus": (
                        round(tally["seconds"] / tally["nuclei"], 3) if tally["nuclei"] else None
                    ),
                }
                for operator, tally in sorted(self.cost.items())
            },
            "rate": {
                "seconds_per_location": (
                    round(seconds / self.rows_written, 3) if self.rows_written else None
                ),
                "seconds_per_head_q4": round(seconds / q4, 3) if q4 else None,
                "locations_per_operator_minute": (
                    round(self.rows_written / (operator_seconds / 60.0), 2)
                    if operator_seconds > 0
                    else None
                ),
                "head_q4_per_operator_minute": (
                    round(q4 / (operator_seconds / 60.0), 2) if operator_seconds > 0 else None
                ),
            },
            "counts": dict(sorted(self.counts.items())),
            "ledger": str(self.ledger.path),
        }


def run(
    *,
    out_dir: Path,
    scorer,
    seed: int = 0,
    rungs=RUNGS,
    minutes: float | None = None,
    generations: int = 1,
    tier_floor: int = SEED_TIER_FLOOR,
    partitions=None,
    roots: int | None = None,
    seed_batch: int = SEED_BATCH,
    log=print,
) -> dict:
    """Derive the seeds and run the channel over them. What the command calls."""
    from fractal_wallpapers.labeling import pins as pin_module

    pinned = pin_module.every_pinned()
    found, record = seeds(tier_floor=tier_floor, partitions=partitions, pinned=pinned)
    if roots is not None:
        found = found[: max(0, int(roots))]
    log(f"[reframe] seeds: {json.dumps(record)}")
    if not found:
        raise ChannelRefused(
            "no proven parameter-plane location survives the pin, so the channel has nowhere "
            "to fire. Label some parameter-plane keepers, or widen --tier-floor."
        )
    channel = Channel(
        out_dir=out_dir,
        scorer=scorer,
        seed=seed,
        rungs=rungs,
        minutes=minutes,
        generations=generations,
        pinned=pinned,
        seed_batch=seed_batch,
        log=log,
    )
    report = channel.run(found)
    report["seed_query"] = record
    return report


def distinct_places(rows: list[dict], radius: float | None = None, log=print) -> tuple:
    """`(rows whose place survived the neutral radius, the record)`.

    The pre-selection [`curation.distinct`] owns, applied here to a list of this
    channel's rows — **before a sheet is cut and never to the ledger**. The ledger
    records everything the channel found; a sitting must not see fifty lookalikes
    off one seed, and those are two different rules with two different placements.

    Strongest first, so the survivor of a near-cluster is the place a seating would
    have reached for anyway. A row whose place has no neutral descriptor is
    admitted and counted, which is [`curation.distinct.suppress`]'s own rule.
    """
    from fractal_wallpapers.curation import distinct

    radius = distinct.PRESELECT_RADIUS if radius is None else float(radius)
    best: dict[str, dict] = {}
    for row in rows:
        key = key_of_row(row)
        if key is None:
            continue
        name = str(key)
        held = best.get(name)
        if held is None or (row.get("score_great") or -1.0) > (held.get("score_great") or -1.0):
            best[name] = row
    order = sorted(best, key=lambda name: -(best[name].get("score_great") or -1.0))
    walk = distinct.suppress(order, radius=radius)
    log(
        f"[reframe] distinctness at {radius}: {len(walk['kept']):,} of {len(order):,} place(s) "
        f"kept, {len(walk['refused']):,} refused"
    )
    return [best[name] for name in order if name in walk["kept"]], {
        "radius": radius,
        "metric": distinct.METRIC,
        "places_asked": len(order),
        "places_kept": len(walk["kept"]),
        "places_refused": len(walk["refused"]),
        "admitted_without_a_descriptor": len(walk["unembedded"]),
        "rule": "geometric distinctness only, applied where a sheet is cut and not to the "
        "ledger — the twin test at ceiling.TAU is still the diversity rule",
    }


def read(path: Path) -> list[dict]:
    """This channel's candidate rows out of a ledger it wrote."""
    return [
        row
        for row in ledger_module.read(Path(path))
        if row.get("kind") == "candidate" and row.get("channel") == CHANNEL
    ]


def frame_multiple(row: dict) -> float | None:
    """How many atom sizes wide the chosen frame is — the audit's `f`.

    Read off the row's own atom and viewport rather than off the rung it names, so
    a row whose frame was re-read from the engine still reports the frame that was
    drawn.
    """
    atom = (row.get("reframing") or {}).get("atom") or {}
    scale = atom.get("window_scale")
    width = (row.get("viewport") or {}).get("width")
    if not scale or width is None:
        return None
    try:
        value = float(width) / float(scale)
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    return value if math.isfinite(value) else None


__all__ = [
    "CHANNEL",
    "DEFAULT_OUT",
    "OPERATORS",
    "RUNGS",
    "SCHEMA",
    "SEED_BATCH",
    "SEED_TIER_FLOOR",
    "SCREEN_BATCH",
    "Channel",
    "ChannelRefused",
    "Nucleus",
    "PinnedPlace",
    "Seed",
    "candidate_row",
    "distinct_places",
    "fate_of",
    "fire",
    "frame_multiple",
    "frame_of",
    "is_head_q4",
    "pick",
    "rank",
    "read",
    "read_rungs",
    "run",
    "screen_rungs",
    "seeds",
]
