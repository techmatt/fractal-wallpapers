"""The refine leg at harvest time: what it may move, and what it may never edit.

The gallery pass's step 5a at the other end of the pipeline, through the same
[`curation.framing`] module. What is pinned here is the half that is new: the
top-k register that decides *which* frames are scanned, the never-edit-in-place
rule and the later row that carries it, the reader that prefers that row, and
that `--refine-per-walk 0` is the walk this repository ran before the leg
existed — same ledger, same seed.

Nothing here renders. `framing.screen` is the seam the gallery tests already
stand on and these stand on it too, so a machine with no engine and no weights
can prove the rules the leg is about.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from fractal_wallpapers.curation import framing
from fractal_wallpapers.discovery import ledger as ledger_module
from fractal_wallpapers.discovery.walk import Best, Limits, Policy, Walk
from fractal_wallpapers.supply import ledgers
from fractal_wallpapers.supply.location import key_of_row

NODE = None  # resolved lazily by the fixtures that need a regime


@dataclass
class Reading:
    score: float | None
    great: float | None
    error: str | None = None
    probabilities: tuple = ()
    regime: str | None = None
    view: str | None = None


class Judge:
    """A scorer that reads a scripted number off each frame's width and centre."""

    name = "judge"

    def __init__(self, table: dict | None = None, fallback: float = 0.10, good: float = 0.385):
        from fractal_wallpapers.models import tiles as tile_module

        self.regime = tile_module.NODE_REGIME
        self.table = table or {}
        self.fallback = fallback
        self.good = good

    def read(self, candidates, pictures=None):
        del pictures
        out = []
        for candidate in candidates:
            viewport = candidate["viewport"]
            key = (
                round(float(viewport["width"]), 6),
                round(float(viewport["center_re"]), 6),
                round(float(viewport["center_im"]), 6),
            )
            great = self.table.get(key, self.fallback)
            out.append(Reading(min(1.0, great + 0.05), great, None, (), self.regime.spelled, None))
        return out

    def score(self, candidate):
        return self.read([candidate])[0].score

    def admits(self, candidate, score):
        return score is not None and score >= self.good

    def expandable(self, candidate, score):
        return score is not None and score >= 0.1


def row(width: str = "1.0", great: float = 0.9, score: float = 0.95, **extra) -> dict:
    """One scored gate-survivor candidate row, in the shape the ledger keeps."""
    return {
        "family": {"kind": "mandelbrot", "degree": 2},
        "viewport": {"center_re": "0.0", "center_im": "0.0", "width": width},
        "maxiter": 500,
        "image": None,
        "root_id": 1,
        "depth": 3,
        "fate": ledger_module.SURVIVED,
        "score": score,
        "score_great": great,
        "score_regime": "384x216ss1",
        **extra,
    }


def stub_screen(monkeypatch):
    """`framing.screen` without an engine: every frame draws and passes the gates."""

    def fake(pairs, directory, log=print):
        del directory, log
        return [
            {
                "framing": frame,
                "picture": f"{index:05d}_{frame.slug}.jpg",
                "fate": "survived",
                "passed": True,
                "viewport": dict(frame.viewport),
                "maxiter": frame.maxiter or 1234,
                "p_ge3": None,
                "p_ge4": None,
                "error": None,
            }
            for index, (_row, frame) in enumerate(pairs)
        ]

    monkeypatch.setattr(framing, "screen", fake)


def walk_at(tmp_path, judge, monkeypatch, **limits) -> Walk:
    """A walk whose identity is asserted without a corpus, ready to refine."""
    from fractal_wallpapers.models import tiles as tile_module

    monkeypatch.setattr(
        Walk, "_enforce_identity", lambda self: {"regime": tile_module.NODE_REGIME.spelled}
    )
    return Walk(
        out_dir=tmp_path / "walk",
        seed=7,
        scorer=judge,
        limits=Limits(batch=1, batches=0, **limits),
        policy=Policy(candidates=1, node_width=tile_module.NODE_REGIME.tile[0]),
    )


