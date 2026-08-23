"""The two phases: a run accumulates and keeps a diagnostic, the collection ships.

Matt's ruling of 2026-08-22 split curation in half. A `curate run` is the pool
phase — it makes candidates, records every one of them, and keeps ten pictures to
look at — and what the collection serves is decided later, globally, over the
whole accumulated pool. Three things follow, and each is a decision rather than a
tuning: a run stops reading the served index, every release row says which
collection it is in, and a run's release is ten.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers.curation import budget, floors, records, selection
from fractal_wallpapers.curation import run as run_module

HERE = {"kind": "mandelbrot"}
FRAME = {"center_re": "-0.5", "center_im": "0", "width": "0.4"}
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


# --------------------------------------------------------------------------- #
# A run never refuses a place because an earlier run released it.
# --------------------------------------------------------------------------- #
def test_a_run_does_not_read_the_collection_and_cannot_be_handed_it() -> None:
    """The deletion, stated as a signature. `_select` took a served index and
    threaded it into the selection; a run that did that let whichever run went
    first cast a veto on the next run's coverage, out of the fraction of the pool
    it happened to hold."""
    import inspect

    taken = inspect.signature(run_module._select).parameters
    assert "served" not in taken
    assert list(taken) == ["scored", "n", "strange_share", "caps", "claims", "log"]


def test_the_same_place_seats_in_two_runs_now(tmp_path) -> None:
    """The behaviour the deletion buys: a run's seats are its own, and a location
    the collection already holds is offered again rather than refused."""
    records.use(tmp_path)
    try:
        rows = [attempt(0, budget.SMOOTH, 0.99, FRAME)]
        first, _, _, _ = run_module._select(
            rows, n=1, strange_share=0.0, caps={"mandelbrot": 99}, claims=[], log=lambda *_: None
        )
        records.write_decisions(
            records.RELEASE,
            "earlier",
            [
                records.decision(
                    run="earlier",
                    stage=records.RELEASE,
                    candidate="0000",
                    verdict=records.RELEASED,
                    row={**rows[0], "key": "k"},
                    collection=records.DIAGNOSTIC,
                    picture="release/0000.png",
                )
            ],
        )
        again, _, split, _ = run_module._select(
            rows, n=1, strange_share=0.0, caps={"mandelbrot": 99}, claims=[], log=lambda *_: None
        )
        assert len(first) == len(again) == 1
        assert split["location_served_skips"] == 0
    finally:
        records.use(None)


def test_one_wallpaper_per_location_still_acts_inside_the_run() -> None:
    """The rule did not go away — its scope did. Two heads bidding for one place
    still seat once between them, and the higher-ranked one keeps it."""
    rows = [
        attempt(0, budget.SMOOTH, 0.99, FRAME),
        attempt(1, budget.STRANGE, 0.99, FRAME),
        attempt(2, budget.SMOOTH, 0.98, ELSEWHERE),
    ]
    selected, _, split, _ = run_module._select(
        rows, n=4, strange_share=0.5, caps={"mandelbrot": 99}, claims=[], log=lambda *_: None
    )
    seated = {entry["row"]["attempt"] for entry in selected}
    assert 1 not in seated, "the strange row is a second wallpaper of the same place"
    assert split["location_served_skips"] == 1
    assert split["location_served_by_cause"] == {"prior_run": 0, "this_run": 1}
    assert floors.CLUSTER_CAP == 1


def test_the_selection_still_takes_a_served_index_for_the_pass_that_has_one() -> None:
    """The argument stays on `select`: the gallery pass over the pool is exactly
    the caller with the population to decide coverage with."""
    pool = selection.entries([attempt(0, budget.SMOOTH, 0.99, FRAME)])
    picked, _, fills = selection.select(pool, {"mandelbrot": 1}, served={pool[0]["group"]})
    assert picked == []
    assert fills["mandelbrot"]["reason"] == selection.LOCATION_SERVED


# --------------------------------------------------------------------------- #
# Which collection, beside whether there is a picture.
# --------------------------------------------------------------------------- #
def test_a_release_row_carries_a_collection_and_a_gate_row_does_not() -> None:
    """A gate decision is about whether a candidate is worth scoring. Nothing
    about it is in a collection, and defaulting it would invent one."""
    at_the_gate = records.decision(
        run="r", stage=records.GATE, candidate="0000", verdict="kept", row={}
    )
    assert at_the_gate["collection"] is None

    released = records.decision(
        run="r",
        stage=records.RELEASE,
        candidate="0000",
        verdict=records.RELEASED,
        row={},
        collection=records.DIAGNOSTIC,
    )
    assert released["collection"] == records.DIAGNOSTIC


def test_the_collection_is_not_a_verdict_and_never_became_one() -> None:
    """The verdicts answer *is there a wallpaper at the end of this row*; the
    collection answers *which collection was this decided for*. Two questions, two
    fields — a collection spelled as a verdict would have made the first
    unanswerable without knowing which collection the reader meant.

    `unrendered` joined the verdicts on 2026-08-22 and is the same question's
    fourth answer — took the slot, no picture, nothing failed — not a collection
    wearing a verdict's clothes."""
    assert records.COLLECTIONS == ("diagnostic", "gallery")
    assert set(records.COLLECTIONS).isdisjoint(
        {records.RELEASED, records.KILLED, records.UNRENDERED, records.PASSED_OVER}
    )


