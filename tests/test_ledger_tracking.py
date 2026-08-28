"""Guard: nothing adds to the candidate ledger without recording what it added.

The manifests in `data/curation/candidate_ledger/` are the only thing about that
store the history keeps — the rows and the score sidecar are tens of megabytes
under `artifacts/` — and they went stale for an era. Three merge legs and the
backfill all wrote the rows; none of them saved. The manifest said 16,006 rows
against 128,368 live, so `curate candidate-ledger check` could only ever answer
`grown` and never `ok`, and `restore` had a copy eight times behind the file it
would have overwritten.

The fix was structural rather than four remembered calls:
[`candidate_ledger.merge`] writes both files **and** records both, and it is the
only door. This is what holds the door shut. A leg reaching past it for
[`candidate_ledger.write`] would write rows nothing recorded, which is exactly
the state above and is invisible until somebody runs `check`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from fractal_wallpapers.curation import candidate_ledger

#: The package this guard reads. Every module of it, not a list that can go stale.
SOURCE = Path(candidate_ledger.__file__).resolve().parent.parent

#: The store's own module, which is where the two writers are allowed to be called.
OWNER = Path(candidate_ledger.__file__).resolve()

#: A call to either raw writer, however the module was imported. Both spellings
#: this package uses — `candidate_ledger.write(...)` and a `from ... import`ed
#: bare `write(...)` cannot both be caught by one pattern, so the guard asks for
#: the qualified one and a second test pins that nothing imports them bare.
CALLS = re.compile(r"\bcandidate_ledger\.write(?:_scores)?\s*\(")

BARE_IMPORT = re.compile(r"^\s*from .*candidate_ledger import .*\bwrite\b", re.MULTILINE)


def modules() -> list[Path]:
    return sorted(path for path in SOURCE.rglob("*.py") if path.resolve() != OWNER)


def test_the_two_raw_writers_are_called_nowhere_but_the_store_itself() -> None:
    """`merge` is the door. Reaching past it writes rows the manifests never see."""
    offenders = {
        str(path.relative_to(SOURCE)): CALLS.findall(path.read_text(encoding="utf-8"))
        for path in modules()
        if CALLS.search(path.read_text(encoding="utf-8"))
    }
    assert offenders == {}, (
        "these call the ledger's raw writers instead of candidate_ledger.merge, so the rows "
        f"they add are never recorded in the tracked manifests: {offenders}"
    )


def test_nothing_imports_the_raw_writers_under_a_bare_name() -> None:
    """The guard above reads a qualified call, so a bare import would evade it."""
    offenders = [
        str(path.relative_to(SOURCE))
        for path in modules()
        if BARE_IMPORT.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_the_door_records_both_files_and_says_what_it_recorded(monkeypatch, tmp_path) -> None:
    """One merge, and both manifests move with it.

    Every path is redirected — the two live files, the two copies and the tracked
    manifest directory — because a test that let any of them resolve would write
    to this machine's real archive tier and to the history. That is not
    hypothetical: it is what the first shape of this change did.
    """
    live, copies, manifests = tmp_path / "live", tmp_path / "copy", tmp_path / "manifests"
    for directory in (live, copies, manifests):
        directory.mkdir()
    monkeypatch.setattr(candidate_ledger, "rows_path", lambda: live / "rows.jsonl")
    monkeypatch.setattr(candidate_ledger, "scores_path", lambda: live / "scores.jsonl")
    monkeypatch.setattr(candidate_ledger, "backup_path", lambda name: copies / name)
    monkeypatch.setattr(candidate_ledger, "manifest_dir", lambda: manifests)

    row = {
        "key": "aaaa",
        "location": {"key": "place-a"},
        "partition": "mandelbrot",
        "provenance": {"run": "hunt1", "candidate": "00001", "store": "hunt"},
    }
    report = candidate_ledger.merge(
        [row], [{"key": "aaaa|art|640x360ss2", "recipe_key": "aaaa"}], log=lambda _line: None
    )

    assert report["ledger"] == {"rows": 1, "new": 1}
    assert report["recorded"]["rows"] == 1, "the manifest was written over the rows just merged"
    assert report["recorded"]["scores"] == 1
    assert (manifests / "rows.manifest.json").is_file()
    assert (manifests / "scores.manifest.json").is_file()
    assert (copies / "rows.jsonl").read_bytes() == (live / "rows.jsonl").read_bytes()

    # And the check the era's stale manifest could never pass.
    verdicts = candidate_ledger.check(log=lambda _line: None)
    assert verdicts["rows"]["verdict"] == "ok"
    assert verdicts["scores"]["verdict"] == "ok"


def test_a_second_merge_of_the_same_rows_leaves_the_manifest_saying_the_same_thing(
    monkeypatch, tmp_path
) -> None:
    """The upsert is idempotent, so the record of it has to be as well."""
    live, copies, manifests = tmp_path / "live", tmp_path / "copy", tmp_path / "manifests"
    for directory in (live, copies, manifests):
        directory.mkdir()
    monkeypatch.setattr(candidate_ledger, "rows_path", lambda: live / "rows.jsonl")
    monkeypatch.setattr(candidate_ledger, "scores_path", lambda: live / "scores.jsonl")
    monkeypatch.setattr(candidate_ledger, "backup_path", lambda name: copies / name)
    monkeypatch.setattr(candidate_ledger, "manifest_dir", lambda: manifests)

    rows = [
        {
            "key": "aaaa",
            "location": {"key": "place-a"},
            "partition": "mandelbrot",
            "provenance": {"run": "hunt1", "candidate": "00001", "store": "hunt"},
        }
    ]
    scores = [{"key": "aaaa|art|640x360ss2", "recipe_key": "aaaa"}]
    first = candidate_ledger.merge(rows, scores, log=lambda _line: None)
    written = (manifests / "rows.manifest.json").read_bytes()
    second = candidate_ledger.merge(rows, scores, log=lambda _line: None)

    assert (first["ledger"]["rows"], first["ledger"]["new"]) == (1, 1)
    assert (second["ledger"]["rows"], second["ledger"]["new"]) == (1, 0)
    assert (manifests / "rows.manifest.json").read_bytes() == written


@pytest.mark.parametrize("leg", ["hunt", "mine", "depth"])
def test_every_merge_leg_reaches_the_ledger_through_the_door(leg: str) -> None:
    """The three legs that add rows, named, so a fourth one arriving is a visible edit."""
    text = (SOURCE / "curation" / f"{leg}.py").read_text(encoding="utf-8")
    assert "candidate_ledger.merge(" in text
