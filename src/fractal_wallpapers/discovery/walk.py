"""The walk: a frontier of places, expanded one rung at a time.

A walk starts from seeds, expands the most promising places it knows about, and
writes down everything it sees. The engine does the looking — one rung per node,
gated, in [`fractal_wallpapers.engine.expand`] — and this module does the
deciding: which nodes to expand next, when to reframe onto a nucleus, what to
record, and when to stop.

```text
seeds ──▶ frontier ──▶ batch ──▶ engine expand ──▶ candidates ──▶ ledger
             ▲                                          │
             └────────── survivors, and reframings ◀─────┘
```

Five decisions shape the loop, and none of them is about pictures.

**The batch is chosen by priority, and priority is score plus a draw.** A
survivor's priority is its score plus a Gumbel draw plus a small depth term.
Under the null scorer the score is neutral for everything and the Gumbel is the
whole of it, so the walk explores uniformly; under the location head the score
is a probability and the draw is what keeps the queue from collapsing onto one
lineage. The two terms are on comparable scales at [`GUMBEL_TEMPERATURE`] `1.0`,
which means the head *tilts* the order rather than dictating it — a deliberate
level for a first steered run, and the one knob to move when a measurement says
the head deserves more of a say.

**A per-root expansion cap, and capped nodes are evicted rather than skipped.**
A root spawns children faster than it drains, so nodes belonging to a capped root
accumulate; leave them on the frontier and they eventually *are* the frontier,
the batch is all dead weight, and throughput goes to zero.

**An optional per-lineage admission cap, for the same reason one level up.** The
expansion cap bounds what a root may *spend*; [`Limits.lineage_admissions`] bounds
what it may *book*. A fertile lineage sits at the top of a priority queue by
construction — it got there by admitting — so without a ceiling it takes the walk
with it, and the finished frame set is one composition. Off by default and on for a
deep run; nothing is retro-refused when it fires, expansion simply stops.

**Two reserved floors, both of available, and neither may stall the batch.**
Reframings hold a floor because nothing has been trained on the views they
produce, so on score alone a mature frontier would never reach them. Fresh roots
hold a floor for the mirror reason: the triggered channel feeds itself — a view
produced by snapping to a nucleus is centered on a nucleus, so snapping it again
nearly always works — and without a floor the operators would crowd out every
root the walk has not touched yet. Whatever a floor cannot fill falls straight
back to the ordinary priority order in the same batch.

**Reframings inherit the root they were triggered from, and burn its budget.**
An operator is not a source: it applies to a place the walk already found, and
it inherits both the provenance and the cost of that place.

## Standing on a place and booking it are two decisions

The scorer is asked twice about every gate survivor, at two heights. *May the
walk continue from here?* is the junk floor; *is this a find worth counting?* is
the good floor. One cut used to answer both, and the cost was arithmetic rather
than taste: a frontier fed only by its own admissions grows by `admissions per
expansion` and dies below one, which is where the first steered run's realized
pass rate put it. The middle tier — good enough to stand on, not good enough to
book — is what keeps the walk moving between finds, and it is invisible to every
book in the project because its rows carry their own fate. See
[`fractal_wallpapers.discovery.ledger`] for the three of them.

## A parameter-plane root starts above the depths its material lives at

The head scores parameter-plane locations near zero at the widths a plane seed
root *starts* at — measured maxima of 1e-4 to 2.4e-2 against a junk floor of
0.20, so roughly one gate survivor in eighty could be stood on and plane nodes
never reached the frontier at all. It is not a bias in the head: labelled class
3/4 parameter-plane material sits at width 1e-4 to 1e-5, four or five rungs below
where a plane root begins, and every one of those rungs was gated on a score the
material only earns *after* the descent. The lever is depth, not height.

So the first [`Limits.plane_grace_rungs`] rungs below a plane-seed root are
exempt from the expansion floor: the walk descends ungated, and the floor resumes
at rung N+1. Four things bound it.

* **Expansion only.** Booking still happens at the good floor everywhere, so
  grace can put a node on the frontier and can never put a find in the books.
* **Plane provenance only.** Julia, twin and phoenix roots are dynamical — their
  home view *is* where their material lives — and are untouched.
* **A waived floor, not a waived verdict.** A candidate with no score at all has
  a failed render behind it rather than a low opinion, and there is no opinion for
  grace to overrule; it stays refused.
* **The measurement is bought with it.** Every gate survivor under a plane root
  records its rung below that root, the raw junk-floor verdict, and whether grace
  was in force — which is the survival-by-rung table a depth-aware floor would
  need if this cliff turns out to be the wrong shape. N is the machinery; the
  table is the reason for it.

## The scorer is asked once per batch, not once per candidate

Every candidate the engine reports is built first, the survivors are read
**together**, and only then are the rows written — in the order the engine
reported them, in one pass, by this process. That is what lets the scorer fan its
renders out across worker processes without the ledger's order becoming a
function of which worker finished first, and it is why [`_record`] is three loops
rather than one. It matters less than it did — nothing is rendered for scoring
any more — but the order is a property of the record and stays a property of the
record.

## The picture the scorer is handed is the gate render

`expand` draws every gate survivor at 384×216, one field sample per pixel, and
that frame is byte-identical to the same location's cached tile at the same
regime — one of the three the shipped head was trained over. So the walk offers
the scorer the picture it already made, and the deploy-geometry steering view is
gone: it was 58.7% of a production run's clean wall and nothing but the scorer
ever read its pixels. The four settings that make the identity true are checked
before the run's first row is written, in
[`fractal_wallpapers.discovery.identity`], and every scored row records the
regime and the recipe digest its score was read off.

Once a run, a small seeded sample of survivors is scored a **second** time at the
deploy geometry and the two verdicts are compared at the three acting gates. That
line is reported and nothing acts on it: it is standing insurance on the live
candidate population, priced at about a minute of a multi-hour leg.
"""

from __future__ import annotations

import json
import math
import random
import time
from dataclasses import dataclass, field, replace
from pathlib import Path

from fractal_wallpapers import engine

# The gallery pass's framing scan, reused rather than forked — one window, one
# margin, one provenance shape at both sites. It imports the engine and the
# standard library and nothing else, so the walk's import graph stays what the
# torch-free base install proves it is; the two model doors it needs are lazy
# inside it, the way every other reach from this half of the project into
# curation is.
from fractal_wallpapers.curation import framing
from fractal_wallpapers.discovery import identity, nucleus, operators, pools
from fractal_wallpapers.discovery import ledger as ledger_module
from fractal_wallpapers.discovery.ledger import Ledger
from fractal_wallpapers.discovery.scoring import NullScorer, Scorer
from fractal_wallpapers.paths import tracked_name
from fractal_wallpapers.supply.location import key_of_row

#: The priority an unscored node carries. Scores are compared only against each
#: other, so the level is arbitrary and only the fact that it is shared matters.
NEUTRAL_PRIOR = 0.0

#: Temperature of the Gumbel draw added to every priority.
#:
#: Drawn once per node when it is pushed, never re-drawn — so the frontier's
#: order is stable, and a node that lost a batch does not get a fresh lottery
#: ticket every time it loses.
GUMBEL_TEMPERATURE = 1.0

#: Priority added per rung of depth. Small: a tie-break toward going deeper,
#: not a reason to.
DEPTH_WEIGHT = 0.02

#: A node's origin: how the walk came to be standing at it.
#:
#: `root` is a seed, `walk` is a rung of ordinary descent, and everything else is
#: the operator that proposed it. **The operator stamp rides the whole subtree
#: below a fired reframing**, not only the node it produced — a reframing's
#: ordinary children are views nothing has been trained on either, and the
#: reserved floor exists for exactly that population. It also means the floor's
#: counters are over the subtree, which makes them much larger than the count of
#: fired operators and is not a bug in either.
ROOT_ORIGIN = "root"
WALK_ORIGIN = "walk"
REFRAMED_ORIGINS = frozenset({"snap_to_nucleus", "lateral_to_sibling", "expand_neighborhood"})

#: What a node the refine leg put on the frontier says it came from. Not one of
#: [`REFRAMED_ORIGINS`] on purpose: those are the nucleus operators, which push a
#: node at a *different* place, and this is the same place at a different frame.
REFINED_ORIGIN = "refine_framing"

#: The depth a root stands at. The engine counts rungs from the root and calls the
#: first one 1, so a root's own children are one rung below it.
ROOT_DEPTH = 1

