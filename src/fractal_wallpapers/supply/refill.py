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

**A Julia twin's pool is manufactured, not shipped.** The higher-degree twins have
no tracked `c`-pool, and used to be deferred forever with "fed by reframing only"
— which reached them never, because a reframing operator is undefined on a
dynamical viewport. Their channel is [`fractal_wallpapers.supply.twins`]: an
admitted location of the degree-`d` parameter plane *is* a `c` for the degree-`d`
Julia family, so serving the parent manufactures the twin's supply. It hands over
the same seed object the tracked pool does, through the same cursor and the same
low-water mark; the only difference is that its list grows during the run.

**The degree-2 twin draws from both, and its queue is where they meet.** It has a
tracked `c`-pool *and* a parent plane, and the channel was kept off it until
2026-09-12 because [`Refill._twin_queue`] did not exist and this class read its
twin branch first — so serving the twin would have handed over the derived list in
place of the pool. A queue that holds both is what made lifting it safe, and the
c-spacing floor that keeps the two apart is the twin channel's, with the pool's
own parameters reserved into it.

**A plane gets fresh places from a sampler over its own view.** A pool hands
over a parameter and a pinned plane has none left to vary, so its fresh supply
used to be one home-view row and could never be a second; a parameter plane's
nucleus pool is five hundred rows and a long leg walks it out.
[`fractal_wallpapers.discovery.viewport_sampler`] is the channel that makes
places, every frame screened by the walk's own gate battery before it becomes a
root: a fixed ladder of jittered tilings on the pinned plane, and on a parameter
plane a boundary-refining draw whose list **grows on demand and does not run
out** — see [`Refill._continuous_queue`] for what that asks of the cursor. Like
the proven channel it is off unless a run asks for it by name.

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

