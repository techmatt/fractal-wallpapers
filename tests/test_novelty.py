"""The two novelty levers: the in-run lineage discount and the protected share.

Three properties carry the whole design and each of them is a thing that has gone
wrong in a real run: an ordering that lets a lower claim eat a higher one, a
discount that decays to nothing and becomes a second lineage cap, and a
membership test that calls ground three runs already worked "novel".
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.discovery import ledger as ledger_module
from fractal_wallpapers.discovery.walk import lineage_distribution
from fractal_wallpapers.supply import currency as money
from fractal_wallpapers.supply import novelty
from fractal_wallpapers.supply.allocation import exploration_slots
from fractal_wallpapers.supply.census import Census
from fractal_wallpapers.supply.partitions import ALL_PARTITIONS
from fractal_wallpapers.supply.prices import load_table
from fractal_wallpapers.supply.quota import Quota

MANDELBROT = {"kind": "mandelbrot"}
JULIA = {"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]}
OTHER_JULIA = {"kind": "julia", "degree": 2, "c": ["-0.4", "0.61"]}


def frame(re: str = "0", im: str = "0", width: str = "0.01") -> dict:
    return {"center_re": re, "center_im": im, "width": width}


def write_ledger(path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def root_row(root_id: int, family: dict, viewport: dict) -> dict:
    return {
        "schema": ledger_module.SCHEMA,
        "kind": "root",
        "root_id": root_id,
        "family": family,
        "viewport": viewport,
        "source": "seed_file",
    }


def candidate_row(root_id: int, family: dict, viewport: dict, score, fate="survived") -> dict:
    return {
        "schema": ledger_module.SCHEMA,
        "kind": "candidate",
        "root_id": root_id,
        "family": family,
        "viewport": viewport,
        "fate": fate,
        "score": score,
    }


def quota(
    deficits: dict | None = None, exploration=None, partitions=ALL_PARTITIONS, run_dir=None
) -> Quota:
    """A quota with a stated stock and no ledgers behind it."""
    deficits = deficits or {}
    return Quota(
        partitions,
        run_dir,
        census=Census(
            counts={},
            currency={p: float(deficits.get(p, 0.0)) for p in partitions},
            partitions=tuple(partitions),
        ),
        prices_config=load_table(None),
        exploration=exploration,
    )


# ------------------------------------------------------------------- lever 3


def test_a_lineage_that_has_booked_nothing_this_run_is_not_discounted() -> None:
    """`n = 0` is exactly one, and that is the whole of the claim: the discount
    prices repetition and must be invisible to a lineage that has not repeated."""
    assert novelty.lineage_discount(0) == 1.0
    assert novelty.lineage_discount(0, k=17.0, floor=0.01) == 1.0


def test_the_discount_falls_with_what_the_lineage_booked_and_stops_at_the_floor() -> None:
    values = [novelty.lineage_discount(n) for n in range(0, 60)]
    assert values == sorted(values, reverse=True), "monotone in what the lineage has booked"
    assert values[1] == pytest.approx(1 / 1.5)
    assert min(values) >= novelty.DISCOUNT_FLOOR
    assert values[-1] == pytest.approx(novelty.DISCOUNT_FLOOR), "it reaches the floor and stays"
    # Never below the floor at any k, however hard the lever is pulled.
    assert novelty.lineage_discount(10**6, k=1000.0) == pytest.approx(novelty.DISCOUNT_FLOOR)


def test_a_zero_k_is_the_lever_turned_off_and_not_a_maximal_discount() -> None:
    assert novelty.lineage_discount(500, k=0.0) == 1.0


def test_the_discount_multiplies_the_score_term_and_leaves_the_draw_alone(tmp_path) -> None:
    """The shape the saturation memory already uses. A saturated lineage with a
    great score loses to a fresh one with a good score and still beats a fresh one
    with a bad score — which a subtracted constant could not do."""
    from fractal_wallpapers.supply.harvest import Harvest

    run = Harvest(_walk(tmp_path), quota(), discount_k=0.5, discount_floor=0.2)
    run.walk.admitted = {1: 0, 2: 40}
    fresh = {"root_id": 1, "priority": 1.0, "score_term": 0.6}
    saturated_great = {"root_id": 2, "priority": 1.0, "score_term": 0.99}
    assert run.contest_key(fresh) == pytest.approx(1.0)
    assert run.contest_key(saturated_great) < run.contest_key(fresh)
    unscored = {"root_id": 2, "priority": 1.0, "score_term": 0.0}
    assert run.contest_key(unscored) == pytest.approx(1.0), (
        "under the null scorer every score term is the neutral prior and nothing moves"
    )
    run.walk.ledger.close()


def test_the_discount_parameters_arrive_from_the_command_line(tmp_path) -> None:
    """The two numbers are run-command parameters and are never stored per row."""
    from fractal_wallpapers.cli import build_parser

    args = build_parser().parse_args(
        ["harvest", "--lineage-discount", "3.0", "--lineage-discount-floor", "0.05"]
    )
    assert (args.lineage_discount, args.lineage_discount_floor) == (3.0, 0.05)

    from fractal_wallpapers.supply.harvest import Harvest

    run = Harvest(
        _walk(tmp_path),
        quota(),
        discount_k=args.lineage_discount,
        discount_floor=args.lineage_discount_floor,
    )
    run.walk.admitted = {1: 1}
    assert run.contest_key({"root_id": 1, "priority": 0.0, "score_term": 1.0}) == pytest.approx(
        novelty.lineage_discount(1, 3.0, 0.05) - 1.0
    )
    run.walk.ledger.close()


def _walk(tmp_path):
    from fractal_wallpapers.discovery.walk import Limits, Walk

    return Walk(out_dir=tmp_path / "run", seed=1, limits=Limits(batch=2, batches=1))


# ------------------------------------------------------------------- lever 4


def test_a_root_any_run_has_ever_booked_from_is_not_a_member(tmp_path) -> None:
    """Membership is cross-run, so this run's own quiet says nothing."""
    write_ledger(
        tmp_path / "earlier" / "walk.jsonl",
        [
            root_row(1, MANDELBROT, frame("0.30", "0.02", "0.01")),
            root_row(2, MANDELBROT, frame("-1.40", "0.00", "0.01")),
            candidate_row(1, MANDELBROT, frame("0.3001", "0.0201", "0.0001"), 0.99),
            # Root 2 was walked and never booked: a lineage that produced nothing
            # is still novel ground, which is the difference between this index
            # and the saturation memory.
            candidate_row(2, MANDELBROT, frame("-1.4001", "0.0", "0.0001"), 0.01, "not_admitted"),
        ],
    )
    found = novelty.build(root=tmp_path)
    assert found.roots_read == 2
    assert found.roots_admitting == 1
    assert not found.is_novel(MANDELBROT, frame("0.30", "0.02", "0.01")), "the root that booked"
    assert found.is_novel(MANDELBROT, frame("-1.40", "0.00", "0.01")), "the root that did not"
    assert found.is_novel(MANDELBROT, frame("0.9", "0.0", "0.01")), "somewhere else entirely"


