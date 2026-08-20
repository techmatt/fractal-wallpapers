"""Training the two finished-render judges.

## The unit is a picture, and that is the whole difference

The location head trains on *places*: a place owns thirty-two tiles and draws one
of them each epoch, so what it learns is which places are worth rendering and not
which rendering of a place is good. These two judges answer the question after
it, so their unit is a **picture** — one row, one file, one verdict — and a place
that carries a dozen pictures contributes a dozen examples on purpose, because
the differences between them are exactly what is being learned.

That leaves one thing to guard. A place with a dozen pictures also contributes a
dozen votes, and the corpora are uneven: the strange corpus averages five
pictures a place and reaches nine. So the sampler carries the location weight the
location head's sampler already had — `1 / pictures at this place` — which makes
a place worth one place's gradient however many ways it was colored, while every
distinct verdict still reaches the model. The class balance is the same square
root for the same reason.

## Two recipes, from two checkpoints, with what changed written down

Each judge's recipe is the one the source project trained its own head under,
read out of that checkpoint's committed config. They agree on almost everything —
forty epochs, batches of thirty-two, the same two learning rates and the same
decay, geometric augmentation only — and differ where the corpora differ: a
medium backbone for smooth renders and a small one for strange. Both now train
**four** tiers; strange's third was a fact about a corpus collected before a 4
existed in it, and it moved the session its store first held one.
[`INHERITANCE`] lists every behavioural key that came across and every
one that did not, with the reason, because "the same recipe" is a claim a reader
has to be able to check rather than take.

**Colour augmentation is off, and here that is not a tuning choice.** For these
judges the coloring *is* the label: a brightness jitter is a small edit to the
thing the verdict is about. Both source recipes say so and both are carried.

## The epoch is chosen on the training side, by a rule that can see probabilities

Something has to decide which epoch to keep, and choosing it on the blind sheet
would spend the only unanchored reading of that population that exists — quietly,
because the head never trains on it and every number read off it afterwards is
still inflated. So a seeded slice of the *training* side pays for model
selection, exactly as the location head's does, and the sheet pays for nothing.

**What it is chosen *by* is not the source project's average precision, and that
is the one change here that was forced rather than chosen.** Average precision is
a rank statistic: it is invariant to any monotone rescaling of the scores, so it
cannot see a probability at all. Selecting on it picked, for two of three seeds
of the smooth judge, an epoch whose deploy-mode probabilities had transiently
collapsed — one of them reading a mean `P(≥2)` of 0.002 on a slice that is 78%
`≥2`, while its loss curve looked healthy because the loss is computed in
training mode where batch statistics hide it. Average precision rated that
checkpoint 0.824 and the sound one from the same run 0.810; it preferred the
broken one.

So the objective is the **validation loss** — the same cross-entropy the trainer
minimizes, computed on the selection slice through the deploy transform. It is a
proper scoring rule, so it is minimized only by probabilities that are both
well ordered *and* correctly scaled, and it rated those same two checkpoints 5.85
against 0.58. That matters here more than it might elsewhere: this head's
interface **is** its probabilities — the supply engine reads `P(≥4)` directly —
so an objective blind to them is an objective blind to what the head is for.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from fractal_wallpapers.labeling import finished
from fractal_wallpapers.labeling import registry as registry_module
from fractal_wallpapers.models import dataset, head, metrics, renders, train

#: The schema every record here carries.
SCHEMA = 1

#: The third side, carried from the location head so the word means one thing.
SELECTION = dataset.SELECTION

#: Share of the training side held out to choose the epoch on, and its seed.
SELECTION_SHARE = dataset.SELECTION_SHARE
SELECTION_SEED = dataset.SELECTION_SEED

#: What each judge trains under. Every value is one the source project's own head
#: for that corpus trained under, read out of its committed config.
#:
#: **`classes` is the model's own, not the store's.** The corpus is cast on
#: [`finished.SCALE`] for every head; what a checkpoint can emit is decided here,
#: written into its config, and read back off the checkpoint by everything that
#: loads one. The two numbers stay separate on purpose — a store may hold a tier
#: no trained head has learned yet, which is the only way a retrain can ever be
#: collected. `strange_render` sat at three while its store grew 4s the shipped
#: head could not see; this is the edit that closed that gap, and every head here
#: now trains the whole scale.
RECIPES: dict[str, dict] = {
    "smooth_render": {
        "classes": 4,
        "backbone": "mobilenetv4_conv_medium.e250_r384_in12k",
        "selection_cutpoint": 3,
    },
    "strange_render": {
        "classes": 4,
        "backbone": "mobilenetv4_conv_small.e2400_r224_in1k",
        "selection_cutpoint": 3,
    },
}

#: What both recipes share, because both source configs did.
COMMON = {
    "pretrained": True,
    "geometry": "stretch",
    "epochs": 40,
    "batch_size": 32,
    "backbone_lr": 2e-4,
    "head_lr": 1e-3,
    "weight_decay": 0.05,
    "drop_rate": 0.2,
    "drop_path_rate": 0.1,
    "grad_clip": 1.0,
    "seed": 0,
    "workers": 4,
    "amp": "off",
    "border_crop": 0.05,
    "augmentation": "geometric only — border crop and both flips. No colour, no JPEG jitter",
    "class_balance": "sqrt",
    "source_dims": [1280, 720],
    "target_dims": [head.TARGET_WIDTH, head.TARGET_HEIGHT],
    "loss": "CORN ordinal, K-1 conditional-subset tasks",
    "sampler": "w_class[1/sqrt] x w_place[1/pictures at this place], in that order",
    "selection": (
        "min validation loss over the selection slice, through the deploy transform: the "
        "mean cross-entropy of the unconditional probability at each cutpoint against that "
        "cutpoint's own truth. A proper scoring rule, so it sees the scale and not only the "
        "order"
    ),
}

#: What the recipes inherited, and every key that did not come across.
INHERITANCE = {
    "source": {
        "smooth_render": "the source project's wallpaper head v4b, config embedded beside it",
        "strange_render": "the source project's render-mode head v3, config embedded beside it",
    },
    "identical": [
        "amp",
        "backbone",
        "backbone_lr",
        "batch_size",
        "border_crop",
        "drop_path_rate",
        "drop_rate",
        "epochs",
        "geometry",
        "grad_clip",
        "head_lr",
        "loss",
        "pretrained",
        "source_dims",
        "target_dims",
        "weight_decay",
    ],
    "changed": [
        {
            "key": "classes",
            "was": "four for smooth renders and three for strange, each the source head's own",
            "now": "four for both",
            "why": "the strange corpus was collected before a 4 existed in it, so three was a "
            "fact about that population rather than a property of the scale. Its store now "
            "holds 4s, and a recipe that cannot express a verdict present in its own "
            "population refuses to train rather than mis-fit a top cutpoint — see "
            "[`refuse_inexpressible`]. Widening it is the only move that does not throw the "
            "tier away, and it makes the head's decode reach the tier the release path cuts "
            "on. The smooth recipe is untouched; it was already four.",
        },
        {
            "key": "augmentation",
            "was": "geometric only (border crop + both flips), colour off",
            "now": "the same, spelled through this repository's own transform",
            "why": "the same three stages, and colour is off in both. Named here because "
            "this repository's transform jitters brightness, contrast and JPEG quality by "
            "default for the location head, and those defaults are switched off rather "
            "than absent.",
        },
        {
            "key": "row_weighting",
            "was": "1 / near-duplicate group size, from a colour-CLIP grouping of the "
            "source's own crops at a 0.974 cut (strange renders only)",
            "now": "1 / pictures at this place",
            "why": "the grouping is an artifact keyed on the source project's image ids, "
            "and this repository keeps none of them — every picture here is regenerated "
            "from a recipe. Re-deriving it would need a model this project does not have. "
            "The structural weight is what remains: it equalizes places rather than "
            "look-alikes, so it is coarser, and it is the same weight the location head's "
            "sampler already carried.",
        },
        {
            "key": "split",
            "was": "a seeded re-derivation over locations, at a 40% evaluation share "
            "(strange), or one batch set frozen as authority (smooth)",
            "now": "the eval-only pin, and nothing else",
            "why": "both of those decide which of a pooled corpus is held out. Here the "
            "held-out set is not a share of the corpus at all — it is the blind sheet, "
            "pinned permanently, and every other batch is anchored and trains.",
        },
        {
            "key": "selection_population",
            "was": "the pooled evaluation side",
            "now": "a seeded slice of the TRAINING side",
            "why": "the evaluation side here is one blind sheet bought to referee two "
            "heads. An instrument is spent the moment it trains, and choosing an epoch on "
            "it is a partial spend that leaves nothing red.",
        },
        {
            "key": "selection_statistic",
            "was": "maximum average precision at the top cutpoint",
            "now": "minimum validation loss, the same cross-entropy training minimizes",
            "why": "FORCED, not chosen. Average precision is a rank statistic and is "
            "invariant to any monotone rescaling of the scores, so it cannot see a "
            "probability. It selected transiently-collapsed checkpoints for two of three "
            "seeds of the smooth judge — one reading a mean P(>=2) of 0.002 on a slice that "
            "is 78% >=2 — and rated the broken checkpoint ABOVE the sound one from the same "
            "run, 0.824 to 0.810. The loss is a proper scoring rule and rated the same pair "
            "5.85 to 0.58. This head's interface is its probabilities, so an objective "
            "blind to them is blind to what it is for.",
        },
    ],
}


def _claim(directory: Path) -> Path:
    """Take the run directory, or refuse. The lock itself lives in [`train.claim`]."""
    try:
        return train.claim(directory)
    except RuntimeError as taken:
        raise TrainingError(str(taken)) from None


def validation_loss(labels, probabilities, classes: int) -> float:
    """The selection objective, under the name this head's records call it by.

    It is [`metrics.cutpoint_cross_entropy`] and nothing else — a proper scoring
    rule over the unconditional probabilities, which are what the interface
    exposes and what every consumer reads. Kept as a name here because every
    config and metrics record this trainer has written calls it the validation
    loss, and moved to `metrics` because the location head's regime-robust
    retrain is judged on the same statistic and two implementations of it would
    be two answers.
    """
    return metrics.cutpoint_cross_entropy(labels, probabilities, classes)


class TrainingError(RuntimeError):
    """A head that cannot be trained on what is here."""


def head_dir(head_name: str, run: str | None = None) -> Path:
    from fractal_wallpapers.paths import repo_root

    base = repo_root() / "models" / finished.head_of(head_name)
    return base / run if run else base


def checkpoint_path(head_name: str, which: str = "best", run: str | None = None) -> Path:
    return head_dir(head_name, run) / f"{which}.pt"


def config_path(head_name: str, run: str | None = None) -> Path:
    return head_dir(head_name, run) / "config.json"


def metrics_path(head_name: str, run: str | None = None) -> Path:
    return head_dir(head_name, run) / "metrics.json"


def recipe_for(head_name: str) -> dict:
    """One judge's whole recipe: what both share, and what is its own."""
    return {**COMMON, **RECIPES[finished.head_of(head_name)]}


