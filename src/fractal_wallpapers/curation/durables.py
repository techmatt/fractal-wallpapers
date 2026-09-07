"""Which files are durable, and which of them a run refuses to start without.

[`curation.durability`] is the mechanism — what a [`durability.Durable`] is, how
one is saved, checked and restored. This is the list: the supply sidecar's own
paths, and the three files [`guarded`] names.

## Why the list is not in the mechanism

The sidecar was the first durable and for a while it was the only one, so
`durability` was written around it: `save()`, `check()` and `restore()` took no
argument and meant the sidecar, and `guarded()` reached **up** into
[`curation.amend`] and [`curation.hunt`] from inside the floor module those two
import. That is a module knowing its own callers, and it held `durability` — and
the gallery passes' gate store behind it — inside the largest import cycle in the
tree.

So the arrow is turned around, the way [`models.roster`] turned it around for
`ship` and [`curation.run_layout`] for `run`. `durability` names no file at all
now and imports `paths` and nothing else above it; every module that *has* a
durable file describes it where the file lives — [`amend.durable`],
[`hunt.frames_durable`], `candidate_ledger.store.durable_rows`,
`flatness.durable`, `signatures.durable`, `embeddings.store`,
`palettes.color_mass.sweep_log` — and this module is
where the sidecar's description lives, beside the one list that has to see three
of them at once.

The zero-argument calls went with it. `durability.save()` meaning the sidecar
was the same accident from the other end: a mechanism whose default argument is
one of its callers' files. `save`, `check`, `restore` and the two manifest verbs
take their `Durable` now, and the sidecar is spelled [`sidecar()`] at the call
site like every other one.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from fractal_wallpapers.curation import durability
from fractal_wallpapers.paths import archive_root, hot_root, repo_root

#: What the sidecar is called, wherever it is.
SIDECAR_NAME = "supply_scores.jsonl"

#: What each of [`guarded`]'s files is called in a refusal and in the line the
#: guard prints. Short, because they are read at the top of every run's log.
GUARD_TAGS = ("sidecar", "amendment", "frames")


def manifest_path() -> Path:
    """The tracked manifest: what the sidecar was, last time anybody recorded it."""
    return repo_root() / "data" / "curation" / "supply_scores.manifest.json"


def sidecar_path() -> Path:
    """The live sidecar, wherever curation's subtree currently is."""
    from fractal_wallpapers.curation import intake

    return intake.scores_path()


def backup_path() -> Path:
    """The durable copy: on the archive tier where there is one, hot where there is not.

    Named off a root rather than through `under()`, because `under()` resolves to
    whichever tier the subtree is already on — which, for a copy that has never
    been written, is the hot one, beside the original it is supposed to survive.
    """
    archive = archive_root()
    root = hot_root() if archive is None else archive
    return Path(root) / durability.BACKUP_UNIT / SIDECAR_NAME


def _by_ledger(path: Path) -> dict:
    """How many of the sidecar's rows each ledger last scored. One parse, in `save`."""
    tally: Counter = Counter()
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                tally[str(json.loads(line).get("ledger"))] += 1
    return dict(sorted(tally.items()))


def _head_of(path: Path) -> dict:
    """The head every row names, or the disagreement where they do not all name one."""
    stamps: Counter = Counter()
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                stamps[str(json.loads(line).get("head_sha256"))] += 1
    if len(stamps) == 1:
        return {"head": "location", "head_sha256": next(iter(stamps))}
    return {"head": "location", "head_sha256": None, "head_sha256_counts": dict(stamps)}


def sidecar() -> durability.Durable:
    """The supply sidecar as a [`durability.Durable`]."""
    return durability.Durable(
        name="the supply sidecar",
        live=sidecar_path(),
        copy=backup_path(),
        manifest=manifest_path(),
        why_not_tracked=(
            "tens of megabytes against a 1 MiB per-file history guard, and rewritten whole "
            "on every `curate score` because the sidecar upserts per ledger — so tracking it "
            "would add a fresh full-size blob to the history every harvest night. The "
            "manifest is what the history keeps; the bytes live on both tiers."
        ),
        save_command="fractal-wallpapers curate sidecar save",
        restore_command="fractal-wallpapers curate sidecar restore",
        rebuild_command="fractal-wallpapers curate score",
        facts=lambda path: {**_head_of(path), "rows_by_ledger": _by_ledger(path)},
    )


# --------------------------------------------------------------------------- #
# The guard a run makes before it does anything else.
# --------------------------------------------------------------------------- #
def guarded() -> tuple[durability.Durable, ...]:
    """The files a `curate run` refuses to start without. **Three**, and the list is here.

    All three are inputs a run reads without being asked to, and none of them can
    be recovered from afterwards:

    * the **supply sidecar**, which is the standing supply the leg is offered;
    * the **score amendment**, which every reader of a seating score overlays on
      that sidecar — so a run started without it is not offered a smaller supply,
      it is offered the same supply at scores nobody has corrected. That is the
      worse of the two failures, because the count would look right;
    * the **hunt frame index**, which every mining leg draws its framings through.
      Its failure is the same shape and it is the least recoverable of the three:
      a location the index has no row for draws at the frame it already carries,
      by design, so a leg that lost the index renders a whole night successfully
      at unrefined framings and reports nothing unusual.

    A file is not on this list merely for being expensive. The embedding store
    and the two ledger sidecars are all expensive and all absent here: a run that
    starts without them fails loudly at the step that needs them, which is a
    different thing from a run that starts and quietly decides on stale numbers.

    The two imports below are the reason this module exists rather than being a
    section of `durability`: `amend` and `hunt` both import `durability`, so a
    list living there could only reach them from inside a function body — which
    is an import cycle written small enough to look like a style choice.
    """
    from fractal_wallpapers.curation import amend, hunt

    return (sidecar(), amend.durable(), hunt.frames_durable())


def guard(log=print) -> dict:
    """Refuse a run whose guarded files are gone, or have lost rows since recording.

    One verdict per file in [`guarded`], keyed by a short tag. It answers the
    questions that cannot be recovered from afterwards: is the standing supply
    still there, and are the corrections to it still there.
    """
    return {
        tag: durability.guard_one(durable, tag, log=log)
        for tag, durable in zip(GUARD_TAGS, guarded(), strict=True)
    }


__all__ = [
    "GUARD_TAGS",
    "SIDECAR_NAME",
    "backup_path",
    "guard",
    "guarded",
    "manifest_path",
    "sidecar",
    "sidecar_path",
]
