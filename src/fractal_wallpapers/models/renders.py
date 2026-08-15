"""The render cache: the pictures the finished-render judges are trained on.

A finished-render row records a verdict and the whole recipe that made the
picture it is a verdict on. It does not record the picture — a corpus of eight
thousand JPEGs is not text and would not survive the history rules — so the
pictures are **regenerated here**, from the rows, through this repository's own
coloring path, into the ignored `artifacts/` tree.

That regeneration is the point rather than an inconvenience. The source project's
crops are not coming across: a head trained on pictures made by one renderer and
deployed against pictures made by another is measuring the difference between the
two renderers as much as the difference between two locations. Everything the
judge ever sees — training, scoring, acceptance — is made here.

## One job per picture, and the picture is the whole recipe

A job is a resolved row's render identity: the place, the mode with its own
settings, the curve, the map, and every knob of the palette pass. Rows that share
all of that share a picture and one file. The file is named for the sha256 of the
job, so the name is a function of the recipe alone: a run that is re-planned
after new rows land re-uses every file it already has, and nothing has to remember
which index a job had.

## Resumable, and honest about how long it will take

The plan is **shuffled by a seed**, so any prefix of it is a fair sample of the
whole: a bounded rehearsal over the first fifty jobs projects the full build
without the deep frames all landing at one end. A job whose file is already on
disk is skipped before its field is iterated, so a killed build continues instead
of restarting.

## What a mode name becomes

The row names a mode and a curve separately, because the curve **replaces** the
mode's own rather than composing with it — that is what the corpora did, and a
composed curve would be a picture nobody judged. So a job does not name a mode to
the engine: it reads the mode's coloring out of the engine's own catalog, puts the
row's curve in it, puts the row's trap settings in it, and hands over the result
in full. The catalog is the engine's, so a mode cannot mean one thing here and
another there.
"""

from __future__ import annotations

import hashlib
import json
import random
import time
from dataclasses import dataclass
from pathlib import Path

from fractal_wallpapers import engine
from fractal_wallpapers.labeling import finished
from fractal_wallpapers.paths import colormap_dir, repo_root

#: The schema every plan and manifest row carries.
SCHEMA = 1

#: The shuffle's seed. Fixed, and recorded in the plan: the prefix honesty above
#: is only true of a plan somebody can rebuild.
SEED = 0

#: How much of the sha256 names a file. Sixteen hex characters is 64 bits; at
#: eight thousand pictures the chance of any two colliding is about 2e-15.
NAME_LENGTH = 16


def cache_dir(head: str) -> Path:
    """Where one judge's pictures live. Ignored, and regenerable from the rows."""
    return repo_root() / "artifacts" / "renders" / finished.head_of(head)


def crop_dir(head: str) -> Path:
    return cache_dir(head) / "crops"


def plan_path(head: str) -> Path:
    return cache_dir(head) / "plan.jsonl"


def build_record_path(head: str) -> Path:
    return cache_dir(head) / "build.json"


def log_path(head: str) -> Path:
    return cache_dir(head) / "build.log"


@dataclass(frozen=True)
class Job:
    """One picture to make, and where it goes."""

    name: str
    row: dict

    @property
    def output(self) -> Path:
        return crop_dir(self.row["_head"]) / f"{self.name}.jpg"


def job_name(row: dict) -> str:
    """The file name for one row's picture: a digest of what makes it.

    Everything the engine is told goes into the digest and nothing else does, so
    two rows that would produce the same picture produce the same name and one
    file — and a row that differs anywhere at all gets its own.
    """
    material = json.dumps(spec_of(row, Path("x")), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:NAME_LENGTH]


_CATALOG: dict[str, dict] | None = None


def catalog() -> dict[str, dict]:
    """`{mode: its coloring}` from the engine's own list, read once."""
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = {mode["name"]: mode["coloring"] for mode in engine.modes()}
    return _CATALOG


