"""The solver: what its rows say, what its objective prefers, and what it refuses.

Almost everything here runs on **synthetic candidates**, which is the point of
[`solve.Candidate`] being a thin value: a constraint is arithmetic over the
ledger's fields, and a test that had to render a picture to check that two
candidates at one location cannot both be seated would be a test nobody runs.

The two rules that genuinely read pixels — the diversity radius and the group cap
— are exercised through a [`Pairs`] whose distances come from a table. That is
not a weakening: [`solve.Pairs.violations`] is the code under test and the
signature it would otherwise make is [`pixel_clouds.of_picture`], which has its
own guards. The slow lane runs the real thing over the tracked pool.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers.curation import candidate_ledger, ceiling, solve

pytest.importorskip("scipy", reason="the solve leg needs SciPy's HiGHS binding")


# --------------------------------------------------------------------------- #
# Building a program out of nothing.
# --------------------------------------------------------------------------- #
def candidate(
    key,
    *,
    location=None,
    score=0.9,
    mode="smooth",
    group=None,
    cells=(),
    families=(),
    partition="mandelbrot",
    kind="smooth_render",
):
    """One synthetic candidate. Its own place and its own palette group unless a
    test says otherwise, so a test about one rule is not silently about another."""
    return solve.Candidate(
        key=str(key),
        location=str(location if location is not None else key),
        partition=partition,
        mode=mode,
        group=str(group if group is not None else f"map:{key}"),
        kind=kind,
        cells=tuple(cells),
        families=tuple(families),
        score=float(score),
        p_ge3=float(score),
        picture=f"artifacts/{key}.jpg",
    )


def program_of(candidates, n, modes=("smooth", "stripe"), targets=None, floor=1):
    """A program at `n`, with an **artificial** mode floor of one by default.

    `solve.mode_floor` is `floor(n / 100)`, so every program small enough to solve
    in a unit test asks for no floors at all and stage 3's rows would never be
    exercised. `floor=1` is what these tests are about; `floor=None` reads the
    real one, and one test below pins that it is zero at these sizes.
    """
    return solve.Program(
        candidates=list(candidates),
        n=int(n),
        rule=solve.rule_for(targets),
        modes=tuple(modes),
        targets=dict(targets or {}),
        floor=floor,
    )


class Table(solve.Pairs):
    """A [`Pairs`] whose distances are a lookup, so a test needs no pictures.

    It replaces [`solve.Pairs.measure`] and nothing else, so everything above it —
    the cache, the two thresholds, the violation list — is the shipped code.
    """

    def __init__(self, candidates, distances, far=1.0):
        super().__init__(candidates)
        self.table = {tuple(sorted(pair)): float(value) for pair, value in distances.items()}
        self.far = float(far)
        self.seen: set = set()

    def measure(self, order, screen=True):
        self.seen.update(order)
        for at, one in enumerate(order):
            for other in order[at + 1 :]:
                pair = (min(one, other), max(one, other))
                if pair in self._distance:
                    continue
                self._distance[pair] = self.table.get(pair, self.far)
                self.measured += 1

    def paid(self):
        """Everything asked about so far — what the real one holds a signature of."""
        return sorted(self.seen)


class Clouds(solve.Pairs):
    """A [`Pairs`] whose *signatures* are synthetic, so everything above the
    picture is the shipped code — the bound, the screen, the exact fallback.

    [`Table`] replaces the whole seam and is what a test about which rule refuses
    a pair wants. This replaces one method below it, and is what a test about the
    bound wants: a bound that agreed with a lookup table would be testing the
    lookup table."""

    def __init__(self, candidates, offsets):
        super().__init__(candidates)
        self.offsets = list(offsets)

    def signature(self, at):
        import numpy

        from fractal_wallpapers.palettes import groups

        if at not in self._signatures:
            made = numpy.full(
                groups.QUANTILES * groups.DIRECTIONS, self.offsets[at], dtype=numpy.float32
            )
            self.made += 1
            self._reduced.setdefault(at, solve.reduce_signature(made))
            self._signatures[at] = made
        return self._signatures[at]


# --------------------------------------------------------------------------- #
# The pool.
# --------------------------------------------------------------------------- #
def ledger_row(key, **overrides):
    row = {
        "key": key,
        "partition": "mandelbrot",
        "location": {"key": f"place-{key}"},
        "recipe": {"mode": "smooth"},
        "palette_group": "map:one",
        "at_candidate_regime": True,
        "colour": {"cells": ["dark_vivid_blue"], "families": ["blue"]},
        "picture": f"artifacts/{key}.jpg",
        "rejected": None,
    }
    row.update(overrides)
    return row


#: The judge these fixtures are read on. The sidecar is keyed on the artifact and
#: [`solve.pool`] joins on one, so a fixture that left it off would be testing a
#: join that cannot happen.
ARTIFACT = "judge-under-test"


def score_row(key, p_ge4=0.9, artifact=ARTIFACT):
    return {
        "recipe_key": key,
        "p_ge4": p_ge4,
        "p_ge3": 0.99,
        "head": "smooth_render",
        "judge_artifact": artifact,
    }


def test_pool_refuses_a_rejected_row_and_says_so():
    """A person's rejection travels on the ledger row so a solver honours it."""
    rows = [ledger_row("a"), ledger_row("b", rejected={"by": "matt"})]
    scores = [score_row("a"), score_row("b")]
    candidates, refused = solve.pool(
        rows=rows, scores=scores, artifact=ARTIFACT, log=lambda *_: None
    )
    assert [c.key for c in candidates] == ["a"]
    assert refused["rejected"] == 1


