"""The two lines the lane prints about tests it did not run.

Both exist for one reason: a guard that stops running silently is a guard nobody
notices is gone. The slow lane says how many it held back; this file guards the
other half, which is a module that never got collected at all.

A module-level `pytest.importorskip` is not a skip of that module's tests — it
stops the module being imported, so its tests are missing from the collected
total rather than counted and skipped. Thirteen modules here gate that way on
`torch` or `PIL`, both of which live in the `models` extra. On an interpreter
without them the lane is 65 fast tests short and says nothing, and a reading
taken there goes into the log looking like every other reading.
"""

from __future__ import annotations

import pytest

import conftest


class _Reporter:
    """The half of `TerminalReporter` the summary hook touches."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def write_sep(self, _sep, title, **_style) -> None:
        self.lines.append(title)


@pytest.fixture
def no_modules_skipped(monkeypatch):
    """`SKIPPED_WHOLE` empty, whatever this interpreter actually did on the way in."""
    monkeypatch.setattr(conftest, "SKIPPED_WHOLE", {})


def _summarise(config) -> list[str]:
    reporter = _Reporter()
    conftest.pytest_terminal_summary(reporter, 0, config)
    return reporter.lines


def test_the_phrase_the_module_name_is_read_out_of_is_pytests_own(no_modules_skipped) -> None:
    """Pinned against the real refusal rather than a copy of its wording.

    `WANTED` reads a module name out of a message pytest writes, so a rewording
    upstream would quietly turn every announcement into the raw text. Asking
    `importorskip` itself is what stops this test passing on a string we wrote.
    """
    with pytest.raises(BaseException) as refusal:
        pytest.importorskip("no_such_module_at_all")

    found = conftest.WANTED.search(str(refusal.value))

    assert found is not None, "pytest no longer says `could not import '<name>'`"
    assert found.group(1) == "no_such_module_at_all"


def test_a_module_that_skipped_whole_is_recorded_with_the_import_it_wanted(
    no_modules_skipped,
) -> None:
    report = pytest.CollectReport(
        nodeid="tests/test_something.py",
        outcome="skipped",
        longrepr=("tests/test_something.py", 11, "Skipped: could not import 'torch': nope"),
        result=[],
    )

    conftest.pytest_collectreport(report)

    assert conftest.SKIPPED_WHOLE == {"tests/test_something.py": "torch"}


def test_a_collected_module_and_a_skipped_test_are_both_left_alone(no_modules_skipped) -> None:
    """Only a *module* that skipped counts. A skipped test was collected and is
    already in the total, and a directory that skipped holds no count of its own."""
    for nodeid, outcome in (("tests/test_a.py", "passed"), ("tests", "skipped")):
        conftest.pytest_collectreport(
            pytest.CollectReport(nodeid=nodeid, outcome=outcome, longrepr=None, result=[])
        )

    assert conftest.SKIPPED_WHOLE == {}


def test_the_lane_says_nothing_when_every_module_was_collected(
    no_modules_skipped, pytestconfig
) -> None:
    """The negative half, so the assertion below is not passing on any line at all."""
    assert not [line for line in _summarise(pytestconfig) if "NOT COLLECTED" in line]


def test_a_short_lane_says_so_and_names_what_is_missing(monkeypatch, pytestconfig) -> None:
    """The count and the reason both, because the count alone reads as a nuisance
    rather than as the figure below it being incomparable."""
    monkeypatch.setattr(
        conftest,
        "SKIPPED_WHOLE",
        {"tests/test_a.py": "torch", "tests/test_b.py": "PIL", "tests/test_c.py": "torch"},
    )

    said = [line for line in _summarise(pytestconfig) if "NOT COLLECTED" in line]

    assert len(said) == 1
    assert "3 test modules NOT COLLECTED" in said[0]
    assert "no PIL, torch" in said[0], "named once each, sorted, not once per module"
    assert "dev,models" in said[0], "the line has to say what the missing extra is"


# --------------------------------------------------------------------------- #
# The session backstop's other half: a leg written onto the live tree.
# --------------------------------------------------------------------------- #
def test_a_leg_that_appeared_during_the_run_is_named(monkeypatch) -> None:
    """The fault it catches leaves a directory behind, so the detector is a
    difference of two listings and not a hash. Named `<where>/<leg>`, because the
    person reading it is about to delete that path."""
    monkeypatch.setattr(
        conftest,
        "live_legs",
        lambda: {"artifacts/curation/runs": ["run9", "r", "earlier"]},
    )

    assert conftest._legs_that_appeared({"artifacts/curation/runs": ["run9"]}) == [
        "artifacts/curation/runs/earlier",
        "artifacts/curation/runs/r",
    ]
    assert conftest._legs_that_appeared({"artifacts/curation/runs": ["run9", "r", "earlier"]}) == []


def test_a_leg_that_went_away_during_the_run_is_not_a_fault() -> None:
    """One direction only. A test that deletes from the live tree is a different
    fault and the tracked-record half already covers the records; a sweep run by
    hand between two lanes is not a fault at all, and reporting it would train
    everybody to ignore the line."""
    # Against the real listing rather than a stub, so this cannot pass on a mock
    # that happens to return nothing: every name is there plus one that is not.
    before = {
        where: [*names, "a_leg_that_is_not_there"] for where, names in conftest.live_legs().items()
    }
    assert conftest._legs_that_appeared(before) == []


def test_the_live_listing_is_a_fixed_name_and_never_a_walk() -> None:
    """`CLAUDE.md`'s rule: this tree carries four hundred thousand untracked files
    and a recursive walk of it takes minutes. Each entry is a path at a fixed
    depth and the listing is one `scandir` of it."""
    import inspect

    assert conftest.LIVE_LEG_DIRS == (("curation", "runs"),)
    source = inspect.getsource(conftest.live_legs)
    for forbidden in ("rglob", "walk(", "**"):
        assert forbidden not in source, forbidden
    assert "iterdir()" in source
