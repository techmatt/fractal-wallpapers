"""The ordinal head: what it is, what it sees, and what it is scored against.

## Four tiers on one scale, not four classes

A human labels a location 1 to 4, and the numbers are ordered: a 3 is closer to a
4 than a 1 is. Cross-entropy over four classes throws that away — it is as
unhappy about calling a 4 a 3 as about calling it a 1 — so the head is
**ordinal**. It emits `K − 1 = 3` logits, one per cutpoint:

```text
cutpoint 0 → ≥2  "not bad"      cutpoint 1 → ≥3  a wallpaper
cutpoint 2 → ≥4  worth releasing
```

The loss is CORN — rank-consistent **conditional** training. Cutpoint `k` is
trained only on the examples that already cleared cutpoint `k − 1`, so the three
tasks are nested by construction rather than by hope. A stack of three
independent binary heads is not: it will happily say a picture is 60% likely to
be at least a 4 and 40% likely to be at least a 3.

That conditioning is also the one thing easy to get wrong at read time, and
[`probabilities`] is where it is got right: `σ(logit_k)` is a probability
*given* that the location cleared the cutpoint below, so the unconditional
answer is the running product. Reading the sigmoids on their own costs seven
points of AUC at the release cutpoint — measured, on this repository's own
evaluation side.

**Both `P(≥3)` and `P(≥4)` are part of the interface**, not just the scalar. The
supply engine weights a release-worthy location ten times a merely good one, and
that weighting reads `P(≥4)` directly; a head that only exposed the summed rank
score would leave it nothing to weight with.

## The transform is the same core in training and at deploy

`deploy` is a bare deterministic resize and normalize. `training` wraps that
*same* resize in augmentation and nothing else — so the geometry a head learns on
and the geometry it is scored on cannot drift apart. What the augmentation may
touch is bounded by one rule: **the palette is part of the label.** A person
judging these pictures is partly judging their color, so hue and saturation are
never jittered. Brightness and contrast move by three percent, flips are free
(the set is symmetric about the real axis and a flipped fractal is a fractal),
and the JPEG quality is re-drawn — which is a real deployment variable rather
than a trick.

The finished-render judges take that rule further and turn the last three off
entirely: for them the *coloring* is what is being judged, not the place, and a
brightness jitter is a small edit to the very thing the verdict is about. Their
recipes say so, so the knobs are parameters here rather than constants — a zero
brightness and an absent JPEG jitter mean the stage is skipped, not run at
strength zero.

The resize is a **stretch**, not a pad: 640×360 to 384×224 squeezes the vertical
by four percent. Padding would spend a tenth of the head's input on black bars,
and a four percent squeeze is far below what the judgement turns on.
"""

from __future__ import annotations

import io
import random
from dataclasses import dataclass

#: The scale a label is cast on, and therefore the number of tiers the head
#: models. Read from the config at every use site rather than assumed, so the
#: scale and the head cannot disagree about how many cutpoints there are.
CLASSES = 4

#: The timm backbone. Pretrained on ImageNet-12k at 384 pixels, which is the
#: resolution these tiles are read at, and small enough that a training run is an
#: hour. A comparison against five alternatives — two vision transformers, a
#: larger convolutional net, a hybrid, and an EfficientNet — kept it: nothing was
#: better outside noise, and it was the fastest and the smallest.
BACKBONE = "mobilenetv4_conv_medium.e250_r384_in12k"

#: What the head is handed, in pixels. Wider than it is tall because the pictures
#: are, and a square input would mean padding or cropping away a third of each.
TARGET_WIDTH, TARGET_HEIGHT = 384, 224

#: The picture a location is judged from: the canonical tile's own size.
SOURCE_WIDTH, SOURCE_HEIGHT = 640, 360

#: How far each edge may be cropped in training, as a fraction of its dimension.
BORDER_CROP = 0.05

#: The JPEG quality band the training transform re-encodes through. The tiles are
#: already drawn across a wider band; this is the second, smaller jitter the
#: source recipe applies on top, and it is carried unchanged.
JPEG_JITTER = (85, 95)

#: How far brightness and contrast may move. Small on purpose — see the module
#: docstring on why color is not a free axis here.
BRIGHTNESS, CONTRAST = 0.03, 0.03


