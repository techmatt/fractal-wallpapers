"""Refilling a partition whose queue has run dry.

The quota can only serve a partition that has something in it. A global low-water
mark on the whole frontier cannot see that: the frontier stays comfortably full
while eight of ten queues sit at zero, because one partition multiplies fast
enough to hold the total up on its own. So the mark is **per partition**, and a
partition below it gets fresh roots.

Three bounds on that, and each one exists because the unbounded version fails:

* **a cooldown**, so a partition whose supply is exhausted is not re-drawn every
  batch to prove it;
* **a share of the loop's clock**, so refills cannot become the run — expressed
  against the total loop wall rather than against batch time alone, so it is
  well-defined at zero and the first refill of a run always clears it;
* **the pool is finite and the cursor only moves forward**, so a refill hands over
  roots the run has not seen rather than re-seeding the same ones.

**A Julia twin's pool is manufactured, not shipped.** The degree-2 twin draws
from a tracked `c`-pool; the higher-degree twins have none, and used to be
deferred forever with "fed by reframing only" — which reached them never, because
a reframing operator is undefined on a dynamical viewport. Their channel is
[`fractal_wallpapers.supply.twins`]: an admitted location of the degree-`d`
parameter plane *is* a `c` for the degree-`d` Julia family, so serving the parent
manufactures the twin's supply. It hands over the same seed object the tracked
pool does, through the same cursor and the same low-water mark; the only
difference is that its list grows during the run.

**Any partition can also be seeded from what a human already liked.** The proven
channel — [`fractal_wallpapers.supply.proven`] — derives a root from every
location the label store holds a keeper verdict on, and hands it over through the
same cursor and the same low-water mark as everything else. It is *interleaved*
with the partition's own pool rather than replacing it: a channel fed by the
project's own past output cannot open new ground, so crowding the pool out would
leave the run nowhere new to look. Off unless a run asks for it by name.

**That is what makes a queue hold two shapes of entry.** A pool hands over a
*parameter* — a `c`, or a phoenix `(c, p, z₋₁)` — and a root built from one comes
up at the family's home view, because a parameter has no frame in it. The proven
channel hands over a *location*, and a root built from one comes up at the frame
the human scored. Both land in the same queue behind the same cursor, so the
place they are told apart is [`Refill._root_of`], once, on the entry's shape: a
branch per partition would be the same question asked five times.

**A partition with no channel is deferred, with a reason, not silently skipped.**
A starved partition absent from both the refill list and the run record is
indistinguishable from a healthy one — which is how a run once went four hundred
batches with eight empty queues and no refills, reporting nothing. Deferral is a
statement: *this partition is below its mark, and here is why no draw can help.*

**An externally-supplied partition is neither starved nor deferred.** No channel
inside the walk feeds it, so an empty queue is its normal state; reporting it
every batch is a permanent false alarm, and a row that is always red trains the
reader to ignore the whole census — which is the opposite of what the census is
for.
"""

from __future__ import annotations

import time
from pathlib import Path

from fractal_wallpapers.discovery import pools
from fractal_wallpapers.supply import proven as proven_channel
from fractal_wallpapers.supply.partitions import (
    ALL_PARTITIONS,
    is_dynamical,
    parameter_plane_of,
    partition_of_family,
)

#: A partition below this many frontier nodes is starved.
LOW_WATER = 8

#: Batches a partition waits between refills.
COOLDOWN = 10

#: Refill seconds may not exceed this share of the loop's wall clock.
SHARE = 0.25

#: Why a starved partition gets no refill, by partition. Empty, and that is the
#: news: the three higher-degree Julia twins were the whole of this table, and
#: [`fractal_wallpapers.supply.twins`] is the channel they were missing. A run
#: with no twin channel wired in says so through [`NO_TWIN_CHANNEL`] instead,
#: because "this run was built without it" and "no such channel exists" are
#: different statements and only one of them used to be sayable.
DEFERRAL: dict = {}

#: Why a Julia twin gets no refill when the run holds no twin channel at all.
NO_TWIN_CHANNEL = (
    "no twin channel is wired into this run, so nothing derives Julia parameters from "
    "{plane}'s admissions. Build the harvest with one — `supply.twins.build()` — or accept "
    "that this partition is fed by reframing only, which reaches it never."
)

