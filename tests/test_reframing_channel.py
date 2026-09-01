"""The reframing channel: what it records, what it refuses, and what it will not do.

The four guards here are the four claims the channel is: an operator's own view
lands as a **candidate** the supply union reads, an evaluation pin refuses a seed
*and* a manufactured frame, one nucleus is one location whatever it was drawn at,
and the rung set is the rung set.

Nothing here renders. The engine and the head are stood in for, because what is
being checked is the channel's bookkeeping and a real gate battery would make
these guards a measurement of the engine instead.
"""

from __future__ import annotations

import json
import random

import pytest

from fractal_wallpapers.discovery import ledger as ledger_module
from fractal_wallpapers.discovery import operators, reframing
from fractal_wallpapers.supply import currency as money
from fractal_wallpapers.supply import ledgers
from fractal_wallpapers.supply.location import location_key

#: A seed centred on a low-period atom, so the snap has something to find.
ON_AN_ATOM = reframing.Seed(
    id="proven-test",
    family={"kind": "mandelbrot"},
    viewport={"center_re": "-0.1592", "center_im": "1.0317", "width": "0.02"},
    tier=4,
    generation=0,
    source="matt_q4",
)


class Stub:
    """A head that says the same thing about every picture it is handed."""

    name = "location:stub"

    def __init__(self, p_ge3: float = 0.99, p_ge4: float = 0.9):
        self.p_ge3 = p_ge3
        self.p_ge4 = p_ge4
        self.batches = 0

    def read(self, candidates, pictures=None):
        from fractal_wallpapers.discovery.scoring import Reading

        del pictures
        self.batches += 1
        return [
            Reading(
                score=self.p_ge3,
                great=self.p_ge4,
                probabilities=(0.99, self.p_ge3, self.p_ge4),
                regime="384x216ss1",
                view="stub",
            )
            for _ in candidates
        ]


def drawn(monkeypatch, fates=None, passed=True):
    """Stand in for `engine.screen`: every rung comes back at the frame asked for."""

    def screen(pairs, directory, log=print):
        del directory, log
        out = []
        for index, (nucleus, rung) in enumerate(pairs):
            frame = reframing.frame_of(nucleus, rung, nucleus.rungs[rung])
            out.append(
                {
                    "nucleus": nucleus,
                    "rung": float(rung),
                    "picture": f"{index:06d}_k{rung:g}.jpg",
                    "fate": (fates or {}).get(float(rung), "survived"),
                    "passed": passed,
                    "viewport": frame,
                    "maxiter": 1000,
                    "interior_fraction": 0.01,
                    "escape": {"median": 100.0},
                    "occupancy": 0.8,
                    "p_ge3": None,
                    "p_ge4": None,
                    "probabilities": (),
                    "error": None,
                    "regime": None,
                    "view": None,
                }
            )
        return out

    monkeypatch.setattr(reframing, "screen_rungs", screen)


def channel(tmp_path, scorer=None, pinned=frozenset(), log=None, **kwargs):
    return reframing.Channel(
        out_dir=tmp_path / "reframe",
        scorer=scorer or Stub(),
        pinned=set(pinned),
        log=log or (lambda *_a, **_k: None),
        **kwargs,
    )


# --------------------------------------------------------------------------- #
# 1. An operator's own view lands as a candidate.
# --------------------------------------------------------------------------- #
def test_an_operators_own_view_lands_as_a_candidate_the_supply_union_reads(
    tmp_path, monkeypatch
) -> None:
    """THE finding this channel exists for.

    A walk pushes the reframed frame onto the frontier as a node and scores only
    what it draws below it, so 0 of 14,678 available reframing viewports on one
    production harvest ever appeared as a candidate viewport. Here the operator's
    own frame IS the row — and not merely a row of some shape: the ledger it lands
    in is walk-shaped, so `supply.ledgers` admits it without being told anything
    about where it came from.
    """
    drawn(monkeypatch)
    run = channel(tmp_path)
    run.run([ON_AN_ATOM])

    rows = reframing.read(run.ledger.path)
    assert rows, "the operator's view produced no candidate at all"

    admitted = ledgers.admitted(run.ledger.path)
    assert admitted, "a candidate the union cannot read is not supply"
    assert all(ledgers.passes_gates(row) for row in admitted)
    # The frame on the row is the operator's, not the seed's.
    assert rows[0]["viewport"] != ON_AN_ATOM.viewport
    assert rows[0]["origin"] in reframing.OPERATORS
    assert rows[0]["atom_key"]
    assert rows[0]["reframing"]["seed"]["tier"] == 4
    assert rows[0]["reframing"]["generation"] == 1


