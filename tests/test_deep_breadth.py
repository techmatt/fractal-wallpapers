"""The two things that make a deep run spend its hours on breadth.

`deep_run1` was given eight hours and spent two hours ten, and 741 of its
admissions came off 15 of its 48 roots. Two changes answer those separately —
seats sized against the wall budget and topped up inside the run, and a cap on
what one lineage may book — and they are tested together because they are one
argument: the budget buys somewhere else for the walk time to go, and the cap is
what sends it there.

Nothing here needs the engine. The projection is arithmetic, the sourcing memory
is set bookkeeping, and the cap is exercised by handing the walk a report the
engine would have made.
"""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from fractal_wallpapers import cli
from fractal_wallpapers.curation import pacing
from fractal_wallpapers.deep import budget
from fractal_wallpapers.deep import roots as roots_module
from fractal_wallpapers.deep import run as deep_run
from fractal_wallpapers.discovery import ledger as ledger_module
from fractal_wallpapers.discovery import walk as walk_module

EIGHT_HOURS = 8 * 3600.0

#: What `deep_run1` actually seated, for the comparisons the report is quoted
#: against. Thirty-two, by hand, against the same eight hours.
DEEP_RUN1_SEATS = 32


# --------------------------------------------------------------------------- #
# The projection.
# --------------------------------------------------------------------------- #
def test_an_eight_hour_budget_buys_a_seat_count_rather_than_a_guess() -> None:
    plan = budget.project(EIGHT_HOURS)
    costs = budget.Costs()
    # The three legs and nothing else: a seat is what it costs to source, to
    # walk and to draw the gallery frames its admissions earn.
    assert plan.per_seat == pytest.approx(
        costs.sourcing_per_seat + costs.walk_per_seat + costs.gallery_per_seat
    )
    assert plan.seats == int(plan.room // plan.per_seat)
    # The whole point of the change, as a number: the same budget `deep_run1`
    # took 32 seats out of buys several times that.
    assert plan.seats > 5 * DEEP_RUN1_SEATS
    assert plan.record()["nodes"] > 2000


def test_the_gallery_is_most_of_a_seat_and_a_walk_only_run_says_so_out_loud() -> None:
    costs = budget.Costs()
    assert costs.gallery_per_seat > costs.sourcing_per_seat + costs.walk_per_seat
    walking = budget.project(EIGHT_HOURS, gallery=False)
    watching = budget.project(EIGHT_HOURS, gallery=True)
    # Not a saving — a different piece of work. The walk-only run buys far more
    # seats because it has promised nobody a picture of what they found.
    assert walking.seats > 5 * watching.seats
    assert walking.per_seat == pytest.approx(costs.sourcing_per_seat + costs.walk_per_seat)


def test_both_margins_come_off_and_neither_stands_in_for_the_other() -> None:
    """One scales with the work and one does not, which is why there are two."""
    assert budget.usable(EIGHT_HOURS) == pytest.approx(
        EIGHT_HOURS * (1.0 - budget.MARGIN_SHARE) - budget.FIXED_RESERVE
    )
    # A fixed reserve alone would be a rounding error at eight hours; a share
    # alone would let a budget under the reserve plan real work.
    assert budget.usable(EIGHT_HOURS) < EIGHT_HOURS * (1.0 - budget.MARGIN_SHARE)
    assert budget.usable(budget.FIXED_RESERVE) == 0.0
    assert budget.project(budget.FIXED_RESERVE).seats == 0


def test_one_projection_answers_the_start_and_the_middle_of_a_run() -> None:
    """The continuation round is the same question with the run's own numbers in it.

    Sizing a top-up off a second formula is how a run comes to seat more than it
    can walk: the two would agree at zero and diverge everywhere else.
    """
    costs = budget.Costs()
    start = budget.project(EIGHT_HOURS, costs=costs)
    middle = budget.project(EIGHT_HOURS, costs=costs, spent=3600.0, admitted=400)
    assert middle.committed == pytest.approx(3600.0 + 400 * costs.gallery_per_admission)
    assert middle.room == pytest.approx(start.room - middle.committed)
    assert middle.seats < start.seats
    # And a run that has spent everything is offered nothing rather than a
    # negative seat count.
    assert budget.project(EIGHT_HOURS, spent=EIGHT_HOURS).seats == 0


def test_every_admission_takes_its_own_frame_off_what_the_walk_may_still_spend() -> None:
    costs = budget.Costs()
    room = budget.usable(EIGHT_HOURS)
    assert budget.spendable(room, 0, costs) == pytest.approx(room)
    assert budget.spendable(room, 100, costs) == pytest.approx(
        room - 100 * costs.gallery_per_admission
    )
    # A walk-only run promised nobody a frame and keeps the whole room.
    assert budget.spendable(room, 100, costs, gallery=False) == pytest.approx(room)
    # And the reserve cannot drive the walk's budget below zero.
    assert budget.spendable(room, 10**9, costs) == 0.0


# --------------------------------------------------------------------------- #
# Sourcing more than once, into the same run.
# --------------------------------------------------------------------------- #
def _deep_ledger(path, rows: int, *, root_id: int = 1) -> None:
    """A ledger holding `rows` admissions at the shallow floor, one lineage each."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_module.Ledger(path) as ledger:
        for index in range(rows):
            ledger.write(
                "candidate",
                run_seed=0,
                root_id=root_id + index,
                family={"kind": "mandelbrot"},
                # Spread far enough apart that `_place_key` calls them different
                # places: the grid is scale-relative and a frame wide.
                viewport=ledger_module.viewport(
                    f"-0.{750 + index * 7}", "0.1", f"{roots_module.CONTINUABLE_WIDTH:.6e}"
                ),
                fate=ledger_module.SURVIVED,
                score=0.9,
            )


def test_a_second_sourcing_round_does_not_seat_what_the_first_one_took(tmp_path) -> None:
    """The failure this prevents is silent: a round with its own dedup sets
    re-offers every row the run is already standing on, and the run pays for
    seats it already has."""
    path = tmp_path / "old" / "walk.jsonl"
    _deep_ledger(path, 6)
    standing = roots_module.Standing()

    first = roots_module.continuation_seats(3, paths=[path], standing=standing, log=lambda *_: None)
    second = roots_module.continuation_seats(
        3, paths=[path], standing=standing, log=lambda *_: None
    )
    assert len(first.seats) == 3 and len(second.seats) == 3
    places = [seat.provenance["place_key"] for seat in [*first.seats, *second.seats]]
    assert len(set(places)) == 6, "a round re-seated a place an earlier round already took"

    # And the supply is finite: a third round has nothing left to offer.
    third = roots_module.continuation_seats(3, paths=[path], standing=standing, log=lambda *_: None)
    assert third.seats == []


def test_a_round_that_shares_no_memory_re_seats_everything(tmp_path) -> None:
    """The control for the test above, so it is testing [`Standing`] and not luck."""
    path = tmp_path / "old" / "walk.jsonl"
    _deep_ledger(path, 6)
    first = roots_module.continuation_seats(3, paths=[path], log=lambda *_: None)
    second = roots_module.continuation_seats(3, paths=[path], log=lambda *_: None)
    assert [seat.provenance["place_key"] for seat in first.seats] == [
        seat.provenance["place_key"] for seat in second.seats
    ]


def test_an_anchor_a_stalled_ladder_spent_is_gone_from_the_next_round() -> None:
    """A ladder costs what it costs whether or not it arrives, so a round that
    re-offered a spent anchor would pay twice to prove one descent does not."""
    standing = roots_module.Standing()
    queues = standing.anchors(3)
    assert queues and standing.anchors_left() == sum(len(q) for q in queues.values())
    before = standing.anchors_left()
    next(iter(queues.values())).pop(0)
    assert standing.anchors_left() == before - 1
    # Read once a run, not once a round: the second call is the same object.
    assert standing.anchors(3) is queues
    assert standing.record()["anchors_left"] == before - 1


def test_a_continuation_shortfall_goes_back_to_the_newton_channel(monkeypatch) -> None:
    """This channel's supply is fifty-odd lineages of finished ledger; the other's
    is nineteen hundred tracked anchors. Asked for ninety seats, a run that let
    the shortfall lie would simply come up short."""
    asked: list[int] = []

    def newton(seats, rng, **kwargs):
        asked.append(int(seats))
        out = roots_module.Sourcing()
        out.seats.extend(
            roots_module.Seat(
                channel=roots_module.NEWTON,
                family={"kind": "mandelbrot"},
                center=None,
                framings=[{"center_re": "0", "center_im": "0", "width": "4e-11"}],
                provenance={},
            )
            for _ in range(int(seats))
        )
        out.count("newton:seated", int(seats))
        return out

    monkeypatch.setattr(roots_module, "newton_seats", newton)
    # `paths=[]` is a continuation channel with nothing at all to offer.
    seats, record = roots_module.sourced(
        20, random.Random(0), newton_share=0.5, paths=[], log=lambda *_: None
    )
    assert asked == [10, 10], "the shortfall was not sent back to the other channel"
    assert len(seats) == 20
    assert record["seated"][roots_module.NEWTON] == 20
    assert record["standing"]["rounds"] == 1


# --------------------------------------------------------------------------- #
# The lineage cap.
# --------------------------------------------------------------------------- #
def _walk(tmp_path, cap: int | None) -> walk_module.Walk:
    return walk_module.Walk(
        out_dir=tmp_path / "walk",
        seed=0,
        limits=walk_module.Limits(batch=4, lineage_admissions=cap),
    )


def _report(root_id: int, node_id: int, count: int) -> dict:
    """The report the engine would have made: `count` gate survivors on one node."""
    return {
        "candidates": [
            {
                "node_id": node_id,
                "root_id": root_id,
                "depth": 2,
                "child_index": index,
                "center_re": f"-0.{750 + index}",
                "center_im": "0.1",
                "width": "1.0e-10",
                "branch": "focus",
                "placement": "center",
                "maxiter": 4096,
                "interior_fraction": 0.1,
                "escape": 4.0,
                "occupancy": 0.5,
                "image": None,
                "fate": ledger_module.SURVIVED,
            }
            for index in range(count)
        ],
        "dead": [],
    }


def _parent(node_id: int, root_id: int) -> dict:
    return {"node_id": node_id, "root_id": root_id, "origin": walk_module.WALK_ORIGIN}


def test_a_lineage_stops_expanding_at_its_cap_and_nothing_is_retro_refused(tmp_path) -> None:
    run = _walk(tmp_path, cap=3)
    rows = run._record(_report(1, 10, 5), {10: _parent(10, 1)}, {"kind": "mandelbrot"})[1]
    run.ledger.close()

    # Every row keeps the fate it earned. The cap stops expansion; it does not
    # reach back and refuse what the head already admitted.
    assert [row["fate"] for row in rows] == [ledger_module.SURVIVED] * 5
    assert run.admitted[1] == 5
    # The row that reaches the cap is the last the lineage books and the first
    # it does not walk from. A node id is the whole of that fact: a row with
    # none behind it is a row nothing descends from.
    assert [row["node_id"] is not None for row in rows] == [True, True, False, False, False]
    assert run.tally["lineage_capped:not_expanded"] == 3
    assert run.tally["tier:admitted"] == 5


def test_the_crossing_evicts_the_lineage_s_standing_frontier_and_says_so(tmp_path) -> None:
    """Evicted at the crossing rather than at the next take, because a saturated
    lineage sits at the TOP of the frontier — it got there by admitting — so the
    next batch is exactly the one the cap exists to reclaim."""
    run = _walk(tmp_path, cap=2)
    run._record(_report(1, 10, 2), {10: _parent(10, 1)}, {"kind": "mandelbrot"})
    survivor = _report(2, 20, 1)
    run._record(survivor, {20: _parent(20, 2)}, {"kind": "mandelbrot"})
    run.ledger.close()

    assert run.saturated == {1}
    assert [node["root_id"] for node in run.frontier] == [2], "the capped lineage still stands"
    capped = [row for row in ledger_module.read(run.ledger.path) if row["kind"] == "lineage_capped"]
    assert len(capped) == 1, "the crossing is recorded once, not on every further admission"
    assert capped[0]["root_id"] == 1
    assert capped[0]["cap"] == 2
    # One node standing when the second admission closed the lineage: the first
    # candidate's. The second is refused expansion rather than evicted.
    assert capped[0]["evicted"] == 1
    assert run.lineages()["capped"] == [1]
    assert run.lineages()["largest"] == 2


def test_a_lineage_may_finish_over_its_cap_from_nodes_already_in_flight(tmp_path) -> None:
    """A stated property rather than a surprise, and it is the honest one.

    Two nodes of one lineage can sit in one batch: the first closes the lineage,
    the second was popped before that happened and its candidates are already
    drawn. Refusing them after the fact would be exactly the retro-refusal this
    project does not do — so they are booked, and the count ends above the cap
    while no further batch slot goes to the lineage.
    """
    run = _walk(tmp_path, cap=2)
    run._record(_report(1, 10, 2), {10: _parent(10, 1)}, {"kind": "mandelbrot"})
    assert run.saturated == {1}
    # The second node of the same lineage, already in flight when it closed.
    rows = run._record(_report(1, 11, 2), {11: _parent(11, 1)}, {"kind": "mandelbrot"})[1]
    run.ledger.close()

    assert run.admitted[1] == 4 > 2
    assert all(row["fate"] == ledger_module.SURVIVED for row in rows)
    # The overshoot is in the count and not in the walk time: nothing from this
    # lineage reaches the frontier, so no later batch spends a slot on it.
    assert all(row["node_id"] is None for row in rows)
    assert not [node for node in run.frontier if node["root_id"] == 1]
    # And the crossing is still recorded exactly once.
    assert (
        len([row for row in ledger_module.read(run.ledger.path) if row["kind"] == "lineage_capped"])
        == 1
    )


def test_a_walk_with_no_cap_is_the_walk_it_always_was(tmp_path) -> None:
    run = _walk(tmp_path, cap=None)
    rows = run._record(_report(1, 10, 5), {10: _parent(10, 1)}, {"kind": "mandelbrot"})[1]
    run.ledger.close()
    assert all(row["node_id"] is not None for row in rows)
    assert run.saturated == set()
    assert "lineage_capped" not in run.tally
    assert not [
        row for row in ledger_module.read(run.ledger.path) if row["kind"] == "lineage_capped"
    ]
    # The counter is still kept: "741 admissions off 15 of 48 roots" is a
    # sentence about a finished run that nothing else in the record makes.
    assert run.lineages() == {
        "cap": None,
        "roots_admitting": 1,
        "admissions": 5,
        "largest": 5,
        "capped": [],
        "by_root": {"1": 5},
    }


def test_the_cap_is_on_for_a_deep_run_and_off_for_the_shallow_walk() -> None:
    assert walk_module.Limits().lineage_admissions is None
    assert deep_run.Limits().lineage_admissions == deep_run.LINEAGE_ADMISSIONS
    assert deep_run.walk_limits(deep_run.Limits()).lineage_admissions == (
        deep_run.LINEAGE_ADMISSIONS
    )
    # Half again `deep_run1`'s equal share of 741 admissions over 48 roots, and
    # well under the 85 the largest lineage actually took.
    assert 741 / 48 < deep_run.LINEAGE_ADMISSIONS < 85


# --------------------------------------------------------------------------- #
# The run, wired up.
# --------------------------------------------------------------------------- #
def test_a_budget_sizes_the_seats_unless_a_person_said_otherwise(tmp_path) -> None:
    """The tri-state, on the field the budget is supposed to fill.

    `Limits.seats` defaulting to a number would out-rank every budget with a
    figure nobody typed — which is the shape of bug this mode has already been
    bitten by once, on the operator flags.
    """
    quiet = {"log": lambda *_: None}
    plain = deep_run.Deep(out_dir=tmp_path / "a", **quiet)
    assert plain.seats_wanted == deep_run.DEFAULT_SEATS
    assert plain.projection is None
    assert plain.batches_allowed == deep_run.DEFAULT_BATCHES

    sized = deep_run.Deep(out_dir=tmp_path / "b", wall_budget=EIGHT_HOURS, **quiet)
    assert sized.seats_wanted == sized.projection.seats > 5 * DEEP_RUN1_SEATS
    # Batches follow the seats rather than being guessed beside them.
    assert sized.batches_allowed > plain.batches_allowed

    told = deep_run.Deep(
        out_dir=tmp_path / "c",
        wall_budget=EIGHT_HOURS,
        limits=deep_run.Limits(seats=5),
        **quiet,
    )
    assert told.seats_wanted == 5


def test_the_run_header_records_the_arithmetic_its_seating_came_from(tmp_path) -> None:
    run = deep_run.Deep(out_dir=tmp_path / "deep", wall_budget=EIGHT_HOURS, log=lambda *_: None)
    run.walk.ledger.close()
    header = next(
        row for row in ledger_module.read(run.walk.ledger.path) if row["kind"] == "deep_run"
    )
    assert header["wall_budget"] == EIGHT_HOURS
    assert header["seats_wanted"] == header["projection"]["seats"]
    assert header["lineage_admissions"] == deep_run.LINEAGE_ADMISSIONS
    assert header["projection"]["costs"]["per_seat"] > 0


def test_a_dry_frontier_is_a_reason_to_seat_again_and_a_spent_clock_is_not(tmp_path) -> None:
    """Five refusals, and the two that matter are the two that look alike from
    outside: an empty frontier with money left is a run to top up, and an empty
    frontier with the budget gone is a run to finish."""
    quiet = {"log": lambda *_: None}
    unbudgeted = deep_run.Deep(out_dir=tmp_path / "a", **quiet)
    assert unbudgeted._reseat() is False, "there is no projection to size a round against"

    refused = deep_run.Deep(
        out_dir=tmp_path / "b",
        wall_budget=EIGHT_HOURS,
        limits=deep_run.Limits(reseat=False),
        **quiet,
    )
    assert refused._reseat() is False

    live = deep_run.Deep(out_dir=tmp_path / "c", wall_budget=EIGHT_HOURS, **quiet)
    live.walk.frontier = [{"root_id": 1, "node_id": index} for index in range(20)]
    assert live._reseat() is False, "a frontier that can still fill a batch is not dry"

    live.walk.frontier = []
    live.clock.leg(deep_run.WALK).may_start()
    live.clock.budget = 0.0
    live.clock.leg(deep_run.WALK).may_start()
    assert live.clock.stopped()
    assert live._reseat() is False, "a run out of clock is not a run to seat more into"


def test_the_walk_leg_is_paced_and_the_sourcing_leg_is_gated_but_never_killed() -> None:
    clock = deep_run.run_clock(EIGHT_HOURS)
    assert clock.leg(deep_run.WALK).ceiling == deep_run.BATCH_CEILING
    # A descent is arbitrary-precision arithmetic in this process: there is no
    # subprocess to kill, so the sourcing leg takes the default ceiling and never
    # uses it. What it does use is the gate and the estimate.
    assert clock.leg(deep_run.SOURCING).ceiling == pacing.DEFAULT_HUNG_CEILING
    assert clock.leg(deep_run.SOURCING).may_start() is None
    clock.budget = 0.0
    assert clock.leg(deep_run.SOURCING).may_start() is not None
    # And an unbudgeted clock declines nothing, which is the old behaviour exactly.
    assert deep_run.run_clock(None).leg(deep_run.WALK).may_start() is None


def _seat(width: str = "4.0e-11") -> roots_module.Seat:
    return roots_module.Seat(
        channel=roots_module.NEWTON,
        family={"kind": "mandelbrot"},
        center=None,
        framings=[{"center_re": "-0.75", "center_im": "0.1", "width": width}],
        provenance={"nucleus_key": "stub"},
    )


def test_a_frontier_that_empties_with_budget_left_is_seated_again(monkeypatch, tmp_path) -> None:
    """The whole change, end to end, with the two expensive legs stubbed out.

    What is under test is the loop: that a dry frontier reaches the sourcing
    channels again, that the second round goes into the SAME ledger with seat
    numbering that continues, and that a round which produces nothing ends the
    run rather than spinning on an exhausted supply.
    """
    rounds: list[int] = []

    def sourced(seats, rng, **kwargs):
        rounds.append(int(seats))
        # Two rounds of supply and then nothing, which is what a run whose anchor
        # queues and ledger lineages have both run dry looks like.
        made = [_seat() for _ in range(2)] if len(rounds) <= 2 else []
        return made, {"seated": {roots_module.NEWTON: len(made)}}

    monkeypatch.setattr(roots_module, "sourced", sourced)
    run = deep_run.Deep(out_dir=tmp_path / "deep", wall_budget=EIGHT_HOURS, log=lambda *_: None)
    # One rung of walking per node and nothing beyond it, so the frontier drains
    # at a known rate instead of feeding itself forever.
    monkeypatch.setattr(run.walk, "expand_batch", lambda batch: [])

    summary = run.run()
    assert len(rounds) == 3, "the run stopped seating before its supply ran out"
    assert rounds[0] == run.projection.seats
    # A top-up is sized off what the run has spent and admitted, and these stubs
    # spend and admit nothing — so the second round is honestly offered the same
    # room as the first. What is proved here is that it is offered at all; the
    # arithmetic that shrinks it is `test_one_projection_answers_...` above.
    assert rounds[1] == rounds[0] == run.projection.seats
    assert [row["round"] for row in summary["rounds"]] == [1, 2, 3]
    assert summary["budget_stopped"] is False
    assert len(run.seats) == 4

    ledger = ledger_module.read(run.walk.ledger.path)
    seats = [row for row in ledger if row["kind"] == "seat"]
    assert [row["seat_index"] for row in seats] == [0, 1, 2, 3], "seat numbering restarted"
    assert [row["round"] for row in seats] == [1, 1, 2, 2]
    assert len([row for row in ledger if row["kind"] == "sourcing_round"]) == 3
    # Same ledger, same artifacts root: a continuation is not a second run.
    assert len({row["root_id"] for row in ledger if row["kind"] == "root"}) == 4


def test_a_run_with_no_reseat_stops_at_the_first_dry_frontier(monkeypatch, tmp_path) -> None:
    """The control: the same stubs, the behaviour turned off."""
    rounds: list[int] = []

    def sourced(seats, rng, **kwargs):
        rounds.append(int(seats))
        return [_seat()], {"seated": {roots_module.NEWTON: 1}}

    monkeypatch.setattr(roots_module, "sourced", sourced)
    run = deep_run.Deep(
        out_dir=tmp_path / "deep",
        wall_budget=EIGHT_HOURS,
        limits=deep_run.Limits(reseat=False),
        log=lambda *_: None,
    )
    monkeypatch.setattr(run.walk, "expand_batch", lambda batch: [])
    run.run()
    assert rounds == [run.projection.seats]


# --------------------------------------------------------------------------- #
# The flags.
# --------------------------------------------------------------------------- #
def test_the_two_behaviours_are_configurable_and_default_on_for_a_deep_run() -> None:
    parse = cli.build_parser().parse_args
    plain = parse(["deep", "walk"])
    assert plain.reseat is None, "an unpassed flag must say nothing, not no"
    assert plain.lineage_cap == deep_run.LINEAGE_ADMISSIONS
    assert plain.wall_budget is None
    assert plain.no_gallery_reserve is False
    assert parse(["deep", "walk", "--no-reseat"]).reseat is False
    assert parse(["deep", "walk", "--reseat"]).reseat is True
    assert parse(["deep", "walk", "--lineage-cap", "0"]).lineage_cap == 0
    # Seats and batches default to `None` so a budget can fill them.
    assert plain.seats is None and plain.batches is None


def test_a_budgeted_run_raises_the_anchor_pool_to_what_its_projection_needs() -> None:
    parse = cli.build_parser().parse_args
    plain = parse(["deep", "walk"])
    assert cli.deep_anchor_pool(plain) == plain.anchors
    budgeted = parse(["deep", "walk", "--wall-budget", str(EIGHT_HOURS)])
    # Eight anchors a family is 32 descents over the four parameter planes, and
    # a projection at eight hours spends several hundred.
    assert cli.deep_anchor_pool(budgeted) > 10 * budgeted.anchors
    # A person who asked for more still gets more.
    asked = parse(["deep", "walk", "--wall-budget", "3600", "--anchors", "5000"])
    assert cli.deep_anchor_pool(asked) == 5000


def test_the_deep_run_uses_the_word_seats_and_the_supply_engine_keeps_refill() -> None:
    """A guard on the naming rule at the one place these two nearly collided.

    `supply.refill` is a fact about release stock. What this mode does when its
    frontier empties is seat more nuclei, and calling that a refill would make a
    grep for either answer with the other.
    """
    source = (deep_run.__file__, roots_module.__file__)
    for path in source:
        assert "refill" not in Path(path).read_text(encoding="utf-8").lower()