@pytest.mark.parametrize(
    ("overrides", "counter"),
    [
        ({"at_candidate_regime": False}, "off_regime"),
        ({"picture": None}, "no_picture"),
    ],
)
def test_pool_refuses_what_no_rule_could_evaluate(overrides, counter):
    rows = [ledger_row("a"), ledger_row("b", **overrides)]
    candidates, refused = solve.pool(
        rows=rows,
        scores=[score_row("a"), score_row("b")],
        artifact=ARTIFACT,
        log=lambda *_: None,
    )
    assert [c.key for c in candidates] == ["a"]
    assert refused[counter] == 1


def test_pool_refuses_a_row_with_no_score_apart_from_the_others():
    """Nothing to rank it by is a different fact from losing on the rank."""
    rows = [ledger_row("a"), ledger_row("b")]
    candidates, refused = solve.pool(
        rows=rows, scores=[score_row("a")], artifact=ARTIFACT, log=lambda *_: None
    )
    assert [c.key for c in candidates] == ["a"]
    assert refused["no_score"] == 1


def test_pool_comes_back_strongest_first():
    rows = [ledger_row("a"), ledger_row("b"), ledger_row("c")]
    scores = [score_row("a", 0.2), score_row("b", 0.9), score_row("c", 0.5)]
    candidates, _refused = solve.pool(
        rows=rows, scores=scores, artifact=ARTIFACT, log=lambda *_: None
    )
    assert [c.key for c in candidates] == ["b", "c", "a"]


def test_an_empty_ledger_refuses_rather_than_solving_nothing():
    with pytest.raises(solve.SolveRefused, match="backfill"):
        solve.pool(rows=[], scores=[], log=lambda *_: None)


# --------------------------------------------------------------------------- #
# The objective.
# --------------------------------------------------------------------------- #
def test_the_floor_stage_beats_the_sum_stage():
    """The whole reason the objective is lexicographic rather than a weighted sum.

    Two seats, and `star` is cut against both of the middling pair, so seating it
    means seating `partner` beside it. On the **sum** that pair wins, 1.53 against
    1.51; on the **floor** it loses badly, 0.53 against 0.75. The floor is asked
    first, so the middling pair is what comes back — which is the whole claim: a
    gallery is only as good as its worst seat, and a sum cannot say so.

    Note what it takes to make the two disagree at all. Under cardinality alone
    the best `n` by score are both the max-sum set and the max-min set; they only
    part company once a row **couples** the choices, which is what the cut does
    here and what the location rule, the ceiling and the radius do on real
    material.
    """
    candidates = [
        candidate("star", score=1.00),
        candidate("partner", score=0.53),
        candidate("mid_a", score=0.76),
        candidate("mid_b", score=0.75),
    ]
    program = program_of(candidates, 2, modes=("smooth",))
    program.cuts = [(0, 2), (0, 3)]
    answer = solve.lexicographic(program, log=lambda *_: None)
    assert answer["feasible"]
    assert sorted(candidates[at].key for at in answer["chosen"]) == ["mid_a", "mid_b"]
    assert answer["values"]["floor"] == pytest.approx(0.75)
    assert answer["values"]["sum"] == pytest.approx(1.51)


def test_stage_one_counts_the_bar_before_it_looks_at_the_scores():
    """Three seats: two just over the bar beat one far above it and two far under."""
    candidates = [
        candidate("best", score=1.0),
        candidate("over_a", score=solve.Q4_BAR + 0.01),
        candidate("over_b", score=solve.Q4_BAR + 0.02),
        candidate("under_a", score=solve.Q4_BAR - 0.01),
        candidate("under_b", score=solve.Q4_BAR - 0.02),
    ]
    answer = solve.lexicographic(program_of(candidates, 3), log=lambda *_: None)
    assert answer["values"]["above_bar"] == 3
    assert sorted(candidates[at].key for at in answer["chosen"]) == ["best", "over_a", "over_b"]


