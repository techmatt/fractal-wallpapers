"""The two levers against monotony: what a lineage's next find is worth, and the
share of the batch that never has to be worth anything.

A harvest's allocator is very good at spending the clock where supply is
scarcest, and completely indifferent to whether the supply it buys there is *the
same picture*. `deep_run1` put 741 admissions on 15 of its 48 roots and 85 on one,
and the finished frames were largely one composition. The walk's per-lineage cap
is the hard stop against that; these two are the soft ones, and they act on the
allocator rather than on the walk.

```text
lineage discount   contest credit ×= max(f, 1 / (1 + k·n)),  n = THIS run's
                   admissions from that lineage
exploration share  a protected fraction of the post-floor slots, reserved for
                   lineages NO run has ever booked an admission from
```

**The two are about different clocks and that is why there are two.** The
discount is *in-run*: it stops one lineage taking the back half of a run once it
has already given the run everything it has. Membership of the share is
*cross-run*: a lineage that earlier runs already mined is not novel however quiet
it has been today. Neither subsumes the other, and running only the first would
re-buy last month's basins at full price.

## Where each one acts

The ruled order of a batch's slots is **floor, then share, then contest**:

1. the per-partition floor's claimants are guaranteed their slot first — the
   re-entry path in [`fractal_wallpapers.supply.allocation`], and nothing below
   may eat it;
2. the exploration share takes its fraction of what is left;
3. the deficit-priced contest takes the remainder, and the discount is applied
   **there and nowhere else**.

Keeping the discount out of the share is not tidiness. A share node's whole
claim is that nothing has priced its lineage, so pricing it inside the share
would be the contest reaching into the one place the contest is excluded from.
Inside the share the head *ranks* — the ordinary priority, undiscounted — and
only the junk floor kills.

## The discount is applied at the contest, not baked into the priority

A frontier node's priority is drawn once, when it is pushed, and never re-drawn.
That is right for the Gumbel — a node that lost a batch should not get a fresh
lottery ticket — and wrong for this, because `n` is a *running* count: a lineage
that had booked nothing when its node was pushed may have booked forty by the
time the node is popped. So the discount is a ranking key evaluated at the pop,
against the lineage's count at that moment, and the node's stored priority is
left alone. That also leaves the share ranking by an unpriced number for free.

Its shape is the one [`fractal_wallpapers.supply.saturation`] already uses — the
score term of the priority is multiplied, the exploration draw is not — so a
saturated lineage with a great score loses to a fresh lineage with a good one and
still beats a fresh lineage with a bad one. And it carries the same honest
caveat: **under the null scorer every score term is the neutral prior and this
moves nothing at all**. There is no quality signal to discount yet; the lever
starts biting the day one arrives.

## Membership is a root-neighbourhood, and it is frozen at the run's start

The ledgers key a lineage by `root_id`, and a `root_id` is scoped to the run that
minted it — two runs mint the same number for different places. So the portable
identity is the root's *place*: its partition, its parameter identity, and its
frame. A prior root that booked at least one admission shadows a disc of
`RADIUS × its own width` around itself, exactly as a visit does in the saturation
memory, and a new root inside one of those discs is not novel.

That tolerance is load-bearing at both ends. Parameter-plane roots come off a
tracked pool at width `1e-2`, so the disc is `3e-3` wide and two neighbouring
pool entries stay different lineages. A Julia root's frame is its family's home
view for every `c`, so the coordinate says nothing and `identity_of` — the `c`
itself, exactly — is what separates them, which is the right answer: a `c` no run
has walked is a lineage no run has walked.

Palette never enters any of it. A colormap is not part of a location's identity
anywhere in this project, and a lineage counted per palette would report one
composition in a hundred and sixty palettes as a hundred and sixty lineages —
which is precisely the number the monotony measure exists to refuse.

The index is built once, before the first batch, and never mutated. This run's
own admissions belong to the *discount*, not to membership: a share member that
starts producing is exactly what the share was bought for, and demoting it
mid-run would make the share's own success look like a shrinking share.

## The share prices itself, in the style the prices already use

```text
rate(channel) = (EMA admissions + one pseudo-slot at the pooled rate)
                ÷ (EMA slots + one pseudo-slot)
share        ← clamp(share × rate(share) / rate(contest), floor, 1)
```

Ratio of two averages, never an average of ratios — the same reason
[`fractal_wallpapers.supply.prices`] holds its numerator and denominator apart: a
batch where the share drew slots and found nothing has a denominator to
contribute even though it has no ratio to sample.

**The pseudo-slot is what makes the ratio finite without a tuning constant.**
Each channel is given one extra slot's worth of evidence at the *pooled* rate, so
a channel nothing has served yet prices at the pooled rate and the ratio is
exactly one — the share does not move on no evidence — and a contest that has
found nothing at all cannot divide the share by zero. It washes out as soon as
either channel has served a few slots, which is what an evidence prior is for.

The floor is a floor and there is no ceiling below one. A share that priced
itself to the whole batch would be a run whose contest has been buying nothing
for long enough to say so, and that is a finding rather than a fault; the floor
is what stops the mirror image from ever silencing exploration entirely.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

from fractal_wallpapers.supply import ledgers, saturation
from fractal_wallpapers.supply.partitions import partition_of_family, partition_of_row

#: How fast a lineage's contest credit decays with what it has already booked
#: this run. At `0.5` the second admission is worth two thirds of the first and
#: the tenth is worth a sixth.
DISCOUNT_K = 0.5

#: The floor the discount never goes below. A lineage that has given a run forty
#: finds is still worth a fifth of a fresh one — it is producing, and a discount
#: that reached zero would be the lineage cap wearing a price's clothes.
DISCOUNT_FLOOR = 0.2

#: The share of post-floor slots exploration may never fall below.
SHARE_FLOOR = 0.25

#: What the share opens at, above its floor, before it has priced itself.
SHARE_START = 0.45

#: The per-served-batch smoothing weight for the share's own pricing. The same
#: number [`fractal_wallpapers.supply.prices.PRICE_EMA`] uses and for the same
#: reason: one batch displaces about a seventh of the accumulated evidence.
SHARE_EMA = 0.15

#: The names a batch's two non-floor channels are recorded under, on the node,
#: on the candidate row, and in every tally that divides them.
SHARE = "share"
CONTEST = "contest"


def lineage_discount(
    admissions: int, k: float = DISCOUNT_K, floor: float = DISCOUNT_FLOOR
) -> float:
    """`max(floor, 1 / (1 + k·n))` — what this lineage's next find is worth.

    `n = 0` is exactly `1.0`, which is the whole of the claim that a lineage that
    has booked nothing this run is not discounted at all.
    """
    n = max(0, int(admissions))
    if k <= 0.0:
        return 1.0
    return max(float(floor), 1.0 / (1.0 + float(k) * n))


class NovelLineages:
    """Which root-neighbourhoods no run in the ledgers has ever booked from.

    Built once and frozen. The index inside is the saturation memory's, holding a
    different population: not every place a walk looked, but every *root* whose
    lineage produced at least one admission.
    """

    def __init__(self, index: saturation.VisitedIndex | None = None):
        self.index = index if index is not None else saturation.VisitedIndex()
        #: Roots read, and roots that admitted — the second is what is indexed.
        self.roots_read = 0
        self.roots_admitting = 0
        self.unplaceable = 0
        self.ledgers = 0
        #: The verdicts this run has handed out, so a readout can say how much of
        #: its own frontier the membership test called novel.
        self.asked = 0
        self.novel = 0

    def is_novel(self, family: dict, viewport: dict) -> bool:
        """Whether no ledger holds an admitting root in this root's neighbourhood.

        A root whose place cannot be read is **not** novel, and is counted. The
        share is a protected allocation, and admitting an unreadable row into it
        would spend a floor on a row nothing can say anything about.
        """
        self.asked += 1
        if not isinstance(family, dict) or not isinstance(viewport, dict):
            self.unplaceable += 1
            return False
        try:
            partition = partition_of_family(family)
            here = self.index.density(
                partition,
                saturation.identity_of(family),
                float(viewport["center_re"]),
                float(viewport["center_im"]),
            )
        except (KeyError, TypeError, ValueError):
            self.unplaceable += 1
            return False
        if here <= 0:
            self.novel += 1
            return True
        return False

    def summary(self) -> dict:
        return {
            "radius": self.index.radius,
            "ledgers": self.ledgers,
            "roots_read": self.roots_read,
            "roots_admitting": self.roots_admitting,
            "indexed": self.index.visits,
            "partitions": dict(sorted(self.index.per_partition.items())),
            "roots_asked": self.asked,
            "roots_novel": self.novel,
            "unplaceable": self.unplaceable,
        }


def build(
    radius: float = saturation.RADIUS,
    root: Path | None = None,
    exclude: Path | None = None,
    admit=None,
    paths=None,
) -> NovelLineages:
    """The cross-run record of which lineages have ever produced, off the ledgers.

    One pass per file, reading both kinds of row it needs: the `root` rows say
    where each lineage stood, and the admitted `candidate` rows say which of them
    produced. A ledger whose rows name a root it never wrote a `root` row for
    contributes nothing for that root and is not an error — the ledger is
    append-only and a killed run can end anywhere.

    `paths` hands in the ledger list a caller has already found, so the three
    builders a harvest starts with share one answer instead of asking three times.
    """
    paths = ledgers.ledger_paths(root, exclude) if paths is None else list(paths)
    found = NovelLineages(saturation.VisitedIndex(radius))
    found.ledgers = len(paths)
    predicate = ledgers.is_admitted if admit is None else admit
    for path in paths:
        roots: dict = {}
        admitting: set = set()
        for row in ledgers.rows(path):
            kind = row.get("kind")
            if kind == "root":
                roots[row.get("root_id")] = row
            elif kind == "candidate" and predicate(row):
                admitting.add(row.get("root_id"))
        found.roots_read += len(roots)
        for root_id in admitting:
            row = roots.get(root_id)
            if row is None:
                continue
            found.roots_admitting += 1
            viewport = row.get("viewport") or {}
            if not found.index.add(
                partition_of_row(row),
                saturation.identity_of(row.get("family") or {}),
                viewport.get("center_re"),
                viewport.get("center_im"),
                viewport.get("width"),
            ):
                found.unplaceable += 1
    return found


@dataclass
class Channel:
    """One channel's evidence: slots served and admissions booked, smoothed."""

    slots: float = 0.0
    admissions: float = 0.0
    #: The raw totals, which the readout reports and the pricing never reads.
    total_slots: int = 0
    total_admissions: int = 0

    def settle(self, slots: int, admissions: int, ema: float) -> None:
        self.total_slots += int(slots)
        self.total_admissions += int(admissions)
        self.slots = (1.0 - ema) * self.slots + ema * float(slots)
        self.admissions = (1.0 - ema) * self.admissions + ema * float(admissions)

    def rate(self, pooled: float) -> float:
        """Admissions per slot, with one pseudo-slot of evidence at `pooled`."""
        return (self.admissions + pooled) / (self.slots + 1.0)

    def state(self) -> dict:
        return {
            "slots": self.slots,
            "admissions": self.admissions,
            "total_slots": self.total_slots,
            "total_admissions": self.total_admissions,
        }