def test_the_channel_writes_the_ledger_the_union_looks_for(tmp_path, monkeypatch) -> None:
    """`<run directory>/walk.jsonl`, at the top level of the regenerable tree.

    The union looks a ledger up at that exact name rather than searching for one,
    so a channel that named its record anything else would be supply nothing ever
    reads.
    """
    drawn(monkeypatch)
    run = channel(tmp_path)
    run.run([ON_AN_ATOM])
    assert run.ledger.path.name == ledgers.LEDGER_NAME


# --------------------------------------------------------------------------- #
# 2. The pin refuses a seed and a derived frame.
# --------------------------------------------------------------------------- #
def test_a_pinned_seed_is_refused_by_name(tmp_path, monkeypatch) -> None:
    """The seed side of the guard. A pinned place may not be fired at."""
    drawn(monkeypatch)
    pin = location_key(ON_AN_ATOM.family, ON_AN_ATOM.viewport)
    run = channel(tmp_path, pinned={pin})
    with pytest.raises(reframing.PinnedPlace, match="evaluation pin"):
        run.run([ON_AN_ATOM])


def test_a_derived_frame_that_lands_on_a_pinned_place_is_refused(tmp_path, monkeypatch) -> None:
    """The half that could not be caught anywhere else.

    The pin is asserted on the **coordinate**, so a frame this channel manufactures
    onto a pinned place spends that blind slice exactly as a re-draw of it would —
    and nothing upstream would notice, because the seed was clean. Guarded on the
    frame the engine reports, which is what the location key is built from.
    """
    drawn(monkeypatch)
    nuclei, _cost = reframing.fire(ON_AN_ATOM, random.Random(0), rungs=reframing.RUNGS)
    assert nuclei, "the fixture seed must find an atom for this guard to mean anything"
    rung, row = nuclei[0].frames()[0]
    pin = location_key(ON_AN_ATOM.family, reframing.frame_of(nuclei[0], rung, row))

    run = channel(tmp_path, pinned={pin})
    with pytest.raises(reframing.PinnedPlace, match="rung"):
        run.run([ON_AN_ATOM])


def test_the_seed_query_excludes_pinned_places_rather_than_counting_them(tmp_path) -> None:
    """Belt as well as braces: the pin acts at the query too, so an ordinary run
    never reaches the guard above. Both are kept — one is a filter and the other
    is an assertion, and a filter nobody asserts behind is a filter that rots."""
    del tmp_path
    rows = [
        {
            "family": ON_AN_ATOM.family,
            "viewport": ON_AN_ATOM.viewport,
            "score": 4,
            "origin": "human",
            "batch": "test",
        }
    ]
    pin = location_key(ON_AN_ATOM.family, ON_AN_ATOM.viewport)
    kept, record = reframing.seeds(pinned={pin}, rows=rows)
    assert kept == []
    assert record["refused_pinned"] == 1

    kept, record = reframing.seeds(pinned=set(), rows=rows)
    assert len(kept) == 1
    assert record["refused_pinned"] == 0
    assert kept[0].tier == 4


# --------------------------------------------------------------------------- #
# 3. One nucleus is one location.
# --------------------------------------------------------------------------- #
def test_one_nucleus_is_one_location_and_the_rungs_are_its_framings(tmp_path, monkeypatch) -> None:
    """Three rungs are three framings of one place, never three places.

    Three rows would put one atom in three seats, count one find three times in
    every book downstream, and let one nucleus fill a gallery. So: one row, every
    rung's own reading on it, and the location's score is the rung that was picked.
    """
    drawn(monkeypatch)
    run = channel(tmp_path)
    run.run([ON_AN_ATOM])
    rows = reframing.read(run.ledger.path)

    assert len({row["atom_key"] for row in rows}) == len(rows), "one row per atom"
    for row in rows:
        block = row["reframing"]
        assert len(block["rungs_drawn"]) == len(block["rungs"])
        assert block["chosen_rung"] in block["rungs"]
        chosen = next(cell for cell in block["rungs_drawn"] if cell["rung"] == block["chosen_rung"])
        assert row["viewport"] == chosen["viewport"]
        assert row["score"] == chosen["p_ge3"]
        assert row["score_great"] == chosen["p_ge4"]


