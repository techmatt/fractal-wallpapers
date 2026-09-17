"""The viewport sampler: does a plane actually get fresh roots, does a parameter
plane's supply keep coming after its pool is walked out, and does a Julia twin
stay out of it.

Two draw schemes live here. The pinned plane's ladder is the one that shipped
first and its tests are unchanged. A parameter plane's straddle refinement is
tested against an analytic plane — a disc, whose straddling cells are known
without an engine — so everything about the tree, the band, the order and the
refill's growing queue stays in the fast lane. Two tests are in the slow lane,
and they are the ones that draw real frames through the real gate battery.
"""

from __future__ import annotations

import math
from collections import Counter
from types import SimpleNamespace

import pytest

from fractal_wallpapers import engine
from fractal_wallpapers.discovery import boundary
from fractal_wallpapers.discovery import viewport_sampler as sampler
from fractal_wallpapers.supply.partitions import (
    ALL_PARTITIONS,
    CLASSIC_PHOENIX,
    DYNAMICAL_PLANES,
    PARAMETER_PLANES,
    PINNED_PLANES,
)
from fractal_wallpapers.supply.refill import Refill

needs_engine = pytest.mark.skipif(
    not engine.is_built(),
    reason="the engine is not built: cargo build --release --manifest-path engine/Cargo.toml",
)

SEED = 20260902
PLANE = "multibrot3"


class Stub:
    """A sampler channel with rows nobody had to render, for the wiring tests.

    The same members the refill asks a channel for. `rows` holds fixed lists for
    ladder partitions; `planes` holds a count per continuous partition, `None`
    meaning it never runs out.
    """

    def __init__(self, rows: dict, planes: dict | None = None):
        self._rows = rows
        self._planes = dict(planes or {})
        self._drawn = {p: [] for p in self._planes}
        self.partitions = tuple(p for p in sampler.SERVED if p in rows or p in self._planes)
        self.records = {p: {"attempts": 4, "rungs": 1, "fates": {}} for p in rows}
        #: What `ViewportSampler.starvation` reads for a continuous partition.
        self.planes = {
            p: SimpleNamespace(narrowest=0.2, widest=0.6, survivors=self._drawn[p])
            for p in self._planes
        }
        self.takes = Counter()

    def continuous(self, partition):
        return partition in self._planes

    def exhausted(self, partition):
        cap = self._planes.get(partition)
        return cap is not None and len(self._drawn[partition]) >= cap

    def seeds(self, partition):
        if partition in self._planes:
            return self._drawn[partition]
        return self._rows.get(partition, [])

    def take(self, partition, index):
        self.takes[partition] += 1
        cap = self._planes[partition]
        drawn = self._drawn[partition]
        while len(drawn) <= index and (cap is None or len(drawn) < cap):
            drawn.append(plane_row(len(drawn)))
        return drawn[index] if index < len(drawn) else None

    def pool(self, partition, other):
        from fractal_wallpapers.supply.proven import interleave

        return interleave(self.seeds(partition), list(other), ratio=1)

    def starvation(self, partition, drawn=0):
        return sampler.ViewportSampler.starvation(self, partition, drawn)

    def summary(self):
        return {"channel": sampler.CHANNEL}


def row(index: int, width: str = "0.28125") -> dict:
    """One screened pinned-plane viewport, as [`sampler.seed_row`] writes it."""
    return sampler.seed_row(
        {"kind": "phoenix", "c": ["0.5667", "0.0"], "p": ["-0.5", "0.0"], "z_prev": ["0.0", "0.0"]},
        {
            "id": f"sampler-r4-{index:03d}-000",
            "rung": 4,
            "cell": [index, 0],
            "scale": width,
            "center_re": f"0.{index}",
            "center_im": "0.1",
            "width": width,
        },
        SEED,
    )


def plane_row(index: int) -> dict:
    """One screened parameter-plane viewport."""
    return sampler.seed_row(
        {"kind": "multibrot", "degree": 3},
        {
            "id": f"sampler-r7-{index:03d}-000",
            "rung": 7,
            "cell": [index, 0],
            "scale": "0.0365",
            "center_re": f"0.{index}",
            "center_im": "0.5",
            "width": "0.0365",
        },
        SEED,
        sampler.STRADDLE,
    )


