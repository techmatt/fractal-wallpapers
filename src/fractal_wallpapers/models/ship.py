"""What ships: half-precision weights, a hash, and the manifest entry.

## Why fp16 and not something smaller

The weights are a download, and a fresh clone pays for them before it can score
anything. Half precision halves that, and it is the last format where
"quantization" is not a lossy approximation the head has to be re-checked
against: fp16 is a real IEEE format, every value round-trips exactly, and
dequantizing is a widening cast rather than an inverse of anything. Eight-bit
schemes need a calibration set, a per-tensor scale, and an argument about which
layers to skip; this needs a cast and a comparison.

The cast is not free — fp16 has ten bits of mantissa where fp32 has twenty-three
— so it is *checked* rather than assumed. Three things, in order:

1. **The artifact re-reads.** Load the shipped file back and widen it: every
   tensor must be bit-identical to the fp16 cast of the original. This catches a
   truncated write, a silently skipped tensor, and a serializer that helpfully
   promoted something.
2. **The head still says the same thing.** Score this head's own evaluation side
   both ways and compare — the **decisions** it reaches and the **order** it puts
   them in, which are the two things a head is used for.
3. **The hash is of the file that was checked**, taken after both, so a manifest
   entry can never describe a file nobody verified.

## Why the second check is stated in swaps and decisions

An earlier version of it bounded the AUC move by an absolute constant and the
per-row probability move by another. Both are the wrong shape, and a population
that sits at its head's decision boundary shows why.

**AUC moves in quanta.** On a population with `p` positives and `n` negatives, one
adjacent rank swap moves it by exactly `1/(p·n)`. The finished-render sheets are
small — one of them has six positives in a hundred and fifty, where a single swap
is worth 0.0012 — so an absolute bound of 0.001 there is a bound on something the
statistic cannot express. It demands *zero* swaps, which is a different and far
stricter requirement than "the order is materially unchanged", and a lossy cast
will always reorder two rows whose scores sit inside its own precision. So the
bound is stated in swaps, with the old absolute constant kept as a floor: on a
population big enough that two swaps are invisible, nothing changes.

**A moved probability is not a changed answer.** The per-row bound was a proxy for
"the shipped head says something different about some picture", so the check now
measures that directly: how many rows change their decoded tier. The proxy fired
where the real thing did not — sheet D was drawn to sit at the `≥4` boundary and
a tenth of its rows are within 0.1 of it, which is exactly where a lossy cast
moves a probability most and exactly where a good instrument should be. The worst
row move is still reported, because it is worth seeing; it no longer gates.

## One shipping path, four heads

The fp16 cast, the re-read, the agreement check and the hash are the same for
every head this project trains, and the only thing that differs is where a head's
checkpoint lives and what population "its own evaluation side" means. So that
difference is a small record — [`Shipment`] — and everything else is written
once. A second copy of the verification would be a second answer to whether an
artifact is safe to publish, and the two would drift on the day one of them was
fixed.

The fourth head is the one that shows what the record is for. Three of them emit
a tier on an ordinal scale, so "the order held" is AUC at a cutpoint and "the
decision held" is a decoded tier. The palette head emits a bare utility and its
answer is a *choice inside a candidate set*, so neither statistic exists for it —
its order is counted in discordant candidate pairs and its decision is the top
pick. What that head supplies is a different **statistic**, through
[`Shipment.agree`]; the cast, the re-read, the bounds it is held to and the hash
are the same code as the other three.

## What a manifest row says beyond the hash

A sha256 answers "is this the file we meant". It cannot answer the two questions
a reader of a release actually has — *which repository made it* and *what taught
it* — and neither is recoverable from the bytes. So a row carries both:

- **`source_commit`**, the commit that was checked out when the artifact was
  staged. That is the state the checkpoint, the corpus and this verification
  code were all in, so it is the one thing that makes the artifact reproducible
  rather than merely identifiable. Staging refuses to write a row it cannot name
  a commit for: a row without one is the gap this field exists to close.
- **`provenance`**, where the head's answers came from. Three of these heads
  learned from human verdicts and the fourth from a pretrained teacher, and the
  distilled one names that teacher by hash — because "approximately equivalent
  to its teacher" is a claim that means nothing without saying which teacher.

## The release itself is not this step's job

`fetch-weights` downloads by tag and asset name and verifies the sha256 before
keeping the file. This stages the artifact and the manifest entry that names it;
creating the GitHub release and uploading the asset is a human's action with a
human's credentials, and a script that could do it is a script that could do it
by accident.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from fractal_wallpapers.models import head, metrics, scoring, train
from fractal_wallpapers.paths import repo_root

#: The schema of the weights manifest.
SCHEMA = 1

#: The release tag a first shipment goes to.
TAG = "weights-v1"

#: Every head this project trains, and therefore every head a release has to
#: carry. A release cut from a manifest that is missing one is a clone that
#: cannot run that head at all, and the only way to notice is to have written
#: the roster down somewhere a check can read it.
HEADS = ("location", "smooth_render", "strange_render", "palette")

#: What supervised each head, and where the record of it lives. A hash says
#: which file; this says what taught it — the part a download cannot verify and
#: the part someone reading the release needs in order to know what they have.
SUPERVISION = {
    "location": ("human verdicts", "data/labels"),
    "smooth_render": ("human verdicts", "data/smooth_render"),
    "strange_render": ("human verdicts", "data/strange_render"),
    "palette": ("distilled from a pretrained teacher", "data/palette_choice"),
}

#: The absolute floor on how far the shipped head's ordering may move, in AUC at
#: any cutpoint. A tenth of a point: far below anything an acceptance read is
#: trying to detect. It binds on a population large enough that a couple of rank
#: swaps are worth less than this.
AUC_TOLERANCE = 0.001

#: How many adjacent rank swaps the shipped head may make at any cutpoint, on a
#: population small enough that one swap is worth more than the floor above.
#:
#: **Eight, and the headroom is the point.** Measured, where this term binds: one
#: swap at three of the four finished-render cutpoints and three at the fourth.
#: A tighter number would sit under something already observed and would refuse a
#: head for rounding rather than for degrading — which is the failure this bound
#: has already produced once, at an earlier and stricter value.
#:
#: Eight is still far inside what any read of these heads can detect. On every
#: cutpoint an acceptance bar actually gates on, it is worth at most four percent
#: of that bar's own margin: 0.0014 against the strange judge's 0.035, and the
#: absolute floor of 0.001 against the smooth judge's 0.055. A systematic
#: degradation reorders dozens of rows, not eight.
#:
#: On the location head's 1,002-row population it never binds at all — sixteen
#: swaps at its first cutpoint are worth 0.000068 of AUC and the floor is the
#: tighter bound. That is the right way round: a swap is worth almost nothing on
#: a large population and a great deal on a small one, and the thinnest cutpoint
#: of all leans on the decision check below rather than on this.
SWAP_TOLERANCE = 8

#: The share of rows whose decoded tier may change. One in a hundred; measured at
#: none of 150 and one of 197 on the two finished-render sheets.
DECISION_TOLERANCE = 0.01

#: What counts as a large per-row probability move, for the report. Not a gate —
#: see the module docstring on why a moved probability is not a changed answer.
ROW_TOLERANCE = 0.01


@dataclass(frozen=True)
class Shipment:
    """Where one head's pieces are. Everything else about shipping is shared."""

    #: `(name, which, run) -> the full-precision checkpoint`.
    checkpoint: Callable
    #: `(name, run) -> the directory the artifact lands in`.
    directory: Callable
    #: `(path, device) -> (model, config, device)`.
    load: Callable
    #: `(name, which, run) -> (paths, labels)` for this head's own evaluation side.
    evaluation: Callable
    #: `(name, which, device, run) -> the agreement record`, for a head whose
    #: answer is not a tier on an ordinal scale. Absent means the ordinal read
    #: below applies — three heads use it and one does not, and the one that does
    #: not needs a different *statistic*, not a different shipping path.
    agree: Callable | None = None