def test_membership_is_a_neighbourhood_and_the_parameter_is_part_of_it(tmp_path) -> None:
    """A `c` no run has walked is a lineage no run has walked, whatever the frame
    says — and inside one parameter the tolerance is the visit's own width."""
    write_ledger(
        tmp_path / "earlier" / "walk.jsonl",
        [
            root_row(1, JULIA, frame("0", "0", "4")),
            candidate_row(1, JULIA, frame("0.1", "0.1", "0.5"), 0.99),
        ],
    )
    found = novelty.build(root=tmp_path)
    assert not found.is_novel(JULIA, frame("0.2", "-0.3", "4")), "same c, inside the disc"
    assert found.is_novel(OTHER_JULIA, frame("0", "0", "4")), "a c nothing has walked"
    assert found.is_novel(MANDELBROT, frame("0", "0", "4")), "another partition entirely"


def test_a_root_whose_place_cannot_be_read_is_not_admitted_to_the_share() -> None:
    """The share is a protected allocation and an unreadable row may not spend it."""
    found = novelty.NovelLineages()
    assert not found.is_novel(None, frame())
    assert not found.is_novel(MANDELBROT, {"center_re": "nonsense", "center_im": "0"})
    assert found.unplaceable == 2


def test_the_share_never_falls_below_its_floor_however_badly_it_prices() -> None:
    """Self-priced above the floor, and the floor is what stops a run that had one
    unlucky hour from silencing exploration for the rest of it."""
    share = novelty.Exploration(floor=0.25, start=0.45, ema=0.5)
    for _ in range(200):
        share.settle({"slots": 4, "admissions": 0}, {"slots": 4, "admissions": 4})
    assert share.share == pytest.approx(0.25)
    assert share.split(8) == 2
    # And it cannot be started below its own floor either.
    assert novelty.Exploration(floor=0.4, start=0.1).share == pytest.approx(0.4)


