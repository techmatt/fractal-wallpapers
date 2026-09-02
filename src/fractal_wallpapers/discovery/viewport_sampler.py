"""Fresh roots for a plane with no free parameter: draw viewports, screen them, keep what survives.

Every other root channel in this project hands over a **parameter** and lets the
walk descend from the frame that parameter implies. A pinned plane has no
parameter left to vary — classic phoenix is Ushiki's single point — so the only
thing a fresh root there can differ in is the *frame*, and
[`fractal_wallpapers.discovery.pools.classic_phoenix_pool`] is one row by
construction because inventing a second frame is not something a pool of
parameters can do.

This is what can. It draws viewports over the family's own home view, screens
each one through the gate battery the walk already uses, and hands the survivors
over as roots. A pinned plane's supply stops being `1 + its labelled places` and
becomes as many places as the draw finds.

```text
the family's home box                 boundary.home_box, 90% of the home frame
        │  a jittered grid at each rung: 2^k cells a side at width home/2^k
        ▼
    candidate viewports               seeded, and every one recorded with its cell
        │  engine.screen — interior cap, occupancy floor, flatness
        ▼
    the survivors, in rung order      each a root, naming its seed, rung and scale
```

## Why a ladder of scales rather than a width band

[`fractal_wallpapers.discovery.boundary`] draws a width log-uniformly out of a
band, which is the right shape for measuring a *rarity*. This is not measuring
anything: it is supplying roots, and what a root has to be is spread over the
plane at a scale the walk can descend from. So the ladder is octaves — rung `k`
is a 2^k x 2^k grid of frames at width `home/2^k`, which tiles the home box
exactly at every rung — and a run gets whole coverage at four scales rather than
a cloud of widths concentrated wherever the band was set.

**Rung 0 is the home view and this sampler does not draw it.** It is the one root
the pool already hands over, and a channel that restated it would put the same
frame in the queue twice under two names.

## The jitter, and why a grid at all

A grid alone would put every root at the centre of its cell, which on a plane
with reflection symmetry means drawing the same structure repeatedly at
different scales. A uniform draw alone clumps: sixteen uniform points over a box
leave holes a walk never looks in. Stratified — one point per cell, displaced
inside it by up to [`JITTER`] of a half-cell — is both, and it is seeded, so a
rung is a reproducible set of frames rather than a number of them.

## What screening is for here, and what it is not

A frame that clears all three gates is straddling the boundary: not mostly
interior, not a flat wash, with detail spread across it. That is the whole
admission test, and it is deliberately the *only* one. **The head is not asked.**
Ranking viewports by a score before the walk has seen them would be
gate-and-forget on the channel that is supposed to open the plane — the head's
opinion of a root frame is not evidence about what lies below it, and the crawl
that motivated this sampler measured `P(>=4)` at ~0 across a whole admitted set
whose `P(>=3)` ran to 0.96. Every attempt is recorded with the gate that refused
it, so the yield is readable afterwards and a rung that produces nothing says so.

## It is derived per run and not checkpointed

The queue is a pure function of the seed, the family and the ladder, and the
gates are deterministic, so a resumed session re-derives exactly the list it had
and the refill's cursor still points at the same entry. That costs the screening
pass again on a resume — seconds, against a checkpoint field that would have to
be kept correct forever.

The visible consequence is that a resumed run's ledger carries the draw rows
twice. They are not duplicates of a record: the second session really did screen
the ladder again, and a reader counting attempts per session gets the right
answer. What a reader must not do is sum them across sessions and call it a
yield — the `viewport_sampler` row states the attempts of the session that wrote
it.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import Counter
from pathlib import Path

from fractal_wallpapers import engine
from fractal_wallpapers.discovery import boundary
from fractal_wallpapers.supply.partitions import (
    CLASSIC_PHOENIX,
    PINNED_PLANES,
    is_pinned,
)

#: The schema every row and every record this module writes carries.
SCHEMA = 1

#: What this channel is called wherever a root's provenance is read back. One
#: spelling, registered here, and the walk's root row carries it: a tally by
#: `source` cannot see a channel, which is how a whole channel's yield went
#: unattributable before `provenance.channel` existed.
CHANNEL = "viewport_sampler"

#: What a root drawn here names as its source. Deliberately not `seed_file`: the
#: expansion grace is keyed on that name, and these roots did not start at a home
#: frame nobody chose.
SOURCE = "viewport_sampler"

#: Octaves in from the home width. Four, so the deepest rung is `home/16` — for
#: classic phoenix a width of 0.31, which sits inside the 0.010–0.448 band its
#: labelled places occupy. It is also where the cost is: the ladder is
#: `4 + 16 + 64 + 256 = 340` frames, and a fifth rung alone would be 1,024 more.
RUNGS = 4

#: How far inside its own cell a frame's centre may be displaced, as a fraction
#: of the half-cell. Half, so a draw is stratified rather than either a lattice
#: (every root on a symmetry line) or a uniform cloud (holes at this sample size).
JITTER = 0.5

#: The partitions this channel serves. A parameter plane is structurally out —
#: an unscreened draw over the higher degrees measured zero good locations in 144
#: — and so is a `julia:*` twin, whose fresh supply is a *parameter* its pool or
#: the twin channel hands over. What is left is exactly the planes with nothing
#: to vary but the frame.
SERVED = PINNED_PLANES


class SamplerRefused(RuntimeError):
    """The draw cannot be made as asked."""


def family_of(partition: str) -> dict:
    """The one family a pinned partition is, as a family record.

    Read off the pool rather than spelled here, so the point this samples over
    and the point [`partition_of_family`] resolves against cannot drift — the
    same reason `pools.classic_phoenix_pool` reads the registry's constants.
    """
    from fractal_wallpapers.discovery import pools

    if partition == CLASSIC_PHOENIX:
        return pools.classic_phoenix_pool()[0]["family"]
    raise SamplerRefused(
        f"{partition!r} has no family this sampler knows how to draw over. A pinned plane "
        f"is one family, and the row that says which one belongs beside its pool."
    )


def digest_of(*parts) -> str:
    """A stable digest of a draw's coordinates, identical on every machine.

    `hash` is not: it is salted per process, so an order taken from it would come
    back different on the next run of the same command.
    """
    text = json.dumps(list(parts), ensure_ascii=False, default=str)
    return hashlib.blake2b(text.encode("utf-8"), digest_size=8).hexdigest()


def cells(rung: int) -> int:
    """Frames a side at this rung. Rung `k` tiles the home box with `2^k`."""
    return 2**rung


def draws(family: dict, *, seed: int = 0, rungs: int = RUNGS) -> list[dict]:
    """Every candidate frame of the ladder, in the order they are handed over.

    Deterministic in `(family, seed, rungs)` and in nothing else — no clock, no
    process hash, and no dependence on the order anything is read in — because
    this list is re-derived rather than checkpointed and a resumed run has to get
    the same one back.

    The order is round-robin across the rungs, and inside a rung by a digest of
    the cell. Both halves matter for a short leg: a queue in rung order would
    spend a ten-minute run entirely at the widest scale, and a queue in cell
    order would hand over neighbours together.
    """
    if rungs < 1:
        raise SamplerRefused("a ladder with no rung is not a ladder")
    centre_re, centre_im, half_width, half_height = boundary.home_box(family)
    per_rung: list[list[dict]] = []
    for rung in range(1, int(rungs) + 1):
        side = cells(rung)
        cell_width = 2.0 * half_width / side
        cell_height = 2.0 * half_height / side
        rows = []
        for j in range(side):
            for i in range(side):
                # The jitter is drawn from the cell's own digest rather than from
                # a shared stream, so one rung's frames do not move when another
                # rung's count changes — the ladder is meant to be extendable.
                mark = digest_of(seed, rung, i, j)
                dx = (int(mark[:8], 16) / 0xFFFFFFFF - 0.5) * JITTER * cell_width
                dy = (int(mark[8:16], 16) / 0xFFFFFFFF - 0.5) * JITTER * cell_height
                rows.append(
                    {
                        "id": f"sampler-r{rung}-{i:03d}-{j:03d}",
                        "rung": rung,
                        "cell": [i, j],
                        "scale": repr(cell_width),
                        "center_re": repr(centre_re - half_width + (i + 0.5) * cell_width + dx),
                        "center_im": repr(centre_im - half_height + (j + 0.5) * cell_height + dy),
                        "width": repr(cell_width),
                        "order": mark,
                    }
                )
        rows.sort(key=lambda row: row["order"])
        per_rung.append(rows)

    out: list[dict] = []
    for index in range(max(len(rows) for rows in per_rung)):
        for rows in per_rung:
            if index < len(rows):
                out.append(rows[index])
    return out


def seed_row(family: dict, draw: dict, seed: int) -> dict:
    """One surviving draw as the row a refill can build a root out of.

    A whole *location* — the family with its constants and the frame — because
    that is what a place is, and it names its sampler seed and its scale so the
    root row can say which draw it came out of rather than only which channel.
    """
    return {
        "schema": SCHEMA,
        "id": draw["id"],
        "family": family,
        "viewport": {
            "center_re": draw["center_re"],
            "center_im": draw["center_im"],
            "width": draw["width"],
        },
        "provenance": {
            "channel": CHANNEL,
            "source": SOURCE,
            # Named `None` rather than left out: the refill fills an absent
            # `file` in from the run's seed file, and this row was never in one.
            "file": None,
            "sampler_seed": int(seed),
            "rung": draw["rung"],
            "scale": draw["scale"],
            "cell": draw["cell"],
        },
    }


def sample(
    family: dict,
    *,
    seed: int = 0,
    rungs: int = RUNGS,
    colormap: str = "twilight_shifted",
    node_width: int | None = None,
    ledger=None,
    log=print,
) -> tuple[list[dict], dict]:
    """Draw the ladder, screen every frame, and return `(rows, record)`.

    Screened in batches of [`boundary.BATCH`] for the reason that module states:
    the engine costs a few milliseconds to start and a probe costs a few more, so
    a batch of one would spend a third of the clock on process spawn.

    Every attempt is written to the ledger where there is one — record and rank,
    never gate and forget. A rung that produced nothing is then a rung with a
    reason beside it rather than an absence.
    """
    frames = draws(family, seed=seed, rungs=rungs)
    kept: list[dict] = []
    fates: Counter = Counter()
    by_rung: dict[int, Counter] = {rung: Counter() for rung in range(1, int(rungs) + 1)}
    started = time.monotonic()
    battery: dict = {}
    for start in range(0, len(frames), boundary.BATCH):
        batch = frames[start : start + boundary.BATCH]
        spec: dict = {
            "schema": 1,
            "frames": [
                {
                    "family": family,
                    **{key: row[key] for key in ("center_re", "center_im", "width")},
                }
                for row in batch
            ],
            "colormap": colormap,
            "colormap_dir": str(engine.colormap_dir()),
        }
        if node_width is not None:
            spec["node_width"] = int(node_width)
        report = engine.screen(spec)
        if not battery:
            # The geometry every verdict was read at, taken from the engine that
            # read them rather than restated on this side.
            battery = {
                key: report.get(key)
                for key in ("tile", "field_supersample", "probe_width", "battery")
            }
        for row, screened in zip(batch, report["frames"], strict=True):
            fates[screened["fate"]] += 1
            by_rung[row["rung"]][screened["fate"]] += 1
            if ledger is not None:
                ledger.write(
                    "sampler_draw",
                    channel=CHANNEL,
                    seed_id=row["id"],
                    sampler_seed=int(seed),
                    rung=row["rung"],
                    cell=row["cell"],
                    family=family,
                    viewport={
                        "center_re": screened["center_re"],
                        "center_im": screened["center_im"],
                        "width": screened["width"],
                    },
                    fate=screened["fate"],
                    passed=bool(screened["passed"]),
                    maxiter=screened.get("maxiter"),
                )
            if screened["passed"]:
                kept.append(seed_row(family, row, seed))

    record = {
        "channel": CHANNEL,
        "seed": int(seed),
        "rungs": int(rungs),
        "jitter": JITTER,
        "attempts": len(frames),
        "survivors": len(kept),
        "yield": round(len(kept) / len(frames), 4) if frames else None,
        "fates": dict(sorted(fates.items())),
        "by_rung": {
            str(rung): {
                "attempts": sum(counts.values()),
                "survivors": sum(count for fate, count in counts.items() if fate == "survived"),
                "fates": dict(sorted(counts.items())),
            }
            for rung, counts in sorted(by_rung.items())
        },
        "seconds": round(time.monotonic() - started, 2),
        **battery,
    }
    log(
        f"[sampler] {record['survivors']}/{record['attempts']} viewport(s) cleared the gates "
        f"over {int(rungs)} rung(s) in {record['seconds']}s"
    )
    return kept, record


class ViewportSampler:
    """The sampled roots each pinned partition can still be handed.

    One list per partition, drawn and screened once when the channel is built.
    Fixed for the run's length, unlike the twin channel's: this one does not feed
    on what the run finds, and re-drawing it mid-run would move entries the
    refill's cursor has already passed.
    """

    def __init__(self, seeds: dict[str, list[dict]], *, records: dict | None = None):
        self._seeds = {p: rows for p, rows in seeds.items() if rows}
        self.records = dict(records or {})
        #: The partitions this channel can serve, in registry order. A partition
        #: whose whole ladder was refused is absent rather than empty: the refill
        #: asks this list whether a channel exists at all.
        self.partitions = tuple(p for p in SERVED if p in self._seeds)

    def seeds(self, partition: str) -> list[dict]:
        """The sampled roots for one partition, in the order they are handed over."""
        return self._seeds.get(partition, [])

    def pool(self, partition: str, other: list) -> list:
        """This partition's queue with the sampled roots interleaved through `other`.

        One sampled root per entry of whatever the partition already had, which
        on a pinned plane is the single home-view row. Interleaved rather than
        appended for the same reason the proven channel is: neither channel can
        be crowded out by the other, and the home view is one row against
        hundreds, so the order is what decides whether it is ever drawn.
        """
        from fractal_wallpapers.supply.proven import interleave

        return interleave(self.seeds(partition), list(other), ratio=1)

    def starvation(self, partition: str, drawn: int = 0) -> str:
        """Why this partition has nothing left to hand over, in one sentence."""
        record = self.records.get(partition) or {}
        have = len(self.seeds(partition))
        if have and drawn >= have:
            return (
                f"the viewport sampler is exhausted: all {have} screened viewport(s) of its "
                f"{record.get('rungs', RUNGS)}-rung ladder have been handed over and walked. "
                f"A longer leg wants more rungs or a denser draw, which is `--sampler-rungs`."
            )
        return (
            f"the viewport sampler drew {record.get('attempts', 0)} viewport(s) over this "
            f"plane and the structural gates refused every one ({record.get('fates')}). That "
            f"is a fact about the plane at these scales, not a fault: the gates are the "
            f"walk's own."
        )

    def summary(self) -> dict:
        return {
            "channel": CHANNEL,
            "seeds": {p: len(self._seeds[p]) for p in self.partitions},
            "draws": {p: record for p, record in sorted(self.records.items())},
        }


def build(
    *,
    partitions=SERVED,
    seed: int = 0,
    rungs: int = RUNGS,
    colormap: str = "twilight_shifted",
    node_width: int | None = None,
    ledger=None,
    log=print,
) -> ViewportSampler:
    """The channel a harvest holds, drawn and screened once.

    `partitions` may be a run's whole partition list; what this channel serves is
    that list's intersection with [`SERVED`], so a run naming one partition gets
    the channel for that one and not for every pinned plane in the registry.
    """
    served = [p for p in partitions if is_pinned(p)]
    seeds: dict[str, list[dict]] = {}
    records: dict[str, dict] = {}
    for partition in served:
        rows, record = sample(
            family_of(partition),
            seed=seed,
            rungs=rungs,
            colormap=colormap,
            node_width=node_width,
            ledger=ledger,
            log=log,
        )
        seeds[partition] = rows
        records[partition] = record
        if ledger is not None:
            ledger.write("viewport_sampler", partition=partition, **record)
    return ViewportSampler(seeds, records=records)


def write(rows: list[dict], path: Path) -> Path:
    """Emit a drawn set as a seed file's exact bytes, so it can be read or diffed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )
    return path


__all__ = [
    "CHANNEL",
    "JITTER",
    "RUNGS",
    "SCHEMA",
    "SERVED",
    "SOURCE",
    "SamplerRefused",
    "ViewportSampler",
    "build",
    "cells",
    "digest_of",
    "draws",
    "family_of",
    "sample",
    "seed_row",
    "write",
]