#: The root sources the expansion grace applies to: the parameter-plane channel,
#: which is the tracked plane seed pool and an explicit `--seeds` file alike — one
#: reader, one source name, and the same starting-too-shallow problem either way.
#: A seed file may still carry a dynamical family, so provenance is necessary and
#: not sufficient: the family has to be a parameter plane as well.
PLANE_ROOT_SOURCES = frozenset({"seed_file"})


@dataclass
class Limits:
    """How much walking to do, and how to divide it."""

    #: Nodes expanded per batch.
    batch: int = 8
    #: Batches to run.
    batches: int = 4
    #: Expansions any one root may pay for, its reframings included.
    root_expansions: int = 12
    #: Share of a batch's slots reserved for roots nothing has expanded yet.
    breadth_floor: float = 0.25
    #: Slots per batch reserved for reframing-originated nodes.
    operator_quota: int = 2
    #: Probability the reframing probe fires on an admitted candidate.
    probe_probability: float = 0.25
    #: Nodes the frontier holds before the worst are dropped.
    frontier_cap: int = 4000
    #: Rungs below a plane-seed root that the expansion floor does not act on.
    #:
    #: Five, matched to the measured four-to-five rung gap between where a plane
    #: root starts and the widths labelled plane material lives at. `0` is the
    #: ungraced walk exactly.
    #:
    #: **Five is matched to material at 1e-4/1e-5, and a later reading moved the
    #: target.** Labelled deep admissions put the keeper rate on the *width* axis,
    #: not the rung axis — .432 at 1e-5 against .714/.833/1.000 at 1e-7/1e-8/1e-9 —
    #: and the seed pool's typical root starts at 1e-2, which [`Policy.zoom`]
    #: narrows about 0.37 decades a rung. Reaching 1e-6 is therefore ~11 rungs, not
    #: five, and at five the candidate population falls off a cliff exactly where
    #: grace ends: 1,304 survivors at rung 6 against 132 at rung 7 over two runs.
    #: A production run at eleven removed that cliff, reached rung 13, and doubled
    #: the share of plane candidates at 1e-6 or deeper (1.5% -> 3.1%) — for half the
    #: shallow throughput, because eleven ungated rungs spend gate renders on
    #: nodes that never clear and maxiter climbs with depth (13,140 at rung 1 to
    #: 31,628 at rung 13). The number is a trade, not a constant; this is its price.
    plane_grace_rungs: int = 5
    #: Admissions any one root's lineage may book before the walk stops expanding
    #: it, or `None` for no cap at all — which is the shallow walk, unchanged.
    #:
    #: **Diminishing returns are a supply-time problem, not a selection-time one.**
    #: A later pass can spread itself over lineages after the fact, and `deep_run1`'s
    #: had to; what it cannot do is get back the walk time that went into the
    #: lineage it then had to thin. That run put 741 admissions on 15 of its 48
    #: roots and 85 of them on one, and the finished floor frames were largely one
    #: composition in a hundred and sixty palettes. Past the cap the lineage stops
    #: expanding and the batch slots flow to cells nothing has saturated.
    #:
    #: `None` and not `0`: zero is a real answer to "how many admissions may a
    #: lineage book" and it is not this one.
    lineage_admissions: int | None = None
    #: How many of a walk's gate survivors have their framing refined when the
    #: walk closes, best first by the seating statistic. `0` disables the leg and
    #: is the walk this project ran before it existed, exactly.
    #:
    #: Three, and it is the archive's own number: the maker reframed the top
    #: `KRAW = 3` frames of each walk and took the walk's reward as the max over
    #: them. It is deliberately tiny — the leg is seven node-regime renders a
    #: location and it buys nothing the walk itself reads, so spending it on more
    #: than the handful of frames a walk is actually likely to ship would be
    #: paying for refinements no gallery will ever seat.
    refine_per_walk: int = 3
    #: Δ the refine leg adopts on, in nats of log-odds on `P(≥4)`, or `None` for
    #: the gallery pass's own default. Read off [`curation.framing`] rather than
    #: restated: one margin, one meaning, and a scan taken here that a pass would
    #: have refused is a scan nobody can compare.
    refine_margin: float | None = None


@dataclass
class Policy:
    """What the engine is told about how to draw candidates."""

    candidates: int = 4
    node_width: int = 384
    branch_weights: tuple[float, float, float] = (0.70, 0.10, 0.20)
    placement: tuple[float, float, float] = (0.25, 0.40, 0.35)
    focus_spread: float = 0.12
    zoom: tuple[float, float] = (0.35, 0.50)
    sigmas: tuple[float, ...] = (8.0, 10.0, 12.0, 14.0, 16.0)

    def wire(self) -> dict:
        return {
            "candidates": self.candidates,
            "node_width": self.node_width,
            "branch_weights": list(self.branch_weights),
            "placement": list(self.placement),
            "focus_spread": self.focus_spread,
            "zoom": list(self.zoom),
            "sigmas": list(self.sigmas),
        }


@dataclass
class Gates:
    """The structural gates, as the engine takes them."""

    interior_cap: float = 0.30
    occupancy_floor: float = 0.321
    occupancy_at_first_rung: bool = False
    spread_min: float = 20.0
    escape_median_min: float = 3.0
    min_width: float = 1e-9
    #: Floors that replace [`min_width`] on one plane, by multibrot degree.
    #:
    #: Empty here and empty for every shallow walk: this walk's floor already
    #: sits above every floor any plane asks for, so nothing it could hold
    #: would bind. It exists because a *deep* walk's floor is not one number —
    #: [`fractal_wallpapers.deep.depth.DEGREE_MIN_WIDTH`] raises it a decade on
    #: degree 5 — and the engine takes one number per call. An expansion is
    #: already one call per distinct family, so [`for_family`] is where the two
    #: meet and nothing above it has to know.
    min_width_by_degree: dict[int, float] = field(default_factory=dict)

    def for_family(self, family: dict) -> Gates:
        """These gates as the plane of this family takes them.

        `self` unchanged where the plane asks for nothing, so a walk with no
        per-degree floors wires byte-identical payloads to the ones it always
        did.
        """
        if not self.min_width_by_degree:
            return self
        degree = operators.degree_of(family.get("kind"), int(family.get("degree", 2)))
        floor = self.min_width_by_degree.get(degree)
        if floor is None or floor <= self.min_width:
            return self
        return replace(self, min_width=float(floor))

    def wire(self) -> dict:
        """The payload the engine takes: one floor, for one family."""
        return {
            "interior_cap": self.interior_cap,
            "occupancy_floor": self.occupancy_floor,
            "occupancy_at_first_rung": self.occupancy_at_first_rung,
            "band": {
                "spread_min": self.spread_min,
                "escape_median_min": self.escape_median_min,
            },
            "min_width": self.min_width,
        }

    def record(self) -> dict:
        """What a run's header says these gates were — the wire and the floors
        it varies by plane, which the wire has no room for."""
        wire = self.wire()
        if self.min_width_by_degree:
            wire["min_width_by_degree"] = {
                str(degree): floor for degree, floor in sorted(self.min_width_by_degree.items())
            }
        return wire


@dataclass
class Reframings:
    """Which reframing operators are live, and how far they may reach."""

    enabled: bool = True
    snap: bool = True
    lateral: bool = True
    #: On, at the priced cost. The neighbourhood enumeration is the expensive
    #: operator — `scratch/demo_neighborhood_run_report.md` replayed 1,379
    #: firings and put it at **23.9% of a harvest's active clock** at the default
    #: `probe_probability`, buying admissions at 3.6x what ordinary descent pays.
    #: That tax is accepted deliberately: what it frames is material nothing has
    #: been trained on, which is what the frontier's reserved operator slot is
    #: for, and a cheaper operator cannot make it. Turn it off per run rather
    #: than here.
    neighborhood: bool = True
    #: How many of a neighbourhood enumeration's finds to propose.
    #:
    #: The operator returns them in *enumeration* order, which is not a quality
    #: order and must not be read as one. Ranking them is a question about
    #: pictures and waits for something that can answer it.
    neighborhood_proposals: int = 2
    framings: tuple[float | None, ...] = operators.FRAMINGS


