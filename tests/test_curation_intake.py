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


def test_the_funnel_puts_each_number_over_the_population_it_is_of(ledger) -> None:
    """The first production run printed "22,751 found, 1,245 above the junk floor"
    with every gate survivor as the denominator and only the scored prefix as the
    numerator, which understated the pass rate by a factor of four. The scored
    count sits between the two so a reader can see which is which."""
    survivors, _ = intake.gate_survivors([ledger])
    scores = scores_for(survivors[:2], [0.4, 0.9])
    _, diagnostics = intake.ranked([ledger], scores)

    assert diagnostics["found"] == 3
    assert diagnostics["scored"] == 2
    assert diagnostics["passing"] == 2
    assert diagnostics["unscored"] == 1
    assert diagnostics["scored"] + diagnostics["unscored"] == diagnostics["found"]

    line = intake.funnel_line(diagnostics)
    assert "3 found" in line and "2 scored" in line and "1 found but unscored" in line


def test_a_partition_s_line_names_its_own_scored_denominator(ledger) -> None:
    survivors, _ = intake.gate_survivors([ledger])
    scores = scores_for(survivors[:1], [0.9])
    _, diagnostics = intake.ranked([ledger], scores)
    assert diagnostics["scored_by_partition"] == {"mandelbrot": 1}
    line = next(line for line in intake.supply_lines(diagnostics) if line.startswith("mandelbrot:"))
    assert "2 found, 1 scored, 1 of those above the junk floor" in line


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


# --------------------------------------------------------------------------- #
# The sidecar: one upsert per ledger, never a wholesale rewrite.
# --------------------------------------------------------------------------- #
def written(path, centers) -> object:
    """A walk ledger holding one gate-surviving candidate per centre."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(candidate(c)) + "\n" for c in centers), encoding="utf-8")
    return path


@pytest.fixture
def score(tmp_path, monkeypatch):
    """`intake.score`, with the renderer and the head stubbed out.

    What is under test is which rows the sidecar keeps across invocations, not
    what the judge said about them, and the real halves need a release engine and
    a shipped head that this question does not depend on.
    """
    from fractal_wallpapers.models import scoring, ship, train

    monkeypatch.setattr(intake, "store_dir", lambda: tmp_path / "curation")
    monkeypatch.setattr(intake, "view_dir", lambda: tmp_path / "views")
    monkeypatch.setattr(intake.floors, "live_stamp", lambda head: "a-stamp")
    monkeypatch.setattr(intake.location_view, "canonical_map", lambda: "twilight_shifted")
    monkeypatch.setattr(intake.location_view, "cyclic_maps", lambda: set())
    monkeypatch.setattr(intake.location_view, "summary", lambda colormap: {"map": colormap})
    monkeypatch.setattr(
        intake.location_view,
        "render_view",
        lambda row, colormap, cyclic, directory: (directory / f"{row['node_id']}.jpg", False),
    )
    monkeypatch.setattr(ship, "shipped_path", lambda head: tmp_path / "head.pt")
    monkeypatch.setattr(scoring, "load", lambda path, device: (None, {"classes": 4}, "cpu"))
    monkeypatch.setattr(scoring, "transform_of", lambda config: None)
    monkeypatch.setattr(
        train, "score", lambda model, pictures, *rest: [[0.9, 0.8, 0.7]] * len(pictures)
    )
    return lambda paths, **kw: intake.score(paths, log=lambda _m: None, **kw)


def test_two_ledgers_scored_in_two_invocations_hold_their_union(tmp_path, score) -> None:
    """Scoping a run's scoring to its own ledger used to be destructive: it took
    the sidecar from 12,580 rows to 6,907 and reported nothing about the 5,673."""
    first = written(tmp_path / "a" / "walk.jsonl", ["-0.5", "-0.6"])
    second = written(tmp_path / "b" / "walk.jsonl", ["-0.7"])
    score([first])
    report = score([second])
    assert (report["sidecar"]["rows_scored"], report["sidecar"]["rows_kept"]) == (1, 2)
    assert len(intake.read_scores()) == 3


def test_re_scoring_one_ledger_replaces_its_own_rows_and_touches_no_other(tmp_path, score) -> None:
    first = written(tmp_path / "a" / "walk.jsonl", ["-0.5", "-0.6"])
    second = written(tmp_path / "b" / "walk.jsonl", ["-0.7"])
    score([first])
    score([second])
    before = intake.scores_path().read_bytes()

    report = score([first])
    assert report["sidecar"]["rows_scored"] == 2, "its own rows, minted again"
    assert report["sidecar"]["rows_kept"] == 1, "the other ledger's row, untouched"
    assert intake.scores_path().read_bytes() == before, "an idempotent re-score"


def test_a_ledger_that_lost_a_location_loses_its_row(tmp_path, score) -> None:
    """The replacement is per ledger rather than per row, so a re-score is the
    ledger's whole current answer and not a merge with its old one."""
    first = written(tmp_path / "a" / "walk.jsonl", ["-0.5", "-0.6"])
    written(tmp_path / "b" / "walk.jsonl", ["-0.7"])
    score([first])
    score([tmp_path / "b" / "walk.jsonl"])
    written(first, ["-0.5"])
    score([first])
    assert sorted(row["node_id"] for row in intake.read_scores().values()) == ["-0.5", "-0.7"]


def test_a_limited_pass_upserts_what_it_looked_at_and_clears_nothing(tmp_path, score) -> None:
    """A prefix is not an answer about the rows it never reached."""
    ledger = written(tmp_path / "a" / "walk.jsonl", ["-0.5", "-0.6"])
    score([ledger])
    report = score([ledger], limit=1)
    assert report["sidecar"]["scoped_ledgers"] == []
    assert len(intake.read_scores()) == 2
