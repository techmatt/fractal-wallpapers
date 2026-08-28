"""The refine-framing step: the window, the margin, and what it may not move.

Three claims a wrong answer would cost real money or a wrong gallery. The window
geometry, because it is the whole search and the archive it came from never swept
it. The margin, because without it the step is an argmax over correlated reads of
one place and adopts noise. And the monotonicity assertion, because it is the one
thing that turns an arithmetic bug into a stopped leg instead of a whole
collection framed on the result.

There was a fourth — that `--no-refine` reproduced the pre-step attempt leg
exactly — and it went with the pre-solver gallery pass on 2026-08-28, along with
the two plan tests beside it. The claim it left behind, that a re-framed row
still stands on its **recorded** place, is pinned where the identity now lives:
`tests/test_candidate_ledger.py` and `tests/test_hunt.py`.

Nothing here renders: [`framing.screen`] is the seam and the tests stand on it.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from fractal_wallpapers.curation import framing

SMOOTH, STRANGE = "smooth_render", "strange_render"


def location(key: str = "k0", width: str = "1.0", maxiter: int = 500) -> dict:
    return {
        "key": key,
        "partition": "mandelbrot",
        "family": {"kind": "mandelbrot", "degree": 2},
        "viewport": {"center_re": "0.0", "center_im": "0.0", "width": width},
        "maxiter": maxiter,
    }


# --------------------------------------------------------------------------- #
# The window.
# --------------------------------------------------------------------------- #
def test_the_window_is_three_widths_and_four_one_axis_recentrings() -> None:
    """Seven framings, and the ladder's own centre is one of them."""
    frames = framing.window(location())
    assert len(frames) == len(framing.WIDTH_LADDER) + len(framing.AXES) == 7
    assert [frame.width_scale for frame in frames[:3]] == list(framing.WIDTH_LADDER)
    assert [(frame.dx, frame.dy) for frame in frames[:3]] == [(0, 0)] * 3
    assert [(frame.dx, frame.dy) for frame in frames[3:]] == list(framing.AXES)
    # One axis at a time: no diagonal is in the window at all.
    assert all(frame.dx == 0 or frame.dy == 0 for frame in frames)
    assert sum(1 for frame in frames if frame.unmoved) == 1


def test_the_unmoved_rung_reproduces_the_record_rather_than_re_deriving_it() -> None:
    """The `x1.0` centre carries the row's own decimals and its own cap.

    It is the frame the sidecar's score was read off. Re-deriving it through the
    same float arithmetic the moved rungs use would be a different string for the
    same number on some rows, and a different string is a different render cache
    entry and a different digest.
    """
    row = location(width="0.00123456789", maxiter=7011)
    centre = next(frame for frame in framing.ladder(row) if frame.unmoved)
    assert centre.viewport == row["viewport"]
    assert centre.maxiter == 7011
    # Every other rung lets the engine's own policy give the width its cap.
    assert all(frame.maxiter is None for frame in framing.ladder(row) if not frame.unmoved)


def test_a_quarter_frame_is_a_quarter_along_the_axis_it_moves_on() -> None:
    """Sideways by a quarter of the width, up by a quarter of the HEIGHT.

    The archive moved by a quarter of the width on both axes, which on a 16:9
    frame is 0.44 frame-heights vertically — two recentrings of two different
    sizes. This is the one place the geometry here departs from it.
    """
    row = location(width="2.0")
    moved = framing.recentres(row, framing.Framing(1.0, 0, 0, row["viewport"]))
    by_axis = {(frame.dx, frame.dy): frame.viewport for frame in moved}
    assert float(by_axis[(1, 0)]["center_re"]) == pytest.approx(0.5)
    assert float(by_axis[(-1, 0)]["center_re"]) == pytest.approx(-0.5)
    assert float(by_axis[(0, 1)]["center_im"]) == pytest.approx(0.5 * framing.aspect())
    assert framing.aspect() == pytest.approx(9 / 16)
    # A recentring never changes the width, and the ladder never moves the centre.
    assert {frame.viewport["width"] for frame in moved} == {repr(2.0)}


