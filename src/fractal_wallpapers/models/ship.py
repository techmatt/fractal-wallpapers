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
2. **The head still says the same thing.** Score this repository's own evaluation
   side both ways and compare, per location and in the aggregate. The ordering
   is what the head is used for, so the number that matters is the AUC at each
   cutpoint, and the tolerance is tight enough that a real degradation cannot
   hide inside it.
3. **The hash is of the file that was checked**, taken after both, so a manifest
   entry can never describe a file nobody verified.

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
from pathlib import Path

from fractal_wallpapers.models import head, metrics, scoring, train
from fractal_wallpapers.paths import repo_root

#: The schema of the weights manifest.
SCHEMA = 1

#: The release tag a first shipment goes to.
TAG = "weights-v1"

#: How far the shipped head's ordering may move from the full-precision head's
#: before the shipment is refused, in AUC at any cutpoint. A tenth of a point:
#: far below anything the acceptance read is trying to detect, and far above the
#: rounding fp16 actually produces.
AUC_TOLERANCE = 0.001

#: How far any single location's probability may move. Larger than the AUC bound
#: on purpose — one row near a decision boundary can move much further than the
#: order does, and pretending otherwise would make the check fail on nothing.
ROW_TOLERANCE = 0.01


def manifest_path() -> Path:
    """The tracked manifest `fetch-weights` reads."""
    return repo_root() / "models" / "weights.json"


def shipped_path(name: str = "location", run: str | None = None) -> Path:
    """The artifact itself: half precision, living beside its tracked metadata.

    At the head's root, not the run's: what ships is the head, and which of its
    runs the weights came from is a fact the config inside the file carries.
    """
    del run
    return train.head_dir(name) / "head.fp16.pt"


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

    source = train.checkpoint_path(name, which, run)
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
    """Score this repository's evaluation side both ways and compare."""
    import numpy

    from fractal_wallpapers.models import dataset
    from fractal_wallpapers.models import tiles as tile_module

    rows = tile_module.read_locations()
    grouped = tile_module.tiles_by_location(tile_module.read_manifest())
    locations = dataset.join(rows, grouped)
    holdout = [location for location in locations if location.side == "eval"]
    paths = [location.canonical() for location in holdout]
    labels = numpy.array([location.score for location in holdout])

    full, config, where = scoring.load(train.checkpoint_path(name, which, run), device)
    transform = scoring.transform_of(config)
    classes = int(config["classes"])
    before = train.score(full, paths, transform, where, classes, {"batch_size": 64})
    del full

    halved, _, _ = scoring.load(shipped_path(name), device)
    after = train.score(halved, paths, transform, where, classes, {"batch_size": 64})

    worst_row = float(numpy.abs(after - before).max())
    cutpoints = {}
    worst_auc = 0.0
    for index in range(classes - 1):
        label = head.cutpoint_label(index)
        truth = (labels >= index + 2).astype(int)
        a = metrics.auc(truth, before[:, index])
        b = metrics.auc(truth, after[:, index])
        moved = None if a is None or b is None else abs(a - b)
        if moved is not None:
            worst_auc = max(worst_auc, moved)
        cutpoints[label] = {"fp32": a, "fp16": b, "moved": moved}

    held = worst_auc <= AUC_TOLERANCE and worst_row <= ROW_TOLERANCE
    return {
        "locations": len(holdout),
        "cutpoints": cutpoints,
        "worst_auc_move": worst_auc,
        "worst_row_move": worst_row,
        "tolerance": {"auc": AUC_TOLERANCE, "row": ROW_TOLERANCE},
        "held": held,
    }


def entry(name: str = "location", tag: str = TAG) -> dict:
    """The manifest row a fetch resolves: tag, asset, and the hash to check."""
    artifact = shipped_path(name)
    return {
        "tag": tag,
        "asset": artifact.name,
        "sha256": sha256_of(artifact),
        "bytes": artifact.stat().st_size,
        "precision": "fp16",
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
            "the half-precision head does not agree with the full-precision one: AUC moved "
            f"{agreed['worst_auc_move']:.5f} and one location moved "
            f"{agreed['worst_row_move']:.5f}. "
            "The artifact has been removed rather than hashed — a manifest entry for a head "
            "that scores differently is worse than no entry."
        )

    row = entry(name, tag)
    manifest = json.loads(manifest_path().read_text(encoding="utf-8"))
    manifest.setdefault("heads", {})[name] = row
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
    "ROW_TOLERANCE",
    "SCHEMA",
    "TAG",
    "agreement",
    "convert",
    "entry",
    "halve",
    "manifest_path",
    "sha256_of",
    "shipped_path",
    "stage",
]
