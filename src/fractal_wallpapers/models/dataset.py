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

## A regime is an axis of the example, not a field of the head

A location's tiles exist at more than one **regime** — a tile size and a field
supersample (see [`fractal_wallpapers.models.tiles.Regime`]). The same slot at two
regimes is the same draw of the same place: same palette, same framing, same
reconstruction, same quality, different geometry. So a training example is a
`(location, regime)` pair, and a run told to use three regimes sees every label
row three times an epoch — three tiles, one label, one row.

The head is handed no regime input and no conditioning. That is the whole point:
one score scale across regimes is the deliverable, and a head that could see which
geometry it was looking at would be free to keep a different scale for each.

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
    #: Tile manifest rows at the canonical regime, in slot order. Slot 0 is the
    #: canonical view.
    tiles: list = field(default_factory=list)
    #: The same slots at every other regime this join covered, keyed by the
    #: regime's tag. The canonical regime's tag is the empty string and its rows
    #: are `tiles` above, so a single-regime join leaves this empty.
    regimes: dict = field(default_factory=dict)

    def at(self, regime: str = "") -> list:
        """This location's tiles at one regime, in slot order."""
        return self.tiles if regime == "" else self.regimes[regime]

    def path(self, slot: int, regime: str = "") -> str:
        return self.at(regime)[slot]["path"]

    def canonical(self, regime: str = "") -> str:
        """The deploy view: the picture this location is scored through.

        At a regime other than the canonical one it is the same slot rendered at
        that geometry — the same place, framed and colored the same way, sampled
        differently. That is exactly the pair a cross-regime reading compares.
        """
        from fractal_wallpapers.models import tiles as tile_module

        return tile_module.canonical_of(self.at(regime))["path"]


def join(
    locations: list[dict],
    tiles_by_location: dict[int, list[dict]],
    others: dict[str, dict[int, list[dict]]] | None = None,
) -> list[Location]:
    """Join the trainer's manifest to the tiles that were built for it.

    Refuses a location whose tiles are missing rather than dropping it. A build
    that silently covers a prefix trains a head on a prefix, and the head reports
    the numbers of a whole corpus.

    `others` maps a regime's tag to that regime's grouped manifest, and every
    regime in it has to cover every location the canonical one does — with the
    same number of slots. A regime short of a location is not a smaller corpus
    either: it is a mix whose composition nobody wrote down.
    """
    out = []
    absent = []
    short: dict[str, list[int]] = {}
    for row in locations:
        identifier = int(row["location_id"])
        tiles = tiles_by_location.get(identifier)
        if not tiles:
            absent.append(identifier)
            continue
        elsewhere = {}
        for tag, grouped in (others or {}).items():
            theirs = grouped.get(identifier)
            if not theirs or len(theirs) != len(tiles):
                short.setdefault(tag, []).append(identifier)
                continue
            elsewhere[tag] = theirs
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
                regimes=elsewhere,
            )
        )
    if absent:
        raise ValueError(
            f"{len(absent)} of {len(locations)} locations have no tiles, e.g. {absent[:5]}. "
            "Finish the build before training on it — a partial corpus is not a smaller "
            "corpus, it is a different one."
        )
    if short:
        first = sorted(short)[0]
        raise ValueError(
            f"regime {first!r} covers {len(locations) - len(short[first])} of "
            f"{len(locations)} locations at the canonical regime's slot count, e.g. "
            f"{short[first][:5]}. A regime mix is only comparable row by row if every "
            "regime holds every row."
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


def sampler(locations: list[Location], beta: float = BETA_BIASED, regimes: int = 1) -> tuple:
    """A `WeightedRandomSampler` over the examples, and its mass table.

    With more than one regime the index space is the `(location, regime)` pairs
    [`TileDraw`] indexes — the location's weight repeated once per regime, and an
    epoch that many times longer. Every location is repeated the *same* number of
    times, so the realized mass per class × source cell is unchanged and the
    table below still describes the mix.
    """
    import numpy
    import torch
    from torch.utils.data import WeightedRandomSampler

    tensor, table = weights(locations, beta)
    if regimes > 1:
        tensor = torch.tensor(numpy.tile(tensor.numpy(), regimes), dtype=torch.double)
    table["regimes"] = regimes
    return (
        WeightedRandomSampler(tensor, num_samples=len(locations) * regimes, replacement=True),
        table,
    )


class TileDraw:
    """The dataset a training epoch iterates: one tile per example, redrawn.

    An example is a `(location, regime)` pair, laid out so that index `i` is
    location `i % len(locations)` at regime `i // len(locations)` — the same
    layout [`sampler`] tiles its weights in. With one regime that is the plain
    per-location index it has always been.

    **The slot is drawn per location, not per example**, so a row's three tiles
    are the same draw at three geometries rather than three unrelated pictures.
    The augmentation is drawn per example, because two views of one picture that
    were cropped and flipped identically would be teaching the head that the
    crop is the invariant.

    A module-level class rather than one built inside [`training_set`], and that
    is not a style preference. The loader's workers are separate *processes* on
    Windows — spawned, not forked — so everything they are handed has to survive
    a pickle, and a class defined inside a function cannot be found again by
    name on the other side. The failure is at the first batch, after the whole
    corpus has been joined.
    """

    def __init__(
        self,
        locations: list[Location],
        transform,
        seed: int = 0,
        regimes: tuple[str, ...] = ("",),
    ):
        self.locations = locations
        self.transform = transform
        self.seed = seed
        self.regimes = tuple(regimes)
        self.epoch = 0

    def set_epoch(self, epoch: int) -> None:
        self.epoch = int(epoch)

    def __len__(self) -> int:
        return len(self.locations) * len(self.regimes)

    def __getitem__(self, index: int):
        from PIL import Image

        which = index % len(self.locations)
        regime = self.regimes[index // len(self.locations)]
        location = self.locations[which]
        # Reproducible per (seed, epoch, location) and varying with the epoch, so
        # the thirty-two tiles are actually exercised rather than one of them
        # being memorized forty times — and shared across the regimes, so the
        # example a row contributes at each of them is the same picture.
        slot = random.Random(
            (self.seed * 2_654_435_761 + self.epoch * 1_000_003 + which) & 0xFFFF_FFFF_FFFF
        ).randrange(len(location.tiles))
        draw = random.Random(
            (self.seed * 2_654_435_761 + self.epoch * 1_000_003 + index) & 0xFFFF_FFFF_FFFF
        )
        path = location.path(slot, regime)
        with Image.open(path) as opened:
            opened.load()
            image = opened.convert("RGB")
        return self.transform(image, draw), location.score, which


def training_set(
    locations: list[Location],
    transform,
    seed: int = 0,
    regimes: tuple[str, ...] = ("",),
) -> TileDraw:
    """One epoch's worth of examples: every location once per regime."""
    return TileDraw(locations, transform, seed, regimes)


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
    "TileDraw",
    "assign_selection",
    "histogram",
    "join",
    "positives_at_cutpoints",
    "sampler",
    "sides",
    "training_set",
    "weights",
]