**Every registered partition is either served or deferred with a reason.** There
is no third state. `phoenix:classic` was one until 2026-09-02 — refused a channel
first and unconditionally, on the ground that a leg outside the walk filled it —
and because that refusal also took it out of the starvation census, its being
empty everywhere downstream went unreported for the life of the project. A
partition nothing can feed is starved and says so.
"""

from __future__ import annotations

import time
from pathlib import Path

from fractal_wallpapers.discovery import pools
from fractal_wallpapers.supply import proven as proven_channel
from fractal_wallpapers.supply import twins
from fractal_wallpapers.supply.partitions import (
    ALL_PARTITIONS,
    CLASSIC_PHOENIX,
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
    "roots on a parameter plane come from the tracked plane seed pool, an explicit --seeds "
    "file, the proven channel, the viewport sampler, or what the reframing operators "
    "reach. This run has none of them — derive the pool with `fractal-wallpapers "
    "derive-plane-seeds --write`, or add `--root-channel viewport_sampler`."
)


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
        partitions=ALL_PARTITIONS,
        twins=None,
        proven=None,
        sampler=None,
    ):
        self.walk = walk
        self.twins = twins
        self.proven = proven
        self.sampler = sampler
        self.low_water = int(low_water)
        self.cooldown = int(cooldown)
        self.share = float(share)
        self.per_draw = int(per_draw if per_draw is not None else low_water)
        self.partitions = list(partitions)
        self.seconds = 0.0
        self.draws = 0
        self.roots_added = 0
        self.deferred_draws = 0
        self.last_refill: dict = {}
        self.cursor: dict = {}
        self._pools: dict = {}
        #: How much of a twin's derived list is already in its built queue. A twin
        #: queue is the one thing here that grows after it is built, and this is
        #: what says where it grew to — see [`_twin_queue`].
        self._twin_mark: dict = {}
        #: A continuous partition's merge state — see [`_continuous_queue`].
        self._streams: dict = {}
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
        # A twin's queue is the one that grows after it is built, because serving
        # the parent plane is what fills it. It is extended rather than re-made —
        # see [`_twin_queue`], which carries what re-making it cost.
        if self._is_twin(partition):
            return self._with_proven(partition, self._twin_queue(partition))
        if self._is_continuous(partition):
            return self._continuous_queue(partition, need=0)
        if partition in self._pools:
            return self._pools[partition]
        if partition == "julia:mandelbrot":
            rows = pools.julia_pool()
        elif partition == "phoenix":
            rows = pools.phoenix_pool()
        elif partition == CLASSIC_PHOENIX:
            rows = pools.classic_phoenix_pool()
            rows = self._with_sampler(partition, rows)
        else:
            rows = (
                [row for row in self._seed_rows() if _seed_partition(row) == partition]
                if self._seeds is not None
                else []
            )
        rows = self._with_proven(partition, rows)
        self._pools[partition] = rows
        return rows

    def _continuous_queue(self, partition: str, need: int) -> list:
        """A parameter plane's queue when the viewport sampler serves it, grown to `need`.

        **Merged at the tail and never re-interleaved**, for the reason
        [`_twin_queue`] carries: the cursor is an index, and an interleave is not
        stable under a side that grows. The finite side — the plane's pool with its
        proven roots already interleaved through it — is fixed at the first call,
        and the sampler's side is an unbounded list that screens more only when
        asked. So the queue is materialized one pair at a time, a sampled survivor
        and then the next finite entry, which is the order the pinned plane's
        interleave puts them in; once the finite side runs out every further entry
        is sampled, and **that is the point**: a plane whose nucleus pool is walked
        out keeps being served.

        `need` of zero builds nothing past what is already there, so asking how
        big the queue is at launch never pays for a refinement.
        """
        state = self._streams.get(partition)
        if state is None:
            other = [
                row
                for row in (self._seed_rows() if self._seeds is not None else [])
                if _seed_partition(row) == partition
            ]
            state = {"queue": [], "other": self._with_proven(partition, other), "given": 0}
            self._streams[partition] = state
            self._pools[partition] = state["queue"]
        queue = state["queue"]
        while len(queue) < need:
            before = len(queue)
            sampled = self.sampler.take(partition, len(queue) - state["given"])
            if sampled is not None:
                queue.append(sampled)
            if state["given"] < len(state["other"]):
                queue.append(state["other"][state["given"]])
                state["given"] += 1
            if len(queue) == before:
                break
        return queue

    def _twin_queue(self, partition: str) -> list:
        """A twin's queue: its tracked `c`-pool, if it has one, its derived list, and
        its proven roots — **built once and extended, never re-interleaved.**

        **Interleaved and not substituted, which is the whole of what the degree-2
        exclusion protected.** This branch is read before the `julia:mandelbrot`
        one below it, so a served degree-2 twin used to get the derived list
        *instead of* the pool's 209 rows — and "a derived parameter must not
        displace the tracked pool" was exactly true, as a fact about this method
        rather than about the coarseness of a parameter-plane centre.

        The pool goes in 1:1 rather than at the proven channel's 2:1. The two
        sides are one pool of a couple of hundred and a derived list that grows
        all run, so the ratio decides how deep a leg must draw to reach the pool's
        back half — where this project's only virgin dynamical roots sit — and
        one-for-one adds a leg's worth of derived parameters without doubling it.

        **Built once because an interleave is not stable under a growing side, and
        the cursor is an index.** `interleave` was documented as only ever
        appending when its second argument grew; it does, until that argument runs
        out before the first one, and a twin's few derived parameters always run
        out before a partition's hundreds of proven roots. Re-interleaving one
        more parameter then moved every entry past that point down a slot: under a
        cursor at 6 the entry at 5 had been handed over and the new parameter took
        its index, so the run walked one root twice and never walked the new one at
        all. Any run with both a twin channel and `--root-channel proven` was doing
        this before 2026-09-12. Growing the built list is what the cursor's
        semantics actually ask for, and it puts a parameter derived mid-run at the
        tail — which is where it belongs, since it did not exist when the entries
        ahead of it were handed out.
        """
        built = self._pools.get(partition)
        seeds = self.twins.seeds(partition)
        if built is None:
            pool = list(twins.tracked_pool(partition))
            rows = list(seeds)
            if pool:
                rows = proven_channel.interleave(pool, rows, ratio=1)
            built = self._with_proven(partition, rows)
            self._pools[partition] = built
            self._twin_mark[partition] = len(seeds)
            return built
        if len(seeds) > self._twin_mark[partition]:
            built.extend(seeds[self._twin_mark[partition] :])
            self._twin_mark[partition] = len(seeds)
        return built

    def _with_proven(self, partition: str, rows: list) -> list:
        """`rows` with this partition's proven roots interleaved through them.

        Interleaved rather than prepended: the proven channel feeds on this
        project's own past output, so a queue that spent itself on proven roots
        first would reach new ground only after it ran out.
        """
        if not self._is_proven(partition):
            return rows
        return self.proven.pool(partition, rows)

    def _with_sampler(self, partition: str, rows: list) -> list:
        """`rows` with this partition's sampled viewports interleaved through them.

        Before the proven interleave rather than after, so the three channels
        reach the queue in the order they can open ground: the pool's one home
        view, the sampler's fresh places, then the label store's proven ones. A
        pinned plane's pool is a single row, so appending instead of interleaving
        would decide by accident whether the home view is ever drawn.
        """
        if not self._is_sampler(partition):
            return rows
        return self.sampler.pool(partition, rows)

    def _is_sampler(self, partition: str) -> bool:
        """Whether the viewport sampler holds roots for this partition.

        It serves every parameter plane and the pinned plane. A Julia twin is the
        one kind it leaves out: its fresh supply is a parameter, which its pool
        or the twin channel hands over.
        """
        return self.sampler is not None and partition in self.sampler.partitions

    def _is_continuous(self, partition: str) -> bool:
        """Whether this partition's sampler list grows on demand — a parameter plane's."""
        return self._is_sampler(partition) and self.sampler.continuous(partition)

    def _open(self, partition: str) -> bool:
        """Whether a draw here could still hand something over.

        A continuous channel counts as open until it says it is exhausted, whatever
        is materialized: its queue is built only as far as a draw asks, so
        `remaining` reads zero on a channel with tens of thousands of cells left.
        """
        if self.remaining(partition) > 0:
            return True
        return self._is_continuous(partition) and not self.sampler.exhausted(partition)

    def _is_twin(self, partition: str) -> bool:
        """Whether the twin channel is one of this partition's channels.

        One of, since 2026-09-12, and not the only one: the channel serves the
        degree-2 twin as well now, and that twin also has a tracked `c`-pool a
        three-stage screen produced. What kept the two apart was that this class
        read the twin branch first and handed over the derived list *instead of*
        the pool — see [`_twin_queue`], which is where the two became one queue.
        """
        return self.twins is not None and partition in self.twins.partitions

    def _is_proven(self, partition: str) -> bool:
        """Whether the proven channel holds roots for this partition.

        It serves every registered partition — `phoenix:classic` included, since
        2026-09-02 — so on the dynamical side it shares a queue with a `c`-pool
        rather than standing in for a missing sampler. It does not compete with
        one: a pool row is a
        parameter and starts at the home view, a proven row is a whole place,
        and the interleave is what keeps either from crowding the other out.
        """
        return self.proven is not None and partition in self.proven.partitions

    def has_channel(self, partition: str) -> bool:
        """Whether any draw could serve this partition at all.

        The three partitions named outright are the ones with a pool of their own
        in this repository. `phoenix:classic` is one of them: its pool is a single
        row by construction, because the plane is one pinned parameter point and
        the only thing a fresh root there can vary is the frame.
        """
        if partition in DEFERRAL:
            return False
        if partition in ("julia:mandelbrot", "phoenix", CLASSIC_PHOENIX):
            return True
        if is_dynamical(partition):
            return self._is_twin(partition) or self._is_proven(partition)
        return self._seeds is not None or self._is_proven(partition) or self._is_sampler(partition)

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
            if not self._open(partition):
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

        `pool` is the whole interleaved queue, `proven` is how much of it came
        from the label store and `sampled` how much of it the viewport sampler
        drew. All three, because on a partition fed by several channels "entries
        left" alone cannot say what is left: a dynamical queue that has run out
        of `c`, one that has run out of labelled places and a pinned plane that
        has walked out its ladder exhaust in different ways and are fixed by
        different things.
        """
        empty = dict.fromkeys(self.partitions, 0)
        reasons = self.deferred(empty)
        out = {}
        for partition in self.partitions:
            servable = self.has_channel(partition)
            pool = len(self._pool(partition)) if servable else 0
            continuous = self._is_continuous(partition)
            if continuous:
                # What the finite side still holds that the queue has not merged,
                # so a plane's pool reads as its pool at launch rather than as 0.
                state = self._streams[partition]
                pool += len(state["other"]) - state["given"]
            drawn = self.cursor.get(partition, 0)
            reason = (reasons.get(partition) or {}).get("reason")
            out[partition] = {
                "channel": servable,
                "pool": pool,
                "proven": len(self.proven.seeds(partition)) if self._is_proven(partition) else 0,
                "sampled": (
                    len(self.sampler.seeds(partition)) if self._is_sampler(partition) else 0
                ),
                "continuous": continuous,
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
                if state["sampled"]:
                    line += f", {state['sampled']} of them sampled viewports"
                if state["continuous"]:
                    line += ", and the viewport sampler's boundary draw behind them, unbounded"
                out.append(line)
            else:
                out.append(f"pool {partition}: {state['reason']}")
        return out

    def deferred(self, queues: dict) -> dict:
        """Partitions below the low-water that no draw will be made for, each with
        the reason. Every registered partition can appear here."""
        out = {}
        for partition in self.partitions:
            if queues.get(partition, 0) >= self.low_water:
                continue
            if self.has_channel(partition) and self._open(partition):
                continue
            if partition in DEFERRAL:
                reason = DEFERRAL[partition]
            elif self._is_twin(partition):
                reason = self.twins.starvation(partition, drawn=self.cursor.get(partition, 0))
            elif self._is_sampler(partition):
                reason = self.sampler.starvation(partition, drawn=self.cursor.get(partition, 0))
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
        start = self.cursor.get(partition, 0)
        rows = (
            self._continuous_queue(partition, need=start + self.per_draw)
            if self._is_continuous(partition)
            else self._pool(partition)
        )
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
        if (
            isinstance(entry, pools.JuliaSeed)
            and self._is_twin(partition)
            # **On the seed and not on the partition.** A pooled twin's queue holds
            # both kinds of `JuliaSeed` — its tracked pool's and this channel's —
            # so a branch that asked which partition it was would call every
            # degree-2 pool row a derived parameter, and the run record would
            # credit the twin channel with what a three-stage screen found.
            and entry.channel.startswith(twins.SEED_CHANNEL)
        ):
            # The same seed object and the same call the degree-2 pool makes, at
            # the degree its parent plane carries. That is what keeps this one
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
        """A `{family, viewport}` row as a root: a seed file's, the proven channel's,
        or the viewport sampler's.

        The one door a root enters at a *place* rather than at a home view, which
        is what the proven channel is worth on a dynamical partition and what the
        sampler is worth on a pinned one: a `c`-pool can express a parameter and
        nothing else, and a pinned plane has no parameter to express.
        """
        view = entry.get("viewport")
        # The row's own channel, carried onto the root. A queue can hold three
        # channels at once, and attributing a find afterwards should be a join on
        # a field rather than a guess at an id prefix.
        provenance = entry.get("provenance") or {}
        channel = provenance.get("channel")
        # Whatever else the channel knew about this row travels with it: the
        # proven channel's tier and label batch, the sampler's seed, rung and
        # scale. The four fields below are computed here and win, so a channel
        # cannot overwrite the root's own identity by naming one of them.
        carried = {
            key: value
            for key, value in provenance.items()
            if key not in ("seed_id", "channel", "file", "refill", "source")
        }
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
            # oversight, and **the reason is the head's reading of a dynamical
            # home view, not this row's framing**: a Julia set's material is at
            # its home view, so nothing here starts above its own depths. The
            # measurement is in [`fractal_wallpapers.discovery.walk`]'s *A
            # parameter-plane root starts above the depths its material lives
            # at*, which carries julia's rung-1 admission share against the
            # plane's 1.2% frontier rate.
            #
            # It is **not** that a row starts at a place rather than a home
            # frame. A proven *plane* row starts at a labelled place too, comes
            # through this same default, and is graced — so that argument would
            # prove the wrong thing about the parameter planes, and it stood here
            # until `FIX_ckpt123_dynamical_expansion_grace` measured the grace.
            # A row may name its own, and one that does not came out of the seed
            # file. The passthrough is what lets a *synthesized* row — the pinned
            # plane's single home view — say where it came from instead of
            # inheriting a pool file it was never in.
            "source": provenance.get("source", "seed_file"),
            "provenance": {
                **carried,
                "seed_id": entry.get("id", f"row{index:04d}"),
                "channel": channel,
                # Named only for a row that actually came out of one: a proven
                # root is derived, and a file name beside it is a provenance
                # field that reads true and is not.
                "file": provenance.get(
                    "file",
                    self._seeds.name if self._seeds and channel != proven_channel.CHANNEL else None,
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
            "sampler": None if self.sampler is None else self.sampler.summary(),
        }


def _seed_partition(row: dict) -> str | None:
    family = row.get("family")
    return partition_of_family(family) if isinstance(family, dict) else None


__all__ = [
    "COOLDOWN",
    "DEFERRAL",
    "LOW_WATER",
    "NO_SEED_FILE",
    "NO_TWIN_CHANNEL",
    "SHARE",
    "Refill",
]