def test_the_share_prices_itself_up_when_it_is_the_channel_that_finds() -> None:
    share = novelty.Exploration(floor=0.25, start=0.45, ema=0.3)
    for _ in range(40):
        share.settle({"slots": 4, "admissions": 4}, {"slots": 4, "admissions": 0})
    assert share.share > 0.45
    assert share.share <= 1.0


def test_the_share_does_not_move_on_no_evidence() -> None:
    """One pseudo-slot at the pooled rate, so a batch nobody served prices at
    exactly one and a contest that found nothing cannot divide by zero."""
    share = novelty.Exploration(floor=0.25, start=0.45)
    priced = share.settle({"slots": 0, "admissions": 0}, {"slots": 0, "admissions": 0})
    assert priced["ratio"] == pytest.approx(1.0)
    assert share.share == pytest.approx(0.45)


def test_the_share_rounds_up_so_a_small_batch_still_has_a_floor() -> None:
    share = novelty.Exploration(floor=0.25, start=0.5)
    assert share.split(0) == 0
    assert share.split(1) == 1
    assert share.split(2) == 1
    assert share.split(8) == 4


def test_the_exploration_share_is_spread_evenly_over_drawable_and_capped_by_supply() -> None:
    """Exploration is allotted to whoever can be explored, not to whoever the mix
    already favours. Intent is not an input — it is not even in the signature."""
    slots, trace = exploration_slots({"mandelbrot": 10, "phoenix": 10, "multibrot3": 10}, 6)
    assert slots == {"mandelbrot": 2, "phoenix": 2, "multibrot3": 2}
    assert sum(slots.values()) == 6
    assert trace["weight_source"] == "even_carry"
    assert trace["drawable"] == 3
    # A partition with one novel node gets one slot and no more: supply still caps.
    thin, _ = exploration_slots({"mandelbrot": 1, "phoenix": 10}, 5)
    assert thin["mandelbrot"] == 1
    assert thin["phoenix"] == 4
    # No novel node is the one way out of the draw.
    none, trace = exploration_slots({"mandelbrot": 0, "phoenix": 10}, 4)
    assert none["mandelbrot"] == 0
    assert trace["drawable"] == 1


def test_no_drawable_partition_is_zeroed_while_the_budget_can_seat_them_all() -> None:
    """Matt's ruling, as an invariant rather than a tendency: floors and
    exploration are two budgets, and carrying a floor cannot cost a partition its
    exploration slot."""
    drawable = {p: 10 for p in ALL_PARTITIONS}
    for budget in range(len(drawable), len(drawable) * 3):
        slots, trace = exploration_slots(drawable, budget)
        assert trace["guaranteed_all"] is True
        assert sum(slots.values()) == budget
        assert min(slots.values()) >= 1, (
            f"a drawable partition was zeroed at {budget} slots over {len(drawable)} partitions"
        )
    # One short of the precondition the guarantee is not claimed, and is not owed:
    # `allocate_slots` refuses to pro-rate a guarantee rather than pretending.
    slots, trace = exploration_slots(drawable, len(drawable) - 1)
    assert trace["guaranteed_all"] is False
    assert sum(slots.values()) == len(drawable) - 1


def test_the_share_carries_its_evenness_across_batches_because_one_batch_cannot() -> None:
    """A leg wants one or two share slots against nine drawable partitions, so
    evenness only exists over the run. Without the carry the tie-break hands one
    partition nearly everything; with it the spread is flat."""
    drawable = {p: 100 for p in ALL_PARTITIONS}
    carried: dict = {}
    for _ in range(60):
        slots, _ = exploration_slots(drawable, 2, taken=carried)
        for partition, n in slots.items():
            carried[partition] = carried.get(partition, 0) + n
    assert sum(carried.values()) == 120
    assert min(carried.values()) >= 1, "every drawable partition is reached over the run"
    assert max(carried.values()) - min(carried.values()) <= 1, carried

    # The same budget with no carry is what the defect looked like: one partition
    # wins every tie-break and the spread is not flat.
    flat: dict = {}
    for _ in range(60):
        slots, _ = exploration_slots(drawable, 2)
        for partition, n in slots.items():
            flat[partition] = flat.get(partition, 0) + n
    assert max(flat.values()) > max(carried.values()), "the carry is what makes it even"


