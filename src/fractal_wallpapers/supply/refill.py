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
from fractal_wallpapers.supply.partitions import ALL_PARTITIONS, partition_of_family

#: A partition below this many frontier nodes is starved.
LOW_WATER = 8

#: Batches a partition waits between refills.
COOLDOWN = 10

#: Refill seconds may not exceed this share of the loop's wall clock.
SHARE = 0.25

#: Why a starved partition gets no refill, by partition.
DEFERRAL = {
    "julia:multibrot3": "no tracked pool of degree-3 Julia parameters; fed by reframing only",
    "julia:multibrot4": "no tracked pool of degree-4 Julia parameters; fed by reframing only",
    "julia:multibrot5": "no tracked pool of degree-5 Julia parameters; fed by reframing only",
}

#: Why a parameter-plane partition gets no refill when it has no pool to draw on.
NO_SEED_FILE = (
    "the parameter planes have no sampler: an unscreened draw over the higher degrees "
    "measured zero good locations in 144, so roots come from the tracked plane seed pool, "
    "an explicit --seeds file, or what the reframing operators reach. This run has none of "
    "the three — derive the pool with `fractal-wallpapers derive-plane-seeds --write`."
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
        external=(),
        partitions=ALL_PARTITIONS,
    ):
        self.walk = walk
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
        self._channels: dict = {
            "julia:mandelbrot": ("julia_c_pool", None),
            "phoenix": ("phoenix_seed_pool", None),
        }
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
        """The entries this partition's channel can still hand over."""
        if partition in self._pools:
            return self._pools[partition]
        if partition == "julia:mandelbrot":
            rows = pools.julia_pool()
        elif partition == "phoenix":
            rows = pools.phoenix_pool()
        elif self._seeds is not None:
            rows = [row for row in self._seed_rows() if _seed_partition(row) == partition]
        else:
            rows = []
        self._pools[partition] = rows
        return rows

    def has_channel(self, partition: str) -> bool:
        """Whether any draw could serve this partition at all."""
        if partition in self.external or partition in DEFERRAL:
            return False
        if partition in ("julia:mandelbrot", "phoenix"):
            return True
        return self._seeds is not None and partition != "phoenix:classic"

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
            elif not self.has_channel(partition):
                reason = NO_SEED_FILE
            else:
                reason = "the channel's pool is exhausted: every entry has been walked"
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
            if partition == "julia:mandelbrot":
                self.walk.add_root(
                    entry.family(2),
                    source="julia_c_pool",
                    provenance={"seed_id": entry.id, "channel": entry.channel, "refill": True},
                )
            elif partition == "phoenix":
                self.walk.add_root(
                    entry.family(),
                    source="phoenix_seed_pool",
                    provenance={"seed_id": entry.id, "branch": entry.branch, "refill": True},
                )
            else:
                view = entry.get("viewport")
                self.walk.add_root(
                    entry["family"],
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
                    provenance={
                        "seed_id": entry.get("id", f"row{index:04d}"),
                        "file": self._seeds.name if self._seeds else None,
                        "refill": True,
                    },
                )
        return len(taken)

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
        }


def _seed_partition(row: dict) -> str | None:
    family = row.get("family")
    return partition_of_family(family) if isinstance(family, dict) else None


__all__ = ["COOLDOWN", "DEFERRAL", "LOW_WATER", "NO_SEED_FILE", "SHARE", "Refill"]