def test_a_nucleus_two_operators_reach_is_one_location_and_says_so() -> None:
    """The dedup is on the atom, not on the operator that got there.

    Which operator found it is provenance; two operators reaching one atom have
    found one atom. The second one is recorded rather than dropped, because "both
    reached it" is a fact about the operators' overlap that a yield read wants.
    """
    seed = ON_AN_ATOM
    view = seed.view()
    rows = operators.snap_at_seed(view, degree=2, framings=reframing.RUNGS)
    assert any(row.available for row in rows)
    keys = {row.key for row in rows if row.available}
    assert len(keys) == 1, "one snap is one nucleus however many framings it emits"


def test_the_head_picks_the_rung_and_the_row_says_which(tmp_path, monkeypatch) -> None:
    """The pick is the seating statistic — `P(>=4)` then `P(>=3)` — so the rung
    this channel chooses is the rung a gallery would have reached for."""
    readings = [
        {"rung": 16.0, "passed": True, "p_ge3": 0.99, "p_ge4": 0.10},
        {"rung": 24.0, "passed": True, "p_ge3": 0.80, "p_ge4": 0.90},
        {"rung": 32.0, "passed": True, "p_ge3": 0.99, "p_ge4": 0.50},
    ]
    chosen, why = reframing.pick(readings)
    assert chosen["rung"] == 24.0
    assert why == "head"

    # A rung the gates refused may not be picked, however it scored: a frame the
    # battery refused is a frame no walk would have admitted.
    refused = [
        {"rung": 16.0, "passed": False, "p_ge3": 1.0, "p_ge4": 1.0},
        {"rung": 24.0, "passed": True, "p_ge3": 0.5, "p_ge4": 0.2},
    ]
    chosen, why = reframing.pick(refused)
    assert chosen["rung"] == 24.0

    # And a nucleus no rung scored is still on the record, carrying its refusal.
    unscored = [
        {"rung": 16.0, "passed": False, "p_ge3": None, "p_ge4": None},
        {"rung": 32.0, "passed": False, "p_ge3": None, "p_ge4": None},
    ]
    chosen, why = reframing.pick(unscored)
    assert why == "no_scored_rung"
    assert chosen["rung"] == 32.0
    del tmp_path, monkeypatch


# --------------------------------------------------------------------------- #
# 4. The rung set.
# --------------------------------------------------------------------------- #
def test_the_rung_set_is_16_24_32_48_and_64_atom_sizes() -> None:
    """The band that reads as a minibrot with detail around it is 50-100 px of
    body at 1280, which is the 32x rung; the walk's widest rung is 16x and is a
    factor of two too tight. 48x and 64x are carried because generation 1's
    head-q4 rate rose monotone outward over the three rungs it had — 2.1%, 2.9%,
    3.5% — which leaves the ladder's own end the thing that was never tested.
    Nothing below 16x is offered: the 2x frame is half interior and the walk's own
    cap refuses it outright."""
    assert reframing.RUNGS == (16.0, 24.0, 32.0, 48.0, 64.0)
    assert min(reframing.RUNGS) >= max(f for f in operators.FRAMINGS if f is not None)


def test_every_rung_is_drawn_and_scored_and_every_reading_is_on_the_row(
    tmp_path, monkeypatch
) -> None:
    """A rung that was not read cannot have been picked against, and a row that
    kept only its winner could never be used to ask which rung the head prefers —
    which is the whole measurement the outer rungs exist to buy."""
    drawn(monkeypatch)
    run = channel(tmp_path, rungs=reframing.RUNGS)
    run.run([ON_AN_ATOM])
    rows = reframing.read(run.ledger.path)
    assert rows
    for row in rows:
        assert [cell["rung"] for cell in row["reframing"]["rungs_drawn"]] == list(reframing.RUNGS)
        assert all(cell["p_ge4"] is not None for cell in row["reframing"]["rungs_drawn"])
        assert all(cell["p_ge3"] is not None for cell in row["reframing"]["rungs_drawn"])


