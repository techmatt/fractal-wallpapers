"""The second cross-regime bar: what it draws, what it counts, what it refuses.

The claims here are the ones a docstring cannot make stick. A labelled location
never enters the draw, because the candidate trained on it at all three regimes.
The draw is a seeded function of the population and nothing else. A gate is the
number its owning module holds rather than a fourth copy of it. A flip is
symmetric and pooled the way the bar says it is pooled. And a rehearsal — a
prefix of the draw, rendered to price the engine — cannot be judged as if it were
the study.
"""

from __future__ import annotations

import json
import re

import pytest

from fractal_wallpapers.models import regime_flips
from fractal_wallpapers.models import tiles as tile_module

pytest.importorskip("numpy")

#: A drive letter or a home directory, the two ways a record names one machine.
#: The lookbehind keeps a URL scheme from reading as a drive letter.
ABSOLUTE_PATH = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z]:[\/]|/(?:home|Users|mnt)/")


def stock(count: int, partition: str = "mandelbrot", offset: int = 0) -> list[dict]:
    """`count` sidecar rows spread over the score bands."""
    rows = []
    for index in range(count):
        score = ((index % 10) + 0.5) / 10.0
        rows.append(
            {
                "head": "location",
                "key": json.dumps([partition, index + offset]),
                "partition": partition,
                "family": {"kind": "mandelbrot", "degree": 2},
                "viewport": {"center_re": "0", "center_im": "0", "width": str(index + 1)},
                "maxiter": 1000,
                "view": f"{partition}{index + offset:05d}.jpg",
                "p_ge3": score,
            }
        )
    return rows


#: A read that clears every acting gate, and one that clears none of them.
#:
#: These used to be 0.9 and 0.1, and 0.1 stopped being "below every gate" on
#: 2026-08-20, when the location flip restated the junk floor to 0.100. A test
#: that writes a probability meaning *this side of the cut* has to sit far enough
#: outside the cuts that a restatement cannot land between it and them —
#: `test_the_two_reads_this_file_is_written_in_sit_outside_every_gate` is what
#: keeps that true rather than the comment.
ABOVE, BELOW = 0.99, 0.0


def test_the_two_reads_this_file_is_written_in_sit_outside_every_gate() -> None:
    """Every fixture below means "passes" or "fails" — at all three cuts at once."""
    for gate in regime_flips.gates():
        assert BELOW < gate["edge"] <= ABOVE, f"{gate['gate']} has moved between the two"


def read_row(key: str, partition: str, reads: dict, band: int = 0) -> dict:
    return {
        "schema": regime_flips.SCHEMA,
        "head": "location",
        "key": key,
        "partition": partition,
        "family": {"kind": "mandelbrot", "degree": 2},
        "viewport": {"center_re": "0", "center_im": "0", "width": "1"},
        "maxiter": 1000,
        "stock_p_ge3": 0.5,
        "band": band,
        "reads": reads,
    }


def flat(canonical: float, cheap: float) -> dict:
    """One head's reads: the same pair of probabilities at every cutpoint."""
    names = [regime_flips.regime_acceptance.spelled(r) for r in tile_module.BUILT_REGIMES]
    return {
        names[0]: {"p_ge2": canonical, "p_ge3": canonical, "p_ge4": canonical},
        names[1]: {"p_ge2": cheap, "p_ge3": cheap, "p_ge4": cheap},
        names[2]: {"p_ge2": cheap, "p_ge3": cheap, "p_ge4": cheap},
    }


def candidates(canonical: float, cheap: float) -> dict:
    """The whole band reading the same way, so a test says one thing at a time."""
    return {run: flat(canonical, cheap) for run in regime_flips.CANDIDATE_RUNS}


def test_a_labelled_location_never_enters_the_draw(monkeypatch) -> None:
    """The candidate saw those at all three regimes; their agreement proves nothing."""
    from fractal_wallpapers.curation import intake
    from fractal_wallpapers.labeling import store

    rows = stock(10)
    monkeypatch.setattr(intake, "read_scores", lambda: {row["key"]: row for row in rows})
    # The store keys on the identity tuple and the sidecar on the JSON text of the
    # same tuple, which is the join the exclusion has to survive.
    labelled = [json.loads(rows[index]["key"]) for index in (0, 3, 7)]
    monkeypatch.setattr(
        store,
        "resolved",
        lambda: type("R", (), {"current": {tuple(key): {} for key in labelled}})(),
    )
    kept, census = regime_flips.eligible()
    assert census["labelled_and_excluded"] == 3
    assert census["eligible"] == 7
    assert all(json.loads(row["key"])[1] not in (0, 3, 7) for row in kept)