class Recorder:
    """A walk that records the roots it is handed instead of walking them."""

    def __init__(self):
        self.roots: list[dict] = []

    def add_root(self, family, view=None, *, source, provenance):
        self.roots.append(
            {"family": family, "viewport": view, "source": source, "provenance": provenance}
        )
        return {"root_id": len(self.roots)}


def disc_probe(radius: float = 1.0, calls: list | None = None):
    """An analytic plane whose interior is the disc `|c| < radius`.

    A child's interior fraction is 1 if the cell lies inside the disc, 0 if it
    misses it, and a half if the circle crosses it — which is all the straddle
    test reads, and needs no grid.
    """

    def probe(family, box, rung, i, j):
        if calls is not None:
            calls.append((rung, i, j))
        centre_re, centre_im, half_width, half_height = box
        side = sampler.cells(rung + 1)
        w, h = 2 * half_width / side, 2 * half_height / side
        out = {}
        for a in (0, 1):
            for b in (0, 1):
                x0 = centre_re - half_width + (2 * i + a) * w
                y0 = centre_im - half_height + (2 * j + b) * h
                near = math.hypot(max(x0, min(0.0, x0 + w)), max(y0, min(0.0, y0 + h)))
                far = max(math.hypot(x, y) for x in (x0, x0 + w) for y in (y0, y0 + h))
                out[(a, b)] = 1.0 if far < radius else 0.0 if near >= radius else 0.5
        return out

    return probe


def finite_side(refill: Refill, rows: list) -> None:
    """Stand `rows` in for the plane's pool, so a test does not read the tracked one.

    `seeds=None` is not "no pool": it is what asks for the tracked plane pool.
    """
    refill._streams[PLANE] = {"queue": [], "other": rows, "given": 0}
    refill._pools[PLANE] = refill._streams[PLANE]["queue"]


def every_other(family, batch, **_):
    """A screen that passes every second frame, so yields are nonzero and not total."""
    pairs = [
        (draw, {"fate": "survived" if k % 2 == 0 else "flat", "passed": k % 2 == 0})
        for k, draw in enumerate(batch)
    ]
    return pairs, {}


# --------------------------------------------------------------------------- #
# What it serves, and what it must never serve.
# --------------------------------------------------------------------------- #
def test_the_sampler_serves_every_plane_and_no_julia_twin() -> None:
    """Every parameter plane and the pinned plane, each under its own scheme. A
    `julia:*` twin's fresh supply is a *parameter*, from its pool or its parent's
    admissions, and varied phoenix is a pool of parameters too."""
    assert (*PARAMETER_PLANES, *PINNED_PLANES) == sampler.SERVED
    assert not set(sampler.SERVED) & set(DYNAMICAL_PLANES)
    assert "phoenix" not in sampler.SERVED
    assert set(sampler.SERVED) <= set(ALL_PARTITIONS)
    assert {p: sampler.scheme_of(p) for p in PARAMETER_PLANES} == dict.fromkeys(
        PARAMETER_PLANES, sampler.STRADDLE
    )
    assert sampler.scheme_of(CLASSIC_PHOENIX) == sampler.LADDER


def test_a_twin_never_routes_through_the_sampler_and_a_plane_does() -> None:
    """Two doors, and each is shut to a twin: `build` intersects with what it
    serves, and the family lookup refuses outright."""
    live = Stub({CLASSIC_PHOENIX: [row(0), row(1)]}, {p: None for p in PARAMETER_PLANES})
    refill = Refill(Recorder(), sampler=live, partitions=list(ALL_PARTITIONS), seeds=None)
    for twin in (*DYNAMICAL_PLANES, "phoenix"):
        assert refill._is_sampler(twin) is False
        assert refill.pool_state()[twin]["sampled"] == 0
        with pytest.raises(sampler.SamplerRefused):
            sampler.family_of(twin)
    assert refill._is_sampler(CLASSIC_PHOENIX) is True
    for plane in PARAMETER_PLANES:
        assert refill._is_continuous(plane) is True
        assert refill.has_channel(plane), "a plane with no pool file is served by the sampler"
    assert sampler.family_of("mandelbrot") == {"kind": "mandelbrot"}
    assert sampler.family_of("multibrot5") == {"kind": "multibrot", "degree": 5}