def test_the_tie_break_cannot_outweigh_one_seat():
    """The safety argument for [`solve.TIE_BREAK`], as arithmetic.

    Stage 1 adds `(TIE_BREAK / n) * score` per column so HiGHS is not choosing
    between fifteen thousand identical answers. Every score is a probability, so
    the whole bonus over `n` seats is at most `TIE_BREAK` — and it can only move
    the count it hands on if that reaches one.
    """
    assert 0.0 < solve.TIE_BREAK < 1.0


def test_the_mode_floor_is_soft_and_is_paid_for():
    """A mode with nothing in the pool is a penalty, never an infeasibility."""
    candidates = [candidate("a", score=0.9), candidate("b", score=0.8)]
    program = program_of(candidates, 2, modes=("smooth", "itinerary"))
    answer = solve.lexicographic(program, log=lambda *_: None)
    assert answer["feasible"]
    assert answer["values"]["modes_missing"] == ["itinerary"]
    assert answer["values"]["penalty_paid"] == pytest.approx(2 * solve.PENALTY_PER_SEAT)


def test_the_mode_penalty_decides_a_seat_the_score_is_indifferent_about():
    candidates = [
        candidate("smooth_a", score=0.99, mode="smooth"),
        candidate("smooth_b", score=0.98, mode="smooth"),
        candidate("striped", score=0.98, mode="stripe"),
    ]
    program = program_of(candidates, 2, modes=("smooth", "stripe"))
    answer = solve.lexicographic(program, log=lambda *_: None)
    assert sorted(candidates[at].mode for at in answer["chosen"]) == ["smooth", "stripe"]
    assert answer["values"]["modes_missing"] == []


def test_the_mode_penalty_cannot_buy_a_mode_at_the_cost_of_the_floor():
    """Stage 3 is where the penalty lives, and stage 2 has already been frozen.

    The ordering is deliberate and this is what it costs: a gallery whose whole
    stripe supply sits below the floor the smooth candidates reach seats no
    stripe, pays the penalty, and reports the mode as missing. That is the
    accounting; recovering it is a decision about the floor, not about the penalty.
    """
    candidates = [
        candidate("smooth_a", score=0.99, mode="smooth"),
        candidate("smooth_b", score=0.99, mode="smooth"),
        candidate("striped", score=0.98, mode="stripe"),
    ]
    program = program_of(candidates, 2, modes=("smooth", "stripe"))
    answer = solve.lexicographic(program, log=lambda *_: None)
    assert sorted(candidates[at].mode for at in answer["chosen"]) == ["smooth", "smooth"]
    assert answer["values"]["floor"] == pytest.approx(0.99)
    assert answer["values"]["modes_missing"] == ["stripe"]


# --------------------------------------------------------------------------- #
# The hard rows.
# --------------------------------------------------------------------------- #
def test_one_wallpaper_per_location_is_absolute():
    candidates = [
        candidate("a", location="one", score=1.0),
        candidate("b", location="one", score=0.99),
        candidate("c", location="two", score=0.10),
    ]
    answer = solve.lexicographic(program_of(candidates, 2), log=lambda *_: None)
    assert sorted(candidates[at].location for at in answer["chosen"]) == ["one", "two"]


def test_the_colour_ceiling_is_a_count_and_not_a_prefix_rule():
    """At n=20 a cell's allowance is one, and the best two of a cell cannot both sit.

    The improvement over the walk stated as a test: nothing here depends on the
    order the candidates arrived in, so the seat the ceiling refuses is decided
    by the objective rather than by whichever picture happened to be seated first.
    """
    rule = solve.rule_for()
    assert rule.allowed("dark_vivid_blue", 20) == 1
    candidates = [
        candidate("blue_a", score=1.00, cells=("dark_vivid_blue",), families=("blue",)),
        candidate("blue_b", score=0.99, cells=("dark_vivid_blue",), families=("blue",)),
        candidate("red", score=0.10, cells=("dark_vivid_red",), families=("red",)),
    ]
    assert rule.allowed("dark_vivid_blue", 2) == 1
    answer = solve.lexicographic(program_of(candidates, 2), log=lambda *_: None)
    seated = sorted(candidates[at].key for at in answer["chosen"])
    assert seated == ["blue_a", "red"]


def test_a_candidate_dominant_in_nothing_cannot_be_refused_by_the_ceiling():
    """The ceiling acts on dominance, so a colourless picture is outside it."""
    candidates = [
        candidate("blue", score=1.0, cells=("dark_vivid_blue",), families=("blue",)),
        candidate("grey_a", score=0.9),
        candidate("grey_b", score=0.8),
    ]
    answer = solve.lexicographic(program_of(candidates, 3), log=lambda *_: None)
    assert len(answer["chosen"]) == 3