def refuse_inexpressible(head_name: str, scores: list[int]) -> int:
    """Return the recipe's class count, having proved it can carry every verdict.

    The store is cast on [`finished.SCALE`] and the recipe says how many tiers
    this head can express. The two are allowed to differ — that difference is the
    whole point of a pending retrain. What is not allowed is training *through*
    it: a 4 handed to a three-class CORN head is a rank with no task to carry it,
    and the failure is a silently mis-fitted top cutpoint rather than a crash.
    """
    expressible = int(recipe_for(head_name)["classes"])
    beyond = sorted({score for score in scores if score > expressible})
    if beyond:
        raise TrainingError(
            f"the {head_name} corpus holds verdicts at tier(s) {beyond} and this recipe trains "
            f"{expressible} classes. Raise `RECIPES[{head_name!r}]['classes']` to {max(beyond)} "
            f"— that edit IS the retrain, and it re-reads the whole corpus at the wider scale. "
            f"Dropping the rows instead would train a head on a population its own labelers no "
            f"longer judge."
        )
    return expressible


@dataclass
class Picture:
    """One training unit: a finished render, its verdict, and where it is."""

    path: Path
    score: int
    side: str
    batch: str
    place: str
    partition: str
    mode: str
    name: str


def population(head_name: str) -> tuple[list[Picture], dict]:
    """Every judged picture, on the side it belongs to.

    The evaluation side is the pin and only the pin. The selection slice is
    carved out of the training side afterwards, by a seeded draw over **places**
    so that a place's pictures cannot straddle the two.
    """
    import random

    head_name = finished.head_of(head_name)
    known = finished.registry(head_name)
    rows = finished.resolved(head_name).scored()
    crops = renders.crop_dir(head_name)

    pictures, absent = [], []
    for row in rows:
        name = renders.job_name({**row, "_head": head_name})
        path = crops / f"{name}.jpg"
        if not path.is_file():
            absent.append(name)
            continue
        pinned = registry_module.lookup(known, row["batch"]).eval_only
        pictures.append(
            Picture(
                path=path,
                score=int(row["score"]),
                side="eval" if pinned else "train",
                batch=row["batch"],
                place=repr(finished.place_of(row)),
                partition=row.get("partition") or "",
                mode=row["mode"],
                name=name,
            )
        )
    if absent:
        raise TrainingError(
            f"{len(absent)} of {len(rows)} judged pictures are not in the render cache "
            f"(e.g. {absent[:3]}). Build it before training: a head trained on the subset "
            f"that happened to be on disk is a head nobody can reproduce."
        )

    refuse_inexpressible(head_name, [picture.score for picture in pictures])

    training = [picture for picture in pictures if picture.side == "train"]
    places = sorted({picture.place for picture in training})
    draw = random.Random(SELECTION_SEED)
    draw.shuffle(places)
    chosen = set(places[: max(1, round(len(places) * SELECTION_SHARE))])
    for picture in training:
        if picture.place in chosen:
            picture.side = SELECTION

    record = {
        "share": SELECTION_SHARE,
        "seed": SELECTION_SEED,
        "drawn_over": "places on the training side, so a place's pictures cannot straddle",
        "places": len(chosen),
        "of_places": len(places),
        "pictures": sum(1 for p in pictures if p.side == SELECTION),
    }
    return pictures, record


