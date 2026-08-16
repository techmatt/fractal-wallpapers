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
        assert set(entry) >= {"tag", "asset", "sha256", "source_commit", "provenance"}, name
        assert len(entry["sha256"]) == 64, name
        assert len(entry["source_commit"]) == 40, name
        assert entry["asset"].endswith(".pt"), name
        assert entry["provenance"]["supervision"], name


def test_the_manifest_is_release_complete() -> None:
    """A release is cut from this file and cannot be un-cut. A head missing from
    it is a clone that cannot run that head, and nothing else here would notice:
    the checkpoint is on the author's disk and every other test passes."""
    manifest = json.loads(ship.manifest_path().read_text(encoding="utf-8"))
    missing = [head for head in ship.HEADS if head not in manifest.get("heads", {})]
    assert not missing, f"the release would ship without: {missing}"


def test_the_distilled_head_names_its_teacher() -> None:
    """Its whole claim is approximate equivalence with one function. A release
    that did not say which function would be publishing an unfalsifiable one."""
    teacher = ship.provenance("palette")["teacher"]
    assert len(teacher["sha256"]) == 64
    assert teacher["name"] and teacher["resolved_through"]
    for head in set(ship.HEADS) - {"palette"}:
        assert "teacher" not in ship.provenance(head), f"{head} learned from human verdicts"


def test_the_tolerances_are_tight_enough_to_be_a_check() -> None:
    """Loose enough and the comparison passes on any pair of files."""
    assert ship.AUC_TOLERANCE <= 0.001
    assert ship.ROW_TOLERANCE <= 0.01


HEADS = ship.HEADS


def test_two_heads_cannot_ship_under_one_name() -> None:
    """A release's assets share one namespace, and the directory that keeps these
    apart on disk does not travel with them."""
    names = {ship.shipped_path(head).name for head in HEADS}
    assert len(names) == len(HEADS), f"two heads would upload the same asset: {sorted(names)}"
    for head in HEADS:
        assert head in ship.shipped_path(head).name


def test_every_head_says_where_its_pieces_are() -> None:
    """The record is what lets one shipping path serve four heads. Three of them
    emit a tier and share the ordinal agreement read; the palette head's answer is
    a choice inside a candidate set, so it supplies its own statistic and nothing
    else about shipping changes."""
    for head in HEADS:
        shipment = ship.shipment_for(head)
        assert callable(shipment.checkpoint)
        assert callable(shipment.directory)
        assert callable(shipment.load)
        assert (shipment.evaluation is None) == (shipment.agree is not None), head


def test_the_ordering_bound_is_stated_in_the_unit_auc_moves_in() -> None:
    """An AUC on `p` positives and `n` negatives moves in steps of `1/(p·n)`.

    A bound finer than one of those demands *zero* rank swaps, which is not what
    "the order is materially unchanged" means and is not something a lossy cast
    can promise. On a large population the absolute floor is the tighter of the
    two and binds instead — which is the right way round.
    """
    tiny = 1.0 / (6 * 144)  # the strange sheet at its unmeasured boundary
    large = 1.0 / (22 * 980)  # the location head at its release cutpoint
    assert max(ship.AUC_TOLERANCE, ship.SWAP_TOLERANCE * tiny) > ship.AUC_TOLERANCE, (
        "on a six-positive sheet a single swap is worth more than the floor, so the "
        "swap term has to be what binds"
    )
    assert max(ship.AUC_TOLERANCE, ship.SWAP_TOLERANCE * large) == ship.AUC_TOLERANCE, (
        "on a thousand-row population a handful of swaps are invisible and the floor binds"
    )


def test_the_ordering_bound_stays_well_inside_what_a_bar_can_detect() -> None:
    """The bound may be generous about rounding; it may not be generous about
    anything an acceptance read is trying to see."""
    import json

    from fractal_wallpapers.models import finished_acceptance as acceptance

    for head, (positives, negatives) in (
        ("smooth_render", (96, 101)),
        ("strange_render", (76, 74)),
    ):
        path = acceptance.prereg_path(head)
        if not path.is_file():
            continue
        margin = json.loads(path.read_text(encoding="utf-8"))["arms"]["ordering"]["margin"]
        bound = max(ship.AUC_TOLERANCE, ship.SWAP_TOLERANCE / (positives * negatives))
        assert bound <= 0.1 * margin, (
            f"{head}: the shipping bound is {bound:.4f} against an acceptance margin of "
            f"{margin}. A cast allowed to move the order by a tenth of what the bar reads "
            f"is a cast that can move the verdict."
        )


def test_a_head_is_shipped_on_its_decisions_rather_than_its_probabilities() -> None:
    """The per-row bound was a proxy; the decoded tier is the thing itself."""
    assert 0.0 < ship.DECISION_TOLERANCE <= 0.02, "one in a hundred, not one in ten"
    from fractal_wallpapers.models import head

    # Decoding is a threshold on a rank, so a probability may move a long way
    # without changing an answer, and a hair's move at the threshold changes one.
    assert head.decode([0.99, 0.98, 0.51], 3) == 4
    assert head.decode([0.99, 0.98, 0.49], 3) == 3
    assert head.decode([0.99, 0.60, 0.49], 3) == 3, "a big move that changes nothing"
