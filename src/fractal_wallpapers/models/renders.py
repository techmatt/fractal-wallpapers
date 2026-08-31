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

One catalogued setting is decided by the family rather than by the name, and it
is put in here for the same reason the curve is: what goes to the engine has to
be the whole picture, and the job name is a digest of exactly that. See
[`coloring_of`] and `engine.pixel_is_z0`.
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
from fractal_wallpapers.paths import colormap_dir, under

#: The schema every plan and manifest row carries.
SCHEMA = 1

#: The shuffle's seed. Fixed, and recorded in the plan: the prefix honesty above
#: is only true of a plan somebody can rebuild.
SEED = 0

#: How much of the sha256 names a file. Sixteen hex characters is 64 bits; at
#: eight thousand pictures the chance of any two colliding is about 2e-15.
NAME_LENGTH = 16

#: How many engines a cache build drives at once, and **one is the measured
#: answer** rather than the render pool's three.
#:
#: The engine iterates one field across every core it can see, so a second
#: process does not find an idle machine — it finds this one. Measured over
#: adjacent hundred-job slices of the same shuffled plan, 2026-08-30: **2.11 s a
#: picture serially against 2.65 s at three**, the same direction and the same
#: size as `discovery.scoring`'s fan-out and the flip leg's. The pool rule is a
#: ceiling on how much of the desktop a leg may take, not a floor, and a leg
#: whose one worker already holds twelve cores is at it.
#:
#: The knob stays because the measurement will want re-taking on a machine with
#: more cores than one field can fill; the priority half of the rule is
#: `engine.run`'s and needs nothing here at any count.
DEFAULT_WORKERS = 1


def cache_dir(head: str) -> Path:
    """Where one judge's pictures live. Ignored, and regenerable from the rows."""
    return under("renders", finished.head_of(head))


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


#: Every row member [`spec_of`] reads. Declared here so the two sets below can be
#: held to covering it: `tests/test_renders.py` records what `spec_of` actually
#: reaches for and fails when this list stops being that.
SPEC_MEMBERS: tuple[str, ...] = (
    "family",
    "viewport",
    "render",
    "mode",
    "mode_params",
    "curve",
    "colormap",
    "recipe",
)

#: **The field-side members: what a dumped scalar field is a function of.** The
#: place, the geometry, and the field the mode names with the curve it is read
#: through. Everything a `dump-field` spends before it stops.
#:
#: **A mode that is not shareable never has a field cached under this name at
#: all**, and `itinerary` is the case worth knowing: `colorize.shareable` is false
#: for it — a modulate has no single scalar index behind it and the engine refuses
#: to dump one — so no itinerary field is ever written, and every itinerary
#: candidate takes the render path. The field cache is moot for it in both
#: directions: an axis added to the modulate's coloring can rename its *pictures*
#: and cannot rename a field, because there are none.
#:
#: The split itself still answers a question about that mode. What a *coloring* is
#: a function of, as opposed to what a recolour spends afterwards, is exactly the
#: half [`fractal_wallpapers.coloring.texture_flat`] keys its register on — one
#: probe there answers for all thirty-two maps at a location. It declares its own
#: list rather than importing this one, because that register is tracked and
#: [`job_name`] digests `colormap_dir`, which is a path on the machine that took
#: the reading.
FIELD_IDENTITY: tuple[str, ...] = (
    "family",
    "viewport",
    "render",
    "mode",
    "mode_params",
    "curve",
)

#: The rest, and the reason the split exists: a recolor spends these *after* the
#: field is on disk, over and over, without iterating anything. Two candidates
#: differing only here are one field and thirty-two pictures.
RECOLOR_MEMBERS: tuple[str, ...] = ("colormap", "recipe")

#: What the recolor half is pinned to when a **field** is being named rather than
#: a picture. Constants, so they contribute nothing that varies — but they have to
#: be present, because the digest goes through [`spec_of`], which is the one
#: derivation this project has of what the engine is told.
FIELD_COLORMAP = "_field"