def test_a_target_raises_the_allowance_of_the_cell_it_names():
    """Otherwise a demand would be refused by the ceiling it asked for."""
    plain = solve.rule_for()
    asked = solve.rule_for({"dark_vivid_lime": 0.5})
    assert plain.allowed("dark_vivid_lime", 20) == 1
    assert asked.allowed("dark_vivid_lime", 20) == 21
    assert asked.allowed("lime", 20) > plain.allowed("lime", 20)


# --------------------------------------------------------------------------- #
# The pairwise rules.
# --------------------------------------------------------------------------- #
def test_the_group_cap_is_the_larger_of_the_two_thresholds():
    """One test, two thresholds — so a pair is measured once whichever names it."""
    candidates = [
        candidate("a", group="map:one"),
        candidate("b", group="map:one"),
        candidate("c", group="map:two"),
    ]
    pairs = Table(candidates, {})
    assert pairs.rule_for(0, 1) == ("group_cap", max(ceiling.TAU, ceiling.TAU_GROUP))
    assert pairs.rule_for(0, 2) == ("diversity", ceiling.TAU)


def test_a_pair_between_the_two_thresholds_is_refused_only_inside_one_group():
    between = (ceiling.TAU + ceiling.TAU_GROUP) / 2
    same = [candidate("a", group="map:one"), candidate("b", group="map:one")]
    apart = [candidate("a", group="map:one"), candidate("b", group="map:two")]
    assert Table(same, {(0, 1): between}).violations([0, 1])
    assert not Table(apart, {(0, 1): between}).violations([0, 1])


def test_the_cutting_plane_generates_only_the_pairs_it_saw():
    """The whole economy of the loop: rows for the incumbent, not for the pool."""
    candidates = [
        candidate("a", score=1.00),
        candidate("b", score=0.99),
        candidate("c", score=0.50),
    ]
    program = program_of(candidates, 2)
    pairs = Table(candidates, {(0, 1): 0.001})
    answer = solve.cutting_plane(program, pairs, log=lambda *_: None)
    assert answer["feasible"]
    assert answer["cuts"] == 1
    assert sorted(candidates[at].key for at in answer["chosen"]) == ["a", "c"]
    assert answer["generated"][0]["rule"] == "diversity"


def test_an_incumbent_that_violates_nothing_ends_the_loop_in_one_round():
    candidates = [candidate("a", score=1.0), candidate("b", score=0.9)]
    answer = solve.cutting_plane(
        program_of(candidates, 2), Table(candidates, {}), log=lambda *_: None
    )
    assert answer["cuts"] == 0
    assert len(answer["rounds"]) == 1


def test_a_master_that_turns_infeasible_ends_the_loop_rather_than_looping():
    """Cuts are valid rows, so an infeasible master is an infeasible program."""
    candidates = [candidate("a", score=1.0), candidate("b", score=0.9)]
    program = program_of(candidates, 2)
    answer = solve.cutting_plane(program, Table(candidates, {(0, 1): 0.0}), log=lambda *_: None)
    assert not answer["feasible"]
    assert answer["cuts"] == 1


def test_the_loop_stops_on_a_wall_budget_and_says_it_had_no_answer():
    """A round cap bounds rounds; above n=60 the rounds and the MILP inside each of
    them both grow, so the ladder carries a clock as well."""
    candidates = [candidate(str(at), score=1.0 - at / 100) for at in range(4)]
    program = program_of(candidates, 2)
    every = {(one, other): 0.0 for one in range(4) for other in range(one + 1, 4)}
    with pytest.raises(solve.SolveRefused, match="wall budget"):
        solve.cutting_plane(program, Table(candidates, every), deadline=-1.0, log=lambda *_: None)


def test_the_loop_refuses_rather_than_spinning_forever():
    """The round cap fires, and says how many pairs were standing when it did."""
    candidates = [candidate(str(at), score=1.0 - at / 100) for at in range(6)]
    program = program_of(candidates, 2)
    every = {(one, other): 0.0 for one in range(6) for other in range(one + 1, 6)}
    with pytest.raises(solve.SolveRefused, match="did not converge in 1 rounds"):
        solve.cutting_plane(program, Table(candidates, every), rounds=1, log=lambda *_: None)


def test_a_round_generates_every_pair_it_has_paid_for_and_not_only_the_seated():
    """The bound made a wide screen free, so a round no longer costs a round to
    learn one pair. Two seats, four candidates all too close: the first round cuts
    the seated pair AND the pairs among everything else it has a signature of."""
    candidates = [candidate(str(at), score=1.0 - at / 100) for at in range(4)]
    program = program_of(candidates, 2)
    every = {(one, other): 0.0 for one in range(4) for other in range(one + 1, 4)}
    pairs = Table(candidates, every)
    pairs.measure([0, 1, 2, 3])
    answer = solve.cutting_plane(program, pairs, rounds=2, log=lambda *_: None)
    assert not answer["feasible"], "every pair is a twin, so two seats cannot be filled"
    assert answer["rounds"][0]["rows_added"] == 6, "all six pairs, in one round"
    assert answer["rounds"][0]["violated_pairs"] == 1, "but only one of them is seated"