def test_the_recentring_is_taken_at_the_width_the_ladder_chose() -> None:
    """Separable means stage B moves the frame stage A picked, not the one it started
    from."""
    row = location(width="1.0")
    moved = framing.recentres(row, framing.Framing(1.414, 0, 0, {}))
    east = next(frame for frame in moved if (frame.dx, frame.dy) == (1, 0))
    assert float(east.viewport["width"]) == pytest.approx(1.414)
    assert float(east.viewport["center_re"]) == pytest.approx(0.25 * 1.414)


# --------------------------------------------------------------------------- #
# The margin.
# --------------------------------------------------------------------------- #
def cell(p_ge4: float, p_ge3: float = 0.9, passed: bool = True, picture: str = "f.jpg") -> dict:
    return {
        "framing": framing.Framing(1.414, 0, 0, {}),
        "picture": picture,
        "fate": "survived" if passed else "occupancy_floor",
        "passed": passed,
        "viewport": {"center_re": "0", "center_im": "0", "width": "1"},
        "maxiter": 500,
        "p_ge4": p_ge4,
        "p_ge3": p_ge3,
        "error": None,
    }


def test_the_margin_is_taken_in_log_odds_and_not_in_the_probability() -> None:
    """THE finding the first scan produced, kept as a test.

    The locations this step sees read `P(>=4)` against its ceiling, where a
    probability margin cannot express how much better a framing is: 0.9990 to
    0.9999 is a tenth of a percent and a factor of ten in the odds.
    """
    assert framing.gain_of(cell(0.9999), cell(0.9990)) == pytest.approx(2.303, abs=1e-3)
    assert cell(0.9999)["p_ge4"] - cell(0.9990)["p_ge4"] < 0.001
    # A probability of exactly 1 is a reading this head really produces, and a
    # difference of infinities is not a margin anything can act on.
    assert framing.logit(1.0) == pytest.approx(-framing.logit(0.0))
    assert framing.gain_of(cell(1.0), cell(0.9999)) > 0


def test_a_winner_that_does_not_clear_the_margin_is_refused() -> None:
    """THE planted case: the window's best is better, and the framing stays anyway."""
    original = cell(0.50)
    # +0.5 nats and +0.2 nats against a margin of 2.
    best, refusal = framing.decide(original, [cell(0.6225), cell(0.5498)], 2.0)
    assert refusal == framing.BELOW_MARGIN
    # The best is still returned - it is the evidence the margin is set right, and
    # the sheet puts it beside the framing that was kept.
    assert best["p_ge4"] == 0.6225
    assert framing.gain_of(best, original) < 2.0


def test_a_winner_that_clears_the_margin_is_adopted() -> None:
    best, refusal = framing.decide(cell(0.50), [cell(0.90), cell(0.6225)], 2.0)
    assert refusal is None
    assert best["p_ge4"] == 0.90
    assert framing.gain_of(best, cell(0.50)) == pytest.approx(2.197, abs=1e-3)


def test_the_margin_is_strict_and_not_an_argmax() -> None:
    """A window whose every candidate reads lower keeps the original, and says why."""
    _, refusal = framing.decide(cell(0.80), [cell(0.10), cell(0.79)], 2.0)
    assert refusal == framing.BELOW_MARGIN


def test_the_tie_among_qualifiers_breaks_on_the_statistic_the_seating_breaks_on() -> None:
    best, refusal = framing.decide(
        cell(0.10), [cell(0.95, p_ge3=0.70), cell(0.95, p_ge3=0.95)], 2.0
    )
    assert refusal is None
    assert best["p_ge3"] == 0.95


def test_a_framing_the_gates_refused_may_not_be_adopted_however_it_reads() -> None:
    """A frame no walk would have admitted is not a frame the gallery may ship."""
    assert not framing.adoptable(cell(0.99, passed=False))
    best, refusal = framing.decide(cell(0.10), [cell(0.99, passed=False)], 2.0)
    assert (best, refusal) == (None, framing.NO_CANDIDATE)


def test_a_window_that_drew_nothing_is_a_different_answer_from_one_that_lost() -> None:
    best, refusal = framing.decide(cell(0.10), [cell(0.99, picture=None)], 2.0)
    assert (best, refusal) == (None, framing.NO_CANDIDATE)
    assert framing.REFUSALS[framing.NO_CANDIDATE] != framing.REFUSALS[framing.BELOW_MARGIN]