def coloring_of(row: dict) -> dict:
    """The mode's coloring, with this row's curve and trap settings put into it.

    The curve lands on the **base** of a composite and nowhere else: the texture
    is a screen over the base and the corpora set one curve per render, which is
    the one the base is read through.
    """
    mode = row["mode"]
    known = catalog()
    if mode not in known:
        raise RenderCacheError(f"the engine has no mode named {mode!r}")
    coloring = json.loads(json.dumps(known[mode]))
    curve = row["curve"]
    settings = row.get("mode_params") or {}

    if coloring["kind"] == "field":
        coloring["transform"] = curve
    elif coloring["kind"] == "composite":
        coloring["base"]["transform"] = curve
    elif coloring["kind"] == "direct":
        coloring["transform"] = curve
        for name, value in settings.items():
            if name not in ("opacity", "threshold"):
                raise RenderCacheError(f"{mode}: no setting named {name!r}")
            coloring[name] = value
        settings = {}
    if settings:
        raise RenderCacheError(f"{mode} takes no settings, and this row carries {settings}")
    return coloring


def spec_of(row: dict, output: Path) -> dict:
    """The JSON object the engine reads, for one row."""
    render = row["render"]
    recipe = row["recipe"]
    return {
        "schema": 1,
        "family": row["family"],
        "viewport": row["viewport"],
        "resolution": list(render["resolution"]),
        "supersample": int(render["supersample"]),
        "maxiter": int(render["maxiter"]),
        "coloring": coloring_of(row),
        "palette": {
            "gamma": recipe["gamma"],
            "cycles": recipe["cycles"],
            "phase": recipe["phase"],
            "reverse": recipe["reverse"],
            "mirror": recipe["mirror"],
            "transfer": recipe["transfer"],
            "rolloff": recipe["rolloff"],
        },
        "colormap": row["colormap"],
        "colormap_dir": str(colormap_dir()),
        "output": str(output),
    }


class RenderCacheError(RuntimeError):
    """A row that cannot become a picture."""


def plan(head: str, seed: int = SEED) -> list[dict]:
    """Every picture one judge's corpus needs, shuffled.

    One row per *picture*, not per verdict: the evaluation side is in the plan
    with everything else, because a held-out picture has to be scored through the
    same renderer the training side was learned from or the number measures the
    render as much as the head.
    """
    head = finished.head_of(head)
    rows = finished.resolved(head).scored()
    jobs: dict[str, dict] = {}
    for row in rows:
        stripped = {key: value for key, value in row.items() if not key.startswith("_")}
        stripped["_head"] = head
        name = job_name(stripped)
        jobs.setdefault(
            name,
            {
                "schema": SCHEMA,
                "name": name,
                "head": head,
                "batch": row["batch"],
                "score": row["score"],
                "partition": row.get("partition"),
                "family": row["family"],
                "viewport": row["viewport"],
                "mode": row["mode"],
                "mode_params": row.get("mode_params") or {},
                "curve": row["curve"],
                "colormap": row["colormap"],
                "recipe": row["recipe"],
                "render": row["render"],
            },
        )
    ordered = [jobs[name] for name in sorted(jobs)]
    random.Random(seed).shuffle(ordered)
    return ordered


def write_plan(head: str, jobs: list[dict], seed: int = SEED) -> Path:
    path = plan_path(head)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for job in jobs:
            handle.write(json.dumps({**job, "seed": seed}, ensure_ascii=False) + "\n")
    return path