# ------------------------------------------------------------ the ruled order


def test_a_starved_partition_is_served_even_when_the_share_would_take_the_slots() -> None:
    """The floor is the re-entry path for a mispriced partition and nothing below
    it may eat that. Here every post-floor slot the share could want exists, and
    the claimant still comes out with one.

    The starved partition is the one with **no novel nodes**, which is now the
    only way to build one: since the share is spread evenly over every drawable
    partition rather than by intent, a partition the share can reach is a
    partition the share keeps served. So what is starved here is what the share
    cannot spend a slot on, and the floor is the only thing that can reach it.
    """
    exploration = novelty.Exploration(floor=1.0, start=1.0)
    exploration.members = dict.fromkeys(range(1, 50), True)
    held = quota({"mandelbrot": 500.0}, exploration=exploration)
    queues = dict.fromkeys(ALL_PARTITIONS, 20)
    novel = dict.fromkeys(ALL_PARTITIONS, 20)
    starved = ALL_PARTITIONS[-1]
    novel[starved] = 0

    # Run long enough that the floor's carry comes due for the quiet partitions.
    for _ in range(40):
        share, contest, trace = held.slots(queues, 4, novel)
        spent = 0.0
        for partition in ALL_PARTITIONS:
            n = share.get(partition, 0) + contest.get(partition, 0)
            if n:
                held.charge(partition, float(n), n)
                spent += float(n)
        held.close_batch(spent)

    share, contest, trace = held.slots(queues, 4, novel)
    claimants = trace["guaranteed"]
    assert claimants, "the carry should have come due by batch twenty at a 5% floor"
    assert starved in claimants, "the partition the share cannot reach is the one owed"
    for partition in claimants:
        assert contest.get(partition, 0) >= 1, (
            f"{partition} is owed the floor and the share took its slot"
        )
    assert sum(share.values()) + sum(contest.values()) == 4


def test_the_share_takes_only_the_post_floor_remainder() -> None:
    """At one slot with a claim standing, the share gets nothing at all."""
    exploration = novelty.Exploration(floor=1.0, start=1.0)
    exploration.members = dict.fromkeys(range(1, 50), True)
    held = quota({"mandelbrot": 500.0}, exploration=exploration)
    queues = dict.fromkeys(ALL_PARTITIONS, 20)
    novel = dict.fromkeys(ALL_PARTITIONS, 20)
    for _ in range(40):
        share, contest, _ = held.slots(queues, 1, novel)
        for partition in ALL_PARTITIONS:
            n = share.get(partition, 0) + contest.get(partition, 0)
            if n:
                held.charge(partition, float(n), n)
        held.close_batch(1.0)
    share, contest, trace = held.slots(queues, 1, novel)
    if trace["guaranteed"]:
        assert sum(share.values()) == 0
        assert sum(contest.values()) == 1


def test_with_no_claim_standing_the_share_takes_its_fraction() -> None:
    exploration = novelty.Exploration(floor=0.25, start=0.5)
    exploration.members = dict.fromkeys(range(1, 50), True)
    held = quota({"mandelbrot": 500.0}, exploration=exploration)
    queues = dict.fromkeys(ALL_PARTITIONS, 20)
    share, contest, trace = held.slots(queues, 8, dict.fromkeys(ALL_PARTITIONS, 20))
    assert trace["guaranteed"] == [], "no minutes spent yet, so nothing is owed"
    assert sum(share.values()) == 4
    assert sum(contest.values()) == 4
    assert trace["share"]["status"] == "on"


def test_a_run_with_no_exploration_allocates_exactly_as_it_always_did() -> None:
    without = quota({"mandelbrot": 100.0})
    with_it = quota({"mandelbrot": 100.0}, exploration=novelty.Exploration())
    queues = dict.fromkeys(ALL_PARTITIONS, 20)
    _, plain, _ = without.slots(queues, 8)
    # No novel queues offered: the share has nothing it may be spent on.
    share, priced, _ = with_it.slots(queues, 8, dict.fromkeys(ALL_PARTITIONS, 0))
    assert sum(share.values()) == 0
    assert priced == plain


