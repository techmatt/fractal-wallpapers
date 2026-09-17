"""Fresh roots drawn over a plane's own view: draw viewports, screen them, keep what survives.

Every other root channel in this project hands over something that already
exists — a pool row, a labelled place, a parameter an admission implied — and so
every one of them runs out. This one makes places. It draws viewports over the
family's home view, screens each through the gate battery the walk already uses,
and hands the survivors over as roots.

It serves two kinds of plane with two draw schemes, chosen by partition kind:

```text
                         the family's home box (boundary.home_box, 90% of the home frame)
                                   │
            ┌──────────────────────┴───────────────────────┐
   a PINNED plane (phoenix:classic)              a PARAMETER plane (mandelbrot, multibrot3..5)
   the fixed ladder: rung k is a                 straddle refinement: a quad-tree refined
   2^k x 2^k jittered tiling, k = 1..RUNGS       only where the connectedness locus's
   340 frames, screened at build                 boundary is, one rung at a time, lazily
            │                                              │
            └───────── engine.screen: interior cap, occupancy floor, flatness ─────────┘
                                   │
                    the survivors, round-robin over rungs, each a root
```

## The pinned plane's ladder

Classic phoenix is Ushiki's single point: nothing to vary but the frame, and
[`fractal_wallpapers.discovery.pools.classic_phoenix_pool`] is one row by
construction. Its plane has no connectedness locus to find a boundary of — a
dynamical plane's interior is scattered basins, not one set — so it keeps the
scheme it shipped with: rung `k` is a `2^k x 2^k` grid of frames at width
`home/2^k`, which tiles the home box exactly at every rung, four rungs deep.
**Rung 0 is the home view and is not drawn**; the pool already hands it over.

## A parameter plane's straddle refinement

A fixed tiling over a parameter plane spends almost all of its frames in the
exterior or deep in a bulb, and it ends: 340 frames is a few dozen roots, and the
plane's structure lives three and four octaves below the widest rung. The
refinement spends its probes where the boundary is instead.

A cell at rung `r` is one cell of the same tiling. A **parent is probed once**
with `engine.dump_field` at [`PROBE_RESOLUTION`], a grid chosen so each of its
four children is an exact sub-block, and a child **straddles** if its block holds
both interior (`NaN`) and escaped samples. Only straddling children are refined
further. Every straddling cell inside the width band is a candidate draw, framed
at the cell and jittered by the run's digest exactly as the ladder is, and goes
through the same `engine.screen` battery and the same `sampler_draw` ledger row.

**A rung is refined when the cursor reaches it, a chunk of parents at a time.**
Refined whole — every straddling parent probed before a rung hands over its
first draw — the first pilot paid 645.6 s to reach rung 12 on multibrot3, whose
133,465 straddling cells a night would never draw. So a rung grows by
[`CHUNK`] parents taken in the rung above's own served order, and the children
of a chunk are handed over in digest order. Each chunk's parents are themselves
a digest-ordered spread over the boundary, so a chunk is not bunched under one
parent, and the rung above grows only when a chunk needs parents it has not
found yet. The order is by digest within a chunk rather than within a whole
rung, and that is the one thing given up for it.

**Why the band, and what "cannot exhaust" means.** The band's ends come from
[`fractal_wallpapers.discovery.boundary`]'s width band, read as the width a
**root** stands at — a draw enters the walk at `walk.ROOT_DEPTH`, and the walk
descends from there — and both ends are flags. Inside it the straddling cells of
the narrowest rung number in the tens of thousands on every plane, so a channel
drawing a few hundred roots a night does not reach the end of any rung; one that
does says so, and the fix is a narrower `--sampler-narrowest`.

## What screening is for here, and what it is not

A frame that clears all three gates is straddling the boundary: not mostly
interior, not a flat wash, with detail spread across it. That is the whole
admission test, and it is deliberately the *only* one. **The head is not asked.**
Ranking viewports by a score before the walk has seen them would be
gate-and-forget on the channel that is supposed to open the plane — the head's
opinion of a root frame is not evidence about what lies below it. Every attempt
is recorded with the gate that refused it, so the yield is readable afterwards
and a rung that produces nothing says so.

The straddle test is **not** a second gate. It decides where the probes go and
nothing else; a straddling cell the battery refuses is refused, and a cell the
probe called one-sided is simply never drawn.

## It is derived per run and not checkpointed

The queue is a pure function of the seed, the family and the scheme's
parameters, and the probes and the gates are deterministic, so a resumed session
re-derives exactly the list it had and the refill's cursor still points at the
same entry. That costs the refinement and the screening again on a resume,
against a checkpoint field that would have to be kept correct forever.

The visible consequence is that a resumed run's ledger carries the draw rows
twice. They are not duplicates of a record: the second session really did screen
them again, and a reader counting attempts per session gets the right answer.
What a reader must not do is sum them across sessions and call it a yield.
"""