class Best:
    """The `k` gate survivors of a walk that are worth refining, best first.

    **The seating statistic, so the walk and the gallery agree about "best".**
    `logit P(≥4)` then `P(≥3)`, which is the order [`curation.framing.rank`] takes
    and the order a gallery slot is filled in. The logit is monotone in the
    probability, so the comparison here is on the probability and the two orders
    are the same one — the scale matters where a *margin* is taken, not where a
    sort is.

    Offered every scored candidate and keeping `k` of them, because a walk is a
    few tens of thousands of rows and the leg is seven node-regime renders each.
    A row with no `P(≥4)` is never offered: a failed render has no verdict to be
    ranked on, and a walk under the null scorer has none at all.
    """

    def __init__(self, k: int):
        self.k = max(0, int(k))
        self.rows: list[tuple] = []
        self.seen = 0

    def offer(self, row: dict) -> None:
        if self.k <= 0 or row.get("score_great") is None:
            return
        self.seen += 1
        # The offer order is the ledger's own order, and it is the last
        # tiebreak — so a walk re-run on one seed refines the same frames rather
        # than whichever of a tie the sort happened to leave on top.
        self.rows.append(
            (-float(row["score_great"]), -float(row.get("score") or 0.0), self.seen, row)
        )
        self.rows.sort(key=lambda cell: cell[:3])
        del self.rows[self.k :]

    def take(self) -> list[dict]:
        return [cell[-1] for cell in self.rows]


def family_key(family: dict) -> str:
    """A stable key for one family identity, constants included.

    The engine expands one family per call, so the batch is grouped by this.
    Two Julia views at different `c` are different fractals and cannot share a
    call, which the key makes structural rather than remembered.
    """
    return json.dumps(family, sort_keys=True)