@dataclass
class Exploration:
    """Lever 4: who is in the protected share, how big it is, and what it bought.

    Held by the run and checkpointed whole, because the share is a *priced*
    quantity: a resumed run that reopened at the start value would throw away
    every batch of evidence the first session paid for.
    """

    lineages: NovelLineages = field(default_factory=NovelLineages)
    floor: float = SHARE_FLOOR
    start: float = SHARE_START
    ema: float = SHARE_EMA
    share: float = None  # type: ignore[assignment]
    share_channel: Channel = field(default_factory=Channel)
    contest_channel: Channel = field(default_factory=Channel)
    steps: int = 0
    #: Post-floor slots offered, and how many of them the share actually took —
    #: per partition and pooled. The realized share is the second over the first.
    offered: dict = field(default_factory=dict)
    taken: dict = field(default_factory=dict)
    #: Membership, cached per root id. A root's place does not change.
    members: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.share is None:
            self.share = max(float(self.floor), float(self.start))

    # ------------------------------------------------------------ membership

    def member(self, root_id: int, root: dict | None) -> bool:
        """Whether this root's lineage is one no run has ever booked from.

        `root` is the walk's own record of what the root is. A root the walk
        cannot describe is not a member, on the same rule as an unreadable one.
        """
        root_id = int(root_id)
        known = self.members.get(root_id)
        if known is not None:
            return known
        verdict = False
        if root:
            verdict = self.lineages.is_novel(root.get("family"), root.get("viewport"))
        self.members[root_id] = verdict
        return verdict

    # ----------------------------------------------------------------- slots

    def split(self, post_floor: int) -> int:
        """How many of the post-floor slots the share claims.

        Rounded half **up**, so a two-slot remainder at the floor claims one
        rather than none: this is a floor on exploration and a floor that
        disappears in every small batch is not one.
        """
        post_floor = max(0, int(post_floor))
        return max(0, min(post_floor, int(math.floor(self.share * post_floor + 0.5))))

    def note_offer(self, partition: str, offered: int, taken: int) -> None:
        self.offered[partition] = self.offered.get(partition, 0) + int(offered)
        self.taken[partition] = self.taken.get(partition, 0) + int(taken)

    # --------------------------------------------------------------- pricing

    def settle(self, share: dict, contest: dict) -> dict:
        """One served batch: both channels take their evidence, then the share
        re-prices itself. Returns what it did, for the batch trace."""
        self.share_channel.settle(share.get("slots", 0), share.get("admissions", 0), self.ema)
        self.contest_channel.settle(contest.get("slots", 0), contest.get("admissions", 0), self.ema)
        before = self.share
        pooled_slots = self.share_channel.slots + self.contest_channel.slots
        pooled_admissions = self.share_channel.admissions + self.contest_channel.admissions
        pooled = pooled_admissions / pooled_slots if pooled_slots > 0 else 0.0
        share_rate = self.share_channel.rate(pooled)
        contest_rate = self.contest_channel.rate(pooled)
        ratio = share_rate / contest_rate if contest_rate > 0 else 1.0
        self.share = min(1.0, max(float(self.floor), self.share * ratio))
        self.steps += 1
        return {
            "share_before": round(before, 4),
            "share": round(self.share, 4),
            "ratio": round(ratio, 4),
            "share_rate": round(share_rate, 5),
            "contest_rate": round(contest_rate, 5),
        }

    # ------------------------------------------------------------- reporting

    def realized(self) -> dict:
        """The share the batches actually spent, per partition and overall."""
        rows = {}
        for partition in sorted(set(self.offered) | set(self.taken)):
            offered = self.offered.get(partition, 0)
            rows[partition] = {
                "post_floor_slots": offered,
                "share_slots": self.taken.get(partition, 0),
                "realized": (
                    round(self.taken.get(partition, 0) / offered, 4) if offered > 0 else None
                ),
            }
        offered = sum(self.offered.values())
        taken = sum(self.taken.values())
        return {
            "floor": self.floor,
            "start": self.start,
            "share_now": round(self.share, 4),
            "overall": {
                "post_floor_slots": offered,
                "share_slots": taken,
                "realized": round(taken / offered, 4) if offered > 0 else None,
            },
            "per_partition": rows,
        }

    def bought(self) -> dict:
        """What each channel spent and what it returned."""
        rows = {}
        for name, channel in ((SHARE, self.share_channel), (CONTEST, self.contest_channel)):
            rows[name] = {
                "slots": channel.total_slots,
                "admissions": channel.total_admissions,
                "admissions_per_slot": (
                    round(channel.total_admissions / channel.total_slots, 4)
                    if channel.total_slots
                    else None
                ),
            }
        return rows

    def summary(self) -> dict:
        return {
            "status": "on",
            "ema": self.ema,
            "steps": self.steps,
            "realized": self.realized(),
            "bought": self.bought(),
            "index": self.lineages.summary(),
            "roots_in_share": sum(1 for v in self.members.values() if v),
            "roots_classified": len(self.members),
        }

    # ----------------------------------------------------------------- state

    def state(self) -> dict:
        return {
            "floor": self.floor,
            "start": self.start,
            "ema": self.ema,
            "share": self.share,
            "steps": self.steps,
            "share_channel": self.share_channel.state(),
            "contest_channel": self.contest_channel.state(),
            "offered": self.offered,
            "taken": self.taken,
            # Membership, and not the index it came from: the index is rebuilt
            # from the same ledgers at every start and the verdicts are cached
            # answers, but a root minted in an earlier session is not on the
            # frontier's classification path any more and would silently default.
            "members": {str(k): bool(v) for k, v in self.members.items()},
        }

    def load_state(self, state: dict) -> None:
        self.share = float(state.get("share", self.share))
        self.steps = int(state.get("steps", self.steps))
        for name, channel in (
            ("share_channel", self.share_channel),
            ("contest_channel", self.contest_channel),
        ):
            saved = state.get(name) or {}
            channel.slots = float(saved.get("slots", channel.slots))
            channel.admissions = float(saved.get("admissions", channel.admissions))
            channel.total_slots = int(saved.get("total_slots", channel.total_slots))
            channel.total_admissions = int(saved.get("total_admissions", channel.total_admissions))
        self.offered.update({p: int(v) for p, v in (state.get("offered") or {}).items()})
        self.taken.update({p: int(v) for p, v in (state.get("taken") or {}).items()})
        self.members.update({int(k): bool(v) for k, v in (state.get("members") or {}).items()})


__all__ = [
    "CONTEST",
    "DISCOUNT_FLOOR",
    "DISCOUNT_K",
    "SHARE",
    "SHARE_EMA",
    "SHARE_FLOOR",
    "SHARE_START",
    "Channel",
    "Exploration",
    "NovelLineages",
    "build",
    "lineage_discount",
]
