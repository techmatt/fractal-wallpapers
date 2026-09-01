"""The bound-signature sidecar: what it holds, when it is stale, and what it saves.

The store exists so the gallery leg stops paying a JPEG decode for a number that
never changes. Two things have to be true for that to be safe and they are what
this file pins: the stored vector is **exactly** what the pass would have derived,
so a gallery chosen with the sidecar is the gallery chosen without it; and a row
whose picture is no longer the recipe's picture is not used.

Real decodes are slow, so the pictures here are tiny generated JPEGs rather than
the pool's — a signature is a signature whatever it is a signature of, and what is
under test is the store and not the metric.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from fractal_wallpapers.curation import rules, signatures


@pytest.fixture(autouse=True)
def sidecar_in_a_tmp_store(tmp_path, monkeypatch):
    """The sidecar under `tmp_path`, never the real store.

    `rehome` resolves a recorded picture through the ledger's tiers and answers
    `None` for anything outside them, so a tmp picture has to be resolved as
    itself — `test_flatness` patches it for the same reason.
    """
    monkeypatch.setattr(signatures.candidate_ledger, "store_root", lambda: tmp_path)
    # Overrides `conftest.no_signature_sidecar`, which points every other test at a
    # store that does not exist. A file fixture runs after the autouse one, so this
    # is the setattr that stands.
    monkeypatch.setattr(signatures, "sidecar_path", lambda: tmp_path / signatures.SIDECAR_NAME)
    monkeypatch.setattr(
        "fractal_wallpapers.paths.rehome",
        lambda path: path if pathlib.Path(path).is_file() else None,
    )
    return tmp_path


def picture(tmp_path, name: str, seed: int):
    """One small JPEG, distinct per seed. Written once and read like any other."""
    import numpy
    from PIL import Image

    rng = numpy.random.default_rng(seed)
    made = rng.integers(0, 256, size=(64, 64, 3), dtype=numpy.uint8)
    where = tmp_path / f"{name}.jpg"
    Image.fromarray(made).save(where, quality=92)
    return where


class Row:
    """The two fields the sidecar reads off a candidate."""

    def __init__(self, key, picture):
        self.key = str(key)
        self.picture = str(picture)


# --------------------------------------------------------------------------- #
# The vector, and that it is the SAME vector.
# --------------------------------------------------------------------------- #
def test_the_stored_vector_is_bit_identical_to_what_the_pass_would_derive():
    """THE PIN. The sidecar is a cache of `rules.reduce_signature`, so a gallery
    chosen from it must be the gallery chosen without it. `float32` round-trips
    exactly; a `float16` packing — which is what `embeddings` uses for its unit
    vectors — would not, and would quietly move a sound lower bound."""
    import numpy

    from fractal_wallpapers.palettes import pixel_clouds

    made = numpy.linspace(0.0, 255.0, 128 * 1024, dtype=numpy.float32)
    want = rules.reduce_signature(made).reshape(-1)
    back = signatures.unpack(signatures.pack(want))
    assert numpy.array_equal(want, back), "not approximately — exactly"
    assert back.dtype == numpy.float32
    blocks, directions = signatures.shape()
    assert len(back) == rules.bound_width() == blocks * directions
    assert directions == pixel_clouds.groups.DIRECTIONS


def test_a_row_carries_the_constants_it_was_reduced_at(tmp_path):
    where = picture(tmp_path, "a", seed=1)
    made = signatures.reduced(where)
    row = signatures.row("k", str(where), signatures.pack(made))
    blocks, directions = signatures.shape()
    assert (row["blocks"], row["directions"]) == (blocks, directions)
    assert row["schema"] == signatures.SCHEMA
    assert row["picture"] == str(where)


def test_a_row_reduced_at_other_constants_is_not_read_back(tmp_path):
    """Change either constant and every row is stale at once, which is correct: a
    signature reduced at other constants is a different vector and must not be able
    to wear this one's name."""
    where = picture(tmp_path, "a", seed=2)
    row = signatures.row("k", str(where), signatures.pack(signatures.reduced(where)))
    row["blocks"] = row["blocks"] + 1
    signatures.write([row])
    assert signatures.by_recipe() == {}, "a foreign reduction answers for nothing"
    assert signatures.for_candidates([Row("k", where)]) == {}


def test_an_unreadable_picture_gets_no_row_rather_than_a_zero(tmp_path):
    """No reading and a reading of nothing are different facts. `reduced` says so
    with `None` and the sweep counts it rather than storing a vector of zeros."""
    assert signatures.reduced(tmp_path / "nothing.jpg") is None
    (tmp_path / "broken.jpg").write_bytes(b"not a jpeg")
    assert signatures.reduced(tmp_path / "broken.jpg") is None


# --------------------------------------------------------------------------- #
# Staleness, and that it is never a clock.
# --------------------------------------------------------------------------- #
def test_staleness_is_the_pictures_identity_and_never_its_mtime(tmp_path):
    """THE RULE. `curate retention` moves pictures and a restore rewrites their
    mtimes, so a store keyed on time re-sweeps a pool nothing changed AND misses a
    picture replaced inside one second. The row carries the picture it was read
    from and a mismatch is the only staleness there is."""
    first = picture(tmp_path, "first", seed=3)
    rows = [Row("k", first)]
    signatures.sweep(rows, workers=1, log=lambda *_: None)
    assert signatures.coverage(rows)["held"] == 1

    # Same key, same store, a DIFFERENT picture: stale, and swept again.
    second = picture(tmp_path, "second", seed=4)
    moved = [Row("k", second)]
    assert [held[0] for held in signatures.missing(moved)] == ["k"]
    assert signatures.coverage(moved)["held"] == 0

    # And the mtime moving under the SAME picture is not staleness at all.
    import os

    os.utime(first, (0, 0))
    assert signatures.missing(rows) == []
    assert signatures.coverage(rows)["held"] == 1


