"""The viewport sampler: does a pinned plane actually get more than one fresh root,
and does a plane with a parameter to vary stay out of it.

Everything a pinned plane had before this was one home-view row and whatever the
label store held, so the first question is the whole point of the channel and the
second is the whole of its scope. One test is in the slow lane, and it is the one
that draws a real ladder through the real gate battery; the other engine-backed
one only needs a walk to exist, so it renders nothing and stays in the fast lane.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers import engine
from fractal_wallpapers.discovery import viewport_sampler as sampler
from fractal_wallpapers.discovery.walk import Limits
from fractal_wallpapers.supply.partitions import (
    ALL_PARTITIONS,
    CLASSIC_PHOENIX,
    DYNAMICAL_PLANES,
    PARAMETER_PLANES,
    PINNED_PLANES,
    is_pinned,
)
from fractal_wallpapers.supply.refill import Refill


def engine_is_built() -> bool:
    try:
        engine.engine_path()
    except FileNotFoundError:
        return False
    return True


needs_engine = pytest.mark.skipif(
    not engine_is_built(),
    reason="the engine is not built: cargo build --release --manifest-path engine/Cargo.toml",
)

SEED = 20260902


class Stub:
    """A sampler channel with rows nobody had to render, for the wiring tests.

    The same three members the refill asks a channel for. Everything about the
    interleave, the provenance passthrough and the deferral sentence is decided
    on this side of the engine, and paying a gate battery to check it would put
    the cheap half of this file in the slow lane for nothing.
    """

    def __init__(self, rows: dict):
        self._rows = rows
        self.partitions = tuple(p for p in sampler.SERVED if p in rows)
        self.records = {p: {"attempts": 4, "rungs": 1, "fates": {}} for p in rows}

    def seeds(self, partition):
        return self._rows.get(partition, [])

    def pool(self, partition, other):
        from fractal_wallpapers.supply.proven import interleave

        return interleave(self.seeds(partition), list(other), ratio=1)

    def starvation(self, partition, drawn=0):
        return sampler.ViewportSampler.starvation(self, partition, drawn)

    def summary(self):
        return {"channel": sampler.CHANNEL, "seeds": {p: len(v) for p, v in self._rows.items()}}


def row(index: int, width: str = "0.28125") -> dict:
    """One screened viewport, as [`sampler.seed_row`] writes it."""
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


class Recorder:
    """A walk that records the roots it is handed instead of walking them."""

    def __init__(self):
        self.roots: list[dict] = []

    def add_root(self, family, view=None, *, source, provenance):
        self.roots.append(
            {"family": family, "viewport": view, "source": source, "provenance": provenance}
        )
        return {"root_id": len(self.roots)}


# --------------------------------------------------------------------------- #
# What it serves, and what it must never serve.
# --------------------------------------------------------------------------- #
def test_the_sampler_serves_the_pinned_planes_and_nothing_else() -> None:
    """Scope, stated three ways because each of them is a different mistake. A
    parameter plane has a solved pool and an unscreened draw over the higher
    degrees measured zero good locations in 144. A `julia:*` twin's fresh supply
    is a *parameter*, from its pool or its parent's admissions. What is left is
    the planes with nothing to vary but the frame."""
    assert sampler.SERVED == PINNED_PLANES == (CLASSIC_PHOENIX,)
    assert not set(sampler.SERVED) & set(PARAMETER_PLANES)
    assert not set(sampler.SERVED) & set(DYNAMICAL_PLANES)
    assert [p for p in ALL_PARTITIONS if is_pinned(p)] == list(sampler.SERVED)


def test_a_parameter_plane_never_routes_through_the_sampler() -> None:
    """Two doors and both are shut. `build` intersects with what it serves, so a
    run naming every partition gets a channel for the pinned one alone; and the
    family lookup refuses outright, so nothing can hand a plane to the draw by
    another route."""
    live = Stub({CLASSIC_PHOENIX: [row(0), row(1)]})
    refill = Refill(Recorder(), sampler=live, partitions=list(ALL_PARTITIONS), seeds=None)
    for plane in (*PARAMETER_PLANES, *DYNAMICAL_PLANES, "phoenix"):
        assert refill._is_sampler(plane) is False
        assert refill.pool_state()[plane]["sampled"] == 0
    assert refill._is_sampler(CLASSIC_PHOENIX) is True

    for plane in (*PARAMETER_PLANES, *DYNAMICAL_PLANES, "phoenix"):
        with pytest.raises(sampler.SamplerRefused):
            sampler.family_of(plane)


# --------------------------------------------------------------------------- #
# The draw, without the engine: what a seed buys.
# --------------------------------------------------------------------------- #
def test_the_ladder_tiles_the_home_box_at_every_rung() -> None:
    """Rung `k` is `2^k` frames a side at width `home/2^k`, so a rung covers the
    box exactly once. A ladder that sampled widths out of a band instead — which
    is what `boundary` does, for a different question — would give a cloud of
    scales and no coverage guarantee at any of them."""
    family = sampler.family_of(CLASSIC_PHOENIX)
    frames = sampler.draws(family, seed=SEED, rungs=3)
    assert len(frames) == 4 + 16 + 64
    widths = {row["rung"]: float(row["width"]) for row in frames}
    assert widths[2] == pytest.approx(widths[1] / 2)
    assert widths[3] == pytest.approx(widths[1] / 4)
    for rung in (1, 2, 3):
        cells = {tuple(row["cell"]) for row in frames if row["rung"] == rung}
        assert len(cells) == sampler.cells(rung) ** 2, "one frame per cell, no cell twice"

    # Rung 0 is the home view, and the pool already hands that over. A channel
    # that restated it would put one frame in the queue twice under two names.
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

    # And a rung added later does not move the rungs already there: the jitter is
    # drawn from each cell's own digest rather than from a shared stream.
    deeper = sampler.draws(family, seed=SEED, rungs=4)
    by_id = {row["id"]: row for row in deeper}
    assert all(by_id[row["id"]] == row for row in once)


def test_a_ladder_with_no_rung_is_refused() -> None:
    with pytest.raises(sampler.SamplerRefused):
        sampler.draws(sampler.family_of(CLASSIC_PHOENIX), seed=SEED, rungs=0)


# --------------------------------------------------------------------------- #
# What the root row says it came from.
# --------------------------------------------------------------------------- #
def test_a_sampled_root_names_its_channel_its_seed_and_its_scale() -> None:
    """`provenance.channel` is the join every readout uses — `source` names the
    pool file an entry was read out of and cannot see a channel at all. The seed
    and the scale ride along so a root can say which draw produced it, which is
    what makes a yield-by-rung readable off the run's own ledger."""
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
        assert root["viewport"]["width"] == "0.28125"
        # It was never in a seed file, and a file name beside it would read true
        # and not be.
        assert root["provenance"]["file"] is None

    # The pool's one row is still in the queue rather than crowded out by three
    # hundred sampled ones: the interleave is what keeps either side reachable.
    assert [r["provenance"]["channel"] for r in walk.roots].count("home_view") == 1


