"""Training the location head: the recipe, the loop, and the record it leaves.

## What is inherited and what is decided here

The hyperparameters are the source project's, carried across as [`RECIPE`] and
not re-tuned. That is deliberate: this repository is changing the corpus's split,
the tile recipe and the coloring pipeline all at once, and a bar that compares
the result against the incumbent can only be read if the *learning* did not move
too. A knob that drifted alongside them would be measured as if it were one of
them.

Three things do move, each because a locked convention here required it, and each
declared in the pre-registration rather than discovered in the numbers:

* **The epoch is chosen on a slice of the training side**, never on the
  evaluation side. The incumbent picked its checkpoint by maximizing an objective
  over six hundred and seventy held-out instrument rows. An instrument is spent
  the moment it trains, and picking on it is a partial spend that leaves nothing
  red — so the training side pays for selection here. See
  [`fractal_wallpapers.models.dataset`].
* **The pictures are this project's own.** A tile is a crop of an extended field,
  colored by this engine's percentile stretch through this repository's colormap
  library. The incumbent's tiles came from a different renderer with a different
  coloring. Two heads compared across that boundary are two whole pipelines
  compared, and the acceptance read says so.
* **The source frame is 640×360**, where the incumbent's was 512×288. The deploy
  transform still ends at 384×224, so the head's input is unchanged; what changed
  is how much resampling happens before it.

## Resumable, because a long run gets killed

Every epoch writes an atomic snapshot of the model, the optimizer, the schedule,
the best-so-far and the random state. A relaunch continues from the next epoch,
so a kill costs one epoch rather than the run. A clean finish deletes it.

## Two checkpoints

`best` is the epoch the selection slice chose. `last` is where the schedule
ended. Both are kept: the two disagreeing by more than noise is worth knowing,
and it costs a file.
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path

from fractal_wallpapers.labeling import pins
from fractal_wallpapers.models import dataset, head, metrics
from fractal_wallpapers.models import tiles as tile_module
from fractal_wallpapers.paths import repo_root

#: The schema every record here carries.
SCHEMA = 1

#: The training recipe, carried from the source project's deployed head and not
#: re-tuned. Every value here is one the incumbent trained under.
RECIPE = {
    "classes": head.CLASSES,
    "backbone": head.BACKBONE,
    # The backbone starts from its ImageNet-12k weights, never from an earlier
    # head of this project: warm-starting would make each version's numbers a
    # statement about the whole chain behind it.
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
    # Full precision, no autocast. These are differences of scores near a
    # cutpoint, and fp16 accumulation moves rows across the line.
    "amp": "off",
    "beta_biased": dataset.BETA_BIASED,
    "class_balance": "sqrt",
    "source_dims": [head.SOURCE_WIDTH, head.SOURCE_HEIGHT],
    "target_dims": [head.TARGET_WIDTH, head.TARGET_HEIGHT],
    "loss": "CORN ordinal, K-1 conditional-subset tasks",
    "sampler": "w_class[1/sqrt] x w_group[1/size] x w_source[beta], in that order",
    "selection": "max average precision at the first cutpoint, over the selection slice",
    "selection_objective": "ap_ge2",
    # The geometry the tiles are drawn at. One regime is the shipped recipe; a
    # run handed more sees every label row once per regime an epoch, and is told
    # nothing about which one it is looking at.
    "regimes": ["640x360ss2"],
}

#: The two objectives an epoch has been chosen on here, and what each one is.
#:
#: `ap_ge2` is the shipped head's, carried from the source project. It is a rank
#: statistic, so it is invariant to any monotone rescaling of the scores — it
#: cannot see a head that keeps the order and collapses the scale, which is
#: exactly the failure a floor walks through.
#:
#: `cutpoint_cross_entropy` is the repository's proper scoring rule, already the
#: selection objective of every head here that reads its own probabilities. A
#: run judged on that rule selects on it too, so selection is not a second,
#: unstated difference between the head being judged and the bar judging it.
SELECTION_OBJECTIVES = {
    "ap_ge2": (
        "max average precision at the first cutpoint, over the selection slice, at the "
        "canonical regime"
    ),
    "cutpoint_cross_entropy": (
        "min the cutpoint cross-entropy over the selection slice, at the canonical regime: "
        "a proper scoring rule, so it sees the scale a floor is a point on and not only the "
        "order"
    ),
}


#: What the recipe above inherited, and the four things it did not.
#:
#: The source project's deployed head embeds its own config in its checkpoint,
#: and thirty of its keys are behavioural. Twenty-six are reproduced here value
#: for value. The other four are listed with the reason, because "identical
#: recipe" is a claim a reader has to be able to check rather than take.
INHERITANCE = {
    "source": "the source project's deployed head, config embedded in its checkpoint",
    "identical": [
        "amp",
        "backbone",
        "backbone_lr",
        "batch_size",
        "beta_biased",
        "class_balance",
        "drop_path_rate",
        "drop_rate",
        "epochs",
        "geometry",
        "grad_clip",
        "head_lr",
        "input_size",
        "interpolation",
        "loss",
        "mean",
        "no_jpeg_aug",
        "num_classes",
        "num_workers",
        "patience",
        "sampler",
        "seed",
        "std",
        "target",
        "target_dims",
        "weight_decay",
    ],
    "changed": {
        "eval_split_is_val": (
            "the incumbent chose its epoch on the evaluation side. An instrument is spent the "
            "moment it trains and picking on it is a partial spend, so the selection slice "
            "here is carved out of the training side instead"
        ),
        "selection": (
            "the same objective — average precision at the first cutpoint — over that "
            "training-side slice rather than over 670 held-out instrument rows"
        ),
        "src_dims": (
            "640x360 rather than 512x288. The head's own input is unchanged at 384x224; what "
            "moved is how much resampling happens before it"
        ),
        "black_thresh": (
            "dropped rather than carried. It was a crop-admission gate from an earlier "
            "corpus and nothing in the incumbent's own location-level path reads it; a "
            "carried constant that changes nothing is history, not a recipe"
        ),
    },
}


def head_dir(name: str = "location", run: str | None = None) -> Path:
    """A head's home: tracked metadata, with the weights beside it, untracked.

    `run` names one training run under it. The bar, the yardstick and the verdict
    belong to the *head* and stay at the root; a checkpoint, its config, its
    metrics and its scores belong to one run and go in a directory of their own.
    That is what lets a seed band exist at all — three runs of one recipe, judged
    against one bar that none of them may rewrite.
    """
    directory = repo_root() / "models" / name
    return directory if run is None else directory / run


def checkpoint_path(name: str = "location", which: str = "best", run: str | None = None) -> Path:
    return head_dir(name, run) / f"head_{which}.pt"


def config_path(name: str = "location", run: str | None = None) -> Path:
    return head_dir(name, run) / "config.json"


def metrics_path(name: str = "location", run: str | None = None) -> Path:
    return head_dir(name, run) / "metrics.json"


def say(*parts) -> None:
    """The default progress log: printed, and **flushed**.

    Flushed because a training run is redirected to a file more often than it is
    watched in a terminal, and Python buffers a redirected stdout by the block. A
    forty-minute run whose progress only appears when it finishes is a run nobody
    can tell from a hung one.
    """
    print(*parts, flush=True)


def shown(value) -> str:
    """A number for the log, or `n/a` where a cutpoint had nothing to measure.

    Spelled out rather than printed as a zero: a selection slice with no
    release-worthy location in it has not measured a bad head.
    """
    return "n/a" if value is None else f"{value:.4f}"


def claim(directory: Path) -> Path:
    """Take the run directory, or refuse because something else already has it.

    Two trainers in one directory do not collide loudly — they interleave their
    logs, take turns overwriting one checkpoint, and produce a run whose numbers
    belong to neither. On Windows the first symptom is a permission error on the
    resume write, tens of minutes in, and by then the log reads like one run
    behaving strangely rather than two behaving normally.

    Written once and used by every trainer here, because a second copy of this
    would be a second answer to whether a directory is free.
    """
    import os

    lock = directory / "training.lock"
    try:
        handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise RuntimeError(
            f"{lock} exists, so another run already has {directory.name}. Two trainers in "
            f"one directory take turns overwriting one checkpoint and produce a run whose "
            f"numbers belong to neither. If nothing is running, delete it."
        ) from None
    with os.fdopen(handle, "w", encoding="utf-8") as writer:
        writer.write(str(os.getpid()))
    return lock


def device_of(requested: str = "auto") -> str:
    import torch

    if requested != "auto":
        return requested
    return "cuda" if torch.cuda.is_available() else "cpu"


def set_seed(seed: int) -> None:
    import numpy
    import torch

    random.seed(seed)
    numpy.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def population(name: str = "location", regimes: tuple = ()) -> tuple[list, dict]:
    """The locations, joined to their tiles, with the selection slice assigned.

    `regimes` names the *other* geometries to join alongside the canonical one.
    Each is read from its own manifest and each has to cover the whole
    population: a mix is only comparable row by row if every regime holds every
    row, and `dataset.join` refuses rather than quietly training on the overlap.
    """
    rows = tile_module.read_locations()
    grouped = tile_module.tiles_by_location(tile_module.read_manifest())
    others = {}
    for regime in regimes:
        if regime == tile_module.CANONICAL_REGIME:
            continue
        others[regime.tag] = tile_module.tiles_by_location(tile_module.read_manifest(regime=regime))
    locations = dataset.join(rows, grouped, others)
    partial = [
        identifier
        for source in (grouped, *others.values())
        for identifier, tiles in source.items()
        if any(t.get("partial") for t in tiles)
    ]
    if partial:
        raise ValueError(
            f"{len(partial)} locations were written by a bounded run and are stamped partial. "
            "A rehearsal's tiles are real files and would train a real head on a prefix of "
            "the corpus; finish the build first."
        )
    del name
    return locations, dataset.assign_selection(locations)


def assert_the_pin_holds(locations: list) -> dict:
    """Refuse to train unless every pinned location is on the evaluation side.

    Asserted at the location coordinate, which is the only place it means
    anything: a pinned place re-rendered under a fresh id, at a different size,
    by a batch nobody remembers is still that place.
    """
    keys = pins.pinned()
    by_id = {tile_module.location_id(key): key for key in keys}
    sides = {}
    for location in locations:
        key = by_id.get(location.location_id)
        if key is not None:
            sides[key] = pins.EVAL if location.side == pins.EVAL else pins.TRAIN
    report = pins.assert_eval(sides, keys, where="the location head's trainer")
    report["resolved_in_the_build"] = len(sides)
    if len(sides) != len(keys):
        raise pins.EvalPinViolation(
            f"the build covers {len(sides)} of {len(keys)} pinned locations. A pinned location "
            "the trainer cannot find is a pin it cannot enforce, and the two are indistinguishable "
            "from the training side."
        )
    return report


def train(
    name: str = "location",
    device: str = "auto",
    epochs: int | None = None,
    seed: int | None = None,
    run: str | None = None,
    regimes: tuple | None = None,
    selection: str | None = None,
    log=say,
) -> dict:
    """Train one head and write its checkpoints, its config and its metrics.

    `regimes` is the geometries the tiles are drawn at, canonical first; more
    than one makes an epoch that many passes long and hands the head no way to
    tell them apart. `selection` names which objective chooses the epoch — see
    [`SELECTION_OBJECTIVES`].
    """
    import numpy
    import torch
    from torch.utils.data import DataLoader

    recipe = dict(RECIPE)
    if epochs is not None:
        recipe["epochs"] = int(epochs)
    if seed is not None:
        recipe["seed"] = int(seed)
    drawn = tuple(regimes) if regimes else (tile_module.CANONICAL_REGIME,)
    if drawn[0] != tile_module.CANONICAL_REGIME:
        raise ValueError(
            f"the canonical regime has to come first, not {drawn[0]}. It is the one the "
            "selection slice, the deploy view and every score file are read at, and a list "
            "that starts elsewhere would silently move all three."
        )
    tags = tuple(regime.tag for regime in drawn)
    recipe["regimes"] = [f"{r.tile[0]}x{r.tile[1]}ss{r.supersample}" for r in drawn]
    chosen_by = selection or recipe["selection_objective"]
    if chosen_by not in SELECTION_OBJECTIVES:
        raise ValueError(f"{chosen_by!r} is not an objective an epoch is chosen on here")
    recipe["selection_objective"] = chosen_by
    recipe["selection"] = SELECTION_OBJECTIVES[chosen_by]
    classes = int(recipe["classes"])

    where = device_of(device)
    set_seed(int(recipe["seed"]))
    locations, selection_record = population(name, drawn)
    pin_report = assert_the_pin_holds(locations)
    by_side = dataset.sides(locations)
    training, choosing, holdout = (
        by_side[pins.TRAIN],
        by_side[dataset.SELECTION],
        by_side[pins.EVAL],
    )
    if not choosing:
        raise ValueError("the selection slice is empty; there is nothing to choose an epoch on")

    log(f"device {where}  torch {torch.__version__}  seed {recipe['seed']}")
    log(f"regimes {recipe['regimes']}  selection {chosen_by}")
    log(
        f"locations {len(locations)}: train {len(training)} {dataset.histogram(training)}, "
        f"selection {len(choosing)} {dataset.histogram(choosing)}, "
        f"eval {len(holdout)} {dataset.histogram(holdout)}"
    )
    log(f"pin: {pin_report}")
    log(f"positives per cutpoint (train): {dataset.positives_at_cutpoints(training, classes)}")

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

    train_transform = head.Transform(
        data_config["mean"], data_config["std"], data_config["interpolation"], train=True
    )
    deploy_transform = head.Transform(
        data_config["mean"], data_config["std"], data_config["interpolation"], train=False
    )
    examples = dataset.training_set(training, train_transform, seed=recipe["seed"], regimes=tags)
    draw, mass = dataset.sampler(training, beta=recipe["beta_biased"], regimes=len(tags))
    log(f"sampled mass {json.dumps(mass['sampled_mass'])}")
    loader = DataLoader(
        examples,
        batch_size=recipe["batch_size"],
        sampler=draw,
        num_workers=recipe["workers"],
        pin_memory=(where == "cuda"),
        persistent_workers=False,
        drop_last=False,
    )

    # Selection reads the canonical regime and only it: the epoch is chosen on
    # the population and the geometry the incumbent chose its own on, so that
    # selection is a controlled variable rather than a second difference. The
    # other regimes are read too and written into the history — reported, never
    # minimized over.
    choosing_paths = {tag: [location.canonical(tag) for location in choosing] for tag in tags}
    choosing_labels = numpy.array([location.score for location in choosing])

    directory = head_dir(name, run)
    directory.mkdir(parents=True, exist_ok=True)
    resume = directory / "resume.pt"

    # Negative infinity rather than -1: the objective is maximized whichever way
    # round it is oriented, and a negated cross-entropy starts well below -1.
    best_metric, best_state, best_epoch, history = float("-inf"), None, -1, []
    start = 0
    if resume.is_file():
        # Onto the CPU, not onto the training device. A snapshot holds two kinds
        # of tensor: weights, which `load_state_dict` places wherever they have
        # to go, and **random-number state**, which is a CPU byte tensor and is
        # rejected outright if it arrives on the GPU. Mapping the whole file at
        # the device therefore loads fine and then fails at `set_rng_state` —
        # which only ever happens on a run that was killed, so it went unseen
        # until one was.
        saved = torch.load(resume, map_location="cpu", weights_only=False)
        if saved.get("selection_objective", chosen_by) != chosen_by:
            raise ValueError(
                f"{resume} was written by a run selecting on "
                f"{saved.get('selection_objective')!r} and this one selects on {chosen_by!r}. "
                "The best-so-far in it is on the other scale; delete it or match it."
            )
        model.load_state_dict(saved["model"])
        optimizer.load_state_dict(saved["optimizer"])
        schedule.load_state_dict(saved["schedule"])
        best_metric, best_epoch = saved["best_metric"], saved["best_epoch"]
        best_state, history = saved["best_state"], saved["history"]
        start = saved["epoch"] + 1
        torch.set_rng_state(saved["torch_rng"].cpu().to(torch.uint8))
        if where == "cuda" and saved.get("cuda_rng") is not None:
            torch.cuda.set_rng_state_all(
                [state.cpu().to(torch.uint8) for state in saved["cuda_rng"]]
            )
        numpy.random.set_state(saved["numpy_rng"])
        log(f"resumed at epoch {start} (best {best_metric:.4f} at epoch {best_epoch})")

    began = time.time()
    for epoch in range(start, recipe["epochs"]):
        examples.set_epoch(epoch)
        model.train()
        clock, running, seen = time.time(), 0.0, 0
        for pictures, labels, _ in loader:
            pictures = pictures.to(where, non_blocking=True)
            labels = labels.to(where, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            logits = model(pictures)
            loss = head.loss_of(logits, labels, num_classes=classes)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), recipe["grad_clip"])
            optimizer.step()
            running += loss.item() * pictures.size(0)
            seen += pictures.size(0)
        schedule.step()

        if any(not torch.isfinite(parameter).all() for parameter in model.parameters()):
            raise RuntimeError(f"the head went non-finite at epoch {epoch}")

        probabilities = score(model, choosing_paths[""], deploy_transform, where, classes, recipe)
        precision = metrics.average_precision(
            (choosing_labels >= 2).astype(int), probabilities[:, 0]
        )
        entropy = metrics.cutpoint_cross_entropy(choosing_labels, probabilities, classes)
        record = {
            "epoch": epoch,
            "loss": running / max(seen, 1),
            "seconds": round(time.time() - clock, 1),
            "selection_ap_ge2": precision,
            "selection_cutpoint_cross_entropy": entropy,
        }
        for index in range(classes - 1):
            label = head.cutpoint_label(index)
            record[f"selection_auc_{label}"] = metrics.auc(
                (choosing_labels >= index + 2).astype(int), probabilities[:, index]
            )
        # Reported, not selected on. A per-regime read of the same slice says
        # whether the mix is landing; the epoch is still chosen at the canonical
        # regime, and nothing here is a cross-regime consistency statistic.
        for tag in tags[1:]:
            elsewhere = score(model, choosing_paths[tag], deploy_transform, where, classes, recipe)
            record[f"selection_cutpoint_cross_entropy{tag}"] = metrics.cutpoint_cross_entropy(
                choosing_labels, elsewhere, classes
            )
        history.append(record)
        log(
            f"epoch {epoch:2d}  loss {record['loss']:.4f}  "
            f"AP>=2 {shown(precision)}  xent {shown(entropy)}  "
            + "  ".join(
                f"AUC>={index + 2} {shown(record[f'selection_auc_{head.cutpoint_label(index)}'])}"
                for index in range(classes - 1)
            )
            + f"  ({record['seconds']}s)"
        )

        # One sign, so "better" is a comparison against the best so far however
        # the objective is oriented — the proper scoring rule is minimized and
        # the rank statistic is maximized.
        objective = precision if chosen_by == "ap_ge2" else (None if entropy is None else -entropy)
        if objective is not None and objective > best_metric:
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
                "selection_objective": chosen_by,
                "history": history,
                "torch_rng": torch.get_rng_state(),
                "cuda_rng": torch.cuda.get_rng_state_all() if where == "cuda" else None,
                "numpy_rng": numpy.random.get_state(),
            },
            temporary,
        )
        temporary.replace(resume)

    last_state = {k: v.detach().cpu() for k, v in model.state_dict().items()}
    if best_state is None:
        best_state = last_state

    config = {
        "schema": SCHEMA,
        "head": name,
        "run": run,
        **recipe,
        "mean": list(data_config["mean"]),
        "std": list(data_config["std"]),
        "interpolation": data_config["interpolation"],
        "best_epoch": best_epoch,
        "inherited": INHERITANCE,
        "tiles": {
            "seed_tag": tile_module.SEED_TAG,
            "plan_seed": tile_module.PLAN_SEED,
        },
        "selection_slice": selection_record,
        "precision": "fp32",
    }
    torch.save({"state_dict": best_state, "config": config}, checkpoint_path(name, "best", run))
    torch.save({"state_dict": last_state, "config": config}, checkpoint_path(name, "last", run))
    if resume.is_file():
        resume.unlink()

    record = {
        "schema": SCHEMA,
        "head": name,
        "run": run,
        "device": where,
        "wall_seconds": round(time.time() - began, 1),
        "best_epoch": best_epoch,
        "selection_objective": chosen_by,
        "best_selection_objective": best_metric,
        "best_selection_ap_ge2": next(
            (row["selection_ap_ge2"] for row in history if row["epoch"] == best_epoch), None
        ),
        "regimes": recipe["regimes"],
        "locations": {
            "total": len(locations),
            "train": len(training),
            "selection": len(choosing),
            "eval": len(holdout),
        },
        "class_counts": {
            "train": dataset.histogram(training),
            "selection": dataset.histogram(choosing),
            "eval": dataset.histogram(holdout),
        },
        "positives_at_cutpoints": {
            "train": dataset.positives_at_cutpoints(training, classes),
            "eval": dataset.positives_at_cutpoints(holdout, classes),
        },
        "eval_pin": pin_report,
        "selection_slice": selection_record,
        "sampled_mass": mass,
        "history": history,
        "checkpoints": {
            "best": str(checkpoint_path(name, "best", run)),
            "last": str(checkpoint_path(name, "last", run)),
        },
    }
    config_path(name, run).write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    metrics_path(name, run).write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return record


def score(model, paths, transform, where: str, classes: int, recipe: dict):
    """Every picture through the deploy transform, in the order it was given."""
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
    out = numpy.zeros((len(paths), classes - 1), dtype=numpy.float64)
    loader = DataLoader(
        Pictures(),
        batch_size=recipe["batch_size"],
        shuffle=False,
        num_workers=0,
        pin_memory=(where == "cuda"),
    )
    with torch.no_grad():
        for pictures, index in loader:
            logits = model(pictures.to(where, non_blocking=True))
            out[index.numpy()] = logits.float().cpu().numpy()
    return head.probabilities(out)


__all__ = [
    "INHERITANCE",
    "RECIPE",
    "SCHEMA",
    "assert_the_pin_holds",
    "checkpoint_path",
    "claim",
    "config_path",
    "device_of",
    "head_dir",
    "metrics_path",
    "population",
    "say",
    "score",
    "shown",
    "set_seed",
    "train",
]
