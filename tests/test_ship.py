"""What ships: the cast, the re-read, and the manifest entry that names a hash."""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.models import ship

torch = pytest.importorskip("torch")


def test_only_the_floating_tensors_are_halved() -> None:
    """A buffer of counts or indices is not a weight. Casting it would be a
    silent change to what the model does rather than to how big the file is."""
    state = {
        "weight": torch.randn(4, 4),
        "running_var": torch.rand(4),
        "num_batches_tracked": torch.tensor(1234567, dtype=torch.long),
    }
    halved = ship.halve(state)
    assert halved["weight"].dtype == torch.float16
    assert halved["running_var"].dtype == torch.float16
    assert halved["num_batches_tracked"].dtype == torch.long
    assert int(halved["num_batches_tracked"]) == 1234567


def test_the_cast_round_trips_exactly() -> None:
    """fp16 is a real format, not an approximation with a scale: what goes in
    comes back out, which is why the verification is an equality and not a
    tolerance."""
    original = torch.randn(64, 64)
    halved = ship.halve({"w": original})["w"]
    assert torch.equal(halved.float().half(), halved)
    # And the widening is exact — a load does not have to undo anything.
    assert torch.equal(halved.float(), halved.to(torch.float32))


def test_a_hash_is_of_the_file_that_was_written(tmp_path) -> None:
    path = tmp_path / "artifact.bin"
    path.write_bytes(b"weights")
    digest = ship.sha256_of(path)
    assert len(digest) == 64
    path.write_bytes(b"different weights")
    assert ship.sha256_of(path) != digest


def test_the_manifest_keeps_its_shape() -> None:
    """`fetch-weights` reads this file and verifies a sha256 before keeping a
    download; a manifest missing a field is a download nobody checked."""
    manifest = json.loads(ship.manifest_path().read_text(encoding="utf-8"))
    assert manifest["schema"] == ship.SCHEMA
    for name, entry in manifest.get("heads", {}).items():
        assert set(entry) >= {"tag", "asset", "sha256"}, name
        assert len(entry["sha256"]) == 64, name
        assert entry["asset"].endswith(".pt"), name


def test_the_tolerances_are_tight_enough_to_be_a_check() -> None:
    """Loose enough and the comparison passes on any pair of files."""
    assert ship.AUC_TOLERANCE <= 0.001
    assert ship.ROW_TOLERANCE <= 0.01


def test_two_heads_cannot_ship_under_one_name() -> None:
    """A release's assets share one namespace, and the directory that keeps these
    apart on disk does not travel with them."""
    names = {
        ship.shipped_path(head).name for head in ("location", "smooth_render", "strange_render")
    }
    assert len(names) == 3, f"two heads would upload the same asset: {sorted(names)}"
    for head in ("location", "smooth_render", "strange_render"):
        assert head in ship.shipped_path(head).name