def field_job_name(
    family: dict,
    viewport: dict,
    render: dict,
    mode: str,
    curve: str,
    mode_params: dict | None = None,
) -> str:
    """The name a **dumped field** is cached under: [`FIELD_IDENTITY`], digested.

    A field cache keyed on a hand-written dict is one engine axis away from two
    different fields sharing a name — and a shared name is not a wrong picture,
    it is thirty-two wrong pictures, because every candidate recolours whichever
    field was dumped first. So the members are named once, above, and this
    refuses rather than proceeds when the two halves stop covering
    [`SPEC_MEMBERS`]: an axis added to the engine and to `spec_of` has to be
    *classified* — field-side or recolour-side — and cannot be left out by being
    forgotten at a call site.

    The digest is [`job_name`]'s, over the same [`spec_of`] every picture goes
    through, so a field and the smooth render of the same row are named by one
    derivation rather than two that can drift.
    """
    uncovered = set(SPEC_MEMBERS) - set(FIELD_IDENTITY) - set(RECOLOR_MEMBERS)
    if uncovered:
        raise RenderCacheError(
            f"{sorted(uncovered)} is read by spec_of and is in neither FIELD_IDENTITY nor "
            f"RECOLOR_MEMBERS, so a dumped field's name does not say whether it depends on "
            f"it. Classify it: field-side members go in the digest, recolour-side members "
            f"are spent after the field exists."
        )
    field_side = {
        "family": family,
        "viewport": viewport,
        "render": render,
        "mode": mode,
        "mode_params": dict(mode_params or {}),
        "curve": curve,
    }
    missing = [member for member in FIELD_IDENTITY if member not in field_side]
    if missing:
        raise RenderCacheError(
            f"{missing} is field-side and this caller supplied no value for it. A field "
            f"cached without it would be shared by every value it can take."
        )
    return job_name(
        {
            **field_side,
            "colormap": FIELD_COLORMAP,
            "recipe": finished.recipe(mirror=False),
        }
    )


_CATALOG: dict[str, dict] | None = None


def catalog() -> dict[str, dict]:
    """`{mode: its coloring}` from the engine's own list, read once."""
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = {mode["name"]: mode["coloring"] for mode in engine.modes()}
    return _CATALOG


#: The field kind an address is written under, and where a *head* address opens
#: when the pixel is `z₀`.
#:
#: Matt's verdict of 2026-08-17: on a dynamical plane the `z₀` address spells its
#: leading symbol from the pixel's own angular sector, which draws a hard wedge
#: seam along the axes; `z₁` opens the address one step in, so every symbol is one
#: the recurrence produced. On a parameter plane `z₀ = 0` for every pixel, there is
#: no wedge to remove, and the engine refuses `z1` there.
#:
#: `ITINERARY` is the **field**'s name and not the mode's: `tail_itinerary` reads
#: the same field under a different window, so a join on the mode name would miss
#: it and a join on the field name catches both. That is the whole reason the
#: split below is written against `start` rather than against the mode.
ITINERARY = "itinerary"
Z1 = "z1"

#: The windows a caller asked for by name, which the plane does not get to move.
#:
#: A `start` the catalog wrote out is a decision already taken — `tail` is the
#: only one today — and the plane rule below applies to the one window that has a
#: leading digit to argue about. Absent means the field's own default, `z0`, which
#: is exactly the case the rule is for.
NAMED_STARTS = frozenset({"tail"})


