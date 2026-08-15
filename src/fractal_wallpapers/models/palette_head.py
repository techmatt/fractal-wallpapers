"""The palette head: what it is, what it sees, and what it is trained against.

## One number per picture, and only the differences mean anything

The three judges before this one answer *how good is this*, on a scale a human
cast, so they emit an ordinal ladder. This one answers a different question —
**which of these colorings of this place is the best one** — and the answer is a
choice inside a set. So the model is a single tower that reads one picture and
emits one scalar utility, and the thing that carries meaning is the *difference*
between two of its scores on two candidates for the same location. A constant
added to every score in a set changes nothing anybody reads.

That shape is not a design decision made here. It is the teacher's, and this head
is a distillation of that teacher: same backbone, same input geometry, same
augmentation. What is new is only how it is trained.

## Distilling a vector, not a winner

The teacher is used at colorize time as an argmax over a candidate set, so the
cheapest possible distillation would copy the argmax and throw the rest away.
That would be a much weaker teacher: a set of thirty-two candidates carries
thirty-two numbers, thirty-one of which say how far behind the winner the rest
came, and a student that never sees them cannot learn the *shape* of the
preference — only its peak. It would also be brittle exactly where the teacher is
least certain, because a set whose top two are a hair apart teaches "this one,
absolutely" instead of "these two, nearly equally".

So the loss is over the whole score vector, and it is [`set_loss`]: the mean
squared error between the student's and the teacher's scores **after both are
centred inside their own set**. Centring is what makes it the right target rather
than a harder one — a global offset is not part of what the teacher says, and
asking the student to reproduce one would spend capacity on a number nobody
reads. Everything else survives: the order, the gaps, and how big the gap to the
winner is.

It is also a proper scoring rule for that vector — minimized only at the
teacher's own centred scores, and *not* invariant to a monotone rescaling of
them. That is why it, rather than a rank statistic, chooses the epoch. A rank
statistic cannot tell a student that agrees with the teacher's order but flattens
its gaps from one that reproduces both, and the gaps are half of what is being
distilled.

## The transform is the teacher's, exactly

A distilled student that saw a different picture from its teacher would be
learning the difference between two transforms as well as the function. So the
deploy transform here is the teacher's own, spelled out: a **squash** to 224×224
— the map is not preserved, because the teacher's was not — bicubic, then
ImageNet-1k normalization. Training adds both flips and nothing else. **No colour
augmentation, and here that is not a tuning choice**: the colour *is* the
question, and a brightness jitter is an edit to the thing being scored. The
teacher's own recipe says so, in those words, and it is carried.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

#: The backbone. The teacher's, because a distilled student with a different one
#: would be a different head that happens to have been taught by this one.
BACKBONE = "mobilenetv4_conv_small.e2400_r224_in1k"

#: What the head is handed, in pixels. Square, and the picture is squashed into
#: it rather than cropped or padded: the teacher was trained that way and a
#: student that framed its input differently would not be reading what it read.
TARGET_WIDTH, TARGET_HEIGHT = 224, 224

#: The picture a candidate is judged from: a 640×360 render of the location
#: through one map. The size the production colorize path formed its own
#: descriptor at, and the size this repository's tiles are drawn at.
SOURCE_WIDTH, SOURCE_HEIGHT = 640, 360

#: The normalization the teacher was trained under. ImageNet-1k's, which is also
#: what `timm` resolves for this checkpoint — the two agree, and this is the pair
#: that is authoritative, because it is the pair the teacher saw.
MEAN = (0.485, 0.456, 0.406)
STD = (0.229, 0.224, 0.225)

#: How the picture is resampled on the way in.
INTERPOLATION = "bicubic"


def build(backbone: str = BACKBONE, **kwargs):
    """The backbone with a one-number head on it: a scalar utility per picture."""
    import timm

    return timm.create_model(backbone, num_classes=1, **kwargs)


@dataclass
class Transform:
    """Picture → normalized tensor. `train` decides whether it flips.

    Geometric only. See the module docstring on why colour is not a free axis
    for a head whose whole question is the colour.
    """

    mean: tuple = MEAN
    std: tuple = STD
    interpolation: str = INTERPOLATION
    train: bool = False

    def __call__(self, image, rng: random.Random | None = None):
        from PIL import Image

        if image.mode != "RGB":
            image = image.convert("RGB")
        image = resize(image, self.interpolation)
        if self.train:
            draw = rng or random
            # Both flips, because the set is symmetric about the real axis and a
            # mirrored fractal is a fractal. The teacher's own augmentation, and
            # the whole of it.
            if draw.random() < 0.5:
                image = image.transpose(Image.FLIP_LEFT_RIGHT)
            if draw.random() < 0.5:
                image = image.transpose(Image.FLIP_TOP_BOTTOM)
        return self._normalize(_to_tensor(image))

    def _normalize(self, tensor):
        import torch

        mean = torch.tensor(self.mean).view(3, 1, 1)
        std = torch.tensor(self.std).view(3, 1, 1)
        return (tensor - mean) / std


def resize(image, interpolation: str = INTERPOLATION):
    """The deterministic core: a rendered candidate to the head's input size."""
    from PIL import Image

    filters = {
        "nearest": Image.NEAREST,
        "bilinear": Image.BILINEAR,
        "bicubic": Image.BICUBIC,
        "lanczos": Image.LANCZOS,
    }
    return image.resize((TARGET_WIDTH, TARGET_HEIGHT), filters.get(interpolation, Image.BICUBIC))


