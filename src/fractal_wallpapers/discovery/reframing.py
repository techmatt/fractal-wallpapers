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
        │  16x 24x 32x 48x 64x      the nine rungs, offered directly
        │  96x 128x 192x 256x
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
nine widths is not nine locations — that would put one atom into nine seats and
would count one find nine times in every book downstream. So every rung is
drawn, every one is scored, every reading is on the row, and the location's own
score is the rung the head picked. The rungs are **offered directly** rather
than walked to, because the built refinement moves x1.414 a step
([`curation.framing.WIDTH_LADDER`]) and cannot reach 256x from 16x in anything a
window that size can express.

**A nucleus location is `centered`.** The centre is the atom the operators
solved for, and it is the whole of what the location is; a framing refinement
over one of these rows may move the **scale** and nothing else.
[`curation.framing`] reads the flag and drops its recentring stage for a row
that carries it, so a later pass cannot walk a quarter-frame off the nucleus and
still call the result this location.

**Record and rank, never gate.** Every derived nucleus is scored and written,
whatever the head said. Distinctness is applied where a *sheet* is cut and never
to the ledger, so a sitting never sees fifty lookalikes off one seed and the
record still says what the channel found.

**The seed is a place a person judged.** Which is why [`operators.snap_at_seed`]
exists and why every derived row carries the seed's tier: the claim being
inherited is somebody's verdict on a picture, and a channel that could not say
whose verdict, at what tier, would be unpriceable.

## The nine rungs, and where the ladder stops at each end

Measured body width of eleven ring-seeded atoms at 1280 px
(`scratch/framing_ladder.jsonl`): 115-183 px at the 16x rung, 57-92 px at 32x,
28-45 px at 64x. The band that reads as *a minibrot with detail around it* is
50-100 px, which is the 32x rung; the walk's widest rung, 16x, is a factor of two
too tight, and 48x and 64x sit below the band at roughly 38-61 px and 28-45 px.
Scaled along the same measurement the outer rungs land at 19-30 px (96x), 14-23
(128x), 10-15 (192x) and 7-11 (256x).

The band was a prediction and the ladder is the measurement of it. Generation 1
drew 16x, 24x and 32x on all 792 of its nuclei and the head-q4 rate rose monotone
outward — 2.1%, 2.9%, 3.5% — which is the direction that says a ladder is
stopping too early. 48x and 64x were added for the question to land in, and over
5,773 locations drawn on that five-rung ladder **the head's pick came back very
nearly flat: 17.5 / 22.2 / 23.0 / 17.5 / 19.8%** at 16 / 24 / 32 / 48 / 64x.

A flat pick over `k` rungs puts `2/k` of the picks on an end, and an end pick is a
truncation rather than an optimum — the head was asked for its favourite width
and answered with the widest or narrowest width it was offered. What extending a
ladder does about that is already on the record: under the three-rung ladder the
outermost rung took **30.6%** of picks, and adding 48x and 64x did not drain that
pile, it *moved* it — 32x settled to 23.0% and the new outer end took 19.8%. So
the ladder went to nine on 2026-09-01 by carrying two more rungs at each end at
its own alternating step (x1.5, x1.333) — `{8, 12}` doubled four times — and the
honest claim for them was dilution and reach rather than a cure: 37.3% of picks
sat on an end at five rungs and about 22% would at nine. Every rung is drawn,
scored and on the row either way, and [`Channel.summary`]'s `ends` block is where
the next leg reads whether the new rungs took picks off the old ends.

**Read on 2026-09-04, and the two ends answered differently, so the ladder moved
outward rather than growing again.** Over `reframe_g7`'s 488 picks the old ends
took 21.1% against 37.3 / 37.3 / 37.8% on the five-rung legs, so the extension
did drain them. But the picks ran 2.7 / 4.9 / 9.4 / 12.9 / 13.1 / 10.9 / 11.7 /
13.9 / **20.5%** outward from 8x: the inner end bought nothing at all — 8x took
13 picks and **no** head-q4, 12x took 24 and two — while 128x was the single most
picked rung and carried 50 of the 128 head-q4 (39%). Nine rungs stay nine: 8x and
12x came off, 192x and 256x went on, and the ladder is now `{16, 24}` doubled
four times at the same alternating step.

**16x is the inner stop, and unlike 8x it is one the ladder has measured.** 8x
was neither the walk's 2x frame, which is 50-75% interior and refused outright by
`interior_cap`, nor its 4x "is this atom any good" frame — it was offerable and
it was drawn, and the head simply never wanted it. What stops the ladder at 16x
is that reading and not a guard: the two rungs below it were paid for over 488
picks and returned two head-q4 between them.

**256x is the outer stop, and `reframe_g8` is the first leg to find the head
turning over before it.** Head-q4 as a share of what was drawn had risen at every
rung the ladder ever offered — 2.5 / 3.3 / 5.8 / 6.0 / 6.4 / 8.8 / **10.2%**
outward to 128x on the nine-rung leg before it. Over 251 locations it now reads
1.6 / 3.6 / 4.4 / 8.0 / 6.4 / 8.4 / 8.8 / **9.6** / 8.8%: it peaks at **192x** and
falls at 256x, which is the first turnover in this chain's history and the honest
place to stop.

A guard is also in sight for the first time. A framing is refused as
`width_over_root_scale` only past [`operators.MAX_WIDTH`], and over 6,590 nucleus
rows the largest atom seen has a window scale of 8.5e-3, so the first rung that
guard would refuse is **352x**. At 128x that was a factor of 2.8 of headroom; at
256x it is **1.38**, so the ladder cannot be doubled again whatever the pictures
say, and it has never fired.

**And the pictures are not what the 14-23 px reading feared.** Every one of the 27
head-q4 picks at the two new rungs has the atom's interior at the centre of its
frame — none is a filament frame — and the bodies measure **8-16 px at 192x and
6-11 px at 256x** of a 1280 px frame, which is the scaling of the eleven-atom
measurement holding to within a pixel. A minibrot at seven pixels is a speck in a
field, and it is still a minibrot; what the ladder is now buying at its outer end
is a subject the *location* head likes and nothing has yet asked a person about.

The f64 spacing wall bit at the other end, and the drop takes the ladder out of
its reach: 8x was offerable on 99.7% of those 6,590 rows and 12x on 99.8%,
against 99.8% for 16x itself. A rung the wall refuses is simply not drawn for
that nucleus, and the new rungs are the *most* offerable the ladder has — 192x
and 256x were drawn on all 251 of that leg's nuclei where 16x and 24x reached
248. What rises outward instead is the gate's own refusal rate, 242 of 248
surviving at 16x against 228 of 251 at 256x.

## What is priced, and against what

Every row carries the seconds its operator spent and the Newton solves it charged,
per operator and per rung, so "candidates per operator-minute" is a division on
the record rather than a stopwatch reading. That is the number an evening leg is
sized against: the target is a thousand nuclei the location head scores q4, and
the channel's own yield per minute is what says whether a night reaches it.

## Generations, and the queue's priority order

A nucleus the head scores at or above the q4 admission bar — the keeper floor on
`P(>=3)` **and** the great cut on `P(>=4)`, both through [`supply.currency`]
rather than restated — is a seed for the next generation. So is one that merely
clears the keeper floor, at a lower priority: generation 1 found 58 of the first
and 496 of the second, and a leg that promoted only the first would run its queue
dry inside an hour.

The queue is ordered and the order is a claim about what a seed is worth
([`SOURCES`]):

```text
matt_q4       a person called it a 4       generation 0
matt_q3       a person called it a 3       generation 0
head_q4       the head calls it a 4        a promotion
head_keeper   the head clears the floor    a promotion
```

A human verdict outranks the head's because it is the thing being inherited, and
inside the human half q4 outranks q3 on measurement: over generation 1's 1,056
consumed seeds the q4 roots returned a head-q4 at **11.4%** and the q3 roots at
**4.2%**, so a q4 seed is worth 2.7 of the others. Both are ahead of any
promotion, because a promotion's claim is the head's read of a picture the head
also framed.

Every row says which of the four it came from and which generation produced it,
so yield per seed is a division on the record. The loop is bounded by
`--generations`; generation 1 alone is the channel firing at proven roots exactly.

## A root the channel fired and got nothing from is recorded too

A candidate row is written where something is found, so for the channel's first
eight legs a root that was **fired and returned nothing** left no trace at all —
and the next plain continuation offered it again, at the front of the queue,
because it was indistinguishable from a root no leg had reached. `reframe_g8`
spent a large share of its seeds on `reframe_g7`'s barren roots that way, at a
fraction of the per-root yield the fresh ones returned.

[`FIRE_KIND`] is one row per seed fired, whatever the firing returned, in the
same ledger. Four rulings shape it, Matt's of 2026-09-05:

**Consumed is fired, converged, and zero locations.** A root Newton did not
settle on ([`newton_settled`]) moves when the period ceiling does, and a root
whose atoms a crashed screen batch cost a verdict was never read — neither is a
verdict about the place, so neither takes a root off the queue. [`OUTCOMES`] is
the five answers and [`BARREN`] is the only consuming one.

**Consumed is relative to the ladder.** A barren verdict at nine rungs is not a
verdict at eleven, so each fire is scoped to the operator set, the rung span and
the period ceiling it ran under — [`ladder_of`], read off the leg's own header
row, which has carried all three since the channel shipped. [`covers`] is what
says a ladder already answers another, and the move it is the shape of is
2026-09-04's: `{8..128}` to `{16..256}` reaches further out, so every root `g7`
fired barren is offered to a leg on the new ladder exactly once.

**One more fire under `--reprobe`, and not two.** The count is per
`(root, ladder)` ([`REPROBE_FIRES`]); a re-probe is a second random sample of one
neighbourhood and a third is the leg saying the same thing three times. A root
that ever produced a location is bounded by nothing, which is what re-probing is
for.