# --------------------------------------------------------------------------- #
# Infeasibility as a shortage list.
# --------------------------------------------------------------------------- #
def test_a_target_nothing_carries_is_short_by_the_whole_demand():
    candidates = [candidate("a", score=1.0), candidate("b", score=0.9)]
    program = program_of(candidates, 2, targets={"dark_vivid_lime": 1.0})
    assert not solve.relaxation(program, log=lambda *_: None)["feasible"]
    read = solve.shortage(program, log=lambda *_: None)
    assert read["by_block"]["colour_target"]["short_by"] == pytest.approx(2.0)
    assert read["by_block"]["colour_target"]["worst"][0]["about"] == "dark_vivid_lime"


def test_the_shortage_list_says_how_many_and_from_which_partitions():
    """The work order: the number sizes the hunt, the partitions launch it."""
    candidates = [
        candidate(
            "lime", score=0.9, partition="phoenix", cells=("dark_vivid_lime",), families=("lime",)
        ),
        candidate("blue_a", score=1.0, cells=("dark_vivid_blue",), families=("blue",)),
        candidate(
            "blue_b",
            score=0.8,
            cells=("dark_vivid_blue",),
            families=("blue",),
            location="elsewhere",
        ),
    ]
    program = program_of(candidates, 3, targets={"dark_vivid_lime": 1.0})
    read = solve.shortage(program, log=lambda *_: None)
    assert read["by_block"]["colour_target"]["short_by"] == pytest.approx(2.0)
    assert read["supply"]["dark_vivid_lime"]["partitions"] == {"phoenix": 1}


def test_the_deletion_filter_drops_a_block_that_is_not_in_the_conflict():
    """`cardinality` and `colour_target` conflict; the ceiling rows are bystanders."""
    candidates = [candidate("a", score=1.0), candidate("b", score=0.9)]
    program = program_of(candidates, 2, targets={"dark_vivid_lime": 1.0})
    blocks = solve.deletion_filter(program, log=lambda *_: None)
    assert "colour_target" in blocks
    assert "colour_ceiling_cells" not in blocks


def test_under_fill_fills_what_it_can_and_relaxes_nothing():
    """No fallback leg: the cardinality row alone moves, and nothing else does."""
    candidates = [
        candidate("a", location="one", score=1.0),
        candidate("b", location="one", score=0.9),
    ]
    program = program_of(candidates, 2)
    read = solve._under_fill(program, Table(candidates, {}), log=lambda *_: None)
    assert read["filled"] == 1
    assert read["unfilled"] == 1


# --------------------------------------------------------------------------- #
# What the answer reports.
# --------------------------------------------------------------------------- #
def test_the_distribution_reports_its_empties_and_not_only_its_fill():
    candidates = [candidate("a", mode="smooth"), candidate("b", mode="smooth", location="two")]
    program = program_of(candidates, 2, modes=("smooth", "stripe", "threads"))
    spread = solve.distribution(program, [0, 1])
    assert spread["modes"]["held"] == 1
    assert spread["modes"]["empty"] == ["stripe", "threads"]


def test_a_near_miss_names_the_row_that_refused_it():
    candidates = [
        candidate(
            "seated", location="one", score=1.0, cells=("dark_vivid_blue",), families=("blue",)
        ),
        candidate("same_place", location="one", score=0.99),
        candidate(
            "same_colour",
            location="two",
            score=0.98,
            cells=("dark_vivid_blue",),
            families=("blue",),
        ),
        candidate("twin", location="three", score=0.97),
        candidate("just_lost", location="four", score=0.96),
    ]
    program = program_of(candidates, 1)
    pairs = Table(candidates, {(0, 3): 0.001})
    misses = solve.near_misses(program, [0], pairs, count=4, log=lambda *_: None)
    assert [miss["why_not"] for miss in misses] == [
        "location_already_seated",
        "colour_ceiling_cell",
        "too_close_to_a_seat",
        "the_objective_preferred_another",
    ]
    assert set(solve.WHY_NOT) >= {miss["why_not"] for miss in misses}


def test_binding_reports_a_tight_row_per_block():
    candidates = [candidate("a", score=1.0), candidate("b", score=0.9, location="two")]
    program = program_of(candidates, 2)
    read = solve.binding(program, [0, 1])
    assert read["cardinality"]["tight"] == 1


