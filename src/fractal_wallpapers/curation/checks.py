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
from fractal_wallpapers.curation import colorize, records, release
from fractal_wallpapers.curation import run as run_module
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


def tasks_of(run: str, rows: list[dict], directory: Path) -> list[release.Task]:
    """Release tasks rebuilt from the records — the join the record exists to carry."""
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
                output=str(Path(directory) / f"{row['candidate']}.png"),
                geometry={
                    "resolution": list(run_module.RELEASE_RESOLUTION),
                    "supersample": run_module.RELEASE_SUPERSAMPLE,
                    "maxiter": int(location["maxiter"]),
                },
            )
        )
    return out


def parity(run: str, rows: int = 2, workers: int = release.DEFAULT_WORKERS, log=print) -> dict:
    """Render a prefix of a real release plan serially and concurrently, and compare."""
    directory = run_module.run_dir(run) / "parity"
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
    """
    directory = run_module.run_dir(run) / "replay"
    directory.mkdir(parents=True, exist_ok=True)
    from fractal_wallpapers import engine
    from fractal_wallpapers.models import palette_sets, renders

    cyclic = palette_sets.cyclic()
    stamps = _stamps(run)
    out = []
    for row in released_rows(run):
        identifier = row["candidate"]
        shipped = run_module.run_dir(run) / "release" / f"{identifier}.png"
        if not shipped.is_file():
            out.append({"candidate": identifier, "verdict": "NO_PICTURE"})
            continue
        stamp = stamps.get(identifier)
        recipe = row["recipe"]
        geometry = {
            "resolution": list(run_module.RELEASE_RESOLUTION),
            "supersample": run_module.RELEASE_SUPERSAMPLE,
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
    path = run_module.run_dir(run) / "release" / "autolevel_stamps.jsonl"
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


__all__ = ["CheckError", "parity", "released_rows", "replay", "tasks_of"]
