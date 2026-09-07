"""Can anything order the judge's flat top slice? A probe that asks, and stages nothing.

The render judge sorts the whole pool well and the top of it barely at all. Cut
the labelled corpus at `P(>=4) >= 0.9` and what is left is about a thousand
pictures, four-fifths of them tier 4, with the judge's own score correlating
`+0.12` with the tier inside that band. A seating walks that band and takes the
first `n` of it, so the order **inside** the flat part is exactly the order
nobody has a column for.

This module asks whether the judge already knows more than its three cutpoints
say. The forward pass ends in a 1,280-wide vector and the classifier reads it
through three numbers; if quality survives in that vector and not in those three
numbers, a linear probe on it will find some of it. Four readings are compared
against three baselines, all out of fold, all on one population.

## It adopts nothing, and cannot

Nothing here writes a score column, a store, a floor or a rank key. It writes one
regenerable readout and one sheet of pictures under `artifacts/`, and the sheet
is the deliverable: a table saying an arm reads `0.62` is a claim about a
statistic, and whether the resulting order is one a person would defend is a
different question that only pictures answer.

## The population is the fittable pool, which is not the whole corpus

[`render_folds.pool`] is the corpus this project already agreed may be fitted on:
it drops the rows a **sweep** filled — `under_seen_modes` past position 269,
which restate the head's own decode — and the rows sitting in the wrong store.
That matters more here than anywhere else, because
`AUDIT_top_slice_ranker_0906`'s finding about this slice is that 86% of it was
labelled against a page that prefilled the judge's decode. Dropping the rows
where that prefill *became* the verdict is the one part of that confound this
module can remove; the rest is a caveat on every number below and is stated in
the readout rather than in a footnote here.

## Two geometries, both rendered, because neither is derivable from the other

A label is cast on a 1280x720 ss2 picture and a mining pass scores a 640x360 ss2
one. Those sample different grids — one doubling apart — so a candidate-geometry
reading cannot be resampled out of a label-geometry file, and the audit measured
the two disagreeing about slice membership at Jaccard 0.81. Both arms are
therefore rendered here, from **one** path: the same job the render cache builds,
with the geometry overridden and nothing else touched.

⚠ That is deliberately *not* the ledger's own 640x360 picture, which about 60% of
the slice has on disk and which reusing would have saved. The ledger joins a
label on [`curation.rank_key.ledger_identity`], which excludes the autolevel
stamp — so those files may carry an operator the label-geometry file does not,
and mixing them with fresh renders of the rest would put an unrecorded operator
into three-fifths of one arm. What this arm measures is the geometry at a fixed
recipe. What it does not measure is the deployment picture with its colouring
pass, and a reader wanting that should ask for it by name.

## The fit is [`spiral_probe`]'s, and the deal is [`render_folds`]'s

A thousand rows against 1,280 columns is the wide design `spiral_probe` was
written for: ridge logistic by damped IRLS on the thin SVD's `U*S`, exact rather
than approximate, the penalty chosen by cross-validated AUC. Nothing is
re-implemented here. The one thing this module supplies is the **deal**: the
ridge and the held-out read are both taken over lineage groups
([`render_folds.assignment`]) rather than over rows, because frames a hair apart
on one plane are the same picture twice and a row-wise deal would put one of them
on each side.

**The ridge is chosen once over the whole population, then the held-out read
runs at it.** That is mildly optimistic — the chosen penalty saw every row — and
it is the same trade [`spiral_probe.fit`] and [`curation.rank_key.fit`] already
make. Nesting the choice inside each fold would multiply an already
forty-minute leg by five for a second-order effect on a number whose bootstrap
interval is +/-0.05 wide.

## No pin is spent

[`curation.rank_key`] states the precedent this stands on: *a selection rule fit
on human labels is a category no eligibility guard covers today: the eligibility
rule is about judge training, and this is not that.* So the pinned locations are
in the population like any others, and the readout counts them rather than
excluding them.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from fractal_wallpapers.paths import under

#: The schema every record this module writes carries.
SCHEMA = 1

#: The subtree the whole leg lands in, under the regenerable tree.
UNIT = "top_slice_probe"

#: Where the judge's own `P(>=4)` is cut to make the slice. **0.9**, which is the
#: band `AUDIT_top_slice_ranker_0906` measured the flatness over: about a
#: thousand rows, four in five of them tier 4. Cutting at 0.99 leaves 579 rows
#: and 83% positives, which is the same question with half the evidence.
CUT = 0.9

#: How many pictures go through the judge at once. Decode dominates a scoring
#: pass at about 20 ms a picture against 1 ms of forward, so this is a hedge
#: against per-batch overhead and not a throughput knob.
BATCH = 64

#: The four readings compared, and what each is read off. A reading of the
#: **picture** the judge sees and a reading of the **place** underneath it are
#: different questions, and the third arm is here to say how much of the answer
#: is in the place alone.
ARMS: dict[str, str] = {
    "label_head": "the shipped judge's penultimate vector on the 1280x720 ss2 label picture",
    "candidate_head": "the same vector on the same recipe at 640x360 ss2, freshly rendered",
    "neutral_dinov2": "DINOv2 ViT-S/14 on the location's neutral render, where the store has one",
    "both_heads": "the two head readings concatenated",
}

#: The arms whose columns are the judge's own penultimate layer, in the order
#: [`ARMS`] lists them. Named because the concatenation is built out of them and
#: a list that drifted from the names above would concatenate the wrong pair.
HEAD_ARMS = ("label_head", "candidate_head")

#: The two questions asked of every arm.
#:
#: `tier4` is the slice's own question — of the pictures that got in, which ones
#: a person called four. `three_against_four` drops the handful of ones and twos
#: and asks the *order* question directly, which is what a seating actually
#: wants: a coarse target being asked to produce a fine order is exactly the
#: mismatch this experiment exists to check.
TARGETS: dict[str, str] = {
    "tier4": "tier == 4 against the rest of the slice",
    "three_against_four": "tier 4 against tier 3, over the rows that are one or the other",
}

#: The baselines every arm is read beside, recomputed on that arm's own held-out
#: population rather than quoted from anywhere.
#:
#: `rank_key` is the shipped five-column sort key and it is **optimistic here**:
#: it was fitted on rows this slice contains, so it reads its own training data.
#: That is stated on the row rather than corrected, because the correction would
#: be a re-fit and this module ships no key.
BASELINES: dict[str, str] = {
    "label_p_ge4": "the judge's own P(>=4) at label geometry — what the slice was cut on",
    "candidate_p_ge4": "the judge's own P(>=4) at candidate geometry — the deployment scalar",
    "rank_key": "the shipped fitted sort key, on the rows carrying all five of its columns",
}

#: Draws in every interval, and the seed. The repository's own, taken from
#: [`render_folds`] so an interval here and one there are the same statistic.
#: The unit resampled is the **lineage group**, for the reason the fold is drawn
#: over one.
DRAWS = 5000
BOOTSTRAP_SEED = 0

#: How many engines the candidate-geometry render drives at once. **One**, and
#: it is [`renders.DEFAULT_WORKERS`]'s measurement rather than a second opinion:
#: this is the same work a cache build does — one full frame per job — and the
#: engine already iterates a field across every core it can see, so a second
#: process finds this one rather than an idle machine. The pool rule's three is
#: a ceiling on how much of the desktop a leg may take, not a floor.
WORKERS = 1


class ProbeRefused(RuntimeError):
    """The probe cannot be built on what is here."""


# --------------------------------------------------------------------------- #
# Where it lands.
# --------------------------------------------------------------------------- #
def root() -> Path:
    """One leg's whole output: scores, pictures, features, readout, sheet."""
    return under(UNIT)