# --------------------------------------------------------------------------- #
# 5. A nucleus location is centered.
# --------------------------------------------------------------------------- #
def test_every_nucleus_location_says_it_is_centered(tmp_path, monkeypatch) -> None:
    """The centre is the atom the operators solved for, and the row has to say so.

    Without the field a later framing refinement would recentre a quarter-frame
    off the nucleus and keep the location's name — the minibrot this whole channel
    exists to frame, off centre, in the picture a gallery seats.
    """
    drawn(monkeypatch)
    run = channel(tmp_path)
    run.run([ON_AN_ATOM])
    rows = reframing.read(run.ledger.path)
    assert rows
    assert all(row["centered"] is True for row in rows)


def test_the_centered_contract_is_the_one_curation_framing_honours(tmp_path, monkeypatch) -> None:
    """The two halves joined: what this channel writes is what that step reads.

    A guard on the flag alone would pass with a `curation.framing` that had never
    heard of it, which is exactly the failure it is here to stop.
    """
    from fractal_wallpapers.curation import framing

    drawn(monkeypatch)
    run = channel(tmp_path)
    run.run([ON_AN_ATOM])
    row = reframing.read(run.ledger.path)[0]
    assert framing.is_centered(row)
    window = framing.window({**row, "key": "k", "maxiter": row["maxiter"]})
    assert [frame.width_scale for frame in window] == list(framing.WIDTH_LADDER)
    assert all((frame.dx, frame.dy) == (0, 0) for frame in window)


def test_the_rungs_are_offered_directly_because_refinement_cannot_reach_them() -> None:
    """The built framing refinement moves x1.414 a step, so it cannot turn 16x
    into 32x in one move — which is why the ladder is offered rather than walked
    to. If that ladder ever widens, this guard is the thing that says so."""
    from fractal_wallpapers.curation import framing

    assert max(framing.WIDTH_LADDER) < 2.0
    assert reframing.RUNGS[-1] / reframing.RUNGS[0] > max(framing.WIDTH_LADDER)


# --------------------------------------------------------------------------- #
# What the row says about itself.
# --------------------------------------------------------------------------- #
def test_a_fate_is_the_supply_engines_own_and_not_a_second_reading_of_the_floors() -> None:
    """One function decides a fate, whether the row is a walk's or a channel's."""
    assert reframing.fate_of({"passed": True, "p_ge3": 1.0, "fate": "survived"}) == (
        ledger_module.SURVIVED
    )
    assert reframing.fate_of({"passed": True, "p_ge3": 0.0, "fate": "survived"}) == (
        ledger_module.NOT_ADMITTED
    )
    # A gate refusal keeps the gate's own name, so the channel's tally reads like
    # a walk's rather than collapsing every structural refusal into one word.
    assert reframing.fate_of({"passed": False, "p_ge3": 1.0, "fate": "interior_cap"}) == (
        "interior_cap"
    )


def test_the_q4_bar_is_the_currencys_two_cuts_and_nothing_else() -> None:
    """A nucleus is q4 when the keeper floor says it has a class at all and the
    great cut says which. Both through the currency, so a restatement of either
    moves this channel's promotion rule with it."""
    assert reframing.is_head_q4({"p_ge3": money.GOOD_FLOOR, "p_ge4": money.GREAT_CUT})
    assert not reframing.is_head_q4({"p_ge3": money.GOOD_FLOOR, "p_ge4": money.GREAT_CUT / 2})
    assert not reframing.is_head_q4({"p_ge3": money.GOOD_FLOOR / 2, "p_ge4": 1.0})
    assert not reframing.is_head_q4({"p_ge3": None, "p_ge4": None})


def test_the_cost_is_priced_per_operator_and_lands_on_the_summary(tmp_path, monkeypatch) -> None:
    """Seconds and yield per operator, on the record rather than on a stopwatch:
    "candidates per operator-minute" is what an evening leg is sized against."""
    drawn(monkeypatch)
    run = channel(tmp_path)
    report = run.run([ON_AN_ATOM])
    assert set(report["cost"]) <= set(reframing.OPERATORS)
    for tally in report["cost"].values():
        assert tally["calls"] >= 1
        assert tally["seconds"] >= 0.0
    assert report["rate"]["locations_per_operator_minute"] is not None
    assert report["seeds_available"] == 1
    assert report["seeds_consumed"] == 1