# --------------------------------------------------------------------------- #
# Which frames get scanned.
# --------------------------------------------------------------------------- #
def test_the_register_keeps_the_best_k_on_the_seating_statistic() -> None:
    """`P(>=4)` first, `P(>=3)` second — the order a gallery slot is filled in."""
    best = Best(2)
    for great, score in ((0.5, 0.9), (0.9, 0.1), (0.9, 0.99), (0.1, 1.0)):
        best.offer(row(great=great, score=score))
    kept = best.take()
    assert [(cell["score_great"], cell["score"]) for cell in kept] == [(0.9, 0.99), (0.9, 0.1)]
    assert best.seen == 4


def test_the_register_never_offers_a_row_with_no_verdict() -> None:
    """A failed render has no score to be ranked on, and a null-scorer walk has none
    at all — neither is a frame worth seven renders."""
    best = Best(3)
    best.offer(row(great=None))
    best.offer({**row(), "score_great": None, "score_error": "no view"})
    assert best.take() == []
    assert best.seen == 0


def test_the_register_breaks_a_full_tie_on_the_order_the_ledger_wrote() -> None:
    """So a walk re-run on one seed refines the same frames rather than whichever of
    a tie the sort happened to leave on top."""
    best = Best(1)
    first, second = row(width="1.0"), row(width="2.0")
    best.offer(first)
    best.offer(second)
    assert best.take() == [first]


def test_k_of_zero_keeps_nothing_and_costs_nothing() -> None:
    best = Best(0)
    best.offer(row())
    assert best.take() == [] and best.seen == 0


# --------------------------------------------------------------------------- #
# The leg, and what it writes.
# --------------------------------------------------------------------------- #
def test_the_leg_is_off_at_k_zero_and_writes_no_row(tmp_path, monkeypatch) -> None:
    """`--refine-per-walk 0` is the walk this repository ran before the leg existed."""
    run = walk_at(tmp_path, Judge(), monkeypatch, refine_per_walk=0)
    run.best.offer(row())
    report = run.refine_framings()
    assert report == {"status": "off", "reason": "--refine-per-walk 0"}
    kinds = [json.loads(line)["kind"] for line in _lines(run)]
    assert ledger_module.REFINED not in kinds


def test_a_walk_that_asserts_no_identity_does_not_scan(tmp_path, monkeypatch) -> None:
    """The same precondition the gate render's own score rests on: without it the
    scan would draw frames the head was never trained on."""
    monkeypatch.setattr(Walk, "_enforce_identity", lambda self: None)
    from fractal_wallpapers.models import tiles as tile_module

    run = Walk(
        out_dir=tmp_path / "walk",
        seed=7,
        scorer=Judge(),
        limits=Limits(batch=1, batches=0),
        policy=Policy(candidates=1, node_width=tile_module.NODE_REGIME.tile[0]),
    )
    run.best.offer(row())
    assert run.refine_framings()["status"] == "skipped"


def test_an_adopted_refinement_is_a_later_row_and_never_an_edit(tmp_path, monkeypatch) -> None:
    """THE record rule. The candidate row on disk is byte-for-byte what was written."""
    stub_screen(monkeypatch)
    judge = Judge({(1.0, 0.0, 0.0): 0.30, (1.414, 0.0, 0.0): 0.95})
    run = walk_at(tmp_path, judge, monkeypatch, refine_per_walk=1)
    original = row(great=0.30, score=0.35)
    run.ledger.write("candidate", node_id=None, **original)
    before = run.ledger.path.read_text(encoding="utf-8")
    run.best.offer(original)

    report = run.refine_framings()
    assert report["adopted"] == 1
    after = run.ledger.path.read_text(encoding="utf-8")
    assert after.startswith(before), "an earlier row was rewritten"

    rows = [json.loads(line) for line in _lines(run)]
    refined = [cell for cell in rows if cell["kind"] == ledger_module.REFINED]
    assert len(refined) == 1
    cell = refined[0]
    # The join is the ORIGINAL frame, because that is the identity every reader
    # already dedups on.
    assert cell["viewport"] == original["viewport"]
    assert float(cell["refined_viewport"]["width"]) == pytest.approx(1.414)
    assert cell["adopted"] is True and cell["score_great"] == 0.95
    # The walk's own read of the same frame, carried beside the scan's.
    assert cell["walk_score_great"] == 0.30
    assert cell["scan_score_great"] == 0.30


