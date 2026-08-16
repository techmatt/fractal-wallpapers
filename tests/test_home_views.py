"""Home views: one owner, and rows that were derived rather than chosen.

Where a family is framed when nothing says otherwise lives in the engine, in
`Family::home_view`, and nowhere else. It used to live in two places — the
engine's table and a literal `{0, 0, 3.0}` in the discovery layer — and the two
agreed right up until the day the engine's Phoenix row moved and the walk's did
not, at which point a phoenix walk root framed 66% of its own set with both
lobes cut.

So the guard here is in two halves. **No framing literal survives on the Python
side**, which is a source check and needs no engine; and **a walk root comes home
to exactly the engine's row**, which is the property the source check exists to
protect and needs the real binary to state.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from fractal_wallpapers import engine
from fractal_wallpapers.discovery import walk as walk_module
from fractal_wallpapers.discovery.walk import Walk

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The Python halves that choose where a walk starts. If a framing constant ever
#: comes back, it comes back in one of these.
STEERING = ("src/fractal_wallpapers/discovery", "src/fractal_wallpapers/supply")

#: A viewport key given a literal number — `"width": "3.0"` and its relatives.
#: Anything computed, passed through, or read from a record is not a match.
FRAMING_LITERAL = re.compile(r'"(?:center_re|center_im|width)"\s*:\s*"?[-0-9.]')

FAMILIES = [
    ("mandelbrot", {"kind": "mandelbrot"}),
    ("multibrot3", {"kind": "multibrot", "degree": 3}),
    ("multibrot4", {"kind": "multibrot", "degree": 4}),
    ("multibrot5", {"kind": "multibrot", "degree": 5}),
    ("julia", {"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]}),
    ("phoenix", {"kind": "phoenix"}),
]


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


# --------------------------------------------------------------------------- #
# one owner
# --------------------------------------------------------------------------- #


def test_the_steering_half_holds_no_framing_literal_of_its_own() -> None:
    """The unification, as a property of the source rather than of a run."""
    offenders = []
    for directory in STEERING:
        for path in sorted((REPO_ROOT / directory).rglob("*.py")):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if FRAMING_LITERAL.search(line):
                    offenders.append(f"{path.relative_to(REPO_ROOT)}:{number}: {line.strip()}")
    assert not offenders, "framing belongs to the engine's home table:\n" + "\n".join(offenders)


def test_the_discovery_layer_no_longer_answers_the_framing_question() -> None:
    """The duplicate is gone, not merely unused: a function still exported is a
    function something imports again."""
    assert not hasattr(walk_module, "home_view")
    assert "home_view" not in walk_module.__all__


# --------------------------------------------------------------------------- #
# the table itself
# --------------------------------------------------------------------------- #


@needs_engine
def test_every_family_reports_a_home_view_with_its_derivation() -> None:
    """The engine answers with the frame *and* what the frame is made of, so a
    reader never has to open the engine's source to see what a row rests on."""
    for name, family in FAMILIES:
        report = engine.run("home-view", {"schema": 1, "family": family})
        assert set(report["viewport"]) == {"center_re", "center_im", "width"}, name
        assert report["rule"] == {
            "grid": 4001,
            "half_span": 2.5,
            "cap": 4000,
            "margin": 0.10,
            "aspect": 16 / 9,
        }, name
        if name == "julia":
            assert report["derived"] is False and report["exception"], "the stated exception"
        else:
            assert report["derived"] is True and report["extent"], name


@needs_engine
def test_the_derived_rows_are_the_ones_the_rule_lands_on() -> None:
    """The five rows, written down once. Not a restatement of the engine's
    constants — there are none — but of what the one rule produces from five
    measured sets, so a change to the rule cannot pass as a change to nothing."""
    assert {name: tuple(engine.home_view(family).values()) for name, family in FAMILIES} == {
        "mandelbrot": ("-0.77", "0.0", "4.4"),
        "multibrot3": ("0.0", "0.0", "5.2"),
        "multibrot4": ("-0.23", "0.0", "4.4"),
        "multibrot5": ("0.0", "0.0", "3.6"),
        "julia": ("0.0", "0.0", "3.0"),
        "phoenix": ("0.04", "0.0", "5.0"),
    }


@needs_engine
def test_every_derived_frame_holds_the_set_it_was_derived_from() -> None:
    """Containment, read off the extent the engine reports beside each row. The
    recurrence is re-measured on the Rust side; this is the arithmetic half of
    the same claim, and it is here because the margin is a shared constant and a
    reader of the Python half should be able to see it hold."""
    for name, family in FAMILIES:
        report = engine.run("home-view", {"schema": 1, "family": family})
        if not report["derived"]:
            continue
        extent, view = report["extent"], report["viewport"]
        width = float(view["width"])
        half_height = width * 9 / 16 / 2
        centre_im = float(view["center_im"])
        centre_re = float(view["center_re"])
        assert extent["re"][0] > centre_re - width / 2, name
        assert extent["re"][1] < centre_re + width / 2, name
        tallest = max(abs(value - centre_im) for value in extent["im"])
        assert tallest < half_height, name
        # The margin is what the frame was bought for, so it has to be real on
        # the axis that decided it rather than a rounding.
        assert tallest < half_height / (1 + report["rule"]["margin"] / 2), name


@needs_engine
def test_asking_twice_costs_one_engine_call() -> None:
    """A walk asks per root and a refill per draw — thousands of times for a
    handful of distinct families."""
    engine.home_view({"kind": "phoenix"})
    before = engine._home_view.cache_info()
    engine.home_view({"kind": "phoenix"})
    assert engine._home_view.cache_info().hits == before.hits + 1


# --------------------------------------------------------------------------- #
# and what the walk does with it
# --------------------------------------------------------------------------- #


@needs_engine
def test_a_walk_root_comes_home_to_the_engine_s_row(tmp_path) -> None:
    """The property the whole unification is for: a root given no view and a
    viewport-less render are the same frame, family by family."""
    run = Walk(out_dir=tmp_path / "walk", seed=0)
    for name, family in FAMILIES:
        node = run.add_root(family, source="test", provenance={})
        home = engine.home_view(family)
        assert (node["center_re"], node["center_im"], node["width"]) == (
            home["center_re"],
            home["center_im"],
            home["width"],
        ), name


@needs_engine
def test_a_phoenix_root_now_frames_the_whole_set(tmp_path) -> None:
    """The one deliberate change in behaviour. A phoenix root used to start at
    three units across, which at 16:9 is 1.69 tall against a set 2.54 tall — 66%
    of it, both lobes cut. It now starts at the frame that holds the set."""
    run = Walk(out_dir=tmp_path / "walk", seed=0)
    run.seed_from_phoenix_pool(limit=2)
    assert run.frontier, "the pool seeded nothing"
    for node in run.frontier:
        assert node["width"] == "5.0"
        assert float(node["width"]) * 9 / 16 > 2.5425, "taller than the measured set"


@needs_engine
def test_a_julia_root_keeps_its_whole_plane_semantics(tmp_path) -> None:
    """Reading the table did not move the family the table frames by exception:
    the class of Julia set worth finding is composed at whole-set framings, and
    the walk still starts there."""
    run = Walk(out_dir=tmp_path / "walk", seed=0)
    run.seed_from_julia_pool(limit=2)
    assert run.frontier
    for node in run.frontier:
        assert (node["center_re"], node["center_im"], node["width"]) == ("0.0", "0.0", "3.0")