def test_the_sweep_is_incremental_and_a_swept_store_reads_no_picture(tmp_path):
    rows = [Row(f"k{at}", picture(tmp_path, f"p{at}", seed=10 + at)) for at in range(3)]
    first = signatures.sweep(rows, workers=1, log=lambda *_: None)
    assert first["read"] == 3 and first["outstanding"] == 3
    again = signatures.sweep(rows, workers=1, log=lambda *_: None)
    assert again["outstanding"] == 0 and again["read"] == 0, "one read and no decodes"
    assert again["rows"] == 3


def test_recompute_re_reads_everything(tmp_path):
    rows = [Row("k", picture(tmp_path, "p", seed=20))]
    signatures.sweep(rows, workers=1, log=lambda *_: None)
    forced = signatures.sweep(rows, workers=1, recompute=True, log=lambda *_: None)
    assert forced["outstanding"] == 1 and forced["read"] == 1


def test_the_record_says_what_stale_means(tmp_path):
    rows = [Row("k", picture(tmp_path, "p", seed=21))]
    record = signatures.sweep(rows, workers=1, log=lambda *_: None)
    assert "NEVER a timestamp" in record["stale_when"]


# --------------------------------------------------------------------------- #
# What a reader gets.
# --------------------------------------------------------------------------- #
def test_for_candidates_keeps_only_the_keys_it_was_asked_for(tmp_path):
    """The store is ~245 MB and a view is a fraction of it. Holding the rest would
    put a quarter of a gibibyte behind a pass that will never look at it."""
    rows = [Row(f"k{at}", picture(tmp_path, f"p{at}", seed=30 + at)) for at in range(4)]
    signatures.sweep(rows, workers=1, log=lambda *_: None)
    held = signatures.for_candidates(rows[:2])
    assert set(held) == {"k0", "k1"}


def test_twins_seeded_from_the_sidecar_opens_no_picture_for_the_bound(tmp_path):
    """THE POINT OF THE STORE. A `Twins` handed the sidecar answers the bound for
    every key it covers without a decode — `reduced_made` stays at zero — and the
    answer is the same one it gives without it."""
    rows = [Row(f"k{at}", picture(tmp_path, f"p{at}", seed=40 + at)) for at in range(3)]
    signatures.sweep(rows, workers=1, log=lambda *_: None)
    held = signatures.for_candidates(rows)
    assert len(held) == 3

    cold = rules.Twins(rules.clouds_for(rows))
    warm = rules.Twins(rules.clouds_for(rows), reduced=held)
    assert warm.reduced_from_the_sidecar == 3
    for row in rows:
        import numpy

        assert numpy.array_equal(cold.reduced_of(row.key), warm.reduced_of(row.key))
    assert cold.reduced_made == 3, "the pass without a sidecar decoded every one"
    assert warm.reduced_made == 0, "the pass with one decoded none"
    assert warm.record()["reduced_from_the_sidecar"] == 3


def test_a_key_the_sidecar_misses_is_made_on_demand_rather_than_refused(tmp_path):
    """A warm-up and never a gate: an unswept checkout is slower and never wrong."""
    rows = [Row(f"k{at}", picture(tmp_path, f"p{at}", seed=50 + at)) for at in range(2)]
    signatures.sweep(rows[:1], workers=1, log=lambda *_: None)
    twins = rules.Twins(rules.clouds_for(rows), reduced=signatures.for_candidates(rows))
    assert twins.reduced_from_the_sidecar == 1
    assert twins.reduced_of("k1") is not None, "made on demand"
    assert twins.reduced_made == 1


# --------------------------------------------------------------------------- #
# The store on disk.
# --------------------------------------------------------------------------- #
def test_the_sidecar_is_jsonl_with_a_schema_on_every_row(tmp_path):
    rows = [Row(f"k{at}", picture(tmp_path, f"p{at}", seed=60 + at)) for at in range(2)]
    signatures.sweep(rows, workers=1, log=lambda *_: None)
    text = signatures.sidecar_path().read_text(encoding="utf-8")
    assert "\r\n" not in text, "written newline='\\n' like every other tracked-shape store"
    for line in text.splitlines():
        assert json.loads(line)["schema"] == signatures.SCHEMA


def test_a_foreign_schema_refuses_rather_than_being_skipped(tmp_path):
    where = signatures.sidecar_path()
    where.write_text(json.dumps({"schema": 99, "recipe_key": "k"}) + "\n", encoding="utf-8")
    with pytest.raises(signatures.SignatureError):
        signatures.read()
    with pytest.raises(signatures.SignatureError):
        signatures.for_candidates([Row("k", "p.jpg")])


def test_the_sweep_writes_by_upsert_and_keeps_what_it_did_not_touch(tmp_path):
    one = [Row("k0", picture(tmp_path, "p0", seed=70))]
    two = [Row("k1", picture(tmp_path, "p1", seed=71))]
    signatures.sweep(one, workers=1, log=lambda *_: None)
    record = signatures.sweep(two, workers=1, log=lambda *_: None)
    assert record["rows"] == 2 and record["new"] == 1
    assert set(signatures.by_recipe()) == {"k0", "k1"}