def test_a_window_that_did_not_clear_the_margin_is_still_recorded(tmp_path, monkeypatch) -> None:
    """What the margin refused is the evidence the margin is set where it should be."""
    stub_screen(monkeypatch)
    run = walk_at(tmp_path, Judge(fallback=0.31), monkeypatch, refine_per_walk=1)
    run.best.offer(row(great=0.30, score=0.35))
    report = run.refine_framings()
    assert report["adopted"] == 0
    [cell] = [
        json.loads(line)
        for line in _lines(run)
        if json.loads(line)["kind"] == ledger_module.REFINED
    ]
    assert cell["adopted"] is False
    assert cell["refused"] == framing.BELOW_MARGIN
    # Nothing to prefer, and the best is on the record anyway.
    assert cell["refined_viewport"] is None and cell["score"] is None
    assert cell["best_score_great"] == 0.31


def test_the_leg_charges_its_own_operator_line(tmp_path, monkeypatch) -> None:
    """Priced where the reframing operators are priced, under its own name."""
    stub_screen(monkeypatch)
    run = walk_at(tmp_path, Judge(), monkeypatch, refine_per_walk=1)
    run.best.offer(row())
    run.refine_framings()
    assert "refine_framing" in run.operator_seconds
    assert run.operator_seconds["refine_framing"]["firings"] == 1


def test_the_leg_compares_the_walks_own_gate_render_with_the_scans(tmp_path, monkeypatch) -> None:
    """The measurement the gallery pass could not take: there the picture the first
    read came off was gone, and here this run drew it."""
    stub_screen(monkeypatch)
    run = walk_at(tmp_path, Judge(), monkeypatch, refine_per_walk=1)
    gate = run.views_dir()
    gate.mkdir(parents=True, exist_ok=True)
    (gate / "g0.jpg").write_bytes(b"a gate render")
    scan = run.refine_dir()
    scan.mkdir(parents=True, exist_ok=True)
    (scan / "00001_w1_c.jpg").write_bytes(b"a gate render")
    run.best.offer(row(great=0.42, image="g0.jpg"))

    report = run.refine_framings()
    cell = report["gate_render"]
    assert cell["compared"] == 1
    assert cell["identical_bytes"] == 1, "the same bytes hash the same"
    # The scan's read of the x1.0 frame against the walk's own, on this row a
    # scripted disagreement of 0.10 - 0.42.
    assert cell["readings"] == 1
    assert cell["max_abs_delta_p_ge4"] == pytest.approx(0.32, abs=1e-9)


# --------------------------------------------------------------------------- #
# The reader that prefers the later row.
# --------------------------------------------------------------------------- #
def ledger_with(tmp_path, candidate: dict, refinement: dict | None) -> Path:
    path = tmp_path / "walk.jsonl"
    lines = [{"schema": 1, "kind": "candidate", **candidate}]
    if refinement is not None:
        lines.append({"schema": 1, "kind": ledger_module.REFINED, **refinement})
    path.write_text(
        "".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8", newline="\n"
    )
    return path


def refinement_of(candidate: dict, width: str = "1.414", score: float = 0.9) -> dict:
    return {
        "family": candidate["family"],
        "viewport": candidate["viewport"],
        "adopted": True,
        "refused": None,
        "margin": 2.0,
        "gain": 3.0,
        "gain_p_ge4": 0.5,
        "width_scale": 1.414,
        "dx": 0,
        "dy": 0,
        "framing": "w1.414_c",
        "refined_viewport": {"center_re": "0.0", "center_im": "0.0", "width": width},
        "refined_maxiter": 999,
        "score": score,
        "score_great": score,
        "run_seed": 7,
        "score_regime": "384x216ss1",
    }


