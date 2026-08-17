"""The walk: the loop, the reserved floors, and the record it leaves.

The last two tests here are **smoke walks** — small, seeded, real runs through
the real engine — because everything else in this file can be true of a walk
that never actually walked. They are sized to a second or two apiece, which is
what makes them runnable on every commit rather than every so often.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers import engine
from fractal_wallpapers.discovery import ledger as ledger_module
from fractal_wallpapers.discovery.scoring import NullScorer
from fractal_wallpapers.discovery.walk import (
    REFRAMED_ORIGINS,
    Gates,
    Limits,
    Policy,
    Reframings,
    Walk,
    family_key,
)

#: A place to stand, for the tests that are about the frontier rather than about
#: framing. Where a walk root *actually* starts is the engine's home table, and
#: `test_home_views.py` is what pins that.
VIEW = {"center_re": "0.0", "center_im": "0.0", "width": "3.0"}


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


def walk(tmp_path, **kwargs) -> Walk:
    kwargs.setdefault("seed", 20260814)
    return Walk(out_dir=tmp_path / "walk", **kwargs)


# --------------------------------------------------------------------------- #
# the frontier
# --------------------------------------------------------------------------- #


def test_two_families_never_share_one_engine_call() -> None:
    """The engine expands one family per call, and two Julia views at different
    `c` are different fractals. Making the grouping key the family itself is
    what keeps that structural rather than remembered."""
    one = {"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]}
    two = {"kind": "julia", "degree": 2, "c": ["-0.4", "0.61"]}
    assert family_key(one) != family_key(two)
    assert family_key(one) == family_key({"c": ["-0.4", "0.6"], "degree": 2, "kind": "julia"})


def test_a_root_whose_budget_is_spent_is_evicted_not_skipped(tmp_path) -> None:
    """Skipping is not enough. A root spawns children faster than it drains, so
    capped nodes accumulate until they *are* the frontier and every batch is
    dead weight."""
    run = walk(tmp_path, limits=Limits(batch=4, root_expansions=1))
    for _ in range(6):
        run.add_root({"kind": "mandelbrot"}, VIEW, source="test", provenance={})
    assert len(run.frontier) == 6

    first = run.pop_batch()
    assert len(first) == 4
    remaining = run.pop_batch()
    assert len(remaining) == 2, "the two untouched roots"
    assert run.pop_batch() == [], "and then nothing: every root is capped"
    assert run.frontier == [], "the capped nodes are gone, not merely passed over"


def test_the_breadth_floor_reserves_slots_for_roots_nothing_has_touched(tmp_path) -> None:
    """Without it the triggered channel starves fresh roots: a view produced by
    snapping to a nucleus is centered on a nucleus, so snapping it again nearly
    always works, and the operators multiply into the whole frontier."""
    run = walk(tmp_path, limits=Limits(batch=4, breadth_floor=0.25, operator_quota=0))
    touched = run.add_root({"kind": "mandelbrot"}, VIEW, source="test", provenance={})
    run.expansions[touched["root_id"]] = 1
    # Six descendants of the touched root, each ranked above the fresh root.
    for _ in range(6):
        node = run._node(
            family={"kind": "mandelbrot"},
            view=VIEW,
            depth=2,
            root_id=touched["root_id"],
            origin="walk",
            parent_node_id=touched["node_id"],
        )
        node["priority"] = 100.0
    fresh = run.add_root({"kind": "mandelbrot"}, VIEW, source="test", provenance={})
    fresh["priority"] = -100.0

    batch = run.pop_batch()
    assert len(batch) == 4
    assert fresh["node_id"] in {node["node_id"] for node in batch}, (
        "the worst-ranked node in the frontier, taken because its root is untouched"
    )
    assert run.tally["breadth_floor_filled"] == 1


def test_a_floor_that_cannot_be_filled_falls_back_rather_than_stalling(tmp_path) -> None:
    """An unfillable reservation must never shrink the batch. Both floors are
    quotas *of available*, and what they cannot fill goes straight back to the
    ordinary order in the same batch."""
    run = walk(tmp_path, limits=Limits(batch=4, breadth_floor=0.5, operator_quota=2))
    root = run.add_root({"kind": "mandelbrot"}, VIEW, source="test", provenance={})
    run.expansions[root["root_id"]] = 1
    for _ in range(6):
        run._node(
            family={"kind": "mandelbrot"},
            view=VIEW,
            depth=2,
            root_id=root["root_id"],
            origin="walk",
            parent_node_id=root["node_id"],
        )

    batch = run.pop_batch()
    assert len(batch) == 4, "a full batch, with neither floor fillable"
    assert run.tally["breadth_floor_filled"] == 0
    assert run.tally["breadth_floor_unfilled"] == 2
    assert run.tally["operator_quota_unfilled"] == 2


def test_the_operator_floor_counts_reframings_and_not_ordinary_descent(tmp_path) -> None:
    """The reserved slots are for the population nothing has been trained on.
    Ordinary descent is not that population, and counting it as such would make
    the floor a floor on everything, which is no floor at all."""
    run = walk(tmp_path, limits=Limits(batch=2, breadth_floor=0.0, operator_quota=1))
    root = run.add_root({"kind": "mandelbrot"}, VIEW, source="test", provenance={})
    run.expansions[root["root_id"]] = 1
    for _ in range(4):
        node = run._node(
            family={"kind": "mandelbrot"},
            view=VIEW,
            depth=2,
            root_id=root["root_id"],
            origin="walk",
            parent_node_id=root["node_id"],
        )
        node["priority"] = 100.0
    reframed = run._node(
        family={"kind": "mandelbrot"},
        view=VIEW,
        depth=2,
        root_id=root["root_id"],
        origin="snap_to_nucleus",
        parent_node_id=root["node_id"],
        atom_key="2:x,y",
    )
    reframed["priority"] = -100.0

    batch = run.pop_batch()
    assert reframed["node_id"] in {node["node_id"] for node in batch}
    assert run.tally["operator_quota_filled"] == 1
    assert "walk" not in REFRAMED_ORIGINS and "root" not in REFRAMED_ORIGINS


# --------------------------------------------------------------------------- #
# the seeds
#
# Seeding asks the engine where the family comes home — there is no framing
# literal on this side any more — so these need the binary that owns the table.
# --------------------------------------------------------------------------- #


@needs_engine
def test_the_julia_pool_seeds_one_root_per_parameter(tmp_path) -> None:
    run = walk(tmp_path)
    assert run.seed_from_julia_pool(limit=5) == 5
    assert len({node["family"]["c"][0] for node in run.frontier}) == 5
    assert all(node["depth"] == 1 for node in run.frontier)


@needs_engine
def test_the_phoenix_pool_seeds_the_whole_parameter_point(tmp_path) -> None:
    run = walk(tmp_path)
    run.seed_from_phoenix_pool(limit=3)
    for node in run.frontier:
        assert {"c", "p", "z_prev"} <= set(node["family"])


@needs_engine
def test_a_root_records_where_it_came_from(tmp_path) -> None:
    run = walk(tmp_path)
    run.seed_from_julia_pool(limit=2)
    run.ledger.close()
    roots = [row for row in ledger_module.read(run.ledger.path) if row["kind"] == "root"]
    assert len(roots) == 2
    assert roots[0]["source"] == "julia_c_pool"
    assert roots[0]["provenance"]["channel"]
    assert roots[0]["viewport"] == VIEW, "a julia root comes home to the whole plane"


# --------------------------------------------------------------------------- #
# smoke walks
# --------------------------------------------------------------------------- #


@needs_engine
def test_a_seeded_smoke_walk_records_a_fate_for_every_candidate(tmp_path) -> None:
    """The whole loop, small and for real: seeds in, engine called, ledger out.

    What it pins is the property the record rests on — **record and rank, never
    gate and forget**. Every candidate the engine drew is on a line of the
    ledger with the gate that refused it or a thumbnail if none did, and the
    rejects are usually the larger half.
    """
    run = walk(
        tmp_path,
        limits=Limits(batch=3, batches=2, operator_quota=0),
        policy=Policy(candidates=2, node_width=128),
        reframings=Reframings(enabled=False),
    )
    run.seed_from_julia_pool(limit=3)
    summary = run.run()

    assert summary["batches"] == 2
    rows = ledger_module.read(run.ledger.path)
    assert rows[0]["kind"] == "run" and rows[0]["scorer"] == "null"
    assert rows[-1]["kind"] == "summary"

    candidates = [row for row in rows if row["kind"] == "candidate"]
    assert candidates, "a walk that drew nothing is not a smoke test"
    for row in candidates:
        assert row["fate"] in ledger_module.FATES
        assert row["family"]["kind"] == "julia"
        assert set(row["viewport"]) == {"center_re", "center_im", "width"}
        assert row["score"] is None and row["scorer"] == "null"
        # A picture and a node id both mean *this candidate reached the
        # frontier*, which is the expansion tier and not the booking one.
        on_frontier = row["fate"] in (ledger_module.SURVIVED, ledger_module.EXPANDABLE)
        assert (row["image"] is not None) == on_frontier
        assert (row["node_id"] is not None) == on_frontier

    for row in rows:
        if row["kind"] == "node_dead":
            assert row["cause"] in ledger_module.NODE_CAUSES


@needs_engine
def test_a_smoke_walk_records_coordinates_as_decimal_strings(tmp_path) -> None:
    """The string is the identity of a location. A row that stored a float would
    have thrown that away at the one point in the pipeline that still had it."""
    run = walk(
        tmp_path,
        limits=Limits(batch=2, batches=1, operator_quota=0),
        policy=Policy(candidates=2, node_width=128),
        reframings=Reframings(enabled=False),
    )
    run.seed_from_julia_pool(limit=2)
    run.run()

    for row in ledger_module.read(run.ledger.path):
        if row["kind"] != "candidate":
            continue
        for value in row["viewport"].values():
            assert isinstance(value, str)
            assert float(value) == float(value), "and it parses back to a number"
        for value in row["family"]["c"]:
            assert isinstance(value, str)


@needs_engine
def test_a_reframing_inherits_the_root_it_was_triggered_from(tmp_path) -> None:
    """An operator is not a source: it applies to a place the walk found, and it
    inherits both that place's provenance and its budget. A reframing with a
    root of its own would be a source wearing an operator's name."""
    run = walk(
        tmp_path,
        limits=Limits(batch=3, batches=2, probe_probability=1.0),
        policy=Policy(candidates=2, node_width=128),
        reframings=Reframings(enabled=True, lateral=False),
    )
    seeds = tmp_path / "seeds.jsonl"
    seeds.write_text(
        "\n".join(
            json.dumps(
                {
                    "schema": 1,
                    "family": {"kind": "mandelbrot"},
                    "viewport": {"center_re": re, "center_im": im, "width": width},
                }
            )
            for re, im, width in (
                ("-0.7453", "0.1127", "0.2"),
                ("0.2929", "0.0149", "0.1"),
                ("-0.748", "0.263", "0.06"),
            )
        ),
        encoding="utf-8",
    )
    run.seed_from_file(seeds)
    run.run()

    rows = ledger_module.read(run.ledger.path)
    reframings = [row for row in rows if row["kind"] == "reframing"]
    assert reframings, "the probe fired but nothing was recorded"
    roots = {row["node_id"]: row["root_id"] for row in rows if row["kind"] == "root"}
    del roots  # the assertion below is about the reframing rows themselves

    used = [row for row in reframings if row["used"]]
    for row in reframings:
        assert row["operator"] in REFRAMED_ORIGINS
        assert row["available"] or row["reason"], "a refusal has to be named"
        if row["available"]:
            assert row["atom_key"] and row["atom_key"].startswith("2:")
            assert row["node_margin_decades"] is not None
    if used:
        # The reframing's own node carries the triggering node's root.
        by_id = {row["node_id"]: row for row in rows if row["kind"] == "candidate"}
        for row in used:
            triggering = by_id.get(row["node_id"])
            if triggering is not None:
                assert triggering["root_id"] == row["root_id"]


