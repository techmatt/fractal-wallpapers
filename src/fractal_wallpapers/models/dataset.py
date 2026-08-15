"""Locations → tensors: which picture an example is, and how often it is drawn.

## The training unit is a location, not a tile

A location owns thirty-two tiles and one label. If each tile were an example, a
location would appear thirty-two times an epoch and the head would spend most of
its capacity learning which colormap is which. So one epoch is one pass over
*locations*, and each location draws **one** of its tiles — a different one each
epoch, reproducibly. Over forty epochs a location is seen forty times through
forty different colorings and framings, which is what the fan-out was built for.

## The sampler is three weights multiplied, in that order

```text
weight  =  w_class(label)  ×  w_group(location)  ×  w_source(location)
```

* `w_group = 1 / group size` equalizes neighbourhoods. Nine hundred frames of one
  hot spot would otherwise outvote nine hundred separate places.
* `w_source = β` for a location drawn with a model's score in the loop, 1
  otherwise. Those locations are worth having and are not worth as much: the
  population they came from was already filtered by an opinion.
* `w_class = 1 / √count` softens the class imbalance. Square root rather than
  inverse frequency, because full inversion makes the six hundred class-4
  locations as loud as the five thousand class-1 ones and the head starts calling
  everything releasable.

**The order is the point.** `w_class` is a pure per-class scalar applied last, so
it scales every location of a class alike and cannot change the biased/unbiased
ratio *inside* a class — the source down-weight cannot be laundered back out
through the class balance. The realized mass per cell is reported, so that claim
is a number rather than an argument.

## The split has three sides, and only two of them are the split

`train` and `eval` come from the label store's shipped pin and are not decided
here. The **selection** slice is carved out of the training side by a seeded draw
over groups, and it exists because something has to choose which epoch to keep.
Choosing on the evaluation side is how an instrument is spent quietly: the head
never trains on it, every number read off it afterwards is still inflated, and
nothing goes red. So the training side pays for model selection and the
evaluation side pays for nothing.
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, field

from fractal_wallpapers.labeling import pins

#: What a location drawn with a model's score in its selection is worth against
#: one drawn blind.
BETA_BIASED = 0.4

#: Share of the training side held out to choose the epoch on.
SELECTION_SHARE = 0.10

#: The seed the selection slice is drawn under.
SELECTION_SEED = 0

#: The third side, named so it cannot be confused with the shipped split.
SELECTION = "selection"


@dataclass
class Location:
    """One training unit: a place, its verdict, and the pictures of it."""

    location_id: int
    score: int
    side: str
    partition: str
    group: int
    batch: str
    biased: bool
    #: Tile manifest rows, in slot order. Slot 0 is the canonical view.
    tiles: list = field(default_factory=list)

    def path(self, slot: int) -> str:
        return self.tiles[slot]["path"]

    def canonical(self) -> str:
        """The deploy view: the picture this location is scored through."""
        from fractal_wallpapers.models import tiles as tile_module

        return tile_module.canonical_of(self.tiles)["path"]


def join(locations: list[dict], tiles_by_location: dict[int, list[dict]]) -> list[Location]:
    """Join the trainer's manifest to the tiles that were built for it.

    Refuses a location whose tiles are missing rather than dropping it. A build
    that silently covers a prefix trains a head on a prefix, and the head reports
    the numbers of a whole corpus.
    """
    out = []
    absent = []
    for row in locations:
        identifier = int(row["location_id"])
        tiles = tiles_by_location.get(identifier)
        if not tiles:
            absent.append(identifier)
            continue
        out.append(
            Location(
                location_id=identifier,
                score=int(row["score"]),
                side=row["side"],
                partition=row["partition"],
                group=int(row["group"]),
                batch=row["batch"],
                biased=bool(row["biased"]),
                tiles=tiles,
            )
        )
    if absent:
        raise ValueError(
            f"{len(absent)} of {len(locations)} locations have no tiles, e.g. {absent[:5]}. "
            "Finish the build before training on it — a partial corpus is not a smaller "
            "corpus, it is a different one."
        )
    return out


def assign_selection(
    locations: list[Location],
    share: float = SELECTION_SHARE,
    seed: int = SELECTION_SEED,
) -> dict:
    """Move a seeded draw of training-side groups onto the selection side.

    Whole groups, for the same reason the shipped split is drawn over groups:
    two frames a hair apart are one picture, and a selection slice that shares a
    neighbourhood with the training side is measuring what the head memorized.
    """
    trainable = [location for location in locations if location.side == pins.TRAIN]
    groups = sorted({location.group for location in trainable})
    drawn = list(groups)
    random.Random(seed).shuffle(drawn)

    target = round(share * len(trainable))
    size = Counter(location.group for location in trainable)
    chosen, held = set(), 0
    for group in drawn:
        if held >= target:
            break
        chosen.add(group)
        held += size[group]
    for location in trainable:
        if location.group in chosen:
            location.side = SELECTION
    return {
        "rule": (
            "a seeded draw over TRAINING-side groups, taken whole. The evaluation side is "
            "never a selection population: a head that picks its epoch on an instrument has "
            "spent it, silently"
        ),
        "seed": seed,
        "target_share": share,
        "train_locations": len(trainable),
        "groups": len(groups),
        "selection_groups": len(chosen),
        "selection_locations": held,
        "realized_share": round(held / len(trainable), 4) if trainable else 0.0,
    }


def sides(locations: list[Location]) -> dict[str, list[Location]]:
    """The three sides, each in the order the manifest gave them."""
    out: dict[str, list[Location]] = {pins.TRAIN: [], SELECTION: [], pins.EVAL: []}
    for location in locations:
        out[location.side].append(location)
    return out


def weights(locations: list[Location], beta: float = BETA_BIASED) -> tuple:
    """Per-location sampling weights, and the realized mass they produce."""
    import numpy
    import torch

    group_size = Counter(location.group for location in locations)
    class_count = Counter(location.score for location in locations)
    per_class = {score: 1.0 / numpy.sqrt(count) for score, count in class_count.items()}

    raw = numpy.array(
        [
            per_class[location.score]
            * (1.0 / group_size[location.group])
            * (beta if location.biased else 1.0)
            for location in locations
        ]
    )
    share = raw / raw.sum()

    mass: dict[str, float] = {}
    counted: Counter = Counter()
    for location, portion in zip(locations, share, strict=True):
        cell = f"score{location.score}|{'biased' if location.biased else 'unbiased'}"
        mass[cell] = mass.get(cell, 0.0) + float(portion)
        counted[cell] += 1
    table = {
        "beta": beta,
        "class_balance": "1/sqrt(count)",
        "class_count": {int(k): int(v) for k, v in sorted(class_count.items())},
        "w_class": {int(k): round(float(v), 6) for k, v in sorted(per_class.items())},
        "sampled_mass": {cell: round(mass[cell], 5) for cell in sorted(mass)},
        "locations": {cell: counted[cell] for cell in sorted(counted)},
    }
    return torch.tensor(raw, dtype=torch.double), table


def sampler(locations: list[Location], beta: float = BETA_BIASED) -> tuple:
    """A `WeightedRandomSampler` over the locations, and its mass table."""
    from torch.utils.data import WeightedRandomSampler

    tensor, table = weights(locations, beta)
    return (
        WeightedRandomSampler(tensor, num_samples=len(locations), replacement=True),
        table,
    )


def training_set(locations: list[Location], transform, seed: int = 0):
    """The dataset a training epoch iterates: one tile per location, redrawn."""
    from torch.utils.data import Dataset

    class TileDraw(Dataset):
        def __init__(self):
            self.epoch = 0

        def set_epoch(self, epoch: int) -> None:
            self.epoch = int(epoch)

        def __len__(self) -> int:
            return len(locations)

        def __getitem__(self, index: int):
            from PIL import Image

            location = locations[index]
            # Reproducible per (seed, epoch, index) and varying with the epoch,
            # so the thirty-two tiles are actually exercised rather than one of
            # them being memorized forty times.
            draw = random.Random(
                (seed * 2_654_435_761 + self.epoch * 1_000_003 + index) & 0xFFFF_FFFF_FFFF
            )
            path = location.path(draw.randrange(len(location.tiles)))
            with Image.open(path) as opened:
                opened.load()
                image = opened.convert("RGB")
            return transform(image, draw), location.score, index

    return TileDraw()


def histogram(locations: list[Location]) -> dict:
    """How many of each score, always all four keys.

    A side with no class-4 location reports a zero rather than omitting the key —
    "none" and "not counted" are different statements and only one of them is a
    fact about the corpus.
    """
    counted = Counter(location.score for location in locations)
    return {str(score): int(counted.get(score, 0)) for score in (1, 2, 3, 4)}


def positives_at_cutpoints(locations: list[Location], classes: int) -> dict:
    """How many locations clear each cutpoint — the population each task trains on."""
    from fractal_wallpapers.models.head import cutpoint_label

    return {
        cutpoint_label(index): sum(1 for location in locations if location.score >= index + 2)
        for index in range(classes - 1)
    }


__all__ = [
    "BETA_BIASED",
    "SELECTION",
    "SELECTION_SEED",
    "SELECTION_SHARE",
    "Location",
    "assign_selection",
    "histogram",
    "join",
    "positives_at_cutpoints",
    "sampler",
    "sides",
    "training_set",
    "weights",
]
