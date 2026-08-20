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


def test_a_second_trainer_is_refused_the_directory(tmp_path, monkeypatch) -> None:
    """Two trainers in one directory take turns overwriting one checkpoint and
    produce a run whose numbers belong to neither. The lock is written in
    `train` and every trainer here uses it — this pins that the one that owns it
    takes it, which for a long time it did not."""
    from fractal_wallpapers.models import train

    train.claim(tmp_path)
    with pytest.raises(RuntimeError, match="already has"):
        train.claim(tmp_path)


def test_the_location_trainer_takes_the_lock_and_gives_it_back() -> None:
    """Taken at the top of the run and released only after the checkpoints are
    written, so a crash leaves it behind and says so rather than letting the
    next run in on top of a half-written one."""
    import inspect

    from fractal_wallpapers.models import train

    body = inspect.getsource(train.train)
    assert "lock = claim(directory)" in body
    taken = body.index("lock = claim(directory)")
    saved = body.index('checkpoint_path(name, "last", run)')
    released = body.index("lock.unlink(")
    assert taken < saved < released, "the lock is released before the run is written down"