def sides(pictures: list[Picture]) -> dict[str, list[Picture]]:
    out: dict[str, list[Picture]] = {"train": [], SELECTION: [], "eval": []}
    for picture in pictures:
        out[picture.side].append(picture)
    return out


def histogram(pictures: list[Picture]) -> dict:
    from collections import Counter

    counted = Counter(picture.score for picture in pictures)
    return {str(score): counted[score] for score in sorted(counted)}


def weights(pictures: list[Picture]) -> tuple[list[float], dict]:
    """The two weights, multiplied in the order the module docstring names.

    `w_place` first, because it is about the population; `w_class` last, because
    it is a per-class scalar and applying it last means it scales every picture of
    a class alike and cannot change the mix of places inside one.
    """
    from collections import Counter

    per_place = Counter(picture.place for picture in pictures)
    per_class = Counter(picture.score for picture in pictures)
    out, mass = [], {}
    for picture in pictures:
        weight = (1.0 / per_place[picture.place]) * (1.0 / (per_class[picture.score] ** 0.5))
        out.append(weight)
        mass[str(picture.score)] = mass.get(str(picture.score), 0.0) + weight
    total = sum(out) or 1.0
    return out, {
        "places": len(per_place),
        "largest_place": max(per_place.values()),
        "sampled_mass": {key: round(value / total, 4) for key, value in sorted(mass.items())},
        "raw_share": {
            str(score): round(count / len(pictures), 4)
            for score, count in sorted(per_class.items())
        },
    }