def _location_evaluation(name: str, which: str, run: str | None):
    import numpy

    from fractal_wallpapers.models import dataset
    from fractal_wallpapers.models import tiles as tile_module

    del which, run
    rows = tile_module.read_locations()
    grouped = tile_module.tiles_by_location(tile_module.read_manifest())
    locations = dataset.join(rows, grouped)
    holdout = [location for location in locations if location.side == "eval"]
    return (
        [location.canonical() for location in holdout],
        numpy.array([location.score for location in holdout]),
    )


def _finished_evaluation(name: str, which: str, run: str | None):
    """The blind sheet, through the render cache. The pin is the whole side."""
    import numpy

    from fractal_wallpapers.labeling import finished
    from fractal_wallpapers.labeling import registry as registry_module
    from fractal_wallpapers.models import renders

    del which, run
    known = finished.registry(name)
    rows = [
        row
        for row in finished.resolved(name).scored()
        if registry_module.lookup(known, row["batch"]).eval_only
    ]
    crops = renders.crop_dir(name)
    paths = [crops / f"{renders.job_name({**row, '_head': name})}.jpg" for row in rows]
    return paths, numpy.array([row["score"] for row in rows])


def _palette_agreement(name: str, which: str, device: str, run: str | None) -> dict:
    """The half-precision read for the palette head, in the units it is judged in.

    Its answer is a choice inside a candidate set rather than a tier, so the two
    things the recipe protects are spelled for that: the **decisions** are the top
    picks, and the **ordering** is counted in discordant candidate pairs. Both
    bounds are the ratified constants — one percent of decisions, eight swaps —
    read on the same real candidate sets the acceptance arm uses.
    """
    from fractal_wallpapers.models import (
        palette_acceptance,
        palette_head,
        palette_scoring,
        palette_sets,
    )
    from fractal_wallpapers.models import palette_teacher as tower

    del name
    rows = palette_scoring.read(run)
    paths, _ = palette_scoring.paths_of(palette_sets.read())
    halved, config, where = palette_scoring.load(shipped_path("palette"), device)
    scores = tower.scored_with(
        halved, paths, palette_head.Transform(train=False), where, int(config.get("batch_sets", 16))
    )

    after, cursor = [], 0
    for row in rows:
        width = len(row["candidates"])
        after.append(scores[cursor : cursor + width])
        cursor += width
    moved = palette_acceptance.fp16_agreement(rows, after)
    decisions_held = moved["decisions"]["share"] <= DECISION_TOLERANCE
    ordering_held = moved["ordering"]["worst_discordant_pairs"] <= SWAP_TOLERANCE
    return {
        "pictures": len(paths),
        "ordering": {
            "rule": f"at most {SWAP_TOLERANCE} discordant candidate pairs in any one set",
            "worst_discordant_pairs": moved["ordering"]["worst_discordant_pairs"],
            "held": ordering_held,
        },
        "decisions": {
            "rule": f"at most {DECISION_TOLERANCE:.0%} of sets change their top pick",
            "changed": moved["decisions"]["changed"],
            "share": moved["decisions"]["share"],
            "held": decisions_held,
        },
        "row_moves": {
            "reported_only": (
                "a moved score is not a changed answer; the decisions above are what this "
                "used to be a proxy for"
            ),
            **moved["row_moves"],
        },
        "held": ordering_held and decisions_held,
    }


