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

import json
import re
from pathlib import Path

import pytest

from fractal_wallpapers import paths
from fractal_wallpapers.curation import candidate_ledger, durability

#: The package this guard reads. Every module of it, not a list that can go stale.
#: Three parents, not two: `candidate_ledger` is a package now, so its `__file__`
#: is a directory deeper than it was and the old spelling quietly resolved to
#: `curation/` — this guard still passing, over a fraction of the tree it means.
SOURCE = Path(candidate_ledger.__file__).resolve().parent.parent.parent

#: Where the two writers may be called: the module that defines them, and the
#: door. `door.merge` reaching for `store.write` IS the recording writer — that is
#: the arrangement this file exists to hold, not an exception to it.
OWNER = {
    Path(candidate_ledger.store.__file__).resolve(),
    Path(candidate_ledger.door.__file__).resolve(),
    Path(candidate_ledger.rerender.__file__).resolve(),
}

#: A call to either raw writer, in either spelling the tree uses: qualified
#: through the package from outside it (`candidate_ledger.write(...)`), and
#: through the store module from inside (`store.write(...)`). The second is new
#: with the split and is the one a fresh module of the package would reach for.
#: A `from ... import`ed bare `write(...)` cannot be caught by the same pattern,
#: so a second test pins that nothing imports them bare.
CALLS = re.compile(r"\b(?:candidate_ledger|store)\.write(?:_scores)?\s*\(")

BARE_IMPORT = re.compile(r"^\s*from .*candidate_ledger import .*\bwrite\b", re.MULTILINE)


def modules() -> list[Path]:
    return sorted(path for path in SOURCE.rglob("*.py") if path.resolve() not in OWNER)


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
    # `rescore` is the third module allowed to hold one, and the exemption is only
    # safe while it records what it wrote. The rule this file is about is not
    # "merge is the only writer" but "nothing writes without recording", and the
    # split is what first made the difference visible: the old sweep skipped the
    # whole ledger module, so this call has always been here and was never read.
    import inspect

    recording = inspect.getsource(candidate_ledger.rescore)
    assert "store.write_scores(" in recording
    assert "durability.save(store.durable_scores()" in recording, (
        "rescore writes the score sidecar; a rescore that stopped recording it would put "
        "the manifest behind the file with nothing saying so"
    )