# --------------------------------------------------------------------------- #
# The pinned plane's ladder, without the engine: what a seed buys.
# --------------------------------------------------------------------------- #
def test_the_ladder_tiles_the_home_box_at_every_rung() -> None:
    """Rung `k` is `2^k` frames a side at width `home/2^k`, so a rung covers the
    box exactly once."""
    family = sampler.family_of(CLASSIC_PHOENIX)
    frames = sampler.draws(family, seed=SEED, rungs=3)
    assert len(frames) == 4 + 16 + 64
    widths = {row["rung"]: float(row["width"]) for row in frames}
    assert widths[2] == pytest.approx(widths[1] / 2)
    assert widths[3] == pytest.approx(widths[1] / 4)
    for rung in (1, 2, 3):
        cells = {tuple(row["cell"]) for row in frames if row["rung"] == rung}
        assert len(cells) == sampler.cells(rung) ** 2, "one frame per cell, no cell twice"

    # Rung 0 is the home view, and the pool already hands that over.
    assert min(row["rung"] for row in frames) == 1


def test_the_queue_interleaves_the_rungs_so_a_short_leg_sees_several_scales() -> None:
    """A queue in rung order would spend a ten-minute run entirely at the widest
    scale — 4 frames at rung 1 against 256 at rung 4."""
    frames = sampler.draws(sampler.family_of(CLASSIC_PHOENIX), seed=SEED, rungs=4)
    assert len({row["rung"] for row in frames[:4]}) == 4


def test_the_same_seed_draws_the_same_ladder_and_a_different_one_does_not() -> None:
    """The queue is re-derived rather than checkpointed, so a resumed session has
    to get the identical list back or its cursor points at a different frame."""
    family = sampler.family_of(CLASSIC_PHOENIX)
    once = sampler.draws(family, seed=SEED, rungs=3)
    again = sampler.draws(family, seed=SEED, rungs=3)
    assert once == again
    assert sampler.draws(family, seed=SEED + 1, rungs=3) != once

    # And a rung added later does not move the rungs already there.
    deeper = sampler.draws(family, seed=SEED, rungs=4)
    by_id = {row["id"]: row for row in deeper}
    assert all(by_id[row["id"]] == row for row in once)


def test_a_ladder_with_no_rung_is_refused() -> None:
    with pytest.raises(sampler.SamplerRefused):
        sampler.draws(sampler.family_of(CLASSIC_PHOENIX), seed=SEED, rungs=0)


# --------------------------------------------------------------------------- #
# A parameter plane's straddle refinement, against an analytic plane.
# --------------------------------------------------------------------------- #
def test_a_probe_s_bottom_half_is_the_children_with_the_lower_cell_index() -> None:
    """The engine writes row 0 at the TOP of the frame and a cell's `j` counts up
    from the bottom, so the two disagree by a flip. Getting it wrong refines the
    mirror image of the boundary, which on a plane symmetric about the real axis
    looks right at the home box and is wrong everywhere off it."""
    width, height = 4, 2
    interior = [True, True, False, False, False, False, False, False]
    fractions = sampler.children_of(interior, width, height)
    assert fractions == {(0, 1): 1.0, (1, 1): 0.0, (0, 0): 0.0, (1, 0): 0.0}