def shipment_for(name: str) -> Shipment:
    """Which family a head belongs to, and where its pieces live."""
    from fractal_wallpapers.labeling import finished

    if name == "palette":
        from fractal_wallpapers.models import palette_scoring, palette_train

        return Shipment(
            checkpoint=lambda _name, which, run: palette_train.checkpoint_path(which, run),
            directory=lambda _name, run=None: palette_train.head_dir(run),
            load=palette_scoring.load,
            evaluation=None,
            agree=_palette_agreement,
        )
    if name in finished.HEADS:
        from fractal_wallpapers.models import finished_scoring, finished_train

        return Shipment(
            checkpoint=finished_train.checkpoint_path,
            directory=finished_train.head_dir,
            load=finished_scoring.load,
            evaluation=_finished_evaluation,
        )
    return Shipment(
        checkpoint=train.checkpoint_path,
        directory=train.head_dir,
        load=scoring.load,
        evaluation=_location_evaluation,
    )


def manifest_path() -> Path:
    """The tracked manifest `fetch-weights` reads."""
    return repo_root() / "models" / "weights.json"


def shipped_path(name: str = "location", run: str | None = None) -> Path:
    """The artifact itself: half precision, living beside its tracked metadata.

    At the head's root, not the run's: what ships is the head, and which of its
    runs the weights came from is a fact the config inside the file carries.

    **Named for the head**, because a release's assets share one namespace: three
    heads that all shipped `head.fp16.pt` could not sit in one release together,
    and the directory that disambiguates them here does not travel. One tag, one
    release, one asset per head.
    """
    del run
    return shipment_for(name).directory(name) / f"{name}.fp16.pt"


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def halve(state: dict) -> dict:
    """Every floating tensor to fp16. Integers are left alone.

    A buffer of counts or indices is not a weight, and casting it would be a
    silent change to what the model does rather than to how big it is.
    """

    return {
        name: (tensor.half() if tensor.is_floating_point() else tensor)
        for name, tensor in state.items()
    }


