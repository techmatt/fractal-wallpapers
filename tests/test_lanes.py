"""The two lines the lane prints about tests it did not run.

Both exist for one reason: a guard that stops running silently is a guard nobody
notices is gone. The slow lane says how many it held back; this file guards the
other half, which is a module that never got collected at all.

A module-level `pytest.importorskip` is not a skip of that module's tests — it
stops the module being imported, so its tests are missing from the collected
total rather than counted and skipped. Thirteen modules here gate that way on
`torch` or `PIL`. On an interpreter without them the lane is 65 fast tests short
and says nothing, and a reading taken there goes into the log looking like every
other reading.

The third thing this file owns, since 2026-09-15, is **the extras themselves**,
because the two ways a lane meets one are different faults. A module-level import
is visible in the source and aborts *collection* — one unguarded `from PIL import
Image` took every CI `check` job down for four days without running a test — so a
sweep of the tree holds every module to guarding it. A **call-time** import is not
visible in any test file at all: sixteen modules under `src/` carry a lazy `import
torch` inside a function body, so the extra arrives through production code the
test never mentions, and only catching it at the call can cover that.
"""

from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from _pytest.outcomes import Skipped

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
# An extra this install does not have.
# --------------------------------------------------------------------------- #
#: The distributions `pip install -e ".[dev]"` buys, read off `pyproject.toml`
#: rather than typed here — the guard below is about the difference between that
#: install and `.[dev,models]`, and a difference restated in two places is one
#: that stops being a difference without anybody noticing.
def _dev_distributions() -> set[str]:
    import tomllib

    from fractal_wallpapers.paths import repo_root

    pyproject = tomllib.loads((repo_root() / "pyproject.toml").read_text(encoding="utf-8"))
    rows = pyproject["project"]["optional-dependencies"]["dev"]
    return {re.split(r"[<>=!~\[ ]", row, maxsplit=1)[0].strip().lower() for row in rows}


#: Import name to the distribution that ships it, for the few that differ.
DISTRIBUTION_OF = {"PIL": "pillow"}


def _must_be_guarded() -> set[str]:
    """Optional dependencies a `.[dev]` lane will NOT have, by import name."""
    from fractal_wallpapers.cli import EXTRA_FOR

    dev = _dev_distributions()
    return {name for name in EXTRA_FOR if DISTRIBUTION_OF.get(name, name).lower() not in dev}