def read_plan(head: str) -> list[dict]:
    path = plan_path(head)
    if not path.is_file():
        raise RenderCacheError(f"{path} is missing — plan the build before running it")
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def build(head: str, limit: int | None = None, log: Path | None = None) -> dict:
    """Render every picture of the plan that is not already on disk."""
    head = finished.head_of(head)
    jobs = read_plan(head)
    if limit is not None:
        jobs = jobs[:limit]
    crops = crop_dir(head)
    crops.mkdir(parents=True, exist_ok=True)
    log = log or log_path(head)
    log.parent.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()
    rendered = skipped = 0
    interior = 0.0
    with log.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"--- build {head}: {len(jobs)} jobs ---\n")
        handle.flush()
        for index, job in enumerate(jobs, start=1):
            output = crops / f"{job['name']}.jpg"
            if output.is_file():
                skipped += 1
                continue
            report = engine.run("render", spec_of({**job, "_head": head}, output))
            rendered += 1
            interior += float(report.get("interior_fraction", 0.0))
            if rendered % 25 == 0 or index == len(jobs):
                spent = time.monotonic() - started
                rate = spent / max(rendered, 1)
                left = (len(jobs) - index) * rate
                handle.write(
                    f"{index}/{len(jobs)}  rendered {rendered}  skipped {skipped}  "
                    f"{rate:.2f}s each  {left / 60:.1f} min left\n"
                )
                handle.flush()

    seconds = time.monotonic() - started
    on_disk = sorted(crops.glob("*.jpg"))
    return {
        "schema": SCHEMA,
        "head": head,
        "jobs": len(jobs),
        "rendered": rendered,
        "skipped": skipped,
        "seconds": round(seconds, 1),
        "seconds_each": round(seconds / rendered, 3) if rendered else None,
        "mean_interior_fraction": round(interior / rendered, 4) if rendered else None,
        "files": len(on_disk),
        "bytes": sum(path.stat().st_size for path in on_disk),
        "partial": limit is not None,
        "recipe": {
            "geometry": "the row's own — the corpora rendered at 1280x720, two samples "
            "per pixel per axis, reconstructed with lanczos3",
            "jpeg_quality": 90,
            "seed": SEED,
        },
    }


#: What a regenerated picture is compared against: a JPEG of the judged one, at
#: this quality, against the judged one itself. "The same picture" is a claim,
#: and this is the scale it has to be true on — a difference smaller than what
#: re-compressing the original costs is not a difference anybody judged.
JPEG_FLOOR_QUALITY = 75


def verify(root: Path, head: str, sample: int = 60, seed: int = 0) -> dict:
    """How close the regenerated pictures are to the ones that were judged.

    The whole recipe — gamma, traversal, fold, the edge transfer, the highlight
    rolloff — is reproduced from a record rather than shared, and every one of
    those knobs is a way to be quietly wrong: the picture still looks like a
    fractal, the head still trains, and the verdict is about something else. So
    the pairs are compared directly, at the head's own input size, against the
    only honest yardstick available — what a plain re-compression of the judged
    picture costs.

    This is a build-era check and it needs the source project present. It found
    the one defect it was written to find: an edge-transfer floor two orders of
    magnitude too small, which left a third of the tonal range wrong on the 1,303
    rows that use it and nothing wrong anywhere else.
    """
    import io
    import random as _random

    import numpy
    from PIL import Image

    from fractal_wallpapers.labeling import finished_import
    from fractal_wallpapers.paths import colormap_dir

    head = finished.head_of(head)
    modes = finished_import.engine_modes()
    cyclic = finished_import.cyclic_maps(finished_import.palette_names(root, head), colormap_dir())
    crops = crop_dir(head)

    pairs = []
    for source_batch in sorted(finished_import.SOURCES[head]):
        directory = finished_import.batch_dir(root, head, source_batch)
        if not (directory / "crops").is_dir():
            continue
        for line in (directory / "images.jsonl").read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            source_row = json.loads(line)
            judged = directory / "crops" / f"{source_row['image_id']}.jpg"
            if not judged.is_file():
                continue
            row = _row_of(source_row, head, modes, cyclic)
            ours = crops / f"{job_name(row)}.jpg"
            if ours.is_file():
                pairs.append((judged, ours, row))

    if not pairs:
        raise RenderCacheError(
            f"no picture of the {head} corpus has both a judged crop under {root} and a "
            f"regenerated one here. There is nothing to compare."
        )
    drawn = _random.Random(seed).sample(pairs, min(sample, len(pairs)))
    size = (head_module_target()[0], head_module_target()[1])

    def read(path: Path):
        with Image.open(path) as opened:
            return numpy.asarray(
                opened.convert("RGB").resize(size, Image.BICUBIC), dtype=numpy.float64
            )

    deltas, floors, worst = [], [], []
    for judged, ours, row in drawn:
        theirs = read(judged)
        delta = float(numpy.abs(theirs - read(ours)).mean())
        buffer = io.BytesIO()
        Image.fromarray(theirs.astype("uint8")).save(buffer, "JPEG", quality=JPEG_FLOOR_QUALITY)
        buffer.seek(0)
        with Image.open(buffer) as opened:
            recompressed = numpy.asarray(opened.convert("RGB"), dtype=numpy.float64)
        deltas.append(delta)
        floors.append(float(numpy.abs(theirs - recompressed).mean()))
        worst.append((delta, row["mode"], row["colormap"], row["recipe"]["transfer"]["kind"]))

    worst.sort(reverse=True)
    array = numpy.asarray(deltas)
    floor = float(numpy.median(floors))
    return {
        "head": head,
        "compared": len(drawn),
        "available": len(pairs),
        "seed": seed,
        "scale": "mean absolute channel difference, 0-255, at the head's own input size",
        "delta": {
            "median": float(numpy.median(array)),
            "p90": float(numpy.percentile(array, 90)),
            "max": float(array.max()),
        },
        "recompression_floor": {
            "quality": JPEG_FLOOR_QUALITY,
            "median": floor,
            "what": "a JPEG of the judged picture against the judged picture",
        },
        "closer_than_a_recompression": int((array <= floor).sum()),
        "furthest": [
            {"delta": round(delta, 2), "mode": mode, "colormap": name, "transfer": transfer}
            for delta, mode, name, transfer in worst[:5]
        ],
    }


