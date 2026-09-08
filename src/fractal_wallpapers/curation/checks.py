"""The two claims a release makes that only a re-render can settle.

Both are about **bytes**, and that is the point of putting them here rather than
in a test: they need a real plan, a real engine and minutes of wall clock, so
they are commands a run is followed by rather than assertions a suite makes.

* [`parity`] — the concurrent release pass and the serial one produce *the same
  file*, not merely equivalent output. Rendered both ways, compared byte for byte.
* [`replay`] — the autolevel stamp is enough. An in-band row's picture is the
  picture the switch-off path would have made, and an acting row's picture is
  rebuilt from its stamp alone with no image and no re-measurement.

The second one is the one worth having. A stamp that could not replay would mean
a release record that says *which* row shipped and cannot say which **image** that
row was — which after the operator ships on is no longer a record of the decision.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from fractal_wallpapers.coloring import autolevel
from fractal_wallpapers.curation import colorize, records, release, run_layout
from fractal_wallpapers.paths import colormap_dir


class CheckError(RuntimeError):
    """A check cannot be run on this run."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def released_rows(run: str) -> list[dict]:
    """The rows one run actually **serves**, in score rank within partition.

    Served and not merely released: a row a later review took back is still in the
    records with its scores intact, and re-deriving a picture nobody serves would
    spend the expensive half of both checks on a wallpaper that is not shipping.
    """
    rows = records.served(records.read_decisions(records.RELEASE, run))
    if not rows:
        raise CheckError(
            f"run {run!r} serves nothing this store knows about. Point --record-root at "
            f"the store the run wrote, or run the curation first."
        )
    return rows


#: What a row that does not say which pixels it shipped is assumed to have
#: shipped. Every row written before `release_geometry` existed came out of a run
#: or a pass whose release leg was 2560x1440 ss4 — there was one regime and it was
#: not a parameter — so this is a **reading of the store as it stands** and not a
#: default anything new relies on. A row written since carries its own.
UNRECORDED_REGIME = release.Regime(
    tuple(run_layout.RELEASE_RESOLUTION), run_layout.RELEASE_SUPERSAMPLE
)


def regime_of_row(row: dict) -> release.Regime:
    """Which pixels one released row is, off the row itself.

    Both checks re-derive a picture and compare **bytes**, so a geometry read from
    anywhere but the row is a check that passes or fails on what today's default
    happens to be. Gallery passes choose their regime per pass, so that is no
    longer a distinction without a difference.
    """
    return release.regime_from_geometry(row.get("release_geometry")) or UNRECORDED_REGIME


def tasks_of(run: str, rows: list[dict], directory: Path) -> list[release.Task]:
    """Release tasks rebuilt from the records — the join the record exists to carry.

    **The levelling decision is rebuilt with the rest of the task and never taken
    again.** A release row carries the whole stamp of the render that shipped
    ([`records.release_row`]), so a task built from the record inherits the curve
    the picture on disk was made through. Re-deriving here would make the parity
    check compare two renders that had each measured themselves at release
    geometry — a fair comparison of the wrong picture, and it would pass.
    """
    out = []
    for row in rows:
        location, recipe = row["location"], row["recipe"]
        out.append(
            release.Task(
                id=row["candidate"],
                row={
                    "family": location["family"],
                    "viewport": location["viewport"],
                    "maxiter": location["maxiter"],
                },
                colormap=recipe["colormap"],
                mode=recipe["mode"],
                mode_params=dict(recipe.get("mode_params") or {}),
                output=str(Path(directory) / f"{row['candidate']}.png"),
                geometry={
                    **regime_of_row(row).geometry(),
                    "maxiter": int(location["maxiter"]),
                },
                autolevel=inherited(row),
            )
        )
    return out


def inherited(row: dict) -> dict | None:
    """The levelling one released row was rendered under, packaged for a re-render.

    `None` where the row's stamp holds no curve — a row that did not act, and a
    row written before the whole stamp existed. Both re-render deciding for
    themselves, which is what they did the first time.
    """
    stamp = row.get("autolevel") or {}
    if not stamp.get("curve"):
        return None
    return autolevel.borrowed_from(
        stamp,
        key=str(row.get("candidate") or ""),
        store="release row",
        was=str((stamp.get("provenance") or {}).get("curve") or autolevel.DERIVED),
    )


def parity(run: str, rows: int = 2, workers: int = release.DEFAULT_WORKERS, log=print) -> dict:
    """Render a prefix of a real release plan serially and concurrently, and compare."""
    directory = run_layout.run_dir(run) / "parity"
    plan = tasks_of(run, released_rows(run)[: max(1, int(rows))], directory)
    log(f"[parity] {len(plan)} row(s) of run {run}, both ways, into {directory}")
    return release.parity(plan, workers, directory, log)


