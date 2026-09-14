"""The release-geometry picture of a seat: found where one already exists, made where it does not.

A recorded gallery's rows name the **candidate** picture — 640x360, the size the
judges read — and that is what the viewer shows, because a thousand of them is a
page that opens. It is not the size a person decides anything at. So this module
answers one question for a record: where is each of its seats at
[`release.RELEASE_REGIME`], `1280x720ss2`.

## Found before made

Most of a record's seats have already been drawn at this geometry, because the
**labeling sheets are cut at it** — a gallery rejection pass renders every seat of
a record, and every sheet before it rendered a few hundred. So the first pass is a
**gather**: every built sheet's row file, read for rows whose own `join.render`
says `1280x720ss2`, indexed by the candidate key in `selected_on.candidate`. Only
what that misses is rendered, on the locked three-worker pool through
[`release`], exactly the way a shipped wallpaper is.

**The match is the recipe key AND the regime, and it is exact.** The key already
carries the family, the viewport, `maxiter`, the mode and its settings, the curve,
the map, the palette and the autolevel band — [`recipes.KEYED`] — so two rows with
one key differ in nothing that decides pixels *except* the regime, which the key
carries too and which is therefore checked against the picture that was actually
drawn rather than assumed. A near match is not taken: a seat whose only picture is
at another frame is a miss and is rendered.

## Nothing is copied

A found picture stays where it is and the index names it. A record's seats are
scattered across a dozen sheets and copying them into one directory would be a
second copy of a hundred and fifty megabytes that goes stale the moment either
side moves. What this module owns on disk is only the pictures it **made**.

## It is not a second picture store

[`curation.candidate_ledger`] owns the candidates and nothing here writes a ledger
row. These are renders of rows that already exist, at a geometry the ledger does
not hold, made so a page can show them — regenerable from the record and the
ledger, and deletable without losing anything a record names.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from fractal_wallpapers.curation import release
from fractal_wallpapers.paths import Tiers, rehome, under

#: The schema the index carries.
SCHEMA = 1

#: The subtree the pictures this module makes land in.
UNIT = "fulls"

#: What "full" means on a viewer, and it is [`release.RELEASE_REGIME`] read
#: through rather than restated: the picture a person looks at to decide is the
#: picture the release leg would ship, and two spellings of that would be two
#: geometries one of which nobody chose. **1280x720 ss2 since 2026-08-25**, and
#: the geometry the labeling sheets and the friend-voting kit are both cut at,
#: which is what makes the gather below find anything at all.
REGIME = release.RELEASE_REGIME


class FullsRefused(RuntimeError):
    """A record's full-geometry pictures cannot be gathered or made."""


def store_dir(regime: release.Regime | None = None) -> Path:
    """Where the pictures this module MADE live. **The one accessor.**"""
    return under("curation", UNIT, (regime or REGIME).spelled)


def index_path(regime: release.Regime | None = None) -> Path:
    """The index: `{candidate key: where its full-geometry picture is}`."""
    return store_dir(regime) / "index.json"


def sheet_roots() -> list[Path]:
    """Every directory a built sheet could be under, on this tier.

    Two, because `label build` writes under `artifacts/sheet/<name>/` and the
    one-off cuts that predate it wrote under `artifacts/<name>/`. Both are read
    rather than one being declared canonical: the older pictures are real
    pictures and the point of the gather is not to re-render what exists.
    """
    return [under("sheet"), under()]


def gather(regime: release.Regime | None = None, log=print) -> dict[str, Path]:
    """`{candidate key: picture}` for every sheet row drawn at `regime`.

    A sheet row says what it was drawn at in its own `join.render` and says which
    candidate it is a picture of in `selected_on.candidate`. Both are required:
    a row missing either is a row that cannot be matched to a seat, and guessing
    from the sheet's manifest would hand back a picture at whatever geometry that
    sheet happened to default to.

    First writer wins on a repeated key, and sheets are read in a stable order, so
    two cuts of one candidate at one regime resolve the same way on every run.
    """
    regime = regime or REGIME
    wanted = (tuple(regime.resolution), int(regime.supersample))
    found: dict[str, Path] = {}
    for root in sheet_roots():
        if not root.is_dir():
            continue
        for directory in sorted(held for held in root.iterdir() if held.is_dir()):
            rows_file = directory / "sheet.jsonl"
            if not rows_file.is_file():
                continue
            taken = 0
            for line in rows_file.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                render = (row.get("join") or {}).get("render") or {}
                resolution, supersample = render.get("resolution"), render.get("supersample")
                if not resolution or supersample is None:
                    continue
                if (tuple(resolution), int(supersample)) != wanted:
                    continue
                key = str((row.get("selected_on") or {}).get("candidate") or "")
                pictures = row.get("pictures") or []
                if not key or key in found or not pictures:
                    continue
                picture = directory / str(pictures[0].get("path") or "")
                if picture.is_file():
                    found[key] = picture
                    taken += 1
            if taken:
                log(f"[fulls] {directory.name}: {taken} row(s) at {regime.spelled}")
    return found