from __future__ import annotations

import array
import hashlib
import json
import math
import sys
import tempfile
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fractal_wallpapers import engine
from fractal_wallpapers.discovery import boundary
from fractal_wallpapers.supply.partitions import (
    CLASSIC_PHOENIX,
    PARAMETER_PLANES,
    PINNED_PLANES,
    degree_of_plane,
)

#: The schema every row and every record this module writes carries.
SCHEMA = 1

#: What this channel is called wherever a root's provenance is read back. One
#: spelling, registered here, and the walk's root row carries it: a tally by
#: `source` cannot see a channel, which is how a whole channel's yield went
#: unattributable before `provenance.channel` existed.
CHANNEL = "viewport_sampler"

#: What a root drawn here names as its source. Its own name rather than `seed_file`,
#: so a tally by source can tell the channels apart; the walk's expansion grace
#: names both in `walk.PLANE_ROOT_SOURCES`, since a straddle draw stands at the pool's
#: widths and pays the same floor from its first rung.
SOURCE = "viewport_sampler"

#: The two draw schemes, as a root's provenance names them.
LADDER = "ladder"
STRADDLE = "straddle"

#: Octaves in from the home width, for the pinned plane's ladder. Four, so the
#: deepest rung is `home/16` — for classic phoenix a width of 0.31, which sits
#: inside the 0.010–0.448 band its labelled places occupy. It is also where the
#: cost is: the ladder is `4 + 16 + 64 + 256 = 340` frames, and a fifth rung alone
#: would be 1,024 more.
RUNGS = 4

#: How far inside its own cell a frame's centre may be displaced, as a fraction
#: of the half-cell. Half, so a draw is stratified rather than either a lattice
#: (every root on a symmetry line) or a uniform cloud (holes at this sample size).
#: Both schemes use it.
JITTER = 0.5

#: The widest root a parameter plane's refinement hands over: `boundary`'s upper
#: width, read as a root width.
WIDEST = boundary.WIDTH_HIGH

#: The narrowest: `boundary`'s lower width, for the same reason.
NARROWEST = boundary.WIDTH_LOW

#: The grid one parent is probed at, `[width, height]`, so each child is an exact
#: 32 x 18 sub-block. **Not the smallest 16:9 grid that splits, and the pilot is
#: why**: at 32 x 18 a child is 16 x 9 samples, which misses the thin filament an
#: exterior child hangs on, and it dropped 13 of the 176 children the screen passed
#: against 2 here — for the same 6.25 ms a probe, because a probe this small is
#: the engine's process start and not its iteration. `discovery/README.md`'s *The
#: straddle probe* has the whole reading.
PROBE_RESOLUTION = (64, 36)

#: Iterations per probe sample: the cheapest that agrees with the screen's
#: `interior_cap` verdict on the children (99.2% at 256; 95.2% at 64, which calls
#: slow escapers interior). `None` would hand it to the engine's width policy,
#: which is what the screen reads at, and costs 11.85 ms a probe for no survivor.
PROBE_MAXITER: int | None = 256