def test_a_seed_on_a_family_with_no_nucleus_is_skipped_rather_than_faked() -> None:
    """A Julia viewport is a z-plane point and has no nucleus in the
    parameter-plane sense. The operators are undefined there, and the channel says
    so instead of returning something."""
    julia = reframing.Seed(
        id="x",
        family={"kind": "julia", "c": [-0.4, 0.6]},
        viewport={"center_re": "0", "center_im": "0", "width": "3"},
        tier=3,
        generation=0,
    )
    found, cost = reframing.fire(julia, random.Random(0))
    assert found == []
    assert cost["refusals"] == {"reframing_undefined": 1}


def test_the_snap_at_a_seed_is_tighter_than_the_snap_at_a_walk_survivor() -> None:
    """The ported operator, and the whole of what was ported.

    A judged view is a claim about a picture, so a nucleus a whole frame width off
    centre was not in that picture and the verdict being inherited is not about it.
    `0.75` is the source project's `snap_max_fw_mult`.
    """
    assert operators.SNAP_AT_SEED_MAX_WIDTH_MULTIPLE == 0.75
    assert operators.SNAP_AT_SEED_MAX_WIDTH_MULTIPLE < operators.SNAP_MAX_WIDTH_MULTIPLE

    # Placed so the atom is inside the walk's radius and outside the seed's.
    rows = operators.snap_at_seed(
        {"node_id": 1, "center_re": "-0.1592", "center_im": "1.0317", "width": "1e-9"}, degree=2
    )
    assert rows[0].reason == operators.OUTSIDE_SEED_VIEW
    assert rows[0].reason != "nucleus_outside_frame", "the two refusals are priced apart"


# --------------------------------------------------------------------------- #
# 6. The seed queue.
# --------------------------------------------------------------------------- #
def test_the_queue_is_matt_q4_then_matt_q3_then_head_q4_then_head_keeper() -> None:
    """The order is a claim about what a seed is worth, and it is measured.

    A human verdict outranks the head's because it is the thing being inherited;
    inside the human half q4 outranks q3 because over generation 1's 1,056
    consumed seeds a q4 root returned a head-q4 at 11.4% against a q3 root's 4.2%.
    """
    assert reframing.SOURCES == ("matt_q4", "matt_q3", "head_q4", "head_keeper")
    assert reframing.source_of_tier(4) == "matt_q4"
    assert reframing.source_of_tier(3) == "matt_q3"
    # A widened --tier-floor spells what it admitted rather than being rounded
    # into the nearest name here, and sorts behind everything the queue knows.
    assert reframing.source_of_tier(2) == "matt_q2"
    assert reframing.priority_of("matt_q2") == len(reframing.SOURCES)

    mixed = [
        reframing.Seed("d", {}, {}, tier=3, generation=1, source="head_keeper"),
        reframing.Seed("b", {}, {}, tier=3, generation=0, source="matt_q3"),
        reframing.Seed("c", {}, {}, tier=4, generation=1, source="head_q4"),
        reframing.Seed("a", {}, {}, tier=4, generation=0, source="matt_q4"),
    ]
    assert [seed.id for seed in reframing.queued(mixed)] == ["a", "b", "c", "d"]
    # Stable inside a class, so `supply.proven`'s own digest order survives.
    twins = [
        reframing.Seed(name, {}, {}, tier=4, generation=0, source="matt_q4")
        for name in ("z", "y", "x")
    ]
    assert [seed.id for seed in reframing.queued(twins)] == ["z", "y", "x"]


def test_both_promotion_classes_fire_and_the_q4_ones_go_first(tmp_path, monkeypatch) -> None:
    """The generation loop, and the reason it has two classes rather than one.

    Generation 1 found 58 nuclei over the q4 bar and 496 over the keeper floor. A
    loop that promoted only the first would run its queue dry inside an hour of an
    overnight leg — and the keeper floor is the bar the supply engine already
    admits on, not a second opinion invented here.
    """
    drawn(monkeypatch)

    # Over the keeper floor, under the great cut: a keeper promotion, not a q4 one.
    run = channel(tmp_path / "keeper", scorer=Stub(p_ge3=0.99, p_ge4=0.0), generations=1)
    report = run.run([ON_AN_ATOM])
    assert report["head_q4"] == 0
    assert report["rounds"][0]["promoted"] >= 1
    assert set(report["rounds"][0]["promoted_by_source"]) == {reframing.HEAD_KEEPER}

    # Under the keeper floor: on the ledger, and no further.
    run = channel(tmp_path / "floor", scorer=Stub(p_ge3=0.0, p_ge4=0.0), generations=2)
    report = run.run([ON_AN_ATOM])
    assert [g["promoted"] for g in report["rounds"]] == [0]

    # Over both: a q4 promotion, and it is what generation 2 is offered first.
    run = channel(tmp_path / "q4", scorer=Stub(p_ge3=0.99, p_ge4=0.99), generations=1)
    report = run.run([ON_AN_ATOM])
    assert report["head_q4"] >= 1
    assert set(report["rounds"][0]["promoted_by_source"]) == {reframing.HEAD_Q4}