def scores_path() -> Path:
    """Every fittable row with both geometries' readings on it. The population."""
    return root() / "scores.jsonl"


def candidate_dir() -> Path:
    """Where the 640x360 ss2 re-renders live, one directory a store."""
    return root() / "candidate"


def features_path(arm: str) -> Path:
    """One arm's design matrix, cached so a re-read costs no GPU."""
    return root() / "features" / f"{arm}.npy"


def readout_path() -> Path:
    return root() / "readout.json"


def held_out_path() -> Path:
    """Every arm's out-of-fold value per row, beside the readout rather than in it.

    A thousand floats a row are what the sheet orders on and what a second look
    at one arm's disagreements would need, and they are also what would make the
    readout unreadable. Two files, one question each.
    """
    return root() / "held_out.json"


def sheet_path() -> Path:
    return root() / "sheet.html"


# --------------------------------------------------------------------------- #
# The population, at both geometries.
# --------------------------------------------------------------------------- #
def _job_of(row: dict, kind: str) -> dict:
    """One label row as the render job that makes its picture. [`renders`]'s own."""
    stripped = {name: value for name, value in row.items() if not name.startswith("_")}
    stripped["_head"] = kind
    return stripped


def at_candidate_geometry(job: dict) -> dict:
    """The same job, one doubling down. Geometry moves and nothing else does."""
    from fractal_wallpapers.curation import colorize

    return {
        **job,
        "render": {
            **job["render"],
            "resolution": list(colorize.RESOLUTION),
            "supersample": int(colorize.SUPERSAMPLE),
        },
    }


def render_candidate(payload: tuple) -> str | None:
    """One candidate-geometry picture, or `None` if it was already there.

    Module level and taking a tuple because a Windows process pool spawns and a
    closure would not pickle — the same shape [`renders.render_one`] takes, for
    the same reason.
    """
    from fractal_wallpapers import engine
    from fractal_wallpapers.engine_spec import spec_of

    job, output = payload
    output = Path(output)
    if output.is_file():
        return None
    output.parent.mkdir(parents=True, exist_ok=True)
    engine.run("render", spec_of(job, output))
    return str(output)