def replay(run: str, log=print) -> dict:
    """Re-derive every released picture from its own record, and compare the bytes.

    Two arms, because the operator has two outcomes and only one of them makes a
    new file:

    * **in band** — the stamp says it did not act, so the picture must be the one
      the operator would never have touched. Re-rendered with the switch off; the
      two must be identical.
    * **acted** — the stamp carries the whole curve, so the leveled stop list is
      rebuilt from it with no image and no re-measurement, and the render through
      those stops must be identical.

    **Both arms inherit the decision and neither retakes it.** Which arm a row
    takes is read off the stamp the shipped render wrote, never off a fresh
    measurement — and that is what keeps the in-band arm honest now that a
    release inherits its curve. An inherited in-band row is unlevelled at every
    geometry, so the switch-off render is still exactly it; a check that
    re-measured at release geometry would find that row *out* of band, level it,
    and report a difference in the picture rather than in itself.
    """
    directory = run_layout.run_dir(run) / "replay"
    directory.mkdir(parents=True, exist_ok=True)
    from fractal_wallpapers import engine
    from fractal_wallpapers.models import palette_sets, renders

    cyclic = palette_sets.cyclic()
    stamps = _stamps(run)
    out = []
    for row in released_rows(run):
        identifier = row["candidate"]
        shipped = run_layout.run_dir(run) / "release" / f"{identifier}.png"
        if not shipped.is_file():
            out.append({"candidate": identifier, "verdict": "NO_PICTURE"})
            continue
        # The row's own stamp first and the sidecar second. Both are written by
        # the same pass about the same render; the row is preferred because it is
        # the record a reader of the store would reach for, and a run whose
        # `autolevel_stamps.jsonl` was swept still checks.
        stamp = row.get("autolevel") or stamps.get(identifier)
        recipe = row["recipe"]
        geometry = {
            **regime_of_row(row).geometry(),
            "maxiter": int(row["location"]["maxiter"]),
        }
        again = directory / f"{identifier}.png"
        spec = renders.spec_of(
            colorize.render_row(
                {"family": row["location"]["family"], "viewport": row["location"]["viewport"]},
                recipe["mode"],
                recipe["colormap"],
                cyclic,
                geometry,
            ),
            again,
        )
        if stamp is None or not stamp.get("acted"):
            arm = "in band -> the switch-off render"
            was = os.environ.get(autolevel.SWITCH_ENV)
            os.environ[autolevel.SWITCH_ENV] = "0"
            try:
                engine.run("render", spec)
            finally:
                if was is None:
                    os.environ.pop(autolevel.SWITCH_ENV, None)
                else:
                    os.environ[autolevel.SWITCH_ENV] = was
        else:
            arm = "acted -> replayed from the stamp"
            entry = json.loads(
                (colormap_dir() / f"{recipe['colormap']}.json").read_text(encoding="utf-8")
            )
            stops = autolevel.stops_from_stamp(stamp, entry["stops"])
            where = directory / f"{identifier}.colormap"
            autolevel.overriding_colormap(recipe["colormap"], stops, entry.get("kind"), where)
            engine.run("render", {**spec, "colormap_dir": str(where)})
        same = _sha256(shipped) == _sha256(again)
        log(f"[replay] {identifier} {arm}: {'identical' if same else 'DIFFERS'}")
        out.append(
            {
                "candidate": identifier,
                "arm": arm,
                "acted": bool(stamp and stamp.get("acted")),
                "shipped_sha256": _sha256(shipped),
                "replayed_sha256": _sha256(again),
                "verdict": "IDENTICAL" if same else "DIFFERS",
            }
        )
    held = [row for row in out if row["verdict"] == "IDENTICAL"]
    return {
        "run": run,
        "rows": len(out),
        "identical": len(held),
        "acted": sum(1 for row in out if row.get("acted")),
        "in_band": sum(1 for row in out if row.get("arm") and not row.get("acted")),
        "held": len(held) == len(out) and bool(out),
        "detail": out,
    }


def _stamps(run: str) -> dict:
    path = run_layout.run_dir(run) / "release" / "autolevel_stamps.jsonl"
    if not path.is_file():
        return {}
    return {
        row["id"]: row["autolevel"]
        for row in (
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }


__all__ = [
    "UNRECORDED_REGIME",
    "CheckError",
    "parity",
    "regime_of_row",
    "released_rows",
    "replay",
    "tasks_of",
]