def test_nothing_imports_the_raw_writers_under_a_bare_name() -> None:
    """The guard above reads a qualified call, so a bare import would evade it."""
    offenders = [
        str(path.relative_to(SOURCE))
        for path in modules()
        if BARE_IMPORT.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def a_row(key: str = "aaaa", place: str = "place-a", **over) -> dict:
    """One ledger row carrying a **whole recipe**, which is the store's contract.

    A row thinned to its key and its provenance was enough while `merge` only
    upserted it. `merge` prunes now, and the prune joins every row back to the
    label store through `retention.render_key_of` — which reads the recipe and
    raises on a family it cannot place. A row that cannot be keyed could never be
    found to carry a label and would be dropped as unlabeled with nothing saying
    so, which is why that raise is loud rather than a `None`, and why a fixture
    row has to be a real one.
    """
    from tests.test_candidate_ledger import decision

    from fractal_wallpapers.curation import recipes

    source = decision(location={**decision()["location"], "key": place})
    recipe = recipes.of_decision(source)
    return {
        **candidate_ledger.row(recipe=recipe, key=key, source=source, picture=None),
        **over,
    }


def redirect(monkeypatch, root, manifests):
    """Point the whole store at a temporary tree, **at the tier roots**.

    Returns `(live, copies)` — where the store's files and their durable copies
    now resolve — because the tests assert against both.

    This used to patch five accessors, and the reason it does not any more is the
    defect the session guard in `conftest` exists for. Every one of those paths
    already resolves through a **root**: the live files and both sidecars through
    `paths.under("curation", …)`, the copies off `hot_root()`/`archive_root()`.
    Setting the two roots redirects all four at once, and it redirects the ones
    nobody thought of too — a redirect written per accessor is complete only
    against the call graph on the day it was written, which is exactly how
    `flatness.sidecar_path` came to be forgotten and this machine's real sidecar
    came to be rewritten with a temporary ledger's keys.

    **Two accessors are still patched and each is patched for its own reason.**
    `manifest_dir` resolves off `repo_root()` rather than off a tier, so there is
    no root to set: that is the tracked half, and it is the half the guard in
    `conftest` covers. `signatures.sidecar_path` is patched to *undo* the autouse
    `no_signature_sidecar` fixture, which points it at a path that does not exist
    for every test in the suite — the roots cannot reach a function that has been
    replaced, and the two tests below are the ones that mean to read it.
    """
    from fractal_wallpapers.curation import signatures

    monkeypatch.setenv(paths.HOT_ROOT_VARIABLE, str(root))
    monkeypatch.setenv(paths.ARCHIVE_ROOT_VARIABLE, "")
    monkeypatch.setattr(candidate_ledger.store, "manifest_dir", lambda: manifests)

    live = root / "curation" / candidate_ledger.store.UNIT
    copies = root / durability.BACKUP_UNIT / candidate_ledger.store.UNIT
    live.mkdir(parents=True, exist_ok=True)
    # And the two stores the prune reads that the five accessor patches never
    # redirected: the supply sidecar (`intake`) and the expressed readout
    # (`rank_key.thin_cells`). Redirecting at the root redirects those too, which
    # is how it came out that every test in this file had been reading THIS
    # MACHINE's real 67k-row supply and its real coverage vector — and would have
    # failed on a fresh clone, where neither file exists. Empty is the honest
    # fixture: none of these synthetic keys was ever in either store.
    (root / "curation").mkdir(parents=True, exist_ok=True)
    (root / "curation" / "supply_scores.jsonl").touch()
    expressed = root / "curation" / "expressed"
    expressed.mkdir(parents=True, exist_ok=True)
    (expressed / "expressed.json").write_text(json.dumps({"thin": []}), encoding="utf-8")
    monkeypatch.setattr(signatures, "sidecar_path", lambda: live / signatures.SIDECAR_NAME)
    return live, copies


def test_the_door_records_both_files_and_says_what_it_recorded(monkeypatch, tmp_path) -> None:
    """One merge, and both manifests move with it.

    Every path is redirected — the two live files, the two copies and the tracked
    manifest directory — because a test that let any of them resolve would write
    to this machine's real archive tier and to the history. That is not
    hypothetical: it is what the first shape of this change did.
    """
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    live, copies = redirect(monkeypatch, tmp_path / "artifacts", manifests)

    row = a_row()
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
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    live, copies = redirect(monkeypatch, tmp_path / "artifacts", manifests)

    rows = [a_row()]
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


def test_the_one_door_fills_the_flatness_sidecar_as_well_as_the_two_files(
    tmp_path, monkeypatch
) -> None:
    """The `mine1h` failure at its cause. The sidecar is keyed on the recipe and
    nothing else filled it, so a leg that merged and stopped left every row it
    wrote unranked to the fitted key — in the pool, clearing its bars, counted in
    every denominator, and unable to win a seat. 8,192 rows, none seated, silent.

    `merge` is already the one door for the rows and the manifests, so it is the
    one door for the reading too, and the report it returns says what it swept.
    A row whose picture this checkout cannot resolve is simply not swept, which is
    the sweep's own rule and not a special case here.
    """
    from PIL import Image

    from fractal_wallpapers.curation import flatness

    redirect(monkeypatch, tmp_path / "artifacts", tmp_path / "manifests")

    def _row() -> dict:
        return a_row(picture="artifacts/one.jpg", colour={"cells": [], "families": []})

    picture = tmp_path / "one.jpg"
    Image.new("RGB", (64, 64), (30, 90, 160)).save(picture)
    monkeypatch.setattr("fractal_wallpapers.paths.rehome", lambda name: picture if name else None)

    report = candidate_ledger.merge(
        [_row()],
        [],
        log=lambda *_a, **_k: None,
    )
    assert report["flatness"]["swept"] == 1, "the merged row was read"
    assert report["flatness"]["read"] == 1
    assert report["flatness"]["column"] == flatness.COLUMN
    assert flatness.by_recipe(flatness.read())["aaaa"] is not None, "and landed in the sidecar"

    again = candidate_ledger.merge(
        [_row()],
        [],
        log=lambda *_a, **_k: None,
    )
    assert again["flatness"]["swept"] == 0, "incremental: a row already read costs no decode"


def test_the_door_records_the_flatness_sidecar_with_the_other_two(tmp_path, monkeypatch) -> None:
    """The third file of the store, recorded by the same write that fills it.

    `merge` saved the rows and the scores and left the sidecar to whoever
    remembered `curate flatness save` — which is a writer that has to remember,
    the exact shape this file's own docstring says goes stale. It matters more
    here than for the other two: an unrecorded sidecar is the one whose loss
    leaves every row of the store unranked to the fitted key.
    """
    from PIL import Image

    from fractal_wallpapers.curation import flatness

    manifests = tmp_path / "manifests"
    manifests.mkdir()
    live, copies = redirect(monkeypatch, tmp_path / "artifacts", manifests)

    picture = tmp_path / "one.jpg"
    Image.new("RGB", (64, 64), (30, 90, 160)).save(picture)
    monkeypatch.setattr("fractal_wallpapers.paths.rehome", lambda name: picture if name else None)

    report = candidate_ledger.merge(
        [a_row(picture="artifacts/one.jpg", colour={"cells": [], "families": []})],
        [],
        log=lambda *_a, **_k: None,
    )

    assert report["recorded"]["flatness"] == 1
    assert (manifests / "flatness.manifest.json").is_file()
    assert (copies / flatness.SIDECAR_NAME).read_bytes() == (
        live / flatness.SIDECAR_NAME
    ).read_bytes()
    named = [name for name in report["recorded"]["manifests"] if "flatness" in name]
    assert len(named) == 1, report["recorded"]["manifests"]


def test_the_door_mirrors_the_reduced_signature_sidecar_too(tmp_path, monkeypatch) -> None:
    """The fourth file of the store, copied rather than left to be re-derived.

    It was outside the mirror while the reduction ran at 1024 directions and the
    store was ~245 MB. At 256 it was 68.6 MB when that landed and is 253 MB over
    44,346 rows on 2026-09-06, and a restore that skipped it paid
    minutes of `curate signatures sweep` over the three-worker pool for bytes a
    copy already had. `merge` does not FILL this one — nothing here does — so the
    pin is that a file which is there is mirrored and recorded.
    """
    from fractal_wallpapers.curation import signatures

    manifests = tmp_path / "manifests"
    manifests.mkdir()
    live, copies = redirect(monkeypatch, tmp_path / "artifacts", manifests)
    monkeypatch.setattr("fractal_wallpapers.paths.rehome", lambda _name: None)
    signatures.write([signatures.row("aaaa", "artifacts/one.jpg", signatures.pack([0.0] * 4))])

    report = candidate_ledger.merge([a_row()], [], log=lambda *_a, **_k: None)

    assert report["recorded"]["signatures"] == 1
    assert (copies / signatures.SIDECAR_NAME).read_bytes() == (
        live / signatures.SIDECAR_NAME
    ).read_bytes(), "the mirror holds the sidecar's bytes"
    named = [name for name in report["recorded"]["manifests"] if "signatures" in name]
    assert len(named) == 1, report["recorded"]["manifests"]


def test_a_checkout_that_never_swept_signatures_merges_without_one(tmp_path, monkeypatch) -> None:
    """No file is a state and not a loss, so the door records `None` and goes on.

    Stronger than the flatness sidecar's version of this: `prune` rewrites that
    one, so it exists by the time the save reaches it. Nothing in a merge writes
    this one at all.
    """
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    live, copies = redirect(monkeypatch, tmp_path / "artifacts", manifests)
    monkeypatch.setattr("fractal_wallpapers.paths.rehome", lambda _name: None)

    report = candidate_ledger.merge([a_row()], [], log=lambda *_a, **_k: None)

    assert report["recorded"]["signatures"] is None
    assert not (manifests / "signatures.manifest.json").exists()
    assert report["recorded"]["rows"] == 1, "the rest of the store is recorded either way"


def test_the_signature_manifest_counts_rows_by_the_shape_each_one_names(tmp_path) -> None:
    """A mirror of bytes does not get to restate what those bytes are.

    The sidecar is upserted by recipe key and nothing sweeps the old constants
    out, so a live file that has outlived a change to either one holds both — the
    real store held 11,454 rows at 4x256 and 182 still at 4x1024 on 2026-09-01.
    A manifest stamped with the CURRENT shape would call those 182 rows something
    they are not.
    """
    from fractal_wallpapers.curation import signatures

    blocks, directions = signatures.shape()
    path = tmp_path / "signatures.jsonl"
    rows = [
        signatures.row("aaaa", "a.jpg", signatures.pack([0.0] * 4)),
        {**signatures.row("bbbb", "b.jpg", signatures.pack([0.0] * 4)), "directions": 1024},
    ]
    body = "".join(json.dumps(held) + chr(10) for held in rows)
    path.write_text(body, encoding="utf-8", newline=chr(10))
    facts = signatures._shapes(path)

    assert facts["rows_by_shape"] == {f"{blocks}x{directions}": 1, f"{blocks}x1024": 1}


def test_a_merge_that_swept_nothing_records_an_empty_sidecar_rather_than_none(
    tmp_path, monkeypatch
) -> None:
    """A merge whose rows name no resolvable picture still records the sidecar.

    Worth pinning because the reason is not the sweep. `flatness.sweep` writes no
    file when it read nothing, so on the sweep alone there would be nothing to
    record — but [`candidate_ledger.prune`] rewrites all THREE files of the store
    and runs between the two, so the sidecar is on disk by the time the save
    reaches it, empty. The conditional in `merge` is therefore a guard against
    [`durability.save`]'s refusal and not the ordinary path.
    """
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    live, copies = redirect(monkeypatch, tmp_path / "artifacts", manifests)
    monkeypatch.setattr("fractal_wallpapers.paths.rehome", lambda _name: None)

    report = candidate_ledger.merge([a_row()], [], log=lambda *_a, **_k: None)

    assert report["flatness"]["read"] == 0, "nothing was resolvable to sweep"
    assert report["recorded"]["flatness"] == 0
    assert (manifests / "flatness.manifest.json").is_file()
    assert report["recorded"]["rows"] == 1, "the other two are recorded either way"
    assert report["recorded"]["scores"] == 0