def head_module_target() -> tuple[int, int]:
    """The head's input size, from the head rather than restated."""
    from fractal_wallpapers.models import head as head_module

    return head_module.TARGET_WIDTH, head_module.TARGET_HEIGHT


def _row_of(source_row: dict, head: str, modes: set, cyclic: set) -> dict:
    """One source row as the store row it becomes — the same conversion, once."""
    from fractal_wallpapers.labeling import finished_import

    render, provenance = source_row["render"], source_row.get("provenance") or {}
    params = finished_import.color_params_of(provenance)
    colormap = render["palette"]
    return {
        "family": finished_import.family_of(render, provenance),
        "viewport": {
            "center_re": str(render["cx"]),
            "center_im": str(render["cy"]),
            "width": str(render["fw"]),
        },
        "mode": finished_import.mode_of(render, provenance, modes),
        "mode_params": finished_import.mode_params_of(render, provenance),
        "curve": finished_import.curve_of(params),
        "colormap": colormap,
        "recipe": finished_import.recipe_of(
            params,
            bool(provenance.get("transfer_dropped")),
            colormap in cyclic,
            colormap,
            finished_import.rolloff_of(render, provenance),
        ),
        "render": finished_import.render_of(render),
        "_head": head,
    }


def missing(head: str) -> list[dict]:
    """The plan's jobs whose picture is not on disk."""
    crops = crop_dir(head)
    return [job for job in read_plan(head) if not (crops / f"{job['name']}.jpg").is_file()]


def crop_of(head: str, row: dict) -> Path:
    """Where one row's picture is, whether or not it has been made yet."""
    stripped = {key: value for key, value in row.items() if not key.startswith("_")}
    stripped["_head"] = head
    return crop_dir(head) / f"{job_name(stripped)}.jpg"


__all__ = [
    "JPEG_FLOOR_QUALITY",
    "NAME_LENGTH",
    "SCHEMA",
    "SEED",
    "Job",
    "RenderCacheError",
    "build",
    "build_record_path",
    "cache_dir",
    "catalog",
    "coloring_of",
    "crop_dir",
    "crop_of",
    "job_name",
    "log_path",
    "missing",
    "plan",
    "plan_path",
    "read_plan",
    "spec_of",
    "verify",
    "write_plan",
]
