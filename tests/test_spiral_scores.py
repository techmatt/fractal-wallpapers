"""The location-side spiral score, and the share cap that reads it.

Two properties carry everything here. **Unknown is not `not_spiral`**: a place
nobody has scored counts toward nothing, in both directions, and every guard
below that touches an unscored location is checking that asymmetry. And **the cap
is a share of the REALIZED seats**, so it paces the gallery as it fills rather
than being spent against a seat count nobody is promising to reach.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.curation import ceiling, rules, solve, spiral_scores


def _candidate(key, *, location=None, spiral=False, p_spiral=None, group=None, score=0.9):
    return solve.Candidate(
        key=str(key),
        location=str(location if location is not None else f"L{key}"),
        partition="mandelbrot",
        mode="smooth",
        group=str(group if group is not None else f"g{key}"),
        kind="smooth_render",
        cells=(),
        families=(),
        score=score,
        p_ge3=score,
        picture=f"{key}.jpg",
        spiral=spiral,
        p_spiral=p_spiral,
    )


def _state(cap, n=1000):
    rule = solve.rule_for({})
    rule.group_cap = 10_000
    return rules.State(rule, n, diversity=None, spiral_cap=cap)


# --------------------------------------------------------------------------- #
# The store.
# --------------------------------------------------------------------------- #
def test_a_row_carries_both_provenances():
    """A picture stamp alone cannot catch a re-fit, and a probe digest alone
    cannot catch the encoder moving. Each can move without the other."""
    row = spiral_scores.row_of("L1", 0.87, "stamp12", "neutral_dinov2", "digest12")
    assert row["stamp"] == "stamp12"
    assert row["probe_digest"] == "digest12"
    assert row["schema"] == spiral_scores.SCHEMA


def test_the_probe_digest_moves_when_a_coefficient_does_and_not_otherwise():
    base = {
        "feature_set": "neutral_dinov2",
        "intercept": -1.9,
        "coefficients": [0.1, 0.2],
        "mean": [0.0, 0.0],
        "deviation": [1.0, 1.0],
    }
    assert spiral_scores.probe_digest(base) == spiral_scores.probe_digest(dict(base))
    moved = {**base, "coefficients": [0.1, 0.2000001]}
    assert spiral_scores.probe_digest(moved) != spiral_scores.probe_digest(base), (
        "a re-fit changes every score in the store while changing no picture, so the "
        "picture stamp cannot be the only thing guarding it"
    )


@pytest.mark.parametrize("field", ["stamp", "probe_digest"])
def test_a_second_provenance_is_refused(tmp_path, field):
    path = tmp_path / "spiral_scores.jsonl"
    path.write_text(
        json.dumps(spiral_scores.row_of("L1", 0.5, "stamp12", "neutral_dinov2", "digest12")) + "\n",
        encoding="utf-8",
    )
    held = {"stamp": "stamp12", "digest": "digest12"}
    held["stamp" if field == "stamp" else "digest"] = "moved"
    with pytest.raises(spiral_scores.StoreRefused):
        spiral_scores.refuse_a_second_provenance(path, held["stamp"], held["digest"])


def test_spirals_holds_only_what_cleared_the_cut_and_omits_the_unscored(tmp_path):
    path = tmp_path / "spiral_scores.jsonl"
    path.write_text(
        "".join(
            json.dumps(spiral_scores.row_of(key, value, "s", "neutral_dinov2", "d")) + "\n"
            for key, value in (("high", 0.9), ("edge", 0.3), ("low", 0.05))
        ),
        encoding="utf-8",
    )
    held = spiral_scores.spirals(path, cut=0.3)
    assert held == {"high", "edge"}, "the cut is inclusive at its own value"
    assert "never_scored" not in held, "an absent location is absent, never a negative"


# --------------------------------------------------------------------------- #
# The cap.
# --------------------------------------------------------------------------- #
def test_the_cap_is_a_share_of_the_realized_seats():
    state = _state(0.10)
    assert state.spiral_allowance() == 1, "the first seat may be a spiral: ceil(0.1 * 1)"
    for n in range(20):
        state.seat(_candidate(f"n{n}"), "t")
    assert state.spiral_allowance() == ceiling.share_of(0.10, 21)
    assert state.spiral_allowance() == 3


def test_the_cap_paces_the_gallery_rather_than_front_loading_it():
    """Offered nothing but spirals and non-spirals alternately, the realized share
    lands ON the cap rather than spending it in the opening seats."""
    state = _state(0.10)
    admitted = 0
    for n in range(200):
        spiral = _candidate(f"s{n}", spiral=True, p_spiral=0.9)
        if state.counted_refusal(spiral) is None:
            state.seat(spiral, "t")
            admitted += 1
        else:
            state.seat(_candidate(f"n{n}"), "t")
    assert state.filled == 200
    assert admitted == len(state.spirals) == 20
    assert len(state.spirals) / state.filled == pytest.approx(0.10, abs=0.005)


def test_an_unscored_location_is_capped_by_nothing_and_fills_nothing():
    state = _state(0.0)
    unknown = _candidate("u", spiral=False, p_spiral=None)
    assert state.counted_refusal(unknown) is None, (
        "a cap of zero refuses every spiral and must still admit a place nobody scored"
    )
    state.seat(unknown, "t")
    assert len(state.spirals) == 0, "and it must not eat the allowance either"


def test_the_cap_names_itself_in_the_refusal_and_the_requirement():
    state = _state(0.10)
    state.seat(_candidate("s0", spiral=True, p_spiral=0.9), "t")
    blocked = _candidate("s1", spiral=True, p_spiral=0.8)
    assert state.counted_refusal(blocked) == "spiral"
    assert state.counted_requirements(blocked) == [{"s0"}], (
        "one seated spiral has to leave, and it is the seated spirals that are named"
    )
    assert "spiral" in rules.rules_for(None), "the census partitions on this name"


def test_no_cap_means_the_rule_cannot_refuse_anything():
    state = _state(None)
    assert state.spiral_allowance() is None
    for n in range(50):
        candidate = _candidate(f"s{n}", spiral=True, p_spiral=0.99)
        assert state.counted_refusal(candidate) is None
        state.seat(candidate, "t")
    assert state.record()["spiral_cap"] is None


def test_unseating_a_spiral_gives_the_allowance_back():
    """The swap loop's half of it: a seat that leaves has to stop counting."""
    state = _state(0.10)
    state.seat(_candidate("s0", spiral=True, p_spiral=0.9), "t")
    assert len(state.spirals) == 1
    state.unseat("s0")
    assert state.spirals == {}, "a spiral that left the gallery still holding its seat"