def made(regime: release.Regime | None = None) -> dict[str, Path]:
    """`{candidate key: picture}` for the ones this module rendered itself."""
    directory = store_dir(regime) / "pictures"
    if not directory.is_dir():
        return {}
    return {held.stem: held for held in sorted(directory.glob("*.jpg"))}


def index(keys, regime: release.Regime | None = None, log=print) -> dict[str, Path]:
    """`{key: picture}` over `keys`, gathered from the sheets and from what was made.

    What this module made wins, because a gathered picture is somebody else's file
    under somebody else's sweep and the one here was made for this.
    """
    wanted = {str(key) for key in keys}
    resolved = {key: path for key, path in gather(regime, log).items() if key in wanted}
    resolved.update({key: path for key, path in made(regime).items() if key in wanted})
    return resolved


def href(picture, directory: Path, tiers: Tiers | None = None) -> str:
    """One picture as a page refers to it: relative, forward slashes.

    The same rule and the same fallback as [`tentative.thumbnail_href`], and for
    the same reason — a folder that can be copied elsewhere and still open.
    """
    resolved = rehome(picture, tiers)
    if resolved is None:
        resolved = Path(str(picture))
    try:
        return Path(os.path.relpath(resolved, directory)).as_posix()
    except ValueError:
        return resolved.absolute().as_uri()


def render(
    rows,
    regime: release.Regime | None = None,
    workers: int = release.DEFAULT_WORKERS,
    log=print,
) -> dict:
    """Render the seats in `rows` that have no picture at `regime` yet.

    `rows` are ledger rows — each with its `recipe` and its `key` — because the
    recipe is what a render is made of and a recorded seat does not carry one.
    Built through [`release.task_for`], so this leg cannot drift from the four
    others in the way that one did: every picture-deciding member is named.

    The pool is [`release.DEFAULT_WORKERS`] at below-normal priority, this
    machine's rule, and the leg is resumable — a key whose JPEG is already on
    disk is not asked for again.
    """
    from fractal_wallpapers.curation import backfill, recipes
    from fractal_wallpapers.curation import stamps as stamps_module

    regime = regime or REGIME
    directory = store_dir(regime) / "pictures"
    directory.mkdir(parents=True, exist_ok=True)
    standing = made(regime)
    wanted = {str(row["key"]): row for row in rows if str(row.get("key")) not in standing}
    # The levelling curve each picture INHERITS from its candidate, and never the
    # stamp block on the candidate's own recipe. A release at another size borrows
    # ([`votes._borrowed`] is the same call for the same reason): the tone of a
    # 1280x720 render is not the tone of the 640x360 JPEG the seat was chosen on,
    # and an operator handed a stamp instead of a curve re-measures — which needs
    # a whole row it was never given and fails 74 of 77 at `KeyError('curve')`.
    borrowed = stamps_module.for_release(
        wanted, backfill.read(), regime=recipes.CANDIDATE_REGIME.spelled, store="sequence"
    )
    log(f"[fulls] {len(borrowed)}/{len(wanted)} seat(s) inherit a levelling curve")
    tasks = []
    for key, row in wanted.items():
        recipe = row.get("recipe") or {}
        if not recipe:
            raise FullsRefused(f"{key} carries no recipe; there is nothing to render it from")
        tasks.append(
            release.task_for(
                id=key,
                row=recipe,
                mode=recipe["mode"],
                colormap=recipe["colormap"],
                mode_params=recipe.get("mode_params"),
                curve=recipe.get("curve"),
                palette=recipe.get("palette"),
                autolevel=borrowed.get(key),
                output=directory / f"{key}.jpg",
                geometry={**regime.geometry(), "maxiter": int(recipe["maxiter"])},
            )
        )

    failed: list[dict] = []

    def sink(task, result) -> None:
        if not result.ok:
            failed.append({"key": task.id, "error": result.error})
            log(f"[fulls] {task.id} failed at {regime.spelled}: {result.error}")

    started = time.monotonic()
    record = release.run_pass(tasks, int(workers), sink, log)
    seconds = time.monotonic() - started
    return {
        "regime": regime.spelled,
        "workers": int(workers),
        "standing": len(standing),
        "planned": len(tasks),
        "made": len(tasks) - len(failed),
        "failed": failed,
        "leg_seconds": round(seconds, 1),
        "seconds_per_picture": round(seconds / max(1, len(tasks) - len(failed)), 2),
        "pass_record": record,
    }


def write_index(resolved: dict, regime: release.Regime | None = None) -> Path:
    """The index beside the pictures, so a reading can be quoted without rebuilding it."""
    regime = regime or REGIME
    path = index_path(regime)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": SCHEMA,
                "regime": regime.spelled,
                "pictures": {key: str(value) for key, value in sorted(resolved.items())},
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


__all__ = [
    "REGIME",
    "SCHEMA",
    "UNIT",
    "FullsRefused",
    "gather",
    "href",
    "index",
    "index_path",
    "made",
    "render",
    "sheet_roots",
    "store_dir",
    "write_index",
]
