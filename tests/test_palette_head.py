"""The palette head's shape, its transform, and the loss that distils it."""

from __future__ import annotations

import pytest

from fractal_wallpapers.models import palette_head

torch = pytest.importorskip("torch")
Image = pytest.importorskip("PIL.Image")


def a_picture(seed: int = 0):
    import numpy
    from PIL import Image as PILImage

    generator = numpy.random.default_rng(seed)
    array = generator.integers(0, 256, size=(360, 640, 3), dtype=numpy.uint8)
    return PILImage.fromarray(array, "RGB")


def test_the_deploy_transform_is_the_teacher_s_own() -> None:
    """The one thing a distilled student cannot be allowed to differ on.

    The teacher's recipe is a squash to 224 with bicubic resampling and
    ImageNet-1k normalization, spelled in `torchvision`'s v2 transforms. This
    repository spells it in PIL, so the two are checked against each other rather
    than assumed to agree — a student reading a slightly different picture would
    be learning the difference between two transforms as well as the function.
    """
    transforms = pytest.importorskip("torchvision.transforms.v2")

    theirs = transforms.Compose(
        [
            transforms.Resize(
                (224, 224), interpolation=transforms.InterpolationMode.BICUBIC, antialias=True
            ),
            transforms.ToImage(),
            transforms.ToDtype(torch.float32, scale=True),
            transforms.Normalize(palette_head.MEAN, palette_head.STD),
        ]
    )
    picture = a_picture()
    ours = palette_head.Transform(train=False)(picture)
    assert ours.shape == (3, 224, 224)
    assert torch.allclose(ours, theirs(picture), atol=1e-5)


def test_the_training_transform_only_flips() -> None:
    """Colour is the question, so no stage of the augmentation may touch it."""
    import random

    picture = a_picture(1)
    deploy = palette_head.Transform(train=False)(picture)
    flipped = palette_head.Transform(train=True)(picture, random.Random(0))
    # Whichever flips were drawn, the multiset of pixel values is unchanged: a
    # colour jitter would move it and a geometric one cannot.
    assert torch.allclose(deploy.sort(dim=-1).values.sum(), flipped.sort(dim=-1).values.sum())
    assert torch.allclose(deploy.mean(), flipped.mean(), atol=1e-6)


def test_the_loss_is_zero_only_on_the_teacher_s_own_vector() -> None:
    teacher = torch.tensor([[1.0, 3.0, 2.0, 0.0], [0.5, 0.25, 0.75, 1.0]])
    assert palette_head.set_loss(teacher, teacher).item() == pytest.approx(0.0)
    assert palette_head.set_loss(teacher + 0.3, teacher).item() == pytest.approx(0.0)
    assert palette_head.set_loss(teacher * 2, teacher).item() > 0.0


def test_the_loss_is_not_invariant_to_a_rescaling() -> None:
    """Why it, and not a rank statistic, chooses the epoch.

    A student that keeps the teacher's order and flattens its gaps is a worse
    distillation than one that reproduces both, and every rank statistic rates
    the two identically.
    """
    from fractal_wallpapers.models import metrics

    teacher = torch.tensor([[0.0, 1.0, 2.0, 3.0]])
    flattened = torch.tensor([[0.0, 0.1, 0.2, 0.3]])
    assert metrics.spearman(flattened[0].numpy(), teacher[0].numpy()) == pytest.approx(1.0)
    assert palette_head.set_loss(flattened, teacher).item() > 0.5


def test_a_set_is_worth_a_set_however_wide_it_is() -> None:
    """Averaged over candidates first, so a 32-map set does not outvote an 8-map one."""
    narrow = torch.zeros((1, 4))
    wide = torch.zeros((1, 32))
    assert palette_head.set_loss(narrow + 1.0, narrow).item() == pytest.approx(
        palette_head.set_loss(wide + 1.0, wide).item()
    )


def test_regret_is_zero_when_the_picks_agree_and_never_negative() -> None:
    import numpy

    teacher = numpy.array([0.1, 0.9, 0.4])
    assert palette_head.regret(numpy.array([0.0, 1.0, 0.0]), teacher) == pytest.approx(0.0)
    assert palette_head.regret(numpy.array([1.0, 0.0, 0.0]), teacher) == pytest.approx(0.8)
    assert palette_head.spread(teacher) == pytest.approx(0.8)


def test_the_head_emits_exactly_one_number_per_picture() -> None:
    timm = pytest.importorskip("timm")
    del timm

    model = palette_head.build(pretrained=False)
    with torch.no_grad():
        out = model(torch.zeros(2, 3, 224, 224))
    assert out.view(-1).shape == (2,)