def unguarded_module_level(paths, wanted: set[str]) -> list[str]:
    """`["<file> imports <module>", …]` for every module-level import of `wanted`
    that no `pytest.importorskip` in the same file covers.

    Module level only: an import inside a function body is the other fault
    entirely and `conftest.pytest_runtest_call` is what answers for it. The cover
    has to name the same top-level module — an `importorskip("numpy")` above an
    `import torch` is not a guard, and reading any `importorskip` as cover for any
    import is the way this sweep would go quiet.
    """
    offenders: list[str] = []
    for path in paths:
        tree = ast.parse(Path(path).read_text(encoding="utf-8"))
        asked = {
            name.partition(".")[0]
            for node in tree.body
            if isinstance(node, ast.Import | ast.ImportFrom)
            for name in (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
            )
        }
        covered = {
            str(node.args[0].value).partition(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "importorskip"
            and node.args
            and isinstance(node.args[0], ast.Constant)
        }
        offenders.extend(
            f"{Path(path).name} imports {name}" for name in sorted(asked & wanted - covered)
        )
    return offenders


def test_a_module_level_import_of_a_missing_extra_is_guarded() -> None:
    """★ **A module that imports an extra `.[dev]` lacks aborts the WHOLE lane.**

    Not its own tests — everything. `pytest` reports an uncollectable module as a
    collection error and stops, so one unguarded `from PIL import Image` at module
    level took every `check` job on CI from 2026-09-11 to 2026-09-15 down in under
    four seconds without executing a single test, and the badge said "failing"
    while the tree was green on the machine it was written on.

    `pytest.importorskip` at module level is the fix and thirteen modules already
    use it. This is what stops the fourteenth being a remembered step: the list
    of what must be guarded is `cli.EXTRA_FOR` less whatever `dev` installs, so
    moving a distribution into `dev` — which is what closed the `PIL` case — takes
    it off this guard by itself, with nothing here to edit.
    """
    guarded_wanted = _must_be_guarded()
    assert guarded_wanted, "nothing is outside `dev`, so this guard is asserting nothing"

    offenders = unguarded_module_level(Path(__file__).parent.glob("test_*.py"), guarded_wanted)

    assert offenders == [], (
        "a module-level import of an extra `.[dev]` does not have aborts collection for "
        f"the whole lane, not just this file: {offenders}. Put "
        "`pytest.importorskip(<name>)` above the import."
    )


def test_the_sweep_catches_an_unguarded_import_and_passes_a_guarded_one(tmp_path) -> None:
    """★ **The sweep above asserts an empty list, which is what a broken sweep also
    returns.** So it is run here over two files written to be caught and not caught:
    without this, deleting the body of [`unguarded_module_level`] leaves a green
    lane and no module-level guard at all.
    """
    (tmp_path / "test_bare.py").write_text("from torch import nn\n", encoding="utf-8")
    (tmp_path / "test_guarded.py").write_text(
        'import pytest\n\npytest.importorskip("torch")\n\nimport torch\n', encoding="utf-8"
    )
    (tmp_path / "test_other_extra.py").write_text(
        'import pytest\n\npytest.importorskip("numpy")\n\nimport torch\n', encoding="utf-8"
    )

    caught = unguarded_module_level(sorted(tmp_path.glob("test_*.py")), {"torch"})

    assert [row.split(" ")[0] for row in caught] == ["test_bare.py", "test_other_extra.py"], (
        f"one bare import caught, one guarded import left alone, and an importorskip "
        f"for a DIFFERENT module not counted as cover: {caught}"
    )


def test_the_extras_this_interpreter_lacks_are_resolved_without_importing_them() -> None:
    """`find_spec` and never an import: resolving the set must not cost the 3.9 s
    of loading timm that the thing it is deciding about would have cost."""
    source = inspect.getsource(conftest._absent_extras)

    assert "find_spec" in source
    assert "import_module" not in source, "that would import the extra to ask whether it is there"


def test_a_test_that_reaches_a_missing_extra_skips_rather_than_failing(monkeypatch) -> None:
    """The call-time half, which no static guard can reach — sixteen modules under
    `src/` import torch inside a function body."""
    monkeypatch.setattr(conftest, "ABSENT_EXTRAS", frozenset({"torch"}))
    monkeypatch.setattr(conftest, "SKIPPED_IN_CALL", {})

    hook = conftest.pytest_runtest_call(SimpleNamespace(nodeid="tests/test_a.py::test_b"))
    next(hook)
    with pytest.raises(BaseException) as outcome:
        hook.throw(ModuleNotFoundError("No module named 'torch'", name="torch"))

    assert isinstance(outcome.value, Skipped), outcome.value
    assert conftest.SKIPPED_IN_CALL == {"tests/test_a.py::test_b": "torch"}


def test_a_missing_module_that_is_not_an_extra_keeps_its_traceback(monkeypatch) -> None:
    """★ The half that stops this hiding a real fault. A typo'd import and a module
    somebody deleted are both `ModuleNotFoundError`, and turning either into a skip
    would be a guard that stopped running and said it was fine."""
    monkeypatch.setattr(conftest, "ABSENT_EXTRAS", frozenset({"torch"}))

    hook = conftest.pytest_runtest_call(SimpleNamespace(nodeid="tests/test_a.py::test_b"))
    next(hook)
    with pytest.raises(ModuleNotFoundError) as refusal:
        hook.throw(
            ModuleNotFoundError(
                "No module named 'fractal_wallpapers.curatoin'",
                name="fractal_wallpapers.curatoin",
            )
        )

    assert "curatoin" in str(refusal.value)


def test_the_lane_says_how_many_tests_reached_a_missing_extra(monkeypatch, pytestconfig) -> None:
    """Same argument as the deselect line and the NOT COLLECTED line: a skip is a
    guard that did not run, and a lane that went quiet about it is the fault."""
    monkeypatch.setattr(conftest, "SKIPPED_IN_CALL", {"a::b": "torch", "c::d": "torch"})

    said = [line for line in _summarise(pytestconfig) if "REACHED A MISSING EXTRA" in line]

    assert len(said) == 1
    assert "2 tests REACHED A MISSING EXTRA" in said[0]
    assert "no torch" in said[0]


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
