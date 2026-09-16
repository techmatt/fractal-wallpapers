"""The plate a plane's dots are drawn over, and the three thumbnails behind every dot.

Both reach the engine through its own doors — the plate through
[`engine.render_report`], every thumbnail through [`curation.colorize.render`], which is
[`engine.run`] — so Rust makes every pixel here as everywhere else.

**Three workers, below normal.** `engine.run` spawns below-normal on its own
(`process_control.child_priority_flags`), so the count is the only thing this file
decides, and three is the rule for every leg on this box.

The gallery thumbnail is the row's own recipe at thumbnail geometry. Where its run
recorded the tone curve it is drawn **through that curve** — borrowed, the way a release
inherits one — so the thumbnail and the row are the same picture at a smaller size. Where
the operator did not act it is drawn plain, and where the curve is `lost` the operator
decides again at thumbnail size, which is the nearest picture there is and is not claimed
as the row's own: the record's `tone` says which of the three it was.
"""

from __future__ import annotations

import json
import shutil
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

WORKERS = 3

#: Samples a pixel along each axis, for the plate and the thumbnails both.
SUPERSAMPLE = 2

#: The palette recipe at the engine's identity, spelled out because the plate is a raw
#: engine spec rather than a candidate recipe.
IDENTITY_PALETTE = {
    "gamma": 1.0,
    "cycles": 1.0,
    "phase": 0.0,
    "reverse": False,
    "mirror": False,
    "transfer": {"kind": "value"},
    "rolloff": {"kind": "none"},
}

_CYCLIC = None


def render_plate(family: dict, resolution, colormap: str, out: Path) -> dict:
    """One `smooth` render of the family's home view through `colormap`; its report."""
    from fractal_wallpapers import engine
    from fractal_wallpapers.paths import colormap_dir

    view = engine.home_view(family)
    spec = {
        "schema": 1,
        "family": family,
        "viewport": view,
        "resolution": list(resolution),
        "supersample": SUPERSAMPLE,
        "maxiter": int(engine.maxiter_for([view["width"]])[0]),
        "coloring": {"kind": "field", "field": {"kind": "smooth"}, "transform": "linear"},
        "palette": dict(IDENTITY_PALETTE),
        "colormap": colormap,
        "colormap_dir": str(colormap_dir()),
        "output": str(out),
    }
    started = time.time()
    report = engine.render_report(spec)
    return {
        "viewport": view,
        "resolution": list(resolution),
        "supersample": SUPERSAMPLE,
        "maxiter": spec["maxiter"],
        "colormap": colormap,
        "mode": "smooth",
        "image": out.name,
        "seconds": round(time.time() - started, 2),
        "bytes": out.stat().st_size if out.is_file() else None,
        "engine_report": report,
    }


def job_of(
    recipe: dict, picture: Path, resolution, supersample: int, borrowed: dict | None = None
) -> dict:
    """One thumbnail's job from a recipe as the ledger stores it, whole.

    Every member that decides a picture is carried across — mode, settings, curve, map,
    palette — and the operator runs exactly where the recipe's own stamp switched it on.
    A location view has no stamp and is drawn plain.
    """
    return {
        "picture": str(picture),
        "family": recipe["family"],
        "viewport": recipe["viewport"],
        "maxiter": int(recipe["maxiter"]),
        "mode": recipe["mode"],
        "mode_params": dict(recipe.get("mode_params") or {}),
        "curve": recipe.get("curve"),
        "colormap": recipe["colormap"],
        "palette": recipe.get("palette"),
        "level": ((recipe.get("autolevel") or {}).get("switch")) == "on",
        "borrowed": borrowed,
        "resolution": list(resolution),
        "supersample": int(supersample),
    }


def draw(job: dict) -> dict:
    """One thumbnail, in a worker. **Module level** — a Windows pool spawns."""
    global _CYCLIC
    from fractal_wallpapers.curation import colorize

    if _CYCLIC is None:
        _CYCLIC = colorize.cyclic()
    out = Path(job["picture"])
    started = time.time()
    row = {"family": job["family"], "viewport": job["viewport"], "maxiter": int(job["maxiter"])}
    try:
        colorize.render(
            row,
            str(job["mode"]),
            str(job["colormap"]),
            _CYCLIC,
            out,
            render_geometry={
                "resolution": list(job["resolution"]),
                "supersample": int(job["supersample"]),
                "maxiter": int(job["maxiter"]),
            },
            level=bool(job["level"]),
            mode_params=dict(job.get("mode_params") or {}),
            curve=job.get("curve") or None,
            palette=dict(job.get("palette") or {}) or None,
            borrowed=job.get("borrowed"),
        )
    except Exception as failure:  # noqa: BLE001 — a failed thumbnail is a recorded fact
        return {"picture": str(out), "made": False, "failed": f"{failure!r}"[:300]}
    return {"picture": str(out), "made": True, "seconds": round(time.time() - started, 3)}


def clear(directory: Path) -> int:
    """Empty a thumbnail directory of what an earlier run left, and say how much.

    A thumbnail is named by its dot's index, and a rerun that moved one dot renumbers every
    dot after it — so a picture left over from the last run is a picture of the wrong
    place under the right name.
    """
    if not directory.is_dir():
        return 0
    gone = 0
    for path in directory.iterdir():
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        gone += 1
    return gone


def draw_all(jobs: list[dict], workers: int = WORKERS, every: int = 60) -> dict:
    """Every thumbnail through a pool of `workers`; the tally."""
    started = time.time()
    made = failed = 0
    why: list[str] = []
    print(f"[{time.strftime('%H:%M:%S')}] {len(jobs):,} thumbnails, {workers} workers", flush=True)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for index, result in enumerate(pool.map(draw, jobs, chunksize=4), start=1):
            if result.get("failed"):
                failed += 1
                why.append(f"{Path(result['picture']).name}: {result['failed']}")
            elif result["made"]:
                made += 1
            if index % every == 0 or index == len(jobs):
                rate = index / max(time.time() - started, 1e-6)
                print(
                    f"[{time.strftime('%H:%M:%S')}] {index:,}/{len(jobs):,} made={made} "
                    f"failed={failed} {rate:.2f}/s",
                    flush=True,
                )
    return {
        "jobs": len(jobs),
        "made": made,
        "failed": failed,
        "why": why[:40],
        "seconds": round(time.time() - started, 1),
    }


def write_json(path: Path, payload, indent: int | None = None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=indent)
    path.write_text(text + ("\n" if indent else ""), encoding="utf-8", newline="\n")