def convert(name: str = "location", which: str = "best", run: str | None = None) -> dict:
    """Write the half-precision artifact and prove it re-reads."""
    import torch

    source = shipment_for(name).checkpoint(name, which, run)
    saved = torch.load(source, map_location="cpu", weights_only=False)
    config = dict(saved["config"])
    config["precision"] = "fp16"
    config["dequantize_at_load"] = (
        "every floating tensor is stored as fp16 and widened to fp32 on load; the head runs "
        "in full precision and only the file is halved"
    )
    halved = halve(saved["state_dict"])

    destination = shipped_path(name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": halved, "config": config}, destination)

    reread = torch.load(destination, map_location="cpu", weights_only=False)["state_dict"]
    mismatched = [
        key
        for key, tensor in halved.items()
        if key not in reread or not torch.equal(reread[key], tensor)
    ]
    if mismatched or len(reread) != len(halved):
        raise ValueError(
            f"the shipped artifact does not re-read: {len(mismatched)} tensors differ and it "
            f"holds {len(reread)} of {len(halved)}. Nothing about a hash of it would be worth "
            "anything."
        )

    floating = sum(1 for tensor in saved["state_dict"].values() if tensor.is_floating_point())
    return {
        "source": str(source),
        "artifact": str(destination),
        "tensors": len(halved),
        "floating_tensors": floating,
        "bytes": {"fp32": source.stat().st_size, "fp16": destination.stat().st_size},
        "reread": "bit-identical",
    }


def agreement(
    name: str = "location", which: str = "best", device: str = "auto", run: str | None = None
) -> dict:
    """Score this head's own evaluation side both ways and compare."""
    import numpy

    kind = shipment_for(name)
    if kind.agree is not None:
        return kind.agree(name, which, device, run)
    paths, labels = kind.evaluation(name, which, run)

    full, config, where = kind.load(kind.checkpoint(name, which, run), device)
    transform = scoring.transform_of(config)
    classes = int(config["classes"])
    before = train.score(full, paths, transform, where, classes, {"batch_size": 64})
    del full

    halved, _, _ = kind.load(shipped_path(name), device)
    after = train.score(halved, paths, transform, where, classes, {"batch_size": 64})

    cutpoints, ordering_held = {}, True
    for index in range(classes - 1):
        label = head.cutpoint_label(index)
        truth = (labels >= index + 2).astype(int)
        positives = int(truth.sum())
        negatives = int(len(truth) - positives)
        a = metrics.auc(truth, before[:, index])
        b = metrics.auc(truth, after[:, index])
        if a is None or b is None:
            cutpoints[label] = {
                "fp32": a,
                "fp16": b,
                "moved": None,
                "verdict": "NOT_MEASURABLE",
                "why": "one class only",
            }
            continue
        # The quantum this statistic moves in on this population.
        swap = 1.0 / max(positives * negatives, 1)
        bound = max(AUC_TOLERANCE, SWAP_TOLERANCE * swap)
        moved = abs(a - b)
        inside = moved <= bound
        ordering_held = ordering_held and inside
        cutpoints[label] = {
            "fp32": a,
            "fp16": b,
            "moved": moved,
            "one_swap_is": swap,
            "swaps": moved / swap,
            "bound": bound,
            "verdict": "PASS" if inside else "FAIL",
        }

    decoded_before = [head.decode(row, classes - 1) for row in before]
    decoded_after = [head.decode(row, classes - 1) for row in after]
    changed = sum(1 for x, y in zip(decoded_before, decoded_after, strict=True) if x != y)
    share = changed / max(len(paths), 1)
    decisions_held = share <= DECISION_TOLERANCE

    moves = numpy.abs(after - before)
    return {
        "pictures": len(paths),
        "ordering": {
            "cutpoints": cutpoints,
            "rule": (
                f"at most {SWAP_TOLERANCE} adjacent rank swaps at any cutpoint, or "
                f"{AUC_TOLERANCE} of AUC, whichever is larger"
            ),
            "held": ordering_held,
        },
        "decisions": {
            "rule": f"at most {DECISION_TOLERANCE:.0%} of rows change their decoded tier",
            "changed": changed,
            "share": share,
            "held": decisions_held,
        },
        "row_moves": {
            "reported_only": (
                "a moved probability is not a changed answer; the decisions above are "
                "what this used to be a proxy for"
            ),
            "median": float(numpy.median(moves)),
            "p99": float(numpy.percentile(moves, 99)),
            "worst": float(moves.max()),
            "over_a_point": int((moves > ROW_TOLERANCE).sum()),
            "of": int(moves.size),
        },
        "held": ordering_held and decisions_held,
    }


def source_commit() -> str:
    """The commit this checkout is on — the state the artifact was staged from.

    Refuses rather than shrugs. An entry that cannot say which repository state
    produced it describes a file nobody can rebuild, and a manifest full of those
    is what this field was added to stop.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root(),
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as unreachable:
        raise ValueError(
            "the source commit could not be read, so this artifact cannot say which "
            "repository state made it. Stage from a checkout with `git` on the path."
        ) from unreachable
    commit = result.stdout.strip()
    if len(commit) != 40:
        raise ValueError(f"`git rev-parse HEAD` returned {commit!r}, which is not a commit")
    return commit


def provenance(name: str) -> dict:
    """Where this head's answers came from, read off the tracked record.

    The distilled head names its teacher by hash. It claims approximate
    equivalence with that function and nothing else, so a release that did not
    say which function it was would be publishing an unfalsifiable claim.
    """
    supervision, corpus = SUPERVISION[name]
    record = {"supervision": supervision, "corpus": corpus}
    if name == "palette":
        split = json.loads((repo_root() / corpus / "split.json").read_text(encoding="utf-8"))
        teacher = split["teacher"]
        record["teacher"] = {
            key: teacher[key] for key in ("name", "checkpoint", "sha256", "resolved_through")
        }
    return record


def entry(name: str = "location", tag: str = TAG, run: str | None = None) -> dict:
    """The manifest row a fetch resolves: tag, asset, and the hash to check.

    Plus the two things the hash cannot carry — which commit staged it and what
    taught the head — because a release is read by people, not only fetched.
    """
    artifact = shipped_path(name)
    return {
        "tag": tag,
        "asset": artifact.name,
        "sha256": sha256_of(artifact),
        "bytes": artifact.stat().st_size,
        "precision": "fp16",
        "run": run or "its own",
        "source_commit": source_commit(),
        "provenance": provenance(name),
    }


def stage(
    name: str = "location",
    which: str = "best",
    tag: str = TAG,
    device: str = "auto",
    run: str | None = None,
) -> dict:
    """Convert, verify, hash, and write the manifest entry. Uploading is a person's job."""
    conversion = convert(name, which, run)
    agreed = agreement(name, which, device, run)
    if not agreed["held"]:
        shipped_path(name).unlink(missing_ok=True)
        raise ValueError(
            "the half-precision head does not agree with the full-precision one: the order "
            f"held={agreed['ordering']['held']} and "
            f"{agreed['decisions']['changed']} of its decisions changed "
            f"({agreed['decisions']['share']:.1%}). The artifact has been "
            "removed rather than hashed — a manifest entry for a head that decides "
            "differently is worse than no entry."
        )

    row = entry(name, tag, run)
    manifest = json.loads(manifest_path().read_text(encoding="utf-8"))
    heads = {**manifest.get("heads", {}), name: row}
    # Sorted, so the order of a tracked file is a fact about the heads rather
    # than about which one happened to be staged last.
    manifest["heads"] = dict(sorted(heads.items()))
    manifest_path().write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return {
        "head": name,
        "conversion": conversion,
        "agreement": agreed,
        "manifest_entry": row,
        "manifest": str(manifest_path()),
        "next": (
            f"create the GitHub release {tag} and upload {row['asset']}; "
            "`fractal-wallpapers fetch-weights` will verify the sha256 on the way down"
        ),
    }


__all__ = [
    "AUC_TOLERANCE",
    "DECISION_TOLERANCE",
    "HEADS",
    "ROW_TOLERANCE",
    "SUPERVISION",
    "SWAP_TOLERANCE",
    "SCHEMA",
    "TAG",
    "Shipment",
    "agreement",
    "convert",
    "entry",
    "halve",
    "manifest_path",
    "provenance",
    "sha256_of",
    "shipment_for",
    "shipped_path",
    "source_commit",
    "stage",
]