def test_every_row_says_which_generation_and_which_queue_class_produced_it(
    tmp_path, monkeypatch
) -> None:
    """Yield per seed by seed source is a division on the record or it is nothing.

    The **human** tier travels with a promotion and the head's verdict never
    becomes one: what says how far from the person the seed has drifted is the
    generation, and what says on whose word it was taken is the source.
    """
    drawn(monkeypatch)
    run = channel(tmp_path, scorer=Stub(p_ge3=0.99, p_ge4=0.99), generations=2)
    report = run.run([ON_AN_ATOM])
    rows = reframing.read(run.ledger.path)
    assert rows
    for row in rows:
        block = row["reframing"]
        assert block["seed"]["source"] in reframing.SOURCES
        assert block["generation"] == block["seed"]["generation"] + 1
        # A promotion inherits the person's tier, never the head's number.
        assert block["seed"]["tier"] == ON_AN_ATOM.tier
    assert [row["reframing"]["seed"]["source"] for row in rows][0] == "matt_q4"
    first, second = report["rounds"][:2]
    assert first["consumed_by_source"] == {"matt_q4": 1}
    assert sum(first["locations_by_source"].values()) == first["locations"]
    assert sum(first["head_q4_by_source"].values()) == first["head_q4"]
    # Generation 2 fires the promotions it was handed, and they are the q4 ones.
    # It writes no row here and that is the dedup working, not a fault: a
    # promotion's frame is already nucleus-centred, so the snap re-finds the atom
    # the run has already made a location of.
    assert second["offered_by_source"] == first["promoted_by_source"]
    assert set(second["consumed_by_source"]) == {reframing.HEAD_Q4}
    assert run.counts.get("nucleus_already_found", 0) >= 1


def test_a_continuing_leg_does_not_write_the_earlier_legs_nuclei_a_second_time(
    tmp_path, monkeypatch
) -> None:
    """`--prior`, and the duplicate it exists to stop.

    The atom-key dedup is per run. A second leg that re-derived its seeds from the
    label store would fire the same roots at the same atoms and put one nucleus in
    two ledgers — which the union reads as two locations, in two seats, counted
    twice in every book downstream.
    """
    drawn(monkeypatch)
    first = channel(tmp_path / "one", scorer=Stub(p_ge3=0.99, p_ge4=0.99))
    first.run([ON_AN_ATOM])
    rows = reframing.read(first.ledger.path)
    assert rows

    carried = reframing.prior_run(first.out_dir, log=lambda *_a: None)
    assert carried["found"] == {row["atom_key"] for row in rows}
    assert carried["fired"] == {ON_AN_ATOM.id}
    assert set(carried["record"]["promoted_by_source"]) == {reframing.HEAD_Q4}

    second = channel(tmp_path / "two", scorer=Stub(p_ge3=0.99, p_ge4=0.99))
    second.seen |= carried["found"]
    report = second.run([], carried=carried["promoted"])
    assert reframing.read(second.ledger.path) == []
    assert report["counts"]["nucleus_already_found"] >= 1
    assert report["seeds_consumed"] == len(carried["promoted"])


