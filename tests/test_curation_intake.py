"""Intake: the ranked offer, the floor that acts on it, and the slots it implies."""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.curation import intake
from fractal_wallpapers.discovery import ledger as ledger_module
from fractal_wallpapers.supply.location import key_of_row


def candidate(center: str, fate: str = ledger_module.SURVIVED, family=None) -> dict:
    return {
        "schema": ledger_module.SCHEMA,
        "kind": "candidate",
        "node_id": center,
        "family": family or {"kind": "mandelbrot"},
        "viewport": {"center_re": center, "center_im": "0", "width": "0.5"},
        "maxiter": 500,
        "fate": fate,
        "score": None,
    }


@pytest.fixture
def ledger(tmp_path):
    """A walk ledger with three survivors and one gate refusal."""
    path = tmp_path / "walk.jsonl"
    rows = [
        candidate("-0.5"),
        candidate("-0.6"),
        candidate("-0.7", family={"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]}),
        candidate("-0.8", fate="flat"),
    ]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def scores_for(rows, values) -> dict:
    return {
        json.dumps(key_of_row(row), ensure_ascii=False): {"p_ge3": value}
        for row, value in zip(rows, values, strict=True)
    }


def test_a_gate_refusal_is_not_supply(ledger) -> None:
    survivors, _ = intake.gate_survivors([ledger])
    assert len(survivors) == 3
    assert all(row["fate"] == ledger_module.SURVIVED for row in survivors)


def test_the_offer_is_best_first_and_the_junk_floor_acts(ledger) -> None:
    survivors, _ = intake.gate_survivors([ledger])
    scores = scores_for(survivors, [0.4, 0.9, 0.05])
    offer, diagnostics = intake.ranked([ledger], scores)
    assert [row["score"] for row in offer["mandelbrot"]] == [0.9, 0.4]
    # The 0.05 row is below the junk floor: found, counted, never offered.
    assert "julia:mandelbrot" not in offer
    assert diagnostics["found_by_partition"] == {"julia:mandelbrot": 1, "mandelbrot": 2}
    assert diagnostics["passing_by_partition"] == {"mandelbrot": 2}


def test_a_location_the_sidecar_has_no_opinion_about_is_counted_and_not_offered(
    ledger,
) -> None:
    """An unscored row has no verdict to spend compute on, and it is not silently
    dropped either — the count is how a reader knows the number is small."""
    offer, diagnostics = intake.ranked([ledger], {})
    assert offer == {}
    assert diagnostics["unscored"] == 3
    assert diagnostics["found"] == 3


def test_every_partition_the_union_saw_gets_a_line_including_the_ones_that_ship_nothing(
    ledger,
) -> None:
    survivors, _ = intake.gate_survivors([ledger])
    scores = scores_for(survivors, [0.4, 0.9, 0.05])
    _, diagnostics = intake.ranked([ledger], scores)
    lines = intake.supply_lines(diagnostics)
    assert any(line.startswith("julia:mandelbrot") for line in lines)
    assert any("thin supply" in line for line in lines)


def test_the_guarantee_triggers_on_the_good_floor_not_the_junk_floor(ledger) -> None:
    survivors, _ = intake.gate_survivors([ledger])
    scores = scores_for(survivors, [0.4, 0.9, 0.05])
    _, diagnostics = intake.ranked([ledger], scores)
    # 0.4 clears the junk floor but not the good one; 0.9 clears both.
    assert diagnostics["good_by_partition"] == {"mandelbrot": 1}
    assert intake.guaranteed(diagnostics) == ["mandelbrot"]


def test_a_guaranteed_partition_is_seated_where_the_mix_alone_would_zero_it() -> None:
    """At small n the mix zeroes the lowest-ratio partitions whatever their supply."""
    partitions = ("mandelbrot", "phoenix:classic")
    bare = intake.slots(partitions, 2)
    assert bare["phoenix:classic"] == 0
    floored = intake.slots(partitions, 2, guarantees=["phoenix:classic"])
    assert floored["phoenix:classic"] == 1
    assert sum(floored.values()) == 2


def test_a_guarantee_is_a_floor_and_not_a_bonus() -> None:
    """A partition the mix already seats gains nothing from being named."""
    partitions = ("mandelbrot", "julia:mandelbrot", "phoenix")
    bare = intake.slots(partitions, 9)
    named = intake.slots(partitions, 9, guarantees=["mandelbrot"])
    assert named == bare


def test_the_emit_caps_come_off_the_offers_own_size(ledger) -> None:
    survivors, _ = intake.gate_survivors([ledger])
    scores = scores_for(survivors, [0.4, 0.9, 0.9])
    offer, _ = intake.ranked([ledger], scores)
    assert intake.emit_caps(offer) == {"julia:mandelbrot": 0, "mandelbrot": 0}


def test_the_canonical_view_is_the_deploy_map(ledger) -> None:
    """The picture a location is judged on is the one a deployed judge is handed."""
    assert intake.canonical_map() == "twilight_shifted"
    row = intake.view_row(candidate("-0.5"), "twilight_shifted", {"twilight_shifted"})
    assert row["mode"] == "smooth"
    assert row["render"]["resolution"] == [640, 360]
    assert row["recipe"]["mirror"] is False


def test_a_score_read_needs_a_sidecar_before_it_can_rank(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(intake, "store_dir", lambda: tmp_path)
    with pytest.raises(intake.IntakeError):
        intake.read_scores()