# --------------------------------------------------------------------------- #
# Monotonicity.
# --------------------------------------------------------------------------- #
def test_an_adopted_framing_that_reads_lower_aborts_rather_than_recording() -> None:
    """The claim the archive's caller made, kept, and kept as a raise."""
    with pytest.raises(framing.MonotonicityViolated):
        framing._assert_monotone(location(), cell(0.80, p_ge3=0.90), cell(0.20, p_ge3=0.10))
    # Equal on `P(>=4)` and higher on the tiebreak is not a violation.
    framing._assert_monotone(location(), cell(0.80, p_ge3=0.90), cell(0.80, p_ge3=0.99))


# --------------------------------------------------------------------------- #
# The leg, over a stubbed engine.
# --------------------------------------------------------------------------- #
@dataclass
class Reading:
    score: float | None
    great: float | None
    error: str | None = None


class Scorer:
    """A head that reads a scripted number off each frame's width and centre."""

    def __init__(self, table: dict, fallback: float = 0.10):
        self.table, self.fallback = table, fallback
        self.batches = 0

    def read(self, candidates, pictures=None):
        self.batches += 1
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
            out.append(Reading(min(1.0, great + 0.05), great))
        return out


def stub_screen(monkeypatch, refuse=()):
    """`framing.screen` without an engine: every frame draws and passes the gates."""

    def fake(pairs, directory, log=print):
        del directory, log
        return [
            {
                "framing": frame,
                "picture": f"{index:05d}_{frame.slug}.jpg",
                "fate": "survived",
                "passed": frame.slug not in refuse,
                "viewport": dict(frame.viewport),
                "maxiter": frame.maxiter or 1234,
                "p_ge3": None,
                "p_ge4": None,
                "error": None,
            }
            for index, (_row, frame) in enumerate(pairs)
        ]

    monkeypatch.setattr(framing, "screen", fake)


def test_the_leg_scans_both_stages_and_adopts_what_clears_the_margin(monkeypatch, tmp_path) -> None:
    """One location, wider and to the left, and the record says so."""
    stub_screen(monkeypatch)
    row = location(width="1.0")
    scorer = Scorer(
        {
            (1.0, 0.0, 0.0): 0.30,  # the original
            (1.414, 0.0, 0.0): 0.40,  # the ladder's winner
            (1.414, -0.3535, 0.0): 0.90,  # a quarter frame west of it
        }
    )
    [record] = framing.refine(
        [row], directory=tmp_path, scorer=scorer, margin=2.0, log=lambda _line: None
    )
    assert record["adopted"] is True
    assert (record["width_scale"], record["dx"], record["dy"]) == (1.414, -1, 0)
    assert record["gain"] == pytest.approx(3.045, abs=1e-3)
    assert record["gain_p_ge4"] == pytest.approx(0.60, abs=1e-6)
    assert record["original"]["p_ge4"] == 0.30
    assert record["best"]["p_ge4"] == 0.90
    assert record["scanned"] == 7
    # Two engine batches and two head batches, not fourteen: both stages are
    # batched across locations, which is what makes the leg affordable.
    assert scorer.batches == 2


def test_the_leg_keeps_the_recorded_framing_when_nothing_clears_the_margin(
    monkeypatch, tmp_path
) -> None:
    stub_screen(monkeypatch)
    row = location()
    scorer = Scorer({(1.0, 0.0, 0.0): 0.50}, fallback=0.60)
    [record] = framing.refine(
        [row], directory=tmp_path, scorer=scorer, margin=2.0, log=lambda _line: None
    )
    assert record["adopted"] is False
    assert record["refused"] == framing.BELOW_MARGIN
    assert record["best"]["p_ge4"] == 0.60
    assert framing.apply_to({"viewport": row["viewport"]}, record)["viewport"] == row["viewport"]