def test_an_exhausted_ladder_says_so_in_the_sampler_s_own_words() -> None:
    """A pinned plane that has walked its ladder out is a channel that worked. The
    deferral has to say that rather than the pool's generic sentence, because what
    to do about it — more rungs, a denser draw — is this channel's business."""
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
# The raised expansion budget.
# --------------------------------------------------------------------------- #
def test_a_pinned_plane_root_gets_a_larger_expansion_budget_than_any_other() -> None:
    """Pinned because the reason is theirs. Every other partition answers a dead
    lineage with a fresh root carrying a fresh parameter; a pinned plane has no
    parameter to vary, so what a root does not reach, nothing else will.

    The numbers are pinned: 12 everywhere, 36 on a pinned plane. The crawl that
    bought the second one stopped at 0.66 of a 30-minute budget with its two
    productive roots on 12 expansions each — the cap — and six others on one."""
    limits = Limits()
    assert (limits.root_expansions, limits.pinned_root_expansions) == (12, 36)
    assert limits.pinned_root_expansions > limits.root_expansions


@needs_engine
def test_the_walk_reads_the_budget_off_each_root_s_own_family(tmp_path) -> None:
    """One walk, two roots, two budgets — so a mixed run does not have to choose
    which policy it is under. Derived from the root record the checkpoint already
    keeps, which is what makes it survive a resume without a new state field."""
    from fractal_wallpapers.discovery.walk import Policy, Walk

    walk = Walk(
        out_dir=tmp_path / "run",
        seed=SEED,
        limits=Limits(batch=2, batches=1, root_expansions=3, pinned_root_expansions=9),
        policy=Policy(candidates=2, node_width=96),
    )
    pinned = walk.add_root(
        sampler.family_of(CLASSIC_PHOENIX),
        {"center_re": "0.1", "center_im": "0.1", "width": "0.3"},
        source=sampler.SOURCE,
        provenance={"channel": sampler.CHANNEL},
    )
    varied = walk.add_root(
        {"kind": "julia", "degree": 2, "c": ["-0.75", "0.1"]},
        source="julia_c_pool",
        provenance={"channel": "shell_draw"},
    )
    assert walk.root_budget(pinned["root_id"]) == 9
    assert walk.root_budget(varied["root_id"]) == 3

    # And the eviction acts on each root's own number rather than on one of them.
    walk.expansions[pinned["root_id"]] = 4
    walk.expansions[varied["root_id"]] = 4
    walk.evict_capped()
    standing = {node["root_id"] for node in walk.frontier}
    assert pinned["root_id"] in standing
    assert varied["root_id"] not in standing


# --------------------------------------------------------------------------- #
# A real ladder, through the real gates.
# --------------------------------------------------------------------------- #
@pytest.mark.slow
@needs_engine
def test_a_pinned_plane_yields_more_than_one_distinct_root() -> None:
    """The whole point of the channel, through the engine: a plane whose fresh
    supply was one row by construction now has a set of screened places, and they
    are different places rather than one frame drawn repeatedly.

    Two rungs rather than four, because this is asking whether the channel opens
    the plane at all and the fourth rung alone is 256 renders."""
    live = sampler.build(partitions=[CLASSIC_PHOENIX], seed=SEED, rungs=2, log=lambda *_: None)
    roots = live.seeds(CLASSIC_PHOENIX)
    assert len(roots) > 1, "a pinned plane's supply is no longer one row"
    assert live.partitions == (CLASSIC_PHOENIX,)

    frames = {
        (r["viewport"]["center_re"], r["viewport"]["center_im"], r["viewport"]["width"])
        for r in roots
    }
    assert len(frames) == len(roots), "distinct places, not one frame under several ids"
    assert len({r["id"] for r in roots}) == len(roots)

    record = live.summary()["draws"][CLASSIC_PHOENIX]
    assert record["attempts"] == 4 + 16
    assert record["survivors"] == len(roots)
    # Record and rank: every attempt is accounted for by the gate that refused
    # it, so a rung that produced nothing has a reason beside it.
    assert sum(record["fates"].values()) == record["attempts"]
    assert set(record["fates"]) <= {"survived", "flat", "interior_cap", "occupancy_floor"}