**A re-offered root is fired last.** It keeps its own class on its row — the
source is what a person cast — and [`queued`] sorts it behind every unfired seed
whatever that class is, so a short leg's clock goes to what nothing has paid for
yet.
"""

from __future__ import annotations

import json
import math
import random
import time
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path

from fractal_wallpapers import engine
from fractal_wallpapers.discovery import ledger as ledger_module
from fractal_wallpapers.discovery import operators
from fractal_wallpapers.discovery.ledger import Ledger
from fractal_wallpapers.supply import currency as money
from fractal_wallpapers.supply.location import key_of_row, location_key
from fractal_wallpapers.supply.location import text_of_row as location_text

#: The schema every record this module writes outside the ledger carries.
SCHEMA = 1

#: What this channel is called wherever a row's provenance is read back.
CHANNEL = "reframing"

#: The row a leg opens its ledger with, and what identifies the ledger as this
#: channel's rather than a walk's.
#:
#: A name cannot do that job: `harvest_reframe_night` is a **walk** whose run
#: directory says otherwise, and a leg called anything at all is still one of
#: these. [`discovered_priors`] reads the first row and nothing else, which is one
#: open per run directory.
RUN_KIND = "reframing_run"

#: The row a leg closes its ledger with. What [`rediscovery`] is read off.
SUMMARY_KIND = "reframing_summary"

#: One row per seed the leg fires, whatever the firing returned. What makes a
#: barren root visible to the next leg.
#:
#: A candidate row is written only where something was found, so a root that was
#: fired and produced nothing left no trace at all and a plain continuation
#: offered it again at the head of the queue. Measured over `reframe_g7`: of the
#: 912 roots it fired, 277 returned nothing, and `reframe_g8` spent a large share
#: of its seeds on them a second time. This row is what closes that.
#:
#: It is a row in the **same** ledger and not a store beside it, so
#: [`prior_run`]'s one parse of a leg answers both questions — which atoms the
#: chain holds and which roots it has spent — and a leg killed mid-flight leaves
#: its fires recorded exactly as far as it got.
FIRE_KIND = "reframing_fire"

#: What a fire returned, on its own row under `outcome`.
#:
#: Only [`BARREN`] is **consumed**, and that is Matt's ruling of 2026-09-05: a
#: root Newton did not settle on, or whose nuclei the leg never got a verdict
#: for, stays on the plain queue because the leg learned nothing about it.
PRODUCTIVE = "productive"
#: Fired, converged, and not one location came of it. THE consumed outcome.
BARREN = "barren"
#: Newton did not settle at the seed at all, so there is no verdict to carry.
NO_CONVERGE = "no_converge"
#: Atoms were found and their screen batch crashed twice, so they were never
#: read. A leg failure rather than an answer about the root.
NOT_DRAWN = "not_drawn"
#: The seed's family has no parameter-plane degree, so the operators are
#: undefined there rather than unlucky. Never reachable from [`seeds`], which
#: serves the parameter planes alone.
UNDEFINED = "undefined"

#: The outcomes a fire row can carry, in the order a readout prints them.
OUTCOMES: tuple[str, ...] = (PRODUCTIVE, BARREN, NO_CONVERGE, NOT_DRAWN, UNDEFINED)

#: Operator refusals that mean **Newton did not settle**, as against a refusal
#: that is a definite fact about the geometry.
#:
#: The distinction is the whole of what separates [`BARREN`] from
#: [`NO_CONVERGE`]. `nucleus_outside_seed_view`, `width_over_root_scale`,
#: `hit_parent`, `duplicate_neighbour` and the rest are answers — fire the same
#: seed under the same ladder again and get them again — so a seed that returned
#: only those is barren. These two are not: the first is Newton running out of
#: iterations and the second is the period scan finding no candidate at all, and
#: both move when [`SEED_SNAP_MAX_PERIOD`] does.
UNRESOLVED: tuple[str, ...] = ("no_converge", "orbit_escaped_immediately")

#: How many barren fires one `(root, ladder)` may take under `--reprobe` before
#: the pair is spent for re-probing too. Matt's ruling: a re-probe is a second
#: random sample of one neighbourhood and is worth taking once; a third is the
#: leg saying the same thing three times.
REPROBE_FIRES = 2

#: The rungs, in atom sizes. See the module docstring for the measurement.
#:
#: Offered directly and not walked to: `refine_framings` moves x1.414 a step, so
#: half an octave cannot turn 8x into 128x however many times it fires.
#:
#: The step alternates x1.5 and x1.333 and the ends continue it rather than
#: inventing a spacing — the whole ladder is `{16, 24}` doubled four times. It
#: was `{8, 12}` doubled four times until 2026-09-04, when the two inner rungs
#: came off and `192` and `256` went on: over 488 picks 8x and 12x took 37
#: between them and returned two head-q4, while the outer end took the most of
#: both. A near-flat pick over `k` rungs leaves `2/k` on the ends whatever the
#: rungs are, so nine rungs buys about 22% and the widths themselves —
#: [`ENDS_READOUT`] is what says whether it bought them.
RUNGS: tuple[float, ...] = (16.0, 24.0, 32.0, 48.0, 64.0, 96.0, 128.0, 192.0, 256.0)

#: How many rungs [`RUNGS`] gained at its inner end and at its outer end, so the
#: `ends` readout can name the new ends and the old ones apart without a second
#: copy of the ladder's history living in a caller.
#:
#: A pair rather than a number because the ladder stopped growing symmetrically:
#: the 2026-09-01 extension added two at each end and this was `2`, and the
#: 2026-09-04 move added two at the outer end and **removed** two at the inner,
#: which is `(0, 2)`. Counts rather than the old ladder spelled out again: what
#: the readout asks is "did the pile move off the ends it was on", and that is a
#: question about position in the ladder rather than about the values 16 and 128.
ENDS_READOUT: tuple[int, int] = (0, 2)

#: What a nucleus location's row says about its centre, and the contract
#: [`curation.framing`] honours: the centre is the atom the operators solved for,
#: so a framing refinement over one of these rows may move the **scale** only.
#:
#: The flag is on the row rather than derived from the channel name, because the
#: property is about the geometry and not about who made it — a hand-placed
#: nucleus frame would carry it too, and a reader that special-cased `channel ==
#: "reframing"` would have to be found and changed the day one arrives.
CENTERED = True

#: Whether a continuing leg fires at the proven roots an earlier one already
#: consumed. `None` is the default and means **decide from the ledgers**
#: ([`convergence`]); `False` is the plain continuation — what is left of the
#: label store, then the promotions — and `True` fires at everything the chain
#: has already spent.
#:
#: The lever exists because [`operators.expand_neighborhood`] **probes at
#: random** — a ring of radii at a random angle, `NEIGHBOUR_PROBES` of them — so
#: a second pass at the same root is a different sample of the same
#: neighbourhood and finds atoms the first one did not. The prior run's nuclei
#: are still deduped, so what a re-probe can add is exactly what it found that
#: the earlier pass missed and nothing else. It is how the channel keeps
#: yielding after its promotion queue converges, which it does: a generation
#: returns well under one promotion per seed.
#:
#: It defaults to a decision rather than to a value because the convergence it
#: answers happens in about two hours and the flag was a thing a person had to
#: remember afterwards. A leg launched into a converged chain without it spent
#: 576 seeds for seven locations.
REPROBE = None

#: The share of the nuclei a leg's operators reach that it has **already found**,
#: at or above which the chain counts as saturated and the next leg re-probes.
#:
#: Read off the priors' own summaries — every leg records `nucleus_already_found`
#: beside what it wrote — and the threshold sits in the gap between the last leg
#: that was still productive and the first that was not. The five legs of
#: 2026-08-31 and 2026-09-01 read **13.5, 56.7, 68.8, 77.5 and 93.0%**: the 77.5%
#: leg wrote 1,607 locations in 168 minutes and is not a leg to skip re-probing
#: for, and the 93.0% one wrote **seven** locations for 576 seeds. So the line is
#: drawn between them and not at either.
#:
#: A share is a share of what the *operators* reached, which is what was written
#: plus what was refused for being already held, for having no offerable frame,
#: and for a crashed batch — not a share of the queue, which was nowhere near
#: empty in the leg that prompted this ([`convergence`]).
SATURATED = 0.90

#: Seeds a prior leg must have consumed before its re-discovery share is read at
#: all. A leg that fired at nine seeds and found nothing new says nothing about a
#: chain; the leg this threshold was measured on consumed 576.
SATURATION_FLOOR = 100

#: The period ceiling the seed snap scans to, over [`operators.MAX_PERIOD`]'s 64.
#:
#: Measured on 60 generation-1 seeds: 64 found 24 nuclei in 5.1 s, 128 found 30 in
#: 8.6 s, and 256 found **35 in 17.7 s** — a 58% hit rate against 40%, at 3.5x the
#: Newton cost. It is the right trade here and would not be in the walk, because
#: the snap is a tenth of this channel's operator clock and seeds are the scarce
#: thing: `nucleus_outside_seed_view` was the single largest refusal in the smoke
#: at 1,416, and a seed the snap misses is a seed nothing else will reach.
SEED_SNAP_MAX_PERIOD = 256

#: The lowest label tier a seed may carry. Both of the currency's paid classes:
#: q3 and q4 alike are places a person called a keeper, and the channel is a claim
#: about the *neighbourhood* of one rather than about the frame itself.
SEED_TIER_FLOOR = 3

#: Frames per [`engine.screen`] call. One engine process per batch, so this trades
#: the process launch against how long the leg goes without saying anything.
#: [`curation.framing.BATCH`]'s number, for the same reason it is that one there.
SCREEN_BATCH = 64

#: How many times a failed [`engine.screen`] batch is tried again before the
#: frames in it are given up on.
#:
#: A batch is one engine process and the process can die — on 2026-08-31 one did,
#: two minutes into an eight-hour leg, returning nonzero with **empty** stdout and
#: stderr, which is a hard crash rather than a refusal the engine could describe.
#: The leg died with it and the night's supervisor read the short ledger as an
#: exhausted queue and moved on to something else. So a crashed batch is retried,
#: and a batch that crashes twice costs its own frames and nothing more: the
#: nuclei in it get no row, the count is on the summary as `screen_failed`, and
#: the leg keeps going. **An unattended leg that stops on one frame has spent the
#: night**, and that is a worse failure than sixty-four missing rows.
SCREEN_RETRIES = 1

#: Seeds fired before the batch's nuclei are drawn and scored. Small enough that a
#: killed leg loses a minute rather than an hour, large enough that the head and
#: the engine are each entered a few times a minute rather than per nucleus.
SEED_BATCH = 24

#: What a promotion the head calls a class 4 is spelled as on the queue.
HEAD_Q4 = "head_q4"

#: What a promotion that merely clears the keeper floor is spelled as.
HEAD_KEEPER = "head_keeper"

#: The queue's priority order, best first. A proven root's source is its own tier
#: — `matt_q4`, `matt_q3` — so a widened `--tier-floor` spells what it admitted
#: rather than flattening it into the nearest name here.
SOURCES: tuple[str, ...] = ("matt_q4", "matt_q3", HEAD_Q4, HEAD_KEEPER)


def source_of_tier(tier: int) -> str:
    """A proven root's queue class: the tier a person cast, spelled as a source."""
    return f"matt_q{int(tier)}"