class Crops:
    """The training set: one picture an example, with its own seeded jitter.

    **Defined here rather than inside the function that builds it**, and that is
    not a style choice. A loader worker on Windows is spawned rather than forked,
    so the dataset is pickled and re-imported by name in the child; a class
    defined inside a function has no importable name and the child dies. The
    location head shipped that defect once, because its smoke test ran with zero
    workers and never tried.

    Subclassing `torch.utils.data.Dataset` would mean importing torch to define
    the module, which the base install does not have — the duck-typed shape is
    all a `DataLoader` needs.
    """

    def __init__(self, rows: list[Picture], transform) -> None:
        self.rows = rows
        self.transform = transform
        self.epoch = 0

    def set_epoch(self, epoch: int) -> None:
        self.epoch = epoch

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int):
        import random

        from PIL import Image

        row = self.rows[index]
        with Image.open(row.path) as opened:
            opened.load()
            image = opened.convert("RGB")
        # Seeded on the picture and the epoch, so a run reproduces and a picture
        # still gets a different crop every pass.
        return self.transform(image, random.Random(f"{row.name}:{self.epoch}")), row.score, index


def _loader(pictures: list[Picture], transform, recipe: dict, where: str):
    import torch
    from torch.utils.data import DataLoader, WeightedRandomSampler

    examples = Crops(pictures, transform)
    raw, mass = weights(pictures)
    sampler = WeightedRandomSampler(
        torch.tensor(raw, dtype=torch.double), num_samples=len(pictures), replacement=True
    )
    loader = DataLoader(
        examples,
        batch_size=recipe["batch_size"],
        sampler=sampler,
        num_workers=recipe["workers"],
        pin_memory=(where == "cuda"),
        persistent_workers=False,
        drop_last=False,
    )
    return examples, loader, mass


