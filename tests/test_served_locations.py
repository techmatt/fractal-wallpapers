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
# The rule applied backwards: retiring what the collection already held twice.
# --------------------------------------------------------------------------- #
def scored_row(candidate: str, viewport: dict, run: str, score: float, head: str) -> dict:
    row = served_row(candidate, viewport, run=run)
    return {**row, "scores": {**row["scores"], "head": head, "p_ge3": score}}


def a_run_finished(run: str, when: str) -> None:
    """A run record carrying nothing but the stamp the run order is read off."""
    path = records.sinks(run)["run_record"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"schema": 1, "run": run, "finished": when}), encoding="utf-8", newline="\n"
    )


def test_retiring_leaves_one_wallpaper_per_location_and_keeps_the_best_reading(tmp_path) -> None:
    records.use(tmp_path)
    try:
        records.write_decisions(
            records.RELEASE,
            "earlier",
            [
                scored_row("0000", FRAME, "earlier", 0.62, "strange_render"),
                scored_row("0001", FRAME, "earlier", 0.94, "smooth_render"),
                scored_row("0002", ELSEWHERE, "earlier", 0.71, "smooth_render"),
            ],
        )
        report = rejection.retire_repeats(rejector="Matt", date="2026-08-22", log=lambda _: None)

        assert report["retired"] == ["earlier|release|0000"]
        assert report["served_before"] == 3
        assert report["served_after"] == 2
        assert report["groups_remaining"] == 0
        assert served_locations.repeats(under=tmp_path) == []

        rows = {row["key"]: row for row in records.read_decisions(records.RELEASE, "earlier")}
        taken = rows["earlier|release|0000"]["rejected"]
        assert taken["reason"] == selection.LOCATION_SERVED
        assert taken["survivor"] == "earlier|release|0001"
        assert taken["bar"] is None
        # The run's own verdict is what the run decided, and it stays true.
        assert taken["rejector"] == "Matt" and taken["date"] == "2026-08-22"
        assert rows["earlier|release|0000"]["verdict"] == records.RELEASED
        assert rows["earlier|release|0000"]["scores"]["p_ge3"] == 0.62
        assert rows["earlier|release|0001"]["rejected"] is None
    finally:
        records.use(None)


def test_a_tie_on_the_score_goes_to_the_later_run(tmp_path) -> None:
    """Two saturated readings of one place is the one comparison the score cannot
    settle, and the collection has exactly one of them."""
    records.use(tmp_path)
    try:
        a_run_finished("earlier", "2026-08-01T00:00:00")
        a_run_finished("later", "2026-08-20T00:00:00")
        records.write_decisions(
            records.RELEASE, "earlier", [scored_row("0000", FRAME, "earlier", 1.0, "smooth_render")]
        )
        records.write_decisions(
            records.RELEASE, "later", [scored_row("0000", FRAME, "later", 1.0, "smooth_render")]
        )
        report = rejection.retire_repeats(rejector="Matt", date="2026-08-22", log=lambda _: None)
        assert report["retired"] == ["earlier|release|0000"]
        assert report["groups"][0]["survivor"]["key"] == "later|release|0000"
    finally:
        records.use(None)


def test_a_dry_run_names_the_same_rows_and_writes_nothing(tmp_path) -> None:
    records.use(tmp_path)
    try:
        rows = [
            scored_row("0000", FRAME, "earlier", 0.62, "strange_render"),
            scored_row("0001", FRAME, "earlier", 0.94, "smooth_render"),
        ]
        records.write_decisions(records.RELEASE, "earlier", rows)
        where = records.decisions_path(records.RELEASE, "earlier", "mandelbrot")
        before = where.read_bytes()

        report = rejection.retire_repeats(
            rejector="Matt", date="2026-08-22", dry_run=True, log=lambda _: None
        )
        assert report["retired"] == ["earlier|release|0000"]
        assert report["groups_remaining"] is None
        assert report["records"] == {}
        assert where.read_bytes() == before
    finally:
        records.use(None)


def test_a_second_pass_has_nothing_to_do(tmp_path) -> None:
    """Not by re-deriving the same answer: a retired row leaves the served set, so
    the group the second pass reads is holding one wallpaper."""
    records.use(tmp_path)
    try:
        records.write_decisions(
            records.RELEASE,
            "earlier",
            [
                scored_row("0000", FRAME, "earlier", 0.62, "strange_render"),
                scored_row("0001", FRAME, "earlier", 0.94, "smooth_render"),
            ],
        )
        rejection.retire_repeats(rejector="Matt", date="2026-08-22", log=lambda _: None)
        where = records.decisions_path(records.RELEASE, "earlier", "mandelbrot")
        settled = where.read_bytes()

        again = rejection.retire_repeats(
            rejector="Somebody else", date="2027-01-01", log=lambda _: None
        )
        assert again["retired"] == []
        assert again["groups"] == []
        assert where.read_bytes() == settled
    finally:
        records.use(None)


def test_each_collection_holds_one_wallpaper_per_location() -> None:
    """The tracked store, after the retirement. This is the rule's whole claim, and
    the only place it can be checked is against the collection itself.

    **Per collection**, which is where the rule acts. The runs' diagnostic pictures
    and the gallery pass's are two sets of places, and a pass that refused every
    place a run's diagnostic release happens to sit on would hand the collection's
    best locations to the ten pictures a night kept to prove its path worked. So a
    group holding one of each is two collections agreeing about a location, and the
    unscoped read is expected to find those."""
    for collection in records.COLLECTIONS:
        assert served_locations.repeats(collection=collection) == [], collection


def test_every_location_served_rejection_names_a_survivor_that_is_still_served() -> None:
    """A retirement is a comparison between two rows, and one pointing at a row
    that is itself no longer served would have retired both pictures of a place."""
    rows = records.read_decisions(records.RELEASE)
    served = {str(row["key"]) for row in records.served(rows)}
    retired = [
        row
        for row in rows
        if (row.get("rejected") or {}).get("reason") == selection.LOCATION_SERVED
    ]
    assert retired
    for row in retired:
        survivor = row["rejected"]["survivor"]
        assert survivor in served
        assert survivor != row["key"]


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
        # Against the bar the RULING was written against, not today's. Both the
        # score and the bar on this row are frozen provenance on the retired
        # judge's scale; the standing height is a point on the live judge's, and
        # comparing the two is the scale error the ruling itself is evidence of.
        assert ruling["p_ge3"] < ruling["bar"]["value"]
        assert ruling["bar"]["head_sha256"] != floors.STRANGE_RELEASE_BAR.head_sha256
        assert ruling["ruled_by"] and ruling["date"] and ruling["reason"]
        assert key.endswith(ruling["candidate"])

    # The exception is keyed on the ROW, so it holds whatever the live scale says
    # about these four today — the property that makes a ruling survive a head
    # flip instead of quietly expiring with one. None of the four is ever offered
    # back to the rejection pass.
    rows = records.read_decisions(records.RELEASE, "run8h")
    offered = {row["candidate"] for row, _ in rejection.below_acting_bar(rows)}
    assert not offered & {ruling["candidate"] for ruling in excused.values()}

    # What the rule finds BESIDES them is not this ruling's business and is not
    # asserted to be empty. The 2026-08-23 head flip moved the whole scale, and
    # rows this run released above the retired judge's bar can sit below the live
    # one — `run8h|0032` reads 0.9999946 retired and 0.4987 on the render judge.
    # Taking those back is a curation pass somebody runs, not a fact about the
    # four rows Matt ruled on.


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