def test_the_share_state_round_trips_so_a_resume_keeps_what_it_paid_for() -> None:
    share = novelty.Exploration(floor=0.25, start=0.45, ema=0.3)
    for _ in range(10):
        share.settle({"slots": 3, "admissions": 3}, {"slots": 5, "admissions": 1})
    share.note_offer("mandelbrot", 8, 3)
    share.member(7, {"family": MANDELBROT, "viewport": frame()})
    restored = novelty.Exploration(floor=0.25, start=0.45, ema=0.3)
    restored.load_state(share.state())
    assert restored.share == pytest.approx(share.share)
    assert restored.bought() == share.bought()
    assert restored.realized() == share.realized()
    assert restored.members == share.members


# ------------------------------------------------------------ the readout


def test_the_monotony_measure_separates_two_runs_with_one_headline() -> None:
    """Five hundred admissions over two hundred lineages and five hundred over
    six are the same number and are not the same run."""
    spread = lineage_distribution(dict.fromkeys(range(200), 2))
    piled = lineage_distribution({1: 300, 2: 50, 3: 30, 4: 10, 5: 5, 6: 5})
    assert spread["max"] == 2 and spread["median"] == 2.0
    assert spread["top5_share"] == pytest.approx(0.025)
    assert piled["max"] == 300 and piled["median"] == 20.0
    assert piled["top5_share"] == pytest.approx(0.9875)
    assert lineage_distribution({}) == {
        "lineages_admitting": 0,
        "admissions": 0,
        "max": 0,
        "median": None,
        "top5": [],
        "top5_share": None,
    }


def test_the_realized_share_is_measured_against_post_floor_slots_only() -> None:
    share = novelty.Exploration(floor=0.25, start=0.5)
    share.note_offer("mandelbrot", 4, 2)
    share.note_offer("phoenix", 4, 1)
    realized = share.realized()
    assert realized["per_partition"]["mandelbrot"]["realized"] == pytest.approx(0.5)
    assert realized["overall"]["realized"] == pytest.approx(0.375)
    assert realized["floor"] == 0.25 and realized["start"] == 0.5


# ---------------------------------------------------------- inside the share


def test_only_the_junk_floor_kills_a_share_candidate() -> None:
    """Inside the share the head *ranks*; it does not reject.

    This is a property of the two-floor design rather than of the share — the
    good floor decides what is *booked* and the junk floor decides what is
    *killed* — and it is pinned here because the share is what makes it load
    bearing. A share slot spent on a candidate the keeper floor refused still
    bought a place the walk can stand on, and a third floor added anywhere above
    the junk one would silently take that back.
    """
    from fractal_wallpapers.curation import floors
    from fractal_wallpapers.discovery.scoring import LocationScorer

    middling = (floors.JUNK_FLOOR + money.GOOD_FLOOR) / 2.0
    assert floors.JUNK_FLOOR < middling < money.GOOD_FLOOR, "a real middle tier exists"
    scorer = object.__new__(LocationScorer)
    assert not LocationScorer.admits(scorer, {}, middling), "not booked"
    assert LocationScorer.expandable(scorer, {}, middling), "and not killed either"
    assert not LocationScorer.expandable(scorer, {}, floors.JUNK_FLOOR / 2.0)
    assert not LocationScorer.expandable(scorer, {}, None), (
        "a candidate with no score has a failed render behind it, not a low opinion"
    )


# --------------------------------------------------------------- end to end


def engine_is_built() -> bool:
    from fractal_wallpapers import engine

    try:
        engine.engine_path()
    except FileNotFoundError:
        return False
    return True


needs_engine = pytest.mark.skipif(
    not engine_is_built(),
    reason="the engine is not built: cargo build --release --manifest-path engine/Cargo.toml",
)