@needs_engine
def test_a_walk_with_no_roots_does_nothing_rather_than_inventing_some(tmp_path) -> None:
    run = walk(tmp_path, limits=Limits(batch=2, batches=2))
    assert run.run()["batches"] == 0


# --------------------------------------------------------------------------- #
# the expansion grace below a plane-seed root
#
# No engine: the decision under test is the walk's, made on a report the engine
# would have handed back, so the report is written out here instead of drawn.
# --------------------------------------------------------------------------- #

#: A plane-seed root's family and the frame it is handed over at.
PLANE_SEED = {"family": {"kind": "mandelbrot"}, "viewport": VIEW}

#: A dynamical row in the same seed file. Its home view *is* where its material
#: lives, so it is one of the roots the grace must not touch.
JULIA_SEED = {"family": {"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]}, "viewport": VIEW}


class FixedScorer:
    """One opinion about everything, compared at the project's real floors.

    Fixed because the question is what the *walk* does with a verdict, and a
    scorer that varied would make a failing test ambiguous between the two.
    """

    name = "fixed"

    def __init__(self, value: float | None):
        self.value = value

    def score(self, candidate: dict) -> float | None:
        del candidate
        return self.value

    def read(self, candidates: list[dict]):
        from fractal_wallpapers.discovery.scoring import Reading

        error = None if self.value is not None else "no view was rendered for this candidate"
        return [Reading(self.value, None, error) for _ in candidates]

    def admits(self, candidate: dict, score) -> bool:
        from fractal_wallpapers.supply import currency

        del candidate
        return currency.passes_good_floor(score)

    def expandable(self, candidate: dict, score) -> bool:
        from fractal_wallpapers.curation import floors

        del candidate
        return floors.passes_junk_floor(score)


def seed_file(tmp_path, rows) -> object:
    path = tmp_path / "seeds.jsonl"
    path.write_text(
        "\n".join(json.dumps({"schema": 1, **row}) for row in rows) + "\n", encoding="utf-8"
    )
    return path


def plane_root(run: Walk, tmp_path) -> dict:
    """One root off a seed file, which is the parameter plane's only channel."""
    assert run.seed_from_file(seed_file(tmp_path, [PLANE_SEED])) == 1
    return run.frontier[0]


def gate_survivors(run: Walk, root, depths) -> list[dict]:
    """Record one gate survivor per depth under `root`, and return the rows.

    The engine's own report, written by hand: every row has already passed every
    structural gate, so what comes back is exactly what the two floors decided.
    """
    report = {
        "candidates": [
            {
                "node_id": root["node_id"],
                "root_id": root["root_id"],
                "depth": depth,
                "child_index": index,
                "center_re": "0.0",
                "center_im": "0.0",
                "width": "0.5",
                "branch": "descend",
                "placement": "focus",
                "focus_score": 0.5,
                "maxiter": 512,
                "interior_fraction": 0.1,
                "escape": 6.0,
                "occupancy": 0.6,
                "image": f"view{index}.png",
                "fate": ledger_module.SURVIVED,
            }
            for index, depth in enumerate(depths)
        ],
        "dead": [],
    }
    _survivors, recorded = run._record(report, {root["node_id"]: root}, root["family"])
    return recorded


def fates_by_rung(run: Walk, root, rungs) -> dict:
    rows = gate_survivors(run, root, [rung + 1 for rung in rungs])
    return {row["plane_rung"]: row["fate"] for row in rows}


def test_the_grace_covers_exactly_the_rungs_below_a_plane_root(tmp_path) -> None:
    """N rungs ungated and the floor back on at N+1. The head scores plane
    locations near zero at the widths a plane root starts at, so without this the
    first rung refuses everything and the channel never descends to its material."""
    run = walk(
        tmp_path,
        scorer=FixedScorer(0.01),
        limits=Limits(plane_grace_rungs=5),
    )
    root = plane_root(run, tmp_path)

    fates = fates_by_rung(run, root, [1, 2, 3, 4, 5, 6, 7])
    assert [fates[rung] for rung in (1, 2, 3, 4, 5)] == [ledger_module.EXPANDABLE] * 5
    assert [fates[rung] for rung in (6, 7)] == [ledger_module.NOT_ADMITTED] * 2
    assert run.tally["grace:rescued"] == 5


def test_no_grace_reproduces_the_gated_walk(tmp_path) -> None:
    """`0` is not a special case; it is the walk as it was."""
    run = walk(tmp_path, scorer=FixedScorer(0.01), limits=Limits(plane_grace_rungs=0))
    root = plane_root(run, tmp_path)

    fates = fates_by_rung(run, root, [1, 2, 3, 4, 5, 6])
    assert set(fates.values()) == {ledger_module.NOT_ADMITTED}
    assert "grace:rescued" not in run.tally


def test_the_grace_is_keyed_to_plane_provenance_and_not_to_depth(tmp_path) -> None:
    """A dynamical root in the same seed file, at the same rung, under the same
    scorer. Provenance is necessary and the family is not sufficient — the word
    "seeds" must not annex a Julia row into the parameter plane's exemption."""
    run = walk(tmp_path, scorer=FixedScorer(0.01), limits=Limits(plane_grace_rungs=5))
    assert run.seed_from_file(seed_file(tmp_path, [PLANE_SEED, JULIA_SEED])) == 2
    plane, julia = run.frontier

    assert fates_by_rung(run, plane, [1]) == {1: ledger_module.EXPANDABLE}
    rows = gate_survivors(run, julia, [2])
    assert rows[0]["fate"] == ledger_module.NOT_ADMITTED
    assert rows[0]["plane_rung"] is None and rows[0]["grace"] is False


def test_a_pooled_root_is_never_graced_however_shallow_it_starts(tmp_path) -> None:
    """The tracked `c`-pools hand over dynamical roots, and the grace is not a
    statement about roots — it is a statement about one channel's depth."""
    run = walk(tmp_path, scorer=FixedScorer(0.01), limits=Limits(plane_grace_rungs=5))
    root = run.add_root(
        {"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]},
        VIEW,
        source="julia_c_pool",
        provenance={},
    )
    assert run.plane_roots == set()
    assert gate_survivors(run, root, [2])[0]["fate"] == ledger_module.NOT_ADMITTED


def test_the_grace_waives_the_floor_and_not_the_missing_verdict(tmp_path) -> None:
    """A candidate with no score has a failed render behind it rather than a low
    opinion, and there is no opinion for a waiver to overrule."""
    run = walk(tmp_path, scorer=FixedScorer(None), limits=Limits(plane_grace_rungs=5))
    root = plane_root(run, tmp_path)

    row = gate_survivors(run, root, [2])[0]
    assert row["fate"] == ledger_module.NOT_ADMITTED
    assert row["grace"] is True and row["cleared_junk"] is False
    assert run.tally["not_admitted:no_score"] == 1
    assert "grace:rescued" not in run.tally


def test_booking_stays_at_the_good_floor_inside_the_grace(tmp_path) -> None:
    """Grace is expansion-only. A graced rung reaches the frontier; only the good
    floor puts anything in the books, and it is unchanged at every rung."""
    run = walk(tmp_path, scorer=FixedScorer(0.9), limits=Limits(plane_grace_rungs=5))
    root = plane_root(run, tmp_path)

    rows = gate_survivors(run, root, [2, 9])
    assert [row["fate"] for row in rows] == [ledger_module.SURVIVED] * 2
    assert [row["cleared_junk"] for row in rows] == [True, True]
    assert run.tally["tier:admitted"] == 2 and "grace:rescued" not in run.tally


def test_a_gate_survivor_under_a_plane_root_records_its_rung_and_its_raw_verdict(
    tmp_path,
) -> None:
    """The measurement the grace buys: share clearing the junk floor at each rung
    below a plane root, which is what a depth-aware floor would be shaped from."""
    run = walk(tmp_path, scorer=FixedScorer(0.01), limits=Limits(plane_grace_rungs=2))
    root = plane_root(run, tmp_path)
    gate_survivors(run, root, [2, 2, 3, 4])

    table = {name: count for name, count in run.tally.items() if name.startswith("plane_rung:")}
    assert table == {
        "plane_rung:01:survivors": 2,
        "plane_rung:01:graced": 2,
        "plane_rung:01:rescued": 2,
        "plane_rung:02:survivors": 1,
        "plane_rung:02:graced": 1,
        "plane_rung:02:rescued": 1,
        "plane_rung:03:survivors": 1,
    }, "no cleared_junk anywhere: this scorer is below the floor at every rung"


def test_the_run_header_states_the_grace_it_walked_under(tmp_path) -> None:
    """A ledger is read against its own configuration, and the depth policy is
    part of it: two runs of one seed under different N are different runs."""
    run = walk(tmp_path, limits=Limits(plane_grace_rungs=3))
    run.ledger.close()
    header = ledger_module.read(run.ledger.path)[0]
    assert header["limits"]["plane_grace_rungs"] == 3


def test_the_null_scorer_admits_on_the_structural_gates_alone() -> None:
    """A real policy, not a placeholder: it is the walk the first labels get
    collected from, and `None` means no opinion rather than no score."""
    scorer = NullScorer()
    candidate = {"fate": "survived"}
    assert scorer.score(candidate) is None
    assert scorer.admits(candidate, None) is True


def test_the_gates_travel_to_the_engine_as_the_engine_names_them() -> None:
    """The two sides have to agree about what a gate is called, and the wire
    format is where that agreement is written down."""
    wire = Gates().wire()
    assert wire["interior_cap"] == 0.30
    assert set(wire) == {
        "interior_cap",
        "occupancy_floor",
        "occupancy_at_first_rung",
        "band",
        "min_width",
    }
    assert set(wire["band"]) == {"spread_min", "escape_median_min"}
    assert wire["min_width"] == 1e-9