class Walk:
    """One discovery run."""

    def __init__(
        self,
        *,
        out_dir: Path,
        seed: int = 0,
        limits: Limits | None = None,
        policy: Policy | None = None,
        gates: Gates | None = None,
        reframings: Reframings | None = None,
        scorer: Scorer | None = None,
        colormap: str = "twilight_shifted",
        report_foci: bool = False,
    ):
        self.out_dir = Path(out_dir)
        self.seed = int(seed)
        self.limits = limits or Limits()
        self.policy = policy or Policy()
        self.gates = gates or Gates()
        self.reframings = reframings or Reframings()
        self.scorer = scorer or NullScorer()
        self.colormap = colormap
        #: Whether the ledger keeps each expanded node's focus set beside its
        #: candidates. **Off, and a run with it off writes the ledger it always
        #: wrote.** The set is a reading of the parent frame that the engine
        #: takes either way, so this decides what is *recorded*, not what is
        #: computed — a run with it on descends into exactly the same places.
        #: On, it costs one row per expanded node, which against four candidate
        #: rows apiece is a ledger about a quarter larger.
        self.report_foci = bool(report_foci)

        # Before the header, because this is the claim the run's scores rest on:
        # a walk that scores its own gate renders is asserting they are the tiles
        # the head was trained on, and a refusal discovered later is a refusal
        # discovered with a ledger already written.
        self.identity = self._enforce_identity()
        self.flip_sample = identity.Sample(seed=self.seed)
        #: The `k` survivors this walk will refine when it closes, kept as they
        #: are scored so nothing has to be re-read off the ledger afterwards.
        self.best = Best(self.limits.refine_per_walk)
        #: Δ the refine leg adopts on. Resolved here so the run header records
        #: the number the leg actually used rather than the word "default".
        self.refine_margin = (
            framing.MARGIN
            if self.limits.refine_margin is None
            else float(self.limits.refine_margin)
        )

        self.rng = random.Random(self.seed)
        self.governor = operators.ProbeGovernor(self.limits.probe_probability, self.rng)
        self.frontier: list[dict] = []
        self.expansions: dict[int, int] = {}
        #: Admissions booked per root — the lineage cap's counter, and a table
        #: worth having whether or not a cap is set: "741 admissions off 15 of 48
        #: roots" is a sentence about a finished run that nothing else records.
        self.admitted: dict[int, int] = {}
        #: What each root *is* — its family, its frame and the channel it came
        #: from. A node carries only the root's id, so anything asking a question
        #: about the lineage rather than about the node has nowhere else to look;
        #: the supply engine's cross-run novelty test is the caller, and it must
        #: get the same answer for a root drawn in an earlier session, which is
        #: why this is checkpointed rather than rebuilt.
        self.roots: dict[int, dict] = {}
        #: Roots the cap has closed. Kept so the crossing is recorded once rather
        #: than on every further admission the same lineage tries to book.
        self.saturated: set[int] = set()
        #: Roots the expansion grace applies below. Kept by root id rather than
        #: re-derived from a node, because a reframing's node carries its own
        #: family and framing but inherits the root — and it is the root's
        #: provenance that says whether the walk started too shallow.
        self.plane_roots: set[int] = set()
        self.visited_reframings: set[tuple[str, float | None]] = set()
        self.next_node_id = 1
        self.next_root_id = 1
        self.batch_index = 0
        self.tally: dict[str, int] = {}
        #: Firings and seconds per reframing operator. Priced separately from the
        #: expansion because the operators are not equally priced: the
        #: neighbourhood enumeration is the expensive one this project has, and
        #: it is on by default in production.
        self.operator_seconds: dict[str, dict] = {}
        self.ledger = Ledger(self.out_dir / ledger_module.LEDGER_NAME)
        # The header goes first, before any root exists: a run's configuration is
        # what its rows have to be read against, and a record whose first line is
        # already data is one that can be read wrongly before it can be read at all.
        self.ledger.write(
            "run",
            seed=self.seed,
            scorer=self.scorer.name,
            scoring=self.scoring_record(),
            identity=self.identity,
            colormap=self.colormap,
            limits=vars(self.limits),
            policy=self.policy.wire(),
            gates=self.gates.record(),
            report_foci=self.report_foci,
            reframings={
                "enabled": self.reframings.enabled,
                "snap": self.reframings.snap,
                "lateral": self.reframings.lateral,
                "neighborhood": self.reframings.neighborhood,
                "framings": list(self.reframings.framings),
            },
        )

    def scoring_record(self) -> dict | None:
        """What the scorer is, for the header and the summary, or `None` for a
        scorer with nothing to declare."""
        summary = getattr(self.scorer, "summary", None)
        return summary() if callable(summary) else None

    def _enforce_identity(self) -> dict | None:
        """Refuse unless the gate render is the picture this scorer's head reads.

        The claim is made only by a scorer that reads the **node regime**, which
        is the regime `expand` draws in. `None` for every other scorer — the null
        one, and any that reads some other geometry — because none of those says
        anything about what the engine drew: they render their own pictures, and a
        check about a frame nobody is going to score would refuse for nothing.
        """
        from fractal_wallpapers.models import tiles as tile_module

        if getattr(self.scorer, "regime", None) != tile_module.NODE_REGIME:
            return None
        return identity.enforce(self.colormap, self.policy.node_width, tile_module.NODE_REGIME)

    def gate_flips(self) -> dict | None:
        """The per-run sanity line: this run's sample, read again at the deploy
        geometry. Reported, never acted on."""
        return identity.dual_score(self.flip_sample, self.scorer, self.out_dir / "flip_sample")

    # ------------------------------------------------------------------ roots

    def add_root(
        self, family: dict, view: dict | None = None, *, source: str, provenance: dict
    ) -> dict:
        """Push one root onto the frontier and record where it came from.

        `view` of `None` means *this family's home view*, and the answer comes
        from the engine — there is no framing literal on this side of the
        boundary. That is the whole of the fix: a walk root and a viewport-less
        render are now the same frame by construction, and a row moved in the
        engine's table moves both.
        """
        if view is None:
            view = engine.home_view(family)
        root_id = self.next_root_id
        self.next_root_id += 1
        plane = is_plane_root(source, family)
        if plane:
            self.plane_roots.add(root_id)
        node = self._node(
            family=family,
            view=view,
            depth=ROOT_DEPTH,
            root_id=root_id,
            origin=ROOT_ORIGIN,
            parent_node_id=None,
        )
        self.roots[root_id] = {
            "family": family,
            "viewport": ledger_module.viewport(**view),
            "source": source,
        }
        self.ledger.write(
            "root",
            root_id=root_id,
            node_id=node["node_id"],
            source=source,
            family=family,
            viewport=ledger_module.viewport(**view),
            provenance=provenance,
            plane_root=plane,
        )
        return node

    def seed_from_julia_pool(self, degree: int = 2, limit: int | None = None) -> int:
        """Roots from the tracked Julia `c`-pool, one per parameter."""
        seeds = pools.julia_pool()
        if limit is not None:
            seeds = seeds[:limit]
        for entry in seeds:
            self.add_root(
                entry.family(degree),
                source="julia_c_pool",
                provenance={"seed_id": entry.id, "channel": entry.channel},
            )
        return len(seeds)

    def seed_from_phoenix_pool(self, limit: int | None = None) -> int:
        """Roots from the tracked Phoenix seed pool, one per parameter point."""
        seeds = pools.phoenix_pool()
        if limit is not None:
            seeds = seeds[:limit]
        for entry in seeds:
            self.add_root(
                entry.family(),
                source="phoenix_seed_pool",
                provenance={
                    "seed_id": entry.id,
                    "branch": entry.branch,
                    "theta": entry.theta,
                    "offset": entry.offset,
                    "real_p_mode": entry.real_p_mode,
                },
            )
        return len(seeds)

    def seed_from_file(self, path: Path, limit: int | None = None) -> int:
        """Roots from an explicit seed file — the only supply for the c-plane.

        There is deliberately no sampler behind this. An unscreened draw over the
        higher multibrot degrees measured zero good locations in a hundred and
        forty-four, so a walk that invented parameter-plane roots would be
        spending its whole budget on a channel already priced at nothing.
        """
        rows = pools.read_seed_file(Path(path))
        if limit is not None:
            rows = rows[:limit]
        for index, row in enumerate(rows):
            view = row.get("viewport")
            self.add_root(
                row["family"],
                (
                    {
                        "center_re": str(view["center_re"]),
                        "center_im": str(view["center_im"]),
                        "width": str(view["width"]),
                    }
                    if view
                    else None
                ),
                source="seed_file",
                provenance={"seed_id": row.get("id", f"row{index:04d}"), "file": Path(path).name},
            )
        return len(rows)

    # -------------------------------------------------------------- frontier

    def _node(self, *, family, view, depth, root_id, origin, parent_node_id, **extra) -> dict:
        node_id = self.next_node_id
        self.next_node_id += 1
        node = {
            "node_id": node_id,
            "root_id": root_id,
            "parent_node_id": parent_node_id,
            "family": family,
            "center_re": str(view["center_re"]),
            "center_im": str(view["center_im"]),
            "width": str(view["width"]),
            "depth": int(depth),
            "origin": origin,
            "priority": self._priority(None, depth),
            # The score half of the priority, kept apart from the draw. A
            # ranking that wants to re-price this node — the contest's lineage
            # discount does, against a count that moves after the node is
            # pushed — has to multiply the term the head set and leave the
            # exploration draw alone, and it cannot recover either from the sum.
            "score_term": NEUTRAL_PRIOR,
            **extra,
        }
        self.frontier.append(node)
        return node

    def _priority(self, score: float | None, depth: int) -> float:
        """Score, a Gumbel draw, and a nudge toward depth.

        The Gumbel is what makes a score-ordered queue explore: adding one to
        each of a set of log-weights and taking the maximum samples from those
        weights exactly, so the same expression is a greedy queue at zero
        temperature and a sampler above it.
        """
        base = NEUTRAL_PRIOR if score is None else float(score)
        gumbel = -math.log(-math.log(self.rng.random()))
        return base + GUMBEL_TEMPERATURE * gumbel + DEPTH_WEIGHT * int(depth)

    def prune(self) -> None:
        """Drop the worst nodes once the frontier passes its cap."""
        if len(self.frontier) <= self.limits.frontier_cap:
            return
        self.frontier.sort(key=lambda node: -node["priority"])
        del self.frontier[self.limits.frontier_cap :]

    def evict_capped(self) -> None:
        """Drop every node whose root has spent its expansion budget.

        *Evicted*, not skipped — see the module docstring for why skipping is not
        enough. Idempotent, so a caller that pops several times per batch can run
        it once at the top and get the same frontier either way.
        """
        self.frontier = [
            node
            for node in self.frontier
            if self.expansions.get(node["root_id"], 0) < self.limits.root_expansions
        ]

    # ----------------------------------------------------------- lineage cap

    def lineage_full(self, root_id: int) -> bool:
        """Whether this root's lineage has booked every admission it may expand from.

        Read *after* the admission that reaches the cap is counted, so the row
        that reaches it is the first one the lineage does not walk from. The
        alternative — expanding the row that reached the cap — is a lineage
        descending from its own ceiling.

        **The cap bounds expansion, and a run may finish over it.** Two nodes of
        one lineage can be in the same batch: the first closes the lineage, the
        second was popped before that happened and its candidates are already
        drawn, so they are booked. Recording them is not a choice — refusing a
        row after the fact is exactly the retro-refusal this project does not do —
        and nothing is lost by it, because the overshoot is in the count and not
        in the walk time. What the cap actually buys is that no further batch
        slot goes to the lineage, and that is true from the crossing.
        """
        cap = self.limits.lineage_admissions
        return cap is not None and self.admitted.get(int(root_id), 0) >= int(cap)

    def _book_admission(self, root_id: int) -> None:
        """Count one admission against its lineage, and close the lineage at the cap.

        Closing evicts the lineage's standing frontier nodes *here*, at the
        crossing, rather than at the next `pop_batch`. The frontier is a priority
        queue that a saturated lineage sits at the top of — it got there by being
        the lineage that admits — so leaving its nodes in place until the next
        take is exactly the batch the cap exists to reclaim.

        **Nothing is retro-refused.** Every row this lineage already wrote keeps
        the fate it earned, admissions included. What stops is expansion.
        """
        root_id = int(root_id)
        self.admitted[root_id] = self.admitted.get(root_id, 0) + 1
        if not self.lineage_full(root_id) or root_id in self.saturated:
            return
        self.saturated.add(root_id)
        standing = len(self.frontier)
        self.frontier = [node for node in self.frontier if node["root_id"] != root_id]
        evicted = standing - len(self.frontier)
        self._count("lineage_capped")
        self._count("lineage_capped:evicted", evicted)
        self.ledger.write(
            "lineage_capped",
            run_seed=self.seed,
            batch=self.batch_index,
            root_id=root_id,
            admissions=self.admitted[root_id],
            cap=self.limits.lineage_admissions,
            evicted=evicted,
        )

    def lineages(self) -> dict:
        """Admissions per root, and what the cap cost — for the run's summary.

        The distribution rides along because the headline is not the measure:
        five hundred admissions over two hundred lineages and five hundred over
        six are the same number and are not the same run, and the second is the
        one whose finished frames are a single composition.
        """
        counts = sorted(self.admitted.values(), reverse=True)
        return {
            "cap": self.limits.lineage_admissions,
            "roots_admitting": len(counts),
            "admissions": sum(counts),
            "largest": counts[0] if counts else 0,
            "capped": sorted(self.saturated),
            "distribution": lineage_distribution(self.admitted),
            "by_root": {str(root): count for root, count in sorted(self.admitted.items())},
        }

    def pop_batch(
        self, *, pool: list[dict] | None = None, size: int | None = None, key=None
    ) -> list[dict]:
        """The next batch: two reserved floors, then plain priority order.

        `pool` narrows the candidates to a subset of the frontier and `size` to a
        number of slots other than a whole batch. Both exist for one caller — the
        supply engine, which divides a batch between partitions and then asks each
        partition for its own share — and both default to the plain walk's
        behaviour, which is the whole frontier and a whole batch.

        `key` replaces the ranking number, highest first, and defaults to the
        node's own stored priority. It exists because a node's priority is drawn
        once and never re-drawn — which is right for the Gumbel and wrong for a
        term that depends on what the run has booked *since* — so a caller that
        prices the queue against a running count ranks with a function here rather
        than by writing over what the head and the draw already decided.

        **Both reserved floors are shares of whatever size is asked for**, so a
        two-slot take reserves a fraction of two slots rather than the whole-batch
        count. Asking for a whole batch reproduces the plain walk exactly.
        """
        self.evict_capped()
        if pool is None:
            chosen_from = self.frontier
        else:
            # A caller's pool was taken before the eviction and may name nodes the
            # eviction just dropped. Intersecting is what keeps the frontier the
            # authority on which nodes exist.
            standing = {node["node_id"] for node in self.frontier}
            chosen_from = [node for node in pool if node["node_id"] in standing]
        rank = key if key is not None else (lambda node: node["priority"])
        live = sorted(chosen_from, key=lambda node: -rank(node))

        size = min(self.limits.batch if size is None else int(size), len(live))
        if size <= 0:
            return []

        taken: dict[int, dict] = {}

        fresh_slots = min(size, math.ceil(size * self.limits.breadth_floor))
        fresh = [node for node in live if self.expansions.get(node["root_id"], 0) == 0]
        for node in fresh[:fresh_slots]:
            taken[node["node_id"]] = node
        self._count("breadth_floor_filled", len(taken))
        self._count("breadth_floor_unfilled", fresh_slots - len(taken))

        if self.reframings.enabled and self.limits.operator_quota > 0:
            reframed = [
                node
                for node in live
                if node["origin"] in REFRAMED_ORIGINS and node["node_id"] not in taken
            ]
            share = math.ceil(size * self.limits.operator_quota / max(1, self.limits.batch))
            quota = max(0, min(share, size - len(taken)))
            for node in reframed[:quota]:
                taken[node["node_id"]] = node
            self._count("operator_quota_filled", min(quota, len(reframed)))
            self._count("operator_quota_unfilled", max(0, quota - len(reframed)))

        for node in live:
            if len(taken) >= size:
                break
            taken.setdefault(node["node_id"], node)

        batch = list(taken.values())
        chosen = set(taken)
        self.frontier = [node for node in self.frontier if node["node_id"] not in chosen]
        for node in batch:
            self.expansions[node["root_id"]] = self.expansions.get(node["root_id"], 0) + 1
        return batch

    def _charge(self, operator: str, seconds: float) -> None:
        """Second and firing, per reframing operator.

        The operators are not equally priced and only the neighbourhood
        enumeration's cost has ever been measured — out of band, on a replay,
        and written into a scratch report that is now gone. Charged here so the
        run that pays for it is the run that reports it, which is the only
        version of this number a later reader can check.
        """
        cell = self.operator_seconds.setdefault(operator, {"firings": 0, "seconds": 0.0})
        cell["firings"] += 1
        cell["seconds"] += float(seconds)

    def _count(self, name: str, amount: int = 1) -> None:
        self.tally[name] = self.tally.get(name, 0) + amount

    # ------------------------------------------------------------------ grace

    def plane_rung(self, root_id: int, depth: int) -> int | None:
        """Rungs below a plane-seed root, or `None` when the root is not one.

        Zero is the root itself, so a root's own children are rung 1. Nothing
        below a non-plane root has a rung: the number is a statement about the
        one channel that starts above its material, not a second name for depth.
        """
        if int(root_id) not in self.plane_roots:
            return None
        return max(0, int(depth) - ROOT_DEPTH)

    def graced(self, rung: int | None) -> bool:
        """Whether the expansion floor is waived at this rung below a plane root."""
        return rung is not None and 1 <= rung <= self.limits.plane_grace_rungs

    def _rung_counts(self, rung: int | None, *, cleared: bool, grace: bool) -> None:
        """One gate survivor's line in the survival-by-rung table.

        Counted in the tally rather than only on the row, so the table is in every
        run's summary and does not need the ledger re-read to be seen. Zero-padded
        because the counters are reported in sorted order and rung 10 must not sort
        between 1 and 2.
        """
        if rung is None:
            return
        self._count(f"plane_rung:{rung:02d}:survivors")
        if cleared:
            self._count(f"plane_rung:{rung:02d}:cleared_junk")
        if grace:
            self._count(f"plane_rung:{rung:02d}:graced")

    # ---------------------------------------------------------------- expand

    def expand_batch(self, batch: list[dict]) -> list[dict]:
        """Expand one batch and return its survivors."""
        return self.expand(batch)["survivors"]

    def expand(self, batch: list[dict]) -> dict:
        """Expand one batch, one engine call per distinct family identity.

        Returns the survivors *and* the candidate rows exactly as they were
        recorded. A caller that has to reconcile what it found against what it
        wrote needs the rows themselves, and re-reading them from the ledger it
        just appended to would be a second answer to what the batch did.
        """
        groups: dict[str, list[dict]] = {}
        for node in batch:
            groups.setdefault(family_key(node["family"]), []).append(node)

        survivors: list[dict] = []
        candidates: list[dict] = []
        for key, nodes in groups.items():
            report = engine.expand(
                {
                    "schema": 1,
                    "family": nodes[0]["family"],
                    "seed": self.seed,
                    "nodes": [
                        {
                            "node_id": node["node_id"],
                            "root_id": node["root_id"],
                            "center_re": node["center_re"],
                            "center_im": node["center_im"],
                            "width": node["width"],
                            "depth": node["depth"],
                        }
                        for node in nodes
                    ],
                    "out_dir": str(self.views_dir()),
                    "colormap": self.colormap,
                    "colormap_dir": str(engine.colormap_dir()),
                    "gates": self.gates.for_family(nodes[0]["family"]).wire(),
                    "policy": self.policy.wire(),
                    "report_foci": self.report_foci,
                }
            )
            by_id = {node["node_id"]: node for node in nodes}
            kept, seen = self._record(report, by_id, json.loads(key))
            survivors.extend(kept)
            candidates.extend(seen)
        return {"survivors": survivors, "candidates": candidates}

    def views_dir(self) -> Path:
        """Where the engine writes this run's gate renders."""
        return views_dir(self.out_dir)

    def _gate_renders(self, rows: list[dict]) -> list[Path | None] | None:
        """The picture the engine already made of each of these survivors.

        `None` — no offer at all — unless this run *asserted* the identity, which
        is the same thing as the scorer reading the node regime and the four
        settings having held. A judge that reads some other geometry is handed
        nothing: the gate render is a real picture of the right place at the wrong
        size, which is exactly the kind of wrong answer that looks right.
        """
        if self.identity is None:
            return None
        directory = self.views_dir()
        return [None if not row.get("image") else directory / row["image"] for row in rows]

    def _check_regime(self, report: dict) -> None:
        """Refuse a report drawn at a geometry this run's scorer does not read.

        The run-start check pins the settings; this pins the *outcome*, off the
        engine's own statement of what it drew. It costs a comparison per engine
        call and it is the only thing standing between "the head reads the gate
        render" and a silent frame-size change making that sentence false.
        """
        regime = self.identity and self.identity.get("regime")
        if regime is None:
            return
        drew = f"{report['tile'][0]}x{report['tile'][1]}ss{report['field_supersample']}"
        if drew != regime:
            raise identity.IdentityBroken(
                f"the engine drew this batch at {drew}, but this run scores gate renders as "
                f"{regime} tiles. The picture the head would be handed is not the one it was "
                f"trained on, and nothing about the score it returned would look wrong."
            )

    def _candidate(self, row: dict, parent: dict, family: dict) -> dict:
        """One engine candidate as the ledger row it will become, score fields blank.

        Built before anything is scored and *before* anything is written, because
        the scorer is handed this row: a judge that saw a different object from
        the one the ledger keeps could not be checked against the record.
        """
        return {
            "run_seed": self.seed,
            "batch": self.batch_index,
            "parent_node_id": row["node_id"],
            "root_id": row["root_id"],
            "depth": row["depth"],
            "child_index": row["child_index"],
            "family": family,
            "viewport": ledger_module.viewport(row["center_re"], row["center_im"], row["width"]),
            "branch": row["branch"],
            "placement": row["placement"],
            "focus_score": row.get("focus_score"),
            "maxiter": row["maxiter"],
            "interior_fraction": row["interior_fraction"],
            "escape": row.get("escape"),
            "occupancy": row.get("occupancy"),
            "image": row.get("image"),
            "origin": parent["origin"],
            "atom_key": parent.get("atom_key"),
            # Which claim on the batch bought this node's expansion — the
            # exploration share or the deficit-priced contest. `null` for every
            # walk that is not a harvest, and absent from every ledger written
            # before the share existed, so a reader treats it as optional.
            "channel": parent.get("channel"),
            "fate": row["fate"],
            "scorer": self.scorer.name,
            # The three the survival-by-rung table is built from. `plane_rung` is
            # structural and known now; the other two are verdicts and are filled
            # in beside the score, where the floors are actually consulted.
            "plane_rung": self.plane_rung(row["root_id"], row["depth"]),
            "cleared_junk": None,
            "grace": None,
            # `P(≥3)`, `P(≥4)`, and why there is neither. The currency weights a
            # class 4 ten times a class 3, so a row that carried only the first
            # would make every machine-classed find a 3 whatever the head said.
            "score": None,
            "score_great": None,
            "score_error": None,
            # Which picture the verdict was read off: the geometry, and the digest
            # of the whole recipe. Provenance, not semantics — one scale acts
            # across regimes — but a union that holds ledgers scored at two
            # geometries must never have to guess which a row is, and the digest
            # is how a later reader checks a persisted picture is still this one.
            # Both stay `null` where nothing had an opinion.
            "score_regime": None,
            "score_view": None,
        }

    def _record(self, report: dict, by_id: dict, family: dict) -> tuple[list[dict], list[dict]]:
        """Score the batch, then write every candidate the engine reported, in order.

        Three passes, and the middle one is the reason: the scorer is handed
        every survivor at once, together with the gate render the engine already
        made of each, and nothing is written until it has answered for all of
        them. A per-candidate score inside the write loop would fix the ledger's
        order to the order the readings finished.
        """
        self._check_regime(report)
        # Before the candidates, because that is the order they happened in: the
        # focus set is a reading of the parent frame and the candidates are draws
        # against it. A reader walking the ledger forward sees what a rung was
        # aiming at before it sees where it landed.
        for found in report.get("foci") or []:
            parent = by_id[found["node_id"]]
            self.ledger.write(
                "foci",
                node_id=found["node_id"],
                root_id=found["root_id"],
                depth=found["depth"],
                family=family,
                viewport=ledger_module.viewport(
                    parent["center_re"], parent["center_im"], parent["width"]
                ),
                tile=report["tile"],
                found=found["found"],
                spread_radius=found["spread_radius"],
                kept=found["kept"],
            )
        candidates = [
            self._candidate(row, by_id[row["node_id"]], family) for row in report["candidates"]
        ]
        # The engine's own verdict, counted before the scorer sees any of it — so
        # `fate:survived` stays the gate-survivor count it has always been, and
        # the three `tier:` counters below divide exactly that number.
        for candidate in candidates:
            self._count(f"fate:{candidate['fate']}")

        standing = [
            index
            for index, candidate in enumerate(candidates)
            if candidate["fate"] == ledger_module.SURVIVED
        ]
        standing_rows = [candidates[index] for index in standing]
        readings = self.scorer.read(standing_rows, pictures=self._gate_renders(standing_rows))
        for index, reading in zip(standing, readings, strict=True):
            candidates[index]["score"] = reading.score
            candidates[index]["score_great"] = reading.great
            candidates[index]["score_error"] = reading.error
            candidates[index]["score_regime"] = reading.regime
            candidates[index]["score_view"] = reading.view
            if reading.error is not None:
                self._count("score_failed")
            else:
                self.flip_sample.offer(candidates[index])

        survivors: list[dict] = []
        recorded: list[dict] = []
        for row, candidate in zip(report["candidates"], candidates, strict=True):
            parent = by_id[row["node_id"]]
            if candidate["fate"] != ledger_module.SURVIVED:
                recorded.append(self.ledger.write("candidate", node_id=None, **candidate))
                continue
            # Two questions, two floors. Booking decides what the census counts;
            # expansion decides what the frontier may stand on. A row that fails
            # the second is recorded and not walked from; a row that passes only
            # the second reaches the frontier under its own fate and is invisible
            # to every book in the project.
            rung = candidate["plane_rung"]
            grace = self.graced(rung)
            candidate["grace"] = grace
            if not self.scorer.admits(candidate, candidate["score"]):
                cleared = self.scorer.expandable(candidate, candidate["score"])
                candidate["cleared_junk"] = cleared
                self._rung_counts(rung, cleared=cleared, grace=grace)
                # Grace waives the floor, never the missing verdict: a candidate
                # with no score at all has a failed render behind it rather than a
                # low opinion, and there is nothing for the waiver to overrule.
                if not cleared and not (grace and candidate["score"] is not None):
                    candidate["fate"] = ledger_module.NOT_ADMITTED
                    self._count("tier:refused")
                    self._count(
                        "not_admitted:no_score"
                        if candidate["score"] is None
                        else "not_admitted:below"
                    )
                    recorded.append(self.ledger.write("candidate", node_id=None, **candidate))
                    continue
                candidate["fate"] = ledger_module.EXPANDABLE
                self._count("tier:expandable")
                if not cleared:
                    self._count("grace:rescued")
                    self._count(f"plane_rung:{rung:02d}:rescued")
            else:
                # Every admission is expandable by the scorer's own contract, so
                # the junk floor is not asked a second time to be told so.
                candidate["cleared_junk"] = True
                self._rung_counts(rung, cleared=True, grace=grace)
                self._count("tier:admitted")
                self._book_admission(row["root_id"])

            if self.lineage_full(row["root_id"]):
                # The lineage has booked its cap. The row keeps its fate and goes
                # on the record with no node behind it — which is the same shape
                # a refused row has, and means "not expanded from" everywhere it
                # is read. Expandable rows of a saturated lineage stop too: the
                # cap closes a lineage, not a tier of it.
                self._count("lineage_capped:not_expanded")
                recorded.append(self.ledger.write("candidate", node_id=None, **candidate))
                continue

            node = self._node(
                family=family,
                view={
                    "center_re": row["center_re"],
                    "center_im": row["center_im"],
                    "width": row["width"],
                },
                depth=row["depth"],
                root_id=row["root_id"],
                origin=(parent["origin"] if parent["origin"] in REFRAMED_ORIGINS else WALK_ORIGIN),
                parent_node_id=row["node_id"],
                atom_key=parent.get("atom_key"),
            )
            node["priority"] = self._priority(candidate["score"], row["depth"])
            node["score_term"] = (
                NEUTRAL_PRIOR if candidate["score"] is None else float(candidate["score"])
            )
            recorded.append(self.ledger.write("candidate", node_id=node["node_id"], **candidate))
            survivors.append(node)

        # After the write loop and not inside it, because a candidate's fate is
        # not settled until that loop has had it: a survivor can still become
        # `expandable` or `not_admitted` when the floors are consulted, and the
        # refine leg picks over gate survivors of all three fates.
        for candidate in candidates:
            if candidate["fate"] in ledger_module.SCORED:
                self.best.offer(candidate)

        for row in report["dead"]:
            self.ledger.write(
                "node_dead",
                run_seed=self.seed,
                batch=self.batch_index,
                node_id=row["node_id"],
                root_id=row["root_id"],
                depth=row["depth"],
                family=family,
                cause=row["cause"],
            )
            self._count(f"dead:{row['cause']}")
        return survivors, recorded

    # ------------------------------------------------------------ reframings

    def trigger_reframings(self, survivors: list[dict]) -> int:
        """Fire the reframing operators off this batch's admissions.

        **Triggered on admissions, never standalone.** An operator inherits the
        quality of whatever triggered it, so it is applied to places the walk
        found and admitted — and applying it to anything else would be sourcing
        atoms from first principles, which is the thing seven attempts found
        does not work.
        """
        if not self.reframings.enabled:
            return 0
        pushed = 0
        for node in survivors:
            degree = operators.degree_of(
                node["family"]["kind"], int(node["family"].get("degree", 2))
            )
            if degree is None:
                # A dynamical viewport is a z-plane point and has no nucleus in
                # the parameter-plane sense. Skipped rather than faked, and
                # counted rather than logged: one row per survivor of every
                # Julia walk would say the same thing several thousand times.
                self._count("reframing_undefined")
                continue
            fire, why = self.governor.should_probe(
                degree, node["center_re"], node["center_im"], node["width"]
            )
            if not fire:
                self.ledger.write(
                    "probe",
                    run_seed=self.seed,
                    batch=self.batch_index,
                    node_id=node["node_id"],
                    degree=degree,
                    fired=False,
                    reason=why,
                )
                continue
            pushed += self._propose(node, degree)
        return pushed

    def _propose(self, node: dict, degree: int) -> int:
        view = {
            "node_id": node["node_id"],
            "center_re": node["center_re"],
            "center_im": node["center_im"],
            "width": node["width"],
        }
        found: list[operators.Reframing] = []
        # One firing, one answer to "which atom is this view on?". Whoever needs
        # it first pays for it and the rest read it — the miss included, which is
        # the majority case and was two thirds of the disc operators' bill.
        parent_atom = operators.ParentAtom()

        if self.reframings.snap:
            started = time.monotonic()
            rows = operators.snap_to_nucleus(view, degree=degree, framings=self.reframings.framings)
            self._charge("snap_to_nucleus", time.monotonic() - started)
            found.extend(rows)
            parent_atom = operators.parent_atom_from_snap(rows)

        if self.reframings.lateral:
            started = time.monotonic()
            row = operators.lateral_to_sibling(view, self.rng, degree=degree, parent=parent_atom)
            self._charge("lateral_to_sibling", time.monotonic() - started)
            found.append(row)

        if self.reframings.neighborhood:
            started = time.monotonic()
            rows = operators.expand_neighborhood(
                view,
                self.rng,
                degree=degree,
                framings=self.reframings.framings,
                parent=parent_atom,
            )
            self._charge("expand_neighborhood", time.monotonic() - started)
            keep = self.reframings.neighborhood_proposals
            available = [row for row in rows if row.available]
            ranks = sorted({row.extra.get("found_rank", 0) for row in available})[:keep]
            found.extend(
                row for row in rows if not row.available or row.extra.get("found_rank", 0) in ranks
            )

        pushed = 0
        for row in found:
            used, why, child = False, "", None
            if row.available:
                identity = (row.key, row.framing)
                if identity in self.visited_reframings:
                    # The framing is part of the identity — the same atom at two
                    # framings is two views — and the operator deliberately is
                    # not: it is provenance, and two operators reaching one view
                    # have found one view.
                    why = "already_visited"
                else:
                    self.visited_reframings.add(identity)
                    child = self._node(
                        family=node["family"],
                        view={
                            "center_re": row.center_re,
                            "center_im": row.center_im,
                            "width": _decimal(row.width),
                        },
                        depth=node["depth"],
                        root_id=node["root_id"],
                        origin=row.operator,
                        parent_node_id=node["node_id"],
                        atom_key=row.key,
                    )
                    used, pushed = True, pushed + 1
            self.ledger.write(
                "reframing",
                run_seed=self.seed,
                batch=self.batch_index,
                node_id=node["node_id"],
                # The node this firing put on the frontier, or `null` where it
                # put none there. Without it a chain through a reframing is a
                # geometric reconstruction — match the row's viewport against
                # every later row's parent frame — which is what the website's
                # figure maker had to do, recovering 283 of 1,965 and dropping
                # 123. It is a lookup now. Old ledgers keep their schema and do
                # not carry it, so a reader treats it as optional and falls back.
                pushed_node_id=child["node_id"] if child is not None else None,
                root_id=node["root_id"],
                operator=row.operator,
                available=row.available,
                reason=row.reason,
                framing=row.framing,
                atom_key=row.key,
                period=row.period,
                log10_abs_A=row.log10_abs_A,
                window_scale=row.window_scale,
                node_margin_decades=row.node_margin_decades,
                deploy_margin_decades=row.deploy_margin_decades,
                viewport=(
                    ledger_module.viewport(row.center_re, row.center_im, _decimal(row.width))
                    if row.available
                    else None
                ),
                newton_solves=row.newton_solves,
                used=used,
                unused_reason=why,
                extra=row.extra,
            )
            self._count(f"reframing:{row.operator}:{'available' if row.available else row.reason}")
        return pushed

    # -------------------------------------------------------- refine framing

    def refine_dir(self) -> Path:
        """Where the refine leg's node-regime scan frames go, under the run."""
        return self.out_dir / "framings"

    def refine_framings(self, log=None) -> dict:
        """Scan the framing of this walk's best `k` survivors. **After it closes.**

        The gallery pass's step 5a, at the other end of the pipeline: the same
        window, the same margin, the same gate requirement, the same provenance
        shape, through the same [`curation.framing`] module. What differs is only
        *which* frames are scanned — a pass scans the neighbourhoods it is about
        to colour, and a walk scans the handful it is most likely to have found.

        **At close, per walk, top-k**, which is the archive's own shape and is
        what makes it affordable: the leg is seven node-regime renders a location
        and it is bought once per run rather than once per admission.

        **Nothing here feeds back into the walk.** No priority moves, no score
        term is re-read, no descent is re-taken; every row this walk wrote stays
        exactly as it was written. What the leg produces is a `refined` row per
        scanned location, appended after the candidates, and
        [`fractal_wallpapers.supply.ledgers.admitted`] is where a reader prefers
        it. That is the whole of the never-edit-in-place rule: the walk's shape
        cannot refine before the row is written, because "the top three of this
        walk" is not knowable until the walk has finished.
        """
        log = log or (lambda _line: None)
        if self.limits.refine_per_walk <= 0:
            return {"status": "off", "reason": "--refine-per-walk 0"}
        if self.identity is None:
            # The same precondition the gate render's own score rests on. Without
            # it the scan would draw frames at a geometry this run's judge does
            # not read, and record the result as a framing decision.
            return {
                "status": "skipped",
                "reason": "this run does not assert the node-regime identity, so the scan "
                "would compare frames the head was never trained on",
            }
        rows = self.best.take()
        if not rows:
            return {"status": "empty", "reason": "no scored gate survivor to refine", "seen": 0}

        started = time.monotonic()
        scanned = [
            {
                "key": _location_text(row),
                "family": row["family"],
                "viewport": row["viewport"],
                "maxiter": row["maxiter"],
                # Carried rather than dropped: a centered location is refined on
                # its scale alone, and the flag is the only thing that says so.
                "centered": bool(row.get("centered")),
            }
            for row in rows
        ]
        records = framing.refine(
            scanned,
            directory=self.refine_dir(),
            scorer=self.scorer,
            margin=self.refine_margin,
            # What the walk's OWN read of the x1.0 frame was, so the record
            # carries the two readings of one frame side by side. This is the
            # gallery pass's sidecar comparison asked at the site that can
            # actually answer it: here the picture the first read was taken off
            # is still on disk.
            scores={cell["key"]: _walk_read(row) for cell, row in zip(scanned, rows, strict=True)},
            log=log,
        )
        seconds = time.monotonic() - started
        self._charge("refine_framing", seconds)

        pushed = 0
        for record, row in zip(records, rows, strict=True):
            record["gate_render"] = self._gate_comparison(row, record)
            written = self._write_refined(row, record)
            pushed += self._admit_refined(row, record, written)
            self._count("refine:scanned")
            self._count(f"refine:{'adopted' if record['adopted'] else record['refused']}")
        report = {
            "status": "on",
            "k": self.limits.refine_per_walk,
            "margin": self.refine_margin,
            "survivors_offered": self.best.seen,
            "operator_nodes_pushed": pushed,
            **framing.price(records),
            "gate_render": _gate_report(records),
        }
        log(
            f"[refine] {report['adopted']}/{report['locations']} framing(s) adopted at "
            f"margin {self.refine_margin:g}, {report['frames']} frame(s) in {seconds:.1f}s"
        )
        return report

    def _write_refined(self, row: dict, record: dict) -> dict:
        """One `refined` ledger row: the join, both frames, both readings.

        Keyed by the **original** family and viewport, because that is the
        identity every reader already dedups on — a refined row is a statement
        *about* a location the ledger already holds, not a second location.
        """
        best = record["best"] or {}
        return self.ledger.write(
            ledger_module.REFINED,
            run_seed=self.seed,
            batch=self.batch_index,
            family=row["family"],
            viewport=row["viewport"],
            maxiter=row["maxiter"],
            adopted=bool(record["adopted"]),
            refused=record["refused"],
            margin=record["margin"],
            gain=record["gain"],
            gain_p_ge4=record["gain_p_ge4"],
            width_scale=record["width_scale"],
            dx=record["dx"],
            dy=record["dy"],
            framing=record["slug"],
            # The frame the reader is to prefer, and what the head made of it.
            # `null` on a row nothing was adopted for, which is what tells a
            # reader to leave the candidate row alone.
            refined_viewport=best.get("viewport") if record["adopted"] else None,
            refined_maxiter=best.get("maxiter") if record["adopted"] else None,
            score=best.get("p_ge3") if record["adopted"] else None,
            score_great=best.get("p_ge4") if record["adopted"] else None,
            # The window's best whether or not it was taken: the evidence the
            # margin is set where it should be, which a record holding only the
            # adopted ones could not show.
            best_score=best.get("p_ge3"),
            best_score_great=best.get("p_ge4"),
            scan_score=(record["original"] or {}).get("p_ge3"),
            scan_score_great=(record["original"] or {}).get("p_ge4"),
            walk_score=row.get("score"),
            walk_score_great=row.get("score_great"),
            gate_render=record["gate_render"],
            # The two frames of the window a person looks at, by name under the
            # run's own `framings/`. Regenerable like every other picture this
            # project makes, and on the row because a before-and-after sheet is
            # the only verdict on the head's framing taste there is.
            scan_picture=(record["original"] or {}).get("picture"),
            best_picture=(record["best"] or {}).get("picture"),
            scanned=record["scanned"],
            scorer=self.scorer.name,
            score_regime=row.get("score_regime"),
        )

    def _admit_refined(self, row: dict, record: dict, written: dict) -> int:
        """Book a refinement that crosses the keeper floor, and fire the operators.

        Only where it **crosses**: a row already admitted had its operators fired
        at its own centre while the walk was running, and firing them again at a
        centre a quarter-frame away would be paying twice for the atom the dedup
        set is about to refuse anyway. A row the refinement lifts over the floor
        is a new admission and gets what any admission gets.

        The nodes this pushes are on the frontier the run is **closing with**, so
        this walk expands none of them and the checkpoint is already written —
        they are a record of what the operator found, not a feed into a descent.
        """
        if not record["adopted"]:
            return 0
        best = record["best"]
        if self.scorer.admits(row, row.get("score")):
            return 0
        if not self.scorer.admits(row, best["p_ge3"]):
            return 0
        self._count("refine:admitted")
        root_id = int(row.get("root_id") or 0)
        self._book_admission(root_id)
        if self.lineage_full(root_id) or not self.reframings.enabled:
            return 0
        node = self._node(
            family=row["family"],
            view=best["viewport"],
            depth=int(row.get("depth") or ROOT_DEPTH),
            root_id=root_id,
            origin=REFINED_ORIGIN,
            parent_node_id=written.get("node_id"),
            atom_key=row.get("atom_key"),
        )
        node["score_term"] = float(best["p_ge3"])
        node["priority"] = self._priority(best["p_ge3"], node["depth"])
        return self.trigger_reframings([node])

    def _gate_comparison(self, row: dict, record: dict) -> dict:
        """The walk's own gate render against the scan's, for the same frame.

        The gallery pass found its `x1.0` reads disagreeing with the supply
        sidecar's by up to 0.029 on `P(≥4)` and could not say why: 19 of its 20
        locations had been scored off a walk's gate render, and that picture is
        not on the view-cache path. Here it is — this run drew it — so the two
        pictures are hashed and the two readings differenced, and the question
        becomes a measurement instead of an inference.
        """
        scan = record.get("original") or {}
        gate = self.views_dir() / str(row.get("image") or "")
        drawn = self.refine_dir() / str(scan.get("picture") or "")
        walk_read, scan_read = row.get("score_great"), scan.get("p_ge4")
        return {
            "gate_sha256": _digest(gate) if row.get("image") else None,
            "scan_sha256": _digest(drawn) if scan.get("picture") else None,
            "gate_bytes": gate.stat().st_size if gate.is_file() else None,
            "scan_bytes": drawn.stat().st_size if drawn.is_file() else None,
            "walk_p_ge4": walk_read,
            "scan_p_ge4": scan_read,
            "delta_p_ge4": (
                None
                if (walk_read is None or scan_read is None)
                else round(scan_read - walk_read, 8)
            ),
            "maxiter": {"walk": row.get("maxiter"), "scan": scan.get("maxiter")},
            "regime": row.get("score_regime"),
        }

    # ------------------------------------------------------------------- run

    def run(self) -> dict:
        """Expand batches until the budget or the frontier runs out."""
        for index in range(self.limits.batches):
            self.batch_index = index
            batch = self.pop_batch()
            if not batch:
                break
            survivors = self.expand_batch(batch)
            self.trigger_reframings(survivors)
            self.prune()
            self._count("batches")
            self._count("expanded", len(batch))

        # After the last batch and before the summary: the leg is about the walk
        # as a whole, so it cannot run until there is a whole walk to rank, and
        # the summary has to be able to report what it cost.
        refined = self.refine_framings()

        summary = {
            "seed": self.seed,
            "batches": self.tally.get("batches", 0),
            "roots": self.next_root_id - 1,
            "frontier": len(self.frontier),
            "scorer": self.scorer.name,
            "scoring": self.scoring_record(),
            "identity": self.identity,
            "gate_flips": self.gate_flips(),
            "lineages": self.lineages(),
            "probe": self.governor.tally(),
            "refine": refined,
            "counts": dict(sorted(self.tally.items())),
            "ledger": tracked_name(self.ledger.path),
        }
        self.ledger.write("summary", **summary)
        self.ledger.close()
        return summary