def open_the_address(coloring: dict, family: dict) -> dict:
    """Put the plane's answer for where a **head** address opens into `coloring`.

    The **catalog listing has no family**, so the coloring `catalog()` holds is the
    parameter-plane form and this is what makes it the row's. Written explicitly
    rather than left to the engine's default: the job name is a digest of the spec
    that goes over the wire, so a choice the engine made after the digest would let
    two different pictures share one file.

    Every field of the coloring is walked, not just the modulate's texture, because
    the second way an address could arrive is the one nobody would look for. The
    plane is asked about only when there is an address to open, so the modes that
    read no address are untouched by a family the split has no answer for.

    **A window the catalog named is left exactly as it arrived.** `tail_itinerary`
    carries `"start": "tail"`, which is not a start the plane decides — a tail
    address never reads `z₀`, so there is no wedge for `z₁` to remove and the mode
    is one coloring on both planes. Overwriting it here would render the head mode
    under the tail mode's name, and the engine would not refuse it: `z1` is legal
    on the plane this branch is about. See [`NAMED_STARTS`].
    """
    addresses = [
        field
        for field in _fields_of(coloring)
        if field.get("kind") == ITINERARY and field.get("start") not in NAMED_STARTS
    ]
    if addresses and engine.pixel_is_z0(family):
        for field in addresses:
            field["start"] = Z1
    return coloring


def _fields_of(coloring: dict) -> list[dict]:
    """Every field this coloring reads. A direct trap makes none."""
    if coloring["kind"] == "field":
        return [coloring["field"]]
    if coloring["kind"] in ("composite", "modulate"):
        return [coloring["base"]["field"], coloring["texture"]["field"]]
    return []


def coloring_of(row: dict) -> dict:
    """The mode's coloring, with this row's curve, trap settings and plane in it.

    The curve lands on the **base** of a composite or a modulate and nowhere else:
    the texture lies over the base and the corpora set one curve per render, which
    is the one the base is read through.
    """
    mode = row["mode"]
    known = catalog()
    if mode not in known:
        raise RenderCacheError(f"the engine has no mode named {mode!r}")
    coloring = json.loads(json.dumps(known[mode]))
    curve = row["curve"]
    settings = row.get("mode_params") or {}
    open_the_address(coloring, row["family"])

    if coloring["kind"] == "field":
        coloring["transform"] = curve
    elif coloring["kind"] in ("composite", "modulate"):
        coloring["base"]["transform"] = curve
    elif coloring["kind"] == "direct":
        # The curve is NOT set here, and that is what the corpora did. A direct
        # trap has no field: its colour key is how near the orbit came, as a
        # fraction of the threshold, and the source's own path samples the
        # gradient at that key untouched — no stretch, no curve, no gamma. Two
        # rows that differ only in a curve are therefore the same picture here,
        # which is why they share one file.
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


def render_one(job: dict) -> float | None:
    """One picture, wherever this is called — in the caller or in a worker.

    Module level and taking a plain dict because a Windows pool **spawns**: a
    closure over the plan would not pickle, and a worker re-imports this module
    and rebuilds [`catalog`] once for the several thousand jobs it is handed.
    Returns the field's interior fraction, or `None` for a picture already on
    disk — the resume check is made here rather than before the hand-off, so a
    file an earlier launch finished costs a `stat` instead of a render.
    """
    output = crop_dir(job["_head"]) / f"{job['name']}.jpg"
    if output.is_file():
        return None
    report = engine.run("render", spec_of(job, output))
    return float(report.get("interior_fraction", 0.0))


