"""The head: the shape of the answer, the loss behind it, and the deploy view.

Two of these are pins rather than tests. The transform is what a score *means* —
a head trained on one geometry and scored on another is a head reporting numbers
about a picture it never saw — so its constants are asserted here rather than
left to whoever edits the module next.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers.models import head

numpy = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")


def test_the_deploy_transform_is_pinned() -> None:
    """384×224, a stretch, bicubic, from the 640×360 canonical tile.

    Every one of those four is load-bearing: the size is what the backbone was
    pretrained at, the stretch is why nothing is padded away, the filter decides
    what a one-pixel filament survives as, and the source size is the tile the
    evaluation is scored through.
    """
    from PIL import Image

    assert (head.TARGET_WIDTH, head.TARGET_HEIGHT) == (384, 224)
    assert (head.SOURCE_WIDTH, head.SOURCE_HEIGHT) == (640, 360)
    source = Image.new("RGB", (head.SOURCE_WIDTH, head.SOURCE_HEIGHT), (10, 20, 30))
    assert head.resize(source).size == (384, 224)
    # A stretch, not a pad: every row of the result carries picture, so a
    # constant image comes back constant rather than framed in black.
    resized = numpy.asarray(head.resize(source))
    assert (resized == numpy.array([10, 20, 30], dtype=numpy.uint8)).all()


def test_the_training_transform_is_the_deploy_transform_plus_jitter() -> None:
    """The same resize core, so the two cannot drift apart. What is added is
    bounded: geometry and exposure, never hue — the palette is part of the label."""
    import random

    from PIL import Image

    mean, std = (0.5, 0.5, 0.5), (0.25, 0.25, 0.25)
    picture = Image.new("RGB", (head.SOURCE_WIDTH, head.SOURCE_HEIGHT), (120, 60, 200))
    deploy = head.Transform(mean, std, "bicubic", train=False)(picture)
    training = head.Transform(mean, std, "bicubic", train=True)(picture, random.Random(0))
    assert deploy.shape == training.shape == (3, 224, 384)
    # A flat picture stays flat under either, and its hue survives: the channel
    # ordering of the training result must still read purple, not a jittered one.
    channels = training.mean(dim=(1, 2)) * torch.tensor(std) + torch.tensor(mean)
    assert channels[0] > channels[1] and channels[2] > channels[0]


def test_the_deploy_transform_is_deterministic() -> None:
    from PIL import Image

    picture = Image.new("RGB", (head.SOURCE_WIDTH, head.SOURCE_HEIGHT))
    transform = head.Transform((0.5,) * 3, (0.25,) * 3, "bicubic", train=False)
    assert torch.equal(transform(picture), transform(picture))


def test_the_head_emits_one_logit_per_cutpoint() -> None:
    model = head.build(num_classes=head.CLASSES, pretrained=False)
    logits = model(torch.zeros(2, 3, head.TARGET_HEIGHT, head.TARGET_WIDTH))
    assert logits.shape == (2, head.CLASSES - 1)


def test_the_probabilities_are_the_running_product_and_never_invert() -> None:
    """The whole point of training the cutpoints conditionally. Read as raw
    sigmoids they can say a place is likelier to be a 4 than to be at least a 3."""
    logits = torch.tensor([[2.0, -1.0, 0.5], [-3.0, 4.0, 1.0], [0.0, 0.0, 0.0]])
    conditional = head.conditional(logits)
    unconditional = head.probabilities(logits)
    assert numpy.allclose(unconditional, numpy.cumprod(conditional, axis=1))
    assert (numpy.diff(unconditional, axis=1) <= 1e-12).all()
    # The second row is the failure the product removes: conditionally it clears
    # the middle cutpoint easily, unconditionally it cannot pass the first.
    assert conditional[1, 1] > conditional[1, 0]
    assert unconditional[1, 1] <= unconditional[1, 0]


def test_a_large_logit_does_not_overflow() -> None:
    probabilities = head.probabilities(torch.tensor([[800.0, -800.0, 0.0]]))
    assert numpy.isfinite(probabilities).all()
    assert probabilities[0, 0] == pytest.approx(1.0)
    assert probabilities[0, 1] == pytest.approx(0.0)


def test_the_loss_trains_each_cutpoint_on_the_subset_that_cleared_the_one_below() -> None:
    """A cutpoint's gradient must not depend on examples that never reached it —
    that conditioning is what makes the emitted probabilities nest."""
    labels = torch.tensor([1, 1, 4])
    logits = torch.zeros(3, 3, requires_grad=True)
    head.loss_of(logits, labels, num_classes=4).backward()
    gradient = logits.grad
    # The two 1s clear nothing, so they carry no gradient at the upper cutpoints.
    assert gradient[0, 1] == 0 and gradient[0, 2] == 0
    assert gradient[1, 1] == 0 and gradient[1, 2] == 0
    assert gradient[2, 2] != 0


def test_the_loss_is_lowest_when_the_head_is_right() -> None:
    labels = torch.tensor([1, 2, 3, 4])
    right = torch.tensor([[-8.0, -8.0, -8.0], [8.0, -8.0, -8.0], [8.0, 8.0, -8.0], [8.0, 8.0, 8.0]])
    assert head.loss_of(right, labels, num_classes=4) < 0.01
    assert head.loss_of(-right, labels, num_classes=4) > 4.0


def test_a_cutpoint_names_what_it_is_about() -> None:
    assert [head.cutpoint_label(index) for index in range(3)] == ["ge2", "ge3", "ge4"]