def priority_of(source: str) -> int:
    """Where a source sits in the queue. Anything unlisted sorts last, not first."""
    return SOURCES.index(source) if source in SOURCES else len(SOURCES)


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
    #: Which class of the seed queue this seed was taken from ([`SOURCES`]).
    source: str = ""
    #: Whether this seed was fired barren before and is being offered once more
    #: because the ladder has grown since ([`offerable`]). It keeps its own
    #: class on the row — the source is what a person cast, not a queue position
    #: — and [`queued`] sorts it behind every unfired seed whatever that class
    #: is, which is the whole of what the flag is for.
    reoffered: bool = False

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
                source=source_of_tier(row["provenance"]["tier"]),
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
        "sources": {
            source: sum(1 for seed in kept if seed.source == source)
            for source in sorted({seed.source for seed in kept}, key=priority_of)
        },
        "rule": "a proven parameter-plane location no eval pin covers, best tier first",
    }


def unpinned(seeds_: list[Seed], pinned: set) -> tuple[list[Seed], int]:
    """`(the seeds no evaluation pin covers, how many were refused)`.

    [`seeds`] applies this rule to the proven roots as it derives them, off the
    label rows. This is the same rule applied to a seed that already exists —
    which is every **carried promotion**, built by [`prior_run`] out of an
    earlier leg's candidate rows and reaching the queue without passing the
    query at all. One pinned promotion among thousands is a leg that dies on
    [`PinnedPlace`] the moment the queue reaches it, and it killed both legs of
    2026-09-06 on the same seed.

    A seed whose frame has no location key is **kept**, because a key that cannot
    be computed is not evidence of a pin — which is exactly what
    [`Channel.refuse_a_pinned_frame`] does with the same case, and the filter and
    the assertion behind it must not disagree about what they are looking at.
    """
    kept: list[Seed] = []
    refused = 0
    for seed in seeds_:
        try:
            key = location_key(seed.family, seed.viewport)
        except (KeyError, TypeError, ValueError):
            key = None
        if key is not None and key in pinned:
            refused += 1
            continue
        kept.append(seed)
    return kept, refused


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