def test_a_chain_inherits_every_earlier_leg_and_not_only_the_last(tmp_path, monkeypatch) -> None:
    """The duplicate a one-directory `--prior` writes, and it is not hypothetical.

    A leg handed only its immediate predecessor inherits only that ledger's atom
    keys, so it re-finds and re-writes what the legs before it found. On the night
    of 2026-08-31 a fourth leg handed only the third's ledger wrote 192 of its 302
    rows on atoms the first leg already held — one atom in two ledgers, which is
    two location keys the moment the two legs pick different rungs, which is one
    atom in two seats.
    """
    drawn(monkeypatch)
    first = channel(tmp_path / "one", scorer=Stub(p_ge3=0.99, p_ge4=0.99))
    first.run([ON_AN_ATOM])
    held = {row["atom_key"] for row in reframing.read(first.ledger.path)}
    assert held, "the first leg must have found something for this guard to mean anything"

    second = channel(tmp_path / "two", scorer=Stub(p_ge3=0.99, p_ge4=0.99), seed=5)
    second.seen |= reframing.prior_run(first.out_dir, log=lambda *_a: None)["found"]
    second.run([ON_AN_ATOM])

    only_the_last = reframing.prior_run(second.out_dir, log=lambda *_a: None)
    whole_chain = reframing.prior_run([first.out_dir, second.out_dir], log=lambda *_a: None)
    assert not (held & only_the_last["found"]), "the last ledger cannot know the first's atoms"
    assert held <= whole_chain["found"]
    assert len(whole_chain["record"]["priors"]) == 2
    assert whole_chain["record"]["nuclei_found"] > only_the_last["record"]["nuclei_found"]
    # And every seed the chain fired at is spent, promotions included — which is
    # what a plain continuation drops and a --reprobe leg deliberately keeps.
    assert ON_AN_ATOM.id in whole_chain["spent"]
    assert ON_AN_ATOM.id in whole_chain["fired"]


def test_a_reprobe_fires_at_a_spent_root_again_and_still_writes_no_duplicate(
    tmp_path, monkeypatch
) -> None:
    """The lever that keeps the channel yielding after its queue converges.

    A generation returns well under one promotion per seed, so the promotion queue
    is geometric and dies. `expand_neighborhood` probes at random, so the same
    root sampled again is a different sample of the same neighbourhood — which is
    a source of new atoms that does not need a new label. The dedup is what makes
    it safe: what a re-probe can add is exactly what the earlier pass missed.
    """
    drawn(monkeypatch)
    first = channel(tmp_path / "one", scorer=Stub(p_ge3=0.99, p_ge4=0.99))
    first.run([ON_AN_ATOM])
    carried = reframing.prior_run(first.out_dir, log=lambda *_a: None)
    assert carried["fired"] == {ON_AN_ATOM.id}

    again = channel(tmp_path / "two", scorer=Stub(p_ge3=0.99, p_ge4=0.99), seed=7)
    again.seen |= carried["found"]
    again.run([ON_AN_ATOM])
    written = reframing.read(again.ledger.path)
    assert not (carried["found"] & {row["atom_key"] for row in written})
    assert again.counts.get("nucleus_already_found", 0) >= 1


def test_a_keeper_row_carries_forward_as_a_keeper_and_a_rejected_one_not_at_all(
    tmp_path, monkeypatch
) -> None:
    """The classes a prior ledger's rows earn, read off the rows and not re-judged."""
    drawn(monkeypatch)
    run = channel(tmp_path / "keeper", scorer=Stub(p_ge3=0.99, p_ge4=0.0))
    run.run([ON_AN_ATOM])
    carried = reframing.prior_run(run.out_dir, log=lambda *_a: None)
    assert set(carried["record"]["promoted_by_source"]) == {reframing.HEAD_KEEPER}

    run = channel(tmp_path / "floor", scorer=Stub(p_ge3=0.0, p_ge4=0.0))
    run.run([ON_AN_ATOM])
    carried = reframing.prior_run(run.out_dir, log=lambda *_a: None)
    assert carried["promoted"] == []
    # And the nuclei are still off the queue, whatever the head said about them.
    assert carried["found"]


def test_a_crashed_screen_batch_costs_its_frames_and_not_the_leg(tmp_path, monkeypatch) -> None:
    """The failure that ended an eight-hour leg two minutes in.

    One `engine.screen` process died returning nonzero with empty stdout and
    empty stderr — a hard crash rather than a refusal it could describe — and the
    whole leg went with it. An unattended leg that stops on one frame has spent
    the night, which is a worse failure than sixty-four missing rows. So the
    batch is retried, a batch that crashes twice is given up on, and the leg
    carries on.
    """
    from fractal_wallpapers import engine

    calls = {"n": 0}

    def crashing(spec):
        calls["n"] += 1
        raise RuntimeError("engine failed: ")

    monkeypatch.setattr(engine, "screen", crashing)
    lines = []
    run = channel(tmp_path, log=lines.append)
    report = run.run([ON_AN_ATOM])
    assert calls["n"] == reframing.SCREEN_RETRIES + 1, "the batch is tried again, once"
    assert reframing.read(run.ledger.path) == []
    assert report["counts"]["nucleus_not_drawn"] >= 1
    assert any("given up on" in line for line in lines)