def test_truncation_offers_the_strongest_places_first():
    candidates = [
        candidate("weak", location="w", score=0.1),
        candidate("strong", location="s", score=0.9),
        candidate("middling", location="m", score=0.5),
    ]
    assert solve.strongest_locations(candidates, 2) == ["s", "m"]
    assert len(solve.strongest_locations(candidates, None)) == 3
    assert [c.key for c in solve.within(candidates, {"s"})] == ["strong"]


# --------------------------------------------------------------------------- #
# The bound, and what it is allowed to settle.
# --------------------------------------------------------------------------- #
def signature_pair(seed):
    """Two signatures shaped the way the metric makes them, from a seeded draw."""
    import numpy

    from fractal_wallpapers.palettes import groups

    rng = numpy.random.default_rng(seed)
    size = groups.QUANTILES * groups.DIRECTIONS
    return (
        numpy.sort(rng.normal(size=size).astype(numpy.float32)),
        numpy.sort(rng.normal(0.3, 1.4, size=size).astype(numpy.float32)),
    )


@pytest.mark.parametrize("seed", range(6))
def test_the_bound_never_exceeds_the_distance_it_bounds(seed) -> None:
    """The whole claim. A prune whose premise is false is what this replaced, and
    the premise here is the triangle inequality and nothing weaker."""
    import numpy

    from fractal_wallpapers.palettes import groups, pixel_clouds

    one, other = signature_pair(seed)
    exact = pixel_clouds.distance(one, other)
    bound = float(
        numpy.abs(solve.reduce_signature(one) - solve.reduce_signature(other)).sum(
            dtype=numpy.float64
        )
        / (groups.DIRECTIONS * solve.BOUND_BLOCKS)
    )
    assert bound <= exact + 1e-9
    assert bound > 0.5 * exact, "and it is not so slack as to settle nothing"


def test_the_bound_at_one_block_is_the_distance_between_the_mean_colours() -> None:
    """Which is what the design predicted the metric would admit. Four blocks is
    that statement per band of the cloud; one block is the statement itself."""
    from fractal_wallpapers.palettes import groups

    one, _other = signature_pair(0)
    grid = one.reshape(groups.QUANTILES, groups.DIRECTIONS)
    assert solve.reduce_signature(one).mean(axis=0) == pytest.approx(grid.mean(axis=0), abs=1e-5)


def test_a_pair_the_bound_settles_is_never_measured() -> None:
    """No signature made, no distance stored, and the pair reads as clearing."""
    import numpy

    from fractal_wallpapers.palettes import groups

    candidates = [candidate("a"), candidate("b")]
    pairs = solve.Pairs(candidates)
    shape = (solve.BOUND_BLOCKS, groups.DIRECTIONS)
    pairs._reduced[0] = numpy.zeros(shape, dtype=numpy.float32)
    pairs._reduced[1] = numpy.full(shape, 1.0, dtype=numpy.float32)
    pairs.measure([0, 1])
    assert pairs.made == 0, "a settled pair opens no picture"
    assert (0, 1) not in pairs._distance
    assert pairs.settled == 1
    assert not pairs.violates(0, 1)
    assert pairs.price()["settled_share"] == 1.0


def test_the_nearest_pairs_are_exact_even_where_the_bound_settled_most() -> None:
    """The radius's calibration instrument reports measurements and never bounds,
    and it reaches them without measuring what the bound already settled: the
    walk is in bound order, and it stops when the next bound is past the worst
    distance kept."""
    candidates = [candidate(str(at)) for at in range(5)]
    pairs = Table(candidates, {(0, 1): 0.01, (0, 2): 0.02}, far=0.9)
    wanted = [(one, other) for one in range(5) for other in range(one + 1, 5)]
    for pair in wanted[2:]:
        pairs._lower[pair] = 0.9
    assert [gap for _pair, gap in pairs.closest(wanted, 2)] == [0.01, 0.02]
    assert pairs.measured == 2, "the eight the bound settled were never opened"


def test_a_settled_pair_still_answers_when_a_caller_asks_for_the_number() -> None:
    """Settled means *proven to clear its rule* and not *known to be this far
    apart*, so the contact sheet asking a settled pair for its distance has to get
    a measurement rather than a KeyError."""
    candidates = [candidate("a"), candidate("b")]
    pairs = Clouds(candidates, [0.0, 0.5])
    pairs.measure([0, 1])
    assert pairs.settled == 1 and not pairs.measured_pair(0, 1)
    assert pairs.distance(0, 1) == pytest.approx(0.5)
    assert pairs.measured == 1


def test_the_screen_and_the_metric_agree_about_which_pairs_violate() -> None:
    """Over a spread of separations either side of the radius: nothing the bound
    settles is a violation, and everything the metric refuses is still refused."""
    offsets = [at * 0.05 for at in range(12)]
    candidates = [candidate(str(at)) for at in range(12)]
    every = list(range(12))
    screened = Clouds(candidates, offsets)
    exact = Clouds(candidates, offsets)
    for one in every:
        for other in every[one + 1 :]:
            exact.measure([one, other], screen=False)
    assert {row["pair"] for row in screened.violations(every)} == {
        row["pair"] for row in exact.violations(every)
    }
    assert screened.settled > screened.measured, "and most were never measured at all"