def test_the_draw_is_a_function_of_the_population_and_the_seed() -> None:
    """Same rows, same seed, same draw — in the same order, twice."""
    rows = stock(200) + stock(200, "phoenix", offset=1000)
    once = regime_flips.draw(rows, 60, seed=0)
    twice = regime_flips.draw(list(reversed(rows)), 60, seed=0)
    assert [row["key"] for row in once] == [row["key"] for row in twice]
    assert regime_flips.draw(rows, 60, seed=1) != once


def test_the_draw_spends_a_thin_cells_quota_on_the_cells_that_can_fill_it() -> None:
    """A thin partition contributes everything it has; the draw is not short."""
    rows = stock(400) + stock(7, "phoenix", offset=1000)
    drawn = regime_flips.draw(rows, 100, seed=0)
    assert len(drawn) == 100
    assert sum(1 for row in drawn if row["partition"] == "phoenix") == 7


def test_every_gate_is_the_number_its_own_module_holds() -> None:
    """One number, one place — a bar that retyped them would be a fourth opinion."""
    from fractal_wallpapers.curation import floors
    from fractal_wallpapers.supply import currency

    edges = {gate["gate"]: gate["edge"] for gate in regime_flips.gates()}
    assert edges == {
        "junk floor": floors.JUNK_FLOOR,
        "good floor": currency.GOOD_FLOOR,
        "great cut": currency.GREAT_CUT,
    }
    fields = {gate["gate"]: gate["field"] for gate in regime_flips.gates()}
    assert fields["great cut"] == "p_ge4", "the great cut reads the top class, not P(>=3)"


def test_the_bar_gates_the_frozen_seed_and_says_so() -> None:
    """A second read that re-picked a seed would choose on the arm that gates it."""
    bar = regime_flips.preregister()
    assert bar["runs"]["gated_candidate"] == regime_flips.STAGED_RUN
    assert bar["arms"]["primary"]["gated"] and bar["arms"]["guard"]["gated"]
    assert len(bar["arms"]["guard"]["cells"]) == 6
    assert "median" in bar["runs"]["why_this_seed"]


def test_the_bar_declares_its_size_and_its_seed_before_any_number() -> None:
    population = regime_flips.preregister()["population"]
    assert population["size"] == regime_flips.DRAW_SIZE
    assert population["seed"] == regime_flips.DRAW_SEED
    assert population["power"]["resolves"] is True


def test_a_flip_is_symmetric_and_pools_as_three_decisions_a_location(tmp_path) -> None:
    """One location that turns off and one that turns on are two flips, not one."""
    names = [regime_flips.regime_acceptance.spelled(r) for r in tile_module.BUILT_REGIMES]
    rows = []
    # Turns off at both cheap regimes, at all three gates.
    rows.append(
        read_row("a", "mandelbrot", {"seed0": flat(ABOVE, BELOW), **candidates(ABOVE, ABOVE)})
    )
    # Turns on at both cheap regimes, at all three gates.
    rows.append(
        read_row("b", "mandelbrot", {"seed0": flat(BELOW, ABOVE), **candidates(BELOW, BELOW)})
    )
    path = tmp_path / "reads.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8", newline="\n")
    read = regime_flips.read_reads(path)
    for gate in regime_flips.gates():
        column = regime_flips._flips(read, "seed0", names[1], names[0], gate)
        assert list(column) == [1.0, 1.0], "a decision that turns on is a flip too"
        direction = regime_flips._direction(read, "seed0", names[1], names[0], gate)
        assert direction == {"turned_off": 1, "turned_on": 1}