def candidate_pictures(rows: list[dict], workers: int = WORKERS, log=print) -> dict:
    """Render every row of the slice at 640x360 ss2. Resumable, and it says what it cost."""
    from concurrent.futures import ProcessPoolExecutor

    payloads = [(at_candidate_geometry(row["_job"]), str(row["candidate_picture"])) for row in rows]
    started = time.perf_counter()
    log(f"[top-slice] {len(payloads):,} candidate-geometry render(s) over {workers} engine(s)")
    made = 0
    if int(workers) <= 1:
        for at, payload in enumerate(payloads, start=1):
            made += render_candidate(payload) is not None
            if at % 100 == 0:
                log(f"[top-slice] {at}/{len(payloads)} in {time.perf_counter() - started:.0f}s")
    else:
        with ProcessPoolExecutor(max_workers=int(workers)) as pool:
            for at, done in enumerate(pool.map(render_candidate, payloads, chunksize=1), start=1):
                made += done is not None
                if at % 100 == 0:
                    log(f"[top-slice] {at}/{len(payloads)} in {time.perf_counter() - started:.0f}s")
    seconds = time.perf_counter() - started
    absent = [row["key"] for row in rows if not Path(row["candidate_picture"]).is_file()]
    if absent:
        raise ProbeRefused(
            f"{len(absent)} candidate-geometry renders are still not on disk (e.g. {absent[:3]}). "
            f"An arm fitted on a population with holes in it is fitted on a different population."
        )
    return {
        "rows": len(payloads),
        "rendered": made,
        "reused": len(payloads) - made,
        "seconds": round(seconds, 1),
        "seconds_each": round(seconds / made, 3) if made else None,
        "workers": int(workers),
        "geometry": f"{list(at_candidate_geometry(rows[0]['_job'])['render']['resolution'])} ss2",
    }


def _read_pictures(judge, paths, want: str = "both", log=print):
    """`(probabilities, activations)` for a list of pictures, through one loaded judge.

    Two passes over the same files when both are wanted, because [`train.score`]
    and [`train.activations`] are separate readings by design and fusing them
    here would put a third implementation of the loader in the tree. `want` is
    what stops that costing anything it need not: the slice is defined by a
    scoring pass over **twelve thousand** pictures and the vectors are wanted for
    a thousand, so asking for both there would double the leg's longest GPU
    stretch to produce eleven thousand rows nothing reads.
    """
    from fractal_wallpapers.models import scoring, train

    model, config, where = judge
    classes = int(config["classes"])
    transform = scoring.transform_of(config)
    recipe = {"batch_size": BATCH}
    probabilities = vectors = None
    if want in ("both", "score"):
        started = time.perf_counter()
        probabilities = train.score(model, paths, transform, where, classes, recipe)
        log(f"[top-slice] {len(paths):,} scored in {time.perf_counter() - started:.0f}s")
    if want in ("both", "activations"):
        started = time.perf_counter()
        vectors = train.activations(model, paths, transform, where, recipe)
        log(
            f"[top-slice] {len(paths):,} penultimate vector(s), {vectors.shape[1]} wide, "
            f"in {time.perf_counter() - started:.0f}s"
        )
    return probabilities, vectors


def population(device: str = "auto", rebuild: bool = False, log=print) -> tuple[list[dict], dict]:
    """Every fittable label row, scored at label geometry, with its lineage fold.

    The whole corpus goes through the judge because the slice is defined by the
    reading — there is no cheaper way to know which rows are in it. About twelve
    thousand pictures at 22 ms each is four minutes, so the answer is cached and
    a re-run of any later stage costs none of it.
    """
    from fractal_wallpapers.curation import colorize
    from fractal_wallpapers.models import render_folds, renders

    cached = scores_path()
    if cached.is_file() and not rebuild:
        rows = [
            json.loads(line) for line in cached.read_text(encoding="utf-8").splitlines() if line
        ]
        log(f"[top-slice] {len(rows):,} scored rows from {cached}")
        return _rehydrate(rows), {"reused": True, "rows": len(rows)}

    started = time.perf_counter()
    label_rows, pictures, record = render_folds.pool()
    deal = render_folds.assignment()
    if len(deal["fold_of_row"]) != len(pictures):
        raise ProbeRefused(
            f"the deal covers {len(deal['fold_of_row'])} rows and the pool holds {len(pictures)}"
        )
    log(
        f"[top-slice] {len(pictures):,} fittable pictures, {record['cut']} cut, in "
        f"{time.perf_counter() - started:.0f}s"
    )

    judge = colorize.load_judge(device)
    probabilities, _ = _read_pictures(judge, [picture.path for picture in pictures], "score", log)

    out: list[dict] = []
    jobs: list[dict] = []
    for at, (row, picture) in enumerate(zip(label_rows, pictures, strict=True)):
        job = _job_of(row, picture.kind)
        name = renders.job_name(job)
        jobs.append(job)
        out.append(
            {
                "schema": SCHEMA,
                "key": f"{picture.kind}:{name}",
                "kind": picture.kind,
                "name": name,
                "tier": int(row["score"]),
                "mode": row["mode"],
                "batch": row["batch"],
                "place": picture.place,
                "fold": int(deal["fold_of_row"][at]),
                "group": int(deal["group_of_row"][at]),
                "label_picture": str(picture.path),
                "candidate_picture": str(candidate_dir() / picture.kind / f"{name}.jpg"),
                "label_p_ge3": round(float(probabilities[at][1]), 6),
                "label_p_ge4": round(float(probabilities[at][2]), 6),
            }
        )
    cached.parent.mkdir(parents=True, exist_ok=True)
    with cached.open("w", encoding="utf-8", newline="\n") as handle:
        for row in out:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    log(f"[top-slice] {cached} — {len(out):,} rows")
    # The jobs are already in hand on this path; [`_rehydrate`] exists for the
    # cached one, and calling it here would sweep both stores a second time for
    # an answer this loop just computed.
    return [{**row, "_job": job} for row, job in zip(out, jobs, strict=True)], {
        "reused": False,
        "rows": len(out),
        "pool": record,
        "deal": {
            "seed": deal["seed"],
            "folds": deal["folds"],
            "unit": deal["unit"],
            "groups": deal["grouping"]["groups"],
        },
        "seconds": round(time.perf_counter() - started, 1),
    }