def test_share_of_is_the_one_spelling_a_target_and_a_cap_share():
    """A target is a floor under this quantity and a cap is a ceiling over it, and
    they must not be able to disagree about what the quantity is."""
    demand = solve.Demand(name="target:x", axis="cell", of="x", share=0.10)
    for filled in (0, 1, 9, 10, 11, 941):
        assert demand.wanted(filled) == ceiling.share_of(0.10, filled)


def test_a_pool_built_from_handed_in_rows_does_not_read_the_real_store(monkeypatch):
    """`tests/README.md`'s rule, at the one new site that could break it.

    A guard that builds a three-row pool in `tmp_path` must not sweep this
    machine's real spiral store on the way — that is the
    `candidate_ledger.prune` -> `intake.read_scores` failure, which cost 4.5-10 s
    a test and was invisible because the answer was still correct.
    """
    read = []
    monkeypatch.setattr(spiral_scores, "by_key", lambda *a, **k: read.append(1) or {})
    rows = [
        {
            "key": "k1",
            "recipe": {"palette_group": "g", "mode": "smooth"},
            "location": {"key": "L1"},
            "partition": "mandelbrot",
            "picture": None,
            "at_candidate_regime": True,
            "colour": {"cells": [], "families": []},
        }
    ]
    solve.pool(rows=rows, scores=[], log=lambda *a: None)
    assert read == [], "handing in rows means handing in a pool, and the store stayed shut"
