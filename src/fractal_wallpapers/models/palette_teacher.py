"""The teacher: the source project's pretrained palette-preference head.

This head is not trained from human labels. There are none here to train it on —
the corpus that taught the original is a set of per-query tiered judgements that
lives in the other project and did not come across, and collecting a new one
would be weeks of somebody's evenings. What *did* come across is the trained
function itself, and this module is the only thing in this repository that
touches it.

## What is read, and what is emphatically not

One file: the checkpoint the source project's own **single-source pointer** names
(`tools/queries/scorer/data.ACTIVE_SCORER_DIR`). The pointer is resolved by
loading that module rather than by restating the path, for the same reason the
finished-render import loads the source's batch registry instead of copying its
table: a second copy of "which checkpoint is live" is a second answer, and the
two would drift the day one of them was flipped.

Nothing is written over there, ever. The source tree is read-only for this
repository, and a teacher is a function to evaluate, not a project to edit.

## The teacher runs on **this** repository's pictures

It would be cheaper to reuse the candidate images the source project made. It
would also make every number afterwards a statement about two renderers. So the
teacher is handed pictures made here, by this engine, through this colormap
library — the same rule the finished-render judges are held to — and what is
distilled is its opinion of *our* pictures. That is the only version of the
teacher a head deployed here could ever be asked to agree with.

## Its architecture is the student's

Single tower, one scalar out, 224×224 squashed input, ImageNet-1k
normalization: [`fractal_wallpapers.models.palette_head`] holds all of it,
because the teacher and the student are the same shape and spelling it twice
would let them disagree. What this module adds is only where the weights come
from and how to prove which ones they were.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

from fractal_wallpapers.models import palette_head

#: The source module that owns which checkpoint is live, relative to its root.
POINTER = Path("tools") / "queries" / "scorer" / "data.py"

#: The attribute on it that names the live checkpoint's directory.
POINTER_ATTRIBUTE = "ACTIVE_SCORER_DIR"

#: The checkpoint file inside that directory.
CHECKPOINT_NAME = "model_best.pt"


class TeacherError(RuntimeError):
    """The teacher cannot be reached, and guessing which one it is would be worse."""


def _pointer_module(root: Path):
    """Load the source project's pointer module by path, without polluting imports.

    By path rather than by name: `data` is a common enough module name that
    putting the source's directory on `sys.path` and importing it would be a
    coin toss, and the coin would be tossed differently depending on what else
    had been imported first.
    """
    path = Path(root) / POINTER
    if not path.is_file():
        raise TeacherError(
            f"{path} is missing. It is the source project's single-source pointer to the "
            f"live palette head, and this repository resolves the teacher through it rather "
            f"than hard-coding a version."
        )
    name = "fractal_wallpapers._source_scorer_pointer"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise TeacherError(f"{path} could not be loaded as a module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as failure:  # noqa: BLE001 — the reason matters more than the type
        raise TeacherError(
            f"{path} did not load: {failure!r}. It imports torch and torchvision, so the "
            f"models extra has to be installed for the teacher to be resolvable at all."
        ) from failure
    return module


def checkpoint_path(root: Path) -> Path:
    """The live teacher's checkpoint, resolved through the source's own pointer."""
    module = _pointer_module(root)
    directory = getattr(module, POINTER_ATTRIBUTE, None)
    if not directory:
        raise TeacherError(f"{POINTER} defines no {POINTER_ATTRIBUTE}")
    path = Path(directory) / CHECKPOINT_NAME
    if not path.is_file():
        raise TeacherError(
            f"{POINTER_ATTRIBUTE} points at {directory}, which holds no {CHECKPOINT_NAME}"
        )
    return path


def digest(path: Path) -> str:
    """The sha256 of the teacher's weights.

    Written onto every row the teacher labels. A machine-labeled corpus whose
    rows do not say *which* teacher cast them is a corpus that cannot be
    regenerated, only re-approximated.
    """
    hashed = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            hashed.update(chunk)
    return hashed.hexdigest()


def identity(root: Path) -> dict:
    """Who the teacher is, in the shape a record carries.

    Everything needed to find this exact function again: where the pointer sent
    us, what the weights hash to, and the config the source embedded beside them.
    """
    path = checkpoint_path(root)
    import torch

    saved = torch.load(path, map_location="cpu", weights_only=False)
    config = saved.get("config") or {}
    backbone = config.get("model")
    if backbone != palette_head.BACKBONE:
        raise TeacherError(
            f"the teacher's own config names backbone {backbone!r}, and this repository's "
            f"student is {palette_head.BACKBONE!r}. Distilling across two architectures is a "
            f"different exercise from the one this head is: fix the student, never the record."
        )
    return {
        "name": path.parent.name,
        "checkpoint": path.name,
        "sha256": digest(path),
        "backbone": backbone,
        "epoch": saved.get("epoch"),
        "config": config,
        "resolved_through": f"{POINTER.as_posix()}.{POINTER_ATTRIBUTE}",
    }


def load(root: Path, device: str = "auto"):
    """The teacher, ready to score. Returns `(model, where)`."""
    import torch

    from fractal_wallpapers.models import train

    where = train.device_of(device)
    path = checkpoint_path(root)
    saved = torch.load(path, map_location="cpu", weights_only=False)
    model = palette_head.build(pretrained=False)
    model.load_state_dict({key: value.float() for key, value in saved["state_dict"].items()})
    return model.to(where).eval(), where


def score(model, paths, where: str, batch_size: int = 64):
    """Every picture through the deploy transform, in the order it was given."""
    return scored_with(model, paths, palette_head.Transform(train=False), where, batch_size)


def scored_with(model, paths, transform, where: str, batch_size: int = 64):
    """One tower over a list of pictures: a scalar each, in the given order.

    Shared by the teacher and the student, because they are the same shape and a
    second reading loop would be a second answer to what a score is.
    """
    import numpy
    import torch
    from PIL import Image
    from torch.utils.data import DataLoader, Dataset

    class Pictures(Dataset):
        def __len__(self) -> int:
            return len(paths)

        def __getitem__(self, index: int):
            with Image.open(paths[index]) as opened:
                opened.load()
                image = opened.convert("RGB")
            return transform(image), index

    model.eval()
    out = numpy.zeros(len(paths), dtype=numpy.float64)
    loader = DataLoader(
        Pictures(),
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
        pin_memory=(where == "cuda"),
    )
    with torch.no_grad():
        for pictures, index in loader:
            values = model(pictures.to(where, non_blocking=True)).view(-1)
            out[index.numpy()] = values.float().cpu().numpy()
    return out


def record(root: Path) -> str:
    """The teacher's identity as one JSON line, for a log."""
    return json.dumps(identity(root), ensure_ascii=False)


__all__ = [
    "CHECKPOINT_NAME",
    "POINTER",
    "POINTER_ATTRIBUTE",
    "TeacherError",
    "checkpoint_path",
    "digest",
    "identity",
    "load",
    "record",
    "score",
    "scored_with",
]
