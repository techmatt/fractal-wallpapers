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


@pytest.fixture
def guarded(sidecar, tmp_path, monkeypatch):
    """Both files a run refuses to start without, inside `tmp_path`.

    The guard reads two files now, so a fixture that redirected one of them would
    leave the other pointed at this machine's real amendment — a unit test asking
    a hundred-thousand-row question about the live tree.
    """
    live, _, _ = sidecar
    amendment = tmp_path / "hot" / "curation" / "score_amendments.jsonl"
    durable = durability.Durable(
        name="the score amendment",
        live=amendment,
        copy=tmp_path / "cold" / durability.BACKUP_UNIT / "score_amendments.jsonl",
        manifest=tmp_path / "score_amendments.manifest.json",
        why_not_tracked="tens of megabytes against a 1 MiB per-file history guard.",
        save_command="fractal-wallpapers curate amendments save",
        restore_command="fractal-wallpapers curate amendments restore",
        rebuild_command="fractal-wallpapers curate redraw",
    )
    monkeypatch.setattr(durability, "guarded", lambda: (durability.sidecar(), durable))
    return live, amendment, durable


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

    with pytest.raises(durability.DurableLost, match="Nothing was written"):
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

    with pytest.raises(durability.DurableLost, match="AHEAD"):
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
    guarded,
) -> None:
    live, _, _ = guarded
    write_rows(live, 50)
    durability.save(log=lambda *_: None)

    assert durability.guard(log=lambda *_: None)["sidecar"]["verdict"] == "ok"

    write_rows(live, 49)
    with pytest.raises(durability.DurableLost, match="curate sidecar restore"):
        durability.guard(log=lambda *_: None)

    live.unlink()
    with pytest.raises(durability.DurableLost, match="curate sidecar restore"):
        durability.guard(log=lambda *_: None)


def test_the_guard_refuses_a_shortened_amendment_too(guarded) -> None:
    """The second guarded file, and the failure it is here for is not the
    sidecar's. A missing amendment does not shrink the supply — every count comes
    out right — it puts the seating silently back on the scores the re-read
    corrected. So it refuses on the same rule and names its own way back."""
    live, amendment, durable = guarded
    write_rows(live, 50)
    durability.save(log=lambda *_: None)
    write_rows(amendment, 40)
    durability.save(durable, log=lambda *_: None)

    verdicts = durability.guard(log=lambda *_: None)
    assert verdicts["sidecar"]["verdict"] == "ok"
    assert verdicts["amendment"] == {"verdict": "ok", "rows": 40, "recorded": 40}

    # Append-only, so shorter is always a loss and never an ordinary state.
    write_rows(amendment, 39)
    with pytest.raises(durability.DurableLost, match="curate amendments restore"):
        durability.guard(log=lambda *_: None)

    amendment.unlink()
    with pytest.raises(durability.DurableLost, match="curate redraw"):
        durability.guard(log=lambda *_: None)


def test_a_grown_amendment_is_the_ordinary_state_and_passes(guarded) -> None:
    """A redraw nobody has saved yet is what `curate redraw` leaves behind, and a
    guard that refused there would refuse the run after every refresh."""
    live, amendment, durable = guarded
    write_rows(live, 50)
    durability.save(log=lambda *_: None)
    write_rows(amendment, 40)
    durability.save(durable, log=lambda *_: None)
    write_rows(amendment, 44)

    assert durability.guard(log=lambda *_: None)["amendment"]["rows"] == 44


def test_the_guard_is_silent_where_nothing_has_recorded_the_files(guarded) -> None:
    """A fresh clone has no manifest and therefore nothing to be short of. A guard
    that refused there would refuse every first run."""
    live, amendment, _ = guarded
    unrecorded = {"sidecar": {"verdict": "unrecorded"}, "amendment": {"verdict": "unrecorded"}}

    assert durability.guard(log=lambda *_: None) == unrecorded
    write_rows(live, 1)
    write_rows(amendment, 1)
    assert durability.guard(log=lambda *_: None) == unrecorded


def test_the_guarded_list_is_the_supply_and_the_amendment_and_nothing_else() -> None:
    """The list is a decision, not an accident of what happens to be expensive.
    The embedding store and the two ledger sidecars are all costly and none of
    them is here: a run that starts without those fails loudly at the step that
    needs them, which is a different thing from a run that starts and quietly
    decides on stale numbers."""
    from fractal_wallpapers.curation import amend

    named = [durable.live.name for durable in durability.guarded()]
    assert named == [durability.SIDECAR_NAME, amend.AMENDMENTS_NAME]
    assert len(durability.GUARD_TAGS) == len(named)


def test_a_run_asks_the_guard_before_it_writes_a_plan(tmp_path, monkeypatch) -> None:
    """Before the run directory, before the heads load, before anything is
    recorded: the refusal has to come while nothing has happened yet."""
    from fractal_wallpapers.curation import run as run_module

    def refuse(log=print):
        raise durability.DurableLost("gone")

    monkeypatch.setattr(run_module.durability, "guard", refuse)
    monkeypatch.setattr(run_module, "run_dir", lambda run: tmp_path / "runs" / run)

    with pytest.raises(durability.DurableLost):
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


def test_the_tracked_manifest_describes_an_amendment_and_names_a_copy() -> None:
    from fractal_wallpapers.curation import amend

    durable = amend.durable()
    record = durability.read_manifest(durable)
    if record is None:
        pytest.skip("no amendment has been recorded in this checkout")
    assert record["path"].endswith(amend.AMENDMENTS_NAME)
    assert record["copy"].startswith(f"artifacts/{durability.BACKUP_UNIT}/")
    assert record["rows"] > 0
    assert len(record["sha256"]) == 64
    # Keyed on (location, engine), so the per-build split has to add up and a
    # manifest giving one number would describe a population that does not exist.
    assert record["rows"] == sum(record["rows_by_engine"].values())


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


def test_every_released_row_names_the_walk_that_found_its_location() -> None:
    """A released row with no ledger is a wallpaper nothing can say it discovered.

    The one way to get one was an **on-demand render**: the seat's own renderer
    copied the candidate's framing across and not its ledger, so gallery4 shipped
    94 of 249 against a ledger named `None` and `curate ledgers` reported them as
    a tenth, unresolvable ledger. Pinned on the store rather than on the renderer
    because the claim is about the collection, and because the renderer is only
    the way it happened to break this time.
    """
    from fractal_wallpapers.curation import records

    missing = [
        row["key"]
        for row in records.read_decisions(records.RELEASE)
        if not (row.get("location") or {}).get("ledger")
    ]
    assert missing == [], f"{len(missing)} released row(s) name no ledger"