def test_only_straddling_cells_are_probed_and_a_full_growth_finds_every_one() -> None:
    """The tree spends a probe on a cell only if it straddled, and a rung grown to
    its end holds exactly the cells the boundary crosses — nothing the chunking
    does can lose one."""
    calls: list = []
    family = sampler.family_of(PLANE)
    tree = sampler.Refinement(family, seed=SEED, probe=disc_probe(calls=calls), workers=1)
    assert tree.probes == 0, "building the tree probes nothing"

    found = tree.cells(5, 10**9)
    assert tree.spent(5)
    probed = Counter(rung for rung, _, _ in calls)
    for rung in range(5):
        assert sorted(c for r, *c in calls if r == rung) == sorted(
            list(c) for c in tree.cells(rung, 0)
        ), "every parent probed is a straddling cell of its rung, and each exactly once"
    assert tree.probes == sum(probed.values())

    # Against the disc itself: exactly the rung-5 cells the circle crosses.
    centre_re, centre_im, half_width, half_height = tree.box
    side = sampler.cells(5)
    w, h = 2 * half_width / side, 2 * half_height / side
    crossed = set()
    for i in range(side):
        for j in range(side):
            x0, y0 = centre_re - half_width + i * w, centre_im - half_height + j * h
            near = math.hypot(max(x0, min(0.0, x0 + w)), max(y0, min(0.0, y0 + h)))
            far = max(math.hypot(x, y) for x in (x0, x0 + w) for y in (y0, y0 + h))
            if near < 1.0 <= far:
                crossed.add((i, j))
    assert set(found) == crossed and len(found) == len(crossed)
    assert len(found) < side * side / 4, "the probes went where the boundary is"


def test_a_rung_grows_only_as_far_as_a_draw_asks_and_never_reorders() -> None:
    """The first pilot refined whole rungs and paid 645.6 s before its first root.
    A draw at a deep rung pays for the chunks under it and no more, and growing a
    rung appends: what was served stays where it was."""
    calls: list = []
    tree = sampler.Refinement(
        sampler.family_of(PLANE), seed=SEED, probe=disc_probe(calls=calls), workers=1, chunk=4
    )
    first = list(tree.frames(7, 1))
    assert first, "one draw at rung 7"
    spent = len(calls)
    assert spent <= 4 * 7, "at most one chunk per rung on the way down"
    assert not tree.spent(7)

    tree.frames(7, 1)
    assert len(calls) == spent, "a draw already found is not paid for again"
    more = tree.frames(7, len(first) + 1)
    assert len(more) > len(first) and more[: len(first)] == first
    assert len(calls) > spent


def test_the_band_holds_the_rungs_whose_width_lies_inside_it() -> None:
    family = sampler.family_of(PLANE)
    home = 2 * boundary.home_box(family)[2]
    rungs = sampler.band(family)
    assert rungs == sorted(rungs) and rungs[0] >= 1
    for rung in rungs:
        assert sampler.NARROWEST <= home / 2**rung <= sampler.WIDEST
    assert home / 2 ** (rungs[0] - 1) > sampler.WIDEST
    assert home / 2 ** (rungs[-1] + 1) < sampler.NARROWEST
    with pytest.raises(sampler.SamplerRefused):
        sampler.band(family, widest=1e-3, narrowest=1e-2)


def test_a_plane_draw_goes_round_robin_over_the_band_in_digest_order() -> None:
    """The ladder's order, over the straddle tree: one draw per rung in turn, and
    inside a chunk of a rung by the cell's digest, jittered by the seed like the
    ladder."""
    family = sampler.family_of(PLANE)
    draw = sampler.PlaneDraw(
        family, seed=SEED, widest=0.5, narrowest=0.05, probe=disc_probe(), screen=every_other
    )
    assert len(draw.rungs) >= 3
    draw.extend(40)
    served = draw.refinement
    order = [row["provenance"]["rung"] for row in draw.survivors[: len(draw.rungs)]]
    assert sorted(set(order)) == draw.rungs, "the first survivors span the band"
    for rung in draw.rungs:
        position = {f["id"]: k for k, f in enumerate(served.frames(rung, 0))}
        ids = [r["id"] for r in draw.survivors if r["provenance"]["rung"] == rung]
        assert ids, f"rung {rung} served nothing"
        assert [position[i] for i in ids] == sorted(position[i] for i in ids), "served order"
        chunk = served.frames(rung, 0)[: len(ids)]
        if served.refined[rung]["chunks"] == 1:
            assert [f["order"] for f in chunk] == sorted(f["order"] for f in chunk)
    for survivor in draw.survivors:
        assert survivor["provenance"]["scheme"] == sampler.STRADDLE
        assert survivor["provenance"]["channel"] == sampler.CHANNEL

    again = sampler.PlaneDraw(
        family, seed=SEED, widest=0.5, narrowest=0.05, probe=disc_probe(), screen=every_other
    )
    again.extend(40)
    assert again.survivors[:40] == draw.survivors[:40], "re-derived, not checkpointed"