def test_the_reader_prefers_the_refinement_and_carries_the_frame_it_replaced(
    tmp_path,
) -> None:
    """The frame, the cap and the verdict all move, and the one it replaced is kept."""
    candidate = row(great=0.1, score=0.2)
    path = ledger_with(tmp_path, candidate, refinement_of(candidate))
    [read] = ledgers.admitted(path, admit=ledgers.passes_gates)
    assert float(read["viewport"]["width"]) == pytest.approx(1.414)
    assert read["maxiter"] == 999
    assert read["score"] == 0.9
    assert read["framing"]["original"]["viewport"] == candidate["viewport"]
    assert read["framing"]["original"]["score"] == 0.2
    # The digest names a picture of the frame that was replaced, so it is dropped
    # rather than carried onto a row it no longer describes.
    assert read["score_view"] is None


def test_a_refined_row_is_a_different_location_the_way_two_framings_always_are(
    tmp_path,
) -> None:
    """The identity moves with the frame, and this is where that is decided.

    It is the project's existing stance — the reframing operators dedup on
    `(atom, framing)` precisely because *the same atom at two framings is two
    views* — and it is the opposite of what the gallery pass does with a
    refinement. The two are not in conflict: a pass refines a location the pool
    already holds at its recorded frame and has to pin identity so one place
    cannot take two seats, while a walk refines a frame nothing downstream has
    seen yet.
    """
    candidate = row(great=0.1, score=0.2)
    path = ledger_with(tmp_path, candidate, refinement_of(candidate))
    [read] = ledgers.admitted(path, admit=ledgers.passes_gates)
    assert key_of_row(read) != key_of_row(candidate)
    # And the union sees ONE of them, not both: the reader replaces the row it
    # refines rather than adding beside it.
    assert len(ledgers.admitted(path, admit=ledgers.passes_gates)) == 1


def test_a_refinement_can_lift_a_row_over_the_keeper_floor(tmp_path) -> None:
    """Admission reads the refined score."""
    candidate = row(great=0.02, score=0.05, fate=ledger_module.NOT_ADMITTED)
    assert ledgers.admitted(ledger_with(tmp_path, candidate, None)) == []
    lifted = ledger_with(tmp_path, candidate, refinement_of(candidate, score=0.9))
    [read] = ledgers.admitted(lifted)
    assert read["fate"] == ledger_module.SURVIVED, "the fate is re-derived, not carried"


def test_a_refusal_row_changes_nothing_about_the_location(tmp_path) -> None:
    """A decision that was deliberately not taken is not a decision a reader acts on."""
    candidate = row(great=0.1, score=0.2)
    refused = {**refinement_of(candidate), "adopted": False, "refined_viewport": None}
    path = ledger_with(tmp_path, candidate, refused)
    [read] = ledgers.admitted(path, admit=ledgers.passes_gates)
    assert read["viewport"] == candidate["viewport"]
    assert "framing" not in read


def test_the_reader_returns_rows_in_ledger_order_whatever_was_refined(tmp_path) -> None:
    """A refinement is decided after the pass, so order has to be put back."""
    path = tmp_path / "walk.jsonl"
    rows = [
        {"schema": 1, "kind": "candidate", **row(width=str(n), great=0.9, score=0.9)}
        for n in range(1, 5)
    ]
    rows[1]["fate"] = "interior_cap"  # a gate refusal, decided on the way past
    third = row(width="3", great=0.9, score=0.9)
    rows.append({"schema": 1, "kind": ledger_module.REFINED, **refinement_of(third, width="9")})
    path.write_text(
        "".join(json.dumps(line) + "\n" for line in rows), encoding="utf-8", newline="\n"
    )
    read = ledgers.admitted(path, admit=lambda _row: True)
    assert [cell["viewport"]["width"] for cell in read] == ["1", "2", "9", "4"]


def _lines(run: Walk) -> list[str]:
    return [line for line in run.ledger.path.read_text(encoding="utf-8").splitlines() if line]