def test_the_leg_re_frames_the_colorizers_row_and_leaves_the_key_alone(
    monkeypatch, tmp_path
) -> None:
    """Identity is the key. A refined attempt is the same location, framed elsewhere."""
    stub_screen(monkeypatch)
    row = location(key="the-key")
    scorer = Scorer({(1.0, 0.0, 0.0): 0.10, (1.414, 0.0, 0.0): 0.90})
    [record] = framing.refine(
        [row], directory=tmp_path, scorer=scorer, margin=2.0, log=lambda _line: None
    )
    moved = framing.apply_to(row, record)
    assert moved["key"] == "the-key"
    assert moved["viewport"] != row["viewport"]
    assert float(moved["viewport"]["width"]) == pytest.approx(1.414)
    block = framing.block(record, framing.REFINED)
    assert block["original"]["viewport"] == row["viewport"]
    assert block["refined"]["viewport"] == moved["viewport"]
    assert block["used"] == framing.REFINED


def test_a_location_whose_own_frame_would_not_draw_is_not_scanned_further(
    monkeypatch, tmp_path
) -> None:
    """No original, no comparison — and stage B is not paid for."""

    def fake(pairs, directory, log=print):
        del directory, log
        return [
            {
                "framing": frame,
                "picture": None,
                "fate": "interior_cap",
                "passed": False,
                "viewport": dict(frame.viewport),
                "maxiter": 10,
                "p_ge3": None,
                "p_ge4": None,
                "error": None,
            }
            for _row, frame in pairs
        ]

    monkeypatch.setattr(framing, "screen", fake)
    [record] = framing.refine(
        [location()], directory=tmp_path, scorer=Scorer({}), margin=2.0, log=lambda _line: None
    )
    assert record["refused"] == framing.UNSCANNABLE
    assert record["scanned"] == len(framing.WIDTH_LADDER)


def test_the_leg_raises_where_an_adopted_framing_would_read_lower(monkeypatch, tmp_path) -> None:
    """The abort, reached the only way it can be: with the decision itself wrong."""
    stub_screen(monkeypatch)
    monkeypatch.setattr(
        framing, "decide", lambda original, candidates, margin: (candidates[0], None)
    )
    scorer = Scorer({(1.0, 0.0, 0.0): 0.90}, fallback=0.10)
    with pytest.raises(framing.MonotonicityViolated):
        framing.refine(
            [location()], directory=tmp_path, scorer=scorer, margin=2.0, log=lambda _line: None
        )


def test_the_log_is_resumable_and_a_torn_tail_is_repaired(tmp_path) -> None:
    path = framing.log_path(tmp_path)
    framing.append(path, {"schema": 1, "key": "a", "adopted": True})
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write('{"schema": 1, "key": "b", "ado')
    done = framing.completed(path, log=lambda _line: None)
    assert sorted(done) == ["a"]
    assert path.read_text(encoding="utf-8").endswith("\n")


# --------------------------------------------------------------------------- #
# The price.
# --------------------------------------------------------------------------- #
def test_the_price_is_aggregates_and_nothing_that_grows_with_the_locations() -> None:
    """The pass record is tracked, so what lands in it may not be a row per location."""
    made = [
        {
            "key": f"k{index}",
            "adopted": index % 2 == 0,
            "refused": None if index % 2 == 0 else framing.BELOW_MARGIN,
            "margin": 2.0,
            "gain": 1.0 * index,
            "gain_p_ge4": 0.1 * index,
            "width_scale": 1.414 if index % 2 == 0 else 1.0,
            "slug": "w1.414_xm" if index % 2 == 0 else framing.UNMOVED,
            "scanned": 7,
            "seconds": 0.5,
            "original": {"p_ge4": 0.2},
            "best": {"p_ge4": 0.2 + 0.1 * index},
            "sidecar": {"p_ge4": 0.2},
        }
        for index in range(6)
    ]
    price = framing.price(made)
    assert price["locations"] == 6
    assert price["adopted"] == 3
    assert price["adopted_share"] == 0.5
    assert price["frames"] == 42
    assert price["chosen_width"] == {"1.414": 3}
    assert price["chosen_move"] == {"xm": 3}
    assert price["gain"]["n"] == 6
    assert price["gain_adopted"]["n"] == 3
    assert price["sidecar_agreement"] == {
        "compared": 6,
        "exact": 6,
        "max_abs_delta_p_ge4": 0.0,
        "mean_abs_delta_p_ge4": 0.0,
    }
    assert all(not isinstance(value, list) or len(value) < 10 for value in price.values())