def test_a_plane_draw_only_grows_and_says_when_its_band_is_spent() -> None:
    """The list a cursor stands in only ever gains entries at its tail. A band
    one rung wide is small enough to spend, and spending it is a statement."""
    family = sampler.family_of(PLANE)
    draw = sampler.PlaneDraw(
        family, seed=SEED, widest=0.6, narrowest=0.2, probe=disc_probe(), screen=every_other
    )
    assert draw.take(0) is not None
    snapshot = list(draw.survivors)
    assert draw.take(10_000) is None
    assert draw.exhausted
    assert draw.survivors[: len(snapshot)] == snapshot
    total = sum(len(draw.refinement.frames(r, 10**9)) for r in draw.rungs)
    assert len(draw.survivors) == (total + 1) // 2, "every candidate screened exactly once"
    record = draw.record()
    assert record["attempts"] == total
    assert record["exhausted"] is True


# --------------------------------------------------------------------------- #
# The refill's side of a channel that does not run out.
# --------------------------------------------------------------------------- #
def test_a_plane_keeps_being_served_after_its_pool_is_walked_out() -> None:
    """The point of the channel. Three pool rows and an unbounded sampler: the
    queue alternates the two while the pool lasts and is all sampler after, and
    the cursor never re-hands or skips an entry however far the queue grows."""
    walk = Recorder()
    live = Stub({}, {PLANE: None})
    refill = Refill(walk, sampler=live, partitions=[PLANE], low_water=8, per_draw=4, seeds=None)
    pool = [
        {"id": f"pool-{k}", "family": {"kind": "multibrot", "degree": 3}, "viewport": None}
        for k in range(3)
    ]
    finite_side(refill, pool)

    for batch in range(5):
        assert refill.starved({PLANE: 0}, batch * refill.cooldown) == [PLANE]
        refill.run({PLANE: 0}, batch=batch * refill.cooldown, loop_seconds=1e6)
    ids = [r["provenance"]["seed_id"] for r in walk.roots]
    assert len(ids) == 20 and len(set(ids)) == 20, "no entry handed over twice"
    assert ids[:6] == [
        "sampler-r7-000-000",
        "pool-0",
        "sampler-r7-001-000",
        "pool-1",
        "sampler-r7-002-000",
        "pool-2",
    ]
    assert all(i.startswith("sampler-") for i in ids[6:]), "the pool is spent; the sampler is not"
    assert refill.deferred({PLANE: 0}) == {}


def test_asking_a_continuous_queue_its_size_draws_nothing() -> None:
    """The launch prints every partition's pool. A continuous channel whose size
    were asked by materializing it would pay a whole refinement before batch 0."""
    live = Stub({}, {PLANE: None})
    refill = Refill(Recorder(), sampler=live, partitions=[PLANE], seeds=None)
    state = refill.pool_state()[PLANE]
    assert state["continuous"] is True
    assert state["reason"] is None
    assert live.takes[PLANE] == 0
    assert any("unbounded" in line for line in refill.pool_lines())


def test_a_spent_band_is_deferred_in_the_sampler_s_own_words() -> None:
    walk = Recorder()
    live = Stub({}, {PLANE: 2})
    refill = Refill(walk, sampler=live, partitions=[PLANE], low_water=8, per_draw=8, seeds=None)
    finite_side(refill, [])
    refill.run({PLANE: 0}, batch=0, loop_seconds=1.0)
    assert len(walk.roots) == 2
    reason = refill.deferred({PLANE: 0})[PLANE]["reason"]
    assert "--sampler-narrowest" in reason