def _to_tensor(image):
    import numpy
    import torch

    array = numpy.array(image, dtype=numpy.uint8)
    return torch.from_numpy(array).permute(2, 0, 1).float() / 255.0


def centre(scores):
    """Scores with each set's own mean removed. `scores` is `[sets, candidates]`.

    The one operation that says what a utility means here: a set's scores are
    read against each other and never against another set's, so the offset they
    share is not part of the answer.
    """
    return scores - scores.mean(dim=1, keepdim=True)


def set_loss(student, teacher):
    """THE distillation objective: centred mean squared error, per set.

    Both arguments are `[sets, candidates]`. Averaged over candidates first and
    over sets second, so a set is worth a set however many candidates it holds.
    """
    difference = centre(student.float()) - centre(teacher.float())
    return (difference * difference).mean(dim=1).mean()


def top_pick(scores) -> int:
    """One set's argmax: the candidate this head would colour the location with.

    Takes a single set's scores rather than a rectangle of them, because the
    sets this head is *judged* on are the real ones and they are not all the
    same size — a production candidate set is one palette flavour's members, and
    the flavours hold different numbers of maps.
    """
    import numpy

    return int(numpy.asarray(scores, dtype=numpy.float64).argmax())


def regret(student_scores, teacher_scores) -> float:
    """How much teacher utility one set gives up by taking the student's pick.

    In the teacher's own units: its score for its own best candidate, minus its
    score for the one the student chose. Zero when they agree, and never
    negative. Reported alongside the agreement rate because a disagreement over
    two candidates the teacher rated within a thousandth of each other is not the
    same event as one that costs a point.
    """
    import numpy

    teacher_scores = numpy.asarray(teacher_scores, dtype=numpy.float64)
    return float(teacher_scores.max() - teacher_scores[top_pick(student_scores)])


def spread(scores) -> float:
    """One set's own scale: how far its best candidate is above its worst.

    What a regret is read against. A set whose candidates the teacher rated
    within a hair of each other cannot give up much by picking the wrong one, and
    a regret quoted without it says nothing about whether the pick mattered.
    """
    import numpy

    array = numpy.asarray(scores, dtype=numpy.float64)
    return float(array.max() - array.min())


__all__ = [
    "BACKBONE",
    "INTERPOLATION",
    "MEAN",
    "SOURCE_HEIGHT",
    "SOURCE_WIDTH",
    "STD",
    "TARGET_HEIGHT",
    "TARGET_WIDTH",
    "Transform",
    "build",
    "centre",
    "regret",
    "resize",
    "set_loss",
    "spread",
    "top_pick",
]