def _rehydrate(rows: list[dict]) -> list[dict]:
    """Put each row's render job back, which the cache does not carry.

    A job is the label row itself and the cache holds a reading of it; rebuilding
    it costs one sweep of the two stores and keeps the cache to the numbers,
    which is what makes it readable.
    """
    from fractal_wallpapers.models import render_folds, renders

    label_rows, pictures, _ = render_folds.pool()
    jobs = {}
    for row, picture in zip(label_rows, pictures, strict=True):
        job = _job_of(row, picture.kind)
        jobs[f"{picture.kind}:{renders.job_name(job)}"] = job
    missing = [row["key"] for row in rows if row["key"] not in jobs]
    if missing:
        raise ProbeRefused(
            f"{len(missing)} cached rows no longer address a pool row (e.g. {missing[:3]}). The "
            f"corpus moved under the cache: re-run the population with --rebuild."
        )
    return [{**row, "_job": jobs[row["key"]]} for row in rows]


def top_slice(rows: list[dict], cut: float = CUT) -> list[dict]:
    """The rows the judge puts at the top, in the order the store gave them."""
    return [row for row in rows if float(row["label_p_ge4"]) >= cut]


def score_candidates(rows: list[dict], device: str = "auto", log=print) -> list[dict]:
    """Read the candidate-geometry pictures, putting both cutpoints on each row."""
    from fractal_wallpapers.curation import colorize

    judge = colorize.load_judge(device)
    paths = [Path(row["candidate_picture"]) for row in rows]
    probabilities, vectors = _read_pictures(judge, paths, "both", log)
    _write_matrix("candidate_head", vectors)
    return [
        {
            **row,
            "candidate_p_ge3": round(float(probabilities[at][1]), 6),
            "candidate_p_ge4": round(float(probabilities[at][2]), 6),
        }
        for at, row in enumerate(rows)
    ]


# --------------------------------------------------------------------------- #
# The four readings.
# --------------------------------------------------------------------------- #
def _write_matrix(arm: str, matrix) -> Path:
    import numpy

    path = features_path(arm)
    path.parent.mkdir(parents=True, exist_ok=True)
    numpy.save(path, numpy.asarray(matrix, dtype=numpy.float32))
    return path


def _read_matrix(arm: str):
    import numpy

    path = features_path(arm)
    return numpy.load(path) if path.is_file() else None


def label_activations(rows: list[dict], device: str = "auto", log=print):
    """The penultimate vector on each row's label-geometry picture."""
    from fractal_wallpapers.curation import colorize

    held = _read_matrix("label_head")
    if held is not None and len(held) == len(rows):
        log(f"[top-slice] label_head {held.shape} from cache")
        return held
    judge = colorize.load_judge(device)
    _, vectors = _read_pictures(
        judge, [Path(row["label_picture"]) for row in rows], "activations", log
    )
    _write_matrix("label_head", vectors)
    return vectors


def neutral_embeddings(rows: list[dict], log=print):
    """`(matrix, mask)` — DINOv2 on the neutral render, where the store has one.

    The store is **not extended**. Its declared denominator is the set of
    admitted locations and appending unadmitted places to it would either widen
    that claim or want a second store; either is a decision, and this experiment
    is not the place one gets made. So the arm is fitted on the rows the store
    already covers and the readout carries the coverage beside every figure it
    produced.

    The key is [`supply.location.key_text`] of the place — the JSON spelling the
    store writes, never `str(tuple)`. Taking the wrong one returns zero matches
    silently, which is exactly what it did to the audit's first pass.
    """
    import numpy

    from fractal_wallpapers.curation import embeddings
    from fractal_wallpapers.supply.location import key_text, location_key

    stored, matrix = embeddings.load()
    by_key = {str(row["key"]): at for at, row in enumerate(stored)}
    log(f"[top-slice] {len(by_key):,} locations in {embeddings.STORE_NAME}")
    mask = numpy.zeros(len(rows), dtype=bool)
    taken = []
    for at, row in enumerate(rows):
        job = row["_job"]
        place = location_key(job.get("family") or {}, job.get("viewport") or {})
        found = None if place is None else by_key.get(key_text(place))
        if found is not None:
            mask[at] = True
            taken.append(found)
    return (matrix[taken] if taken else numpy.zeros((0, 0), dtype=numpy.float32)), mask