#: Parents probed per growth of a rung. A rung is grown lazily, a chunk at a time,
#: because the first pilot refined whole rungs and paid **72,800 probes and 645.6 s**
#: to list multibrot3 down to rung 12 before its first root — 133,465 cells at
#: rung 12, against a leg that wanted 40.
#:
#: **The chunk is the trade between that cost and the spread**, and 256 is the
#: knee of it. Over multibrot3's first 128 candidates, read as how many distinct
#: rung-6 cells (width 0.073) they descend from: whole rungs 105 at 645.6 s, 1,024
#: parents 97 at 38.1 s, **256 parents 85 at 15.4 s**, 64 parents 41 at 3.2 s —
#: and at rung 4 the three larger settings all reach 41–43 of the same ancestors.
#: A small chunk narrows because a deep rung's first chunk descends from the rung
#: above's first chunk, and so on up.
CHUNK = 256

#: Probes running at once. The render pool is three workers on this machine, and
#: a refinement is a render leg in miniature.
PROBE_WORKERS = 3

#: The partitions this channel serves: every parameter plane, and the pinned
#: plane. A `julia:*` twin is the one kind left out — its fresh supply is a
#: *parameter*, which its pool or the twin channel hands over, and a frame drawn
#: over one `c`'s Julia set is a place on a fractal nobody chose.
SERVED = (*PARAMETER_PLANES, *PINNED_PLANES)


class SamplerRefused(RuntimeError):
    """The draw cannot be made as asked."""


def scheme_of(partition: str) -> str:
    """Which of the two draw schemes serves this partition."""
    if partition in PARAMETER_PLANES:
        return STRADDLE
    if partition in PINNED_PLANES:
        return LADDER
    raise SamplerRefused(
        f"{partition!r} is not a plane this sampler draws over. It serves the parameter "
        f"planes and the pinned plane; a Julia twin's fresh supply is a parameter."
    )


def family_of(partition: str) -> dict:
    """The one family a served partition is, as a family record.

    The pinned plane's is read off its pool rather than spelled here, so the
    point this samples over and the point `partition_of_family` resolves against
    cannot drift. A parameter plane is its degree and nothing else.
    """
    if partition == CLASSIC_PHOENIX:
        from fractal_wallpapers.discovery import pools

        return pools.classic_phoenix_pool()[0]["family"]
    if partition in PARAMETER_PLANES:
        degree = degree_of_plane(partition)
        return {"kind": "mandelbrot"} if degree == 2 else {"kind": "multibrot", "degree": degree}
    raise SamplerRefused(
        f"{partition!r} has no family this sampler knows how to draw over. It serves "
        f"{list(SERVED)}."
    )


def digest_of(*parts) -> str:
    """A stable digest of a draw's coordinates, identical on every machine.

    `hash` is not: it is salted per process, so an order taken from it would come
    back different on the next run of the same command.
    """
    text = json.dumps(list(parts), ensure_ascii=False, default=str)
    return hashlib.blake2b(text.encode("utf-8"), digest_size=8).hexdigest()


def cells(rung: int) -> int:
    """Cells a side at this rung. Rung `k` tiles the home box with `2^k`."""
    return 2**rung


def frame_of(box: tuple, rung: int, i: int, j: int, seed: int) -> dict:
    """Cell `(i, j)` of rung `rung` as a draw: jittered centre, cell width, digest order.

    `j` counts up from the box's lower edge. The jitter is drawn from the cell's
    own digest rather than from a shared stream, so one rung's frames do not move
    when another rung's count changes.
    """
    centre_re, centre_im, half_width, half_height = box
    side = cells(rung)
    cell_width = 2.0 * half_width / side
    cell_height = 2.0 * half_height / side
    mark = digest_of(seed, rung, i, j)
    dx = (int(mark[:8], 16) / 0xFFFFFFFF - 0.5) * JITTER * cell_width
    dy = (int(mark[8:16], 16) / 0xFFFFFFFF - 0.5) * JITTER * cell_height
    return {
        "id": f"sampler-r{rung}-{i:03d}-{j:03d}",
        "rung": rung,
        "cell": [i, j],
        "scale": repr(cell_width),
        "center_re": repr(centre_re - half_width + (i + 0.5) * cell_width + dx),
        "center_im": repr(centre_im - half_height + (j + 0.5) * cell_height + dy),
        "width": repr(cell_width),
        "order": mark,
    }