def test_the_word_gallery_is_curations_and_the_deep_run_names_its_frames() -> None:
    """The collision the rename settled: `gallery` cannot mean the collection a
    picture is in here and the evaluation frames a deep walk books there."""
    from fractal_wallpapers.deep import budget as deep_budget

    costs = deep_budget.Costs()
    assert costs.evaluation_frames_per_admission > 0
    assert costs.evaluation_per_seat > 0
    assert not any("gallery" in name for name in dir(costs))
    assert records.GALLERY == "gallery"


def test_every_release_row_on_record_says_which_collection_it_is_in() -> None:
    """Against the tracked store: every row names a collection and it is one of the
    two. `None` is what a row written before the field existed carries, and the
    backfill left none of those."""
    rows = records.read_decisions(records.RELEASE)
    kinds = {row.get("collection") for row in rows}
    assert kinds <= set(records.COLLECTIONS), f"{len(rows)} rows carry {kinds}"
    assert None not in kinds
    # Only the gallery pass writes the second one, and it writes it on every row.
    galleries = {row["run"] for row in rows if row["collection"] == records.GALLERY}
    diagnostics = {row["run"] for row in rows if row["collection"] == records.DIAGNOSTIC}
    assert not (galleries & diagnostics)


# --------------------------------------------------------------------------- #
# A run's release is a diagnostic.
# --------------------------------------------------------------------------- #
def test_a_run_stamps_diagnostic_on_the_rows_it_writes(tmp_path, monkeypatch) -> None:
    """Written by the run itself rather than by a later pass, because it is the
    run that knows its pictures were the best of its own attempts."""
    records.use(tmp_path)
    try:
        rows = [attempt(0, budget.SMOOTH, 0.99, FRAME)]
        selected, log_rows, split, group_of = run_module._select(
            rows, n=1, strange_share=0.0, caps={"mandelbrot": 99}, claims=[], log=lambda *_: None
        )
        identifier = f"{rows[0]['attempt']:04d}"
        written = records.decision(
            run="r",
            stage=records.RELEASE,
            candidate=identifier,
            verdict=records.PASSED_OVER,
            row=rows[0],
            collection=records.DIAGNOSTIC,
            group=group_of.get(identifier),
        )
        records.write_decisions(records.RELEASE, "r", [written])
        back = records.read_decisions(records.RELEASE, "r")
        assert [row["collection"] for row in back] == [records.DIAGNOSTIC]
        assert len(selected) == 1 and len(log_rows) == 1 and split["short_by"] == 0
    finally:
        records.use(None)


@pytest.mark.parametrize(
    ("share", "expected"),
    [(0.6, {budget.SMOOTH: 4, budget.STRANGE: 6}), (0.5, {budget.SMOOTH: 5, budget.STRANGE: 5})],
)
def test_ten_slots_split_six_four_towards_the_judge_with_a_roster(share, expected) -> None:
    """Six tenths, on Matt's call: the strange judge has seventeen production
    modes to draw from and an acting bar to get past, and the smooth judge has one
    coloring and an advisory."""
    assert budget.head_slots(run_module.DEFAULT_N, share) == expected


def test_the_mode_table_is_a_parameter_and_a_run_records_the_one_it_used() -> None:
    """It was a constant, which made a reservation computed from a copy of it
    correct only by luck. A run that draws a third strange mode plans a third."""
    assert budget.modes_of(None) == budget.MODES_PER_LOCATION
    wider = budget.modes_of({budget.STRANGE: 3})
    assert wider == {budget.SMOOTH: 1, budget.STRANGE: 3}

    slots = budget.head_slots(10, 0.6)
    default, record = budget.head_attempts(slots, None)
    more, wider_record = budget.head_attempts(slots, None, modes=wider)
    assert more[budget.STRANGE] > default[budget.STRANGE]
    assert more[budget.SMOOTH] == default[budget.SMOOTH], "the smooth roster is one mode"
    assert wider_record["modes_per_location"] == wider
    assert record["modes_per_location"] == dict(budget.MODES_PER_LOCATION)

    # The banner reports the table in force, not the module's default.
    assert floors.summary(wider)["caps"]["modes_per_location"] == wider


def test_the_smooth_judge_may_not_be_asked_for_a_second_mode() -> None:
    """Its roster IS one coloring, so a second draw renders the same picture. Not
    a policy — a fact about the engine — so it refuses rather than being a knob."""
    with pytest.raises(ValueError, match="one coloring"):
        budget.modes_of({budget.SMOOTH: 2})


def test_a_runs_shape_carries_the_mode_table_so_a_resume_cannot_re_plan_it() -> None:
    """The same rule the strange share is under: a resumed run takes the table it
    was planned with, not whatever the module says today."""
    assert "modes" in run_module.SHAPE
    assert "strange_share" in run_module.SHAPE