def build(num_classes: int = CLASSES, backbone: str = BACKBONE, **kwargs):
    """The backbone with an ordinal head on it: `K − 1` logits, one per cutpoint."""
    import timm

    return timm.create_model(backbone, num_classes=num_classes - 1, **kwargs)


def data_config(model) -> dict:
    """The normalization the pretrained backbone was trained under.

    Read off the checkpoint rather than assumed to be ImageNet-1k's: this one is
    an ImageNet-12k checkpoint and its statistics differ. A head normalized with
    the wrong constants trains anyway, a few points worse, and says nothing.
    """
    import timm

    resolved = timm.data.resolve_model_data_config(model)
    return {
        "mean": tuple(float(value) for value in resolved["mean"]),
        "std": tuple(float(value) for value in resolved["std"]),
        "interpolation": resolved["interpolation"],
        "input_size": tuple(int(value) for value in resolved["input_size"]),
    }


def resize(image, interpolation: str = "bicubic"):
    """The deterministic core: a source picture to the head's input size.

    Identical in training and at deploy, which is the whole point of it being a
    function of its own.
    """
    from PIL import Image

    filters = {
        "nearest": Image.NEAREST,
        "bilinear": Image.BILINEAR,
        "bicubic": Image.BICUBIC,
        "lanczos": Image.LANCZOS,
    }
    return image.resize((TARGET_WIDTH, TARGET_HEIGHT), filters.get(interpolation, Image.BICUBIC))


@dataclass
class Transform:
    """Picture → normalized tensor. `train` decides whether it jitters."""

    mean: tuple
    std: tuple
    interpolation: str = "bicubic"
    train: bool = False
    #: How far each edge may be cropped, as a fraction of its dimension.
    border_crop: float = BORDER_CROP
    #: The JPEG quality band to re-encode through, or `None` to skip re-encoding.
    jpeg: tuple | None = JPEG_JITTER
    #: How far brightness and contrast may move. Zero skips the stage.
    brightness: float = BRIGHTNESS
    contrast: float = CONTRAST

    def __call__(self, image, rng: random.Random | None = None):
        from PIL import Image

        if image.mode != "RGB":
            image = image.convert("RGB")
        if not self.train:
            tensor = _to_tensor(resize(image, self.interpolation))
            return self._normalize(tensor)

        draw = rng or random
        width, height = image.size
        left = round(draw.uniform(0, self.border_crop) * width)
        top = round(draw.uniform(0, self.border_crop) * height)
        right = round(draw.uniform(0, self.border_crop) * width)
        bottom = round(draw.uniform(0, self.border_crop) * height)
        if left + right < width - 8 and top + bottom < height - 8:
            image = image.crop((left, top, width - right, height - bottom))
        image = resize(image, self.interpolation)
        # Both flips, because the set is symmetric about the real axis and a
        # mirrored fractal is a fractal — this is a free doubling twice over,
        # not a distortion the head has to be robust to.
        if draw.random() < 0.5:
            image = image.transpose(Image.FLIP_LEFT_RIGHT)
        if draw.random() < 0.5:
            image = image.transpose(Image.FLIP_TOP_BOTTOM)
        if self.jpeg is not None:
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=draw.randint(*self.jpeg))
            buffer.seek(0)
            image = Image.open(buffer).convert("RGB")

        tensor = _to_tensor(image)
        if self.brightness == 0.0 and self.contrast == 0.0:
            return self._normalize(tensor)
        tensor = tensor * (1.0 + draw.uniform(-self.brightness, self.brightness))
        middle = tensor.mean()
        tensor = (tensor - middle) * (1.0 + draw.uniform(-self.contrast, self.contrast)) + middle
        return self._normalize(tensor.clamp(0, 1))

    def _normalize(self, tensor):
        import torch

        mean = torch.tensor(self.mean).view(3, 1, 1)
        std = torch.tensor(self.std).view(3, 1, 1)
        return (tensor - mean) / std


def _to_tensor(image):
    import numpy
    import torch

    array = numpy.array(image, dtype=numpy.uint8)
    return torch.from_numpy(array).permute(2, 0, 1).float() / 255.0