def arm_matrix(arm: str, rows: list[dict], device: str = "auto", log=print):
    """`(matrix, mask)` for one arm — the rows it can read, and their columns."""
    import numpy

    if arm not in ARMS:
        raise ProbeRefused(f"unknown arm {arm!r} — known: {list(ARMS)}")
    if arm == "neutral_dinov2":
        return neutral_embeddings(rows, log)
    if arm == "both_heads":
        parts = [_read_matrix(name) for name in HEAD_ARMS]
        if any(part is None or len(part) != len(rows) for part in parts):
            raise ProbeRefused(
                "the concatenation is built from the two head arms and one of them is not "
                "cached at this population's size — read those first."
            )
        return numpy.hstack(parts), numpy.ones(len(rows), dtype=bool)
    held = _read_matrix(arm)
    if held is None or len(held) != len(rows):
        raise ProbeRefused(f"{arm} has no cached matrix at {len(rows)} rows")
    return held, numpy.ones(len(rows), dtype=bool)


# --------------------------------------------------------------------------- #
# The deal, the fit and the interval.
# --------------------------------------------------------------------------- #
def blocks_of(rows: list[dict], folds: int | None = None) -> list:
    """The lineage deal as index blocks over THESE rows, one entry a fold.

    [`render_folds.assignment`] deals the whole fittable pool; a slice of it
    keeps each row's fold and this turns those into the blocks
    [`spiral_probe.held_out`] takes. A fold that no row of the slice landed in is
    dropped rather than passed as an empty block, which would divide by zero in
    every statistic downstream.
    """
    import numpy

    count = folds if folds is not None else (max((row["fold"] for row in rows), default=-1) + 1)
    blocks = []
    for fold in range(count):
        members = numpy.array(
            [at for at, row in enumerate(rows) if int(row["fold"]) == fold], dtype=int
        )
        if members.size:
            blocks.append(members)
    return blocks


def targets_for(rows: list[dict], target: str):
    """`(mask, values)` — which rows the target is asked of, and the answer for each.

    `tier4` asks it of the whole slice. `three_against_four` asks it only of the
    rows that are one or the other, so the ones and twos — which are a handful
    and which every column already separates — cannot flatter an arm.
    """
    import numpy

    tiers = numpy.array([int(row["tier"]) for row in rows])
    if target == "tier4":
        return numpy.ones(len(rows), dtype=bool), (tiers >= 4).astype(float)
    if target == "three_against_four":
        return numpy.isin(tiers, (3, 4)), (tiers >= 4).astype(float)
    raise ProbeRefused(f"unknown target {target!r} — known: {list(TARGETS)}")


def interval(target, score, groups, draws: int = DRAWS, seed: int = BOOTSTRAP_SEED) -> dict:
    """A percentile interval on one AUC, resampling LINEAGE GROUPS with replacement.

    Rows, not groups, is the wrong unit for the same reason the fold is: two rows
    of one neighbourhood are one picture judged twice, and an interval that
    resampled them independently would report a spread narrower than the evidence
    supports. A draw that comes back with one class is skipped and counted.
    """
    import numpy

    target = numpy.asarray(target, dtype=float)
    score = numpy.asarray(score, dtype=float)
    groups = numpy.asarray(groups)
    members: dict = {}
    for at, group in enumerate(groups):
        members.setdefault(int(group), []).append(at)
    order = sorted(members)
    blocks = [numpy.array(members[group], dtype=int) for group in order]
    rng = numpy.random.default_rng(seed)
    values = []
    for _ in range(draws):
        drawn = numpy.concatenate([blocks[at] for at in rng.integers(0, len(blocks), len(blocks))])
        value = spiral_auc(target[drawn], score[drawn])
        if value == value:
            values.append(value)
    if not values:
        return {"lo": None, "hi": None, "draws": 0}
    array = numpy.sort(numpy.array(values))
    return {
        "lo": round(float(numpy.percentile(array, 2.5)), 4),
        "hi": round(float(numpy.percentile(array, 97.5)), 4),
        "draws": len(values),
        "unit": "lineage group",
    }


def spiral_auc(target, score) -> float:
    """[`spiral_probe.auc`], reached through one name so there is one of it here."""
    from fractal_wallpapers.models import spiral_probe

    return spiral_probe.auc(target, score)


def read_arm(
    arm: str, matrix, rows: list[dict], target: str, draws: int = DRAWS, log=print
) -> dict:
    """One arm on one target: choose the ridge, read out of fold, price the spread."""
    import numpy

    from fractal_wallpapers.models import spiral_probe

    mask, values = targets_for(rows, target)
    held = [row for at, row in enumerate(rows) if mask[at]]
    features = numpy.asarray(matrix, dtype=numpy.float64)[mask]
    answer = values[mask]
    blocks = blocks_of(held, folds=max((row["fold"] for row in rows), default=0) + 1)
    started = time.perf_counter()
    lam, grid = spiral_probe.choose_lambda(features, answer, blocks=blocks)
    probability = spiral_probe.held_out(features, answer, lam, blocks=blocks)
    seconds = time.perf_counter() - started
    auc = spiral_auc(answer, probability)
    log(
        f"[top-slice] {arm} / {target}: n={len(held):,} d={features.shape[1]} "
        f"AUC {auc:.3f} at lambda {lam} in {seconds:.0f}s"
    )
    return {
        "arm": arm,
        "target": target,
        "rows": len(held),
        "positives": int(answer.sum()),
        "columns": int(features.shape[1]),
        "folds": len(blocks),
        "lambda": lam,
        "lambda_grid": [
            {"lambda": entry["lambda"], "auc": round(entry["auc"], 4)} for entry in grid
        ],
        "auc": round(auc, 4),
        **interval(answer, probability, [row["group"] for row in held], draws=draws),
        "seconds": round(seconds, 1),
        "held_out": [round(float(value), 6) for value in probability],
        "keys": [row["key"] for row in held],
    }


