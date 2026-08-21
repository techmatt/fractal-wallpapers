"""What a run record's clock can prove about who wrote it, and what it cannot.

The prose this pins used to say the inequality outright: `wall_seconds` at least
the sum of `history[*].seconds`, and far less than it means a second process. It
is not true of a resumed run — the clock starts after the snapshot loads and the
history is restored from it — and both trainers here resume, so the check had to
learn the difference between a relaunch and a concurrent writer rather than call
every relaunch a writer.
"""

from __future__ import annotations

import json

from fractal_wallpapers.models import audit
from fractal_wallpapers.paths import repo_root


def record(seconds: list[float], wall: float | None, **extra) -> dict:
    """A run record with nothing in it but the clock."""
    history = [{"epoch": index, "seconds": value} for index, value in enumerate(seconds)]
    return {"history": history, "wall_seconds": wall, **extra}


def test_a_wall_covering_every_epoch_is_one_segment() -> None:
    reading = audit.serial_time(record([10.0, 10.0, 10.0], 31.2))
    assert reading["reading"] == audit.SERIAL
    assert reading["covers"] == [0, 2]
    assert reading["uncovered_epochs"] == 0


def test_rounding_to_a_tenth_is_slop_and_not_evidence() -> None:
    """Every second in a record is rounded on the way in. A wall a few
    hundredths under the sum of its own epochs has not detected anything."""
    reading = audit.serial_time(record([10.1, 10.1, 10.1], 30.2))
    assert reading["reading"] == audit.SERIAL


def test_a_resumed_run_reads_as_resumed_rather_than_as_a_second_writer() -> None:
    """The whole point. Four epochs of history, a wall that covers the last two:
    a relaunch at epoch 2 produces exactly this and nothing is wrong with it."""
    reading = audit.serial_time(record([100.0, 100.0, 100.0, 100.0], 205.0))
    assert reading["reading"] == audit.RESUMED
    assert reading["covers"] == [2, 3]
    assert reading["uncovered_epochs"] == 2
    assert "a re-score can" in reading["says"]


def test_a_wall_too_short_for_even_the_last_epoch_is_the_one_proof_there_is() -> None:
    """No resume explains a wall the final epoch does not fit inside: two epochs
    ran at once."""
    reading = audit.serial_time(record([100.0, 100.0], 40.0))
    assert reading["reading"] == audit.OVERLAPPED
    assert reading["covers"] is None


def test_a_record_with_no_clock_says_so_instead_of_passing() -> None:
    reading = audit.serial_time(record([10.0, 10.0], None))
    assert reading["reading"] == audit.UNRECORDED
    assert reading["wall_seconds"] is None


def test_segments_turn_the_weak_reading_into_the_strict_one() -> None:
    """A record that says where its launches were is checked exactly: the same
    history and wall that could only read RESUMED reads SERIAL once the earlier
    segment is on the record."""
    said = record(
        [100.0, 100.0, 100.0, 100.0],
        205.0,
        segments=[
            {"from_epoch": 0, "through_epoch": 1, "wall_seconds": 203.0},
            {"from_epoch": 2, "through_epoch": 3, "wall_seconds": 205.0},
        ],
    )
    reading = audit.serial_time(said)
    assert reading["reading"] == audit.SERIAL
    assert reading["segments_recorded"] is True
    assert reading["uncovered_epochs"] == 0


def test_a_segment_that_cannot_hold_its_own_epochs_is_caught() -> None:
    """Two trainers in one directory take turns, so one launch's wall ends up
    under the epochs attributed to it. That is the failure the segments exist to
    make visible."""
    said = record(
        [100.0, 100.0, 100.0, 100.0],
        205.0,
        segments=[
            {"from_epoch": 0, "through_epoch": 1, "wall_seconds": 90.0},
            {"from_epoch": 2, "through_epoch": 3, "wall_seconds": 205.0},
        ],
    )
    reading = audit.serial_time(said)
    assert reading["reading"] == audit.OVERLAPPED
    assert "epochs 0-1" in reading["says"]


def test_segments_that_do_not_cover_the_history_are_caught() -> None:
    said = record(
        [100.0, 100.0, 100.0],
        105.0,
        segments=[{"from_epoch": 1, "through_epoch": 2, "wall_seconds": 205.0}],
    )
    reading = audit.serial_time(said)
    assert reading["reading"] == audit.OVERLAPPED
    assert "cover 2 of 3 epochs" in reading["says"]
    assert reading["uncovered_epochs"] == 1


def test_no_tracked_run_record_reads_as_a_second_writer() -> None:
    """Every `metrics.json` this repository ships, read the corrected way. Two of
    them have a wall shorter than their own history and both are relaunches —
    RESUMED is the honest reading of those, and OVERLAPPED is what would mean a
    record nobody can attribute."""
    found = sorted(repo_root().glob("models/*/**/metrics.json"))
    assert found, "no tracked run records to read"
    overlapped = {}
    for path in found:
        said = json.loads(path.read_text(encoding="utf-8"))
        reading = audit.serial_time(said)
        if reading["reading"] == audit.OVERLAPPED:
            overlapped[str(path.relative_to(repo_root()))] = reading["says"]
    assert not overlapped, f"run records that two processes wrote: {overlapped}"