def fire(
    seed: Seed,
    rng: random.Random,
    *,
    rungs=RUNGS,
    probe_max=None,
    found_max=None,
    max_period: int = SEED_SNAP_MAX_PERIOD,
):
    """`(nuclei, cost)` — every atom this seed's operators reached, at every rung.

    One Newton pass at the seed's centre answers [`operators.snap_at_seed`] and
    then seeds the neighbourhood enumeration through the shared
    [`operators.ParentAtom`], so the atom under the seed is solved for once even
    though two operators want it. The snap scans to [`SEED_SNAP_MAX_PERIOD`]
    rather than the operator module's default: the seed set is the scarce thing
    here and the snap is a tenth of the clock, which is a trade the walk does not
    have and this channel does.

    A seed on a family with no parameter-plane degree returns nothing and says so:
    the operators are undefined there rather than unlucky.
    """
    degree = seed.degree()
    ladder = list(rungs)
    cost: dict = {
        "operators": {},
        "degree": degree,
        "max_period": int(max_period),
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
    snapped = operators.snap_at_seed(
        view, degree=degree, framings=ladder, max_period=int(max_period)
    )
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
    failed = 0
    for start in range(0, len(pairs), SCREEN_BATCH):
        chunk = pairs[start : start + SCREEN_BATCH]
        spec = {
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
        report = None
        for attempt in range(SCREEN_RETRIES + 1):
            try:
                report = engine.screen(spec)
                break
            except (RuntimeError, OSError, ValueError) as failure:
                log(
                    f"[reframe] screen batch at {start} failed on attempt {attempt + 1} of "
                    f"{SCREEN_RETRIES + 1}: {failure!r}"
                )
        if report is None:
            # Given up on, and counted. The frames are lost and the leg is not.
            failed += len(chunk)
            log(f"[reframe] screen batch at {start}: {len(chunk)} frame(s) given up on")
            continue
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
    if failed:
        log(f"[reframe] {failed} of {len(pairs)} rung(s) were never drawn")
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
        # The centre is the atom, and it is the whole of what this location is.
        # A framing refinement over this row may move the scale and nothing else;
        # `curation.framing` reads the flag rather than the channel name.
        "centered": CENTERED,
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
                "source": nucleus.seed.source,
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
# Finding the earlier legs, and reading whether the chain is spent.
# --------------------------------------------------------------------------- #
def first_row(path: Path) -> dict | None:
    """A ledger's opening row, or `None` where it has none this reader can use.

    One line, not one file: the population being classified is every walk ledger
    under both tiers, some of them tens of megabytes, and each would be parsed
    whole to learn a thing its first row says.
    """
    try:
        with Path(path).open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    return None
    except OSError:
        return None
    return None


def is_a_leg(path: Path) -> bool:
    """Whether a walk ledger is one of this channel's, off its own first row.

    A **name** cannot answer this and must never be asked to: on this machine
    `artifacts/harvest_reframe_night` is a walk, and a leg of this channel is
    whatever its `--out-dir` was called. [`RUN_KIND`] is the answer and it is on
    the first row of every leg ever written, because the header goes down before
    the first seed is fired.
    """
    head = first_row(path)
    return bool(head) and head.get("kind") == RUN_KIND and head.get("channel") == CHANNEL


def when(head: dict | None, path: Path) -> str:
    """When a leg ran, for ordering a chain: its own stamp, else its ledger's mtime.

    Legs written before the header carried `started` fall back to the file. That
    is sound here and is not sound in general — `storage` copies through
    `shutil.copy2`, so archiving a leg preserves its mtime, but a tree copied by
    hand does not and would reorder a chain silently. Both spellings are the same
    fixed-width UTC format, so they sort against each other.

    Ordering cannot come from the name: `<head>_g10` sorts before `<head>_g2`.
    """
    stamped = (head or {}).get("started")
    if isinstance(stamped, str) and stamped:
        return stamped
    try:
        seconds = Path(path).stat().st_mtime
    except OSError:
        return ""
    return datetime.fromtimestamp(seconds, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def discovered_priors(exclude: Path | None = None, log=print) -> tuple[list[Path], dict]:
    """`(every earlier leg of this channel, oldest first, the record)`.

    What `--prior` defaults to, and it defaults to it because naming them all by
    hand is exactly the thing a person forgets: a leg handed only its immediate
    predecessor re-writes what the legs before it found — 192 of one leg's 302
    rows, measured 2026-09-01.

    **Both tiers when the archive is reachable, hot alone when it is not**, and
    the record says which. They are different populations, and the difference is
    the point of archiving being reversible: a leg is a top-level name of the
    regenerable tree, `storage archive` moves whole top-level names, and a chain
    that forgot its archived links would re-find their atoms exactly as a
    one-directory `--prior` does. Hot alone is therefore the **narrower** default
    and the one that writes duplicates, which is why it is recorded as a note
    rather than passed over — but it is not a refusal, because a machine with the
    disk unplugged can still run a leg and every atom it re-finds costs engine
    time rather than putting a wrong row anywhere. Measured on this machine
    2026-09-03: all five legs are hot and the archive holds none of them, so the
    two populations coincide today and the note is about tomorrow.

    `exclude` is this run's own ledger. A leg whose `--out-dir` names a directory
    an earlier killed leg already wrote into would otherwise inherit its own finds
    and refuse every one of them as already found.
    """
    from fractal_wallpapers import paths
    from fractal_wallpapers.supply import ledgers as union

    tiers = paths.Tiers.current()
    every = union.ledger_paths(exclude=exclude)
    legs: list[tuple[str, str, Path]] = []
    for path in every:
        head = first_row(path)
        if not head or head.get("kind") != RUN_KIND or head.get("channel") != CHANNEL:
            continue
        # Named by its run **directory**: that is what `--prior` takes, so the
        # record is pasteable into the invocation that would name them by hand.
        legs.append((when(head, path), paths.tracked_name(path.parent), path))
    legs.sort()
    record = {
        "tiers": [paths.HOT, paths.ARCHIVE] if tiers.archive_is_reachable else [paths.HOT],
        "archive_reachable": tiers.archive_is_reachable,
        "ledgers_seen": len(every),
        # The tiers each opened ledger actually came off, as the run header
        # carries it. `tiers` above says which were *searched*, which is a
        # different question and the one that answers "was the archive plugged
        # in"; this says where the population came from.
        "ledgers_read": union.tiers_read(every),
        "legs": [name for _stamp, name, _path in legs],
        "excluded": None if exclude is None else paths.tracked_name(exclude),
    }
    if not tiers.archive_is_reachable and tiers.archive is not None:
        record["note"] = (
            f"the archive ({tiers.archive}) is not mounted, so this chain is the HOT legs "
            f"alone. An archived leg a run cannot see is a leg whose atoms it finds again and "
            f"writes a second time."
        )
    log(f"[reframe] priors: {json.dumps(record)}")
    return [path.parent for _stamp, _name, path in legs], record


def rediscovery(summary: dict | None) -> dict | None:
    """What share of the nuclei a leg's operators reached, it had already found.

    The saturation reading, off a leg's own summary row and nothing else. The
    denominator is what the **operators** reached — what was written, plus every
    nucleus refused for being already held, for having no offerable frame, and
    for a batch that crashed twice — and not the seed queue, which was 3,795 deep
    in the leg that made this necessary.

    `None` where the leg wrote no summary (it was killed) or reached nothing.
    """
    if not summary:
        return None
    counts = summary.get("counts") or {}
    again = int(counts.get("nucleus_already_found", 0) or 0)
    new = int(summary.get("locations") or 0)
    lost = int(counts.get("nucleus_no_frame", 0) or 0)
    lost += int(counts.get("nucleus_not_drawn", 0) or 0)
    found = new + again + lost
    if found <= 0:
        return None
    return {
        "found": found,
        "new": new,
        "again": again,
        "lost": lost,
        "share": round(again / found, 4),
        "seeds_consumed": int(summary.get("seeds_consumed") or 0),
    }


def convergence(earlier: dict | None, roots: list, carried: list) -> tuple[bool, dict]:
    """`(whether the chain is spent, why)` — the branch `--reprobe` used to be.

    `roots` and `carried` are what a **plain continuation** would fire at: the
    proven roots the chain has got nothing from, and the promotions it has not
    spent. Two clauses, both read, both on the record:

    * **exhausted** — that queue is empty. Today this is the leg that raises
      `no seed survives` and stops; a chain in this state has nothing to offer
      except a second sample of a neighbourhood it has already probed, so
      re-probing is the only thing left that is not a refusal.
    * **saturated** — the queue is not empty and is not the constraint. The
      chain's latest leg found [`SATURATED`] or more of its nuclei already held,
      having consumed at least [`SATURATION_FLOOR`] seeds. Measured 2026-09-01:
      the fifth leg on these roots spent 576 seeds, reached 100 nuclei, and 93 of
      them were in the priors' `seen` set — seven new locations and one head-q4,
      with 3,795 seeds still offered and the clock not binding.

    The second clause exists because the first hardly ever fires. A root that was
    consumed and returned **nothing** used to appear in no row, so it landed in
    neither `fired` nor `spent` and a plain continuation offered it again:
    measured 2026-09-03 over the five legs on this machine, 635 of 2,153 proven
    roots are in `fired`, and 977 of that gap is the label store having grown
    since. Queue exhaustion is an honest floor and a useless trigger; what says a
    chain is spent is what its last leg got for what it fired.

    **[`FIRE_KIND`] closes the invisibility and not this clause.** A barren root
    is now recorded and a plain continuation drops it ([`offerable`]), so the
    queue shortens honestly as the chain fires — but the first clause stays the
    rare one, because the same fire rows also say the queue is thousands deep.
    What is spent is still the neighbourhoods rather than the queue.
    """
    latest = None
    for leg in reversed(((earlier or {}).get("record") or {}).get("priors", [])):
        seen = leg.get("rediscovery")
        if seen and seen["seeds_consumed"] >= SATURATION_FLOOR:
            latest = leg
            break
    why = {
        "converged": False,
        "clause": None,
        "saturated_at": SATURATED,
        "saturation_floor": SATURATION_FLOOR,
        "continuation_queue": {"roots": len(roots), "promotions": len(carried)},
        "latest_leg": latest,
    }
    if not roots and not carried:
        why["converged"] = True
        why["clause"] = "exhausted"
        why["because"] = (
            "a plain continuation has no seed left: every proven root the chain got anything "
            "from is off the queue and every promotion is spent. Re-probing is the only thing "
            "left that is not a refusal."
        )
        return True, why
    if latest is not None and latest["rediscovery"]["share"] >= SATURATED:
        seen = latest["rediscovery"]
        why["converged"] = True
        why["clause"] = "saturated"
        why["because"] = (
            f"the chain's latest leg ({latest['prior']}) spent {seen['seeds_consumed']:,} "
            f"seed(s) to reach {seen['found']:,} nucleus/nuclei, {seen['again']:,} of which it "
            f"already held — {seen['share']:.1%}, at or over the {SATURATED:.0%} a chain is "
            f"called spent at. The queue is not the constraint; the neighbourhoods are."
        )
        return True, why
    if latest is None:
        why["because"] = (
            f"no leg of the chain consumed {SATURATION_FLOOR} seed(s) and wrote a summary, so "
            f"there is no saturation reading, and the continuation queue is not empty."
        )
    else:
        seen = latest["rediscovery"]
        why["because"] = (
            f"the chain's latest leg ({latest['prior']}) already held {seen['share']:.1%} of "
            f"what it reached, under the {SATURATED:.0%} a chain is called spent at, and "
            f"{len(roots):,} root(s) and {len(carried):,} promotion(s) are still unfired."
        )
    return False, why


# --------------------------------------------------------------------------- #
# What a fire is scoped to, and what it returned.
# --------------------------------------------------------------------------- #
def ladder_of(head: dict | None) -> dict:
    """The fire context a leg ran under, off the leg's own header row.

    A barren verdict is only as good as the ladder that produced it — Matt's
    ruling of 2026-09-05 — so a root fired barren under a shorter ladder is
    offered again when the ladder grows, and the record has to say which ladder
    each fire ran under to know that.

    It is read off the header rather than copied onto every fire row, and that is
    the whole reason there is no second store here: [`RUN_KIND`]'s row has
    carried `rungs`, `operators` and `seed_max_period` since the channel shipped,
    so the ladder is already written down once per leg and a fire row that
    repeated it would be a second answer to the same question.

    `max_period` is `0` where the header predates the field (`reframe_g1` is the
    only such leg on this machine). Zero rather than the current default,
    because an unrecorded ceiling [`covers`] nothing and the honest reading of a
    missing field is *unknown*, never *whatever it is today*.
    """
    head = head or {}
    return {
        "operators": sorted(str(name) for name in (head.get("operators") or OPERATORS)),
        "rungs": sorted(float(rung) for rung in (head.get("rungs") or ())),
        "max_period": int(head.get("seed_max_period") or 0),
    }


def ladder_key(ladder: dict) -> str:
    """A ladder as one string, so a fire count can be kept per `(root, ladder)`.

    The rungs in full rather than their span and count: two different ladders can
    share both, and a key that collided would silently retire a root under a
    ladder it was never fired on.
    """
    return "{ops}|{rungs}|p{period}".format(
        ops="+".join(ladder["operators"]),
        rungs=",".join(f"{rung:g}" for rung in ladder["rungs"]),
        period=int(ladder["max_period"]),
    )


def settles_the_same(older: dict, newer: dict) -> bool:
    """Whether Newton at a seed under `older` already answers what `newer` asks.

    The half of [`covers`] that is about **reaching an atom at all**, and it is
    the whole of what an unsettled fire is scoped to. [`fire`] snaps at the
    seed's own centre first and hands the atom it found to the neighbourhood
    enumeration as its parent, so a seed [`newton_settled`] says no about is one
    where the deterministic snap failed and the random probing never ran. What
    can move that verdict is the period ceiling the snap scans to, and the
    operator set that does the scanning. What cannot is the rung ladder: a rung
    is a width the atom is framed at, and there is no atom yet to frame.

    So the rungs are deliberately not asked about here. A leg that widened its
    ladder and left `--seed-max-period` alone re-offers every barren root and
    **none** of the unresolved ones, and both of those are right.
    """
    reaches = int(older["max_period"]) >= int(newer["max_period"])
    return reaches and set(older["operators"]) >= set(newer["operators"])


def covers(older: dict, newer: dict) -> bool:
    """Whether a barren fire under `older` already answers what `newer` would ask.

    Reach, not membership: the rungs inside a span are widths of one atom and a
    ladder that added one between two it already had has not looked anywhere
    new, while a ladder that reached further out has. So the span has to contain
    the span, on top of everything [`settles_the_same`] asks — the operator set
    has to contain the operator set and the period ceiling has to be at least as
    high.

    The move this is the shape of is 2026-09-04's: `{8..128}` to `{16..256}`
    reaches further out, so it does **not** cover, and every root `reframe_g7`
    fired barren is offered to a leg on the new ladder exactly once. The reverse
    — a leg run on the short ladder after the long one — is covered and is not
    offered, which is what stops a narrowed `--rungs` re-opening the whole store.
    """
    if not older["rungs"] or not newer["rungs"]:
        return False
    return (
        settles_the_same(older, newer)
        and min(older["rungs"]) <= min(newer["rungs"])
        and max(older["rungs"]) >= max(newer["rungs"])
    )


def newton_settled(cost: dict) -> bool:
    """Whether Newton settled on this seed at all, off [`fire`]'s own cost block.

    True the moment any operator returned an atom. Where none did, it is the
    refusals that answer: a seed whose every refusal is a fact about the geometry
    was **asked and answered**, and one that hit [`UNRESOLVED`] was not.
    """
    reasons: set[str] = set()
    for tally in (cost.get("operators") or {}).values():
        if tally.get("nuclei"):
            return True
        for reason in tally.get("refusals") or {}:
            # `expand_neighborhood` reports its parent-atom failure under the
            # snap's own word, prefixed. The prefix is about which operator gave
            # up and the reason behind it is the same reason.
            reasons.add(str(reason).split("no_parent_atom:", 1)[-1])
    return not (reasons & set(UNRESOLVED))


def outcome_of(fired: dict) -> str:
    """Which of [`OUTCOMES`] one seed's firing earned. [`BARREN`] is consumed.

    Ordered by what the next leg can do about it. A location written settles it
    whatever else happened; an undefined family and an unsettled Newton are both
    "no verdict here"; a batch that crashed twice is the leg's failure and not
    the root's; and what is left — converged, drawn, read, and nothing came of it
    — is the one outcome that takes a root off the queue.
    """
    if fired["locations"]:
        return PRODUCTIVE
    if fired["undefined"]:
        return UNDEFINED
    if not fired["converged"]:
        return NO_CONVERGE
    if fired["not_drawn"]:
        return NOT_DRAWN
    return BARREN


def unsettled_under(entry: dict | None, ladder: dict) -> bool:
    """Whether Newton has already failed at this seed under a ladder that answers `ladder`.

    Matt's ruling of 2026-09-05 stands: a [`NO_CONVERGE`] fire does **not**
    consume a root, because a seed the period scan found nothing at could still
    converge under a higher ceiling. What it also does not do is earn a second
    firing under the *same* ceiling — that is the identical scan over the
    identical orbit, and the answer is the identical one. Measured 2026-09-06:
    `reframe_g9` left 343 unresolved roots, `reframe_g10`'s whole root queue was
    those 343, all 343 came back unresolved, and they cost 3.9 of its 4.4
    minutes for nothing.

    [`settles_the_same`] is what "the ceiling has not moved" means, so raising
    `--seed-max-period` offers every one of them again and nothing else does.
    True under `--reprobe` as well: re-probing is a second random sample of a
    neighbourhood, and this is a seed no neighbourhood was ever reached from.
    """
    if not entry:
        return False
    return any(
        cell["unsettled"] and settles_the_same(cell["ladder"], ladder) for cell in entry.values()
    )


def refusal(entry: dict | None, ladder: dict, *, reprobe: bool) -> str | None:
    """Why a seed with this fire history is not offered under `ladder`, or `None`.

    `entry` is `{ladder key: {"fires", "unsettled", "locations", "ladder"}}` —
    what [`prior_run`] carries per seed id — and `None` is a seed the chain has
    never fired, which is always offered.

    The reason and not merely the verdict, because the seed query's
    `ladder_rule` readout is the only place anybody sees why a queue is the size
    it is, and a readout that could say only "refused" was what let the
    re-offering of unresolved roots run for two legs unnoticed. [`offerable`] is
    this function asked as a yes or no.

    Four rulings, in the order they bite:

    * **A seed that ever produced a location is off the plain queue** and on the
      re-probe one. That is the rule the channel already had, unchanged: what a
      `--reprobe` leg is for is a second random sample of a neighbourhood that
      paid.
    * **A seed Newton never settled at is off both queues until the period
      ceiling moves**, which is [`unsettled_under`].
    * **A barren fire is worth one fire under the plain continuation and two
      under `--reprobe`.** The count is per `(seed, ladder)`, so two barren fires
      under one ladder spend the pair for re-probing too.
    * **A ladder that reaches further than every ladder the seed was barren
      under resets the count**, which is [`covers`] — so the fires that bind are
      the ones under a ladder that already answers this one.
    """
    if entry is None:
        return None
    if any(cell["locations"] for cell in entry.values()):
        return None if reprobe else "produced"
    if unsettled_under(entry, ladder):
        return NO_CONVERGE
    binding = [cell["fires"] for cell in entry.values() if covers(cell["ladder"], ladder)]
    if max(binding or [0]) >= (REPROBE_FIRES if reprobe else 1):
        return BARREN
    return None


def offerable(entry: dict | None, ladder: dict, *, reprobe: bool) -> bool:
    """Whether a seed with this fire history is offered under `ladder`.

    [`refusal`] asked as a yes or no, so the queue and the readout that explains
    it can never drift apart into two answers.
    """
    return refusal(entry, ladder, reprobe=reprobe) is None


def returned_nothing(entry: dict | None) -> bool:
    """Whether this seed's whole history is fires that returned nothing.

    What [`Seed.reoffered`] is, and it is **barren and unresolved alike**: both
    are a firing the chain paid for and got no location from, and the flag is
    about where such a seed goes on the queue rather than about which of the two
    verdicts it earned. An unresolved root that carried no fire count at all
    sorted to the *front* of `reframe_g10`'s queue for exactly this reason.

    Read over every ladder rather than the one being offered: a seed offered
    again because a ladder grew is still a seed the chain has paid for and got
    nothing from, and that is what decides where on the queue it goes.
    """
    if not entry:
        return False
    return not any(cell["locations"] for cell in entry.values()) and any(
        cell["fires"] or cell["unsettled"] for cell in entry.values()
    )


# --------------------------------------------------------------------------- #
# The queue.
# --------------------------------------------------------------------------- #
def prior_run(directories, log=print) -> dict:
    """What earlier runs of this channel leave the next one: found, fired, promoted.

    **Every** earlier run, and that is the whole of why this takes a list. A leg
    handed only its immediate predecessor inherits only that ledger's atom keys,
    so a chain of legs re-finds and re-writes what the legs before the last one
    already found: measured on the night of 2026-08-31, a fourth leg handed only
    the third's ledger wrote **192 of its 302 rows** on atoms the first leg
    already held. One atom in two ledgers is two location keys wherever the two
    legs picked different rungs, which is one atom in two seats — the exact harm
    the per-run dedup exists to stop and cannot see across runs.

    What comes back:

    * `found` — every atom key the chain has made a location of. They seed the new
      run's `seen`, so an atom reached again is counted rather than re-written.
    * `fired` — the proven root ids the chain consumed *and got something from*.
      What is left of the label store is the front of the new queue, at its own
      tier.
    * `spent` — every seed id the chain has fired at, promotions included. A plain
      continuation drops a promotion it already fired; a `--reprobe` leg keeps it,
      because the point of re-probing is a second random sample of one
      neighbourhood.
    * `history` — `{seed id: {ladder key: {"fires", "unsettled", "locations",
      "ladder"}}}`, which is the two above with the **barren** half filled in and
      is what [`offerable`] decides the queue on. `locations` counts candidate
      rows and so is filled for every leg ever written; `fires` and `unsettled`
      count [`FIRE_KIND`] rows and are filled only for legs written since
      2026-09-05. The two are apart because only `fires` consumes: an unresolved
      root is held while the period ceiling stands ([`unsettled_under`]) and
      offered the moment it moves.
    * `promoted` — the chain's admitted rows as seeds, deduplicated on the atom
      and kept at the better class where two legs disagree about one.

    **A root that was fired and returned nothing used to be invisible here**, so
    it landed in neither `fired` nor `spent` and a plain continuation offered it
    again at the front of the queue. `reframe_g8` spent a large share of its
    seeds on `reframe_g7`'s barren roots for that reason. The fire rows are what
    close it, and they are scoped to the ladder they ran under ([`ladder_of`])
    because a barren verdict at nine rungs is not a verdict at eleven.

    Each leg's entry under `priors` also carries its `started` stamp and its
    [`rediscovery`] reading, which is what [`convergence`] decides the re-probe
    branch on. Both come off rows this already had in hand: the ledger is parsed
    **once** and split by kind, where it used to be read through [`read`] and the
    header and summary thrown away.

    Rows only; nothing here re-reads the head or re-decides a floor. `head_q4` is
    the flag the earlier run wrote, and the keeper class is its own recorded fate.
    """
    from fractal_wallpapers import paths

    if isinstance(directories, (str, Path)):
        directories = [directories]
    found: set[str] = set()
    fired: set[str] = set()
    spent: set[str] = set()
    best: dict[str, Seed] = {}
    per_run: list[dict] = []
    #: `{seed id: {ladder key: cell}}`. One dict for the whole chain, so a root
    #: barren under `g7`'s ladder and fired again under `g8`'s carries both.
    history: dict[str, dict[str, dict]] = {}

    def cell(seed_id: str, ladder: dict) -> dict:
        return history.setdefault(str(seed_id), {}).setdefault(
            ladder_key(ladder), {"fires": 0, "unsettled": 0, "locations": 0, "ladder": ladder}
        )

    for directory in directories:
        directory = Path(directory)
        path = directory / ledger_module.LEDGER_NAME
        if not path.is_file():
            raise ChannelRefused(
                f"{directory} holds no {ledger_module.LEDGER_NAME}, so it is not a run of this "
                f"channel a later one could continue. Point --prior at an earlier --out-dir."
            )
        every = ledger_module.read(path)
        rows = [
            row for row in every if row.get("kind") == "candidate" and row.get("channel") == CHANNEL
        ]
        head = next((row for row in every if row.get("kind") == RUN_KIND), None)
        summary = next((row for row in reversed(every) if row.get("kind") == SUMMARY_KIND), None)
        ladder = ladder_of(head)
        fires = 0
        for row in every:
            if row.get("kind") != FIRE_KIND or row.get("channel") != CHANNEL:
                continue
            seed = row.get("seed") or {}
            if not seed.get("id"):
                continue
            fires += 1
            spent.add(str(seed["id"]))
            if seed.get("kind") == "proven" and row.get("outcome") == PRODUCTIVE:
                fired.add(str(seed["id"]))
            # Only a fire the leg got an answer out of counts against the root.
            # An undrawn batch and an undefined family are both "the leg learned
            # nothing here", and Matt's ruling is that such a root stays on the
            # plain queue.
            if row.get("outcome") in (PRODUCTIVE, BARREN):
                cell(seed["id"], ladder)["fires"] += 1
            # An unsettled Newton is the third of those and is still not a
            # verdict — but it is a fire, and a fire that left no trace at all is
            # what let 343 roots come back at the *head* of the next leg's queue
            # booked as fresh. Counted apart from `fires` because it must not
            # consume: what re-opens it is the period ceiling and nothing else.
            elif row.get("outcome") == NO_CONVERGE:
                cell(seed["id"], ladder)["unsettled"] += 1
        for row in rows:
            block = row.get("reframing") or {}
            if row.get("atom_key"):
                found.add(str(row["atom_key"]))
            seed = block.get("seed") or {}
            if seed.get("id"):
                spent.add(str(seed["id"]))
                cell(seed["id"], ladder)["locations"] += 1
                if seed.get("kind") == "proven":
                    fired.add(str(seed["id"]))
            source = None
            if block.get("head_q4"):
                source = HEAD_Q4
            elif row.get("fate") == ledger_module.SURVIVED:
                source = HEAD_KEEPER
            if source is None:
                continue
            name = str(row.get("atom_key") or row["root_id"])
            held = best.get(name)
            if held is not None and priority_of(held.source) <= priority_of(source):
                continue
            best[name] = Seed(
                id=name,
                family=row["family"],
                viewport=row["viewport"],
                tier=int(seed.get("tier", SEED_TIER_FLOOR)),
                generation=int(block.get("generation", 1)),
                kind=CHANNEL,
                source=source,
            )
        per_run.append(
            {
                "prior": paths.tracked_name(path),
                "rows": len(rows),
                "started": when(head, path),
                "rediscovery": rediscovery(summary),
                "ladder": ladder_key(ladder),
                "fires": fires,
            }
        )
    promoted = list(best.values())
    # Oldest first whatever order the caller named them in, so "the chain's
    # latest leg" is a fact about when the legs ran rather than about how a
    # command line was typed. [`convergence`] reads the last entry.
    per_run.sort(key=lambda leg: (leg["started"], leg["prior"]))
    nothing = [name for name, entry in history.items() if returned_nothing(entry)]
    unsettled = [
        name for name, entry in history.items() if any(cell["unsettled"] for cell in entry.values())
    ]
    record = {
        "priors": per_run,
        "nuclei_found": len(found),
        "roots_fired": len(fired),
        "seeds_spent": len(spent),
        "fires_recorded": sum(leg["fires"] for leg in per_run),
        "seeds_returned_nothing": len(nothing),
        "seeds_unsettled": len(unsettled),
        "ladders": sorted({leg["ladder"] for leg in per_run}),
        "promoted": len(promoted),
        "promoted_by_source": by_source(promoted),
    }
    log(f"[reframe] prior: {json.dumps(record)}")
    return {
        "found": found,
        "fired": fired,
        "spent": spent,
        "history": history,
        "promoted": promoted,
        "record": record,
    }


def queued(seeds_: list[Seed]) -> list[Seed]:
    """One generation's seeds in the queue's priority order ([`SOURCES`]).

    Stable inside a class, so the order [`supply.proven`] already imposed on the
    proven roots — best tier first, then a digest of the location so a short leg
    reaches a spread of places rather than a basin — survives untouched.

    A **re-offered** seed sorts behind every unfired one whatever its class,
    which is the one thing here that is not [`SOURCES`]. A root fired barren
    under a shorter ladder is a root the chain has already paid for once and got
    nothing from; offering it ahead of an unfired `matt_q3` would spend the front
    of a short leg's clock on the least promising thing on the queue. Its own
    class is untouched and still on its row — this decides where it is fired,
    never what it is.
    """
    return sorted(seeds_, key=lambda seed: (seed.reoffered, priority_of(seed.source)))


def _bump(where: dict, key: str, by: int = 1) -> None:
    where[key] = where.get(key, 0) + by


def by_source(seeds_: list[Seed]) -> dict:
    """`{source: count}` over a seed list, in queue order. What a readout divides."""
    counts: dict[str, int] = {}
    for seed in seeds_:
        counts[seed.source] = counts.get(seed.source, 0) + 1
    return {source: counts[source] for source in sorted(counts, key=priority_of)}


def end_picks(picked: dict, ladder, added: tuple[int, int] = ENDS_READOUT) -> dict:
    """Where a leg's picks landed relative to the ladder's ends.

    `picked` is `{rung: count}` and `ladder` is the ladder that was offered.
    `added` is `(inner, outer)`: how many rungs the ladder gained at each end.
    The block splits the picks three ways — those new rungs, the two rungs the
    pile could pile on before they arrived, and everything strictly inside —
    because that is the one comparison that says whether the move bought
    anything.

    **A pick on a new end is not the failure an old-end pick was.** The old ends
    were the ladder's whole reach, so a pick there was the head asking for a width
    it could not be offered; a new end is a width that had never been drawn. What
    the shares answer is whether the pile moved off the old ends or merely moved
    outward with them, which is what happened the first time this ladder grew.

    `old_ends` is *the rungs that are ends no longer*, which is not the same as
    "the rungs that were there before": the 2026-09-04 move dropped 8x and 12x, so
    16x becomes an end by deletion rather than by anything being added under it,
    and it is read here beside 128x for exactly that reason — both are rungs the
    pile is now free to pile on and was not, or was, before.

    `added` rungs off each end of a ladder too short to hold them and an interior
    would overlap, so the split degrades to new-ends-and-interior rather than
    double-counting a rung into two buckets.
    """
    inner, outer = added
    rungs = sorted(float(rung) for rung in ladder)
    total = sum(picked.values())
    new_ends = set(rungs[:inner]) | set(rungs[len(rungs) - outer :] if outer else [])
    rest = [rung for rung in rungs if rung not in new_ends]
    old_ends = {rest[0], rest[-1]} if rest else set()
    buckets = {
        "new_ends": sorted(new_ends),
        "old_ends": sorted(old_ends),
        "interior": [rung for rung in rest if rung not in old_ends],
    }
    block: dict = {"ladder": rungs, "picks": total}
    for name, group in buckets.items():
        count = sum(picked.get(rung, 0) for rung in group)
        block[name] = {
            "rungs": group,
            "picks": count,
            "share": round(count / total, 4) if total else None,
        }
    return block


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
        max_period: int = SEED_SNAP_MAX_PERIOD,
        ledgers_read: dict | None = None,
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
        self.max_period = int(max_period)
        #: Which earlier ledgers this leg's queue was built off, by tier. Carried
        #: to the header rather than derived there, because the reading is
        #: [`discovered_priors`]' and was taken before the channel existed.
        self.ledgers_read = ledgers_read
        self.log = log
        self.rng = random.Random(self.seed)
        self.pinned = pin_module.every_pinned() if pinned is None else set(pinned)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.ledger = Ledger(self.out_dir / ledger_module.LEDGER_NAME)
        self.frames_dir = self.out_dir / "rungs"
        #: Atom keys this run has already made a location of. One nucleus is one
        #: location, whichever operator or seed reached it first.
        self.seen: set[str] = set()
        #: Per **generation** — a row's, not a round's. The drift read: whether
        #: the head-q4 rate holds up as the queue moves away from the person who
        #: cast the verdict being inherited.
        self.per_generation: dict[int, dict] = {}
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

    def ladder(self) -> dict:
        """This leg's fire context, off the same three fields its header carries.

        Through [`ladder_of`] rather than assembled here, so the ladder a leg
        writes and the ladder the next leg reads are one function.
        """
        return ladder_of(
            {
                "operators": list(OPERATORS),
                "rungs": list(self.rungs),
                "seed_max_period": self.max_period,
            }
        )

    def _generation_tally(self, generation: int) -> dict:
        return self.per_generation.setdefault(
            int(generation),
            {
                "seeds_consumed": 0,
                "locations": 0,
                "head_q4": 0,
                "head_keeper": 0,
                "consumed_by_source": {},
                "rung_picked": {},
            },
        )

    def by_generation(self) -> dict:
        """`{generation: what it consumed and what it returned}`, best generation first.

        Off the run's own counters rather than off the ledger, because the ledger
        is the thing a readout re-derives this from and a summary that agreed with
        it by construction would prove nothing.
        """
        out = {}
        for generation in sorted(self.per_generation):
            tally = dict(self.per_generation[generation])
            seeds_ = tally["seeds_consumed"]
            tally["locations_per_seed"] = round(tally["locations"] / seeds_, 4) if seeds_ else None
            tally["head_q4_per_seed"] = round(tally["head_q4"] / seeds_, 4) if seeds_ else None
            tally["head_q4_rate"] = (
                round(tally["head_q4"] / tally["locations"], 4) if tally["locations"] else None
            )
            out[str(generation)] = tally
        return out

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
    def run(self, roots: list[Seed], carried: list[Seed] | None = None) -> dict:
        """Fire every round the budget allows and return what was found.

        `carried` is an earlier run's promotions ([`prior_run`]), and they enter
        the **first** round's queue rather than a round of their own: the queue's
        order already puts every proven root ahead of every promotion, and a
        second knob for the same fact would be a second answer to it. A round is
        therefore not a generation — a row's generation is its seed's plus one and
        is on the row — and the loop's record says `round` for that reason.
        """
        header = {
            "channel": CHANNEL,
            # What orders a chain. [`discovered_priors`] falls back to the
            # ledger's mtime for the legs written before this was stamped, which
            # survives archiving (`storage` copies through `shutil.copy2`) but
            # not a re-copy by hand.
            "started": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "run_seed": self.seed,
            "rungs": list(self.rungs),
            "operators": list(OPERATORS),
            "rounds": self.generations,
            "minutes": self.minutes,
            "seed_max_period": self.max_period,
            "queue": list(SOURCES),
            "seeds": len(roots),
            "pinned_places": len(self.pinned),
            "scorer": self.scorer.name,
            "q4_bar": {
                "good_floor": money.GOOD_FLOOR,
                "great_cut": money.GREAT_CUT,
            },
        }
        # Through [`ledger.Ledger.header`] and not [`write`], which is what puts
        # the invocation and the ledger tiers on it: both are facts about any run
        # record, and a leg kind that assembled its own header would have to
        # remember them.
        header = self.ledger.header(RUN_KIND, ledgers_read=self.ledgers_read, **header)
        self.log(f"[reframe] {json.dumps(header)}")

        pending = queued([*roots, *(carried or [])])
        consumed = 0
        per_round: list[dict] = []
        for index in range(1, self.generations + 1):
            if not pending or self.out_of_time():
                break
            tally, promoted = self._generation(index, pending)
            consumed += tally["seeds_consumed"]
            per_round.append(
                {
                    "round": index,
                    "seeds_offered": len(pending),
                    "offered_by_source": by_source(pending),
                    **tally,
                    "promoted": len(promoted),
                    "promoted_by_source": by_source(promoted),
                }
            )
            # The queue's own order, re-imposed every round: a head-q4 promotion
            # is fired before any head-keeper one, whichever batch each came out
            # of.
            pending = queued(promoted)
        report = self.summary([*roots, *(carried or [])], consumed, per_round)
        self.ledger.write(SUMMARY_KIND, **report)
        self.ledger.close()
        return report

    def _generation(self, index: int, pending: list[Seed]) -> tuple[dict, list[Seed]]:
        """`(what this round did, the seeds it promoted)`.

        The tally is kept per **seed source** as well as in total, because "yield
        per seed by seed source" is the number the queue's order is an argument
        about, and a run that only counted the total could not settle it.
        """
        tally = {
            "seeds_consumed": 0,
            "consumed_by_source": {},
            "locations": 0,
            "locations_by_source": {},
            "head_q4": 0,
            "head_q4_by_source": {},
        }
        promoted: list[Seed] = []
        for start in range(0, len(pending), self.seed_batch):
            if self.out_of_time():
                break
            chunk = pending[start : start + self.seed_batch]
            self.batch_index += 1
            nuclei: list[Nucleus] = []
            fires: dict[str, dict] = {}
            for seed in chunk:
                tally["seeds_consumed"] += 1
                _bump(tally["consumed_by_source"], seed.source)
                self._count(f"seed_consumed:{seed.source}")
                mine = self._generation_tally(seed.generation + 1)
                mine["seeds_consumed"] += 1
                _bump(mine["consumed_by_source"], seed.source)
                self.refuse_a_pinned_frame(seed.family, seed.viewport, f"seed {seed.id}")
                found, cost = fire(seed, self.rng, rungs=self.rungs, max_period=self.max_period)
                self._charge(cost)
                fired = self._fired(seed, cost, fires)
                for nucleus in found:
                    fired["nuclei"] += 1
                    if nucleus.key in self.seen:
                        self._count("nucleus_already_found")
                        fired["already_found"] += 1
                        continue
                    if not nucleus.frames():
                        self._count("nucleus_no_frame")
                        fired["no_frame"] += 1
                        continue
                    self.seen.add(nucleus.key)
                    nuclei.append(nucleus)
            self._draw(nuclei, promoted, tally, fires)
            self._record_fires(fires)
            self.log(
                f"[reframe] round {index}: "
                f"{min(start + self.seed_batch, len(pending)):,}/{len(pending):,} seed(s), "
                f"{tally['locations']:,} location(s), {tally['head_q4']:,} head-q4, "
                f"{self.spent() / 60.0:.1f} min"
            )
        for field_ in ("consumed_by_source", "locations_by_source", "head_q4_by_source"):
            tally[field_] = {
                source: tally[field_][source] for source in sorted(tally[field_], key=priority_of)
            }
        return tally, promoted

    # ------------------------------------------------------------- the fires
    def _fired(self, seed: Seed, cost: dict, fires: dict) -> dict:
        """Open this seed's fire record. One per seed per batch, merged if repeated.

        Everything but `locations` and `not_drawn` is known the moment [`fire`]
        returns; those two are what [`_draw`] fills in, which is why the record is
        opened here and written after the batch is read.
        """
        held = fires.setdefault(
            seed.id,
            {
                "seed": seed,
                "converged": newton_settled(cost),
                "undefined": bool((cost.get("refusals") or {}).get("reframing_undefined")),
                "nuclei": 0,
                "already_found": 0,
                "no_frame": 0,
                "not_drawn": 0,
                "locations": 0,
            },
        )
        return held

    def _record_fires(self, fires: dict) -> None:
        """One [`FIRE_KIND`] row per seed the batch fired, outcome and all.

        Written per **batch** rather than per seed, because the outcome is not
        known until the batch has been drawn and read — and per batch rather than
        per round, because a leg killed at hour six of eight would otherwise have
        recorded none of what it spent.

        The ladder is not on the row: the header carries it once for the whole
        leg and [`ladder_of`] is what reads it back.
        """
        for record in fires.values():
            seed = record["seed"]
            outcome = outcome_of(record)
            self._count(f"fire:{outcome}")
            self._count(f"fire:{outcome}:{seed.kind}")
            self.ledger.write(
                FIRE_KIND,
                channel=CHANNEL,
                batch=self.batch_index,
                seed={
                    "id": seed.id,
                    "kind": seed.kind,
                    "source": seed.source,
                    "tier": seed.tier,
                    "generation": seed.generation,
                    "reoffered": bool(seed.reoffered),
                },
                outcome=outcome,
                converged=bool(record["converged"]),
                locations=int(record["locations"]),
                nuclei=int(record["nuclei"]),
                already_found=int(record["already_found"]),
                no_frame=int(record["no_frame"]),
                not_drawn=int(record["not_drawn"]),
            )

    def _draw(
        self,
        nuclei: list[Nucleus],
        promoted: list[Seed],
        tally: dict,
        fires: dict | None = None,
    ) -> int:
        """Screen, score and write one batch of nuclei. One row per nucleus.

        `fires` is this batch's open fire records ([`_fired`]), and what is added
        to them here is per-seed: how many locations the seed's atoms became, and
        how many of them a crashed screen batch cost it a verdict on.
        """
        fires = {} if fires is None else fires
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
                # Its batch crashed twice and was given up on. The atom stays in
                # `seen`, so it is not reached again this run — which is the
                # honest cost of carrying on rather than stopping the leg. Its
                # seed's fire says so too, so a root the leg never got a verdict
                # for is not written down as barren.
                self._count("nucleus_not_drawn")
                if nucleus.seed.id in fires:
                    fires[nucleus.seed.id]["not_drawn"] += 1
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
            if nucleus.seed.id in fires:
                fires[nucleus.seed.id]["locations"] += 1
            tally["locations"] += 1
            mine = self._generation_tally(nucleus.generation)
            mine["locations"] += 1
            _bump(mine["rung_picked"], f"{chosen['rung']:g}")
            _bump(tally["locations_by_source"], nucleus.seed.source)
            self._count(f"location:{nucleus.seed.source}")
            self._count(f"fate:{row['fate']}")
            self._count(f"rung_picked:{chosen['rung']:g}")
            self._count(f"operator:{nucleus.operator}")
            for cell in readings:
                self._count(f"rung_drawn:{cell['rung']:g}")
                if cell["passed"]:
                    self._count(f"rung_passed:{cell['rung']:g}")
                if cell["p_ge4"] is not None and is_head_q4(cell):
                    self._count(f"rung_head_q4:{cell['rung']:g}")
            # Both promotion classes fire. A nucleus the head calls a 4 is the
            # better seed and goes ahead of every keeper on the queue, but a
            # generation that promoted only those would have offered 58 seeds
            # where 496 cleared the floor — and the floor is the bar the supply
            # engine already admits on, not a second opinion invented here.
            if row["reframing"]["head_q4"]:
                self._count("head_q4")
                self._count(f"head_q4:{nucleus.seed.source}")
                tally["head_q4"] += 1
                mine["head_q4"] += 1
                _bump(tally["head_q4_by_source"], nucleus.seed.source)
                promoted.append(self._promotion(nucleus, chosen, HEAD_Q4))
            elif money.passes_good_floor(chosen["p_ge3"]):
                self._count("head_keeper")
                mine["head_keeper"] += 1
                promoted.append(self._promotion(nucleus, chosen, HEAD_KEEPER))
        return written

    def _promotion(self, nucleus: Nucleus, chosen: dict, source: str) -> Seed:
        """One nucleus as the next generation's seed.

        The **human** tier travels, never the head's verdict: the claim this
        channel inherits is somebody's, and a promotion is a step away from the
        person who cast it rather than a new person. What says how far away is
        the generation, and what says on whose word this seed was taken is
        [`SOURCES`] — which is why both are on the row.
        """
        return Seed(
            id=nucleus.key,
            family=nucleus.seed.family,
            viewport=chosen["viewport"],
            tier=nucleus.seed.tier,
            generation=nucleus.generation,
            kind=CHANNEL,
            source=source,
        )

    # ------------------------------------------------------------ the record
    def summary(self, roots: list[Seed], consumed: int, per_round: list[dict]) -> dict:
        seconds = self.spent()
        operator_seconds = sum(tally["seconds"] for tally in self.cost.values())
        nuclei = len(self.seen)
        q4 = self.counts.get("head_q4", 0)
        return {
            "channel": CHANNEL,
            "run_seed": self.seed,
            "seconds": round(seconds, 2),
            "operator_seconds": round(operator_seconds, 2),
            "seed_max_period": self.max_period,
            "queue": list(SOURCES),
            "seeds_available": len(roots),
            "seeds_available_by_source": by_source(roots),
            "seeds_consumed": consumed,
            "nuclei": nuclei,
            "locations": self.rows_written,
            "head_q4": q4,
            "rounds": per_round,
            "by_generation": self.by_generation(),
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
            "ends": end_picks(
                {
                    float(name.split(":", 1)[1]): count
                    for name, count in self.counts.items()
                    if name.startswith("rung_picked:")
                },
                self.rungs,
            ),
            "fires": {
                "ladder": self.ladder(),
                "ladder_key": ladder_key(self.ladder()),
                "outcomes": {
                    name: self.counts.get(f"fire:{name}", 0)
                    for name in OUTCOMES
                    if self.counts.get(f"fire:{name}")
                },
                # What the next leg takes off its queue: fired, converged, and
                # not one location came of it. The others are all still offered.
                "consumed": self.counts.get(f"fire:{BARREN}", 0),
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
    max_period: int = SEED_SNAP_MAX_PERIOD,
    prior=None,
    reprobe: bool | None = REPROBE,
    log=print,
) -> dict:
    """Derive the seeds and run the channel over them. What the command calls.

    Two of this leg's arguments **default to a reading of the ledgers** rather
    than to a value, because both were things a person had to remember and the
    cost of forgetting either is silent:

    * `prior=None` discovers every earlier leg of this channel on both tiers
      ([`discovered_priors`]). An explicit list still wins and an empty one means
      none, but either way the discovery runs, so a list that omits a leg the
      ledgers know about is warned about.
    * `reprobe=None` decides from the chain ([`convergence`]). `True` and `False`
      are still obeyed exactly as before, and what the ledgers would have said is
      recorded beside the flag either way.
    """
    from fractal_wallpapers import paths
    from fractal_wallpapers.labeling import pins as pin_module

    pinned = pin_module.every_pinned()
    found, record = seeds(tier_floor=tier_floor, partitions=partitions, pinned=pinned)
    # This run's own ledger is excluded by the file rather than by the spelling,
    # and it is excluded even when it does not exist yet: a leg re-using a killed
    # leg's --out-dir would otherwise inherit its own finds.
    known, discovery = discovered_priors(exclude=Path(out_dir) / ledger_module.LEDGER_NAME, log=log)
    if prior is None:
        prior, discovery["source"] = known, "discovered"
    else:
        prior = [Path(each) for each in prior]
        discovery["source"] = "named"
        named = {path.resolve() for path in prior}
        omitted = [paths.tracked_name(path) for path in known if path.resolve() not in named]
        discovery["omitted"] = omitted
        if omitted:
            log(
                f"[reframe] WARNING: --prior names {len(prior)} leg(s) and the ledgers know of "
                f"{len(omitted)} more ({', '.join(omitted)}). A leg that omits an earlier one "
                f"re-finds its atoms and writes them a second time — 192 of one leg's 302 "
                f"rows, measured 2026-09-01. Running anyway: naming fewer is allowed."
            )
    record["priors_seen"] = discovery
    record["reprobe"] = None
    record["reprobe_because"] = None
    carried: list[Seed] = []
    earlier = None
    if prior:
        earlier = prior_run(prior, log=log)
        # The pin, on the promotions as well as on the roots. [`seeds`] applies
        # it while it derives the roots; a promotion is built out of an earlier
        # leg's own candidate rows and reaches the queue without passing that
        # query at all, so one pinned place among thousands used to raise
        # `PinnedPlace` the moment the queue got to it and end the leg — it
        # killed both legs of 2026-09-06 on the same seed. Filtered here rather
        # than in `prior_run`, whose job is to read the ledgers back as they are.
        earlier["promoted"], refused_pinned = unpinned(earlier["promoted"], pinned)
        record["carried_refused_pinned"] = refused_pinned
        if refused_pinned:
            log(
                f"[reframe] {refused_pinned} carried promotion(s) land on a place an "
                f"evaluation pin covers and were dropped from the queue."
            )
        # The ladder this leg would fire under, which is what a barren verdict on
        # the record is scoped to. Built off the same three fields the header row
        # is about to carry, through the reader the next leg will use.
        ladder = ladder_of(
            {
                "operators": list(OPERATORS),
                "rungs": list(rungs),
                "seed_max_period": int(max_period),
            }
        )
        history = earlier["history"]
        record["ladder"] = ladder
        record["ladder_key"] = ladder_key(ladder)

        def queue(seeds_: list[Seed], *, reprobe: bool) -> list[Seed]:
            """The offerable seeds, each marked with whether it is a re-offer."""
            out = []
            for seed in seeds_:
                entry = history.get(seed.id)
                if not offerable(entry, ladder, reprobe=reprobe):
                    continue
                out.append(replace(seed, reoffered=True) if returned_nothing(entry) else seed)
            return out

        # What a plain continuation would fire at. Both branches are derived
        # before either is chosen, because the convergence reading is about this
        # queue and the record has to carry it whichever way the leg went.
        plain_roots = queue(found, reprobe=False)
        plain_carried = queue(earlier["promoted"], reprobe=False)
        settled, why = convergence(earlier, plain_roots, plain_carried)
        if reprobe is None:
            reprobe, why["decided_by"] = settled, "ledgers"
        else:
            reprobe = bool(reprobe)
            why["decided_by"] = "flag"
            why["flag"] = reprobe
        before = len(found)
        offered = [*found, *earlier["promoted"]]
        if reprobe:
            found, carried = queue(found, reprobe=True), queue(earlier["promoted"], reprobe=True)
        else:
            found, carried = plain_roots, plain_carried
        record["refused_already_fired"] = before - len(found)
        record["carried"] = len(carried)
        record["reprobe"] = bool(reprobe)
        record["reprobe_because"] = why
        record["seeds"] = len(found)
        record["sources"] = by_source(found)
        # What the ladder rule did to this queue, every state named, and the two
        # refusals apart because they are different rulings. A `consumed` seed
        # was fired barren under a ladder that covers this one and is gone until
        # the ladder reaches further; a `held_unsettled` one is a seed Newton
        # never settled at, held while the period ceiling stands and offered the
        # moment it moves; a `reoffered` one returned nothing under a ladder that
        # no longer answers and is offered once more, last on the queue. The rest
        # of the gap between the label store and `fired` is seeds no leg has a
        # fire row for at all, which is every leg written before 2026-09-05 and
        # is why `unknown` is not zero. The reasons come off [`refusal`] itself,
        # so this readout cannot disagree with the queue it describes.
        why_refused = [refusal(history.get(seed.id), ladder, reprobe=False) for seed in offered]
        record["ladder_rule"] = {
            "seeds_returned_nothing": sum(
                1 for seed in offered if returned_nothing(history.get(seed.id))
            ),
            "consumed": sum(1 for reason in why_refused if reason == BARREN),
            "held_unsettled": sum(1 for reason in why_refused if reason == NO_CONVERGE),
            "reoffered": sum(1 for seed in [*found, *carried] if seed.reoffered),
            "unknown": sum(1 for seed in offered if not history.get(seed.id)),
        }
    if roots is not None:
        found = found[: max(0, int(roots))]
    log(f"[reframe] seeds: {json.dumps(record)}")
    if not found and not carried:
        raise ChannelRefused(
            "no seed survives: no proven parameter-plane location the pin allows, and no "
            "promotion carried in from a --prior run. Label some parameter-plane keepers, "
            "widen --tier-floor, or point --prior at a run that admitted something. On a "
            "chain whose queue is spent this is reachable only under --no-reprobe: the "
            "default reads the ledgers and re-probes instead of refusing."
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
        max_period=max_period,
        ledgers_read=discovery.get("ledgers_read"),
        log=log,
    )
    if earlier is not None:
        channel.seen |= earlier["found"]
    report = channel.run(found, carried=carried)
    report["seed_query"] = record
    report["prior"] = None if earlier is None else earlier["record"]
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
        # [`supply.location.key_text`] and not `str(key)`. The embedding store
        # spells a key as JSON, and a tuple repr matches none of it — which the
        # suppressor cannot report, because a place with no descriptor is kept by
        # rule. This read that way once and the whole pre-selection was a no-op.
        name = location_text(row)
        if name is None:
            continue
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
    "BARREN",
    "CENTERED",
    "CHANNEL",
    "DEFAULT_OUT",
    "FIRE_KIND",
    "HEAD_KEEPER",
    "HEAD_Q4",
    "ENDS_READOUT",
    "NOT_DRAWN",
    "NO_CONVERGE",
    "OUTCOMES",
    "OPERATORS",
    "PRODUCTIVE",
    "RUNGS",
    "REPROBE_FIRES",
    "UNDEFINED",
    "UNRESOLVED",
    "SCHEMA",
    "SEED_BATCH",
    "SEED_SNAP_MAX_PERIOD",
    "SEED_TIER_FLOOR",
    "SOURCES",
    "SATURATED",
    "SATURATION_FLOOR",
    "SCREEN_BATCH",
    "SCREEN_RETRIES",
    "RUN_KIND",
    "SUMMARY_KIND",
    "Channel",
    "ChannelRefused",
    "Nucleus",
    "PinnedPlace",
    "Seed",
    "by_source",
    "candidate_row",
    "convergence",
    "covers",
    "discovered_priors",
    "distinct_places",
    "end_picks",
    "fate_of",
    "fire",
    "first_row",
    "frame_multiple",
    "frame_of",
    "is_a_leg",
    "is_head_q4",
    "ladder_key",
    "ladder_of",
    "pick",
    "newton_settled",
    "offerable",
    "outcome_of",
    "prior_run",
    "rediscovery",
    "priority_of",
    "queued",
    "rank",
    "read",
    "read_rungs",
    "REPROBE",
    "run",
    "screen_rungs",
    "seeds",
    "refusal",
    "returned_nothing",
    "settles_the_same",
    "source_of_tier",
    "unpinned",
    "unsettled_under",
    "when",
]