def paired_delta(answer, mine, theirs, groups, draws: int = DRAWS, seed: int = BOOTSTRAP_SEED):
    """`AUC(mine) - AUC(theirs)` and its interval, resampled on ONE population.

    **This is the number that decides and two overlapping intervals are not it.**
    An arm and its baseline are read on the same rows, so their errors move
    together: a draw that happens to contain the easy rows lifts both. Comparing
    two marginal intervals throws that pairing away and reports a spread far
    wider than the difference actually has — which is how a real gain of two
    points looks unresolved and a real null looks like a maybe. The same
    lineage-group resample is applied to both readings at once.
    """
    import numpy

    answer = numpy.asarray(answer, dtype=float)
    mine = numpy.asarray(mine, dtype=float)
    theirs = numpy.asarray(theirs, dtype=float)
    groups = numpy.asarray(groups)
    members: dict = {}
    for at, group in enumerate(groups):
        members.setdefault(int(group), []).append(at)
    blocks = [numpy.array(members[group], dtype=int) for group in sorted(members)]
    rng = numpy.random.default_rng(seed)
    values = []
    for _ in range(draws):
        drawn = numpy.concatenate([blocks[at] for at in rng.integers(0, len(blocks), len(blocks))])
        one = spiral_auc(answer[drawn], mine[drawn])
        two = spiral_auc(answer[drawn], theirs[drawn])
        if one == one and two == two:
            values.append(one - two)
    point = spiral_auc(answer, mine) - spiral_auc(answer, theirs)
    if not values:
        return {"delta": round(float(point), 4), "delta_lo": None, "delta_hi": None}
    array = numpy.sort(numpy.array(values))
    return {
        "delta": round(float(point), 4),
        "delta_lo": round(float(numpy.percentile(array, 2.5)), 4),
        "delta_hi": round(float(numpy.percentile(array, 97.5)), 4),
        "delta_draws": len(values),
    }


def read_baseline(
    name: str,
    rows: list[dict],
    target: str,
    columns: dict,
    against: dict | None = None,
    draws: int = DRAWS,
) -> dict:
    """One baseline on the same held-out population, or a row saying it could not be.

    `against` is the arm's own out-of-fold value per row. Where it is given the
    row carries a **paired** delta as well as the two marginal figures — see
    [`paired_delta`] on why that is the figure to read and the marginals are the
    context.
    """
    import numpy

    mask, values = targets_for(rows, target)
    held = [row for at, row in enumerate(rows) if mask[at]]
    answer = values[mask]
    score = numpy.array([columns.get(row["key"]) for row in held], dtype=object)
    covered = numpy.array([value is not None for value in score], dtype=bool)
    if covered.sum() < 2 or len(numpy.unique(answer[covered])) < 2:
        return {"baseline": name, "rows": int(covered.sum()), "auc": None, "why": "no population"}
    reading = numpy.asarray(score[covered], dtype=float)
    auc = spiral_auc(answer[covered], reading)
    groups = [row["group"] for at, row in enumerate(held) if covered[at]]
    paired = {}
    if against is not None:
        ours = numpy.array(
            [against[row["key"]] for at, row in enumerate(held) if covered[at]], dtype=float
        )
        paired = paired_delta(answer[covered], ours, reading, groups, draws=draws)
    return {
        "baseline": name,
        "rows": int(covered.sum()),
        "positives": int(answer[covered].sum()),
        "coverage": round(float(covered.mean()), 4),
        "auc": round(auc, 4),
        **interval(answer[covered], reading, groups, draws=draws),
        **paired,
    }


def rank_key_column(rows: list[dict], rebuild: bool = False, log=print) -> dict:
    """`{key: the shipped key's value}` for every slice row carrying all four columns.

    Off [`render_grade.rank_key_columns`], which is the same join
    [`curation.rank_key.fit`] makes and is keyed by `<kind>:<job name>` — which
    is what a row here already carries, so no store is opened twice.

    **`rebuild` is worth passing and the coverage says why.** That join is
    cached, the cache is a reading of the ledger on the day it was taken, and
    the ledger grows every mining leg — so a stale cache does not go wrong, it
    quietly narrows this baseline's population while the arms keep the whole
    slice. The readout prints the coverage beside the figure for that reason.
    """
    from fractal_wallpapers.curation import rank_key
    from fractal_wallpapers.models import render_grade

    carried = render_grade.rank_key_columns(rebuild=rebuild, log=log)["rows"]
    key = rank_key.load()
    out: dict = {}
    for row in rows:
        entry = carried.get(row["key"])
        if entry is None:
            continue
        out[row["key"]] = key.score(
            {
                "loc_p_ge4": entry["loc_p_ge4"],
                "p_ge3": entry["incumbent_p_ge3"],
                "p_ge4": entry["incumbent_p_ge4"],
                "flat16_1.0": entry["flat16_1.0"],
            }
        )
    log(f"[top-slice] the shipped rank key reads {len(out):,} of {len(rows):,} slice rows")
    return out