def build(
    head: str,
    limit: int | None = None,
    log: Path | None = None,
    workers: int = DEFAULT_WORKERS,
) -> dict:
    """Render every picture of the plan that is not already on disk.

    Ordered work, unordered accounting: the plan goes to the pool in its own
    order and the log counts what comes back. A build's only ordering
    requirement is the shuffle that makes a prefix a fair sample, and that is
    already in the plan rather than in the order results land.
    """
    from concurrent.futures import ProcessPoolExecutor

    head = finished.head_of(head)
    jobs = [{**job, "_head": head} for job in read_plan(head)]
    if limit is not None:
        jobs = jobs[:limit]
    crops = crop_dir(head)
    crops.mkdir(parents=True, exist_ok=True)
    log = log or log_path(head)
    log.parent.mkdir(parents=True, exist_ok=True)
    workers = max(1, int(workers))

    started = time.monotonic()
    rendered = skipped = 0
    interior = 0.0
    with log.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"--- build {head}: {len(jobs)} jobs on {workers} engine(s) ---\n")
        handle.flush()

        def account(index: int, fraction: float | None) -> None:
            nonlocal rendered, skipped, interior
            if fraction is None:
                skipped += 1
                return
            rendered += 1
            interior += fraction
            if rendered % 25 == 0 or index == len(jobs):
                spent = time.monotonic() - started
                rate = spent / max(rendered, 1)
                left = (len(jobs) - index) * rate
                handle.write(
                    f"{index}/{len(jobs)}  rendered {rendered}  skipped {skipped}  "
                    f"{rate:.2f}s each  {left / 60:.1f} min left\n"
                )
                handle.flush()

        if workers == 1:
            for index, job in enumerate(jobs, start=1):
                account(index, render_one(job))
        else:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                for index, fraction in enumerate(pool.map(render_one, jobs, chunksize=1), start=1):
                    account(index, fraction)

    seconds = time.monotonic() - started
    on_disk = sorted(crops.glob("*.jpg"))
    return {
        "schema": SCHEMA,
        "head": head,
        "jobs": len(jobs),
        "rendered": rendered,
        "skipped": skipped,
        "seconds": round(seconds, 1),
        "workers": workers,
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


# --------------------------------------------------------------------------- #
# The decoded cache: the same pixels, without the JPEG.
# --------------------------------------------------------------------------- #
#: What a decoded array is called, beside the crops it was decoded from.
DECODED = "decoded"


def decoded_dir(head: str) -> Path:
    """Where one judge's decoded arrays live. Ignored, and rebuilt from the crops."""
    return cache_dir(head) / DECODED


def decoded_of(picture: Path) -> Path:
    """Where one crop's decoded array sits, addressed from the crop rather than the head.

    A picture is handed to the training loop as a path and nothing else, so the
    cache has to be findable from that path alone — `<head>/crops/<name>.jpg`
    becomes `<head>/decoded/<name>.npy` and no caller has to carry a head around
    to open a picture.
    """
    picture = Path(picture)
    return picture.parent.parent / DECODED / f"{picture.stem}.npy"


def open_picture(path):
    """One crop as an RGB image, through the decoded cache where it has been built.

    **Exactly the pixels the JPEG holds.** This removes a decode and nothing
    else — no resize, no colour conversion, no smaller intermediate — so a run
    over the cache and a run over the JPEGs are the same run. That is the whole
    reason the cache is at the source geometry and costs 2.7 MB a picture: an
    array at anything smaller would put a second resize in the chain, and then
    the recipe a band was fitted at would depend on whether a cache happened to
    be warm.

    The loop is data-loading bound — the GPU sits near 10% while a worker decodes
    a 1280x720 JPEG — and the decode is 12 ms of a 30 ms example. A half-written
    or truncated array reads as a **miss** rather than as a failure: the JPEG is
    still there and is still the authority.
    """
    import numpy
    from PIL import Image

    cached = decoded_of(path)
    if cached.is_file():
        try:
            return Image.fromarray(numpy.load(cached, mmap_mode="r"))
        except (OSError, ValueError):
            pass
    with Image.open(path) as opened:
        opened.load()
        return opened.convert("RGB")


def decode(head: str, limit: int | None = None, log=print) -> dict:
    """Decode every crop of one head's cache once, and keep the array beside it.

    Resumable the way the build is, and by the same rule: written to a temporary
    and renamed, so presence means complete. Costs about 3 GB a thousand
    pictures, which is why it lives in the ignored tree and is never shipped.
    """
    import numpy
    from PIL import Image

    from fractal_wallpapers.paths import WRITING_INFIX

    head = finished.head_of(head)
    crops = sorted(crop_dir(head).glob("*.jpg"))
    if limit is not None:
        crops = crops[:limit]
    out = decoded_dir(head)
    out.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()
    written = skipped = 0
    total = 0
    for picture in crops:
        target = decoded_of(picture)
        if target.is_file():
            skipped += 1
            total += target.stat().st_size
            continue
        with Image.open(picture) as opened:
            opened.load()
            array = numpy.asarray(opened.convert("RGB"))
        temporary = target.with_name(target.name + WRITING_INFIX)
        # Through a handle rather than a path: `numpy.save` appends `.npy` to a
        # name that does not end in it, so the temporary would be written beside
        # itself and the rename would find nothing.
        with temporary.open("wb") as handle:
            numpy.save(handle, array, allow_pickle=False)
        temporary.replace(target)
        written += 1
        total += target.stat().st_size
        if written % 500 == 0:
            log(f"[decode] {head}: {written:,} written, {skipped:,} already there")
    seconds = time.monotonic() - started
    return {
        "schema": SCHEMA,
        "head": head,
        "crops": len(crops),
        "written": written,
        "skipped": skipped,
        "bytes": total,
        "seconds": round(seconds, 1),
        "what": "the crop's own pixels, decoded once. No resize and no other change",
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


def present(head: str) -> set[str]:
    """Every file name in one head's crop directory, as **one** listing of it.

    THE answer to "is this head's picture on disk", for a caller asking it of a
    whole store rather than of one row. The same trade
    [`curation.candidate_ledger.present_pictures`] already takes over the
    candidate pool: a directory listing costs one syscall where a stat per row
    costs one each, and on Windows the difference is the whole cost of the
    question. Measured on this machine, 2026-08-31: the two crop directories hold
    10,552 entries and list in **13 ms** together, against about 100 us a row for
    `is_file` — 1.1 s per sweep of the 11,072 scored rows, paid by every one of
    the eleven sweeps the slow lane used to make.

    A directory that is not there yet lists as empty: nothing is on disk either
    way, and a caller asking this of an unbuilt cache wants "none" rather than an
    error — [`missing`] is exactly the caller that then reports the whole plan.
    """
    import os

    try:
        return {entry.name for entry in os.scandir(crop_dir(head))}
    except OSError:
        return set()


def missing(head: str) -> list[dict]:
    """Every picture the store's verdicts need that is not on disk.

    Derived from the corpus rather than read off the written plan, because those
    two answer different questions and only one of them is *is the cache
    complete*. A plan is a record of what a build was asked for; the store grows
    afterwards, every ingest of a labeling session grows it, and a plan that
    predates those rows reports a full cache while the trainer refuses to start.
    """
    on_disk = present(head)
    return [job for job in plan(head) if f"{job['name']}.jpg" not in on_disk]


def crop_of(head: str, row: dict) -> Path:
    """Where one row's picture is, whether or not it has been made yet."""
    stripped = {key: value for key, value in row.items() if not key.startswith("_")}
    stripped["_head"] = head
    return crop_dir(head) / f"{job_name(stripped)}.jpg"


__all__ = [
    "DECODED",
    "DEFAULT_WORKERS",
    "FIELD_COLORMAP",
    "FIELD_IDENTITY",
    "JPEG_FLOOR_QUALITY",
    "NAME_LENGTH",
    "RECOLOR_MEMBERS",
    "SCHEMA",
    "SEED",
    "SPEC_MEMBERS",
    "Job",
    "RenderCacheError",
    "build",
    "field_job_name",
    "build_record_path",
    "cache_dir",
    "catalog",
    "coloring_of",
    "crop_dir",
    "crop_of",
    "decode",
    "decoded_dir",
    "decoded_of",
    "job_name",
    "log_path",
    "missing",
    "open_picture",
    "plan",
    "plan_path",
    "present",
    "read_plan",
    "render_one",
    "spec_of",
    "verify",
    "write_plan",
]
