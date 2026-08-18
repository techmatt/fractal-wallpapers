"""The palette head's score store: a tree of shards, and one reader over it."""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.models import palette_scoring, palette_train

#: How much of the 1 MiB history guard the largest shard may take. The guard is
#: the wall; this is the distance from it that makes splitting worth doing at all.
LARGEST_SHARE = 0.5

SEEDS = ("seed0_listwise", "seed0_regression", "seed1_listwise", "seed2_listwise")


@pytest.fixture
def head(tmp_path, monkeypatch):
    """A score store somewhere disposable, with the package pointed at it."""
    monkeypatch.setattr(palette_train, "head_dir", lambda run=None: tmp_path / (run or ""))
    return tmp_path


def a_row(set_id: str, batch: str, partition: str) -> dict:
    return {
        "schema": palette_scoring.SCHEMA,
        "head": "palette",
        "set": set_id,
        "source_batch": batch,
        "partition": partition,
        "candidates": ["viridis", "magma"],
        "score": [0.25, 0.75],
        "teacher_score": [0.3, 0.7],
        "agreed": True,
    }


def test_the_rows_go_to_a_file_per_batch_per_partition(head) -> None:
    rows = [
        a_row("b-0001", "batch_b", "julia:mandelbrot"),
        a_row("a-0002", "batch_a", "mandelbrot"),
        a_row("a-0001", "batch_a", "mandelbrot"),
    ]
    palette_scoring.write(rows, "best", "seed0")

    where = palette_scoring.scores_dir("seed0")
    assert {
        str(path.relative_to(where)).replace("\\", "/") for path in where.glob("*/*.jsonl")
    } == {
        "batch_a/mandelbrot.jsonl",
        "batch_b/julia_mandelbrot.jsonl",
    }, "`:` is not legal in a Windows path, so the corpus's own naming rule applies"

    # Each shard is in set order on its own, which is what the reader relies on.
    part = (where / "batch_a" / "mandelbrot.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["set"] for line in part] == ["a-0001", "a-0002"]


def test_the_unified_reader_is_the_whole_store_in_set_order(head) -> None:
    """The same list, in the same order, that the single accumulated file gave."""
    rows = [
        a_row("z-0001", "batch_a", "phoenix"),
        a_row("a-0001", "batch_b", "mandelbrot"),
        a_row("m-0001", "batch_a", "mandelbrot"),
    ]
    palette_scoring.write(rows, "best", "seed0")

    back = palette_scoring.read("seed0")
    assert [row["set"] for row in back] == ["a-0001", "m-0001", "z-0001"]
    assert all(row["checkpoint"] == "best" for row in back)


def test_a_re_score_rewrites_the_store_rather_than_adding_to_it(head) -> None:
    """A shard the new rows do not fill loses its file, and its batch loses its
    directory — otherwise a partition dropped from the corpus is still readable."""
    palette_scoring.write(
        [a_row("a-0001", "batch_a", "mandelbrot"), a_row("b-0001", "batch_b", "phoenix")],
        "best",
        "seed0",
    )
    palette_scoring.write([a_row("a-0001", "batch_a", "mandelbrot")], "best", "seed0")

    where = palette_scoring.scores_dir("seed0")
    assert [path.name for path in sorted(where.iterdir())] == ["batch_a"]
    assert [row["set"] for row in palette_scoring.read("seed0")] == ["a-0001"]


def test_a_re_written_store_is_byte_identical(head) -> None:
    rows = [a_row("a-0001", "batch_a", "mandelbrot"), a_row("b-0001", "batch_b", "phoenix")]
    palette_scoring.write(rows, "best", "seed0")
    where = palette_scoring.scores_dir("seed0")
    before = {path.name: path.read_bytes() for path in sorted(where.glob("*/*.jsonl"))}

    palette_scoring.write(list(reversed(rows)), "best", "seed0")
    assert {path.name: path.read_bytes() for path in sorted(where.glob("*/*.jsonl"))} == before


@pytest.mark.parametrize("seed", SEEDS)
def test_the_tracked_store_reads_back_whole_and_has_room_to_grow(seed: str) -> None:
    """The four seeds as they are committed. 999 KiB of accumulated file each, and
    47 KiB of headroom, is what the split was for."""
    from tests.test_history_purity import MAX_TRACKED_BYTES

    where = palette_scoring.scores_dir(seed)
    assert not where.with_suffix(".jsonl").exists(), "the pre-split file is gone, not shadowed"

    rows = palette_scoring.read(seed)
    assert len(rows) == 377
    assert [row["set"] for row in rows] == sorted(row["set"] for row in rows)

    shards = sorted(where.glob("*/*.jsonl"))
    assert len(shards) == 12
    largest = max(path.stat().st_size for path in shards)
    assert largest < LARGEST_SHARE * MAX_TRACKED_BYTES, (
        f"the largest shard is {largest} bytes against a {MAX_TRACKED_BYTES}-byte guard, "
        f"which is not room to grow"
    )
