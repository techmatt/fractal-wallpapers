"""The supply sidecar's manifest, its restore path, and the guard over a run.

`artifacts/curation/supply_scores.jsonl` is the location head's read of the
standing supply and the one file under the regenerable tree the checkout cannot
regenerate: `curate score` rebuilds it from the walk ledgers, and those are under
that tree too. It is archived under a manifest rather than tracked — tens of
megabytes, rewritten whole on every score — so the thing the history holds is a
count and a hash, and everything below is what those two facts have to buy.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.curation import durability

ROW = {
    "schema": 1,
    "head": "location",
    "head_sha256": "a" * 64,
    "key": "[]",
    "ledger": "artifacts/harvest_here/walk.jsonl",
    "partition": "mandelbrot",
    "p_ge3": 0.5,
}


@pytest.fixture
def sidecar(tmp_path, monkeypatch):
    """A live sidecar, a durable copy beside it, and the manifest pointed at both."""
    live = tmp_path / "hot" / "curation" / "supply_scores.jsonl"
    copy = tmp_path / "cold" / durability.BACKUP_UNIT / "supply_scores.jsonl"
    manifest = tmp_path / "supply_scores.manifest.json"
    live.parent.mkdir(parents=True)
    monkeypatch.setattr(durability, "sidecar_path", lambda: live)
    monkeypatch.setattr(durability, "backup_path", lambda: copy)
    monkeypatch.setattr(durability, "manifest_path", lambda: manifest)
    # `restore` and `check` re-address the copy through `rehome`, which knows
    # nothing about a temporary tree; the fallback is `backup_path`, which is
    # what this fixture has already redirected.
    monkeypatch.setattr(durability, "rehome", lambda stored: None)
    return live, copy, manifest


def write_rows(path, count: int, salt: str = "") -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for index in range(count):
            handle.write(json.dumps({**ROW, "key": f"[{index}]{salt}"}) + "\n")


# --------------------------------------------------------------------------- #
# What the manifest is, and what it is instead of.
# --------------------------------------------------------------------------- #
def test_the_manifest_carries_the_count_the_hash_and_the_per_ledger_split(sidecar) -> None:
    """The whole point of not tracking the file is that these three still are."""
    live, copy, manifest = sidecar
    write_rows(live, 40)

    record = durability.save(when="2026-01-01", log=lambda *_: None)

    assert record["rows"] == 40
    assert record["bytes"] == live.stat().st_size
    assert len(record["sha256"]) == 64
    assert record["rows_by_ledger"] == {"artifacts/harvest_here/walk.jsonl": 40}
    assert record["head_sha256"] == "a" * 64
    assert json.loads(manifest.read_text(encoding="utf-8")) == record
    assert copy.is_file()
    # LF, because this one is in the history and a Windows run must not dirty it.
    assert b"\r\n" not in manifest.read_bytes()


def test_the_copy_is_a_copy_and_not_a_tier_move(sidecar) -> None:
    """`storage archive` moves a subtree and the collision guard forbids two of
    one name. This is the opposite thing on purpose, so it has its own name."""
    live, copy, _ = sidecar
    write_rows(live, 12)

    durability.save(log=lambda *_: None)

    assert live.is_file() and copy.is_file()
    assert live.read_bytes() == copy.read_bytes()
    assert durability.BACKUP_UNIT != "curation"


# --------------------------------------------------------------------------- #
# The five verdicts, which are not two.
# --------------------------------------------------------------------------- #
def test_a_scored_harvest_reads_as_grown_rather_than_as_a_fault(sidecar) -> None:
    """More rows than the manifest records is the ordinary state between a
    harvest and the next save. Reporting it as a problem would teach an operator
    to ignore the one report that matters."""
    live, _, _ = sidecar
    write_rows(live, 10)
    durability.save(log=lambda *_: None)
    write_rows(live, 25)

    assert durability.check(log=lambda *_: None)["verdict"] == "grown"


def test_a_shorter_sidecar_reads_short_and_a_deleted_one_reads_missing(sidecar) -> None:
    live, _, _ = sidecar
    write_rows(live, 30)
    durability.save(log=lambda *_: None)

    write_rows(live, 4)
    assert durability.check(log=lambda *_: None)["verdict"] == "short"

    live.unlink()
    assert durability.check(log=lambda *_: None)["verdict"] == "missing"


def test_the_same_count_over_different_bytes_is_changed_and_not_ok(sidecar) -> None:
    """A re-score replaces rows without adding any. The count cannot see that and
    the hash can, which is why both are on the manifest."""
    live, _, _ = sidecar
    write_rows(live, 16)
    durability.save(log=lambda *_: None)
    write_rows(live, 16, salt="x")

    assert durability.check(log=lambda *_: None)["verdict"] == "changed"


# --------------------------------------------------------------------------- #
# The restore, which counts before it believes.
# --------------------------------------------------------------------------- #
def test_restore_refuses_a_copy_that_is_not_what_the_manifest_says(sidecar) -> None:
    live, copy, _ = sidecar
    write_rows(live, 20)
    durability.save(log=lambda *_: None)
    write_rows(copy, 3)
    live.unlink()

    with pytest.raises(durability.SidecarLost, match="Nothing was written"):
        durability.restore(log=lambda *_: None)
    assert not live.exists()


def test_restore_refuses_to_overwrite_a_live_file_that_is_ahead_of_the_manifest(
    sidecar,
) -> None:
    """The ahead case is a harvest nobody has saved yet, and restoring over it
    would delete exactly the rows the manifest exists to protect."""
    live, _, _ = sidecar
    write_rows(live, 10)
    durability.save(log=lambda *_: None)
    write_rows(live, 60)

    with pytest.raises(durability.SidecarLost, match="AHEAD"):
        durability.restore(log=lambda *_: None)
    assert durability.count_rows(live) == 60

    durability.restore(force=True, log=lambda *_: None)
    assert durability.count_rows(live) == 10


def test_a_verified_copy_comes_back_byte_for_byte(sidecar) -> None:
    live, _, _ = sidecar
    write_rows(live, 44)
    record = durability.save(log=lambda *_: None)
    before = live.read_bytes()
    live.unlink()

    back = durability.restore(log=lambda *_: None)

    assert back["sha256"] == record["sha256"]
    assert live.read_bytes() == before


# --------------------------------------------------------------------------- #
# The guard a run makes before it does anything else.
# --------------------------------------------------------------------------- #
def test_the_guard_refuses_a_missing_or_shortened_sidecar_and_names_the_way_back(
    sidecar,
) -> None:
    live, _, _ = sidecar
    write_rows(live, 50)
    durability.save(log=lambda *_: None)

    assert durability.guard(log=lambda *_: None)["verdict"] == "ok"

    write_rows(live, 49)
    with pytest.raises(durability.SidecarLost, match="curate sidecar restore"):
        durability.guard(log=lambda *_: None)

    live.unlink()
    with pytest.raises(durability.SidecarLost, match="curate sidecar restore"):
        durability.guard(log=lambda *_: None)


def test_the_guard_is_silent_where_nothing_has_recorded_the_sidecar(sidecar) -> None:
    """A fresh clone has no manifest and therefore nothing to be short of. A guard
    that refused there would refuse every first run."""
    live, _, _ = sidecar

    assert durability.guard(log=lambda *_: None) == {"verdict": "unrecorded"}
    write_rows(live, 1)
    assert durability.guard(log=lambda *_: None) == {"verdict": "unrecorded"}


def test_a_run_asks_the_guard_before_it_writes_a_plan(tmp_path, monkeypatch) -> None:
    """Before the run directory, before the heads load, before anything is
    recorded: the refusal has to come while nothing has happened yet."""
    from fractal_wallpapers.curation import run as run_module

    def refuse(log=print):
        raise durability.SidecarLost("gone")

    monkeypatch.setattr(run_module.durability, "guard", refuse)
    monkeypatch.setattr(run_module, "run_dir", lambda run: tmp_path / "runs" / run)

    with pytest.raises(durability.SidecarLost):
        run_module.curate(run="never", log=lambda *_: None)
    assert not (tmp_path / "runs").exists()


# --------------------------------------------------------------------------- #
# The tracked records, against the tree they describe.
# --------------------------------------------------------------------------- #
def test_the_tracked_manifest_describes_a_sidecar_and_names_a_copy() -> None:
    record = durability.read_manifest()
    if record is None:
        pytest.skip("no sidecar has been recorded in this checkout")
    assert record["path"].startswith("artifacts/")
    assert record["copy"].startswith(f"artifacts/{durability.BACKUP_UNIT}/")
    assert record["rows"] > 0
    assert len(record["sha256"]) == 64
    assert record["rows"] == sum(record["rows_by_ledger"].values())


def test_the_ledger_provenance_record_agrees_with_the_release_store() -> None:
    """Provenance and not a repair: what it has to be right about is how many
    rows each ledger accounts for, which is a fact about the store."""
    from fractal_wallpapers.curation import records

    path = durability.provenance_path()
    if not path.is_file():
        pytest.skip("no provenance record in this checkout")
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["pool_rows"] == len(records.read_decisions(records.RELEASE))
    assert stored["pool_rows"] == sum(cell["rows"] for cell in stored["ledgers"])