def run(
    head_name: str,
    device: str = "auto",
    epochs: int | None = None,
    seed: int | None = None,
    run_name: str | None = None,
    log=train.say,
) -> dict:
    """Train one finished-render judge, and write its checkpoints and records."""
    import numpy
    import torch

    head_name = finished.head_of(head_name)
    recipe = recipe_for(head_name)
    if epochs is not None:
        recipe["epochs"] = int(epochs)
    if seed is not None:
        recipe["seed"] = int(seed)
    classes = int(recipe["classes"])

    where = train.device_of(device)
    train.set_seed(int(recipe["seed"]))
    pictures, selection_record = population(head_name)
    by_side = sides(pictures)
    training, choosing, holdout = by_side["train"], by_side[SELECTION], by_side["eval"]
    if not choosing:
        raise TrainingError("the selection slice is empty; there is nothing to choose an epoch on")
    # The check the trainer runs on the split it BUILT, not a claim the pin makes
    # about itself: a pass that never consulted the pin still dies here.
    pinned = {repr(key) for key in finished.pinned(head_name)}
    trespassing = [p for p in training + choosing if p.place in pinned]
    if trespassing:
        raise TrainingError(
            f"{len(trespassing)} training pictures sit on a place pinned to the "
            f"{head_name} evaluation side (e.g. batch {trespassing[0].batch!r}). A blind "
            f"sheet is spent the moment it trains — fix the split, never the pin."
        )
    pin_report = {
        "pinned_places": len(pinned),
        "asserted_on": "the location, so a re-render under a fresh recipe is still the pin",
        "train_pictures_on_a_pinned_place": 0,
        "eval_pictures": len(holdout),
    }

    log(f"device {where}  torch {torch.__version__}  seed {recipe['seed']}  head {head_name}")
    log(
        f"pictures {len(pictures)}: train {len(training)} {histogram(training)}, "
        f"selection {len(choosing)} {histogram(choosing)}, "
        f"eval {len(holdout)} {histogram(holdout)}"
    )
    log(f"pin: {pin_report}")

    probe = head.build(
        num_classes=classes, backbone=recipe["backbone"], pretrained=recipe["pretrained"]
    )
    data_config = head.data_config(probe)
    del probe
    log(f"data config {data_config}")

    model = head.build(
        num_classes=classes,
        backbone=recipe["backbone"],
        pretrained=recipe["pretrained"],
        drop_rate=recipe["drop_rate"],
        drop_path_rate=recipe["drop_path_rate"],
    ).to(where)
    head_parameters = list(model.get_classifier().parameters())
    head_ids = {id(parameter) for parameter in head_parameters}
    backbone_parameters = [p for p in model.parameters() if id(p) not in head_ids]
    optimizer = torch.optim.AdamW(
        [
            {"params": backbone_parameters, "lr": recipe["backbone_lr"]},
            {"params": head_parameters, "lr": recipe["head_lr"]},
        ],
        weight_decay=recipe["weight_decay"],
    )
    schedule = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=recipe["epochs"])

    # Geometric only: the coloring is the label, so the three colour stages this
    # repository's transform runs for the location head are switched off here.
    train_transform = head.Transform(
        data_config["mean"],
        data_config["std"],
        data_config["interpolation"],
        train=True,
        border_crop=recipe["border_crop"],
        jpeg=None,
        brightness=0.0,
        contrast=0.0,
    )
    deploy_transform = head.Transform(
        data_config["mean"], data_config["std"], data_config["interpolation"], train=False
    )
    examples, loader, mass = _loader(training, train_transform, recipe, where)
    log(f"sampled mass {json.dumps(mass['sampled_mass'])} over {mass['places']} places")

    choosing_paths = [picture.path for picture in choosing]
    choosing_labels = numpy.array([picture.score for picture in choosing])
    cutpoint = min(int(recipe["selection_cutpoint"]), classes) - 2

    directory = head_dir(head_name, run_name)
    directory.mkdir(parents=True, exist_ok=True)
    lock = _claim(directory)
    resume = directory / "resume.pt"

    best_metric, best_state, best_epoch, history = float("inf"), None, -1, []
    start = 0
    if resume.is_file():
        saved = torch.load(resume, map_location=where, weights_only=False)
        model.load_state_dict(saved["model"])
        optimizer.load_state_dict(saved["optimizer"])
        schedule.load_state_dict(saved["schedule"])
        best_metric, best_epoch = saved["best_metric"], saved["best_epoch"]
        best_state, history = saved["best_state"], saved["history"]
        start = saved["epoch"] + 1
        torch.set_rng_state(saved["torch_rng"])
        if where == "cuda" and saved.get("cuda_rng") is not None:
            torch.cuda.set_rng_state_all(saved["cuda_rng"])
        numpy.random.set_state(saved["numpy_rng"])
        log(f"resumed at epoch {start} (best {best_metric:.4f} at epoch {best_epoch})")

    began = time.time()
    for epoch in range(start, recipe["epochs"]):
        examples.set_epoch(epoch)
        model.train()
        clock, running, seen = time.time(), 0.0, 0
        for crops, labels, _ in loader:
            crops = crops.to(where, non_blocking=True)
            labels = labels.to(where, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            logits = model(crops)
            loss = head.loss_of(logits, labels, num_classes=classes)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), recipe["grad_clip"])
            optimizer.step()
            running += loss.item() * crops.size(0)
            seen += crops.size(0)
        schedule.step()

        if any(not torch.isfinite(parameter).all() for parameter in model.parameters()):
            raise TrainingError(f"the head went non-finite at epoch {epoch}")

        probabilities = train.score(model, choosing_paths, deploy_transform, where, classes, recipe)
        objective = validation_loss(choosing_labels, probabilities, classes)
        record = {
            "epoch": epoch,
            "loss": running / max(seen, 1),
            "seconds": round(time.time() - clock, 1),
            "selection_loss": objective,
            f"selection_ap_ge{cutpoint + 2}": metrics.average_precision(
                (choosing_labels >= cutpoint + 2).astype(int), probabilities[:, cutpoint]
            ),
        }
        for index in range(classes - 1):
            record[f"selection_auc_ge{index + 2}"] = metrics.auc(
                (choosing_labels >= index + 2).astype(int), probabilities[:, index]
            )
            record[f"selection_mean_p_ge{index + 2}"] = float(probabilities[:, index].mean())
        history.append(record)
        log(
            f"epoch {epoch:2d}  loss {record['loss']:.4f}  "
            f"val {train.shown(objective)}  "
            f"AP>={cutpoint + 2} {train.shown(record[f'selection_ap_ge{cutpoint + 2}'])}  "
            + "  ".join(
                f"AUC>={index + 2} {train.shown(record[f'selection_auc_ge{index + 2}'])}"
                for index in range(classes - 1)
            )
            + f"  ({record['seconds']}s)"
        )

        if objective is not None and objective < best_metric:
            best_metric, best_epoch = objective, epoch
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

        temporary = directory / "resume.pt.partial"
        torch.save(
            {
                "epoch": epoch,
                "model": model.state_dict(),
                "optimizer": optimizer.state_dict(),
                "schedule": schedule.state_dict(),
                "best_metric": best_metric,
                "best_epoch": best_epoch,
                "best_state": best_state,
                "history": history,
                "torch_rng": torch.get_rng_state(),
                "cuda_rng": torch.cuda.get_rng_state_all() if where == "cuda" else None,
                "numpy_rng": numpy.random.get_state(),
            },
            temporary,
        )
        temporary.replace(resume)

    lock.unlink(missing_ok=True)
    last_state = {k: v.detach().cpu() for k, v in model.state_dict().items()}
    if best_state is None:
        best_state = last_state

    config = {
        "schema": SCHEMA,
        "head": head_name,
        "run": run_name,
        **recipe,
        "mean": list(data_config["mean"]),
        "std": list(data_config["std"]),
        "interpolation": data_config["interpolation"],
        "best_epoch": best_epoch,
        "inherited": INHERITANCE,
        "renders": {"seed": renders.SEED, "jpeg_quality": 90},
        "selection_slice": selection_record,
        "precision": "fp32",
    }
    torch.save(
        {"state_dict": best_state, "config": config}, checkpoint_path(head_name, "best", run_name)
    )
    torch.save(
        {"state_dict": last_state, "config": config}, checkpoint_path(head_name, "last", run_name)
    )
    if resume.is_file():
        resume.unlink()

    record = {
        "schema": SCHEMA,
        "head": head_name,
        "run": run_name,
        "device": where,
        "wall_seconds": round(time.time() - began, 1),
        "best_epoch": best_epoch,
        "best_selection_objective": best_metric,
        "selection_metric": "validation loss (minimized)",
        "pictures": {
            "total": len(pictures),
            "train": len(training),
            "selection": len(choosing),
            "eval": len(holdout),
        },
        "class_counts": {
            "train": histogram(training),
            "selection": histogram(choosing),
            "eval": histogram(holdout),
        },
        "eval_pin": pin_report,
        "selection_slice": selection_record,
        "sampled_mass": mass,
        "history": history,
        "checkpoints": {
            "best": str(checkpoint_path(head_name, "best", run_name)),
            "last": str(checkpoint_path(head_name, "last", run_name)),
        },
    }
    config_path(head_name, run_name).write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    metrics_path(head_name, run_name).write_text(
        json.dumps(record, indent=2, default=str) + "\n", encoding="utf-8", newline="\n"
    )
    return record


__all__ = [
    "COMMON",
    "INHERITANCE",
    "RECIPES",
    "SCHEMA",
    "SELECTION",
    "SELECTION_SEED",
    "SELECTION_SHARE",
    "Picture",
    "TrainingError",
    "checkpoint_path",
    "config_path",
    "head_dir",
    "histogram",
    "metrics_path",
    "population",
    "recipe_for",
    "run",
    "sides",
    "validation_loss",
    "weights",
]
