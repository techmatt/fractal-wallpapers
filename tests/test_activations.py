"""The penultimate hook: that it reads the same pass the score does, and no other.

[`models.train.activations`] exists so a probe can be fitted on what the judge
saw one layer before it decided. That is only true if three things hold, and each
of them is a way the hook could be quietly wrong.

The **round trip**: the model's own `classifier` on the returned vector has to
reproduce `model(x)` exactly. If it does not, the vector is a reading of some
other point in the network and every coefficient fitted on it means something
nobody stated.

The **width**: the vector is the backbone's `head_hidden_size`, which is the
post-`norm_head` layer the classifier reads. `num_features` is the conv trunk and
is a different, wider-in-some-backbones and narrower-in-this-one tensor; the two
are easy to confuse and impossible to tell apart from a coefficient file.

The **order**: [`score`] promises "in the order it was given" and a probe joins
its rows to labels by position, so a hook that returned batches in completion
order would mislabel every row past the first batch and still look fine.

One model is built here and shared: `pretrained=False`, so nothing is fetched,
but it is still a network over real pictures and that is slow-lane work.
"""

from __future__ import annotations

import pytest

pytest.importorskip("torch")
pytest.importorskip("timm")

import numpy  # noqa: E402
import torch  # noqa: E402

from fractal_wallpapers.models import head as head_module  # noqa: E402
from fractal_wallpapers.models import train  # noqa: E402

#: The backbone both finished-render judges ship on. Read off the roster rather
#: than spelled again, so this guard follows a shipped artifact that moves.
BACKBONE = head_module.SHIPPED_BACKBONES["render"]

#: What the shipped render judge counts, and therefore three cutpoint logits.
CLASSES = 4


@pytest.fixture(scope="module")
def judge():
    """A judge-shaped model with untrained weights, in eval. Built once, seeded.

    Seeded because one of these guards quotes a float bound: an untrained
    backbone puts its logits out at about ±1000, where the CORN squash saturates
    and a rerun on fresh weights would move the bound around.
    """
    torch.manual_seed(0)
    model = head_module.build(num_classes=CLASSES, backbone=BACKBONE, pretrained=False)
    return model.eval()


@pytest.fixture(scope="module")
def pictures(tmp_path_factory):
    """Eight distinguishable pictures at the corpus aspect, on disk in a known order."""
    from PIL import Image

    directory = tmp_path_factory.mktemp("activations")
    rng = numpy.random.default_rng(7)
    out = []
    for index in range(8):
        array = rng.integers(0, 256, size=(72, 128, 3), dtype=numpy.uint8)
        path = directory / f"{index:02d}.jpg"
        Image.fromarray(array).save(path, quality=90)
        out.append(path)
    return out


def transform_of(judge):
    config = head_module.data_config(judge)
    return head_module.Transform(config["mean"], config["std"], config["interpolation"], False)


def stacked(judge, pictures):
    """Every picture as one batch, through the deploy transform."""
    from PIL import Image

    transform = transform_of(judge)
    frames = []
    for path in pictures:
        with Image.open(path) as opened:
            opened.load()
            frames.append(transform(opened.convert("RGB")))
    return torch.stack(frames)


@pytest.mark.slow
def test_the_classifier_on_the_penultimate_vector_reproduces_the_logits(judge, pictures) -> None:
    """The round trip, and it is EXACT rather than close.

    `forward_head(..., pre_logits=True)` stops one operation short of the
    logits, so putting the model's own `classifier` back on it is the same
    arithmetic in the same order on the same tensor — the head's dropout is
    identity in eval and drops out of the comparison with it. `AUDIT_top_slice_
    ranker_0906` measured max |Δ| = 0.0 on the shipped artifact; anything above
    zero here means the two paths are not the same path any more.
    """
    batch = stacked(judge, pictures)
    with torch.no_grad():
        logits = judge(batch)
        penultimate = judge.forward_head(judge.forward_features(batch), pre_logits=True)
        rebuilt = judge.classifier(penultimate)
    assert float((logits - rebuilt).abs().max()) == 0.0


@pytest.mark.slow
def test_the_hook_returns_the_penultimate_layer_and_not_the_trunk(judge, pictures) -> None:
    """The width is `head_hidden_size`, which is not `num_features`.

    On this backbone they are 1,280 and 960, and a probe handed the wrong one
    fits happily and reads a tensor the classifier never sees. The two are
    asserted to differ so that a backbone where they coincide cannot make this
    guard pass by accident.
    """
    read = train.activations(judge, pictures, transform_of(judge), "cpu", {"batch_size": 3})
    assert judge.head_hidden_size != judge.num_features
    assert read.shape == (len(pictures), judge.head_hidden_size)


@pytest.mark.slow
def test_the_hook_is_the_inline_pattern_it_replaces(judge, pictures) -> None:
    """The hook returns what `spiral_probe.features` computes by hand, exactly.

    Same batches, same order, and therefore the same reduction order in every
    matmul — so this is `== 0.0` and not a tolerance. It is the guard that says
    a caller may replace the inline pattern with the hook and change no number.
    """
    transform = transform_of(judge)
    read = train.activations(judge, pictures, transform, "cpu", {"batch_size": 3})
    blocks = []
    with torch.no_grad():
        for start in range(0, len(pictures), 3):
            batch = stacked(judge, pictures[start : start + 3])
            blocks.append(
                judge.forward_head(judge.forward_features(batch), pre_logits=True).float().numpy()
            )
    assert float(numpy.abs(read - numpy.vstack(blocks)).max()) == 0.0


@pytest.mark.slow
def test_the_hook_reads_the_same_pass_the_score_does(judge, pictures) -> None:
    """One pass, two stopping points: the hook's vectors carry the score.

    Both readings go through [`train._pictures`], so the decode, the transform
    and the order are one implementation, and the classifier on the hook's output
    lands back on [`score`]'s probabilities. The bound is not zero because the
    comparison multiplies all eight rows at once where the hook batched at
    three, which is a different GEMM shape; on this backbone's untrained weights
    that moves the logits by 4e-4 out at ±1000 and the probabilities by 2e-20.
    """
    recipe = {"batch_size": 3}
    transform = transform_of(judge)
    read = train.activations(judge, pictures, transform, "cpu", recipe)
    with torch.no_grad():
        logits = judge.classifier(torch.from_numpy(read)).double().numpy()
    scored = train.score(judge, pictures, transform, "cpu", CLASSES, recipe)
    assert float(numpy.abs(scored - head_module.probabilities(logits)).max()) < 1e-12


@pytest.mark.slow
def test_the_rows_come_back_in_the_order_the_paths_were_given(judge, pictures) -> None:
    """Position is the join, so a batch landing out of order is a mislabelled probe.

    Read once in the given order and once reversed, at a batch size that does
    not divide the population: the reversed reading has to be the first one
    upside down, row for row.
    """
    transform, recipe = transform_of(judge), {"batch_size": 3}
    forward = train.activations(judge, pictures, transform, "cpu", recipe)
    backward = train.activations(judge, list(reversed(pictures)), transform, "cpu", recipe)
    assert numpy.allclose(forward, backward[::-1], atol=1e-6)
    assert not numpy.allclose(forward[0], forward[1]), "eight random pictures are eight readings"


def test_an_empty_population_is_a_shape_rather_than_a_crash(judge) -> None:
    """No pictures is a state a caller can reach — a slice that cut to nothing —
    and it comes back as an empty array rather than as `None` or an exception."""
    read = train.activations(judge, [], transform_of(judge), "cpu", {"batch_size": 4})
    assert read.shape == (0, 0)
