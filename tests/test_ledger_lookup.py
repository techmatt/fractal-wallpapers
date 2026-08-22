"""Where a walk ledger is allowed to sit, and why the union looks rather than searches.

The union used to `rglob` for `walk.jsonl` under every root it was given. That is
a walk of the whole regenerable tree — which is overwhelmingly `views/`, `fields/`
and `tiles/` — to find a few dozen small text files, and a harvest paid it three
times before its first batch: 734.6 s over run10's own tiers against 0.08 s for a
lookup. The lookup is only correct because a walk's run directory is a top-level
name of the tree, so that rule is now enforced at the writer instead of assumed at
the reader, and both halves are pinned here.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers import paths
from fractal_wallpapers.discovery import ledger as ledger_module
from fractal_wallpapers.supply import ledgers


@pytest.fixture
def tree(tmp_path, monkeypatch):
    """A hot tier at `tmp_path`, with no archive configured."""
    monkeypatch.setenv(paths.HOT_ROOT_VARIABLE, str(tmp_path))
    monkeypatch.setenv(paths.ARCHIVE_ROOT_VARIABLE, "")
    return tmp_path


def make_ledger(directory) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / ledgers.LEDGER_NAME).write_text("", encoding="utf-8")


def test_a_ledger_is_looked_up_under_each_run_directory(tree) -> None:
    make_ledger(tree / "harvest_run3")
    make_ledger(tree / "walk_demo")
    (tree / "tiles" / "384x216ss1" / "0000").mkdir(parents=True)
    found = [paths.tracked_name(path) for path in ledgers.ledger_paths()]
    assert found == [
        f"{paths.ARTIFACTS_NAME}/harvest_run3/{ledgers.LEDGER_NAME}",
        f"{paths.ARTIFACTS_NAME}/walk_demo/{ledgers.LEDGER_NAME}",
    ]


def test_a_named_root_means_the_same_ledgers_as_the_default_does(tree) -> None:
    """The two spellings a caller has: `--ledgers <the tree>` and `--harvest <one
    run>`. Neither may see a different population from the other."""
    make_ledger(tree / "harvest_run3")
    whole = [paths.tracked_name(p) for p in ledgers.ledger_paths(root=tree)]
    assert whole == [paths.tracked_name(p) for p in ledgers.ledger_paths()]
    one = [paths.tracked_name(p) for p in ledgers.ledger_paths(root=tree / "harvest_run3")]
    assert one == whole


def test_this_runs_own_ledger_is_excluded_by_the_file_and_not_by_the_spelling(tree) -> None:
    """Two spellings of one file is how a run ends up seeded with its own finds."""
    make_ledger(tree / "harvest_run3")
    own = tree / "harvest_run3" / ledgers.LEDGER_NAME
    assert ledgers.ledger_paths(exclude=own) == []
    assert ledgers.ledger_paths(exclude=tree / "." / "harvest_run3" / ledgers.LEDGER_NAME) == []


def test_a_root_that_is_not_there_is_no_ledgers_rather_than_a_crash(tree) -> None:
    assert ledgers.ledger_paths(root=tree / "never_ran") == []


def test_a_walk_refuses_to_write_its_ledger_below_a_top_level_name(tree) -> None:
    """The failure this prevents is the quiet kind: a run under `artifacts/studies/
    tonight/` writes a perfectly good ledger that no census, saturation memory or
    novelty pool ever reads again, and the supply it found simply is not there."""
    nested = tree / "studies" / "tonight"
    nested.mkdir(parents=True)
    with pytest.raises(ValueError) as refusal:
        ledger_module.Ledger(nested / ledgers.LEDGER_NAME)
    said = str(refusal.value)
    assert "top-level name" in said
    assert "studies_tonight" in said, "the refusal names the out-dir that would work"
    assert not (nested / ledgers.LEDGER_NAME).exists()


def test_a_ledger_outside_the_tree_is_nobody_here_s_business(tmp_path) -> None:
    """Every test's `tmp_path` and every one-off elsewhere. The rule is about the
    shape of the regenerable tree, not about where a file may be written."""
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    with ledger_module.Ledger(deep / ledgers.LEDGER_NAME) as ledger:
        ledger.write("candidate")
    assert (deep / ledgers.LEDGER_NAME).is_file()


def test_the_writer_and_the_reader_agree_about_the_file_name() -> None:
    """The lookup is by name at a fixed depth, so the two modules agreeing about
    the name is the whole of why anything is found."""
    assert ledgers.LEDGER_NAME is ledger_module.LEDGER_NAME
