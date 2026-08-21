"""The boundary draw: seeded, recorded, and screened by the walk's own gates.

The claim this generator exists to support is a claim about *rarity*, so the two
things that must hold are that the draw is reproducible from its number and that
every attempt is on the record — a draw that kept only its keepers could not
afterwards say how many it made.
"""

from __future__ import annotations

import json
import random

import pytest

from fractal_wallpapers import engine, locations
from fractal_wallpapers.discovery import boundary


def engine_is_built() -> bool:
    try:
        engine.engine_path()
    except FileNotFoundError:
        return False
    return True


needs_engine = pytest.mark.skipif(
    not engine_is_built(),
    reason="the engine is not built: cargo build --release --manifest-path engine/Cargo.toml",
)

BOX = (-0.77, 0.0, 1.98, 1.11375)


def test_the_same_number_draws_the_same_frames() -> None:
    """Every random draw in this project is seeded and the seed is recorded. A
    sampler that could not be re-run is a record of a draw, which is the thing
    this replaces."""
    one = boundary.draws(random.Random(7), 5, BOX, (1e-3, 1e-1), 0)
    two = boundary.draws(random.Random(7), 5, BOX, (1e-3, 1e-1), 0)
    assert one == two
    assert one != boundary.draws(random.Random(8), 5, BOX, (1e-3, 1e-1), 0)


def test_a_draw_stays_inside_the_box_and_the_band() -> None:
    rows = boundary.draws(random.Random(3), 200, BOX, (1e-3, 1e-1), 0)
    centre_re, centre_im, half_width, half_height = BOX
    for row in rows:
        assert abs(float(row["center_re"]) - centre_re) <= half_width
        assert abs(float(row["center_im"]) - centre_im) <= half_height
        assert 1e-3 <= float(row["width"]) <= 1e-1
    assert [row["index"] for row in rows] == list(range(200))


def test_the_index_continues_across_batches() -> None:
    """Attempts are screened in batches, and the record is one file: an index
    that restarted per batch would make two attempts share a number."""
    rows = boundary.draws(random.Random(3), 4, BOX, (1e-3, 1e-1), 64)
    assert [row["index"] for row in rows] == [64, 65, 66, 67]


def test_a_draw_that_keeps_nothing_or_tries_nothing_is_refused(tmp_path) -> None:
    for kwargs in ({"keep": 0}, {"attempts": 0}, {"band": (1.0, 0.5)}):
        with pytest.raises(boundary.BoundaryError):
            boundary.sample({"kind": "mandelbrot"}, out_dir=tmp_path, **kwargs)


@needs_engine
def test_every_attempt_is_on_the_record_and_the_keepers_are_a_manifest(tmp_path) -> None:
    """Record and rank, never gate and forget — the same rule the ledger holds.
    The yield *is* the measurement here, so a file holding only survivors would
    have thrown away the number the figure is about."""
    report = boundary.sample(
        {"kind": "mandelbrot"},
        seed=1,
        keep=2,
        attempts=boundary.BATCH,
        out_dir=tmp_path,
        images=False,
        log=lambda _message: None,
    )
    rows = [
        json.loads(line)
        for line in (tmp_path / "draws.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    header, *middle = rows
    summary = middle.pop()
    assert header["kind"] == "run"
    assert header["seed"] == 1
    # The geometry the verdicts were read at comes from the engine that read
    # them, not from a constant on this side.
    assert header["tile"] == [384, 216]
    assert header["field_supersample"] == 1
    assert summary["kind"] == "summary"
    assert summary["attempts"] == len(middle)
    assert sum(summary["fates"].values()) == summary["attempts"]
    assert summary["pass_rate"] == summary["survived"] / summary["attempts"]

    for row in middle:
        assert row["kind"] == "draw"
        assert row["kept"] == (row["fate"] == "survived")
        assert row["verdicts"], "a gate ran and said something"

    # The manifest is a plain list of locations and nothing else, so it feeds
    # straight into anything that reads them.
    kept = locations.read(tmp_path / "kept.jsonl")
    assert len(kept) == summary["kept"]
    assert all(row["family"] == {"kind": "mandelbrot"} for row in kept)
    assert report["record"].endswith("draws.jsonl")


@needs_engine
def test_a_kept_frame_really_did_clear_every_gate(tmp_path) -> None:
    """The survivors are the boundary claim: a frame that is not mostly set, not
    far exterior and has detail spread over it is straddling the boundary. If a
    kept row could carry a failed verdict the claim would be empty."""
    boundary.sample(
        {"kind": "mandelbrot"},
        seed=4,
        keep=3,
        attempts=boundary.BATCH * 3,
        out_dir=tmp_path,
        images=False,
        log=lambda _message: None,
    )
    for line in (tmp_path / "draws.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("kind") != "draw" or not row["kept"]:
            continue
        assert all(verdict["passed"] for verdict in row["verdicts"])
        assert row["interior_fraction"] < 0.30
        assert row["occupancy"] >= 0.321