# --------------------------------------------------------------------------- #
# The leg.
# --------------------------------------------------------------------------- #
def run(
    device: str = "auto",
    cut: float = CUT,
    workers: int = WORKERS,
    rebuild: bool = False,
    draws: int = DRAWS,
    log=print,
) -> dict:
    """Every arm, every target, every baseline, one readout and one sheet.

    Ordered so the expensive things happen once and the cheap things happen
    last: the corpus is scored, the slice is cut, the slice is re-rendered and
    re-read, and only then does anything fit. Each stage caches, so a fit that
    is changed and re-run costs no engine and no GPU.
    """
    started = time.perf_counter()
    rows, record = population(device=device, rebuild=rebuild, log=log)
    held = top_slice(rows, cut)
    log(f"[top-slice] {len(held):,} of {len(rows):,} rows at P(>=4) >= {cut}")
    if not held:
        raise ProbeRefused(f"nothing is at P(>=4) >= {cut}, so there is no slice to order")

    rendered = candidate_pictures(held, workers=workers, log=log)
    held = score_candidates(held, device=device, log=log)
    label_activations(held, device=device, log=log)

    columns = {
        "label_p_ge4": {row["key"]: row["label_p_ge4"] for row in held},
        "candidate_p_ge4": {row["key"]: row["candidate_p_ge4"] for row in held},
        "rank_key": rank_key_column(held, rebuild=rebuild, log=log),
    }

    arms: list[dict] = []
    baselines: list[dict] = []
    for arm in ARMS:
        matrix, mask = arm_matrix(arm, held, device=device, log=log)
        population_of_arm = [row for at, row in enumerate(held) if mask[at]]
        if len(population_of_arm) < 50:
            log(f"[top-slice] {arm}: {len(population_of_arm)} rows covered — not fitted")
            arms.append({"arm": arm, "rows": len(population_of_arm), "auc": None, "why": "thin"})
            continue
        for target in TARGETS:
            reading = read_arm(arm, matrix, population_of_arm, target, draws=draws, log=log)
            arms.append({**reading, "coverage": round(len(population_of_arm) / len(held), 4)})
            ours = dict(zip(reading["keys"], reading["held_out"], strict=True))
            for name, column in columns.items():
                against = read_baseline(
                    name, population_of_arm, target, column, against=ours, draws=draws
                )
                baselines.append({"beside": arm, "target": target, **against})
                log(
                    f"[top-slice]   against {name}: {against.get('auc')} "
                    f"(d {against.get('delta')} [{against.get('delta_lo')}, "
                    f"{against.get('delta_hi')}] over {against.get('rows')} rows)"
                )

    readings = {
        f"{entry['arm']}/{entry['target']}": {
            "keys": entry["keys"],
            "held_out": entry["held_out"],
            "auc": entry["auc"],
            "lo": entry["lo"],
            "hi": entry["hi"],
            "arm": entry["arm"],
            "target": entry["target"],
        }
        for entry in arms
        if "held_out" in entry
    }
    held_out_path().parent.mkdir(parents=True, exist_ok=True)
    held_out_path().write_text(
        json.dumps({"schema": SCHEMA, "readings": readings}) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    best = max(
        (entry for entry in arms if entry.get("auc") is not None and entry["target"] == "tier4"),
        key=lambda entry: entry["auc"],
        default=None,
    )
    page = sheet(held, best, log=log) if best is not None else None

    document = {
        "schema": SCHEMA,
        "what": (
            "a linear probe over the render judge's penultimate layer, asking whether the "
            "flat top of its own score can be ordered"
        ),
        "cut": float(cut),
        "population": record,
        "slice": _slice_record(held, cut),
        "candidate_render": rendered,
        "arms": {name: ARMS[name] for name in ARMS},
        "targets": dict(TARGETS),
        "baselines": dict(BASELINES),
        "draws": int(draws),
        "bootstrap_seed": BOOTSTRAP_SEED,
        "table": [
            {name: entry[name] for name in entry if name not in ("held_out", "keys")}
            for entry in arms
        ],
        "baseline_table": baselines,
        "best": None if best is None else {"arm": best["arm"], "auc": best["auc"]},
        "held_out_values": str(held_out_path()),
        "sheet": None if page is None else str(page),
        "adopted": "nothing — no score column, no store, no flip, no floor",
        "seconds": round(time.perf_counter() - started, 1),
    }
    readout_path().parent.mkdir(parents=True, exist_ok=True)
    readout_path().write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")
    log(f"[top-slice] {readout_path()}")
    return document


def _slice_record(rows: list[dict], cut: float) -> dict:
    """What the slice is made of, so a table's population is readable beside it."""
    from collections import Counter

    from fractal_wallpapers.models import render_train

    pinned = {repr(place) for place in render_train.pinned_everywhere()}
    return {
        "rows": len(rows),
        "cut": float(cut),
        "places": len({row["place"] for row in rows}),
        "lineage_groups": len({row["group"] for row in rows}),
        "tiers": dict(sorted(Counter(str(row["tier"]) for row in rows).items())),
        "kinds": dict(sorted(Counter(row["kind"] for row in rows).items())),
        "modes": dict(sorted(Counter(row["mode"] for row in rows).items())),
        "batches": dict(sorted(Counter(str(row["batch"]) for row in rows).items())),
        "pinned_rows": sum(1 for row in rows if row["place"] in pinned),
        "pin_rule": (
            "a pinned place is fitted on like any other — curation.rank_key's precedent, "
            "that a selection rule fit on human labels is not judge training"
        ),
        "per_fold": dict(sorted(Counter(str(row["fold"]) for row in rows).items())),
    }


# --------------------------------------------------------------------------- #
# The sheet, which is the deliverable.
# --------------------------------------------------------------------------- #
#: The long edge of a tile. Wider than the glance sheets' 200 because the
#: question here is *is this order defensible*, which is answered by looking at
#: the picture rather than at its colour.
THUMBNAIL_WIDTH = 240

STYLE = """
body { background:#12141a; color:#e8e8ea; font:13px/1.5 system-ui, sans-serif; margin:24px; }
h1 { font-size:20px; margin:0 0 4px; }
p.note { color:#9aa0aa; max-width:70em; }
.grid { display:flex; flex-wrap:wrap; gap:10px; margin-top:18px; }
.tile { margin:0; width:240px; }
.tile img { width:240px; border-radius:3px; display:block; }
figcaption { color:#9aa0aa; font-size:11px; margin-top:3px; word-break:break-word; }
.rank { color:#e8e8ea; font-weight:600; }
.t4 { color:#8fd18f; } .t3 { color:#d1c48f; } .t2 { color:#d1a08f; } .t1 { color:#d18f8f; }
"""


def sheet(rows: list[dict], best: dict, output: Path | None = None, log=print) -> Path:
    """The slice at label geometry, ordered by the winning arm, good to bad.

    Every row is on it and none is sampled away: the question is whether the
    *order* is defensible, and a page showing the top twenty of a thousand would
    answer a different one. The tier is printed beside each tile because the
    eye-check is against a person's own past verdict, and the held-out value is
    printed because a reader disagreeing with the order has to be able to say
    where.

    It is a **glance sheet and not an instrument**: no pin is spent on it, no
    correction is expected from it, and nothing downstream reads it.
    """
    import html

    from fractal_wallpapers.curation import sheet as sheet_module

    values = dict(zip(best["keys"], best["held_out"], strict=True))
    ordered = sorted(
        (row for row in rows if row["key"] in values),
        key=lambda row: -values[row["key"]],
    )
    tiles = []
    for at, row in enumerate(ordered, start=1):
        source = sheet_module.thumbnail(Path(row["label_picture"]), width=THUMBNAIL_WIDTH)
        if not source:
            continue
        caption = " · ".join((row["mode"], str(row["batch"])))
        tiles.append(
            '<figure class="tile">'
            f'<img loading="lazy" src="{source}" alt="">'
            f'<figcaption><span class="rank">#{at}</span> '
            f'<span class="t{row["tier"]}">tier {row["tier"]}</span> · '
            f"{values[row['key']]:.3f} · P(&ge;4) {row['label_p_ge4']:.3f}<br>"
            f"{html.escape(caption)}</figcaption></figure>"
        )
    note = (
        f"{len(ordered):,} rows of the judge's top slice (P(&ge;4) &ge; {CUT} at label geometry), "
        f"ordered good to bad by <b>{html.escape(best['arm'])}</b> on <b>"
        f"{html.escape(best['target'])}</b> — held-out AUC {best['auc']:.3f} "
        f"[{best['lo']}, {best['hi']}]. Every value is read by the lineage fold that did not "
        f"train on it. Pictures are the 1280&times;720 ss2 renders a label was cast on. "
        f"Nothing was adopted off this page and no pin was spent on it."
    )
    page = (
        "<!doctype html><meta charset='utf-8'><title>the judge's top slice, ordered</title>"
        f"<style>{STYLE}</style><h1>the judge's top slice, ordered</h1>"
        f"<p class='note'>{note}</p><div class='grid'>{''.join(tiles)}</div>"
    )
    where = sheet_path() if output is None else Path(output)
    where.parent.mkdir(parents=True, exist_ok=True)
    where.write_text(page, encoding="utf-8", newline="\n")
    log(f"[top-slice] {where} — {len(tiles):,} tiles")
    return where


__all__ = [
    "ARMS",
    "BASELINES",
    "BATCH",
    "BOOTSTRAP_SEED",
    "CUT",
    "DRAWS",
    "HEAD_ARMS",
    "SCHEMA",
    "STYLE",
    "TARGETS",
    "THUMBNAIL_WIDTH",
    "UNIT",
    "WORKERS",
    "ProbeRefused",
    "arm_matrix",
    "at_candidate_geometry",
    "blocks_of",
    "candidate_dir",
    "candidate_pictures",
    "features_path",
    "held_out_path",
    "interval",
    "label_activations",
    "neutral_embeddings",
    "paired_delta",
    "population",
    "rank_key_column",
    "read_arm",
    "read_baseline",
    "readout_path",
    "render_candidate",
    "root",
    "run",
    "score_candidates",
    "scores_path",
    "sheet",
    "sheet_path",
    "spiral_auc",
    "targets_for",
    "top_slice",
]
