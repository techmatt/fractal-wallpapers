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


def channel(tmp_path, scorer=None, pinned=frozenset(), **kwargs):
    return reframing.Channel(
        out_dir=tmp_path / "reframe",
        scorer=scorer or Stub(),
        pinned=set(pinned),
        log=lambda *_a, **_k: None,
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
def test_the_rung_set_is_16_24_and_32_atom_sizes() -> None:
    """The band that reads as a minibrot with detail around it is 50-100 px of
    body at 1280, which is the 32x rung and nothing else; the walk's widest rung
    is 16x and is a factor of two too tight. Nothing below 16x is offered: the 2x
    frame is half interior and the walk's own cap refuses it outright."""
    assert reframing.RUNGS == (16.0, 24.0, 32.0)
    assert min(reframing.RUNGS) >= max(f for f in operators.FRAMINGS if f is not None)


def test_every_rung_is_drawn_and_scored_and_all_three_readings_are_on_the_row(
    tmp_path, monkeypatch
) -> None:
    """A rung that was not read cannot have been picked against, and a row that
    kept only its winner could never be used to ask which rung the head prefers —
    which is the measurement the 24x rung exists to buy."""
    drawn(monkeypatch)
    run = channel(tmp_path, rungs=(16.0, 24.0, 32.0))
    run.run([ON_AN_ATOM])
    for row in reframing.read(run.ledger.path):
        assert [cell["rung"] for cell in row["reframing"]["rungs_drawn"]] == [16.0, 24.0, 32.0]
        assert all(cell["p_ge4"] is not None for cell in row["reframing"]["rungs_drawn"])


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


def test_a_generation_promotes_only_what_clears_the_q4_bar(tmp_path, monkeypatch) -> None:
    """The loop, and its bound. A nucleus at or above the bar is next generation's
    seed; one below it is on the ledger and goes no further."""
    drawn(monkeypatch)
    run = channel(tmp_path, scorer=Stub(p_ge3=0.99, p_ge4=0.0), generations=2)
    report = run.run([ON_AN_ATOM])
    assert report["head_q4"] == 0
    assert [g["promoted"] for g in report["generations"]] == [0]

    run = channel(tmp_path / "b", scorer=Stub(p_ge3=0.99, p_ge4=0.99), generations=1)
    report = run.run([ON_AN_ATOM])
    assert report["head_q4"] >= 1
    # Generation 1 only: the promotion is recorded and not fired.
    assert len(report["generations"]) == 1
    assert report["generations"][0]["promoted"] >= 1


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
