"""The acting release bar, and the retroactive rejection that comes with it.

Four claims, and the third is the one that is easy to get wrong: an unfillable
slot goes unfilled rather than down to the next row, the smooth path does not
move because a decision was taken about the strange one, a rejected row leaves
every served view while staying in the records, and re-running the rejection
changes nothing.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.curation import floors, records, rejection, selection, sheet


@pytest.fixture(autouse=True)
def unbound():
    records.use(None)
    yield
    records.use(None)


@pytest.fixture
def bar(tmp_path, monkeypatch):
    """A live acting bar at 0.5 on a head named `h`, with a movable manifest."""
    manifest = tmp_path / "weights.json"
    manifest.write_text(json.dumps({"schema": 1, "heads": {"h": {"sha256": "abc"}}}))
    from fractal_wallpapers.models import ship

    monkeypatch.setattr(ship, "manifest_path", lambda: manifest)
    return floors.Bar("h_release", 0.5, "h", "abc", "for a test")


def entry(identifier: str, partition: str, group: str, score: float) -> dict:
    return {"id": identifier, "partition": partition, "group": group, "score": score, "row": {}}


# --------------------------------------------------------------------------- #
# The gate at selection.
# --------------------------------------------------------------------------- #
def test_an_unfillable_slot_yields_a_shorter_release_and_never_a_below_bar_row(bar) -> None:
    """The release target is a cap, not a quota. Padding never returns."""
    pool = [entry(str(i), "mandelbrot", f"g{i}", 0.49 - i / 100) for i in range(5)]
    picked, log, fills = selection.select(pool, {"mandelbrot": 3}, bar=bar)
    assert picked == []
    assert {row["skipped"] for row in log} == {"below_bar"}
    assert fills["mandelbrot"]["planned"] == 3
    assert fills["mandelbrot"]["seated"] == 0
    assert fills["mandelbrot"]["unfilled"] == 3
    assert fills["mandelbrot"]["reason"] == "below_bar"


def test_the_slot_stops_at_the_last_passing_row_rather_than_reaching_below_the_bar(bar) -> None:
    pool = [
        entry("a", "mandelbrot", "g1", 0.99),
        entry("b", "mandelbrot", "g2", 0.60),
        entry("c", "mandelbrot", "g3", 0.4999),
        entry("d", "mandelbrot", "g4", 0.01),
    ]
    picked, _, fills = selection.select(pool, {"mandelbrot": 4}, bar=bar)
    assert [e["id"] for e in picked] == ["a", "b"]
    assert fills["mandelbrot"]["seated"] == 2
    assert fills["mandelbrot"]["unfilled"] == 2
    assert fills["mandelbrot"]["below_bar"] == 2


def test_the_bar_outranks_the_guarantee(bar) -> None:
    """A guaranteed partition with no passing supply ships nothing. The guarantee
    buys a slot and the right to spend it, not the right to spend it below the bar."""
    pool = [entry("a", "phoenix:classic", "g1", 0.2)]
    picked, log, fills = selection.select(
        pool,
        {"phoenix:classic": 1},
        caps={"phoenix:classic": 0},
        guarantees=["phoenix:classic"],
        bar=bar,
    )
    assert picked == []
    assert log[0]["skipped"] == "below_bar"
    assert fills["phoenix:classic"]["unfilled"] == 1


def test_a_seated_row_stamps_the_bar_that_acted(bar) -> None:
    """Value and artifact both: a seat is a claim nobody can restate once the head
    moves unless the height and the hash are on the row."""
    picked, log, _ = selection.select(
        [entry("a", "mandelbrot", "g1", 0.9)], {"mandelbrot": 1}, bar=bar
    )
    assert len(picked) == 1
    stamp = next(row for row in log if row["picked"])["bar"]
    assert stamp == {"name": "h_release", "value": 0.5, "head_sha256": "abc"}


def test_an_ungated_head_picks_exactly_as_it_did_before_any_head_gated(bar) -> None:
    """`bar=None` is no bar at all, not a bar at zero. The smooth path does not move
    because a decision was taken about the strange one."""
    pool = [entry(str(i), "mandelbrot", f"g{i}", 0.9 - i / 10) for i in range(6)]
    ungated, ungated_log, ungated_fills = selection.select(pool, {"mandelbrot": 6})
    assert [e["id"] for e in ungated] == ["0", "1", "2", "3", "4", "5"]
    assert all(row.get("bar") is None for row in ungated_log if row["picked"])
    assert ungated_fills["mandelbrot"]["unfilled"] == 0
    assert ungated_fills["mandelbrot"]["below_bar"] == 0

    # The same pool through the same call, with the bar the only difference: the
    # 0.4 row is the one and only thing that moves.
    gated, _, gated_fills = selection.select(pool, {"mandelbrot": 6}, bar=bar)
    assert [e["id"] for e in gated] == ["0", "1", "2", "3", "4"]
    assert gated_fills["mandelbrot"]["unfilled"] == 1


def test_an_unfilled_slot_records_the_binding_reason() -> None:
    """Every reason a slot goes unfilled has a sentence, and it is named on the row."""
    capped = {"one_look": floors.CLUSTER_CAP}
    pool = [entry("a", "mandelbrot", "one_look", 0.9)]
    _, _, fills = selection.select(pool, {"mandelbrot": 2}, used=capped)
    assert fills["mandelbrot"]["reason"] == "cluster_cap"
    assert fills["mandelbrot"]["why"] == selection.UNFILLED_REASONS["cluster_cap"]

    _, _, thin = selection.select(pool, {"mandelbrot": 2}, caps={"mandelbrot": 1})
    assert thin["mandelbrot"]["reason"] == "supply_cap"

    _, _, empty = selection.select([], {"mandelbrot": 2})
    assert empty["mandelbrot"]["reason"] == "no_candidates"


# --------------------------------------------------------------------------- #
# What the run reports, so a short release is attributable at a glance.
# --------------------------------------------------------------------------- #
def scored(attempt: int, head: str, score: float, centre: str) -> dict:
    return {
        "attempt": attempt,
        "head": head,
        "partition": "mandelbrot",
        "p_ge3": score,
        "family": {"kind": "mandelbrot"},
        "viewport": {"center_re": centre, "center_im": "0", "width": "0.4"},
    }


def test_the_run_reports_planned_against_seated_against_unfilled_per_head() -> None:
    """The strange head's slots go unfilled against real supply, and the summary
    says which partition and why rather than leaving it to look like thin supply."""
    from fractal_wallpapers.curation import budget
    from fractal_wallpapers.curation import run as run_module

    rows = [
        scored(0, budget.SMOOTH, 0.99, "-0.50"),
        scored(1, budget.SMOOTH, 0.98, "0.28"),
        scored(2, budget.STRANGE, 0.01, "-0.75"),
        scored(3, budget.STRANGE, 0.02, "0.10"),
    ]
    selected, _, split = run_module._select(
        rows, n=4, strange_share=0.5, caps={"mandelbrot": 99}, claims=[], log=lambda *_: None
    )
    assert [entry["row"]["head"] for entry in selected] == [budget.SMOOTH] * 2

    smooth, strange = split["fill"][budget.SMOOTH], split["fill"][budget.STRANGE]
    assert (smooth["planned"], smooth["seated"], smooth["unfilled"]) == (2, 2, 0)
    assert smooth["bar"] is None
    assert (strange["planned"], strange["seated"], strange["unfilled"]) == (2, 0, 2)
    assert strange["bar"]["value"] == floors.STRANGE_RELEASE_BAR.value
    assert strange["bar"]["acts"] is True
    assert strange["by_partition"]["mandelbrot"]["reason"] == "below_bar"
    assert split["below_bar_skips"] == 2
    assert split["short_by"] == 2


# --------------------------------------------------------------------------- #
# The retroactive rejection.
# --------------------------------------------------------------------------- #
def released(candidate: str, head: str, score: float, **extra) -> dict:
    row = records.decision(
        run="r",
        stage=records.RELEASE,
        candidate=candidate,
        verdict="released",
        row={"head": head, "p_ge3": score, "partition": "mandelbrot"},
        slot_source="mix",
    )
    row.update(extra)
    return row


def test_a_rejection_is_added_and_nothing_is_deleted(tmp_path) -> None:
    records.use(tmp_path)
    from fractal_wallpapers.curation import budget

    rows = [released("0000", budget.STRANGE, 0.0001), released("0001", budget.STRANGE, 0.99)]
    records.write_decisions(records.RELEASE, "r", rows)

    report = rejection.apply("r", rejector="matt_review", date="2026-08-17", log=lambda *_: None)
    assert report["newly_rejected"] == ["0000"]

    back = {row["candidate"]: row for row in records.read_decisions(records.RELEASE, "r")}
    taken = back["0000"]
    assert taken["verdict"] == "released"  # what the run decided, still true
    assert taken["scores"]["p_ge3"] == 0.0001  # untouched
    assert taken["rejected"]["rejector"] == "matt_review"
    assert taken["rejected"]["date"] == "2026-08-17"
    assert taken["rejected"]["reason"] == rejection.BELOW_ACTING_BAR
    assert taken["rejected"]["bar"]["value"] == floors.STRANGE_RELEASE_BAR.value
    assert back["0001"]["rejected"] is None


def test_a_rejected_row_is_out_of_every_served_view_and_still_in_the_records(tmp_path) -> None:
    records.use(tmp_path)
    from fractal_wallpapers.curation import budget

    records.write_decisions(
        records.RELEASE,
        "r",
        [released("0000", budget.STRANGE, 0.0001), released("0001", budget.STRANGE, 0.99)],
    )
    rejection.apply("r", rejector="matt_review", date="2026-08-17", log=lambda *_: None)

    rows = records.read_decisions(records.RELEASE, "r")
    assert len(rows) == 2
    assert [row["candidate"] for row in records.served(rows)] == ["0001"]

    from fractal_wallpapers.curation import checks

    assert [row["candidate"] for row in checks.released_rows("r")] == ["0001"]


def test_the_smooth_head_is_not_touched_by_the_strange_heads_bar(tmp_path) -> None:
    """Its below-advisory rows belong to a mix-ratio decision nobody has taken."""
    records.use(tmp_path)
    from fractal_wallpapers.curation import budget

    records.write_decisions(records.RELEASE, "r", [released("0000", budget.SMOOTH, 0.0084)])
    report = rejection.apply("r", rejector="matt_review", date="2026-08-17", log=lambda *_: None)
    assert report["newly_rejected"] == []
    assert records.read_decisions(records.RELEASE, "r")[0]["rejected"] is None


def test_rejecting_twice_writes_the_same_bytes(tmp_path) -> None:
    records.use(tmp_path)
    from fractal_wallpapers.curation import budget

    records.write_decisions(
        records.RELEASE,
        "r",
        [released("0000", budget.STRANGE, 0.0001), released("0001", budget.STRANGE, 0.99)],
    )
    rejection.apply("r", rejector="matt_review", date="2026-08-17", log=lambda *_: None)
    path = records.sinks("r")["release"]
    once = path.read_bytes()
    sheet_once = (rejection.run_module.run_dir("r") / "release_sheet_r.html").read_bytes()

    second = rejection.apply("r", rejector="matt_review", date="2026-08-17", log=lambda *_: None)
    assert second["newly_rejected"] == []
    assert path.read_bytes() == once
    assert (rejection.run_module.run_dir("r") / "release_sheet_r.html").read_bytes() == sheet_once


def test_a_re_record_does_not_un_reject_a_row_a_person_took_back(tmp_path) -> None:
    """The rejection was never one of the run's inputs, so a re-run would re-derive
    it as absent. It is carried forward instead."""
    records.use(tmp_path)
    from fractal_wallpapers.curation import budget

    records.write_decisions(records.RELEASE, "r", [released("0000", budget.STRANGE, 0.0001)])
    rejection.apply("r", rejector="matt_review", date="2026-08-17", log=lambda *_: None)

    records.write_decisions(records.RELEASE, "r", [released("0000", budget.STRANGE, 0.0001)])
    back = records.read_decisions(records.RELEASE, "r")[0]
    assert back["rejected"]["rejector"] == "matt_review"


def test_the_sheet_shows_a_rejected_row_under_its_own_heading(tmp_path) -> None:
    """Dropping it outright would make the page disagree with the record."""
    rows = [
        released(
            "0000",
            "strange_render",
            0.0001,
            rejected=records.rejection(
                rejector="matt_review",
                date="2026-08-17",
                reason=rejection.BELOW_ACTING_BAR,
                note="below the bar",
                bar={"name": "strange_render_release", "value": 0.5, "head_sha256": "79201d0c"},
            ),
        ),
        released("0001", "strange_render", 0.99),
    ]
    page = sheet.from_records("r", rows, {"requested": 2}, tmp_path, tmp_path / "s.html")
    text = page.read_text(encoding="utf-8")
    assert "Rejected after review (1)" in text
    assert "REJECTED by matt_review on 2026-08-17" in text
    assert text.index("<h2>Released</h2>") < text.index("Rejected after review")
    assert "1 released of 2" in text


def test_a_run_with_no_release_records_is_refused_rather_than_reported_as_clean(tmp_path) -> None:
    records.use(tmp_path)
    with pytest.raises(rejection.RejectionRefused):
        rejection.apply("nobody", rejector="matt_review", date="2026-08-17")