def corn_loss(logits, ranks, num_classes: int = CLASSES):
    """CORN: one conditional-subset binary task per cutpoint.

    Cutpoint `k` is trained only on the examples whose rank already reached `k`,
    which is what makes the emitted probabilities monotone by construction rather
    than by hope. Each subset contributes its own mean, and the losses are
    averaged over the cutpoints, so a rare top class cannot be drowned by the
    common bottom one simply because there is more of it.
    """
    import torch.nn.functional as functional

    total = logits.new_zeros(())
    tasks = num_classes - 1
    for cutpoint in range(tasks):
        subset = ranks > (cutpoint - 1)
        if subset.sum() < 1:
            continue
        target = (ranks[subset] > cutpoint).float()
        predicted = logits[subset, cutpoint]
        log_sigmoid = functional.logsigmoid(predicted)
        loss = -(log_sigmoid * target + (log_sigmoid - predicted) * (1.0 - target)).sum()
        total = total + loss / subset.sum()
    return total / tasks


def loss_of(logits, labels, num_classes: int = CLASSES):
    """The training loss, from raw 1..K labels."""
    return corn_loss(logits.float(), (labels - 1).long(), num_classes=num_classes)


def conditional(logits):
    """Logits → the **conditional** probabilities the loss trains directly.

    Column `k` is `P(label > k+1 | label ≥ k+1)`, because that is the subset
    cutpoint `k` was trained on. On its own it is not the answer to any question
    a caller asks; see [`probabilities`].
    """
    import numpy

    array = numpy.asarray(logits, dtype=numpy.float64)
    # The stable sigmoid: `exp` of a large positive logit overflows, and the
    # scores this head produces do reach that far on an easy negative.
    positive = array >= 0
    out = numpy.empty_like(array)
    out[positive] = 1.0 / (1.0 + numpy.exp(-array[positive]))
    exponent = numpy.exp(array[~positive])
    out[~positive] = exponent / (1.0 + exponent)
    return out


def probabilities(logits):
    """Logits → `P(≥2), P(≥3), P(≥4)` — the running product of the conditionals.

    **This is the whole reason CORN's cutpoints are trained conditionally, and
    reading a cutpoint's sigmoid on its own throws it away.** Cutpoint `k` sees
    only the examples that already cleared cutpoint `k − 1`, so `σ(logit_k)` is a
    probability *given* that they did. What a caller wants — "how likely is this
    place worth releasing" — is unconditional, and it is the product of the
    conditionals along the way.

    Two things follow, and both matter downstream. The columns are **monotone
    non-increasing by construction**, so the head can never say a location is
    more likely to be a 4 than to be at least a 3. And the deeper cutpoints stop
    being systematically over-confident: read as raw sigmoids, the source
    project's own committed control scores measure **AUC(≥4) = 0.869–0.900** on
    this repository's evaluation side, and the same numbers read as products
    measure **0.943–0.949**. Seven points of ordering at the release cutpoint,
    from the reading alone.
    """
    import numpy

    return numpy.cumprod(conditional(logits), axis=1)


def rank_score(probabilities_):
    """The one monotone scalar: `Σ P(≥k)`, in `[0, K − 1]`.

    Useful for ranking a queue when only an order is wanted. It is deliberately
    *not* the interface — a consumer that needs "is this releasable" reads
    `P(≥4)` and gets a probability, not a position on a made-up scale.
    """
    import numpy

    return numpy.asarray(probabilities_, dtype=numpy.float64).sum(axis=1)


def decode(probabilities_, cutpoints: int | None = None) -> int:
    """One row's tier: 1, plus every cutpoint whose probability reaches a half.

    A threshold on a rank rather than an argmax over classes. The probabilities
    are monotone by construction, so this can never name a tier the head thought
    less likely than the one below it — which an argmax over four independent
    class scores can and does.
    """
    row = list(probabilities_)
    tier = 1
    for index in range(cutpoints if cutpoints is not None else len(row)):
        if row[index] >= 0.5:
            tier += 1
    return tier


def cutpoint_label(index: int) -> str:
    """What cutpoint `index` is about, as it is written in every record."""
    return f"ge{index + 2}"


__all__ = [
    "BACKBONE",
    "BORDER_CROP",
    "BRIGHTNESS",
    "CLASSES",
    "CONTRAST",
    "JPEG_JITTER",
    "SOURCE_HEIGHT",
    "SOURCE_WIDTH",
    "TARGET_HEIGHT",
    "TARGET_WIDTH",
    "Transform",
    "build",
    "conditional",
    "corn_loss",
    "cutpoint_label",
    "decode",
    "data_config",
    "loss_of",
    "probabilities",
    "rank_score",
    "resize",
]