def test_a_rehearsal_cannot_be_judged_as_if_it_were_the_study(tmp_path, monkeypatch) -> None:
    """A prefix rendered to price the engine is a measurement, not a smaller bar."""
    bar = regime_flips.preregister()
    prereg = tmp_path / "flip_prereg.json"
    prereg.write_text(json.dumps(bar), encoding="utf-8", newline="\n")
    monkeypatch.setattr(regime_flips, "prereg_path", lambda head=regime_flips.HEAD: prereg)
    reads = tmp_path / "reads.jsonl"
    reads.write_text(
        json.dumps(
            read_row("a", "mandelbrot", {"seed0": flat(ABOVE, BELOW), **candidates(ABOVE, ABOVE)})
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    with pytest.raises(regime_flips.FlipError, match="not a smaller study"):
        regime_flips.read(path=reads)


def test_the_read_gates_on_both_arms_and_names_the_cell_that_failed(tmp_path, monkeypatch) -> None:
    """A candidate that is worse at one gate fails the guard, whatever the pooled rate."""
    bar = regime_flips.preregister()
    bar["population"]["size"] = 40
    prereg = tmp_path / "flip_prereg.json"
    prereg.write_text(json.dumps(bar), encoding="utf-8", newline="\n")
    monkeypatch.setattr(regime_flips, "prereg_path", lambda head=regime_flips.HEAD: prereg)

    rows = []
    for index in range(40):
        # The incumbent flips at every gate on the first thirty; the candidate on
        # none of them. A clean improvement everywhere.
        incumbent = flat(ABOVE, BELOW) if index < 30 else flat(ABOVE, ABOVE)
        rows.append(
            read_row(f"row{index}", "mandelbrot", {"seed0": incumbent, **candidates(ABOVE, ABOVE)})
        )
    reads = tmp_path / "reads.jsonl"
    reads.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8", newline="\n"
    )
    report = regime_flips.read(path=reads)
    assert report["verdict"] == "PASS"
    assert report["failed_cells"] == []
    for entry in report["primary"].values():
        assert entry["incumbent"] == pytest.approx(0.75)
        assert entry["candidate"] == 0.0
        assert entry["verdict"] == "IMPROVED"

    # Now hand the candidate the flips instead. Same numbers, other direction.
    flipped = []
    for index in range(40):
        cheap = BELOW if index < 30 else ABOVE
        flipped.append(
            read_row(
                f"row{index}",
                "mandelbrot",
                {"seed0": flat(ABOVE, ABOVE), **candidates(0.9, cheap)},
            )
        )
    reads.write_text(
        "".join(json.dumps(row) + "\n" for row in flipped), encoding="utf-8", newline="\n"
    )
    worse = regime_flips.read(path=reads)
    assert worse["verdict"] == "FAIL"
    assert len(worse["failed_cells"]) == 8, "two primary regimes and six guard cells"


def test_the_canonical_arm_reads_the_picture_the_sidecar_scored() -> None:
    """A deploy recipe that moved would make the strata and the arm two pictures."""
    rows = [{"key": "a", "view": "beef.jpg"}]
    with pytest.raises(regime_flips.FlipError, match="two different pictures"):
        regime_flips._check_canonical_names(rows, [tile_module.cache_root() / "cafe.jpg"])


def test_no_record_this_study_writes_names_a_machine() -> None:
    """A verdict git keeps must not say `C:` — it means nothing on the next machine.

    Scoped to the records this study writes, and it fails on the file rather than
    on the code, because the bug was a value written by a run, not a literal.
    Thirty-one older tracked records carry one; that is a migration and a
    decision, and this guard deliberately does not pretend to be it.
    """
    from fractal_wallpapers.models import regime_acceptance, ship

    written = (
        regime_flips.acceptance_path(),
        regime_acceptance.acceptance_path(),
        ship.candidate_record_path(),
    )
    offenders = [
        path.name
        for path in written
        if path.is_file() and ABSOLUTE_PATH.search(path.read_text(encoding="utf-8"))
    ]
    assert not offenders, (
        f"{offenders} name an absolute path. Write one through "
        f"`fractal_wallpapers.paths.tracked_name`."
    )


def test_the_two_bars_write_different_records() -> None:
    """One candidate, two populations, two verdicts that must not overwrite each other."""
    from fractal_wallpapers.models import regime_acceptance

    assert regime_flips.prereg_path() != regime_acceptance.prereg_path()
    assert regime_flips.acceptance_path() != regime_acceptance.acceptance_path()