def draws(family: dict, *, seed: int = 0, rungs: int = RUNGS) -> list[dict]:
    """Every candidate frame of the pinned plane's ladder, in the order handed over.

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
    box = boundary.home_box(family)
    per_rung: list[list[dict]] = []
    for rung in range(1, int(rungs) + 1):
        side = cells(rung)
        rows = [frame_of(box, rung, i, j, seed) for j in range(side) for i in range(side)]
        rows.sort(key=lambda row: row["order"])
        per_rung.append(rows)
    return round_robin(per_rung)


def round_robin(per_rung: list[list[dict]]) -> list[dict]:
    """One entry from each rung in turn, a rung dropping out when it runs dry."""
    out: list[dict] = []
    for index in range(max((len(rows) for rows in per_rung), default=0)):
        for rows in per_rung:
            if index < len(rows):
                out.append(rows[index])
    return out


def seed_row(family: dict, draw: dict, seed: int, scheme: str = LADDER) -> dict:
    """One surviving draw as the row a refill can build a root out of.

    A whole *location* — the family with its constants and the frame — because
    that is what a place is, and it names its sampler seed, its scheme and its
    scale so the root row can say which draw it came out of rather than only
    which channel.
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
            "scheme": scheme,
            "rung": draw["rung"],
            "scale": draw["scale"],
            "cell": draw["cell"],
        },
    }


