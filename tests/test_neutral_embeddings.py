"""The neutral render, and the store of vectors the gallery pass will select over.

Two things are being guarded here and they fail differently. The **frozen
choices** — the colormap, the geometry, the mode, the encoder — fail silently:
change one and every stored vector becomes a reading of a picture that no longer
exists, while a cosine between two of them is still a plausible number between
-1 and 1. The **store** fails loudly, and the tests below are mostly about the
count: a store one location short of its population is a gallery pass that
cannot choose that place and does not say so.

Nothing here builds a vector. The encoder is two hundred megabytes of downloaded
weights and a GPU pass, and what it returns is not a property this repository
decides; what this repository decides is the picture handed to it, the key the
answer is filed under, and whether the file survives.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.curation import durability, embeddings, neutral
from fractal_wallpapers.models import embedding

ROW = {
    "key": '["mandelbrot", 2, [], "-0.5", "0", "3"]',
    "partition": "mandelbrot",
    "family": {"kind": "mandelbrot"},
    "viewport": {"center_re": "-0.5", "center_im": "0", "width": "3"},
    "maxiter": 512,
    "ledger": "artifacts/harvest_here/walk.jsonl",
    "p_ge3": 0.9,
}


# --------------------------------------------------------------------------- #
# The frozen choices.
# --------------------------------------------------------------------------- #
def test_the_frame_is_a_whole_number_of_the_encoders_patches() -> None:
    """Which is the whole reason the geometry is 448x252 and not 640x360.

    DINOv2 tiles its input into 14-pixel patches. A frame that is not a multiple
    of 14 on both axes is resized on the way in — by whichever interpolation the
    transform happened to carry — and the vector is then a reading of a picture
    nobody chose.
    """
    width, height = neutral.RESOLUTION
    assert width % embedding.PATCH == 0 and height % embedding.PATCH == 0
    assert width * 9 == height * 16, "a wallpaper is 16:9 and so is the picture it is judged by"


def test_the_neutral_map_is_cyclic_so_nothing_is_mirrored() -> None:
    """`MIRROR` is False because the map wraps. If it stopped wrapping, every
    neutral render would grow a seam and nothing else here would notice."""
    assert neutral.MIRROR is False
    neutral.check_map()  # raises if the name has left the cyclic set


def test_a_changed_choice_changes_the_stamp() -> None:
    """The stamp is the whole mechanism: the manifest records it, every row
    carries it, and a leg that would append a second provenance refuses."""
    marked = neutral.stamp()
    assert len(marked) == 12
    assert neutral.stamp() == marked
    assert neutral.stamp({"variant": embedding.VARIANT}) != marked


def test_the_neutral_render_is_not_the_location_heads_view(tmp_path) -> None:
    """Two pictures of one place, and they must not collide on one file.

    The judged view follows whatever map the tile pool reserves in its floor
    slot; this one may not move at all. Both are `smooth` and both are addressed
    by a digest of their own recipe, so the guard is that the digests differ.
    """
    from fractal_wallpapers.models import location_view

    judged = location_view.view_name(ROW, location_view.canonical_map(), cyclic=set())
    assert neutral.neutral_name(ROW) != judged


def test_the_recipe_puts_every_palette_knob_at_the_value_that_does_nothing() -> None:
    """ "Neutral" is a claim about the picture, and this is the whole of it."""
    made = neutral.neutral_row(ROW)
    assert made["colormap"] == neutral.COLORMAP
    assert made["mode"] == "smooth" and made["curve"] == "linear"
    assert made["render"]["resolution"] == list(neutral.RESOLUTION)
    assert made["render"]["supersample"] == neutral.SUPERSAMPLE
    assert made["recipe"] == {
        "gamma": 1.0,
        "cycles": 1.0,
        "phase": 0.0,
        "reverse": False,
        "mirror": False,
        "transfer": {"kind": "value"},
        "rolloff": {"kind": "none"},
    }


# --------------------------------------------------------------------------- #
# The row, which carries its own vector and its own join.
# --------------------------------------------------------------------------- #
def test_a_vector_survives_the_round_trip_through_a_row() -> None:
    """Half precision, base64, and back. The tolerance is what `float16` has."""
    numpy = pytest.importorskip("numpy")

    vector = numpy.linspace(-1, 1, embedding.DIM).astype(numpy.float32)
    vector /= numpy.linalg.norm(vector)
    back = embeddings.unpack(embeddings.pack(vector))

    assert back.shape == (embedding.DIM,)
    assert numpy.abs(back - vector).max() < 1e-3
    assert abs(float(numpy.linalg.norm(back)) - 1.0) < 1e-3


def test_a_stored_row_re_renders_its_own_picture_without_any_ledger() -> None:
    """The join rule, and the reason the pictures are not copied to the archive:
    the store is what regenerates them, and it needs nothing else to do it."""
    numpy = pytest.importorskip("numpy")

    vector = numpy.ones(embedding.DIM, dtype=numpy.float32) / numpy.sqrt(embedding.DIM)
    name = neutral.neutral_name(ROW)
    row = embeddings.row_of(ROW, vector, f"{name}.jpg", "stamp12345678", neutral.choices())

    assert row["schema"] == embeddings.SCHEMA
    assert row["key"] == ROW["key"]
    assert neutral.neutral_name(row) == name, "the row must name the picture it carries"
    assert row["picture"] == f"{name}.jpg"
    assert row["location_p_ge3"] == 0.9


# --------------------------------------------------------------------------- #
# The store: keys in, count out.
# --------------------------------------------------------------------------- #
@pytest.fixture
def store(tmp_path, monkeypatch):
    """A live store, a durable copy beside it, and the manifest pointed at both."""
    live = tmp_path / "hot" / "curation" / embeddings.STORE_NAME
    copy = tmp_path / "cold" / durability.BACKUP_UNIT / embeddings.STORE_NAME
    manifest = tmp_path / "neutral_embeddings.manifest.json"
    live.parent.mkdir(parents=True)
    monkeypatch.setattr(embeddings, "store_path", lambda: live)
    monkeypatch.setattr(embeddings, "backup_path", lambda: copy)
    monkeypatch.setattr(embeddings, "manifest_path", lambda: manifest)
    monkeypatch.setattr(durability, "rehome", lambda stored: None)
    return live, copy, manifest


def write_store(path, count: int, stamp: str = "stamp12345678") -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for index in range(count):
            row = {
                **ROW,
                "key": f'["mandelbrot", 2, [], "{index}", "0", "3"]',
                "viewport": {"center_re": str(index), "center_im": "0", "width": "3"},
            }
            handle.write(
                json.dumps(
                    {
                        **embeddings.row_of(
                            row, [0.0] * embedding.DIM, "x.jpg", stamp, neutral.choices()
                        )
                    }
                )
                + "\n"
            )


def test_the_keys_are_read_without_decoding_a_single_vector(store) -> None:
    """`stored_keys` is what an incremental leg subtracts with, and it runs before
    anything is rendered, so it must not be the expensive read."""
    pytest.importorskip("numpy")
    live, _, _ = store
    write_store(live, 5)

    assert len(embeddings.stored_keys()) == 5
    assert '["mandelbrot", 2, [], "3", "0", "3"]' in embeddings.stored_keys()
    assert embeddings.stored_keys(live) == embeddings.stored_keys()


def test_an_empty_store_reads_as_no_keys_rather_than_a_failure(store) -> None:
    """A fresh clone has never embedded anything, and that is not an error."""
    assert embeddings.stored_keys() == set()
    assert embeddings.read() == []


def test_a_second_provenance_is_refused_rather_than_appended(store) -> None:
    """The one failure this whole stamp mechanism exists for."""
    pytest.importorskip("numpy")
    live, _, _ = store
    write_store(live, 3, stamp="oldstamp0000")

    with pytest.raises(embeddings.StoreRefused, match="arithmetic between unrelated numbers"):
        embeddings._refuse_a_second_provenance(live, "newstamp0000")
    # And says nothing where the stamps agree, or where there is nothing to disagree.
    embeddings._refuse_a_second_provenance(live, "oldstamp0000")
    embeddings._refuse_a_second_provenance(live.parent / "absent.jsonl", "newstamp0000")


def test_cover_names_the_locations_a_named_population_is_missing(store) -> None:
    """How "are all 475 judged locations in here" is asked."""
    pytest.importorskip("numpy")
    live, _, _ = store
    write_store(live, 3)

    answer = embeddings.cover(
        ['["mandelbrot", 2, [], "0", "0", "3"]', '["mandelbrot", 2, [], "9", "0", "3"]']
    )
    assert answer == {
        "asked": 2,
        "stored": 1,
        "absent": ['["mandelbrot", 2, [], "9", "0", "3"]'],
    }


def test_the_background_is_what_makes_a_neighbour_cosine_mean_anything() -> None:
    """A nearest neighbour at 0.96 reads as "barely distinguishable" until the
    background turns out to sit at 0.73. The degenerate store — every vector the
    same — is the case this measurement exists to catch, and it must show up as a
    background that has collapsed onto the neighbour rather than as an error."""
    numpy = pytest.importorskip("numpy")

    rng = numpy.random.default_rng(0)
    spread = rng.normal(size=(400, embedding.DIM)).astype(numpy.float32)
    spread /= numpy.linalg.norm(spread, axis=1, keepdims=True)
    wide = embeddings.background(spread, pairs=2000)
    assert wide["pairs"] == pytest.approx(2000, rel=0.02)
    assert abs(wide["median"]) < 0.1, "independent directions are near-orthogonal"

    one = numpy.repeat(spread[:1], 400, axis=0)
    assert embeddings.background(one, pairs=2000)["median"] == pytest.approx(1.0, abs=1e-3)
    assert embeddings.background(spread[:1], pairs=10) == {"pairs": 0}


def test_a_second_leg_cannot_append_while_the_first_one_is_running(store) -> None:
    """The planted red for what actually happened on 2026-08-22.

    Two legs compute the same outstanding list, render the same pictures and
    interleave half-written rows into one JSONL. The store then holds duplicate
    keys and lines that will not parse, and neither leg says anything about it.
    """
    from fractal_wallpapers.models import train

    live, _, _ = store
    held = train.claim(live.parent, name=embeddings.LOCK_NAME)
    try:
        with pytest.raises(RuntimeError, match="already has"):
            embeddings.build(log=lambda *_: None)
    finally:
        held.unlink()
    # And the lock is not left behind by a leg that refused for another reason.
    assert not list(live.parent.glob("*.lock"))


def test_the_two_ways_a_judged_location_leaves_the_gallery_passs_reach(
    tmp_path, monkeypatch
) -> None:
    """A judgement and a gap, and they must not be reported as one number.

    Below the junk floor is today's head disagreeing with a colorize somebody
    paid for. Absent from the sidecar is a location no cut has been applied to at
    all, because the standing supply has no row for it.
    """
    from fractal_wallpapers.curation import intake

    sidecar = tmp_path / "supply_scores.jsonl"
    rows = [
        {"schema": 1, "key": "good", "p_ge3": 0.9},
        {"schema": 1, "key": "weak", "p_ge3": 0.001},
    ]
    sidecar.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8", newline="\n"
    )
    monkeypatch.setattr(intake, "scores_path", lambda: sidecar)

    answer = embeddings.unreachable(
        {"good": "mandelbrot", "weak": "mandelbrot", "nowhere": "phoenix"}
    )
    assert answer["judged"] == 3 and answer["admitted"] == 1
    assert answer["below_the_junk_floor"] == {"count": 1, "keys": ["weak"]}
    assert answer["absent_from_the_sidecar"] == {"count": 1, "keys": ["nowhere"]}


# --------------------------------------------------------------------------- #
# The pilot's draw.
# --------------------------------------------------------------------------- #
def test_the_stratified_draw_spreads_over_the_partitions_and_is_seeded() -> None:
    """A pilot drawn uniformly over this supply would be four fifths julia and
    would say nothing about how the parameter planes behave."""
    rows = [
        {"key": f"{name}:{index}", "partition": name}
        for name, count in (("julia:mandelbrot", 900), ("mandelbrot", 90), ("phoenix", 10))
        for index in range(count)
    ]
    drawn = embeddings.stratified(rows, 100, seed=0)

    assert len(drawn) == 100
    counted = {name: 0 for name in ("julia:mandelbrot", "mandelbrot", "phoenix")}
    for row in drawn:
        counted[row["partition"]] += 1
    assert counted["julia:mandelbrot"] > counted["mandelbrot"] > 0
    assert counted["phoenix"] >= 1, "every partition with supply is in the pilot"
    assert embeddings.stratified(rows, 100, seed=0) == drawn
    assert embeddings.stratified(rows, 100, seed=1) != drawn


def test_asking_for_more_than_there_is_returns_everything() -> None:
    rows = [{"key": str(index), "partition": "mandelbrot"} for index in range(5)]
    assert embeddings.stratified(rows, 50) == rows


# --------------------------------------------------------------------------- #
# Durability: the same three verbs the supply sidecar has.
# --------------------------------------------------------------------------- #
def test_the_manifest_carries_the_count_the_hash_and_the_frozen_choices(store) -> None:
    """The vectors are not in the history; these facts about them are."""
    pytest.importorskip("numpy")
    live, copy, manifest = store
    write_store(live, 4)

    record = durability.save(embeddings.store(), when="2026-01-01", log=lambda *_: None)

    assert record["rows"] == 4
    assert record["bytes"] == live.stat().st_size
    assert len(record["sha256"]) == 64
    assert record["stamp"] == "stamp12345678"
    assert record["choices"] == neutral.choices()
    assert record["rows_by_partition"] == {"mandelbrot": 4}
    assert record["pictures"]["directory"].endswith("neutral")
    assert json.loads(manifest.read_text(encoding="utf-8")) == record
    assert copy.is_file()
    assert "\r\n" not in manifest.read_text(encoding="utf-8", newline="")


def test_the_copy_does_not_share_the_name_the_tiers_arbitrate(store) -> None:
    """Same rule as the sidecar's copy: `curation` is a name the tier collision
    guard moves to exactly one disk, and this is the file meant to be on both."""
    _, copy, _ = store
    assert durability.BACKUP_UNIT != "curation"
    assert copy.parent.name == durability.BACKUP_UNIT


def test_a_store_that_has_grown_is_not_a_store_that_is_broken(store) -> None:
    """`grown` is the ordinary state between a harvest's admissions being
    embedded and the next save, and it must not read as a loss."""
    pytest.importorskip("numpy")
    live, _, _ = store
    write_store(live, 4)
    durability.save(embeddings.store(), log=lambda *_: None)
    write_store(live, 9)

    assert durability.check(embeddings.store(), log=lambda *_: None)["verdict"] == "grown"

    write_store(live, 2)
    assert durability.check(embeddings.store(), log=lambda *_: None)["verdict"] == "short"


def test_a_restore_will_not_delete_admissions_nobody_has_saved(store) -> None:
    """The live store is append-only, so a live file AHEAD of the manifest is
    work, not corruption. The refusal names the command that records it."""
    pytest.importorskip("numpy")
    live, _, _ = store
    write_store(live, 4)
    durability.save(embeddings.store(), log=lambda *_: None)
    write_store(live, 9)

    with pytest.raises(durability.DurableLost, match="curate embeddings save"):
        durability.restore(embeddings.store(), log=lambda *_: None)
    assert durability.count_rows(live) == 9

    durability.restore(embeddings.store(), force=True, log=lambda *_: None)
    assert durability.count_rows(live) == 4


def test_the_refusal_when_nothing_is_there_names_the_command_that_builds_it(store) -> None:
    """A refusal a reader has to come back and ask about is half a refusal."""
    with pytest.raises(durability.DurableLost, match="curate embed"):
        durability.save(embeddings.store(), log=lambda *_: None)


# --------------------------------------------------------------------------- #
# The command line.
# --------------------------------------------------------------------------- #
def test_the_curate_group_carries_the_four_subcommands() -> None:
    """`embed` makes the store, `embeddings` keeps it, `neighbours` reads it,
    `reach` says which judged locations it cannot hold."""
    from fractal_wallpapers import cli

    parser = cli.build_parser()
    for step in ("embed", "embeddings", "neighbours", "reach"):
        parsed = parser.parse_args(
            ["curate", step, "check"] if step == "embeddings" else ["curate", step]
        )
        assert callable(parsed.handler)