def _location_text(row: dict) -> str:
    """A ledger row's location identity as JSON, the spelling the sidecar uses.

    The refine leg keys its records on this, so a scan taken at a walk and a scan
    taken at a gallery pass are keyed the same way and a reader joining the two
    is joining on one string rather than on two spellings of one idea.
    """
    key = key_of_row(row)
    return "" if key is None else json.dumps(key, ensure_ascii=False)


def _walk_read(row: dict) -> dict:
    """What this walk's own judge said about the frame, in the shape the refine
    record keeps a second opinion in."""
    return {
        "regime": row.get("score_regime"),
        "head_sha256": None,
        "p_ge4": row.get("score_great"),
        "p_ge3": row.get("score"),
    }


def _digest(path: Path) -> str | None:
    """The sha256 of a picture, or `None` where it is not on disk."""
    import hashlib

    path = Path(path)
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _gate_report(records: list[dict]) -> dict:
    """The gate-render comparison over a leg: how often the two paths agree.

    The measurement the gallery pass could not take. `identical` counts the
    frames where the walk's own render and the scan's are the same bytes;
    `exact` counts the readings that came out equal. They are different
    questions and a run where the first is high and the second is not would be
    saying something about the head rather than about the engine.
    """
    cells = [record.get("gate_render") or {} for record in records]
    both = [cell for cell in cells if cell.get("gate_sha256") and cell.get("scan_sha256")]
    deltas = [abs(cell["delta_p_ge4"]) for cell in cells if cell.get("delta_p_ge4") is not None]
    return {
        "compared": len(both),
        "identical_bytes": sum(1 for cell in both if cell["gate_sha256"] == cell["scan_sha256"]),
        "readings": len(deltas),
        "exact": sum(1 for delta in deltas if delta == 0.0),
        "max_abs_delta_p_ge4": round(max(deltas), 8) if deltas else None,
        "mean_abs_delta_p_ge4": (round(sum(deltas) / len(deltas), 8) if deltas else None),
    }