def screen_batch(
    family: dict,
    batch: list[dict],
    *,
    seed: int,
    scheme: str,
    colormap: str,
    node_width: int | None,
    ledger,
) -> tuple[list[tuple[dict, dict]], dict]:
    """Screen one batch of draws; `([(draw, screened), ...], geometry)`.

    Every attempt is written to the ledger where there is one — record and rank,
    never gate and forget.
    """
    spec: dict = {
        "schema": 1,
        "frames": [
            {"family": family, **{key: row[key] for key in ("center_re", "center_im", "width")}}
            for row in batch
        ],
        "colormap": colormap,
        "colormap_dir": str(engine.colormap_dir()),
    }
    if node_width is not None:
        spec["node_width"] = int(node_width)
    report = engine.screen(spec)
    # The geometry every verdict was read at, taken from the engine that read
    # them rather than restated on this side.
    geometry = {
        key: report.get(key) for key in ("tile", "field_supersample", "probe_width", "battery")
    }
    pairs = list(zip(batch, report["frames"], strict=True))
    if ledger is not None:
        for row, screened in pairs:
            ledger.write(
                "sampler_draw",
                channel=CHANNEL,
                scheme=scheme,
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
    return pairs, geometry


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
    """Draw the pinned plane's ladder, screen every frame, and return `(rows, record)`.

    Screened in batches of [`boundary.BATCH`] for the reason that module states:
    the engine costs a few milliseconds to start and a probe costs a few more, so
    a batch of one would spend a third of the clock on process spawn.
    """
    frames = draws(family, seed=seed, rungs=rungs)
    kept: list[dict] = []
    fates: Counter = Counter()
    by_rung: dict[int, Counter] = {rung: Counter() for rung in range(1, int(rungs) + 1)}
    started = time.monotonic()
    battery: dict = {}
    for start in range(0, len(frames), boundary.BATCH):
        pairs, geometry = screen_batch(
            family,
            frames[start : start + boundary.BATCH],
            seed=seed,
            scheme=LADDER,
            colormap=colormap,
            node_width=node_width,
            ledger=ledger,
        )
        battery = battery or geometry
        for row, screened in pairs:
            fates[screened["fate"]] += 1
            by_rung[row["rung"]][screened["fate"]] += 1
            if screened["passed"]:
                kept.append(seed_row(family, row, seed))

    record = {
        "channel": CHANNEL,
        "scheme": LADDER,
        "seed": int(seed),
        "rungs": int(rungs),
        "jitter": JITTER,
        "attempts": len(frames),
        "survivors": len(kept),
        "yield": round(len(kept) / len(frames), 4) if frames else None,
        "fates": dict(sorted(fates.items())),
        "by_rung": by_rung_record(by_rung),
        "seconds": round(time.monotonic() - started, 2),
        **battery,
    }
    log(
        f"[sampler] {record['survivors']}/{record['attempts']} viewport(s) cleared the gates "
        f"over {int(rungs)} rung(s) in {record['seconds']}s"
    )
    return kept, record


def by_rung_record(by_rung: dict[int, Counter]) -> dict:
    return {
        str(rung): {
            "attempts": sum(counts.values()),
            "survivors": counts.get("survived", 0),
            "fates": dict(sorted(counts.items())),
        }
        for rung, counts in sorted(by_rung.items())
    }


# --------------------------------------------------------------------------- #
# The parameter planes: straddle refinement.
# --------------------------------------------------------------------------- #
def band(family: dict, *, widest: float = WIDEST, narrowest: float = NARROWEST) -> list[int]:
    """The rungs whose cell width lies inside `[narrowest, widest]`, shallowest first."""
    widest, narrowest = float(widest), float(narrowest)
    if not 0 < narrowest <= widest:
        raise SamplerRefused(f"the width band {narrowest}..{widest} is not a band")
    home = 2.0 * boundary.home_box(family)[2]
    first = max(1, math.ceil(math.log2(home / widest) - 1e-9))
    last = math.floor(math.log2(home / narrowest) + 1e-9)
    if last < first:
        raise SamplerRefused(
            f"no rung of the home box (width {home:.4g}) halves into {narrowest}..{widest}: "
            f"a band has to hold at least one power-of-two cell width"
        )
    return list(range(first, last + 1))


def probe_spec(family: dict, box: tuple, rung: int, i: int, j: int, output: Path) -> dict:
    """The `dump-field` spec that probes cell `(i, j)` of `rung`, unjittered."""
    centre_re, centre_im, half_width, half_height = box
    side = cells(rung)
    cell_width = 2.0 * half_width / side
    cell_height = 2.0 * half_height / side
    spec = {
        "schema": 1,
        "family": family,
        "viewport": {
            "center_re": repr(centre_re - half_width + (i + 0.5) * cell_width),
            "center_im": repr(centre_im - half_height + (j + 0.5) * cell_height),
            "width": repr(cell_width),
        },
        "resolution": list(PROBE_RESOLUTION),
        "colormap": "twilight_shifted",
        "coloring": {"kind": "field", "field": {"kind": "smooth"}},
        "output": str(output),
    }
    if PROBE_MAXITER is not None:
        spec["maxiter"] = int(PROBE_MAXITER)
    return spec


def children_of(interior: list[bool], width: int, height: int) -> dict:
    """`{(a, b): interior_fraction}` for the four sub-blocks of one probe.

    `interior` is row-major with row 0 at the **top** of the frame, which is the
    engine's layout; `b` counts up from the bottom like a cell's `j`, so the
    bottom half of the grid is `b = 0`.
    """
    half_w, half_h = width // 2, height // 2
    out = {}
    for b in (0, 1):
        rows = range(half_h, height) if b == 0 else range(0, half_h)
        for a in (0, 1):
            cols = range(0, half_w) if a == 0 else range(half_w, width)
            inside = sum(interior[y * width + x] for y in rows for x in cols)
            out[(a, b)] = inside / (half_w * half_h)
    return out


def straddles(fraction: float) -> bool:
    """Both interior and escaped samples in one block."""
    return 0.0 < fraction < 1.0


def engine_probe(family: dict, box: tuple, rung: int, i: int, j: int) -> dict:
    """Probe one parent through the engine; its four children's interior fractions."""
    width, height = PROBE_RESOLUTION
    with tempfile.TemporaryDirectory(prefix="straddle-") as directory:
        output = Path(directory) / "probe.f32"
        engine.dump_field(probe_spec(family, box, rung, i, j, output))
        values = array.array("f")
        values.frombytes(output.read_bytes())
    if sys.byteorder == "big":
        values.byteswap()
    return children_of([math.isnan(v) for v in values], width, height)


class Refinement:
    """The straddle tree of one plane, grown a chunk of parents at a time on demand.

    A rung's cells are held in the order they are served. Growing a rung takes the
    next [`CHUNK`] cells of the rung above it — in *that* rung's served order, so
    the chunk is spread over the whole boundary rather than clustered — probes
    each, and appends the straddling children sorted by their digest. The rung
    above grows the same way when it is short, which is what makes the tree lazy
    all the way up: a draw at rung 12 pays for the chunks it stands on and not for
    the 133,465 straddling cells the whole of rung 12 is.

    `probe(family, box, rung, i, j)` returns `{(a, b): interior_fraction}` for
    the four children of cell `(i, j)`; the engine's is the default and a test
    hands in an analytic one.
    """

    def __init__(
        self,
        family: dict,
        *,
        seed: int = 0,
        probe=engine_probe,
        workers: int = PROBE_WORKERS,
        chunk: int | None = None,
    ):
        self.family = family
        self.seed = int(seed)
        self.box = boundary.home_box(family)
        self.probe = probe
        self.workers = max(1, int(workers))
        self.chunk = max(1, int(chunk if chunk is not None else CHUNK))
        #: Straddling cells per rung, as `(i, j)`, in served order. Rung 0 is the
        #: home box, which holds the whole locus and is never probed as a child.
        self._cells: dict[int, list[tuple[int, int]]] = {0: [(0, 0)]}
        self._frames: dict[int, list[dict]] = {0: []}
        #: How many cells of the rung above each rung has consumed as parents.
        self._used: dict[int, int] = {0: 0}
        self._spent: set[int] = {0}
        #: `{rung: {"parents", "straddling", "chunks", "seconds"}}`, cumulative.
        self.refined: dict[int, dict] = {}
        self.probes = 0
        self.seconds = 0.0

    def _grow(self, rung: int) -> None:
        """One more chunk for `rung`, or mark it spent when the rung above is."""
        start = self._used.setdefault(rung, 0)
        self._cells.setdefault(rung, [])
        self._frames.setdefault(rung, [])
        parents = self.cells(rung - 1, start + self.chunk)[start : start + self.chunk]
        if not parents:
            self._spent.add(rung)
            return
        started = time.monotonic()

        def one(cell):
            return cell, self.probe(self.family, self.box, rung - 1, *cell)

        if self.workers == 1 or len(parents) == 1:
            results = [one(cell) for cell in parents]
        else:
            with ThreadPoolExecutor(max_workers=self.workers) as pool:
                results = list(pool.map(one, parents))
        found = [
            frame_of(self.box, rung, 2 * i + a, 2 * j + b, self.seed)
            for (i, j), children in results
            for (a, b), fraction in sorted(children.items())
            if straddles(fraction)
        ]
        found.sort(key=lambda row: row["order"])
        seconds = time.monotonic() - started
        self._used[rung] = start + len(parents)
        self._frames[rung].extend(found)
        self._cells[rung].extend(tuple(row["cell"]) for row in found)
        self.probes += len(parents)
        self.seconds += seconds
        tally = self.refined.setdefault(
            rung, {"parents": 0, "straddling": 0, "chunks": 0, "seconds": 0.0}
        )
        tally["parents"] += len(parents)
        tally["straddling"] += len(found)
        tally["chunks"] += 1
        tally["seconds"] = round(tally["seconds"] + seconds, 2)

    def _ensure(self, rung: int, count: int) -> None:
        while len(self._cells.get(rung, ())) < count and rung not in self._spent:
            self._grow(rung)

    def cells(self, rung: int, count: int) -> list[tuple[int, int]]:
        """At least `count` of `rung`'s straddling cells in served order, or all there are."""
        self._ensure(rung, count)
        return self._cells[rung]

    def frames(self, rung: int, count: int) -> list[dict]:
        """The same, as draws: jittered by the seed, in served order."""
        self._ensure(rung, count)
        return self._frames[rung]

    def spent(self, rung: int) -> bool:
        """Whether every straddling cell of this rung has been found."""
        return rung in self._spent


class PlaneDraw:
    """One parameter plane's continuous supply: candidates refined and screened on demand.

    `survivors` only ever grows, at its tail, so a cursor over it stays correct.
    """

    def __init__(
        self,
        family: dict,
        *,
        seed: int = 0,
        widest: float = WIDEST,
        narrowest: float = NARROWEST,
        colormap: str = "twilight_shifted",
        node_width: int | None = None,
        ledger=None,
        log=print,
        probe=engine_probe,
        screen=screen_batch,
    ):
        self.family = family
        self.seed = int(seed)
        self.widest, self.narrowest = float(widest), float(narrowest)
        self.rungs = band(family, widest=widest, narrowest=narrowest)
        self.refinement = Refinement(family, seed=seed, probe=probe)
        self.colormap = colormap
        self.node_width = node_width
        self.ledger = ledger
        self.log = log
        self._screen = screen
        self.survivors: list[dict] = []
        self.exhausted = False
        self._index = 0
        self._turn = 0
        self.fates: Counter = Counter()
        self.by_rung: dict[int, Counter] = {rung: Counter() for rung in self.rungs}
        self.screen_seconds = 0.0
        self.battery: dict = {}

    def _next_candidates(self, count: int) -> list[dict]:
        """Up to `count` more draws, round-robin over the band's rungs."""
        out: list[dict] = []
        while len(out) < count and not self.exhausted:
            # A round in which no rung has an entry left is the end of the band.
            need = self._index + 1
            if self._turn == 0 and not any(
                self._index < len(self.refinement.frames(rung, need)) for rung in self.rungs
            ):
                self.exhausted = True
                break
            rows = self.refinement.frames(self.rungs[self._turn], need)
            if self._index < len(rows):
                out.append(rows[self._index])
            self._turn += 1
            if self._turn == len(self.rungs):
                self._turn = 0
                self._index += 1
        return out

    def extend(self, count: int) -> int:
        """Screen until at least `count` survivors exist or the band runs dry."""
        while len(self.survivors) < count and not self.exhausted:
            batch = self._next_candidates(boundary.BATCH)
            if not batch:
                break
            started = time.monotonic()
            pairs, geometry = self._screen(
                self.family,
                batch,
                seed=self.seed,
                scheme=STRADDLE,
                colormap=self.colormap,
                node_width=self.node_width,
                ledger=self.ledger,
            )
            self.screen_seconds += time.monotonic() - started
            self.battery = self.battery or geometry
            for row, screened in pairs:
                self.fates[screened["fate"]] += 1
                self.by_rung[row["rung"]][screened["fate"]] += 1
                if screened["passed"]:
                    self.survivors.append(seed_row(self.family, row, self.seed, STRADDLE))
        return len(self.survivors)

    def take(self, index: int) -> dict | None:
        """Survivor `index`, screening further to reach it; `None` past the band's end."""
        self.extend(index + 1)
        return self.survivors[index] if index < len(self.survivors) else None

    def record(self) -> dict:
        attempts = sum(self.fates.values())
        return {
            "channel": CHANNEL,
            "scheme": STRADDLE,
            "seed": self.seed,
            "band": [self.narrowest, self.widest],
            "rungs": list(self.rungs),
            "jitter": JITTER,
            "probe": {"resolution": list(PROBE_RESOLUTION), "maxiter": PROBE_MAXITER},
            "refined": {str(r): v for r, v in sorted(self.refinement.refined.items())},
            "probes": self.refinement.probes,
            "probe_seconds": round(self.refinement.seconds, 2),
            "attempts": attempts,
            "survivors": len(self.survivors),
            "yield": round(len(self.survivors) / attempts, 4) if attempts else None,
            "fates": dict(sorted(self.fates.items())),
            "by_rung": by_rung_record(self.by_rung),
            "screen_seconds": round(self.screen_seconds, 2),
            "exhausted": self.exhausted,
            **self.battery,
        }


class ViewportSampler:
    """The sampled roots each served partition can be handed.

    A pinned plane's list is drawn and screened once when the channel is built,
    and fixed for the run. A parameter plane's is a [`PlaneDraw`], which refines
    and screens only when a draw asks for more and whose list only grows.
    """

    def __init__(
        self,
        seeds: dict[str, list[dict]],
        *,
        records: dict | None = None,
        planes: dict[str, PlaneDraw] | None = None,
    ):
        self._seeds = {p: rows for p, rows in seeds.items() if rows}
        self.records = dict(records or {})
        self.planes = dict(planes or {})
        #: The partitions this channel can serve, in registry order. A pinned plane
        #: whose whole ladder was refused is absent rather than empty: the refill
        #: asks this list whether a channel exists at all.
        self.partitions = tuple(p for p in SERVED if p in self._seeds or p in self.planes)

    def continuous(self, partition: str) -> bool:
        """Whether this partition's list grows on demand rather than being fixed."""
        return partition in self.planes

    def exhausted(self, partition: str) -> bool:
        plane = self.planes.get(partition)
        return plane.exhausted if plane is not None else True

    def seeds(self, partition: str) -> list[dict]:
        """The sampled roots screened so far, in the order they are handed over."""
        if partition in self.planes:
            return self.planes[partition].survivors
        return self._seeds.get(partition, [])

    def take(self, partition: str, index: int) -> dict | None:
        """A parameter plane's survivor `index`, drawn if it has not been yet."""
        return self.planes[partition].take(index)

    def pool(self, partition: str, other: list) -> list:
        """A pinned plane's queue with the sampled roots interleaved through `other`.

        One sampled root per entry of whatever the partition already had, which
        on a pinned plane is the single home-view row. Interleaved rather than
        appended for the same reason the proven channel is: neither channel can
        be crowded out by the other.
        """
        from fractal_wallpapers.supply.proven import interleave

        return interleave(self.seeds(partition), list(other), ratio=1)

    def starvation(self, partition: str, drawn: int = 0) -> str:
        """Why this partition has nothing left to hand over, in one sentence."""
        if partition in self.planes:
            plane = self.planes[partition]
            return (
                f"the viewport sampler has handed over every screened straddling cell of its "
                f"{plane.narrowest:g}..{plane.widest:g} band ({len(plane.survivors)} of them). "
                f"A longer leg wants a lower `--sampler-narrowest`, which adds a rung."
            )
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
            "seeds": {p: len(self.seeds(p)) for p in self.partitions},
            "draws": {
                **{p: record for p, record in sorted(self.records.items())},
                **{p: plane.record() for p, plane in sorted(self.planes.items())},
            },
        }


