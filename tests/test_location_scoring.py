"""Scoring a location the moment the walk finds it.

The point of the change these cover is a loop that used to be open: a harvest
wrote twenty-two thousand rows with a null score, the census reads each row's own
score, and so the books did not move at all. The tests here are about the seam
rather than about the head — a stub scorer says what the head would say, which is
what lets them run on a machine with no weights and still pin the two things that
can go wrong: what lands on the row, and in what order.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers import engine
from fractal_wallpapers.discovery import ledger as ledger_module
from fractal_wallpapers.discovery import scoring
from fractal_wallpapers.discovery.walk import Limits, Policy, Walk
from fractal_wallpapers.supply import currency

#: Three Mandelbrot frames the walk tests already stand on — known to produce
#: candidates through the real gates, so a smoke walk here has something to score.
SEEDS = (
    ("-0.7453", "0.1127", "0.2"),
    ("0.2929", "0.0149", "0.1"),
    ("-0.748", "0.263", "0.06"),
)


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


class Stub:
    """A scorer with an opinion, standing in for the head on a machine with none.

    `readings` is consumed in order, so a test can say what each candidate of a
    batch comes back as and then assert what the ledger did with it.
    """

    name = "stub"

    def __init__(self, readings, admit_floor: bool = True):
        self.readings = list(readings)
        self.admit_floor = admit_floor
        self.batches: list[int] = []

    def score(self, candidate):
        return self.read([candidate])[0].score

    def read(self, candidates):
        self.batches.append(len(candidates))
        out = [
            self.readings[index] if index < len(self.readings) else scoring.NO_OPINION
            for index in range(len(candidates))
        ]
        del self.readings[: len(candidates)]
        return out

    def admits(self, candidate, score):
        return currency.passes_good_floor(score) if self.admit_floor else True


# --------------------------------------------------------------------------- #
# the seam
# --------------------------------------------------------------------------- #
def test_a_reading_carries_both_cutpoints_and_a_reason_for_neither() -> None:
    """The currency weights a class 4 ten times a class 3, so one number is not
    enough — and a render that failed is not a score of zero."""
    assert scoring.Reading(None, None, None) == scoring.NO_OPINION
    full = scoring.Reading(0.81, 0.42)
    assert (full.score, full.great, full.error) == (0.81, 0.42, None)
    assert scoring.Reading(error="no view").score is None


def test_the_null_scorer_answers_a_whole_batch_and_admits_on_the_gates_alone() -> None:
    scorer = scoring.NullScorer()
    candidates = [{"a": 1}, {"a": 2}, {"a": 3}]
    assert scorer.read(candidates) == [scoring.NO_OPINION] * 3
    assert scorer.score(candidates[0]) is None
    assert scorer.admits(candidates[0], None) is True


def test_the_engine_thread_count_is_explicit_above_one_worker() -> None:
    """Inherited thread counts are how four engines each take the whole machine."""
    assert scoring.engine_threads_for(1) is None
    assert scoring.engine_threads_for(4) == scoring.ENGINE_THREADS_PER_WORKER


def test_the_location_head_admits_at_the_keeper_floor_and_nowhere_else() -> None:
    """One word, one owner: `supply.currency` already decides what "admitted"
    means for the census, the ledger union and the slot guarantee."""
    admits = scoring.LocationScorer.admits
    scorer = object.__new__(scoring.LocationScorer)
    assert admits(scorer, {}, currency.GOOD_FLOOR) is True
    assert admits(scorer, {}, currency.GOOD_FLOOR - 1e-9) is False
    assert admits(scorer, {}, None) is False


def test_views_come_back_in_the_order_they_were_asked_for(tmp_path, monkeypatch) -> None:
    """A pooled render finishes out of order and the ledger must not."""
    made = []

    def render(task):
        made.append(task.output)
        return scoring.ViewResult(task.output, True, 0.0)

    monkeypatch.setattr(scoring, "render_view", render)
    tasks = [scoring.ViewTask({}, str(tmp_path / f"{i}.jpg")) for i in range(5)]
    out = scoring.render_views(tasks, workers=1)
    assert [result.output for result in out] == [task.output for task in tasks]


# --------------------------------------------------------------------------- #
# what the walk writes
# --------------------------------------------------------------------------- #
def _walk(tmp_path, scorer) -> Walk:
    run = Walk(
        out_dir=tmp_path / "walk",
        seed=20260816,
        limits=Limits(batch=3, batches=2, root_expansions=4),
        policy=Policy(candidates=2, node_width=128),
        scorer=scorer,
    )
    for index, (centre_re, centre_im, width) in enumerate(SEEDS):
        run.add_root(
            {"kind": "mandelbrot"},
            {"center_re": centre_re, "center_im": centre_im, "width": width},
            source="test",
            provenance={"seed_id": f"s{index}"},
        )
    return run


def _rows(run: Walk) -> list[dict]:
    run.ledger.close()
    return [row for row in ledger_module.read(run.ledger.path) if row["kind"] == "candidate"]


@needs_engine
def test_every_admitted_row_carries_the_head_s_two_numbers(tmp_path) -> None:
    """The census reads `score` and `score_great` off the row. A harvest that
    wrote neither moved the standing deficit by exactly zero."""
    scorer = Stub([scoring.Reading(0.9, 0.7)] * 64)
    run = _walk(tmp_path, scorer)
    run.run()

    admitted = [row for row in _rows(run) if row["fate"] == ledger_module.SURVIVED]
    assert admitted, "the smoke walk found nothing to score"
    for row in admitted:
        assert row["scorer"] == "stub"
        assert row["score"] == 0.9
        assert row["score_great"] == 0.7
        assert row["score_error"] is None


@needs_engine
def test_a_candidate_below_the_floor_is_recorded_rather_than_dropped(tmp_path) -> None:
    """Record and rank, never gate and forget: the row keeps its score and its
    frame, and only the fate says the scorer refused it."""
    scorer = Stub([scoring.Reading(0.01, 0.0)] * 64)
    run = _walk(tmp_path, scorer)
    summary = run.run()

    rows = _rows(run)
    refused = [row for row in rows if row["fate"] == "not_admitted"]
    assert refused, "a scorer that admits nothing must still leave rows behind"
    for row in refused:
        assert row["score"] == 0.01
        assert row["viewport"]["width"]
    assert summary["counts"].get("not_admitted:below") == len(refused)
    assert not [row for row in rows if row["fate"] == ledger_module.SURVIVED]


@needs_engine
def test_a_view_that_could_not_be_made_is_a_reason_and_not_a_zero(tmp_path) -> None:
    """A crashed render and a bad location must not be the same number."""
    scorer = Stub([scoring.Reading(error="engine failed")] * 64)
    run = _walk(tmp_path, scorer)
    summary = run.run()

    rows = [row for row in _rows(run) if row["fate"] == "not_admitted"]
    assert rows
    assert all(row["score"] is None and row["score_error"] == "engine failed" for row in rows)
    assert summary["counts"].get("not_admitted:no_score") == len(rows)
    assert summary["counts"].get("score_failed") == len(rows)


@needs_engine
def test_the_scorer_is_asked_once_per_engine_call_not_once_per_candidate(tmp_path) -> None:
    """The whole reason the renders can fan out: a per-candidate call would fix
    the ledger's order to whichever worker finished first."""
    scorer = Stub([scoring.Reading(0.9, 0.5)] * 64, admit_floor=False)
    run = _walk(tmp_path, scorer)
    run.run()
    assert scorer.batches, "the scorer was never asked anything"
    assert max(scorer.batches) > 1, "a batch of one is a per-candidate call in disguise"


