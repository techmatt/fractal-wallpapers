"""A killed run has to come back, and the snapshot is where that is decided.

Resuming is the one path in a trainer that only ever runs after something went
wrong, so it is the one path that can be broken for months without anyone
noticing. It was: a forty-epoch run stalled on its eleventh epoch, and the
relaunch died reading its own snapshot.
"""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")


def snapshot() -> dict:
    """The random-number half of what a trainer writes every epoch."""
    return {
        "torch_rng": torch.get_rng_state(),
        "cuda_rng": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None,
    }


def test_a_snapshot_read_back_onto_the_cpu_is_accepted(tmp_path) -> None:
    """What the trainers do now, and it has to keep working."""
    path = tmp_path / "resume.pt"
    torch.save(snapshot(), path)
    saved = torch.load(path, map_location="cpu", weights_only=False)
    torch.set_rng_state(saved["torch_rng"].cpu().to(torch.uint8))
    if saved["cuda_rng"] is not None:
        torch.cuda.set_rng_state_all([state.cpu().to(torch.uint8) for state in saved["cuda_rng"]])


@pytest.mark.skipif(not torch.cuda.is_available(), reason="the bug needs a device to map onto")
def test_a_snapshot_mapped_onto_the_training_device_is_refused(tmp_path) -> None:
    """The failure this pins, planted red. A snapshot holds two kinds of tensor:
    weights, which `load_state_dict` places wherever they have to go, and
    random-number state, which is a CPU byte tensor and is rejected outright if
    it arrives on the GPU. `map_location=where` loads the file fine and then
    dies several lines later, which is why it read as a corrupt snapshot rather
    than as a wrong argument."""
    path = tmp_path / "resume.pt"
    torch.save(snapshot(), path)
    saved = torch.load(path, map_location="cuda", weights_only=False)
    with pytest.raises(TypeError, match="ByteTensor"):
        torch.set_rng_state(saved["torch_rng"])