def test_the_seed_snap_scans_further_than_the_walks_own_ceiling() -> None:
    """256, and the measurement behind it.

    On 60 generation-1 seeds the snap found 24 nuclei at a ceiling of 64 in 5.1 s,
    30 at 128 in 8.6 s and **35 at 256 in 17.7 s** — 58% against 40% at 3.5x the
    Newton cost. It is the right trade here and the wrong one in the walk: the
    snap is a tenth of this channel's operator clock and seeds are the scarce
    thing, so a seed the snap misses is a seed nothing else reaches.
    """
    assert reframing.SEED_SNAP_MAX_PERIOD == 256
    assert reframing.SEED_SNAP_MAX_PERIOD > operators.MAX_PERIOD

    seen = {}
    real = operators.snap_at_seed

    def spy(view, *, degree, framings, max_period=operators.MAX_PERIOD, **rest):
        seen["max_period"] = max_period
        return real(view, degree=degree, framings=framings, max_period=max_period, **rest)

    original = reframing.operators.snap_at_seed
    try:
        reframing.operators.snap_at_seed = spy
        reframing.fire(ON_AN_ATOM, random.Random(0))
    finally:
        reframing.operators.snap_at_seed = original
    assert seen["max_period"] == reframing.SEED_SNAP_MAX_PERIOD


def test_the_sheet_cut_reads_the_key_spelling_the_embedding_store_writes(
    tmp_path, monkeypatch
) -> None:
    """The pre-selection, and the way it failed without saying anything.

    `distinct.suppress` keeps a place with no neutral descriptor by rule, so a
    caller offering keys in the wrong spelling gets every place back and no
    error. This offers rows whose descriptors ARE in the store: a reader on
    `str(key)` matches none of them and the refusal count is zero.
    """
    from fractal_wallpapers.curation import distinct
    from fractal_wallpapers.supply import location as location_module

    drawn(monkeypatch)
    run = channel(tmp_path)
    run.run([ON_AN_ATOM])
    first = reframing.read(run.ledger.path)[0]
    rows = [
        first,
        {
            **first,
            "viewport": {
                **first["viewport"],
                "width": repr(float(first["viewport"]["width"]) * 1.5),
            },
        },
    ]

    # Two places one hair apart, spelled the way every store on disk spells them.
    stored = [
        {"key": location_module.text_of_row(row), "vector": vector}
        for row, vector in zip(rows, ("A", "B"), strict=True)
    ]
    seen = {}

    def matrix_for(locations, store=None):
        del store
        seen["asked"] = list(locations)
        import numpy

        kept = [row for row in stored if row["key"] in set(locations)]
        return [row["key"] for row in kept], numpy.ones((len(kept), 4), dtype="float32") / 2.0

    monkeypatch.setattr(distinct, "matrix_for", matrix_for)
    kept, record = reframing.distinct_places(rows, log=lambda _l: None)
    assert record["admitted_without_a_descriptor"] == 0
    assert record["places_refused"] == 1, "identical vectors, so one must lose"
    assert len(kept) == 1
    assert all(name.startswith("[") for name in seen["asked"])


def test_the_ledger_is_readable_json_lines_carrying_their_own_join(tmp_path, monkeypatch) -> None:
    """Every row a complete location: the family with its constants and the
    viewport, on the line, so a candidate is never split across two files."""
    drawn(monkeypatch)
    run = channel(tmp_path)
    run.run([ON_AN_ATOM])
    text = run.ledger.path.read_text(encoding="utf-8")
    for line in text.splitlines():
        row = json.loads(line)
        assert row["schema"] == ledger_module.SCHEMA
        if row["kind"] == "candidate":
            assert row["family"] and row["viewport"]
            assert location_key(row["family"], row["viewport"]) is not None