#: Why a parameter-plane partition gets no refill when it has no pool to draw on.
NO_SEED_FILE = (
    "the parameter planes have no sampler: an unscreened draw over the higher degrees "
    "measured zero good locations in 144, so roots come from the tracked plane seed pool, "
    "an explicit --seeds file, the proven channel, or what the reframing operators "
    "reach. This run has none of them — derive the pool with `fractal-wallpapers "
    "derive-plane-seeds --write`, or add `--root-channel proven`."
)

#: Why an externally-supplied partition has no pool. It is not starvation and it
#: is not a missing channel: another leg of the project fills it, so the refill
#: has nothing to say about it and says that rather than reporting an empty pool.
EXTERNALLY_SUPPLIED = "externally supplied: another leg fills this partition, no draw is made"


def _tracked_plane_pool() -> Path | None:
    """The shipped parameter-plane pool, or `None` on a clone that has not derived it."""
    from fractal_wallpapers.discovery import plane_seeds

    path = plane_seeds.pool_path()
    return path if path.is_file() else None


class Refill:
    """The seed pools a run can still draw from, and what is left of each.

    Holds a cursor per channel rather than a fresh draw: a pool is data, so
    "refill" means *hand over the next entries nobody has walked yet*, and a
    channel that runs out says so instead of re-seeding what the run already has.
    """

    def __init__(
        self,
        walk,
        *,
        low_water: int = LOW_WATER,
        cooldown: int = COOLDOWN,
        share: float = SHARE,
        per_draw: int | None = None,
        seeds: Path | None = None,
        external=(),
        partitions=ALL_PARTITIONS,
        twins=None,
        proven=None,
    ):
        self.walk = walk
        self.twins = twins
        self.proven = proven
        self.low_water = int(low_water)
        self.cooldown = int(cooldown)
        self.share = float(share)
        self.per_draw = int(per_draw if per_draw is not None else low_water)
        self.partitions = list(partitions)
        self.external = set(external)
        self.seconds = 0.0
        self.draws = 0
        self.roots_added = 0
        self.deferred_draws = 0
        self.last_refill: dict = {}
        self.cursor: dict = {}
        self._pools: dict = {}
        # The tracked pool is the default channel for the parameter planes, not a
        # fallback nobody reaches: a run that had to be handed a seed file to
        # refill four of its ten partitions is a run that silently does not, and
        # the first production run spent two hours proving it.
        self._seeds = Path(seeds) if seeds is not None else _tracked_plane_pool()

    # ----------------------------------------------------------- the channels

    def _seed_rows(self) -> list[dict]:
        """The seed file's rows. The tracked pool is read through its own reader,
        so its invariants are checked here and not only where it was derived."""
        from fractal_wallpapers.discovery import plane_seeds

        if self._seeds == plane_seeds.pool_path():
            return pools.plane_pool(self._seeds)
        return pools.read_seed_file(self._seeds)

    def _pool(self, partition: str) -> list:
        """The entries this partition's channel can still hand over.

        One queue however many channels feed it, because the cursor is per
        partition: two cursors served in whatever order a queue drains would
        decide the mix between the channels by accident.
        """
        # The twin channel's list is never cached: it grows as the run books
        # parent-plane admissions, and a snapshot of it would freeze a channel
        # whose whole point is that serving the parent fills it. The interleave
        # is re-made with it and that is safe under the cursor — `interleave`
        # only ever appends when the pool side grows, so everything already
        # drawn stays where it was.
        if self._is_twin(partition):
            return self._with_proven(partition, self.twins.seeds(partition))
        if partition in self._pools:
            return self._pools[partition]
        if partition == "julia:mandelbrot":
            rows = pools.julia_pool()
        elif partition == "phoenix":
            rows = pools.phoenix_pool()
        else:
            rows = (
                [row for row in self._seed_rows() if _seed_partition(row) == partition]
                if self._seeds is not None
                else []
            )
        rows = self._with_proven(partition, rows)
        self._pools[partition] = rows
        return rows

    def _with_proven(self, partition: str, rows: list) -> list:
        """`rows` with this partition's proven roots interleaved through them.

        Interleaved rather than prepended: the proven channel feeds on this
        project's own past output, so a queue that spent itself on proven roots
        first would reach new ground only after it ran out.
        """
        if not self._is_proven(partition):
            return rows
        return self.proven.pool(partition, rows)

    def _is_twin(self, partition: str) -> bool:
        """Whether the twin channel is this partition's channel.

        The channel names the twins it serves, and it deliberately leaves out the
        degree-2 one: that twin has a tracked `c`-pool a three-stage screen
        produced, and a derived parameter must not displace it.
        """
        return self.twins is not None and partition in self.twins.partitions

    def _is_proven(self, partition: str) -> bool:
        """Whether the proven channel holds roots for this partition.

        It serves every partition but `phoenix:classic`, so on the dynamical
        side it shares a queue with a `c`-pool rather than standing in for a
        missing sampler. It does not compete with one: a pool row is a
        parameter and starts at the home view, a proven row is a whole place,
        and the interleave is what keeps either from crowding the other out.
        """
        return self.proven is not None and partition in self.proven.partitions

    def has_channel(self, partition: str) -> bool:
        """Whether any draw could serve this partition at all.

        The refusal of the pinned classic phoenix is first and unconditional:
        no channel in the walk feeds one parameter point, and it must not
        acquire one by being swept up in a list that grew.
        """
        if partition in self.external or partition in DEFERRAL:
            return False
        if partition == "phoenix:classic":
            return False
        if partition in ("julia:mandelbrot", "phoenix"):
            return True
        if is_dynamical(partition):
            return self._is_twin(partition) or self._is_proven(partition)
        return self._seeds is not None or self._is_proven(partition)

    def remaining(self, partition: str) -> int:
        return max(0, len(self._pool(partition)) - self.cursor.get(partition, 0))

    # ------------------------------------------------------------- the census

    def starved(self, queues: dict, batch: int) -> list[str]:
        """Partitions below the low-water that a draw can actually serve."""
        out = []
        for partition in self.partitions:
            if not self.has_channel(partition):
                continue
            if queues.get(partition, 0) >= self.low_water:
                continue
            last = self.last_refill.get(partition)
            if last is not None and (batch - last) < self.cooldown:
                continue
            if self.remaining(partition) <= 0:
                continue
            out.append(partition)
        return out

    def pool_state(self) -> dict:
        """`{partition: {channel, pool, proven, drawn, remaining, reason}}` before a batch.

        A channel's *reach*, stated at launch instead of inferred from a readout.
        run10 opened with 39, 46 and 52 derived parameters in its three julia
        twins and 209 and 96 in the two tracked `c`-pools, against 413 to 507 in
        each parameter plane. All five of the small ones ran dry inside the night,
        the exploration share had nothing left to buy in those partitions, and the
        first anybody read of it was the readout. Nothing was wrong with the
        allocation; the numbers that predicted it were simply never printed.

        A partition no draw can serve carries the same sentence [`deferred`] would
        give it, so the two never disagree about why: this is asked at batch zero
        with every queue empty, which is exactly the state that makes `deferred`'s
        reasons the ones that apply.

        `pool` is the whole interleaved queue and `proven` is how much of it came
        from the label store. Both, because on a partition fed by two channels
        "entries left" alone cannot say what is left: a dynamical queue that has
        run out of `c` and a dynamical queue that has run out of labelled places
        exhaust in different ways and are fixed by different things.
        """
        empty = dict.fromkeys(self.partitions, 0)
        reasons = self.deferred(empty)
        out = {}
        for partition in self.partitions:
            servable = self.has_channel(partition)
            pool = len(self._pool(partition)) if servable else 0
            drawn = self.cursor.get(partition, 0)
            reason = (reasons.get(partition) or {}).get("reason")
            if reason is None and partition in self.external:
                reason = EXTERNALLY_SUPPLIED
            out[partition] = {
                "channel": servable,
                "pool": pool,
                "proven": len(self.proven.seeds(partition)) if self._is_proven(partition) else 0,
                "drawn": drawn,
                "remaining": max(0, pool - drawn),
                "reason": reason,
            }
        return out

    def pool_lines(self) -> list[str]:
        """[`pool_state`] as the lines a launch prints, one per partition."""
        out = []
        for partition, state in sorted(self.pool_state().items()):
            if state["reason"] is None:
                line = f"pool {partition}: {state['remaining']} of {state['pool']} entries left"
                if state["proven"]:
                    line += f", {state['proven']} of them proven roots"
                out.append(line)
            else:
                out.append(f"pool {partition}: {state['reason']}")
        return out

    def deferred(self, queues: dict) -> dict:
        """Partitions below the low-water that no draw will be made for, each with
        the reason. Externally-supplied partitions are absent by design."""
        out = {}
        for partition in self.partitions:
            if partition in self.external:
                continue
            if queues.get(partition, 0) >= self.low_water:
                continue
            if self.has_channel(partition) and self.remaining(partition) > 0:
                continue
            if partition in DEFERRAL:
                reason = DEFERRAL[partition]
            elif self._is_twin(partition):
                reason = self.twins.starvation(partition, drawn=self.cursor.get(partition, 0))
            elif self.has_channel(partition):
                # Asked before the missing-channel sentences, because a twin with
                # proven roots and no twin channel has a channel: what it ran out
                # of is labelled places, and "no twin channel is wired in" would
                # name the wrong thing to go and fix.
                reason = "the channel's pool is exhausted: every entry has been walked"
            elif is_dynamical(partition) and partition != "julia:mandelbrot":
                reason = NO_TWIN_CHANNEL.format(plane=parameter_plane_of(partition))
            else:
                reason = NO_SEED_FILE
            out[partition] = {
                "queue": queues.get(partition, 0),
                "low_water": self.low_water,
                "reason": reason,
            }
        return out

    def affordable(self, loop_seconds: float) -> bool:
        """Have refills stayed inside their share of the loop's wall clock?

        Against the total loop wall — batch time plus refill time — so it is
        well-defined at zero: the first refill of a run always clears it, and a run
        that has spent nothing but refilling always fails it.
        """
        total = float(loop_seconds) + self.seconds
        return self.seconds <= self.share * total if total > 0 else True

    # -------------------------------------------------------------- the draw

    def run(self, queues: dict, batch: int, loop_seconds: float) -> dict:
        """Refill whatever is starved and affordable. Returns what it did.

        Cost is charged whether or not the draw produced anything: a draw that
        yields nothing still spent the clock, and an affordability bound fed only
        by successful draws is a bound that loosens exactly when the draws stop
        working.
        """
        starved = self.starved(queues, batch)
        if not starved:
            return {"refilled": [], "roots": 0}
        if not self.affordable(loop_seconds):
            self.deferred_draws += 1
            return {"refilled": [], "roots": 0, "reason": "over the refill share"}
        started = time.monotonic()
        added = 0
        for partition in starved:
            added += self._draw(partition)
            self.last_refill[partition] = batch
        self.seconds += time.monotonic() - started
        self.draws += 1
        self.roots_added += added
        return {"refilled": starved, "roots": added}

    def _draw(self, partition: str) -> int:
        rows = self._pool(partition)
        start = self.cursor.get(partition, 0)
        taken = rows[start : start + self.per_draw]
        self.cursor[partition] = start + len(taken)
        for index, entry in enumerate(taken, start=start):
            root = self._root_of(partition, entry, index)
            self.walk.add_root(
                root["family"],
                root["viewport"],
                source=root["source"],
                provenance=root["provenance"],
            )
        return len(taken)

    def _root_of(self, partition: str, entry, index: int) -> dict:
        """One queue entry as the root it becomes: family, view, source, provenance.

        **The dispatch is on the entry's shape, not on its partition**, and that
        is the whole of it. A queue holds two kinds of entry: a pool's typed
        seed, which is a *parameter* and comes up at the family's home frame, and
        a row, which is a whole *location* and comes up at the frame it carries.
        Both reach every served partition now that the proven channel does, so a
        branch per partition would answer the same question five times over and
        the five answers would drift.
        """
        if isinstance(entry, dict):
            return self._root_of_row(entry, index)
        if isinstance(entry, pools.JuliaSeed) and self._is_twin(partition):
            # The same seed object and the same call the degree-2 channel makes,
            # at the degree its parent plane carries. That is what keeps this one
            # channel more rather than a second mechanism.
            return {
                "family": entry.family(self.twins.degree_of(partition)),
                "viewport": None,
                "source": "twin_channel",
                "provenance": {
                    "seed_id": entry.id,
                    "channel": entry.channel,
                    "parent_plane": self.twins.plane_of(partition),
                    "refill": True,
                },
            }
        if isinstance(entry, pools.JuliaSeed) and partition == "julia:mandelbrot":
            return {
                "family": entry.family(2),
                "viewport": None,
                "source": "julia_c_pool",
                "provenance": {"seed_id": entry.id, "channel": entry.channel, "refill": True},
            }
        if isinstance(entry, pools.PhoenixSeed) and partition == "phoenix":
            return {
                "family": entry.family(),
                "viewport": None,
                "source": "phoenix_seed_pool",
                "provenance": {"seed_id": entry.id, "branch": entry.branch, "refill": True},
            }
        raise TypeError(
            f"{partition} handed the refill a {type(entry).__name__}, and no channel this "
            f"partition has builds a root out of one. A queue entry is either a row — a "
            f"location, carrying its own viewport — or the typed seed of that partition's "
            f"own pool."
        )

    def _root_of_row(self, entry: dict, index: int) -> dict:
        """A `{family, viewport}` row as a root: a seed file's, or the proven channel's.

        The one door a root enters at a *place* rather than at a home view, which
        is what the proven channel is worth on a dynamical partition: a `c`-pool
        can express a parameter and nothing else.
        """
        view = entry.get("viewport")
        # The row's own channel, carried onto the root. A queue can hold two
        # channels at once, and attributing a find afterwards should be a join on
        # a field rather than a guess at an id prefix.
        channel = (entry.get("provenance") or {}).get("channel")
        return {
            "family": entry["family"],
            "viewport": (
                {
                    "center_re": str(view["center_re"]),
                    "center_im": str(view["center_im"]),
                    "width": str(view["width"]),
                }
                if view
                else None
            ),
            # One source for every row, and the grace below a plane root is what
            # it decides — but the source is only half of that predicate. The
            # other half is the family, and `operators.degree_of` is `None` for
            # julia and for phoenix, so a dynamical row comes through this same
            # door and is not graced. That is the right answer rather than an
            # oversight: the grace pays for the descent out of a home frame
            # nobody chose, and a row did not start at one.
            "source": "seed_file",
            "provenance": {
                "seed_id": entry.get("id", f"row{index:04d}"),
                "channel": channel,
                # Named only for a row that actually came out of one: a proven
                # root is derived, and a file name beside it is a provenance
                # field that reads true and is not.
                "file": (
                    self._seeds.name if self._seeds and channel != proven_channel.CHANNEL else None
                ),
                "refill": True,
            },
        }

    def note_admission(self, partition: str, row: dict) -> None:
        """One location the run just booked, offered to whatever channel it feeds.

        The refill is where a channel's supply arrives, so it is where an
        admission that *is* another partition's supply gets handed over. The
        harvest stays ignorant of which channels exist.
        """
        if self.twins is not None:
            self.twins.note(partition, row)

    def summary(self, loop_seconds: float = 0.0) -> dict:
        return {
            "low_water": self.low_water,
            "cooldown_batches": self.cooldown,
            "share": self.share,
            "draws": self.draws,
            "roots_added": self.roots_added,
            "deferred_draws": self.deferred_draws,
            "seconds": round(self.seconds, 3),
            "share_used": (
                round(self.seconds / (loop_seconds + self.seconds), 4)
                if (loop_seconds + self.seconds) > 0
                else 0.0
            ),
            "remaining": {p: self.remaining(p) for p in self.partitions if self.has_channel(p)},
            "twins": None if self.twins is None else self.twins.summary(),
            "proven": None if self.proven is None else self.proven.summary(),
        }


def _seed_partition(row: dict) -> str | None:
    family = row.get("family")
    return partition_of_family(family) if isinstance(family, dict) else None


__all__ = [
    "COOLDOWN",
    "DEFERRAL",
    "LOW_WATER",
    "EXTERNALLY_SUPPLIED",
    "NO_SEED_FILE",
    "NO_TWIN_CHANNEL",
    "SHARE",
    "Refill",
]
