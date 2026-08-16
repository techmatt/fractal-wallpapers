"""The distillation loop: how a batch is assembled, and what that must not change."""

from __future__ import annotations

import pytest

from fractal_wallpapers.models import palette_train

torch = pytest.importorskip("torch")


class Corpus:
    """A [`palette_train.Sets`] with the pictures already made, and no disk at all."""

    def __init__(self, sets: int, width: int, seed: int = 0) -> None:
        generator = torch.Generator().manual_seed(seed)
        self.sets = [{"set": f"{index:04d}"} for index in range(sets)]
        self.width = width
        self.names = [entry["set"] for entry in self.sets]
        self.pictures = torch.randint(
            0, 256, (sets * width, 3, 224, 224), dtype=torch.uint8, generator=generator
        )
        self.scores = torch.randn((sets, width), generator=generator)

    def __len__(self) -> int:
        return len(self.sets)

    def batch(self, indices, where: str, epoch: int | None = None):
        from fractal_wallpapers.models import palette_head

        offsets = torch.arange(self.width)
        flat = (torch.as_tensor(indices).view(-1, 1) * self.width + offsets).reshape(-1)
        pictures = palette_head.normalize(self.pictures[flat])
        pictures = pictures.view(len(indices), self.width, *pictures.shape[1:])
        return pictures, self.scores[torch.as_tensor(indices)]


def a_recipe(**over) -> dict:
    return {**palette_train.RECIPE, "listwise": 0.0, "listwise_temperature": None, **over}


def relative(mine, theirs) -> float:
    """How far apart two gradients are, as a share of the one they should be.

    Elementwise equality is the wrong test: the two runs sum the same terms in a
    different order, so they differ by float32's own last bits on values of order
    a thousand. What is being claimed is that they are the same vector.
    """
    return float(
        torch.linalg.vector_norm(mine - theirs) / torch.linalg.vector_norm(theirs).clamp(min=1e-12)
    )


def gradients(model):
    """Every parameter's gradient as ONE vector, which is what is being compared.

    Per-tensor comparison would fail on the biases whose gradient is a rounding
    error either way: a relative test against a number near zero says nothing.
    """
    return torch.cat(
        [
            parameter.grad.detach().reshape(-1)
            for parameter in model.parameters()
            if parameter.grad is not None
        ]
    )


@pytest.mark.parametrize("listwise", [0.0, 1.0])
def test_a_batch_split_into_pieces_is_the_same_gradient(listwise: float) -> None:
    """The claim the microbatching rests on. The objective is a mean over sets, so
    a piece scaled by its share of the batch contributes exactly its share of the
    gradient — otherwise the batch size would be an untracked hyperparameter that
    moved with the size of the card.

    Read in `eval` so BatchNorm uses its running statistics: the batch statistic is
    the ONE thing the split really changes, and this test is about the other thing.
    """
    pytest.importorskip("timm")
    from fractal_wallpapers.models import palette_head

    examples = Corpus(sets=4, width=6)
    recipe = a_recipe(listwise=listwise, listwise_temperature=0.5)
    indices = [0, 1, 2, 3]

    whole = palette_head.build(pretrained=False).eval()
    torch.manual_seed(0)
    palette_train.accumulate(whole, examples, indices, "cpu", recipe, None, len(indices))
    one_pass = gradients(whole)

    pieced = palette_head.build(pretrained=False).eval()
    pieced.load_state_dict(whole.state_dict())
    torch.manual_seed(0)
    palette_train.accumulate(pieced, examples, indices, "cpu", recipe, None, 2)
    assert relative(one_pass, gradients(pieced)) < 1e-5


def test_a_ragged_last_piece_is_still_weighted_by_what_it_holds() -> None:
    """The last batch of an epoch is not a whole batch, and neither is its last
    piece. A piece weighted as if it were full would let the tail of an epoch pull
    harder than the rest of it."""
    pytest.importorskip("timm")
    from fractal_wallpapers.models import palette_head

    examples = Corpus(sets=5, width=4, seed=1)
    recipe = a_recipe()
    indices = [0, 1, 2, 3, 4]

    whole = palette_head.build(pretrained=False).eval()
    palette_train.accumulate(whole, examples, indices, "cpu", recipe, None, 5)
    one_pass = gradients(whole)

    pieced = palette_head.build(pretrained=False).eval()
    pieced.load_state_dict(whole.state_dict())
    palette_train.accumulate(pieced, examples, indices, "cpu", recipe, None, 2)
    assert relative(one_pass, gradients(pieced)) < 1e-5


def test_the_recipe_keeps_the_batch_the_teacher_trained_under() -> None:
    """The piece is a fact about this card; the batch is a fact about the teacher's
    config, and it is the one the optimizer steps on."""
    assert palette_train.RECIPE["batch_sets"] == 16
    assert palette_train.RECIPE["microbatch_sets"] <= palette_train.RECIPE["batch_sets"]
    assert palette_train.RECIPE["batch_sets"] % palette_train.RECIPE["microbatch_sets"] == 0
    assert palette_train.RECIPE["listwise"] == 0.0, (
        "the listwise term is an arm; a default that is on is not an arm"
    )