# --------------------------------------------------------------------------- #
# The greedy seed.
# --------------------------------------------------------------------------- #
def test_the_seed_keeps_every_pair_it_refused_as_a_row() -> None:
    """A pair under its threshold can never both be seated, whoever noticed it —
    so a greedy walk's refusals are valid rows however bad its own answer is."""
    candidates = [candidate(str(at), score=1.0 - at / 100) for at in range(4)]
    program = program_of(candidates, 2)
    pairs = Table(candidates, {(0, 1): 0.0, (0, 2): 0.0}, far=0.9)
    read = solve.seed_greedily(program, pairs, log=lambda *_: None)
    assert read["seats"] == 2
    assert set(read["pairs"]) == {(0, 1), (0, 2)}
    assert read["feasible"] and read["floor"] == pytest.approx(0.97)


def test_a_seed_that_breaks_a_row_it_does_not_read_is_kept_only_for_its_cuts() -> None:
    """A greedy walk seats by score; a colour target is a demand, and nothing in
    the walk asks about it. The incumbent is thrown away and the cuts are not."""
    candidates = [
        candidate("a", score=1.0),
        candidate("b", score=0.9, location="two"),
        candidate("c", score=0.8, location="three", cells=("dark_vivid_lime",)),
    ]
    program = program_of(candidates, 2, targets={"dark_vivid_lime": 1.0})
    read = solve.seed_greedily(
        program, Table(candidates, {(0, 1): 0.0}, far=0.9), log=lambda *_: None
    )
    assert not read["feasible"], "it seated no lime, and the target demands two"
    assert read["pairs"] == [(0, 1)]


def test_a_seed_holding_every_seat_above_the_bar_proves_stage_one() -> None:
    """`n` seats cannot hold more than `n` above the bar, so a seed that holds `n`
    attains the optimum and branch-and-bound has nothing left to prove."""
    candidates = [candidate(str(at), score=1.0) for at in range(4)]
    program = program_of(candidates, 2)
    seed = {"feasible": True, "chosen": [0, 1], "above_bar": 2, "floor": 1.0}
    answer = solve.lexicographic(program, seed=seed, log=lambda *_: None)
    assert answer["values"]["above_bar"] == 2
    assert "the seed" in answer["values"]["stage_one_from"]


def test_stage_two_reaches_only_what_an_incumbent_admits() -> None:
    """The whole cost of a round was stage 2 over every column in the ledger. An
    incumbent's own floor is a proof that the ones below it cannot be seated."""
    candidates = [candidate("a", score=1.0), candidate("b", score=0.9, location="two")]
    candidates += [candidate(str(at), score=0.2, location=str(at)) for at in range(6)]
    program = program_of(candidates, 2)
    answer = solve.lexicographic(program, log=lambda *_: None)
    assert answer["values"]["columns_free"] == 2, "the six no floor can reach are fixed off"
    assert answer["values"]["floor"] == pytest.approx(0.9)
    assert sorted(answer["chosen"]) == [0, 1]


def test_the_column_fix_does_not_move_the_answer() -> None:
    """The claim the fix stands on, on a program small enough to state by hand:
    an incumbent that clears the same count cannot rule out a better floor."""
    candidates = [
        candidate("a", score=0.99),
        candidate("b", score=0.98, location="two"),
        candidate("c", score=0.50, location="three"),
    ]
    program = program_of(candidates, 2)
    answer = solve.lexicographic(program, log=lambda *_: None)
    assert answer["values"]["floor"] == pytest.approx(0.98)
    assert sorted(answer["chosen"]) == [0, 1]


def test_an_infeasibility_the_lp_cannot_see_is_named_as_one_and_not_as_a_shortage() -> None:
    """Four candidates no two of which may sit together, and two seats. Every
    linear row is met at once — the LP puts a quarter-seat in each — so nothing is
    short, and a readout saying "0.0 candidates short over six irreducible blocks"
    would be a work order nobody can spend."""
    candidates = [candidate(str(at), score=1.0 - at / 100) for at in range(4)]
    program = program_of(candidates, 2)
    program.cuts += [(one, other) for one in range(4) for other in range(one + 1, 4)]
    assert solve.relaxation(program, log=lambda *_: None)["feasible"]
    assert not solve.lexicographic(program, log=lambda *_: None)["feasible"]
    read = solve.shortage(program, log=lambda *_: None)
    assert read["total_slack"] == 0.0
    assert read["irreducible_blocks"] == [], "the filter is over the LP and the LP is fine"
    assert "NOT a supply shortage" in read["verdict"]
    assert "6 pairwise row(s)" in read["verdict"]