def views_dir(out_dir) -> Path:
    """Where a run keeps its gate renders, given the run's directory.

    One spelling, and three readers now: the engine is told to write them here,
    the walk's own scorer is told to find them here, and curation's re-score
    reaches a finished run's the same way — from the run directory its ledger
    sits in. A second copy of `/ "views"` is how a re-score silently starts
    re-rendering pictures that were already on disk.
    """
    return Path(out_dir) / "views"


def lineage_distribution(admitted: dict) -> dict:
    """How a run's admissions spread over its lineages — the monotony measure.

    `max`, `median` and the top five, because those three say between them
    whether a finished frame set will be one composition in a hundred palettes.
    `deep_run1` would have reported a max of 85 against a median of 2.
    """
    counts = sorted((int(v) for v in admitted.values()), reverse=True)
    total = sum(counts)
    middle = len(counts) // 2
    if not counts:
        median = None
    elif len(counts) % 2:
        median = float(counts[middle])
    else:
        median = (counts[middle - 1] + counts[middle]) / 2.0
    return {
        "lineages_admitting": len(counts),
        "admissions": total,
        "max": counts[0] if counts else 0,
        "median": median,
        "top5": counts[:5],
        "top5_share": round(sum(counts[:5]) / total, 4) if total else None,
    }


def is_plane_root(source: str, family: dict) -> bool:
    """Whether a root is one of the parameter-plane ones the grace applies below.

    Both halves are load-bearing. The source names the one channel that hands over
    roots at a family's home frame rather than at a place the walk found, and
    [`fractal_wallpapers.discovery.operators.degree_of`] is what the walk already
    means by *parameter plane* — the same predicate the reframing probe reads, so
    a dynamical row in a seed file is not annexed by the word "seeds".
    """
    if source not in PLANE_ROOT_SOURCES:
        return False
    kind = family.get("kind")
    if not isinstance(kind, str):
        return False
    return operators.degree_of(kind, int(family.get("degree", 2))) is not None


def _decimal(value: float) -> str:
    """A computed width, as the decimal string it will be recorded as."""
    text = repr(float(value))
    return text if any(mark in text for mark in ".eE") else text + ".0"


__all__ = [
    "PLANE_ROOT_SOURCES",
    "ROOT_DEPTH",
    "Gates",
    "Limits",
    "NullScorer",
    "Policy",
    "Reframings",
    "Walk",
    "family_key",
    "is_plane_root",
    "lineage_distribution",
    "nucleus",
    "views_dir",
]