# --------------------------------------------------------------------------- #
# What the root row says it came from.
# --------------------------------------------------------------------------- #
def test_a_sampled_root_names_its_channel_its_seed_and_its_scale() -> None:
    """`provenance.channel` is the join every readout uses. The seed and the scale
    ride along so a root can say which draw produced it."""
    walk = Recorder()
    refill = Refill(
        walk,
        sampler=Stub({CLASSIC_PHOENIX: [row(0), row(1), row(2)]}),
        partitions=[CLASSIC_PHOENIX],
        low_water=8,
        per_draw=4,
    )
    refill.run({CLASSIC_PHOENIX: 0}, batch=0, loop_seconds=1.0)

    sampled = [r for r in walk.roots if r["provenance"]["channel"] == sampler.CHANNEL]
    assert len(sampled) == 3, "the pinned pool's home view is the fourth"
    for root in sampled:
        assert root["source"] == sampler.SOURCE
        assert root["provenance"]["sampler_seed"] == SEED
        assert root["provenance"]["rung"] == 4
        assert root["provenance"]["scheme"] == sampler.LADDER
        assert root["viewport"]["width"] == "0.28125"
        assert root["provenance"]["file"] is None

    assert [r["provenance"]["channel"] for r in walk.roots].count("home_view") == 1


def test_an_exhausted_ladder_says_so_in_the_sampler_s_own_words() -> None:
    walk = Recorder()
    refill = Refill(
        walk,
        sampler=Stub({CLASSIC_PHOENIX: [row(0)]}),
        partitions=[CLASSIC_PHOENIX],
        low_water=8,
        per_draw=8,
    )
    refill.run({CLASSIC_PHOENIX: 0}, batch=0, loop_seconds=1.0)
    reason = refill.deferred({CLASSIC_PHOENIX: 0})[CLASSIC_PHOENIX]["reason"]
    assert "viewport sampler is exhausted" in reason
    assert "--sampler-rungs" in reason


# --------------------------------------------------------------------------- #
# Real frames, through the real gates.
# --------------------------------------------------------------------------- #
@pytest.mark.slow
@needs_engine
def test_a_pinned_plane_yields_more_than_one_distinct_root() -> None:
    """A plane whose fresh supply was one row by construction now has a set of
    screened places. Two rungs rather than four: the fourth alone is 256 renders."""
    live = sampler.build(partitions=[CLASSIC_PHOENIX], seed=SEED, rungs=2, log=lambda *_: None)
    roots = live.seeds(CLASSIC_PHOENIX)
    assert len(roots) > 1, "a pinned plane's supply is no longer one row"
    assert live.partitions == (CLASSIC_PHOENIX,)

    frames = {
        (r["viewport"]["center_re"], r["viewport"]["center_im"], r["viewport"]["width"])
        for r in roots
    }
    assert len(frames) == len(roots), "distinct places, not one frame under several ids"

    record = live.summary()["draws"][CLASSIC_PHOENIX]
    assert record["attempts"] == 4 + 16
    assert record["survivors"] == len(roots)
    assert sum(record["fates"].values()) == record["attempts"]
    assert set(record["fates"]) <= {"survived", "flat", "interior_cap", "occupancy_floor"}


@pytest.mark.slow
@needs_engine
def test_a_parameter_plane_refines_through_the_engine_and_yields_distinct_roots() -> None:
    """The straddle probe through `dump-field` and the draw through the battery,
    over a three-rung band (6–8 on multibrot3) so it is seconds: the probe finds the boundary rather
    than the whole box, and what the screen passes is a set of distinct places."""
    live = sampler.build(partitions=[PLANE], widest=0.1, narrowest=0.02, seed=SEED)
    assert live.partitions == (PLANE,)
    first = live.take(PLANE, 7)
    assert first is not None, "eight roots off three rungs of a plane's boundary"
    record = live.summary()["draws"][PLANE]
    refined = record["refined"]
    deepest = str(max(int(r) for r in refined))
    assert refined[deepest]["straddling"] < sampler.cells(int(deepest)) ** 2 / 2
    roots = live.seeds(PLANE)
    views = {(r["viewport"]["center_re"], r["viewport"]["center_im"]) for r in roots}
    assert len(views) == len(roots)
    assert sum(record["fates"].values()) == record["attempts"]