def test_a_real_shortage_still_reads_as_one() -> None:
    candidates = [candidate("a", score=1.0), candidate("b", score=0.9, location="two")]
    program = program_of(candidates, 2, targets={"dark_vivid_lime": 1.0})
    read = solve.shortage(program, log=lambda *_: None)
    assert read["total_slack"] == 2.0
    assert "colour_target" in read["irreducible_blocks"]
    assert "a hunt is what spends it" in read["verdict"]


# --------------------------------------------------------------------------- #
# The constants, and where they are read from.
# --------------------------------------------------------------------------- #
def test_the_q4_bar_is_the_advisory_and_says_it_is_not_a_crossover():
    from fractal_wallpapers.curation import floors

    assert solve.Q4_BAR == floors.RELEASE_ADVISORY
    assert "NOT a measured crossover" in solve.Q4_BASIS


def test_the_diversity_distance_is_the_twin_threshold_and_has_only_one_name():
    """`solve.RADIUS` is retired. Two spellings of one fact is a silent null."""
    assert not hasattr(solve, "RADIUS")
    assert "RADIUS" not in solve.__all__
    assert ceiling.TAU < ceiling.TAU_GROUP


def test_the_mode_floor_scales_with_the_gallery_and_is_zero_below_a_hundred():
    assert solve.mode_floor(20) == 0
    assert solve.mode_floor(99) == 0
    assert solve.mode_floor(150) == 1
    assert solve.mode_floor(1000) == 10
    assert not hasattr(solve, "MODE_FLOOR")


def test_a_program_reads_the_real_floor_unless_a_caller_puts_one_back():
    """The artificial floor is a debug affordance and the record says which it was."""
    plain = program_of([candidate("a")], 20, floor=None)
    assert plain.mode_floor == 0
    assert plain.config()["mode_floor_artificial"] is False
    assert program_of([candidate("a")], 20).mode_floor == 1
    assert program_of([candidate("a")], 20).config()["mode_floor_artificial"] is True


def test_a_lensless_rule_carries_the_constants_and_refuses_to_seat():
    """[`solve`] wants the allowance arithmetic without the pictures; a seating
    wants both, and says so rather than failing at the first candidate."""
    rule = solve.rule_for()
    assert rule.allowed("rose", 20) == 4
    with pytest.raises(RuntimeError, match="needs a Lens"):
        rule.begin(20)


def test_a_record_round_trips_through_its_own_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(solve, "solve_dir", lambda name: tmp_path / str(name))
    written = solve.write_record("pilot", {"schema": solve.SCHEMA, "feasible": True})
    assert written.read_text(encoding="utf-8").endswith("\n")
    assert solve.read_record("pilot")["feasible"] is True
    with pytest.raises(solve.SolveRefused, match="no solve called"):
        solve.read_record("nothing")


# --------------------------------------------------------------------------- #
# The tracked pool. Real rows, real pictures, real HiGHS.
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def tracked_pool():
    if not candidate_ledger.rows_path().is_file():
        pytest.skip("the candidate ledger has not been backfilled on this machine")
    candidates, _refused = solve.pool(log=lambda *_: None)
    return candidates


@pytest.mark.slow
def test_the_tracked_pool_solves_and_honours_every_rule(tracked_pool):
    """One small real solve, end to end: the store, the pictures, and HiGHS.

    Five seats rather than twenty, because the guard is that every rule is
    honoured on real material and not that a particular gallery comes back — and
    a five-seat solve over the whole pool costs seconds where twenty costs half a
    minute.
    """
    from fractal_wallpapers import engine

    program = solve.Program(
        candidates=tracked_pool,
        n=5,
        rule=solve.rule_for(),
        modes=tuple(engine.production_modes()),
    )
    pairs = solve.Pairs(tracked_pool)
    answer = solve.cutting_plane(program, pairs, log=lambda *_: None)
    assert answer["feasible"]
    seated = [tracked_pool[at] for at in answer["chosen"]]
    assert len({c.location for c in seated}) == 5
    for at, one in enumerate(answer["chosen"]):
        for other in answer["chosen"][at + 1 :]:
            assert pairs.distance(one, other) >= pairs.rule_for(one, other)[1]
    for cell in {name for c in seated for name in c.cells}:
        held = sum(1 for c in seated if cell in c.cells)
        assert held <= program.rule.allowed(cell, 5)


@pytest.mark.slow
def test_every_candidate_the_solver_may_seat_has_its_picture(tracked_pool):
    """The pool's own claim. A candidate no pairwise rule can read is refused at
    [`solve.pool`], so a missing picture here is a store that moved under it."""
    missing = [c.key for c in tracked_pool[:400] if not solve.picture_of(c).is_file()]
    assert missing == []
