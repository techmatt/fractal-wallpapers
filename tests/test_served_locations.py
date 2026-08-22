"""One wallpaper per location, collection-wide, and the ruling that keeps a row.

Two rules with the same shape and opposite directions, both settled by Matt on a
sheet rather than by a measurement: a location the collection has already
released is refused a second seat, and four named run8h rows below the acting
strange bar stay in service. Each is pinned because each is a *decision*, and a
decision nothing tests is a decision the next refactor reverses silently.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.curation import (
    floors,
    records,
    rejection,
    selection,
    served_locations,
)

HERE = {"kind": "mandelbrot"}
FRAME = {"center_re": "-0.5", "center_im": "0", "width": "0.4"}
#: Far enough away on the same plane to be a different group under every clause
#: of the neighbour rule.
ELSEWHERE = {"center_re": "0.28", "center_im": "0.01", "width": "0.001"}


def attempt(number: int, head: str, score: float, viewport: dict) -> dict:
    return {
        "attempt": number,
        "head": head,
        "partition": "mandelbrot",
        "p_ge3": score,
        "family": HERE,
        "viewport": viewport,
    }


def served_row(candidate: str, viewport: dict, run: str = "earlier") -> dict:
    return records.decision(
        run=run,
        stage=records.RELEASE,
        candidate=candidate,
        verdict=records.RELEASED,
        row={
            "key": f"{run}-{candidate}",
            "partition": "mandelbrot",
            "family": HERE,
            "viewport": viewport,
            "head": "smooth_render",
            "p_ge3": 0.99,
        },
        picture=f"{candidate}.png",
    )


# --------------------------------------------------------------------------- #
# The index.
# --------------------------------------------------------------------------- #
def test_the_index_reads_the_tracked_store_and_not_this_process_s_root(tmp_path) -> None:
    """`--ephemeral` redirects everything a rehearsal writes. The collection is not
    a thing a rehearsal owns, and an index that read its own empty root would seat
    places the collection already has."""
    records.use(tmp_path)
    try:
        records.write_decisions(records.RELEASE, "rehearsal", [served_row("0000", FRAME)])
        assert served_locations.build().summary()["by_run"].keys() >= {"run9"}
        assert "rehearsal" not in served_locations.build().summary()["by_run"]
    finally:
        records.use(None)


def test_the_index_is_the_served_set_and_a_rejected_row_frees_its_place(tmp_path) -> None:
    """Rejecting a row is how a place is given back, so the index has to read the
    served set and not the raw verdict."""
    records.use(tmp_path)
    try:
        kept = served_row("0000", FRAME)
        taken_back = {
            **served_row("0001", ELSEWHERE),
            "rejected": records.rejection(
                rejector="Matt", date="2026-08-22", reason="a test", note="a test", bar=None
            ),
        }
        records.write_decisions(records.RELEASE, "earlier", [kept, taken_back])
        index = served_locations.build(under=tmp_path)
        assert len(index) == 1
        assert index.summary() == {"served_rows": 1, "by_run": {"earlier": 1}}
    finally:
        records.use(None)


def test_a_resume_is_not_blocked_by_the_wallpapers_it_already_released(tmp_path) -> None:
    """A run continuing itself would otherwise refuse every seat its first half
    took, and re-plan itself into an empty release."""
    records.use(tmp_path)
    try:
        records.write_decisions(records.RELEASE, "mine", [served_row("0000", FRAME, run="mine")])
        assert len(served_locations.build(under=tmp_path)) == 1
        assert len(served_locations.build(exclude_run="mine", under=tmp_path)) == 0
    finally:
        records.use(None)


def test_repeats_names_every_place_the_collection_holds_twice(tmp_path) -> None:
    records.use(tmp_path)
    try:
        records.write_decisions(
            records.RELEASE,
            "earlier",
            [served_row("0000", FRAME), served_row("0001", FRAME), served_row("0002", ELSEWHERE)],
        )
        found = served_locations.repeats(under=tmp_path)
        assert len(found) == 1
        assert [row["candidate"] for row in found[0]["served"]] == ["0000", "0001"]
        assert found[0]["runs"] == ["earlier"]
    finally:
        records.use(None)


# --------------------------------------------------------------------------- #
# The rule at selection. Cross-run, same-run cross-head, and who keeps the seat.
# --------------------------------------------------------------------------- #
def test_a_place_an_earlier_run_served_takes_no_second_seat() -> None:
    rows = [attempt(0, "smooth_render", 0.99, FRAME)]
    entries, already = selection.grouped(
        {"smooth_render": rows}, [{"family": HERE, "viewport": FRAME}]
    )
    picked, log, fills = selection.select(
        entries["smooth_render"], {"mandelbrot": 1}, served=already
    )
    assert picked == []
    assert log[0]["skipped"] == selection.LOCATION_SERVED
    assert log[0]["cause"] == "prior_run"
    assert fills["mandelbrot"]["reason"] == selection.LOCATION_SERVED


def test_the_two_heads_share_one_seat_for_one_place() -> None:
    """Both heads attempt every location. The second seat is now always refused,
    and the counter that refuses it spans both passes."""
    by_head = {
        "smooth_render": [attempt(0, "smooth_render", 0.99, FRAME)],
        "strange_render": [attempt(1, "strange_render", 0.98, FRAME)],
    }
    entries, already = selection.grouped(by_head)
    assert already == set()
    used: dict = {}
    first, _, _ = selection.select(entries["smooth_render"], {"mandelbrot": 1}, used=used)
    second, log, _ = selection.select(entries["strange_render"], {"mandelbrot": 1}, used=used)
    assert len(first) == 1
    assert second == []
    assert log[0]["skipped"] == selection.LOCATION_SERVED
    assert log[0]["cause"] == "this_run"


def test_the_higher_ranked_candidate_keeps_the_place() -> None:
    rows = [
        attempt(0, "smooth_render", 0.40, FRAME),
        attempt(1, "smooth_render", 0.95, FRAME),
    ]
    entries, _ = selection.grouped({"smooth_render": rows})
    picked, log, _ = selection.select(entries["smooth_render"], {"mandelbrot": 2})
    assert [entry["id"] for entry in picked] == ["0001"]
    assert next(row for row in log if row["id"] == "0000")["skipped"] == selection.LOCATION_SERVED


def test_the_cap_is_one_and_the_rule_is_read_off_it() -> None:
    assert floors.CLUSTER_CAP == 1


# --------------------------------------------------------------------------- #
# The other direction: a ruling that keeps a row in service.
# --------------------------------------------------------------------------- #
def test_the_tracked_ruling_holds_the_four_run8h_rows_in_service() -> None:
    """The rule is live and idempotent, so it would find these four every time it
    was asked. The ruling is what stops it, and it names them one by one."""
    excused = rejection.exceptions()
    assert set(excused) == {
        "run8h|release|0008",
        "run8h|release|0017",
        "run8h|release|0029",
        "run8h|release|0072",
    }
    for key, ruling in excused.items():
        assert ruling["run"] == "run8h"
        assert ruling["head"] == "strange_render"
        assert ruling["p_ge3"] < floors.STRANGE_RELEASE_BAR.value
        assert ruling["ruled_by"] and ruling["date"] and ruling["reason"]
        assert key.endswith(ruling["candidate"])

    rows = records.read_decisions(records.RELEASE, "run8h")
    assert [row["candidate"] for row, _ in rejection.below_acting_bar(rows)] == []


def test_an_unexcused_row_below_the_bar_is_still_taken_back(tmp_path) -> None:
    """The exception is per row. A row nothing names is refused exactly as before,
    which is what stops the list becoming the bar's retirement."""
    records.use(tmp_path)
    try:
        row = records.decision(
            run="whenever",
            stage=records.RELEASE,
            candidate="0000",
            verdict=records.RELEASED,
            row={
                "key": "k",
                "partition": "mandelbrot",
                "family": HERE,
                "viewport": FRAME,
                "head": "strange_render",
                "p_ge3": floors.STRANGE_RELEASE_BAR.value - 0.1,
            },
            picture="0000.png",
        )
        assert [r["candidate"] for r, _ in rejection.below_acting_bar([row])] == ["0000"]
    finally:
        records.use(None)


def test_every_ruling_names_a_release_row_that_exists() -> None:
    """A ruling whose key matches nothing is either a typo or a run that was
    renamed under it, and both read as 'the exception is being honoured'."""
    keys = {str(row["key"]) for row in records.read_decisions(records.RELEASE)}
    assert set(rejection.exceptions()) <= keys


def test_the_ruling_file_is_jsonl_carrying_a_schema_from_its_first_row() -> None:
    rows = [
        json.loads(line)
        for line in rejection.exceptions_path().read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert rows
    assert all(row["schema"] == 1 for row in rows)


@pytest.mark.parametrize("reason", sorted(selection.UNFILLED_REASONS))
def test_every_unfilled_reason_has_a_sentence(reason: str) -> None:
    assert selection.UNFILLED_REASONS[reason]