@needs_engine
def test_a_smoke_harvest_divides_its_batches_between_the_two_channels(tmp_path) -> None:
    """Small and seeded, through the real engine: the share draws, the contest
    draws, the columns add to the slots, and every row says which paid for it."""
    from fractal_wallpapers.discovery.walk import Limits, Policy, Walk
    from fractal_wallpapers.supply import autopsy
    from fractal_wallpapers.supply.harvest import Budget, Harvest
    from fractal_wallpapers.supply.refill import Refill

    walk = Walk(
        out_dir=tmp_path / "run",
        seed=20260821,
        limits=Limits(batch=4, root_expansions=3),
        policy=Policy(candidates=2, node_width=96),
    )
    exploration = novelty.Exploration(lineages=novelty.build(root=tmp_path / "nothing"))
    run = Harvest(
        walk,
        quota(run_dir=tmp_path / "run", exploration=exploration),
        budget=Budget(minutes=0.0, batches=3),
        batch_size=4,
        refill=Refill(walk, low_water=2, per_draw=2),
    )
    summary = run.run()

    channels = summary["tally"]["by_channel"]
    assert channels["share"]["slots"] > 0, "no ledger behind this run, so every root is novel"
    assert channels["contest"]["slots"] > 0
    assert sum(row["slots"] for row in channels.values()) == summary["tally"]["expanded"]
    assert sum(row["found"] for row in channels.values()) == summary["tally"]["found"]
    assert (
        sum(row["distinct"] for row in channels.values())
        == (summary["tally"]["distinct_admissions"])
    )

    stamped = {
        row.get("channel")
        for row in ledger_module.read(tmp_path / "run" / "walk.jsonl")
        if row["kind"] == "candidate"
    }
    assert stamped <= {"share", "contest"} and stamped, "every candidate names its channel"

    realized = summary["exploration"]["realized"]
    assert realized["floor"] == novelty.SHARE_FLOOR
    assert realized["start"] == novelty.SHARE_START
    assert realized["overall"]["realized"] >= 0.0

    sheet = autopsy.write(tmp_path / "run", summary)
    assert sheet is not None and sheet.is_file()
    page = sheet.read_text(encoding="utf-8")
    assert "share · admitted" in page and "contest · refused" in page


@needs_engine
def test_a_resumed_run_keeps_the_share_it_paid_for(tmp_path) -> None:
    """The share is a priced quantity and membership is classified once, so a
    session that reopened at the start value would throw away what it bought."""
    from fractal_wallpapers.discovery.walk import Limits, Policy, Walk
    from fractal_wallpapers.supply.harvest import Budget, Harvest
    from fractal_wallpapers.supply.refill import Refill

    def build(batches: int) -> Harvest:
        walk = Walk(
            out_dir=tmp_path / "run",
            seed=20260821,
            limits=Limits(batch=4, root_expansions=3),
            policy=Policy(candidates=2, node_width=96),
        )
        exploration = novelty.Exploration(lineages=novelty.build(root=tmp_path / "nothing"))
        return Harvest(
            walk,
            quota(run_dir=tmp_path / "run", exploration=exploration),
            budget=Budget(minutes=0.0, batches=batches),
            batch_size=4,
            refill=Refill(walk, low_water=2, per_draw=2),
        )

    first = build(2)
    first.run()
    priced = first.exploration.share
    members = dict(first.exploration.members)
    assert members, "the first session classified its roots"

    second = build(4)
    assert second.resume() is True
    assert second.exploration.share == pytest.approx(priced)
    assert second.exploration.members == members
    assert second.walk.roots, "and the roots those verdicts were read off came back"
    assert second.tally.by_channel == first.tally.by_channel


def test_the_batch_trace_records_the_step_that_moved_the_share() -> None:
    """ "Did the self-pricing move at all" has to be a read, not a difference
    between consecutive rows."""
    exploration = novelty.Exploration(floor=0.25, start=0.5, ema=0.5)
    held = quota({"mandelbrot": 100.0}, exploration=exploration)
    held.slots(dict.fromkeys(ALL_PARTITIONS, 20), 8, dict.fromkeys(ALL_PARTITIONS, 20))
    held.note_share_pricing(
        exploration.settle({"slots": 4, "admissions": 4}, {"slots": 4, "admissions": 0})
    )
    assert held._trace["share_priced"]["share"] > 0.5
    assert held._trace["share_priced"]["ratio"] > 1.0
    assert held._trace["share"]["share"] == pytest.approx(0.5), (
        "the row still says the share the batch was allocated under"
    )