@needs_engine
def test_the_ledger_s_order_is_the_engine_s_order(tmp_path) -> None:
    """Rows are written after the whole batch is scored, and still in the order
    the engine reported them — never in the order the views happened to finish."""
    scorer = Stub([scoring.Reading(0.9, 0.5)] * 64, admit_floor=False)
    run = _walk(tmp_path, scorer)
    reported = run.expand(run.pop_batch())["candidates"]
    assert reported, "the smoke batch produced no candidates"

    written = _rows(run)
    identity = [(row["parent_node_id"], row["child_index"]) for row in reported]
    assert [(row["parent_node_id"], row["child_index"]) for row in written] == identity
    for node_id in {parent for parent, _ in identity}:
        indices = [child for parent, child in identity if parent == node_id]
        assert indices == sorted(indices), "one node's children came back out of order"


def test_the_run_header_names_the_judge_that_produced_the_scores(tmp_path) -> None:
    """A ledger nobody can attribute is a ledger whose scores mean nothing."""
    run = Walk(out_dir=tmp_path / "walk", seed=0, scorer=Stub([]))
    run.ledger.close()
    header = ledger_module.read(run.ledger.path)[0]
    assert header["kind"] == "run"
    assert header["scorer"] == "stub"
    assert header["scoring"] is None, "a scorer with nothing to declare declares nothing"


# --------------------------------------------------------------------------- #
# the loop this closes
# --------------------------------------------------------------------------- #
def test_a_scored_ledger_moves_the_standing_deficit(tmp_path) -> None:
    """The whole point. Under the null scorer every row is `unclassed` and the
    machine leg contributes nothing; with the head's two numbers on the row the
    census classes it without reading a sidecar."""
    from fractal_wallpapers.supply import census

    path = tmp_path / "walk.jsonl"
    rows = [
        {
            "schema": 1,
            "kind": "candidate",
            "fate": ledger_module.SURVIVED,
            "family": {"kind": "mandelbrot"},
            "viewport": {"center_re": "-0.5", "center_im": f"0.{index}", "width": "0.01"},
            "scorer": "location:abcdef",
            "score": 0.91,
            "score_great": great,
            "score_error": None,
        }
        for index, great in enumerate((0.8, 0.1))
    ]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8", newline="\n")

    leg = census.machine_stock(("mandelbrot",), ledger_paths=[path])
    assert leg.n_unclassed == 0, "a scored row must not read as unclassed"
    # One class 4 (it cleared the great cut) and one class 3: 1.0 + 0.1.
    assert leg.counts["mandelbrot"] == {4: 1, 3: 1}
    assert leg.currency["mandelbrot"] == pytest.approx(1.1)


def test_an_unscored_ledger_is_still_readable_and_still_says_so(tmp_path) -> None:
    """The corpus is mixed across the day the head was wired in, and a reader
    asks the row what judged it rather than assuming."""
    from fractal_wallpapers.supply import census

    path = tmp_path / "walk.jsonl"
    path.write_text(
        json.dumps(
            {
                "schema": 1,
                "kind": "candidate",
                "fate": ledger_module.SURVIVED,
                "family": {"kind": "mandelbrot"},
                "viewport": {"center_re": "-0.5", "center_im": "0.1", "width": "0.01"},
                "scorer": "null",
                "score": None,
            }
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    leg = census.machine_stock(("mandelbrot",), ledger_paths=[path])
    # Not admitted at all, rather than admitted and unclassed: the union's own
    # admission predicate is the gates AND the keeper floor, and an unscored row
    # has no verdict to be kept on. That is the state twenty-two thousand rows
    # were in, and the reason the harvest moved the books by zero.
    assert leg.n_admitted == 0
    assert leg.currency["mandelbrot"] == 0.0
