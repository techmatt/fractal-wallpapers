"""The label store: the join on every row, append-only writes, one reader.

Three properties are load-bearing and each is here because losing it is silent.
A row without its join is a verdict about a picture nobody can find again. A
revision written in place destroys the thing it revises. And a second reader is a
second answer to "what does this corpus say", which is the failure that only
shows up in the one number somebody was about to publish.
"""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path

import pytest

from fractal_wallpapers.labeling import store

JULIA = {"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]}
OTHER_JULIA = {"kind": "julia", "degree": 2, "c": ["-0.4", "0.61"]}
VIEW = {"center_re": "0.1", "center_im": "0.2", "width": "0.5"}


def row(score=3, family=None, viewport=None, batch="a_batch", **extra) -> dict:
    return store.label_row(
        batch=batch,
        score=score,
        family=family or JULIA,
        viewport=viewport or VIEW,
        labeler="matt",
        **extra,
    )


def test_a_row_carries_its_whole_join() -> None:
    written = row()
    assert written["family"] == JULIA
    assert written["viewport"] == VIEW
    assert written["score"] == 3


def test_a_row_without_a_location_is_refused_at_the_writer() -> None:
    """The reader counts what it cannot key; the writer simply refuses to make it."""
    with pytest.raises(store.LabelError, match="whole join"):
        store.label_row(batch="a", score=3, family=JULIA, viewport={"center_re": "0.1"})


def test_a_score_outside_the_scale_is_refused() -> None:
    with pytest.raises(store.LabelError, match="score"):
        store.label_row(batch="a", score=5, family=JULIA, viewport=VIEW)


def test_a_label_is_cast_by_a_human_or_by_a_named_rule() -> None:
    assert store.label_row(batch="a", score=1, family=JULIA, viewport=VIEW, origin="rule:interior")
    with pytest.raises(store.LabelError, match="origin"):
        store.label_row(batch="a", score=1, family=JULIA, viewport=VIEW, origin="somebody")


def test_the_writer_refuses_an_unregistered_batch(store_dir) -> None:
    """Registration comes first, because afterwards the answer is from memory."""
    with pytest.raises(store.LabelError, match="no registration"):
        store.append([row()])


def test_a_revision_is_a_new_row_and_the_original_survives(store_dir, registered) -> None:
    known = registered("a_batch")
    store.append([row(score=3, recorded_at="2026-01-01T00:00:00Z")], known=known)
    store.append([row(score=1, recorded_at="2026-02-01T00:00:00Z")], known=known)

    lines = store.batch_path("a_batch").read_text(encoding="utf-8").strip().splitlines()
    assert [json.loads(line)["score"] for line in lines] == [3, 1]

    resolution = store.resolved()
    assert len(resolution.current) == 1
    assert resolution.scored()[0]["score"] == 1
    assert resolution.n_superseded == 1


def test_latest_wins_is_keyed_on_the_location_not_the_batch(store_dir, registered) -> None:
    """A re-render under a fresh batch is the same place, and cannot hold a second
    live verdict beside the first."""
    registered("first")
    known = registered("second")
    store.append([row(score=2, batch="first", recorded_at="2026-01-01T00:00:00Z")], known=known)
    store.append(
        [
            row(
                score=4,
                batch="second",
                recorded_at="2026-03-01T00:00:00Z",
                render={"resolution": [3840, 2160], "supersample": 4},
            )
        ],
        known=known,
    )
    resolution = store.resolved()
    assert len(resolution.current) == 1
    assert resolution.scored()[0]["score"] == 4


def test_two_julia_views_with_different_seeds_are_two_locations(store_dir, registered) -> None:
    known = registered("a_batch")
    store.append([row(score=3), row(score=1, family=OTHER_JULIA)], known=known)
    assert len(store.resolved().current) == 2


def test_a_withdrawn_verdict_is_read_past(store_dir, registered) -> None:
    known = registered("a_batch")
    store.append([row(score=3, recorded_at="2026-01-01T00:00:00Z")], known=known)
    store.append([row(score=None, recorded_at="2026-02-01T00:00:00Z")], known=known)
    resolution = store.resolved()
    assert len(resolution.current) == 1
    assert resolution.scored() == []


def test_the_schema_is_checked_on_every_row(store_dir, registered) -> None:
    known = registered("a_batch")
    store.append([row()], known=known)
    path = store.batch_path("a_batch")
    path.write_text(json.dumps({**row(), "schema": 99}) + "\n", encoding="utf-8")
    with pytest.raises(store.LabelError, match="schema"):
        store.resolved()


def test_nothing_is_written_when_one_row_of_a_batch_is_bad(store_dir, registered) -> None:
    known = registered("a_batch")
    good = row()
    bad = {**row(), "score": 9}
    with pytest.raises(store.LabelError):
        store.append([good, bad], known=known)
    assert not store.batch_path("a_batch").exists()


# --------------------------------------------------------------------------- #
# The choke point.
# --------------------------------------------------------------------------- #

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The one module allowed to know where the label records live.
STORE_MODULE = "src/fractal_wallpapers/labeling/store.py"

#: The path segment that addresses them.
SEGMENT = "labels"


def tracked_sources() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "src"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [name for name in result.stdout.split("\0") if name.endswith(".py")]


def addresses_the_records(source: str) -> bool:
    """Whether this source builds a path through the label directory's own name.

    Read off the syntax tree rather than the text, and read as *path building*
    rather than as the word: the prose that explains the store in half a dozen
    module docstrings is not a second reader of it, and neither is a report key
    that happens to be spelled the same. What a second reader has to write is a
    join — `something / "labels"`, or a path with the segment inside it.
    """

    def joined(node) -> bool:
        return isinstance(node, ast.Constant) and node.value == SEGMENT

    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.BinOp)
            and isinstance(node.op, ast.Div)
            and (joined(node.left) or joined(node.right))
        ):
            return True
        if isinstance(node, ast.Call):
            for argument in node.args:
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                    spelled = argument.value.replace("\\", "/")
                    if f"/{SEGMENT}/" in spelled or spelled.endswith(f"/{SEGMENT}"):
                        return True
    return False


def test_only_the_store_addresses_the_label_records() -> None:
    offenders = [
        name
        for name in tracked_sources()
        if name.replace("\\", "/") != STORE_MODULE
        and addresses_the_records((REPO_ROOT / name).read_text(encoding="utf-8"))
    ]
    assert not offenders, (
        "these modules address data/labels themselves instead of going through "
        f"{STORE_MODULE}: {offenders}. A second reader is a second answer to what the "
        "corpus says."
    )


def test_the_choke_point_guard_would_actually_catch_something() -> None:
    """A guard that cannot fire is not a guard."""
    assert addresses_the_records('path = repo_root() / "data" / "labels" / "rows"')
    assert addresses_the_records('path = Path("data/labels")')
    assert not addresses_the_records('"""Prose about data/labels is not a second reader."""')
    assert not addresses_the_records('report = {"labels": len(rows)}')
