"""Training the palette head by distillation, and the record it leaves.

## The recipe is the teacher's; the loss is not

Everything that decides *how* the model learns — the two learning rates, the
decay, sixteen sets to a batch, forty epochs, the seed — is read out of the
teacher's own committed config and carried unchanged. That is
what makes the resulting head comparable to it at all: this repository is already
changing the corpus, the renderer and the colormap library, and a knob that
drifted alongside them would be measured as if it were one of them.

Three things move. Two are forced by what distillation *is*:

* **The objective.** The teacher learned from human tiers, through a
  margin-ranking hinge over cross-tier pairs — the only thing a tier ordering
  can support. The student learns from the teacher's own numbers, which carry
  far more than an ordering, so the loss is the centred squared error over the
  whole score vector ([`palette_head.set_loss`]). Training on pairs instead would
  discard the gaps and keep only their signs.
* **What chooses the epoch.** The teacher picked its checkpoint by maximizing
  pair-direction accuracy — a rank statistic, and the only one available when the
  labels are tiers. Here the target is a vector of real numbers, and a rank
  statistic cannot tell a student that reproduces the teacher's order but
  flattens its gaps from one that reproduces both. So the epoch is chosen on the
  **held-out distillation loss**: the same objective the trainer minimizes, over
  locations the run never trained on. It is minimized only at the teacher's own
  centred scores, so it sees the scale as well as the order.

The third is the teacher's early stop, and it was dropped after being measured
rather than on principle: the objective it would watch here moves by a factor of
four between adjacent epochs of a perfectly healthy run, so a patience of eight
is a coin toss rather than a stopping rule. [`INHERITANCE`] carries the numbers.

The second change is the same one the finished-render judges were forced into,
for the same reason and after a rank statistic there had already selected a
broken checkpoint. It is not a coincidence: a selection rule that cannot see the
quantity the head exists to emit will eventually pick a head that gets that
quantity wrong.

## The unit is a set, and a batch of them goes through the net in halves

A batch is sixteen *sets*, not sixteen pictures, because the loss is defined
inside a set — the mean is removed per set before anything is compared. A
sampler that shuffled candidates across set boundaries would be centring on a
mean that belongs to no location.

Sixteen sets of thirty-two candidates is five hundred and twelve pictures, and
that does not fit in eight gigabytes: measured on this machine, a step of 320
pictures takes 0.25 s and a step of 384 takes 3.05 s, because the allocator
starts fighting for room rather than because the arithmetic grew twelve-fold. So
each batch is put through the net in [`RECIPE`]`["microbatch_sets"]`-set pieces
with the gradients accumulated. The loss is a mean over sets, so weighting each
piece by its share of the batch reproduces the whole batch's gradient — measured
at a relative difference of **1.3e-6**, which is float32 summing the same terms in
a different order. The one thing that is not identical is BatchNorm, which now
sees 256 pictures at a time instead of 512 — both far past the point where a batch
statistic is noisy, and it is declared rather than assumed away.

There is no class balance and no place weight here, and their absence is
structural rather than an omission: every set is one location and holds the same
number of candidates, so the population is already balanced over the only unit
that exists.

## The loss carries an optional listwise term, and it was a pre-declared arm

The first pass's miss pattern was the teacher's *second* favourite winning, which
is the one thing a per-set-centred regression is least sharp about: it spends
thirty-one of a set's thirty-two squared errors on candidates nobody will colour
with. [`palette_head.listwise_loss`] reads the set as a distribution instead. It
is off unless asked for, its temperature is read off the corpus rather than
chosen, and whether it is on at all was decided by a **held-out** read between two
arms — never by the real sets, which are the instrument.

## Three seeds, and the band is the answer

One run of one recipe is a sample. The head is trained at three seeds and all
three are reported; what ships is the **median** seed by the acceptance read's
own primary statistic. The median rather than the best, because picking the best
of three is the thing pre-registration exists to stop.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from fractal_wallpapers import storage
from fractal_wallpapers.models import palette_corpus, palette_head, train
from fractal_wallpapers.paths import tracked_name

#: The schema every record here carries.
SCHEMA = 1

#: What the head trains under. Every value but the loss and the selection rule is
#: one the teacher trained under, read out of the config embedded in its
#: checkpoint.
RECIPE = {
    "backbone": palette_head.BACKBONE,
    # ImageNet-1k weights, never the teacher's. A student warm-started from its
    # teacher is not a distillation of it, it is a copy of it with extra steps,
    # and every number afterwards would be a statement about that copy.
    "pretrained": True,
    "geometry": "squash",
    "epochs": 40,
    # No early stop. See [`INHERITANCE`]: the teacher's patience of 8 is the one
    # inherited value that had to go, because the objective it would be watching
    # here moves by a factor of four between adjacent epochs.
    "patience": None,
    "batch_sets": 16,
    # How many sets go through the net at once. Not an optimization knob: the
    # gradient of a batch is assembled from these and is identical either way.
    # Eight sets of 32 candidates is 256 pictures, which is inside the measured
    # cliff at ~320 on an eight-gigabyte card.
    "microbatch_sets": 8,
    # The listwise arm. Zero is the first pass's loss exactly; the weight is 1.0
    # when it is on, which is "equal footing with the regression" and not a
    # searched value. The temperature is null here because it is a fact about the
    # corpus and is read out of its split record — see [`palette_corpus.temperature`].
    "listwise": 0.0,
    "listwise_temperature": None,
    "backbone_lr": 1e-4,
    "head_lr": 1e-3,
    "weight_decay": 0.05,
    "grad_clip": 1.0,
    "seed": 0,
    # Full precision, no autocast: these are differences between two scores that
    # can sit inside fp16's own precision, and the whole loss is those differences.
    "amp": "off",
    "source_dims": [palette_head.SOURCE_WIDTH, palette_head.SOURCE_HEIGHT],
    "target_dims": [palette_head.TARGET_WIDTH, palette_head.TARGET_HEIGHT],
    "augmentation": "geometric only — both flips. No colour: the colour is the question",
    "loss": "centred mean squared error against the teacher's score vector, per set",
    "LISTWISE_ARM": (
        "declared before training and decided on the HELD-OUT top-pick agreement at seed 0, "
        "never on the real sets. Both arms' numbers are recorded either way"
    ),
    "selection": (
        "min held-out distillation loss — the same objective the trainer minimizes, over "
        "locations the run never saw. A proper scoring rule for a score vector, so it sees "
        "the scale and not only the order"
    ),
}

#: What the recipe inherited from the teacher, and the four things it did not.
INHERITANCE = {
    "source": (
        "the teacher's own config, embedded in its checkpoint and resolved through the "
        "source project's single-source pointer"
    ),
    "identical": [
        "backbone",
        "backbone_lr",
        "batch_sets",
        "epochs",
        "geometry",
        "grad_clip",
        "head_lr",
        "interpolation",
        "mean",
        "pretrained",
        "seed",
        "std",
        "target_dims",
        "weight_decay",
    ],
    "changed": [
        {
            "key": "loss",
            "was": "margin-ranking hinge, margin 1.0, over cross-tier candidate pairs",
            "now": "centred mean squared error over the teacher's whole score vector",
            "why": "FORCED. The teacher's labels were human tiers, which support an ordering "
            "and nothing more. The student's labels are the teacher's own real-valued "
            "scores, and a pairwise hinge would throw away every gap and keep only its sign "
            "— which is most of what a set of candidates says.",
        },
        {
            "key": "selection",
            "was": "max validation pair-direction accuracy",
            "now": "min held-out distillation loss",
            "why": "FORCED, for the reason the finished-render judges were: a rank statistic "
            "is invariant to any monotone rescaling of the scores, so it cannot tell a "
            "student that keeps the teacher's order while flattening its gaps from one that "
            "reproduces both. The distillation loss is a proper scoring rule for the vector "
            "being distilled.",
        },
        {
            "key": "patience",
            "was": "8 epochs without an improvement in the selection objective",
            "now": "none — every run takes all 40 epochs",
            "why": "MEASURED, not assumed. The teacher's objective was a pair-direction "
            "accuracy over 200 validation queries, which moves smoothly; this one is a "
            "squared error over 120 held-out sets and it moves by a FACTOR OF FOUR between "
            "adjacent epochs of a healthy run — seed 0 read 1.52, 1.52, 2.63, 1.76 across "
            "epochs 30 to 33. A patience of 8 on a signal that noisy is not an early stop, "
            "it is a coin toss: at the first attempt it cut seed 2 off at epoch 12 on a "
            "lucky epoch-4 reading of 2.82, while the two seeds that survived reached 1.52. "
            "The epoch is chosen on the held-out loss either way, so patience was only ever "
            "saving time, and a full run of this head is three minutes.",
        },
        {
            "key": "batch delivery",
            "was": "one forward and backward pass over the whole batch",
            "now": "the batch in microbatch_sets-set pieces with the gradients accumulated",
            "why": "MECHANICAL, and the gradient is unchanged. Sixteen sets of 32 candidates "
            "is 512 pictures and this card holds 8 GB: a measured step of 320 pictures takes "
            "0.25 s and one of 384 takes 3.05 s. The loss is a mean over sets, so a piece "
            "weighted by its share of the batch contributes exactly its share of the "
            "gradient. The one difference is that BatchNorm sees 256 pictures per update "
            "instead of 512.",
        },
        {
            "key": "split",
            "was": "location-disjoint 80/20 over the query corpus, stratified by query type",
            "now": "a seeded 80/20 over the corpus's own locations, shipped as data",
            "why": "the corpora are different objects. There is no query type here — every "
            "set is a uniform pool draw at one place — so there is nothing to stratify on, "
            "and location-disjointness is the property that carries across.",
        },
    ],
}


class TrainingError(RuntimeError):
    """A head that cannot be trained on what is here."""


def head_dir(run: str | None = None) -> Path:
    return train.head_dir("palette", run)


def checkpoint_path(which: str = "best", run: str | None = None) -> Path:
    return head_dir(run) / f"{which}.pt"


def config_path(run: str | None = None) -> Path:
    return head_dir(run) / "config.json"


def metrics_path(run: str | None = None) -> Path:
    return head_dir(run) / "metrics.json"


class Sets:
    """One side of the corpus, decoded once and mapped: pictures, scores, names.

    The whole side is decoded to a file of `uint8` bytes and memory-mapped back —
    51,200 candidates at 224×224 is 7.7 GB — because decoding a JPEG costs far
    more than the forward pass through this backbone, and a loop that decoded per
    epoch would spend a forty-epoch run inside `libjpeg`. A *file* rather than an
    allocation because this machine's commit charge already exceeds its physical
    memory: an anonymous 7.7 GB would be paged to the swap file and read back
    from an SSD anyway, so it is written to an SSD deliberately instead, where the
    pages are clean and the next run reuses them.

    It also means no loader workers at all, which on Windows is one fewer way to
    be wrong: a worker there is spawned rather than forked, so everything it
    touches has to be picklable and importable by name.
    """

    def __init__(self, sets: list[dict], cache=None) -> None:
        import torch

        self.sets = sets
        self.width = len(sets[0]["candidates"])
        self.names = [entry["set"] for entry in sets]
        self.pictures = palette_head.decoded(
            [palette_corpus.crop_of(row) for entry in sets for row in entry["rows"]],
            cache=cache,
        )
        self.scores = torch.tensor([entry["scores"] for entry in sets], dtype=torch.float32)

    def __len__(self) -> int:
        return len(self.sets)

    def batch(self, indices, where: str, epoch: int | None = None):
        """One batch of whole sets: `[B, K, 3, H, W]` normalized, and `[B, K]` scores.

        `epoch` turns the augmentation on, and it is drawn **per set**: flipping
        the candidates of one location independently would make the geometry an
        axis the head could read the palette off. Seeded on the set's own name and
        the epoch, so a run reproduces and a set still gets a fresh flip each pass.
        """
        import random

        import numpy
        import torch

        offsets = numpy.arange(self.width)
        flat = (numpy.asarray(indices).reshape(-1, 1) * self.width + offsets).reshape(-1)
        # Indexed in numpy, which turns the mapped pages into one owned copy of
        # exactly this batch — the tensor never holds a view of the whole file.
        taken = torch.from_numpy(numpy.ascontiguousarray(self.pictures[flat]))
        pictures = palette_head.normalize(taken.to(where, non_blocking=True))
        pictures = pictures.view(len(indices), self.width, *pictures.shape[1:])
        if epoch is not None:
            for position, index in enumerate(indices):
                draw = random.Random(f"{self.names[int(index)]}:{epoch}")
                if draw.random() < 0.5:
                    pictures[position] = torch.flip(pictures[position], dims=(-1,))
                if draw.random() < 0.5:
                    pictures[position] = torch.flip(pictures[position], dims=(-2,))
        return pictures, self.scores[torch.as_tensor(indices)].to(where, non_blocking=True)


def population() -> tuple[list[dict], list[dict]]:
    """The corpus, folded into sets and split into the two sides."""
    sets = palette_corpus.grouped()
    if not sets:
        raise TrainingError("the distillation corpus is empty — build and label it first")
    training = [entry for entry in sets if entry["side"] == "train"]
    holdout = [entry for entry in sets if entry["side"] == "holdout"]
    if not holdout:
        raise TrainingError("the held-out side is empty; there is nothing to choose an epoch on")
    widths = {len(entry["candidates"]) for entry in sets}
    if len(widths) != 1:
        raise TrainingError(
            f"the corpus holds sets of {sorted(widths)} candidates. The loss centres inside a "
            f"set and a batch stacks them, so a ragged corpus would have to be padded — and a "
            f"padded candidate is a picture the teacher never scored."
        )
    return training, holdout


def accumulate(
    model,
    examples: Sets,
    indices: list[int],
    where: str,
    recipe: dict,
    epoch: int | None,
    piece_sets: int,
) -> float:
    """One batch's gradient, assembled from pieces that fit in the card.

    The whole batch is `indices`; it goes through the net `piece_sets` sets at a
    time and each piece's loss is scaled by its share of the batch before
    `backward`. Because the objective is a **mean over sets**, those scaled pieces
    sum to the gradient a single pass over the whole batch would have produced —
    the same vector to within float32's own last bits, which is what
    `tests/test_palette_train.py` measures rather than assumes. The one thing that
    genuinely differs is BatchNorm, which sees a piece's pictures rather than the
    batch's.

    Returns the batch's loss, assembled the same way.
    """
    total = 0.0
    for cut in range(0, len(indices), piece_sets):
        piece = indices[cut : cut + piece_sets]
        weight = len(piece) / len(indices)
        pictures, scores = examples.batch(piece, where, epoch=epoch)
        flat = pictures.view(-1, *pictures.shape[2:])
        predicted = model(flat).view(len(piece), examples.width)
        loss = palette_head.set_loss(
            predicted,
            scores,
            listwise=recipe["listwise"],
            temperature=recipe["listwise_temperature"] or 1.0,
        )
        (loss * weight).backward()
        total += loss.item() * weight
    return total


def evaluate(model, held: Sets, where: str, batch_size: int) -> dict:
    """The held-out read: the distillation loss, and the two things it is for.

    The top-pick agreement is broken out by set kind, because the corpus now holds
    two populations. The **hard** figure is the one that resembles what a
    production colorize really asks; the uniform one says whether teaching the
    fine question cost the coarse one.
    """
    import numpy
    import torch

    from fractal_wallpapers.models import metrics

    model.eval()
    rows = []
    with torch.no_grad():
        for start in range(0, len(held), batch_size):
            indices = list(range(start, min(start + batch_size, len(held))))
            pictures, _ = held.batch(indices, where)
            flat = pictures.view(-1, *pictures.shape[2:])
            rows.append(model(flat).view(len(indices), held.width).float().cpu().numpy())
    ours = numpy.concatenate(rows).astype(numpy.float64)
    theirs = held.scores.numpy().astype(numpy.float64)
    sets = held.sets
    centred = (ours - ours.mean(axis=1, keepdims=True)) - (
        theirs - theirs.mean(axis=1, keepdims=True)
    )
    agreements = [
        int(palette_head.top_pick(ours[index]) == palette_head.top_pick(theirs[index]))
        for index in range(len(sets))
    ]
    correlations = [
        value
        for index in range(len(sets))
        if (value := metrics.spearman(ours[index], theirs[index])) is not None
    ]
    by_kind = {}
    for kind in ("hard", "uniform"):
        picked = [index for index, entry in enumerate(sets) if entry.get("kind") == kind]
        if picked:
            by_kind[kind] = float(numpy.mean([agreements[index] for index in picked]))
    return {
        "loss": float((centred * centred).mean(axis=1).mean()),
        "top_pick_agreement": float(numpy.mean(agreements)),
        "top_pick_by_kind": by_kind,
        "median_spearman": float(numpy.median(correlations)) if correlations else None,
        "sets": len(sets),
    }


def run(
    device: str = "auto",
    epochs: int | None = None,
    seed: int | None = None,
    run_name: str | None = None,
    listwise: float | None = None,
    log=train.say,
) -> dict:
    """Train one palette head, and write its checkpoints and records.

    Refuses before it imports torch if the distillation corpus is archived — see
    [`fractal_wallpapers.storage.require_hot`] for why a slow read is worth a
    refusal rather than a warning.
    """
    import torch

    storage.require_hot(palette_corpus.cache_dir(), what="training the palette head")
    recipe = dict(RECIPE)
    if epochs is not None:
        recipe["epochs"] = int(epochs)
    if seed is not None:
        recipe["seed"] = int(seed)
    if listwise is not None:
        recipe["listwise"] = float(listwise)
    if recipe["listwise"]:
        recipe["listwise_temperature"] = _temperature()
        if recipe["listwise_temperature"] is None:
            raise TrainingError(
                "the listwise arm reads its temperature off the corpus's split record and "
                "that record does not carry one — relabel the corpus before training with it."
            )

    where = train.device_of(device)
    train.set_seed(int(recipe["seed"]))
    training, holdout = population()
    log(f"device {where}  torch {torch.__version__}  seed {recipe['seed']}  head palette")
    log(
        f"sets {len(training) + len(holdout)}: train {len(training)}, held out {len(holdout)}; "
        f"{len(training[0]['candidates'])} candidates each"
    )

    model = palette_head.build(pretrained=recipe["pretrained"]).to(where)
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

    clock = time.time()
    cache = palette_corpus.cache_dir() / "decoded"
    examples, held = Sets(training, cache), Sets(holdout, cache)
    log(f"decoded {len(examples) + len(held)} sets in {time.time() - clock:.1f}s")

    directory = head_dir(run_name)
    directory.mkdir(parents=True, exist_ok=True)
    lock = train.claim(directory)
    try:
        best_metric, best_state, best_epoch, history = float("inf"), None, -1, []
        best_read: dict = {}
        began = time.time()
        stale = 0
        shuffler = torch.Generator().manual_seed(int(recipe["seed"]))
        piece_sets = recipe["microbatch_sets"]
        for epoch in range(recipe["epochs"]):
            model.train()
            clock, running, seen = time.time(), 0.0, 0
            order = torch.randperm(len(examples), generator=shuffler).tolist()
            for start in range(0, len(order), recipe["batch_sets"]):
                indices = order[start : start + recipe["batch_sets"]]
                optimizer.zero_grad(set_to_none=True)
                batch_loss = accumulate(model, examples, indices, where, recipe, epoch, piece_sets)
                torch.nn.utils.clip_grad_norm_(model.parameters(), recipe["grad_clip"])
                optimizer.step()
                running += batch_loss * len(indices)
                seen += len(indices)
            if any(not torch.isfinite(parameter).all() for parameter in model.parameters()):
                raise TrainingError(f"the head went non-finite at epoch {epoch}")

            read = evaluate(model, held, where, piece_sets)
            record = {
                "epoch": epoch,
                "loss": running / max(seen, 1),
                "seconds": round(time.time() - clock, 1),
                "holdout_loss": read["loss"],
                "holdout_top_pick_agreement": read["top_pick_agreement"],
                "holdout_top_pick_by_kind": read["top_pick_by_kind"],
                "holdout_median_spearman": read["median_spearman"],
            }
            history.append(record)
            log(
                f"epoch {epoch:2d}  loss {record['loss']:.4f}  "
                f"held out {read['loss']:.4f}  "
                f"top-1 {read['top_pick_agreement']:.3f}  "
                f"hard {train.shown(read['top_pick_by_kind'].get('hard'))}  "
                f"rho {train.shown(read['median_spearman'])}  ({record['seconds']}s)"
            )

            if read["loss"] < best_metric:
                best_metric, best_epoch, stale = read["loss"], epoch, 0
                best_read = read
                best_state = {
                    key: value.detach().cpu().clone() for key, value in model.state_dict().items()
                }
            elif recipe["patience"] is not None:
                stale += 1
                if stale >= recipe["patience"]:
                    log(f"early stop: no held-out improvement for {recipe['patience']} epochs")
                    break
    finally:
        lock.unlink(missing_ok=True)

    last_state = {key: value.detach().cpu() for key, value in model.state_dict().items()}
    if best_state is None:
        best_state = last_state

    config = {
        "schema": SCHEMA,
        "head": "palette",
        "run": run_name,
        **recipe,
        "mean": list(palette_head.MEAN),
        "std": list(palette_head.STD),
        "interpolation": palette_head.INTERPOLATION,
        "best_epoch": best_epoch,
        "inherited": INHERITANCE,
        "teacher": _teacher_note(),
        "corpus": {
            "batch": palette_corpus.BATCH,
            "seed": palette_corpus.SEED,
            "sets": len(training) + len(holdout),
            "candidates_per_set": len(training[0]["candidates"]),
            "hard_sets": sum(1 for entry in training + holdout if entry.get("kind") == "hard"),
        },
        "precision": "fp32",
    }
    torch.save({"state_dict": best_state, "config": config}, checkpoint_path("best", run_name))
    torch.save({"state_dict": last_state, "config": config}, checkpoint_path("last", run_name))

    record = {
        "schema": SCHEMA,
        "head": "palette",
        "run": run_name,
        "device": where,
        "wall_seconds": round(time.time() - began, 1),
        "best_epoch": best_epoch,
        "best_holdout_loss": best_metric,
        "selection_metric": "held-out distillation loss (minimized)",
        "listwise": recipe["listwise"],
        "listwise_temperature": recipe["listwise_temperature"],
        # The arm statistic, at the epoch the selection rule chose. This is what
        # decides whether the listwise term ships, and it is a held-out number.
        "arm": {
            "holdout_top_pick_agreement": best_read.get("top_pick_agreement"),
            "holdout_top_pick_by_kind": best_read.get("top_pick_by_kind"),
            "holdout_median_spearman": best_read.get("median_spearman"),
        },
        "sets": {"train": len(training), "holdout": len(holdout)},
        "history": history,
        # Tracked-record spelling; see [`train`] for why a checkpoint path in
        # a tracked record never carries a drive letter.
        "checkpoints": {
            "best": tracked_name(checkpoint_path("best", run_name)),
            "last": tracked_name(checkpoint_path("last", run_name)),
        },
    }
    config_path(run_name).write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    metrics_path(run_name).write_text(
        json.dumps(record, indent=2, default=str) + "\n", encoding="utf-8", newline="\n"
    )
    return record


def _temperature() -> float | None:
    """The listwise term's scale, read off the corpus rather than chosen here."""
    document = json.loads(palette_corpus.split_path().read_text(encoding="utf-8"))
    return document.get("listwise_temperature")


def _teacher_note() -> dict:
    """Which teacher taught this head, read off the corpus rather than the source.

    The corpus is what the head learned from, and its split record carries the
    teacher's identity as it was at labeling time. Re-resolving the pointer here
    would ask a different question — *who is live now* — and could answer it
    differently.
    """
    document = json.loads(palette_corpus.split_path().read_text(encoding="utf-8"))
    return document.get("teacher", {})


__all__ = [
    "INHERITANCE",
    "RECIPE",
    "SCHEMA",
    "Sets",
    "TrainingError",
    "accumulate",
    "checkpoint_path",
    "config_path",
    "evaluate",
    "head_dir",
    "metrics_path",
    "population",
    "run",
]