def build(
    *,
    partitions=SERVED,
    seed: int = 0,
    rungs: int = RUNGS,
    widest: float = WIDEST,
    narrowest: float = NARROWEST,
    colormap: str = "twilight_shifted",
    node_width: int | None = None,
    ledger=None,
    log=print,
) -> ViewportSampler:
    """The channel a harvest or a walk holds.

    `partitions` may be a run's whole partition list; what this channel serves is
    that list's intersection with [`SERVED`]. A pinned plane's ladder is drawn
    and screened here; a parameter plane costs nothing until its first draw.
    """
    seeds: dict[str, list[dict]] = {}
    records: dict[str, dict] = {}
    planes: dict[str, PlaneDraw] = {}
    for partition in (p for p in partitions if p in SERVED):
        family = family_of(partition)
        if scheme_of(partition) == STRADDLE:
            planes[partition] = PlaneDraw(
                family,
                seed=seed,
                widest=widest,
                narrowest=narrowest,
                colormap=colormap,
                node_width=node_width,
                ledger=ledger,
                log=log,
            )
            continue
        rows, record = sample(
            family,
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
    return ViewportSampler(seeds, records=records, planes=planes)


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
    "CHUNK",
    "JITTER",
    "LADDER",
    "NARROWEST",
    "PROBE_MAXITER",
    "PROBE_RESOLUTION",
    "PROBE_WORKERS",
    "RUNGS",
    "SCHEMA",
    "SERVED",
    "SOURCE",
    "STRADDLE",
    "WIDEST",
    "PlaneDraw",
    "Refinement",
    "SamplerRefused",
    "ViewportSampler",
    "band",
    "build",
    "cells",
    "children_of",
    "digest_of",
    "draws",
    "engine_probe",
    "family_of",
    "frame_of",
    "probe_spec",
    "round_robin",
    "sample",
    "scheme_of",
    "seed_row",
    "straddles",
    "write",
]
