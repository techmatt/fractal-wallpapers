"""The ledger binding: what a curation reads, and what it refuses to assume.

The failure being pinned here is silent rather than loud. Curation used to read
every `walk.jsonl` under `artifacts/` when no ledger was named, so a release meant
for one harvest's supply would have ranked an earlier harvest's unscored rows
alongside it and printed one funnel over both populations. Nothing raised,
nothing looked wrong, and the numbers were about two different things.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.curation import binding, intake
from fractal_wallpapers.discovery import ledger as ledger_module
from fractal_wallpapers.supply import ledgers as ledger_reader


def candidate(center: str) -> dict:
    return {
        "schema": ledger_module.SCHEMA,
        "kind": "candidate",
        "node_id": center,
        "family": {"kind": "mandelbrot"},
        "viewport": {"center_re": center, "center_im": "0", "width": "0.5"},
        "maxiter": 500,
        "fate": ledger_module.SURVIVED,
        "score": None,
    }


def harvest(root, name: str, centers=("-0.5",)):
    """A harvest run directory, with the ledger a walk would have left in it."""
    path = root / name / ledger_reader.LEDGER_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(candidate(c)) + "\n" for c in centers), encoding="utf-8")
    return path


@pytest.fixture
def artifacts(tmp_path, monkeypatch):
    """An `artifacts/` tree of the test's own, with nothing harvested into it yet."""
    root = tmp_path / "artifacts"
    root.mkdir()
    monkeypatch.setattr(ledger_reader, "ledger_root", lambda: root)
    return root


# --------------------------------------------------------------------------- #
# Nothing defaults to everything.
# --------------------------------------------------------------------------- #
def test_two_ledgers_and_no_binding_is_a_refusal_that_names_both(artifacts) -> None:
    """THE pin. An unbound invocation reading both would have pulled one harvest's
    17,251 unscored rows into another harvest's intake without saying a word."""
    harvest(artifacts, "harvest_run3")
    harvest(artifacts, "run8h")
    with pytest.raises(binding.Unbound) as refusal:
        binding.resolve()
    said = str(refusal.value)
    assert "harvest_run3" in said and "run8h" in said
    assert said.count("--ledger") == 2, "every candidate is listed, not just the count"


def test_the_intake_refuses_the_same_way_rather_than_taking_the_union(artifacts) -> None:
    """The refusal has to sit where the supply is read, not only where it is
    declared: `curate score` and a run's intake reach the union through here."""
    harvest(artifacts, "harvest_run3")
    harvest(artifacts, "run8h")
    with pytest.raises(binding.Unbound):
        intake.gate_survivors()


def test_the_only_ledger_there_is_binds_without_being_named(artifacts) -> None:
    """Choosing between one candidate and nothing is not a guess."""
    only = harvest(artifacts, "harvest_run3")
    assert binding.resolve() == [only]
    assert len(intake.gate_survivors()[0]) == 1


def test_nothing_harvested_says_so_rather_than_returning_an_empty_offer(artifacts) -> None:
    with pytest.raises(binding.Unbound, match="harvest"):
        binding.resolve()


# --------------------------------------------------------------------------- #
# How a binding is declared.
# --------------------------------------------------------------------------- #
def test_a_harvest_directory_is_a_binding(artifacts) -> None:
    """The inheritance: the run names the harvest that fed it, not a path inside it."""
    expected = harvest(artifacts, "harvest_run3")
    harvest(artifacts, "run8h")
    assert binding.resolve(harvests=[artifacts / "harvest_run3"]) == [expected]


def test_a_directory_that_never_harvested_anything_is_refused(artifacts) -> None:
    (artifacts / "empty").mkdir()
    with pytest.raises(binding.Unbound, match="walk.jsonl"):
        binding.resolve(harvests=[artifacts / "empty"])


def test_a_ledger_that_is_not_there_is_a_refusal_not_a_narrowing(artifacts) -> None:
    """A typo that silently shrank the supply a run released would be recorded as
    the population that run decided out of."""
    harvest(artifacts, "harvest_run3")
    with pytest.raises(binding.Unbound, match="not a walk ledger"):
        binding.resolve([artifacts / "harvest_run4" / "walk.jsonl"])


def test_one_ledger_named_twice_is_bound_once(artifacts) -> None:
    """`--harvest x --ledger x/walk.jsonl` is one supply, and a union that read it
    twice would count every location in it twice."""
    only = harvest(artifacts, "harvest_run3")
    assert binding.resolve([only], harvests=[artifacts / "harvest_run3"]) == [only]


def test_a_relative_binding_is_read_against_the_repository(artifacts) -> None:
    """Not against the shell's cwd: a binding is recorded as a relative label and
    read back by a resume that may have started anywhere."""
    assert binding.anchored("artifacts/harvest_run3/walk.jsonl").is_absolute()
    assert binding.label(binding.anchored("artifacts/x/walk.jsonl")) == "artifacts/x/walk.jsonl"
