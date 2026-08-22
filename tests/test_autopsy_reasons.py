"""Why a refused card is refused — derived from the run, or left unsaid.

The rule the reasons are held to is the one that makes them worth reading: a
reason appears only where the run data supports it. A card whose run kept no
batch trace, or whose family belongs to no partition, gets the half the ledger
knows and no more.
"""

from __future__ import annotations

from fractal_wallpapers.discovery import ledger as ledger_module
from fractal_wallpapers.supply import autopsy


def facts(expanded=(), booked=None) -> dict:
    return {"expanded": set(expanded), "booked": dict(booked or {})}


def trace(batch: int, slots=None, share=None, capped=()) -> dict:
    return {
        "batch": batch,
        "slots": dict(slots or {}),
        "share": {"slots": dict(share or {})},
        "capped": list(capped),
    }


def node(batch: int, node_id: int, root: int = 1, fate: str = ledger_module.EXPANDABLE) -> dict:
    return {
        "kind": "candidate",
        "batch": batch,
        "node_id": node_id,
        "root_id": root,
        "fate": fate,
        "family": {"kind": "multibrot", "degree": 3},
    }


ON = {"lineage_discount": {"status": "on"}}
OFF = {"lineage_discount": {"status": "off"}}


def test_a_row_below_the_junk_floor_says_the_floor_killed_it() -> None:
    """It never reached the frontier, so no allocation ever had the chance to
    pass it over. Naming a slot reason here would be inventing one."""
    reasons = autopsy.Reasons(facts(), {0: trace(0)}, OFF)
    said = reasons.of(node(0, 5, fate=ledger_module.NOT_ADMITTED))
    assert said == autopsy.JUNK_FLOOR


def test_a_structural_refusal_says_what_its_gate_is_about() -> None:
    """The `fate` line names the gate; the reason says what the gate is. These are
    most of any run's refusals, and they used to be the cards with nothing on
    them — which made the reject half of the page unreadable to anybody who did
    not already know the pipeline."""
    reasons = autopsy.Reasons(facts(), {0: trace(0)}, OFF)
    assert reasons.of({**node(0, 5), "fate": "interior_cap"}) == autopsy.GATES["interior_cap"]


def test_every_declared_gate_has_a_sentence_and_an_unknown_one_says_so() -> None:
    """A fate added to the ledger and not here must leave a card that admits it
    rather than a card that quietly drops the line."""
    from fractal_wallpapers.discovery import ledger as ledger_module

    structural = set(ledger_module.FATES) - set(ledger_module.SCORED)
    assert structural == set(autopsy.GATES)

    reasons = autopsy.Reasons(facts(), {0: trace(0)}, OFF)
    unknown = reasons.of({**node(0, 5), "fate": "a_gate_invented_tomorrow"})
    assert "a_gate_invented_tomorrow" in unknown
    # And an admitted row still has no refusal to explain.
    assert reasons.of({**node(0, 5), "fate": ledger_module.SURVIVED}) is None


def test_a_node_the_walk_expanded_is_refused_by_the_good_floor_alone() -> None:
    """It was stood on. Nothing outbid it, so the only thing keeping it out of the
    books is its own score."""
    reasons = autopsy.Reasons(facts(expanded=[7]), {0: trace(0), 1: trace(1)}, OFF)
    assert reasons.of(node(0, 7)) == autopsy.GOOD_FLOOR


def test_a_partition_capped_for_every_later_batch_says_capped() -> None:
    reasons = autopsy.Reasons(
        facts(),
        {0: trace(0), 1: trace(1, capped=["multibrot3"]), 2: trace(2, capped=["multibrot3"])},
        OFF,
    )
    assert autopsy.CAPPED in reasons.of(node(0, 7))


def test_a_partition_that_took_no_slot_says_outbid_on_partition() -> None:
    """Uncapped, offered, and never served: the batch went somewhere else every
    time. That is a different failure from losing inside your own partition."""
    reasons = autopsy.Reasons(
        facts(), {0: trace(0), 1: trace(1, slots={"mandelbrot": 4}), 2: trace(2)}, OFF
    )
    assert autopsy.OUTBID_PARTITION in reasons.of(node(0, 7))


def test_a_served_partition_says_the_node_lost_on_rank() -> None:
    reasons = autopsy.Reasons(
        facts(), {0: trace(0), 1: trace(1, slots={"multibrot3": 2}), 2: trace(2)}, OFF
    )
    assert autopsy.OUTBID_RANK in reasons.of(node(0, 7))


def test_a_lineage_that_had_booked_says_the_discount_priced_it_down() -> None:
    """The contest ranks by a key that discounts a lineage by what it has already
    booked *this run*. Where that discount was on and the root had booked, it is
    the more specific answer than losing on rank."""
    traces = {0: trace(0), 1: trace(1, slots={"multibrot3": 2}), 2: trace(2)}
    booked = {1: 0}
    assert autopsy.DISCOUNTED in autopsy.Reasons(facts(booked=booked), traces, ON).of(node(0, 7))
    # Off, it is not a fact about this run and is not claimed.
    assert autopsy.OUTBID_RANK in autopsy.Reasons(facts(booked=booked), traces, OFF).of(node(0, 7))
    # And a lineage that first booked in the final batch never priced this node.
    late = autopsy.Reasons(facts(booked={1: 2}), traces, ON).of(node(0, 7))
    assert autopsy.OUTBID_RANK in late


def test_a_node_still_on_the_frontier_when_the_run_stopped_says_so() -> None:
    """Nothing outbid it. The clock ran out, which is a state and not a verdict."""
    reasons = autopsy.Reasons(facts(), {0: trace(0), 1: trace(1)}, OFF)
    assert autopsy.UNSPENT in reasons.of(node(1, 7))


def test_a_run_with_no_trace_gets_the_floor_half_and_no_more() -> None:
    """Every ledger written before the quota kept a trace. The page says what the
    row says, and stops — a guess would be worse than a shorter caption."""
    reasons = autopsy.Reasons(facts(), {}, OFF)
    assert reasons.of(node(0, 7)) == autopsy.NEVER_EXPANDED


def test_a_family_outside_the_partition_registry_gets_no_slot_reason() -> None:
    """A render-only family reaches pictures and never the books, so there is no
    partition whose allocation could have passed it over."""
    reasons = autopsy.Reasons(facts(), {0: trace(0), 1: trace(1)}, OFF)
    stranger = {**node(0, 7), "family": {"kind": "fractional_multibrot", "degree": "2.5"}}
    assert reasons.of(stranger) == autopsy.NEVER_EXPANDED
